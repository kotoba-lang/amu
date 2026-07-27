(ns kotoba.compiler.w1-elaboration-test
  "W1 frontend elaboration: friendly named operations, transitive effects,
  effect ceilings, and source-span diagnostics (ADR-2607279200)."
  (:require [clojure.java.io :as io]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.frontend :as frontend]))

(defn- slurp-example [name]
  (slurp (io/file "examples" name)))

(deftest pure-representative-compiles-without-new-special-forms
  (let [source (slurp-example "w1-pure.kotoba")
        hir (frontend/analyze source)
        checked (compiler/check-source source {})]
    (is (= 'main (:entry hir)))
    (is (= #{} (:effects hir)))
    (is (= #{} (:named-operations hir)))
    (is (empty? (:missing (:admission checked))))
    (is (not (re-find #"cap-call|typed-cap-call|defapp|defservice" source)))
    (is (= '(+ n n)
           (some #(when (= 'double (:name %)) (:body %)) (:functions hir))))))

(deftest friendly-named-operation-elaborates-without-numeric-ids
  (let [source (slurp-example "w1-effect-named.kotoba")
        hir (frontend/analyze source)
        main-body (some #(when (= 'main (:name %)) (:body %)) (:functions hir))
        read-body (some #(when (= 'read-clock (:name %)) (:body %)) (:functions hir))
        checked (compiler/check-source source {:allow #{[:cap/call 7]}})]
    (testing "source uses friendly namespaced ops, not cap-call syntax"
      (is (not (re-find #"\((cap-call|typed-cap-call)\b" source)))
      (is (re-find #"\(clock/now\b" source)))
    (testing "elaboration yields typed cap-call + inferred effect + named op"
      (is (= #{:clock/now} (:named-operations hir)))
      (is (= #{[:cap/call 7]} (:effects hir)))
      (is (= '(typed-cap-call 7 :i64 :i64 seed) read-body))
      (is (= :clock/now (:source-operation (meta read-body))))
      (is (map? (:span (meta read-body))))
      (is (integer? (get-in (meta read-body) [:span :line]))))
    (testing "transitive effects through the call graph"
      (is (= #{[:cap/call 7]}
             (some #(when (= 'main (:name %)) (:effects %)) (:functions hir))))
      (is (= '(read-clock 42) main-body)))
    (testing "policy admission accepts the inferred effect"
      (is (true? (get-in checked [:admission :admitted?])))
      (is (= #{[:cap/call 7]} (get-in checked [:admission :required]))))))

(deftest effect-ceiling-violation-names-operation-and-span
  (let [source (slurp-example "w1-denial-ceiling.kotoba")
        data (try
               (frontend/analyze source)
               nil
               (catch clojure.lang.ExceptionInfo e
                 (ex-data e)))
        msg (try
              (frontend/analyze source)
              nil
              (catch clojure.lang.ExceptionInfo e
                (ex-message e)))]
    (is (re-find #"inferred effects exceed declared effect ceiling" (str msg)))
    (is (re-find #"guarded" (str msg)))
    (is (= :effect-ceiling (:phase data)))
    (is (= 'guarded (:function data)))
    (is (= #{:log/append} (:operations data)))
    (is (map? (:span data)))
    (is (integer? (:line (:span data))))
    (is (integer? (:column (:span data))))))

(deftest undeclared-named-operation-fails-closed-with-operation-name
  (let [source "(ns app (:capabilities #{:log/append}))\n(defn main [] (clock/now 7))"
        e (try
            (frontend/analyze source)
            nil
            (catch clojure.lang.ExceptionInfo ex ex))]
    (is (some? e))
    (is (re-find #"capability not declared in namespace :capabilities" (ex-message e)))
    (is (re-find #":clock/now" (ex-message e)))
    (is (= :subset (:phase (ex-data e))))))

(deftest policy-denial-includes-named-operations
  (let [source (slurp-example "w1-effect-named.kotoba")
        e (try
            (compiler/check-source source {:allow #{}})
            nil
            (catch clojure.lang.ExceptionInfo ex ex))]
    (is (some? e))
    (is (re-find #"capability policy denies required effects" (ex-message e)))
    (is (= #{:clock/now} (:operations (ex-data e))))
    (is (= #{[:cap/call 7]} (:missing (ex-data e))))))

(deftest arity-and-unknown-named-op-diagnostics-carry-span-and-operation
  (testing "arity mismatch keeps source operation and span"
    (let [e (try
              (frontend/analyze
               "(ns app (:capabilities #{:clock/now}))\n(defn main []\n  (clock/now 1 2))")
              nil
              (catch clojure.lang.ExceptionInfo ex ex))]
      (is (re-find #"named operation" (ex-message e)))
      (is (= :clock/now (:operation (ex-data e))))
      (is (integer? (get-in (ex-data e) [:span :line])))))
  (testing "unknown namespaced head is fail-closed"
    (let [e (try
              (frontend/analyze "(defn main [] (not/a-capability 1))")
              nil
              (catch clojure.lang.ExceptionInfo ex ex))]
      (is (re-find #"not a registered capability" (ex-message e)))
      (is (= :subset (:phase (ex-data e)))))))

(deftest legacy-keyword-cap-call-still-elaborates
  (let [hir (frontend/analyze
             "(ns app (:capabilities #{:clock/now}))\n(defn main [] (cap-call :clock/now 7))")]
    (is (= #{[:cap/call 7]} (:effects hir)))
    (is (= #{:clock/now} (:named-operations hir)))
    (is (= :clock/now
           (:source-operation (meta (get-in hir [:functions 0 :body])))))))
