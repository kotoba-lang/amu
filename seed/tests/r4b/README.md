# R4B conformance programs: values by reference (owner R4B)

Gate: `scripts/seed/gr.sh r4b` (positives equal to the stage-0 oracle `r4b.oracle`, or to `r4b.spec` where stage-0
refuses; negatives refused). Oracle: `scripts/seed/oracle.sh r4b`. Capability programs: `seed/tests/r4b/check-caps.sh`
(they need grants and resources, which gr.sh does not give).

* `feat/` 28 programs: records by reference (`[:ref :kw]` through an ns `(:schemas {..})` clause, a defrecord keyword, or an
  inline schema), recursive and mutually recursive schemas, forward defrecord references, nested records and `assoc`,
  `[:list [:ref R]]`, `[:option [:ref R]]`, `[:result [:ref R] E]`; `:bytes` parameters, results, record fields, list items
  and loop values, `bytes-empty/count/at/concat/slice`, `string-from-utf8` (and its traps); 6, 7, 8, 9 and 16 parameters
  (stack-passed beyond 7, forwarded, rotated through a self tail call); vector literals of 65..128 integer literals as an
  expression, a def and a fresh copy; a loop of 15 bindings.
* `neg/` 16 negatives (E2179 E2178 E2108 E2104 E2105 E2116 E2128 E2111). `r4b-neg.oracle` marks the 6 that stage-0 accepts
  (n02 17 parameters, n03 a 6-parameter export, n07 a 65-item non-literal vector, n12 a record capture, n15 a fn type over
  :bytes, n16 a 21-binding loop): the seed's subset is narrower there, by name.
* `caps/` 6 capability programs: wires 3 (:hash/sha256), 33 (:env/read), 34 (:fs/browse), 41 (:io/read) and wire 35
  `:string -> :bytes` in both spellings; `caps/caps.oracle` recorded with stage-0 (`check-caps.sh --stage0 --record`).

Stage-0 quirks met while writing them (the programs use the forms stage-0 accepts, so the oracle is stage-0's):
keyword projection of a let-bound record taken from a record field ("runtime KIR record projection rejected"), `count` on a
let-bound `[:list [:ref R]]` of a :schemas record ("got :i64"), and a record with an `[:option [:ref R]]` field (feat/21,
"runtime KIR record construction rejected", in r4b.spec). Stage-0's vector literal limit is 128 items, which the seed adopts.
