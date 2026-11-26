# KOTOBA-963 · Lean proof of the T2 i64 constant addition rule

## Compiler path

`(+ x y)` for two i64 literals still reaches SIR as `CONST t x`,
`CONST (t+1) y`, `BIN BOP-ADD t`. `lw-bop` selects `BOP-ADD`, `lw-expr`
emits `CONST` for each integer literal, and `lw-fold` emits `BIN` after
lowering the right operand. SIR defines wrapping addition and writes the
result to `t`. The test-only `lw-ix` interpreter reads both operands and
writes that result. Its binary trap predicate excludes i64 addition.
[SIR](../../seed/SIR#L12-L58) · [Lowering](../../seed/30-lower.kotoba#L189-L194) · [Interpreter](../../seed/30-lower.kotoba#L1334-L1374)

The `aarch64-macos` compiler runs `lw-run` and `gn-run`. Its initial emitter
can fold eagerly with constant descriptors in `srf-original-op-bin`. At
`OP-END`, `t2-end` can recompile the function from SIR and select a new
native entry. This proof targets **one existing rewrite in that selected
T2 path**. `t2-op` reads the SSA IDs for `t` and `t+1` and binds a fresh
result ID to `t`. In a reachable block, `t2-gvn-vals` recognizes two
resolved constant operands via `t2-foldable?`, allocates a `t2-const`
using `t2-foldk` → `gn-fold` (`BOP-ADD`), and sets `t2-f-repl` for the
original result if allocation succeeds. `t2-res` follows the replacement
when uses are counted and when the constant is materialized. T2's own
size/admission checks still decide whether its entry is installed.
[Driver](../../seed/90-drv.kotoba#L409-L419) · [Initial emitter](../../seed/41-a64gen.kotoba#L2576-L2588) · [SSA construction](../../seed/41-a64gen.kotoba#L20845-L20855) · [Fold and replacement](../../seed/41-a64gen.kotoba#L20973-L21006) · [Wrapping operation](../../seed/41-a64gen.kotoba#L2335-L2344) · [Use resolution](../../seed/41-a64gen.kotoba#L20019-L20023) · [Materialization](../../seed/41-a64gen.kotoba#L23610-L23616) · [T2 driver](../../seed/41-a64gen.kotoba#L24890-L24919)

The [native witness](witness.kotoba) reaches that entry on the pinned Mac
root. Both literal additions feed branches and the selected entry returns
42. The entry marker and constant-return body are visible in the extracted
code. This is an execution witness for choosing T2 over the initial emitter.

## Model and boundary

[`Fold.lean`](Fold.lean) models the literal-operand subset of that SSA
rule. `accepts` checks a contiguous slice of one block containing two
constant definitions and their add, with distinct SSA IDs for the two
operands and result. The candidate binds the same logical result ID to the
modular sum, abstracting the compiler's fresh constant ID and redirection.
The real rewrite retains both operand definitions. The model includes a
definition in the proposed slice whenever its value is live out. Leaving
out an unobserved definition models that it needs no materialization for
these observations. T2 counts resolved uses separately from the fold.
[Use counting](../../seed/41-a64gen.kotoba#L21234-L21243)

- `add_mod` states that the unsigned representation of the `BitVec 64`
  sum is `(x.toNat + y.toNat) % 2^64`. The candidate computes the bit
  pattern by converting the unbounded sum back to 64 bits.
- `accepts_sound` quantifies over every incoming SSA value map, fuel
  amount, and opaque context. Accepted slices leave equal live-out values,
  fuel and context. `continuation_sound` lifts that equality to every
  continuation whose observation depends only on those components or the
  trap observation.
- Region selection assumes checked SIR, valid SSA IDs and a single entry
  before the first definition. `live` must cover every read of an outgoing
  value before a later overwrite of its SIR temporary on any continuation
  path. This includes branch and return uses, PHI inputs and values that
  can affect later traps or fuel charges. The checker consumes these facts.
  It does not infer a CFG, dominance or live-out sets from compiler bytes.
- A constant or `BOP-ADD` neither charges fuel nor traps. The checker
  rejects windows containing a fuel charge or trap and candidates that
  introduce either. Any fuel charges and traps outside the slice stay at
  their original boundaries. The model observes remaining fuel, whether
  execution reaches the exit, and exhaustion or explicit trap codes. On a
  trap it exposes fuel and opaque context without temporary values. Lean
  models fuel as a logical remaining budget. Native fuel publication,
  signal details, fault PCs, execution timing and physical registers are
  outside the observation.

The proof assumes that the real values, block boundary and live-out facts
are represented correctly. It covers the checked literal slice only. T2's
broader handling of resolved aliases and `t2-undef`, the construction and
checking of actual compiler records, allocator failure, other optimizations,
and machine-code emission are outside this proof. Checking actual compiler
instances against the rule is follow-up work under KOTOBA-964/965.

## Reproduce

With Elan available, run the same kernel check as CI from this directory.
The `lean-toolchain` file selects Lean `4.21.0` (commit `6741444a63ee`).
The [independent workflow](../../.github/workflows/sir-i64-add-proof.yml)
also checks the SHA-256 of the Linux release archive. The proof imports
Lean's bundled `Init` library and uses kernel-checked `decide` examples.

```sh
cd proofs/sir-i64-add
lean --version
lean -DwarningAsError=true Fold.lean
```

This checks signed overflow (`0x7fffffffffffffff + 1`), full wrap
(`0xffffffffffffffff + 1`), keeping a live right operand, and rejection of
an incorrect sum, dropping a live operand, and crossing fuel or trap
instructions. `#guard_msgs` checks the output of `#print axioms`.
`add_mod` depends on `propext`. `accepts_sound` and `continuation_sound`
depend on `propext` and `Quot.sound`, both from Lean. Warnings are errors.

On Apple Silicon, from the repository root, run the native witness and
inspect the native root's selected export:

```sh
bin/amu run proofs/sir-i64-add/witness.kotoba
root="$PWD/seed/bootstrap/aarch64-macos/amu-full-root.macho"
probe=$(mktemp -d)
cp proofs/sir-i64-add/witness.kotoba "$probe/"
(
  cd "$probe"
  "$root" compile witness.kotoba --target aarch64-macos --output witness.kseed 3<.
  "$root" extract-native witness.kseed --symbol main --output witness.raw 3<.
  xxd -e -g4 witness.raw
)
```

At the [reviewed source snapshot](https://github.com/kotoba-lang/amu/tree/87ec570aff47a0a21b4876fcda4fa9d4e3b934fb),
the run printed `42`. The root SHA-256 was
`2cf49c2346437a9c3bd85f29cd72b7947d3280c98bed091ef99a552707d22370`.
The export offset was 60 bytes into the 96-byte payload. Its first four
words were `d2800005 d2800549 aa0903e0 d65f03c0` (`mov x5,#0`,
`mov x9,#42`, `mov x0,x9`, `ret`). The first word matches the `t2-emit1`
entry marker, after the earlier emitted body ends.
[T2 entry emitter](../../seed/41-a64gen.kotoba#L24740-L24765)

The existing Mac CLI pure-forms corpus runs with
`bin/amu run seed/tests/native-pure-forms.kotoba` and expects `0`.
