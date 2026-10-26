# ADR-0362 slice 3: the SUBGROUP answer consumer parser, 2026-10-23

Tick: amu-gpu chain (bot/amu-gpu-chain). Tracking: JUN-56 (the dispatch
contract), parent JUN-55.

## What landed (implemented, with tests)

ADR-0362 named three implementation slices. Slices 1 (protocol-table
entries) and 3 (the consumer parser) are landed; this directory covers
slice 3:

- `kotoba.compiler.accelerator-targets/device-from-subgroup` parses one
  wire-42 SUBGROUP answer -- `<size>|<ops>` (decision 2) -- into the two
  descriptor keys rule 6 (ADR-0356) already consumes (decision 4):
  `{:subgroup-size <positive int> :subgroup-ops #{<keywords>}}`.
- The vocabulary is the eight Vulkan 1.1 core `VkSubgroupFeatureFlagBits`
  names, lower-cased, mapped 1:1 to keywords with the hyphen preserved
  (`subgroup-op-tokens`, the `device-class-tokens` idiom). An unknown token,
  a non-digit/zero/overflowing `<size>`, a field count other than 2, or a
  non-string answer makes the WHOLE answer nil (an absent fact) --
  all-or-nothing, exactly decision 4. An EMPTY `<ops>` is a fact (zero
  ops), not a refusal.
- Tokenization is the wire's own rule (the request grammar's): runs of
  non-space bytes separated by one or more spaces, byte 32 the only
  separator, so a separator-only field is also zero tokens. A duplicate
  token is the same set fact and collapses. These two points are parser
  decisions the ADR left to the implementation; they are recorded in the
  ADR amendment of this date.
- Both readings, as the module's W3 idiom requires: the `:kotoba` arm
  (document walks) and the `:default` arm. The nbb/sci read of the file
  reads both arms (reader conditionals read every branch), so the parse
  that ran in the gate below covers the kotoba arm's syntax too; its
  EXECUTION has no runner here and is unverified.

Tests: `test/kotoba/compiler/accelerator_targets_test.cljk` gained
`subgroup-answers-parse-into-rule-6-facts` (the two-field shape, the eight
tokens 1:1, the empty-ops fact, the token rule, duplicate collapse, 22
malformed answers all nil, determinism), and
`test/kotoba/compiler/accelerator_variants_test.cljk` gained
`rule-6-reads-the-facts-the-subgroup-answer-parses` -- the seam decision 4
names: the parser's answer feeds `select-variant` rule 6 and selects
`:subgroup-reduce`, while a missing op, a non-dividing size, and a
malformed answer each fail closed to `:baseline`.

## Verification (runner output, not paraphrase)

Touched namespaces, scoped run of the gate engine (kbb --backend sci):

    Testing kotoba.compiler.accelerator-targets-test

    Testing kotoba.compiler.accelerator-variants-test

    Ran 16 tests containing 2198 assertions.
    0 failures, 0 errors.

(scoped-gate-touched-namespaces.txt in this directory). Baseline before
this diff, same scoped run: 14 tests, 2164 assertions, 0 failures, 0
errors -- the +2 tests / +34 assertions are this slice's.

The FULL gate (`kbb --backend sci --classpath "src:test:$(kbb -Spath
-M:test)" run-tests.cljk`) is RED AT BASE and was red before this diff was
written (verified before the first edit): it aborts at load with zero tests
run -- "Error: Could not find namespace: kotoba.form" (full-gate-kbb.txt).
Named cause chain (outside this diff): `kotoba.compiler.js-value-target`
(W3 port, PR #1486) requires `kotoba.form` in its `:default` arm, and on
the kbb route `kotoba.form` resolves only to `src/kotoba/form.kotoba`,
which nbb cannot load. It is reachable from `run-tests.cljk`'s require
list through `kotoba.compiler.uefi-target-gate-test` ->
`kotoba.compiler.core` (also `kotoba.compiler.backend-evm-test`); a direct
`(require 'kotoba.compiler.js-value-target)` on the gate classpath fails
the same way. The suite is therefore NOT green and this report does not
claim it is. Fixing that module is another track's work; this tick reports
it only.

## State honesty

This is an implementation slice (code + tests). It produces NO measurement
and touches no `:measured?` flag and no workgroup row. The variant rows
stay UNMEASURED on their own contracts (ADR-0356 rule 4, ADR-0357/0360/0361
measurement contracts); the workgroup rows of ADR-0355/0358 keep their
labels. ADR-0362 slice 2 (the provider's SUBGROUP answer) REMAINS
UNIMPLEMENTED: no live wire feeds this parser, no rule-6 fact has a
producer, and every rule-6 row keeps failing closed to `:baseline` for a
descriptor without subgroup facts -- behavior unchanged by this slice.
