;; Negative controls for the coverage report (JUN-890, ADR 0410).
;;
;; Each control damages a copy of the real snapshot and requires the number to
;; fall, or the report to refuse. Nothing here touches the committed files.
;; Ported from test_scoreboard.py.
;; Run from the repo root:
;;   PYTHONPATH=scripts/coverage basilisp test -- -p no:cacheprovider --rootdir scripts/coverage scripts/coverage/test_scoreboard.cljc
(ns test-scoreboard
  (:require [basilisp.test :refer [deftest is]]
            [scoreboard :as sb])
  (:import hashlib json operator pathlib shutil tempfile
           [receipt_privacy :as privacy]))

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

(deftest a-matching-digest-does-not-admit-private-receipt-data
  (doseq [field [{"password" "synthetic-credential-marker"}
                 {"contact" "synthetic@example.invalid"}
                 {"phoneNumber" "+1 202 555 0100"}
                 {"args" ["/Users/synthetic/workspace/compiler"]}]]
    (let [result (scored (rewrite arm #(assoc % "nested" [field])))]
      (is (= [0 809] (bounds result)))
      (is (= [(str arm ": receipt publication check failed")]
             (get-in result ["targets" "aarch64-linux" "L1" "problems"]))))))

(deftest text-evidence-refuses-private-fields-and-preserves-public-metadata
  (doseq [[value kind] [["GITHUB_TOKEN='synthetic-credential-marker'" "credential"]
                        ["Authorization: Bearer synthetic-credential-marker" "credential"]
                        ["Contact: synthetic@example.invalid" "email"]
                        ["Phone number: +1 202 555 0100" "personal information"]
                        ["Mailing address: 123 Example Street" "personal information"]]]
    (is (= kind (try (privacy/publication_bytes (.encode value) false)
                    (catch privacy/ReceiptPrivacyError error (str error))))))
  (let [public (str "platform=Darwin arm64\n/usr/bin/true\nfile:///usr/bin/true\n"
                    "source=https://github.com/kotoba-lang/amu\nsha256=" zeros "\n")
        original (str public "argv=/Users/synthetic-user/work/input\n"
                       "trace=file:///Users/synthetic-user/work/output\n"
                       "temp=/private/tmp/synthetic-run/result\n")
        expected (str public "argv=<host-home>/work/input\n"
                       "trace=file://<host-home>/work/output\n"
                       "temp=<host-temp>/result\n")
        control (.read_bytes (.joinpath sb/root "docs/qualification/android-a1/20261106/out/fs-control.txt"))]
    (is (operator/eq (.encode expected) (privacy/publication_bytes (.encode original) false)))
    (is (operator/eq control (privacy/publication_bytes control false)))))

(deftest report-output-is-confined-to-the-workspace
  (with-open [temp (tempfile/TemporaryDirectory)]
    (let [workspace (pathlib/Path temp "workspace")
          report-path (.joinpath workspace "score.json")
          outside (pathlib/Path temp "outside.json")
          args ["report" "--snapshot" (str snapshot-dir) "--as-of" day "--output"]]
      (.mkdir workspace)
      (with-redefs [sb/root workspace]
        (is (= 1 (apply sb/-main (conj args (str outside)))))
        (is (not (.exists outside)))
        (is (= 0 (apply sb/-main (conj args (str report-path)))))
        (is (= [215 809] (bounds (sb/read-json report-path))))
        (is (= 1 (sb/-main "collect" "--date" "20260230")))))))

(deftest collect-publishes-sanitized-copies-with-both-digests
  (with-open [temp (tempfile/TemporaryDirectory)]
    (let [workspace (pathlib/Path temp "workspace")
          coverage (.joinpath workspace "coverage")
          out (.joinpath coverage "snapshots/20261128")
          blocked (.joinpath coverage "snapshots/20261129")
          runs {"selfhost" 1 "mac" 2}
          artifact-names (vec (keys sb/artifacts))
          receipt (.joinpath out "receipts" arm)
          incoming (atom nil)
          download (fn [_ artifact dest]
                     (shutil/copytree (.joinpath snapshot-dir "receipts" artifact) dest)
                     (when (= "bootstrap-arm64" artifact)
                       (.write_text (.joinpath dest "selfhost-bootstrap.json") @incoming)))
          gh (fn [& args]
               (if (= "run" (first args))
                 {"workflowName" (if (= "1" (nth args 2)) "selfhost-native" "mac-selfhost-aiueos")
                  "conclusion" "success" "headSha" zeros "createdAt" "2026-11-06T00:00:00Z"}
                 {"artifacts" (mapv (fn [name] {"name" name "id" name "digest" zeros}) artifact-names)}))
          baseline (sb/read-json (.joinpath snapshot-dir "receipts" arm))]
      (with-redefs [sb/root workspace sb/coverage coverage sb/gh-json gh sb/download-artifact download]
        (reset! incoming (sb/dump (assoc baseline "args" ["/Users/synthetic/work/bin/amu"])))
        (let [provenance (sb/collect table runs out)]
          (is (= ["<host-home>/work/bin/amu"] (get (sb/read-json receipt) "args")))
          (is (= (.hexdigest (hashlib/sha256 (.encode @incoming))) (get-in provenance ["receivedReceiptSha256" arm])))
          (is (= (sb/digest receipt) (get-in provenance ["receipts" arm])))
          (is (= [215 809] (bounds (sb/report table out day)))))
        (reset! incoming (sb/dump (assoc baseline "password" "synthetic-credential-marker")))
        (is (try (sb/collect table runs blocked) false
                 (catch basilisp.lang.exception/ExceptionInfo e (sb/refused? e))))
        (is (not (.exists blocked)))))))
