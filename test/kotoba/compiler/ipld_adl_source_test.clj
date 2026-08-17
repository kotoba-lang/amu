(ns kotoba.compiler.ipld-adl-source-test
  (:require [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.provenance :as provenance])
  (:import (java.nio.file Files)
           (java.nio.file.attribute FileAttribute)))

(def identity-source
  "(ns adl.identity
       (:export [validate-representation decode encode validate-logical]))
   (defn validate-representation [value :bytes] :bool true)
   (defn decode [value :bytes] :bytes value)
   (defn encode [value :bytes] :bytes value)
   (defn validate-logical [value :bytes] :bool true)")

(def closed-source
  "(ns adl.closed
       (:export [validate-representation decode encode validate-logical]))
   (defn validate-representation [value :bytes] :bool true)
   (defn decode [value :bytes] :bytes (bytes))
   (defn encode [value :bytes] :bytes value)
   (defn validate-logical [value :bytes] :bool false)")

(def input-count-source
  "(ns adl.input-count
       (:export [validate-representation decode encode validate-logical]))
   (defn validate-representation [value :bytes] :bool (= (bytes-count value) 4))
   (defn decode [value :bytes] :bytes value)
   (defn encode [value :bytes] :bytes value)
   (defn validate-logical [value :bytes] :bool (= (bytes-count value) 4))")

(deftest kotoba-source-compiles-to-the-closed-adl-abi
  (let [compiled (compiler/compile-ipld-adl-source identity-source)
        module (Files/createTempFile "kotoba-adl-source-" ".wasm"
                                     (make-array FileAttribute 0))]
    (try
      (Files/write module (:bytes compiled) (make-array java.nio.file.OpenOption 0))
      (let [validation (shell/sh "wasm-tools" "validate" (str module))
            inspection (shell/sh "wasm-tools" "print" (str module))]
        (is (zero? (:exit validation)) (:err validation))
        (is (zero? (:exit inspection)) (:err inspection))
        (is (re-find #"\(export \"memory\" \(memory 0\)\)" (:out inspection)))
        (is (re-find #"\(export \"adl_alloc\" \(func 0\)\)" (:out inspection)))
        (is (re-find #"\(export \"adl_transform\" \(func 1\)\)" (:out inspection)))
        (is (not (re-find #"\(import " (:out inspection)))))
      (is (= :pure-identity-v1 (get-in compiled [:adl :profile])))
      (is (= 2 (get-in compiled [:limits :memory-pages])))
      (is (= (:provenance compiled)
             (provenance/verify! identity-source {} compiled)))
      (finally (Files/deleteIfExists module)))))

(deftest non-identity-closed-plan-is-preserved-in-kir-and-wasm
  (let [compiled (compiler/compile-ipld-adl-source closed-source)]
    (is (= :pure-closed-v1 (get-in compiled [:adl :profile])))
    (is (= {:validate-representation :true :decode :empty-bytes
            :encode :identity :validate-logical :false}
           (get-in compiled [:kir :plan])))
    (is (= (:provenance compiled)
           (provenance/verify! closed-source {} compiled)))))

(deftest input-byte-count-validator-is-preserved-in-kir-and-wasm
  (let [compiled (compiler/compile-ipld-adl-source input-count-source)]
    (is (= :input-bytes-v1 (get-in compiled [:adl :profile])))
    (is (= [:input-byte-count-eq 4]
           (get-in compiled [:kir :plan :validate-representation])))
    (is (= [:input-byte-count-eq 4]
           (get-in compiled [:kir :plan :validate-logical])))
    (is (= (:provenance compiled)
           (provenance/verify! input-count-source {} compiled)))))

(deftest profile-rejects-source-it-cannot-faithfully-lower
  (testing "a changed body is not silently compiled as identity"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"unsupported IPLD ADL operation body"
         (compiler/compile-ipld-adl-source
          (.replace identity-source
                    "(defn decode [value :bytes] :bytes value)"
                    "(defn decode [value :bytes] :bytes (if true value (bytes)))")))))
  (testing "extra exports cannot enlarge the ABI"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"exact operation set"
         (compiler/compile-ipld-adl-source
          (.replace identity-source
                    "validate-logical]))"
                    "validate-logical extra]))\n(defn extra [] 1)")))))
  (testing "unbounded or reordered byte expressions are not admitted"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"unsupported IPLD ADL operation body"
         (compiler/compile-ipld-adl-source
          (.replace input-count-source
                    "(= (bytes-count value) 4)"
                    "(= 4 (bytes-count value))"))))))
