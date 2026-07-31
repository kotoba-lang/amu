(ns kotoba.compiler.typed-set-nth-test
  "T8.3 typed-set-nth frontend + KIR execute."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]))

(deftest typed-set-nth-compiles-and-runs
  (let [src
        (str
         "(ns t (:export [main]))\n"
         "(defn main [] :string\n"
         "  (let [s (typed-set-new [:set :string] \"Host\" \"Accept\")\n"
         "        a (typed-set-nth [:set :string] s 0)\n"
         "        b (typed-set-nth [:set :string] s 1)]\n"
         "    (string-concat a b)))\n")
        c (compiler/compile-source src :wasm32-kotoba-v1 {})
        out (ir/execute (:kir c) 'main [] {})]
    (is (= "AcceptHost" out))))

(deftest typed-set-nth-fold-edn-vector
  (let [src
        (str
         "(ns t (:export [main]))\n"
         "(defn main [] :string\n"
         "  (let [s (typed-set-new [:set :string] \"Host\" \"Accept\")\n"
         "        n (typed-set-count [:set :string] s)]\n"
         "    (loop [i 0 acc \"[]\"]\n"
         "      (if (>= i n)\n"
         "        acc\n"
         "        (let [item (typed-set-nth [:set :string] s i)\n"
         "              piece (string-concat \"\\\"\" (string-concat item \"\\\"\"))\n"
         "              acc2 (if (string=? acc \"[]\")\n"
         "                     (string-concat \"[\" (string-concat piece \"]\"))\n"
         "                     (string-concat\n"
         "                      (string-substring acc 0 (- (string-length acc) 1))\n"
         "                      (string-concat \" \" (string-concat piece \"]\"))))]\n"
         "          (recur (+ i 1) acc2))))))\n")
        c (compiler/compile-source src :wasm32-kotoba-v1 {})
        out (ir/execute (:kir c) 'main [] {})]
    (is (= "[\"Accept\" \"Host\"]" out))))
