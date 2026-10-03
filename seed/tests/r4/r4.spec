;; R4 expectations for the positives stage-0 REFUSES on native code (see r4.oracle): count / conj on a (list ..) or a rest
;; parameter (stage-0 types them as an :i64 pair chain natively) and a fn literal in a [:fn ..] result position (stage-0 does
;; not pass the result contract to the literal: "expected i64, got string"; lang/guest-grammar.edn :callable-type says it
;; does). conf/ values are lang/conformance/manifest.edn :expect (kotoba-lang 919232de); feat/ values are derived by hand,
;; the arithmetic below.
conf/fn-multi_arity 25
;; 16: (sum-all 1) = 1; (sum-all 1 2 3 4) = 1 + 10*3 + 2 = 33; (sum-all 0 5 5) = 0 + 20 + 5 = 25 -> 1 + 33 + 2500
feat/16-variadic 2534
;; 18: count 4 + 10*7 + 100*2 + 1000*0
feat/18-list 274
;; 20: 100 + (string-length "abc")
feat/20-result-contract 103
