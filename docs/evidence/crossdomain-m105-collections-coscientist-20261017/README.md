# M105 collections co-scientist experiments

Status: **exact result and fuel parity; timing exploratory and unqualified; no candidate promoted**.

These experiments continue the Generate → Debate → Reflect → Rank → Evolve loop from `docs/codegen-coscientist.md`. They use the same collections benchmark and the same adopted M105 compiler as the prior records. The M1 Max was heavily loaded during both runs, so the timing results do not establish a speedup or regression.

## Hypotheses

1. **Reciprocal division:** replacing repeated signed division by positive constant `1000003` with a hoisted reciprocal and `smulh` should reduce the collections hot loop. Counter-hypothesis: the reciprocal dependency and correction instructions cost at least as much as `sdiv`.
2. **Evolution with MSub fusion:** combining reciprocal division with `msub` remainder fusion should improve further. Counter-hypothesis: instruction scheduling or added dependencies cancel the saved `mul`/`sub` work.

## Method and exactness

Each compiler built the same benchmark source with the pinned adopted native bootstrap; the compiler images are the fixed-point images already recorded by the source evidence. Each workload size ran four ABBA samples per arm, with one warmup call and one measured call per fresh runner process. The runner checks the full result and fuel count before accepting a timing sample. Its vector capacities are 4,194,304 handles and 134,217,728 items; fuel limit is 167,772,160.

Both candidates match the prior at 20,000 and 50,000 iterations:

| Iterations | Result | Fuel consumed | Exactness |
|---:|---:|---:|---|
| 20,000 | 3,393,300,000 | 4,260,002 | pass |
| 50,000 | 8,483,250,000 | 10,650,002 | pass |

The reciprocal compiler image is pinned at `40696a8a…1fa55`; the reciprocal-plus-MSub image is pinned at `854fad33…258a3b`. Full SHA-256 values, emitted benchmark image hashes, runner hash, and all sample rows are in the JSON reports.

## Results

| Candidate | Iterations | Prior in-run median | Candidate in-run median | Candidate change | Sample ranges overlap? |
|---|---:|---:|---:|---:|---|
| Reciprocal | 20k | 36.966 ms | 34.730 ms | 6.05% shorter | yes |
| Reciprocal | 50k | 96.037 ms | 89.591 ms | 6.71% shorter | yes |
| Reciprocal + MSub | 20k | 106.429 ms | 94.889 ms | 10.84% shorter | yes |
| Reciprocal + MSub | 50k | 155.912 ms | 243.629 ms | 56.26% longer | yes |

Fresh-process medians for the reciprocal candidate were 4.35% and 5.14% shorter, with overlapping ranges and a 50k prior outlier. For the combined candidate, fresh-process medians were 4.16% longer at 20k and 65.78% longer at 50k, also with large overlap. The combined run cannot separate the candidate from scheduling noise.

Load averages were 72.10/69.24/65.96 before the reciprocal run and 71.34/66.93/65.45 before the combined run. The M1 Max was not a qualified quiet host. Treat both outcomes as exploratory observations only.

## Decision

The exactness and generated-code hypotheses remain valid. The reciprocal timing shows a positive but unresolved signal. The combined MSub hypothesis is not supported by a stable timing result. Keep both candidates out of the adopted compiler pending a quiet-host paired run. Neither result changes the C comparison, the Embench score, or SPEC qualification.

Files:

- `reciprocal-abba.json` — reciprocal candidate measurements and hashes.
- `combined-msub-abba.json` — reciprocal plus MSub measurements and hashes.
- `combined-msub-first-attempt-20k.json` — preserved first attempt; its report aggregation failed after the 20k samples, so it is excluded from the results above. The complete run was repeated after fixing the arm label.
- `kexe-benchmark-expanded-vectors.c` — exact C runner source used for both complete runs.
