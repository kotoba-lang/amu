;; Exercise the descriptor writer on a disposable receipt-derived fixture.
;;
;; Ad-hoc Mac signatures can differ by host. This tests update/refusal behavior; it does not assert that the
;; checkout's signed descriptors match this host. Ported from check-descriptor-writer-ci.py (Basilisp, JUN-974):
;; the fixture carries the Basilisp writer, its test and the shared helper, and both run from inside it.
;; Run: basilisp run -p scripts/seed scripts/seed/check-descriptor-writer-ci.cljc -- --mac-build DIR --cross-build DIR
(ns check-descriptor-writer-ci
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import pathlib shutil subprocess sys tempfile))

(def files
  ["scripts/seed/gate_util.cljc" "scripts/seed/write-bootstrap-descriptors.cljc" "scripts/seed/test-write-bootstrap-descriptors.cljc"
   "examples/foundation-starter/candidate.json" "seed/bootstrap/aarch64-macos/root.json"
   "seed/bootstrap/aarch64-linux-static-root.json" "native-product.json"
   "seed/bootstrap/aarch64-macos/amu-full-root.macho" "seed/bootstrap/aarch64-macos/kotoba-packager-root.macho"
   "seed/bootstrap/aarch64-linux-static-root.elf" "bin/amu-linux-x86_64" "bin/x86_64-linux/amu"])

(defn -main [& args]
  (let [mac (.resolve (pathlib/Path (or (u/opt args "--mac-build") (sys/exit "--mac-build is required"))) ** :strict true)
        cross (.resolve (pathlib/Path (or (u/opt args "--cross-build") (sys/exit "--cross-build is required"))) ** :strict true)
        tmp (tempfile/TemporaryDirectory ** :prefix "descriptor-writer-ci-")
        repo (pathlib/Path (.__enter__ tmp))
        bl (fn [script & extra]
             (subprocess/run (python/list (concat ["basilisp" "run" "-p" "scripts/seed" (str "scripts/seed/" script) "--"] (map str extra)))
                             ** :cwd repo :check true))]
    (try
      (doseq [rel files]
        (let [dst (pathlib/Path repo rel)]
          (.mkdir (.-parent dst) ** :parents true :exist_ok true)
          (shutil/copyfile (pathlib/Path u/root rel) dst)))
      ;; Writer validates receipts and hashes before modifying this fixture.
      (bl "write-bootstrap-descriptors.cljc" "--mac-build" mac "--cross-build" cross "--repo" repo "--write" "--install")
      (bl "test-write-bootstrap-descriptors.cljc" "--mac-build" mac "--cross-build" cross)
      (finally (.__exit__ tmp nil nil nil)))
    (println "PASS_DISPOSABLE_DESCRIPTOR_WRITER_FIXTURE")))

(when (some #(or (= % "check-descriptor-writer-ci.cljc") (str/ends-with? % "/check-descriptor-writer-ci.cljc")) sys/argv)
  (apply -main *command-line-args*))
