(ns kotoba.compiler.uefi-operations-portable-test
  "The half of `kotoba.compiler.uefi-target-gate-test` that needs no compiler.

  That file drives `kotoba.compiler.core/compile-source`, which is JVM-only, so
  every assertion about this gate ran on one host -- in a namespace whose own
  docstring says `Both compile routes call it … because a gate on one route is
  not a gate`. `kotoba.compiler.nbb.cli` calls
  `reject-outside-uefi-target!` on the JDK-free route, and nothing on that host
  had ever executed it.

  Nothing here compiles anything. The gate's contract is (target, module) ->
  module or throw, and a module is a map, so both hosts can be handed one."
  (:require #?(:clj  [clojure.test :refer [deftest is testing]]
               :cljs [cljs.test :refer [deftest is testing] :include-macros true])
            [kotoba.compiler.uefi-operations :as uefi]))

(defn- module
  "A module shaped the way the gate reads one: `:functions`, walked whole."
  [& bodies]
  {:functions (vec (map-indexed (fn [i b] {:name (symbol (str "f" i))
                                           :params [] :body b})
                                bodies))})

(defn- refusal
  "The ex-data of the refusal, or `:admitted` if the gate let it through."
  [f target m]
  (try (do (f target m) :admitted)
       (catch #?(:clj clojure.lang.ExceptionInfo :cljs :default) e
         (ex-data e))))

(deftest the-two-sets-and-the-target-are-what-both-hosts-see
  ;; Data, and it is the whole basis of both refusals. A host that read a
  ;; different set would gate a different program.
  (is (= '#{kernel-system-table kernel-load-ptr kernel-uefi-call2 kernel-jump-to
            kernel-uefi-call4 kernel-uefi-call6 kernel-scratch-region
            kernel-uefi-alloc-region}
         uefi/uefi-only-operations))
  (is (= '#{ucs2 guid bytes-literal bytes-literal-length kernel-function-address}
         uefi/rodata-literal-operations))
  (is (= :x86_64-aiueos-uefi-v1 uefi/uefi-target))
  (testing "and the literal targets are derived from the profile table, so a
            host that resolved profiles differently would answer differently"
    ;; TWELVE since 2026-09-09: the two aiueos packagers plus every `:native`
    ;; execution profile, on both ISAs. The COUNT is what makes a host that
    ;; resolved profiles differently answer differently -- naming four members
    ;; would still pass on a host that lost the other eight.
    (is (= 12 (count uefi/rodata-literal-targets)))
    (is (every? uefi/rodata-literal-targets
                [:x86_64-aiueos-uefi-v1 :x86_64-aiueos-kernel-v1
                 :x86_64-kotoba-v1 :aarch64-kotoba-v1]))
    (is (= #{:x86_64-aiueos-uefi-v1 :x86_64-aiueos-kernel-v1}
           uefi/function-address-targets))))

(deftest every-gated-head-is-refused-outside-the-firmware-target
  (doseq [op uefi/uefi-only-operations
          target [:x86_64-kotoba-v1 :x86_64-linux-kotoba-v1
                  :x86_64-aiueos-kernel-v1]]
    (testing (str op " on " target)
      (let [data (refusal uefi/reject-outside-uefi-target! target
                          (module (list op 1 2)))]
        (is (= :target (:phase data)))
        (is (= target (:target data)))
        (is (= uefi/uefi-target (:required data)))
        (is (= [op] (:operations data)))))))

(deftest the-firmware-target-admits-them-all
  ;; The other direction, in the same file: a gate that refused everything
  ;; would pass every assertion above.
  (doseq [op uefi/uefi-only-operations]
    (testing (str op)
      (let [m (module (list op 1 2))]
        (is (= m (uefi/reject-outside-uefi-target! uefi/uefi-target m)))))))

(deftest a-head-bound-in-a-let-is-still-a-head
  ;; The scar this gate's docstring names: kotoba-kir's admission walk once
  ;; missed a `let` binding's value, so the identical operation was gated
  ;; written directly and admitted written bound.
  (is (= '[kernel-load-ptr]
         (:operations (refusal uefi/reject-outside-uefi-target!
                               :x86_64-kotoba-v1
                               (module '(let [p (kernel-load-ptr 4096 64)] p)))))))

(deftest a-module-naming-none-of-them-is-untouched
  (let [m (module '(+ 1 2))]
    (is (= [] (uefi/operations-used m)))
    (is (= m (uefi/reject-outside-uefi-target! :x86_64-kotoba-v1 m)))
    (is (= m (uefi/reject-rodata-literals-outside-native-targets!
              :wasm32-browser-v1 m)))))

(deftest the-literal-pool-is-a-different-sentence-and-a-wider-set
  ;; Two refusals, and the point of their being two is that they say different
  ;; things. Asserting the message literal is the assertion: if upstream
  ;; renamed one to the other, only this comparison would notice.
  ;;
  ;; ⚠ THE REFUSING TARGET IS NOW `:wasm32-browser-v1`, not
  ;; `:x86_64-linux-kotoba-v1`. The hosted native targets joined the admitted
  ;; set on 2026-09-09 -- the kexe loader mmaps the code buffer and jumps into
  ;; it, so a pool beside the code is reachable exactly as it is inside an
  ;; image. Wasm is where the heads still lower to nothing at all, which is
  ;; the reason this refusal exists.
  (doseq [op uefi/rodata-literal-operations]
    (testing (str op " on a backend with no pool at all")
      (let [data (refusal uefi/reject-rodata-literals-outside-native-targets!
                          :wasm32-browser-v1 (module (list op "x")))]
        (is (= :target (:phase data)))
        (is (= [op] (:operations data))))))
  (testing "every admitted target admits them, so none carries the others"
    ;; The two families are checked against their OWN target sets, because
    ;; they stopped sharing one in the same change: `kernel-function-address`
    ;; is still refused on AArch64 by `kotoba.mir`, so admitting it here would
    ;; be a green check and a red compile.
    (doseq [target uefi/rodata-literal-targets
            op uefi/rodata-literal-only-operations]
      (let [m (module (list op "x"))]
        (is (= m (uefi/reject-rodata-literals-outside-native-targets! target m))
            (str op " on " target))))
    (doseq [target uefi/function-address-targets
            op uefi/function-address-operations]
      (let [m (module (list op "x"))]
        (is (= m (uefi/reject-rodata-literals-outside-native-targets! target m))
            (str op " on " target))))))

(deftest a-function-address-is-refused-where-a-literal-is-admitted
  ;; The control for the split: on a hosted native target the two families
  ;; disagree, and each says so in its own sentence.
  (let [target :aarch64-kotoba-v1
        lit (module '(bytes-literal "dead"))
        addr (module '(kernel-function-address main))]
    (is (= lit (uefi/reject-rodata-literals-outside-native-targets! target lit)))
    (is (= '[kernel-function-address]
           (:operations (refusal uefi/reject-rodata-literals-outside-native-targets!
                                 target addr))))))

(deftest the-two-gates-disagree-about-the-kernel-target-on-purpose
  ;; Both heads arrived together; one is admitted on the aiueos KERNEL target
  ;; and the other is not, because there the backend's answer for the region is
  ;; WRONG rather than absent.
  (is (contains? uefi/uefi-only-operations 'kernel-scratch-region))
  (is (contains? uefi/rodata-literal-operations 'kernel-function-address))
  (let [kernel :x86_64-aiueos-kernel-v1
        addr (module '(kernel-function-address main))
        scratch (module '(kernel-scratch-region))]
    (is (= addr (uefi/reject-rodata-literals-outside-native-targets! kernel addr)))
    (is (= '[kernel-scratch-region]
           (:operations (refusal uefi/reject-outside-uefi-target! kernel scratch))))))
