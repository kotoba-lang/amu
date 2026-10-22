# ADR-0362 -- The rule-6 facts get a producer: one additive wire-42 request, `SUBGROUP`

- Status: accepted as design. The protocol-table entries (decision 1's verb
  code, decision 2's field count, decision 3's refusal) are IMPLEMENTED
  (2026-10-23, amendment below). The consumer parser (decision 4) is
  IMPLEMENTED (2026-10-23, slice-3 amendment below). The producer's answer
  remains unimplemented and lands with the ADR 0371 GPU provider track.
  Nothing is measured; no `:measured?` flag moves and no workgroup row is
  touched.
- Date: 2026-10-23
- Tracking: JUN-56 (the dispatch contract). Parent JUN-55. Serves the
  variant rows JUN-57 (ADR-0361), JUN-58 (ADR-0360), JUN-59 (ADR-0356)
  and JUN-60 (ADR-0357).

## Context

ADR-0356 rule 6 gates every `:subgroup-reduce` row on two descriptor
facts -- `:subgroup-size` (the compute-stage subgroup width) and
`:subgroup-ops` (the subgroup operations the fold needs: `:basic` and
`:shuffle-relative`) -- and the producer of those facts does not exist.
ADR-0360 and ADR-0361 name the gap exactly: the wire-42 answers carry no
such facts (`INFO` is four fields -- ADR 0371 decision 3 froze it there
after the superseded fifth-field shape -- and `DEVCLASS` is one class
word), so every rule-6 row today selects only for a descriptor a future
probe or provider fills in, and fails closed to `:baseline` without them.
This ADR is the "separate design decision" those ADRs left open: how the
facts are produced and carried.

## Decision 1: one additive request verb, `SUBGROUP`

Wire 42 gains one request verb, `SUBGROUP` (no arguments), parallel to
`DEVCLASS`: the guest asks, the provider answers what the device reports.
It takes verb code 18 in `tools/gpu_compute_protocol.kotoba` (the next
free after `FREE` = 17; the verb code is public ABI like the refusal
index -- append, never renumber). The framing, handle numbering, `!`
refusal prefix and the meaning of every existing verb are unchanged.

## Decision 2: the answer is exactly two fields

`SUBGROUP` answers exactly two `|`-separated fields (the protocol table's
"every verb has an exact field count" rule applies):

    <size>|<ops>

- `<size>` -- decimal digits, the subgroup size the device reports FOR
  THE COMPUTE STAGE (Vulkan: `VkPhysicalDeviceSubgroupProperties`'s
  `subgroupSize`, counted only when `supportedStages` includes
  `VK_SHADER_STAGE_COMPUTE_BIT`). Wire 42 dispatches compute; a width
  that is not a compute-stage fact is not this answer.
- `<ops>` -- zero or more space-separated tokens from one fixed
  vocabulary, the Vulkan 1.1 core `VkSubgroupFeatureFlagBits` names
  lower-cased (verified against the Khronos registry 2026-10-23):
  `basic`, `vote`, `arithmetic`, `ballot`, `shuffle`, `shuffle-relative`,
  `clustered`, `quad`. A token means the bit is set AND supported in the
  compute stage (the provider intersects `supportedOperations` with
  `supportedStages` before answering). Bits outside the core eight
  (`rotate`, `rotate-clustered`, `partitioned`) are masked off in v1 --
  the fold needs only `basic` and `shuffle-relative`, and a future bit
  appends a token only together with the consumer that understands it.
  An EMPTY `<ops>` field is a legal answer meaning "no subgroup
  operations in compute" -- a fact, not a refusal.

## Decision 3: refusals stay named, and a refusal is not a fact

When the device reports no compute-stage subgroups at all (or the
provider serves no GPU), the provider answers a named refusal in ADR
0371's `!<code> <text>` scheme: `gpu/no-compute-subgroups`, appended at
refusal index 35 (the list is public ABI: "append, never renumber").
A refusal reaches the selection gate exactly like an absent fact:
`:baseline`, fail closed. Nothing guesses a subgroup size from a vendor
name.

## Decision 4: the consumer half is total and all-or-nothing

The parsed answer becomes the descriptor keys rule 6 already consumes:
`:subgroup-size` (a positive integer) and `:subgroup-ops` (a set of
keywords; the token/keyword map is 1:1 with the hyphen preserved,
`shuffle-relative` -> `:shuffle-relative`, the `device-class-tokens`
idiom). The parse is all-or-nothing: a non-digit `<size>`, an unknown
token, or a field count other than 2 makes the WHOLE answer an absent
fact (rule 6 then answers `:baseline`). A partially trusted answer must
not select a variant. The gate itself is unchanged -- this ADR produces
the facts the gate already demands, it does not relax one condition.

## Where the producer reads the facts (vendor documentation, not
measurements)

Vulkan: `VkPhysicalDeviceProperties2` chained to
`VkPhysicalDeviceSubgroupProperties`, read once at provider startup the
way `INFO`/`DEVCLASS` are read. On Apple through MoltenVK the same
struct is the intended source and Apple's SIMD-group width is 32 per the
Metal feature-set tables; whether MoltenVK fills the struct to that
value is UNVERIFIED here -- nothing probed this host (the probe that
could was removed with the C loader; ADR-0355's honest state).

## Interaction with ADR 0371

ADR 0371 decision 3 (Proposed, not owner-accepted) says the protocol-v1
verb set "does not change". This ADR amends that sentence to: the verb
set grows only by additive verbs that protocol-v1 guests never send;
framing, handle numbering, the `!` refusal prefix and the meaning of
every existing verb do not change. Existing generated guests send no
`SUBGROUP` line and see no new answer shape, so the byte-compatibility
decision 3 protects is preserved. If the owner accepts decision 3 in its
strict unamended form instead, this ADR's decision 1 needs re-decision
and the gap re-opens -- named here, not hidden.

The implementation lives in the provider track, not here: the protocol
table's verb/field/refusal entries (`tools/gpu_compute_protocol.kotoba`
and its test), the provider's answer, and the consumer parser are three
separate slices, none landed by this ADR. Until they land, the facts
still have no producer and every rule-6 row keeps answering `:baseline`
for a descriptor without them -- behavior unchanged by this document.

## State honesty

This ADR is one design decision (accepted design only). No code, no
tests and no measurement land with it. No `:measured?` flag moves: the
variant rows stay UNMEASURED on their own contracts (ADR-0356 rule 4 and
the per-vendor measurement contracts of ADR-0357/0360/0361), the
workgroup rows of ADR-0355/0358 keep their labels untouched, and the
JUN-58 measurement remains blocked on the ADR 0371 provider for its own
reasons (wire 42 has no route today).

## Amendment 2026-10-23: slice 1 landed (the protocol-table entries)

`tools/gpu_compute_protocol.kotoba` now carries the SUBGROUP verb (code 18),
the answer field count (constant 17 = 2) and the refusal
`gpu/no-compute-subgroups` (index 35, appended; constant 16 = 35), with the
table's own tests extended (114 cases, both targets green,
`docs/evidence/gpu-compute-protocol-subgroup-20261023/`). Slices 2 (the
provider's answer) and 3 (the consumer parser) remain unimplemented, so no
rule-6 fact has a producer yet and the fail-closed behavior above is
unchanged. No measurement, no `:measured?` move, no workgroup row touched.

## Amendment 2026-10-23 (slice 3): the consumer parser landed

`kotoba.compiler.accelerator-targets/device-from-subgroup` parses the answer
(`<size>|<ops>`) into the two descriptor keys rule 6 already consumes
(`:subgroup-size` a positive integer, `:subgroup-ops` a keyword set), in
both readings (the W3 `:kotoba` arm and the host arm). All-or-nothing per
decision 4: every named failure trigger answers nil (an absent fact). Two
points decision 4 left open are pinned by the implementation: the `<ops>`
tokens are read by the wire's own token rule (runs of non-space bytes
separated by one or more spaces -- byte 32 the request grammar's only
separator -- so a separator-only field is also zero tokens), and a
duplicate token is the same set fact and collapses. Tests cover the
contracts and the decision-4 seam end to end (the parser's answer feeds
`select-variant` rule 6; missing facts fail closed to `:baseline`); see
`docs/evidence/gpu-subgroup-consumer-parser-20261023/`. Slice 2 (the
provider's answer) remains unimplemented: no live wire feeds the parser,
no rule-6 fact has a producer, and the fail-closed behavior above is
unchanged. No measurement, no `:measured?` move, no workgroup row touched.
