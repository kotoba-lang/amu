(ns kotoba.compiler.error-code-contract-test
  "T3.1: explicit reject! codes + diagnostic preference over coarse phase codes."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.diagnostic :as diagnostic]
            [kotoba.compiler.frontend :as frontend]))

(defn- catch-analyze [source]
  (try
    (frontend/analyze source)
    nil
    (catch clojure.lang.ExceptionInfo e
      e)))

(deftest migrated-reject-sites-carry-specific-error-codes
  (testing "two namespaces"
    (let [e (catch-analyze
             "(ns a (:export [f])) (ns b (:export [g])) (defn f [] 1) (defn g [] 1)")]
      (is (some? e))
      (is (= :subset (:phase (ex-data e))))
      (is (= :kotoba.error/namespace-count
             (:kotoba.error/code (ex-data e))))))
  (testing "empty do"
    (let [e (catch-analyze
             "(ns t (:export [f])) (defn f [] (do))")]
      (is (some? e))
      (is (= :kotoba.error/do-empty
             (:kotoba.error/code (ex-data e))))))
  (testing "invalid ns symbol"
    (let [e (catch-analyze "(ns 123) (defn f [] 1)")]
      (is (some? e))
      (is (= :kotoba.error/namespace-symbol
             (:kotoba.error/code (ex-data e)))))))

(deftest diagnostic-prefers-specific-code-over-phase
  (let [e (catch-analyze
           "(ns a (:export [f])) (ns b (:export [g])) (defn f [] 1) (defn g [] 1)")
        d (diagnostic/from-error e "x.kotoba")]
    (is (= :kotoba.error/namespace-count (:code d)))
    (is (not= :kotoba/source-rejected (:code d)))
    (is (= "x.kotoba" (:source d)))
    (is (not (contains? d :message)))
    (is (not (contains? d :form)))))

(deftest diagnostic-falls-back-to-phase-code-without-specific
  (let [e (ex-info "rejected" {:phase :subset :limit 10})
        d (diagnostic/from-error e nil)]
    (is (= :kotoba/source-rejected (:code d)))
    (is (= :error (:severity d)))))
