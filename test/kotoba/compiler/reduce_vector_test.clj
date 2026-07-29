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
