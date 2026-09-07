(ns kotoba.compiler.native-fuel-metadata-test
  (:require [clojure.test :refer [deftest is testing]]
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

(deftest fuel-declared-twice-is-refused-unless-the-two-agree
  ;; amu-h6. `emit-metadata` `:fuel` (the CLI's `--fuel`) and the policy's
  ;; `[:budgets :fuel]` name the same budget. `declared-fuel` read them in
  ;; that order, so a disagreement was resolved silently in favour of the flag
  ;; and the policy author never learned their number was not the one sealed.
  (testing "different values are a usage error naming both"
    (try
      (compiler/compile-source deep-source :aarch64-kotoba-v1
                               {:budgets {:fuel 4096}} {:fuel 8192})
      (is false "two different fuel declarations were admitted")
      (catch clojure.lang.ExceptionInfo error
        (is (= {:phase :usage :reason :fuel-declared-twice :flag 8192 :policy 4096}
               (select-keys (ex-data error) [:phase :reason :flag :policy]))))))
  (testing "the same value twice is one declaration"
    (let [compiled (compiler/compile-source deep-source :aarch64-kotoba-v1
                                            {:budgets {:fuel 1024}} {:fuel 1024})]
      (is (= 1024 (get-in compiled [:artifact :limits :fuel])))
      (is (= {:mode :hidden-context-x7 :initial 1024}
             (get-in compiled [:artifact :fuel-abi])))))
  (testing "one declaration on either side is unchanged"
    (is (= 1024 (get-in (compiler/compile-source deep-source :aarch64-kotoba-v1
                                                 {:budgets {:fuel 1024}} {})
                        [:artifact :limits :fuel])))
    (is (= 1024 (get-in (compiler/compile-source deep-source :aarch64-kotoba-v1
                                                 {} {:fuel 1024})
                        [:artifact :limits :fuel])))))
