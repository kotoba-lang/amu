(ns kotoba.compiler.aggregate-abi-test
  (:require [clojure.edn :as edn]
            [clojure.test :refer [deftest is]]
            [kotoba.native.aggregate-abi :as aggregate-abi]
            [kotoba.native.machine-ir :as machine]))

(defn- dependency-pin [coordinate]
  (get-in (edn/read-string (slurp "deps.edn")) [:deps coordinate :git/sha]))

(deftest pinned-closure-carries-the-held-aggregate-boundary
  (is (= "ceca09377c53a33c4ea8bcf4a3f2e49f32cdf83d"
         (dependency-pin 'io.github.kotoba-lang/kotoba-native)))
  (is (= "2b0d715febeb109710f09c279d66a7d10272de96"
         (dependency-pin 'io.github.kotoba-lang/kotoba-verifier)))
  (is (= 1 (:abi/version aggregate-abi/contract)))
  (is (= :held (get-in aggregate-abi/contract
                        [:extracted :record-boundary])))
  (is (= :held (get-in aggregate-abi/contract
                        [:extracted :variant-boundary])))
  (is (= :held (get-in aggregate-abi/contract
                        [:extracted :call-admission])))
  (is (= :all-allocator-registers
         (get-in aggregate-abi/contract
                 [:targets :x86-64 :call-clobbers])))
  (is (= :all-allocator-registers
         (get-in aggregate-abi/contract
                 [:targets :aarch64 :call-clobbers]))))

(deftest amu-does-not-route-call-shaped-kir-into-extracted-gmir
  (is (not (machine/pilot-expression? ['x] '(callee x))))
  (try
    (machine/lower-kir-expression ['x] '(callee x))
    (is false "call-shaped KIR must remain on the established emitter")
    (catch clojure.lang.ExceptionInfo error
      (is (= :aggregate-abi (:phase (ex-data error))))
      (is (= :call-abi-not-admitted (:problem (ex-data error)))))))
