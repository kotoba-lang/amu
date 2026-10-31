# Native `definition-cids` (JUN-582 / JUN-583 / JUN-584)

Status 2026-10-31 (JUN-584): **in `FULL-MANIFEST`**. The full compiler answers `definition-cids` itself, with
per-definition refusal. Not in `MANIFEST` or `seed/compiler-core.json`: the adopted 18-module core is unchanged (§2).
Earlier status (2026-10-29): candidate, qualified on aarch64-linux, x86_64-linux (CI) and aarch64-macos (JUN-586, §3).

Goal (JUN-579): cljk/edn reader sugar must mint the same Definition CID as pure `.kotoba`. Checking that natively
needs a `definition-cids` command in every Amu host. Semantics: ADR 0300; payload-version 2, dag-cbor, sha2-256.

## 1. What exists vs what is missing

The 2026-10-29 brief said seed/04 does not implement the producer and that nothing sits between checked KIR and 04.
Measured against the source, that is only true of 04 itself. The pipeline *exists* as an unmanifested prototype:

| Stage | Module | State |
|---|---|---|
| frontend (lex/read/names/check) | `10`-`21` (adopted core) | adopted |
| source -> canonical KIR v4 (resolved binders, effect mask, loops -> helpers) | `05-checked-source`, `05-source-loops` | prototype, CI gate `native-checked-source` |
| KIR -> normalized DAG: de Bruijn binder renaming (`k0..`), effect row as keyword set, direct deps, SCC (<=8) + group members | `05-checked-definition`, `05-definition-graph`, `06-definition-groups` | prototype, CI gate `native-checked-definition` |
| DAG-CBOR + SHA-256 + CID | `04-definition-cid` | prototype, frozen-vector gate `native-definition-cid` |
| per-definition objects / incremental build | `07`-`09` | prototype, out of scope here |
| **user-facing command** | `78-full-entry` (`full-definition-cids`), `99-definition-cids-entry` (harness) | in the full compiler since JUN-584 |

So the missing piece was the entry, not the producer. The previous test entries (`dsb-source` in checked-source
gate) were test-only.

### Output and exit codes (ADR 0300, per-definition refusal since JUN-584)
`definition-cids <file.kotoba> [--groups]` prints, in declaration order, one line per definition and then
`SCANNED<TAB><identified>/<total>`. A line is `name<TAB>CID`, or `name<TAB>REFUSED:<marker>` for a definition with no
identity. `--groups` appends `<TAB>group-CID-or-"-"<TAB>member-index` (index `-1` outside a recursive group, and
`-<TAB>-1` on a refused line); the CIDs are identical with or without it. Exit codes: `0` report (also when some or all
lines are refused), `66` no identity could be computed at all, `2` usage.

Per-definition refusal follows the reference `definitions` loop (`src/kotoba/compiler/definition_identity.cljk`,
`format-lines`, `scanned-line`):
- a definition the native bridge cannot express (closure in a loop, loop in a closure, closure in operator position,
  a type the bridge does not carry, ...) is `REFUSED:unbridged-source` (05-checked-source `dsb-source-report`);
- a definition whose effect row names an unregistered wire is `REFUSED:unbridged-effect`;
- a recursive group above the scc-v1 bound (8) is `REFUSED:recursive-group-too-large` for every member (06 `dcs-rows`);
- a definition that calls a refused one is `REFUSED:dependency-unavailable`, transitively, also through a loop helper
  or an inlined def;
- every other definition is identified exactly as in the whole module: a refused definition, its text, loop helpers
  and closures never reach the KIR, and a definition is kept only when nothing it calls is refused. The gate checks
  that the kept CIDs equal those of the same definitions in a module without the refused ones.

Still whole-module (exit 66, empty stdout, a `DSB:*` line on stderr), as on the reference route where the frontend or
the identity layer cannot answer at all: lexer/reader/name/check errors (`DSB:SOURCE`), computed defs that are not
literals, templates/specializations and unexpected FN kinds (`DSB:BRIDGE`), an unregistered wire no definition carries
(`DSB:EFFECT`), and producer failures (`DSB:IDENTITY`: the fresh KIR check, the canonical codec, internal invariants).

Differences from the reference report that remain:
- `unbridged-source` is a native-only marker: the reference lambda-lifts closures and has no such bridge, so those
  definitions have a CID there (§ local closures). No CID parity is claimed for them.
- A module the frontend rejects exits 66 here; the reference reports the check failure itself.
- No `UNAVAILABLE` line, no `:order`/`:entries` map; the text lines are the contract. Nothing is printed on stderr for a
  refused line.
- The reference route was not executed for this change (no JVM/nbb run); parity is with its source.
- The legacy `DCP1 6 2` + `name cid group index` rows (format 0) still refuse the whole module; they exist in 06 for the
  older test gates only.

### Which identity this is (for JUN-587)
Native CIDs are payload-version 2, dag-cbor, sha2-256, **profile-version 6 / desugar-contract-version 2**, with
s-expression bodies using de Bruijn-style `k0..` binders, effect row as keyword set and direct dependencies by CID
(recursive groups via `kotoba.definition/group`). The frozen vectors in `lang/code-identity-vectors.edn` (and
`seed/tests/definition-cid-vectors.json`) are **profile-version 4 / desugar 1** with KIR `{:op :const ...}` bodies. A
native source-derived CID can therefore never equal a frozen-vector CID; the vectors qualify the codec (04) only. Any
cljk/edn-vs-`.kotoba` comparison must be made between two profile-6 reports, both from the same route.

### Local closures (JUN-588 item B1, owner decision 2026-10-29: native-only form)
A let-bound or value-held `(fn [x ..] body)` is accepted by the bridge (05-checked-source) and sealed by 05-checked-definition
as `(fn [kN ..] body)`: the head is the symbol `fn`, parameters are renamed by the same never-resetting left-to-right
counter as `let` binders (before the body), the scope is restored afterwards. A captured outer local is the OUTER binder's
`k` name (a binder reference, not a source name); a top-level definition referenced in the body is a direct dependency by
CID. Renaming the lambda parameter, the let name or the definition does not move the CID; changing the body, or which
binder is captured, does. No core module (20/21/30) and not 05-source-loops changed (the loop/closure guard lives in the bridge): the frontend already checked closures.

This is **a candidate native-only identity, NOT compatible with the reference, and no parity is claimed** (not with the
reference route, not with the 2026-09-08 CIDs, not for JUN-587 corpus pairs). Measured 2026-10-29 on the JVM reference
(local measurement only; kotoba-sema a3303527, osaho e20c9aff): the reference LAMBDA-LIFTS a closure
(`run = (let [g (pair 1 0)] (__kotoba_invoke$arity1 g n))` plus `__kotoba_lambda_1_arity1` and a module-wide dispatcher) and the
module lambda counter leaks into the CID: the identical `run` source gets a different CID when another closure precedes it
in the module. It is stable under renaming and `(app (lam ..) n)` equals the `let`/`fn` spelling there. The native CID is
position-independent and differs from the reference's. The reference alpha-normalizer (osaho
`kotoba.kir.alpha-normalization`, amu `definition_identity.cljk`) has no `fn` binder either (five binders: params, `let`,
`result-match-of`, `variant-match`, `option-match`). Which closure identity is right (lambda-lifted reference vs a
position-independent form) is an owner decision that must precede any closure parity claim. Natively `app`/`lam`/`ref` are
still refused (item A1), so that pair cannot be compared. Data: JUN-588 comments; measurement files
`jun588-b1-reference-measurement*` in the shared session notes.

Observation (pinned in the gate, not an equivalence claim): `(let [g (fn [x] (+ x 1))] (g n))` and the hand-inlined
`(+ n 1)` get DIFFERENT CIDs natively (`bafyreighx...` vs `bafyreids3...`); a closure keeps its own identity.

Still refused fail-closed (exit 66, empty stdout, named `DSB:*`): a closure inside a `loop` body, `loop`/`recur` inside a
closure, a closure in operator position `((fn ..) a)`, closures through interfaces (`:fn` parameter/result types), any
closure parameter whose checked type is not `:i64` (the source syntax has no annotation; only hinted callbacks have
others), nesting deeper than 7 closures. Mutants (closure head spelling, unbound parameter) are detected by the gate.

## 2. Manifest decision (ADR 0370)
JUN-584 (2026-10-31): 04, 05-definition-graph, 05-checked-definition, 06, 05-checked-source, 05-source-loops, 07, 08
and 09 are in `FULL-MANIFEST` (58 modules), right after `90-drv`; `78-full-entry` dispatches `definition-cids`.
`seed/MANIFEST` and `seed/compiler-core.json` (the adopted 18-module core) are **unchanged**: none of the promoted
modules is a core module, so there is no new core identity and no new adoption receipt. The core round's checks were
run against the grown compiler instead (Mac G1=G2=G3 of the unchanged 18 core reproduces the current receipt; CDCI
pins recomputed; see the PR).

- Self-rebuild fixed point of the grown closure: Mac arm64 F1 = F2 = F3 (`check-aiueos-user-macos-native.py`, run by
  `repin-derived-pins.py`).
- `seed/DEFINITION-CIDS-MANIFEST` (`CORE-STATIC-MANIFEST` minus `99-entry` + the definition layer +
  `99-definition-cids-entry`) stays as the gate's smaller harness for mutants; the gate requires the full compiler and
  the harness to print the same bytes.

## 3. Evidence (what was actually run)
- aarch64-linux, **native** in podman (`python:3.12-slim`, arm64 host), compiler
  `seed/bootstrap/aarch64-linux-static-root.elf`:
  `python3 -I scripts/seed/check-definition-cids-native.py --compiler ... --output ...` -> `PASS_NATIVE_DEFINITION_CIDS`
  (69 native calls). Controls: CIDs for const/leaf/caller/dependency-edit/self/cycle2/cycle8 equal the independent
  oracle image; rename and reordering preserve CIDs; dependency edit changes caller CID; unbound name and unbalanced
  source exit 66 with empty stdout; `--groups` keeps CIDs and adds group/member columns; declaration order is preserved; usage errors exit 2; an encoder mutant is refused by its own validator; closure controls (hand-authored oracle payloads for closure/capture/dependency/nested/two-capture, rename invariance, body and captured-binder sensitivity, five closure refusals, two closure mutants); `check` still works through the
  new entry.
- macOS arm64 (JUN-586, 2026-10-29, Apple M1 Max, main 6b99bf63, Mac root `amu-full-root.macho` db4bec67,
  `diagnostic-candidate`): both gates take a Darwin branch (`scripts/seed/macos_native_image.py`): the Mac root compiles
  to `aarch64-macos`, `extract-native` takes `main`, the Mac packager wraps it in `fs2-cli-stdio-general`, a copy is
  ad-hoc signed; FD 3 is the file root and file arguments are basenames (KOTOBA-169). On the Mac, main's result is the
  exit code (Linux prints `:result N` under `KEXE_STRUCTURED_REPORT`), so the codec gate compares exit codes there.
  - `check-definition-cid-native.py` -> `PASS_NATIVE_DEFINITION_CID_CODEC` (10 frozen vectors decoded and constructed,
    26 refusal controls, boundary/encoder self-checks, 7 mutants detected; 55 calls).
  - `check-definition-cids-native.py` -> `PASS_NATIVE_DEFINITION_CIDS` (the same 64 calls as on Linux).
  - F1 = F2: the Mac gate rebuilt the full compiler from the same source (F1 = F2 container `48c1d8f3…`; F2 is the
    checked-in root's bytes). Images built by F2 are byte-identical to those built by the root (5 unsigned images),
    and all observations are identical (64 + 55 calls).
  - Three hosts: for the same 6b99bf63 modules, all 60 non-build calls (exit code and stdout SHA-256, i.e. every
    printed CID) equal the Linux CI artifacts of run 40856855461 on aarch64 and x86_64. This is the gate's own corpus,
    not the JUN-579 surface corpus (JUN-587).
  - CI: both gates run in `mac-selfhost-aiueos.yml` (`mac-root`, macos-15) against the job's F2 compiler.
- x86_64: not run locally (no x86 host). CI job `native-definition-cids` (ubuntu-latest, `bin/amu-linux-x86_64`) passed
  for the PR #1673 version of this gate (legacy row format); the ADR 0300 format change is verified on x86 only by its own CI run.
- Whether the existing x86 `bin/amu-linux-x86_64` has `definition-cids`: it contains the string `extract-native` but no
  `definition-cids` (`grep -a`), and `seed/90-drv`/`78-full-entry` have no such command. Conclusion from source and
  string evidence: it does not. Could not execute it to confirm.

## 4. Remaining (JUN-583/584/585/586)
- Mac: done for this gate (JUN-586); the Mac root stays `diagnostic-candidate`, not a release qualification.
- aarch64-linux / x86_64-linux / Mac: the shipped full compilers carry `definition-cids` since JUN-584.
- per-definition refusal: done natively (JUN-584, §1); the reference route was not executed against it.
- surface-equivalence corpus
  (`lang/surface-equivalence-corpus.edn` is not present in the local kotoba-lang checkout) and the parity gate (JUN-587).
