# amu-front: a native `check` built from the big frontend (agent COMPOSE, 2026-10-03)

Question: can the Kotoba-route frontend of kotoba-sema (`kotoba.compiler.frontend.analyze/analyze`, the whole linked
frontend: expand, namespace_defs, validate, infer, desugar, row, record_projection, state_ability, analyze ...) run as ONE
native command, `amu-front check <file>`, with no node/JVM/nbb at run time, and how often does its verdict equal stage-0
`amu check`?

Labels: **M** measured here, **E** estimate. Host load 30-92 during every run (recorded per file in results/): times are
indications, never results. Verdict equality does not depend on load.

## 0. Result

| | |
|---|---|
| command | `build/compose/amu-front` (2,542,592 B Mach-O, libSystem only; guest code 2,336,864 B) **M** |
| no host processes | PASS: under build/seed/noproc/noproc.dylib with an empty PATH, 0 program starts, 1 supervisor fork per run **M** |
| corpus (391 programs: the dirs of kir-backend-diff.sh) | **382 / 391 same verdict and same report** (349 SAME-OK, 33 SAME-REFUSE), 9 differ, 0 traps **M** |
| the 315 programs stage-0 compiles for aarch64-macos | **313 / 315** (312 SAME-OK, 1 SAME-REFUSE); 2 float-literal programs differ **M** |
| time per file (corpus, load 81-84) | median 0.01 s, p90 0.03 s, max 0.39 s wall; max RSS 156 MB **M** (indication) |
| largest input that fits | **248,134 B** (seed MANIFEST prefix 00-ns..20-names, MEM2's rewritten closed program): 5.3 s, 38.3 M vector handles (57% of 64 Mi), 52.8 M pairs (79% of 64 Mi), 1.71 GB heap; same verdict as stage-0 **M** |
| where it stops | the next prefix (..21-check, 515,715 B): `KEXE_TRAP :budget/cells :arena :pairs` (the 64 Mi pair arena) after 11.9 s **M** |

"Same report" = the same `ok profile=.. effects=.. exports=..` line (effect set compared as a set) or, for a refusal, the same
message text after `error: <code> at <file>[:line:col]: ` (span and code spelling are not compared; see gaps).

## 1. Route (why this one)

1. **Stage-0 native cannot produce this program.** The stable stage-0 (build/native-image/amu-native, BOOTSTRAP-REFERENCE)
   with kotoba-sema HEAD (15e45a3, ADR63's port): `compile seed/amu-front/check.cljk --target aarch64-macos --unpinned`
   analyses the whole linked frontend (228 s CPU, loaded) and then refuses at the native target admission: "typed values
   currently require the kotoba-script web target, typed Wasm/CLJS target, or the qualified native one-word
   string/record/variant/option/result slice" (`:phase :target`) **M**. It has no KIR emission either.
2. **KIR** therefore comes from `scripts/selfhost-wall/kir-dump.clj` on the JVM-built compiler classes
   (build/native-image/work, pre-ADR-0363 lineage, BOOTSTRAP-REFERENCE, build time only), over kotoba-sema **bd40e37** (the
   last frontend revision written for that lineage; 15e45a3 is the ADR 0363 port, which that lineage would not accept).
   This is FRONT's route for analyze (docs/selfhost-front-native-20261003.md). 34 modules, 4,612 functions, 296 s.
3. **Seed**: `seed compile-kir` of the committed seed lineage (tag seed-r6c-kir, be8898af) with a PRIVATE MEMORY-MAP of
   M = 16 Mi words (FRONT's region table: TOK 524,288, NODE 458,752, SIR 458,752, CODE 1 Mi, OUT 3 Mi, FN 16,384, ...),
   built by be8898af and its own fixed point (seed-1 == seed-2 = 32e54d55, 675,512 B) **M**. Needed because main's call
   closure is ~435k KIR tokens and the committed TOK region holds 262,144. The one `decimal-f64-parse` of the reader twin is
   replaced by none (no seed lowering; float literals are then refused: gap G1).
4. **Package**: tools/kexe_loader.c in its KEXE_EMBEDDED form (as scripts/seed/package.sh), budgets after MEM2
   (docs/selfhost-analyze-memory-20261003.md): 64 Mi vector handles, 64 Mi pairs, 128 Mi vector items, 1 GiB string pool,
   hash-consing 2^16 on by default (a constructor in the generated header; the environment can still override). Wires
   3 (hash/sha), 35 (fs), 37/39 (stdout/stderr), 38 (argv); never 20.
   **Wire 3 is required**: the frontend names record schemas and closure types by sha256 (`:schema-identities`,
   `__kotoba_invoke_t_<hash>`). Without it every record/closure program trapped with SIGILL (denied capability): 28 of 391
   in the first run **M**; the same input answers through FRONT's e2e guest (granted wire 3) and the JVM KIR interpreter.
   FRONT's "16 slice-carrier SIGILL" on its e2e corpus may be the same cause; not re-checked here.

## 2. The driver (seed/amu-front/check.cljk, 187 lines)

argv `check <file> [--source-path ...]` (wire 38); reads the file through wire 35; `an/analyze text nil`; prints
`amu check`'s human line (cli.cljk "check", diagnostic/format-human): ok on stdout (exit 0), refusal on stderr (exit 65).
Reproduced stage-0 report rules: the frontend's code keyword printed by name; diagnostic/refine's `(:require ..)` rename
(namespace-require-needs-project and its text); the default capability policy (no grant: `capability-missing-grant` with
the catalog names of the wires, core.cljk capability-deny-message).

## 3. Gaps (the 9 differing programs, all "stage-0 ok, native refuses")

| gap | programs | owner / next change |
|---|---|---|
| G1 float literals: the reader's `decimal-f64-parse` has no seed lowering (replaced by none) -> "source reader rejected input" | 6 (10-f64, f64-bits, vector-f64, vector_f64_composed, general-document-map, local-uleb128-130) | seed: correctly rounded decimal-f64-parse (already OPEN for kir.decimal) |
| G2 `ucs2` literal: frontend answers `vx/unsupported: ucs2` | 2 (aiueos-uefi-literals, -scratch) | kotoba-sema frontend |
| G3 typed_map_kit: frontend refuses "if test is :i64 ..." where the host sema accepts | 1 | kotoba-sema frontend (Kotoba route vs host) |

Not compared / not implemented: `--policy` (only the default no-grant policy), `--source-path` project linking (a module
with `:require` gets stage-0's single-module refusal, as stage-0 does without --source-path), refusal spans (line:col),
`--json`, definitions CIDs. The KIR is the pre-ADR-0363 lineage with kotoba-sema bd40e37, not HEAD (15e45a3).

## 4. Compiler-size ladder (results/ladder-20261003.tsv, MEM2's inputs from analyze-memory-inputs.py)

| input | bytes | verdict vs stage-0 | wall s | vectors | pairs | heap |
|---|---:|---|---:|---:|---:|---:|
| 00-ns | 13,734 | SAME-OK | 0.17 | 1.71 M | 3.73 M | 98 MB |
| ..01-mem | 28,805 | SAME-OK | 0.29 | 4.32 M | 6.20 M | 199 MB |
| ..02-io | 39,686 | SAME-REFUSE (policy: needs 35/37/38/39, i.e. analysed to the end) | 0.42 | 6.44 M | 8.34 M | 282 MB |
| ..10-lex | 64,075 | SAME-REFUSE | 0.81 | 11.06 M | 14.13 M | 480 MB |
| ..11-read | 72,503 | SAME-REFUSE | 1.02 | 12.89 M | 16.66 M | 562 MB |
| ..12-kirread | 211,983 | SAME-REFUSE | 3.96 | 31.74 M | 43.64 M | 1.42 GB |
| **..20-names** | **248,134** | **SAME-REFUSE** | 5.28 | 38.28 M | 52.78 M | 1.71 GB |
| ..21-check | 515,715 | TRAP pair arena (64 Mi) | 11.91 | 19.69 M | 67.1 M | 1.46 GB |

The per-byte rates equal MEM2's (~155 handles, ~213 pairs, ~6.9 KB heap per source byte). Next change for compiler-size
inputs (E): build the frontend's constant tables once per analyze run (kotoba-sema, filed by MEM2; E 3-5x fewer pairs),
then a larger pair arena (an ADR like 0364) -- 21-check alone (263 KB) or the 810 KB unity do not fit one process today.
The frontend's own modules cannot be checked single-file (they `:require`); a project route is not part of this driver.

## 5. Reproduce

```
seed/amu-front/build.sh [work]          # default build/compose: private seed, kir-dump (JVM, ~5 min), compile-kir, package, no-host check
seed/amu-front/corpus.sh <work> [cmd]   # verdict differential vs stage-0 (AF_FILES=<list> for other inputs)
python3 scripts/selfhost-wall/analyze-memory-inputs.py . <dir>   # the ladder inputs
```

## 6. Open risks

- KIR lineage: pre-ADR-0363 JVM classes + kotoba-sema bd40e37; the ADR-0363 frontend (HEAD) has not been compiled natively.
- The seed is a private 16 Mi-word M build, not a committed rung (CONTRACT-REQUESTS 2026-10-03 COMPOSE).
- All timings are on a loaded host (load 30-92); no quiet-host measurement was possible in this session.
- The stage-0 oracle is the stage-0 *host* sema; agreement is per report line, not per HIR.

## 7. Update 2026-10-04 (agent ARENA)

The frontend constant tables are now built once per analyze run (kotoba-sema `agent/arena-const-tables` c2766ee) and
amu-front can be built from the recorded large-M seed profile (`AF_SEED`, seed/profiles/README.md). Same corpus verdicts
(382/391); the whole 810 KB seed unity and a 1.04 MB input now fit one process (pairs 59% of 64 Mi). Measurements, census
method and remaining gaps: docs/selfhost-arena-20261004.md; results: results/arena-*-20261004.tsv.

## 8. Update 2026-10-04 (agent F64): 391 / 391

All nine differences of section 3 are closed, plus stage-0's input bound; the corpus is **391 / 391 same verdict and
same report** (358 SAME-OK, 33 SAME-REFUSE, 0 differ, 0 traps) **M**, and **315 / 315** on the programs stage-0
compiles for aarch64-macos (314 SAME-OK, 1 SAME-REFUSE). Results: `results/f64-corpus-20261004.tsv`,
`results/f64-scale-20261004.tsv`, `results/amu-front-f64-20261004.info` (no-host-processes PASS). Load 40-110 during
the runs: times are indications only (median 0.01 s, max 0.34 s per file).

| gap | programs | change | where |
|---|---|---|---|
| G1 float literals | 6 | `compile-kir` lowers `decimal-f64-parse` (12-kirread dec group = 21-check's R6D prelude in the KIR float representation; seed/tests/f64, rung r6g); build with `AF_F64=1` | seed 12-kirread |
| general-document-map (one of the 6) | 1 | then refused "value type is outside the safe profile": the Kotoba desugar's document walk kept a bare f64 Form; now `(document-f64 (f64-from-bits n))`, the host reader's shape | kotoba-sema desugar |
| G2 `ucs2` literal | 2 | validate_expr checks the rodata literals (`ucs2`/`guid`/`bytes-literal(-length)`) like the host's `rodata-literal-content?` instead of `vx/unsupported` | kotoba-sema validate_expr |
| G2' aiueos-uefi-scratch | 1 | then TRAPPED (SIGILL): check-kernel-region-provenance! passed `(fl-nth problems 0)` to `require-k` eagerly, reading an empty list on every admitted kernel memory operation (the JVM KIR interpreter: list-index-out-of-bounds 0/0); any `(kernel-load-u8 s 1 0)` trapped | kotoba-sema kernel_region |
| G3 typed_map_kit | 1 | the Kotoba desugar-expr now wraps the i64-answer predicates (`typed-map-equal` ..) as `(= op 1)` exactly once (host `bool-predicate-answer`; the mark is a head-symbol span no reader writes) | kotoba-sema desugar |
| input bound | (scale) | check.cljk refuses a file above 1 MiB with `invalid-data .. input exceeds byte limit` before analysis: the 1,563,759 B input is now SAME-REFUSE (was REFUSE-DIFF) | check.cljk |

kotoba-sema: branch `agent/f64-front` (5971905, 2d7d05d on c2766ee, the ARENA tree this route compiles; pushed). The
ADR-0363 lineage (15e45a3 / PORT's port) needs the same three edits (Kotoba arms only). Build:
`AF_SEED=<large-M seed of r6g> AF_F64=1 AF_KSEMA=<kotoba-sema at 2d7d05d> AF_KSEMA_REV=2d7d05d seed/amu-front/build.sh <work>`.
Spot checks beyond the corpus (amu-front == stage-0 line): computed kernel base, scratch window > 16 KiB, alloc window,
malformed GUID / hex, `(ucs2 x)` of a parameter, `typed-set-equal` as a :bool result and as an i64 operand (refused by
both).
