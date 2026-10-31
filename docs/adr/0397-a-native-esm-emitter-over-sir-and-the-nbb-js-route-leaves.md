# ADR 0397 — A native ES-module emitter over SIR; the nbb js route leaves

- Date: 2026-10-31
- Status: Accepted; §1 implemented (Phase 1, 2026-11-01). §2-§4 open.
- Tracking: Linear JUN-706 (related: JUN-353, JUN-702, JUN-703)

## Context

The owner's instruction (2026-10-31): *amu での js transpile 経路も設計、nbb 経路は外す*.

What exists, measured at origin/main `26833b1` on 2026-10-31:

- `--target js` / `js-browser` compile only on the hosted route.
  `src/kotoba/compiler/nbb/js_cli.cljk` drives `kotoba-lang/kotoba-script`
  (`src/kotoba/script.cljk`, about 3.6k lines of `.cljk`) under nbb (ADR 0340).
  `docs/retirement/hosted-compilers.json` already lists `js_cli.cljk` with
  `"action": "remove"`. The complete native core (`seed/FULL-MANIFEST`) has
  no JavaScript emitter.
- The documented way to write a browser UI in Kotoba is the app contract
  driven by `runtime/dom-driver.mjs`: pure `init`, `view` and `step` over
  `:document` values (`examples/todo-app.kotoba`,
  `examples/approval-queue-app.kotoba`). It is built only through that hosted
  route (`scripts/browser-matrix.cljk`, `compile-web!`,
  `--target js-browser --jvm-free`). So no Kotoba app UI, including the
  itonami dapps that are now required to be written in Kotoba (JUN-702;
  itonami Moji in JUN-703), can be built without nbb.
- The native `wasm32-browser` target (seed/81 and seed/82, JUN-353) works on
  this Mac through `seed/bootstrap/aarch64-macos/amu-full-root.macho` with an
  FD3 directory root. Its output is a program: exports `memory` and
  `start(fuel)`, imports `kotoba:host` `write`, `cap`, `now`, `exit` and
  `input`. It refuses `:document` operations with E7101 ("outside the runtime
  profile"), and the native checker refuses an export whose result is not
  `:i64` (E2104 on `view [state :document] :document`).
- The same `:document` program compiles and runs natively on aarch64-macos
  (`bin/amu run` printed the expected 106 for a map/vector/string probe), so
  the native runtime implements the operations. They are missing from the
  browser profile, not from the compiler. Which runtime sections carry them
  has not been traced yet; that is the first task of §2.
- A native runtime defect was found while doing this: reading a keyword back
  out of a `:document` (`document-keyword-value`) crashes a `bin/amu run`
  program with exit 139. The minimal reproduction is in JUN-706.

## Decision

### 1. One more plain emitter over SIR: `js-browser-static/v1`

Add `seed/81-js-esm.kotoba` and `seed/82-js-esm-rt.kotoba` beside the wasm32
pair, built the same way:

- **Input is SIR**, the runtime profile seed/70-71 admit and seed/75 rules,
  exactly what seed/80 (aarch64) and seed/81 (wasm32) consume. Nothing new is
  added to the frontend, checking or lowering, so the JS route cannot accept a
  program the native routes refuse.
- **Every value is an i64** held as a JavaScript `BigInt` and wrapped with
  `BigInt.asIntN(64, …)` after every arithmetic operation. Each function is a
  `for(;;) switch (pc)` over its basic blocks, mirroring seed/81's
  `loop`/`br_table`, so SIR's arbitrary labels need no structuring pass.
  `FADDR` and `CALLI` go through a function table, as in seed/81.
- **Linear memory is one `ArrayBuffer`** read through `DataView`
  `getBigInt64`/`setBigInt64`, with the same layout as wasm32 (context at
  XW-CTX, literal pool at XW-POOL, then the arena). The runtime text is cut
  from seed/77 by the same section markers seed/82 uses, so the native, wasm
  and JS runtimes cannot drift. A missing marker is refused, as E7106 is.
- **The module is a restricted ES module** that exports only `start(fuel,
  host)`. `host` is the same five functions as `kotoba:host` (`write`, `cap`,
  `now`, `exit`, `input`, with the same arguments and answers), so the page
  and the existing Worker host protocol (`runtime/wasm32-browser-static-host.js`:
  `{bytes|module, fuel, allow, args, files}` in,
  `{exit, stdout, stderr, output, report}` out) serve both targets. The
  emitted text names no global: no `globalThis`, `window`, `self`, `fetch`,
  `import()`, `eval`, `Function`, `WebAssembly` and no `import` statement. The
  emitter guarantees that by construction, and the qualification checks it
  with a token scan outside string literals.
- **Fuel is charged exactly where seed/81 charges it**, so a run's remaining
  fuel is comparable across native, wasm and JS.
- **Refusals stay the same:** floating point, the syscall and call-at
  intrinsics are refused (E7101), as on seed/80 and seed/81.

The public spelling is `--target js-browser`. It is accepted by the native
CLI on every host that already accepts `wasm32-browser`.

### 2. The browser profile admits `:document`, and apps get an entry ABI

The app contract (`init`, `view`, `step` over `:document`) does not change
for authors. Two pieces make it compile natively for both browser targets:

- **The runtime profile for `wasm32-browser` and `js-browser` admits the
  document, string and vector operations the native runtime already
  implements.** Their runtime text is cut by section marker, like the rest of
  seed/82. If a part exists only in a macOS- or Linux-specific runtime, it is
  moved into a shared section first.
  The E7101 refusal of document operations in the browser profile is removed;
  floats stay refused.
- **`kotoba.app-entry/v1`:** with `--entry app`, the compiler synthesizes the
  program's `main` from a module that exports `init`, `view` and `step`. The
  synthesized `main` reads the input files `/app/state` (absent means "call
  `init`") and `/app/event` (target, kind and value) through wire 35, calls
  `step` and then `view`, and writes `{:state … :view …}` to stdout as one
  canonical document encoding. The encoding is an existing one (see the
  open questions), so the host's decoder is not a new format. Exports other than
  `main` are not exposed, so the native "every export is `:i64`" rule holds.
- **`runtime/dom-driver.mjs` gains an adapter for that entry.** It runs one
  fresh instance per interaction, which is the driver's model already ("each
  interaction gets a fresh instance and its own full budget"). It hands the
  held state and the event in as files, decodes the output, and passes `view`
  to the unchanged `reconcileUiDocument`. No capability is granted. State
  persistence stays with the page (client-runtime local-state), outside the
  guest.

### 3. Qualification, in the native tiers, without Node

The gates follow `scripts/seed/check-wasm32-browser.py`: Python orchestrates,
and headless Chromium (the `qualify-x86_64` job's `google-chrome`) executes.
No Node, nbb, kbb or JVM process runs in any gate.

1. **24 native cases:** each compiled to `js-browser` returns the same
   result, the same trap and the same remaining fuel as native and as
   `wasm32-browser`.
2. **Differential:** the case inputs, plus the `:document` probes added for
   §2, give byte-identical stdout across js-browser, wasm32-browser and
   native.
3. **Apps:** `examples/todo-app.kotoba` and
   `examples/approval-queue-app.kotoba` built with `--entry app` drive the
   browser matrix through dom-driver for both browser targets.
   `cloud-itonami/app-itonami-moji`'s `src/moji/editor.kotoba` is the first
   external consumer, with its 13 checks.
4. **Negative controls**, each of which must fail:
   - a module whose text contains a forbidden global, which the token scan
     must catch;
   - fuel exhaustion, whose trap and remaining fuel must equal wasm's;
   - an ungranted wire, which must be refused;
   - a float operation, which must be refused at compile time (E7101).

### 4. The nbb js route leaves, after §3 is green

In dependency order, as ADR 0348 did for the JVM:

1. `scripts/browser-matrix.cljk` `compile-web!` (and every other caller
   found by `git grep -- '--target js'`) switches to the native target and
   `--entry app`.
2. Delete `src/kotoba/compiler/nbb/js_cli.cljk` (as the retirement record
   already says) and `test/nbb/js_parity.cljk`. Any launcher spelling that
   routes js targets to nbb is removed, and `--jvm-free` is refused as an
   unknown flag instead of being honoured.
3. `test/fixtures/js-parity/` stays as dated historical data. It is a record
   of what the hosted emitter produced, not a required comparison (the
   workspace rule for reference oracles). **Byte parity with kotoba-script
   output is not a goal:** the new emitter is a different emitter with a
   different ABI, the program form plus the app entry, not
   `instantiateKotoba`'s typed restricted-ESM ABI. Semantic parity is what §3
   measures.
4. Before deletion, inventory the consumers of the typed restricted-ESM ABI.
   Known: `runtime/http/route-decide.mjs` (a committed artifact) and the
   `browser-host.mjs` `instantiateKotoba` path. Each one either moves to the
   program form or is recorded as a retained artifact with no build route.
   Whether `kotoba-lang/kotoba-script` is archived is the owner's decision.

## Consequences

- Kotoba app UIs, the itonami dapps included, get a build route that needs
  no hosted runtime. Until §1-§3 land, the Moji editor is checked natively
  through its own `main` (`scripts/check-editor-native.sh`), and its browser
  build stays blocked on this ADR.
- The browser targets become a profile question rather than a compiler
  question. The next runtime operation that should reach the browser is cut
  from seed/77 by marker, not re-implemented per target.
- `BigInt` arithmetic is slower than wasm i64. js-browser is for hosts that
  cannot or will not run Wasm, or where an inspectable ES module is wanted.
  wasm32-browser stays the default browser target.
- The keyword crash (`document-keyword-value`, exit 139) has to be fixed
  before §2 is qualified, because the app gate exercises keyword documents.
  The todo example stores its filter as a keyword.

## Open questions, to settle in the implementation PRs

- **i64 representation:** `BigInt` everywhere, or a pair of 32-bit halves on
  the hot paths. Measure before choosing, then record the result here.
- **The output encoding of `kotoba.app-entry/v1`:** the native value codec
  as it stands, or DAG-CBOR. Use whichever the host already decodes without a
  new parser.
- **Whether `instantiateKotoba`'s typed ABI** needs a native producer at all
  once the app entry exists. This is answered by the §4.4 inventory.

## Implementation record, 2026-11-01 (§1, Phase 1)

`seed/81-js-esm.kotoba` (`xj-*`) is in FULL-MANIFEST after seed/82, and
`seed/78-full-entry` dispatches `compile SRC --target js-browser --output NEW`.
Four things differ from the design above. They were measured, not assumed:

- **No separate runtime module.** The emitter reuses seed/82's `xw-rt-src`
  unchanged. Its JS-specific names are the five `kxrt-host-*` imports and
  `kxrt-wasm-grow/size`, which the JS emitter recognizes by the same names as
  seed/81. This means the wasm and JS runtimes cannot drift. There is no
  `82-js-esm-rt`.
- **The export is `instantiate(host)`, returning `{memory, start}`,** rather
  than `start(fuel, host)`. This is the shape of a wasm instance's exports, so
  `runtime/wasm32-browser-static-host.js` serves both targets: a message that
  carries `js` (the module text) is imported from a Blob URL.
- **Tail calls are trampolined.** JS has no proper tail calls. The first run
  failed `mutual-tail` with "Maximum call stack size exceeded". Where seed/81
  emits `return_call`, the JS emitter now returns `new TC(f,[args])`, and
  every other call site runs `R(..)`, which resumes deferred calls. Recursion
  that is not in tail position still ends in the engine's stack overflow
  (probe `deep`, exit 120), as it does on wasm.
- **The host decodes copies of guest bytes.** The JS module's memory is a
  resizable ArrayBuffer, and Chrome's `TextDecoder` refuses views over one, so
  the entry ABI's file read returned -1 and the runtime refused it. The host
  now decodes `.slice()` copies on both targets.

`scripts/seed/check-js-browser.py` (Mac CI) compiles the 24 runtime cases and
the probes to both targets, runs them in headless Chrome, and checks:

- every js case returns the static case's result, trap and remaining fuel;
- every js case's stdout, report included, equals the wasm module's byte for
  byte (24 of 24);
- the probes behave: spin traps with no fuel left, deep exits 120 from an
  engine trap, and entry echoes the file only with the page's grants;
- no module names a forbidden global or loader, and a mutated module that
  calls `fetch` is refused (negative control);
- all 11 float cases are refused with E7101 and no artifact is written.

Still open: §2 (`:document` in the browser profile and
`kotoba.app-entry/v1`), the Linux CI wiring of the js target beside
selfhost-bootstrap's wasm32-browser job, and §4, removing the nbb route.
