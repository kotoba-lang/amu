(ns kotoba.compiler.lazy-sequence-test
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as kir]))

(defn- execute-main [source]
  (kir/execute (:kir (compiler/compile-source source :wasm32-kotoba-v1)) 'main []))

(defn- rejection-message [source]
  (try
    (compiler/check-source source)
    nil
    (catch clojure.lang.ExceptionInfo error
      (ex-message error))))

(def naturals-source
  "(defn naturals [n] (lazy-cons n (naturals (+ n 1))))")

(deftest lazy-cells-force-heads-and-tails
  (is (= 1 (execute-main
            (str naturals-source
                 " (defn main [] (lazy-first (naturals 1)))"))))
  (is (= 4 (execute-main
            (str naturals-source
                 " (defn main [] (lazy-first (drop 3 (naturals 1))))"))))
  (is (= 6 (execute-main
            (str naturals-source
                 " (defn main []
                      (let [xs (take 3 (naturals 1))]
                        (+ (first xs)
                           (+ (first (rest xs))
                              (first (rest (rest xs)))))))")))))

(deftest lazy-empty-is-explicit-and-finite
  (is (= 1 (execute-main
            "(defn main [] (if (lazy-empty? 0) 1 0))")))
  (is (= 1 (execute-main
            "(defn finite [n]
               (if (> n 2) 0 (lazy-cons n (finite (+ n 1)))))
             (defn main [] (if (lazy-empty? (drop 3 (finite 0))) 1 0))"))))

(deftest lazy-thunks-are-effect-free
  (testing "call-by-name cannot duplicate a capability effect"
    (is (re-find #"must be effect-free"
                 (rejection-message
                  "(defn main [] (lazy-cons (cap-call 1 0) 0))")))))

(deftest lazy-core-lowers-reproducibly-to-wasm
  (let [source (str naturals-source
                    " (defn main [] (lazy-first (drop 4 (naturals 38))))")
        a (compiler/compile-source source :wasm32-browser-kotoba-v1)
        b (compiler/compile-source source :wasm32-browser-kotoba-v1)]
    (is (= 42 (kir/execute (:kir a) 'main [])))
    (is (java.util.Arrays/equals ^bytes (:bytes a) ^bytes (:bytes b)))))
