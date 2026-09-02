(ns kotoba.compiler.let-body-sequencing-test
  "A `let` body with several forms emits every one of them.

  Until 2026-09-02 it emitted the first and dropped the rest, with `:ok true`.
  Measured against this repo at b1fdaad2 / kotoba-sema 8b2cb10:

      (defn run [n :i64] :i64 (let [x (+ n 1)] (+ x 10) (+ x 100)))

  `amu check --jvm-free` answered `:ok true`; the wasm32 artifact executed
  `run(5)` as 16, not 106. A `let` body of four kernel stores emitted ONE.
  In the QWEN-RUNTIME stream the dropped form carried the high word of a
  64-bit offset cursor.

  Fixed in the frontend, which collapses a multi-form body into a `do`
  (kotoba-sema c14ca39e); refused at the IR boundary if it ever arrives
  uncollapsed (kotoba-kir 0fd7e259); stated in the authority as
  `:core-form-shapes` (kotoba-lang 4adda169). This suite is the compiled
  evidence.

  The assertions are deliberately allocator-independent. An earlier draft
  counted a pinned store opcode and had to be thrown away twice: once because
  the needle came from a kotoba-native checkout behind its pin and matched
  nothing, and once because at four stores the allocator picked a different
  register and the count came up one short. Neither failure was about the
  subject. What is asserted instead is the property itself -- a `let` body of
  N forms emits exactly what the explicit `(do ...)` of those N forms emits,
  and N forms do not fit in the object for N-1."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]))

(def ^:private kernel-targets [:x86_64-aiueos-kernel-v1 :aarch64-aiueos-kernel-v1])

;; A literal base, not `(kernel-boot-info)`: boot-info is an x86 privileged
;; operation and the aarch64 kernel target refuses it with
;; `x86-privileged-target-mismatch`, which is a refusal about the base and not
;; about the body.
(def ^:private region "150994944")

(defn- code-for [source target]
  (:code (:artifact (compiler/compile-source source target))))

(defn- stores [n] (for [i (range n)] (str "(kernel-store-u8 region 8 " i " " (+ 65 i) ")")))

(defn- let-body-source [n]
  (str "(defn main [] (let [region " region "] " (clojure.string/join " " (stores n)) "))"))

(defn- do-body-source [n]
  (str "(defn main [] (let [region " region "] (do "
       (clojure.string/join " " (stores n)) ")))"))

(defn- occurrences [bytes needle]
  (count (filter #(= needle %) (partition (count needle) 1 bytes))))

(defn- words [bytes]
  (map (fn [w] (reduce (fn [n i] (+ n (bit-shift-left (long (bit-and 0xff (nth w i))) (* 8 i))))
                       0 (range 4)))
       (partition 4 bytes)))

(defn- immediate-loads
  "How many times VALUE is loaded as an immediate in CODE.

  The two architectures hide the number in different places and there is no
  common needle. x86_64 writes `mov r32, imm32`, so the value is four
  little-endian bytes in the stream. AArch64 is fixed-width: `movz Xd, #imm16`
  packs the value into bits 20:5 of one 32-bit word, and searching the byte
  stream for it finds nothing -- which is how an earlier draft of this test
  reported four absent stores that were all present.

  The AArch64 form is the 64-bit `movz` (`0xd28.....`), read off the emitted
  words rather than assumed: the 32-bit `movz Wd` (`0x528.....`) is the one a
  reader expects for a byte-sized value, and it matches nothing here."
  [target code value]
  (case target
    :x86_64-aiueos-kernel-v1 (occurrences code [value 0 0 0])
    :aarch64-aiueos-kernel-v1
    (count (filter (fn [w] (and (= 0xd2800000 (bit-and w 0xffe00000))
                                (= value (bit-and (bit-shift-right w 5) 0xffff))))
                   (words code)))))

;; --- the emitted object ----------------------------------------------------

(deftest a-let-body-emits-exactly-what-the-explicit-do-emits
  ;; The strongest form of the claim, and the one that does not depend on which
  ;; register the allocator chose: the body IS an implicit `do`, so writing one
  ;; must change nothing. Before the fix the `let` side of this equality was
  ;; the object for ONE store at every n.
  (doseq [target kernel-targets
          n [1 2 3 4]]
    (is (= (code-for (do-body-source n) target)
           (code-for (let-body-source n) target))
        (str target " with " n " stores"))))

(deftest n-stores-do-not-fit-in-the-object-for-fewer
  ;; Length, not opcodes. A compiler that keeps the first body form emits the
  ;; same object for every n, so this is exactly the discriminating
  ;; measurement, and it survives any change of register allocation or
  ;; instruction selection.
  (doseq [target kernel-targets]
    (let [sizes (mapv #(count (code-for (let-body-source %) target)) [1 2 3 4])
          steps (mapv - (rest sizes) (butlast sizes))]
      (is (apply < sizes)
          (str target " SCANNED object sizes for 1..4 stores: " sizes
               " -- the pre-fix compiler emitted four equal objects"))
      (is (apply = steps)
          (str target " each additional store costs the same: " steps)))))

(deftest every-store-value-reaches-the-object
  ;; Names the data that was disappearing. Each store writes a distinct
  ;; immediate; with only the first form kept, 66/67/68 were absent from the
  ;; object entirely.
  (doseq [target kernel-targets]
    (let [code (code-for (let-body-source 4) target)]
      (doseq [value [65 66 67 68]]
        (is (pos? (immediate-loads target code value))
            (str target " -- immediate " value " is in the object"))))))

(deftest a-one-form-let-body-is-byte-for-byte-what-it-always-was
  ;; The collapse must not wrap a single-form body in a `do`; that would move
  ;; the emitted bytes of every existing program.
  (doseq [target kernel-targets]
    (is (= (code-for (str "(defn main [] (kernel-store-u8 " region " 8 0 65))") target)
           (code-for (let-body-source 1) target))
        (str target " -- a let that only names the region adds no instruction"))))

;; --- the value ------------------------------------------------------------

(deftest the-value-of-a-let-body-is-its-last-form
  (testing "through the constant oracle on the pure target"
    (is (= 106 (:value (:artifact (compiler/compile-source
                                   "(defn main [] (let [x 6] (+ x 10) (+ x 100)))"
                                   :aarch64-kotoba-v1)))))
    (is (= 1006 (:value (:artifact (compiler/compile-source
                                    "(defn main [] (let [x 6] (+ x 10) (+ x 100) (+ x 1000)))"
                                    :aarch64-kotoba-v1))))))
  (testing "a nested let in non-final position is not the value"
    ;; The shape that made the truncation read as a scoping rule: the pre-fix
    ;; answer here was 7, which looks like the inner binding leaking out.
    (is (= 106 (:value (:artifact (compiler/compile-source
                                   "(defn main [] (let [x 6] (let [y (+ x 1)] y) (+ x 100)))"
                                   :aarch64-kotoba-v1)))))))

;; --- refusals -------------------------------------------------------------

(deftest an-empty-let-body-is-refused
  (is (thrown-with-msg? clojure.lang.ExceptionInfo #"at least one body expression"
        (compiler/compile-source "(defn main [] (let [x 1]))" :aarch64-kotoba-v1))))

(deftest an-if-that-is-not-ternary-is-refused
  ;; Found alongside the `let` truncation and the same shape: a fourth argument
  ;; was dropped by a pass that rebuilt the form from [test then else], and
  ;; `(if (> n 0) (+ n 10) (+ n 100) (+ n 1000))` compiled and answered its
  ;; `then`.
  (is (thrown-with-msg? clojure.lang.ExceptionInfo #"if requires test, then, else; got 4"
        (compiler/compile-source "(defn main [] (if (< 0 1) 10 100 1000))" :aarch64-kotoba-v1)))
  (is (thrown-with-msg? clojure.lang.ExceptionInfo #"if requires test, then, else; got 2"
        (compiler/compile-source "(defn main [] (if (< 0 1) 10))" :aarch64-kotoba-v1))))
