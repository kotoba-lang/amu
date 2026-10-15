# Same-algorithm compiler m104 (a9edc1f0): adoption evidence, 15 October 2026

This directory records why the seed compiler built from `a9edc1f0d5021efabf6864e70c5b92d59257f348` (branch
`claude/embench-same-algo-m104-20261015`) is adopted as the pinned native bootstrap.

## What is adopted

* **Sources:** the `seed/MANIFEST` modules of `a9edc1f0`, merged with `main`. `main`'s changes since the merge base are the
  additive x86_64-linux modules and manifests; no file was changed on both sides. Unity sha256
  `5565bd0e41d0ba51e89a3f53af811902dd3cebe53ff41011c35eaa34462df808`.
* **Bootstrap:** `seed/bootstrap/adopted-20261012.bin` = `e5fc0ca2b6996deb1bf4722d285790eab2a35ea9724904f5cf2be296943d702d`
  (2,548,904 bytes). Its container `seed/bootstrap/adopted-20261012.kseed` = `0dcce679ba12900ec1a7a98207ed2dfacf2004de5d0e7abd54bc3ee9aee07fde`.
  * The image is a fixed point: `scripts/seed/build-adopted.py --generations 2` reproduces it, and
    `verify-preserved-integration.py --main` gets three identical generations.
* **Previous bootstrap:** the replaced image `87efe842…` (source `ffa4cfc1`) is kept here as `previous-bootstrap.bin` and
  `.kseed`.
* **Chain from the previous public bootstrap:** `87efe842` builds stage A = `ffa4cfc1`'s sources with this `seed/00-ns.kotoba`.
  That file differs only in 22 generated memory-map constants, and gives `5583a2fd…`. Then G1 = G2 = G3 = `e5fc0ca2…`.
  `bench/embench/reproduce-20261015/b_build.py --round rounds/sa-m104-20261015.json` re-runs this chain.
* **Policy-native golden:** regenerated per the #1313 convention by `native19-golden.py`, as
  `seed/main-same-algo-m104-native19.json` and `main-same-algo-m104-native19.tgz`.

## Qualification

* **Validation** (`tools/validate.py`): 39 images, 483/483 result/fuel/state observations, and 19/19 official images exact
  in result, fuel and all 17 arena counters.
* **Differential test:** 71,496 cases, 0 mismatches, over four shards.
* **Fuzz campaign** (random differential testing against the adopted `main` compiler):
  * Three bugs were found and fixed: b01 (nested short-circuit jump threading), b02 (stale fuel at host stack exhaustion)
    and b03 (latch coalescing, fixed in `e8f4ebe4`).
  * No wrong-result mismatch has been found since b03 in the m43 to m92 campaigns, for example m92b with 3,629 programs
    and 700,387 cases.
  * One m92a record was a compile wall-clock timeout (SIGALRM after 97 s on a heavily loaded host). The same program
    compiles in 4.9 s with this compiler.
* **Kernel scope:** same algorithm only. The policy and the per-kernel audit tables are in
  `bench/embench/reproduce-20261015/audit/`. The SHA-256 crypto instructions are off; sha256 runs on the scalar path.

## Official Embench rounds

Both were run on an Apple M4 with translated Kotoba ports, the upstream Embench driver and fresh C in the same cycle. The
reproduction package `bench/embench/reproduce-20261015/` (README in English and Japanese) re-checks and re-runs both.

| round | source | Kotoba / C (GM of (4/m_w)·K/C) | kernel scope |
|---|---|---|---|
| m93 | `be7f0ce3` | 0.7999 | contained substitution kernels and the SHA-256 instructions (see the audit) |
| corrected m104 | `a9edc1f0` (this compiler) | **0.8213** | same algorithm only; all 38 runs accepted on the first attempt, all exact |

## CI checks on this branch

They were run locally on macOS arm64; the Linux-only executions were not run. See the PR description for each step's
result and for the checks whose historical attribution needs an update with this adoption.
