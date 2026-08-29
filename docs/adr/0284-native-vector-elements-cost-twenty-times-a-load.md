# ADR 0284: A native vector element costs ~21x a C load, and the context call is only half of it

- Status: accepted
- Date: 2026-08-30

## Decision

Native `vector-i64` / `vector-f64` are not a viable representation for
bulk element data (pixel planes, sample buffers, codec working sets). Two
independent bounds say so, and neither is removed by finishing the export
copy ABI:

1. **Capacity.** The whole element arena is 65,536 words
   (`kexe_loader.c` `KEXE_VECTOR_ITEM_CAPACITY`), one vector is capped at
   16,384 (`kotoba.kir.value/vector-item-limit`), and the handle table holds
   4,096 entries. A 256x256 luma plane exactly exhausts the total arena on its
   own; 320x240 does not fit at all.
2. **Cost.** Touching one element costs 21x what the same loop costs in C at
   `-O3`, measured below.

Two defects blocking the measurement are fixed here (see Evidence). The export
copy ABI's parameter half is **not** built, and the reason is in Evidence: the
result half it would mirror does not exist below the admission gate.

## Evidence boundary

### What was measured

Host: MacBookPro18,4, Apple M1 Max, 10 cores, macOS. All arms interleaved in
one shell loop, `CLOCK_THREAD_CPUTIME_ID` (not wall clock -- this host ran at
load1 341-422 from other sessions throughout), minimum over rounds, n=7.
Qualified with `perfgate` default policy against a `:measured`
`machine.core` descriptor probed by `sysctl`; all three comparisons returned
`:qualified? true` with `:reasons []` and `gap > summed-stdev`.

| arm | ns per element | rel-stdev |
|---|---|---|
| Kotoba native, loop with one `vector-at` | **6.920** | 0.0035 |
| Kotoba native, identical loop without it | **3.678** | 0.0465 |
| C `-O3`, `acc += a[i]` | **0.329** | 0.0881 |
| C `-O3`, indirect call to the same `checked_vector_at` body | 4.547 | 0.0041 |

- Kotoba native vs C, per element touched: **21.1x**.
- The loop **alone**, performing no element access at all: **11.2x**.
- Marginal cost of the `vector-at` context call: **3.242 ns**, itself 9.9x the
  entire C loop.

The middle row is the finding that matters. **The host context call is not the
dominant cost.** Removing it entirely would move 21.1x to 11.2x. The rest is
the backend's tail-recursive loop, which spends ~15 instructions of stack
traffic per element before the call target runs: `emit-heap-call` spills every
argument to the stack (`save-x0` / `restore-to`, two instructions each) and
brackets the call with a seven-instruction context-pointer save/restore, all
of which are single instructions in `kotoba.native.aarch64`.

Re-measured at load1 126-134 after other sessions drained: the Kotoba arm
moved 6.920 -> 7.010 ns, **1.3% for a 3x change in host load**. That is the
evidence the clock choice was sound, not that the host was quiet -- ADR 0281
established no fleet host reaches the quiet-gate threshold.

Native results were checked against the KIR reference interpreter
(`kotoba.kir/execute`) at identical inputs: both arms return 2016 at reps=1 and
6048 at reps=3, matching the interpreter exactly, and 16,128,000 at reps=8000
(= 2016 x 8000). Export offsets came from the artifact's own `:exports` table
(`run-touch` at 524, `run-base` at 632); zero was never passed.

### Two defects fixed

**`kotoba-native`: `:vector-i64` was spelled `:vector`.**
`machine-ir/word-result-type?` listed `:vector`, a spelling no producer emits
-- `:vector-i64` appeared **nowhere** in that repository, while kotoba-kir, the
verifier and the frontend all use it. `scalar-boundary-type?` is applied to
every parameter and result, so one function taking or returning a
`:vector-i64` rejected the whole module as `unsupported-function-module`.
`:vector-f64` was spelled correctly, so the f64 family crossed function
boundaries while the i64 family could not -- an asymmetry that reads from
outside as `:vector-i64` lacking a constructor. It does not: `vector-new` is
admitted by `kotoba.kir/only-native-word-typed-features?` and lowers through
`vector-new-empty` plus one `vector_conj` per element.

Admitting the correct spelling adds no representation and no lowering: both
families alias onto the same six host slots (`vector-op-aliases`). Pinned by
`kotoba.native.vector-boundary-spelling-test`, which derives its expectation
from `kotoba.kir/native-private-handle-type?` rather than restating it.
Falsified: restoring `:vector` fails 3 assertions and errors 1, with
`:problem :unsupported-function-module`, while the `:vector-f64` control still
passes. Full suite after the fix: 216 tests, 2457 assertions, 0 failures.

**`amu`: the JDK-free driver could not describe an f64 program.**
`kotoba.compiler.nbb.cli` selected the value ABI from two branches where
`kotoba.compiler.core`, `nbb.wasm-cli` and `kotoba.verifier` all select from
four. Any native compile through `bin/amu` carrying floating point stamped
`:kotoba.typed/externref-v1` while the verifier re-derived
`:kotoba.typed/mixed-f64-v2` and refused the artifact. Falsified end to end:
the same `vector-f64` source exits 65 `native compatibility metadata rejected`
before and 0 after, with the artifact now carrying `mixed-f64-v2`. Pinned by
`test/nbb/native-value-abi.cljs`; reverting the fix fails exactly the three
f64/f32 assertions and leaves both controls green.

`native-value-abi` derives from the KIR rather than the HIR because the KIR is
what the verifier reads back out of the sealed artifact.

### What was NOT done, and why

**The export copy ABI's parameter half was not built.** The premise for
building it was that the result half exists and needs a symmetric counterpart.
It does not exist. `kotoba.kir/native-export-copy-result-type?` and the
verifier's independent copy both admit an exported zero-arity function
returning a vector, but `tools/kexe_loader.c` has no vector value for
`KEXE_RESULT_TYPE` (`i64`, `string`, `option-i64`, `result-i64`, `record:N`,
`variant:...` only), the backends emit no copy-out, and
`kototama.native.executor/admit-entry-result!` refuses the type. Such a module
verifies and then hands its caller a raw table index.

That is already the failure this workspace forbids -- an admission gate that
admits what nothing can lower. Adding a symmetric parameter half would double
it. The parameter half is worth building **after** the result half has a
loader implementation, and the measurement above says neither is worth building
for bulk data.

**The capacity ceilings were not raised.** They are a sandbox bound, not a
tunable: `verify-runtime!` demands exact equality on `:vector-capacity 4096`
and `:vector-item-capacity 65536` alongside fuel, `:memory-bytes 65536` and
`:stack-bytes 4096`, the loader pins the same numbers with `_Static_assert`,
the arenas are fixed-size arrays inside one `struct kexe_shared_v3`, and every
exhaustion path raises `SIGILL`. Raising them changes the loader's memory image
and the pinned runtime identity SHA. That is an owner decision.

### Limits of this evidence

- AArch64 only. x86-64 emits the same shape (`emit-heap-call` is the same
  function) but was not run.
- One access pattern: sequential reads over a 64-element vector resident in L1.
  A working set exceeding the arena cannot be built at all, so no cache-miss
  regime was measured -- and cannot be, under the current bound.
- `vector-conj` was measured only as setup, not as an arm. It interns a table
  entry per element and relocates on append, so construction cost is
  additional to everything above.
- These are upper bounds. Thread CPU time removes descheduling, not cache or
  SMT interference from a host at load 126-422.
- No claim is made that a different representation would be fast. This ADR
  measures the one that exists.
