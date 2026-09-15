# ADR 0350 — Linked closures on the JVM-free route: `amu test --source-path`, the artifact reader's structural indexes, and the two dependency fixes

- Date: 2026-09-16
- Status: Accepted
- Related: ADR 0349 (`amu test` per-test instances), ADR 0346 (template modules),
  kotoba-sema #80, kotoba-script #102, root ADR-2609151600 (the langgraph port that
  measured all of this).

## Context

Porting `kotoba-lang/langgraph`'s StateGraph loop to a Kotoba template module over
the application's state record — nodes as `[:fn [[:i64 :i64 state] state]]` closures,
compiled to `aarch64-macos` and executed through the kexe loader — met four walls in
one afternoon, none of them in the language:

1. **A name the compiler wrote, the compiler refused.** The dispatcher for a closure
   family with typed parameters AND a structured result was named
   `__kotoba_invoke_p_<64 hex>_t_<64 hex>$arityN` — 156 characters against
   `max-symbol-chars` 128. Single-module analysis never validated the synthesized
   name, so `amu check` admitted the program; the project linker re-reads the linked
   source as text and `valid-name?` refused it as `invalid function name` at a span the
   author never wrote, and the verifier refused the artifact as `runtime KIR function
   shape rejected`. Fixed in kotoba-sema #80: one digest of the whole clause signature,
   `__kotoba_invoke_pt_<64>$arityN` (90 characters); the two older families keep their
   names and their CIDs.
2. **A read-back artifact with any closure was refused by its own oracle.**
   `read-artifact-file!` returns a BigInt for every integer token — right for an i64
   value, wrong for `:closure-param-indexes` / `:i64-pair-chain-param-indexes`, which
   the interpreter checks with `integer?` and uses with `nth`. `extract-native` on the
   first native program passing a `(fn [s] ...)` answered `native artifact oracle
   evaluation rejected` / `closure parameter indexes are malformed`; every fixture
   that had reached the command before was closure-free.
3. **A template module's tests could be compiled but never run.** `amu test` took a
   single file; the tests of a module that `(:require ...)`s another — and a
   template's tests can only exist in an importer that binds its `:params` — were
   refused as an unresolved namespace.
4. **On the js target only, every linked program with a closure across modules
   trapped `invalid-i64`.** amu's linker renames each module's dispatcher to
   `kotoba_module__m__n` and keeps its `__kotoba_closure_*` parameter; kotoba-script's
   `closure-dispatcher?` keyed on the name as well, so the renamed dispatcher guarded
   its closure word with `assertI64`. The frontend's refinement inference did not
   cover it either (it flows callee → caller; this callee only reads `pair-first`).
   Reproduced on a two-module `apply-twice` against amu main b2a52f48. Fixed in
   kotoba-script #102: keyed on the parameter name, which only the frontend writes.

## Decision

- `kotoba.compiler.nbb.cli-support/read-artifact-file!` narrows exactly the two
  structural-index keys of every function to host integers after the read — the
  same move `extract-native` already makes for `:code`. `examples/closure-node.kotoba`
  (a node closure over a record state, 3 steps ⇒ 301) joins the JDK-free native
  conformance: compile → extract → execute.
- `amu test <file> [--source-path <dir> ...]` links the closed graph through
  `project/link-source` and runs the linked unit's exported `test-*` with
  `:admit-linked-synthetics?` — the seam `compile --source-path` opens.
  `scripts/test-nbb-test.cljk` runs a root that requires a template module (3/3 on
  the three targets once kotoba-script #102 is pinned) and shows the same root refused
  without the flag.
- The kotoba-sema and kotoba-script pins advance to the merge commits of #80 and #102
  in this same change, with `deps-lock.edn` regenerated.

## Consequences

- Closures whose parameters are records (a state-graph node, a reducer over a typed
  state) compile and run on every target the JVM-free route serves, and their
  artifacts verify on read-back.
- The first consumer, `kotoba-lang/langgraph` `src/langgraph/core.kotoba`, measures
  nine scenarios equal between the `.cljk` oracle and the native binary
  (`scripts/verify-kotoba-core.cljk` there); that script is the shape a component's
  native gate takes: literals pinned once for both sides, interpreter and wasm32
  through `amu test --source-path`, native through extract + loader, executed, not
  merely built.
- Frontend shapes the port had to write around, each measured and named in that
  module's header rather than here (they are kotoba-sema's to remove): a keyword
  projection of a record parameter is untyped when it stands in a loop's initial
  value; a closure call inside a loop whose value is a record leaves the loop typed
  i64; a closure call standing directly as a `record-new` argument is not desugared;
  a `record-new` in a record-valued loop's exit branch leaves the loop typed i64; a
  record has at most 5 fields (its constructor is a function of the ABI's 5
  parameters); a `(fn [...] (->R ...))` lambda body must call a named typed function.
