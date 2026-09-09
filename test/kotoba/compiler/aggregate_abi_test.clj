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
  ;; And REPRODUCED, not only contained: `compare` above answers whether a SHA
  ;; is reachable from this pin, which is a different question from whether the
  ;; artifacts still come out the same. Both Qwen3.5 tranche-three objects were
  ;; recompiled at 452422f and reproduce the bytes committed on aiueos main
  ;; exactly -- 5cd0baa6... at 17,872 and 23308afe... at 6,808 -- and neither
  ;; had been built with d710558 in its closure, so the reentry-spill repair
  ;; does not reach those two (aiueos ADR-0175). 452422f is an ancestor of the
  ;; pin below (`merge-base --is-ancestor`), so the reproduction claim stays
  ;; covered by the advance.
  ;;
  ;; fuel64 -- 2026-09-03: the object replenish is no longer an imm32.
  ;;           `replenish-bytes` picks between `mov qword [r9+8],imm32` and
  ;;           `movabs r10,imm64; mov [r9+8],r10`, so a per-call budget past
  ;;           2,147,483,647 can exist at all (ADR 0078). Every shipped tier
  ;;           still fits the narrow form: that repo carries the SHA-256 of
  ;;           all 108 packaged objects taken BEFORE the change and
  ;;           re-derives them, so this advance moves no object bytes.
  ;;           95361f3 also carries ADR 0079 -- `package-user` read the
  ;;           constant 512 instead of the declared budget, the same defect
  ;;           this repository's PE32+ packager had.
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
  ;; Advanced 2026-09-08 for the osaho rename. The range is ONE commit
  ;; touching deps.edn alone, +2/-2 -- no encoding, no lowering, no opcode.
  ;; The boundary is byte-identical, so this carries no qualification claim.
  ;; Advanced 2026-09-08 to a5711bdc, which carries kotoba-mir ac690136 and
  ;; DOES change bytes on this front, deliberately.
  ;; `aarch64-fuse-zero-equality-branches` tested its constant with `zero?`,
  ;; which is false for a JavaScript bigint, so the fusion never fired for a
  ;; literal that came from the reader -- every literal in real source.
  ;; `(if (= a 0) a a)` was 24 bytes under nbb and 12 through the JVM, for the
  ;; same program. The JVM side is unchanged by this advance: a Long always
  ;; compared to 0, so the boundary this test pins moves not at all here, and
  ;; what moves is the OTHER front, toward these bytes.
  ;; Advanced 2026-09-09 to 7cbed512, which carries kotoba-mir b70a567a and is
  ;; the pin that makes TWO NEW AArch64 ARMS reachable from this repository:
  ;; `kernel-dot-f32` and Q8_0's fused dequantize-and-dot. Both are the x86
  ;; SCALAR arm reproduced instruction for instruction, because the contract of
  ;; those operations is an ACCUMULATION TREE and not a dot product -- one
  ;; specific order of summation IS the operation. Without this pin they are
  ;; refused at MIR selection with `x86-simd-target-mismatch`.
  ;;
  ;; It changes bytes on the AArch64 front by ADDING arms, not by moving an
  ;; existing sequence, so the boundary this test pins is untouched.
  ;; `the-fused-dequant-answers-the-same-bits-on-every-available-isa` is the
  ;; assertion that the two ISAs agree, executed as real processes.
  ;; Advanced 2026-09-09 to c14a49f3, which carries kotoba-mir 4a049cc9: a
  ;; LITERAL'S ADDRESS now emits on AArch64 through `adr`, a single
  ;; instruction. The refusal it replaces named ADRP+ADD's 4 KiB page split as
  ;; the blocker and the named blocker was the wrong instruction -- `adr`
  ;; reaches +/-1 MiB, and the pool is at the end of the same emitted buffer
  ;; as the code, so the distance is bounded by the size of one program.
  ;;
  ;; It ADDS an arm rather than moving an existing sequence, so the boundary
  ;; this test pins is untouched.
  ;; Advanced again 2026-09-09 to edbbe987: a FUNCTION'S address is `adr` on
  ;; AArch64 too, at the same label a call resolves against. It carries
  ;; kotoba-mir 1a1c4358 and kotoba-codegen 3e6c815a. The gap it closes was
  ;; named by the commit that closed the literal's, hours earlier -- the
  ;; refusal there said a function's address is x86-only "for exactly the
  ;; reason the literal is", and the literal's reason had already stopped
  ;; holding.
  ;;
  ;; Merged 2026-09-09: BOTH notes stand and the sha is the one deps.edn
  ;; carries. This assertion exists to make the two agree, so resolving it
  ;; by picking a side would have made the ratchet assert a pin nobody is
  ;; using -- green, and about nothing.
  ;;
  ;; Advanced 2026-09-09 to 11691559 for `lower-index-of` (kotoba-native ADR
  ;; 0081). It moves bytes only for programs that use `string-index-of`, which
  ;; nothing could until this pin: the head had no lowering, so it was
  ;; call-shaped and `reject-unextracted-call!` refused it as
  ;; `call-abi-not-admitted` -- one gate EARLIER than the two ADR 0002 opened,
  ;; which is why neither kotoba.kir nor the verifier had ever seen it. The
  ;; lowering is the scan `string-contains?` already emits, returning the
  ;; offset `kotoba$string-find` had computed instead of folding it to 0/1, so
  ;; no helper, callback, value representation or ABI version moves here.
  (is (= "edbbe9873fc0eac387d1420e5191be6fab0ff469"
         (dependency-pin 'io.github.kotoba-lang/kotoba-native)))
  ;; Advanced 2026-09-07 to kotoba-native main c9d5c44 (hoist #151, cross-call
  ;; hoist #152, copy coalescing #154; 06badc8's allow-list entry is on main as
  ;; 4e717ab). main...c9d5c44 by merge-base --is-ancestor: forward only.
  ;; Advanced again 2026-09-07 to kotoba-native main f040b483 (c9d5c44..f040b483
  ;; ahead 6, forward only): #153 context slots in the RW page, #155 the
  ;; vector-6 'U' handler, #156 `kernel-undefined-opcode-handler-address`
  ;; lowering, #162 kotoba-gmir -> a3f0597c. The head is admitted by
  ;; kotoba-sema af8cc780, lowered by kotoba-kir 658436f2 and verified by
  ;; kotoba-verifier ed9bf9b4 in the SAME commit as this pin -- a frontend that
  ;; admits it over a native that cannot encode it is the gap fwstore measured.
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
  ;; Advanced 2026-09-03 to b021a0d1 for 41341bd, the five collection
  ;; primitives, and it moves in the SAME COMMIT as the kotoba-sema pin
  ;; because the two are not independent. Measured on this branch with the
  ;; kotoba-sema pin advanced and this one held at 233bd6bb, `(pop [7 8 9])`
  ;; compiles to `{:error :ir, :code :kotoba/lowering-failed, :message
  ;; "unknown-function"}` at exit 70: the frontend ADMITS the head and the
  ;; lowering has never heard of it. That is worse than either pin alone,
  ;; because it moves the refusal from compile time to a name KIR cannot
  ;; resolve. With both pins advanced the same program refuses at
  ;; `:wasm-typed-lowering`, which is an emitter gap in a fourth repository
  ;; and is recorded as such rather than papered over.
  ;; Advanced 2026-09-07 to kotoba-kir main 658436f2 (b021a0d1..658436f2 ahead
  ;; 17, forward only) for kotoba-kir#83, the lowering of
  ;; `kernel-undefined-opcode-handler-address`; moved in the SAME commit as the
  ;; kotoba-sema pin that admits the head, for the reason the paragraph above
  ;; measured.
  ;; Advanced 2026-09-08 to 73243145: the native admission gate now admits
  ;; `i64-shift-left` / `i64-shift-right` / `u64-shift-right` beside a typed
  ;; value, under the operand restriction it already enforced for their i32
  ;; twins. It widens what compiles; it moves no encoding.
  ;; Advanced 2026-09-08 to c24c92a1: `kotoba.kir/lower` gains an
  ;; `:oracle-fuel` option, so the execution that seals a pure entry's value
  ;; runs on the budget its author declared instead of a private 100,000.
  ;; It moves no encoding; it widens what can be lowered at all.
  ;; Advanced 2026-09-09 to 74426bad: a native function may DECLARE an :f64
  ;; parameter or result. The operations were admitted in ADR-2608030300, so
  ;; this moves no encoding either -- it admits the signature that could
  ;; already be computed with, and which every float kernel in this workspace
  ;; had been writing around through f64-from-bits.
  ;; Advanced 2026-09-09 to a37577c9: `kotoba.kir.descriptor/capability-contracts`
  ;; deduplicates, orders and groups capability ids, and on ClojureScript
  ;; those ids are BigInt -- which cljs.core can neither sort, nor `distinct`,
  ;; nor `group-by`. Only the sort fired, and it fires at the SECOND contract,
  ;; so `compile --target wasm32-browser` answered `internal compiler error`
  ;; for any module declaring two or more capabilities while ONE capability
  ;; and both native targets were fine (a one-element `Array.sort` never
  ;; invokes its comparator). No native path builds this table, which is why
  ;; the split was never about the backends. This moves no encoding: on the
  ;; JVM the narrowing is `identity`.
  ;;
  ;; Merged 2026-09-09: BOTH notes stand and the sha is the one deps.edn
  ;; carries. This assertion exists to make the two agree, so resolving it
  ;; by picking a side would have made the ratchet assert a pin nobody is
  ;; using -- green, and about nothing.
  ;;
  ;; Advanced 2026-09-09 to 1a81e2d7, and this one is a CORRECTNESS advance.
  ;; `utf8-index-of!` converted the host's UTF-16 index to a UTF-8 byte offset
  ;; one unit at a time: it charged a surrogate PAIR 4 bytes at the high
  ;; surrogate and then stepped onto the low one, which matched no earlier arm
  ;; and took `:else` for 3 more. Every astral code point before a match added
  ;; 7. `(string-index-of "<G clef>ab" "ab")` answered 7 where kotoba-script's
  ;; JS emitter, kotoba-native's new lowering and CPython all answer 4.
  ;; `lower` folds a pure i64 entry through this evaluator, so the wrong offset
  ;; reached ARTIFACTS as a baked constant, not only runtime. Found from
  ;; outside, by kotoba-native's oracle comparison, which writes no expected
  ;; value down (osaho ADR 0271).
  (is (= "1a81e2d7df947a719b75db1e6e5616a900f3ebb7"
         (dependency-pin 'io.github.kotoba-lang/osaho)))
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
  ;;   fuel64  -- the same independence, decided the OTHER way. `max-native-fuel`
  ;;            was 2^20 there and 2^20 in this repository's JVM-free driver,
  ;;            while the object route shipped tiers of 250,000,000 and
  ;;            2,147,483,647 past both without ever meeting them. The verifier
  ;;            now READS `kotoba.kir/max-fuel`: re-deriving a SET has a safe
  ;;            direction, but a CEILING does not -- admitting less refuses
  ;;            valid artifacts and admitting more ratifies a budget the oracle
  ;;            cannot decrement (kotoba-verifier ADR 0049).
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
  ;; Advanced 2026-09-07 to kotoba-verifier main ed9bf9b4 (1ee32cab..ed9bf9b4
  ;; ahead 2, forward only) for kotoba-verifier#51: the rows for
  ;; `kernel-undefined-opcode-handler-address`. This verifier rejects by
  ;; absence, so it moves with the kotoba-sema / kotoba-kir / kotoba-native
  ;; pins in this commit or the head is a green `check` and a red `compile`.
  ;; Advanced 2026-09-08 for the osaho rename. The range is ONE commit
  ;; touching deps.edn alone, +2/-2 -- no encoding, no lowering, no opcode.
  ;; The boundary is byte-identical, so this carries no qualification claim.
  ;; Advanced 2026-09-08 to ea50d8f2. Seven gates in the `.cljs` branch of
  ;; `verify-artifact!` had never run against a real artifact -- `amu verify`
  ;; was `.clj`-only -- and read the JVM's representation. The seventh was not
  ;; a refusal but a host TypeError: a param index out of an artifact is a
  ;; bigint, `nth` will not take one, and this repository reported it as
  ;; `:kotoba/internal-error`. It admits nothing new.
  ;; Advanced 2026-09-09 to 39db2f3f, the other half of that admission. This
  ;; verifier rejects by ABSENCE, so with the older pin the boundary kir now
  ;; admits would be a green `check` and a red `compile`.
  ;; Advanced again 2026-09-09 to 33b3d067, and this one ADMITS rather than
  ;; widens a type: the slice memory subfamily plus `kernel-subregion` may now
  ;; reach a general native target when the verifier's own re-derivation proves
  ;; every base is a parameter -- a region the CALLER granted. The byte-window
  ;; family and everything privileged stay aiueos-only, and a literal base is
  ;; refused on a hosted target even though the frontend admits one. Same skew
  ;; argument in the other direction: without this pin a program this
  ;; repository compiles is refused at verification.
  ;; Advanced again 2026-09-09 to 6f4871f3, which lifts exactly the two
  ;; restrictions the paragraph above records as standing. The four rodata
  ;; literal heads leave the aiueos-only set for the two hosted native
  ;; targets, and a literal IS admitted as a region base beside a parameter --
  ;; for a reason the integer does not have: `4096` is an address the program
  ;; chose and could have chosen differently, while `(bytes-literal "...")` is
  ;; a relocation the backend resolves into a pool it placed beside the code.
  ;; A pool that is addressable and unreadable is not a pool.
  ;; Advanced again 2026-09-09 to 93eacd80, which takes
  ;; `kernel-function-address` out of the verifier's aiueos-only set. It was
  ;; there beside `kernel-scratch-region` under ONE comment covering both,
  ;; and the reason belonged to the reservation: a `.data` reservation is a
  ;; place in an IMAGE, a function's label is a place in the emitted buffer,
  ;; and every native target has one of those. Required with this file's
  ;; `function-address-targets` change for the usual reason -- without it the
  ;; program this repository now compiles is refused at verification.
  ;;
  ;; Merged 2026-09-09: BOTH notes stand and the sha is the one deps.edn
  ;; carries. This assertion exists to make the two agree, so resolving it
  ;; by picking a side would have made the ratchet assert a pin nobody is
  ;; using -- green, and about nothing.
  ;;
  ;; Advanced 2026-09-09 to 1810a62c: `string-operations` gains
  ;; `string-index-of 2` (kotoba-verifier ADR 0051). Required WITH the
  ;; kotoba-native pin above and not separable from it -- ADR 0002 measured
  ;; that opening one of these gates alone moves nothing, and the verifier
  ;; re-derives its own table, so a head this repository can emit and that
  ;; table does not carry is refused after emission.
  (is (= "85ea11d61cc3613bfb5ac80a7736de7ae1382942"
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
