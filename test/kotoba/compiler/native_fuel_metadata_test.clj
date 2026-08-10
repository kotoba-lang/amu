(ns kotoba.compiler.native-fuel-metadata-test
  (:require [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]))

(def ^:private deep-source
  ;; 512 shallow calls are the first flat witness beyond the target's default
  ;; budget. A recursive witness tests the JVM's platform-specific thread stack
  ;; before it reliably tests Kotoba fuel on Linux x86_64.
  (str "(defn tick [] :i64 0) (defn main [] :i64 (do "
       (str/join " " (concat (repeat 512 "(tick)") ["1"]))
       "))"))

(deftest declared-native-fuel-drives-sealed-abi-and-oracle
  (testing "the default verifier budget still rejects deeper pure execution"
    (try
      (compiler/compile-source deep-source :aarch64-kotoba-v1)
      (is false "default native fuel unexpectedly admitted the deep program")
      (catch clojure.lang.ExceptionInfo error
        (is (= "fuel-exhausted" (:cause (ex-data error)))))))
  (let [compiled (compiler/compile-source deep-source :aarch64-kotoba-v1
                                          {} {:fuel 1024})]
    (is (= 1 (get-in compiled [:artifact :value])))
    (is (= 1024 (get-in compiled [:artifact :limits :fuel])))
    (is (= {:mode :hidden-context-x7 :initial 1024}
           (get-in compiled [:artifact :fuel-abi])))))
