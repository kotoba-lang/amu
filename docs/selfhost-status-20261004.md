# Selfhost status, one page (2026-10-04, agent HOUSE5)

Tree: `agent/dual-runtime-port` at `47221cd4d` (tag `seed-r6d`). Everything below is measured unless marked **E**
(estimate). Stage-0 is the BOOTSTRAP-REFERENCE (JVM-built native image `build/native-image/amu-native`, sha256 `d2cb84f6`);
a "seed" is selfhost-built (a seed compiled by a seed). The host is shared and loaded: **no timing on this page is a result**
(load labels in section 3); equality, fixed points, counts and byte sizes do not depend on load.

## 1. What 100% means (docs/selfhost-priority.md rules 8-11)

The `amu` binary, built by `amu` itself (no GraalVM, no JVM, no node, no nbb at build time or run time), runs the full
`check`, `refactor` and `compile` on its own sources, shown by `scripts/selfhost-wall/no-host-processes.sh -- <command>`
(an execve trace; a missing tracer is a failure). Embench is then measured on that compiler on a quiet host with the
binary hash recorded. File counts, `amu check` OK counts and GraalVM binaries do not count. Sub-goals that have
their own gates: R0 seed (a Kotoba compiler that compiles itself to a byte-identical fixed point and the 19 Embench ports),
R6 convergence (the seed compiles the big compiler's own modules from source), then linking the seed backend and the
frontend into the amu image.

## 2. Done

### 2.1 Seed rungs (all gates PASS; `bootstrap.sh` reproduces every hash)

| rung | what it added | seed-1 = seed-2 (sha256 prefix) | bytes |
|---|---|---|---:|
| r0 | 41 heads, i64/bool/string/vector, 3 capability wires | fe2c20ae | 187,186 |
| r1 | sugar, enums, flat records | c0526b73 | 291,392 |
| r2 | performance (inline vector access, linear-scan alloc, folding) | e1b2ecd5 | 269,456 |
| r3 | options/results, try/abort, typed lists, maps, sets, strings | cbae36dc | 330,584 |
| r4 | fn, closures, multi-arity, map/filter/reduce | e9598b28 | 382,968 |
| r5a | modules and linking (the seed split into 14 namespaces is its own fixed point) | 62e5655b | 493,479 |
| r4b | values by reference, `:bytes`, capability calls | 568d6152 | 502,759 |
| r5b | effects: atom/swap!, perform/handle, capability policy | 04c11dbe | 552,688 |
| r6a | keyword hashes, cross-module values, linker arena | 36433468 | 566,144 |
| r6b | `:document` as a source library, hex, str/ex-info | 6cc3dd9b | 636,184 |
| r6c | refined parameters, f64 carrier, per-module differential | ecc9c136 | 647,632 |
| r6c-kir | `compile-kir` as a KIR backend (F1-F5 pass) | be8898af | 675,512 |
| **r6d** | link-wide keyword table, absence typing, `:option-i64`, correctly rounded `decimal-f64-parse` | **e3654a64** | **698,960** |

Records: `seed/rungs/*.record`; ladder with per-port compile ms: `docs/selfhost-seed-rungs-20261002.md` (regenerated this
wave, now with rows r6c-kir and r6d). Unity source 16,102 lines of Kotoba in 16 modules (`seed/MANIFEST`).

### 2.2 Gates re-run this wave (clean worktree `/private/tmp/wt-H5-clean` at `47221cd4d`, load 32-53 at the gate rows)

- `gates.sh --rung r6c --with-unit --with-aux` (r6d adds no test directory of its own beyond the r6c set, as R6D recorded):
  **14/14 PASS**, 481.8 s: BUILD fixed point `e3654a64` (stage-0 not in the chain beyond the lineage route), ERR 137 codes,
  G1 19/19 under seed-0 and seed-1, G2 65/66 = stage-0 (1 refused by the front end, 0 different), G3 292 programs (232 refused
  with golden text, 60 accepted, 0 broken), G5 no program started by the seed, GR, XTRA, KIR 19/19, LEXREAD 74 dumps
  byte-identical, LW 65/66, A64GEN 756/756, UNIT 12/12.
- `bootstrap.sh` (same worktree): **OK in 22.7 s wall, no stage-0**: r0 .. r6d each reproduce `seed1_sha256` from the
  committed r0 seed and git; head seed-A == seed-B == seed-C `e3654a64f780d518` (698,960 B). Output of the run:
  every line `bootstrap: <rung> FIXED POINT == record <sha>`.

### 2.3 Embench on seeds, with load labels (scripts/seed/embench-rungs.sh, runner unchanged, 19 ports, check/compile/run x5)

**Verdict LOADED, both runs.** The script polled the 1-minute load every 10 min for 3 h (19 samples 19:42-22:42): minimum
**9.68**, median 18.3, maximum 73.6; never below the threshold 8. Then two LOADED runs (load at start/end of each run in the
table). Raw: `docs/selfhost-seed-embench-loaded-20261004.md` (and untracked `build/h5/embench*/`) (RESULT.txt, table.tsv, seed-provenance.json: `selfhost_built true`,
`official_embench_score false`).

| compiler | correct | compile ms, sum of 19 | run ns, geomean ratio to stage-0 (cold single call) | code bytes, sum | load start/end |
|---|---|---:|---:|---:|---|
| stage-0 (bootstrap-reference) | 19/19 | 4,302 | 1 | 152,476 | 25.1 / 20.6 |
| seed r2 | 19/19 | 378 | 0.937 | 96,969 | 20.6 / 21.1 |
| seed r4 | 19/19 | 378 | 0.685 | 97,673 | 21.1 / 21.5 |
| seed r6c | 19/19 | 371 | 0.701 | 97,673 | 21.5 / 20.2 |
| stage-0 (second run) | 19/19 | 4,321 | 1 | 152,476 | 23.1 / 19.9 |
| seed r6c-kir | 19/19 | 376 | 0.699 | 97,801 | 19.9 / 19.7 |
| seed r6d | 19/19 | 393 | 0.718 | 97,801 | 19.7 / 19.4 |

Read: correctness and code size are results; the seed emits 36% fewer code bytes than stage-0 (97.8 KB vs 152.5 KB) on
the same ports. The ms columns are LOADED indications only (the ratio 11x compile is consistent with every earlier
record, but not a measurement; `docs/selfhost-seed-embench-loaded-20261003.md` is the earlier loaded record). A QUIET
number does not exist yet. Note: the first attempt failed at once because `SEED_BUILD` was outside the repo
(`bootstrap.sh` requires its work dir inside `SEED_RESOURCES_35`); fixed by using `build/h5`.

### 2.4 KIR backend verdict (docs/selfhost-seed-merge-20261003.md section 00)

`seed compile-kir <in> --output <out> [--metered]` passes the falsification test F1-F5 (seed `be8898af`, fixed point):
0 of 357 exports differ from stage-0, 307 of 315 programs accepted (8 documented refusals: 4 floats, 4 variant /
hetero-vector), metered fuel equal on 347 of 347 comparable exports, 75/75 merge runs equal. INT2 added the opt-in
`--backend seed` (ADR 0365, bootstrap-labelled, process/spawn, fallback to `machine_ir` on any refusal; default unchanged):
Embench 19/19 correct and 19/19 seed-emitted, verifier re-emission 19/19, `scripts/seed-backend/test.sh` 16/16 (INT2's record).
Open risk: the fuel model is checked on these 315 programs only.

### 2.5 Seed source route (R6): the seed compiles the big compiler's modules from source

- R6 scan: **43 of 126 modules** compile from source (R6B 33, R6C 41, R6D 43; 44 before INT2's provenance edit).
- Per-module differential `r6-diff.sh` (R6D record): **984/984 cases agree** (36 modules AGREE, 3 stage-0-refused, 4 without cases).
  R6C had 960/972 with 3 differing modules; R6D fixed the per-module keyword text table and absence typing.
- Not yet from source: 12 modules refused, 73 blocked behind a refused require; 65 of those 73 sit behind
  `kotoba.lang.text`, which stage-0 refuses as well (R6C report).

### 2.6 Frontend ledger and native frontend

- Ledger (`ledger.sh`, minimal reach set, WALL_CP `/private/tmp/wall-cp-16.txt`): **126 modules, 10,163 definitions, REAL 3,209
  (31.6%)**, unverified-arm 3,671, unverified-plain 1,744, nil 1,531, refusal 2, stub 6; REAL host lines 21,185 of 136,207
  (15.6%). `covered-by-differential` shows 0 because no `LEDGER_DIFF` table was supplied, so it is not a finding. (Earlier
  page: 3,209 of 10,219 = 31.4%; the reach set changed by 56 definitions, the REAL count is the same.)
- ADR 0363 done: the current stage-0 accepts all 12 frontend modules. infer/state/row/record_projection are natively
  differential-equal to the host (3,468 infer cases, 2,307 others). `an/analyze` compiles natively only with a larger seed memory.
- COMPOSE `seed/amu-front` (native `check` built from the frontend guests, no host process at run time, PASS by noproc):
  **382 of 391** corpus programs have the same verdict and report as stage-0 `amu check` (313 of the 315 compilable ones);
  largest input that fits 248,134 B (seed prefix 00-ns..20-names, 5.3 s, 1.71 GB); the next prefix (515,715 B) hits the 64 Mi
  pair arena.

### 2.7 Memory plan verdicts (docs/selfhost-memory-plan-20261002.md, MEM2, pass-driver)

| idea | verdict |
|---|---|
| 1 hash-consing | confirmed, on by default in the hardened form: desugar 616 -> 148 B per source byte, output byte-identical on 720 cases, +32% CPU |
| 2 flat Forms | refuted as the next step: the program's Forms are 2.7% of handles and 21% of pairs; 62% / 79% are frontend constant tables re-built per call |
| 3 persistent records | partly: `record-assoc` prefix sharing came with hash-consing; hot-fields-first estimated 2-6x fewer pairs per env update (**E**, not built) |
| 4 definition CIDs | not adopted: 99.2% of definitions unchanged between commits, but the CID is computed after infer, so it cannot skip the frontend without a source-level pre-key (**E**) |
| 5 process per pass | confirmed for desugar-class passes and infer; analyze ceiling moved from ~5 KB to ~217 KB of source per process (ADR 0364, vector table 64 Mi); next wall the 64 Mi pair arena (< 291 KB) |

### 2.8 Boundary (`bootstrap-boundary.sh`, product path on nbb/node/JVM)

Union of PRODUCT src files: **58** (snapshot 2026-10-01: 56). Growth of 2 is rule-10 relevant: nbb entry files 15 -> 17
(`check_cli.cljk` and `aarch64_packaged_cli.cljk`, added by 15d9fcccf when the reach set was cut; both still without a
`:kotoba` arm). Others unchanged: 4 launchers (`bin/amu` = node + nbb), 48 modules with `#?(:kotoba nil)` or no :kotoba arm,
13 src files with unguarded host tokens (36 tokens), 56 of 109 src files have a :kotoba arm. Target: 0.

## 3. Load record

Start of this wave 13.7 (1-min), rising to 74 around 20:20, then mostly 10-25 until 22:20 (one sample of 55); Embench runs at 19.4-25.1; clean
gates 32-53 at the gate rows. Quiet (< 8) was not reached in 3 h. A quiet-host Embench needs a reserved window (decision 5).

## 4. Open, ranked (by what it unblocks)

1. `kotoba.lang.text` is refused by stage-0 and the seed: 65 of the 83 modules not yet compiled from source depend on it (R6 scan).
2. The `analyze` pair arena (64 Mi, < 291 KB of source per process): re-materialised frontend constant tables (filed to kotoba-sema;
   **E** 3-5x) or a larger arena; without it `amu-front` cannot check the compiler's largest modules (the seed's own `21-check` prefix is 515 KB).
3. Link the seed backend and the frontend into the amu image as Kotoba modules and call them in-process (today: process/spawn,
   opt-in `--backend seed`); then flip the default with the fallback list kept.
4. Seed gaps on the KIR route: floats (4 programs; `decimal-f64-parse` landed in R6D, f64 arithmetic not), variant and heterogeneous
   vectors (4), `:document` under `--metered`.
5. `refactor` and the `kotoba ...` commands native: 17 nbb entry files, 4 launchers.
6. Rule 11 trace over the full commands on the self-built binary (`no-host-processes.sh`); today it passes only for the seed
   (G5) and `amu-front check` (noproc).
7. A QUIET Embench of the head seed; the ledger's REAL share (31.6%) and its differential coverage table.

## 5. ETA (all **E**, low confidence; assumptions in the last column)

| milestone | range | assumptions |
|---|---|---|
| R6 convergence: all 126 modules compile from source and agree per module | 3-6 weeks | `kotoba.lang.text` unblocked in the first week (it gates 65 modules); no new type family beyond floats; one R6 owner per two modules; rate seen so far 33 -> 41 -> 43 per wave but the remainder is one cluster, not linear |
| seed backend linked in the amu image, selector default flipped | 1-2 weeks after R6 | the 14-namespace split (r5a) is the link; fuel model holds on programs outside the 315 |
| native `check` on the compiler's own sources (rule 11, one of three commands) | 6-10 weeks | analyze pair arena fixed (item 2) so 515 KB modules fit; amu-front stays at 98% verdict equality |
| full rule 11 (`check`, `refactor`, `compile` natively, no host process) | 3-5 months | refactor port is the unmeasured part; bin/amu and 17 nbb entries replaced; two or more agents full time |
| QUIET selfhost Embench | 1 day once a quiet window exists | not dependent on engineering |

## 6. The five decisions that matter now

1. **Fix `kotoba.lang.text` first** (kotoba-lang owner): it gates 65 modules, and both stage-0 and the seed refuse it today.
2. **Choose the analyze memory route**: remove recomputed constant tables in kotoba-sema (cheap, E 3-5x) before raising the 64 Mi arenas again.
3. **Make the seed the default backend** once linked in-process; keep `machine_ir` as the named fallback for floats, variants, metered documents. Until then the flag stays opt-in and bootstrap-labelled.
4. **Retire or port the nbb entries**: 17 files, +2 since the snapshot; decide per entry (retire `*_packaged_cli`, port `check_cli`) and gate rule 10 on the count so it cannot grow again.
5. **Reserve a quiet window** (or a second machine) of about 30 minutes for the QUIET Embench; polling for 3 h found a minimum load of 9.68.

## 7. Links and reproduction

- Design `docs/selfhost-seed-design-20261002.md`; rules `docs/selfhost-priority.md`; boundary `docs/selfhost-bootstrap-boundary-20261001.md`;
  rung ladder `docs/selfhost-seed-rungs-20261002.md`; KIR verdict `docs/selfhost-seed-merge-20261003.md`; memory
  `docs/selfhost-memory-plan-20261002.md`, `docs/selfhost-analyze-memory-20261003.md`, `docs/selfhost-pass-driver-20261003.md`;
  frontend `docs/selfhost-front-native-20261003.md`, `docs/selfhost-frontend-adr0363-20261003.md`, `seed/amu-front/README.md`;
  tournament `docs/selfhost-coscientist.md`; open contract items `seed/CONTRACT-REQUESTS.md`; earlier loaded Embench `docs/selfhost-seed-embench-loaded-20261003.md`.
- Reproduce: `zsh scripts/seed/bootstrap.sh` (chain, no stage-0); `zsh scripts/seed/gates.sh --rung r6c --with-unit --with-aux`;
  `zsh scripts/seed/embench-rungs.sh --rungs "r2 r4 r6c" --out <dir inside the repo>` (polls up to 3 h, else LOADED);
  `scripts/selfhost-wall/bootstrap-boundary.sh`; `WALL_CP=/private/tmp/wall-cp-16.txt WALL_K=/private/tmp/wt-K-kotoba-lang scripts/selfhost-wall/ledger.sh`.
