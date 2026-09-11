(ns kotoba.compiler.map-filter-vector-test
  "T4.5: map/filter over vector-i64 desugar to zero-charge loops."
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]))

(defn- run [src]
  (ir/execute (:kir (compiler/compile-source src :wasm32-kotoba-v1)) 'main []))

(deftest map-fn-form
  (is (= 12 (run "(ns t (:export [main]))
(defn main [] :i64 (reduce + 0 (map (fn [x] (* x 2)) (vector-i64 1 2 3))))")))
  (is (= 0 (run "(ns t (:export [main]))
(defn main [] :i64 (vector-count (map (fn [x] x) (vector-i64))))"))))

(deftest map-inc-dec
  (is (= 9 (run "(ns t (:export [main]))
(defn main [] :i64 (reduce + 0 (map inc (vector-i64 1 2 3))))")))
  (is (= 3 (run "(ns t (:export [main]))
(defn main [] :i64 (reduce + 0 (map dec (vector-i64 1 2 3))))"))))

(deftest filter-fn-form
  (is (= 9 (run "(ns t (:export [main]))
(defn main [] :i64 (reduce + 0 (filter (fn [x] (> x 1)) (vector-i64 1 2 3 4))))")))
  (is (= 0 (run "(ns t (:export [main]))
(defn main [] :i64 (vector-count (filter (fn [x] (> x 10)) (vector-i64 1 2 3))))"))))

(deftest map-filter-compose
  ;; 12 + 9 + 9 = 30 (map *2 + filter >1 + map inc)
  (is (= 30 (run "(ns t (:export [main]))
(defn main [] :i64
  (+ (reduce + 0 (map (fn [x] (* x 2)) (vector-i64 1 2 3)))
     (+ (reduce + 0 (filter (fn [x] (> x 1)) (vector-i64 1 2 3 4)))
        (reduce + 0 (map inc (vector-i64 1 2 3))))))"))))
