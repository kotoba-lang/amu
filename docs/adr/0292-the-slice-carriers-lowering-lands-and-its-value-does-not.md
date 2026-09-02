# ADR 0292: The slice carrier's lowering lands, and its value does not

- Status: accepted
- Date: 2026-09-02
- Follows: ADR 0284 (a context call per element), ADR 0285 (a bulk carrier must
  be guest-addressable memory)

## Decision

ADR 0285 decided three things. This change delivers the first at the **machine
layer**, honours the second literally, and does not touch the third.

1. **A distinct carrier whose element access lowers to a load.** Landed as
   `slice-{load,store}-u{8,16,32,64}`: element-indexed, ceiling 2^40 elements,
   one unsigned compare and one scaled `mov` per element, no context callback.
2. **Do not raise `vector-item-limit` (16384), `:vector-item-capacity` (65536)
   or `:vector-capacity` (4096).** None of them moves. The loader memory image,
   the verifier's derived limits and the pinned runtime identity SHA do not
   move together, which is the cheapest way to avoid a second instance of the
   co-movement defect ADR 0284 found.
3. **Frame-scale pixel data does not enter the guest.** Untouched; nothing here
   is evidence for or against it.

Alongside it, the byte-indexed window family becomes four transfer widths by
four tiers, with a natural-alignment check. That is kotoba-native ADR 0042 and
kotoba-kir ADR 0229; the pins are bumped here.

## What is NOT landed, stated first because it is the important half

**`[:slice T]` is not a type, and no gate admits one.**

ADR 0285 asks for a two-word (base, length) carrier that a `let` binds, a
function parameter carries, and `slice-sub` narrows. What lands is the machine
layer such a carrier lowers to: three separate i64 operands, `base length
index`, exactly the shape the window family already had.

`kotoba.kir/native-word-value-type?` deliberately does not list `[:slice T]`.
Nothing produces a slice value, so nothing admits one — **an admission gate
that admits what nothing can lower is precisely the defect ADR 0284 named**,
and 0285's own closing section refuses to create a second instance of it:

> Landing any proper subset would create exactly the defect ADR 0284 named — an
> admission gate admitting what nothing can lower.

The remaining work is a **register-allocator** change, not a machine-code one.
Both backends already emit every load, store and check a slice needs. What
neither can do is *carry* a two-word value:

1. `kotoba.native.machine-ir/pilot-expression?` knows exactly one value shape,
   `:scalar`; `value` returns a register, not a register pair.
2. `kotoba.native.x86-64`'s fallback path keeps every value in RAX with stack
   pushes.
3. Either GMIR/MIR gain a two-register SSA value, or the frontend erases slices
   into two i64s before KIR — scalar replacement, which the record path already
   does for a directly nested `record-new`.
4. `kotoba.compiler.frontend` gains `[:slice T]` with construction restricted
   to a parameter, a `kernel-boot-info`-derived region, or `slice-sub`.

Route 3-by-erasure needs no new IR value: a slice parameter becomes two i64
parameters and a slice `let` becomes two bindings — which is exactly the shape
the operations landed here already take. The full authority diff, including the
`kotoba-lang` entries this proposes, is in kotoba-native
`docs/lang-authority-diff.md`.

`[:slice :f32]` is **declared and not admitted** for the same reason at one
remove: there is no f32 element to load yet on this path, and the F32 stream
owns admitting it.

## What the emitted code actually looks like

`test/fixtures/slice-sum-u8.kotoba` sums a byte region and a word region and
compiles JVM-free to a 1336-byte ELF object:

```
amu compile test/fixtures/slice-sum-u8.kotoba \
  --target x86_64-aiueos-kernel-v1 --jvm-free --output slice-sum.o
{:ok true, :target :x86_64-aiueos-kernel-v1, :artifact-bytes 1336}
```

Disassembled (`llvm-objdump`, LLVM 22.1.7), the u8 loop body is:

```
 5e: 49 ba 00 00 00 00 00 01 00 00   movabsq $0x10000000000, %r10
 68: 4d 39 d4                        cmpq    %r10, %r12          ; length <= 2^40
 6b: 0f 87 ...                       ja      trap
 71: 48 85 db                        testq   %rbx, %rbx          ; base != 0
 74: 0f 84 ...                       je      trap
 7a: 4d 39 e5                        cmpq    %r12, %r13          ; index < length
 7d: 0f 83 ...                       jae     trap
 83: 4e 8d 1c 2b                     leaq    (%rbx,%r13), %r11
 87: 45 0f b6 03                     movzbl  (%r11), %r8d
```

and the u64 loop, which is where the scale is visible:

```
138: 4e 8d 1c eb                     leaq    (%rbx,%r13,8), %r11
13c: 4d 8b 03                        movq    (%r11), %r8
```

Three facts this pins:

- **`movabsq $0x10000000000`** — the ceiling does not fit an `imm32`. That is
  the visible sign that it is an address-space bound and not a window profile;
  a window tier is a `cmp r64, imm32`.
- **`leaq (%rbx,%r13,8)`** — the index is scaled in the addressing mode. The
  guest computes no byte offset. The u8 loop's `leaq (%rbx,%r13)` is the same
  instruction with the scale field at 1.
- **Zero indirect calls.** `llvm-objdump | grep -c 'callq *\*'` is 0 across the
  whole object; the only three `callq`s are the probe/entry plumbing, outside
  both loops. ADR 0285 measured `vector-at` at 381.72 ns/element on wasm32 and
  attributed it to the crossing. This is what removing the crossing looks like.

**What this does not measure.** No number here is a timing. ADR 0285's own
Reflect stage refused the timing comparison — `:not-separated-from-noise`, gap
0.031 against summed stdev 0.044 — and this change does not re-run it. The
claim is structural and counted: the element access is one compare and one
load, and there is no callback. Whether that is *faster* on this hardware
remains unmeasured, and 0285 is explicit that the absence of a result is the
result.

## The gate that had not opened

The first compile of the fixture failed:

```
{:error :verify, :message "runtime KIR operation rejected"}
```

Every upstream gate was already open — `kotoba.compiler.frontend` admitted the
operation, `kotoba.kir` executed it, both native backends emitted it — and
`kotoba.verifier` refused it, because that repository rejects by **absence** and
re-derives its own tables on purpose. Both gates have to open. That is the
design working, not a defect, and it is recorded here because it is the second
time this repository's history has learned it (the first was `string-contains?`,
kotoba-kir ADR 0222).

## Evidence

- The four namespaces this change touches —
  `kotoba.compiler.slice-carrier-test`,
  `kotoba.compiler.kernel-region-provenance-test`,
  `kotoba.compiler.aggregate-abi-test` (the pin assertions) and
  `kotoba.compiler.test-runner-completeness-test` (which refuses a test
  namespace missing from the runner) — **18 tests, 177 assertions, 0
  failures**, run on the merged pins.

  Discriminated rather than asserted: replacing `slice-load-u64` with
  `kernel-load-u64-4k` in the fixture turns
  `an-element-access-is-one-compare-and-one-scaled-mov` red on exactly the
  scaled-address assertion, and the dumped bytes show the window family's
  sequence in its place — `cmp r12, imm32` for the tier, `and r10, 7` for the
  per-access alignment, and an unscaled `add`. Restored: 0 failures.

- The **full** 159-namespace suite, on the merged pins:
  `test-runner: COMPLETE -- 159 of 159`, **1234 tests / 8969 assertions** on the
  first run and **1234 / 8974** on the second.

  Both runs failed only inside `kotoba.compiler.isa-execution-test`, and **the
  two runs failed different assertions** — six on the first (`recursion`,
  `mutual tail calls`, `keyword parameter`, the four-argument entry), one on the
  second (`source-variant-sroa`). Run standalone, that namespace passes **twice
  over: 25 tests, 768 assertions, 0 failures each time.**

  Every failure has the same shape:
  `{:status :trap :exit 120 :fuel {:initial 512 :remaining 512}}` — fuel
  untouched, so the process never executed an instruction — and every one is on
  the **x86_64** arm, which on this Apple Silicon host runs the emitted binary
  through **Rosetta 2** (`cc -arch x86_64`, `isa_execution_test.clj:17,70`). The
  aarch64 arm never failed.

  So this is process launch under contention, not codegen: a deterministic
  defect fails the same assertion every time, and would not disappear when the
  namespace runs alone. The host carried load average 112–211 throughout, with
  several other streams' JVMs resident (one 1 day 19 hours old). Four
  measurements are recorded rather than one, because a single green run and a
  single red run are each equally consistent with the wrong conclusion.

- The fixture compiles under `--jvm-free`, which is the acceptance rule: no
  `java`, no `clojure`, in the compile path.
- `kotoba.compiler.kernel-region-provenance-test` now covers all twenty loads
  and twenty stores: a loaded byte as an address is refused at every width, so
  is bare `(+ base 1)`, and a `kernel-subregion` narrowing and
  `kernel-boot-info` are admitted at every width. A slice base parameter is
  reported as an ABI boundary without a line written for slices — because the
  provenance walk reads `kernel-memory-operations`, which is the whole reason
  the slice family shares that table.

## Pins

| repository | from | to |
|---|---|---|
| kotoba-sema | `74ac0d7` | `87f7d32` |
| kotoba-kir | `b6bfe23` | `7aa6d2d` |
| kotoba-native | `4a4c4c3` | `3b7a426` |
| kotoba-verifier | `58a02b4` | `6ef43bd` |

`deps-lock.edn` regenerated with `nbb scripts/lock-classpath.cljs`. Each bump
was checked with `git merge-base --is-ancestor` rather than assumed to be a
fast-forward.
