# The selfhost acceptance gate (JUN-242 part 3)

The standard is the Linear document "合格判定と品質基準（Kotoba / amu selfhost /
Kotoba spec / Lisp machine）2026-10-21" (project P-JUN-5). This page says how
the gate measures it. The gate is a command-line program, not a CI workflow:
an itonami node (kotoba-lang/tsukasa ledger, placed by murakumo) or a person's
machine runs it and keeps the verdict file. Nothing here depends on a
particular runner.

## Run it

```
npm ci --include=dev            # once: the pinned nbb engine (package-lock.json)
node node_modules/nbb/cli.js scripts/gate/run.cljk \
  --repo <amu checkout> --base <ref> --head <ref> \
  [--kotoba-lang ~/github/kotoba-lang/kotoba-lang] [--kotoba-lang-ref 4d4d188b...] \
  [--work DIR] [--out DIR/verdict.edn] [--cache DIR] [--jobs N]
```

Exit status: 0 the head passes the ratchet, 1 it does not, 2 the run could
not complete. Every non-zero status is a fail.

A consumer repository (any kotoba-lang library with `src/`) is judged by a
pinned amu:

```
node node_modules/nbb/cli.js scripts/gate/run.cljk \
  --repo <library checkout> --base <ref> --head <ref> \
  --amu <amu checkout> --amu-ref <amu commit>
```

In consumer mode the gates are G0, G1 and G2 over the library's own modules.
They are overlaid on the amu farm: each library file replaces its namespace
and that namespace's twin files. S1, S2 and S5 belong to the amu product and
are recorded as NOT-CLAIMED.

`scripts/gate/report_status.cljk --verdict <verdict.edn> --repo OWNER/NAME`
posts the verdict as a GitHub commit status on the head (`gh api`, with the
runner's credentials; `--dry-run` prints the request). It is separate from
the gate, and the gate never talks to GitHub.

`node node_modules/nbb/cli.js scripts/gate/test_gate.cljk` checks the pure
halves: the ratchet rules and the scanners.

## What each gate measures

Both sides are detached worktrees. In amu mode each side is measured with
its own product compiler (`bin/amu` of that commit).

| gate | measurement | per-unit verdicts |
| --- | --- | --- |
| G0 form | for each `.cljk` / `.kotoba` file under `src/` in `git diff base...head` (fixtures elsewhere, such as the deliberately unreadable `seed/tests/lexread/neg/*.kotoba`, are not modules); a file the refactor reader cannot read counts `unreadable`; the `:rc-no-arm` findings of `amu refactor to-kotoba <file> --check`, the `#?(:kotoba nil` forms, and the host literals inside `:kotoba` arms (regex, `#js`, char, `js/`, `.method`, `java.` / `goog.`, `"node:`) | PASS when all three are 0, otherwise REFUSED. NOT-CLAIMED when the file is absent on that side. |
| G1 language | `bin/amu check <module> --source-path <farm> --policy lang/selfhost-compiler-grant.edn --jvm-free` for every module of the compiler-closure farm | PASS when the output is `{:format :kotoba.check/v1 ...}` with `:profile-version 6`. REFUSED(code) with the diagnostic code and line. UNMEASURED when the oracle gave no answer. |
| G2 identity | `bin/amu definition-cids <module> --jvm-free`, run twice, for each G1 PASS module | PASS when both runs succeed with identical output. REFUSED(nondeterministic) when they differ. BLOCKED(g1) when the module did not pass G1. |
| S1 lineage | `seed/tools/bootstrap.kotoba --upto r6n` (seed/README.md, "Seed lineage bootstrap"), then a check that `build/seed-boot/r6n/seed-1.bin` has the sha256 recorded in `seed/rungs/r6n.record` | PASS, or REFUSED(lineage / no-loader / seed-hash / no-record) |
| S2 selfbuild scan | `seed/tools/selfbuild.kotoba` (JUN-202; seed/README.md, "Selfbuild scan (gate S2)") in the side's tree, with the lock `seed/selfbuild/integration-lock.edn` (or `deps-lock.edn` when the head has no integration lock; `--lock` overrides, and both sides use the same path), kotoba-lang at the pinned commit and the S1 seed. Its `selfbuild.edn` gives one verdict per module. | PASS (`:ok`, an object was written), REFUSED(Exxxx), BLOCKED (`:blocked-by`), UNMEASURED (`:trap`) |
| S5 ratchet | the PRODUCT inventory of the deleted `scripts/selfhost-wall/bootstrap-boundary.sh`, transcribed rule for rule in `scripts/gate/boundary.cljk` (on 7c8c8a4b it gives the same counts as the shell original: 4 launchers, 17 nbb entries, 16 audit rows, 56 computed, 11 host-token files, 65 union, 146 `#?(:kotoba nil` forms). It also counts the `native-gates` allowlist of `scripts/check-workflows.cljk` and the tracked `.sh` files. The audit-document rows (16) are reported in `:info` and are not ratcheted, so that adding or restoring that document does not count as PRODUCT growth. | one number per metric |

The farm is the selfbuild tool's (`build/selfbuild/r6`), and G1 checks the
same files. The farm is generated, not checked in. The tool extracts every
`src` root at its lock commit with `git restore`, reading from
`~/github/kotoba-lang/<repo>` or from `~/.gitlibs` after the dependency
prefetch. It takes the closure of `src/kotoba/compiler/nbb/*_cli.cljk`,
applies the project loader's twin rule against kotoba-lang `lang/compat`, and
orders the modules dependency-first. The gate compiles the tools once per run
from its own checkout: the adopted C loader, then `bootstrap.kotoba` and
`selfbuild.kotoba` built by the committed adopted seed. It then runs them
against each side's tree. Consumer mode builds the same farm once from the
pinned amu, so it also needs a macOS arm64 node.

## The ratchet

Most modules are REFUSED today, so the head is judged against the base. The
head is not required to reach 100%. The gate FAILs when any of these holds:

- G1 or G2: the PASS count drops, or a module flips from PASS to anything else (including a module that disappears).
- G2: any head module has nondeterministic CIDs.
- G0: a changed `src/` file gains a `:rc-no-arm`, a `#?(:kotoba nil`, a host literal in a `:kotoba` arm, or becomes unreadable. A new file starts from zero.
- S1: the lineage flips from PASS.
- S2: the OK count drops. Individual flips are listed but do not fail the gate.
- S5: any metric grows.
- Any requested gate is UNMEASURED on either side, or is missing from either side's measurement (fail closed). Examples are a missing `bin/amu`, policy, seed, C compiler or nbb engine, or a node that is not aarch64-macos for S1/S2.

S1, S2 and the farm that G1 and G2 check run the aarch64-macos seed and
loader, so every run needs a macOS arm64 node with `cc` and `git`. Any other
node records these gates as UNMEASURED, and that is a FAIL.

## The verdict file

`<out>` holds EDN (`:format :kotoba.selfhost-gate/v1`), with JSON at
`<out>.json` and the markdown table at `<out>.md`. It records:

- `:verdict` (PASS / FAIL) and `:failures`.
- `:gates`: one ratchet result per gate, with the base and head tallies, flips and gains.
- `:change`: the repo, base, head, merge base and changed files.
- `:pins`: for each side, the subject commit, the oracle (`:amu-commit`, `:deps-lock` sha256 and `:lock/digest`, `:nbb-pin`, node version), the policy (kotoba-lang commit, file sha256, `lang/compat` digest), the farm (`farm.txt` and `order.txt` sha256, module count) and the host. Under `:seed` it records the rung, seed sha256, record sha256, lineage loader sha256 and adopted seed sha256.
- `:gate`: the gate's own commit and the sha256 of its three source files.
- `:measurements`: every per-module verdict of both sides.

`--cache DIR` reuses a side's measurement only when every pin in its key is
the same: subject commit, amu commit, kotoba-lang commit, policy sha256,
gates, rung and gate sources.

## Follow-ups

- kotoba-lang is pinned to main `4d4d188b`, the commit the standard was written against. JUN-202's parity run used `965c5f5b` (branch `agent/wall2-project-twin`, with more compat twins), so its seed OK count (97/269) is not comparable with the gate's.
- Making the gate a required check is an owner decision. It needs a branch protection rule or ruleset that requires the `selfhost-gate` commit status.
