;; Native compiler-local positive interval, entry and scratch refusal controls.
;; Ported from check-positive-quotient-proof.py (Basilisp, JUN-974). --selfbuild-output is the output directory of selfhost-bootstrap.
;; Run on arm64 Linux: basilisp run -p scripts/seed scripts/seed/check-positive-quotient-proof.cljc -- --selfbuild-output DIR
(ns check-positive-quotient-proof
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [selfbuild-controls :as sc])
  (:import sys))

(defn -main [& args]
  (sc/run (or (u/opt args "--selfbuild-output") (sys/exit "--selfbuild-output is required"))
          {:dir "positive-quotient-proof-controls" :producer "positive-quotient-proof-producer.bin" :fixture "seed/tests/unit/positive_quotient_t.kotoba" :calls "positive-quotient-proof-calls.json" :report "positive-quotient-proof-controls-report.json" :prefix "positive-proof" :status "PASS_NATIVE_POSITIVE_QUOTIENT_RANGE_ROOT_SCRATCH_REFUSALS"
           :fields [["positiveAdmission" true] ["wordRefusals" 6] ["incomingRootRefusals" 5] ["rangeWorkBudgetRefusal" true] ["signed64OverflowRefusal" true]]}))

(when (some #(or (= % "check-positive-quotient-proof.cljc") (str/ends-with? % "/check-positive-quotient-proof.cljc")) sys/argv)
  (apply -main *command-line-args*))
