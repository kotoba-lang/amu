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
