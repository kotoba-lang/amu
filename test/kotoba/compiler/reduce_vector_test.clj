(ns kotoba.compiler.reduce-vector-test
  "T4.5: reduce over vector-i64 desugars to zero-charge loop."
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]))

(defn- run [src]
  (ir/execute (:kir (compiler/compile-source src :wasm32-kotoba-v1)) 'main []))

(deftest reduce-arithmetic-op
  (is (= 10 (run "(ns t (:export [main]))
(defn main [] :i64 (reduce + 0 (vector-i64 1 2 3 4)))")))
  (is (= 7 (run "(ns t (:export [main]))
(defn main [] :i64 (reduce + 7 (vector-i64)))"))))

(deftest reduce-fn-form
  (is (= 13 (run "(ns t (:export [main]))
(defn main [] :i64 (reduce (fn [a x] (+ a x)) 10 (vector-i64 1 2)))")))
  (is (= 12 (run "(ns t (:export [main]))
(defn main [] :i64 (reduce (fn [a x] (+ a (* x 2))) 0 (vector-i64 1 2 3)))"))))

(deftest reduce-without-init
  (is (= 41 (run "(ns t (:export [main]))
(defn main [] :i64
  (reduce (fn ([] 41) ([a x] (+ a x))) (vector-i64)))")))
  (is (= 6 (run "(ns t (:export [main]))
(defn main [] :i64
  (reduce (fn ([] 0) ([a x] (+ a x))) (vector-i64 1 2 3)))")))
  (is (= 17 (run "(ns t (:export [main]))
(defn sum ([] 11) ([a x] (+ a x)))
(defn main [] :i64
  (+ (reduce sum (vector-i64)) (reduce sum (vector-i64 1 2 3))))")))
  (is (= 46 (run "(ns t (:export [main]))
(defn make [empty] (fn ([] empty) ([a x] (+ a x))))
(defn main [] :i64
  (+ (reduce (make 40) (vector-i64))
     (reduce (make 0) (vector-i64 1 2 3))))"))))
