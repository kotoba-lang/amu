(ns kotoba.compiler.object-provider-test
  "W5 stream-object dual-runtime first slice — put-block + CAS write path."
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [provider.object :as object]
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
        kir (ir/lower (:hir (compiler/check-source
                             source {:allow #{[:cap/call 15] [:cap/call 16]}})))]
    (runtime/instantiate kir {:allow #{15 16} :providers (:providers kit)})))

(deftest put-block-crosses-only-the-typed-boundary
  (let [seen (atom nil)
        runtime (hosted (fn [request]
                          (reset! seen request)
                          true))
        request [object/put-block-request-type
                 :example/blocks "sha256:deadbeef" "payload-bytes"]]
    (is (true? ((:invoke runtime) 'put-block [request])))
    (is (= {:operation :put-block
            :binding :example/blocks
            :digest "sha256:deadbeef"
            :bytes "payload-bytes"}
           @seen))))

(deftest cas-wins-and-loses-are-typed-bools
  (let [won (hosted (fn [_] true))
        lost (hosted (fn [_] false))
        expected [object/expected-etag-type true "etag-1"]
        request [object/cas-request-type
                 :example/refs "main" expected "etag-2"]]
    (is (true? ((:invoke won) 'compare-and-set-ref [request])))
    (is (false? ((:invoke lost) 'compare-and-set-ref [request])))))

(deftest bindings-and-empty-fields-fail-closed
  (let [called? (atom false)
        runtime (hosted (fn [_] (reset! called? true) true))]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"binding is not allowed"
         ((:invoke runtime) 'put-block
          [[object/put-block-request-type
            :example/other "sha256:x" "p"]])))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"digest must be non-empty"
         ((:invoke runtime) 'put-block
          [[object/put-block-request-type
            :example/blocks "" "p"]])))
    (is (false? @called?))))

(deftest transport-exceptions-are-redacted
  (let [runtime (hosted (fn [_] (throw (ex-info "secret object URL" {}))))]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"object provider failed"
         ((:invoke runtime) 'put-block
          [[object/put-block-request-type
            :example/blocks "sha256:x" "p"]])))))

(deftest missing-grant-denies-before-provider-invoke
  (let [kir (ir/lower (:hir (compiler/check-source
                             source {:allow #{[:cap/call 15] [:cap/call 16]}})))
        runtime (runtime/instantiate kir)]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"capability denied"
         ((:invoke runtime) 'put-block
          [[object/put-block-request-type
            :example/blocks "sha256:x" "p"]])))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"capability denied"
         ((:invoke runtime) 'compare-and-set-ref
          [[object/cas-request-type
            :example/refs "main"
            [object/expected-etag-type false]
            "etag-2"]])))))
