# The big frontend's Kotoba-route passes, natively through the seed backend (H-F1 / H-M3, agent FRONT, 2026-10-03)

Question (H-F1 with the new tool): now that `seed compile-kir` compiles 3,620 of 3,621 big-guest function slices, do the
frontend passes themselves (`infer`, `analyze`, `record_projection`, `row`, `state_ability`, `desugar`; kotoba-sema
`src/kotoba/compiler/frontend/*.cljk`, branch agent/fs-app-data-bytes) compile to native code and agree with the host case by
case, and what does each pass cost in the loader's arenas (H-M3)?

Labels: **M** measured here; **E** estimate. Host: M1 Max 32 GB, load average 40-90 during every run (recorded per step);
timings are indications, never results. Equality verdicts do not depend on load.

## 0. Verdicts

| hypothesis | verdict | numbers |
|---|---|---|
| H-F1 (the passes compile natively and agree with the host) | **confirmed for infer, state_ability, row, record_projection (and desugar via KIR5); analyze compiles only with a larger seed M** | infer 3,468/3,468 host cases agree (3,409 OK + 59 same refusal), ana 2,307/2,307 OK, e2e (whole `an/analyze`) 233/263 programs give the host's HIR or refusal (section 4) |
| H-M3 on infer | **confirmed** | 200-case processes peak at 0.61 M vectors / 1.6 M pairs / 39 MB heap with hash-consing; even all 3,468 cases in ONE process fit with it (3.37 M vectors = 80%, 10.3 M pairs = 15%); without it one process traps on the vector table |
| H-M3 on analyze | **ceiling (refuted beyond ~5 KB of source per process)** | one program per process: up to 1.84 M vectors (44% of 4 Mi) for a 1,307-byte source; 865 vectors and 49 KB of heap per source byte (aggregate), fit vectors ~ 487 * bytes^1.04, so the 4 Mi vector table holds about 5 KB of source per `analyze` process; a 100 KB module would need ~7x10^7 vectors and ~2.4 GB of heap (E). Process-per-pass cannot split below one module: needs freeing inside a pass (arena scopes per definition) or flat Forms (H-M4) |

Speed (indication, both loaded): the earlier infer differential ran on the JVM KIR interpreter at 1,277 cases in 2,440 s per
process (0.52 case/s, /private/tmp/ie-diff/interp-pt0.log); natively 3,468 cases take 0.5-0.8 s wall (4,300-7,000 cases/s),
about **10^4 x**. The linked e2e took ~100 s per program per JVM process (docs/selfhost-frontend-remainder-20261002.md: 263
programs ~2.5 h at 3 processes); natively 263 programs, one process each, take 5 s wall (~**5x10^3 x**).

## 1. Route (why not stage-0 native)

- The stable stage-0 (build/native-image/amu-native, Oct 2 19:44) carries ADR 0363 (an imported aborting function passes its
  abort on). The frontend's Kotoba code still unwraps imports as `[:result T E]` (expand.cljk `imp-validate-value-type!` and
  two more), so `check` refuses expand, desugar, record_projection, row, state_ability, namespace_defs, validate, infer and
  analyze ("expression type mismatch: expected [:result :i64 [:ref :fe/err]], got i64", expand.cljk line 149, M). Rewriting the
  three wrappers moves the wall to "call to aborting function `kotoba_import__550` in a function that neither catches it nor
  aborts with the same error type" (record_projection) -- the port to ADR 0363 is open work in kotoba-sema, not done here.
- The pre-0363 image (amu-native.prev-0024) accepts the infer guest's frontend (91 s) and then refuses at the aarch64 target
  admission ("typed values currently require ... the qualified native one-word ... slice"), before any KIR is written.
- So the KIR comes from the JVM-built classes of that lineage (build/native-image/work, BOOTSTRAP-REFERENCE):
  `scripts/selfhost-wall/kir-dump.clj` prints `(ir/native-program (ir/lower (sema/analyze linked)))`, the value a kexe's
  `:program` would hold. `slice.py slice .. main` keeps main's call closure; `seed compile-kir` (R6A seed 36433468) compiles
  it under the C loader only; the guest runs under tools/kexe_loader.c. Host answers come from the nbb host recorders.

| guest | passes | KIR B (fns) | main closure B / fns / tokens | seed compile | code B |
|---|---|---|---|---|---|
| ie (ie-gen.py, infer.cljk) | check-value-types!, elaborate-named-abilities, infer-loop-helper-results, check-loop-recur-argument-types!, resolve-loop-helper-param-types, infer-closure-refinements | 1,388,747 (2,571) | 425,633 / 718 / 80,069 | ok, 0.58 s | 421,239 |
| ana (guests/ana.cljk) | state_ability, row, record_projection | 1,718,359 (3,079) | 649,925 / 1,047 / 122,705 | ok, 0.20 s | 569,775 |
| e2e (guests/e2e.cljk) | the whole linked frontend, `an/analyze` | 2,674,794 (4,610) | 2,294,914 / 3,600 / 435,502 | R6A: E101 TOK full; private M (section 4): ok, 0.65 s | 2,326,201 |
| desugar | ds_pass (KIR5) | | | ok | EQUAL to stage-0 native at scale 1 and 8 (docs/selfhost-seed-merge-20261003.md) |

KIR dump times on the JVM: 119 s (ie), 157 s (ana), 328 s (e2e), 1.35-1.37 GB RSS.

## 2. infer (M)

Host cases regenerated from kotoba-sema HEAD + bd40e37 (ie-host.cljs: 2,126 test programs, 3,468 distinct pass calls):

| op | OK | OKERR (same refusal) |
|---|---:|---:|
| clr check-loop-recur-argument-types! | 649 | |
| cvt check-value-types! | 266 | 36 |
| ela elaborate-named-abilities | 598 | 23 |
| icr infer-closure-refinements | 598 | |
| lhr infer-loop-helper-results | 649 | |
| rlh resolve-loop-helper-param-types | 649 | |

0 DIFF, 0 TRAP. The 3,833 cases of 2026-10-02 (cases-all.txt) give 3,761 OK + 72 OKERR. Answers are byte-identical with
`KEXE_HASHCONS=16` on and off.

Arena marks per loader process (`KEXE_ARENA_USE=1`; limits 64 Mi pairs, 4 Mi vectors):

| cases per process | hash-consing | processes | max pairs | max vectors | max heap MB |
|---:|---|---:|---:|---:|---:|
| 200 | off | 18 | 3.01 M | 0.91 M | 66 |
| 200 | on | 18 | 1.63 M | 0.61 M | 39 |
| 1,600 | on | 3 | 4.85 M | 1.66 M | 117 |
| 3,468 | on | **1** | 10.31 M | 3.37 M (80%) | 248 |
| 3,468 | off | traps on the vector table at the first process; split 3 ways: 2.71 M vectors | | | |

## 3. state_ability, row, record_projection (M)

ana-record.cljs over the same tests + ds-corpus: 2,307 cases, **2,307 OK** (pred 1,177, tlit 300, spec 153, rowspec 143,
tl 136, rowgen 136, rps 132, thread 130). 200 per process: max 3.96 M pairs, 0.84 M vectors, 81 MB. All in one process traps
even with hash-consing (split 3 ways: 2.49 M vectors).

## 4. analyze (whole linked frontend) (M)

compile-kir needs 435,502 KIR tokens; R6A's M (8 Mi words) holds 131,072 (E101 region 1). A private copy of the R6A sources
(build/front/seedx, not committed) with M = 16,777,216 words (TOK 524,288, NODE 458,752, SIR 458,752, CODE 1 Mi, OUT 3 Mi,
FN 16,384, LABEL 262,144, LIT 32,768, LITB 512 Ki) is its own fixed point and compiles ana to the same container bytes as
36433468; it compiles e2e (0.65 s, 2.33 MB). Its first build answered garbage on e2e: 30-lower keeps a loop's node in 17 bits
(lw-kn), so loop nodes >= 131,072 were truncated (latent at R6A's NODE-CAP 131,072; filed in seed/CONTRACT-REQUESTS.md with
the planned NODE growth). With lw-kn widened (fixed point 183382cc, 566,144 B) and the one `decimal-f64-parse` (reader twin
float literals, no seed lowering) replaced by `none`:

| outcome over the 263 recorded programs (e2e-record.cljs) | programs |
|---|---:|
| same HIR / same refusal as host `kotoba.sema/analyze` | **233** |
| DIFF, refusal order or unported (`fold-def-value!` computed constants, entryless-library export check order, slice region provenance) | 7 |
| DIFF, HIR | 6 |
| TRAP SIGILL (16 use the slice carrier, 1 kernel-load-u8) | 17 |

The JVM interpreter run of 2026-10-02 found the same classes on its 88-program sample (79/88 same, 7 slice traps, 2 DIFF).
JVM check of the 30 non-OK programs on this corpus: see section 6.

Per program, one process each (246 non-trapping): max 1.84 M vectors (44%) and 3.24 M pairs without hash-consing, 1.57 M /
1.55 M with it; max heap 93 MB; aggregate 865 vectors, 1,856 pairs and 48,915 heap bytes per source byte; the largest
sources (1,307 / 956 / 927 / 900 B) need 1.84 / 0.89 / 0.90 / 1.34 M vectors. These are test programs (median 67 B); the
frontend's own modules are 30-440 KB.

## 5. Reproduce

```
scripts/selfhost-wall/front-native.sh build/front-x ie        # ana; e2e needs FRONT_SEED=<seed with the larger M>
```

`native-batch.py` runs any text->text native guest one loader process per batch with arena marks; `kir-dump.clj` writes the
native KIR of a project-route module without the native admission.

## 6. Open risks

- The KIR is from the pre-ADR-0363 JVM lineage; the frontend sources do not check on the current stage-0 until the ADR 0363
  port (section 1). A current-stage-0 KIR may differ.
- e2e ran on a private seed (larger M + the lw-kn fix) and with float literal parsing removed; neither is a committed rung.
- Equality is guest-vs-host per case (the guests' own `form/eq`), not seed-vs-stage-0 native (stage-0 refuses these guests).
- The analyze memory figures come from small test programs; the per-byte fit is extrapolated (E) to compiler-sized modules.
