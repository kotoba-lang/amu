# Seed backend merge test: big-compiler KIR through `compile-kir` (2026-10-03, agent KIR3)

Question: can the seed backend (`seed compile-kir`, seed/12-kirread.kotoba feeding 20-names .. 50-out) replace
stage-0's `native/machine_ir` + aarch64 backend for the BIG compiler? **KIR5 re-ran the flip test (section 0): the
verdict is GO** for the condition this page set. Sections 1-6 are the KIR3/KIR4 history (NO-GO at the time). Section 7 is
the integration plan, which starts with its falsification test.

## 0. KIR5 flip test (2026-10-03, agent KIR5): GO

Command: `seed/tests/kir/flip.sh <seed.bin>` (SCAN + MERGE + EQUAL in one run, summary in `$FLIP_W/flip.txt`). The seed is
the R4B seed 4502396d's sources + this commit's 12-kirread / 02-io: **1d84e6ff (503,992 B), its own fixed point**
(seed-1 == seed-2, built by 4502396d). Stage-0 is the stable native image (sha256 d2cb84f6..). Load 40 at the start, 74
after SCAN, 82-84 at the end. Equality verdicts do not depend on load. The run times below are indications only.

**SCAN** (slice.py scan, every non-helper function's call closure of the 10 big guests): **3,620 of 3,621 compile
(99.97%)**. R4B's seed compiled 3,259 (90.0%). The one refusal is vc `kotoba_module__16__44`, a `typed-cap-call 23`
(`:entropy/draw`). Its output is random, so no equality test can cover it. The wire belongs to R5B's capability table
(request filed).

**MERGE** (merge.sh: stage-0's native `main` vs the seed's native `main` compiled from stage-0's KIR, same input, stdout
compared byte for byte plus sha256/16 of each side; scale 1 and 8; MERGE_RUNS 3, vx parts 1):

| guest (big-compiler code) | scale 1: verdict, out bytes | scale 8: verdict, out bytes | code bytes s0 / seed | run ms s0 / seed (s8) |
|---|---|---|---|---|
| desugar pass `!read` (ds_pass = ds_guest_w + pass tail, :io/read) | EQUAL 104,514 | EQUAL 907,134 | 911,487 / 841,520 | 60 / 70 |
| desugar pass `!desugar` | EQUAL 180,187 | EQUAL 1,508,507 | same image | 420 / 510 |
| desugar pass `!all` (read, desugar x2, count) | EQUAL 1,604 | both trap `:vector-table-exhausted` at the same point, 0 B each | same image | 510 / 620 |
| validate-expr (vx.cljk; cases = stage-0's `!desugar` answers, gen-vx.py; 96 cases per run) | EQUAL in 6/6 parts, 53,740 | EQUAL in 43/43 parts, 442,156 | 195,341 / 170,128 | 1,400 / 1,160 (sum of parts) |
| form_count (kotoba.form/edn-form + node count) | EQUAL 1,585 | EQUAL 12,597 | 68,743 / 60,912 | 40 / 50 |
| kotoba.lang.edn read/write (edn.cljk) | both SIGILL at line 19 of the corpus, 1,847 B equal | same | 76,329 / 59,496 | 20 / 20 |
| keywords from text (kw.cljk, 155 keyword texts of the corpus) | EQUAL 10,408 | EQUAL (same texts) | 38,110 / 35,400 | 10 / 10 |
| f64/f32 conversions (float.cljk, gen-float.py) | EQUAL 741,441 | EQUAL 3,660,593 | 2,343 / 3,281 | 180 / 180 |
| kotoba.string + decimal-text | EQUAL 141,483 | EQUAL 1,131,989 | 10,740 / 12,488 | 140 / 200 |
| posix-path | EQUAL 235,910 | EQUAL 1,880,213 | 8,344 / 8,328 | 120 / 160 |
| string.case | EQUAL 5,727,282 | EQUAL 7,357,492 | 47,927 / 36,857 | 540 / 510 |
| sha2.core | EQUAL 8,602 | EQUAL 70,312 | 13,627 / 10,073 | 40 / 30 |
| all 31 document ops (docops.cljk) | EQUAL 41,986 | EQUAL 342,190 | 51,418 / 41,920 | 440 / 480 |
| runtime-identity documents with `--unknown` keywords (ri_doc.cljk) | EQUAL 39,566 | EQUAL 321,026 | 97,303 / 68,888 | 50 / 70 |

So 75 runs give 0 DIFF and no seed-only trap. Three runs trap on both sides at the same point with identical output:
ds `!all` at 8x and edn at both scales. The edn trap is a guest/corpus limit, the same on both backends. ri_doc
`--unknown` used to TRAP in the seed (KIR4: the keyword tables) and is now EQUAL. vx in one run exhausts the loader's
vector table on BOTH sides (320 of 516 cases at 1x; the guest never frees), so flip.sh runs it in parts.

**EQUAL per function** (slice.py equal): a big-guest function counts when its slice compiles AND a function with the
same structural hash is in the `main` call closure of a merge guest whose runs were all EQUAL. The hash covers the body,
param types and result, with callee names replaced by the callees' hashes, so stage-0's per-guest numbering drops out.
Result: **1,741 of 3,621 (48.1%) compiled and reached by EQUAL runs; 0 reached by a non-EQUAL run.** By guest:
ds_guest_w 843/1,002, vx 249/394, cc 96/325, oa 118/400, di 122/412, vc 156/481, codec 85/200, oat 40/304, ri 26/89,
case 6/14. This is static reachability. A reached function need not have run on these inputs.

**Verdict: GO.** The condition set in section 1 was ">= 95% of functions compile AND form_count, validate-expr and
desugar pass merge.sh with EQUAL". Both halves hold: compile is 99.97%, and the three guests are EQUAL at 1x and 8x with
0 DIFF. On the stricter reading ("each function's own result shown equal"), only 48.1% of the big guests' functions are
reached by an EQUAL run. Functions not reached are not known to be equal: none is known to differ, and none has been
tested. The integration (section 7) therefore starts with a falsification test that compares whole compiles, not
slices.

Gates on these sources (HEAD 79bca5f32 + this commit): `gates.sh --rung r4b` READY (BUILD fixed point 1d84e6ff via the
lineage seed 568d6152, ERR, G1 19/19 with both seeds, G2 65/66, G3 0 differ from refusal-r4b.txt, G4, G5, GR), `gates.sh
--rung r5a --only XTRA` READY (split fixed point, SPLIT-G1/G2/G4, SEP), KIR gate 19/19 + 33 tests, unit 02-io and 12-kirread
PASS (12-kirread golden: token/node counts of the larger prelude, digest unchanged). Load 79 during the gates.

What KIR5 changed to get there (all inside 12-kirread / doclib / 02-io; no SIR, HEADS, 21-check or 41-a64gen change):

- **Keywords are their text** on the KIR route (`:keyword` -> `:string`, keyword literals in value positions -> string
  literals, keyword `=` -> `string=?` where stage-0's own keyword-equality rule sees a keyword (literal, :keyword
  parameter, record field typed :keyword, call returning :keyword, if/let of those). Other `=` stay i64 and 21-check
  refuses a string operand (E2123), so a missed case is a refusal, not a wrong answer). This is stage-0's native
  representation. It removes KIR4's per-program keyword tables, which trapped on texts the program never spells
  (non-literal `document-keyword`, `keyword-from-string` of input text, `document-kind`). The `:schemas` map is walked
  the same way (KIR4's dropped-:schemas request is closed).
- **f64/f32** as their IEEE bit patterns in an i64 (f32 sign-extended, = stage-0's f32-to-bits). `f64-to-bits`,
  `f64-from-bits` and `f32-to-bits` are the identity. `f64-to-f32-rounded` / `f32-to-f64-exact` are library code with
  fcvt's result under the default FPCR (RNE, subnormals, overflow to infinity, NaN quieting with its payload kept). That
  is EQUAL on 3.66 MB of float.cljk output and pos/13-floats (22 checks). Float arithmetic, compares and parse/print are
  still refused by name: none is on the frontier.
- **record-assoc on a record by reference**: the dropped inline schema was left unwalked (`:keyword`) and conflicted with
  the walked `:schemas` entry (E2128, 4 functions; pos/14).
- **WRITE_SEP in output** (CONTRACT-REQUESTS R4B line): 02-io `io-write-bytes` writes a container in pieces that never
  hold a whole loader token. The first piece goes as a WRITE, and the request is cut one byte into every occurrence of
  WRITE_SEP/APPEND_SEP, with the rest sent as APPENDs. Both token texts are built at run time from byte tables, so the seed's
  own string pool never spells them. Content without a token is one write, as before. seed/tests/kir/writesep/run.sh:
  4/4 programs whose literals spell the tokens compile by file = by hex route, and extract and run. 50-out itself is
  unchanged.

Every number below was measured on this Mac while it was loaded (load average 87-148, recorded per row). Timings are
indications only. Equality verdicts do not depend on load.

## 1. Falsification first: what makes it a no-go

The seed backend is a **no-go** as a replacement if any one of these holds. Each is checked by a script in seed/tests/kir/.

| # | falsifier | status today |
|---|---|---|
| N1 | a guest that both backends compile gives different output bytes on the same input | **not observed**: 5 guests x 4 input sizes, 0 DIFF (section 3) |
| N2 | the seed refuses KIR shapes that the big compiler cannot avoid, and the shapes have no lowering on the seed's i64/pair/vector ABI | **holds for now**: 69% of the big guests' functions are refused (section 4). Every blocking shape is lowerable, because stage-0 itself lowers it onto the same loader ABI, but the seed lacks the lowering |
| N3 | the seed's code is clearly slower or needs clearly more memory than stage-0's on the same KIR | not observed: run time 0.78x-1.43x of stage-0, peak RSS equal or lower. On sha2 the seed gets 3.8x further before the loader's vector table runs out |
| N4 | the seed backend breaks its own fixed point or the rung gates when the KIR additions land | not observed. On the R3 HEAD (4c2634097): fixed point e77accc9 (338,144 bytes), gates `--rung r3` READY, KIR gate 19/19 ports. Rebased on R4's WIP commit f316f4a1f: fixed point 6ccfcf24 (382,832 bytes, seed-2 == seed-3), KIR gate 19/19 ports + 29/29 tests; G1 G2 G4 G5 GR pass, G3 shows 17 R4 refusal-text changes (R4's golden is pending, not a KIR change) |

**Verdict: NO-GO for replacing `native/machine_ir` + aarch64 now (N2).** The seed backend is a **GO** as the backend for
the leaf layer of the big compiler (string, i64 and vector code: the string library, path handling, case mapping,
SHA-2, decimal text). It gives byte-identical output there, at comparable speed and lower memory. The decision flips to
GO for the whole backend when the scan in section 4 reaches >= 95% of functions and the record/document guests
(form_count, validate-expr, desugar) pass merge.sh with EQUAL.

## 2. Census: compile-kir on the 315 programs stage-0 compiles

`seed/tests/kir/census.sh` (391 programs; stage-0 compiles 315 of them). The seed is HEAD + this commit's 12-kirread,
built by the R3 seed cbae36dc.

| compiler | compile-kir accepts | programs whose runnable exports all equal stage-0 |
|---|---|---|
| commit 2459a0f91 (R1 + KIR) | 241 / 315 | 224 / 295 |
| R3 seed cbae36dc (HEAD) | 271 / 315 (86.0%) | 252 / 295 |
| **this commit (e77accc9)** | **299 / 315 (94.9%)** | **277 / 295 (93.9%)**; exports 338 / 368 |

There are 0 value mismatches. The two programs counted as "not equal" trap on both sides, with a different signal
(SIGILL vs SIGTRAP: `examples/range-slots` bad-byte, `test/nbb/fixtures/fs-app-data-read`). The other 16 refusals are
outside the seed's language: f64/f32/i32/u32 (5), `variant-new`, `hetero-vector-at`, `arena-scope`,
`string-fold-ascii`, `string-compare-lines`, `string-from-utf8`, recursive records `[:ref R]` (2), `:document`, a
6-field record constructor (more than 5 parameters).

What 12-kirread gained in this wave (all in the reader; no other module changed):

- UTF-8 string literals in KIR. Byte scans step over whole code points. A byte >= 128 outside a string is E1002 at that
  byte (neg/20).
- The KIR effect `:state`. Stage-0 has already lowered perform/handle to state passing (pos/08, was neg/17).
- Respellings: `typed-cap-call` with the wire ids 35/37/38/39, `vector-get`, the option/result constructors and tests
  (`option-some` .. `result-error` -> the R3 `-of` heads).
- A **KIR library**: KIR builtins that the seed has no head for are written in the seed language and appended to the
  prelude. Only the ones a program uses are emitted, so a program that uses none compiles to the same bytes as before.
  The builtins are `string-find-byte`, `string-contains?`, `string-replace-all`, `string-append-range`,
  `string-index-of-from`, `vector-take` and `vector-drop`. Each keeps the traps of the loader's runtime operation or of
  stage-0's lowering (pos/09). `vector-take`/`vector-drop` copy into ONE vector (`vector-alloc` + `vector-assoc!`). A
  `vector-conj` loop minted one vector-table entry per item, and the posix-path merge input at 20x trapped
  `:vector-table-exhausted` earlier than stage-0. That was found by this test and is fixed.

## 3. The merge test: big-compiler pieces, stage-0 KIR, seed native code, compared with stage-0 native code

`seed/tests/kir/merge.sh <guest> <input>` runs these steps for each guest:

1. Stage-0 compiles the guest against the wall classpath (`compile --unpinned --target aarch64-macos`).
2. The KIR is cut out of the kexe.
3. `seed compile-kir` compiles the KIR under the C loader only.
4. Stage-0's `main` and the seed's `main` both run natively on the same input file. The stdout bytes are compared.

The inputs come from `seed/tests/kir/merge/gen-inputs.py <dir> [scale]` and are deterministic. Each guest is a thin
`main` around the big compiler's own module:

| guest | big-compiler code under test | input |
|---|---|---|
| posix_path.cljk | `kotoba.compiler.posix-path` basename / dirname / normalize / join | 20k x scale paths (UTF-8 segments, `.`, `..`, `//`) |
| kstring.cljk | `kotoba.string` (lang/compat: starts/ends-with, includes, blank, trim*, reverse, index-of, last-index-of, replace, utf16/byte index) + `kotoba.compiler.decimal-text` (decimal?, parse, fields) | 20k x scale cases over 16 ops |
| case.cljk | `kotoba.string.case/upper-case-root` (lang/compat, 415-line tables) | every Unicode scalar value + 4k x scale random lines |
| sha2.cljk | `sha2.core` sha256-hex, sha224-hex, hmac-sha256-hex (behind `compile-cache/sha256-bytes`) | 30 KB as byte chunks of 0..199 |

Results with MERGE_RUNS=5. Run times are medians of the loader process. "cpu" is user+sys including the forked runner.
Stage-0's compile time includes its whole frontend, so it is not comparable with the seed's backend-only compile-kir;
it is shown for scale only.

| guest (scale 8) | verdict | KIR bytes | code bytes s0 / seed | run ms s0 / seed | cpu ms s0 / seed | peak RSS MB s0 / seed | compile ms s0 (whole) / seed (KIR) | load1 |
|---|---|---|---|---|---|---|---|---|
| posix | EQUAL (1,880,213 B out) | 8,804 | 8,344 / 7,976 | 120 / 150 | 110 / 130 | 131 / 132 | 560 / 40 | 90 |
| kstring | EQUAL (1,131,989 B) | 14,053 | 10,740 / 11,168 | 140 / 200 | 130 / 190 | 64 / 62 | 450 / 30 | 90 |
| case | EQUAL (7,357,492 B) | 33,741 | 47,927 / 36,241 | 560 / 520 | 530 / 500 | 127 / 128 | 4,080 / 50 | 89 |
| sha2 (30 KB) | EQUAL (81,158 B) | 12,094 | 13,627 / 9,985 | 60 / 40 | 40 / 30 | 103 / 59 | 530 / 30 | 88 |

Rebased on R4's WIP HEAD (seed 6ccfcf24, scale 8, load 117-121), all 4 guests are EQUAL again. The seed's code is
larger because R4 inlines string-code-point-at (posix 8,328 B, kstring 12,488 B, case 36,857 B, sha2 10,073 B). Run
times are the same as above within noise.

Other runs (all equal):

- **Scale 1** (load 148): posix, kstring and case EQUAL.
- **Scale 20** (load 94-97): kstring EQUAL (2.8 MB out), case EQUAL (10.2 MB). Posix trapped `:vector-table-exhausted`
  on BOTH sides at the same point, with identical output up to the trap. Before the vector-take fix, the seed trapped
  earlier.
- **sha2 on 356 KB**: both trap on the vector table (KEXE_VECTORS 4,194,304). The output prefixes are equal. Stage-0
  answered 585 lines and the seed 2,243 lines (3.8x), so the seed's code mints fewer vectors.

Seed compile-kir peak RSS is 69-70 MB for every guest, which is the loader's reserved arenas. Stage-0's is 100-250 MB.

Where the seed is slower: kstring (1.43x run, 1.46x cpu). The KIR library loops in generated code where stage-0 calls the
loader's C operations `string_find_byte` and `string_index_of_from`. This is fixable with an RT call per builtin (see the
requests below).

## 4. The rest: per-function scan of the big guests' KIR and the exact missing shapes

`seed/tests/kir/slice.py scan` cuts each of the 10 big-guest KIRs (build/seed-kir/big, from
scripts/selfhost-wall/guests) into the call closure of every function. Each closure is compiled with compile-kir.
`slice.py frontier` then keeps the refused functions whose callees all compile, so each refusal there is the
function's OWN shape. It also reads the form at the reported byte.

| guest | big-compiler module | KIR bytes | functions | compile | frontier |
|---|---|---|---|---|---|
| case | kotoba.string.case | 33,649 | 14 | 12 | 1 |
| cc | kotoba.compiler.nbb.compile-cache | 136,558 | 325 | 173 | 45 |
| codec | kotoba.value.codec | 64,811 | 200 | 58 | 34 |
| di | kotoba.kir.definition-identity | 145,748 | 412 | 200 | 46 |
| ds_guest_w | desugar pass (generated guest) | 633,680 | 1,002 | 40 | 88 |
| oa | kotoba.compiler.nbb.output-admission | 165,346 | 400 | 184 | 65 |
| oat | kotoba.compiler.nbb.output-attestation | 122,898 | 304 | 166 | 36 |
| ri | kotoba.artifact.runtime-identity | 42,351 | 89 | 8 | 22 |
| vc | kotoba.compiler.nbb.verdict-cache (+ kotoba.lang.edn) | 205,395 | 481 | 217 | 75 |
| vx | kotoba.compiler.validate-expr | 173,320 | 172 | 11 | 25 |
| **total** (shared modules counted per guest) | | | **3,399** | **1,069 (31.4%)** | **437** |

The two `case` refusals and every guest's `main` are the wrapper's capability call (wire 41 `:io/read`), not module
code.

The frontier shapes, by function count. These are the exact KIR shapes the seed backend lacks:

| shape (first refusal of the function itself) | frontier fns | example | owner |
|---|---|---|---|
| `:document` as a parameter, result or local type, and the `document-*` ops (keyword 353, null 332, count 248, kind 240, vector 207, vector-conj 191, map 149, ...) | 170 | `[:document :document] -> [:result :document :document]` (runtime-identity) | 12-kirread could lower these as a KIR library on `:vector-i64` (stage-0's machine_ir lowers `:document` onto pairs/vectors too; the loader has no document op), or a TY in 21-check |
| `[:ref R]`, a record by reference through `:schemas` (`:form/r` 59, `:fe/env` 22, `:vx/r` 8, `:form/rd` 8, `:fe/err`/`:fe/dr`/`:fe/drs`) | 100 | `[[:ref :form/r]] -> :string` | 21-check: resolve `[:ref :kw]` to the record registered under that name, registered BEFORE its fields (`:form/r` is recursive: `[:kids [:list [:ref :form/r]]]`) |
| `[:list [:ref R]]` | 29 | `[] -> [:list [:ref :form/r]]` | 21-check (R3 lists hold i64 / pair handles: the item type must admit a record) |
| `:bytes` as a parameter, result or local type (R0: only as a cap argument/result) | 60 | `[:string :string :bytes] -> :i64` | 21-check TY-BYTES admission |
| `string-from-utf8` | 33 | `(string-from-utf8 (bytes-from-vector-i64 out))` (kotoba.bytes/hex) | new head -> RT `string_from_utf8` (loader ABI v11 slot exists) |
| capability calls wire 3 `hash/sha256`, 33 `:env/read`, 34 `:fs/browse`, 41 `:io/read` | 17 | | 21-check E2115 table + grants |
| f64/f32 | 7 | value codec | out of the seed's scope until a float rung |
| more than 5 parameters (E2108) | 7 | `kotoba_module__8__23` | SIR/41-a64gen calling convention (R4) |
| vector literal over 64 items (E2116) | 6 | SHA tables, `(vector-new -1 -1 ...)` | 12-kirread can split the literal into `vector-conj` chains |
| record schema with a `:bytes` field (E2128) | 6 | `[:record ..Found [[:hit :bool] [:data :bytes]]]` | follows `:bytes` |
| `document-edn-print` | 2 | | follows `:document` |

Every one of these is a shape stage-0's own native backend lowers onto the same C-loader ABI (pairs, vectors, strings,
caps). None needs a new runtime representation, so N2 is a lowering gap, not a ceiling.

## 5. Order of work that would flip the verdict

Ranked by frontier functions unblocked per unit of work:

1. `[:ref R]` + `[:list [:ref R]]` in 21-check (129). This is what form_count, validate-expr and desugar need.
2. `:document` as a 12-kirread library on `:vector-i64` (170). This is in the KIR reader's own scope, so no new SIR.
3. `:bytes` as a general type + `string-from-utf8` (93).
4. Caps 3/33/34/41 and more than 5 parameters (24).

Then rerun `slice.py scan` on the 10 guests and merge.sh on form_count / vx / ds_guest_w. The verdict flips at >= 95%
compile with 0 DIFF.

## 6. Reproduce

```
SEED_BUILD=build/seed-kir3t zsh scripts/seed/build.sh 1; zsh scripts/seed/build.sh 2   # seed-0 = R3 seed cbae36dc
python3 seed/tests/kir/merge/gen-inputs.py build/m 8
for g in posix_path:posix kstring:kstring case:case; do
  SEED_BUILD=$PWD/build/seed-kir3t MERGE_W=$PWD/build/m MERGE_RUNS=5 zsh seed/tests/kir/merge.sh \
    seed/tests/kir/merge/${g%%:*}.cljk build/m/${g#*:}.in ${g#*:}; done
SEED_BUILD=$PWD/build/seed-kir3t zsh seed/tests/kir/census.sh
python3 seed/tests/kir/slice.py scan build/seed-kir/big/vx.kir vx.tsv '<seed compile-kir command>'
python3 seed/tests/kir/slice.py frontier build/seed-kir/big/vx.kir vx.tsv
```

Open risks:

- Every timing was taken on a loaded host. Rerun quietly before quoting.
- The census's KIRs come from the stable stage-0 at build/native-image/amu-native. A rebuilt stage-0 may emit new
  shapes.
- The scan counts compile acceptance, not run equality. Run equality is shown only for the four merged modules.
- R4's uncommitted sources (21-check, 30-lower, 41-a64gen) were not part of this build. 12-kirread was built on HEAD, so
  it must be re-gated once R4 lands.

## 7. Integration plan (KIR5): the seed backend as the backend of the big route

Goal: `compile --target aarch64-macos` of the project route keeps stage-0's frontend (HIR -> KIR) and replaces
`kotoba.native.aarch64/emit-program` (machine_ir + AArch64 emission) with the seed's `compile-kir`.

**Falsification test first (must fail before anything is switched):** `scripts/selfhost-wall/kir-backend-diff.sh` (to
write). For every program stage-0 compiles on the aarch64-macos route (the 315-program census, the 19 Embench ports, the
10 big guests + the merge guests) it runs both backends on the identical sealed `:program` KIR (`ir/native-program kir`,
the bytes the verifier re-emits from) and compares exported results, stdout bytes and traps on the same inputs. The
switch is a **no-go** if any one of these holds:
- (F1) one DIFF;
- (F2) a program that machine_ir compiles and the seed refuses, other than the documented refusals (wire 23 today);
- (F3) a seed-only trap;
- (F4) a fuel-metered program whose fuel accounting differs (kexe-benchmark `contextFuelConsumed`, KIR gate column) where
  the artifact promises the x7 fuel ABI;
- (F5) the seed's fixed point or any rung gate breaking.

Today this is shown only on slices and 75 merge runs, not on whole sealed programs.

What must change in amu-measure:
1. **CLI path**: `src/kotoba/compiler/nbb/aarch64_cli.cljk` passes `aarch64/emit-program` to `native-cli/run!`. Add a
   backend selector (`--native-backend seed|machine-ir`, default machine-ir until F1-F5 pass), whose seed arm writes
   `(pr-str program)` and runs `seed compile-kir` under the C loader (a packaged seed binary + tools/kexe_loader.c, no
   JVM/node). It reads back `:code` and the symbol table in the shape `emit-program` returns. The native image must not
   start a host process at compile time (G5's rule): the seed runs as an in-process loader call or as a separately
   invoked tool. That is one owner decision.
2. **Verifier re-emission check** (`nbb/cli.cljk` compile-native!: "Verification re-emits from this closed program";
   `verify-artifact!`, ADR 0262): the artifact records which backend emitted `:code`
   (`:lowering :runtime-aapcs64-v1` gains a backend id, e.g. `:emitter :seed/<sha256 of the seed binary>`), and the
   verifier re-emits with THAT backend. With machine_ir it would refuse every seed-built artifact (design table, row 50).
   The seed's fixed point makes the emitter hash a stable identity.
3. **ABI facts the artifact asserts**: `:fuel-abi {:mode :hidden-context-x7}`, the value ABI and `kexe-fs-forms/refuse-
   unanswered!` (a scan of `:code` for :fs/app-data tokens) must hold for seed code. The KIR gate already measures equal
   fuel on the 19 ports. The token scan must accept the seed's pieces.
4. **Shapes still outside the seed**: wire 23 (`:entropy/draw`), float arithmetic, compares and parse/print, more than
   16 parameters, 65+ item vectors with non-literal items, record captures in fn literals. The selector falls back to
   machine_ir by name for these (a refusal, never a silent switch) until each has a seed lowering.
5. **Order**: (a) kir-backend-diff.sh with F1-F5, (b) a selector defaulting to machine-ir, plus the verifier's emitter
   field, (c) flip the default for aarch64-macos only, (d) delete machine_ir's aarch64 path only after one release with
   F1-F5 green on CI.
