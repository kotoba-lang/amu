# ADR-0362 slice 2 (pure half): the SUBGROUP producer's answer mapping, 2026-10-23

Tick: amu-gpu chain (bot/amu-gpu-chain). Tracking: JUN-56 (the dispatch
contract), parent JUN-55.

## What landed (implemented, with tests)

ADR-0362 named three implementation slices. Slices 1 (protocol-table
entries) and 3 (the consumer parser) were landed earlier; this directory
covers slice 2's PURE HALF -- the mapping the provider will call -- and
nothing else:

- `kotoba.compiler.accelerator-targets/subgroup-answer` answers the
  wire-42 SUBGROUP payload `"<size>|<ops>"` for one device record -- the
  `VkPhysicalDeviceSubgroupProperties` fields as data
  ({:subgroup-size <int>, :supported-stages <VkShaderStageFlags>,
  :supported-ops <VkSubgroupFeatureFlags>}) -- or nil, which the provider
  answers as the named refusal `gpu/no-compute-subgroups` (the protocol
  table's refusal 35; decision 3 treats the refusal exactly like an
  absent fact).
- A payload answers exactly when the record reports compute-stage
  subgroups: the size is a positive integer AND
  VK_SHADER_STAGE_COMPUTE_BIT (0x20) is set in :supported-stages.
  `<ops>` is the set tokens of the core eight VkSubgroupFeatureFlagBits
  bits set in :supported-ops, in the fixed vocabulary order
  (`subgroup-op-tokens`'s order), space-separated. An EMPTY `<ops>` is
  the legal zero-ops fact (decision 2), not a refusal.
- Bit values, verified against the Vulkan registry refpages
  (docs.vulkan.org/refpages/latest/refpages/source/ -- the
  VkShaderStageFlagBits and VkSubgroupFeatureFlagBits pages, fetched
  2026-10-23): COMPUTE stage 0x00000020; core eight ops
  basic 0x1, vote 0x2, arithmetic 0x4, ballot 0x8, shuffle 0x10,
  shuffle-relative 0x20, clustered 0x40, quad 0x80. Bits outside the
  core eight -- partitioned 0x100, rotate 0x200, rotate-clustered
  0x400 -- are masked off in v1 (decision 2). These are VENDOR-
  PUBLISHED struct field values, not measurements.
- Both readings, as the module's W3 idiom requires: the `:kotoba` arm
  (sg-compute-stage-bit / sg-bits-doc / sg-token-at / sg-bits-at /
  sg-ops-emit / subgroup-answer, document walks) and the `:default` arm
  (subgroup-compute-stage-bit / subgroup-op-bits / subgroup-answer).
  As with slice 3: the nbb/sci read parses both arms (this gate run
  covers the kotoba arm's syntax), but the kotoba arm's EXECUTION has no
  runner here and is UNVERIFIED.

Tests: `test/kotoba/compiler/accelerator_targets_test.cljk` gained
`subgroup-answers-are-produced-from-the-device-record`: the compute-stage
gate (payload exactly when COMPUTE is in supported-stages; 13 nil cases
for every named failure trigger), the eight single-bit pins (a changed
bit answers a different token and fails), the vocabulary-order pin, the
mask-off pins (partitioned/rotate/rotate-clustered answer no token), the
empty-ops fact, the producer/consumer round-trip seam (the payload the
producer emits parses back to the exact rule-6 descriptor through
slice 3's `device-from-subgroup`), and determinism.

## Verification (runner output, not paraphrase)

Touched namespaces, scoped run of the gate engine (kbb --backend sci):

    Testing kotoba.compiler.accelerator-targets-test

    Testing kotoba.compiler.accelerator-variants-test

    Ran 17 tests containing 2228 assertions.
    0 failures, 0 errors.

(scoped-gate-touched-namespaces.txt in this directory). Baseline before
this diff, same scoped run (measured before the first edit, verbatim
tail: "Ran 16 tests containing 2198 assertions. 0 failures, 0 errors."):
16 tests, 2198 assertions, 0 failures, 0 errors -- the +1 test / +30
assertions are this slice's.

The FULL gate (`kbb --backend sci --classpath "src:test:$(kbb -Spath
-M:test)"` run-tests.cljk`) is RED AT BASE and unchanged by this diff:
it aborts at load with zero tests run -- "Error: Could not find
namespace: kotoba.form" via `kotoba.compiler.js-value-target`'s
`:default` arm (the W3 port; on the kbb route `kotoba.form` resolves
only to `src/kotoba/form.kotoba`, which nbb cannot load). Same abort,
same cause as the slice-3 evidence (full-gate-kbb.txt here). Named, not
hidden; outside this diff. The suite is NOT green and this report does
not claim it is.

## State honesty

This is an implementation slice (code + tests) of the PURE mapping only.
IMPLEMENTED: the record -> payload mapping (`subgroup-answer`).
UNIMPLEMENTED: the provider's Vulkan read of
VkPhysicalDeviceSubgroupProperties and its wire reply (the ADR 0371 GPU
provider track), so no live wire feeds this function, no rule-6 fact has
a live producer, and every rule-6 row keeps failing closed to
`:baseline` -- behavior unchanged by this slice. No measurement was
taken (no provider, no wire 42 route), no `:measured?` flag moved and no
workgroup row was touched; the variant rows stay UNMEASURED on their own
contracts (ADR-0356 rule 4, ADR-0357/0360/0361).

Named residue, not hidden: the `:kotoba` arm of `string-ascii-lower`
(appended 2026-10-22 with the W3 port) renders code points through
`string-from-i64`, which the dialect's own desugar defines as i64 ->
DECIMAL string (`__kotoba_string_from_i64`, kotoba-sema frontend/analyze
1077-1113). Under that definition the arm's lowercasing walk would
append decimal text, not characters. The kotoba arm's execution is
unverified (no runner), so this is a reading-level observation, not a
measured failure; it is another track's line to confirm and fix. This
slice's kotoba arm uses `string-from-i64` for the decimal `<size>`
rendering, where the decimal definition is the correct one.
