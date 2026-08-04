(ns kotoba.compiler.record-protocol-static-dispatch-test
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.frontend :as frontend]
            [kotoba.kir :as ir]))

(def fixture
  "(defprotocol Value
     (value [this]))

   (defrecord LocalBox [x]
     Value
     (value [this] (get this :x)))

   (defrecord ExtendedBox [x])

   (extend-type ExtendedBox
     Value
     (value [this] (get this :x)))

   (defn main []
     (+ (value (->LocalBox 7))
        (value (map->ExtendedBox {:x 9}))))")

(defn- compile-fixture [source]
  (compiler/compile-source source :wasm32-kotoba-v1 {}
                           {:language-profile :pure-product}))

(deftest record-protocol-fixture-has-static-kir-and-wasm-parity
  (let [first-build (compile-fixture fixture)
        second-build (compile-fixture fixture)]
    (is (= 16 (ir/execute (:kir first-build) 'main [])))
    (is (= (seq (:bytes first-build)) (seq (:bytes second-build))))
    (is (not-any? #{'defrecord 'defprotocol 'extend-type}
                  (tree-seq coll? seq (:kir first-build))))))

(deftest protocol-dispatch-follows-record-types-through-lexical-bindings
  (let [source
        "(defprotocol Value (value [this]))
         (defrecord Box [x] Value (value [this] (get this :x)))
         (defn main [] (let [box (->Box 41)] (+ 1 (value box))))"]
    (is (= 42 (ir/execute (:kir (compile-fixture source)) 'main [])))))

(deftest record-member-rewrite-respects-lexical-shadowing
  (let [rewrite-member @(ns-resolve 'kotoba.compiler.frontend
                                    'rewrite-record-member-access)
        descriptor [:record 'kotoba.user/Box [[:x :i64]]]]
    (is (= '(let [this local]
              (get this :x))
           (rewrite-member '(let [this local]
                              (get this :x))
                           'this descriptor)))
    (is (= '(let [x (record-get [:record kotoba.user/Box [[:x :i64]]] this :x)
                  this local]
              (get this :x))
           (rewrite-member '(let [x (get this :x)
                                  this local]
                              (get this :x))
                           'this descriptor)))
    (is (= '(fn [this] (get this :x))
           (rewrite-member '(fn [this] (get this :x)) 'this descriptor)))
    (is (= '(loop [this local
                   x (record-get [:record kotoba.user/Box [[:x :i64]]] this :x)]
              (get this :x))
           (rewrite-member '(loop [this local x (get this :x)]
                              (get this :x))
                           'this descriptor)))
    (is (= '(fn [value]
              (record-get [:record kotoba.user/Box [[:x :i64]]] this :x))
           (rewrite-member '(fn [value] (get this :x)) 'this descriptor)))))

(deftest extend-type-supports-multiple-complete-protocol-sections
  (let [source
        "(defprotocol Value (value [this]))
         (defprotocol Delta (delta [this x]))
         (defrecord Box [x])
         (extend-type Box
           Value (value [this] (get this :x))
           Delta (delta [this x] (+ (get this :x) x)))
         (defn main []
           (+ (value (->Box 7)) (delta (->Box 8) 9)))"]
    (is (= 24 (ir/execute (:kir (compile-fixture source)) 'main [])))))

(deftest defrecord-fields-use-the-function-signature-type-spelling
  (let [constructor-source
        "(defrecord Person [name :string active :bool])
         (defn main [] :string (:name (->Person \"Ada\" true)))"
        map-source
        "(defrecord Person [name :string active :bool])
         (defn main [] :string
           (:name (map->Person {:active true :name \"Grace\"})))"
        protocol-source
        "(defprotocol Label (label [this]))
         (defrecord Person [name :string]
           Label
           (label [this] (get this :name)))
         (defn main [] :string (label (->Person \"Lin\")))"]
    (is (= "Ada" (ir/execute (:kir (compile-fixture constructor-source)) 'main [])))
    (is (= "Grace" (ir/execute (:kir (compile-fixture map-source)) 'main [])))
    (is (= "Lin" (ir/execute (:kir (compile-fixture protocol-source)) 'main [])))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo
         #"type mismatch"
         (compile-fixture
          "(defrecord Person [name :string])
           (defn main [] :string (:name (->Person 7)))")))))

(deftest wide-defrecord-keeps-direct-and-map-construction-data-shaped
  (let [source
        "(ns demo.http)
         (defrecord Header [name :string value :string])
         (defrecord Request
           [url :string
            headers [:set [:ref :demo.http/Header]]
            names [:set :string]
            body :string
            timeout :i64
            code :i64])
         (defn main [] :i64
           (let [header (->Header \"accept\" \"text/plain\")
                 headers (typed-set-conj [:set [:ref :demo.http/Header]]
                                         (typed-set-new [:set [:ref :demo.http/Header]])
                                         header)
                 request (map->Request
                          {:url \"https://example.test\"
                           :headers headers
                           :names (typed-set-new [:set :string])
                           :body \"\"
                           :timeout 30
                           :code 7})]
             (+ (:code request)
                (typed-set-count [:set [:ref :demo.http/Header]]
                                 (:headers request)))))"
        positional
        "(ns demo.wide)
         (defrecord Six [a b c d e f])
         (defrecord Wrapper [six [:ref :demo.wide/Six]])
         (defn main []
           (:f (:six (map->Wrapper {:six (->Six 1 2 3 4 5 6)}))))"]
    (is (= 8 (ir/execute (:kir (compile-fixture source)) 'main [])))
    (is (= 6 (ir/execute (:kir (compile-fixture positional)) 'main [])))
    (doseq [compiled [(compile-fixture source) (compile-fixture positional)]]
      (is (not-any? #{'defrecord '->Six 'map->Request}
                    (tree-seq coll? seq (:kir compiled)))))))

(deftest defrecord-registers-before-the-closed-schema-graph-is-validated
  (let [source
        "(ns demo.forward
           (:schemas {:demo.forward/Node
                      [:variant :demo.forward/Node
                       [[:entry [:ref :demo.forward/Entry]]]]}))
         (defrecord Entry [k :string v :string])
         (defn main [] :i64
           (match-variant
            (variant-new
             [:variant :demo.forward/Node
              [[:entry [:ref :demo.forward/Entry]]]]
             :entry
             (->Entry \"answer\" \"42\"))
            [:variant :demo.forward/Node
             [[:entry [:ref :demo.forward/Entry]]]]
            (:entry entry (string-length (:v entry)))))"
        compiled (compile-fixture source)
        analyzed (frontend/analyze source {:language-profile :pure-product})]
    (is (= 2 (ir/execute (:kir compiled) 'main [])))
    (is (= [:record :demo.forward/Entry [[:k :string] [:v :string]]]
           (get (:schemas analyzed) :demo.forward/Entry))))
  (is (= [:record :demo.exact/Entry [[:value :string]]]
         (get (:schemas
               (frontend/analyze
                "(ns demo.exact
                   (:schemas {:demo.exact/Entry
                              [:record :demo.exact/Entry [[:value :string]]]
                              :demo.exact/Node
                              [:variant :demo.exact/Node
                               [[:entry [:ref :demo.exact/Entry]]]]}))
                 (defrecord Entry [value :string])
                 (defn main [] 0)"))
              :demo.exact/Entry)))
  (is (thrown-with-msg?
       clojure.lang.ExceptionInfo
       #"forward declaration must match exactly"
       (frontend/analyze
        "(ns demo.collision
           (:schemas {:demo.collision/Box
                      [:record :demo.collision/Box [[:x :string]]]}))
         (defrecord Box [x])
         (defn main [] 0)"))))

(deftest record-and-protocol-surface-fails-closed
  (doseq [[source message]
          [["(defprotocol Value (value [this]))
             (defrecord Box [x])
             (defn main [] (value 1))"
            #"statically known implemented record"]
           ["(defprotocol Value (value [this]))
             (defrecord Box [x] Value (value [this] 1))
             (extend-type Box Value (value [this] 2))
             (defn main [] 0)"
            #"duplicate protocol method implementation"]
           ["(defprotocol Value (value [this]) (other [this]))
             (defrecord Box [x] Value (value [this] 1))
             (defn main [] 0)"
            #"implement every declared method exactly once"]
           ["(defrecord Box [x])
             (defn main [] (map->Box {:wrong 1}))"
            #"exactly the declared fields"]
           ["(defrecord Box [x :string y])
             (defn main [] 0)"
            #"alternating name/type pairs"]
           ["(defrecord Box [x :string x :i64])
             (defn main [] 0)"
            #"at most 32 unique fields"]
           ["(defprotocol Value (value [this]))
             (defrecord Box [x])
             (extend-protocol Value Box (value [this] 1))
             (defn main [] 0)"
            #"outside the canonical compiler's first static-dispatch profile"]
           ["(defprotocol Value (value [this]))
             (defn value [x] x)
             (defrecord Box [x])
             (defn main [] (value 1))"
            #"must not collide with declared functions"]]]
    (testing source
      (is (thrown-with-msg? clojure.lang.ExceptionInfo message
                            (frontend/analyze source))))))
