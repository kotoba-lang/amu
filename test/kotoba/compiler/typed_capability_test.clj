(ns kotoba.compiler.typed-capability-test
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.frontend :as frontend]
            [kotoba.kir :as ir]))

(def source
  "(ns demo.typed-cap (:export [invoke]) (:capabilities #{:http/post}))
   (defn invoke [request [:record :demo/request [[:url :string]]]]
     [:record :demo/response [[:status :i64]]]
     (typed-cap-call :http/post
       [:record :demo/request [[:url :string]]]
       [:record :demo/response [[:status :i64]]]
       request))")

(def request-type [:record :demo/request [[:url :string]]])
(def result-type [:record :demo/response [[:status :i64]]])

(deftest typed-capability-validates-both-sides-of-provider-boundary
  (let [kir (ir/lower (:hir (compiler/check-source source {:allow #{[:cap/call 4]}})))
        request [request-type "https://example.test"]]
    (is (= [result-type 204]
           (ir/execute kir 'invoke [request]
                       {:typed-cap-call
                        (fn [id actual-request-type actual-result-type actual-request]
                          (is (= 4 id))
                          (is (= request-type actual-request-type))
                          (is (= result-type actual-result-type))
                          (is (= request actual-request))
                          [result-type 204])})))
    (testing "a provider cannot forge a differently typed result"
      (is (thrown-with-msg?
           clojure.lang.ExceptionInfo #"invalid-parametric-value"
           (ir/execute kir 'invoke [request]
                       {:typed-cap-call (fn [& _] [request-type "wrong boundary"])}))))
    (testing "legacy cap-call cannot satisfy a typed boundary"
      (is (thrown-with-msg?
           clojure.lang.ExceptionInfo #"capability-denied"
           (ir/execute kir 'invoke [request] {:cap-call (fn [_ _] 0)}))))))

(deftest typed-capability-is-checked-statically
  (is (thrown-with-msg?
       clojure.lang.ExceptionInfo #"expression type mismatch"
       (compiler/check-source
        "(defn main [] :string (typed-cap-call 4 :string :string 1))"))))

(deftest schema-reference-is-closed-and-resolved-at-the-runtime-boundary
  (let [schema-type [:record :demo/request [[:url :string]]]
        source "(ns demo.ref-cap
                  (:export [invoke])
                  (:capabilities #{:http/post})
                  (:schemas {:demo/request [:record :demo/request [[:url :string]]] }))
                (defn invoke [request [:ref :demo/request]] [:ref :demo/request]
                  (typed-cap-call :http/post [:ref :demo/request] [:ref :demo/request] request))"
        kir (ir/lower (:hir (compiler/check-source source {:allow #{[:cap/call 4]}})))
        request [schema-type "https://example.test"]]
    (is (= request
           (ir/execute kir 'invoke [request]
                       {:typed-cap-call (fn [_ request-ref result-ref value]
                                          (is (= [:ref :demo/request] request-ref result-ref))
                                          value)})))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"outside the closed namespace table"
         (compiler/check-source
          "(ns missing.ref (:export [identity]))
           (defn identity [x [:ref :missing/schema]] [:ref :missing/schema] x)")))))

(deftest closed-document-requests-use-the-declared-boundary-type
  (let [source
        "(ns demo.document-cap
           (:export [expected submit forward])
           (:capabilities #{:http/post}))
         (defn expected [] :document
           (document {:action :actor/run :attempt 3 :ready true}))
         (defn submit [] :document
           (typed-cap-call :http/post :document :document
             {:action :actor/run :attempt 3 :ready true}))
         (defn forward [request :document] :document
           (typed-cap-call 4 :document :document request))"
        hir (frontend/analyze source)
        bodies (into {} (map (juxt :name :body) (:functions hir)))
        kir (ir/lower (:hir (compiler/check-source source {:allow #{[:cap/call 4]}})))
        expected (ir/execute kir 'expected [])
        provider (fn [id request-type actual-result-type request]
                   (is (= 4 id))
                   (is (= :document request-type actual-result-type))
                   request)]
    (is (= (nth (get bodies 'submit) 4)
           (get bodies 'expected))
        "the request must be the same constructor tree as explicit document syntax")
    (is (= expected
           (ir/execute kir 'submit [] {:typed-cap-call provider})))
    (is (= expected
           (ir/execute kir 'forward [expected] {:typed-cap-call provider}))
        "a document-typed lexical value must remain a value, not become symbol data")))
