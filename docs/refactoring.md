# Refactoring with `amu refactor` (default workflow)

Decision recorded 2026-10-01. AST-based refactoring is the default way to change
Amu / Kotoba compiler sources. Hand text edits, sed and regex are the exception.
`kotoba refactor` in `kotoba-lang` has the same subcommands and output.

The CLI path is nbb/Kotoba only: no Python, no JVM. It fails closed
(`docs/selfhost-priority.md`). Existing commands are unchanged.

## Subcommands

All output is EDN with `:format :kotoba.refactor/v1`. Refusals carry a stable
`:code`, like the other CLIs.

| command | what |
|---|---|
| `refactor list-rules` | rule ids, one-line description, host effect |
| `refactor plan <rules> <paths>` | dry run: counts (patterns / ported / actionable / auto / human) and a unified diff (`--no-diff`, `--patch-out FILE`) |
| `refactor apply <rules> <paths> [--check] [--out FILE]` | `--check` applies in memory, re-parses, writes nothing, exit 1 while changes are pending; without it, writes (temp file + rename, only after every file re-parsed) |
| `refactor graph <path> [--summary] [--out FILE]` | dependency graph EDN: nodes, weighted edges, SCCs, dynamic vars |
| `refactor partition <path> [--modules N] [--driver FORM] [--names FILE] [--out FILE]` | pass-ownership partition (an acyclic module graph), the input of `split` |
| `refactor split <path> --partition p.edn --out dir [--ns NAME]` | extract modules plus a facade; byte-identical round trip is checked before anything is written |
| `refactor verify --runner run-tests.cljk --classpath CP [--base-first DIR] [--candidate-first DIR] [--stack-size N]` | differential: run the project's test set twice (baseline root first, candidate root first) and compare per-test outcomes |

`<rules>` is `a,b,d,e,f`, one rule id or name, or `all` (= `a,b,d,e,f`). Rule `c`
(dynamic vars) needs `--target dual|host-env`. Other rule options:
`--include-ported`, `--lower-accessor`, `--regions shared,default,kotoba`,
`--observable-from DIR`, `--max-passes N`. A `<path>` is a file or a directory
(searched for `.cljk` `.cljc` `.clj` `.cljs`).

Exit status: 0 ok; 1 the answer is `:ok false` (`apply --check` pending, `verify`
found differing outcomes); 64 usage; 65 the input is unfit; 74 a write failed.
Refusals are the usual `:kotoba.cli-error/v1` report on stderr; the stable codes
are `:refactor/usage`, `unknown-rule`, `target-required`, `unreadable`,
`parse-error`, `no-paths`, `output-unparsable`, `no-driver`,
`partition-incomplete`, `roundtrip-failed`, `verify-no-result`, `write-failed`
(`kotoba.compiler.refactor-cli` header has the table).

## The loop

1. `list-rules`, then `plan <rule> <paths>`. Read the diff. `:human` findings
   are never applied; they are the remaining hand work.
2. `apply <rule> <paths> --check`, then `apply`.
3. `verify`. Zero changed outcomes and zero new refusals, or the change does not
   land.
4. Commit (path-specific `git add`). The message contains the rule id, the
   `plan` counts and the `verify` summary.

## Why a syntax tree

The parser is lossless with absolute offsets: comments, whitespace and every
untouched byte are preserved, so a rewrite is a list of text edits. Reader
conditionals are structure. A rewrite never replaces host text with Kotoba
text: it is host-equivalent code, or the host text stays byte-for-byte as the
`:default` arm of a one-form `#?(:kotoba NEW :default OLD)`. Edits are atomic per
finding; nested conflicts keep the innermost and re-run to a fixpoint.

## Differential discipline

- `verify` compares the same test set at the same revision, before and after.
- Never change a test or loosen a check to make `verify` pass.
- A failure that existed before stays a failure and is listed, not hidden.
- JVM/nbb behaviour must stay byte-identical; load the module under nbb after
  the change.

## Adding a rule

A rule is a map `{:id :find}`. `:find` receives `{:src :nodes :opts}` and returns
findings `{:status :auto|:human :reason :edits}`; `:edits` are
`{:s :e :text}` (a zero-width edit inserts).

1. Write the rule next to the existing ones in
   `src/kotoba/compiler/refactor/rules/<name>.cljk` (the parser is
   `refactor/cst.cljk`, the edit algebra `refactor/edit.cljk`, the driver
   `refactor/core.cljk`).
2. Add a fixture and a test in `test/kotoba/compiler/refactor_test.cljk`; where
   the rule claims host equivalence, prove it by evaluation (see
   `test/fixtures/refactor/equiv.cljk`).
3. Register it in `refactor/rules.cljk` so `list-rules` shows it; give each
   refusal a stable code.
4. A rule that cannot prove equivalence emits `:human`, never `:auto`.

If you are about to make the same hand edit a second time, write the rule. If
the change is truly one-off, say why in the commit message.

## Parallelising a large module

```
refactor graph  <path>                         # SCCs, cross-module edges, dynamic vars
refactor split  <path> --partition p.edn --out dir
# one agent per module: plan -> apply --check -> verify on that module
refactor verify                                # on the recombined whole
```

Each agent edits only its module and commits path-specific. Cycles reported by
`graph` are opened first, in the partition, not worked around.

## Status of the CLI

`amu refactor` is implemented (nbb, no Python, no JVM): the pure core is
`src/kotoba/compiler/refactor/*.cljk` and `refactor_cli.cljk`, the Node
entrypoint is `src/kotoba/compiler/nbb/refactor_cli.cljk`, routed from
`bin/amu`. Tests: `test/kotoba/compiler/refactor{,_graph,_cli}_test.cljk` (in
`run-tests.cljk`) and `scripts/test-refactor.sh` (through the launcher).

Measured on `kotoba-sema` `frontend.cljk` (22484 lines): `plan a` reports 238
destructuring-lambda patterns, 19 ported, 219 actionable (219 auto, 0 human);
`apply all --out` produces the same bytes as `scripts/selfhost-codemod`
(except the helper comment label); `verify` of the rewritten copy against the
original over kotoba-sema's `run-tests.cljk` compares 620 tests with identical
per-test outcomes (77 failed, 25 errors before and after), and a deliberately
broken helper turns it red (114 differing lines).

`scripts/selfhost-codemod/` and `scripts/selfhost-split/` (Python) are the
prototypes this was ported from. They are superseded: use `amu refactor`.
The Kotoba-route port of the refactor modules themselves is future work (the
entrypoint refuses on the Kotoba route, like `amu test`).
