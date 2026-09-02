(ns kotoba.compiler.ambient-negative-corpus-test
  "T2.4: always-on security regression — ambient / forbidden forms reject.

  Complements kotoba-lang `docs/grade-a-malicious-source-corpus.md` and
  `lang/malicious-source/*` (policy evaluator corpus). This suite pins the
  **compiler frontend** gate for the same security classes on guest source."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.sema :as sema]))

(defn- analyze-error
  ([source] (analyze-error source nil))
  ([source opts]
   (try
     (sema/analyze source opts)
     nil
     (catch clojure.lang.ExceptionInfo e
       e))))

(def ambient-cases
  "Stable table: [id source expected-code-or-nil]."
  [[:load-string
    "(ns t (:export [f])) (defn f [] (load-string \"(+ 1 2)\"))"
    :kotoba.error/ambient-forbidden]
   [:require
    "(ns t (:export [f])) (defn f [] (require 'foo))"
    :kotoba.error/ambient-forbidden]
   [:load
    "(ns t (:export [f])) (defn f [] (load \"x\"))"
    :kotoba.error/ambient-forbidden]
   [:atom
    "(ns t (:export [f])) (defn f [] (atom 1))"
    :kotoba.error/ambient-forbidden]
   [:future
    "(ns t (:export [f])) (defn f [] (future 1))"
    :kotoba.error/ambient-forbidden]
   [:new
    "(ns t (:export [f])) (defn f [] (new Object))"
    :kotoba.error/ambient-forbidden]
   [:dot-interop
    "(ns t (:export [f])) (defn f [] (.toString 1))"
    :kotoba.error/ambient-forbidden]
   [:set-bang
    "(ns t (:export [f])) (defn f [] (set! x 1))"
    :kotoba.error/ambient-forbidden]
   ;; `throw` left this corpus on 2026-09-02 (ADR 0294): kotoba-sema e42b74ef
   ;; admits it as the typed abort ability's sugar, and kotoba-lang 9336e582's
   ;; `lang/guest-grammar.edn` no longer lists `throw try catch` under
   ;; `:forbidden-heads`. Its own refusals -- unhandled at an export boundary,
   ;; two error types in one function, outside tail/let position -- are pinned
   ;; by exact text in kotoba-sema's abort_ability_test, and the export-boundary
   ;; one again in kotoba.compiler.effect-row-test on this side.
   [:resolve
    "(ns t (:export [f])) (defn f [] (resolve 'x))"
    :kotoba.error/ambient-forbidden]
   [:binding
    "(ns t (:export [f])) (defn f [] (binding [x 1] x))"
    :kotoba.error/ambient-forbidden]
   [:defmacro-top
    "(ns t (:export [f])) (defmacro m [] 1) (defn f [] 1)"
    :kotoba.error/top-level-form]
   [:ns-import-clause
    "(ns t (:import [java.lang String]) (:export [f])) (defn f [] 1)"
    :kotoba.error/namespace-export-clause]
   [:max-parameters-6
    "(ns t (:export [f])) (defn f [a b c d e g] :i64 0)"
    :kotoba.error/max-parameters]])

(deftest ambient-and-forbidden-forms-always-reject
  (doseq [[id source expected-code] ambient-cases]
    (testing (str id)
      (let [e (analyze-error source)]
        (is (some? e) (str id " should reject"))
        (when expected-code
          (is (= expected-code (:kotoba.error/code (ex-data e)))
              (str id " code " (pr-str (ex-data e)))))))))

(deftest pure-product-rejects-typed-eval-effects
  (testing "typed eval remains unavailable to the pure-product profile"
    (let [e (analyze-error
             "(ns t (:export [f])) (defn f [request :document] :i64 (eval request))"
             {:language-profile :pure-product})
          code (:kotoba.error/code (ex-data e))]
      (is (some? e))
      (is (= :kotoba.error/pure-product-effects code) (str "got " code)))))

(deftest pure-product-rejects-cap-call-and-doseq
  ;; Cross-link T2.1 living gate — must stay red under pure-product.
  (let [e1 (analyze-error
            "(ns t (:export [f])) (defn f [] (cap-call :clock/now))"
            {:language-profile :pure-product})
        e2 (analyze-error
            "(ns t (:export [f])) (defn f [] (doseq [x [1]] x) 0)"
            {:language-profile :pure-product})]
    (is (= :kotoba.error/pure-product-forbidden
           (:kotoba.error/code (ex-data e1))))
    (is (= :kotoba.error/pure-product-forbidden
           (:kotoba.error/code (ex-data e2))))))
