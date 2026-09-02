(ns kotoba.compiler.aggregate-abi-test
  (:require [clojure.edn :as edn]
            [clojure.test :refer [deftest is]]
            [kotoba.native.aggregate-abi :as aggregate-abi]
            [kotoba.native.machine-ir :as machine]))

(defn- dependency-pin [coordinate]
  (get-in (edn/read-string (slurp "deps.edn")) [:deps coordinate :git/sha]))

(deftest pinned-closure-carries-the-complete-native-boundary
  ;; Advanced 2026-08-31: `elf64.clj` and `elf64.cljc` are a twin and the JVM
  ;; loads the `.clj`, but nothing measured that they agreed. They had drifted
  ;; to 74 entries against 69 -- three names only in `.cljc`, eight only in
  ;; `.clj` -- and because the JVM packager is the one that runs, the three it
  ;; was missing made three aiueos kernel objects stop building. They surfaced
  ;; as `:kotoba/internal-error`, "internal compiler error", which reads like a
  ;; crash in THIS compiler and is not one. Both tables now carry the union,
  ;; and `elf64-twin-parity-test` keeps them there. The advance also upstreams
  ;; the three ecdsa entries aiueos was patching in locally and puts the ecdsa
  ;; objects in the fuel tier a scalar multiplication needs.
  ;;
  ;; Advanced again 2026-08-31 to `0daafbf`: the table was not the only axis
  ;; the twins had drifted on. `package-kernel-object` picks its fuel immediate
  ;; from a per-object tier table, and the `.clj` had four arms to the `.cljc`'s
  ;; six -- missing `ecdsa-fuel?` and `dhcp-fuel?`. So the JVM packager gave
  ;; `aiueos-ecdsa-p256-sha256-verify` 250,000,000 instead of 2,147,483,647 and
  ;; both DHCP objects the 1,024 default instead of 65,536, 64x less. The
  ;; shipped objects say which file was right: at file offset 75 all three
  ;; carry the `.cljc` values.
  ;;
  ;; Found from OUTSIDE. Clojure loads the `.clj` for that namespace and nbb
  ;; loads the `.cljc`, so no single runtime can call both packagers and no
  ;; test inside either one can compare them. It took building all 66 aiueos
  ;; objects on both routes and diffing the bytes. `elf64-twin-parity-test` now
  ;; compares the tier arms with their four fuel bytes, so the cheap
  ;; source-level guard catches the next drift earlier.
  ;;
  ;; Advanced 2026-08-31 for a fourth instance of ADR-0286's class, this one
  ;; in the AArch64 leaf-constant cache. `a64-cache-leaf-constants` grouped
  ;; constant occurrences in a map keyed by the raw i64, and a ClojureScript
  ;; i64 is a BigInt primitive that `goog.getUid` cannot hash. Eight or fewer
  ;; entries is an array map, which compares with `=` and never hashes, so the
  ;; throw stayed invisible until a leaf carried more than eight distinct
  ;; constants -- and `kernel_deep.kotoba` and `kernel_wide.kotoba`, two of
  ;; this repository's own runtime-comparison fixtures, do. Both answered
  ;; "internal compiler error" on the NBB front while the JVM front compiled
  ;; them, so `--jvm-free` could not build the fixtures the codegen
  ;; co-scientist loop ranks this compiler on. `const-key` already existed for
  ;; exactly this, added for the x86-64 path; AArch64 had not adopted it.
  ;; The emitted kexe is byte-identical to the JVM front's, and the JVM
  ;; front's own output is byte-identical across the advance.
  ;;
  ;; Advanced 2026-09-01 for context ABI v4: this backend now lowers
  ;; `vector-alloc` (slot 200) and `vector-assoc!` (slot 208), the two heads
  ;; KIR has declared and admitted since b6bfe23 with nothing on native to
  ;; emit them. Superproject ADR-2609010200.
  ;; Advanced 2026-09-02 twice over, by two streams, and resolved to the tip
  ;; that contains both:
  ;;   f32  -- the KIR-to-GMIR lowering and both ISAs' encoders for the binary32
  ;;           family, with byte goldens that assert the single-precision opcode
  ;;           is present AND its double-precision twin is not. ADDSS and ADDSD
  ;;           are one prefix byte apart and a program built from the wrong one
  ;;           still returns a number (kotoba-native#104).
  ;;   boot -- the four UEFI firmware-boundary encodings (kotoba-native
  ;;           ADR-0039): :system-table, :load-ptr, :uefi-call2 and :jump-to,
  ;;           the four things a BOOTX64.EFI written in Kotoba has to name.
  ;;
  ;; boot: advanced 2026-09-02 for the four UEFI firmware-boundary encodings
  ;; (kotoba-native ADR-0039) -- :system-table, :load-ptr, :uefi-call2 and
  ;; :jump-to, the four things a BOOTX64.EFI written in Kotoba has to name.
  ;;
  ;; memwidth: and for four transfer widths by four window tiers instead of
  ;; seven hand-listed combinations (ADR 0042), a natural-alignment check on
  ;; every access wider than a byte, and the element-indexed slice family from
  ;; ADR 0285 -- one unsigned compare and one scaled `mov` per element, with no
  ;; context callback in the loop. Both are in this SHA; it is main, and it was
  ;; checked with `merge-base --is-ancestor` against each stream's own merge
  ;; rather than assumed to contain them.
  ;;
  ;; qwen  -- 2026-09-02: the three Qwen3.5 forward-pass kernel objects
  ;;           (aiueos-qwen35-dot-f32 / -dequant-row / -matvec) enter
  ;;           kernel-object-entries with measured fuel tiers (kotoba-native#113).
  (is (= "24f43e212085d5e22bc01ab4f478f9971fd9b72d"
         (dependency-pin 'io.github.kotoba-lang/kotoba-native)))
  ;; Advanced 2026-08-31 for two more instances of ADR-0286's class -- a KIR
  ;; i64 is a BigInt under ClojureScript and reached a host operation that
  ;; cannot take one. There, `hetero-vector-at`; here, `uleb` (every
  ;; capability contract writes one) and, in kotoba-wasm, the `[:capability
  ;; id]` import key, which ClojureScript cannot hash at all. Together they
  ;; made `compile --jvm-free --target wasm32-browser` an internal compiler
  ;; error for any guest declaring a capability, while `check --jvm-free`
  ;; passed. The same advance also drops an npm package (`@noble/hashes`) out
  ;; of `kotoba.kir.value`'s ClojureScript require graph.
  ;; Advanced 2026-09-02 by the same two streams:
  ;;   f32  -- the native admission, which carried the line "f32 is deliberately
  ;;           absent: neither backend implements it" over an interpreter that
  ;;           implements the whole family (kotoba-kir#58).
  ;;   boot -- the UEFI entry contract v2 on the firmware target profile, and
  ;;           the four operations' oracle refusals (ADR-0229).
  ;;
  ;; memwidth: and `kernel-memory-profile` as four widths by four tiers,
  ;; `slice-memory-profile` as the ADR 0285 carrier's oracle, and
  ;; `word-load`/`word-byte-at` replacing a helper whose ClojureScript branch
  ;; used a THIRTY-TWO bit shift -- correct only because nothing had ever asked
  ;; it for a byte above the fourth. A u64 store asks.
  ;;
  ;; Advanced 2026-09-02 again (ADR 0294): `definition-identity/effect-row-from-hir`,
  ;; the wire-row -> named-row adapter, alongside kotoba-sema e42b74ef (typed
  ;; abort slice 1, type-directed arithmetic) and kotoba-hir ac8e7051 (a row
  ;; may hold the bare keyword `:abort`). The ten frozen identity vectors are
  ;; unchanged by that advance.
  ;;
  ;; Advanced 2026-09-02 again (this repo's ADR 0296): `native-boundary-type-refusal`
  ;; and `native-erased-source-carrier-types` -- the NAMED refusal for a
  ;; `[:slice T]` that reached KIR, which can only happen if kotoba-sema's
  ;; erasure did not run. Refusal by absence was already correct; what this
  ;; adds is a reason a caller can read (kotoba-kir ADR 0240).
  (is (= "061283e9cb7d819bf96ae0c28d0afbbd52195b6a"
         (dependency-pin 'io.github.kotoba-lang/kotoba-kir)))
  ;; Advanced 2026-09-01 alongside the backend: the verifier re-derives the
  ;; two new arities and the v4 `expected-context`, and is what turns a
  ;; mismatched ABI into an explicit refusal rather than a v3 artifact
  ;; hunting for slots that are not there.
  ;; Advanced 2026-09-02 by three streams:
  ;;   f32   -- this verifier re-derives the admitted operation set INDEPENDENTLY
  ;;            of kotoba.kir, so f32 admitted there and absent here produced a
  ;;            green `check` and `{:error :verify, :message "runtime KIR
  ;;            operation rejected"}` on compile. That is how the gap was found,
  ;;            and it is why the two omission lists have to stay identical
  ;;            across two repositories (kotoba-verifier#31).
  ;;   boot  -- so the firmware target may name the machine (ADR-0020). Refusing
  ;;            :x86_64-aiueos-uefi-v1 a port write refused the target its own
  ;;            profile describes, and is why BOOTX64.EFI was still C.
  ;;   shift -- so a shift count is recognized as a literal on BOTH compiler
  ;;            hosts (kotoba-verifier ADR-0022, 3d7a6f0). The gate was bare
  ;;            `integer?`, false for the JavaScript bigint every guest literal
  ;;            is under nbb, so no artifact using an i64 or i32 shift could be
  ;;            built on the JDK-free route while the JVM route compiled the
  ;;            same source -- the same independence, the same shape, a third
  ;;            time (this repo's ADR-0293).
  ;; The pin is the branch tip, which also carries the interrupt entry address
  ;; gate.
  ;;   slice -- the same independence a fourth time: the verifier keeps its OWN
  ;;            copy of the erased-source-carrier list and refuses a `[:slice T]`
  ;;            at a function boundary by name (kotoba-verifier ADR 0028). That
  ;;            commit also unsticks this repository's sibling: kotoba-verifier
  ;;            had been pinned to kotoba-native a2023fed for 302 commits
  ;;            because three tests pinned SPILL SLOTS as literals across an
  ;;            allocator that gained a callee-saved tier (ADR 0027).
  (is (= "7a8cdcd98227b86af18e0c6e4d33a3e51eff17ff"
         (dependency-pin 'io.github.kotoba-lang/kotoba-verifier)))
  (is (= 7 (:abi/version aggregate-abi/contract)))
  (is (= :recursive-word-handles
         (get-in aggregate-abi/contract
                 [:portable/record :boundary/field-representation])))
  (is (= 32
         (get-in aggregate-abi/contract
                 [:portable/record :boundary/max-nesting-depth])))
  (is (= :word-pair-chain-admitted (get-in aggregate-abi/contract
                        [:extracted :record-boundary])))
  (is (= :recursive-payload-pair-handle-admitted (get-in aggregate-abi/contract
                        [:extracted :variant-boundary])))
  (is (= :sealed-callable-admitted (get-in aggregate-abi/contract
                                            [:extracted :call-admission])))
  (is (= {:indirect :closed-ordinal-dispatch
          :apply :bounded-pair-chain
          :max-apply-arguments 4
          :arbitrary-address false}
         (get-in aggregate-abi/contract [:extracted :callable-dispatch])))
  (is (= {:mode :closed-module-graph
          :ambient-symbols false
          :unresolved-symbols false}
         (get-in aggregate-abi/contract [:extracted :linkage])))
  (is (= :all-allocator-registers
         (get-in aggregate-abi/contract
                 [:targets :x86-64 :call-clobbers])))
  (is (= :all-allocator-registers
         (get-in aggregate-abi/contract
                 [:targets :aarch64 :call-clobbers]))))

(deftest pinned-aarch64-constant-selector-is-small-and-bounded
  (let [magic -9223372032559808509
        chunks (#'machine/a64-constant-chunks magic)
        recognize (var-get #'machine/a64-logical-immediate-fields)
        probes (atom 0)]
    (is (= [0xe0 0x0b 0x41 0xb2 0x20 0x00 0xc0 0xf2]
           (#'machine/a64-constant :aarch64/x0 magic))
        "the modular-mix reciprocal is exactly one logical seed plus one MOVK")
    (is (nil? (ns-resolve 'kotoba.native.machine-ir
                          'a64-logical-seed-index))
        "the pin does not restore the cold global candidate index")
    (with-redefs [machine/a64-logical-immediate-fields
                  (fn [candidate]
                    (swap! probes inc)
                    (recognize candidate))]
      (is (some? (#'machine/a64-logical-seed-plan chunks)))
      (is (<= @probes 8)
          "four lanes times zero/full replacement is the structural ceiling"))))

(deftest standalone-expressions-still-reject-calls-but-modules-admit-them
  (is (not (machine/pilot-expression? ['x] '(callee x))))
  (try
    (machine/lower-kir-expression ['x] '(callee x))
    (is false "standalone call-shaped KIR must require module lowering")
    (catch clojure.lang.ExceptionInfo error
      (is (= :aggregate-abi (:phase (ex-data error))))
      (is (= :call-abi-not-admitted (:problem (ex-data error))))))
  (let [module {:format :kotoba.kir/v4
                :exports ['main]
                :functions [{:name 'inc-one :params ['x] :result :i64
                             :body '(+ x 1)}
                            {:name 'main :params [] :result :i64
                             :body '(let [live 40]
                                      (+ live (inc-one 1)))}]}
        gmir (machine/lower-kir-module module)]
    (is (machine/pilot-module? module))
    (is (= 3 (:gmir/version gmir)))
    (is (= ['inc-one 'main]
           (mapv :gmir/name (:gmir/functions gmir))))
    (doseq [target [:x86-64 :aarch64]]
      (let [mc (machine/compile-gmir target gmir)
            caller (second (:mc/functions mc))
            encodings (map :mc/encoding (:mc/instructions caller))]
        (is (= :call-live (:mc/frame-policy caller)) target)
        (is (zero? (:mc/frame-slots caller)) target)
        (is (not-any? #{(keyword (name target) "spill-store")
                        (keyword (name target) "spill-load")}
                      encodings)
            [target "the call-crossing value is preserved, not spilled
                     (kotoba-mir 8a2bc4d via kotoba-native 1fd9c22)"])))))

(deftest pinned-closure-carries-the-zero-frame-four-argument-entry
  (let [module {:format :kotoba.kir/v4
                :exports ['main]
                :functions
                [{:name 'sum-four :params ['a 'b 'c 'd] :result :i64
                  :body '(+ (+ a b) (+ c d))}
                 {:name 'main :params [] :result :i64
                  :body '(sum-four 1 2 4 8)}]}]
    (doseq [target [:x86-64 :aarch64]]
      (let [[callee caller]
            (:mc/functions (->> module machine/lower-kir-module
                                (machine/compile-gmir target)))
            spill-encodings #{(keyword (name target) "spill-store")
                              (keyword (name target) "spill-load")}]
        (is (= [0 0] (mapv :mc/frame-slots [callee caller])) target)
        (is (= [:allocator :call-live]
               (mapv :mc/frame-policy [callee caller])) target)
        (is (not-any? #(contains? spill-encodings (:mc/encoding %))
                      (mapcat :mc/instructions [callee caller])) target)))))

(deftest five-argument-entries-no-longer-spill-the-excess-input
  (let [module {:format :kotoba.kir/v4
                :exports ['main]
                :functions
                [{:name 'sum-five :params ['a 'b 'c 'd 'e] :result :i64
                  :body '(+ (+ (+ a b) (+ c d)) e)}
                 {:name 'main :params ['a 'b 'c 'd 'e] :result :i64
                  :body '(sum-five a b c d e)}]}]
    (doseq [target [:x86-64 :aarch64]]
      (let [[callee caller]
            (:mc/functions (->> module machine/lower-kir-module
                                (machine/compile-gmir target)))
            functions [callee caller]
            store-encoding (keyword (name target) "spill-store")
            load-encoding (keyword (name target) "spill-load")]
        ;; A fifth live argument used to exhaust the four-register allocator
        ;; and get backed directly from its ABI register: one slot, one store,
        ;; one lazy reload, in each of the two functions. The pool now reaches
        ;; past four, so five arguments all arrive in registers and neither
        ;; function touches the stack.
        (is (= [0 0] (mapv :mc/frame-slots functions)) target)
        (is (= [:allocator :call-live]
               (mapv :mc/frame-policy functions)) target)
        (doseq [function functions]
          (let [encodings (map :mc/encoding (:mc/instructions function))]
            (is (zero? (count (filter #{store-encoding} encodings)))
                [target (:mc/name function)])
            (is (zero? (count (filter #{load-encoding} encodings)))
                [target (:mc/name function)])))))))
