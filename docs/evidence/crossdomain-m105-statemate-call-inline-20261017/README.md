# Statemate repeated-state driver call probe

Status: exploratory, not promoted. This probe asks whether removing the small
`body` wrapper call from Kotoba's repeated state-machine driver improves the
largest current M105 workload gap.

## Comparison context

The M105 M4 analysis records statemate Kotoba/C geometric means of 1.287443
for the baseline campaign and 1.455884 for the candidate campaign. The image
is unchanged between compiler variants; same-image timing controls also move,
so the candidate-over-baseline normalized ratio 1.130833 is not attributable
to compiler codegen. See
[`analysis.json`](../m105-abba-m4-20261016/analysis.json).

The upstream C benchmark keeps state in scalar globals and a 64-byte
`Bitlist`. `benchmark_body` clears the bitlist and calls `init`, `interface`,
and `FH_DU` in its inner loop. The Kotoba port represents state as a
169-element vector and has 517 private `s-N` functions and 355 `vector-at`
reads. These are source-shape differences that may explain codegen cost; they
do not prove why the timed ratio differs. The inspected upstream C source SHA-256
is `389c4bae5caba79a6f9139e02bf5e61c92921a756ec01200d2d2f16dc1c4ccf5`.

## Source and generated image

The only source change was:

```clojure
(repeats (body s) (- n 1))
```

to:

```clojure
(repeats (c-FH_DU (c-interface (c-init (clear-bits s 0)))) (- n 1))
```

Both versions were compiled with the same selfhost G3 (`bf6148d2…0110fdc7`)
and trusted loader (`05798f17…6b482f7aa`) on macOS arm64. The baseline image
exactly matches the pinned official image: 264,184 bytes,
`6cb09af5443a9e2ce159f2853b92db2e74b887e73a108349c4cde2b65d5e6636`. The
inline image is 264,568 bytes,
`28832123206f8cfbf8ce281dec745f3bd53af64288c0872e3bc8a251b03655c9`.

The baseline native `repeats` loop calls `body` with `bl` on each iteration;
the `body` entry also performs a fuel check. This gives the hypothesis a
concrete code path to remove.

## Exactness and timing

All six executions returned result `1` and matched the expected arena report.
Baseline benchmark fuel was `20159447042`; inline benchmark fuel was
`20132167682`. The difference, `27279360`, equals `n`, so the source edit
removes one fuel charge per iteration. It does not match pinned fuel and does
not pass the full exactness rule.

Samples ran in this order (`base, inline, inline, base, base, inline`):

| Variant | Elapsed seconds |
|---|---:|
| Baseline | 18.6021, 8.5283, 4.5008 |
| Inline | 16.3758, 10.7764, 20.1091 |

The baseline alone varies by more than 4x. No per-sample quiet-host gate was
recorded, and the timing protocol therefore does not establish a speedup or
regression. The full receipt, including all six samples, exactness fields, and
source/image/compiler hashes, is in [`receipt.json`](receipt.json).

## Next candidate

Do not promote the source rewrite. First evaluate a compiler transform that
removes repeated bounds work for constant-index accesses when a fixed vector
length is proven, while preserving exact fuel. Then compare generated code and
run a qualified paired timing campaign.
