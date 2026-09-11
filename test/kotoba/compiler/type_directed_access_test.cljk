(ns kotoba.compiler.type-directed-access-test
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.sema :as sema]
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

(deftest ordinary-nth-also-selects-homogeneous-vector-accessors
  (is (= 2 (ir/execute
            (:kir (compile-source "(defn main [] (nth [1 2 3] 1))"))
            'main [])))
  (is (= 9 (ir/execute
            (:kir (compile-source "(defn main [] (nth [1] 4 9))"))
            'main []))))

(deftest heterogeneous-nth-fails-closed-when-the-child-type-is-ambiguous
  (doseq [[source message]
          [["(defn pick [index :i64] :string
               (nth (hetero-vector [:vector [:i64 :string]] 7 \"x\") index))"
            #"index must be an integer literal"]
           ["(defn main [] :string
               (nth (hetero-vector [:vector [:i64 :string]] 7 \"x\") 2))"
            #"index must be in range"]
           ["(defn main [] :string
               (nth (hetero-vector [:vector [:i64 :string]] 7 \"x\") 1 0))"
            #"type mismatch"]
           ["(defn main [] :string
               (nth (hetero-vector [:vector [:i64 :string]] 7 \"x\") 1 false))"
            #"type mismatch"]]]
    (testing source
      (is (thrown-with-msg? clojure.lang.ExceptionInfo message
                            (sema/analyze source))))))

(deftest heterogeneous-nth-admits-a-typed-unreachable-default
  (let [source
        "(defn main [] :string
           (nth (hetero-vector [:vector [:i64 :string]] 7 \"x\")
                1 \"fallback\"))"
        compiled (compile-source source)]
    (is (= "x" (ir/execute (:kir compiled) 'main [])))
    (is (not-any? #{"fallback"}
                  (tree-seq coll? seq (:kir compiled))))))

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

(deftest nested-destructuring-selects-exact-accessors
  (let [vector-source
        "(defn main [] :string
           (let [[id [name active]]
                 (hetero-vector
                  [:vector [:i64 [:vector [:string :bool]]]]
                  7
                  (hetero-vector [:vector [:string :bool]] \"Ada\" true))]
             (if active name \"inactive\")))"
        record-source
         "(ns demo)
         (defrecord Profile [name :string])
         (defrecord User [profile [:record :demo/Profile [[:name :string]]]])
         (defn main [] :string
           (let [{{:keys [name]} :profile}
                 (->User (->Profile \"Lin\"))]
             name))"
        typed-map-source
        "(defn main [] :string
           (let [{:keys [name] :or {name \"missing\"}}
                 (typed-map-new [:map :keyword :string] :name \"Grace\")]
             name))"]
    (is (= "Ada" (ir/execute (:kir (compile-source vector-source)) 'main [])))
    (is (= "Lin" (ir/execute (:kir (compile-source record-source)) 'main [])))
    (is (= "Grace" (ir/execute (:kir (compile-source typed-map-source)) 'main [])))
    (doseq [source [vector-source record-source typed-map-source]]
      (is (not-any? #(and (seq? %)
                          (contains? '#{nth get __kotoba_destructure_get} (first %)))
                    (tree-seq coll? seq (:kir (compile-source source))))))))

(deftest typed-map-destructuring-keeps-missingness-explicit
  (is (thrown-with-msg?
       clojure.lang.ExceptionInfo
       #"requires an :or default"
       (sema/analyze
        "(defn main [] :string
           (let [{:keys [name]}
                 (typed-map-new [:map :keyword :string] :name \"Ada\")]
             name))"))))

(deftest typed-function-parameters-admit-nested-patterns
  (let [source
        "(defn choose
           [[id [name active]] [:vector [:i64 [:vector [:string :bool]]]]]
           :string
           (if active name \"inactive\"))
         (defn main [] :string
           (choose
            (hetero-vector
             [:vector [:i64 [:vector [:string :bool]]]]
             9
             (hetero-vector [:vector [:string :bool]] \"Mio\" true))))"]
    (is (= "Mio" (ir/execute (:kir (compile-source source)) 'main [])))))

(deftest heterogeneous-vector-rest-synthesizes-an-exact-suffix
  (let [source
        "(defn main [] :string
           (let [[id [left right] & rest]
                 [7 [1 2] \"Ada\" true]
                 [name active] rest]
             (if active name \"inactive\")))"
        compiled (compile-source source)
        nodes (tree-seq coll? seq (:kir compiled))]
    (is (= "Ada" (ir/execute (:kir compiled) 'main [])))
    (is (some #(and (seq? %)
                    (= 'hetero-vector-new (first %))
                    (= [:vector [:string :bool]] (second %)))
              nodes))
    (is (not-any? #(and (seq? %) (= 'vector-drop (first %))) nodes))
    (is (= (:kir compiled) (:kir (compile-source source)))
        "the suffix temp is deterministic across compilations")))

(deftest heterogeneous-vector-rest-may-be-empty
  (let [source
        "(defn main [] :i64
           (let [[value & rest]
                 (hetero-vector [:vector [:i64]] 7)]
             (hetero-vector-count [:vector []] rest)))"]
    (is (= 0 (ir/execute (:kir (compile-source source)) 'main [])))))

(deftest heterogeneous-vector-drop-is-literal-and-bounded
  (doseq [[source message]
          [["(defn bad [n :i64] [:vector [:string]]
               (vector-drop
                (hetero-vector [:vector [:i64 :string]] 7 \"x\") n))"
            #"drop count must be an integer literal"]
           ["(defn bad [] [:vector []]
               (vector-drop
                (hetero-vector [:vector [:i64 :string]] 7 \"x\") 3))"
            #"drop count must be in range"]]]
    (testing source
      (is (thrown-with-msg? clojure.lang.ExceptionInfo message
                            (sema/analyze source))))))

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
                            (sema/analyze source))))))
