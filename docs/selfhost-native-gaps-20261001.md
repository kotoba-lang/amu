# Native backend gaps found by running the differential guests as compiled code (2026-10-01)

Premise (owner, 2026-10-01; `docs/selfhost-bootstrap-boundary-20261001.md`): the product must not depend on nbb, Node or the
JVM. The differential harnesses (`vx-diff`, `ds-diff`, `tm-diff`, the definition-identity and value-codec probes) ran the
Kotoba side on the KIR interpreter, which itself runs on nbb: about 6 ms per source byte, 48 cases per second on the
simplest guest. This note records what it took to run that side as **compiled code** instead, what already works, and the
exact refusals that keep the other guests off the native backend. The refusal list is the native-backend gap list.

## Modes (`scripts/selfhost-wall/guest-run.sh`)

| mode | what runs the Kotoba code | status |
|---|---|---|
| `native` (default) | `amu` aarch64-macos `.kexe`, extracted with `amu extract-native`, executed by `tools/kexe_loader.c` in command mode (stdin in via `:io/read` wire 41, answer out via `:io/write` wire 37, `:hash/sha256` wire 3 allowed) | product path for the run. The compile step still runs the compiler on nbb (bootstrap, 15-20 s for a small module, cached) |
| `wasm` | wasm32-browser artifact instantiated by node's WebAssembly through `runtime/browser-host.mjs` (`wasm-run.mjs`) | bootstrap reference |
| `interp` (`--interp`) | KIR interpreter on nbb (`interp-run.cljs`) | bootstrap reference, the semantics oracle |

`guest-run.sh [--native-only|--wasm-only|--interp] [--resolve] <guest.cljk> <entry> < cases > answers`. The default tries
native, then wasm, then the interpreter, printing and caching (`$GUEST_CACHE`, default `/tmp/kotoba-guest-cache`) the refusal
that sent the guest down a step; `--native-only`/`--wasm-only` fail instead. `vx-diff.sh`, `ds-diff.sh` and `tm-diff.sh` now ask
`guest-run.sh --resolve` first and run their batches through the compiled mode when one admits the guest; `--interp` (or
`GUEST_MODE=interp`) skips the compilers. Today every Form-based guest resolves to `interp` (below), so their numbers are unchanged
and the refusal is printed at the start of each run.

Loader budgets the wrapper sets (all defaults are tiny): `KEXE_PAIRS=32M` (default 4096 pair handles trap a 20 KB string
walk), `KEXE_STRING_POOL=256M`, `KEXE_CPU_SECONDS=KEXE_WALL_SECONDS=600` (defaults 1 s and 3 s). A single string value is
capped at 64 KiB (`KEXE_STRING_VALUE_LIMIT`), so batches stay under about 60 KB, as the interpreter harnesses already did.

## Measured (this Mac, arm64, unloaded apart from other agents)

`scripts/selfhost-wall/case-diff.sh`: `kotoba.string.case/upper-case-root` (the Kotoba reading in `lang/compat`) against the
host's `String.prototype.toUpperCase`, one Unicode scalar value per line (surrogates excluded) plus folding-heavy words.

| mode | cases | agree | seconds | cases/second |
|---|---|---|---|---|
| native | 1,112,073 (every scalar value) | 1,112,073 | 21.1 | 52,710 (process spawn and the node oracle dominate) |
| wasm | 20,000 | 20,000 | 8.3 | 2,411 |
| interp | 600 | 600 | 12.4 | 48 |

One 6 KB run of the same guest: native 0.09 s, wasm 0.88 s, interpreter 40.4 s (4.9 s of that is linking). All three modes and
the host produce identical bytes on the 1 KB, 6 KB and 20 KB inputs (`cmp`). Native is about 1,000 times the interpreter and
makes the exhaustive corpus (all 1.1 M scalar values) a 21 second job; the interpreter would need about 6 hours.

## Native gap list (the first-refusal of each guest, then the full per-function scan)

`scripts/selfhost-wall/native-gaps.sh <guest>...` asks the native admission gate (`kotoba.kir/only-native-word-typed-features?`,
through `unqualified-native-feature`) about every function on its own and lists the operations that neither kotoba-wasm nor
kotoba-verifier mention. The guests are in `scripts/selfhost-wall/guests/`.

| guest (module closure) | functions | native refusal (exact) | wasm refusal |
|---|---|---|---|
| `case.cljk` (kotoba.string.case) | 13 | none: compiles and runs | none: runs |
| `ds` (desugar port, `ds-gen.sh`, 280 KB) | 944 | the whole closure: 280 functions with boundary `[[:ref :form/r]]`, 92 with `[[:ref :fe/env] [:ref :form/r] [:result [:ref :fe/dr] [:ref :fe/err]]]`, 49, 43, 25 `[[:list [:ref :form/r]]]`, ...; the CLI stops at the first: `native target aarch64-macos does not qualify the boundary type [[:list [:ref :form/r]]] of function kotoba_module__0__0`; 14 `document-*` operations absent from the verifier | `typed Wasm operation is not qualified` (op: `typed-list-conj`) |
| `vx.cljk` (validate-expr) | 445 | 193 functions with boundary `[[:ref :form/r]]`, 33 with `[[:ref :form/r] [:ref :vx/env]]`, 21 `[:ref :form/r] x2`, ... (all through `:form/r`, `:vx/env`) | same op |
| `codec.cljk` (kotoba.value.codec) | 230 | 44 boundary `[[:ref :form/r]]`, 10 `[:ref :form/r] x2`, 9 `[:list [:ref :form/r]] x2`, ... | `typed-list-conj`, `vector-take` absent |
| `di.cljk` (kotoba.kir.definition-identity) | 488 | 52 boundary `[[:ref :form/r]]`, 19 `[:ref :form/r] x2`, 10 `[[:list [:ref :form/r]]]`, plus `[[:option :vector-i64]]` x5, `[[:option :bytes]]` x5, feature `option-match` | `typed-list-conj`, `string-index-of-from`, `vector-take` absent |
| `cc.cljk` (compile-cache) | 384 | `[[:option :vector-i64]]` x5, `[[:option :bytes]]` x5, `[[:record :kotoba.compiler.nbb.io/OutputEntry [[:path :string] [:kind :i64] [:data :bytes] [:text :string] [:mode :i64]]]]` x5, `[[:list [:record ...OutputEntry...]]]` x5, `[[:record :kotoba.compiler.nbb.compile-cache/Found [[:hit :bool] [:data :bytes]]]]` x2, `[[:result :bytes :document]]`, feature `record-get` | `string-index-of-from`, `vector-take` absent |
| `vc.cljk` (verdict-cache) | 558 | the cc list, plus feature `typed-cap-call` | same |
| `oa.cljk` (output-admission) | 469 | the cc list | same |
| `oat.cljk` (output-attestation) | 379 | `[[:option :vector-i64]]` x11, `[[:option :bytes]]` x5, features `option-match` x4, `option-value-of` x2 | none listed |
| `ri.cljk` (runtime-identity) | 99 | 0 refused by the admission gate, then the native verifier rejects the program: `runtime KIR operation rejected` (22 `document-*` operations absent from kotoba-verifier: `document-assoc document-bool document-contains document-count document-kind document-list-at ...`; reproduced on a 2-line `(document-edn-print (document-edn-read s))` module) | runs in principle (document ops exist in the wasm host) |

`tm-diff`: `tm-gen.py` still extracts from the single-file frontend; the split frontend (`frontend/base.cljk`, ...) leaves
aliases such as `base/max-reader-depth` unresolved in the generated guest (`constant alias must name a declared constant`),
so there is no tm guest to compile until `tm-gen` reads `FRONTEND_LIST` the way `ds-gen` does.

### The three missing native features, isolated on small records

Measured with `guests`-style probes (internal function taking `[:ref :r/R]`; the admission gate, aarch64):

| record field | native |
|---|---|
| `:i64 :string :keyword` | admitted |
| `[:list :i64]`, `[:list :string]`, `[:option [:ref R]]` | admitted |
| `:bytes` | refused (`[[:ref :r/R] [:ref :r/R]]` boundary): `:bytes` is a private handle admitted only as a bare parameter, not as a record field |
| `:vector-i64` | refused, same reason |
| `[:list [:ref :r/R]]` or `[:list [:ref :r/S]]` (list of aggregates) | refused; also as a bare `[:list [:ref :r/S]]` parameter |

1. **List of aggregate handles.** `[:list T]` is native only for word-like `T` (`kotoba.kir/native-handle-type?` has no `:list`
   arm; `native-word-value-type?` admits `[:list :i64]`/`[:list :string]`). `:form/r` (the recursive Form record every selfhost guest
   walks) holds `[:kids [:list [:ref :form/r]]]`, so no Form-based module can go native. This is the wall for vx, ds, tm,
   definition-identity and the value codec. It needs a native list arena whose items are pair handles (ADR 0087's aggregate ABI v8
   carries records/variants/heterogeneous vectors as one-word handles; a list of them is the missing step), the matching
   `typed-list-nth`/`conj`/`count` lowering on aarch64 and x86-64, the verifier twin, and loader boundary budgets.
2. **`:bytes` / `:vector-i64` as record fields, and `[:option :vector-i64]`, `[:option :bytes]`, `[:result :bytes :document]`
   as handles.** `native-private-handle-type?` is deliberately non-recursive ("so option/result ownership is not widened as a
   side effect"). Needed by the Form record (`:data :bytes`), compile-cache, verdict-cache, output-admission and
   output-attestation. Widening it means deciding handle ownership inside records and options.
3. **`:document` operations in the native verifier.** `document-edn-read/print`, `document-kind`, `-count`, `-list-at`,
   `-vector`, `-assoc`, `-bool`, `-contains`, ... (22 heads) are admitted by kotoba-wasm and the interpreter but not by
   `kotoba.verifier`. Needed by runtime-identity and by anything that reads configuration as data.

Smaller refusals seen: feature `option-match` and `option-value-of` over option-of-handle, `record-get` on a record holding a
bytes field, `typed-cap-call` with a non-generic type pair in verdict-cache.

### The wasm fallback walls (why it is not a substitute for Form guests)

- kotoba-wasm has no `typed-list-conj` (the Form builders `append-form`, ... lower to it), `string-index-of-from`, `vector-take`
  or `string-find-byte` intrinsic (`core.cljk` dispatches by literal operation symbol and the fall-through is the unqualified
  refusal; `ex-data` carries `:operation`, the CLI prints only the message).
- `runtime/browser-host.mjs` is a bounded sandbox host, not a compiler runtime: lists, vectors and maps are capped at 32 items
  (`list item limit exceeded`), 64 typed descriptors, a 1 MiB module (`MAX_MODULE_BYTES`), and every typed operation
  re-validates its value. A Form tree with more than 32 kids, or a 280 KB guest (ds), is outside it.
- Compiling a Form guest to wasm takes 1 to 2.5 minutes on nbb, and string-heavy guests are slow in the host (20 KB of
  `substring` walks took 12 s, 6 KB took 0.9 s).

## What replaces the bootstrap pieces

The compile step of both compiled modes (`aarch64_cli.cljk` / `wasm_cli.cljk` on nbb) is itself bootstrap: it is the selfhost
compiler that cannot yet run natively (stage S6). `guest-run.sh` keeps the compile and the run separate on purpose: the run
needs only `tools/kexe_loader.c` and the `.bin`, so once `amu` is a native binary the compile line changes and nothing else
does. Bootstrap-only files carry `;; bootstrap-tooling`: `interp-run.cljs`, `wasm-run.mjs`, `native-gaps.cljs`; the host-side
oracle of `case-diff.sh` is node (`toUpperCase`) and is the reference, not a product dependency.
