# amu-main: `amu check | compile | refactor` as one Kotoba entry (agent MAINS, 2026-10-04)

Question: can amu's three commands be Kotoba command entries (arity-0 `main`, argv through wire 38, the same reports as
stage-0), compiled by what compiles today, with every missing piece a declared stub that names it? How close is each
command to stage-0 on the corpus?

Labels: **M** measured here, **E** estimate. Host load 25-90 during every run, so no time on this page is a result.
Stage-0 = `build/native-image/amu-native` (sha256 `d2cb84f6`), the BOOTSTRAP-REFERENCE oracle. It is never in an amu
image's process tree. A stub is never counted as behaviour.

## 0. Result

| | route s (`build/mains/amu-s`) | route k (`build/mains/amu-k`) |
|---|---|---|
| built by | seed r6f `da6d0a98` from source, project route, with the seed's split source linked in. No stage-0, JVM or node at any step **M** | KIR from `kir-dump` on the JVM classes (BOOTSTRAP-REFERENCE at build time), plus native code from the large-M r6g seed `c13e22c0` (compile-kir) **M** |
| image | 940,848 B Mach-O (sha256 `06f39c7b`), guest code 756,418 B, libSystem only, wires 35,37,38,39 | 2,641,656 B (`837a2287`), guest code 2,432,600 B, libSystem only, wires 3,35,37,38,39 |
| `check` | argument layer real (extension 64, regular file 65). Analysis: **declared stub** (exit 69) | **real**: frontend `analyze` (seed/amu-front/check.cljk). 390/391 fully equal to stage-0, 1 differs in exit status only |
| `compile` (aarch64-macos) | **real**: the seed compiler, called in-process. 262 of the 315 programs stage-0 compiles are behaviour-equal on every export | **declared stub**: the JVM lineage refuses the seed's source (section 4) |
| `refactor` | subcommand layer real (no or unknown subcommand: refactor-cli's exact :refactor/usage map, 64). Every subcommand: **declared stub** | same |
| self-reproduction | amu-s compiles HEAD's seed unity to `da6d0a98` byte-identical, and compiles its own entry to the identical kseed (756,449 B) **M** | n/a (KIR from the JVM) |

Neither image holds all three real commands. Section 4 explains why one image is not possible today.

## 1. Layout

- `src/amu/main.kotoba`: the dispatcher. It follows bin/amu's routing for the three commands and returns stage-0's usage
  refusal for anything else (64).
- `src/amu/cli.kotoba`: argv (wire 38), stdout and stderr (37/39), STAT (35), and stage-0's `:kotoba.cli-error/v1` shapes.
- `src/amu/refactor.kotoba`: shared by both routes.
- `s/amu/{check,compile}.kotoba`: route s.
- `k/amu/{check,compile}.kotoba`: route k.
- `build.sh [--route s|k|both]`, `build-k.sh` (variant k2 = compile real, tried first; k1 = compile stub),
  `parity.sh <work> [--check AMU] [--compile AMU]` (the corpus differential), `missing.py <selfbuild-dir>` writes
  `missing.tsv`.

## 2. check parity (amu-k vs stage-0 `check <file>`, 391 programs of seed/amu-front/corpus.sh)

**M** (amu-k sha256 `837a2287`, load 65-70): **390 / 391 same verdict, same report line and same exit status**
(358 SAME-OK, 32 SAME-REFUSE). In 1 more case the verdict and the report line match but the exit status does not:
`examples/w1-denial-ceiling` (effect-ceiling refusal: stage-0 exits 70, amu-k 65). There are 0 OK-DIFF, 0 REFUSE-DIFF
and 0 traps. That is amu-front's 391/391, now reached through the dispatcher and its argument layer. Results:
`build/mains/parity-k/{summary.txt,check.tsv}`. amu-s answers every readable `.kotoba` input with the stub (exit 69).
That follows from its construction and was not run over the corpus.

## 3. compile parity (amu-s vs stage-0 `compile <f> --target aarch64-macos`, the same 391 programs) **M**

| class | n | meaning |
|---|---:|---|
| BEHAVIOUR-SAME | 262 | both compile; every user export run from both codes (C loader, fuel 16M) gives the same result, status and trap |
| BOTH-OK-DIFF | 4 | both compile; 5 exports that stage-0 exports are absent from amu's container (public definitions in files with no :export clause, with fn-typed, record or untyped signatures: `choose`, `build`, `->Reading`, `apply-one`, `make-renderer`). Every run export is SAME |
| BOTH-REFUSE | 55 | both refuse |
| AMU-REFUSES | 49 | stage-0 compiles, the seed refuses by name (`defprotocol`/`defmethod`, `if-some`/`when-some`, float literals, untyped results E2126, records, ...) |
| AMU-ACCEPTS | 21 | stage-0 refuses, amu compiles: 5 doseq programs (stage-0's "if test is :i64" rule), abort/throw programs (stage-0 "native artifact contains an unsupported effect" at verify), 2 nbb fixtures, ... |

Export runs: 644 SAME, 0 DIFF, 0 TIMEOUT, 5 MISSING. Of the 315 programs stage-0 compiles, 262 (83%) are behaviour-equal
on every run export. The report format is not compared, and that difference is declared: amu-s writes kseed/v1 and
prints the seed's ok line or `seed: E..` refusal line. Exit statuses are mapped to stage-0's (0, 65, 64).
Results: `build/mains/parity-s/{summary.txt,compile.tsv,exports.tsv}`.

## 4. What is missing (exact; module rows in `missing.tsv`, generated from the seed da6d0a98 scan build/walls/sb0)

| for | missing |
|---|---|
| one image with check + compile | route s: the frontend's closure from source. route k: the seed's source through the JVM lineage. kir-dump refuses it with "vector-assoc! requires a linear handle: M0 is used more than once on some path through mem-init-fills" (measured, variant k2). Option C (requested): `compile-kir --emit-module`, so that KIR-route objects link with source-route objects through `seed link` |
| check on route s | `kotoba.compiler.frontend.analyze`: 33-module closure, 18 OK, walls kotoba-reader (E2102 `0.0`) and kir.interp (E2101 `string-split-count`), 13 BLOCKED. The product entry `nbb.check-cli` adds walls json (E2104) and information-flow (E2105): 80 modules, 48 OK |
| check on route k (vs stage-0) | `--policy`, `--source-path` project linking, refusal spans, `--json`, definition CIDs. The file must be argv[1] |
| compile = stage-0's | the `:kotoba.kexe/v1` artifact (`:program` KIR, provenance and inputs files), stage-0's refusal map, the default `--output` (stub), targets other than aarch64-macos (stub), and the big frontend's language (the seed's subset: 49 AMU-REFUSES, 21 AMU-ACCEPTS). The big backend route `nbb.aarch64-cli`: 98 modules, 57 OK, walls kotoba-reader, uefi-operations, kir.interp, json, machine-ir (E1005), information-flow, verifier.fx (E2001 empty name) |
| refactor | refactor-cli/run's Kotoba arm (a stub that throws). The library: cst (E2003 `declare`; typed twin on kotoba-lang agent/refactor-cst-twin, unmerged), edit/diff/verify (E1005 `#`), prelude (E6009), core/graph/extract/partition/rules.* (blocked behind cst). `verify` needs wire 20 (spawn), which the image never holds |

## 5. Reproduce

```
zsh seed/amu-main/build.sh                 # amu-s (seconds; no stage-0/JVM/node)
zsh seed/amu-main/build-k.sh               # amu-k (JVM kir-dump ~5-10 min loaded, then compile-kir)
zsh seed/amu-main/parity.sh build/mains/parity-s --compile build/mains/amu-s
zsh seed/amu-main/parity.sh build/mains/parity-k --check build/mains/amu-k
python3 seed/amu-main/missing.py build/walls/sb0 > seed/amu-main/missing.tsv
```

## 6. Open risks

- `missing.tsv` is a snapshot of a scan that other agents are changing (WALLS). It must be regenerated after each wall fix.
- Both routes build from git HEAD. Route k pins kotoba-sema `2d7d05d` (agent/f64-front, unmerged), as amu-front's
  391/391 build does.
- Route k's KIR comes from a JVM lineage. It is not selfhost-built, and its label says so.
- MISSING exports are an export-table difference: the seed omits public defns that are not exported. The behaviour of
  those 5 exports was not compared.
- The parity runs single representative argument vectors (kbd_exports.py), not exhaustive inputs.
