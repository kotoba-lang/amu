# Seed R4 (functions): report, 2026-10-03

Rung R4 of the seed ladder (docs/selfhost-seed-design-20261002.md section 1.4): `fn` literals and closures, `fn-ref`,
`invoke`, `apply`, `map` / `filter` / `reduce`, multi-arity and variadic `defn`, `list`. Tag `seed-r4`, record
`seed/rungs/r4.record`. All timings below were taken on a loaded host (load average 95-140); rerun on a quiet host before
quoting them.

## Result

| item | value |
|---|---|
| bridge | unity of f316f4a1f (R4 features written in the R3 language) compiled by the R3 seed cbae36dc -> d0909898 (373,600 bytes) |
| rung proof | unity of 929867140 (10,648 lines; 30-lower, 21-check and 41-a64gen rewritten with R4 features) |
| fixed point | seed-1 == seed-2 e9598b28 (382,968 bytes); `bootstrap.sh --no-head` reproduces r0 -> r1 -> r2 -> r3 -> r4 from the committed R0 seed |
| gates `--rung r4` | BUILD ERR G1 G2 G3 G4 G5 GR all PASS (G1 19/19 for bridge and seed-1, G2 65/66 as before, G3 golden refusal-r4.txt, G4 84 containers identical bridge vs seed-1, GR r4 33 = stage-0 + 4 = spec, 27 negatives refused) |
| previous rung gates | GR r3 26 + 28 / 28 negatives; GR r1 52 + 5 / 35 refused + 5 accepted by decision; KIR gate 19/19 (code bytes and fuel equal to the source route) |
| conformance `functions/` | 5 of 7 accepted with the manifest values: callable_contracts 7, closure_list_result 2, contextual_invoke 2, multi_arity 25 verbatim (plus an ns line); closures 37 as a typed adaptation (callable parameters annotated). closure_bytes_result (:bytes) and lazy_sequences (lazy-*) stay refused |
| Embench compile, 19 ports | seed 609 ms in all vs stage-0 4,730 ms (record medians, same host and load) |
| code bytes, 19 ports | 97,673 (R3 96,969; +352 of them in xgboost, the in-line string-code-point-at) |

## Design (seed/HEADS heads 131-141, seed/SIR :r4-lowering, seed/CONTRACT-REQUESTS.md R4 lines)

- A fn literal is lambda-lifted by 21-check into its own FN record (FK-LAMBDA): parameters first, then the captured
  locals (at most 5 in all). A closure value is `pair(code address, env)`: env 0, the single capture, or a pair chain of
  the captures; with 2 or more captures an adapter FN (FK-ADAPTER) unpacks the env. The seed calls closures through the
  code address (new SIR ops FADDR = `adr` + fixup FX-ADR19, CALLI = `blr`), not through stage-0's
  `__kotoba_invoke$arityN` dispatchers. `fn-ref f` = `pair(address of f, 0)`.
- A let-bound fn literal is a known function: `(f a ..)` is a direct CALL with the captured slots appended, and no
  closure is allocated unless the rest of the let uses `f` as a value.
- map / filter / reduce lower to inline counted loops (R3 style hidden slots); the callback is called directly for an
  inline fn or a defn name, through CALLI for a value.
- Multi-arity defns are one FN record per clause; a call picks the clause by argument count; a variadic clause packs the
  surplus into a `[:list :i64]`.
- The callable rules follow the reference, measured on stage-0: bare fn parameters typed by context (a `[:fn ..]`
  parameter slot, a declared `[:fn ..]` result in tail position, the map/filter/reduce item and accumulator), captures
  :i64 or callable only, no callable inside a fn type, :vector-i64 sources only, no-init reduce only through a defn with
  arities 0 and 2. New refusal E2139 (annotated fn parameter); E2134-E2138 for function values, aborts in fn literals,
  missing clauses, capture overflow and multi-arity exports.

## The UTF-8 rule (R2 open item)

Every string literal is valid UTF-8 by construction (seed/HEADS :tokens R4 RULE). 41-a64gen therefore reads an ASCII
byte of a code-relative string in line (bounds checked against the pair and code_length) and calls the C helper only for
other strings, non-ASCII bytes or out-of-range indexes; the loader is unchanged. Embench xgboost (`kexe-benchmark raw`,
20 calls + 2 warmup per sample, 6 alternating samples, load average 125):

| xgboost built by | ms per call (6 samples) | median |
|---|---|---|
| R3 seed cbae36dc | 2426 2395 2400 2427 2442 2425 | 2425 |
| R4 seed 4cae021c (same generator as e9598b28) | 27.2 27.4 27.1 27.6 28.1 27.6 | 27.5 |

The R3 code re-validated the 10.9 KB literal on every `string-code-point-at` call (quadratic in the literal length); fuel
is unchanged (1,587,388 per call in both).

## Open

- Narrower than the reference, refused by name: fn-ref of a multi-arity defn, multi-clause `[:fn ..]` types,
  multi-source map, `+`/`inc` as callbacks, typed-list/set sources for map/filter/reduce, inference of untyped callable
  parameters across call sites (conformance closures).
- `(list ..)` is a `[:list T]` in the seed; the reference reads it as a pair chain where no type is given, and stage-0
  refuses `count`/`conj` on it natively (4 positives use r4.spec).
- Closure creation allocates `1 + max(0, k-1)` pairs; the seed source uses closures only off the hot paths (vector and
  pair budgets of the self-compile are unchanged in practice: seed-1 builds with the default seed_run limits).
- g3.sh does not include seed/tests/r4/neg yet (GATES request); unit tests of 30-lower/41-a64gen were not rerun.
