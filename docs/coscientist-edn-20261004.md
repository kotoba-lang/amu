# Selfhost EDN: complete body and rejected short-conversion candidates

The new `bench/embench/batch-ports/edn.kotoba` runs all eight upstream EDN
operations in order: vector multiply, MAC, FIR, FIR with redundant-load
elimination, lattice synthesis, IIR, the upstream empty codebook search, and
both JPEG DCT passes. It preserves signed-short conversions, arithmetic
shifts, scalar results, output initialization and persistence between body
iterations. The old `ports/edn.kotoba` remains the explicitly adapted probe;
no historical measurements are relabelled.

## Differential evidence

Both native `amu check` and native `amu compile` accept the complete source.
The compiler is the three-generation source-built unified Amu image
`abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e`.
No Node/nbb/JVM compiler is used. The final native artifact is
`60049792f18b9d7c43a253807b567096f7f31fd8a18138f32791e0a179c0ec5c`.

For each of nine states (initialization and after each of eight operations),
all 603 values are compared independently: `a[200]`, `b[200]`, `output[200]`,
and `c`, `d`, `e`. **5,427/5,427 match C**, including the DCT array that the
upstream verifier does not examine. Batch counts 1, 2, 17 and 32 satisfy the
unchanged upstream output/scalar oracle; count 0 returns 0 in both adapters.
An earlier hash comparison of these states also agrees, but the per-cell
comparison is the stronger final evidence.

The recorded seed caps constant vectors at 128 items. Generation keeps all
200 items in two checked tables. It does not truncate the input or redefine
language semantics. The immutable B table represents the values that the C
body copies into a global array on each iteration. Kotoba uses an i64 vector
for A/output/scalars rather than C's short/long globals; copying and checked
access costs therefore differ. This is a complete fixed-workload translation,
not a pure estimate of compiler efficiency.

The first exploratory source compiled but `check` refused its mutable-handle
flow. The final algorithm passes handles directly through nested consuming
calls, reads scalar arguments before handing a handle over, and keeps the
FIR read loop inside its consuming function. Both native commands now pass;
no checker, ownership guard, bounds check or fuel rule is weakened.

## Matched native timings on asher

Thirty rotated samples per arm, 32 body iterations per call, one untimed
warmup, calibrated intervals around 300 ms. Both adapters verify once after
the batch. This includes amortized verification/allocation/ABI overhead;
the Kotoba arenas/fuel reset once per batch. C uses unchanged upstream
benchmark_body with Clang 17 `-O2`, local scale 1 and global scale 32.

| Initial complete-body run | Mean ns/body | Sample SD ns |
|---|---:|---:|
| Kotoba / selfhost Amu | 13,645.480 | 538.557 |
| C | 950.431 | 58.289 |

Kotoba is **14.357x slower than C**. Maximum observed load is 2.17 (gate <=4).
This load criterion does not establish CPU-idle qualification. No official
Embench score, formal perfgate result, or C-or-better claim follows.

## Co-scientist rejection evidence

The emitted short conversion uses mask/compare/branches/subtract. The
target-independent identity `sshr(shl(x,48),48)` has four emitted instructions
including result move/return, versus ten for the branch helper. Its two-shift
result agrees with the branch version in 327,680 lane comparisons across
five upper-bit patterns (including MIN/MAX regions) and named signed limits.
Both EDN candidates also match every one of the 5,427 C state values.

Fewer helper instructions did **not** produce an adoptable whole-body win:

| Same-run experiment | Reference ns/body | Candidate ns/body | Verdict |
|---|---:|---:|---|
| Source-generated shift helper | 13,834.635 | 16,394.750 | reject, 18.51% slower |
| Hand-patched helper, every other byte/offset retained | 14,401.683 | 13,993.184 | reject, 2.84% reduction not separated |

For the second run, the 408.499 ns gap is smaller than the summed sample SD
of 1,221.617 ns and below the 5% research threshold. The source-generated
variant changes layout as well as the helper; the isolated patch preserves
it. These results do not establish layout as the cause of the slowdown.
Neither candidate is promoted and no compiler optimization is implemented
from this hypothesis. The branch strategy remains the generator default.

## Reproduction and claim boundary

Upstream commit: `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`.
EDN source SHA256:
`2604a80fbe70e2b6bc4276649bfb5974d02e18f70b84fc804c7d52bf47f6a20e`.
`bench/embench/generate_edn_port.py` refuses a different profile and combines
its extracted tables with `edn-full-body.kotoba`. `--short-strategy shifts`
reproduces the rejected source candidate. This is new algorithm authoring and
profile generation; existing product sources are not text-refactored.

Generate/check/compile with the source-built Amu, then extract each exported
`batch`, `stage-hash`, and `stage-cell` to `<symbol>.bin`, saving extraction
stdout as `<symbol>-extract.log`. Put `edn.kotoba`, `check.log`, and the archived
`c-bridge.c` in a directory under the comparison root containing `runner`,
`images/r6m`, and pinned `upstream`. Run:

```
python3 scripts/seed/image/measure-edn-full.py <research-directory>
# Optional same-run reference:
python3 scripts/seed/image/measure-edn-full.py <candidate-directory> \
  --reference <reference-directory>
```

The harness rebuilds the C adapter against unchanged upstream functions,
compares all state cells, verifies batch results, calibrates each arm,
rotates sample order, checks load, and records source/native/C/compiler/runner
hashes. It refuses to replace an existing result. Reference batches are also
checked. A patched prototype is explicitly labelled in its report.

Evidence: `docs/evidence/coscientist-edn-20261004/research-artifacts.tgz`
contains all three experiments, full raw results, native and C artifacts,
provenance/extraction/check logs, exhaustive short tests, disassembly and
patch metadata. `sha256.json` covers archive members; `summary.json` gives
compact experiment summaries. Final generated-source attribution/comments
are reflected in regenerated provenance; its machine bytes match the measured
baseline exactly. The PRODUCT dependency inventory is unchanged.

EDN now has a complete verified alternative, extending coverage beyond the
original nine full correctness translations. Nine adapted workloads remain
without complete replacements: huffbench, nettle-aes, nsichneu, picojpeg,
qrduino, sglib-combined, slre, statemate and wikisort. Initialization/timing and
size-score work also remains. The full-suite C-or-better goal stays open.
Next investigate the measured loop/access/call costs rather than adopting
the refuted helper-instruction-count prediction.
