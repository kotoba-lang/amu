(ns kotoba.compiler.product-value-abi-v1-test
  "Product Value ABI v1: if-some on [:option :string], string-length, string-from-i64."
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as kir]))

(defn- exec [src export args]
  (let [r (compiler/compile-source src :wasm32-kotoba-v1 {})]
    (when-let [err (:error r)]
      (throw (ex-info "compile failed" {:error err :src src})))
    (kir/execute (:kir r) export args)))

(deftest if-some-on-option-string
  (let [src "(ns t (:export [claim-sub]))
(defn claim-sub [sub [:option :string]] :string
  (if-some [x sub] x \"anonymous\"))"]
    (is (= "anonymous"
           (exec src 'claim-sub [[[:option :string] false]])))
    (is (= "bob"
           (exec src 'claim-sub [[[:option :string] true "bob"]])))))

(deftest if-some-on-option-i64-ttl
  (let [src "(ns t (:export [claim-exp]))
(defn claim-exp [now :i64 ttl [:option :i64]] :i64
  (+ now (if-some [x ttl] x 2592000)))"]
    (is (= 2592100
           (exec src 'claim-exp [100 [[:option :i64] false]])))
    (is (= 110
           (exec src 'claim-exp [100 [[:option :i64] true 10]])))))

(deftest string-length-and-from-i64
  (is (= 5 (exec "(ns t (:export [f]))
(defn f [s :string] :i64 (string-length s))"
                 'f ["hello"])))
  (is (= "-42" (exec "(ns t (:export [f]))
(defn f [n :i64] :string (string-from-i64 n))"
                     'f [-42])))
  (is (= "0" (exec "(ns t (:export [f]))
(defn f [n :i64] :string (string-from-i64 n))"
                   'f [0]))))
