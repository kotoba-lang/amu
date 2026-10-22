Verbatim copies of the kotoba-lang conformance programs (`lang/conformance/*/*.kotoba`, kotoba-lang commit 919232de5831f6b3ee4ad0640b81842f41ccdf5f, 55 files), so the gates are hermetic.
They are untyped Clojure-style programs outside the seed subset. They are used by the refusal gate (scripts/seed/g3.sh: each must be refused with the golden text of the rung) and by the rung tables; they are NOT compiled for results.
The R1-level typed adaptations with stage-0 results are in seed/tests/r1/.
