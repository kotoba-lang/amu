# Selfhost co-scientist — tournament state

The research goal is the owner's sentence: *an amu binary built by amu itself runs
`check`, `compile` and `refactor` on its own sources with zero node, JVM and nbb
processes, and Embench is measured on that compiler* (docs/selfhost-priority.md
rules 8-11). Stubs, refusal twins and bootstrap-only readings do not count.

This file follows the loop of `docs/codegen-coscientist.md`. One iteration = one
hypothesis taken to a measured verdict. The fitness function is deterministic, never
judgment.

## Fitness (the only things that decide a verdict)

| gate | command | meaning |
|---|---|---|
| F1 rung gates | `scripts/seed/gates.sh --rung rN` | G1 19 Embench ports return 1, G2 corpus equals stage-0, G3 refusal texts, G4 fixed point (seed-N+1 == seed-N+2 bytes), G5 no host processes |
| F2 ledger | `scripts/selfhost-wall/ledger.sh` | definitions with a real Kotoba body that agrees with the host (REAL), not files OK |
| F3 differential | `ds-diff.sh`, `vx-diff.sh`, `tm-diff.sh`, `abort-diff.sh`, `kir-gate.sh` | the Kotoba route agrees with the host case by case |
| F4 boundary | `scripts/selfhost-wall/bootstrap-boundary.sh` | product-path dependencies on nbb/node/JVM (must reach 0) |
| F5 Embench | `bench/embench/run_native_qualification.py` with the packaged seed | correctness 19/19; compile ms, code bytes, execute medians on a recorded host |

"Files OK on the native checker" (scripts/selfhost-wall/check-native.sh) is a
bootstrap feedback signal, not a verdict.

## The loop

| stage | what it means here |
|---|---|
| **Generate** | hypotheses come from measured artifacts: refusal histograms (`wall-scan-*.tsv`), the ledger, memory high-water marks (`KEXE_ARENA_USE=1`), gate failures, git throughput. Not from intuition alone |
| **Reflect** | falsify cheaply first: a one-day spike, a hand-built fixture, a 1-file probe, a count over real data. A hypothesis that does not survive its spike gets no wave |
| **Rank** | expected progress on F1/F2/F5 × probability, grounded in the spike number; a blocker that gates other hypotheses outranks any single win |
| **Evolve** | a confirmed-direction hypothesis that is not yet sufficient is combined with the next mechanism, not discarded |
| **Meta-review** | after each wave: rerun the fitness gates on immutable snapshots, update this table, record the verdict ("not separated" is the absence of a result), and retire or promote hypotheses |

Terminal states: **reached** (F1-F5 all green on the rung that replaces the compiler),
or a **proven ceiling** written down with evidence (for example a memory bound no
representation reaches).

## Hypothesis population

| id | hypothesis | status | evidence |
|---|---|---|---|
| H-S1 | A small seed compiler compiled from itself reaches a real selfhost fixed point and an Embench measurement far sooner than porting the 136k-line host compiler | **confirmed — seed R0** | fixed point `fe2c20ae…`, 19/19 ports, compile 376 ms vs 4423 ms same-host stage-0 (docs/selfhost-seed-r0-report-20261002.md) |
| H-S2 | A rung ladder (R1 sugar+records, R2 perf, R3 values, R4 functions, R5 modules/effects, R6 Forms) keeps every step self-proving with a fixed point | **R1-R4 confirmed**, R5 designed (docs/selfhost-seed-r5-design-20261002.md) | tags seed-r1..r4; fixed points c0526b73, e1b2ecd5, cbae36dc, e9598b28 (382,968 B); R2: Embench run time geomean 0.96x of same-host stage-0, code 96,969 B vs 152,476 B; R4: xgboost 2,425 -> 27.5 ms per call after the UTF-8-literal rule |
| H-M1 | The seed backend can consume the big frontend's KIR text (`compile-kir`), bypassing the memory-hungry `machine_ir`/`mir` Form route | **leaf layer GO, replacement of machine_ir/aarch64 NO-GO for now** (docs/selfhost-seed-merge-20261003.md) | 299/315 programs compile via compile-kir (277/295 runnable equal to stage-0); 4 big-compiler pieces (posix-path, kstring+decimal, string.case, sha2) give identical output at scale 1/8/20, run time 0.93-1.43x, peak memory <= stage-0; but only 1,069/3,399 (31.4%) per-function slices of 10 big-compiler guests compile. Missing: `:document` 170 fns, records by ref 100, `:bytes` params 60, string-from-utf8 33, [:list [:ref R]] 29, cap calls 17. Verdict flips at >= 95% of functions compiling with EQUAL results on form_count, validate-expr, desugar |
| H-M2 | Loader-level hash-consing cuts the Form route's heap enough for per-pass processes | **confirmed; hardened (2026-10-03)** | desugar 616 -> 148 B/source byte, byte-identical output on 720 cases; collision-safe by exact compare; default now a 4-way 2^16-entry table: +32% CPU instead of +75%, +4% pairs (docs/selfhost-pass-driver-20261003.md) |
| H-M3 | Process-per-pass keeps each pass under the loader's pair limit | **confirmed for desugar-class passes, with H-M2; ceiling = vector table** | `scripts/selfhost-wall/pass-driver.sh`; 32x the real corpus (4.6 MB): per pass <= 0.48 GB heap, 14.6 M pairs (22% of 64 Mi), 3.4 M vectors (82% of 4 Mi); one process or no hash-consing traps on the vector table. `analyze`/`infer` not native yet, so unmeasured (docs/selfhost-pass-driver-20261003.md) |
| H-M4 | Flat Forms (struct of arrays) are needed | open — only if a pass measured natively needs them | 170 B/node today vs 40 B flat (estimate) |
| H-F1 | The big frontend's remaining Form ports (`infer`, `desugar`, `record_projection`, `analyze`) are on the critical path for R6 | open | ledger: REAL 3,209 of 10,219 defs (31.4%); many passes carry real bodies, differential 3,869 cases agree on `infer` |
| H-F2 | Mechanical rewrites via `amu refactor` are cheaper than hand ports | **confirmed for destructuring/reject!** | rules a-f, 1,000+ sites, outcomes identical |
| H-V1 | Distributed or remote CPU is worth its coordination cost | **refuted for now (owner decision)** | single-Mac loop; native checker 48 s -> 1 s removed the need |
| H-X1 | Compiled differential tests (native guests) replace interpreter-on-nbb runs | partly confirmed | `kotoba.string.case` 1.1M cases at 52,710/s; Form guests blocked by aggregate lists in the native backend (docs/selfhost-native-gaps-20261002.md) |
| H-N1 | nbb, node and JVM can leave the product path once the seed lineage reaches R5 | open | bootstrap-boundary report: 56 product-path files; S6 plan |

## Iteration log

- **0-15 (historical):** frontend ports, limits (ADR 0358-0360), tooling (wall harness, refactor, native checker); state lived in wave scripts and `docs/selfhost-core-rewrite-plan-20260930.md`.
- **16 — H-S1 (2026-10-02):** spike T1/T2/T3, then modules, then integration. Verdict: confirmed (seed R0, F1 G1-G5 green, F5 19/19).
- **17 — H-S2/H-M1 (2026-10-02):** R1 and `compile-kir` built; gates green. Verdict: R1 confirmed, H-M1 confirmed on the 19 ports.
- **18 — H-M2 (2026-10-03):** hash-consing spike in the loader. Verdict: confirmed.
- **19 — H-S2 (2026-10-02/03):** R2, R3 built and gated; KIR coverage 241 -> 299/315. Verdict: R2, R3 confirmed.
- **21 — H-S2/H-M1 (2026-10-03):** R4 functions (fixed point e9598b28), R5 design + oracle (77 cases), KIR merge test. Verdicts: R4 confirmed; H-M1 NO-GO for replacing machine_ir now, GO for the leaf layer.
- **20 — H-M3 (2026-10-03):** falsified at 8x and 32x on a real corpus, built `pass-driver.sh`, hardened the loader's hash-consing. Verdict: confirmed for desugar-class passes (with H-M2); next wall is `KEXE_VECTOR_MAX`, then the unmeasured `infer`/`analyze`.

## Next iterations (ranked, 2026-10-03)

1. **H-M1 flip conditions**: seed lowering for records by reference, `:bytes` params/results, [:list [:ref R]], `string-from-utf8`, capability calls, >5 parameters, then `:document` (these are R5/R6 features; each is measured by the per-function slice scan `seed/tests/kir/slice.py`).
2. **R5 implementation** (modules/linking + effects) per the design; gate = 20 conformance programs with oracle values.
3. **H-F1**: `infer`/`analyze` natively (next measured wall of H-M3 is KEXE_VECTOR_MAX).

## Superseded list (2026-10-03 morning)

1. **H-M3 + H-M2 on by default**: process-per-pass driver for the big frontend (falsify first: run `desugar` guest with hash-consing at 8x and read the arena marks).
2. **H-M1 coverage**: the share of the repo's programs that `compile-kir` handles; the number decides whether the seed backend replaces `machine_ir`.
3. **H-F1**: finish `infer` natively (the unknown flagged by the memory study) before more Form ports.
4. **H-N1**: native launcher for `amu` as soon as R5 gates are green.
