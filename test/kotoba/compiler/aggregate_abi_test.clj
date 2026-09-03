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
  ;; boot-scratch -- 2026-09-02: `:scratch-region` (`lea r10,[r9+0x60]`, four
  ;;           bytes) and `:x86-64/function-address` (`lea dst,[rip+disp32]`,
  ;;           resolved against the same label table a call uses), plus
  ;;           `kotoba.native.image-scratch` -- the offset and the 16 KiB
  ;;           reservation, read by the encoder AND by this repository's PE32+
  ;;           packager (kotoba-native ADR-0068/0069).
  ;;
  ;; Advanced 2026-09-03 by the pin-consolidation stream (ADR 0330). Forty-four
  ;; merges had landed behind this one pin while every K16 stream was told the
  ;; amu bump was batched, and two QEMU proofs were unreproducible from landed
  ;; code because of it: both `AIUEOS_DOT_F32_QEMU_OK` and
  ;; `AIUEOS_DEQUANT_KQUANT_QEMU_OK` answered `COULD-NOT-RUN compile-failed`
  ;; against this repository's main and reproduced only against private
  ;; branches. Every claim below was checked with `compare` against this SHA:
  ;;   279fbc3  a bounded store answers with the word it STORED.
  ;;   da3593b5 kernel-read-cr4 / kernel-write-cr4 / kernel-xsetbv -- the
  ;;            "aggregate ABI rejected: call-abi-not-admitted" the dot-f32
  ;;            probe was hitting.
  ;;   a727bf7  six RTL8125 driver symbols and the FIFO-drain fuel tier.
  ;;   1baa450  three SHA-256 symbols for a message arriving in pieces.
  ;;   70984ea / 2c4d6c3 / 449792d  Qwen3.5 export names and measured fuel
  ;;            tiers, tranches two and three.
  ;;   1072816 / bbeed36 / a63faa6  Q4_K and Q6_K EMIT, thirty-two groups
  ;;            unrolled; the four codebook formats refused BY NAME.
  ;;   91033a9  the writable region is an lea, a function's address is a label.
  ;;   d710558  a reentry parameter's home is stored inside the loop.
  ;;
  ;; fwstore: advanced 2026-09-03 to adeb1b0f for ONE encoding,
  ;; `:uefi-alloc-region` (kotoba-native ADR-0080). It is `x86-uefi-call-wide`'s
  ;; frame with the fifth-argument slot repurposed as the out-word
  ;; `AllocatePages` writes through, so the address the firmware chose comes
  ;; back in a register instead of through a load -- which is what makes the
  ;; pages a region-provenance root rather than an address the program has to
  ;; be trusted about. The failure answer is `xor r11,r11` / `test rax,rax` /
  ;; `cmovne r10,r11`, and `cmove` is one bit away and inverts the whole
  ;; operation with nothing faulting to say so, which is why the suite pins
  ;; that byte as an explicit `not`. Checked with `merge-base --is-ancestor`
  ;; against 452422f.
  (is (= "adeb1b0fa5bcd2dd18a657c7e3bd3c4acbd630ae"
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
  ;; Advanced 2026-09-02: `kotoba.kir.alpha-normalization`. The five-binder
  ;; walk was implemented in this repository AND in kotoba.codebase.typed-code
  ;; -- the same algorithm over the same KIR, with neither copy the authority,
  ;; which kotoba-lang lang/code-identity.edn recorded as a residual risk of
  ;; :ci8. It is now kir's and both consumers delegate. `definition-cid` still
  ;; does not normalize internally, so the ten frozen identity vectors are
  ;; unchanged by this advance too.
  ;;
  ;; This advance also carries 984a507, whose `:abort` decision ADR 0314 held
  ;; this pin to await. deps.edn records the adjudication and its three reasons.
  ;;
  ;; Advanced 2026-09-02 again (boot-scratch, ADR-0242): the two heads that
  ;; name a place in the IMAGE -- its `.data` reservation and its function
  ;; labels -- refuse under `:image-address-unavailable` rather than under the
  ;; literal pool's keyword, and both mark a module kernel-native.
  ;; Advanced 2026-09-03 (ADR 0330) to b2e5d9c: d809f28 the four codebook
  ;; dequant formats with their six grid tables, 268e28b the fused
  ;; dequantize-and-dot oracle the QEMU K-quant smoke checks its digits
  ;; against, 18f7c3a the sealed control-effect vocabulary as this
  ;; repository's export rather than a second derivation.
  ;; Advanced 2026-09-03 to 233bd6bb by two decisions, both of which put a
  ;; number or an answer where the thing that produces it lives:
  ;;   b4d9d494 (ADR 0268) -- `execute` bounds a declared fuel budget at
  ;;     2^53-1, decided at the counter rather than inherited from
  ;;     `kotoba.native.elf64`'s `mov qword [r9+8], imm32` sign-extended
  ;;     immediate. `charge!` is `(vswap! fuel dec)` on a host double, so
  ;;     above that line the decrement is a no-op and the interpreter would
  ;;     answer `:ok` for a program that never terminates. Not
  ;;     `kotoba.wasm/max-fuel` (2^62-1), whose counter is i64 throughout.
  ;;   5f3f961f (ADR-0269) -- `kernel-uefi-alloc-region` traps
  ;;     `:kernel-privileged-unavailable` rather than folding to zero. Zero is
  ;;     the answer for a FAILED allocation, so answering it for "no firmware
  ;;     here" would make the two indistinguishable and turn every access
  ;;     through the result into a trap the source never wrote.
  ;; That head is the same one kotoba-sema 727f9d6 made a provenance root,
  ;; which is what moved `guest-grammar-vendor-test`'s kernel count to 115.
  (is (= "233bd6bb6b15912679c529611a42c8af15f2354c"
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
  ;;   boot-scratch -- the arity row for `kernel-scratch-region` and, for
  ;;            `kernel-function-address`, a check on the NAME. Its argument is
  ;;            source text and is not walked, so with the name unchecked
  ;;            nothing in that file stands between a misspelling and a backend
  ;;            `lea` at a label it would have to invent (ADR-0044).
  ;;   dequant -- the fifth and sixth instances of the same independence:
  ;;            b58c009 re-derives the fused dequantize-and-dot family and
  ;;            bcea4a1 the four codebook formats on this side of the
  ;;            boundary, so a format kotoba.kir admits and this repository
  ;;            does not is a green `check` and a refusal at compile time
  ;;            rather than a wrong artifact. 6a743c3 adds the image-symbol
  ;;            name check (ADR 0330).
  ;;   fwstore -- 2026-09-03, 96edd345: the four rows for
  ;;            `kernel-uefi-alloc-region` (kotoba-verifier ADR-0050). Its
  ;;            arity is the one in that table whose consequence is worst if
  ;;            it is wrong, and it is one that file cannot see -- the operand
  ;;            that matters is the one that is NOT there, because the
  ;;            out-pointer belongs to the emitted frame. A miscounted operand
  ;;            list does not fail to compile: it shifts every argument by one
  ;;            and hands `AllocatePages` a page count that was meant to be a
  ;;            memory type. That commit also advances the verifier's OWN
  ;;            kotoba-native pin to adeb1b0f, so this repository resolves one
  ;;            kotoba-native across both pins rather than an older one behind
  ;;            its own.
  (is (= "96edd345ce46bc2e2c3c4ae9b4f4cdc26484f188"
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
