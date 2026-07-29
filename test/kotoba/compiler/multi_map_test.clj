(ns kotoba.compiler.multi-map-test
  "T4.5: 2-source map over vector-i64."
  (:require [clojure.test :refer [deftest is]]
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
