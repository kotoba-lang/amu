(ns kotoba.compiler.native-fuel-metadata-test
  (:require [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]))

(def ^:private deep-source
  "(defn spin [n :i64] :i64
     (if (= n 0) 1 (spin (- n 1))))
   ;; Two bounded descents exhaust the aggregate default fuel without making
   ;; the qualification depend on the host JVM's recursion-stack limit.
   (defn main [] :i64 (+ (spin 300) (spin 300)))")

(deftest declared-native-fuel-drives-sealed-abi-and-oracle
  (testing "the default verifier budget still rejects deeper pure execution"
    (try
      (compiler/compile-source deep-source :aarch64-kotoba-v1)
      (is false "default native fuel unexpectedly admitted the deep program")
      (catch clojure.lang.ExceptionInfo error
        (is (= "fuel-exhausted" (:cause (ex-data error)))))))
  (let [compiled (compiler/compile-source deep-source :aarch64-kotoba-v1
                                          {} {:fuel 1024})]
    (is (= 2 (get-in compiled [:artifact :value])))
    (is (= 1024 (get-in compiled [:artifact :limits :fuel])))
    (is (= {:mode :hidden-context-x7 :initial 1024}
           (get-in compiled [:artifact :fuel-abi])))))
