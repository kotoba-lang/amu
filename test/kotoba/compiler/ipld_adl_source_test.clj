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

(def byte-at-source
  "(ns adl.byte-at
       (:export [validate-representation decode encode validate-logical]))
   (defn validate-representation [value :bytes] :bool (= (bytes-at value 0) 161))
   (defn decode [value :bytes] :bytes value)
   (defn encode [value :bytes] :bytes value)
   (defn validate-logical [value :bytes] :bool (= (bytes-at value 0) 161))")

(def slice-source
  "(ns adl.slice
       (:export [validate-representation decode encode validate-logical]))
   (defn validate-representation [value :bytes] :bool true)
   (defn decode [value :bytes] :bytes (bytes-slice value 1 3))
   (defn encode [value :bytes] :bytes value)
   (defn validate-logical [value :bytes] :bool true)")

;; Rotates the four-byte ABI input: bytes [1,3) then byte [0,1). The second
;; source byte is the one a destination that overlapped the input would have
;; destroyed before reading it, which is what makes this fixture discriminate.
(def join-source
  "(ns adl.join
       (:export [validate-representation decode encode validate-logical]))
   (defn validate-representation [value :bytes] :bool true)
   (defn decode [value :bytes] :bytes
     (bytes-concat (bytes-slice value 1 3) (bytes-slice value 0 1)))
   (defn encode [value :bytes] :bytes value)
   (defn validate-logical [value :bytes] :bool true)")

(def join-double-source
  "(ns adl.join-double
       (:export [validate-representation decode encode validate-logical]))
   (defn validate-representation [value :bytes] :bool true)
   (defn decode [value :bytes] :bytes (bytes-concat value value))
   (defn encode [value :bytes] :bytes value)
   (defn validate-logical [value :bytes] :bool true)")

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

(deftest indexed-byte-validator-is-preserved-in-kir-and-wasm
  (let [compiled (compiler/compile-ipld-adl-source byte-at-source)]
    (is (= :input-bytes-v1 (get-in compiled [:adl :profile])))
    (is (= [:input-byte-at-eq 0 161]
           (get-in compiled [:kir :plan :validate-representation])))
    (is (= [:input-byte-at-eq 0 161]
           (get-in compiled [:kir :plan :validate-logical])))
    (is (= (:provenance compiled)
           (provenance/verify! byte-at-source {} compiled)))))

(deftest indexed-byte-validator-emits-a-bounds-check-before-the-load
  (let [compiled (compiler/compile-ipld-adl-source byte-at-source)
        module (Files/createTempFile "kotoba-adl-byte-at-" ".wasm"
                                     (make-array FileAttribute 0))]
    (try
      (Files/write module (:bytes compiled) (make-array java.nio.file.OpenOption 0))
      (let [validation (shell/sh "wasm-tools" "validate" (str module))
            text (:out (shell/sh "wasm-tools" "print" (str module)))]
        (is (zero? (:exit validation)) (:err validation))
        (is (re-find #"i32\.load8_u" text)
            "the byte is read unsigned, so 0xFF is 255 rather than -1")
        (is (re-find #"unreachable" text)
            "an out-of-range index traps instead of reading past the operand")
        ;; The guard has to compare against the ABI length (local 2). Comparing
        ;; against the pointer, or omitting the compare and trusting the linear
        ;; memory bound, both still validate as Wasm -- and both read whatever
        ;; happens to sit after the input.
        (is (re-find #"(?s)local\.get 2.*i32\.le_u.*unreachable.*i32\.load8_u" text)
            "the bound is the operand's length, not the memory's size")
        (is (not (re-find #"\(import " text))))
      (finally (Files/deleteIfExists module)))))

(deftest subrange-transform-is-preserved-in-kir-and-wasm
  (let [compiled (compiler/compile-ipld-adl-source slice-source)]
    (is (= :input-bytes-v1 (get-in compiled [:adl :profile])))
    (is (= [:input-subrange 1 3] (get-in compiled [:kir :plan :decode])))
    (is (= :identity (get-in compiled [:kir :plan :encode])))
    (is (= (:provenance compiled)
           (provenance/verify! slice-source {} compiled)))))

(deftest subrange-transform-is-a-bounded-view-not-a-copy
  (let [compiled (compiler/compile-ipld-adl-source slice-source)
        module (Files/createTempFile "kotoba-adl-slice-" ".wasm"
                                     (make-array FileAttribute 0))]
    (try
      (Files/write module (:bytes compiled) (make-array java.nio.file.OpenOption 0))
      (let [validation (shell/sh "wasm-tools" "validate" (str module))
            text (:out (shell/sh "wasm-tools" "print" (str module)))]
        (is (zero? (:exit validation)) (:err validation))
        ;; The guard has to compare the requested end against the ABI length
        ;; (local 2) and trap. Comparing against the memory size, or omitting
        ;; the compare, still validates as Wasm and still returns a pointer --
        ;; into bytes that are not the operand.
        (is (re-find #"(?s)local\.get 2.*i32\.lt_u.*unreachable" text)
            "the bound is the operand's length, not the memory's size")
        ;; A view, not a copy: the result is the operand's own pointer moved
        ;; forward, so the module never writes to linear memory. That is the
        ;; alias rule, and it is checkable.
        (is (not (re-find #"i32\.store|i64\.store|memory\.copy|memory\.fill" text))
            "a subrange aliases the operand instead of being copied out")
        (is (not (re-find #"\(import " text))))
      (finally (Files/deleteIfExists module)))))

(deftest join-transform-is-preserved-in-kir-and-wasm
  (let [compiled (compiler/compile-ipld-adl-source join-source)]
    (is (= :input-bytes-v1 (get-in compiled [:adl :profile])))
    (is (= [:input-join [[:sub 1 3] [:sub 0 1]]]
           (get-in compiled [:kir :plan :decode])))
    (is (= (:provenance compiled)
           (provenance/verify! join-source {} compiled))))
  (let [compiled (compiler/compile-ipld-adl-source join-double-source)]
    (is (= [:input-join [[:whole] [:whole]]]
           (get-in compiled [:kir :plan :decode])))))

(deftest join-writes-past-the-operand-and-pays-per-byte
  (let [compiled (compiler/compile-ipld-adl-source join-source)
        module (Files/createTempFile "kotoba-adl-join-" ".wasm"
                                     (make-array FileAttribute 0))]
    (try
      (Files/write module (:bytes compiled) (make-array java.nio.file.OpenOption 0))
      (let [validation (shell/sh "wasm-tools" "validate" (str module))
            text (:out (shell/sh "wasm-tools" "print" (str module)))]
        (is (zero? (:exit validation)) (:err validation))
        ;; Unlike a subrange, a join must write. So "contains no store" is no
        ;; longer the alias rule -- "the destination starts past the operand"
        ;; is. The write cursor is initialised from pointer + length before any
        ;; store, which is what keeps a source byte from being overwritten
        ;; before it is read.
        (is (re-find #"(?s)local\.get 1.*local\.get 2.*i32\.add.*local\.set 3.*i32\.store8" text)
            "the destination cursor starts past the operand")
        ;; Room for operand + result is checked before the first store, so the
        ;; write cannot leave the module's own memory.
        (is (re-find #"(?s)i32\.gt_u.*unreachable.*i32\.store8" text)
            "the combined length is bounded before anything is written")
        ;; A bulk copy would move the same bytes for one instruction's fuel.
        (is (not (re-find #"memory\.copy|memory\.fill" text))
            "the join pays per byte moved, not per instruction")
        (is (re-find #"i32\.load8_u" text))
        (is (not (re-find #"\(import " text))))
      (finally (Files/deleteIfExists module)))))

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
                    "(= 4 (bytes-count value))")))))
  (testing "a reordered indexed byte comparison is not admitted"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"unsupported IPLD ADL operation body"
         (compiler/compile-ipld-adl-source
          (.replace byte-at-source
                    "(= (bytes-at value 0) 161)"
                    "(= 161 (bytes-at value 0))")))))
  (testing "a negative byte index is refused by name, not lowered"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"byte index must be a non-negative int32"
         (compiler/compile-ipld-adl-source
          (.replace byte-at-source
                    "(bytes-at value 0)"
                    "(bytes-at value -1)")))))
  (testing "a comparison outside 0..255 can never hold, so it is refused"
    ;; bytes-at yields an unsigned byte. Admitting 256 would compile a source
    ;; mistake into a validator that silently always answers false.
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"byte comparison must be an unsigned byte"
         (compiler/compile-ipld-adl-source
          (.replace byte-at-source
                    "(bytes-at value 0) 161)"
                    "(bytes-at value 0) 256)"))))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"byte comparison must be an unsigned byte"
         (compiler/compile-ipld-adl-source
          (.replace byte-at-source
                    "(bytes-at value 0) 161)"
                    "(bytes-at value 0) -1)")))))
  (testing "a computed index is outside this closed profile"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"unsupported IPLD ADL operation body"
         (compiler/compile-ipld-adl-source
          (.replace byte-at-source
                    "(bytes-at value 0)"
                    "(bytes-at value (bytes-count value))")))))
  (testing "an inverted or negative subrange is refused by name"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"subrange offsets must satisfy 0 <= start <= end"
         (compiler/compile-ipld-adl-source
          (.replace slice-source "(bytes-slice value 1 3)" "(bytes-slice value 3 1)"))))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"subrange offsets must satisfy 0 <= start <= end"
         (compiler/compile-ipld-adl-source
          (.replace slice-source "(bytes-slice value 1 3)" "(bytes-slice value -1 3)")))))
  (testing "a subrange the fixed memory could never satisfy is refused"
    ;; Two pages leave 130048 bytes for input, so a slice ending past that can
    ;; never be in range at run time. Rejecting it at compile time is the
    ;; lowering half of the max-output bound; the runner enforces the other.
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"subrange exceeds the module's input capacity"
         (compiler/compile-ipld-adl-source
          (.replace slice-source "(bytes-slice value 1 3)" "(bytes-slice value 0 130049)"))))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"subrange exceeds the module's input capacity"
         (compiler/compile-ipld-adl-source
          (.replace slice-source "(bytes-slice value 1 3)" "(bytes-slice value 0 65000)")
          {:memory-pages 1}))))
  (testing "a computed offset is outside this closed profile"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"unsupported IPLD ADL operation body"
         (compiler/compile-ipld-adl-source
          (.replace slice-source
                    "(bytes-slice value 1 3)"
                    "(bytes-slice value 1 (bytes-count value))")))))
  (testing "a nested join is the closed expression grammar, not this profile"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"unsupported IPLD ADL operation body"
         (compiler/compile-ipld-adl-source
          (.replace join-source
                    "(bytes-slice value 1 3) (bytes-slice value 0 1)"
                    "(bytes-concat value value) (bytes-slice value 0 1)")))))
  (testing "a join whose constant part alone cannot fit is refused"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"join exceeds the module's input capacity"
         (compiler/compile-ipld-adl-source
          (.replace join-source
                    "(bytes-slice value 1 3) (bytes-slice value 0 1)"
                    "(bytes-slice value 0 70000) (bytes-slice value 0 70000)")))))
  (testing "an inverted offset inside a join is still refused by name"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"subrange offsets must satisfy 0 <= start <= end"
         (compiler/compile-ipld-adl-source
          (.replace join-source "(bytes-slice value 1 3)" "(bytes-slice value 3 1)"))))))
