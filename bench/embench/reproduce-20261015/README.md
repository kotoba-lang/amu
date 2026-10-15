# Reproducing the 15 October 2026 Embench result (Kotoba / C = 0.7999)

[日本語版 README.ja.md](README.ja.md)

This directory lets a third party check, rebuild and re-time the result published at
<https://kotoba-lang.org/blog/embench-c-parity-20261015/> (evidence bundle `/benchmarks/embench-official-20261015/`).
The measured compiler source is commit `be7f0ce358ebe8d1a715b2784f272ce0eda8e934` of this repository
(branch `claude/embench-c-parity-m93-20261015`). This package was added in a later commit on that branch and does not change
the measured source: `seed/` is identical at both commits.

## 1. What is claimed

On one Apple M4 Mac mini (macOS, arm64), in one measurement cycle on 15 October 2026:

* The 19 Embench IoT workloads, as translated Kotoba ports compiled by the seed compiler built from `be7f0ce3`, ran at a
  geometric-mean execution time of **0.7999× the original Embench C** compiled with Apple clang 17.0.0 `-O2`.
  Per workload, ratio_w = (4 / m_w) · K_ns / C_ns, where Kotoba runs n_w = LSF_w · 8192 · m_w iterations and C runs
  LSF_w · 32768. Both are normalized per iteration; below 1 means Kotoba is faster.
* Every Kotoba run was **exact**: the result, the benchmark and verify fuel, and all 17 arena counters equal values
  re-derived from trusted reference images (never from the measured compiler). Every C run printed one `EMBENCH_NS` line,
  with empty stderr and exit 0.
* The timing protocol was the upstream Embench speed driver (`benchmark_speed.py`, upstream commit `09c2ed8c`) with this
  harness:
  * warm-up 1, sample 1;
  * CPU admission: raw idle ≥ 70 % before, and raw idle and estimated background idle ≥ 70 % over the run;
  * at most 3 attempts, with retries only for CPU reasons; the first qualified attempt is selected, never the fastest;
  * a 0.5 s floor on every timed interval;
  * fuel budget 2^35;
  * the Kotoba campaign first, then fresh C, in the same cycle.
* The 19 measured images depend only on the source `be7f0ce3`, and the measured compiler is a selfhost fixed point. Level (b)
  builds it from the public native bootstrap with no JVM, GraalVM or Node.js. Level (b) builds the fixed-point compiler G* = S(S) from the
  public bootstrap and shows that G* compiles the 19 ports to byte-identical images.

## 2. What is not claimed

* **Not a certified Embench score.** The Kotoba programs are translated ports: Kotoba code written to follow each C benchmark,
  with a separate `benchmark-unchecked` / `verify-state` interface. Using the upstream driver and formula does not make this
  an unmodified Embench submission.
* **Certified kernels.** Most of the gain comes from certified kernels. When a function's intermediate code exactly matches a
  recognized shape, the compiler emits hand-written AArch64 for it:
  * the fuel accounting is identical to the general path, and there is a fallback to that path;
  * admission is by code shape, never by workload name;
  * but the shapes were written for hot functions of these ports, so the speedups do not carry over to other programs
    automatically.
* **SHA instructions.** `nettle-sha256` uses the ARMv8 SHA-256 instructions; the C build (`-O2`, no intrinsics) does not.
  With a scalar sha256 path (local estimate about 1.27×), the geometric mean would be about 0.848.
* **Single cycle.** One measurement cycle, on one host, with one accepted sample per workload. No confidence interval is
  claimed. Other hosts, compilers and load conditions will give other numbers (see level (d)).
* **The m_w projection is not a lower bound.** Actual / projected interval ranged from 0.67 to 1.76. Every interval still
  cleared the 0.5 s floor; the minimum was 0.777 s (matmult-int).
* **C side.** The C side is the unmodified upstream C with Apple clang 17.0.0 `-O2` only: no `-O3`, LTO, `-mcpu` or profile
  guidance.

## 2a. Kernel scope

The m93 compiler (`be7f0ce3`) contains certified kernels: hand-written AArch64 for recognized function shapes, admitted
under the rules in force on 15 October 2026 (see section 2). After publication, the project adopted a stricter rule for later
rounds: **same algorithm only**. Under it, a kernel may change *how* a source function's work is executed, but never *what*
work is executed. These are not allowed:
* closed-form results instead of the iterations;
* simulating the algorithm on another data structure;
* new run-time data structures the source does not build;
* reusing results across repetitions;
* a different algorithm.

An audit that classifies every kernel of this compiler is in progress. Its tables will be published in [`audit/`](audit/).
This package reproduces the published m93 round exactly as measured, whatever the audit finds. A later official round will use
a same-algorithm-only build and run through the same scripts (section 7).

## 3. Requirements

| level | needs |
|---|---|
| (a) offline | Python ≥ 3.9 only, on any OS (no network, no Apple hardware) |
| (b) build | macOS on Apple silicon (arm64), Xcode command-line tools (`clang`), `git`, Python 3; a normal clone with history (not `--depth 1`) |
| (c) exactness | as (b), plus `patch` |
| (d) timing | as (c), plus network access once to fetch Embench IoT from GitHub |

All commands run from the repository root. Each `--out` must be a new directory.

## 4. Verification levels

### (a) Offline: recompute everything from the raw records

```
python3 bench/embench/reproduce-20261015/a_offline.py
```

What it checks:

* `SHA256SUMS` of this package.
* The collection custody of both campaign arms. Every collected file is either vendored under `records/` with its recorded
  hash, or listed in `records/omitted-files.json` with the same hash and a reason. Omitted files are the
  measurement-host timer binaries, duplicate loader copies, the frozen C binaries and Embench upstream files.
* For every attempt of both arms, recomputed from the tick counters and raw stdout/stderr:
  * CPU qualification;
  * exactness;
  * the 0.5 s floor;
  * retry eligibility and first-qualified selection.
* The pre-registration arithmetic (m_w and the 0.6 s screen) and the exact timer invocations (n_w, caps).
* Both campaign geometric means, the 19 ratios and the full-19 GM.

With `--upstream <embench-iot checkout>`, the omitted upstream files are checked too. Expected last line:

```
LEVEL_A PASS GM 0.7998826447941968
```

(The published value 0.7998826447941967 differs only in the last bit, from summation order. The tolerance is 1e-12.)

### (b) Build: public bootstrap → fixed point → the measured images

```
python3 bench/embench/reproduce-20261015/b_build.py --out /tmp/embench-b
```

About 10 minutes on an idle M-series Mac; much longer under load. Steps and expected SHA-256:

| step | what | expected |
|---|---|---|
| 0 | loader = `clang -std=c11 -O2 seed/bootstrap/adopted-loader-20261012.c` | source `f44b5099…a8c3` |
| 1 | the public bootstrap `seed/bootstrap/adopted-20261012.bin` compiles its own source (unity of `ffa4cfc1`, `233cafbf…`) to itself | `87efe842dc0389f0ba7d476fcf034f6820483632df61fad53b474a2297e3e345` |
| 2 | stage A: adopted compiles the `ffa4cfc1` unity with `seed/00-ns.kotoba` taken from `be7f0ce3` (unity `f2dca71d…`) | `5583a2fdf8267938f466782fc6c7873eecc03f321a4434f2a6d8840794a6691d` |
| 3 | G1 = A(S), G2 = G1(S), G3 = G2(S), with S = unity of `be7f0ce3` (`1b9d9e30…`, 2,625,422 bytes); **G2 = G3** | **G1 = G2 = G3 = G\* = `bcd70b2474f0421a53c40c07b61bef100e52220f562def767958f51f07ddad16`** |
| 4 | G* compiles `ports/official-*.kotoba`; all 19 kseeds, native images and export tables equal the measured ones | `expected/measured-images.json` |

Why stage A: `be7f0ce3` enlarged the compiler's own memory map. Its `seed/00-ns.kotoba` differs from `ffa4cfc1`'s only in 22
generated constants: the larger TOK, NODE, SIR, CODE, FIX and OUT tables, and MM-WORDS. The public bootstrap's tables are too
small for the measured source, so it cannot compile it directly: it stops with
`seed: E101 compiler table full: region 1` (the token table). Compiling its own source with the new constants gives a
compiler with the old code generator and the new tables. No other source change is needed, and both input files are in
public commits.

**The measured compiler is the fixed point.** The round's compiler `bcd70b2474f0421a53c40c07b61bef100e52220f562def767958f51f07ddad16`
had been built by the development compiler m92. The chain above gives the same bytes already at G1 = A(S), and G1 = G2 = G3.
The reason is that the new optimizing tiers (T2 and the post-emission passes) are size-budgeted off for programs as large as
the compiler itself (`t2-max-sir` = 131072 SIR records in `seed/41-a64gen.kotoba`). So the compiler's own code comes from the
backend that `ffa4cfc1` and `be7f0ce3` share, and every producer with that backend (stage A, m92, S itself) yields the same
binary. The 19 ports are small, so they do get T2 and the certified kernels; step 4 shows their images depend only on S.

### (c) Exactness: run every image at its n_w

```
python3 bench/embench/reproduce-20261015/c_exactness.py --out /tmp/embench-c [--count-instructions] [--images /tmp/embench-b/step4-images]
python3 bench/embench/reproduce-20261015/c_reference.py --out /tmp/embench-cref
```

**`c_exactness.py`** builds each timer and runs it once at n_w with the official caps:

* The timer is `harness/separated-loader.c`. It is checked to be `seed/bootstrap/adopted-loader-20261012.c` plus
  `harness/separated-loader.diff`, plus the two timing headers and a generated header holding the image.
* It compares the result, fuel and the arena line with `records/round/expected-accounting-mw.json`. Expected: `LEVEL_C PASS 19/19 exact`.
* `--count-instructions` re-counts the timed-interval instructions at m=1 (I_w of the pre-registration), using the
  `tools/mktimer.py` / `validate.py` instrumentation. The counts agree with the pre-registered values to well under 1 %.
* Elapsed times printed here are not results.

**`c_reference.py`** re-derives the expected values at each n_w from the trusted reference images in `reference/`:

* **round51**: the original translated ports, compiled by the qualified WM G4 fixed point. Their round51 raw records are where
  the m=1 values (`reference/expected-original-accounting-m1.json`) came from.
* **round114**: images from an independent compiler, used as a cross-check.

Both run in the same harness. Requirements:

* both reproduce the m=1 values;
* they agree with each other at n_w;
* they equal the published expected values;
* fuel and the 17 arena counters are exactly affine in n, from ≥ 3 points per multiplied workload. The only deviation is
  tarfind's benchmark fuel, whose step-to-step increments differ by 2,250 out of 7.84e9 (data-dependent, warm-seeded work);
  its value at n_w is measured directly.

Expected: `LEVEL_C_REFERENCE PASS`, after about 10–30 minutes.

### (d) Timing: your own same-host campaign

```
python3 bench/embench/reproduce-20261015/tools/fetch_upstream.py --dest /tmp/embench-iot
python3 bench/embench/reproduce-20261015/d_timing.py --upstream /tmp/embench-iot --out /tmp/embench-d
```

What it does:

* builds the 19 C binaries with your clang (`c/build_c.py`, the exact official command line);
* builds the 19 Kotoba timers;
* runs the Kotoba campaign, then the C campaign, through the unmodified upstream driver and the round's `run_trigger.py`
  files (`harness/kotoba`, `harness/c`), with the full protocol (load gate, CPU-only retries, first qualified);
* prints the full-19 GM only if all 38 runs are accepted, since there is no subset GM.

`--workloads crc32,edn` gives a short smoke run, which never prints a GM.

`d_timing.py` re-implements the round's two campaign scripts with parameterized paths. Those scripts are kept verbatim in
`records/official/campaign.py` and `records/fresh-C/campaign.py`. What it keeps the same: the timer invocations (n_w,
caps), the driver command, the `run_trigger.py` files and the score formulas. What it drops: the measurement host's
custody receipts and process patterns. It also builds C instead of reusing the frozen binaries.

**Expected spread.** The published 0.7999 is one cycle on one Apple M4 under its background load, with C built by Apple clang
17.0.0. Your result depends on:

* your CPU (the C and Kotoba code use the core differently);
* your clang version (the C binaries change);
* background load and thermal state.

Per-workload ratios can move by 10 % or more, and the GM by several percent. On a busy machine the 70 % CPU gate refuses
attempts (`quiet-admission-timeout`, `raw-post-cpu`); run on an otherwise idle machine. The frozen official C binaries'
hashes are in `records/fresh-C/source-custody.json`. A different clang builds different, equally valid binaries.

## 5. Contents

| path | what |
|---|---|
| `a_offline.py`, `b_build.py`, `c_exactness.py`, `c_reference.py`, `d_timing.py` | the five commands |
| `tools/repro_lib.py` | shared helpers: unity from git commits, loader build, compiler invocation, timer generation, caps, exactness rule |
| `tools/fetch_upstream.py` | fetch and verify Embench IoT at `09c2ed8c` (40 source and 6 driver hashes) |
| `tools/make_sums.py` | maintainer tool that writes `SHA256SUMS` |
| `ports/official-<w>.kotoba` | the 19 measured port sources, with SPDX license lines (see `ports/PROVENANCE.md`) |
| `images/<w>.bin`, `images/<w>.kseed` | the 19 measured images (native code; the kseed adds the export table) |
| `harness/` | timer loader + its patch from the public loader, timing headers, `run_trigger.py` for both arms, `darwin_cpu_idle.py`, workload table (LSF, m_w, n_w, caps) |
| `c/build_c.py`, `c/boardsupport.c` | C build with the exact official command line; the timing board support (`EMBENCH_NS`) |
| `reference/` | trusted reference images (round51 WM G4, round114) with export tables, and the original m=1 expected values |
| `records/round/` | protocol revision text, hashed pre-registration, reference-accounting receipt, expected values at n_w, compile/preparation/precheck receipts, verifier review, final summary |
| `records/official/`, `records/fresh-C/` | the collected campaign records of both arms (reports, raw attempts, quiet-admission probes, invocation scripts, custody), verbatim |
| `records/omitted-files.json` | collected files not vendored here, with hashes and reasons |
| `expected/` | pins for level (b): build inputs, compiler chain, measured images |
| `rounds/` | round configs (commit, multiplier table, pins); `m93-20261015.json` is the published round and the default |
| `audit/` | kernel audit tables for the m93 compiler (added when the audit is complete) |

`records/` files are verbatim evidence. They keep the absolute paths and the host label of the measurement machines, because
their hashes are part of the custody chain. The scripts never use those paths.

## 6. Licenses and provenance

* Embench IoT (upstream `https://github.com/embench/embench-iot`, commit `09c2ed8c`) is GPL-3.0-or-later. The C sources are
  fetched, not vendored. `records/*/upstream/baseline-data/speed.json` is the upstream baseline table, needed for the
  formula.
* The Kotoba ports translate the Embench C programs and keep their copyright and SPDX lines (GPL-3.0-or-later; MIT for
  md5sum and tarfind; Apache-2.0 for depthconv); see `ports/PROVENANCE.md` and `bench/embench/licenses/`.
* `c/boardsupport.c` and the harness are this project's measurement code. The timer loader is derived from
  `seed/bootstrap/adopted-loader-20261012.c`; the derivation is `harness/separated-loader.diff`.

## 7. Running another round

The scripts are parameterized by a round config, `rounds/<name>.json`. The default is `rounds/m93-20261015.json`, the published
round. A config names:
* the measured source commit;
* the files stage A takes from that commit (`seed/00-ns.kotoba`);
* the port and image directories;
* the workload table;
* an optional `multipliers` table `{workload: m_w}`;
* where the round's expected values, pre-registration, records and pins live.

With a `multipliers` table, n_w = LSF · 8192 · m_w and the arena caps are recomputed by the pre-registration rule. The rule is:
a KEXE resource whose m=1 usage × m_w exceeds its m=1 capacity gets capacity × m_w. Two limits apply:
* **Fuel:** projected (benchmark + verify) fuel must stay ≤ 0.9 · 2^35.
* **Loader ceilings:** pairs 64 Mi, string pool 1 GiB, vectors 64 Mi, vector items 128 Mi. Exceeding one makes a multiplier
  infeasible. In particular, **aha-mont64 can only run at m_w = 1** (it needs about 50.3 M vectors at m = 1), and statemate
  is limited to m_w = 1 by fuel.

`tools/repro_lib.py:feasible_multipliers` lists the allowed values. For a new commit and multiplier table:

```
# 1. compiler chain and images (no pins yet: records them)
python3 bench/embench/reproduce-20261015/b_build.py --round rounds/<name>.json --out /tmp/r-b --record bench/embench/reproduce-20261015/expected/<name>
# 2. expected values at the new n_w from the trusted references (never from the candidate)
python3 bench/embench/reproduce-20261015/c_reference.py --round rounds/<name>.json --out /tmp/r-cref --write bench/embench/reproduce-20261015/expected/<name>/expected-accounting.json
# 3. exactness of the new images
python3 bench/embench/reproduce-20261015/c_exactness.py --round rounds/<name>.json --images /tmp/r-b/step4-images --out /tmp/r-c
# 4. timing
python3 bench/embench/reproduce-20261015/d_timing.py --round rounds/<name>.json --images /tmp/r-b/step4-images --upstream /tmp/embench-iot --out /tmp/r-d
```

Then add the recorded files to the config's `pins` and `expectedAccounting`, so that later runs compare instead of record.
The official round's records can be checked with `a_offline.py --round` once they are laid out like `records/`.

