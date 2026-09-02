(ns kotoba.compiler.f32-native-execution-test
  "Binary32 EXECUTED as machine code on this host, and compared bit-for-bit
  against the KIR reference interpreter.

  Everything else in this wave measures bytes. Bytes are the right unit for
  \"did the backend emit ADDSS or ADDSD\", and they cannot answer \"does the
  program compute the number the language says it computes\". A byte golden can
  only assert the sequences someone thought to write down; a backend that
  emitted every right opcode against the wrong register, or in the wrong order,
  produces goldens that pass and answers that are wrong. This namespace runs the
  code and compares the number.

  The comparison is against `kotoba.kir/execute` -- the oracle, which is the
  definition -- rather than against numbers written down here, so a case cannot
  be made to pass by adjusting an expectation. Where an expectation IS written
  down it is a binary32 bit pattern with its hex beside it, because that is
  what distinguishes the two widths: 0.1f + 0.2f is 0x3E99999A in binary32 and
  0x3FD3333333333334 in binary64, and no amount of printing shows the
  difference.

  Decided by kotoba-lang docs/adr/ADR-kotoba-floating-point-on-native.md."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.atomic-output :as atomic-output]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [kotoba.sema :as sema]
            [kototama.native.executor :as executor]
            [kotoba.artifact.runtime-identity :as runtime-identity]
            [kotoba.verifier.signing :as signing]))

(defn- target []
  (if (contains? #{"aarch64" "arm64"} (.toLowerCase (System/getProperty "os.arch")))
    :aarch64-kotoba-v1
    :x86_64-kotoba-v1))

(defonce ^:private measured-runtime
  (delay
    (let [{:keys [runtime loader-bytes]} (executor/measure-runtime)
          loader (doto (java.io.File/createTempFile "kotoba-f32-loader-" "")
                   (.deleteOnExit))]
      (atomic-output/write-bytes! (.getPath loader) loader-bytes {:executable? true})
      {:runtime runtime :loader-path (.getPath loader)})))

(defn- run-native
  "Compile, sign, verify and EXECUTE `source` on this host, returning the i64
  the entry produced."
  [source]
  (let [artifact (:artifact (compiler/compile-source source (target) {:allow #{}}))
        key (signing/generate-keypair)
        envelope (signing/sign artifact key {:not-before 1000 :expires 2000})
        trust {:format :kotoba.trust/v1 :trusted-signers #{(:signer key)}
               :revoked-signers #{} :revoked-artifacts #{}}
        {:keys [runtime loader-path]} @measured-runtime
        trust (assoc trust :trusted-runtime-sha256
                     #{(runtime-identity/identity-sha256 runtime)})
        result (executor/execute
                envelope trust {:allow #{}} {:args []}
                {:now 1500 :entry 'main :runtime runtime
                 :loader-path loader-path})]
    (is (= :ok (get-in result [:evidence :status]))
        (str "native execution must succeed: " (pr-str (:evidence result))))
    (get-in result [:evidence :result])))

(defn- run-oracle
  "The same source through the KIR reference interpreter, which is the
  definition the machine code has to agree with."
  [source]
  (ir/execute (ir/lower (sema/analyze source)) 'main []))

(defn- both
  "Run `source` on the machine and on the oracle and assert they agree. Returns
  the value so a caller can additionally pin it as a bit pattern.

  `main` takes no arguments -- the frontend requires that of an entry -- so the
  operands are literal patterns inside the source and the helper that consumes
  them is what carries the parameters. That is also the shape the fixture in
  examples/ has, and the shape a kernel has: the words come from somewhere else
  and a small function does the arithmetic."
  [source]
  (let [native (run-native source)
        oracle (run-oracle source)]
    (is (= oracle native)
        (str "native and the KIR oracle must agree bit-for-bit on " source))
    native))

(defn- unary
  "`(op (f32-from-bits <pattern>))` to bits, as a complete zero-arg module."
  [op pattern]
  (str "(defn step [a :i64] :i64 (f32-to-bits (" op " (f32-from-bits a))))"
       "(defn main [] :i64 (step " pattern "))"))

(defn- binary
  "`(op (f32-from-bits <l>) (f32-from-bits <r>))` to bits."
  [op l r]
  (str "(defn step [a :i64 b :i64] :i64"
       "  (f32-to-bits (" op " (f32-from-bits a) (f32-from-bits b))))"
       "(defn main [] :i64 (step " l " " r "))"))

(defn- predicate
  "`(if (op ...) 1 0)`, so a comparison's 0/1 word crosses the boundary."
  [op l r]
  (str "(defn step [a :i64 b :i64] :i64"
       "  (if (" op " (f32-from-bits a) (f32-from-bits b)) 1 0))"
       "(defn main [] :i64 (step " l " " r "))"))

;; Binary32 patterns, as the signed i32s `f32-to-bits` yields.
(def ^:private bits-one 0x3F800000)
(def ^:private bits-two 0x40000000)
(def ^:private bits-three 0x40400000)
(def ^:private bits-four 0x40800000)
(def ^:private bits-tenth 0x3DCCCCCD)
(def ^:private bits-fifth 0x3E4CCCCD)
(def ^:private bits-minus-one -1082130432)   ; 0xBF800000
(def ^:private bits-qnan 2143289344)         ; 0x7FC00000

(deftest f32-arithmetic-executes-and-agrees-with-the-oracle
  ;; 0.1f + 0.2f. The single most useful case in this file: in binary32 the sum
  ;; is exactly 0x3E99999A. In binary64 it is 0x3FD3333333333334, which shares
  ;; no low bits with it, so a backend that reached ADDSD cannot land here by
  ;; accident.
  (testing "0.1f + 0.2f is binary32, not binary64"
    (is (= 0x3E99999A (both (binary "f32-add" bits-tenth bits-fifth)))))
  (testing "the four arithmetic operations"
    (is (= 0x40A00000 (both (binary "f32-add" bits-two bits-three))) "5.0f")
    (is (= bits-minus-one (both (binary "f32-sub" bits-two bits-three))) "-1.0f")
    (is (= 0x40C00000 (both (binary "f32-mul" bits-two bits-three))) "6.0f")
    (is (= 0x3F000000 (both (binary "f32-div" bits-one bits-two))) "0.5f")))

(deftest f32-sign-and-sqrt-execute
  (is (= bits-one (both (unary "f32-abs" bits-minus-one))))
  (is (= bits-minus-one (both (unary "f32-neg" bits-one))))
  (is (= -2147483648 (both (unary "f32-neg" 0)))
      "negating +0.0f gives -0.0f, a distinct pattern")
  (is (= bits-two (both (unary "f32-sqrt" bits-four))) "sqrt(4.0f) = 2.0f"))

(deftest a-negative-result-keeps-the-word-sign-extended
  ;; The invariant the whole representation rests on. `f32-to-i64-bits` in the
  ;; oracle yields a SIGNED i32, so a machine that left the result
  ;; zero-extended after `movd` / `FMOV W` returns 3212836864 where the oracle
  ;; returns -1082130432 -- the same low 32 bits and a different i64.
  ;;
  ;; Measured, by deleting the sign extension from `a64-f32-binary`: this case
  ;; fails with exactly `(not (= -1082130432 3212836864))`. kotoba-native's byte
  ;; goldens catch that same break, because they assert the narrowing move is
  ;; immediately followed by an extension -- so this is not a hole they leave,
  ;; it is the same hole from the other side. What running adds is the class the
  ;; goldens cannot enumerate: a sequence whose bytes are all individually right
  ;; and whose ANSWER is wrong (operands swapped, the wrong register read, a
  ;; conversion that rounds the way the other width would).
  (let [result (both (binary "f32-sub" bits-one bits-two))]
    (is (= -1082130432 result) "-1.0f as a SIGNED i32, not 3212836864")
    (is (neg? result) "and therefore negative as an i64")))

(deftest f32-comparisons-execute-and-nan-is-unordered
  (is (= 1 (both (predicate "f32-lt" bits-one bits-two))))
  (is (= 0 (both (predicate "f32-lt" bits-two bits-one))))
  (is (= 1 (both (predicate "f32-eq" bits-one bits-one))))
  (is (= 0 (both (predicate "f32-eq" bits-qnan bits-qnan)))
      "NaN is not equal to itself")
  (is (= 0 (both (predicate "f32-lt" bits-qnan bits-one)))
      "every ordered comparison against NaN is false")
  (is (= 0 (both (predicate "f32-gt" bits-qnan bits-one))))
  (is (= 0 (both (predicate "f32-le" bits-qnan bits-one))))
  (is (= 0 (both (predicate "f32-ge" bits-qnan bits-one))))
  (is (= 1 (both (predicate "f32-unordered" bits-qnan bits-one)))
      "and f32-unordered is what says so")
  (is (= 0 (both (predicate "f32-unordered" bits-one bits-one)))))

(deftest width-conversions-execute
  (is (= bits-tenth
         (both (str "(defn step [a :i64] :i64"
                    "  (f32-to-bits (f64-to-f32-rounded (f32-to-f64-exact (f32-from-bits a)))))"
                    "(defn main [] :i64 (step " bits-tenth "))")))
      "widening is exact, so it round-trips")
  (is (= 0x4B800000
         (both (str "(defn step [a :i64] :i64 (f32-to-bits (i64-to-f32-rounded a)))"
                    "(defn main [] :i64 (step 16777217))")))
      "16777217 is not representable in binary32; RNE gives 16777216.0f")
  (is (= bits-one
         (both (str "(defn step [a :i64] :i64 (f32-to-bits (i64-to-f32-rounded a)))"
                    "(defn main [] :i64 (step 1))"))))
  (is (= 4607182418800017408                ; 0x3FF0000000000000, 1.0d
         (both (str "(defn step [a :i64] :i64 (f64-to-bits (i64-to-f64-rounded a)))"
                    "(defn main [] :i64 (step 1))")))
      "the f64 conversion fills the whole word and is not narrowed"))

(deftest the-dot-product-shape-executes
  ;; What a dequantised inference kernel looks like, end to end:
  ;; 1*1 + 2*2 + 3*3 = 14.0f = 0x41600000, accumulated with NO contraction --
  ;; each multiply rounds before the add sees it.
  (is (= 0x41600000
         (both (str "(defn fma [acc :i64 x :i64 y :i64] :i64"
                    "  (f32-to-bits (f32-add (f32-from-bits acc)"
                    "                        (f32-mul (f32-from-bits x) (f32-from-bits y)))))"
                    "(defn main [] :i64"
                    "  (fma (fma (fma 0 " bits-one " " bits-one ") "
                    bits-two " " bits-two ") " bits-three " " bits-three "))"))))
  (is (= 0x406F7751 (both (unary "f32-sqrt" 0x41600000)))
      "sqrt(14.0f) = 3.7416575f. Written down wrong the first time and caught by
       the oracle comparison, which is the reason that comparison exists."))

(deftest scanned-counts-are-nonzero
  ;; This suite is worthless if the executor silently declined every case, and
  ;; a deftest full of skipped work looks exactly like one full of passes.
  (is (contains? #{:aarch64-kotoba-v1 :x86_64-kotoba-v1} (target))
      "SCANNED: a native target was selected for this host")
  (is (some? (:runtime @measured-runtime))
      "SCANNED: the native runtime was measured, so execution really ran"))
