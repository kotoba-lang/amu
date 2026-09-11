(ns kotoba.compiler.document-in-record-test
  "document-in-record unlock: guest records may carry :document fields.

  Proves the design-system Delivery-6 residual (css rule-doc / render-decls
  multi-arg pure) can fold once schema admits :document in closed profile."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]))

(def ^:private rule-src
  (str
   "(ns css-doc-rec\n"
   "  (:export [go])\n"
   "  (:schemas {:doc/rule [:record :doc/rule\n"
   "                        [[:selector :string] [:decls :document]]]}))\n"
   "\n"
   "(defn rule-doc [x [:ref :doc/rule]] :document\n"
   "  (let [selector (record-get x :selector)\n"
   "        decls (record-get x :decls)]\n"
   "    (document-map :selector (document-string selector)\n"
   "                  :decls decls)))\n"
   "\n"
   "(defn sel-of [d :document] :string\n"
   "  (option-value-of [:option :string]\n"
   "    (document-string-value\n"
   "      (option-value-of [:option :document]\n"
   "        (document-get d :selector) (document-null)))\n"
   "    \"*\"))\n"
   "\n"
   "(defn go [] :string\n"
   "  (sel-of\n"
   "    (rule-doc\n"
   "      (record-new [:ref :doc/rule]\n"
   "                  \".card\"\n"
   "                  (document-vector\n"
   "                    (document-map :prop (document-keyword :color)\n"
   "                                  :value (document-string \"red\")))))))\n"))

(deftest rule-doc-guest-record-compiles-and-runs
  (testing "schema admits :document field; KIR projects selector through record"
    (let [c (compiler/compile-source rule-src :wasm32-kotoba-v1 {})
          out (ir/execute (:kir c) 'go [] {})]
      (is (some? (:kir c)))
      (is (= ".card" out)))))

(deftest rule-doc-guest-record-document-roundtrip-shape
  (testing "record-held decls remain a document vector for render folds"
    (let [src (str
               "(ns css-doc-rec2\n"
               "  (:export [go])\n"
               "  (:schemas {:doc/rule [:record :doc/rule\n"
               "                        [[:selector :string] [:decls :document]]]}))\n"
               "(defn rule-doc [x [:ref :doc/rule]] :document\n"
               "  (document-map :selector (document-string (record-get x :selector))\n"
               "                :decls (record-get x :decls)))\n"
               "(defn go [] :i64\n"
               "  (document-count\n"
               "    (option-value-of [:option :document]\n"
               "      (document-get\n"
               "        (rule-doc\n"
               "          (record-new [:ref :doc/rule]\n"
               "                      \".x\"\n"
               "                      (document-vector\n"
               "                        (document-map :prop (document-keyword :a)\n"
               "                                      :value (document-string \"1\"))\n"
               "                        (document-map :prop (document-keyword :b)\n"
               "                                      :value (document-string \"2\")))))\n"
               "        :decls)\n"
               "      (document-null))))\n")
          c (compiler/compile-source src :wasm32-kotoba-v1 {})
          out (ir/execute (:kir c) 'go [] {})]
      (is (= 2 out)))))
