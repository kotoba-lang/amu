# Selfhost SLRE: complete regex workload, correctness first

`bench/embench/batch-ports/slre.kotoba` implements the pinned SLRE engine
instead of recognizing just four fixed expressions. Native selfhost Amu
accepts and compiles it. The historical port and published timing table stay
unchanged. This is not yet a C-or-better result: asher remains unreachable,
so no timing ratio or optimization promotion is claimed.

The upstream profile is Embench commit
`09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`, `libslre.c` SHA-256
`ff918566aa585c665433fecfa1c56ca0136f819df0a5654f2ae98cc696d96056`,
and `slre.h` SHA-256
`87bdc34b18e269c46c13c3e221f2618fa2aac2b4299fe59561810522880e3264`.
Native compiler SHA-256 is
`abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e`,
from the byte-identical three-generation Amu build. Checking, compilation
and execution use no Node, nbb or JVM fallback. Python constructs diagnostic
fixtures and Clang builds the unchanged C oracle outside the product path;
all 97 PRODUCT inventory entries remain unchanged.

The port preserves regex parsing, bracket and branch records, stable branch
sorting, unanchored search, character operations and ranges, optional/star/
plus and non-greedy quantifiers, captures and recursive backtracking. It
retains the upstream range-case condition, including its unusual polarity.
Hex shifting is multiplication by 16 over bounded hex digits; the native
analyser refuses the named shift form, so no checker bypass is used. The
804-cell owned workspace has the original capacities of 100 brackets,
100 branches and 100 capture slots. The actual four-expression body reuses
one workspace across patterns and repeated bodies; active records are reset
in the original order. C stack/pointer storage and owned Kotoba vectors have
different representations and overheads, which the comparison discloses.

The first differential found that exhausted unanchored search discarded
`SLRE_UNEXPECTED_QUANTIFIER` (-2) and returned ordinary no-match (-1) for
`*a`. That version is rejected and archived. The corrected search returns
the last named error exactly as C does. No compiler or safety rule changes
were needed.

Evidence covers 42 ASCII fixtures: the four original patterns/text, anchors,
empty input, all quantifier forms, alternation, nested/sequential captures,
ranges and inversion, case flag, escaped operators, hex/digit/space classes,
invalid expressions, capture capacity, and bracket/branch limits. For each,
all 804 initialized state slots plus the result are compared with C
(33,810 values). The observation adapter zero-initializes otherwise unused
C state; regex pointers and capture pointers are normalized to source/text
offsets. Its results and captures are also compared with unchanged
`slre_match`, using positive capture capacities. Null capture pointers,
arbitrary non-ASCII inputs and every possible malformed expression are not
claimed by these bounded fixtures. The final C oracle adds four NUL bytes to each regex buffer so the original
four-byte flag probe is valid even for short fixtures. A separate replay
revalidates every recorded native value against this padded oracle, and
its 42 selfchecks, 33,810 state reads and original 32-body benchmark pass
AddressSanitizer and UndefinedBehaviorSanitizer. The initial unpadded
observation report is retained with this explicit qualification receipt.

The production four-match body additionally agrees on 15 defined active
state/result values; batch counts 0/1/2/17/32 agree with C (positive counts
produce original sum 102). Workspace index 803 succeeds, 804 traps, and
fuel 1 traps. Local execution times in raw diagnostic output are not
performance samples. Timing rows are empty and formal qualification is false.

`docs/evidence/coscientist-slre-20261004/` saves native/C artifacts, provenance,
all comparisons, rejected first search, oracle access checks, regeneration,
source-pin refusal and a fresh timing replay bundle. The fixture adapter is
new benchmark-authoring/bootstrap code; existing Kotoba AST refactor rules
do not cover algorithm authoring. Product sources are unchanged.

Unpack the measurement bundle beside pinned `upstream`, `runner` and
`images/r6m`, then run:

```sh
python3 measure-slre-full.py coscientist-slre-complete
```

The harness checks and compiles both source and diagnostic exports, verifies
the full differential and guards, refuses report replacement, and records
failures. Timing uses 32 bodies per call, one untimed warmup, calibrated
counts, 30 rotating samples per arm, and load <= 4. CPU idle and the formal
native performance gate still need separate qualification. This is not an
official full-suite Embench score.

Four adapted workloads still lack complete alternatives: picojpeg, qrduino,
sglib-combined and wikisort. The next performance decision remains a matched
asher comparison followed by hypothesis ranking, not promotion from source
size or correctness counts. The C-or-better goal remains open.
