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

(deftest lexical-closures-use-ordinary-application-syntax
  (is (= 5 (execute-main
            "(defn main [] (let [f (fn [x] (+ x 1))] (f 4)))")))
  (is (= 7 (execute-main
            "(defn main []
               (let [bias 3 f (fn [x] (+ x bias)) result (f 4)] result))")))
  (is (= 5 (execute-main
            "(defn call-one [f] (f 4))
             (defn main [] (call-one (fn [x] (+ x 1))))")))
  (is (= 6 (execute-main
            "(defn main []
               (invoke (fn [f] (f 5)) (fn [x] (+ x 1))))")))
  (is (= 3 (execute-main
            "(defn main []
               (let [[f] [(fn [x] (+ x 1))]] (f 2)))"))))

(deftest lexical-closure-heads-shadow-ordinary-functions
  (is (= 5 (execute-main
            "(defn add [x] (+ x 100))
             (defn main [] (let [add (fn [x] (+ x 1))] (add 4)))")))
  (is (= 5 (execute-main
            "(defn main [] (let [+ (fn [a b] (- a b))] (+ 9 4)))")))
  (testing "unbound call heads remain closed-world errors"
    (is (re-find #"no admitted lowering"
                 (rejection-message "(defn main [] (misspelled 1))"))))
  (testing "direct closure application retains the ABI arity bound"
    (is (re-find #"arity four"
                 (rejection-message
                  "(defn main []
                     (let [f (fn [x] x)] (f 1 2 3 4 5)))")))))

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

(deftest stored-closures-compose-with-bounded-higher-order-operations
  (is (= 5 (execute-main
            "(defn main []
               (let [bias 2 f (fn [x] (+ x bias))]
                 (vector-at (map f [1 3]) 1)))")))
  (is (= 4 (execute-main
            "(defn make [bias] (fn [x] (+ x bias)))
             (defn transform [f :i64 xs :vector-i64] :vector-i64 (map f xs))
             (defn main [] (vector-at (transform (make 3) [1]) 0))")))
  (is (= 4 (execute-main
            "(defn main []
               (let [minimum 2 keep? (fn [x] (> x minimum))]
                 (vector-at (filter keep? [1 4 2]) 0)))")))
  (is (= 5 (execute-main
            "(defn make [minimum] (fn [x] (> x minimum)))
             (defn select [pred :i64 xs :vector-i64] :vector-i64 (filter pred xs))
             (defn main [] (vector-at (select (make 3) [2 5 3]) 0))")))
  (is (= 5 (execute-main
            "(defn main []
               (let [bias 1 add (fn [acc x] (+ acc (+ x bias)))]
                 (reduce add 0 [1 2])))")))
  (is (= 9 (execute-main
            "(defn add [a b] (+ a b))
             (defn main [] (reduce (fn-ref add) 0 [4 5]))"))))

(deftest lexical-callbacks-shadow-same-named-top-level-functions
  (is (= 4 (execute-main
            "(defn keep? [x] false)
             (defn main []
               (let [keep? (fn [x] (> x 2))]
                 (vector-at (filter keep? [1 4]) 0)))")))
  (is (= 7 (execute-main
            "(defn combine [a b] (+ a b))
             (defn main []
               (let [combine (fn [a b] (- a b))]
                 (reduce combine 10 [3])))"))))

(deftest callable-values-have-explicit-typed-results
  (is (= 1 (execute-main
            "(defn main []
               (if (invoke :bool (fn [x] (> x 2)) 3) 1 0))")))
  (is (= 7 (execute-main
            "(defn main []
               (vector-at (invoke :vector-i64 (fn [x] [x]) 7) 0))")))
  (is (= 2 (execute-main
            "(defn main []
               (string-length (invoke :string (fn [x] (string-from-i64 x)) 42)))")))
  (testing "a closure from a different result family traps closed"
    (is (thrown? clojure.lang.ExceptionInfo
                 (execute-main
                  "(defn main []
                     (if (invoke :bool (fn [x] (+ x 1)) 3) 1 0))"))))
  (testing "a vector dispatcher rejects a scalar-returning closure"
    (is (thrown? clojure.lang.ExceptionInfo
                 (execute-main
                  "(defn main []
                     (vector-count (invoke :vector-i64 (fn [x] (+ x 1)) 3)))"))))
  (testing "a string dispatcher rejects a scalar-returning closure"
    (is (thrown? clojure.lang.ExceptionInfo
                 (execute-main
                  "(defn main []
                     (string-length (invoke :string (fn [x] (+ x 1)) 3)))")))))

(deftest lexical-string-results-use-contextual-application-syntax
  (is (= 2 (execute-main
            "(defn main []
               (let [render (fn [x] (string-from-i64 x))]
                 (string-length (render 42))))")))
  (is (= 3 (execute-main
            "(defn render-with [f] :string (let [n 123] (f n)))
             (defn main []
               (string-length (render-with (fn [x] (string-from-i64 x)))))")))
  (is (= 2 (execute-main
            "(defn main []
               (let [render (fn [x] (string-from-i64 x))]
                 (string-length
                  (if (> 2 1) (render 42) (render 7)))))")))
  (is (= 4 (execute-main
            "(defn main []
               (let [render (fn [x] (string-from-i64 x))]
                 (string-length (string-concat (render 12) (render 34)))))")))
  (is (= 2 (execute-main
            "(defn render [x :i64] :string (string-from-i64 x))
             (defn main []
               (string-length (invoke :string (fn-ref render) 42)))"))))

(deftest lexical-vector-results-use-contextual-application-syntax
  (is (= 7 (execute-main
            "(defn main []
               (let [singleton (fn [x] [x])]
                 (vector-at (singleton 7) 0)))")))
  (is (= 4 (execute-main
            "(defn main []
               (let [singleton (fn [x] [x])]
                 (vector-at (map inc (singleton 3)) 0)))")))
  (is (= 7 (execute-main
            "(defn call-singleton [f] (vector-at (f 7) 0))
             (defn main [] (call-singleton (fn [x] [x])))")))
  (is (= 8 (execute-main
            "(defn singleton [x :i64] :vector-i64 [x])
             (defn main []
               (vector-at (invoke :vector-i64 (fn-ref singleton) 8) 0))")))
  (is (= 9 (execute-main
            "(defn main []
               (let [singleton (fn [x] [x]) stored [singleton]]
                 (vector-at (invoke :vector-i64 (vector-at stored 0) 9) 0)))")))
  (testing "the default scalar family still rejects vector-returning closures"
    (is (thrown? clojure.lang.ExceptionInfo
                 (execute-main
                  "(defn main []
                     (let [singleton (fn [x] [x])]
                       (invoke singleton 3)))")))))

(deftest lexical-predicates-use-contextual-application-syntax
  (is (= 1 (execute-main
            "(defn main []
               (let [positive? (fn [x] (> x 0))]
                 (if (positive? 3) 1 0)))")))
  (is (= 7 (execute-main
            "(defn choose [predicate] (cond (predicate 3) 7 :else 0))
             (defn main [] (choose (fn [x] (> x 2))))")))
  (is (= 1 (execute-main
            "(defn main []
               (let [positive? (fn [x] (> x 0))]
                 (if (and (positive? 2) (positive? 1)) 1 0)))")))
  (is (= 1 (execute-main
            "(defn main []
               (let [> (fn [a b] (< b a))]
                 (if (> 3 2) 1 0)))")))
  (testing "contextual boolean calls retain result-family safety"
    (is (thrown? clojure.lang.ExceptionInfo
                 (execute-main
                  "(defn main []
                     (let [not-a-predicate (fn [x] (+ x 1))]
                       (if (not-a-predicate 3) 1 0)))")))))

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

(deftest vector-returning-closures-lower-reproducibly-for-js-and-wasm
  (let [source "(defn main []
                  (let [singleton (fn [x] [x])]
                    (vector-at (singleton 42) 0)))"
        js (compiler/compile-source source :js-kotoba-v1)
        wasm-a (compiler/compile-source source :wasm32-browser-kotoba-v1)
        wasm-b (compiler/compile-source source :wasm32-browser-kotoba-v1)]
    (is (= 42 (kir/execute (:kir js) 'main [])))
    (is (= (:kir wasm-a) (:kir wasm-b)))
    (is (java.util.Arrays/equals ^bytes (:bytes wasm-a) ^bytes (:bytes wasm-b)))))

(deftest string-returning-closures-lower-reproducibly-for-js-and-wasm
  (let [source "(defn main []
                  (let [render (fn [x] (string-from-i64 x))]
                    (string-length (render 42))))"
        js (compiler/compile-source source :js-kotoba-v1)
        wasm-a (compiler/compile-source source :wasm32-browser-kotoba-v1)
        wasm-b (compiler/compile-source source :wasm32-browser-kotoba-v1)]
    (is (= 2 (kir/execute (:kir js) 'main [])))
    (is (= (:kir wasm-a) (:kir wasm-b)))
    (is (java.util.Arrays/equals ^bytes (:bytes wasm-a) ^bytes (:bytes wasm-b)))))
