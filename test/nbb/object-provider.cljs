(ns test.nbb.object-provider
  "W5 stream-object dual-runtime first slice — put-block + CAS on `:cljs`
  with a mock host transport. Kit `:bytes` is a host Uint8Array (runtime leaf via kotoba.kir.value).

  Linear get-stream handles are out of this slice (Component v0.3 path).
  Run: `npm run test-nbb-object-provider`."
  (:require [kotoba.kir.admission :as admission]
            [kotoba.compiler.frontend :as frontend]
            [kotoba.kir :as ir]
            [provider.object :as object]
            [kotoba.kir.value :as value]
            [kotoba.compiler.reference-runtime :as runtime]))

(def source
  (str "(ns app.object (:export [put-block compare-and-set-ref]) "
       "(:capabilities #{:object/put-block :object/compare-and-set-ref}))"
       "(defn put-block [request " (pr-str object/put-block-request-type) "] "
       (pr-str object/put-block-result-type)
       " (typed-cap-call :object/put-block "
       (pr-str object/put-block-request-type) " "
       (pr-str object/put-block-result-type) " request))"
       "(defn compare-and-set-ref [request " (pr-str object/cas-request-type) "] "
       (pr-str object/cas-result-type)
       " (typed-cap-call :object/compare-and-set-ref "
       (pr-str object/cas-request-type) " "
       (pr-str object/cas-result-type) " request))"))

(defn- hosted [transport]
  (let [kit (object/create-providers
             {:allowed-bindings #{:example/blocks :example/refs}
              :transport transport})
        hir (frontend/analyze source)
        _ (admission/check hir {:allow #{[:cap/call (js/BigInt 14)]
                                         [:cap/call (js/BigInt 15)]
                                         [:cap/call (js/BigInt 16)]}})
        kir (ir/lower hir)]
    (runtime/instantiate kir {:allow #{14 15 16} :providers (:providers kit)})))

(defn- check [name ok? detail]
  {:name name :ok? (boolean ok?) :detail (when-not ok? detail)})

(defn- put-boundary-case []
  (try
    (let [seen (atom nil)
          runtime (hosted (fn [request]
                            (reset! seen request)
                            true))
          payload (value/utf8-string->bytes "payload-bytes")
          request [object/put-block-request-type
                   :example/blocks "sha256:deadbeef" payload]
          result ((:invoke runtime) 'put-block [request])]
      (check "cljs-put-block-crosses-only-the-typed-boundary"
             (and (true? result)
                  (= :example/blocks (:binding @seen))
                  (= "sha256:deadbeef" (:digest @seen))
                  (value/bytes-value? (:bytes @seen))
                  (zero? (value/compare-typed-values :bytes payload (:bytes @seen))))
             (pr-str {:result result :seen @seen})))
    (catch :default e
      (check "cljs-put-block-crosses-only-the-typed-boundary" false (.-message e)))))

(defn- cas-case []
  (try
    (let [won (hosted (fn [_] true))
          lost (hosted (fn [_] false))
          expected [object/expected-etag-type true "etag-1"]
          request [object/cas-request-type
                   :example/refs "main" expected "etag-2"]
          r1 ((:invoke won) 'compare-and-set-ref [request])
          r2 ((:invoke lost) 'compare-and-set-ref [request])]
      (check "cljs-cas-wins-and-loses-are-typed-bools"
             (and (true? r1) (false? r2))
             (pr-str {:r1 r1 :r2 r2})))
    (catch :default e
      (check "cljs-cas-wins-and-loses-are-typed-bools" false (.-message e)))))

(defn- binding-case []
  (try
    (let [called? (atom false)
          runtime (hosted (fn [_] (reset! called? true) true))
          binding-threw?
          (try
            ((:invoke runtime) 'put-block
             [[object/put-block-request-type :example/other "sha256:x" (value/utf8-string->bytes "p")]])
            false
            (catch :default e
              (boolean (re-find #"binding is not allowed" (.-message e)))))
          empty-threw?
          (try
            ((:invoke runtime) 'put-block
             [[object/put-block-request-type :example/blocks "" (value/utf8-string->bytes "p")]])
            false
            (catch :default e
              (boolean (re-find #"digest must be non-empty" (.-message e)))))]
      (check "cljs-bindings-and-empty-fields-fail-closed"
             (and binding-threw? empty-threw? (false? @called?))
             (pr-str {:binding-threw? binding-threw? :empty-threw? empty-threw?
                      :called? @called?})))
    (catch :default e
      (check "cljs-bindings-and-empty-fields-fail-closed" false (.-message e)))))

(defn- redaction-case []
  (try
    (let [runtime (hosted (fn [_] (throw (js/Error. "secret object URL"))))
          threw?
          (try
            ((:invoke runtime) 'put-block
             [[object/put-block-request-type :example/blocks "sha256:x" (value/utf8-string->bytes "p")]])
            false
            (catch :default e
              (boolean (re-find #"object provider failed" (.-message e)))))]
      (check "cljs-transport-exceptions-are-redacted"
             threw?
             (pr-str {:threw? threw?})))
    (catch :default e
      (check "cljs-transport-exceptions-are-redacted" false (.-message e)))))

(defn- denial-case []
  (try
    (let [hir (frontend/analyze source)
          _ (admission/check hir {:allow #{[:cap/call (js/BigInt 15)]
                                           [:cap/call (js/BigInt 16)]}})
          kir (ir/lower hir)
          runtime (runtime/instantiate kir)
          denied?
          (try
            ((:invoke runtime) 'put-block
             [[object/put-block-request-type :example/blocks "sha256:x" (value/utf8-string->bytes "p")]])
            false
            (catch :default e
              (boolean (re-find #"capability denied" (.-message e)))))]
      (check "cljs-missing-grant-denies-before-provider-invoke"
             denied?
             (pr-str {:denied? denied?})))
    (catch :default e
      (check "cljs-missing-grant-denies-before-provider-invoke" false (.-message e)))))

(let [results [(put-boundary-case)
               (cas-case)
               (binding-case)
               (redaction-case)
               (denial-case)]
      failures (remove :ok? results)]
  (doseq [{:keys [name ok? detail]} results]
    (println (if ok? "PASS" "FAIL") name (or detail "")))
  (println (count results) "cases," (count failures) "failed")
  (when (seq failures) (.exit js/process 1)))
