(ns kotoba.compiler.i64-bitwise-test
  "ADR-2607254600 D1/D2: 64-bit shifts and the missing bitwise ops.

  `bit-and`/`bit-xor` were already `i64.and`/`i64.xor` while the only shifts
  were 32-bit, so a 64-bit lane rotation -- the body of Keccak-f[1600] and the
  natural shape of u256 limb arithmetic -- could not be written. These tests
  pin the semantics against `ir/execute` (the interpreter oracle) and pin the
  emitted opcodes, so a future refactor cannot silently change either."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.frontend :as frontend]
            [kotoba.kir :as ir]))

(defn- oracle
  "Evaluate `main` through the IR interpreter."
  [body]
  (let [source (str "(ns t) (defn main [] " body ")")]
    (ir/execute (ir/lower (:hir (compiler/check-source source))) 'main [])))

(defn- rejection [body]
  (try (compiler/check-source (str "(ns t) (defn main [] " body ")")) nil
       (catch clojure.lang.ExceptionInfo e (ex-message e))))

(defn- wasm-hex [body]
  (let [source (str "(ns t) (defn main [] " body ")")
        bytes (:bytes (compiler/compile-source source :wasm32-kotoba-v1))]
    (apply str (map #(format "%02x" (bit-and (int %) 0xff)) bytes))))

;; --- semantics -------------------------------------------------------------

(deftest bit-or-and-not-match-jvm-semantics
  (testing "bit-or is a real i64 or, not a derivation"
    (is (= 0xF0F0 (oracle "(bit-or 0xF000 0x00F0)")))
    (is (= -1 (oracle "(bit-or -1 0)")))
    (is (= 0 (oracle "(bit-or 0 0)"))))
  (testing "bit-not is a full 64-bit complement"
    (is (= -1 (oracle "(bit-not 0)")))
    (is (= 0 (oracle "(bit-not -1)")))
    (is (= (bit-not 42) (oracle "(bit-not 42)")))))

(deftest i64-shifts-cover-the-full-width
  (testing "shift-left reaches the sign bit, which no 32-bit shift can"
    (is (= Long/MIN_VALUE (oracle "(i64-shift-left 1 63)")))
    (is (= 0x100000000 (oracle "(i64-shift-left 1 32)")))
    (is (= 1 (oracle "(i64-shift-left 1 0)"))))
  (testing "shift-right is arithmetic (sign-propagating)"
    (is (= -1 (oracle "(i64-shift-right -1 63)")))
    (is (= -1 (oracle "(i64-shift-right -8 3)")))
    (is (= 1 (oracle "(i64-shift-right 0x100000000 32)"))))
  (testing "u64-shift-right is logical (zero-filling)"
    (is (= 1 (oracle "(u64-shift-right -1 63)")))
    (is (= 0x1FFFFFFFFFFFFFFF (oracle "(u64-shift-right -1 3)")))
    (is (= 1 (oracle "(u64-shift-right 0x100000000 32)"))))
  (testing "arithmetic and logical right shift differ on negatives"
    (is (not= (oracle "(i64-shift-right -1 1)")
              (oracle "(u64-shift-right -1 1)")))))

(deftest rotation-is-derivable-from-the-new-primitives
  ;; ADR-2607254600 records rotation as derivable rather than a prerequisite:
  ;; with a literal count n, 64-n is also a literal. Keccak's lane rotations
  ;; are exactly this shape, so prove the identity rather than assert it.
  (letfn [(rotl [x n] (str "(bit-or (i64-shift-left " x " " n ")"
                           " (u64-shift-right " x " " (- 64 n) "))"))]
    (doseq [n [1 7 32 63]]
      (is (= (Long/rotateLeft 0x0123456789ABCDEF n)
             (oracle (rotl "0x0123456789ABCDEF" n)))
          (str "rotl by " n " does not match Long/rotateLeft"))
      (is (= (Long/rotateLeft -1 n) (oracle (rotl "-1" n)))))))

;; --- admission -------------------------------------------------------------

(deftest shift-count-admission-is-fail-closed
  (testing "a literal count in [0,63] is admitted"
    (is (nil? (rejection "(i64-shift-left 1 0)")))
    (is (nil? (rejection "(i64-shift-left 1 63)"))))
  (testing "a count outside the width is rejected, not masked"
    (is (some? (rejection "(i64-shift-left 1 64)")))
    (is (some? (rejection "(i64-shift-left 1 -1)"))))
  (testing "a non-literal count is rejected"
    ;; Wasm would mask it modulo 64, so this is an admission choice, not a
    ;; safety requirement -- but it must be enforced, not merely documented.
    (is (some? (rejection "(i64-shift-left 1 (+ 1 1))"))))
  (testing "arity is enforced"
    (is (some? (rejection "(i64-shift-left 1)")))
    (is (some? (rejection "(bit-not 1 2)")))
    (is (some? (rejection "(bit-or 1)")))))

;; --- emitted encoding ------------------------------------------------------

(deftest emitted-opcodes-are-the-canonical-i64-instructions
  (testing "shifts emit the i64 opcodes with no wrap/extend around them"
    ;; The i32 shifts wrap to i32 (0xa7) and extend back (0xac/0xad). The i64
    ;; forms must not, or they would silently truncate to 32 bits.
    (is (re-find #"86" (wasm-hex "(i64-shift-left 1 3)")))
    (is (re-find #"87" (wasm-hex "(i64-shift-right 1 3)")))
    (is (re-find #"88" (wasm-hex "(u64-shift-right 1 3)")))
    (is (not (re-find #"a7" (wasm-hex "(i64-shift-left 1 3)")))
        "an i64 shift must not wrap its operand to i32"))
  (testing "bit-or emits i64.or"
    (is (re-find #"84" (wasm-hex "(bit-or 1 2)"))))
  (testing "bit-not emits i64.const -1 followed by i64.xor"
    (is (re-find #"427f85" (wasm-hex "(bit-not 1)")))))

;; --- reserved names --------------------------------------------------------

(deftest new-operations-are-reserved-function-names
  (testing "a program cannot shadow the new ops with its own defn"
    (doseq [op ["bit-or" "bit-not" "i64-shift-left" "i64-shift-right"
                "u64-shift-right"]]
      (is (some? (try (compiler/check-source
                       (str "(ns t) (defn " op " [x] x) (defn main [] 1)"))
                      nil
                      (catch clojure.lang.ExceptionInfo e (ex-message e))))
          (str op " must be reserved")))))
