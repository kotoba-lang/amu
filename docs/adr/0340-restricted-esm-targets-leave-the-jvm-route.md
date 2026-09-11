# ADR 0340 — The restricted-ESM targets leave the JVM route

- Date: 2026-09-06
- Status: Accepted

## Context

`bin/amu` hosts every Wasm, native and EVM target on nbb/Node and refuses
`--jvm-free` only where the JVM genuinely still owns something. `--target js`
and `js-browser` were the exception: they spawned `clojure -M`, and the
superproject's CLAUDE.md table said so in bold (*JVM を起こす*; *新規で選ばない*).

Nothing in code generation needed the JVM. The frontend, admission, KIR
lowering and provenance are the same `.cljc` this route already runs for
`wasm32`. The one JVM-only piece was the emitter: `kotoba-lang/kotoba-script`
was a single `src/kotoba/script.clj`, whose JVM-specific surface turned out to
be three seams — `Character/isLetterOrDigit` + `format "%04x"` in identifier
mangling, `Double.toString` for f64 literals, and Closure Compiler for
verifying the emitted module.

The owner's instruction (2026-09-06) was *kotoba compile で js も対応* as one
leg of moving the script host from nbb to kbb (ADR-2607181900 /
ADR-2609051100 in the superproject): a JVM-free JS artifact is the second
oracle Q9 wants beside the native KEXE, and the host `kbb --backend js` can
instantiate.

## Decision

1. **kotoba-script is `.cljc`** (kotoba-lang/kotoba-script `b1900f5b`). The
   three seams sit behind reader conditionals; `java-double-string` rebuilds
   JDK 19+ `Double.toString` from `Number.prototype.toExponential` (including
   the `4.9E-324` spelling of `MIN_VALUE`); the cljs verifier is `node --check`
   plus a token scan outside string literals for the same forbidden globals,
   properties and import forms, and labels itself `:verifier :token-scan`.
   That repo's `npm run test-nbb` compares nbb `emit` bytes with goldens the
   JVM wrote: identical.
2. **`kotoba.compiler.nbb.js-cli` hosts `--target js` / `js-browser`** and
   `bin/amu` routes those spellings there (`nbbJsTargets`), exactly as
   `evm_cli.cljs` hosts the EVM. It mirrors the `:js-kotoba-v1` branch of
   `compile-source*`: same limits, same manifest, `provenance/attach` on the
   same result shape, four files written (`.mjs`, `.manifest.edn`,
   `.manifest.json`, `.provenance.edn`).
3. **The parity claim is measured by `test/nbb/js_parity.cljk`** with
   `clojure`/`java` hidden from PATH: `runtime/http/route-decide.kotoba`
   compiles to the committed `runtime/http/route-decide.mjs` byte for byte
   (60,092 bytes — that file is the JVM's artifact at the same pin, refreshed
   in this change), `examples/capability.kotoba` runs under Node through a
   supplied grant and is refused without it, and `cljs-browser --jvm-free` is
   refused rather than routed. Measured once more by hand at the same pin:
   the JVM's and nbb's manifest and provenance are equal as EDN values.
4. **`cljs-browser` stays on the JVM route.** It emits ClojureScript source
   text through a different backend; nothing here changes that.

## Consequences

- `scripts/http-service-e2e.cljk`'s drift gate no longer needs a JDK; its
  header comment says so. The committed `route-decide.mjs` moved by one line:
  the previous file was compiled at kotoba-script `69f65b33`, and the emitter
  has since grown `linearValues`, `vectorAlloc` and `stringIndexOf` runtime
  helpers (the first nbb compile "differed" from the old golden at byte
  22,624 for exactly that reason — a pin skew, not a port bug, settled by
  compiling both routes at the new pin).
- The superproject CLAUDE.md table that marks `js` / `js-browser` as *JVM*
  and *新規で選ばない* is superseded for the JVM half; the *default is
  `wasm32-browser`* guidance stands.
- The parity gate widened past `route-decide` (2026-09-06, second slice):
  `test/fixtures/js-parity/` holds three goldens the JVM route wrote once at
  kotoba-script `8a55311b` (README.md there records the exact command per
  golden) -- `todo-app.mjs` (`examples/todo-app.kotoba`: typed values,
  `:document`, no policy, default fuel), `consumer.mjs` (`consumer.kotoba`
  requiring `parity.util` from `lib/` through `--source-path`, so the linked
  project graph is compared, not a single file) and `capability-fuel.mjs`
  (`examples/capability.kotoba` with its policy and `--fuel 4096`; the
  consumer command carries `--unpinned` because the JVM refuses a path-resolved
  project without it, ADR-2608580000 D5, while the nbb route accepts either
  spelling -- recorded, not changed). For each,
  `test/nbb/js_parity.cljk` compiles on the nbb route with the same flags and
  asserts the `.mjs` byte for byte and the `.manifest.edn` / `.provenance.edn`
  sidecars as EDN values, naming the first differing key when they diverge;
  the fuel golden must also carry `let fuel=4096;`. What the earlier golden
  did not cover -- typed-value limits, project linking, the fuel resolution
  order -- is now measured rather than asserted by the driver's docstring.
  The first run of the widened gate was red: the nbb `consumer.mjs` was 281
  bytes shorter than the JVM's (first difference at byte 1,195) and its
  `:build-metadata-sha256` was the SHA-256 of `{}`, because `js-cli` passed
  the CLI's `--fuel` metadata where `compile-project` passes the module-graph
  digest, the per-module source digests and `:admit-linked-synthetics? true`,
  and never merged `:kotoba.artifact/module-graph-digest` /
  `:kotoba.artifact/module-source-digests` into the manifest.
  `project-source/module-graph` now computes the same `:kotoba.module-graph/v1`
  record and `js-cli` seals it the same way; the three files are equal again.
- Not mirrored: the JVM's `.inputs.edn` sidecar (folded into the printed
  result, as the Wasm route does) and hash-map key ORDER inside the manifest
  and provenance text. Both are values; the test compares them as such.
