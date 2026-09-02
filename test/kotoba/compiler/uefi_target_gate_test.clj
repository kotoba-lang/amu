(ns kotoba.compiler.uefi-target-gate-test
  "boot: who may name the UEFI firmware boundary.

  `kotoba.compiler.frontend` admits privileged operations by arity and has
  never seen a target keyword, which is correct for it and wrong for these
  four: outside the target whose entry contract establishes the boundary,
  `kernel-system-table` reads a slot nobody wrote and everything derived from
  it is a wild pointer. The gate is here, and its failure mode is a compile
  that refuses rather than a machine that faults."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.uefi-operations :as uefi]))

(def ^:private bodies
  {'kernel-system-table "(defn main [] (kernel-system-table))"
   'kernel-load-ptr     "(defn main [] (kernel-load-ptr 4096 64))"
   'kernel-uefi-call2   "(defn main [] (kernel-uefi-call2 4096 8 4096 0))"
   'kernel-jump-to      "(defn main [] (kernel-jump-to 1048576 4096))"
   ;; boot-lit: the two wider calls. Their operands are literals rather than
   ;; parameters because this frontend caps a FUNCTION's parameter count at
   ;; the ABI's argument registers -- a six-parameter wrapper is refused as
   ;; "function parameters exceed ABI-supported arity", which has nothing to do
   ;; with the gate.
   'kernel-uefi-call4   "(defn main [] (kernel-uefi-call4 4096 8 1 2 3 4))"
   'kernel-uefi-call6   "(defn main [] (kernel-uefi-call6 4096 8 1 2 3 4 5 6))"})

(deftest the-set-is-closed-and-named
  (is (= '#{kernel-system-table kernel-load-ptr kernel-uefi-call2 kernel-jump-to
            kernel-uefi-call4 kernel-uefi-call6}
         uefi/uefi-only-operations))
  (is (= :x86_64-aiueos-uefi-v1 uefi/uefi-target))
  (is (= (sort (keys bodies)) (sort uefi/uefi-only-operations))
      "every gated operation has a case below"))

(deftest each-operation-is-refused-outside-the-firmware-target
  (doseq [[op source] bodies
          target [:x86_64-kotoba-v1 :x86_64-linux-kotoba-v1
                  :x86_64-aiueos-kernel-v1]]
    (testing (str op " on " target)
      (let [thrown (try (compiler/compile-source source target) nil
                        (catch clojure.lang.ExceptionInfo e e))]
        (is (some? thrown) (str op " reached " target))
        (is (= "UEFI firmware operations require the aiueos UEFI target"
               (ex-message thrown)))
        (is (= [op] (:operations (ex-data thrown))))
        (is (= target (:target (ex-data thrown))))))))

(deftest a-head-hidden-in-a-let-is-still-a-head
  ;; kotoba-kir's own admission walk carries this scar: a `let` binding's
  ;; value was never inspected, so the identical operation was gated when
  ;; written directly and admitted when bound. The gate walks the tree.
  (let [thrown (try (compiler/compile-source
                     "(defn main [] (let [p (kernel-load-ptr 4096 64)] p))"
                     :x86_64-kotoba-v1)
                    nil
                    (catch clojure.lang.ExceptionInfo e e))]
    (is (some? thrown))
    (is (= "UEFI firmware operations require the aiueos UEFI target"
           (ex-message thrown)))
    (is (= '[kernel-load-ptr] (:operations (ex-data thrown))))))

(deftest the-firmware-target-admits-all-four
  ;; The other direction, in the same file: a gate that refused everything
  ;; would pass every assertion above.
  (doseq [[op source] bodies]
    (testing (str op " on the firmware target")
      (is (some? (:binary (compiler/compile-source
                           source :x86_64-aiueos-uefi-v1)))
          (str op " must package on the firmware target")))))

(deftest a-module-that-names-none-of-them-is-untouched
  (is (empty? (uefi/operations-used
               {:functions [{:name 'main :params [] :body '(+ 1 2)}]})))
  (is (some? (:binary (compiler/compile-source "(defn main [] 0)"
                                               :x86_64-aiueos-uefi-v1)))))

;; boot-lit ───────────────────────────────────────────────────────────────────

(def ^:private wide-call-bodies
  ;; Two parameters and a tail of constants: a six-parameter function is
  ;; refused as "function parameters exceed ABI-supported arity", which would
  ;; make these green for a reason that has nothing to do with the gate.
  {'kernel-uefi-call4
   "(defn f [a b] (kernel-uefi-call4 a b 1 2 3 4))
    (defn main [] (f 4096 8))"
   'kernel-uefi-call6
   "(defn f [a b] (kernel-uefi-call6 a b 1 2 3 4 5 6))
    (defn main [] (f 4096 8))"})

(deftest boot-lit-the-wider-calls-are-gated-with-the-narrow-one
  ;; The set membership is asserted by `the-set-is-closed-and-named` above,
  ;; which also requires a case in `bodies` for every gated head. What this
  ;; adds is the wider calls in a FUNCTION rather than in `main`, which is the
  ;; shape a real call site has.
  (doseq [[op source] wide-call-bodies
          target [:x86_64-kotoba-v1 :x86_64-linux-kotoba-v1
                  :x86_64-aiueos-kernel-v1]]
    (testing (str op " on " target)
      (let [thrown (try (compiler/compile-source source target) nil
                        (catch clojure.lang.ExceptionInfo e e))]
        (is (some? thrown) (str op " reached " target))
        (is (= "UEFI firmware operations require the aiueos UEFI target"
               (ex-message thrown)))
        (is (= [op] (:operations (ex-data thrown)))))))
  (testing "and both package on the firmware target"
    (doseq [[op source] wide-call-bodies]
      (is (some? (:binary (compiler/compile-source
                           source :x86_64-aiueos-uefi-v1)))
          (str op)))))

(def ^:private literal-bodies
  {'ucs2 "(defn main [] (ucs2 \"AIUEOS\"))"
   'guid "(defn main [] (guid \"5B1B31A1-9562-11D2-8E3F-00A0C969723B\"))"
   'bytes-literal "(defn main [] (bytes-literal \"deadbeef\"))"
   'bytes-literal-length "(defn main [] (bytes-literal-length \"deadbeef\"))"})

(deftest boot-lit-a-literal-pool-is-gated-to-the-native-aiueos-targets
  ;; A WIDER set than the firmware boundary's, and a different sentence.
  ;; `kernel-uefi-call2` on a Linux target is a program that would fault;
  ;; `(guid "...")` on the Wasm target is a program the backend has no way to
  ;; compile at all, and saying "require the aiueos UEFI target" about it would
  ;; name the wrong requirement.
  (is (= '#{ucs2 guid bytes-literal bytes-literal-length}
         uefi/rodata-literal-operations))
  (is (= #{:x86_64-aiueos-uefi-v1 :x86_64-aiueos-kernel-v1}
         uefi/rodata-literal-targets))
  (doseq [[op source] literal-bodies
          target [:x86_64-kotoba-v1 :x86_64-linux-kotoba-v1
                  :aarch64-aiueos-kernel-v1]]
    (testing (str op " on " target)
      (let [thrown (try (compiler/compile-source source target) nil
                        (catch clojure.lang.ExceptionInfo e e))]
        (is (some? thrown) (str op " reached " target))
        (is (= "read-only literals require a native aiueos x86-64 target"
               (ex-message thrown)))
        (is (= [op] (:operations (ex-data thrown))))))))

(deftest boot-lit-the-admitted-targets-actually-admit-them
  ;; The other direction, in the same file: a gate that refused everything
  ;; would pass every assertion above. Both admitted targets, so neither is
  ;; carried by the other.
  (doseq [target uefi/rodata-literal-targets
          [op source] literal-bodies]
    (testing (str op " on " target)
      (is (some? (:binary (compiler/compile-source source target)))
          (str op " must compile on " target)))))

(deftest boot-lit-a-literal-hidden-in-a-let-is-still-a-literal
  (let [thrown (try (compiler/compile-source
                     "(defn main [] (let [p (ucs2 \"AIUEOS\")] p))"
                     :x86_64-kotoba-v1)
                    nil
                    (catch clojure.lang.ExceptionInfo e e))]
    (is (some? thrown))
    (is (= "read-only literals require a native aiueos x86-64 target"
           (ex-message thrown)))
    (is (= '[ucs2] (:operations (ex-data thrown))))))
