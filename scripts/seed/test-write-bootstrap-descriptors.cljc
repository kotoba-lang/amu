;; Controls for write-bootstrap-descriptors (JUN-545). Ported from test-write-bootstrap-descriptors.py (Basilisp,
;; JUN-974). Takes the outputs of the Mac gate and the cross gate and runs, on copies: the committed descriptors
;; against their own receipts (DESCRIPTORS_CURRENT); four refusals (one digit of the mac receipt, one byte of the
;; x86 compiler, of the x86 host entry, of the signed compiler); a wrong digest reported as differing, --write
;; repairing it, a second --check current; the source phase current, an unknown cross status refused, the final
;; phase without a cross build refused; --install refused without --write, leaving a current repo alone and
;; restoring a corrupted binary; the starter candidate rebinding without release authority.
;; Run: basilisp run -p scripts/seed scripts/seed/test-write-bootstrap-descriptors.cljc -- --mac-build DIR --cross-build DIR
(ns test-write-bootstrap-descriptors
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator pathlib shutil subprocess sys tempfile))

(def root u/root)
(def seed-dir (pathlib/Path root "scripts/seed"))
(def writer (pathlib/Path seed-dir "write-bootstrap-descriptors.cljc"))
(def binaries ["seed/bootstrap/aarch64-macos/amu-full-root.macho" "seed/bootstrap/aarch64-macos/kotoba-packager-root.macho"
               "seed/bootstrap/aarch64-linux-static-root.elf" "bin/amu-linux-x86_64" "bin/x86_64-linux/amu"])
(def files ["seed/bootstrap/aarch64-macos/root.json" "seed/bootstrap/aarch64-linux-static-root.json" "native-product.json"])

(defn writer-run [& args]
  (subprocess/run (python/list (concat ["basilisp" "run" "-p" (str seed-dir) (str writer) "--"] (map str args)))
                  ** :capture_output true :text true :cwd root))

(defn run
  ([mac cross] (run mac cross root))
  ([mac cross repo & extra] (apply writer-run "--mac-build" mac "--cross-build" cross "--repo" repo extra)))

(defn flip [path offset]
  (let [data (python/bytearray (.read_bytes path))]
    (operator/setitem data offset (bit-xor (operator/getitem data offset) 1))
    (.write_bytes path (python/bytes data))))

(defn g [m & ks] (reduce (fn [a k] (operator/getitem a k)) m ks))
(defn rj [p] (json/loads (.read_text p)))
(defn out- [r] (str (.-stdout r) (.-stderr r)))
(defn with-tmp [f]
  (let [d (tempfile/TemporaryDirectory)
        name (.__enter__ d)]
    (try (f (pathlib/Path name)) (finally (.__exit__ d nil nil nil)))))
(defn copy-in [repo rels]
  (doseq [rel rels]
    (.mkdir (.-parent (pathlib/Path repo rel)) ** :parents true :exist_ok true)
    (shutil/copy (pathlib/Path root rel) (pathlib/Path repo rel))))

(defn -main [& args]
  (let [mac-build (pathlib/Path (or (u/opt args "--mac-build") (sys/exit "--mac-build is required")))
        cross-build (pathlib/Path (or (u/opt args "--cross-build") (sys/exit "--cross-build is required")))
        failures (atom [])
        expect (fn [name cond & [detail]]
                 (println (str (if cond "ok   " "FAIL ") name (when-not cond (str "  " detail))))
                 (when-not cond (swap! failures conj name)))
        refused? (fn [r] (and (= (.-returncode r) 2) (str/includes? (.-stderr r) "REFUSED")))]
    (let [r (run mac-build cross-build)]
      (expect "committed descriptors are current" (and (= (.-returncode r) 0) (str/includes? (.-stdout r) "DESCRIPTORS_CURRENT")) (out- r)))
    (with-tmp
      (fn [tmp]
        (let [mac (pathlib/Path tmp "mac") cross (pathlib/Path tmp "cross")]
          (shutil/copytree mac-build mac)
          (shutil/copytree cross-build cross)
          (let [receipt (pathlib/Path mac "mac-aiueos-user-target.json")
                text (.read_text receipt)
                i (if (str/includes? text "e031180f") (.index text "e031180f") (+ (.index text "\"sha256\"") 12))]
            (.write_text receipt (str (subs text 0 i) (if (not= (nth text i) "f") "f" "e") (subs text (inc i))))
            (expect "one digit of the mac receipt is refused" (refused? (run mac cross-build)) "")
            (shutil/copy (pathlib/Path mac-build "mac-aiueos-user-target.json") receipt))
          (flip (pathlib/Path cross "F-x86_64.elf") 100)
          (expect "one byte of the x86 compiler is refused" (refused? (run mac-build cross)) "")
          (shutil/copy (pathlib/Path cross-build "F-x86_64.elf") (pathlib/Path cross "F-x86_64.elf"))
          (flip (pathlib/Path cross "H-x86_64.elf") 100)
          (expect "one byte of the x86 host entry is refused (KOTOBA-174)" (refused? (run mac-build cross)) "")
          (shutil/copy (pathlib/Path cross-build "H-x86_64.elf") (pathlib/Path cross "H-x86_64.elf"))
          (flip (pathlib/Path mac "F2-signed.macho") 5000)
          (expect "one byte of the signed compiler is refused" (refused? (run mac cross-build)) "")
          (let [repo (pathlib/Path tmp "repo")]
            (copy-in repo files)
            (let [product (pathlib/Path repo "native-product.json")
                  original (.read_text product)
                  mutated (json/loads original)
                  digest (g mutated "image" "sha256")]
              (operator/setitem (g mutated "image") "sha256" (str (if (not= (first digest) \0) "0" "1") (subs digest 1)))
              (operator/setitem mutated "compilerGenerations" (python/list (repeat 3 (python/dict (g mutated "image")))))
              (doseq [f ["nativePinnedCheckAndCompile" "controllerQualified" "currentCompilerLinkVerified" "broaderPublicCompatibilityQualified"]]
                (operator/setitem mutated f true))
              (.write_text product (str (json/dumps mutated ** :indent 2 :ensure_ascii false) "\n"))
              (expect "descriptor negative control actually changes image digest" (not= (g mutated "image" "sha256") digest))
              (let [r (run mac-build cross-build repo)]
                (expect "a wrong descriptor digest is reported" (and (= (.-returncode r) 1) (str/includes? (.-stdout r) "DESCRIPTORS_DIFFER")) (out- r)))
              (let [r (run mac-build cross-build repo "--write")
                    repaired (rj product)
                    expected (json/loads original)]
                (expect "--write repairs pins and invalidates prior compiler qualification"
                        (and (= (.-returncode r) 0) (u/deq (g repaired "image") (g expected "image"))
                             (u/deq (g repaired "sourceUnity") (g expected "sourceUnity"))
                             (nil? (g repaired "sourceRevision")) (u/deq (g repaired "compilerGenerations") (python/list []))
                             (every? #(false? (g repaired %)) ["nativePinnedCheckAndCompile" "controllerQualified" "currentCompilerLinkVerified" "broaderPublicCompatibilityQualified"]))
                        (out- r)))
              (let [r (run mac-build cross-build repo)]
                (expect "a second check is current" (and (= (.-returncode r) 0) (str/includes? (.-stdout r) "DESCRIPTORS_CURRENT")) (.-stdout r))))))))
    (let [r (writer-run "--phase" "source" "--mac-build" mac-build)]
      (expect "the source phase is current on the same receipt" (and (= (.-returncode r) 0) (str/includes? (.-stdout r) "DESCRIPTORS_CURRENT")) (out- r)))
    (let [r (writer-run "--mac-build" mac-build)]
      (expect "the final phase needs a cross build" (refused? r) (.-stderr r)))
    (with-tmp
      (fn [tmp]
        (let [cross (pathlib/Path tmp "cross")]
          (shutil/copytree cross-build cross)
          (let [receipt (pathlib/Path cross "cross.json") record (rj receipt)]
            (operator/setitem record "status" "SOMETHING_ELSE")
            (.write_text receipt (u/json-dump record))
            (expect "an unknown cross status is refused" (refused? (run mac-build cross)) "")))))
    (let [r (run mac-build cross-build root "--install")]
      (expect "--install without --write is refused" (refused? r) (.-stderr r)))
    (with-tmp
      (fn [repo]
        (copy-in repo (concat files binaries))
        (let [r (run mac-build cross-build repo "--write" "--install")]
          (expect "--install leaves a current repository alone"
                  (and (= (.-returncode r) 0) (not (str/includes? (.-stdout r) "installed")) (str/includes? (.-stdout r) "DESCRIPTORS_CURRENT")) (out- r)))
        (flip (pathlib/Path repo "bin/amu-linux-x86_64") 1000)
        (let [r (run mac-build cross-build repo "--write" "--install")]
          (expect "--install restores a corrupted binary"
                  (and (= (.-returncode r) 0) (str/includes? (.-stdout r) "installed bin/amu-linux-x86_64")
                       (u/deq (.read_bytes (pathlib/Path repo "bin/amu-linux-x86_64")) (.read_bytes (pathlib/Path root "bin/amu-linux-x86_64"))))
                  (out- r)))))
    (with-tmp
      (fn [repo]
        (copy-in repo files)
        (let [candidate (pathlib/Path repo "examples/foundation-starter/candidate.json")]
          (.mkdir (.-parent candidate) ** :parents true)
          (let [expected (rj (pathlib/Path root "examples/foundation-starter/candidate.json"))
                stale (json/loads (json/dumps expected))
                zeros (apply str (repeat 64 "0"))]
            (operator/setitem (g stale "compilerImage") "sha256" zeros)
            (operator/setitem (g stale "compilerSourceUnity") "sha256" zeros)
            (operator/setitem stale "publicReleaseReady" true)
            (.write_text candidate (u/json-dump stale))
            (let [r (run mac-build cross-build repo "--write")
                  repaired (rj candidate)
                  product (rj (pathlib/Path repo "native-product.json"))]
              (expect "changed compiler rebinds starter pins without carrying release authority"
                      (and (= (.-returncode r) 0) (u/deq (g repaired "compilerImage") (g product "image"))
                           (u/deq (g repaired "compilerSourceUnity") (g product "sourceUnity"))
                           (nil? (g repaired "upstreamRevision")) (false? (g repaired "publicReleaseReady"))
                           (u/deq (g repaired "fixtures") (g expected "fixtures")))
                      (out- r)))
            (let [r (run mac-build cross-build repo)]
              (expect "rebound starter is idempotent" (and (= (.-returncode r) 0) (str/includes? (.-stdout r) "DESCRIPTORS_CURRENT")) (out- r)))))))
    (if (empty? @failures)
      (do (println "PASS_BOOTSTRAP_DESCRIPTOR_WRITER") (sys/exit 0))
      (do (println (str "FAILED " (vec @failures))) (sys/exit 1)))))

(when (some #(or (= % "test-write-bootstrap-descriptors.cljc") (str/ends-with? % "/test-write-bootstrap-descriptors.cljc")) sys/argv)
  (apply -main *command-line-args*))
