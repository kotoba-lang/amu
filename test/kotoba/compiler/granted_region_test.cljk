(ns kotoba.compiler.granted-region-test
  "granted regions: the slice memory family on a target that is not aiueos.

  This is the pair that says the admission is an admission and not a hole.
  `test/fixtures/granted-region-sum.kotoba` compiles for `aarch64`, and three
  neighbours do not -- each refused with its OWN sentence, because they are
  three different problems and a caller reading the report should not have to
  guess which one it wrote.

  ⚠ WHAT THIS FILE CANNOT SAY. It compiles; it does not execute. That was
  measured outside this repository on 2026-09-09: the fixture's `sum-bytes`
  was extracted with `amu extract-native`, assembled, and CALLED from C with a
  real buffer and a context block carrying fuel at [x7+8]. 64 bytes summed to
  2080, a granted length of 10 over a 64-byte region summed to 55, an empty
  region answered 0, and four 0xFF bytes summed to 1020 rather than to a
  negative. The reproduction is in that order: compile, `extract-native
  --symbol sum-bytes`, `.byte` under a label, `clang -c -target
  arm64-apple-macos`, call as `int64_t f(int64_t,...,void *)` -- the operands
  arrive in x0.. and the eighth argument register is the context."
  (:require [kotoba.lang.text] [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]))

(def ^:private fixture (slurp "test/fixtures/granted-region-sum.kotoba"))

(defn- compiled [source]
  (try {:ok true :artifact (:artifact (compiler/compile-source source :aarch64-kotoba-v1 {}))}
       (catch clojure.lang.ExceptionInfo e
         {:ok false :message (ex-message e) :data (ex-data e)})))

(deftest a-region-granted-by-the-caller-compiles-for-a-hosted-target
  (let [result (compiled fixture)]
    (is (:ok result)
        (str "the fixture must compile for aarch64: " (:message result)))
    (is (seq (:code (:artifact result))) "and it must emit real code")))

(deftest a-literal-base-is-refused-on-a-hosted-target
  ;; The frontend ADMITS a literal base -- naming MMIO is the job on aiueos --
  ;; so this refusal is the verifier's own, and it has to be, or the admission
  ;; above would have opened the whole address space instead of one region.
  (let [result (compiled (kotoba.lang.text/replace
                          fixture
                          "(defn sum-bytes [base :i64 length :i64]\n  (sum-from (slice-of-u8 base length) 0 0))"
                          "(defn sum-bytes [length :i64]\n  (sum-from (slice-of-u8 4096 length) 0 0))"))]
    (is (false? (:ok result)))
    (is (= "region base must be granted by the caller, not chosen by the program"
           (:message result))
        "the refusal names the problem, not merely the target")))

(deftest a-computed-base-is-refused-earlier-and-differently
  ;; The frontend's own provenance rule, which this admission did not touch.
  ;; A different sentence for a different problem: this program did not merely
  ;; choose an address, it built one.
  (let [result (compiled (kotoba.lang.text/replace
                          fixture
                          "(slice-of-u8 base length)"
                          "(slice-of-u8 (+ base 8) length)"))]
    (is (false? (:ok result)))
    (is (= "slice base must name a region, not compute one" (:message result)))))

(deftest the-byte-window-family-is-still-aiueos-only
  ;; That is a SURFACE-SIZE decision and not a property -- a parameter-based
  ;; window would be exactly as safe as a parameter-based slice. Asserted so
  ;; that widening it later is a deliberate act with a red test in front of it.
  (let [result (compiled "(ns w (:export [go]))
                          (defn go [base :i64] (kernel-load-u8 base 100 0))")]
    (is (false? (:ok result)))
    (is (= "bounded kernel memory operation requires the aiueos kernel target"
           (:message result)))))

(deftest the-three-refusals-are-three-different-sentences
  ;; The point of the three tests above, asserted as one fact: collapsing any
  ;; two of them would let a program start being refused for the wrong reason
  ;; without anything going red.
  (let [messages (into #{}
                       (map (fn [source] (:message (compiled source))))
                       [(kotoba.lang.text/replace
                         fixture
                         "(defn sum-bytes [base :i64 length :i64]\n  (sum-from (slice-of-u8 base length) 0 0))"
                         "(defn sum-bytes [length :i64]\n  (sum-from (slice-of-u8 4096 length) 0 0))")
                        (kotoba.lang.text/replace fixture "(slice-of-u8 base length)"
                                                "(slice-of-u8 (+ base 8) length)")
                        "(ns w (:export [go]))
                         (defn go [base :i64] (kernel-load-u8 base 100 0))"])]
    (is (= 3 (count messages)) (str "SCANNED distinct refusals: " (pr-str messages)))))
