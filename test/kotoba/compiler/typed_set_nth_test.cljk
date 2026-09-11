(ns kotoba.compiler.typed-set-nth-test
  "T8.3 typed-set-nth frontend + KIR execute (guest set fold / EDN encode)."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]))

(deftest typed-set-nth-compiles-and-runs
  (testing "guest fold over set items via nth + recursive helper"
    (let [src
          (str
           "(ns t (:export [main]))\n"
           "(defn- go [s [:set :string] i :i64 n :i64 acc :string] :string\n"
           "  (if (>= i n)\n"
           "    acc\n"
           "    (go s (+ i 1) n\n"
           "        (string-concat acc (typed-set-nth [:set :string] s i)))))\n"
           "(defn main [] :string\n"
           "  (let [s (typed-set-new [:set :string] \"Host\" \"Accept\")\n"
           "        n (typed-set-count [:set :string] s)]\n"
           "    (go s 0 n \"\")))\n")
          c (compiler/compile-source src :wasm32-kotoba-v1 {})
          out (ir/execute (:kir c) 'main [] {})]
      (is (= "AcceptHost" out)))))

(deftest typed-set-nth-fold-headers-edn-shape
  (testing "build EDN vector string from set of strings via nth fold"
    (let [src
          (str
           "(ns t (:export [main]))\n"
           "(defn- piece [item :string] :string\n"
           "  (string-concat \"\\\"\" (string-concat item \"\\\"\")))\n"
           "(defn- go [s [:set :string] i :i64 n :i64 acc :string] :string\n"
           "  (if (>= i n)\n"
           "    acc\n"
           "    (let [item (typed-set-nth [:set :string] s i)\n"
           "          p (piece item)\n"
           "          acc2 (if (string=? acc \"[]\")\n"
           "                 (string-concat \"[\" (string-concat p \"]\"))\n"
           "                 (string-concat\n"
           "                  (string-substring acc 0 (- (string-length acc) 1))\n"
           "                  (string-concat \" \" (string-concat p \"]\"))))]\n"
           "      (go s (+ i 1) n acc2))))\n"
           "(defn main [] :string\n"
           "  (let [s (typed-set-new [:set :string] \"Host\" \"Accept\")\n"
           "        n (typed-set-count [:set :string] s)]\n"
           "    (go s 0 n \"[]\")))\n")
          c (compiler/compile-source src :wasm32-kotoba-v1 {})
          out (ir/execute (:kir c) 'main [] {})]
      (is (= "[\"Accept\" \"Host\"]" out)))))

(deftest typed-set-nth-simple-item
  (let [src "(ns t (:export [main]))
(defn main [] :string
  (let [s (typed-set-new [:set :string] \"Host\" \"Accept\")]
    (typed-set-nth [:set :string] s 0)))"
        c (compiler/compile-source src :wasm32-kotoba-v1 {})]
    (is (= "Accept" (ir/execute (:kir c) 'main [] {})))))
