(ns kotoba.compiler.callable-values-test
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as kir]))

(defn- execute-main [source]
  (kir/execute (:kir (compiler/compile-source source :js-kotoba-v1)) 'main []))

(defn- rejection-message [source]
  (try
    (compiler/check-source source)
    nil
    (catch clojure.lang.ExceptionInfo error
      (ex-message error))))

(deftest closures-cross-value-boundaries
  (is (= 5 (execute-main
            "(defn main [] (let [f (fn [x] (+ x 1))] (invoke f 4)))")))
  (is (= 7 (execute-main
            "(defn main [] (let [n 3 f (fn [x] (+ x n))] (invoke f 4)))")))
  (is (= 8 (execute-main
            "(defn make [n] (fn [x] (+ x n)))
             (defn main [] (invoke (make 5) 3))")))
  (is (= 3 (execute-main
            "(defn main []
               (let [f (fn [x] (+ x 1)) v [f]]
                 (invoke (vector-at v 0) 2)))"))))

(deftest callable-values-support-multiple-arities-and-bounded-apply
  (is (= 9 (execute-main
            "(defn make [base] (fn ([] base) ([a b] (+ a b))))
             (defn main [] (+ (invoke (make 4)) (invoke (make 0) 2 3)))")))
  (is (= 9 (execute-main
            "(defn add [a b] (+ a b))
             (defn main [] (apply (fn-ref add) (list 4 5)))")))
  (is (= 10 (execute-main
             "(defn main []
                (apply (fn [a b c d] (+ (+ a b) (+ c d))) 1 2 (list 3 4)))"))))

(deftest callable-values-are-bounded-and-closed
  (testing "closure ABI is capped at arity four"
    (is (re-find #"zero to four"
                 (rejection-message
                  "(defn main [] (invoke (fn [x] x) 1 2 3 4 5))"))))
  (testing "top-level references must resolve in the closed module"
    (is (re-find #"declared top-level function"
                 (rejection-message "(defn main [] (fn-ref missing))")))))

(deftest callable-values-lower-reproducibly-for-js-and-wasm
  (let [source "(defn add [a b] (+ a b))
                (defn main [] (invoke (fn-ref add) 20 22))"
        js (compiler/compile-source source :js-kotoba-v1)
        wasm-a (compiler/compile-source source :wasm32-browser-kotoba-v1)
        wasm-b (compiler/compile-source source :wasm32-browser-kotoba-v1)]
    (is (= 42 (kir/execute (:kir js) 'main [])))
    (is (= (:kir wasm-a) (:kir wasm-b)))
    (is (java.util.Arrays/equals ^bytes (:bytes wasm-a) ^bytes (:bytes wasm-b)))))
