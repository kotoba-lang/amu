(ns kotoba.compiler.type-directed-access-test
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.frontend :as frontend]
            [kotoba.kir :as ir]))

(defn- compile-source [source]
  (compiler/compile-source source :wasm32-kotoba-v1 {}
                           {:language-profile :pure-product}))

(deftest ordinary-nth-selects-the-heterogeneous-vector-accessor
  (let [source
        "(defn main [] :string
           (let [values (hetero-vector [:vector [:i64 :string :bool]]
                                       7 \"Ada\" true)]
             (nth values 1)))"
        compiled (compile-source source)]
    (is (= "Ada" (ir/execute (:kir compiled) 'main [])))
    (is (some #(and (seq? %) (= 'hetero-vector-at (first %)))
              (tree-seq coll? seq (:kir compiled))))
    (is (not-any? #(and (seq? %) (= 'nth (first %)))
                  (tree-seq coll? seq (:kir compiled))))))

(deftest heterogeneous-nth-keeps-the-child-type-exact
  (let [source
        "(defn main [] :bool
           (nth (hetero-vector [:vector [:string :bool]] \"x\" true) 1))"]
    (is (= true (ir/execute (:kir (compile-source source)) 'main [])))))

(deftest heterogeneous-nth-fails-closed-when-the-child-type-is-ambiguous
  (doseq [[source message]
          [["(defn pick [index :i64] :string
               (nth (hetero-vector [:vector [:i64 :string]] 7 \"x\") index))"
            #"index must be an integer literal"]
           ["(defn main [] :string
               (nth (hetero-vector [:vector [:i64 :string]] 7 \"x\") 1 \"fallback\"))"
            #"requires value and one literal index"]
           ["(defn main [] :string
               (nth (hetero-vector [:vector [:i64 :string]] 7 \"x\") 2))"
            #"index must be in range"]]]
    (testing source
      (is (thrown-with-msg? clojure.lang.ExceptionInfo message
                            (frontend/analyze source))))))

(deftest ordinary-get-selects-typed-map-and-record-accessors
  (let [typed-map-source
        "(defn main [] :string
           (let [names (typed-map-new [:map :keyword :string] :user \"Ada\")]
             (option-or (get names :user) \"missing\")))"
        default-source
        "(defn main [] :string
           (get (typed-map-new [:map :keyword :string] :user \"Ada\")
                :missing \"Grace\"))"
        record-source
        "(defrecord Person [name :string])
         (defn main [] :string (get (->Person \"Lin\") :name))"]
    (is (= "Ada" (ir/execute (:kir (compile-source typed-map-source)) 'main [])))
    (is (= "Grace" (ir/execute (:kir (compile-source default-source)) 'main [])))
    (is (= "Lin" (ir/execute (:kir (compile-source record-source)) 'main [])))))

(deftest type-directed-get-rejects-schema-erasing-uses
  (doseq [[source message]
          [["(defn main [] :string
               (get (typed-map-new [:map :keyword :string] :x \"ok\") :x 0))"
            #"type mismatch"]
           ["(defrecord Person [name :string])
             (defn main [] :string (get (->Person \"Ada\") :missing))"
            #"record field"]
           ["(defrecord Person [name :string])
             (defn main [] :string (get (->Person \"Ada\") :name \"fallback\"))"
            #"requires a value and one keyword field"]]]
    (testing source
      (is (thrown-with-msg? clojure.lang.ExceptionInfo message
                            (frontend/analyze source))))))
