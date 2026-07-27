(ns kotoba.compiler.named-ability-elaboration-test
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.frontend :as frontend]))

(def ^:private schemas
  "(:schemas
    {:demo/request [:record :demo/request [[:body :string]]]
     :demo/result [:variant :demo/result [[:ok :string] [:error :keyword]]]})")

(defn- source [operation]
  (str "(ns demo.named (:export [invoke]) "
       "(:capabilities #{:http/post}) " schemas ")"
       "(defn invoke [request [:ref :demo/request]] [:ref :demo/result] "
       operation ")"))

(deftest friendly-operation-elaborates-to-the-existing-typed-kir-shape
  (let [friendly (:hir
                  (compiler/check-source
                   (source "(http/post request)")
                   {:allow #{[:cap/call 4]}}))
        explicit (:hir
                  (compiler/check-source
                   (source
                    "(typed-cap-call :http/post
                       [:ref :demo/request] [:ref :demo/result] request)")
                   {:allow #{[:cap/call 4]}}))]
    (is (= explicit friendly))
    (is (= #{[:cap/call 4]} (:effects friendly)))
    (is (= '(typed-cap-call 4
             [:ref :demo/request] [:ref :demo/result] request)
           (get-in friendly [:functions 0 :body])))))

(deftest branch-context-elaborates-both-effect-paths
  (let [checked
        (compiler/check-source
         (str "(ns demo.branch (:export [invoke]) " schemas ")"
              "(defn invoke [flag :bool request [:ref :demo/request]]"
              " [:ref :demo/result]"
              " (if flag (http/post request) (http/post request)))")
         {:allow #{[:cap/call 4]}})]
    (is (= #{[:cap/call 4]} (get-in checked [:hir :effects])))
    (is (= 2
           (count
            (filter #(and (seq? %) (= 'typed-cap-call (first %)))
                    (tree-seq coll? seq
                              (get-in checked [:hir :functions 0 :body]))))))))

(deftest namespace-declaration-remains-a-security-ceiling
  (testing "friendly operation is included in declare-then-check"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo
         #"not declared"
         (compiler/check-source
          (str "(ns demo.denied (:export [invoke]) "
               "(:capabilities #{:llm/generate}) " schemas ")"
               "(defn invoke [request [:ref :demo/request]] [:ref :demo/result]"
               " (http/post request))"))))))

(deftest operations-without-result-context-fail-closed
  (is (thrown-with-msg?
       clojure.lang.ExceptionInfo
       #"requires a typed result context"
       (compiler/check-source
        "(ns demo.unbound (:export [invoke]))
         (defn invoke [request :i64] :i64
           (let [response (http/post request)] response))"))))

(deftest catalog-drives-both-source-and-wire-resolution
  (is (= :http/post (get frontend/source-operation-registry 'http/post)))
  (is (= 4 (get frontend/capability-registry :http/post)))
  (is (= (set (keys frontend/capability-registry))
         (set (vals frontend/source-operation-registry)))))
