(ns kotoba.compiler.test-runner
  (:require [clojure.test :as t]
            [kotoba.compiler.atomic-output-test]
            [kotoba.compiler.aiueos-target-test]
            [kotoba.compiler.accelerator-test]
            [kotoba.compiler.cli-test]
            [kotoba.compiler.component-abi-test]
            [kotoba.compiler.core-test]
            [kotoba.compiler.coverage-test]
            [kotoba.compiler.coverage-evidence-test]
            [kotoba.compiler.bounded-edn-test]
            [kotoba.compiler.frontend-fuzz-test]
            [kotoba.compiler.frontend-limits-test]
            [kotoba.compiler.frontend-extensions-test]
            [kotoba.compiler.f64-value-test]
            [kotoba.compiler.frontend-destructuring-loop-test]
            [kotoba.compiler.backend-cljs-test]
            [kotoba.compiler.ios-aot-test]
            [kotoba.compiler.native-executor-test]
            [kotoba.compiler.admission-test]
            [kotoba.compiler.property-test]
            [kotoba.compiler.receipt-test]
            [kotoba.compiler.release-test]
            [kotoba.compiler.security-fuzz-test]
            [kotoba.compiler.signing-test]
            [kotoba.compiler.typed-value-test]
            [kotoba.compiler.verifier-profile-test]))

(defn -main [& _]
  (let [{:keys [fail error]} (t/run-tests 'kotoba.compiler.atomic-output-test
                                          'kotoba.compiler.aiueos-target-test
                                          'kotoba.compiler.accelerator-test
                                          'kotoba.compiler.cli-test
                                          'kotoba.compiler.component-abi-test
                                          'kotoba.compiler.core-test
                                          'kotoba.compiler.coverage-test
                                          'kotoba.compiler.coverage-evidence-test
                                          'kotoba.compiler.bounded-edn-test
                                          'kotoba.compiler.frontend-fuzz-test
                                          'kotoba.compiler.frontend-limits-test
                                          'kotoba.compiler.frontend-extensions-test
                                          'kotoba.compiler.f64-value-test
                                          'kotoba.compiler.frontend-destructuring-loop-test
                                          'kotoba.compiler.backend-cljs-test
                                          'kotoba.compiler.ios-aot-test
                                          'kotoba.compiler.admission-test
                                          'kotoba.compiler.signing-test
                                          'kotoba.compiler.native-executor-test
                                          'kotoba.compiler.receipt-test
                                          'kotoba.compiler.release-test
                                          'kotoba.compiler.security-fuzz-test
                                          'kotoba.compiler.typed-value-test
                                          'kotoba.compiler.verifier-profile-test
                                          'kotoba.compiler.property-test)]
    ;; Compiler tests may initialize non-daemon backend/runtime workers. Exit
    ;; explicitly on success as well as failure so CI cannot hang after a
    ;; complete green assertion report.
    (System/exit (if (pos? (+ fail error)) 1 0))))
