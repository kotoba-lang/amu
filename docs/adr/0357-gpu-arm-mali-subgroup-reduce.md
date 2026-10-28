# ADR-0357 -- The ARM row: a subgroup-size-parametric reduce for Mali

- Status: accepted as design. Nothing is implemented; the row is UNMEASURED.
  [STATUS CORRECTED 2026-10-24 (the debt named in docs/evidence/gpu/
  adr0356-intel-arm-route-prose-20261024.txt): the "Nothing is implemented"
  clause is stale on the IMPLEMENTATION axis -- this file's own 2026-10-22
  amendment below ("the emission and the shared selection row now exist")
  and ADR-0356's rows table (the `:subgroup-reduce` | arm row, implemented
  2026-10-22) contradict it, and that amendment predates ADR-0363's WGSL
  route which this row also rides. The implementation state today: the
  shared subgroup-size-parametric emission -- the Vulkan/GLSL arm
  (ADR-0359, commit 53248c112) and the WGSL arm (`emit-wgsl`, commit
  905a15b5a) -- and the shared selection row (`kotoba.compiler.accelerator-
  variants`, the `#{:intel :arm ...}` vendor set; `:glsl-v1` and `:wgsl-v1`
  both carry :arm, checked live this tick) are IMPLEMENTED. The UNMEASURED
  clause is unchanged and governs: no Mali device exists in this fleet and
  the measurement contract below has not run. The line above describes the
  state at adoption, 2026-10-19. Prose only -- nothing but this Status
  line moves in this correction.]
- Date: 2026-10-19
- Tracking: JUN-60 (ARM). Parent JUN-55. This is the design decision that
  ADR-0356 deferred ("ARM (JUN-60) is deliberately not designed in this ADR
  ... one vendor per decision").

> **Dated note (2026-10-24, ADR 0371).** The GPU execution path this ADR
> refers to is deleted: the C loader `tools/kexe_loader.c`, and wire 42's
> `:gpu/compute` brokered by `tools/kexe_gpu_vulkan.c`. ADR 0371 replaced
> it with a provider process that the static launcher starts and that
> speaks the same wire-42 protocol. Since #1510 two things hold: main's
> compiler refuses that provider's `--format platform-linked` build, and
> its qualifications are outside mandatory native CDCI (`AGENTS.md`). So
> no current route executes a GPU artifact. The text below is kept as
> written.

## Decision

The ARM row of the per-vendor kernel variant table is a subgroup-reduce
variant for `:reduce` kernels on Mali devices: fold within the subgroup using
subgroup arithmetic, then one write barrier and a cross-subgroup tree over
the `W/S` partials. It is the same reduction shape as the Intel row of
ADR-0356, and it deliberately reuses that row's **subgroup-size-parametric
emission** when that emission lands -- the emitted code queries the subgroup
size at runtime and never bakes a width into the fold.

The parametric emission is not a convenience, it is the ARM decision. Mali
subgroup width is chosen by GPU generation and device, spanning 4 to 32. A
fold baked to any one width is wrong on the others; a fold that asks is not.
(Intel's subgroup size is device-chosen among 8/16/32; Mali widens the same
imperative from a design nicety to a correctness requirement.)

Selection predicate: vendor `:arm` (as ADR-0355 classifies it: PCI 5045, or
a `mali` device-name fragment), op `:reduce`, operator in `{:sum :max :min}`,
workgroup `W >= 32`. Everything else -- elementwise kernels, other vendors,
sub-32 workgroups -- answers `:baseline`. The rules of ADR-0356 bind this
row unchanged: totality, semantics preservation, emission admission first,
the UNMEASURED lock, determinism.

## Two portability conditions on the emission (P1, normative)

1. **The fold preserves the baseline `:sum` association, or the claim is
   scoped.** The baseline reduction is the fixed `W/2` tree of
   `accelerator.cljk:73-74`; folding contiguous lanes inside a subgroup
   re-associates the sum, and for cancellation-sensitive inputs the change
   is not confined to the low bits: with `W=32`, `x[0..2] = [1e20, -1e20, 1]`
   the baseline tree answers `0` while a four-lane contiguous fold may answer
   `1`. Subgroup arithmetic additionally does not guarantee any association
   matching the tree. Therefore either (a) the emitted fold applies the
   baseline tree's operand order to each subgroup's lane block (same shape,
   narrowed to `S` lanes), keeping per-stage results aligned with the
   baseline, or (b) the `:sum` claim is scoped to well-conditioned inputs
   ("low bits only, for inputs without catastrophic cancellation") and the
   cancellation-sensitive regime is recorded as UNMEASURED divergence from
   the baseline. ADR-0356 rule 2 is amended by this scope; `:max`/`:min`
   keep their bit-for-bit rule within the ordinary-value domain.

2. **Partial compaction uses subgroup IDs, not `lid` arithmetic.** Placing
   one result per subgroup into the dense `W/S` partial array may not use
   `local_invocation_index % S` to elect a leader or `local_invocation_index
   / S` as the partial index: WGSL defines no relationship between the local
   index and the subgroup IDs. The portable emission requires
   `subgroup_invocation_id` plus `subgroup_id`/`num_subgroups` (Vulkan
   equivalents included). A device or language surface without those
   builtins answers `:baseline`; the `S`-strided cross-subgroup tree may
   keep using `S` as a stride over the partial array, since that indexing is
   by construction dense.

## Safety condition: `S` divides `W` (mechanically checked)

The fold assumes one subgroup width `S` divides the workgroup `W`. The KIR
admits exactly the eleven powers of two in `[1, 1024]` (checked against the
real `accelerator/validation-errors`: 11 accepted sizes; all 2037
non-powers-of-two in 1..2048 carry `:invalid-workgroup-size`). For every
admissible `W >= 32` and every Mali width `S` in `{4, 8, 16, 32}`, `S`
divides `W` -- verified across all six sizes 32..1024 for all four widths
(twenty-four checks, all true). The `W >= 32` bound is therefore sufficient:
below it, some device-chosen `S` would not divide `W`, and those workgroups
answer `:baseline`.

## What the variant buys, stage-counted (UNMEASURED as speed)

Numbers from the real WGSL emitter's baseline reduce (`accelerator/lower`,
`:wgsl-v1`, `:reduce`), where the dynamic barrier count is 1 (the load
barrier) plus the emitted stride loop's iterations, mechanically enumerated
from `stride = W/2 ... stride = stride/2`:

| W | baseline barriers | variant barriers, S=4 | S=8 | S=16 | S=32 |
|---|-------------------|-----------------------|-----|------|------|
| 32   | 6  | 4 | 3 | 2 | 1 |
| 64   | 7  | 5 | 4 | 3 | 2 |
| 128  | 8  | 6 | 5 | 4 | 3 |
| 256  | 9  | 7 | 6 | 5 | 4 |
| 512  | 10 | 8 | 7 | 6 | 5 |
| 1024 | 11 | 9 | 8 | 7 | 6 |

The variant column is 1 (the write barrier) plus `log2(W/S)` cross-subgroup
tree stages. The stage reduction is arithmetic, not a claim of speed: whether
removing barrier stages wins on Mali hardware is UNMEASURED, and a subgroup
fold costs register shuffles whose price on Mali is exactly what no one has
measured here.

## The Mali capability precondition (the ARM-specific gate)

Mali subgroup arithmetic (`VK_KHR_shader_subgroup` arithmetic / the WGSL
subgroups extension) is exposed by newer Mali generations and uneven driver
coverage. Emission admission -- ADR-0356 rule 3 -- therefore has an
ARM-specific condition: the subgroup-reduce emission is admitted for a
device only when the device descriptor that ADR-0355 dispatch already
consumes reports subgroup support (the wire-42 INFO/DEVCLASS answer of the
runtime loader). The variant table itself keeps its total `(vendor, kir)`
shape and is never the place that learns about devices; a descriptor without
the capability answers `:baseline` at the dispatch layer, which is a
fallback, not a refusal.

## Honest state (checked 2026-10-19, amu at bea7b9b2)

- Implemented: nothing in this ADR. The baseline ADR-0002 emitters and the
  ADR-0355 dispatch table are on main; the variant table with the NVIDIA row
  is in flight (PR #1331) and ADR-0356 (PR #1333) is open at this date.
  This file is the only artifact of this decision.
- Accepted design only: this row's shape, predicate, capability precondition
  and measurement contract.
- UNMEASURED: every performance word above. There is no Mali device in this
  fleet -- this host is Apple Silicon, and the only vendor measurable here
  is Apple (JUN-58). No subgroup-reduce emission exists for any vendor yet,
  so per rule 3 the selection row must not exist in code until it does.
- The ADR-0355 workgroup rows are untouched and stay `:measured? false` on
  their own axis; nothing here upgrades them.

Amended 2026-10-22: the state above is the 2026-10-19 snapshot and is
superseded on the IMPLEMENTATION axis only. The emission and the shared
selection row now exist -- `kotoba.compiler.accelerator-subgroup-reduce`
emits the Vulkan/GLSL arm for the (:glsl-v1, :subgroup-reduce) pair
(ADR-0359 decision 1) with the sealed GLSL -> SPIR-V build step of decision
2, and `select-variant` (kotoba.compiler.accelerator-variants) answers
`:subgroup-reduce` for `:arm` and `:intel` under ADR-0356 rule 6 and this
file's capability precondition (the descriptor must report the fold's
subgroup ops and a subgroup size dividing `W`; anything else fails closed to
`:baseline`). Every performance word and this row's `:measured?` stay
UNMEASURED: no Mali device exists in this fleet and the measurement
contract below has not been run.

## Measurement contract (JUN-60)

The row flips `:measured? false` to true only on an interleaved
baseline-vs-variant reduce comparison on a Mali device that reports subgroup
arithmetic, with read-back verification (the protocol the workgroup sweeps
established: fresh-process runs, interleaved samples, verified read-back
words), recorded under `docs/evidence/`. Until then no report may cite this
row as optimization evidence.

## Consequences

- ARM (JUN-60) moves from *proposed* to *accepted design only*. The three
  states stay distinguishable: nothing in this file claims code, and the
  stage table claims arithmetic only.
- One subgroup-size-parametric emission serves the Intel and ARM rows when
  it lands; the rows differ in predicate, capability gate and basis text.
  Implementing it is shared work across JUN-59 and JUN-60.
- When ADR-0356 lands, its rows table should point the ARM row at this file.
  That edit is left to the ADR-0356 branch (PR #1333) to avoid two branches
  writing one file; if it lands without the pointer, this ADR is still the
  ARM decision of record.
