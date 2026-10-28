# Huffbench reusable-workspace initialization candidates

Three initialization candidates now pass native selfhost check/compile and
complete-workspace differential checks. **No speedup is established and none
is adopted.** asher was offline during this wave; the local Apple M1 Max had
load 17.53, so we did not run or rank performance samples there. The preceding
C comparison remains 7.289x slower and the C-or-better goal stays open.

## Hypothesis and implementations

The native seed emits handle validation and an index bounds check for each
`vector-assoc!`. Its zero-store path already uses AArch64's zero register,
so replacing scalar zero construction alone is not a useful next hypothesis.
The full reset currently mixes 500 input copies and 2,809 zero stores in one
recursive loop. Test whether separating those phases and grouping zero
stores reduces loop/control costs in the full workload sufficiently to
survive the research timing gate.

`generate_huffbench_port.py --reset-strategy` now offers:

- `full`: original mixed loop, still the default, byte-identical generated
  source and native code to the measured baseline.
- `split`: 500 input copies, then one zero store per iteration.
- `unroll4`: four checked zero stores per full iteration, with a checked
  single-store remainder.
- `unroll8`: eight checked zero stores per full iteration, with a checked
  single-store remainder.

Every candidate performs the same 3,309 initialization writes, retains the
same 3,309-cell allocation and reuses it. The terminal test precedes stores;
the grouped arm runs only when all group indices precede RESET-LIMIT. All
stores still use the compiler's checked primitive. There is no added host
callback, arena enlargement, guard removal, or embedded answer. The upstream
input and codec operations remain unchanged. `--initialization fresh` remains
an explicitly rejected independent experiment; its earlier memory failure
is not fixed or hidden by these new options.

## Verification and resource evidence

`check-huffbench-reset.py` adds an untimed diagnostic helper which fills the
entire workspace with -17 before running the real codec. It compares every
cell after **1 and 32 repetitions** against the same pinned C observation
oracle. This catches omitted resets that a fresh zeroed allocation could
conceal. Each candidate passes **6,618 cell comparisons**, batches
0/1/2/17/32, the out-of-range state-cell trap (SIGILL) and one-fuel batch trap
(SIGTRAP). All diagnostics are checked and compiled by source-built Amu
`abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e`.
The oracle selfcheck verifies 1,001 decoded/compressed bytes against unchanged
C, and all five C batch results agree. C initializes its workspace on each
body; its fixed-profile expected final state therefore repeats identically.

| Strategy | Native artifact bytes | Fuel consumed, 32 bodies |
|---|---:|---:|
| full | 13,248 | 818,123 |
| split | 13,488 | 818,155 |
| unroll4 | 13,688 | 750,763 |
| unroll8 | 14,000 | 739,531 |

These counts are **not timings or a performance ranking**. The source
recursion count changes, so fuel consumption need not equal the baseline;
all executed loop and function fuel checks remain in emitted code. The
binary includes static profile data as well as code; these sizes are not
an official dummy-subtracted Embench size score. PRODUCT dependencies are
unchanged. This wave authors new benchmark generation choices and a single
diagnostic helper; no available AST refactor rule covers those changes.

## Reproduction and next acceptance step

Generate each strategy from pinned `libhuffbench.c`, then use native Amu to
check, compile to aarch64-macos, and extract `batch`, `state-cell`, and
`test-huffbench`, retaining `<symbol>-extract.log`. Create `c-bridge.c` with
the existing pinned oracle generator. To repeat the correctness audit:

```
python3 scripts/seed/image/check-huffbench-reset.py <split-dir> <unroll4-dir> <unroll8-dir> \
  --compiler <source-built-amu> --runner <native-runner> \
  --oracle-library <diagnostic-c.dylib>
```

The audit refuses replacement of an existing report. Evidence in
`docs/evidence/coscientist-huffbench-reset-20261004/` includes all generated
sources, native artifacts, poisoned audit sources, complete cell/batch/trap
reports, provenance/check/extraction logs, the local C oracle library and its
pinned source inputs, resource counts, and member hashes. It also contains
`queued-measurements.tgz` with the three research directories ready for the
existing asher runner; this is a prepared replay bundle, not a running job.

After asher is reachable, extract that bundle under
`/private/tmp/amu-embench-compare-20261004`, copy the latest
`measure-huffbench-full.py`, and compare each against the preserved baseline:

```
python3 measure-huffbench-full.py coscientist-huffbench-reset-split \
  --reference coscientist-huffbench
# Repeat for reset-unroll4 and reset-unroll8.
```

Require all C state and batch checks, 30 rotated samples per arm, load <= 4,
>= 5% time reduction and a gap greater than summed sample SD, with relative
SD <= 10%, before any candidate promotion. Formal native perfgate and official
full-suite scoring remain separate unmet requirements. Recover the previous
rejected handle-prototype raw reports from asher as well. No measurement has
been restarted, and no background measurement is claimed live.
