(ns kotoba.compiler.uefi-operations
  "boot: which target may name the UEFI firmware boundary.

  `kotoba.compiler.frontend` admits privileged operations by arity and by
  nothing else -- it has never seen a target keyword, which is why
  `kernel-write-cr3` is admitted for `x86_64-linux-kotoba-v1` too. That was
  survivable while every privileged operation named an instruction a kernel
  runs on its own machine. It is not survivable for these four.

  `kernel-system-table` reads a context slot that only the two-arity EFI entry
  shim writes; under any other entry contract it reads a zero and every
  address derived from it is a wild pointer. `kernel-load-ptr` is an unchecked
  64-bit read. `kernel-uefi-call2` calls through a pointer read out of
  firmware memory. `kernel-jump-to` does not return. Outside the target whose
  entry contract establishes the boundary, none of them means anything, and
  the failure mode of all four is a machine that faults rather than a compile
  that refuses.

  So this is the target gate, and it lives here rather than in the frontend
  because this is the layer that sees a target keyword next to a module. Both
  compile routes call it -- `kotoba.compiler.core` on the JVM and
  `kotoba.compiler.nbb.cli` on the JDK-free one -- because a gate on one route
  is not a gate."
  (:require [clojure.walk :as walk]))

(def uefi-target :x86_64-aiueos-uefi-v1)

(def uefi-only-operations
  '#{kernel-system-table kernel-load-ptr kernel-uefi-call2 kernel-jump-to})

(defn operations-used
  "The UEFI-only heads this module names, as a sorted vector. Walks the whole
  tree rather than the top level of each body: a head bound by a `let` is
  still a head, which is how `u32-wrap` once reached a backend that had gated
  it (kotoba-kir's own admission walk carries the same scar)."
  [module]
  (let [found (volatile! #{})]
    (walk/postwalk
     (fn [form]
       (when (and (seq? form) (contains? uefi-only-operations (first form)))
         (vswap! found conj (first form)))
       form)
     (:functions module))
    (vec (sort @found))))

(defn reject-outside-uefi-target!
  "Throw unless TARGET is the one whose entry contract establishes the
  firmware boundary. Returns MODULE so it can sit in a `let` chain."
  [target module]
  (let [used (operations-used module)]
    (when (and (seq used) (not= uefi-target target))
      (throw (ex-info "UEFI firmware operations require the aiueos UEFI target"
                      {:phase :target :target target
                       :required uefi-target
                       :operations used})))
    module))
