# js-parity goldens

Artifacts the **JVM route** wrote once, so `test/nbb/js_parity.cljk` can hold
the JVM-free route (`bin/amu compile --target js --jvm-free`, driver
`src/kotoba/compiler/nbb/js_cli.cljk`) to them: the `.mjs` byte for byte, the
`.manifest.edn` / `.provenance.edn` sidecars as EDN values. They are compiler
OUTPUTS, not authored code; do not edit them by hand. See ADR 0340.

Pin: `io.github.kotoba-lang/kotoba-script` `:git/sha
8a55311bff0785b18e161fba2062fd38ca98868d` (deps.edn), amu `9708f975`
(origin/main on 2026-09-06). If either moves and the emitter's output changes,
regenerate every golden with the commands below (through the resource guard;
each compile takes about a minute) and record the new pin here.

Every golden was produced from the repo root by

    node <superproject>/scripts/resource-guard.mjs run build -- clojure -M:run compile <args>

with `<args>` as follows (`F=test/fixtures/js-parity`):

| golden | `<args>` | covers |
|---|---|---|
| `todo-app.mjs` | `examples/todo-app.kotoba --target js --output $F/todo-app.mjs` | typed values, `:document`, no policy, default fuel (the module's header says it needs neither) |
| `consumer.mjs` | `$F/consumer.kotoba --target js --source-path $F/lib --unpinned --output $F/consumer.mjs` | a `--source-path` linked project: `consumer` requires `parity.util` (`lib/parity/util.kotoba`, one `:string` and one `:i64` export) |
| `capability-fuel.mjs` | `examples/capability.kotoba --target js --policy examples/capability-policy.edn --fuel 4096 --output $F/capability-fuel.mjs` | a capability-bearing module with a `--fuel` override; the module must carry `let fuel=4096;` |

The JVM also wrote `.manifest.json` and `.inputs.edn` beside each; those are
not kept -- the test compares `.manifest.edn` and `.provenance.edn` as values
and the JSON is the same value in a different key order.

## Measured while producing them (2026-09-06)

- `--unpinned` is in the consumer command because the JVM route REFUSES a
  path-resolved multi-module compile without it (`:compile/unpinned-inputs`,
  ADR-2608580000 D5). The nbb route does not: `project-source` accepts
  `--source-path` with or without `--unpinned` and emits the same bytes either
  way. The golden's flags are the JVM's, so both routes are asked the same
  question; the flag-less nbb acceptance is a divergence this slice records
  and does not change.
- The first nbb compile of `consumer` was 281 bytes SHORTER than the JVM's
  (first difference at byte 1195) and its `:build-metadata-sha256` was the
  SHA-256 of `{}`: `js_cli` did not seal the module-graph digest and the
  per-module source digests that `compile-project` puts in the emitted header,
  the manifest and the provenance metadata. Fixed in the same change
  (`project-source/module-graph`), after which all three files are equal.
- `--fuel` is not threaded through `compile-project` on the JVM route
  (`cli.clj`, comment at its `build-metadata` remark), so a project compile's
  fuel comes from the policy's `:budgets` or the emitter default on BOTH routes.
  Mirrored, not fixed, here.
