(ns kotoba.compiler.record-projection-sugar-test
  "`(record-get value :field)` — the schema is recovered from the value's
  inferred type and rewritten to the canonical 3-arity form before validation,
  so lowering and the backends are untouched."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]))

(def ^:private S
  "[:record :r/lanes [[:text :i64] [:media :i64] [:postproc :i64]]]")

(defn- run [src fn-sym args]
  (let [c (compiler/compile-source src :wasm32-kotoba-v1 {}
                                   {:language-profile :pure-product})]
    (ir/execute (:kir c) fn-sym (vec args) {})))

(defn- rejection [src]
  (try
    (compiler/compile-source src :wasm32-kotoba-v1 {}
                             {:language-profile :pure-product})
    nil
    (catch clojure.lang.ExceptionInfo e
      {:code (:kotoba.error/code (ex-data e)) :message (.getMessage e)})))

(deftest projects-a-let-bound-record
  (is (= 5 (run (str "(ns p)\n(defn go [t :i64 m :i64 p :i64] :i64\n"
                     "  (let [r (record-new " S " t m p)] (record-get r :media)))\n"
                     "(defn main [] :i64 0)")
                'go [4 5 6]))))

(deftest projects-a-record-parameter
  (is (= 6 (run (str "(ns p)\n(defn pick [r " S "] :i64 (record-get r :postproc))\n"
                     "(defn go [t :i64 m :i64 p :i64] :i64 (pick (record-new " S " t m p)))\n"
                     "(defn main [] :i64 0)")
                'go [4 5 6]))))

(deftest projects-a-call-result-directly
  (is (= 4 (run (str "(ns p)\n(defn mk [t :i64 m :i64 p :i64] " S " (record-new " S " t m p))\n"
                     "(defn go [t :i64 m :i64 p :i64] :i64 (record-get (mk t m p) :text))\n"
                     "(defn main [] :i64 0)")
                'go [4 5 6]))))

(deftest projects-repeatedly-inside-an-expression
  (is (= 15 (run (str "(ns p)\n(defn go [t :i64 m :i64 p :i64] :i64\n"
                      "  (let [r (record-new " S " t m p)]\n"
                      "    (+ (record-get r :text)\n"
                      "       (+ (record-get r :media) (record-get r :postproc)))))\n"
                      "(defn main [] :i64 0)")
                 'go [4 5 6]))))

(deftest three-arity-is-unchanged
  (testing "the canonical form still compiles and still means the same thing"
    (is (= 5 (run (str "(ns p)\n(defn go [t :i64 m :i64 p :i64] :i64\n"
                       "  (record-get " S " (record-new " S " t m p) :media))\n"
                       "(defn main [] :i64 0)")
                  'go [4 5 6])))))

(deftest fails-closed-on-a-non-record-value
  (let [r (rejection "(ns p)\n(defn go [x :i64] :i64 (record-get x :text))\n(defn main [] :i64 0)")]
    (is (= :kotoba.error/record-projection-unresolved (:code r)))
    (is (re-find #"requires a record value" (:message r)))))

(deftest fails-closed-on-a-wrong-arity
  (let [r (rejection "(ns p)\n(defn go [x :i64] :i64 (record-get x))\n(defn main [] :i64 0)")]
    (is (re-find #"record-get requires" (:message r)))))

(deftest fails-closed-on-an-undeclared-field
  (testing "the rewrite supplies the schema; field validation is unchanged"
    (let [r (rejection (str "(ns p)\n(defn go [t :i64 m :i64 p :i64] :i64\n"
                            "  (let [r (record-new " S " t m p)] (record-get r :nope)))\n"
                            "(defn main [] :i64 0)"))]
      (is (some? r))
      (is (re-find #"declared keyword literal" (:message r))))))
