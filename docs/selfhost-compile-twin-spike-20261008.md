# Compile twin spike: nbb.cli `compile-native!` on the Kotoba route (2026-10-08)

Question: can the product entry nbb.cli reach the Kotoba route as a thin `compile!` twin (the check-driver pattern)
instead of a line-by-line port of its 858 host lines, and what actually blocks it?

## Method

`seed/tests/compile-twin/spike.kotoba` is an entry that runs `compile-native!`'s aarch64 steps with existing Kotoba
modules only: `nbb-io/read-text-file` -> `sema/analyze` -> `effect-row/check` (policy through the new cli-support
readings) -> `kir/lower` -> `native-program` (host `kotoba.kir/native-program` without the recursive-schema clause) ->
`native.aarch64/emit-program`, and writes `:code`/`:exports`. It is compiled and linked by seed r6m `8d3338e1` against
the seed17 frontend objects (`build/seed17/front0`, kotoba-native `752cdf2`, kotoba-sema `c2e1343`), and run with the
native image's budgets (`scripts/seed/launcher/build.sh`; the default 64 Ki vector table traps immediately).
`seed/tests/compile-twin/run.sh` compares it with `bin/amu compile --target aarch64-macos` (BOOTSTRAP-REFERENCE, host
lock: kotoba-native `33418cd`) on the 372 programs of the parity corpus dirs present in this tree (no Embench ports).

## Result (measured)

| class | n | meaning |
|---|---:|---|
| SAME | 256 | code bytes and export entries equal (2 of them differ only in the printed order of `:exports`) |
| BOTH-REFUSE | 60 | both refuse |
| GUEST-FAILS | 49 | the Kotoba route refuses what the host compiles |
| CODE-DIFF | 4 | code bytes differ |
| GUEST-ONLY | 3 | the Kotoba route emits code the host refuses |

Of the 309 programs the host compiles, the Kotoba route emits identical native code for 256 (83%).

### The gaps, by cause

1. **Oracle interpreter (41 of 49 GUEST-FAILS).** `kotoba.kir/lower` (the guest twin) refuses
   `kotoba.kir/oracle-unavailable` when a pure entry uses an operation family `kotoba.kir.interp` has not ported. A
   spike variant that falls back to `kotoba.kir.lowering/lower-base` (the structural module, no oracle) emits code
   equal to the host's for all 41: the emitter is not the problem, the sealed `:value` is.
2. **kgraph capacity (8 of 49).** The frontend itself traps `:budget/cells :arena :kgraph`: the loader's
   `KEXE_KGRAPH_CAPACITY` is a fixed 4096 (tools/kexe_loader_decisions.kotoba). A resource decision, not a port.
3. **Native admission gate (3 GUEST-ONLY).** The host refuses `record-assoc` / typed closure results before emitting
   (`kotoba.kir/only-native-word-typed-features?`, `unqualified-native-feature`); the guest kir twin has no such gate,
   so the spike emits code for programs native does not qualify. The twin needs this gate.
4. **Counted self-recur loops (4 CODE-DIFF).** Every differing program has a counted self-recursive loop; the guest
   code carries the bulk fuel prepay entry (`cmp`, `b.lt` cold, ...) where the host's does not. Both kotoba-native
   versions contain the plan (`counted-self-recur-plans`); the guest's Kotoba arm
   (`counted-self-recur-plans-of-gmir`, d2c0f1f) applies it and the host lock's host arm does not. A same-source host
   comparison was not possible: the host arm of `752cdf2` does not load on nbb (`Integer/toString`,
   machine_ir.cljk:2397). To be settled in kotoba-native.
5. **Printed map order.** The host prints a map of more than eight entries in hash order, so a byte comparison of the
   kexe text is not meaningful; compare entries (and the seal, which is over canonical bytes).

## What this settles for the twin

- The route exists end to end: frontend, lowering, the aarch64 emitter and the cli-support readings link into one
  6.8 MB image and compile real programs with no node/JVM/nbb.
- The twin is wiring plus four named pieces, in order of reach: the native admission gate (correctness: never emit
  what native does not qualify), the oracle interpreter families (41 programs), the loop fuel divergence
  (kotoba-native), the kgraph capacity decision (8 programs).
- Artifact assembly (target profile, compatibility, seal, provenance, verifier) takes `:document` on the Kotoba
  route, not Form: the twin converts with `frontend.base/form->document` / `form/from-document`, and compares
  artifacts by entries and seal, not by text.

Out of scope of the spike: the artifact map, seal, provenance, verifier, caches, `--source-path`, x86-64.

## Addendum: the native admission gate (same day)

`src/kotoba/compiler/native_admission.kotoba` is osaho's `only-native-word-typed-features?` (with its type predicates,
operation tables and provider contracts) over `:form/r`, clause for clause in the host's order. The spike now refuses a
v3 module the gate rejects before anything is emitted, as `compile-native!` does: `42-rec-assoc` and
`canonical-bytes-closure-result` move from GUEST-ONLY to BOTH-REFUSE. The third GUEST-ONLY, `local-uleb128-130`, is
refused by the host's VERIFIER ("runtime KIR module shape rejected"), not the gate: it belongs to the artifact/verify
step, which the spike does not run yet.

`seed/tests/native-admission/run.sh` checks it against the host gate on every function (alone in its module), every body
sub-form (nbb.cli's probe) and mutations of every call (arity -1/+1, a broken type descriptor or first element in each
vector operand, each integer operand at -1/0/63/64/255/256, an unknown member keyword) of the 174 v3 programs: 28,856
cases, 3,897 of them refused by the host, all agree (24 mutations the host gate itself throws on are left out). Four
deliberately wrong gates (shift bound 64, cap id bound 256, `let` binders not checked, document-map arity not checked)
each FAIL it.

## Addendum: the counted self-recur divergence (same day)

The four CODE-DIFF programs were a host bug in kotoba-mir, not in kotoba-native: `counted-self-recur-plan` tested the
decrement constant with `(= 1 (:mir/value one))`, and on nbb a literal from the reader is a BigInt, so `(= 1 1n)` refused
every source-written countdown (the JVM and the Kotoba arm admit it). kotoba-mir #72 (merged as 4bd4d583) compares through
`host-number`; amu's lock now pins it. Measured with `bin/amu compile`: the four programs equal the Kotoba route's code;
the 254 programs that already agreed are byte-identical to their pre-change host code.

## Addendum: artifact assembly, seal, provenance and verifier (2026-10-09)

`src/kotoba/compiler/native_artifact.kotoba` (`kotoba.compiler.native-artifact`) is the rest of `compile-native!` on the
Kotoba route, for the later nbb.cli `compile!` twin: the fuel policy (`fuel-policy!` / `native-fuel!`, metered vs
unmetered by `unmetered-default-targets`, oracle budget 100000, ceiling `kotoba.kir/max-fuel`), the native admission /
entryless / UEFI gates, `effect-row/check`, `kir/lower`, `native-program` with the recursive-schema clause, the target
profile and compatibility descriptor (from `kotoba.kir.target` / `kotoba.kir.compatibility`), the whole
`:kotoba.kexe/v1` map (`:lowering :fuel-abi :context-abi :limits :code :program :exports :effects :compatibility
:kir-sha256 :value`, the `:oracle` inconclusive record), the seal, `definition-identity/describe` (catalog from
`kotoba.sema/capability-id->name`), `provenance/attach`, and the verifier step. The spike now calls it and writes the
`.kexe`, its `.provenance.edn` and the verifier's message. `compare_artifact.py` compares host and guest semantically:
the `:sha256` seals first, then both maps key by key, then the provenance records the same way.

The artifact is a Form, not a `:document` (a document is bounded to 32 items, depth 8), sealed with
`kotoba.verifier.seal/sha256-form`. The verifier step is the `kotoba.verifier` twin's
`verify-artifact-structure-message` followed by the two steps the twin refuses by name, now done for real: the code
region is re-emitted with `kotoba.native.aarch64/emit-program` and compared, and the entry is re-executed with
`kotoba.kir/execute` under `:limits :fuel` and judged with the host's messages.

### Measured (full corpus, 372 programs, one build with every fix)

Build: seed r6m `8d3338e1`, the seed17 front0 objects, osaho 23c329e `kir/interp.cljk` (dependents rebuilt), and the
`kotoba.kir.target` fix below; guests run with `kexe-loader-1mi` and `KEXE_KGRAPH=1048576`. Host: `bin/amu compile
--target aarch64-macos` of this worktree (BOOTSTRAP-REFERENCE). Rows: `workspaces/claude/artifact-verify/full/result.tsv`.

| class | n | meaning |
|---|---:|---|
| BOTH-ACCEPT | 291 | both write the artifact and both verifiers accept it |
| GUEST-VERIFY-REFUSES | 14 | identical artifact; the twin's verifier refuses what the host's accepts |
| GUEST-FAILS | 4 | the host compiles, the Kotoba route refuses before an artifact |
| BOTH-VERIFY-REFUSE | 3 | the host verifier refuses; the twin refuses with the same message |
| BOTH-REFUSE | 60 | both refuse before the verifier |

- **Seal:** of the 305 programs where both sides wrote an artifact, the `:sha256` seal is SAME for 305; no artifact key
  differs. 149 of the 291 accepted artifacts seal a value, re-derived by the twin's oracle re-run; one carries the
  `:oracle :inconclusive` record.
- **Provenance:** SAME for 305 of 305 (seal and every key, `:definitions` included: the Kotoba
  `definition-identity/describe` with the sema catalog gives the host's CIDs).
- **Verifier:** the host verifier refuses 3 programs (`local-uleb128-130` "runtime KIR module shape rejected",
  `computed-record-map` "runtime KIR record projection rejected", `composed_surface_kit` "native artifact oracle
  evaluation rejected"); the twin refuses the same 3 with the same messages. The twin is stricter than the host on 14
  (ADR 0024: stricter is sound, looser is not; none is looser): 7 `:abort` programs ("native artifact contains an
  unsupported effect": the twin admits only `:state` beside capability calls, the host also admits `:abort`), 5
  "runtime KIR function shape rejected" (`higher_order`, `indexed_map`, `closure_bytes_result`, `collections_12`,
  `multi_map_12`) and 2 "runtime KIR operation rejected" (`collections/vector`, `dual-backend/11-minmax`). These are gaps of the `kotoba.verifier` twin's program verification, not of the assembly.
  **Decision (owner, 2026-10-09): the twin's verifier keeps this strictness.** The 14 stay refused on the Kotoba route;
  the verifier twin is not loosened to the host's admission.
- **GUEST-FAILS:** 3 `kotoba.kir/oracle-unavailable` (interpreter families not ported: `recursive-tree`,
  `ex_info_round_trip`, `typed-closure-parameters`) and 1 resource trap (`lazy-sequence`: the frontend exhausts the
  vector table).

### Named differences that remain (also in the module header)

1. **`kotoba.kir.target` is unreadable on this route as shipped.** Its Kotoba reading parses the profile table with
   `document-edn-read`, and the r6m seed's document reader does not skip `;` comments and miscounts a newline inside a
   nested map (`{:a 1 ;; x y\n :b 2}` counts 3 entries, `{:a {:x 1}\n :b {:y 2\n :z 3}\n :c 3}` counts 4): every
   `(profile t)` answers nil, the compatibility descriptor traps, and the verifier twin would refuse every artifact
   ("native target profile does not match target identity"). Measured: the spike built against the unpatched module
   traps on `examples/fuel.kotoba`. The measurement above uses the same table with comments removed and whitespace
   collapsed to one line (`workspaces/claude/artifact-verify/target-profiles-text.patch`, scratch only, same data).
   **Decided (owner, 2026-10-09): the table text.** osaho commit 9387ddf (branch `claude/target-profiles-text`, from
   `agent/dual-runtime-port-D`) writes `profiles-text` as one line without comments, equal to the host literal (27
   targets); a seed r6m probe reads both checked profiles as maps and 27 entries (54 with the old text).
2. **kexe-fs-forms is not called.** `refuse-unanswered!`'s Kotoba reading takes the code as a `:document` (it cannot
   hold a code vector) and `kexe-fs-forms/forms` traps on this route (`form-table-read` assocs onto `document-null`).
   Every form of the table is answered by the loader today, so the host check refuses nothing.
3. **Verifier message order:** the host checks the code region before fuel/limits/ABI/compatibility, the composition
   after them (the twin exports no prefix-only entry). Not exercised by the corpus.
4. **Oracle re-run outside the ported interpreter:** `kotoba.kir/execute`'s `interpreter-unavailable` is refused by its
   own message, never accepted. Not exercised by the corpus (lowering refuses the same modules first).
5. **Metered compiles:** the Kotoba `kir/lower` takes no oracle budget, so a metered compile whose declared fuel is not
   100000 is refused by name. Not exercised (the corpus compiles unmetered aarch64-macos).
6. **One emitter, chosen not injected:** a fn literal may not abort and the seed refuses a `try` around an injected
   function, so the module calls `kotoba.native.aarch64/emit-program` itself and refuses other ISAs by name; an emitter
   abort during re-derivation propagates instead of "runtime KIR cannot be safely lowered".
7. **Not on this route:** `--backend seed` (`:emitter`), the stage / verdict / compile caches, packaging (`:binary`),
   and the `.publication.edn` output set.

## Addendum: nbb.cli and nbb.aarch64-cli compile from source (2026-10-09, compile-cli)

The spike is gone from the measured path: the product entries themselves now have a Kotoba reading and the seed builds
the entry from source.

### Structure

- `src/kotoba/compiler/nbb/cli.cljk`: the host reading is the same program (every top-level form read under `:cljs` and
  under `:clj` is equal before and after, measured with edamame; the host forms now sit in the `:default` branch
  `(do ...)` of one `#?(:kotoba <run!> :default (do ...))`, whose `:kotoba` branch is the twin's `run!` (its helpers are
  `#?(:kotoba ...)` forms before it), the requires in one `#?@(:kotoba [...] :default [...])`, the export list in one
  `#?(:kotoba [run!] :default [...])`). The Kotoba reading sees only the twin: `run!` over `[:list :string]`,
  answering the stdout text. `compile <source> --target aarch64-macos [--output] [--policy] [--fuel] [--source-path ...]`
  is `compile-uncached!` over `kotoba.compiler.native-artifact/compile-native` plus provenance, and writes the `.kexe`,
  `.provenance.edn` and `.publication.edn` (the Kotoba `output-set/serialize` over the bytes written) in one
  `nbb-io/write-set!`. `--source-path` links through the project twins as check-driver's Kotoba reading does.
- Refused by name (usage, 64, unless noted): every command but `compile` (`extract-native` included); every target but
  aarch64-macos (an unknown name and the x86-64 names with the host entry's own messages); `--artifact object|image`
  (packaging; an unknown kind is the host's `:artifact-target`, 70); `--backend`; `--module-lock`; `--package-lock`;
  `worker` (in aarch64-cli's `main`). There is no compile / stage / verdict cache on this route.
- `src/kotoba/compiler/nbb/aarch64_cli.cljk`: a Kotoba `main` in check-cli's style (`worker` refused, else cli's `run!`,
  try/catch), as the `:kotoba` branch of `#?(:kotoba <main> :default (do ...host entry...))`; the host entry is the same
  program (same check). Neither file adds a `#?(:kotoba nil ...)` form.
- `src/kotoba/compiler/nbb/cli_support.cljk`: three Kotoba-only exports for an entry's error contract: `error-phase`
  (`:phase` of the caught refusal's ex-info data, `:internal` without one), `exit-code` (the host table entry for entry)
  and `refusal-text` (a reduced `:kotoba.cli-error/v1` report: format, ok, error, message).
- Size: the linked entry is 8,275,577 bytes (8,275,177 before the nbb.io path fix); the seed's `extract-native` reads the image as one bytes value, at most
  8 MiB (`KEXE_BYTES_VALUE_LIMIT`, ADR 0362), so the headroom is 113,031 bytes. A first build that reached the project
  twins through `check-driver` (whose Kotoba reading also requires package-lock and compile-cache) linked
  8,848,289 bytes and could not be extracted; cli.cljk calls the twins directly instead.

### Build (seed r6m `8d3338e1`, no spike)

The seed17 farm (`build/seed17/inputs/scan`) with osaho 464cb04's `kotoba/kir/interp.cljk` and `kotoba/kir/target.cljk`,
this tree's `bounded_edn`, `cli_support`, `refactor/rules`, `cli`, `aarch64_cli`, `native_admission`, `native_artifact`;
the objects of every module that transitively requires a changed one deleted and recompiled dependency-first
(`scan.zsh` with the AGENT-ENV compile budgets; workspace `workspaces/claude/compile-twin-cli`).

| module | before (this tree's host-only cli.cljk) | after |
|---|---|---|
| `kotoba.compiler.nbb.cli` | refused: `E6004 qualified call is not an admitted exported import: compile-cache/resolve-stage!` | OK, 200,361 B object |
| `kotoba.compiler.nbb.aarch64-cli` | BLOCKED (requires nbb.cli) | OK, 252,824 B object (with `--entry`) |
| `kotoba.compiler.native-admission` / `native-artifact` (not in the 138) | - | OK |

Selfbuild picture (the 138 modules of `inputs/scan/order.txt`): **122 / 138** compile (was 120). The 16 left are all
`kotoba.compiler.refactor.*`: `cst` (E2003 top-level `declare`), `edit`, `diff`, `verify` (E1005 `#` reader syntax),
`prelude` (E6009 exports nothing), and 11 BLOCKED behind them.

The entry links (`link`), extracts (`extract-native --symbol main`) and runs with the native image's budgets
(`kexe-loader-1mi`, `KEXE_KGRAPH=1048576`).

### Differential (full corpus, 372 programs)

`seed/tests/compile-cli/run.sh <objects> <work> [list]` builds the entry as above and runs every program of the
compile-twin corpus through `bin/amu compile --target aarch64-macos` (BOOTSTRAP-REFERENCE, `KOTOBA_VERDICT_CACHE=off`)
and through the guest with the same command line: exit code, then for both-accept `compare_artifact.py` (kexe and
provenance: seal, then key by key) and `compare_cli.py` (the stdout answer as data with the output directory
normalised, and the `.publication.edn` markers).

| class | n | detail |
|---|---:|---|
| BOTH-ACCEPT | 291 | seal SAME 291, artifact keys differing 0, provenance SAME 291 (0 keys), stdout answer SAME 291 (0 keys), publication SAME-SHAPE 289 + SIZE-DIFF 2 |
| BOTH-REFUSE (same exit code) | 62 | 65: 24 `:subset`, 4 `:admission`, 3 `:verify` (same messages as the host verifier); 70: 29 `:target`, 1 `:effect-ceiling`, 1 emitter (host phase `:kir-to-gmir`, guest `:ir`) |
| BOTH-REFUSE, exit code differs | 1 | `examples/w1-effect-named`: host 65 `:admission`; guest 70 `:target`: the Kotoba native admission refuses a module the host gate admits (host `only-native-word-typed-features?` = true on the host HIR); not diagnosed here |
| HOST-ONLY | 18 | 14 verifier strictness (owner decision: kept): 7 `:abort` "unsupported effect", 5 "runtime KIR function shape rejected", 2 "runtime KIR operation rejected"; 3 `kotoba.kir/oracle-unavailable` (`recursive-tree`, `ex_info_round_trip`, `typed-closure-parameters`); 1 `lazy-sequence` (vector table exhausted, exit 120) |
| GUEST-ONLY | 0 | |

The two SIZE-DIFF markers (`recursive-generic`, `recursive-list`): the host prints `:schemas` with the namespaced-map
syntax (`#:app{:cell ...}`), the guest with full keys; the data and the seal are equal. Every publication marker on both
sides describes its own files (sha256 and size of the bytes written, marker digest over its payload).

### Refusals (`seed/tests/compile-cli/refusals.sh`)

26 cases against the host ENTRY (`aarch64_cli.cljk` under nbb with the locked classpath, without bin/amu's routing).
The guest writes no artifact in any case and answers every one with a report. Equal exit code in 16: no command,
`check`, missing / unknown / two x86-64 targets, `--artifact bogus` (70), `--backend seed`, `--fuel abc`, missing
source, wrong extension, and the five path cases (absent source, a directory, an unreadable file, an absent policy:
65 `:decode` "input could not be read"; an absent output directory: 74 `:output`). Different, by design: the guest
refuses by name (64) what the host entry serves or fails on otherwise: `aarch64`, `aarch64-linux` (host 0),
`aarch64-linux-static`, `aarch64-aiueos-kernel-v1` (host 70: packager not loaded), `--artifact object` (host 0),
`worker` (host 0 on empty stdin), `extract-native` of an absent file (host 65), `--module-lock` (host 65) and
`--package-lock` (host 70) with absent locks; `--fuel 5000` is native-artifact's metered-compile difference (65, host 0).

**Unreadable paths (fixed).** nbb.io's Kotoba `read-text-file` READ the path through wire 35, and the loader's READ
raises SIGILL when its `O_RDONLY | O_NOFOLLOW` open fails or the read fails: an absent source, a directory, an
unreadable file and an absent `--policy` all ended the guest with exit 120 and no report (host: 65 `:decode` "input
could not be read"). The Kotoba reading now refuses them first, from the STAT answer (STAT opens the path the same way
and answers "" when that open fails; its fourth field is 1 for a directory), with the host's phase and message. The
host reading is unchanged (same forms under `:cljs` and `:clj`). Before -> after (guest exit): absent 120 -> 65,
directory 120 -> 65, unreadable 120 -> 65, absent policy 120 -> 65; absent output directory 74 -> 74 (already the host's,
from `write-set!`). Still a trap: an invalid UTF-8 file (READ traps; the host answers "input is not valid UTF-8") and a
path outside the loader's scope.

### Named differences of the twin (also in cli.cljk's header)

1. `:verdict-cache` is `{:native-verify :disabled}` (no store on this route): what the host answers with
   `KOTOBA_VERDICT_CACHE=off`; with its store on the host answers `:miss` / `:hit`.
2. Artifact and provenance texts are printed in entry order (the host: hash order, and `#:ns{}` maps), so they are equal
   as data, not as bytes, and the publication marker carries this route's sha256 / size / digest.
3. Refusal reports are reduced (no `:diagnostic`, no `:details`, message not refined); the native admission gate's
   message names no feature; a linked graph's refusal is not attributed to module and line; the frontend's refusal
   phase is the frontend error's own (`subset`, `read`, ...).
4. Everything native-artifact names (kexe-fs-forms not called, metered compiles only at 100000, verifier strictness).

### Bootstrap boundary (`scripts/selfhost-wall/bootstrap-boundary.sh`, before -> after)

Every line that differs from the base (c290f734b):

- nbb entries with no `:kotoba` arm: **7 -> 5** (cli.cljk and aarch64_cli.cljk are now `has-:kotoba-arm` in list 2).
- src files with at least one `:kotoba` arm: 62 -> 64 of 112.

Unchanged: modules with `#?(:kotoba nil ...)` forms or no `:kotoba` arm 50, `#?(:kotoba nil ...)` forms in src 151,
union of PRODUCT src files 58, launchers 4, unguarded host tokens 10 files. (A first cut with a
`#?(:kotoba nil :default (do ...))` host region put both files into list 3b, 50 -> 52; the twin is the `:kotoba` branch
of that conditional instead.) The host modes inside the host branch (caches, worker, x86-64, packaging,
extract-native, `--backend seed`, locks) are refused by name on the Kotoba route and remain debt.
