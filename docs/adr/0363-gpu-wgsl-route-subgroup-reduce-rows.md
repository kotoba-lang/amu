# ADR-0363 -- The WGSL route carries the Intel and ARM subgroup-reduce rows

- Status: accepted as design and implemented the same date (code + tests in
  `kotoba.compiler.accelerator-variants`); the extension to the Apple and
  NVIDIA rows is NOT decided here.
- Date: 2026-10-23
- Tracking: JUN-55 (parent), JUN-59 (Intel), JUN-60 (ARM).
- Closes: the open question the 2026-10-23 WGSL-arm amendment of ADR-0356
  named ("Extending the Intel/ARM rows to :wgsl-v1 ... proposed here and
  decided nowhere").

## Decision

The WGSL route -- one route under the two names callers may hold for it, the
api name `:webgpu` and the emitter target name `:wgsl-v1`, exactly the
`:vulkan` / `:glsl-v1` idiom of ADR-0359 decision 3 -- now carries the
Intel (JUN-59) and ARM (JUN-60) `:subgroup-reduce` selection rows.
`select-variant` answers `:subgroup-reduce` for `:intel` and `:arm` on that
route under the same gate the Vulkan route uses: ADR-0356 rule 3 (emission
admission -- satisfied 2026-10-23 by the WGSL arm and `lower`'s
(:wgsl-v1, :subgroup-reduce) admission) and rule 6 / ADR-0357's capability
precondition (the descriptor must report `:subgroup-ops` containing `:basic`
and `:shuffle-relative` and a `:subgroup-size` that divides `W`; every other
answer fails closed to `:baseline`).

The Apple (ADR-0360) and NVIDIA (ADR-0361) rows do NOT move: their ADRs
scope them to the Vulkan route, and "one vendor per decision" (ADR-0356's
own consequence) means extending either is a separate decision this ADR does
not make. On the WGSL route `:apple` and `:nvidia` keep answering
`:baseline`. What speaks for leaving them there for now is recorded so a
later decision can disagree with it on purpose: their vendor-default
emission targets are `:msl-v1` and `:cuda-v1` (`accelerator-targets`,
`vendor-default-target`), so unlike Intel/ARM they have no default path
that this row would light up, and each already carries a route-scoped row
whose scope its own ADR set.

## Rationale

1. **Rule 3 is satisfied, and rule 3 is the ordering rule, not a ban.** The
   2026-10-23 WGSL arm landed with `lower`'s admission in both readings. A
   variant is selected only where it can be emitted; now it can be. The
   CUDA `:warp-shuffle-reduce` row is the precedent that a selection row
   does not require an in-repo execution path -- it selects today and CUDA
   has never executed anything here.
2. **The Intel and ARM designs name the WGSL builtin.** ADR-0356's Intel
   row text says the emission "queries the subgroup size at runtime
   (`gl_SubgroupSize` / the WGSL subgroup builtin)", and ADR-0357 P2's last
   sentence refuses only "a language surface without those builtins" --
   the rows were designed surface-parametric, and the WGSL surface has the
   builtins (spec-pinned 2026-10-23 in the WGSL-arm amendment).
3. **The WGSL route is the vendor-DEFAULT emission target for `:intel` and
   `:arm`.** `target-for` answers `:wgsl-v1` for an api-less Intel or ARM
   device (`vendor-default-target`). Without this extension the two rows
   can never select on their own vendors' default path -- a row that
   answers only when the caller happens to name `:vulkan` is half a row.
4. **One gate, no new fact keys.** Rule 6 consumes the same descriptor
   vocabulary on both routes (`:subgroup-size`, `:subgroup-ops`). The
   WGSL `subgroups` feature is the same capability fact: whatever future
   producer fills the descriptor (the ADR-0362 wire-42 SUBGROUP payload, or
   a WebGPU adapter probe answering the same keys) answers it. This ADR
   invents no key and no producer.

## Non-claims (every one of these is a state the code carries)

- **UNCOMPILED.** No WGSL compiler or validator exists on the implementing
  host (`which tint naga wgsl_analyzer` -- empty); the emission's text
  contracts are the whole verification, the same regime as the nvcc-less
  CUDA arm.
- **UNMEASURED.** No WebGPU execution path exists in this repository and no
  hardware ran the variant on this route. Every answer keeps
  `:measured? false`; rule 4's lock is untouched and no workgroup row of
  ADR-0355/0358 is affected (different axis).
- The rule-6 fact producer still does not exist (ADR-0362: the provider's
  Vulkan read and wire reply are the ADR 0371 track, unimplemented), so on
  BOTH routes every row still fails closed to `:baseline` without a filled
  descriptor. This ADR widens where a FILLED descriptor selects; it does
  not conjure facts.
- The measurement contract per vendor (JUN-59, JUN-60) is unchanged and
  stays keyed to the tested device class. A `:wgsl-v1` measurement needs a
  WebGPU execution path that does not exist; until one does, this route's
  rows have no measurement channel at all.

## Consequences

- `route-names` gains the WGSL pair `:webgpu` / `:wgsl-v1`; the sets stay
  disjoint and selection stays total and deterministic (rules 1 and 5).
- The seal/verify regime is unchanged: the selected variant is recorded in
  the seal and the artifact regenerates with it (rule 5); a `:wgsl-v1`
  `:subgroup-reduce` artifact seals and verifies exactly as the `:glsl-v1`
  one does.
- The MSL route is untouched: `:msl-v1` / `:metal` keep answering
  `:baseline` everywhere (rule 3 -- the MSL emitter admits `:baseline`
  only). A Metal simdgroup row remains not designed (ADR-0360 said so and
  this ADR does not design it).
- `:amd`, `:unknown`, `:qualcomm` and any other vendor keep answering
  `:baseline` on every route.
