;; Negative controls for the coverage report (JUN-890, ADR 0410).
;;
;; Each control damages a copy of the real snapshot and requires the number to
;; fall, or the report to refuse. Nothing here touches the committed files.
;; Ported from test_scoreboard.py.
;; Run from the repo root:
;;   PYTHONPATH=scripts/coverage basilisp test -p no:cacheprovider --rootdir scripts/coverage scripts/coverage/test_scoreboard.cljc
(ns test-scoreboard
  (:require [basilisp.test :refer [deftest is]]
            [scoreboard :as sb])
  (:import hashlib json pathlib shutil tempfile))

(def snapshot-dir (.joinpath sb/coverage "snapshots/20261106"))
(def table (sb/read-json (.joinpath sb/coverage "table.json")))
(def day "2026-11-06")
(def arm "bootstrap-arm64/selfhost-bootstrap.json")
(def x86 "x86_64-native-receipt/x86/x86_64-native.json")
(def x86-complete "x86_64-native-receipt/complete/complete-x86.json")
(def mac "mac-aiueos-user-root/public-macos-product/public-macos-product.json")

(defn scored
  ([] (scored nil table day))
  ([damage] (scored damage table day))
  ([damage tbl] (scored damage tbl day))
  ([damage tbl as-of]
   (with-open [temp (tempfile/TemporaryDirectory)]
     (let [snapshot (pathlib/Path temp "snapshot")]
       (shutil/copytree snapshot-dir snapshot)
       (when damage (damage snapshot))
       (sb/report tbl snapshot as-of)))))

(defn bounds [result] [(get result "lowerBasisPoints") (get result "upperBasisPoints")])

(defn refused? [damage tbl]
  (try (scored damage tbl) false
       (catch basilisp.lang.exception/ExceptionInfo e (sb/refused? e))))

(defn remove-receipt [path]
  (fn [snapshot] (.unlink (.joinpath (.joinpath snapshot "receipts") path))))

(defn rewrite
  ([path change] (rewrite path change true))
  ([path change fix-digest]
   (fn [snapshot]
     (let [file (.joinpath (.joinpath snapshot "receipts") path)
           body (change (sb/read-json file))]
       (.write_text file (json/dumps (sb/to-py body)))
       (when fix-digest
         (let [name (.joinpath snapshot "provenance.json")
               provenance (assoc-in (sb/read-json name) ["receipts" path]
                                    (.hexdigest (hashlib/sha256 (.read_bytes file))))]
           (.write_text name (json/dumps (sb/to-py provenance)))))))))

(defn change-runs [change]
  (fn [snapshot]
    (let [name (.joinpath snapshot "provenance.json")
          provenance (update (sb/read-json name) "runs" change)]
      (.write_text name (json/dumps (sb/to-py provenance))))))

(defn with-slice [name fields]
  (update-in table ["denominator" "slices" name] merge fields))

(def zeros (apply str (repeat 64 "0")))

(deftest baseline
  (let [b (scored)]
    (is (= [215 809] (bounds b)))
    (is (false? (get b "gateVerdict")))
    (is (false? (get b "meetsThreshold")))
    (is (= 9918 (get b "denominatorBasisPoints")))
    (is (= {"x86_64-linux" true "aarch64-linux" false "aarch64-macos" true
            "x86_64-macos" false "x86_64-windows" false "aarch64-windows" false}
           (get b "developmentHostsAtL3")))
    ;; A cell the OS forbids is not a pass, and nothing evidences a missing target.
    (is (= "prohibited" (get-in b ["targets" "aarch64-ios" "L3" "state"])))
    (is (= 0 (get-in b ["slices" "ios" "upperBasisPoints"])))))

(deftest removing-evidence-lowers-the-number
  ;; Linux needs both ISAs in the lower bound.
  (is (= [0 809] (bounds (scored (remove-receipt arm)))))
  (is (= [0 809] (bounds (scored (remove-receipt x86)))))
  (is (= [215 215] (bounds (scored (remove-receipt mac)))))
  (is (= [0 594] (bounds (scored (fn [s] ((remove-receipt arm) s) ((remove-receipt x86) s)))))))

(deftest removing-evidence-from-one-level-fails-that-level-alone
  (let [r (scored (remove-receipt x86-complete))]
    (is (= "fail" (get-in r ["targets" "x86_64-linux" "L3" "state"])))
    (is (= "pass" (get-in r ["targets" "x86_64-linux" "L1" "state"])))
    (is (false? (get-in r ["developmentHostsAtL3" "x86_64-linux"])))))

(deftest a-receipt-must-say-the-right-thing-even-with-a-matching-digest
  (doseq [[name change] [["status" #(assoc % "status" "FAIL")]
                         ["emulation" #(assoc % "emulation" true)]
                         ["other host" #(assoc % "host" ["Linux" "x86_64"])]
                         ["dropped required field" #(dissoc % "cCompilerOrLoader")]]]
    (is (= [0 809] (bounds (scored (rewrite arm change)))) name))
  ;; Emulation fails a cell even when the table does not name that field.
  (is (= [215 215] (bounds (scored (rewrite mac #(assoc % "emulation" true)))))))

(deftest unrecorded-edit-and-hostless-receipt
  (is (= [0 809] (bounds (scored (rewrite arm identity false)))))
  (is (= [0 809] (bounds (scored (rewrite arm #(dissoc % "host"))))))
  (is (= [215 215] (bounds (scored (rewrite "mac-aiueos-user-root/mac-smoke/execution/receipt.json" #(dissoc % "host")))))))

(deftest a-fixed-point-needs-identical-generations
  (is (= "fail" (get-in (scored (rewrite x86-complete #(assoc-in % ["generations" 0 "sha256"] zeros)))
                        ["targets" "x86_64-linux" "L3" "state"]))))

(deftest old-evidence-counts-as-nothing
  (is (= [215 809] (bounds (scored nil table "2026-12-06"))))
  (is (= [0 0] (bounds (scored nil table "2026-12-07")))))

(deftest runs-must-agree-and-must-have-succeeded
  (is (refused? (change-runs #(assoc-in % ["mac" "headSha"] (apply str (repeat 40 "0")))) table))
  (is (refused? (change-runs #(assoc-in % ["selfhost" "conclusion"] "failure")) table))
  (is (refused? (change-runs #(dissoc % "mac")) table)))

(deftest a-measured-split-gives-partial-credit-and-must-be-whole
  (is (= [(+ 215 534) (+ 215 534)]
         (bounds (scored nil (with-slice "macos" {"isaSplitBasisPoints" {"aarch64-macos" 9000 "x86_64-macos" 1000}}) day))))
  (is (refused? nil (with-slice "macos" {"isaSplitBasisPoints" {"aarch64-macos" 9000 "x86_64-macos" 999}})))
  (is (refused? nil (with-slice "macos" {"isaSplitBasisPoints" {"aarch64-macos" 10000}}))))

(deftest the-table-cannot-overclaim
  (is (refused? nil (with-slice "linux" {"shareBasisPoints" 2000})))
  (is (refused? nil (with-slice "linux" {"targets" ["x86_64-linux" "aarch64-macos"]})))
  (is (refused? nil (with-slice "linux" {"targets" ["riscv64-linux"]}))))
