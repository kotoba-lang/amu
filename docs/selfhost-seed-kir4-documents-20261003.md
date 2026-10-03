# Seed compile-kir: the KIR `:document` (2026-10-03, agent KIR4)

The KIR3 merge verdict ranked `:document` first among the shapes the seed backend lacks (170 frontier functions of the
10 big-compiler guests). This wave adds it. All of the work is in `seed/12-kirread.kotoba` and its tests. No SIR op, HEADS
entry or other module changed.

## Representation

The C loader has no document runtime. `tools/kexe_loader.c` has no document op, so the wave brief was wrong on this
point. Stage-0's own native backend (kotoba-native `src/kotoba/native/document.cljk`) stores a `:document` as a string
holding its canonical EDN text. It lowers every `document-*` op onto string ops plus helper functions that it emits.

The seed now does the same thing, so both backends use one representation and their output can be compared byte for
byte:

- The type keyword `:document` becomes `:string` everywhere: params, results and nested types such as
  `[:option :document]`.
- 29 `document-*` heads are respelled as calls into a second KIR library. The library is in
  `seed/tests/kir/doclib/doclib.kotoba`: 107 defns ported from stage-0's `kotoba$doc-*` helpers. `gen-doclib.py` embeds
  it into 12-kirread (`--check` reports drift). The library is emitted as one group, and only when a program uses it.
- `document-vector`, `-list`, `-set` and `-map` become left folds.
- `(document-keyword :k)` and keyword map keys become string literals.
- A keyword-typed key operand is wrapped in `__kr_kwtext`. "Keyword-typed" means a `:keyword` param, a call that
  returns `:keyword`, or `option-value-of [:option :keyword]`.

Keyword text: a seed keyword has no text at run time. When a program uses `document-keyword` on a keyword variable,
`document-keyword-value`, `keyword-name` or `keyword-from-string`, 12-kirread fills two `case` tables with every
keyword that the emitted bodies spell.

## Results (loaded host, load 50-66; timings are indications only)

| test | result |
|---|---|
| stage-0's `native_document_test` program | 19201371337 on both backends |
| `pos/11-documents.kir` (22 checks), `pos/12-keyword-text.kir` (10 checks) | 1 on both backends |
| `merge/docops.cljk`: all 31 lowered ops, 3 corpora x 30,000 ops | EQUAL, no trap (309-329 KB out each) |
| `merge/ri_doc.cljk`: runtime-identity `loader-source-for-profile` + `trust-decision`, 2,000 and 40,000 lines | EQUAL (1.15 MB out); run 120 ms stage-0 vs 180 ms seed |
| `merge/ri_doc.cljk --unknown` (`:os` keywords that the program never spells) | **DIFF**: the seed traps where stage-0 answers `none` |
| KIR gate | 19/19 ports + 31 tests |
| fixed point (HEAD de7f33fb4 + this 12-kirread) | seed-1 == seed-2 a7489ef4 (474,312 B) |

Per-function scan (`slice.py scan`, every non-helper function's call closure compiled):

| guest | functions | R4 seed e9598b28 | KIR4 seed a7489ef4 |
|---|---|---|---|
| ri | 89 | 8 | 72 |
| case | 14 | 12 | 12 |
| cc | 325 | 173 | 240 |
| codec | 200 | 58 | 84 |
| di | 412 | 200 | 226 |
| oa | 400 | 184 | 304 |
| oat | 304 | 166 | 233 |
| vc | 481 | 217 | 359 |
| vx | 394 | 36 | 75 |
| ds_guest_w | 1002 | 40 | 101 |
| **total** | **3,621** | **1,094 (30.2%)** | **1,706 (47.1%)** |

The KIR3 table listed 3,399 functions because its vx scan stopped at 172 of 394. The baseline above is a full rescan
with the R4 seed.

No `document-*` refusal remains on the frontier (306 functions). The remaining frontier shapes, by function count:

| shape | functions |
|---|---|
| `[:ref R]` / `[:list [:ref R]]` (E2105 `[`) | 151 |
| `:bytes` | 60 |
| `string-from-utf8` | 33 |
| E2128 `:data` | 15 |
| caps 3/41/34/33 | 23 |
| more than 5 params | 7 |
| vector literals over 64 items | 6 |
| f64 | 7 |
| a seed compile trap | 3 |
| loop with more than 10 bindings | 1 |

The trap and the loop cap were reported to R4B in seed/CONTRACT-REQUESTS.md. The repro is
`seed/tests/kir/repro/compile-trap-result-match.kir`, and the R4 seed traps on it too.

## Open risks

- Keyword text is closed-world. `document-keyword-value` or `keyword-from-string` on a text that the program never
  spells traps. The seed cannot make such a keyword without a new head, so it stops instead of answering differently.
  The `ri_doc --unknown` corpus shows this happening.
- `kr-kwtext` and `kr-kwof` are linear `case` / search chains over the program's keywords. With hundreds of keywords,
  keyword-heavy code runs slower (ri_doc 1.5x stage-0, measured under load).
- The library is lexed with every KIR program, so the 12-kirread unit golden went from 801 to 6,648 tokens. No KIR
  program gets close to the 131k token cap from this, and the compile time added to small ports was below 10 ms
  (loaded host).
- Key operands are recognised as keyword-typed only in the three forms listed in the Representation section. A
  let-bound keyword used as a key is refused (E2104), not lowered.
- The scan counts compile acceptance. Run equality is shown only for the docops and ri_doc guests.
