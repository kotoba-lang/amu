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

(deftest lazy-map-supports-inline-named-and-stored-callbacks
  (is (= 12 (execute-main
             (str naturals-source
                  " (defn main []
                       (let [xs (take 3 (lazy-map (fn [x] (* x 2)) (naturals 1)))]
                         (+ (first xs)
                            (+ (first (rest xs))
                               (first (rest (rest xs)))))))"))))
  (is (= 10 (execute-main
            "(defn finite [n limit]
               (if (> n limit) 0 (lazy-cons n (finite (+ n 1) limit))))
             (defn add [a b] (+ a b))
             (defn main []
               (let [xs (take 2 (lazy-map add (finite 1 3) (finite 3 4)))]
                 (+ (first xs) (first (rest xs)))))")))
  (is (= 15 (execute-main
             (str naturals-source
                  " (defn main []
                       (let [offset 3 f (fn [x] (+ x offset))
                             xs (take 3 (lazy-map f (naturals 1)))]
                         (+ (first xs)
                            (+ (first (rest xs))
                               (first (rest (rest xs)))))))"))))
  (is (= 11 (execute-main
             "(defn one [x] (lazy-cons x 0))
              (defn main []
                (let [bias 1
                      add4 (fn [a b c d] (+ bias (+ a (+ b (+ c d)))))]
                  (lazy-first
                   (lazy-map add4 (one 1) (one 2) (one 3) (one 4)))))")))
  (is (= 1 (execute-main
            "(defn finite [n limit]
               (if (> n limit) 0 (lazy-cons n (finite (+ n 1) limit))))
             (defn add [a b] (+ a b))
             (defn main []
               (if (lazy-empty?
                    (drop 2 (lazy-map add (finite 1 3) (finite 3 4))))
                 1 0))")))
  (is (= 2 (execute-main
            "(defn transform [x] (+ x 100))
             (defn source [] (lazy-cons 1 0))
             (defn main []
               (let [transform (fn [x] (+ x 1))]
                 (lazy-first (lazy-map transform (source)))))"))))

(deftest lazy-filter-uses-bool-closures-and-terminates-on-rejection
  (is (= 12 (execute-main
             (str naturals-source
                  " (defn main []
                       (let [minimum 2 keep? (fn [x] (> x minimum))
                             xs (take 3 (lazy-filter keep? (naturals 1)))]
                         (+ (first xs)
                            (+ (first (rest xs))
                               (first (rest (rest xs)))))))"))))
  (is (= 1 (execute-main
            "(defn finite [n]
               (if (> n 3) 0 (lazy-cons n (finite (+ n 1)))))
             (defn main []
               (if (lazy-empty? (lazy-filter (fn [x] (> x 9)) (finite 0))) 1 0))")))
  (is (= 4 (execute-main
            "(defn keep? [x] false)
             (defn source [] (lazy-cons 4 0))
             (defn main []
               (let [keep? (fn [x] (> x 2))]
                 (lazy-first (lazy-filter keep? (source)))))"))))

(deftest lazy-hof-callback-effects-are-rejected
  (is (re-find #"must be effect-free"
               (rejection-message
                "(defn effectful [x] (cap-call 1 x))
                 (defn source [] (lazy-cons 1 0))
                 (defn main [] (lazy-map effectful (source)))"))))

(deftest lazy-core-lowers-reproducibly-to-wasm
  (let [source (str naturals-source
                    " (defn main [] (lazy-first (drop 4 (naturals 38))))")
        a (compiler/compile-source source :wasm32-browser-kotoba-v1)
        b (compiler/compile-source source :wasm32-browser-kotoba-v1)]
    (is (= 42 (kir/execute (:kir a) 'main [])))
    (is (java.util.Arrays/equals ^bytes (:bytes a) ^bytes (:bytes b)))))
