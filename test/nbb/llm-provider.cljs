(ns test.nbb.llm-provider
  "W5 family-6 first slice — dual-runtime semantic vectors for `llm-v1` on
  `:cljs` with a mock host transport. Token/temperature fields are JS bigint
  (canonical i64). Production cljs LLM transport remains unimplemented.

  Run: `npm run test-nbb-llm-provider`."
  (:require [kotoba.kir.admission :as admission]
            [kotoba.kir.cljs-i64 :as i64]
            [kotoba.sema :as sema]
            [kotoba.kir :as ir]
            [provider.llm :as llm]
            [kotoba.compiler.reference-runtime :as runtime]))

(def source
  (str "(ns app.llm (:export [generate]) (:capabilities #{:llm/generate}))"
       "(defn generate [request " (pr-str llm/request-type) "] "
       (pr-str llm/result-type) " (typed-cap-call :llm/generate "
       (pr-str llm/request-type) " " (pr-str llm/result-type) " request))"))

(defn- hosted [transport]
  (let [provider (llm/provider {:allowed-models #{:example/text-v1}
                                :transport transport})
        hir (sema/analyze source)
        _ (admission/check hir {:allow #{[:cap/call (js/BigInt 11)]}})
        kir (ir/lower hir)]
    (runtime/instantiate kir {:allow #{11} :providers {11 provider}})))

(defn- check [name ok? detail]
  {:name name :ok? (boolean ok?) :detail (when-not ok? detail)})

(defn- refusal
  "What THUNK refused with: the exception's ex-data plus its :message, or nil
  when it did not refuse.

  Cases assert the structured keys where the provider carries one that
  identifies the guard -- :phase plus the operand it rejected -- and the
  message only where it does not. A message is not the contract: measured
  2026-08-18, three cases in this directory matched wording that belonged to a
  guard behind the one that actually fired, and failed while the property in
  their own name still held."
  [thunk]
  (try (thunk) nil (catch :default e (assoc (or (ex-data e) {}) :message (.-message e)))))

(defn- generation-case []
  (try
    (let [seen (atom nil)
          runtime (hosted (fn [request]
                            (reset! seen request)
                            {:text "Hello" :finish-reason :llm/stop
                             :input-tokens 12 :output-tokens 3}))
          request [llm/request-type :example/text-v1 "Be concise" "Say hello"
                   (js/BigInt 64) (js/BigInt 250)]
          result ((:invoke runtime) 'generate [request])]
      (check "cljs-generation-crosses-only-the-typed-boundary"
             (and (= [llm/result-type :ok
                      [llm/completion-type "Hello" :llm/stop
                       [llm/usage-type (js/BigInt 12) (js/BigInt 3)]]]
                     result)
                  (= :example/text-v1 (:model @seen))
                  (= 64 (:max-output-tokens @seen))
                  (= 250 (:temperature-milli @seen)))
             (pr-str {:result result :seen @seen})))
    (catch :default e
      (check "cljs-generation-crosses-only-the-typed-boundary" false (.-message e)))))

(defn- models-budgets-case []
  (try
    (let [called? (atom false)
          runtime (hosted (fn [_] (reset! called? true) {:text "" :finish-reason :llm/stop
                                                         :input-tokens 0 :output-tokens 0}))
          model-denial
          (refusal #((:invoke runtime) 'generate
                     [[llm/request-type :example/other "" "hello"
                       (js/BigInt 64) i64/zero]]))
          budget-denial
          (refusal #((:invoke runtime) 'generate
                     [[llm/request-type :example/text-v1 "" "hello"
                       (js/BigInt 4097) i64/zero]]))]
      (check "cljs-models-and-budgets-fail-closed"
             ;; The rejected operand, not the wording: :model and
             ;; :max-output-tokens are what separate these two guards.
             (and (= :llm-provider (:phase model-denial))
                  (= :example/other (:model model-denial))
                  (= :llm-provider (:phase budget-denial))
                  (= (js/BigInt 4097) (:max-output-tokens budget-denial))
                  (false? @called?))
             (pr-str {:model model-denial :budget budget-denial
                      :called? @called?})))
    (catch :default e
      (check "cljs-models-and-budgets-fail-closed" false (.-message e)))))

(defn- errors-case []
  (try
    (let [reported (hosted (fn [_] {:error {:code :llm/rate-limited
                                            :message "try later"
                                            :retryable true}}))
          crashed (hosted (fn [_] (throw (js/Error. "secret credential"))))
          request [llm/request-type :example/text-v1 "" "hello" (js/BigInt 64) i64/zero]
          r1 ((:invoke reported) 'generate [request])
          r2 ((:invoke crashed) 'generate [request])]
      (check "cljs-provider-errors-and-exceptions-are-typed"
             (and (= [llm/result-type :error
                      [llm/error-type :llm/rate-limited "try later" true]]
                     r1)
                  (= [llm/result-type :error
                      [llm/error-type :llm/transport "provider failed" false]]
                     r2))
             (pr-str {:r1 r1 :r2 r2})))
    (catch :default e
      (check "cljs-provider-errors-and-exceptions-are-typed" false (.-message e)))))

(defn- denial-case []
  (try
    (let [hir (sema/analyze source)
          _ (admission/check hir {:allow #{[:cap/call (js/BigInt 11)]}})
          kir (ir/lower hir)
          runtime (runtime/instantiate kir)
          denial
          (refusal #((:invoke runtime) 'generate
                     [[llm/request-type :example/text-v1 "" "hello"
                       (js/BigInt 64) i64/zero]]))]
      (check "cljs-missing-grant-denies-before-provider-invoke"
             ;; WHICH capability, not merely that something was denied.
             (and (= :reference-runtime (:phase denial))
                  (= (js/BigInt 11) (:capability denial)))
             (pr-str {:denial denial})))
    (catch :default e
      (check "cljs-missing-grant-denies-before-provider-invoke" false (.-message e)))))

(let [results [(generation-case)
               (models-budgets-case)
               (errors-case)
               (denial-case)]
      failures (remove :ok? results)]
  (doseq [{:keys [name ok? detail]} results]
    (println (if ok? "PASS" "FAIL") name (or detail "")))
  (println (count results) "cases," (count failures) "failed")
  (when (seq failures) (.exit js/process 1)))
