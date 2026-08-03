(ns kotoba.compiler.kernel-region-provenance-test
  "A kernel memory base must NAME a region, not be conjured out of memory.

  The native backends already emit a real bounds check before every
  `kernel-load-u8`/`kernel-store-u8`/... : length is compared against the op's
  static maximum, base against zero, index against length, and a violation
  reaches `UD2`/`brk` before the access. That constrains the offset within a
  window and says nothing about the window. Before this pass the base was any
  `:i64` the program could produce, so a byte read out of attacker-controlled
  data could be used directly as a physical address in ring 0.

  What is enforced here is ROOTEDNESS: every base resolves to a literal, to
  `kernel-boot-info`, or to a parameter. Narrowing a validated region to a
  sub-window is what real kernel code does, so it must be expressible, and it
  is spelled `kernel-subregion` -- whose offset the native backends bound
  with an emitted check (see kernel-subregion-test). Bare `(+ base offset)`
  in a base position is rejected here as a result."
  (:require [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.frontend :as frontend]))

(defn- provenance-rejection
  "The rejection message when SOURCE is refused for region provenance, or nil
  when it is admitted. Rethrows any OTHER rejection so a test can never pass
  because the source was malformed for an unrelated reason."
  [source]
  (try (frontend/analyze source) nil
       (catch Exception e
         (if (= :kotoba.error/kernel-region-provenance
                (:kotoba.error/code (ex-data e)))
           (.getMessage e)
           (throw e)))))

(deftest a-base-conjured-from-memory-content-is-rejected
  (testing "the shape with no legitimate counterpart: loaded byte as address"
    (is (some? (provenance-rejection
                "(defn f [buf length]
                   (kernel-load-u8 (kernel-load-u8 buf length 0) 4096 0))
                 (defn main [] 0)"))))
  (testing "and on the store side"
    (is (some? (provenance-rejection
                "(defn f [buf length]
                   (kernel-store-u8 (kernel-load-u8 buf length 0) 4096 0 1))
                 (defn main [] 0)")))))

(deftest the-shapes-aiueos-actually-uses-stay-admitted
  (testing "fixed physical address"
    (is (nil? (provenance-rejection
               "(defn main [] (kernel-load-u8 167772160 4096 0))"))))
  (testing "base threaded through a recursive helper from an ABI parameter"
    (is (nil? (provenance-rejection
               "(defn step [base length index hash]
                  (if (= index length) hash
                    (step base length (+ index 1)
                          (* (bit-xor hash (kernel-load-u8 base length index))
                             16777619))))
                (defn main [] 0)"))))
  (testing "let-bound alias of a parameter"
    (is (nil? (provenance-rejection
               "(defn f [base length] (let [b base] (kernel-load-u8 b length 0)))
                (defn main [] 0)"))))
  (testing "kernel-boot-info"
    (is (nil? (provenance-rejection
               "(defn main [] (kernel-load-u8 (kernel-boot-info) 4096 0))"))))
  (testing "sub-window of a validated region, the pattern in six aiueos
            objects -- now spelled as the checked narrowing, since bare `+`
            in a base position is rejected (kernel-subregion-test)"
    (is (nil? (provenance-rejection
               "(defn fnv [base length] (kernel-load-u8 base length 0))
                (defn f [base length] (fnv (kernel-subregion base length 48 16) 16))
                (defn main [] 0)")))))

(deftest taint-propagates-through-call-sites
  (testing "a callee's base parameter constrains what callers may pass"
    (is (some? (provenance-rejection
                "(defn sink [base length] (kernel-load-u8 base length 0))
                 (defn f [buf length] (sink (kernel-load-u8 buf length 0) 4096))
                 (defn main [] 0)")))
    (testing "which would otherwise be the hole the callee's own check closed"
      (is (nil? (provenance-rejection
                 "(defn sink [base length] (kernel-load-u8 base length 0))
                  (defn f [base length] (sink base length))
                  (defn main [] 0)"))))))

(deftest report-names-the-abi-boundary
  (let [hir (frontend/analyze
             "(defn read-byte [base length index] (kernel-load-u8 base length index))
              (defn entry [base length] (read-byte base length 0))
              (defn main [] (kernel-load-u8 167772160 4096 0))")
        report (frontend/kernel-region-report (:functions hir))]
    (testing "literal windows are enumerated"
      (is (contains? (:literal-bases report) 167772160)))
    (testing "a base parameter no internal call supplies is the trust boundary"
      (is (= '[base] (get (:abi-boundary report) 'entry))
          "the C kernel hands `entry` its region; that is unverifiable here")
      (is (nil? (get (:abi-boundary report) 'read-byte))
          "an internally-supplied parameter is not a boundary"))))

(deftest modules-without-kernel-ops-are-untouched
  (is (nil? (provenance-rejection "(defn main [] (+ 1 2))"))))
