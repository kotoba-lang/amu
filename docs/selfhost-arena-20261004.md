# Native analyze memory: frontend tables built once per run, re-measure, large-M seed profile (agent ARENA, 2026-10-04)

Question (MEM2's request, CONTRACT-REQUESTS 2026-10-03): the native `analyze` (amu-front, the kotoba-sema frontend
compiled by the seed's `compile-kir`) stopped at ~290 KB of source on the 64 Mi pair arena, and MEM2's census put 62% of
vector handles and 79% of pairs on frontend constant tables rebuilt per call. Remove the recomputation, re-measure the
largest input that fits, size the seed memory for building amu-front from a recorded profile, re-run the corpus.

Labels: **M** measured here, **E** estimate. Stage-0 = BOOTSTRAP-REFERENCE (`build/native-image/amu-native`, the oracle
of the corpus differential; the KIR comes from the JVM-built classes via `scripts/selfhost-wall/kir-dump.clj`, build
time only). Host load 27-70 during every run: wall times below are indications, never results. Handle and pair counts,
heap bytes, verdicts and hashes do not depend on load.

## 1. Result

| | before (COMPOSE, 2026-10-03) | after (this change) |
|---|---|---|
| corpus, 391 programs, same verdict + report as stage-0 `check` | 382 / 391 | **382 / 391, 0 verdict or report-line changes** (M) |
| seed prefix ..11-read (72.5 KB): vectors / pairs / heap | 12.89 M / 16.66 M / 562 MB | **0.91 M / 2.71 M / 63 MB** (14x / 6.1x / 9x fewer) (M) |
| seed prefix ..20-names (248 KB) | 38.3 M / 52.8 M / 1.71 GB | **3.28 M / 10.1 M / 228 MB** (M) |
| the whole seed unity (810 KB) | pair-arena trap (from 291 KB on) | **fits: 13.0 M / 31.4 M / 755 MB**, same verdict as stage-0 (M) |
| largest input analysed TO THE END (capability verdict) | 248,134 B | **1,037,509 B** (20-names x4, `front_scale.py`): 16.7 M vectors (25% of 64 Mi), 39.9 M pairs (59%), 963 MB; same verdict as stage-0 (M) |
| per source byte, full analysis | ~155 vectors / ~213 pairs / ~6.9 KB heap | **16 / 38 / 0.93 KB** (x4 input) (M) |
| where the pair arena would end | ~0.29 MB | **~1.7 MB** of source (E: 59.8 M pairs measured at 1.56 MB, 89%); stage-0 itself refuses a file above 1 MiB ("input exceeds byte limit"), so every file stage-0 admits fits one process now (M up to 1,037,509 B) |

## 2. What changed (kotoba-sema, branch `agent/arena-const-tables`, commit c2766ee on bd40e37)

bd40e37 is the frontend revision the KIR route accepts (the ADR-0363 port 15e45a3 is not accepted by the pre-ADR-0363
JVM classes, seed/amu-front/README.md section 1). The patch applies to 15e45a3 except one conflict in analyze.cljk
(the an-c-validate-expr block) **M** (`git apply --3way`); porting it is open.

Found with a per-function census (`scripts/seed/front_census.py`: a 12-byte exported marker before each of the 3,605
KIR functions, the large-M profile's EXP 8,192 holds them; a diagnostic loader copy with 40 recorded frames instead of 8;
attribution through the frames to the first function outside the reader). Shares of the native analyze's handles, seed
prefix ..02-io, after step 1: `form/edn-form` under table functions 68% of pairs / 54% of vectors; of that,
`reserved-function-names` (a 45-table union rebuilt per definition) 59% of all pairs, 46% of vectors **M**. After step 2,
prefix ..11-read: affine's linear-returning fixpoint 47% of pairs, minted keyword keys (`fget`) ~20% **M**.

| step | change | ..11-read vectors / pairs (M) |
|---|---|---|
| 0 | bd40e37 (COMPOSE's amu-front) | 12.89 M / 16.66 M |
| 1 | validate: the 24 operation tables, operator index and head-set indexes folded ONCE per analyze run (`make-ctx` / `check-form-in` / `validate-ctx` / `validate-expr-in`; `check-form` unchanged) | 4.14 M / 11.73 M |
| 2 | `scripts/gen-table-lookups.py`: allocation-free `NAME-has?` / `NAME-has-name?` for the 83 symbol tables (dispatch on byte length + first code point, then `string=?`; host: `(table-has? NAME k)`); `reserved-function-name?` without building the union; direct table-has? sites use them | 1.80 M / 6.15 M |
| 3 | affine: [name params body (do body)] prepared once for the linear-returning fixpoint (was per pair x function); literal head sets compared by name, not parsed; `fget` (affine, base) and `fhas?` read keyword keys without minting a key Form | 0.91 M / 2.71 M |

Every rewrite answers what the code it replaces answered (same equality: symbol name `string=?`, keyword `=`); the
corpus differential (391 programs, verdict + report line) is unchanged. Host (:default) code is unchanged except the
generated `NAME-has?` defns; the host build was not run here (open).

## 3. Seed memory: the large-M profile (`seed/profiles/`, record `large-m-r6d.record`)

COMPOSE built amu-front with a private 16 Mi-word seed of the r6c-kir lineage. Now a recorded option: `scripts/seed/
large-m.sh --rung r6d --check` archives rung r6d's unity commit, rewrites `seed/MEMORY-MAP` with `scripts/seed/large_m.py`
(M 16 Mi words = the loader's per-vector boundary; TOK 655,360, NODE/SIR 458,752, LABEL 262,144, CODE 1 Mi, OUT 3 Mi, LITB
512 Ki, EXP 8,192; heap 1,933,056 words), builds it with the recorded r6d seed and checks: fixed point seed-1 == seed-2 =
**9e7895f1** (698,960 B); the large-M seed compiles r6d's own default-map unity to exactly **e3654a64** (the r6d seed:
a compiler's output does not depend on its own table sizes); NODE-CAP within 30-lower's 2^20 loop-node mask; reproduced
in a fresh directory **M**. It is not a rung (bootstrap.sh never builds from it); `AF_SEED=<its seed-1.bin>` builds
amu-front from it. TOK sizing: the table change grew main's closure from 436,697 to 453,816 KIR tokens (python count),
87% of the 524,288 FRONT used; 655,360 leaves 31% headroom, and the census build with 3,671 markers (~520k) fits **M**.
The same KIR compiled by the be8898af-lineage private seed and by 9e7895f1 gives identical handle and pair counts **M**.

## 4. Remaining gaps of the corpus (9 programs, all "stage-0 ok, native refuses"; unchanged)

| gap | programs | measured cause | owner |
|---|---|---|---|
| G1 float literals | 6 | the reader twin's `decimal-f64-parse`: the R6D seed provides it on the SOURCE route only (21-check prelude); `compile-kir` of 9e7895f1 refuses it, `E2101 unknown or unsupported form 'decimal-f64-parse'` (M, AF_F64=1 build), so build.sh still replaces it by none | 12-kirread (EXPORT): lower `decimal-f64-parse` on the KIR route (the prelude exists) |
| G2 `ucs2` literal | 2 | validate_expr's port answers `vx/unsupported` for the rodata literal family (not ported: `rodata-literal-content?`) | kotoba-sema frontend |
| G3 typed_map_kit | 1 | "if test is :i64": `(if (typed-map-contains ..) ..)` / `typed-map-equal` -- the Kotoba-route infer treats these as i64-answer predicates where the host admits them as tests | kotoba-sema infer |

New, found by the scale inputs: amu-front does not apply stage-0's 1 MiB per-file input limit (a 1.56 MB file: stage-0
"input exceeds byte limit", amu-front analyses it, REFUSE-DIFF) -- seed/amu-front/check.cljk should refuse the same way.

## 5. Reproduce

```
scripts/seed/large-m.sh --check                                   # the profile seed, checked against the record
AF_SEED=build/seed-large-m-r6d/b/seed-1.bin AF_KSEMA_REV=c2766ee seed/amu-front/build.sh <work>
AF_SKIP_S0=1 seed/amu-front/corpus.sh <work>/corpus <work>/amu-front
python3 scripts/seed/front_scale.py build/compose/ladder/in/pfx07-20-names.kotoba 4 x4.kotoba   # the 1 MB ladder input
python3 scripts/seed/front_census.py mark|report ...               # census attribution (needs EXP >= functions + 1)
```
Results: seed/amu-front/results/arena-{corpus,ladder,scale}-20261004.tsv, amu-front-arena-20261004.info.

## 6. Open risks

- The frontend change is on the bd40e37 lineage; kotoba-sema HEAD (15e45a3, ADR 0363) needs the same change (one conflict).
- Host-side tests of kotoba-sema were not run; the generated host `NAME-has?` defns are new code there.
- Ladder inputs from ..21-check on refuse at `parameter-use-conflict` (as stage-0 does), i.e. before the end of
  analysis; the full-analysis numbers above 248 KB come from the replicated 20-names inputs, not from real modules.
- The scale inputs are K renamed copies of one program: real modules may have other per-definition costs.
- No timing is a result (loaded host); per-byte rates are counts.
