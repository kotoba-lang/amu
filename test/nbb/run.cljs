(ns test.nbb.run
  "Repeatable, JVM-free regression test for the nbb-native wasm32
  compile/check path (`kotoba.compiler.nbb.cli`, spawned by `bin/kotoba` for
  `wasm32*` targets -- see its own comment). Every case must emit valid Wasm.
  Semantic, ABI, and rejection behavior is covered by the conformance suites;
  emitted bytes are deliberately not treated as the language contract.
  Run from the repo root: `nbb test/nbb/run.cljs`."
  (:require ["node:fs" :as fs]
            [kotoba.compiler.frontend :as frontend]
            [kotoba.kir.admission :as admission]
            [kotoba.kir :as ir]
            [kotoba.wasm.core :as wasm]
            [kotoba.compiler.diagnostic :as diagnostic]
            [kotoba.compiler.kotoba-reader :as kr]
            [test.nbb.cases :as cases]))

(defn- compile-case [{:keys [source target policy]}]
  (let [src (.readFileSync fs source "utf8")
        hir (frontend/analyze src)
        policy-value (if policy (first (kr/read-forms (.readFileSync fs policy "utf8"))) {})
        _ (admission/check hir policy-value)
        kir (ir/lower hir)]
    (wasm/emit kir (get cases/target-keyword target))))

(defn- diagnostic-case []
  (try
    (frontend/analyze "(defn main []\n  (forbidden-call 1))")
    {:name "structured-diagnostic" :ok? false :detail "unsafe source was admitted"}
    (catch :default error
      (let [value (diagnostic/from-error error "program.cljk")
            span (:span value)
            ;; T3.1 (compiler#422 / ADR 0172): reject! sites carry stable
            ;; :kotoba.error/* codes, default :subset-reject. The JVM twin
            ;; (cli_test/structured-diagnostic-has-stable-code-and-bounded-source-span)
            ;; was updated then; this one was not, and main has been red since.
            ok? (and (= :kotoba.error/subset-reject (:code value))
                     (= "program.cljk" (:source value))
                     (= 2 (:line span)) (= 3 (:column span)))]
        {:name "structured-diagnostic" :ok? ok?
         :detail (when-not ok? (pr-str value))}))))

(defn- named-operation-case []
  (try
    (let [hir (frontend/analyze
               "(ns demo (:capabilities #{:http/post}))
                (defn main [] :i64 (http/post 41))")
          body (get-in hir [:functions 0 :body])
          effect-id (second (first (:effects hir)))
          ok? (and (= 'typed-cap-call (first body))
                   (= 4 (second body))
                   (= :i64 (nth body 2))
                   (= :i64 (nth body 3))
                   (= 4 (js/Number effect-id)))]
      {:name "named-operation-elaboration" :ok? ok?
       :detail (when-not ok? (pr-str {:body body :effects (:effects hir)}))})
    (catch :default error
      {:name "named-operation-elaboration" :ok? false
       :detail (str "threw: " (.-message error))})))

(let [results
      (conj
       (vec
        (for [{:keys [name] :as case} cases/cases]
          (try
            (let [actual (compile-case case)
                  ok? (js/WebAssembly.validate actual)]
              {:name name :ok? ok?
               :detail (when-not ok? "emitted invalid Wasm")})
            (catch :default e
              {:name name :ok? false :detail (str "threw: " (.-message e))}))))
       (diagnostic-case)
       (named-operation-case))
      failures (remove :ok? results)]
  (doseq [{:keys [name ok? detail]} results]
    (println (if ok? "PASS" "FAIL") name (or detail "")))
  (println (count results) "cases," (count failures) "failed")
  (when (seq failures) (.exit js/process 1)))
