(ns kotoba.compiler.reduce-named-test
  "T4.5: named binary HOF for reduce over vector-i64."
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]))

(defn- run [src]
  (ir/execute (:kir (compiler/compile-source src :wasm32-kotoba-v1)) 'main []))

(deftest reduce-named-binary
  (is (= 10 (run "(ns t (:export [main]))
(defn add [a :i64 b :i64] :i64 (+ a b))
(defn main [] :i64 (reduce add 0 (vector-i64 1 2 3 4)))")))
  (is (= 12 (run "(ns t (:export [main]))
(defn mul-acc [a :i64 b :i64] :i64 (+ a (* b 2)))
(defn main [] :i64 (reduce mul-acc 0 (vector-i64 1 2 3)))"))))
