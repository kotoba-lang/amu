# Selfhost status and build order, 2026-09-30

Reachable set (the 154 sources the compiler's entry points require): **57 pass `amu check` on the
Kotoba route** (37%). Measured with the integrated classpath of every worktree, first refusal per file.

| stage | reachable files that pass `check` |
|---|---:|
| session start | 9 |
| parallel per-file ports (wave 1) | 33 |
| abort export, char, document heads, record-export import, set literals | 38 |
| `:document` sequence heads and reduce/map/filter/remove over documents | 47 |
| per-file port workflow (wave 4, 10 ports, 0 refuted by adversarial verification) | 56 |
| merge/select-keys/get-in/assoc-in/update/empty?/some/every?/concat/keep/into on documents; wave 5 (1 port; the harvest of per-file rewrites is exhausted) | **57** |

What landed in the language (kotoba-sema / amu / osaho / native / verifier): `typed-list-conj`, an export may
abort ([:result T E]), `contains?` on typed sets, `(char n)`, `assoc`/`dissoc`/`get`/`contains?`/`count`/`first`/
`rest`/`nth`/`keys`/`vals` and `reduce`/`map`/`filter`/`remove` on `:document`, `#{...}` literals typed by their
items, an import of an export returning a `[:ref]` record, descriptor bounds 64 deep / 512 nodes (ADR 0355), source
bound 8 MiB (ADR 0356), reduce over a `[:list T]` parameter, native lowering of typed lists. A recursive typed
`Form` (a record whose field is `[:list [:ref :form/r]]`) is unbounded in depth and count (kotoba-hir `form.cljk`).

The last two passes say where the ceiling of per-file work is: wave 4 admitted 10 files, wave 5 admitted 1 after the
remaining collection heads were added. The 97 files still blocked need a feature designed and built, not a rewrite:
bytes and host crypto, mutable cells that can be parameters and return values, protocols with a closure ABI, and a
`:kotoba/host-only` scope marker for the host glue. Each of those crosses the frontend, KIR, native and the module ABI.

## What is left, ranked by files unblocked (workflow synthesis of the 84 blocked)

# Amu selfhost: build order for the 84 BLOCKED files

Of the 84 files, 41 are blocked by walls in their own text. The other 43 are blocked by an imported module. Counts below are per feature, and one file can hit several features. "Own" means the file's own text needs the feature. "Cascade" means dependents that clear their first wall when a root module (mostly not in the 84) is fixed. "Full" means the file has no other reported wall.

## Build order by files unblocked

### 1. Untyped `:document` collection heads: ≈25 files (5 own, ≈20 cascade)
- **Own:** pe32plus, x86_64, ipld_adl_source (concat), component/wit, mir.
- **Own, secondary:** project (count), uefi_operations, aarch64, native/linux_static, verdict_cache, coll.
- **Cascade root A, `kotoba.artifact.core`:** edn-safe and canonical use `(into (empty x) (map (fn [[k v]] ..)) x)`.
  - Full: evm, provenance, project_source, compiler/trust_cli.
  - First wall only: ios_aot, interface, cache, coverage_evidence, js_cli, evm_cli, nbb/trust_cli, output_set_cli, compiler/run_cli, nbb/cli.
- **Cascade root B, `kotoba.sema` (affine.cljk:257):** the `count` on an untyped value is inferred as `:i64`.
  - Full: capability_names, effect_classification, effect_row, receipt.
  - First wall only: definition_identity (compiler), interface, nbb/cli, test_cli (via project and project_files).
- **Design, map and entry heads:**
  - `map`, `into`, `keep`, `mapcat` and `some`/`every?` over a `:document` infer the item type as `:document`. A map source yields `[k v]` entries.
  - `(fn [[k v]] ..)` destructures an entry as `(doc-key e)` and `(doc-val e)`.
  - `(into (empty x) xf x)` and `(into {} xf m)` elaborate to a `reduce` with `doc-assoc` or `doc-conj`.
  - `count` on a `:document` becomes a tag-dispatched `doc-count`.
- **Design, other heads:** these are eager combinators that inline the literal `fn`, `#()`, keyword or `juxt-of-keywords` argument.
  - `merge`, `update`, `get-in`, `assoc-in`, `sort-by`, `group-by`, `frequencies`, `zipmap`, `concat`.
  - `concat` is variadic and expands to nested `list-append`.
  - `postwalk` and `tree-seq` are bounded by fuel.
- **Limits:**
  - No lazy or infinite seqs. `lazy-seq`, `iterate` and `for` become eager, size-bounded loops.
  - No first-class fn values.
- **Cheapest step first:** annotate `form :document` in the sema `expand-threads` code. That is a library edit and needs no compiler change.
- **Risk:**
  - Kotoba typed maps iterate in sorted order and Clojure maps do not, so results can diverge from the host. Force `sort` where order matters.
  - Changing the default type of unannotated params from `:i64` to `:document` would silently retype existing modules. Keep it opt-in.

### 2. Bytes, capability payloads and host crypto: ≈24 files (13 own, plus 5 secondary, ≈6 cascade)
- **Own:** io/file, wasm/tools, signing, nbb/io, module_lock, native_package, output_attestation, output_admission, release, project_files, test_profile, wasm_cli, component/artifact.
- **Own, secondary:** to_bytes, script, cli_support, verdict_cache, package_authoring.
- **Cascade off nbb/io:** atomic_output, bounded_edn, run_cli (compiler), package_lock, output_set_cli.
- **Design, do in three tiers.**
  - Tier (i), the biggest lever:
    - Add a `:bytes` value type with `bytes-len`, `bytes-get`, `bytes-slice`, `bytes-concat`, `utf8-encode` and `utf8-decode`.
    - Add the `:bytes` payload for `typed-cap-call` (wire 35), exposed as `fs/app-data-bytes`.
    - Fixing this makes nbb/io admissible and clears atomic_output and bounded_edn, with the second-order dependents behind them.
  - Tier (ii), pure builtins:
    - `sha256` as `:bytes` or `:document` to hex `:string`.
    - `base64`.
    - `ed25519` sign and verify. These can be written in Kotoba itself.
    - These clear the sha256 gap in artifact.core and evm, and cover signing and output_attestation.
  - Tier (iii), declare as host-only and stop porting:
    - process spawn (wasm/tools, test_profile, component/artifact).
    - JS interop (`js/Number`, `js/Buffer`, `js/BigInt`, TextDecoder).
    - Node entrypoints.
    - Mark these `:kotoba/host-only` so they leave the backlog.
- **Risk:**
  - The capability wire has to land in three hosts (wasm, JVM, Node).
  - `catch :default` and CLI top-level forms have no honest port.
  - io/file returns host arrays.
  - Ed25519 written in Kotoba is a security-review burden.

### 3. Mutable cells: ≈21 files (9 primary, 9 secondary, ≈3 cascade)
- **Own, primary:** byte_buffer (atom returned from a function), len (deref of an atom param), put (swap! on an atom param), to_bytes, compile_cache, native/linux_static, aarch64, kir, kir/value (top-level atom).
- **Own, secondary:** reader_buffer, script, verifier (dynamic vars plus volatile), cli_support, package_authoring, project, project_files, verdict_cache, uefi_operations.
- **Cascade via kir and kir/value:** reference_runtime, cljs, definition_identity (compiler).
- **Design:**
  - Add a `[:ref T]` type: one heap slot in the module arena, with T a fixed-representation type.
  - Forms and what they elaborate to:
    - `atom` and `volatile!` allocate the slot.
    - `@r` and `deref` load.
    - `reset!` and `vreset!` store.
    - `swap!` and `vswap!` load, call a known fn or inline `fn` with the extra args, then store.
  - A ref may be a param, a return value, a record field or a `:document` map value. This lifts the current "let-bound only" slice-1 rule. That rule is the wall for byte_buffer, len and put.
  - Top-level `(def x (atom ..))` is not allowed. Rewrite to a module-level `state` capability, or thread the ref through. kir/value has 3 such cells, so it needs a resource-table capability.
  - `^:dynamic` plus `binding` becomes an explicit context param via a source rewrite. That covers verifier, kir and aarch64.
- **Limits:**
  - No `add-watch`, `compare-and-set!` or thread sharing.
  - No GC. The arena is freed per call.
- **Risk:**
  - Refs collide with the affine and ownership checker and with the "pure export" verification story.
  - Cross-module ABI is a stability commitment.
  - The dynamic-var rewrite is invasive and the highest risk item here.
  - kir and kir/value are 6k and 2.7k lines. Cells alone do not clear them; they also need try/catch and cross-module handles.

### 4. Protocols, `reify` and protocol-only modules: 7 files (3 own, 4 cascade)
- **Own:** reader, writer (both protocol-only), reader_buffer (`reify` with an atom).
- **Cascade, dependency `kotoba.io.reader` / `kotoba.io.writer`:** stream (also host glue), buffer_writer (needs `reify` and `swap!`), copy (needs `when-let` over an option), reader_seq (`lazy-seq`).
- **Design:**
  - Allow a `defprotocol` module with typed method signatures, for example `(read! [r] :- [:option :bytes])`.
  - Allow `:export [read!]`. Each method exports as a dispatch fn.
  - Implementers are `{tag, env-ptr}` closure objects called through a funcref-table `call_indirect`.
  - `(reify P (m [_ ..] body))` is closure-converted. Captured variables must be immutable or a `[:ref]` from feature 3.
  - `when-let` over an option is plain sugar.
  - `lazy-seq` becomes an eager loop into `[:list :bytes]`.
- **Limits:**
  - Only reader and writer (2 files) are unblocked without features 2 and 3.
  - Infinite readers are not supported.
- **Risk:**
  - The current "sealed static dispatch over same-module records" model is closed. Open cross-module extension needs a closure ABI. That ABI is also the base for feature 8.
  - `lazy-seq` changes semantics.

### 5. `try`/`catch`/`throw`/`ex-info`/`finally`: 8 own, plus 1 cascade
- **Own:** mir (`ex-data`-driven spill retry), package_authoring, cli_support, kir, project_files, signing, module_lock, aarch64.
- **Cascade:** bounded_edn, whose wall is "try requires exactly one body expression and one catch clause".
- **Design:**
  - Lower `try` to a Result. A `throws` effect is inferred per fn, and every call that may throw returns `[:result T :document]`.
  - `(throw (ex-info m d))` is an early return of Err.
  - `(catch ExceptionInfo e ..)` and `:default` bind the document.
  - `ex-data` reads the map.
  - `finally` duplicates the cleanup on both paths.
  - The immediate cheap step is allowing an implicit `do` body and multiple catches. That clears bounded_edn's first wall.
- **Limits:** no Java class hierarchy. Only `ExceptionInfo` and `:default`.
- **Risk:** it needs a cross-module signature change. Host-thrown exceptions such as `NumberFormatException` cannot be caught.

### 6. Regex: 9 files touch it
- **Files:** text, script, verifier, verdict_cache, component/wit, output_admission, project, coverage_evidence, compiler/core (the reader rejects the literal).
- **Design:**
  - The reader accepts `#"..."`.
  - Compile a bounded regex subset at build time to code: classes, `{n}`, `+`, `*`, `?`, alternation, and `^`/`$` implied by `re-matches`.
  - Add `re-matches`, `re-find`, `re-seq`, `str/replace` and `re-pattern` with a literal only.
  - The dominant use is `#"[0-9a-f]{64}"`, which is trivial.
- **Limits:** no backrefs, no lookaround, no runtime-constructed patterns (a runtime `re-pattern` needs an interpreter).
- **Risk:** semantic drift versus the JVM regex. Pin the subset and reject the rest.

### 7. Cross-module constant and value references: 7 files (6 cascade, 1 own)
- **Cascade:** wasm/core and component/core (kotoba.wasm.typed), kir/admission (abac), mc and machine_ir (kotoba.mir), and component/artifact (typed/wasm-type).
- **Own:** kir/admission needs `seq` as a builtin in crypto-policy.
- **Design:**
  - Resolve `(def X other/Y)` by compile-time evaluation.
  - A top-level `def` whose initializer is pure over literals and imported constants, such as `(into #{} (map #(keyword "mir" (name %))) gmir/kernel-atomic-ops)`, is folded to a constant.
  - This also gives `(def x ns/f)` re-export aliases as generated wrapper defns, taken from the imported signature. That is io.cljk (see 8).
  - Add `seq` to the builtins.
- **Risk:**
  - The constant folder needs a fuel bound.
  - The mir case is really a classpath fix: point wall-cp at the wt-D-kotoba-mir source, where kernel-atomic-ops is the constant.

### 8. Function values and variadics: 4 own (io.cljk, coll, native_package, compile_cache)
- **Also:** text (`& args`); evm_cli and nbb/run_cli (dep) pass closures.
- **Design:**
  - Add `[:fn [A..] R]` param and record-field types via funcref tables and typed `call_indirect`.
  - Add variadic exports as a `[:list T]` tail param: `[fmt & args]` becomes `[fmt args]`.
  - The `=` on fns in native_package's `kits` becomes a keyword tag.
- **Limits:** closures capturing mutable state need feature 3.
- **Risk:** this shares the closure ABI with feature 4. Do them together.
- coll additionally needs transient/persistent!, PersistentQueue and `map-entry?`/`record?`. It is a poor first target.

### 9. Symbols and dynamic keywords in documents: 3 files (uefi_operations, pe32plus, x86_64)
- **Design:**
  - Add `document-symbol`, `symbol?`, `[:set :symbol]`, quoted symbol-set literals and `(keyword (str ..))`.
  - Add the `\\u0000` char literal.
- **Risk:** a symbol needs an interned tag in the document encoding, which is a wire change.

### 10. Module literal limits: 2 files (linux_static_handlers, script)
- **linux_static_handlers:** 165 KB of EDN strings against the 16 x 4096 budget.
- **script:** a quoted set of more than 32 items is refused with a misleading "mixes symbols" message.
- **Design:** raise the set-literal cap. Add a `^:data` def into a data segment with a hash-addressed 1 MiB cap.
- **Risk:** low.

### 11. Double math: 1 file (text)
- Needs `Math/abs`, `Math/pow`, `Math/round` and `(double x)`, plus a variadic `format`.

### 12. Generic dynamic CBOR encode (osaho kir/definition_identity)
- `cbor.core/encode` of a tagged tree is host-only in org-ietf-cbor. Either add a generic encode to that repo's Kotoba side or build the canonical bytes from typed `encode-*` fragments. It is a dependency item (see below).

### Not features: exclude as host shells
These are nbb top-level effectful entrypoints and CLI glue: aarch64_cli, x86_64_cli, nbb/trust_cli, js_cli, wasm_cli, nbb/run_cli, package_authoring's spawn code, and native_package.

An optional `:kotoba/entry` sugar would rewrite the top-level `(support/execute! ..)` to an exported `main`. That would give these files an `:export` instead of "exports nothing".

## Cheap wins to do before compiler work
1. **kotoba.mir classpath** (`wt-D-kotoba-mir` in place of the gitlibs copy): clears mc and machine_ir, which are 2 files.
2. **`:document` annotation in kotoba-sema `expand-threads`:** clears capability_names, effect_classification, effect_row and receipt, which are 4 files.
3. **`elf64.cljk`:** add a merged file, since only elf64.clj.cljk and elf64.cljc.cljk exist. Clears aarch64_cli, x86_64_cli and the elf64 wall in core, which are 3 files. core still has the regex and sha256 walls.
4. **"constant alias must name a declared constant"** appears in both wasm.typed and security.abac. Fixing it clears the first wall for wasm/core, component/core and kir/admission.
5. **Multi-body `try`** clears bounded_edn.
6. **artifact.core `edn-safe`/`canonical`:** rewrite `(fn [[k v]])` as `(fn [e] (let [k (key e) v (val e)] ..))` on the port side. That gives 4 full files and 10 first-wall clears with no compiler change.

## Blocked only by a dependency (43 files)
Each entry below names the dependency, and the file is fully cleared if nothing else is listed.

- **kotoba.artifact.core** (`[k v]` destructure, plus sha256):
  - evm (already ported, awaiting only this)
  - provenance
  - project_source (other imports unverified)
  - compiler/trust_cli
  - ios_aot (also kotoba.verifier)
  - interface (also kotoba.sema)
  - cache (also provenance, signing, verifier)
  - coverage_evidence (also signing, verifier)
  - js_cli (also host glue in its own text)
  - evm_cli (also cli_support, nbb/io)
  - nbb/trust_cli (also cli_support)
- **kotoba.sema / affine.cljk:257 (`count`):**
  - capability_names (also postwalk from kotoba.lang.coll)
  - effect_classification
  - effect_row
  - receipt
  - nbb/cli (11 of its 16 imports fail)
  - definition_identity (compiler, also kotoba.kir)
- **kotoba.kir** (top-level `atom` in kir/value):
  - reference_runtime
  - cljs (via reference_runtime; authority is now OK)
  - definition_identity (compiler)
- **kotoba.mir:** mc, machine_ir.
- **kotoba.native.elf64** (missing merged .cljk): compiler/core (plus regex and sha256 own walls), aarch64_cli, x86_64_cli.
- **kotoba.wasm.typed** (constant alias): wasm/core (4119 lines, more walls likely), component/core.
- **kotoba.security.abac** and **crypto-policy** (`seq`): kir/admission.
- **kotoba.verifier** (`set/union`, and itself blocked): verifier/linux_static (also kotoba.native.linux-static), coverage (also host IO in `verify-dataset!`).
- **nbb/io `fs/app-data-bytes`:** atomic_output, bounded_edn, package_lock (also cli_support), compiler/run_cli (also atomic_output, receipt, trust_cli).
- **nbb/cli_support** ("let requires an even binding vector", and itself blocked): nbb/test_cli, output_set_cli.
- **kotoba.compiler.nbb.compile-cache** (`js/Number`): output_set (fully ported, passes with a stub).
- **kotoba.compiler.test-cli** (string host import): nbb/test_cli.
- **kotoba.compiler.test-cli's imports** (bounded_edn, project, project_files, test_profile): compiler/test_cli.
- **kototama.native.executor** (not on the source path): nbb/run_cli.
- **Protocol modules kotoba.io.reader and kotoba.io.writer:** stream, buffer_writer, copy, reader_seq (see feature 4).
- **org-ietf-cbor generic `encode`:** osaho kir/definition_identity. The `str/lower` wall there is already fixable with `simple-lower-case` under `#?(:kotoba ..)`.

## Unlock counts
- **Root-module fixes.** They are ranked by cascade, not by own files, so they beat any single language feature for near-term count:
  - artifact.core: 14 files.
  - sema: 8.
  - nbb/io plus cli_support: 9.
- **Language features to build next.** In order: document heads and `count`, then bytes with capability payloads, then mutable cells, then protocols with closure ABI, then try/throw, then regex.
- **Overall.** About 8 dependency files clear from the cheap wins alone. Features 1 to 3 together attack about 60 of the 84, but roughly 20 host shells should be declared out of scope rather than ported."
  },
  "workflowProgress": [
    {
      "type": "workflow_phase",
      "index": 1,
      "title": "Port"
    },
    {
      "type": "workflow_phase",
      "index": 2,
      "title": "Verify"
    },
    {
      "type": "workflow_phase",
      "index": 3,
      "title": "Synthesize"
    },
    {
      "type": "workflow_agent",
      "index": 1,
      "label": "port#0",
      "phaseIndex": 1,
      "phaseTitle": "Port",
      "agentId": "a279a137410ae38f6",
      "model": "claude-sonnet-5-5",
      "state": "done",
      "startedAt": 1790728940619,
      "queuedAt": 1790728940599,
      "attempt": 1,
      "lastToolName": "StructuredOutput",
      "lastToolSummary": "/private/tmp/wt-E-io/src/kotoba/io.cljk",
      "promptPreview": "You are porting ONE Amu compiler / Kotoba library source so `amu check` admits it on the Kotoba (selfhost) route while it behaves identically on the host (nbb/JVM).
First read /private/tmp/porting-brief.md (the dual-runtime idiom, tools, rules). Its capability list is OUT OF DATE; use THIS one, which is current and all live on the shared classpath:
 - An export may abort (Kotoba interface [:result…",
      "promptFramed": true,
      "lastProgressAt": 1790728955540,
      "tokens": 61955,
      "toolCalls": 3,
      "durationMs": 14912,
      "resultPreview": "{"file":"/private/tmp/wt-E-io/src/kotoba/io.cljk","status":"BLOCKED","blocked_by_dependency":false,"blocker_feature":"Function values crossing modules: (def name other-ns/fn) aliases used as the module's public API. Kotoba has no re-export/alias of an imported function, and an :export must name a locally defined typed defn.","blocker_detail":"The file is about 60 lines of (def x some-ns/x) re-expo…"
    },
    {
      "type": "workflow_agent",
      "index": 2,
      "label": "port#1",
      "phaseIndex": 1,
      "phaseTitle": "Port",
      "agentId": "a55f9f4d24f65d7b3",
      "model": "claude-sonnet-5-5",
      "state": "done",
      "startedAt": 1790728940621,
      "queuedAt": 1790728940600,
      "attempt": 1,
      "lastToolName": "StructuredOutput",
      "lastToolSummary": "/private/tmp/wt-F-coll/src/kotoba/lang/coll.cljk",
      "promptPreview": "You are porting ONE Amu compiler / Kotoba library source so `amu check` admits it on the Kotoba (selfhost) route while it behaves identically on the host (nbb/JVM).
First read /private/tmp/porting-brief.md (the dual-runtime idiom, tools, rules). Its capability list is OUT OF DATE; use THIS one, which is current and all live on the shared classpath:
 - An export may abort (Kotoba interface [:result…",
      "promptFramed": true,
      "lastProgressAt": 1790728971072,
      "tokens": 69775,
      "toolCalls": 4,
      "durationMs": 27999,
      "resultPreview": "{"file":"/private/tmp/wt-F-coll/src/kotoba/lang/coll.cljk","status":"BLOCKED","blocked_by_dependency":false,"blocker_feature":"Polymorphic, higher-order, variadic public API with no single typed interface (function-typed parameters and variadic exports), plus host-class interop (PersistentQueue), transient/persistent!, map-entry?/record?","blocker_detail":"I did not edit the file. I did not run `w…"
    },
    {
      "type": "workflow_agent",
      "index": 3,
      "label": "port#2",
      "phaseIndex": 1,
      "phaseTitl
