(ns kotoba.compiler.callable-values-test
  (:require [clojure.test :refer [deftest is testing]]
            [clojure.java.shell :as shell]
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
  (is (= 1 (execute-main
            "(defn main []
               (document-count
                (invoke :document (fn [x] (document-vector (document-i64 x))) 42)))")))
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
                     (string-length (invoke :string (fn [x] (+ x 1)) 3)))"))))
  (testing "a document dispatcher rejects a scalar-returning closure"
    (is (thrown? clojure.lang.ExceptionInfo
                 (execute-main
                  "(defn main []
                     (document-count (invoke :document (fn [x] (+ x 1)) 3)))")))))

(deftest lexical-document-results-use-contextual-application-syntax
  (is (= 1 (execute-main
            "(defn main []
               (let [build (fn [x] (document-vector (document-i64 x)))]
                 (document-count (build 42))))")))
  (is (= 1 (execute-main
            "(defn build-with [f] :document
               (let [n 42] (if (> n 0) (f n) (document-null))))
             (defn main []
               (document-count
                (build-with (fn [x] (document-vector (document-i64 x))))))")))
  (is (= 2 (execute-main
            "(defn main []
               (let [build (fn [x] (document-i64 x))]
                 (document-count (document-vector (build 1) (build 2)))))")))
  (is (= 1 (execute-main
            "(defn build [x :i64] :document
               (document-vector (document-i64 x)))
             (defn main []
               (document-count (invoke :document (fn-ref build) 42)))"))))

(deftest descriptor-keyed-record-results-use-contextual-application-syntax
  (let [point "[:record :demo/point [[:x :i64] [:label :string]]]"
        other "[:record :demo/other [[:x :i64] [:label :string]]]"]
    (is (= 7 (execute-main
              (str "(defn main []
                      (let [make (fn [x] (record-new " point " x \"point\"))]
                        (record-get " point " (make 7) :x)))"))))
    (is (= 8 (execute-main
              (str "(defn main []
                      (record-get " point "
                        (invoke " point "
                          (fn [x] (record-new " point " x \"point\")) 8)
                        :x))"))))
    (is (= 9 (execute-main
              (str "(ns demo (:schemas {:demo/point " point "}))
                    (defn call-maker [f] [:ref :demo/point]
                      (let [n 9] (f n)))
                    (defn main []
                      (record-get [:ref :demo/point]
                        (call-maker
                          (fn [x] (record-new [:ref :demo/point] x \"point\")))
                        :x))"))))
    (is (= 10 (execute-main
               (str "(defn make [x :i64] " point "
                       (record-new " point " x \"point\"))
                     (defn main []
                       (record-get " point "
                         (invoke " point " (fn-ref make) 10) :x))"))))
    (testing "nominally distinct record dispatchers do not share candidates"
      (is (thrown? clojure.lang.ExceptionInfo
                   (execute-main
                    (str "(defn main []
                            (record-get " other "
                              (invoke " other "
                                (fn [x] (record-new " point " x \"point\")) 3)
                              :x))")))))))

(deftest descriptor-keyed-option-and-result-results-use-contextual-application-syntax
  (let [option-string "[:option :string]"
        option-i64 "[:option :i64]"
        result-type "[:result :string :i64]"]
    (is (= 2 (execute-main
              (str "(defn main []
                      (let [render (fn [x]
                                     (option-some-of " option-string "
                                       (string-from-i64 x)))]
                        (string-length
                          (option-value-of " option-string " (render 42) \"\"))))"))))
    (is (= 3 (execute-main
              (str "(defn render-with [f] " option-string "
                       (let [n 123] (if (> n 0) (f n)
                                     (option-none-of " option-string "))))
                    (defn main []
                      (string-length
                        (option-value-of " option-string "
                          (render-with
                            (fn [x] (option-some-of " option-string "
                                      (string-from-i64 x))))
                          \"\")))"))))
    (is (= 2 (execute-main
              (str "(defn main []
                      (let [render (fn [x]
                                     (result-ok-of " result-type "
                                       (string-from-i64 x)))]
                        (string-length
                          (result-value-of " result-type " (render 42) \"\"))))"))))
    (is (= 3 (execute-main
              (str "(defn render-with [f] " result-type "
                       (let [ignored 0] (f 123)))
                    (defn main []
                      (string-length
                        (result-value-of " result-type "
                          (render-with
                            (fn [x] (result-ok-of " result-type "
                                      (string-from-i64 x))))
                          \"\")))"))))
    (is (= 2 (execute-main
              (str "(defn main []
                      (string-length
                        (option-value-of " option-string "
                          (invoke " option-string "
                            (fn [x] (option-some-of " option-string "
                                      (string-from-i64 x))) 42)
                          \"\")))"))))
    (testing "parameterized option dispatchers remain descriptor-specific"
      (is (thrown? clojure.lang.ExceptionInfo
                   (execute-main
                    (str "(defn main []
                            (option-value-of " option-i64 "
                              (invoke " option-i64 "
                                (fn [x] (option-some-of " option-string "
                                          (string-from-i64 x))) 3)
                              0))")))))))

(deftest descriptor-keyed-collection-and-variant-results-use-contextual-application-syntax
  (let [variant-type "[:variant :demo/reply [[:ok :i64] [:label :string]]]"
        vector-type "[:vector [:i64 :string]]"
        set-type "[:set :i64]"
        map-type "[:map :keyword :string]"]
    (is (= 7 (execute-main
              (str "(defn main []
                      (let [make (fn [x]
                                   (variant-new " variant-type " :ok x))]
                        (match-variant (make 7) " variant-type "
                          (:ok value value)
                          (:label text 0))))"))))
    (is (= 8 (execute-main
              (str "(ns demo (:schemas {:demo/reply " variant-type "}))
                    (defn main []
                      (let [make (fn [x]
                                   (variant-new [:ref :demo/reply] :ok x))]
                        (match-variant (make 8) [:ref :demo/reply]
                          (:ok value value)
                          (:label text 0))))"))))
    (is (= 7 (execute-main
              (str "(defn main []
                      (let [make (fn [x]
                                   (hetero-vector-new " vector-type " x \"ok\"))]
                        (hetero-vector-at " vector-type " (make 7) 0)))"))))
    (is (= 1 (execute-main
              (str "(defn main []
                      (let [make (fn [x] (typed-set-new " set-type " x))]
                        (typed-set-count " set-type " (make 7))))"))))
    (is (= 1 (execute-main
              (str "(defn main []
                      (typed-set-count " set-type "
                        (invoke " set-type "
                          (fn [x] (typed-set-new " set-type " x)) 7)))"))))
    (is (= 2 (execute-main
              (str "(defn main []
                      (let [render (fn [x] (string-from-i64 x))
                            make (fn [x]
                                   (typed-map-new " map-type "
                                     :value (render x)))]
                        (string-length
                          (option-value-of [:option :string]
                            (typed-map-get " map-type " (make 42) :value)
                            \"\"))))"))))
    (testing "a variant dispatcher traps before returning its typed default"
      (is (thrown? clojure.lang.ExceptionInfo
                   (execute-main
                    (str "(defn main []
                            (match-variant
                              (invoke " variant-type " (fn [x] (+ x 1)) 3)
                              " variant-type "
                              (:ok value value)
                              (:label text 0)))")))))
    (testing "descriptor-distinct typed collections do not share candidates"
      (is (thrown? clojure.lang.ExceptionInfo
                   (execute-main
                    "(defn main []
                       (typed-set-count [:set :string]
                         (invoke [:set :string]
                           (fn [x] (typed-set-new [:set :i64] x)) 3)))"))))))

(deftest descriptor-keyed-collection-closures-lower-reproducibly-for-js-and-wasm
  (let [source "(defn main []
                  (let [make (fn [x]
                               (typed-map-new [:map :keyword :string]
                                 :value (string-from-i64 x)))]
                    (string-length
                      (option-value-of [:option :string]
                        (typed-map-get [:map :keyword :string]
                          (make 42) :value)
                        \"\"))))"
        js (compiler/compile-source source :js-kotoba-v1)
        wasm-a (compiler/compile-source source :wasm32-browser-kotoba-v1)
        wasm-b (compiler/compile-source source :wasm32-browser-kotoba-v1)
        module (java.io.File/createTempFile "kotoba-structured-closure-" ".mjs")
        probe (try
                (spit module
                      (str (:source js)
                           "\nconst x=instantiateKotoba({});"
                           "if(x.main()!==2n)process.exit(2);"))
                (shell/sh "node" (.getPath module))
                (finally (.delete module)))]
    (is (= 2 (kir/execute (:kir js) 'main [])))
    (is (zero? (:exit probe)) (:err probe))
    (is (= (:kir wasm-a) (:kir wasm-b)))
    (is (java.util.Arrays/equals ^bytes (:bytes wasm-a) ^bytes (:bytes wasm-b)))))

(deftest numeric-closure-results-use-contextual-application-syntax
  (let [one-f64-bits 4607182418800017408
        two-f64-bits 4611686018427387904
        one-f32-bits 1065353216]
    (is (= two-f64-bits
           (execute-main
            (str "(defn main []
                    (let [decode (fn [bits] (f64-from-bits bits))]
                      (f64-to-bits (f64-add (decode " one-f64-bits ")
                                            (decode " one-f64-bits ")))))"))))
    (is (= one-f32-bits
           (execute-main
            (str "(defn main []
                    (let [decode (fn [bits] (f32-from-bits bits))]
                      (f32-to-bits (f32-abs (decode " one-f32-bits ")))))"))))
    (is (= two-f64-bits
           (execute-main
            (str "(defn main []
                    (let [singleton (fn [bits]
                                      (vector-f64-new (f64-from-bits bits)))]
                      (f64-to-bits
                        (vector-f64-at (singleton " two-f64-bits ") 0))))"))))
    (is (= one-f64-bits
           (execute-main
            (str "(defn main []
                    (f64-to-bits
                      (invoke :f64 (fn [bits] (f64-from-bits bits))
                        " one-f64-bits ")))"))))
    (testing "numeric result dispatch remains family-specific"
      (is (thrown? clojure.lang.ExceptionInfo
                   (execute-main
                    (str "(defn main []
                            (f64-to-bits
                              (invoke :f64
                                (fn [bits] (f32-from-bits bits))
                                " one-f32-bits ")))")))))))

(deftest numeric-closure-results-lower-reproducibly-for-js-and-wasm
  (let [source "(defn main []
                  (let [singleton (fn [bits]
                                    (vector-f64-new (f64-from-bits bits)))]
                    (f64-to-bits
                      (vector-f64-at
                        (singleton 4607182418800017408) 0))))"
        js (compiler/compile-source source :js-kotoba-v1)
        wasm-a (compiler/compile-source source :wasm32-browser-kotoba-v1)
        wasm-b (compiler/compile-source source :wasm32-browser-kotoba-v1)
        module (java.io.File/createTempFile "kotoba-numeric-closure-" ".mjs")
        probe (try
                (spit module
                      (str (:source js)
                           "\nconst x=instantiateKotoba({});"
                           "if(x.main()!==4607182418800017408n)process.exit(2);"))
                (shell/sh "node" (.getPath module))
                (finally (.delete module)))]
    (is (= 4607182418800017408 (kir/execute (:kir js) 'main [])))
    (is (zero? (:exit probe)) (:err probe))
    (is (= (:kir wasm-a) (:kir wasm-b)))
    (is (java.util.Arrays/equals ^bytes (:bytes wasm-a) ^bytes (:bytes wasm-b)))))

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

(deftest document-returning-closures-lower-reproducibly-for-js-and-wasm
  (let [source "(defn main []
                  (let [build (fn [x] (document-vector (document-i64 x)))]
                    (document-count (build 42))))"
        js (compiler/compile-source source :js-kotoba-v1)
        wasm-a (compiler/compile-source source :wasm32-browser-kotoba-v1)
        wasm-b (compiler/compile-source source :wasm32-browser-kotoba-v1)]
    (is (= 1 (kir/execute (:kir js) 'main [])))
    (is (= (:kir wasm-a) (:kir wasm-b)))
    (is (java.util.Arrays/equals ^bytes (:bytes wasm-a) ^bytes (:bytes wasm-b)))))

(deftest descriptor-keyed-closures-lower-reproducibly-for-js-and-wasm
  (let [source "(defn main []
                  (let [make (fn [x]
                               (record-new
                                [:record :demo/point [[:x :i64] [:label :string]]]
                                x \"point\"))]
                    (record-get
                     [:record :demo/point [[:x :i64] [:label :string]]]
                     (make 42) :x)))"
        js (compiler/compile-source source :js-kotoba-v1)
        wasm-a (compiler/compile-source source :wasm32-browser-kotoba-v1)
        wasm-b (compiler/compile-source source :wasm32-browser-kotoba-v1)]
    (is (= 42 (kir/execute (:kir js) 'main [])))
    (is (= (:kir wasm-a) (:kir wasm-b)))
    (is (java.util.Arrays/equals ^bytes (:bytes wasm-a) ^bytes (:bytes wasm-b)))))
