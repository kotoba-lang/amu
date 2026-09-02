(ns kotoba.compiler.slice-carrier-test
  "memwidth / ADR 0291: what the ADR 0285 carrier's lowering actually emits.

  The prose claim is that an element access is one unsigned compare and one
  scaled `mov`, with no context callback in the loop. That is a claim about
  bytes, so it is checked against bytes rather than restated -- and the two
  halves are checked separately, because a fixture that emits no load at all
  would satisfy `no callback` trivially."
  (:require [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]))

(def ^:private source (slurp "test/fixtures/slice-sum-u8.kotoba"))

(defn- code []
  (:code (:artifact (compiler/compile-source source :x86_64-aiueos-kernel-v1 {}))))

(defn- contains-bytes? [bytes needle]
  (boolean (some #(= (vec needle) %) (partition (count needle) 1 bytes))))

(deftest the-fixture-compiles-for-the-freestanding-kernel-target
  (let [bytes (code)]
    (is (seq bytes))
    (is (> (count bytes) 200) "a real traversal, not an empty body")))

(deftest an-element-access-is-one-compare-and-one-scaled-mov
  (let [bytes (code)]
    (testing "the ceiling arrives by movabs, because 2^40 is not an imm32"
      ;; movabsq $0x10000000000, %r10
      (is (contains-bytes? bytes [0x49 0xba 0x00 0x00 0x00 0x00 0x00 0x01 0x00 0x00])
          "a window tier would be `cmp r64, imm32`; an address-space bound is not"))
    (testing "the index is scaled in the addressing mode"
      ;; leaq (%rbx,%r13,8), %r11 -- SIB scale field 3, then movq (%r11), %r8
      (is (contains-bytes? bytes [0x4e 0x8d 0x1c 0xeb])
          "u64 elements address at base + index*8")
      (is (contains-bytes? bytes [0x4d 0x8b 0x03])
          "and the access itself is a plain REX.W mov")
      ;; leaq (%rbx,%r13), %r11 -- the same lea with the scale at 1
      (is (contains-bytes? bytes [0x4e 0x8d 0x1c 0x2b])
          "u8 elements address at base + index, which is the same instruction"))))

(deftest no-context-callback-appears-anywhere-in-the-object
  ;; `call qword ptr [r9+disp]` is how every host callback leaves. ADR 0285
  ;; measured `vector-at` at 381.72 ns/element and attributed it to that
  ;; crossing; the whole point of the carrier is that an element access is not
  ;; one. Both encodings are checked, because the disp8 form silently becomes
  ;; the disp32 form past offset 127.
  (let [bytes (code)]
    (is (not (contains-bytes? bytes [0x41 0xff 0x51]))
        "no disp8 context call")
    (is (not (contains-bytes? bytes [0x41 0xff 0x91]))
        "no disp32 context call")
    (testing "and the check is not vacuous: the object does contain calls"
      ;; Three direct `callq rel32` for the probe/entry plumbing. If this
      ;; assertion ever fails, the two above have stopped meaning anything.
      (is (contains-bytes? bytes [0xe8])
          "a direct call is present, so `no indirect call` is a real distinction"))))

(deftest the-window-family-and-the-slice-family-differ-only-in-the-scale
  ;; Compiled side by side so the difference is one SIB byte rather than a
  ;; paragraph. A window index is a byte offset; a slice index counts elements.
  (let [window (:code (:artifact (compiler/compile-source
                                  "(ns w)
                                   (defn f [base length index]
                                     (kernel-load-u64-4k base length index))
                                   (defn main [] 0)"
                                  :x86_64-aiueos-kernel-v1 {})))
        slice (:code (:artifact (compiler/compile-source
                                 "(ns s)
                                  (defn f [base length index]
                                    (slice-load-u64 base length index))
                                  (defn main [] 0)"
                                 :x86_64-aiueos-kernel-v1 {})))
        ;; the SIB byte of a `lea r11, [base + index*N]`: REX with W|R, 8d,
        ;; ModRM 0x1c, then SIB whose top two bits are log2(scale)
        scale-of (fn [bytes]
                   (some (fn [[rex opcode modrm sib]]
                           (when (and (= 0x48 (bit-and rex 0x48))
                                      (= 0x04 (bit-and rex 0x04))
                                      (= 0x8d opcode)
                                      (= 0x1c modrm))
                             (bit-shift-right sib 6)))
                         (partition 4 1 bytes)))]
    (is (nil? (scale-of window))
        "a window access adds the index, so it emits no scaled lea at all")
    (is (= 3 (scale-of slice))
        "a slice access scales it by the element width")
    (testing "and the window family pays a tail check the slice family does not"
      ;; cmp r10, 8 -- `length - index >= 8`, which an element index makes
      ;; structurally unnecessary.
      (is (contains-bytes? window [0x49 0x81 0xfa 0x08 0x00 0x00 0x00]))
      (is (not (contains-bytes? slice [0x49 0x81 0xfa 0x08 0x00 0x00 0x00]))))))
