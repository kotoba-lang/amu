(ns kotoba.compiler.named-hof-test
  "T4.5: named unary HOF for map/filter over vector-i64."
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]))

(defn- run [src]
  (ir/execute (:kir (compiler/compile-source src :wasm32-kotoba-v1)) 'main []))

(deftest map-named-unary
  (is (= 12 (run "(ns t (:export [main]))
(defn dbl [x :i64] :i64 (* x 2))
(defn main [] :i64 (reduce + 0 (map dbl (vector-i64 1 2 3))))"))))

(deftest filter-named-unary
  (is (= 9 (run "(ns t (:export [main]))
(defn above1 [x :i64] :i64 (if (> x 1) 1 0))
(defn main [] :i64 (reduce + 0 (filter above1 (vector-i64 1 2 3 4))))"))))

(deftest named-hof-compose
  (is (= 21 (run "(ns t (:export [main]))
(defn dbl [x :i64] :i64 (* x 2))
(defn above1 [x :i64] :i64 (if (> x 1) 1 0))
(defn main [] :i64
  (+ (reduce + 0 (map dbl (vector-i64 1 2 3)))
     (reduce + 0 (filter above1 (vector-i64 1 2 3 4)))))"))))
