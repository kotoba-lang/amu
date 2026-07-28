(ns kotoba.compiler.object-product-vertical-test
  "W5 fuller product apps (ADR 0140–0142): guest put→get, put→CAS→get, and
  conditional-get product verticals on dual-runtime (affine let / one-arm if)."
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.reference-runtime :as runtime]
            [kotoba.kir :as ir]
            [kotoba.kir.value :as value]
            [provider.object :as object]))

(def product-source
  "ADR 0140: put then measure stream body.
   ADR 0141: put + CAS ref then measure stream body.
   ADR 0142: get only when put (or put+CAS) succeeds (one-arm linear if)."
  (str "(ns app.object-product "
       "(:export [put-then-count put-cas-then-count "
       "put-then-count-if put-cas-then-count-if]) "
       "(:capabilities #{:object/get-stream :object/put-block :object/compare-and-set-ref}))"
       "(defn put-then-count [put-req " (pr-str object/put-block-request-type)
       " get-req " (pr-str object/get-stream-request-type) "] :i64 "
       "(let [ok (typed-cap-call :object/put-block "
       (pr-str object/put-block-request-type) " "
       (pr-str object/put-block-result-type) " put-req) "
       "task (typed-cap-call :object/get-stream "
       (pr-str object/get-stream-request-type) " "
       (pr-str object/get-stream-result-type) " get-req)] "
       "(bytes-task-byte-count task)))"
       "(defn put-cas-then-count [put-req " (pr-str object/put-block-request-type)
       " cas-req " (pr-str object/cas-request-type)
       " get-req " (pr-str object/get-stream-request-type) "] :i64 "
       "(let [ok-put (typed-cap-call :object/put-block "
       (pr-str object/put-block-request-type) " "
       (pr-str object/put-block-result-type) " put-req) "
       "ok-cas (typed-cap-call :object/compare-and-set-ref "
       (pr-str object/cas-request-type) " "
       (pr-str object/cas-result-type) " cas-req) "
       "task (typed-cap-call :object/get-stream "
       (pr-str object/get-stream-request-type) " "
       (pr-str object/get-stream-result-type) " get-req)] "
       "(bytes-task-byte-count task)))"
       "(defn put-then-count-if [put-req " (pr-str object/put-block-request-type)
       " get-req " (pr-str object/get-stream-request-type) "] :i64 "
       "(let [ok (typed-cap-call :object/put-block "
       (pr-str object/put-block-request-type) " "
       (pr-str object/put-block-result-type) " put-req)] "
       "(if ok "
       "(let [task (typed-cap-call :object/get-stream "
       (pr-str object/get-stream-request-type) " "
       (pr-str object/get-stream-result-type) " get-req)] "
       "(bytes-task-byte-count task)) "
       "0)))"
       "(defn put-cas-then-count-if [put-req " (pr-str object/put-block-request-type)
       " cas-req " (pr-str object/cas-request-type)
       " get-req " (pr-str object/get-stream-request-type) "] :i64 "
       "(let [ok-put (typed-cap-call :object/put-block "
       (pr-str object/put-block-request-type) " "
       (pr-str object/put-block-result-type) " put-req) "
       "ok-cas (typed-cap-call :object/compare-and-set-ref "
       (pr-str object/cas-request-type) " "
       (pr-str object/cas-result-type) " cas-req)] "
       "(if ok-cas "
       "(let [task (typed-cap-call :object/get-stream "
       (pr-str object/get-stream-request-type) " "
       (pr-str object/get-stream-result-type) " get-req)] "
       "(bytes-task-byte-count task)) "
       "0)))"))

(defn- memory-store-transport
  "In-memory put/get/CAS transport.
  Blocks keyed by [binding digest-or-key]; refs by [binding key] → etag string."
  []
  (let [store (atom {})
        refs (atom {})]
    (fn [req]
      (case (:operation req)
        :put-block
        (do (swap! store assoc [(:binding req) (:digest req)] (:bytes req))
            true)
        :get-stream
        (if-let [bytes (get @store [(:binding req) (:key req)])]
          {:bytes bytes}
          (throw (ex-info "object missing" {:phase :object-product-transport
                                            :key (:key req)})))
        :compare-and-set-ref
        (let [rk [(:binding req) (:key req)]
              cur (get @refs rk)
              expected (:expected req)
              next-etag (:next req)]
          (if (or (nil? expected) (= cur expected))
            (do (swap! refs assoc rk next-etag) true)
            false))
        (throw (ex-info "unsupported object operation"
                        {:phase :object-product-transport
                         :operation (:operation req)}))))))

(defn- hosted-product
  ([transport] (hosted-product transport #{:example/blocks :example/refs}))
  ([transport allowed-bindings]
   (let [kit (object/create-providers
              {:allowed-bindings allowed-bindings
               :transport transport})
         checked (compiler/check-source
                  product-source {:allow #{[:cap/call 14] [:cap/call 15] [:cap/call 16]}})
         kir (ir/lower (:hir checked))]
     {:runtime (runtime/instantiate kir {:allow #{14 15 16}
                                         :providers (:providers kit)})
      :hir (:hir checked)})))

(deftest product-put-then-count-is-typed
  (let [{:keys [hir]} (hosted-product (memory-store-transport))
        by-name (into {} (map (juxt :name identity) (:functions hir)))
        f (by-name 'put-then-count)]
    (is (= :i64 (:result f)))
    (is (= #{[:cap/call 14] [:cap/call 15]} (:effects f)))
    (is (= 'let (first (:body f))))))

(deftest product-put-cas-then-count-is-typed
  "ADR 0141: put + CAS + get-stream in one guest export."
  (let [{:keys [hir]} (hosted-product (memory-store-transport))
        f (first (filter #(= 'put-cas-then-count (:name %)) (:functions hir)))]
    (is (= :i64 (:result f)))
    (is (= #{[:cap/call 14] [:cap/call 15] [:cap/call 16]} (:effects f)))
    (is (= 'let (first (:body f))))))

(deftest product-put-then-count-round-trips-bytes
  "put-block then get-stream in one guest export; body length matches payload."
  (let [payload (value/utf8-string->bytes "hello-product")
        {:keys [runtime]} (hosted-product (memory-store-transport))
        put-req [object/put-block-request-type :example/blocks "k1" payload]
        get-req [object/get-stream-request-type :example/blocks "k1"]
        n ((:invoke runtime) 'put-then-count [put-req get-req])]
    (is (= (value/bytes-byte-count payload) n))
    (is (= 13 n))))

(deftest product-put-then-count-missing-get-fails-closed
  (let [{:keys [runtime]} (hosted-product (memory-store-transport))
        put-req [object/put-block-request-type
                 :example/blocks "only-put" (value/utf8-string->bytes "x")]
        get-req [object/get-stream-request-type :example/blocks "missing-key"]]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"object provider failed|missing"
         ((:invoke runtime) 'put-then-count [put-req get-req])))))

(deftest product-put-then-count-ordering-records-put-before-get
  (let [ops (atom [])
        transport (fn [req]
                    (swap! ops conj (:operation req))
                    (case (:operation req)
                      :put-block true
                      :get-stream {:bytes (value/utf8-string->bytes "ab")}
                      (throw (ex-info "bad" req))))
        {:keys [runtime]} (hosted-product transport)
        put-req [object/put-block-request-type
                 :example/blocks "k" (value/utf8-string->bytes "ab")]
        get-req [object/get-stream-request-type :example/blocks "k"]
        n ((:invoke runtime) 'put-then-count [put-req get-req])]
    (is (= [:put-block :get-stream] @ops))
    (is (= 2 n))))

(deftest product-put-cas-then-count-round-trips-on-cas-win
  "ADR 0141: put → CAS win → get; body length matches payload."
  (let [payload (value/utf8-string->bytes "cas-product")
        {:keys [runtime]} (hosted-product (memory-store-transport))
        put-req [object/put-block-request-type :example/blocks "blob-1" payload]
        cas-req [object/cas-request-type
                 :example/refs "main"
                 [object/expected-etag-type false]
                 "etag-1"]
        get-req [object/get-stream-request-type :example/blocks "blob-1"]
        n ((:invoke runtime) 'put-cas-then-count [put-req cas-req get-req])]
    (is (= (value/bytes-byte-count payload) n))
    (is (= 11 n))))

(deftest product-put-cas-then-count-ordering
  (let [ops (atom [])
        transport (fn [req]
                    (swap! ops conj (:operation req))
                    (case (:operation req)
                      :put-block true
                      :compare-and-set-ref true
                      :get-stream {:bytes (value/utf8-string->bytes "xy")}
                      (throw (ex-info "bad" req))))
        {:keys [runtime]} (hosted-product transport)
        put-req [object/put-block-request-type
                 :example/blocks "k" (value/utf8-string->bytes "xy")]
        cas-req [object/cas-request-type
                 :example/refs "main"
                 [object/expected-etag-type false]
                 "e1"]
        get-req [object/get-stream-request-type :example/blocks "k"]
        n ((:invoke runtime) 'put-cas-then-count [put-req cas-req get-req])]
    (is (= [:put-block :compare-and-set-ref :get-stream] @ops))
    (is (= 2 n))))

(deftest product-put-cas-then-count-still-reads-after-cas-lose
  "CAS lose returns false but unconditional path still measures get."
  (let [payload (value/utf8-string->bytes "still")
        transport (memory-store-transport)
        ;; seed ref so first CAS with expected etag-x loses
        _ (transport {:operation :compare-and-set-ref
                      :binding :example/refs
                      :key "main"
                      :expected nil
                      :next "etag-seed"})
        {:keys [runtime]} (hosted-product transport)
        put-req [object/put-block-request-type :example/blocks "b" payload]
        cas-req [object/cas-request-type
                 :example/refs "main"
                 [object/expected-etag-type true "wrong"]
                 "etag-new"]
        get-req [object/get-stream-request-type :example/blocks "b"]
        n ((:invoke runtime) 'put-cas-then-count [put-req cas-req get-req])]
    (is (= 5 n))))

(deftest product-put-then-count-if-skips-get-on-put-fail
  "ADR 0142: when put returns false, get is not invoked and result is 0."
  (let [ops (atom [])
        transport (fn [req]
                    (swap! ops conj (:operation req))
                    (case (:operation req)
                      :put-block false
                      :get-stream (throw (ex-info "should-not-get" {}))
                      (throw (ex-info "bad" req))))
        {:keys [runtime]} (hosted-product transport)
        put-req [object/put-block-request-type
                 :example/blocks "k" (value/utf8-string->bytes "x")]
        get-req [object/get-stream-request-type :example/blocks "k"]
        n ((:invoke runtime) 'put-then-count-if [put-req get-req])]
    (is (= [:put-block] @ops))
    (is (zero? n))))

(deftest product-put-then-count-if-gets-on-put-success
  (let [ops (atom [])
        transport (fn [req]
                    (swap! ops conj (:operation req))
                    (case (:operation req)
                      :put-block true
                      :get-stream {:bytes (value/utf8-string->bytes "ok!")}
                      (throw (ex-info "bad" req))))
        {:keys [runtime]} (hosted-product transport)
        put-req [object/put-block-request-type
                 :example/blocks "k" (value/utf8-string->bytes "ok!")]
        get-req [object/get-stream-request-type :example/blocks "k"]
        n ((:invoke runtime) 'put-then-count-if [put-req get-req])]
    (is (= [:put-block :get-stream] @ops))
    (is (= 3 n))))

(deftest product-put-cas-then-count-if-skips-get-on-cas-lose
  "ADR 0142: CAS lose → 0 without get-stream."
  (let [ops (atom [])
        transport (fn [req]
                    (swap! ops conj (:operation req))
                    (case (:operation req)
                      :put-block true
                      :compare-and-set-ref false
                      :get-stream (throw (ex-info "should-not-get" {}))
                      (throw (ex-info "bad" req))))
        {:keys [runtime]} (hosted-product transport)
        put-req [object/put-block-request-type
                 :example/blocks "k" (value/utf8-string->bytes "x")]
        cas-req [object/cas-request-type
                 :example/refs "main"
                 [object/expected-etag-type true "nope"]
                 "e2"]
        get-req [object/get-stream-request-type :example/blocks "k"]
        n ((:invoke runtime) 'put-cas-then-count-if [put-req cas-req get-req])]
    (is (= [:put-block :compare-and-set-ref] @ops))
    (is (zero? n))))

(deftest product-put-cas-then-count-if-gets-on-cas-win
  (let [payload (value/utf8-string->bytes "win!")
        {:keys [runtime]} (hosted-product (memory-store-transport))
        put-req [object/put-block-request-type :example/blocks "blob" payload]
        cas-req [object/cas-request-type
                 :example/refs "main"
                 [object/expected-etag-type false]
                 "etag-1"]
        get-req [object/get-stream-request-type :example/blocks "blob"]
        n ((:invoke runtime) 'put-cas-then-count-if [put-req cas-req get-req])]
    (is (= 4 n))))
