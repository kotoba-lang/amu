(ns kotoba.compiler.slice-value-test
  "slice-value / ADR 0285: what the CARRIER costs, measured in bytes.

  ADR 0292 landed the slice family's lowering and said out loud that the value
  did not exist -- a traversal still took `base` and `length` as two i64
  parameters and re-proved the base's provenance at every call site.
  kotoba-sema ADR 0009 gives it a value, `[:slice T]`, and erases it into
  exactly those two words before HIR.

  The claim that has to be checked here rather than asserted is that the
  erasure is FREE. Not equivalent, not close: the carried source and the
  machine-spelled source must compile to the same bytes on both ISAs. If they
  do, then everything the frontend refuses about slices -- returning one,
  putting one in a record, exporting one -- is bought with nothing."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]))

(def ^:private fixture (slurp "test/fixtures/slice-carrier-sum.kotoba"))

(defn- code [source target]
  (vec (:code (:artifact (compiler/compile-source source target {})))))

(defn- contains-bytes? [bytes needle]
  (boolean (some #(= (vec needle) %) (partition (count needle) 1 bytes))))

;; The same traversal twice, once through the carrier and once through the
;; machine operations. Region base is a LITERAL rather than `kernel-boot-info`
;; so both ISAs can compile it: `kernel-boot-info` is an x86 privileged read
;; and `:aarch64-aiueos-kernel-v1` refuses it (`x86-privileged-target-mismatch`).
(defn- carried-source [element]
  (format "(ns s)
           (defn- sum [s [:slice %s] index :i64 total :i64]
             (if (< index (slice-length s))
               (sum s (+ index 1) (+ total (slice-get s index)))
               total))
           (defn main [] (sum (slice-of-%s 4096 512) 0 0))"
          element (name element)))

(defn- machine-source [element]
  (format "(ns s)
           (defn- sum [base :i64 length :i64 index :i64 total :i64]
             (if (< index length)
               (sum base length (+ index 1)
                    (+ total (slice-load-%s base length index)))
               total))
           (defn main [] (sum 4096 512 0 0))"
          (name element)))

(deftest the-carrier-and-the-machine-spelling-compile-to-the-same-bytes
  ;; The whole argument for erasure. A `[:slice T]` parameter is one source
  ;; parameter and two machine words, and this is the statement that "two
  ;; machine words" is literal: identical objects, on both ISAs, at every
  ;; element width.
  (doseq [target [:x86_64-aiueos-kernel-v1 :aarch64-aiueos-kernel-v1]
          element [:u8 :u16 :u32 :u64]]
    (let [carried (code (carried-source element) target)
          machine (code (machine-source element) target)]
      (is (seq carried) [target element])
      (is (> (count carried) 120) [target element "a real traversal, not a stub"])
      (is (= machine carried)
          (str target " " element
               ": the carrier must cost nothing -- carried "
               (count carried) " bytes, machine-spelled " (count machine))))))

(deftest the-fixture-compiles-for-the-freestanding-kernel-target
  (let [bytes (code fixture :x86_64-aiueos-kernel-v1)]
    (is (seq bytes))
    (is (> (count bytes) 400)
        "three traversals and a narrowing, not an empty body")))

(deftest an-element-access-through-the-carrier-is-one-compare-and-one-scaled-load
  (let [bytes (code fixture :x86_64-aiueos-kernel-v1)]
    (testing "the ceiling arrives by movabs, because 2^40 is not an imm32"
      ;; movabsq $0x10000000000, %r10
      (is (contains-bytes? bytes [0x49 0xba 0x00 0x00 0x00 0x00 0x00 0x01 0x00 0x00])
          "an address-space bound, not a window tier"))
    (testing "the element width comes from the SLICE TYPE, not the operation name"
      ;; Both traversals are spelled `(slice-get s index)`. The only thing that
      ;; differs is `[:slice :u8]` versus `[:slice :u64]`, and it lands in the
      ;; SIB scale field.
      (is (contains-bytes? bytes [0x4e 0x8d 0x1c 0x2b])
          "leaq (%rbx,%r13), %r11 -- scale 1 for a [:slice :u8]")
      (is (contains-bytes? bytes [0x4e 0x8d 0x1c 0xeb])
          "leaq (%rbx,%r13,8), %r11 -- scale 8 for a [:slice :u64]")
      (is (contains-bytes? bytes [0x45 0x0f 0xb6 0x03])
          "movzbl (%r11), %r8d -- a byte element is zero-extended")
      (is (contains-bytes? bytes [0x4d 0x8b 0x03])
          "movq (%r11), %r8 -- a word element is a plain REX.W load"))))

(deftest no-context-callback-appears-anywhere-in-the-carried-object
  ;; ADR 0285 measured `vector-at` at 381.72 ns/element and attributed it to
  ;; the host crossing. The carrier exists so that an element access is not
  ;; one, and the carried spelling must not reintroduce it -- a `slice-get`
  ;; that lowered to a callback would be the whole point undone.
  (let [bytes (code fixture :x86_64-aiueos-kernel-v1)]
    (is (not (contains-bytes? bytes [0x41 0xff 0x51])) "no disp8 context call")
    (is (not (contains-bytes? bytes [0x41 0xff 0x91])) "no disp32 context call")
    (testing "and the check is not vacuous: the object does contain direct calls"
      (is (contains-bytes? bytes [0xe8])))))

(deftest slice-sub-emits-a-checked-narrowing-and-a-narrowed-length
  ;; `(slice-sub s 16 32)` on a `[:slice :u8]`. The offset and the count are
  ;; ELEMENTS in the source; `kernel-subregion` reads BYTES; at :u8 the scale
  ;; is one, so the literals survive as 0x10 and 0x20 and the narrowing is
  ;; readable in the object.
  (let [bytes (code fixture :x86_64-aiueos-kernel-v1)]
    (testing "the offset and the sub-length reach the check as literals"
      (is (contains-bytes? bytes [0xba 0x10 0x00 0x00 0x00]) "movl $0x10, %edx")
      (is (contains-bytes? bytes [0x41 0xb8 0x20 0x00 0x00 0x00]) "movl $0x20, %r8d"))
    (testing "and the check is three comparisons into a ud2, not an addition"
      (is (contains-bytes? bytes [0x48 0x85 0xc0]) "testq %rax, %rax -- non-null parent")
      (is (contains-bytes? bytes [0x48 0x39 0xca]) "cmpq %rcx, %rdx -- offset within length")
      (is (contains-bytes? bytes [0x49 0x29 0xd2]) "subq %rdx, %r10 -- the remainder")
      (is (contains-bytes? bytes [0x4d 0x39 0xd0]) "cmpq %r10, %r8 -- count within it")
      (is (contains-bytes? bytes [0x0f 0x0b]) "ud2"))
    (testing "the narrowed slice carries its OWN length, not the parent's"
      (is (contains-bytes? bytes [0xb8 0x20 0x00 0x00 0x00])
          "movl $0x20, %eax -- 32 elements, which is what the loop bounds against"))))

(deftest the-frontend-refusals-survive-the-whole-compiler
  ;; kotoba-sema pins these individually; what is checked here is that they are
  ;; still refusals after `compile-source` has had a chance to do something
  ;; else with them -- a target that admitted a slice would be a hole this
  ;; repository owns.
  (doseq [[label source]
          [["a slice returned"
            "(ns s)(defn- p [b :i64] [:slice :u8] (slice-of-u8 b 8))(defn main [] 0)"]
           ["a slice on an exported function"
            "(ns s)(defn p [s [:slice :u8]] (slice-get s 0))(defn main [] 0)"]
           ["a slice built from arithmetic"
            "(ns s)(defn- p [i :i64] (slice-get (slice-of-u8 (+ i 1) 8) 0))
             (defn main [] (p 1))"]
           ["a slice element with no native load"
            "(ns s)(defn- p [s [:slice :f32]] (slice-get s 0))(defn main [] 0)"]]]
    (is (thrown? clojure.lang.ExceptionInfo
                 (compiler/compile-source source :x86_64-aiueos-kernel-v1 {}))
        label))
  (testing "and the shapes beside them still compile"
    (is (seq (code "(ns s)(defn- p [s [:slice :u8]] (slice-get s 0))
                    (defn main [] (p (slice-of-u8 4096 8)))"
                   :x86_64-aiueos-kernel-v1)))))
