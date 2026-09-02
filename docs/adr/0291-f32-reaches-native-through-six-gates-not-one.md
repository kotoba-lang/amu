# ADR 0291: f32 reaches native, through six gates and not one

- Status: accepted
- Date: 2026-09-02

## Decision

`compile-source*` no longer refuses f32 on the native backends. The gate said:

```clojure
;; f32 and f64 gated separately: kotoba-native implements f64 scalar
;; arithmetic (ADR-2608030300) and no f32 at all, so admitting them
;; together would route f32 to a backend that cannot emit it.
(throw (ex-info "f32 values require the kotoba-script or Wasm target" ...))
```

The premise was true when it was written and is no longer. Both widths now
reach both native ISAs, so the two backend sets are the same set. The two gates
stay separate only because the two refusals still have to name their own width.

Semantics are decided in `kotoba-lang`
(`docs/adr/ADR-kotoba-floating-point-on-native.md`): IEEE-754 binary32,
round-to-nearest-ties-to-even, no contraction, no fast-math, NaN/Inf/−0.0
representable in computation while the value codec's rejection of them *on the
wire* stands. This ADR records what it took to make that reachable from `amu`.

## The finding: six independent gates, discovered one at a time

f32 was fully specified, fully interpreted by the KIR oracle, and fully typed by
the frontend — and unreachable. Removing the throw above moved the refusal one
layer down, six times. Each was found by running the next command, not by
reading:

| # | Layer | How it refused |
|---|---|---|
| 1 | `kotoba-kir` `only-native-word-typed-features?` | admitted nothing f32; the comment said *"f32 is deliberately absent: neither backend implements it"* |
| 2 | `kotoba-sema` literal desugar | `(f32-add 1.5 2.5)` became `(f64-from-bits …)`, so every f32 op rejected its own literal argument as the wrong type |
| 3 | `kotoba-gmir` `instruction-keysets` | no `:gmir/f32-*` operation existed to lower into |
| 4 | `kotoba-mir` | op keyset, allocator value set, physical selection |
| 5 | `kotoba-codegen` `selected-keysets` | `MC rejected: non-canonical-selected-instruction {:mc/encoding :aarch64/f32-add …}` |
| 6 | `kotoba-verifier` `verify-expr!` | `{:error :verify, :message "runtime KIR operation rejected"}` — after *every* other layer had accepted the program |

Gate 6 is the one worth remembering. `kotoba.verifier` re-derives the admitted
operation set **independently** of `kotoba.kir`, by design: being stricter is
sound, being looser is not. The consequence is that the two omission lists are
maintained in separate repositories and must stay identical, and nothing checks
that they do. A `compile --jvm-free` that reaches `:error :verify` after a green
`check` is what that drift looks like.

## A second finding: the stack emitters are not on the compile path

`kotoba.native.x86-64/emit-program` and its AArch64 twin are, in full,
`machine-ir/compile-kir-module`. The stack emitters below them — including their
f64 tables — are reachable only from tests; `amu` calls `emit-program` and
nothing else. A first draft of the backend change added f32 to those tables and
was dead code. It was reverted. Anyone extending the native surface starts in
`machine_ir.cljc`.

## What is admitted, and what is not

Admitted on native: `f32-add` `f32-sub` `f32-mul` `f32-div`, `f32-neg`
`f32-abs` `f32-sqrt`, the six comparisons, `f32-from-bits` `f32-to-bits`, and
four conversions — `f32-to-f64-exact` `f64-to-f32-rounded` `i64-to-f32-rounded`
`i64-to-f64-rounded`.

Refused, each for its own reason rather than by omission:

- **`f32-min` / `f32-max`** — x86 `MINSS`/`MAXSS` return the *second* operand
  when either input is NaN; AArch64 `FMIN`/`FMAX` and the oracle's `Math/min`
  return the NaN. The **f64 twins are already implemented on both backends**, so
  x86 already disagrees with the oracle on code that has shipped since
  ADR-2608030300. That is a pre-existing defect, recorded rather than repaired,
  because repairing it moves f64 goldens. This width does not inherit it.
- **The `-checked` conversions** — they trap in the oracle on inexactness and no
  backend emits the check.
- **The truncating float → int conversions** — three answers out of domain: x86
  `CVTTSS2SI` yields the integer indefinite value, AArch64 `FCVTZS` saturates,
  the oracle traps.

The gate in `compile-source*` does **not** duplicate that list. It admits the
width; `ir/only-native-word-typed-features?` admits the operations. A second
copy here could disagree with the first.

## Representation

An f32 is one machine word holding its binary32 pattern **sign-extended from
bit 31**. `f32-to-bits` therefore emits nothing, as `f64-to-bits` does, and
`f32-from-bits` is the one member that is not an identity: it sign-extends,
which also canonicalises the zero-extended u32 that `kernel-load-u32` returns.
A guest reading floats out of memory writes
`(f32-from-bits (i32-wrap (kernel-load-u32 base len index)))`.

`:f32` is **not** a native function-boundary type, and neither is `:f64`. The
kexe export ABI passes i64 words; floats cross as their bit pattern. Named as a
gap rather than left silent — it applies equally to f64.

## Evidence

Measured 2026-09-02 on macOS/arm64.

- `bin/amu check examples/f32-dot-product.kotoba --jvm-free` → `{:ok true}`.
- `bin/amu compile examples/f32-dot-product.kotoba --target x86_64 --jvm-free`
  → 839 bytes of code containing `addss` (`f3 0f 58 c1`), `mulss`, `sqrtss`,
  `ucomiss`, `cvtss2sd`, `cvtsi2ss`, and **not** `ADDSD` or `MULSD`.
- The same for `--target aarch64` → 520 bytes containing `FADD S`
  (`1e212800`), `FMUL S`, `FSQRT S`, `FCMP S`, `FCVT D,S`, `SCVTF S`, and
  **not** `FADD D` or `FMUL D`.
- `test/kotoba/compiler/f32_native_execution_test.clj` — 7 tests, **81
  assertions**: real machine code, signed, verified and **executed** through
  `kototama.native.executor` on this host, every case compared **bit-for-bit
  against the KIR reference interpreter** rather than against a number written
  down here. Includes `0.1f + 0.2f = 0x3E99999A` (the pattern that separates
  binary32 from binary64), NaN unordered on all six comparisons, and
  round-to-nearest-even at `i64-to-f32-rounded 16777217`.
- Shown to discriminate: deleting the sign extension from `a64-f32-binary`
  fails that suite with exactly `(not (= -1082130432 3212836864))` — the
  signed/zero-extended divergence the representation exists to prevent — and it
  passes unchanged when restored. One expectation in the suite (`sqrt(14.0f)`)
  was written down wrong and was caught by the oracle comparison, which is the
  reason the comparison is against the oracle and not against constants.

Not done, and named: no packed SIMD, no XMM/YMM register allocation, no float
function-boundary type at either width, and no machine check that kir's and the
verifier's omission lists still agree.
