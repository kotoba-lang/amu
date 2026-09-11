(ns kotoba.compiler.object-transport-test
  "Production object-store transport (ADR 0129) — host-configured endpoint,
  fixed-path JSON, get-stream / put-block / CAS through typed providers."
  (:require [json.data-json :as json]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [provider.object :as object]
            [provider.object-transport :as transport]
            [kotoba.compiler.reference-runtime :as runtime]
            [kotoba.kir.value :as value])
  (:import (com.sun.net.httpserver HttpServer HttpHandler)
           (java.net InetSocketAddress)
           (java.util Base64)
           (java.util.concurrent ConcurrentHashMap)))

(defn- respond-json! [ex status m]
  (let [body (.getBytes (json/write-str m) "UTF-8")]
    (.. ex getResponseHeaders (add "Content-Type" "application/json"))
    (.sendResponseHeaders ex status (alength body))
    (doto (.getResponseBody ex)
      (.write body)
      (.close))))

(defn- fake-object-server
  "In-memory object store speaking object-transport's wire protocol."
  []
  (let [blocks (ConcurrentHashMap.)
        refs (ConcurrentHashMap.)
        server (HttpServer/create (InetSocketAddress. "127.0.0.1" 0) 0)]
    (.createContext
     server "/object/v1/transact"
     (reify HttpHandler
       (handle [_ ex]
         (let [raw (slurp (.getRequestBody ex))
               req (json/read-str raw {:key-fn keyword})
               op (keyword (:operation req))
               binding (:binding req)]
           (try
             (case op
               :get-stream
               (let [k (str binding "/" (:key req))
                     b64 (.get blocks k)]
                 (if b64
                   (respond-json! ex 200 {:tag "found" :bytes_base64 b64})
                   (respond-json! ex 200 {:tag "missing"})))

               :put-block
               (let [k (str binding "/" (:digest req))]
                 (.put blocks k (:bytes_base64 req))
                 (respond-json! ex 200 {:tag "ok" :won true}))

               :compare-and-set-ref
               (let [k (str binding "/" (:key req))
                     expected (:expected req)
                     next (:next req)
                     cur (.get refs k)
                     won? (or (nil? expected) (= expected cur))]
                 (when won? (.put refs k next))
                 (respond-json! ex 200 {:tag "ok" :won won?}))

               (respond-json! ex 400 {:tag "error"
                                      :error {:code "object/bad-op"
                                              :message "unknown"
                                              :retryable false}}))
             (catch Exception e
               (respond-json! ex 500 {:tag "error"
                                      :error {:code "object/server"
                                              :message (.getMessage e)
                                              :retryable true}})))))))
    (.setExecutor server nil)
    (.start server)
    {:server server
     :port (.getPort (.getAddress server))
     :endpoint (str "http://127.0.0.1:" (.getPort (.getAddress server)))
     :blocks blocks
     :refs refs}))

(defn- stop! [{:keys [server]}] (.stop server 0))

(def get-stream-source
  (str "(ns app.obj (:export [get-stream put-block compare-and-set-ref]) "
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

(defn- hosted [endpoint]
  (let [t (transport/production-transport {:endpoint endpoint})
        kit (object/create-providers
             {:allowed-bindings #{:example/blocks :example/refs}
              :transport t})
        kir (ir/lower (:hir (compiler/check-source
                             get-stream-source
                             {:allow #{[:cap/call 14] [:cap/call 15] [:cap/call 16]}})))]
    (runtime/instantiate kir {:allow #{14 15 16} :providers (:providers kit)})))

(deftest resolve-endpoint-requires-host-config
  (is (thrown-with-msg? clojure.lang.ExceptionInfo #":endpoint"
                        (transport/resolve-endpoint {})))
  (is (= "https://o.example" (transport/resolve-endpoint {:endpoint "https://o.example"}))))

(deftest production-put-then-get-stream-round-trip
  (let [{:keys [endpoint] :as fake} (fake-object-server)]
    (try
      (let [runtime (hosted endpoint)
            payload (value/utf8-string->bytes "object-payload")
            put-req [object/put-block-request-type
                     :example/blocks "sha256:dead" payload]
            get-req [object/get-stream-request-type
                     :example/blocks "sha256:dead"]
            put-ok ((:invoke runtime) 'put-block [put-req])
            task ((:invoke runtime) 'get-stream [get-req])
            chunk (value/stream-read! (:stream (value/task-poll task)) 65536)]
        (is (true? put-ok))
        (is (true? (:done? chunk)))
        (is (zero? (value/compare-typed-values :bytes payload (:bytes chunk)))))
      (finally (stop! fake)))))

(deftest production-cas-wins-and-loses
  (let [{:keys [endpoint] :as fake} (fake-object-server)]
    (try
      (let [runtime (hosted endpoint)
            expected-none [object/expected-etag-type false]
            expected-old [object/expected-etag-type true "v1"]
            r1 ((:invoke runtime)
                'compare-and-set-ref
                [[object/cas-request-type :example/refs "main" expected-none "v1"]])
            r2 ((:invoke runtime)
                'compare-and-set-ref
                [[object/cas-request-type :example/refs "main" expected-old "v2"]])
            r3 ((:invoke runtime)
                'compare-and-set-ref
                [[object/cas-request-type :example/refs "main" expected-old "v3"]])]
        (is (true? r1))
        (is (true? r2))
        (is (false? r3)))
      (finally (stop! fake)))))

(deftest production-get-stream-missing-fails-closed
  (let [{:keys [endpoint] :as fake} (fake-object-server)]
    (try
      (let [runtime (hosted endpoint)]
        (is (thrown-with-msg?
             clojure.lang.ExceptionInfo #"object provider failed|missing"
             ((:invoke runtime) 'get-stream
              [[object/get-stream-request-type :example/blocks "nope"]]))))
      (finally (stop! fake)))))
