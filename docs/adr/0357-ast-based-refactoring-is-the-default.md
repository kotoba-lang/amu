# ADR 0357 — AST-based refactoring is the default; text edits are the exception

- Date: 2026-10-01
- Status: Accepted (owner decision, 2026-10-01).
- Related: `docs/selfhost-priority.md` (rules 1, 2, 6), ADR 0354 (walls are
  fixed in the language, not worked around in source), ADR 0356,
  `docs/selfhost-frontend-decomposition-20260930.md`,
  `scripts/selfhost-split/` (3e187fb0), `scripts/selfhost-codemod/` (050928ec).
- Companion in `kotoba-lang/kotoba-lang`:
  `docs/adr/ADR-ast-based-refactoring-is-the-default.md` (`kotoba refactor`).

## Context

Moving the compiler's own sources onto the Kotoba route (`amu check`) means
rewriting hundreds of call sites in a 22k-line namespace (`frontend.cljk`)
and cutting it into modules. Two experiments settled how to do that:

- `scripts/selfhost-split/` builds the reference graph from a concrete syntax
  tree with exact offsets, partitions it, extracts modules and proves with
  `roundtrip.py` that every form is kept byte-identical exactly once.
- `scripts/selfhost-codemod/` is an offset-preserving lossless parser plus
  rules a-f (destructuring lambdas, `reject!`, dynamic vars, keyword
  callbacks, `let`, `Form` loops). On `frontend.cljk` it found 238 patterns for
  rule (a) alone, and the rewrite is mechanical for all but a measured
  remainder that needs a person.

Both beat the alternatives (sed/regex, an LLM rewriting files by hand) on the
properties that matter here: comments, `#?` reader conditionals and layout are
preserved, a rule's reach is countable before it runs, the result is checkable
against the original, and independent modules can be refactored in parallel
without merge conflicts in one giant file. But they are scripts in a scratch
directory, depend on Python for the analysis half, and nothing in the product
points at them. A contributor's default tool is still `sed` and an editor.

## Decision

1. **Refactoring is AST-based by default.** A change that is a rule applied to
   many sites, a rename across a namespace, a module split, or a
   dialect-porting rewrite (the selfhost wall work) is made with
   `amu refactor`, not by editing text. A hand text edit is the exception and
   is for a change that is not a pattern (a one-off logic fix, a new
   function). When a hand edit turns out to repeat, it becomes a rule.
2. **The tool is part of the product.** `amu refactor` ships in the `amu`
   CLI; `kotoba refactor` in the `kotoba` CLI delegates to the same
   implementation and the same rules (companion ADR). No Python and no JVM on
   the CLI path.
3. **Rules are data plus Kotoba functions**, versioned and CID-identified
   (below), not scripts.
4. **Every apply is planned, guarded and verified** (safety contract below).

## Rationale

- *Lossless.* The parser keeps every byte (whitespace, comments, `#?`/`#?@`
  branches) with offsets; a rewrite replaces spans and nothing else. A pass
  that parses and prints back must reproduce the file exactly
  (`print(parse(s)) == s`); that identity is checked on every input before
  any rule runs.
- *Differential verification.* Behaviour preservation is checked by running
  the project's test set before and after and comparing per-test outcomes,
  not by trusting the rewrite.
- *Rules as data.* A rule is inspectable, countable (`plan`), diffable,
  cacheable by CID, and attributable in provenance.
- *Parallel by module.* The graph and split commands cut a namespace into
  modules along the SCC/closure partition so different rules and different
  people touch different files.
- *Selfhost.* See "Relation to selfhost".

## CLI surface

`amu refactor <subcommand>`; `kotoba refactor` accepts the identical
subcommands and options. All stdout is one EDN map with
`:format :kotoba.refactor/v1` and `:subcommand`. Failures are
`:kotoba.cli-error/v1` reports on stderr with a stable `:code` and the
existing exit mapping (65 refusal, 64 usage), as in the other `amu` commands.

| command | effect |
|---|---|
| `refactor list-rules [--rules dir]` | the rules in the loaded rule set: name, version, CID, description, dialect scope |
| `refactor plan <rule> <paths...> [--rules dir] [--lower-accessor ...]` | dry run. Writes nothing. Reports `:actionable` and `:human` counts per file and per rule, the rule CID, and a unified diff of what `apply` would write. |
| `refactor apply <rule> <paths...> [--check] [--rules dir]` | runs the plan again, then writes. With `--check` it writes nothing and exits non-zero if any actionable site remains (CI form: "the tree is already refactored"). |
| `refactor graph <path>` | EDN dependency graph of the top-level forms of a namespace: nodes, weighted edges, SCCs, dynamic vars (defined in / read by / bound by), per reader-conditional feature |
| `refactor split <path> --partition p.edn --out dir` | writes the modules and the facade named by the partition into `dir` and verifies the round trip (every form byte-identical, exactly once). Never writes into the source tree unless `--out` points there and the tree is clean. |
| `refactor verify [--tests <set>] [--before <rev> or <dir>] ...` | differential: run the project's test set on the baseline and on the working tree, compare per-test outcomes, report `:same`, `:fixed`, `:regressed`, `:flaky`. Exit 65 on any `:regressed`. |

Refusal codes (stable): `:refactor/unknown-rule`, `:refactor/rule-invalid`,
`:refactor/dirty-tree`, `:refactor/input-not-parsing`,
`:refactor/roundtrip-failed`, `:refactor/no-plan`,
`:refactor/plan-stale`, `:refactor/guard-failed`,
`:refactor/partition-invalid`, `:refactor/cycle-cut`,
`:refactor/verify-regressed`, `:refactor/nondeterministic-baseline`,
`:refactor/path-escapes-root`, `:refactor/over-limit`.

## Rule format

A rule set is a directory (default `lang/refactor-rules/`, or `--rules`):

```
rules/
  manifest.edn            ; {:kotoba.refactor.rules/version 1 :rules [...]}
  a-destructuring-lambda.edn
  a-destructuring-lambda.cljk   ; the Kotoba functions the EDN names
```

A rule is an EDN map:

```clojure
{:kotoba.refactor.rule/version 1
 :name        :selfhost/destructuring-lambda          ; stable identifier
 :description "map/reduce/... callbacks with destructuring params -> plain params + let"
 :dialects    #{:cljk}                                ; which sources it may touch
 :pattern     {:head #{map mapv filter reduce ...}    ; structural match on the CST
               :where :a/destructuring-callback?}     ; Kotoba fn name, node -> bool
 :rewrite     :a/rewrite-callback                     ; Kotoba fn: node ctx -> [span new-text] | :human
 :classify    :a/classify                             ; node ctx -> :actionable | :human
 :guard       :a/guard                                ; applicability, below
 :order       {:after #{} :before #{:selfhost/let-flatten}}
 :reader-conditional {:arms #{:default :kotoba} :policy :shared-and-default-only}}
```

- **pattern** selects nodes; it is purely structural and runs on the
  offset-preserving CST (including every reader-conditional arm).
- **rewrite** returns spans to replace (offset range, new text). It never
  prints the whole file; untouched bytes are copied.
- **classify** is the actionable/human split. `:actionable` sites are
  rewritten; `:human` sites are listed with file, line and a reason and are
  left untouched. `plan` reports both counts; a site is never silently
  skipped. The human count is a first-class output because it is the work
  that remains.
- **guard** is the applicability guard: a predicate over the site and its
  context (is this inside the host arm of a definition that already has a
  hand port; is the callee shadowed by a local; is the namespace one the rule
  declares it may rewrite). A site failing the guard counts as `:not-applicable`
  and is reported, not rewritten.
- **order** makes the sequence of rules in a full run explicit (the
  codemod's `a,b,d,e,f` then `c`).
- Functions named by the EDN are ordinary Kotoba functions in the rule set's
  `.cljk`, written in the Kotoba-route subset so the rule set itself passes
  `amu check`.

Rule sets are loaded with the same bounded EDN reader as other lang EDN
(size, depth and node limits); an unknown key or a missing function is
`:refactor/rule-invalid`, never ignored.

## Safety contract

1. **plan before apply.** `apply` computes the plan itself and refuses
   (`:refactor/no-plan`) when invoked with `--plan-cid X` that does not match;
   interactive use may omit it, since `apply` always prints the plan summary
   it is about to execute. The plan is a pure function of
   (rule CID, input bytes), so plan and apply agree or `apply` refuses with
   `:refactor/plan-stale`.
2. **Clean tree.** `apply` and `split --out <source tree>` refuse on a dirty
   working tree for the target paths (`:refactor/dirty-tree`), so the diff is
   exactly the refactor and `git checkout` is the undo. The check reads
   VCS state through the existing capability layer; with no VCS, `--allow-no-vcs`
   is explicit.
3. **Parsing input.** Every input file must parse and round-trip
   (`print(parse(s)) == s`) before rules run (`:refactor/input-not-parsing`,
   `:refactor/roundtrip-failed`). Every output file must parse again after the
   rewrite; otherwise nothing is written (all-or-nothing across paths).
4. **No dependency on the thing being refactored.** The tool does not require
   the sources it edits to compile; it needs only that they parse.
5. **Bounded.** File size uses the 8 MiB admission bound (ADR 0356); node
   counts, rule applications per file and plan size have declared limits and
   refuse with `:refactor/over-limit`.
6. **verify compares outcomes.** `verify` runs the same test set on baseline
   and after, per test; a test that passed before and does not pass after is
   `:regressed` and fails the command. A baseline whose outcomes differ between
   two baseline runs is `:refactor/nondeterministic-baseline`. Rules that are
   host-behaviour-preserving by construction (everything in the selfhost
   codemod) require `verify` green before the commit.
7. **Paths.** Paths are resolved under the project root; escapes are refused.
   `apply` writes only the files in the plan.
8. **Host behaviour unchanged.** Existing commands and their outputs are
   unchanged; `refactor` is a new subcommand group.

## Rule storage, versioning, identity

- Rule sets live in `lang/refactor-rules/` (built-in) and any `--rules`
  directory. `manifest.edn` lists rules with their versions.
- A rule's identity is the CID of its canonical form: the EDN with the
  named Kotoba functions replaced by their definition CIDs
  (`amu definition-cids`). The rule set CID is the CID of the sorted list of
  rule CIDs. Both are recorded in `plan`/`apply` output and in the commit
  trailer or provenance record of a refactor (`:refactor/rule-set-cid`,
  `:refactor/input-cid`, `:refactor/output-cid`), consistent with
  `lang/code-identity.edn` and the CID-pinned package lock.
- A change to pattern, rewrite, classify or guard changes the CID; the
  `:version` is a human-readable label and is bumped on any behaviour change.
  A rule is never edited in place under the same CID.

## Relation to selfhost

`docs/selfhost-priority.md` rule 2 labels an nbb or JVM build a bootstrap
reference. The first implementation of `refactor` therefore runs on nbb
(the existing `*_cli.cljk` route) and is labelled bootstrap wherever its
numbers appear. The design requires that it can stop being bootstrap:

- The parser, rule engine, differ and every rule are `.cljk` written in the
  Kotoba-route subset (`#?(:kotoba ...)` bodies where needed, `Form` as the
  dynamic tree). When they pass `amu check` on the project route, `amu`
  builds the refactoring tool itself, and a selfhost-built `amu` runs
  `amu refactor` with no nbb.
- The refactoring tool is also its own first user: the rules that remove the
  selfhost walls (destructuring lambdas, `Form` loops) are applied to the
  tool's own sources, so the tool moves onto the Kotoba route by its own
  means. Walls found in the tool are fixed in the language (rule 1), not
  routed around.
- No JVM, GraalVM or Python fallback is added for `refactor` (rule 6). A
  missing capability is a refusal with its reason.
- `verify` runs the project's test set through `amu test` (one instance per
  test), not through a JVM test runner.

## Migration plan for the Python analysis

| step | content | done when |
|---|---|---|
| 1 | Port `cljparse.py` + `sourcegraph.py` to a shared nbb module on the codemod's lossless parser (one parser, not two); `crosscheck-reader.cljs` becomes a unit test against `kotoba.sema/read-forms` | graph EDN from nbb equals the Python `graph.edn` on `frontend.cljk` (byte-equal after canonical ordering) |
| 2 | Port `analyze.py graph|partition`, `extract.py`, `roundtrip.py` to `refactor graph` / `split` | `partition.edn` and the extracted modules equal the Python output; round trip proven in-tool |
| 3 | Port `verify.py` and `consumers.py` to `refactor verify` and a `retarget-facade-consumers` rule | per-test outcome table equals the Python table on the frontend split |
| 4 | Move the codemod rules a-f into `lang/refactor-rules/` in the format above; `scripts/selfhost-codemod/codemod.sh` becomes a thin call to `amu refactor apply` | `diff-suite.sh` passes through the CLI |
| 5 | Delete the Python files and the shell wrappers; keep the README as a pointer. `names-frontend.json`-style labels move into the partition EDN | no `.py` under `scripts/selfhost-*` |
| 6 | Make the parser, engine and rules pass `amu check` on the project route | `amu refactor` listed as selfhost-buildable in the scoreboard |

Steps 1-3 are gated on differential equality with the Python output while
both exist; the Python is removed only after that (never both silently
diverging).

## Making it the default (documentation)

`AGENTS.md` and `docs/selfhost-priority.md` state: for rule-shaped changes
use `amu refactor` (plan, apply, verify), and say why a hand edit was used
otherwise. The Kotoba-route wall work in the selfhost scoreboard is done with
rules wherever a pattern recurs.

## Consequences

- A new rule needs a pattern, a rewrite, a classify and a guard, which is more
  than a regex; in exchange its reach is known before it runs.
- The parser must track the reader (`#?`, `#?@`, tagged literals,
  `^:meta`); it is cross-checked against `kotoba.sema/read-forms` in CI and
  refuses (never guesses) on a construct it cannot place.
- Until step 6, `refactor` is a bootstrap-reference tool and is labelled so.
- Existing commands are unchanged; `refactor` adds usage lines to `bin/amu`
  and to `lang/cli.edn` in `kotoba-lang`.

## Not decided here

The rule language beyond Kotoba functions (a pattern DSL) and automatic rule
synthesis from before/after pairs. Those need a measured need first.

## Implementation (2026-10-01)

`amu refactor` exists: `list-rules`, `plan`, `apply [--check]`, `graph`,
`partition`, `split`, `verify`, in nbb with no Python or JVM
(`src/kotoba/compiler/refactor/*.cljk`, `refactor_cli.cljk`,
`nbb/refactor_cli.cljk`, routed from `bin/amu`). The lossless parser, the rule
engine and rules a-f are the codemod prototype ported to `.cljk` (the scanner is
character based, no regex objects); the call graph, partition and extraction are
the Python analysis ported onto the same parser, so one parser serves both.
Differences kept on purpose from the prototypes: `apply` re-parses every
rewritten file before writing any, writes through a temporary file and a
rename, `split` checks the round trip before writing, and `--check` and
`verify` answer exit 1 when they find something. The helper comment label in
generated code reads `amu-refactor:` (was `selfhost-codemod:`). Evidence is in
`docs/refactoring.md`. The prototypes under `scripts/` are superseded.
