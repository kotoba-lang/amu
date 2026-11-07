;; Native compiler-local bounded scan grammar and CFG refusal controls.
;; Ported from check-sequential-scan.py (Basilisp, JUN-974). --selfbuild-output is the output directory of selfhost-bootstrap.
;; Run on arm64 Linux: basilisp run -p scripts/seed scripts/seed/check-sequential-scan.cljc -- --selfbuild-output DIR
(ns check-sequential-scan
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [selfbuild-controls :as sc])
  (:import sys))

(defn -main [& args]
  (sc/run (or (u/opt args "--selfbuild-output") (sys/exit "--selfbuild-output is required"))
          {:dir "sequential-scan-controls" :producer "sequential-scan-producer.bin" :fixture "seed/tests/unit/clw_sequential_scan_t.kotoba" :calls "sequential-scan-calls.json" :report "sequential-scan-controls-report.json" :prefix "scan-controls" :status "PASS_NATIVE_SEQUENTIAL_SCAN_ADMISSION_REFUSAL_CONTROLS"
           :fields [["boundedLengths" (python/list (range 2 9))] ["singleWordOpcodeRegisterMutations" 126] ["extentRefusals" 7] ["invalidLengthRefusals" 14] ["newAndOldCFGEdgeControls" 19]]}))

(when (some #(or (= % "check-sequential-scan.cljc") (str/ends-with? % "/check-sequential-scan.cljc")) sys/argv)
  (apply -main *command-line-args*))
