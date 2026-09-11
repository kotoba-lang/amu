(ns kotoba.compiler.pure-product-profile-test
  "T2.1 / T2.3: pure-product language-profile admission + PVA golden on KIR."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.diagnostic :as diagnostic]
            [kotoba.sema :as sema]
            [kotoba.kir :as kir]))

(def claim-sub-src
  ";; Product Value ABI v1 golden (mirrors kotoba-lang examples/product-value-abi-v1/claim_sub.kotoba)
(ns claim-sub-demo
  (:export [claim-sub claim-exp i64-label]))

(defn claim-sub [sub [:option :string]] :string
  (if-some [x sub]
    x
    \"anonymous\"))

(defn claim-exp [now :i64 ttl [:option :i64]] :i64
  (+ now (if-some [x ttl] x 2592000)))

(defn i64-label [n :i64] :string
  (string-concat \"n=\" (string-from-i64 n)))")

(defn- analyze-error [source opts]
  (try
    (sema/analyze source opts)
    nil
    (catch clojure.lang.ExceptionInfo e
      e)))

(deftest pure-product-admits-pva-golden
  (let [hir (sema/analyze claim-sub-src {:language-profile :pure-product})]
    (is (= :pure-product (:language-profile hir)))
    (is (empty? (:effects hir)))
    (is (some #{'claim-sub} (:exports hir)))))

(deftest pure-product-rejects-capabilities-clause
  (let [e (analyze-error
           "(ns t (:export [f]) (:capabilities #{:clock/now}))
(defn f [] 1)"
           {:language-profile :pure-product})]
    (is (some? e))
    (is (= :kotoba.error/pure-product-capabilities
           (:kotoba.error/code (ex-data e))))
    (is (re-find #"pure-product" (ex-message e)))))

(deftest pure-product-rejects-cap-call
  (let [e (analyze-error
           "(ns t (:export [f]))
(defn f [] (cap-call :clock/now))"
           {:language-profile :pure-product})]
    (is (some? e))
    (is (= :kotoba.error/pure-product-forbidden
           (:kotoba.error/code (ex-data e))))
    (is (re-find #"cap-call" (ex-message e)))))

(deftest pure-product-rejects-doseq-sugar
  (let [e (analyze-error
           "(ns t (:export [f]))
(defn f [] (doseq [x [1 2]] x) 0)"
           {:language-profile :pure-product})]
    (is (some? e))
    (is (= :kotoba.error/pure-product-forbidden
           (:kotoba.error/code (ex-data e))))))

(deftest pure-product-default-profile-still-allows-doseq-shape-or-rejects-normally
  ;; Without pure-product, doseq is not auto-forbidden by this profile gate
  ;; (may still fail other admission). Just ensure analyze without profile
  ;; does not emit pure-product-forbidden for a simple pure program.
  (let [hir (sema/analyze
             "(ns t (:export [f]))
(defn f [x :i64] :i64 (+ x 1))")]
    (is (nil? (:language-profile hir)))
    (is (empty? (:effects hir)))))

(deftest pure-product-compile-and-kir-execute-golden
  (testing "T2.3 living contract: compile with pure-product + KIR exec"
    (let [r (compiler/compile-source claim-sub-src :wasm32-kotoba-v1 {}
                                     {:language-profile :pure-product})]
      (is (map? (:kir r)))
      (is (= "anonymous"
             (kir/execute (:kir r) 'claim-sub [[[:option :string] false]])))
      (is (= "bob"
             (kir/execute (:kir r) 'claim-sub [[[:option :string] true "bob"]])))
      (is (= 2592100
             (kir/execute (:kir r) 'claim-exp [100 [[:option :i64] false]])))
      (is (= "n=-7"
             (kir/execute (:kir r) 'i64-label [-7]))))))

(deftest error-code-and-diagnostic-v1
  (testing "T3.1: reject sites carry stable codes; diagnostic preserves them"
    (let [e (analyze-error
             "(ns t (:export [f]) (:capabilities #{:clock/now}))
(defn f [] 1)"
             {:language-profile :pure-product})
          d (diagnostic/from-error e "claim.kotoba")]
      (is (= :kotoba.diagnostic/v1 (:format d)))
      (is (= :kotoba.error/pure-product-capabilities (:code d)))
      (is (= "claim.kotoba" (:source d)))
      (is (re-find #"pure-product" (ex-message e)))))
  (testing "migrated value-type reject carries specific code"
    (let [e (analyze-error
             "(ns t (:export [f]))
(defn f [x :not-a-real-type] :i64 x)"
             nil)]
      (when e
        (let [code (:kotoba.error/code (ex-data e))]
          (is (keyword? code))
          (is (= "kotoba.error" (namespace code))))))))
