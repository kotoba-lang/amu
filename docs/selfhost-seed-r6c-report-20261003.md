# Seed rung R6C: more R6 source-route features, and the per-module differential (2026-10-03)

Agent R6C. Continues R6B (`docs/selfhost-seed-r6b-report-20261003.md`): the seed compiles more of the 126-module reach set
from SOURCE (`scripts/seed/r6-scan.sh`), and, new in this rung, what it compiles is RUN against stage-0's build of the same
module (`scripts/seed/r6-diff.sh`, design 1.4 row R6). Host load was 30-150 during the work; no timing below is a result.

## Result

| measure | value |
|---|---|
| R6 scan | **41 of 126 modules compile** (R6B: 33; +8: cbor.core, kotoba.bytes, kotoba.bytes.sha256, compiler.base64-text, host-integer, posix-path, provenance, schema). All 41 are in stage-0's check-native OK set (R6A table); 12 refused, 73 blocked by a refused require (65 of them behind kotoba.lang.text, which stage-0 refuses too). Compiler ecc9c136, load 43-66** (R6B: 33). Data `seed/tests/r6c/scan/` |
| per-module differential | **960 of 972 cases agree** (829 equal values, 131 both trap) over 38 modules with cases: 33 AGREE, 3 DIFF (12 cases, every one "seed traps, stage-0 answers", root cause the per-module keyword text table, below), 2 drivers stage-0 refuses natively (host-integer: the interfaces differ, below; string-search: "typed values currently require .. native one-word slice"), 3 modules with no callable export. 39 exports not called (aborting, keyword/symbol results, record params other than :form/r). Data `seed/tests/r6c/diff/` (r6-diff.tsv, values.tsv)** |
| feature cases | `seed/tests/r6c/check-r6c.sh` 10/10 (7 positives, each on the single-module AND the project route with byte-identical images; want = stage-0 d2cb84f6's own answer for all 7; 3 negatives) |
| gate cases | `gate-r6c.sh`: LOOPW (a program whose nested `loop`s are read at node 159,615 > 131,072 answers the generator's value), LIBSTUB (stage-0's answer; the R6B seed loops on it), R6B-X |
| bridge | commit bb0deb700 (the R6C features written in the R6B language): the R6B seed 6cc3dd9b compiles it to 871ca1a9 (647,632 B), its own fixed point |
| fixed point / rung proof | the bridge compiles the R6C unity (96f8d0b8a, 15,213 lines) to **ecc9c136 (647,632 B) == its own fixed point**; the R6B seed refuses that unity (E2104 at ck-r6c-doctail: its parameter S is unannotated and refined only through a later callee, which needs the R6C probe; plus a `(- x)`). `scripts/seed/bootstrap.sh` replays r0 .. r6b -> bridge -> r6c from the committed R0 seed: OK, every hash as recorded |
| gates (clean worktree) | `gates.sh --rung r6c --no-build --with-aux --with-unit`: **14/14 PASS** (BUILD ERR G1 G2 G3 G4 G5 GR XTRA UNIT KIR LEXREAD LW A64GEN; G3 golden refusal-r6c.txt = refusal-r6b.txt except 2 lines: `(- x)` now ACCEPT, an :f64 export parameter now E2104 at the export instead of E2105), load 46-74; record `seed/rungs/r6c.record` |

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

| module | verdict | cases agreeing | exports not called | first difference |
|---|---|---|---|---|
| cbor.core | AGREE | 56/56 | 1 | - |
| x25519.field | AGREE | 41/41 | 0 | - |
| ed25519.edwards | AGREE | 27/27 | 0 | - |
| ed25519.scalar | AGREE | 14/14 | 0 | - |
| sha2.sha512 | AGREE | 31/31 | 0 | - |
| ed25519.sign | AGREE | 20/20 | 0 | - |
| ed25519.core | AGREE | 47/47 | 0 | - |
| json.core | AGREE | 8/8 | 1 | - |
| kotoba.artifact.core | AGREE | 20/20 | 0 | - |
| kotoba.bytes | AGREE | 83/83 | 0 | - |
| kotoba.bytes.sha256 | AGREE | 14/14 | 0 | - |
| kotoba.codegen.layout | AGREE | 28/28 | 0 | - |
| kotoba.form | AGREE | 120/120 | 8 | - |
| kotoba.gmir | AGREE | 43/43 | 3 | - |
| kotoba.mir | AGREE | 45/45 | 6 | - |
| kotoba.codegen.mc | AGREE | 1/1 | 1 | - |
| kotoba.compiler.base64-text | AGREE | 7/7 | 0 | - |
| kotoba.compiler.frontend-tables | AGREE | 98/98 | 0 | - |
| kotoba.compiler.value-type | AGREE | 80/80 | 4 | - |
| kotoba.compiler.validate-expr | AGREE | 8/8 | 0 | - |
| kotoba.compiler.schema | DIFF | 13/15 | 0 | c2 seed trap stage-0 -5730407114169878608: (m/identities (document-map (document-keyword :a) (document-i64 1))) |
| kotoba.compiler.decimal-text | AGREE | 12/12 | 0 | - |
| multiformats.base32 | AGREE | 7/7 | 0 | - |
| kotoba.compiler.host-integer | S0-REFUSED | 0/24 | 0 | expression type mismatch: expected i64, got [:option :i64]" |
| kotoba.compiler.module-lock | NOCASE | 0/0 | 1 | - |
| kotoba.compiler.posix-path | AGREE | 16/16 | 0 | - |
| kotoba.compiler.text-bytes | AGREE | 37/37 | 0 | - |
| sha2.core | AGREE | 27/27 | 0 | - |
| kotoba.kir.compatibility | AGREE | 5/5 | 3 | - |
| kotoba.verifier.seal | AGREE | 12/12 | 0 | - |
| kotoba.compiler.provenance | DIFF | 4/12 | 1 | c0 seed trap stage-0 984004173437137646: (m/attach "" (kf/string-form "a.b") (kf/vec2 (kf/int-form 1) (kf/string-form "x")) (kf/nil-form)) |
| kotoba.kir.target | DIFF | 2/4 | 1 | c1 seed trap stage-0 198446: (m/profile :a) |
| kotoba.native.image-scratch | AGREE | 4/4 | 0 | - |
| kotoba.native.document | AGREE | 2/2 | 2 | - |
| kotoba.native.string-index | NOCASE | 0/0 | 4 | - |
| kotoba.native.string-search | S0-REFUSED | 0/8 | 2 | typed values currently require the kotoba-script web target, typed Wasm/CLJS target, or the qualified native one-word string/record/variant/option/res |
| kotoba.native.keyword-equality | AGREE | 8/8 | 0 | - |
| kotoba.native.vector-region | AGREE | 8/8 | 0 | - |
| kotoba.compiler.nbb.host.fs | AGREE | 8/8 | 0 | - |
| kotoba.compiler.nbb.host.process | AGREE | 4/4 | 0 | - |
| kotoba.compiler.refactor-cli | NOCASE | 0/0 | 1 | - |

## Open (measured, ranked)

1. **Keyword text across modules** (the 12 differing cases): the R6B table `__r6-kwtab` holds the keywords ONE module spells, so a
   keyword made in one module and turned into text in another (keyword-name, a document of it, a hash of a form) traps. Options in
   seed/CONTRACT-REQUESTS.md (a project-wide table, a link-time registry, or the KIR representation keyword = text).
2. **`when`/`if` without else in an inferred result** is :i64 (R1) where the reference makes it [:option T]: host-integer's
   `decimal-count` has a different interface in the seed (the driver is refused by stage-0). No wrong value within one compiler.
3. Scan refusals left (stage-0 refuses #"re"/#() too): kir.decimal needs a correctly rounded decimal-f64-parse and the tuple type
   [:vector [:f64 :f64 :f64]] (21 blocked, but 0 unblocked alone); kotoba.lang.json follows the pre-ADR-0363 interface and the CURRENT
   stage-0 refuses it as well (the source must change, 12 blocked); information-flow `reduce` over a list (stage-0 refuses it
   natively); hardware (namespaced keyword-keyed record literal); :option-i64 (peephole); templates (clojure.set); kexe-fs-forms after its
   map literals (a referenced def of a keyword set, `reduce` over a document). No refused module unblocks another on its own:
   73 blocked modules wait on kotoba.lang.text / kotoba.lang.coll.
4. The differential calls only exports whose signature the generator can feed (i64 bool string vector bytes document keyword, and
   kotoba.form's :form/r) on 1-6 fixed inputs each; it is evidence of agreement on those inputs, not equivalence. 131 of the 960
   agreeing cases are "both trap" (wrong input shapes for the export); a trap's kind is not compared.
5. `:f64` is a carrier only: no arithmetic, comparison, literal or record field (stage-0 has all but the field natively).
6. Process note: during the work one bare `git stash` was run in the private worktree /private/tmp/wt-r6c and popped at once
   (nothing of another agent's was touched); every commit was path-specific.
