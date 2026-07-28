(ns kotoba.compiler.check-cli-test
  "T9.2 / T3.4: check-source pure-product + human diagnostics."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.diagnostic :as diagnostic]
            [kotoba.compiler.frontend :as frontend]))

(def pure-ok
  "(ns demo (:export [main]))\n(defn main [] :i64 (+ 1 2))\n")

(def pure-eval-bad
  "(ns demo (:export [main]))\n(defn main [] (eval 1))\n")

(def pure-caps-bad
  "(ns demo (:export [main]) (:capabilities #{:clock/now}))\n(defn main [] 0)\n")

(deftest check-source-default-admits-pure
  (let [r (compiler/check-source pure-ok)]
    (is (true? (get-in r [:admission :admitted?])))
    (is (nil? (:language-profile r)))
    (is (empty? (get-in r [:hir :effects])))))

(deftest check-source-pure-product-admits-pure
  (let [r (compiler/check-source pure-ok {:language-profile :pure-product})]
    (is (= :pure-product (:language-profile r)))
    (is (true? (get-in r [:admission :admitted?])))))

(deftest check-source-pure-product-rejects-eval
  (is (thrown-with-msg? clojure.lang.ExceptionInfo #"pure-product|eval|forbidden"
        (compiler/check-source pure-eval-bad {:language-profile :pure-product}))))

(deftest check-source-pure-product-rejects-capabilities
  (try
    (compiler/check-source pure-caps-bad {:language-profile :pure-product})
    (is false "expected reject")
    (catch clojure.lang.ExceptionInfo e
      (is (= :kotoba.error/pure-product-capabilities
             (:kotoba.error/code (ex-data e)))))))

(deftest format-human-includes-code-and-message
  (try
    (frontend/analyze pure-caps-bad {:language-profile :pure-product})
    (is false)
    (catch clojure.lang.ExceptionInfo e
      (let [s (diagnostic/format-human e "demo.kotoba")]
        (is (re-find #"error: pure-product-capabilities" s))
        (is (re-find #"demo\.kotoba" s))
        (is (re-find #"capabilities" s))))))
