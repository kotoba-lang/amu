;; R5 expectations that do NOT come from a stage-0 run (owner R5D). Format: `<label> <value>` (one per line; `;;` comments).
;; Used only where r5.oracle says `refused` for a POSITIVE. Every other positive's expectation is its r5.oracle value.
;;
;; Stage-0 (build/native-image/amu-native, 2026-10-03) compiles these programs but its verifier refuses the artifact with
;; "native artifact oracle inconclusive: the sealed value cannot be re-derived" (phase :verify, after code generation).
;; Measured: 100 stateful calls pass (conformance state/loop_accumulator), 400 and 5000 do not, a 63-module call chain
;; does not; the cause inside the verifier's re-derivation was NOT isolated (a re-execution budget is the likely one).
;; The values are derived by hand, one line of arithmetic each:
feat/p13-state-in-loop-call 12497500
;;   sum of i for i in 0..4999 = 4999 * 5000 / 2
feat/p13b-state-in-loop-call-400 79800
;;   sum of i for i in 0..399 = 399 * 400 / 2
feat/p20-depth-64 63
;;   m63/f = 1 and m(k)/f = 1 + m(k+1)/f, so m1/f = 63; the chain root main (depth 1) .. m63 (depth 64) is within
;;   max-project-depth 64 (n15, one module deeper, is refused by stage-0 with "project dependency depth exceeds limit")
;; Stage-0 native refuses with "native artifact contains an unsupported effect", while feat/p10 (a try/catch around calls
;; that abort in other functions and another module) runs natively on stage-0 (11005); so the refusal follows the
;; handle/catch spelling (cause not isolated). Reference meaning:
;; (handle body (catch e h)) eliminates :abort exactly as (try body (catch e h)) (lang/state-ability.edn :install).
feat/p23-handle-catch 705
;;   (chk -1) throws 7 -> 7 * 100 = 700; (chk 5) = 5; 700 + 5
