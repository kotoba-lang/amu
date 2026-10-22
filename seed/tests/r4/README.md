# R4 conformance programs (owner R4)

Gate: `scripts/seed/gr.sh r4` (positives equal to the stage-0 oracle `r4.oracle`, or to `r4.spec` where stage-0 refuses
natively; negatives refused). Oracle: `scripts/seed/oracle.sh r4`.

* `feat/` 32 programs, one R4 feature each: fn literals and closures (0-3 captures, known let-bound fns, nested captures of
  callables), fn-ref, invoke (typed), apply, map / filter / reduce (with and without init, defn names, fn values, vector and
  bool accumulators), multi-arity and variadic defns, list, contract-typed fn parameters ([:fn ..] parameter slots and
  results).
* `conf/` 5 of the 7 `lang/conformance/functions/` programs (kotoba-lang 919232de): callable_contracts, closure_list_result,
  contextual_invoke, multi_arity verbatim with an `(ns .. (:export [main]))` line; closures as a typed adaptation (its
  callable parameters annotated: the reference infers them across call sites). closure_bytes_result (:bytes) and
  lazy_sequences (lazy-*) are outside R4 and stay refused (G3 golden).
* `neg/` 26 negatives (E2101 E2103-E2105 E2111 E2134-E2139 E2001). `r4-neg.oracle` marks the 5 that stage-0 accepts
  (n01 n08 n09 n11 n15): the seed's subset is narrower there, by name.
