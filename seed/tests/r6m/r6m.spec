;; seed/tests/r6m/r6m.spec -- expectations of the r6m positives stage-0 (d2cb84f6, BOOTSTRAP-REFERENCE) refuses natively.
;; Format (gr.sh): `<label> <value>`; each value is hand-derived (agent SEEDLANG, 2026-10-04), the derivation in the line above.
;; p03: fact 10 + fib 15 + (sum 1..100) = 3628800 + 610 + 5050 (stage-0: "native artifact oracle inconclusive")
feat/p03-self-recursion 3634460
;; p09: bits(3.75) + bits(0.1) + bits(-2.75) + trunc(12.5 * 4.0) mod 2^64 (python struct '<d'; stage-0: typed values on native)
feat/p09-float-literal 4597499679601170892
;; p16: length "kotoba" + length "xy" (stage-0: if-some over a call answering [:option :string] refused, see the file)
feat/p16-if-some-string-call 8
