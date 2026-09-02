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
  (:require [clojure.walk :as walk]
            [kotoba.kir.target :as target-profile]))

(def uefi-target :x86_64-aiueos-uefi-v1)

(def uefi-only-operations
  '#{kernel-system-table kernel-load-ptr kernel-uefi-call2 kernel-jump-to
     ;; boot-lit: the two wider calls. Same gate, same reason -- they call
     ;; through a pointer read out of firmware memory, and the only difference
     ;; from `kernel-uefi-call2` is how many arguments go with it.
     kernel-uefi-call4 kernel-uefi-call6})

;; boot-lit: read-only literals are gated too, but not to the same target and
;; not for the same reason.
;;
;; None of `ucs2`, `guid` or `bytes-literal` is dangerous. What they need is a
;; BACKEND that places a literal pool and an instruction that reaches it, and
;; only the x86-64 native backend has one -- `lea dst,[rip+disp32]`, with the
;; pool at the end of `.text` so no relocation and no fourth section is
;; required. On the Wasm, kotoba-script and CLJS backends the heads would lower
;; to nothing at all.
;;
;; So this list is the set of targets whose backend can answer, and it is
;; deliberately wider than one: the aiueos KERNEL targets can place a pool in
;; their own `.text` too, and a kernel that has to name a GUID or a UTF-16
;; string has the same problem a bootloader does. The AArch64 kernel target is
;; absent because kotoba-mir refuses the operation there (`adrp`+`add` splits
;; the address at a 4 KiB page boundary and the layout pass does not model it)
;; -- an admission of a gap, and refusing here says so one layer earlier and
;; with the target named.
(def rodata-literal-operations
  '#{ucs2 guid bytes-literal bytes-literal-length})

;; Derived from `kotoba.kir.target`'s own profiles rather than written out, so
;; a new aiueos x86-64 target does not silently lack the literal pool its
;; backend already has. The two conditions are the two things the backend
;; needs: an x86-64 ISA (`lea …,[rip+disp32]`) and an aiueos OS (a `.text` the
;; pool can sit at the end of, with no dynamic loader to relocate it).
(def rodata-literal-targets
  (into #{}
        (keep (fn [[name profile]]
                (when (and (= :x86_64 (:isa profile))
                           (= :aiueos (:os profile))
                           (contains? #{:firmware :kernel} (:execution profile)))
                  name)))
        target-profile/profiles))

(defn heads-used
  "The heads from OPERATIONS this module names, as a sorted vector. Walks the
  whole tree rather than the top level of each body: a head bound by a `let` is
  still a head, which is how `u32-wrap` once reached a backend that had gated
  it (kotoba-kir's own admission walk carries the same scar)."
  [operations module]
  (let [found (volatile! #{})]
    (walk/postwalk
     (fn [form]
       (when (and (seq? form) (contains? operations (first form)))
         (vswap! found conj (first form)))
       form)
     (:functions module))
    (vec (sort @found))))

(defn operations-used
  "The UEFI-only heads this module names."
  [module]
  (heads-used uefi-only-operations module))

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

(defn reject-rodata-literals-outside-native-targets!
  "boot-lit: throw unless TARGET's backend can place a literal pool. Returns
  MODULE so it can sit in a `let` chain beside the refusal above.

  A separate function rather than a second clause inside that one because the
  two refusals are different sentences. `kernel-uefi-call2` on a Linux target
  is a program that would fault; `(guid \"...\")` on the Wasm target is a
  program the backend has no way to compile, and saying `require the aiueos
  UEFI target` about it would name the wrong requirement."
  [target module]
  (let [used (heads-used rodata-literal-operations module)]
    (when (and (seq used) (not (contains? rodata-literal-targets target)))
      (throw (ex-info "read-only literals require a native aiueos x86-64 target"
                      {:phase :target :target target
                       :admitted (vec (sort rodata-literal-targets))
                       :operations used})))
    module))
