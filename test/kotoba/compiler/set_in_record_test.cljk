(ns kotoba.compiler.set-in-record-test
  "set-in-record unlock: guest records may carry `[:set T]` fields.

  Proves T8.3 true-set uniqueness residual can fold on the pure/KIR path
  without substring-scan honesty — typed-set-contains/conj over a
  record-held `[:set :string]` (header-name bag shape). Component AOT
  packages still use hand-WAT substring uniqueness until a pure Component
  twin without kotoba:typed is admitted; this slice does **not** flip
  `:wasm-aot :implemented`."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]))

(def ^:private bag-src
  (str
   "(ns hdr-set-rec\n"
   "  (:export [go])\n"
   "  (:schemas {:hdr/bag [:record :hdr/bag\n"
   "                      [[:seen [:set :string]]]]}))\n"
   "\n"
   "(defn go [] :i64\n"
   "  (let [empty (record-new [:ref :hdr/bag] (typed-set [:set :string]))\n"
   "        s0 (record-get empty :seen)\n"
   "        s1 (typed-set-conj [:set :string] s0 \"Host\")\n"
   "        bag (record-new [:ref :hdr/bag] s1)]\n"
   "    (if (typed-set-contains [:set :string] (record-get bag :seen) \"Host\")\n"
   "      1\n"
   "      0)))\n"))

(deftest header-name-set-in-record-compiles-and-runs
  (testing "schema admits [:set :string] field; KIR projects through record"
    (let [c (compiler/compile-source bag-src :wasm32-kotoba-v1 {})
          out (ir/execute (:kir c) 'go [] {})]
      (is (some? (:kir c)))
      (is (= 1 out)))))

(deftest header-name-set-uniqueness-via-record
  (testing "typed-set-conj of duplicate name does not grow the set (true uniqueness)"
    (let [src
          (str
           "(ns hdr-uniq\n"
           "  (:export [go])\n"
           "  (:schemas {:hdr/bag [:record :hdr/bag\n"
           "                      [[:seen [:set :string]]]]}))\n"
           "(defn go [] :i64\n"
           "  (let [empty (typed-set [:set :string])\n"
           "        s1 (typed-set-conj [:set :string] empty \"Host\")\n"
           "        s2 (typed-set-conj [:set :string] s1 \"Host\")\n"
           "        s3 (typed-set-conj [:set :string] s2 \"Accept\")\n"
           "        bag (record-new [:ref :hdr/bag] s3)]\n"
           "    (typed-set-count [:set :string] (record-get bag :seen))))\n")
          c (compiler/compile-source src :wasm32-kotoba-v1 {})
          out (ir/execute (:kir c) 'go [] {})]
      ;; Host twice + Accept once → cardinality 2 (true set, not multiset / substring)
      (is (= 2 out)))))

(deftest header-name-set-reject-duplicate-constructor
  (testing "typed-set constructor rejects duplicate items at value time (closed uniqueness)"
    (let [src
          (str
           "(ns hdr-dup\n"
           "  (:export [go])\n"
           "  (:schemas {:hdr/bag [:record :hdr/bag\n"
           "                      [[:seen [:set :string]]]]}))\n"
           "(defn go [] [:set :string]\n"
           "  (record-get\n"
           "    (record-new [:ref :hdr/bag]\n"
           "                (typed-set [:set :string] \"Host\" \"Host\"))\n"
           "    :seen))\n")
          c (compiler/compile-source src :wasm32-kotoba-v1 {})]
      (is (thrown-with-msg? clojure.lang.ExceptionInfo
                            #"duplicate"
                            (ir/execute (:kir c) 'go [] {}))))))
