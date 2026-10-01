# ADR 0358 — The function-count admission bound: 1024 → 16384

- Date: 2026-10-01
- Status: Accepted (owner direction: the 100% definition is a native compiler
  that builds itself).
- Amends: `lang/guest-grammar.edn` `:admission-limits :max-functions`,
  `kotoba.compiler.project/max-project-functions`, `kotoba.verifier/max-functions`.
- Related: ADR 0354 (limits are kept only when they bound a resource), 0355
  (type-descriptor bounds), 0356 (source admission bound, the process followed
  here), `docs/build-scaling-coscientist.md` H-2/H-2′ (the earlier refusal to
  raise this bound for a benchmark).

## Context

The 2026-09-30 wall scan (`/private/tmp/wall-scan-21.tsv`, 162 sources) left 17
sources refusing with `function count exceeds admission limit`: the compiler's
own modules (`frontend`, `sema`, `core`, `project`, `project_files`, `receipt`,
`interface`, `effect_*`, `capability_names`, `ipld_adl_source`, `test_profile`,
the five `nbb/*_cli` drivers). The `mir` and `mc` linked projects were at 1008
and 1018 of 1024.

`docs/build-scaling-coscientist.md` H-2 rejected raising the bound because the
only argument then was a benchmark's convenience. This ADR has a different
argument, and measures it: the language's own compiler, linked, is larger than
the bound, so no arrangement of modules can ever compile it.

There is one number, not two. The project linker (`link-source`) produces ONE
source unit and the frontend analyses it as one module, so
`sema/max-functions` (per analysed unit) and `project/max-project-functions`
(linked count) have always been twins with the same value; the doc above
measured this (`linked project exceeds function limit` at 2048 over 4 modules).
A "per-module-unit" model would not remove the whole-program count: native and
Wasm images index all functions of the program.

## Evidence

Measured 2026-10-01.

1. Size of what must link. Top-level `defn`/`defn-` over the 162-file reach
   list (`/private/tmp/reach-list4.txt`): 3063. Every `(defn` occurrence in
   those files (counts the `:kotoba` and `:default` arms of dual-runtime
   bodies twice, so an upper bound): 6382. The frontend's linked closure alone
   (what 15 of the 17 files link) is 1035 functions before synthesized helpers
   (instrumented `analyze`, `FNCOUNT-PRE`); closure lowering adds roughly
   10-30% (264 vs 200, 387 vs 354 in the modules measured). The linked whole
   compiler (frontend + sema + kir + mir + wasm + native machine-ir/aarch64/
   x86_64 + linking) is therefore a few thousand functions: 1035 over the
   bound after only the frontend closure, ~3000-4500 for everything.
2. What the bound feeds, and whether each consumer scales:
   - Wasm function indices: LEB128 `uleb` (multi-byte; the single-byte
     truncation of issue #526 is fixed). Measured: 1129, 3076 and 6151-function
     programs compile to Wasm, validate and instantiate, and `main` returns the
     expected sum (3297, 8994, 17997).
   - Native: the same 3076-function program compiles to `aarch64-macos` and
     `x86_64-linux` kexe images (nbb `aarch64_cli` / `x86_64_cli`, ~100-140 s
     on a loaded host). No fixed-width function table was found in
     `kotoba-native` / `kotoba-codegen` (searched for count/index/table
     bounds on functions); call encodings are rel-branch ranges, not indices.
   - Lambda ids: `lambda-id-base = module-index * max-functions` and the
     project dispatcher's `(lower, upper]` ranges. Ids are i64 values;
     `max-project-modules` is 256, so the largest id is 256 * 16384 = 4 194 304.
   - Verifier `:function-count` (`1 <= n <= max-functions`): same number,
     moved with the others.
   - The per-unit analysis cost that the bound existed to bound: `check` of a
     3076-function module takes ~19 s unloaded (H-3e/H-3f removed the
     quadratic terms), 6151 functions ~47 s. Linear enough that a bound is
     still meaningful at 16384 (the Wasm compile of the largest probe stayed
     under one minute).
   - The `fuel` default (512) is a run-time budget, not this bound: a program
     with 1129 calls trapped `unreachable` on the default and ran correctly
     with `--fuel 100000`. Not changed.
3. Why 16384: it is the next power of two over the 6382 upper bound with a
   factor of ~2.5 for synthesized helpers; it keeps every consumer above in
   its measured range; and it is 1/4 of the 65536 where a u16 index would
   start to matter, so no future 16-bit table silently becomes the limit.

## Decision

`:max-functions` is 16384 in the authority (`kotoba-lang`
`lang/guest-grammar.edn`), its vendored copy in `kotoba-sema`
(`resources/kotoba/lang/guest-grammar.edn`),
`kotoba.compiler.frontend.namespace-defs/max-functions` (re-exported as
`frontend/max-functions` and `sema/max-functions`), `kotoba.verifier/max-functions`
(and its two `.kotoba` compat twins), and `kotoba.compiler.project/max-project-functions`,
which `lang/limits.edn` now lists as a copy of `:language/admission :max-functions`
so the agreement test compares it (it was unlisted before, which is how the
two twins could have drifted). It stays a fail-closed admission refusal.

## Consequences

- `value_bounds_agreement_test`: 98 copies compared, 0 failures (the new
  project copy included). `max_functions_test` (kotoba-sema) pins the value and
  checks a 1100-function module is admitted and that a lowered `max-functions`
  still refuses.
- Rescan of the 17 files (measured on the pre-split frontend, kotoba-sema
  `53888c7` + this change): none stops at the function count any more; all 17
  (the frontend and sema sources included) reach the same next wall, the first
  Kotoba-route port gap in `frontend.cljk` (`map fn parameter destructures
  ([k v])`, near line 3090).
- The vendored `guest-grammar.edn` copies in `grammar`, `kotoba`, `kotoba-tagline`
  and the pinned digests in the three `guest_grammar_vendor_test` files were
  already out of step with the authority before this change (the authority
  carried ADR 0356 without a digest advance); they are NOT advanced here and
  remain a separate resync wave. `docs/build-scaling-coscientist.md` and the
  site text still say 1024 as measured history.
