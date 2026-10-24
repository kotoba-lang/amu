amu-gpu tick 2026-10-23 -- ADR-0360's second decision: the Apple row is
NARROWED to the measured device (JUN-58's own open question (2)).
Evidence log; no POSIX shell files.

WHAT CHANGED (one design decision + its thin implementation slice):

1. docs/adr/0360-gpu-apple-subgroup-reduce.md -- new amendment "the
   second decision: the row is NARROWED to the measured device".
   DECIDES question (2) of the measurement amendment ("what the Apple
   row should select given the measured cell") as NARROWING. Question
   (1) -- whether a native Metal harness satisfies the measurement
   contract -- REMAINS PROPOSED and undecided. Rationale recorded both
   ways: narrow, not keep (the row's basis is measured-contradicted on
   the named device, twice, both routes); narrow, not delete (the
   evidence is one device and speaks for M1 Max only -- the uB5G rule).
   Scope stated plainly: W > 256 on M1 Max is UNMEASURED; the demotion
   there follows the monotone trend toward the fail-safe arm and claims
   no measurement.

2. docs/adr/0356-gpu-kernel-variant-selection.md -- rows table, apple
   cell: the "what the row selects ... is PROPOSED, decided nowhere"
   clause replaced by the decided state (narrowed to the measured
   device; a Metal-native simdgroup row stays NOT designed). The
   :measured? lock's blocker text now names question (1) as the
   remaining blocker.

3. src/kotoba/compiler/accelerator_variants.cljk -- select-variant
   implements the narrowing (uB5G idiom): a descriptor whose name parts
   (:device, :name, or the :vendor name key) carry the measured-device
   fragment "m1 max" (case-insensitively) answers :baseline for the
   reduce shape on BOTH Apple routes, at every W, with the refutation
   appended to :basis ("APPLE ROW NARROWED ..."). Every other Apple
   device (including an unnamed {:vendor-id 4203} descriptor) keeps
   :subgroup-reduce; non-Apple vendors untouched; a refuted device
   WITHOUT rule-6 facts keeps the ordinary fail-closed :baseline basis
   and NO narrowing note (the note is only the row's own demotion).
   variant-bases :subgroup-reduce and the select-variant docstring
   updated to the decided state. :measured? UNCHANGED (false on every
   answer -- question (1) undecided).

4. test/kotoba/compiler/accelerator_variants_test.cljk -- new deftest
   the-apple-row-is-narrowed-on-the-measured-device: 5 device spellings
   x 4 targets x 3 operators x 5 workgroup sizes answer :baseline with
   the note (:measured? false); 5 unrefuted descriptors x 4 targets keep
   :subgroup-reduce without the note; non-Apple vendors with an
   "M1 Max"-named descriptor are untouched (4 vendors); 3 facts-absent
   refuted shapes answer plain fail-closed :baseline with no note;
   determinism.

VERIFICATION (runner output, not paraphrase):

BEFORE (this host, measured before the first edit, kbb --backend sci,
scratch runner gpu_scoped_gate.cljk over the 7 GPU-owned namespaces):

    Ran 84 tests containing 4759 assertions.
    0 failures, 0 errors.

AFTER (same command, output verbatim in scoped-gate.txt):

    Testing kotoba.compiler.accelerator-targets-test
    Testing kotoba.compiler.accelerator-variants-test
    Testing kotoba.compiler.accelerator-test
    Testing kotoba.compiler.accelerator-pipeline-test
    Testing kotoba.compiler.accelerator-subgroup-reduce-test
    Testing kotoba.compiler.accelerator-spirv-test
    Testing kotoba.compiler.accelerator-spirv-compile-test

    Ran 85 tests containing 6336 assertions.
    0 failures, 0 errors.

Full gate (kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)"
run-tests.cljk, output verbatim in full-gate.txt): RED AT BASE, unchanged
by this diff -- aborts at namespace load with "Could not find namespace:
kotoba.form" (kotoba.compiler.js-value-target, the upstream W3 port;
outside this diff). No green-suite claim.

STATE HONESTY:
- ACCEPTED + IMPLEMENTED: the narrowing decision (ADR-0360's second
  decision) and its selection code + tests.
- PROPOSED, undecided: question (1) (native-harness measurement
  contract); a Metal-native simdgroup row (still NOT designed).
- UNMEASURED: no measurement was taken this tick -- every number above
  is a citation of the merged record (PR #1343/#1347/#1348, 009c86ef /
  7f1c7faf / ADR-0360's measurement amendment). W > 256 on M1 Max is
  UNMEASURED and the demotion there claims none. No :measured? flag
  moved (all answers false) and no workgroup row (ADR-0355/0358) was
  touched.

NOTE (tooling defect, this tick): the patch wire's escape-drift
auto-corrector stripped a required backslash before a quote inside a
docstring once (kbb failed at load with "m1 is not ISeqable" -- the
escaped "m1 max" became a bare quote and the reader took m1 as a
symbol). Fixed by an exact byte-level replacement and re-verified by
od(1) before the green gate run. Named, not hidden.
