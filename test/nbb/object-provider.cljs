(ns test.nbb.object-provider
  "W5 stream-object dual-runtime — put-block + CAS + get-stream (ready /
  pending→fulfill / multi-chunk) on `:cljs` with a mock host transport.

  Kit `:bytes` is a host Uint8Array (runtime leaf via kotoba.kir.value).
  Linear Component v0.3 handles remain out of this slice.
  Run: `npm run test-nbb-object-provider`."
  (:require [kotoba.kir.admission :as admission]
            [kotoba.compiler.frontend :as frontend]
            [kotoba.kir :as ir]
            [provider.object :as object]
            [kotoba.kir.value :as value]
            [kotoba.compiler.reference-runtime :as runtime]))

(def source
  (str "(ns app.object (:export [get-stream put-block compare-and-set-ref]) "
       "(:capabilities #{:object/get-stream :object/put-block :object/compare-and-set-ref}))"
       "(defn get-stream [request " (pr-str object/get-stream-request-type) "] "
       (pr-str object/get-stream-result-type)
       " (typed-cap-call :object/get-stream "
       (pr-str object/get-stream-request-type) " "
       (pr-str object/get-stream-result-type) " request))"
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
          _ (admission/check hir {:allow #{[:cap/call (js/BigInt 14)]
                                           [:cap/call (js/BigInt 15)]
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

(defn- get-stream-ready-case []
  (try
    (let [payload (value/utf8-string->bytes "stream-body")
          seen (atom nil)
          runtime (hosted (fn [request]
                            (reset! seen request)
                            {:bytes payload}))
          request [object/get-stream-request-type :example/blocks "key-1"]
          task ((:invoke runtime) 'get-stream [request])
          polled (value/task-poll task)
          chunk (value/stream-read! (:stream polled) 65536)]
      (check "cljs-get-stream-returns-ready-task-and-reads-bytes"
             (and (= {:operation :get-stream :binding :example/blocks :key "key-1"} @seen)
                  (value/task-value? task)
                  (= :ready (:state polled))
                  (true? (:done? chunk))
                  (zero? (value/compare-typed-values :bytes payload (:bytes chunk))))
             (pr-str {:seen @seen :state (:state polled) :done? (:done? chunk)})))
    (catch :default e
      (check "cljs-get-stream-returns-ready-task-and-reads-bytes" false (.-message e)))))

(defn- get-stream-pending-fulfill-case []
  (try
    (let [payload (value/utf8-string->bytes "late-body")
          runtime (hosted (fn [_] {:pending true}))
          request [object/get-stream-request-type :example/blocks "key-pending"]
          pending ((:invoke runtime) 'get-stream [request])
          polled0 (value/task-poll pending)
          ready (value/task-fulfill! pending payload)
          polled1 (value/task-poll ready)
          chunk (value/stream-read! (:stream polled1) 65536)]
      (check "cljs-get-stream-pending-then-fulfill-then-read"
             (and (value/task-value? pending)
                  (= :pending (:state polled0))
                  (nil? (:stream polled0))
                  (= :ready (:state polled1))
                  (= (:kotoba.task/id pending) (:kotoba.task/id ready))
                  (true? (:done? chunk))
                  (zero? (value/compare-typed-values :bytes payload (:bytes chunk))))
             (pr-str {:state0 (:state polled0) :state1 (:state polled1)})))
    (catch :default e
      (check "cljs-get-stream-pending-then-fulfill-then-read" false (.-message e)))))

(defn- get-stream-multi-chunk-case []
  (try
    (let [a (value/utf8-string->bytes "hel")
          b (value/utf8-string->bytes "lo")
          joined (value/utf8-string->bytes "hello")
          runtime (hosted (fn [_] {:chunks [a b]}))
          request [object/get-stream-request-type :example/blocks "key-chunks"]
          task ((:invoke runtime) 'get-stream [request])
          polled (value/task-poll task)
          chunk (value/stream-read! (:stream polled) 65536)]
      (check "cljs-get-stream-multi-chunk-ready-task"
             (and (= :ready (:state polled))
                  (true? (:done? chunk))
                  (zero? (value/compare-typed-values :bytes joined (:bytes chunk))))
             (pr-str {:state (:state polled) :done? (:done? chunk)})))
    (catch :default e
      (check "cljs-get-stream-multi-chunk-ready-task" false (.-message e)))))

(defn- get-stream-chunk-queue-case []
  (try
    (let [a (value/utf8-string->bytes "hel")
          b (value/utf8-string->bytes "lo")
          runtime (hosted (fn [_] {:chunk-queue [a b]}))
          request [object/get-stream-request-type :example/blocks "key-queue"]
          task ((:invoke runtime) 'get-stream [request])
          polled (value/task-poll task)
          c1 (value/stream-read! (:stream polled) 65536)
          c2 (value/stream-read! (:stream polled) 65536)]
      (check "cljs-get-stream-chunk-queue-yields-discrete-chunks"
             (and (= :ready (:state polled))
                  (false? (:done? c1))
                  (zero? (value/compare-typed-values :bytes a (:bytes c1)))
                  (true? (:done? c2))
                  (zero? (value/compare-typed-values :bytes b (:bytes c2))))
             (pr-str {:state (:state polled) :done1 (:done? c1) :done2 (:done? c2)})))
    (catch :default e
      (check "cljs-get-stream-chunk-queue-yields-discrete-chunks" false (.-message e)))))

(defn- get-stream-open-stream-case []
  (try
    (let [runtime (hosted (fn [_] {:open-stream true}))
          request [object/get-stream-request-type :example/blocks "key-open"]
          task ((:invoke runtime) 'get-stream [request])
          stream (:stream (value/task-poll task))
          p0 (value/stream-read! stream 65536)
          a (value/utf8-string->bytes "prog")
          _ (value/stream-enqueue! stream a)
          c1 (value/stream-read! stream 65536)
          _ (value/stream-close! stream)
          done (value/stream-read! stream 65536)]
      (check "cljs-get-stream-open-stream-progressive-push"
             (and (true? (:pending? p0))
                  (false? (:done? p0))
                  (zero? (value/compare-typed-values :bytes a (:bytes c1)))
                  (false? (:done? c1))
                  (true? (:done? done)))
             (pr-str {:pending? (:pending? p0) :done-c1 (:done? c1) :done? (:done? done)})))
    (catch :default e
      (check "cljs-get-stream-open-stream-progressive-push" false (.-message e)))))

(def guest-poll-read-source
  (str "(ns app.object-guest (:export [get-stream-ready get-stream-byte-count]) "
       "(:capabilities #{:object/get-stream}))"
       "(defn get-stream-ready [request " (pr-str object/get-stream-request-type) "] :i64 "
       "(task-ready? (typed-cap-call :object/get-stream "
       (pr-str object/get-stream-request-type) " "
       (pr-str object/get-stream-result-type) " request)))"
       "(defn get-stream-byte-count [request " (pr-str object/get-stream-request-type) "] :i64 "
       "(bytes-task-byte-count (typed-cap-call :object/get-stream "
       (pr-str object/get-stream-request-type) " "
       (pr-str object/get-stream-result-type) " request)))"))

(defn- hosted-guest [transport]
  (let [provider (object/get-stream-provider
                  {:allowed-bindings #{:example/blocks}
                   :transport transport})
        hir (frontend/analyze guest-poll-read-source)
        _ (admission/check hir {:allow #{[:cap/call (js/BigInt 14)]}})
        kir (ir/lower hir)]
    (runtime/instantiate kir {:allow #{14} :providers {14 provider}})))

(defn- guest-task-ready-case []
  (try
    (let [payload (value/utf8-string->bytes "abc")
          runtime (hosted-guest (fn [_] {:bytes payload}))
          request [object/get-stream-request-type :example/blocks "k"]
          n ((:invoke runtime) 'get-stream-ready [request])]
      (check "cljs-guest-task-ready?-reports-ready-task"
             (= (js/BigInt 1) n)
             (pr-str {:n n})))
    (catch :default e
      (check "cljs-guest-task-ready?-reports-ready-task" false (.-message e)))))

(defn- guest-byte-count-case []
  (try
    (let [payload (value/utf8-string->bytes "hello")
          runtime (hosted-guest (fn [_] {:bytes payload}))
          request [object/get-stream-request-type :example/blocks "k"]
          n ((:invoke runtime) 'get-stream-byte-count [request])]
      (check "cljs-guest-bytes-task-byte-count-without-host-poll"
             (= (js/BigInt 5) n)
             (pr-str {:n n})))
    (catch :default e
      (check "cljs-guest-bytes-task-byte-count-without-host-poll" false (.-message e)))))


(def product-source
  (str "(ns app.object-product (:export [put-then-count]) "
       "(:capabilities #{:object/get-stream :object/put-block}))"
       "(defn put-then-count [put-req " (pr-str object/put-block-request-type)
       " get-req " (pr-str object/get-stream-request-type) "] :i64 "
       "(let [ok (typed-cap-call :object/put-block "
       (pr-str object/put-block-request-type) " "
       (pr-str object/put-block-result-type) " put-req) "
       "task (typed-cap-call :object/get-stream "
       (pr-str object/get-stream-request-type) " "
       (pr-str object/get-stream-result-type) " get-req)] "
       "(bytes-task-byte-count task)))"))

(defn- hosted-product [transport]
  (let [kit (object/create-providers
             {:allowed-bindings #{:example/blocks}
              :transport transport})
        hir (frontend/analyze product-source)
        _ (admission/check hir {:allow #{[:cap/call (js/BigInt 14)]
                                         [:cap/call (js/BigInt 15)]}})
        kir (ir/lower hir)]
    (runtime/instantiate kir {:allow #{14 15 16}
                              :providers (select-keys (:providers kit) [14 15])})))

(defn- product-put-then-count-case []
  (try
    (let [store (atom {})
          transport (fn [req]
                      (case (:operation req)
                        :put-block
                        (do (swap! store assoc [(:binding req) (:digest req)] (:bytes req))
                            true)
                        :get-stream
                        (if-let [bytes (get @store [(:binding req) (:key req)])]
                          {:bytes bytes}
                          (throw (ex-info "missing" {})))
                        (throw (ex-info "bad" req))))
          runtime (hosted-product transport)
          payload (value/utf8-string->bytes "hello-product")
          put-req [object/put-block-request-type :example/blocks "k1" payload]
          get-req [object/get-stream-request-type :example/blocks "k1"]
          n ((:invoke runtime) 'put-then-count [put-req get-req])]
      (check "cljs-product-put-then-count-round-trip"
             (= (js/BigInt 13) n)
             (pr-str {:n n})))
    (catch :default e
      (check "cljs-product-put-then-count-round-trip" false (.-message e)))))

(let [results [(put-boundary-case)
               (cas-case)
               (binding-case)
               (redaction-case)
               (denial-case)
               (get-stream-ready-case)
               (get-stream-pending-fulfill-case)
               (get-stream-multi-chunk-case)
               (get-stream-chunk-queue-case)
               (get-stream-open-stream-case)
               (guest-task-ready-case)
               (guest-byte-count-case)
               (product-put-then-count-case)]
      failures (remove :ok? results)]
  (doseq [{:keys [name ok? detail]} results]
    (println (if ok? "PASS" "FAIL") name (or detail "")))
  (println (count results) "cases," (count failures) "failed")
  (when (seq failures) (.exit js/process 1)))
