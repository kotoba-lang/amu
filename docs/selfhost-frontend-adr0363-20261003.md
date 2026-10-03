# The kotoba-sema frontend follows ADR 0363 (2026-10-03, agent ADR63)

Status: measured. kotoba-sema `agent/fs-app-data-bytes` ecacc4f, f8635bf, 15e45a3 (on bd40e37). Checker: the stable
native image `build/native-image/amu-native` (Oct 2 19:44, BOOTSTRAP-REFERENCE, carries ADR 0363) through
`scripts/selfhost-wall/check-native.sh`, `WALL_CP=/private/tmp/wall-cp-16.txt`, `WALL_K=/private/tmp/wt-K-kotoba-lang`,
`CHECK_NATIVE_NO_REMAP=1`. Host load 27-37 during every run (timings are indications only).

## Result

| module (dependency order) | before | after |
|---|---|---|
| base, kernel_region, closure_types | OK | OK |
| expand, namespace_defs, validate | refused: expected [:result :i64 [:ref :fe/err]], got i64 (expand.cljk:149) | OK |
| infer | refused (same, via expand); once expand passed: "linked project exports exceed limit" | OK (71 s) |
| record_projection, state_ability | refused (same); then "call to aborting function kotoba_import__N in a function that neither catches it nor aborts with the same error type" | OK |
| row, desugar | refused (same) | OK (desugar 124 s) |
| analyze | refused (same); then the same aborting-call refusal | OK (245 s) |

**12 of 12 frontend modules are admitted by the current stage-0.** No refusal remains in `src/kotoba/compiler/frontend/`.

## What changed (Kotoba arms only)

1. expand: the three `imp-*` wrappers (match an imported `[:result T E]`, re-throw) are deleted; the calls name the
   imported function (ADR 0363: an imported aborting function passes its abort on).
2. record_projection (7), state_ability (1), analyze (38): the `*-caught` + `*-unwrap` pairs become the plain call
   (or a `let` over it); the one real fallback (`an-typed-param-parts-or-nil`) is `try` / `catch [:ref :fe/err]`.
   The record helpers left unused (`rp-ir`, `rp-unwrap`, `sa-ir`, `sa-unwrap`, `an-unwrap`, `an-st-unwrap`,
   `an-st-err`) are removed.
3. Every module except desugar (which had one) gets `#?(:kotoba {:kotoba/export [...]})`: the names other modules'
   Kotoba arms, `kotoba.sema` and the amu guests reference (226 clauses for the 11 maps). Without it every public
   defn is an export and the linked frontend passes `max-project-exports` (1024). Host reading: unchanged.

## Host behaviour

- 7-namespace sema subset (`/private/tmp/sema-tests.cljk`, incl. frontend-tables-test), before (HEAD worktree) and
  after, same cwd: 82 tests, 15 failures, 13 errors, same set, output identical modulo paths and line numbers.
- Full suite (`run-tests.cljk`, kbb sci): 622 tests, 76 failures, 24 errors before and after, same failing set
  (the task's 77/25 baseline is from an older test tree). Assertion count 2258 vs 2260: frontend-tables-test reads
  `$(cwd)/../kotoba-sema/resources/...`, which exists only from the real checkout; re-run per namespace, that is the
  only difference.

## Ledger (`scripts/selfhost-wall/ledger.sh`, minimal reach set, 126 modules)

The scan for non-frontend modules is the Oct 2 `wall-scan-native4.tsv` in both runs; only the frontend rows differ.

| | before | after |
|---|---|---|
| TOTAL REAL | 3,620 of 10,219 defs (35.4%) | 5,952 of 10,163 (58.6%) |
| REAL host lines | 23,983 of 136,566 (17.6%) | 45,750 of 136,207 (33.6%) |
| frontend REAL | 411 (base 219, kernel_region 88, closure_types 104) | 2,743 (analyze 414, desugar 591, infer 515, expand 185, record_projection 158, state_ability 157, row 149, namespace_defs 124, validate 39, + the three above) |

REAL here means admitted by the checker; agreement with the host is not re-measured by this change (the FRONT
differentials ran on the pre-0363 KIR). Open: ie-gen.py now produces two export maps (CONTRACT-REQUESTS).
