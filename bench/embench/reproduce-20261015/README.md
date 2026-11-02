# Embench-derived results and reproduction (M104 corrected; M93 historical)

[日本語版 README.ja.md](README.ja.md)

This directory lets a third party check, rebuild and re-time the result published at
<https://kotoba-lang.org/blog/embench-c-parity-20261015/> (evidence bundle `/benchmarks/embench-official-20261015/`).

## Current measurement status

* **Do not cite the original M93 value, 0.7999, as a same-algorithm result.** A later kernel audit found substitution kernels
  in the measured M93 compiler; it also used ARMv8 SHA-256 instructions only on the Kotoba side. M93 remains below as a
  historical reproduction record.
* The corrected **M104** round measures all 19 workloads with the same-algorithm-only selfhost fixed-point compiler, scalar
  SHA-256, the pinned upstream Embench speed driver and the documented per-iteration ratio formula. The original Apple M4
  cycle reports **Kotoba / C = 0.8213**. A separate 16 October cycle on another Apple M4 Mac mini (`Mac16,10`, 16 GB,
  macOS 26.3.1) passed 19/19 in both arms and reports **0.7877703356** using freshly built Apple clang 21.0.0 C binaries.
  These host-specific cycles are retained separately and are not averaged. Both are **Embench-derived translated-port
  comparisons**, not official or certified Embench scores: the Kotoba programs use a project-specific translation and harness.
  The follow-up's raw evidence and independent verifier are in
  `round-sa-m104-20261015/records/m4-macmini-attempt-20261016-r1/`.
* The 16 October 2026 Apple M1 Max attempt retained its records but was **rejected and is not a score**. The external
  10-second raw-idle gate reached 70.39% once and started the campaign, but the two executed `aha-mont64` attempts in each
  arm were rejected because raw idle during timing was below 70%. The other 18 workloads timed out at quiet admission and
  did not execute. Both arms accepted 0/19 workloads, so there is no geometric mean. The full raw record is in
  `round-sa-m104-20261015/records/m1-attempt-20261016-r1/`.
* The M104 protocol requires at least 70% raw CPU idle before each attempt, raw and estimated background idle at least 70%
  during every timed run, full 19/19 acceptance for both arms, exact Kotoba outputs, and retained raw records. No M1 score
  is claimed until a full run passes and its raw records are independently checked against the protocol.

The method reference is the [Embench User Guide](https://github.com/embench/embench-iot/blob/master/doc/README.md) and the
pinned [Embench upstream source](https://github.com/embench/embench-iot/tree/09c2ed8c3b7008c95d08b038de4a3f6dc103ed70). The
reproduction uses that commit's unmodified speed driver and baseline table, with custom Kotoba/C target modules. The target
programs and harness therefore remain a translated-port comparison, not an unmodified Embench submission.

For the historical M93 reproduction below, the measured compiler source was commit `be7f0ce358ebe8d1a715b2784f272ce0eda8e934` of this repository
(branch `claude/embench-c-parity-m93-20261015`). This package was added in a later commit on that branch and does not change
the measured source: `seed/` is identical at both commits.

## 1. Historical M93 claim (superseded)

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

**Audit findings for the m93 compiler.** The audit is complete. The policy and the tables are in [`audit/`](audit/):
`KERNEL-POLICY.md`, `kernels-a.md`, `kernels-b.md`, `kernels-c.md` and `kernels-other.md`. Under the policy, with unsure
cases counted as substitution, the **measured m93 compiler contains these substitution kernels**:
* huffbench: `st` (sort-table as a run merge on a copy), `hd` (decode-bits through a per-call scan table) and `eb`
  (encode-bits per symbol instead of per bit);
* qrduino: `qa` (all-runs on bit words with a bit transpose), and `bp` and `mr` (blocks-row and mask-row evaluated
  bit-parallel; unsure);
* tarfind: `lcg` (the seeded LCG advanced two steps at a time; unsure);
* ud: the column-0 path of `init` (the row sum in closed form);
* picojpeg: the whole-block NEON IDCT, which takes DC-only lanes through the AC butterfly instead of the source's fill
  branch (unsure).

In addition, **nettle-sha256 uses the ARMv8 SHA-256 crypto instructions**. The published 0.7999 includes all of these. The
**next official round will use a same-algorithm-only build, with the scalar sha256 path**, and will run through the same
scripts (section 7). This package keeps reproducing the published m93 round exactly as measured.

**SHA-256 conditions (owner decision, 2026-10-29).** A comparison with C runs under C-equivalent conditions: the scalar
sha256 path. An ordinary compile uses the ARMv8 SHA-256 instructions. `compile ... --no-crypto-hw` selects the scalar
path; a new round that compares with C must pass it and record it. The option is in the compiler source
(`seed/41-a64gen.kotoba`, `kb-sha-hw`); the m93 and M104 compilers in this package do not have it (m93 has the hardware
paths on, M104 has them compiled out), so this package's harness is unchanged. Evidence:
`docs/evidence/crypto-hw-option-20261029/README.md`.

The tables also cover later development snapshots (m97 to m101), so they list substitution kernels that are not in m93:
picojpeg's end-of-block bitmask, sglib `qk`, `ls` and `tb`, xgboost `xs`, and slre's set entries were added after m93 or
never merged. Each statement about m93 above was checked against `seed/41-a64gen.kotoba` at `be7f0ce3`.

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
python3 bench/embench/reproduce-20261015/a_offline.py --round rounds/m93-20261015.json
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
python3 bench/embench/reproduce-20261015/b_build.py --round rounds/m93-20261015.json --out /tmp/embench-b
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
python3 bench/embench/reproduce-20261015/c_exactness.py --round rounds/m93-20261015.json --out /tmp/embench-c [--count-instructions] [--images /tmp/embench-b/step4-images]
python3 bench/embench/reproduce-20261015/c_reference.py --round rounds/m93-20261015.json --out /tmp/embench-cref
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
python3 bench/embench/reproduce-20261015/d_timing.py --round rounds/m93-20261015.json --upstream /tmp/embench-iot --out /tmp/embench-d
```

What it does:

* builds the 19 C binaries with your clang (`c/build_c.py`, the exact official command line);
* builds the 19 Kotoba timers;
* runs the Kotoba campaign, then the C campaign, through the unmodified upstream driver and the round's `run_trigger.py`
  files (`harness/kotoba`, `harness/c`), with the full protocol (load gate, CPU-only retries, first qualified);
* prints the full-19 GM only if all 38 runs are accepted, since there is no subset GM.

`--workloads crc32,edn` gives a short smoke run, which never prints a GM.

If `--images` is supplied, every kseed must match the selected round's pinned kseed, native payload, exports, and source
table. If `--c-binaries` is supplied, its `build-c.json` must be a schema-2 receipt from `c/build_c.py`; the verifier checks
the pinned upstream revision, every compiled source and included header, the recorded `-O2` command, and each binary hash.
Both upstream driver exit codes must also be zero before a full-19 GM is reported.

`d_timing.py` re-implements the round's two campaign scripts with parameterized paths. Those scripts are kept verbatim in
`records/official/campaign.py` and `records/fresh-C/campaign.py`. What it keeps the same: the timer invocations (n_w,
caps), the driver command, the `run_trigger.py` files and the score formulas. What it drops: the measurement host's
custody receipts and process patterns. It also builds C instead of reusing the frozen binaries.

**Expected spread.** The original M104 Apple M4 cycle reports 0.8213; a separate Mac16,10 follow-up with Apple clang 21.0.0
reports 0.7877703356. Keep these host-specific cycles separate; do not average them into a universal M4 value. Do not use
the historical M93 0.7999 as a same-algorithm result. Your result depends on:

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
| `round-sa-m104-20261015/records/m4-macmini-attempt-20261016-r1/` | second-host full-19 M4 cycle, fresh clang build receipt, raw attempts, upstream verification, and an independent record verifier |
| `round-sa-m104-20261015/records/m1-attempt-20261016-r1/` | rejected M1 Max attempt, CPU gate evidence, and all raw attempt records; not a benchmark score |
| `records/omitted-files.json` | collected files not vendored here, with hashes and reasons |
| `expected/` | pins for level (b): build inputs, compiler chain, measured images |
| `rounds/` | round configs (commit, multiplier table, pins); `sa-m104-20261015.json` is the default corrected round; M93 is historical |
| `audit/` | the kernel scope policy and the kernel audit tables (see section 2a) |
| `round-sa-m104-20261015/` | the corrected same-algorithm round (section 8): records, images, workload table, pins |

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

The scripts are parameterized by a round config, `rounds/<name>.json`. The default is the corrected
`rounds/sa-m104-20261015.json`. To reproduce the historical M93 round, pass `--round rounds/m93-20261015.json`. A config names:
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

## 8. The corrected same-algorithm round (m104, 15 October 2026)

This branch, `claude/embench-same-algo-m104-reproduce-20261015`, is based on commit `a9edc1f0d5021efabf6864e70c5b92d59257f348`,
the same-algorithm-only compiler source. The m93 round above stays reproducible from it, because `be7f0ce3` and `ffa4cfc1` are
ancestors. Its round config is `rounds/sa-m104-20261015.json`, and its data is in `round-sa-m104-20261015/`.

* **Compiler.** `e5fc0ca2b6996deb1bf4722d285790eab2a35ea9724904f5cf2be296943d702d`. The chain is the public bootstrap →
  stage A `5583a2fd…` → G1 = G2 = G3 = `e5fc0ca2…`, so the measured compiler is the fixed point, and all 19 images are
  identical to the measured ones.
* **Kernel scope.** Same algorithm only (`audit/KERNEL-POLICY.md`). The SHA-256 crypto instructions are off, and sha256 runs
  scalar.
* **Protocol.** As for m93, plus the following. The full text is in `round-sa-m104-20261015/records/round/protocol-revision.txt`.
  * **Amendment 3:** an image identical to one already timed may be timed again only where its multiplier is forced. This
    applies to aha-mont64, which is held at m = 1 by the loader ceiling.
  * The screen is 0.85 s, and R_w is calibrated on m43, m87 and m93.
  * **Amendment 4:** a workload at its maximum feasible m is accepted at ≥ 0.6 s. This applies to matmult-int: projection
    0.78 s, and its m93 interval at m = 8 was 0.777 s.
* **Result.** **Kotoba / C = 0.8213**, against the historical m93 0.7999 and round114's 2.688. 19/19 Kotoba and
  19/19 C were accepted, all on the first attempt and all exact. The report labels this an exploratory translated-port
  result and sets `officialUnmodifiedCScore` to `false`. Verifier: `PASS_INDEPENDENT_SA_M104_RAW_CUSTODY_MULTIPLIER_FORMULA_V1`.
* **Noise check (Amendment 3).** aha-mont64 had the same image and n as in m93: 2.039 s against
  1.953 s (×1.044). This cycle's C elapsed GM was ×1.044 of
  m93's, so the host ran about 4 % slower in both arms.
* **crc32** has the same image as m93, but was timed at m = 2, a new n.

Verify this round with the same commands, adding `--round rounds/sa-m104-20261015.json`:

```
python3 bench/embench/reproduce-20261015/a_offline.py --round rounds/sa-m104-20261015.json
python3 bench/embench/reproduce-20261015/b_build.py   --round rounds/sa-m104-20261015.json --out /tmp/sa-b
python3 bench/embench/reproduce-20261015/c_exactness.py --round rounds/sa-m104-20261015.json --out /tmp/sa-c
python3 bench/embench/reproduce-20261015/c_reference.py --round rounds/sa-m104-20261015.json --out /tmp/sa-cref
python3 bench/embench/reproduce-20261015/d_timing.py  --round rounds/sa-m104-20261015.json --upstream /tmp/embench-iot --out /tmp/sa-d
```

| workload | m_w | ratio (4/m_w)·K/C | m93 ratio | change |
|---|---|---|---|---|
| aha-mont64 | 1 | 0.8688 | 0.9036 (m1) | 0.961 |
| crc32 | 2 | 0.6766 | 0.7084 (m1) | 0.955 |
| depthconv | 16 | 0.2660 | 0.2645 (m16) | 1.006 |
| edn | 4 | 0.9328 | 0.9503 (m2) | 0.982 |
| huffbench | 2 | 1.1586 | 0.6661 (m4) | 1.739 |
| matmult-int | 8 | 0.3093 | 0.3219 (m8) | 0.961 |
| md5sum | 2 | 0.5756 | 1.0322 (m2) | 0.558 |
| nettle-aes | 2 | 0.9080 | 0.7804 (m2) | 1.164 |
| nettle-sha256 | 2 | 1.0088 | 0.4158 (m2) | 2.426 |
| nsichneu | 4 | 0.3995 | 0.4096 (m4) | 0.975 |
| picojpeg | 2 | 1.4065 | 1.6002 (m2) | 0.879 |
| qrduino | 1 | 1.2088 | 0.5073 (m2) | 2.383 |
| sglib-combined | 1 | 1.1563 | 1.6124 (m1) | 0.717 |
| slre | 1 | 1.1689 | 1.8806 (m1) | 0.622 |
| statemate | 1 | 1.4356 | 1.3549 (m1) | 1.060 |
| tarfind | 2 | 0.7177 | 0.6575 (m2) | 1.092 |
| ud | 4 | 0.7559 | 0.7333 (m4) | 1.031 |
| wikisort | 8 | 0.7935 | 0.9646 (m8) | 0.823 |
| xgboost | 1 | 1.5184 | 1.9575 (m1) | 0.776 |

## 9. Second Apple M4 Mac mini cycle (16 October 2026)

The follow-up record at `round-sa-m104-20261015/records/m4-macmini-attempt-20261016-r1/` is a fresh full-19 run of the same M104 round on a separate M4 Mac mini (`Mac16,10`, 16 GB, macOS 26.3.1). It used the unchanged timing script and pinned upstream commit `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`; the C arm was rebuilt with Apple clang 21.0.0. All 19 workloads in each arm passed the protocol, including raw and estimated-background CPU idle gates. The GM is **0.7877703355587422**. `verify-record.py` independently checks all raw rows, exact Kotoba outputs, gate receipts, ratios, and the full-19 GM. This remains a translated-port comparison, not an official Embench result or a SPEC score. It is recorded separately from the original 0.8213 M4 cycle because host/compiler-specific runs should not be pooled.
