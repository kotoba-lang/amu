# Seed R6 entry (R6A): the cross-module interface, the string arena, the first R6 scan (2026-10-03)

Agent R6A. Rung R6 of the seed ladder (Forms and the cross-module interface), entry part. Tag `seed-r6a`, record
`seed/rungs/r6a.record`. Every timing on this page was taken on a loaded host (load average 37-80) and is an indication only.

## Result

| item | value |
|---|---|
| fixed point | the R5B seed 04c11dbe (reproduced here: R4B-era seed 4502396d -> bridge a49a6098 -> 04c11dbe) compiles the R6A unity (14,026 lines) to **36433468** (566,144 B), which compiles it to itself. No bridge: the R6A sources are written in the R5B language, and the unity has no run-time keyword, so the old and new keyword lowering give the same bytes |
| gates | `gates.sh --rung r5b --no-build --with-aux --with-unit` READY (14 gates) and `gates.sh --rung r6a --no-build --with-aux --with-unit` READY (14 gates: BUILD ERR G1 19/19 G2 65/66 G3 0 differ G4 84/84 containers identical seed-0 vs seed-1 G5 GR (r1 r3 r4 r4b r5 full) XTRA (gate-r6a: R6A 10/10, R5B extra, R5A split fixed point + SEP) UNIT 12/12 KIR 19/19 LEXREAD LW A64GEN 756/756) |
| R6A cases | `seed/tests/r6a/check-r6a.sh` 10/10: keyword (p01), record by reference without and with the importer's own schema (p02, p02b), the Form shape `:form/r` (recursive, keyword field, list of refs, bytes field; p03), fn types incl. a closure result (p04), a variadic export (p05), `:bytes` (p06), nested record schemas (p07), a 7-parameter export (p08), a schema conflict refused (n01, E2128 at the importer's declaration). In-process image == separate-mode image on all 9 positives. Stage-0 agrees on p01 p03 p04 p06 p08 (`stage0-verdicts.tsv`) |
| string arena | seed split (14 namespaces) linked by the R5B seed vs the R6A seed, same sources, identical container: vector handles 885 -> 347, conj 691 -> 154, vector items 12,204,528 -> 12,203,365, string pool 4.52 -> 4.64 MB, pairs 344,654 -> 355,360 (KEXE_ARENA_USE, 3 runs each, deterministic) |
| R6 scan | 126 modules (`scripts/seed/r6-scan.sh`, separate mode, the seed as checker): **2 compile** (kotoba.compiler.module-lock, kotoba.native.keyword-equality), 36 refused, 88 blocked by a refused require. Stage-0 (check-native, same day) checks 71 of the 126; of those 71 the seed compiles 2, refuses 31, and 38 are blocked |

## What changed

1. **Keywords across modules.** A keyword's run-time value is now the 64-bit FNV-1a hash of its spelling (`SF-HASH`, 30-lower
   `lw-kwval`, delimited R6A block) instead of its SYM index, which is private to one compile. Every module, and the separate-mode
   objects, agree without a link-time table. Cost: a keyword constant is up to 4 instructions instead of 1-2.
2. **Interfaces (60-proj).** Stub templates now spell `:bytes`, `:keyword`, records `[:ref :kw]`, fn types `[:fn [[P ..] R]]`,
   variadic clauses `[p0 T0 & p1]`, and parameters 6.. of a 16-parameter clause. A record crosses with its schema: every record
   reachable from a signature (fields, nested, recursive) is written as a `[:record :kw [[:f T] ..]]` piece of the interface
   entry (KSEEDO1 E line after a TAB). The importer's generated ns form carries `(:schemas {imported .. own ..})`; 21-check
   registers both and refuses one name with two definitions (E2128); the error position in the copied own text is mapped back
   to the module's source. The module's own `:schemas` clause / `:kotoba/schemas` entry is now kept on the project route (R4B's
   open item). E6017 remains for: an error type no stub can throw (record, collection), more than 8 clauses, a record with no
   registered schema.
3. **String arena.** P, the linker's string pool, is a `:string` arena plus a start-offset table in L (`pj-n`, `pj-p L P i`,
   `pj-padd`, in-place compare `pj-peq`); it costs no loader vector handle per string (R5A's `[:list :string]` cost one each).
4. **Project-route normalisation (pj-norm).** Docstrings and a defn's attr-map, a top-level `nil` (`#?(:kotoba nil ..)`), and
   `clojure.core/f` are read on the project route; `^meta` reads as nothing (10-lex, one delimited line). The single-module route
   still refuses docstrings (request to 20-names/21-check in CONTRACT-REQUESTS).

The language reference refuses a variadic export (stage-0: "variadic function total cannot be exported .."); the seed admits it
across a library interface as the R6A brief asks. This is a recorded extension, not the reference's behaviour.

## The R6 scan: first refusal per module

`scripts/seed/r6-scan.sh` copies the 126 files into one root, orders them dependency-first (the Kotoba reading of each ns form),
and runs `compile --emit-module` per module against its requires' objects. "Blocks" is the number of the 126 that import the
refused modules directly or not. Data: `seed/tests/r6a/scan/` (r6-scan.tsv, hist.txt, seed-vs-stage0.tsv).

| modules | code | first refusal | blocks |
|---|---|---|---|
| 9 | E2105 | `:document` type (json.core, codegen.layout, kotoba.form, gmir, kir.decimal, kexe-fs-forms, kir.target, native.document, native.vector-region) | 47 |
| 3 | E1005 | `#` reader syntax (`#"re"`, `#(..)`: kotoba.lang.text, lang.coll, refactor.cst; stage-0 refuses all three too) | 72 |
| 4 | E2102 | hex integer literals `0x80` `0xff` `0xffffffff` (kotoba.bytes, multiformats.base32, sha2.core, sha2.sha512) | 18 / 9 / 8 / 6 |
| 2+1+2+1 | E2101 | stdlib heads `string-find-byte`, `string-to-utf8`, `vector-i64` (variadic constructor), `ex-info` | 15, 12, 7, 1 |
| 3 | E6010 | friendly capability names `hash/sha256` (kotoba.artifact.core), `fs/app-data`, `process/spawn` | 24, 3, 3 |
| 2+1+1+1+1 | E2105 | types `:symbol`, `:f64`, `:option-i64`, a map-shaped type `{..}`/`[`, `:hardware/qualified?` | 3, 8, 2, 5, 6 |
| 2 | E2124 | a `def` of a non-literal (keyword, expression) | 5, 3 |
| 1 / 1 / 1 | E2128 / E6009 / E6023 | `[:option :document]` record fields; a module exporting nothing (stage-0 too); a template module (stage-0 needs `:with` too) | 8 / 1 / 3 |

Ranked next features (by the stage-0-OK modules each one gates, then by modules blocked):

1. **`:document` in the source route** (KIR4/KIR5's canonical-EDN representation and doclib, with a hash -> text table for keyword
   text now that a keyword's value is a hash): 9 modules first, kotoba.form among them, 47 blocked.
2. **Hex integer literals** (10-lex): 4 modules, up to 18 blocked; cheap.
3. **Stdlib heads** `string-find-byte`, `string-to-utf8`, `vector-i64`, `ex-info`: 6 modules; they block 15, 12, 7 and 1 modules (overlapping).
4. **Friendly capability names** in the R5B catalogue (`hash/sha256` blocks 24).
5. **Types** `:symbol`, `:f64`, `:option-i64`, `def` of keyword values.
6. **Link capacity**: the image lives in L (at most ~1.9 MB of code); the 126 modules are about 5 MB at the split's code/line
   ratio (est.), so the design's separate 8 MiB image buffer is needed before a full R6 link. Pairs (355k for the 14k-line split,
   budget 4.19M) are the next loader budget (est. ~3.2M at 123k lines).

The deeper frontier is not visible yet: 88 modules never ran because a require was refused, and the stage-0-refused modules
(55 of 126: typed `[:result .. [:ref :fe/err]]` mismatches in the frontend ports, `set` as an operation, ..) are the frontend
port work (H-F1), not seed features.

## Reproduce

    SEED_BUILD=<abs build dir> zsh seed/tests/r6a/check-r6a.sh <seed.bin>
    SEED_BUILD=<abs build dir> zsh scripts/seed/r6-scan.sh <seed.bin>          # 126 modules, about 1 min at load 40-60
    SEED_BUILD=<abs build dir> zsh scripts/seed/gates.sh --rung r6a --no-build --with-aux --with-unit
