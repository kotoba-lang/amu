(ns kotoba.compiler.backend-evm-test
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.backend.evm :as evm]
            [kotoba.compiler.core :as compiler]))

(def valid-kir
  {:format :kotoba.kir/v3
   :entry 'main
   :exports ['main]
   :signature {:params [] :result :i64}
   :effects #{}
   :functions [{:name 'main
                :params []
                :result :i64
                :effects #{}
                :body '(+ 40 (* 1 2))}]})

(deftest checked-kir-emits-a-deployable-ethereum-artifact
  (let [artifact (evm/emit valid-kir)]
    (is (= :evm/v1 (:format artifact)))
    (is (= :evm256-kotoba-v1 (:target artifact)))
    (is (= [0xdf 0xfe 0xad 0xd0] (:selector artifact)))
    (is (= "int64" (get-in artifact [:abi 0 :outputs 0 :type])))
    (is (= [0x60 (count (:runtime-bytes artifact)) 0x60 0x0c]
           (subvec (:creation-bytes artifact) 0 4)))
    (is (= (:runtime-bytes artifact)
           (subvec (:creation-bytes artifact) 12)))
    (is (= artifact (evm/verify-artifact! artifact)))))

(deftest source-passes-through-sema-admission-and-checked-kir
  (let [source "(ns evm.answer) (defn main [] (+ 40 (* 1 2)))"
        result (compiler/compile-source source :evm256-kotoba-v1)]
    (is (= :evm/v1 (:format result)))
    (is (= :kotoba.kir/v3 (get-in result [:kir :format])))
    (is (= #{} (get-in result [:admission :required])))
    (is (seq (:creation-bytes result)))))

(deftest unsupported-kir-fails-closed
  (testing "unsupported arithmetic is not silently miscompiled"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo
         #"unsupported checked-KIR expression"
         (evm/emit (assoc-in valid-kir [:functions 0 :body] '(- 42 1))))))
  (testing "effects are rejected at the EVM boundary"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo
         #"one pure zero-arity main"
         (evm/emit (-> valid-kir
                       (assoc :effects #{[:cap/call 7]})
                       (assoc-in [:functions 0 :effects] #{[:cap/call 7]}))))))
  (testing "extra functions are rejected"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo
         #"one pure zero-arity main"
         (evm/emit (update valid-kir :functions conj
                           {:name 'helper :params [] :result :i64
                            :effects #{} :body 0}))))))

(deftest verifier-detects-bytecode-substitution
  (let [artifact (evm/emit valid-kir)
        tampered (update-in artifact [:runtime-bytes 0] bit-xor 1)]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo
         #"does not match checked-KIR re-emission"
         (evm/verify-artifact! tampered)))))
