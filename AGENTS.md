# Agent rules

## Selfhost is the top priority

- The Amu compiler must become a native executable produced by Amu, with no
  JVM, GraalVM or Node.js needed to build it. This outranks features, new
  targets and benchmark publication. Details: `docs/selfhost-priority.md`.
- Only a selfhost-built compiler is selfhost evidence. GraalVM Native Image,
  JVM and Node/nbb builds are bootstrap references; label their numbers so.
- Do not add a JVM, GraalVM or Node fallback to make a selfhost stage pass.
  Unreachable files stay on the scoreboard as refused, with the reason.
- Compiler benchmarks (Embench etc.) are published as selfhost results only
  when taken with a selfhost-built compiler on a quiet host.

## Language semantics are target-independent

- wasm32 is one build target of the Amu native compiler, not the definition of
  the language. Do not cap, narrow or defer a language or stdlib feature
  because wasm32 cannot lower it yet. Specify the semantics, check them
  against the KIR interpreter, and let each target either lower the feature or
  refuse it by name (exit 65, recorded in `lang/surface-status.edn`).
- A limit is kept only if it bounds a resource or protects an invariant. Remove
  a limit that only records what one backend could do. Details:
  `docs/adr/0354-language-semantics-are-target-independent.md`.
- This never relaxes the shared safety pipeline, fail-closed behaviour, or the
  no-JVM/GraalVM/Node-fallback rules.

## Q9 compiler routes must be JVM-free

- Q9 callers use `bin/amu check ... --jvm-free` and
  `bin/amu compile ... --target <target> --jvm-free`. Write the target: an
  omitted `--target` means the host's native target (ADR 0351), so a
  browser / Worker / WASI build names `wasm32-browser` / `wasm32-wasi`.
- `--jvm-free` must never invoke `java`, `javac`, `clojure`, `clj`,
  `resolveWithJvm`, a Clojure main namespace or another JVM launcher.
- Missing/stale dependency locks, unsupported commands/targets and project
  linker gaps fail closed. Do not silently remove `--source-path`, ignore a
  module lock or fall back to the JVM to make a component compile.
- New Q9 compiler/test routes use nbb/CLJS, Node, native or Wasm. Existing JVM
  suites are compatibility diagnostics and are not Q9 acceptance evidence.
- Preserve tests that shadow forbidden JVM executables and verify that no
  marker was written on both unsupported-route and lock-failure paths.

## Refactor with `amu refactor`, not by hand

- Mechanical source changes (porting a form shape, renaming, splitting a
  namespace, moving a definition, any edit of the same shape in more than one
  place) go through the AST-based CLI, never through hand text edits, sed,
  regex or ad-hoc scripts. Use `amu refactor` (`kotoba refactor` in
  `kotoba-lang`; same subcommands, same EDN, format `:kotoba.refactor/v1`).
  It runs on nbb/Kotoba only: no Python, no JVM (fail closed).
- The loop is `plan -> apply --check -> verify`:
  1. `amu refactor list-rules`, then `amu refactor plan <rule> <paths>`
     (dry run: actionable / human counts and a unified diff). `:human`
     findings are not applied; they are the hand work that remains.
  2. `amu refactor apply <rule> <paths> --check`, then `apply` without
     `--check`. Rules are offset-preserving: comments, whitespace and every
     untouched byte survive, and the host (JVM/nbb) arm is kept byte-for-byte
     as `:default` of a one-form `#?(:kotoba NEW :default OLD)`.
  3. `amu refactor verify`: the differential. It runs the project's test set
     before and after and compares per-test outcomes. Any test whose outcome
     changed, or any new refusal, blocks the change.
- Hand text edits are only for a change no rule covers. Then either write the
  rule (below) or record in the commit message why this change is one-off.
  If you made the same hand edit twice, it was a rule.
- To add a rule: implement a rule map `{:id :find}` in the refactor rule
  library (`scripts/selfhost-codemod/src` today, being folded into the
  `*_cli.cljk` nbb sources), where `:find` takes `{:src :nodes :opts}` and
  returns findings `{:status :auto|:human :reason :edits}`. Add a fixture and a
  test (host equivalence by evaluation where the rule claims it), register it
  so `list-rules` shows it, and give refusals a stable code. A rule that cannot
  prove host equivalence reports `:human`, not `:auto`.
- The commit message carries the evidence: the rule id, the `plan` counts
  (actionable / human / ported), and the `verify` result (tests compared,
  changed outcomes = 0). A refactor commit without them is incomplete.
- Differential discipline: never "fix" a test or loosen a check to make
  `verify` pass; compare before and after on the same test set and the same
  revision otherwise. Failures that existed before stay failures, and are
  listed, not hidden.
- Parallelising a large module: `amu refactor graph <path>` (dependency graph
  EDN, SCCs, dynamic vars) -> choose or generate a partition ->
  `amu refactor split <path> --partition p.edn --out dir` (byte-identical
  round trip, facade keeps the old namespace) -> one agent per module, each
  using the loop above on its own module -> `verify` on the recombined whole.
  Agents commit path-specific and never touch another module's files.
- Until the CLI subcommands land in your checkout, the same rules run from
  `scripts/selfhost-codemod/codemod.sh` and `scripts/selfhost-split/`; use
  them with this same loop and note it in the commit.
