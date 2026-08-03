(ns kotoba.compiler.multi-map-test
  "Bounded one-to-five-source eager map over vector-i64."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]))

(defn- run [src]
  (ir/execute (:kir (compiler/compile-source src :wasm32-kotoba-v1)) 'main []))

(deftest multi-map-fn
  (is (= 18 (run "(ns t (:export [main]))
(defn main [] :i64
  (reduce + 0 (map (fn [x y] (+ x y)) (vector-i64 1 2) (vector-i64 7 8))))"))))

(deftest multi-map-named
  (is (= 18 (run "(ns t (:export [main]))
(defn add [a :i64 b :i64] :i64 (+ a b))
(defn main [] :i64
  (reduce + 0 (map add (vector-i64 1 2) (vector-i64 7 8))))"))))

(deftest multi-map-shortest
  (is (= 2 (run "(ns t (:export [main]))
(defn main [] :i64
  (vector-count (map (fn [x y] (+ x y)) (vector-i64 1 2 3) (vector-i64 7 8))))"))))

(deftest multi-map-inline-scales-through-five-sources
  (is (= 6 (run "(defn main []
  (vector-at
    (map (fn [a b c] (+ a (+ b c))) [1] [2] [3])
    0))")))
  (is (= 15 (run "(defn main []
  (vector-at
    (map (fn [a b c d e] (+ a (+ b (+ c (+ d e)))))
         [1] [2] [3] [4] [5])
    0))"))))

(deftest multi-map-named-scales-through-five-sources
  (is (= 15 (run "(defn sum-five [a b c d e] (+ a (+ b (+ c (+ d e)))))
(defn main []
  (vector-at (map sum-five [1] [2] [3] [4] [5]) 0))"))))

(deftest multi-map-stored-closure-scales-through-four-sources
  (is (= 11 (run "(defn main []
  (let [bias 1
        combine (fn [a b c d] (+ bias (+ a (+ b (+ c d)))))]
    (vector-at (map combine [1] [2] [3] [4]) 0)))"))))

(deftest multi-map-five-source-shortest-termination
  (is (= 2 (run "(defn main []
  (vector-count
    (map (fn [a b c d e] (+ a (+ b (+ c (+ d e)))))
         [1 2 3] [4 5] [6 7 8] [9 10 11] [12 13 14])))"))))

(deftest multi-map-callback-bounds-and-lexical-shadowing
  (testing "stored closures retain their arity-four closure ABI"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"stored map callbacks support at most four"
         (compiler/check-source
          "(defn main []
             (let [f (fn [a b c d] (+ a (+ b (+ c d))))]
               (map f [1] [2] [3] [4] [5])))"))))
  (testing "known named callbacks fail before lowering when their arity disagrees"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"does not support the source arity"
         (compiler/check-source
          "(defn add [a b] (+ a b))
           (defn main [] (map add [1] [2] [3]))"))))
  (testing "a lexical callback shadows a same-named top-level function"
    (is (= 5 (run "(defn add [a b] (+ a b))
(defn main []
  (let [add (fn [a b] (- a b))]
    (vector-at (map add [9] [4]) 0)))")))))

(deftest map-scales-on-every-qualified-typed-product-target
  (let [two-source "(defn add [a b] (+ a b))
(defn main [] (vector-at (map add [1] [2]) 0))"
        five-source "(defn sum-five [a b c d e] (+ a (+ b (+ c (+ d e)))))
(defn main [] (vector-at (map sum-five [1] [2] [3] [4] [5]) 0))"
        typed-targets [:js-kotoba-v1 :wasm32-kotoba-v1 :cljs-kotoba-v1]
        ordinary (mapv #(compiler/compile-source two-source %) typed-targets)
        packed (mapv #(compiler/compile-source five-source %) typed-targets)]
    (is (= [3 3 3]
           (mapv #(get-in % [:kir :oracle-value]) ordinary)))
    (is (= [15 15 15]
           (mapv #(get-in % [:kir :oracle-value]) packed)))))
