(ns kotoba.compiler.object-product-vertical-test
  "W5 fuller product app (ADR 0140): guest single-export put→get-stream
  product vertical on dual-runtime, using affine let-move (ADR 0137–0139)."
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.reference-runtime :as runtime]
            [kotoba.kir :as ir]
            [kotoba.kir.value :as value]
            [provider.object :as object]))

(def product-source
  "Single guest export that puts a block then measures the stream body.
  Closes ADR 0132's deferred guest put+get mixed body via affine let."
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

(defn- memory-store-transport
  "In-memory put/get transport keyed by [binding digest-or-key]."
  []
  (let [store (atom {})]
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
        (throw (ex-info "unsupported object operation"
                        {:phase :object-product-transport
                         :operation (:operation req)}))))))

(defn- hosted-product [transport]
  (let [kit (object/create-providers
             {:allowed-bindings #{:example/blocks}
              :transport transport})
        checked (compiler/check-source
                 product-source {:allow #{[:cap/call 14] [:cap/call 15]}})
        kir (ir/lower (:hir checked))]
    {:runtime (runtime/instantiate kir {:allow #{14 15 16}
                                        :providers (select-keys (:providers kit)
                                                                [14 15])})
     :hir (:hir checked)}))

(deftest product-put-then-count-is-typed
  (let [{:keys [hir]} (hosted-product (memory-store-transport))
        f (first (:functions hir))]
    (is (= 'put-then-count (:name f)))
    (is (= :i64 (:result f)))
    (is (= #{[:cap/call 14] [:cap/call 15]} (:effects f)))
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
