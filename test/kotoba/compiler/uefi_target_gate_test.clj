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
   'kernel-jump-to      "(defn main [] (kernel-jump-to 1048576 4096))"})

(deftest the-set-is-closed-and-named
  (is (= '#{kernel-system-table kernel-load-ptr kernel-uefi-call2 kernel-jump-to}
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
