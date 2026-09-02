(ns kotoba.compiler.test-runner
  (:require [clojure.test :as t]
            [kotoba.compiler.atomic-output-test]
            [kotoba.compiler.namespace-reachability-test]
            [kotoba.compiler.value-codec-test]
            [kotoba.compiler.test-runner-completeness-test]
            [kotoba.compiler.aiueos-target-test]
            ;; boot: the UEFI firmware boundary's target gate.
            [kotoba.compiler.uefi-target-gate-test]
            [kotoba.compiler.accelerator-test]
            [kotoba.compiler.application-syntax-test]
            [kotoba.compiler.cli-test]
            [kotoba.compiler.core-test]
            [kotoba.compiler.coverage-test]
            [kotoba.compiler.coverage-evidence-test]
            [kotoba.compiler.bounded-edn-test]
            [kotoba.compiler.cache-test]
            [kotoba.compiler.compact-graph-value-test]
            [kotoba.compiler.document-value-test]
            [kotoba.compiler.document-in-record-test]
            [kotoba.compiler.set-in-record-test]
            [kotoba.compiler.typed-set-nth-test]
            [kotoba.compiler.set-of-record-host-test]
            [kotoba.compiler.document-ui-render-test]
            [kotoba.compiler.document-digest-style-test]
            [kotoba.compiler.document-sha256-test]
            [kotoba.compiler.document-dom-reconcile-test]
            [kotoba.compiler.dom-app-driver-test]
            [kotoba.compiler.document-dual-renderer-test]
            [kotoba.compiler.document-roundtrip-test]
            [kotoba.compiler.document-edn-test]
            [kotoba.compiler.document-perf-workload-test]
            [kotoba.compiler.recursive-tree-value-test]
            [kotoba.compiler.recursive-tree-update-test]
            [kotoba.compiler.plan-test]
            [kotoba.compiler.logic-manifest-test]
            [kotoba.compiler.string-operation-test]
            [kotoba.compiler.ci7-elaboration-parity-test]
            [kotoba.compiler.w1-elaboration-test]
            [kotoba.compiler.named-ability-elaboration-test]
            [kotoba.compiler.symbol-operation-test]
            [kotoba.compiler.frontend-fuzz-test]
            [kotoba.compiler.frontend-assert-test]
            [kotoba.compiler.frontend-equality-diagnostic-test]
            [kotoba.compiler.product-value-abi-v1-test]
            [kotoba.compiler.option-flow-sugar-test]
            [kotoba.compiler.pure-product-profile-test]
            [kotoba.compiler.record-projection-sugar-test]
            [kotoba.compiler.map-filter-vector-test]
            [kotoba.compiler.multi-map-test]
            [kotoba.compiler.named-hof-test]
            [kotoba.compiler.reduce-named-test]
            [kotoba.compiler.reduce-vector-test]
            [kotoba.compiler.schema-metadata-test]
            [kotoba.compiler.schema-test]
            [kotoba.compiler.test-profile-test]
            [kotoba.compiler.ambient-negative-corpus-test]
            [kotoba.compiler.lang-conformance-test]
            [kotoba.compiler.lang-conformance-golden-test]
            [kotoba.compiler.lang-native-conformance-test]
            [kotoba.compiler.fuel-estimate-test]
            [kotoba.compiler.capability-names-test]
            [kotoba.compiler.effect-row-test]
            [kotoba.compiler.check-cli-test]
            [kotoba.compiler.capability-deny-test]
            [kotoba.compiler.kir-trap-source-test]
            [kotoba.compiler.kernel-region-provenance-test]
            [kotoba.compiler.native-device-io-test]
            [kotoba.compiler.slice-carrier-test]
            [kotoba.compiler.kernel-subregion-test]
            [kotoba.compiler.error-code-contract-test]
            [kotoba.compiler.frontend-condp-test]
            [kotoba.compiler.frontend-doseq-test]
            ;; a let body is an implicit do; every form reaches the object
            [kotoba.compiler.let-body-sequencing-test]
            [kotoba.compiler.frontend-dotimes-test]
            [kotoba.compiler.f64-value-test]
            [kotoba.compiler.f32-value-test]
            [kotoba.compiler.frontend-limits-test]
            [kotoba.compiler.frontend-multimethod-test]
            [kotoba.compiler.record-protocol-static-dispatch-test]
            [kotoba.compiler.type-directed-access-test]
            [kotoba.compiler.callable-values-test]
            [kotoba.compiler.lazy-sequence-test]
            [kotoba.compiler.frontend-extensions-test]
            [kotoba.compiler.frontend-destructuring-loop-test]
            [kotoba.compiler.frontend-named-capability-test]
            [kotoba.compiler.linear-resource-test]
            [kotoba.compiler.backend-cljs-test]
            [kotoba.compiler.backend-evm-test]
            [kotoba.compiler.backend-cljs-portable-test]
            [kotoba.compiler.portable-surface-test]
            [kotoba.compiler.backend-qualification-test]
            [kotoba.compiler.host-profile-test]
            [kotoba.compiler.component-artifact-test]
            [kotoba.compiler.component-composition-test]
            [kotoba.compiler.component-admission-test]
            [kotoba.compiler.i64-bitwise-test]
            [kotoba.compiler.effectful-component-source-test]
            [kotoba.compiler.ios-aot-test]
            [kotoba.compiler.interface-test]
            [kotoba.compiler.native-executor-test]
            [kotoba.compiler.f32-native-execution-test]
            [kotoba.compiler.admission-test]
            [kotoba.compiler.guest-grammar-conformance-test]
            [kotoba.compiler.property-test]
            [kotoba.compiler.module-lock-test]
            [kotoba.compiler.project-test]
            [kotoba.compiler.receipt-test]
            [kotoba.compiler.ipld-adl-test]
            [kotoba.compiler.ipld-adl-source-test]
            [kotoba.compiler.release-test]
            [kotoba.compiler.security-fuzz-test]
            [kotoba.compiler.signing-test]
            [kotoba.compiler.source-path-test]
            [kotoba.compiler.typed-value-conformance-test]
            [kotoba.compiler.typed-capability-test]
            [kotoba.compiler.reference-runtime-test]
            [kotoba.compiler.state-provider-test]
            [kotoba.compiler.ui-provider-test]
            [kotoba.compiler.http-provider-test]
            [kotoba.compiler.http-transport-test]
            [kotoba.compiler.llm-provider-test]
            [kotoba.compiler.llm-transport-test]
            [kotoba.compiler.object-provider-test]
            [kotoba.compiler.object-product-vertical-test]
            [kotoba.compiler.object-transport-test]
            [kotoba.compiler.http-ingress-provider-test]
            [kotoba.compiler.stream-ingress-provider-test]
            [kotoba.compiler.storage-provider-test]
            [kotoba.compiler.storage-transport-test]
            [kotoba.compiler.storage-wasm-aot-test]
            [kotoba.compiler.net-datagram-provider-test]
            [kotoba.compiler.link-frame-provider-test]
            [kotoba.compiler.can-frame-provider-test]
            [kotoba.compiler.clock-provider-test]
            [kotoba.compiler.clock-transport-test]
            [kotoba.compiler.log-provider-test]
            [kotoba.compiler.log-wasm-aot-test]
            [kotoba.compiler.log-jit-test]
            [kotoba.compiler.http-wasm-aot-test]
            [kotoba.compiler.llm-wasm-aot-test]
            [kotoba.compiler.state-wasm-aot-test]
            [kotoba.compiler.ui-wasm-aot-test]
            [kotoba.compiler.clock-native-kexe-oracle-test]
            [kotoba.compiler.http-ingress-wasm-aot-qualification-test]
            [kotoba.compiler.http-wasm-aot-qualification-test]
            [kotoba.compiler.llm-wasm-aot-qualification-test]
            [kotoba.compiler.log-wasm-aot-qualification-test]
            [kotoba.compiler.native-aot-qualification-test]
            [kotoba.compiler.state-wasm-aot-qualification-test]
            [kotoba.compiler.storage-wasm-aot-qualification-test]
            [kotoba.compiler.ui-wasm-aot-qualification-test]
            [kotoba.compiler.ui-jit-test]
            [kotoba.compiler.dataspace-match-test]
            [kotoba.compiler.dataspace-provider-test]
            [kotoba.compiler.dataspace-wasm-aot-test]
            [kotoba.compiler.dataspace-jit-test]
            [kotoba.compiler.dataspace-native-aot-test]
            [kotoba.compiler.ui-native-aot-test]
            [kotoba.compiler.provider-conformance-test]
            [kotoba.compiler.aggregate-abi-test]
            [kotoba.compiler.string-simd-loader-test]
            [kotoba.compiler.isa-execution-test]
            [kotoba.compiler.native-fuel-metadata-test]
            [kotoba.compiler.wasm-typed-test]
            [kotoba.compiler.wasm32-kotoba-v1-qualification-test]
            [kotoba.compiler.verifier-profile-test]))

;; The namespaces this suite claims to cover, as data, so the runner can say
;; how many it finished rather than only how many failed.
(def ^:private suite
  ['kotoba.compiler.atomic-output-test
   'kotoba.compiler.namespace-reachability-test
   'kotoba.compiler.value-codec-test
   'kotoba.compiler.test-runner-completeness-test
   'kotoba.compiler.aggregate-abi-test
   'kotoba.compiler.string-simd-loader-test
   'kotoba.compiler.isa-execution-test
   'kotoba.compiler.native-fuel-metadata-test
   'kotoba.compiler.aiueos-target-test
   'kotoba.compiler.uefi-target-gate-test
   'kotoba.compiler.accelerator-test
   'kotoba.compiler.application-syntax-test
   'kotoba.compiler.cli-test
   'kotoba.compiler.core-test
   'kotoba.compiler.coverage-test
   'kotoba.compiler.coverage-evidence-test
   'kotoba.compiler.bounded-edn-test
   'kotoba.compiler.cache-test
   'kotoba.compiler.compact-graph-value-test
   'kotoba.compiler.document-value-test
   'kotoba.compiler.document-in-record-test
   'kotoba.compiler.set-in-record-test
   'kotoba.compiler.typed-set-nth-test
   'kotoba.compiler.set-of-record-host-test
   'kotoba.compiler.document-ui-render-test
   'kotoba.compiler.document-digest-style-test
   'kotoba.compiler.document-sha256-test
   'kotoba.compiler.document-dom-reconcile-test
   'kotoba.compiler.document-dual-renderer-test
   'kotoba.compiler.document-roundtrip-test
   'kotoba.compiler.document-edn-test
   'kotoba.compiler.document-perf-workload-test
   'kotoba.compiler.recursive-tree-value-test
   'kotoba.compiler.recursive-tree-update-test
   'kotoba.compiler.plan-test
   'kotoba.compiler.logic-manifest-test
   'kotoba.compiler.string-operation-test
   'kotoba.compiler.ci7-elaboration-parity-test
   'kotoba.compiler.w1-elaboration-test
   'kotoba.compiler.named-ability-elaboration-test
   'kotoba.compiler.symbol-operation-test
   'kotoba.compiler.frontend-fuzz-test
   'kotoba.compiler.frontend-assert-test
   'kotoba.compiler.frontend-equality-diagnostic-test
   'kotoba.compiler.product-value-abi-v1-test
   'kotoba.compiler.option-flow-sugar-test
   'kotoba.compiler.pure-product-profile-test
   'kotoba.compiler.record-projection-sugar-test
   'kotoba.compiler.map-filter-vector-test
   'kotoba.compiler.multi-map-test
   'kotoba.compiler.named-hof-test
   'kotoba.compiler.reduce-named-test
   'kotoba.compiler.reduce-vector-test
   'kotoba.compiler.schema-metadata-test
   'kotoba.compiler.schema-test
   'kotoba.compiler.test-profile-test
   'kotoba.compiler.ambient-negative-corpus-test
   'kotoba.compiler.lang-conformance-test
   'kotoba.compiler.lang-conformance-golden-test
   'kotoba.compiler.lang-native-conformance-test
   'kotoba.compiler.fuel-estimate-test
   'kotoba.compiler.capability-names-test
   'kotoba.compiler.effect-row-test
   'kotoba.compiler.check-cli-test
   'kotoba.compiler.capability-deny-test
   'kotoba.compiler.kernel-region-provenance-test
   'kotoba.compiler.native-device-io-test
   'kotoba.compiler.slice-carrier-test
   'kotoba.compiler.kernel-subregion-test
   'kotoba.compiler.kir-trap-source-test
   'kotoba.compiler.error-code-contract-test
   'kotoba.compiler.frontend-condp-test
   'kotoba.compiler.frontend-doseq-test
   'kotoba.compiler.let-body-sequencing-test
   'kotoba.compiler.frontend-dotimes-test
   'kotoba.compiler.f64-value-test
   'kotoba.compiler.f32-value-test
   'kotoba.compiler.frontend-limits-test
   'kotoba.compiler.frontend-multimethod-test
   'kotoba.compiler.record-protocol-static-dispatch-test
   'kotoba.compiler.type-directed-access-test
   'kotoba.compiler.callable-values-test
   'kotoba.compiler.lazy-sequence-test
   'kotoba.compiler.frontend-extensions-test
   'kotoba.compiler.frontend-destructuring-loop-test
   'kotoba.compiler.frontend-named-capability-test
   'kotoba.compiler.linear-resource-test
   'kotoba.compiler.backend-cljs-test
   'kotoba.compiler.backend-evm-test
   'kotoba.compiler.backend-cljs-portable-test
   'kotoba.compiler.portable-surface-test
   'kotoba.compiler.backend-qualification-test
   'kotoba.compiler.host-profile-test
   'kotoba.compiler.component-artifact-test
   'kotoba.compiler.component-composition-test
   'kotoba.compiler.component-admission-test
   'kotoba.compiler.i64-bitwise-test
   'kotoba.compiler.effectful-component-source-test
   'kotoba.compiler.ios-aot-test
   'kotoba.compiler.interface-test
   'kotoba.compiler.admission-test
   'kotoba.compiler.guest-grammar-conformance-test
   'kotoba.compiler.signing-test
   'kotoba.compiler.source-path-test
   'kotoba.compiler.typed-value-conformance-test
   'kotoba.compiler.typed-capability-test
   'kotoba.compiler.reference-runtime-test
   'kotoba.compiler.state-provider-test
   'kotoba.compiler.ui-provider-test
   'kotoba.compiler.http-provider-test
   'kotoba.compiler.http-transport-test
   'kotoba.compiler.llm-provider-test
   'kotoba.compiler.llm-transport-test
   'kotoba.compiler.object-provider-test
   'kotoba.compiler.object-product-vertical-test
   'kotoba.compiler.object-transport-test
   'kotoba.compiler.http-ingress-provider-test
   'kotoba.compiler.stream-ingress-provider-test
   'kotoba.compiler.storage-provider-test
   'kotoba.compiler.storage-transport-test
   'kotoba.compiler.storage-wasm-aot-test
   'kotoba.compiler.net-datagram-provider-test
   'kotoba.compiler.link-frame-provider-test
   'kotoba.compiler.can-frame-provider-test
   'kotoba.compiler.clock-provider-test
   'kotoba.compiler.clock-transport-test
   'kotoba.compiler.log-provider-test
   'kotoba.compiler.log-wasm-aot-test
   'kotoba.compiler.log-jit-test
   'kotoba.compiler.http-wasm-aot-test
   'kotoba.compiler.llm-wasm-aot-test
   'kotoba.compiler.state-wasm-aot-test
   'kotoba.compiler.ui-wasm-aot-test
   'kotoba.compiler.clock-native-kexe-oracle-test
   'kotoba.compiler.http-ingress-wasm-aot-qualification-test
   'kotoba.compiler.http-wasm-aot-qualification-test
   'kotoba.compiler.llm-wasm-aot-qualification-test
   'kotoba.compiler.log-wasm-aot-qualification-test
   'kotoba.compiler.native-aot-qualification-test
   'kotoba.compiler.state-wasm-aot-qualification-test
   'kotoba.compiler.storage-wasm-aot-qualification-test
   'kotoba.compiler.ui-wasm-aot-qualification-test
   'kotoba.compiler.ui-jit-test
   'kotoba.compiler.dataspace-match-test
   'kotoba.compiler.dataspace-provider-test
   'kotoba.compiler.dataspace-wasm-aot-test
   'kotoba.compiler.dataspace-jit-test
   'kotoba.compiler.dataspace-native-aot-test
   'kotoba.compiler.ui-native-aot-test
   'kotoba.compiler.provider-conformance-test
   'kotoba.compiler.wasm-typed-test
   'kotoba.compiler.wasm32-kotoba-v1-qualification-test
   'kotoba.compiler.native-executor-test
   'kotoba.compiler.f32-native-execution-test
   'kotoba.compiler.receipt-test
   'kotoba.compiler.ipld-adl-test
   'kotoba.compiler.ipld-adl-source-test
   'kotoba.compiler.release-test
   'kotoba.compiler.security-fuzz-test
   'kotoba.compiler.verifier-profile-test
   'kotoba.compiler.module-lock-test
   'kotoba.compiler.project-test
   'kotoba.compiler.property-test])

;; A run that stops early is the failure mode this guards. `kotoba.compiler.cli`
;; exits the JVM through `*exit*` on an error path, and a test that reaches it
;; without binding that var takes the whole suite down: every namespace after it
;; silently never runs and `run-tests` never prints its totals. Measured
;; 2026-08-17, before this: 11 of 128 namespaces ran and the output carried no
;; failures, because nothing was left alive to report one. Absence of failures
;; is not evidence of success unless something says how far the run got.
(defn -main [& _]
  (let [finished (atom 0)]
    (.addShutdownHook
     (Runtime/getRuntime)
     (Thread.
      ^Runnable
      (fn []
        (when (< @finished (count suite))
          (binding [*out* *err*]
            (println (str "test-runner: INCOMPLETE -- finished " @finished
                          " of " (count suite) " namespaces before the JVM"
                          " exited. The counts above cover only those; they are"
                          " not a result for this suite.")))))))
    (println (str "test-runner: running " (count suite) " namespaces"))
    (let [{:keys [fail error] :as summary}
          (reduce (fn [acc namespace]
                    (require namespace)
                    (let [counters (t/test-ns namespace)]
                      (swap! finished inc)
                      (merge-with + acc counters)))
                  {:test 0 :pass 0 :fail 0 :error 0}
                  suite)]
      (println (str "\nRan " (:test summary) " tests containing "
                    (:pass summary) " assertions."))
      (println (str (:fail summary) " failures, " (:error summary) " errors."))
      (println (str "test-runner: COMPLETE -- " @finished " of " (count suite)
                    " namespaces"))
      (System/exit (if (pos? (+ fail error)) 1 0)))))
