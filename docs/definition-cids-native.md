# Native `definition-cids` (JUN-582 / JUN-583 / JUN-584)

Status 2026-10-29: **candidate**, qualified on aarch64-linux only. Not in `MANIFEST`, `FULL-MANIFEST` or
`seed/compiler-core.json`.

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
| **user-facing command** | - | **missing** (this change) |

So the missing piece was the entry, not the producer. The previous test entries (`dsb-source` in checked-source
gate) were test-only.

### Output and exit codes (ADR 0300, aligned 2026-10-29)
`definition-cids <file.kotoba> [--groups]` prints, in declaration order, one `name<TAB>CID` line per definition and then
`SCANNED<TAB>n/n`. `--groups` appends `<TAB>group-CID-or-"-"<TAB>member-index` (index `-1` outside a recursive group);
the CIDs are identical with or without it. Exit codes: `0` report, `66` no identity could be computed, `2` usage.

Differences from the nbb report that remain:
- The native producer refuses the **whole module** before printing (any unresolved/unsupported definition), so there is
  no per-definition `REFUSED:<marker>` line, `SCANNED` is always `n/n`, and a refusal prints nothing on stdout, a `DSB:*`
  diagnostic on stderr, and exits 66. The nbb route lists refused definitions and exits 0; reproducing that needs a
  per-definition refusal in 05/06 (not done).
- No `UNAVAILABLE` line, no `:order`/`:entries` map; the text lines are the contract.
- The legacy `DCP1 6 2` + `name cid group index` rows (format 0) still exist in 06 for the older test gates only.

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
`seed/compiler-core.json` (18 modules) and `MANIFEST`/`FULL-MANIFEST` are **unchanged**. A successor core needs
self-rebuild evidence; none exists for 04-06 (+ bridge), so they are not folded in. Instead:

- `seed/DEFINITION-CIDS-MANIFEST` = `CORE-STATIC-MANIFEST` minus `99-entry` + 04, 05-definition-graph,
  05-checked-definition, 06, 05-checked-source, 05-source-loops + `99-definition-cids-entry`.
- `99-definition-cids-entry` dispatches `definition-cids <file>` and otherwise calls the unchanged `drv-main`.
- Promotion to FULL-MANIFEST is blocked until: Mac `arena-scope` support (JUN-546), a self-rebuild fixed point of
  the grown closure, and the output-format decision above.

## 3. Evidence (what was actually run)
- aarch64-linux, **native** in podman (`python:3.12-slim`, arm64 host), compiler
  `seed/bootstrap/aarch64-linux-static-root.elf`:
  `python3 -I scripts/seed/check-definition-cids-native.py --compiler ... --output ...` -> `PASS_NATIVE_DEFINITION_CIDS`
  (69 native calls). Controls: CIDs for const/leaf/caller/dependency-edit/self/cycle2/cycle8 equal the independent
  oracle image; rename and reordering preserve CIDs; dependency edit changes caller CID; unbound name and unbalanced
  source exit 66 with empty stdout; `--groups` keeps CIDs and adds group/member columns; declaration order is preserved; usage errors exit 2; an encoder mutant is refused by its own validator; closure controls (hand-authored oracle payloads for closure/capture/dependency/nested/two-capture, rename invariance, body and captured-binder sensitivity, five closure refusals, two closure mutants); `check` still works through the
  new entry.
- macOS arm64 Mach-O root (`amu-full-root.macho`, run on this Mac with FD 3 as the file root): the candidate
  **compiles, packages and signs**, `check` works, but `definition-cids` stops with the packager's deliberate
  `seed: arena-scope unsupported (Mac runtime, JUN-546)` (exit 70). 05/06 use `arena-scope`. Fails closed.
- x86_64: not run locally (no x86 host). CI job `native-definition-cids` (ubuntu-latest, `bin/amu-linux-x86_64`) passed
  for the PR #1673 version of this gate (legacy row format); the ADR 0300 format change is verified on x86 only by its own CI run.
- Whether the existing x86 `bin/amu-linux-x86_64` has `definition-cids`: it contains the string `extract-native` but no
  `definition-cids` (`grep -a`), and `seed/90-drv`/`78-full-entry` have no such command. Conclusion from source and
  string evidence: it does not. Could not execute it to confirm.

## 4. Remaining (JUN-583/584/585/586)
- Mac: JUN-546 `arena-scope` in the Mac runtime packager (blocks JUN-586).
- aarch64-linux in the shipped root: the candidate image builds with the root, but the production closure is unchanged.
- per-definition refusal markers (nbb parity); surface-equivalence corpus
  (`lang/surface-equivalence-corpus.edn` is not present in the local kotoba-lang checkout) and the parity gate (JUN-587).
