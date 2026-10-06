# Seed rung R6C: more R6 source-route features, and the per-module differential (2026-10-03)

Agent R6C. Continues R6B (`docs/selfhost-seed-r6b-report-20261003.md`): the seed compiles more of the 126-module reach set
from SOURCE (`scripts/seed/r6-scan.sh`), and, new in this rung, what it compiles is RUN against stage-0's build of the same
module (`scripts/seed/r6-diff.sh`, design 1.4 row R6). Host load was 30-150 during the work; no timing below is a result.

## Result

| measure | value |
|---|---|
| R6 scan | **@SCAN@** (R6B: 33). Data `seed/tests/r6c/scan/` |
| per-module differential | **@DIFF@** |
| feature cases | `seed/tests/r6c/check-r6c.sh` 10/10 (7 positives, each on the single-module AND the project route with byte-identical images; want = stage-0 d2cb84f6's own answer for all 7; 3 negatives) |
| gate cases | `gate-r6c.sh`: LOOPW (a program whose nested `loop`s are read at node 159,615 > 131,072 answers the generator's value), LIBSTUB (stage-0's answer; the R6B seed loops on it), R6B-X |
| bridge | @BRIDGE@ |
| fixed point / rung proof | @FIXED@ |
| gates (clean worktree) | @GATES@ |

## Features

- **Unannotated parameters** (kotoba.compiler.posix-path, host-integer, kotoba.bytes). The reference
  (`kotoba-sema infer.cljk infer-absent-parameter-types`) gives an unannotated parameter a provisional `:i64` and refines it to
  T when the checker's first refusal is "this bare parameter, expected T, got :i64". The seed does the same with its OWN
  refusal (no table of operand types): the synthetic type node is `KW-PINFER`, `ck-sym` notes a use of a provisional parameter
  in `M[MM-CK-LAST]` (every `ck-mark` clears it, so it names the parameter only when the bare parameter was the expression just
  compared), `ck-err` turns an E2104 into the refinement `f*2^28 + k*2^24 + T` in `M[MM-CK-REFINE]`, and the driver (90-drv
  single route, 60-proj per module) re-runs the module from the read with the refinements so far (at most 64, each new; they are
  applied right after the signatures, `ck-hints-apply`). If tests (`if`/`and`/`or`/`not`) do not refine, as in stage-0 ("if
  test is :i64 ..."). The reference takes the first function, in order, whose OWN body asks; the seed stops at its first
  refusal, so when a strict run fails without a refinement a PROBE run checks the provisional functions first and lets a call
  pass a non-i64 argument to a provisional parameter; a probe only contributes refinements, the verdict is always a strict run's
  (p07: a caller defined before its callee).
- **`(- x)`** = `(- 0 x)` (wrapping), stage-0's reading.
- **A typed catch around a body that cannot abort** (kotoba.compiler.schema `validate-table!`): admitted, as stage-0 does; an
  untyped catch there stays E2131 (the conformance negative).
- **vector-drop / vector-take / subvec / into** on `:vector-i64`: source-library group `vec` (copies; out of range traps).
- **A map or vector literal in the tail of a `:document` defn** (kexe-fs-forms `form-table`): `(document-map ..)` /
  `(document-vector ..)`, nested literals converted, scalars through `__r6-todoc`; the canonical text equals stage-0's (p05).
- **`:f64` as an opaque carrier** (cbor.core): its binary64 bits in an i64, `f64-to-bits` / `f64-from-bits` only. `=`, arithmetic,
  literals and `:f64` record fields are refused by name (stage-0 admits `=`/`+` on floats and refuses the record field natively:
  recorded narrowings, never a different answer).
- **60-proj fix** (R6B defect, found by the differential): the source library was appended AFTER the trailer, so an importer that
  also got a library group had library functions where 60-proj expects its import stubs (the last FN records) and the link
  patched them: the driver of kotoba.compiler.decimal-text looped. The library now precedes the trailer.

## The differential (`scripts/seed/r6-diff.sh`)

For every module the seed compiled in the scan, `r6_diff.py gen` writes a driver project: one arity-0 export per case, each
calling one export of the module (its interface line in the seed's object = the seed's checked signature) on fixed arguments
and folding the result into an i64 (bool 0/1, strings/bytes/vectors/documents by a byte hash, `[:option T]` by tag and value).
The seed compiles it through the project route (module and requires from source, linked), stage-0 compiles the same driver
(`--source-path --unpinned`), and every case runs on both images under the C loader with the same budgets and grant (wire 3).
A case agrees when both answer the same value or both trap. Exports with record, list, fn or keyword/symbol results and
aborting exports (stage-0 refuses an import abort on native code) are not called (counted as skipped).

@DIFFTABLE@

## Open (measured, ranked)

@OPEN@
