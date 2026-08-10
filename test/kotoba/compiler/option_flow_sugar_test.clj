(ns kotoba.compiler.option-flow-sugar-test
  "Type-directed Option fallback syntax: authors write `(option-or value
  fallback)` while every downstream stage keeps the existing explicit
  `option-value-of` representation."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.sema :as sema]
            [kotoba.kir :as ir]))

(defn- compile-kir [source]
  (:kir (compiler/compile-source source :wasm32-kotoba-v1 {}
                                 {:language-profile :pure-product})))

(defn- execute [source function args]
  (ir/execute (compile-kir source) function args {}))

(deftest infers-payloads-from-constructors-and-function-results
  (let [source
        "(ns option.flow (:export [some-i64 none-i64 some-string none-string]))
         (defn maybe-name [present :bool] [:option :string]
           (if present
             (option-some-of [:option :string] \"kotoba\")
             (option-none-of [:option :string])))
         (defn some-i64 [] :i64
           (option-or (option-some-of [:option :i64] 7) 99))
         (defn none-i64 [] :i64
           (option-or (option-none-of [:option :i64]) 99))
         (defn some-string [] :string (option-or (maybe-name true) \"guest\"))
         (defn none-string [] :string (option-or (maybe-name false) \"guest\"))"]
    (is (= 7 (execute source 'some-i64 [])))
    (is (= 99 (execute source 'none-i64 [])))
    (is (= "kotoba" (execute source 'some-string [])))
    (is (= "guest" (execute source 'none-string [])))))

(deftest infers-document-and-let-local-option-types
  (let [source
        "(ns option.document (:export [field text]))
         (defn field [d :document] :document
           (option-or (document-get d :name) (document-null)))
         (defn text [d :document]
           (let [name (document-string-value (field d))]
             (option-or name \"anonymous\")))"]
    (is (= "kotoba"
           (execute source 'text [["map" [[:name ["string" "kotoba"]]]]])))
    (is (= "anonymous" (execute source 'text [["map" []]])))))

(deftest elaborates-to-the-existing-low-level-option-form
  (let [source
        "(ns option.shape (:export [choose]))
         (defn choose [value [:option :string]] :string
           (option-or value \"fallback\"))"
        hir (sema/analyze source {:language-profile :pure-product})
        body (:body (first (:functions hir)))]
    (is (= 'option-value-of (first body)))
    (is (= [:option :string] (second body)))
    (is (not-any? #{'option-or} (tree-seq coll? seq body)))))

(deftest infers-an-unannotated-result-after-rewrite
  (let [source
        "(ns option.inferred (:export [choose]))
         (defn choose [value [:option :string]]
           (option-or value \"fallback\"))"]
    (is (= "fallback"
           (execute source 'choose [[[:option :string] false]])))))

(deftest threads-lowered-pattern-binders-into-option-inference
  (let [source
        "(ns option.branch (:export [lookup]))
         (def map-type [:map :i64 :bool])
         (def entry-type [:vector [:i64 :bool]])
         (defn lookup [values [:alias map-type]] :bool
           (match-option (typed-map-entry-at map-type values 0)
             [:option entry-type]
             (none false)
             (some entry
               (let [key (hetero-vector-at entry-type entry 0)]
                 (option-or (typed-map-get map-type values key) false)))))"
        hir (sema/analyze source {:language-profile :pure-product})
        body (:body (first (:functions hir)))]
    (is (not-any? #{'option-or} (tree-seq coll? seq body)))
    (is (some #{'option-value-of} (tree-seq coll? seq body)))))

(deftest threads-result-and-variant-payload-binders-too
  (doseq [source
          ["(ns option.result-branch (:export [choose]))
            (def result-type [:result [:option :i64] :string])
            (defn choose [value [:alias result-type]] :i64
              (match-result value result-type
                (ok payload (option-or payload 0))
                (err message 0)))"
           "(ns option.variant-branch (:export [choose]))
            (def variant-type
              [:variant :option/branch
               [[:present [:option :i64]] [:absent :bool]]])
            (defn choose [value [:alias variant-type]] :i64
              (match-variant value variant-type
                (:present payload (option-or payload 0))
                (:absent ignored 0)))"]]
    (let [hir (sema/analyze source {:language-profile :pure-product})
          body (:body (first (:functions hir)))]
      (is (not-any? #{'option-or} (tree-seq coll? seq body)))
      (is (some #{'option-value-of} (tree-seq coll? seq body))))))

(deftest rejects-non-options-and-payload-mismatches
  (testing "the type-directed surface fails closed before lowering"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"option-or requires an option value"
         (sema/analyze
          "(ns bad (:export [f])) (defn f [x :i64] :i64 (option-or x 0))"))))
  (testing "the existing type checker still owns fallback compatibility"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"expression type mismatch"
         (sema/analyze
          "(ns bad (:export [f]))
           (defn f [x [:option :string]] :string (option-or x 0))")))))
