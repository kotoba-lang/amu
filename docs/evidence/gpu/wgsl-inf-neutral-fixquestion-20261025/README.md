# JUN-59/JUN-60: the WGSL infinite-neutral fix question is DECIDED (2026-10-25)

ONE design decision (backlog item 4). The class-1 refusal the 2026-10-25
toolchain judgment named -- "the infinite neutral's
`bitcast<f32>(0xFF800000u)` / `bitcast<f32>(0x7F800000u)` const-folds to
-inf/inf and Tint answers `value -inf cannot be represented as 'f32'`" --
was left with the fix question UNDECIDED: *"whether that refusal is a Tint
const-eval limit or real spec drift in the spelling"*. It is decided now.

## The decision

**NEITHER. The refusal is the WGSL spec's own Finite Math Assumption doing
its job; the emitter's neutral spelling is the defect.** Concretely:

1. The arm's neutral `bitcast<f32>(0xFF800000u)` is a **const-expression of
   floating-point type that evaluates to -infinity** (spec 8.1.1 + 17.2.1
   `@const` bitcast; spec-quotes.txt quotes 1/2/3/6), and the Finite Math
   Assumption (15.7.3) says verbatim: *"A shader-creation error results if
   any const-expression of floating-point type overflows or evaluates to
   NaN or infinity."* Tint's refusal is **conformant behavior**, not a
   toolchain limitation to route around and not spec drift in Tint.
2. **A runtime-escape spelling is NOT the fix.** The runtime-masked probe
   (p05) does validate clean in Tint -- the refusal is scoped to
   const-evaluation -- but the same spec clause continues: *"Implementations
   may assume that overflow, infinities, and NaNs are not present during
   shader execution ... the final result will be an indeterminate value of
   the target type. Note: This means some functions (e.g. min and max) may
   not return the expected result."* The arm's combine operators ARE min
   and max. An infinity smuggled into runtime position is spec-permitted to
   become garbage on any conforming implementation. The escape hatch
   validates today and is not portable WGSL.
3. **The fix rule (accepted design; IMPLEMENTATION IS ITS OWN LATER
   SLICE): the :subgroup-reduce WGSL arm must contain no infinite value in
   any position.** For :max/:min the out-of-range lanes hold an IN-RANGE
   element (a clamped-index fill: every lane carries `x[min(i, n-1)]`, so
   invalid lanes duplicate a valid element and max/min stay exact), and
   :sum keeps its finite 0.0 identity. The n = 0 case (no element to clamp
   to) is a contract/branch question the implementation slice answers.
   This removes bitcast-of-infinity from the arm entirely -- which also
   sidesteps Naga's separate refusal class (below).

## The probes (9 files, 2 real toolchains; compile-log.txt is verbatim)

Corpus docs/evidence/gpu/wgsl-inf-neutral-fixquestion-20261025/probes/:
p00/p08 are controls (finite bitcast in let / const position), p01-p04 +
p06 are the infinite neutral in const/let/var/the arm's own select shape +
the :min row's positive spelling, p05 is the runtime-escape hypothesis,
p07 is the hex-float-literal route. Instruments:
scripts/validate-gpu-wgsl-inf-probes.mjs (Chrome/Tint via WebGPU
shader creation) and scripts/judge-gpu-wgsl-probes-deno.ts (Deno's
bundled wgpu/Naga). Verdicts:

| probe | Chrome 155 Dawn/Tint | Deno 2.7.14 wgpu/Naga |
|-------|----------------------|-----------------------|
| p00 finite bitcast (let)   | VALIDATES CLEAN | VALIDATES CLEAN |
| p01 -inf in const-decl     | REFUSED `value -inf cannot be represented as 'f32'` | REFUSED `Not implemented as constant expression: bitcast built-in function` |
| p02 -inf in let-init       | REFUSED (same) | VALIDATES CLEAN |
| p03 -inf in var-init       | REFUSED (same) | VALIDATES CLEAN |
| p04 the arm's select shape | REFUSED (same, at the select's neutral arm) | VALIDATES CLEAN |
| p05 runtime-masked -inf    | VALIDATES CLEAN | VALIDATES CLEAN |
| p06 +inf in let-init (:min row) | REFUSED `value inf cannot be represented as 'f32'` | VALIDATES CLEAN |
| p07 hexfloat 0x1p128       | REFUSED `value 340282366920938463463374607431768211456.0 cannot be represented as 'f32'` | REFUSED `the concrete type f32 cannot represent the abstract value ... accurately` |
| p08 finite bitcast (const) | VALIDATES CLEAN | REFUSED (same as p01: bitcast const-eval unimplemented) |

Reading, in the decision's terms:

- Tint is **value-scoped, not spelling-scoped**: the finite controls
  (p00, p08) validate in the same positions where the infinite spelling
  is refused (p01-p04, p06). The refusal class is about the infinite
  VALUE, exactly as the Finite Math Assumption says.
- Tint refuses the arm's **own emitted shape** (p04) at the neutral arm --
  the 2026-10-25 refusal is reproduced by a 12-line probe.
- Naga's p01/p08 refusals are a **different class** ("Not implemented as
  constant expression: bitcast"): Naga lacks bitcast const-evaluation for
  ANY value, finite included. Naga accepts the let/var initializers
  (p02/p03/p04/p06) where Tint refuses them -- the two front ends
  disagree on that context. An emitter must not live in a toolchain
  disagreement zone; decision point 3 removes the spelling both ways.
- The runtime-escape probe p05 validates in BOTH toolchains -- and is
  still rejected as the fix, per decision point 2's spec clause.

## State honesty (the three states)

- ACCEPTED DESIGN ONLY: decision point 3 (the no-infinite-value fix rule).
  It is recorded here and in ADR-0363 / ADR-0356. The emitter is NOT
  changed by this slice; the :max/:min rows still emit the refused
  spelling and still fail Chrome 155's Tint. The tests' spelling pins
  stand unchanged beside this decision (they pin what IS emitted, which
  is true today).
- IMPLEMENTED (unchanged): the arm's emission + text contracts + tests,
  and the two probe instruments (NEW this slice, scripts only).
- TOOLCHAIN FACTS (new, self-dated in compile-log.txt): the 18 verdicts
  above.
- UNMEASURED, unchanged and still the operative claim: no kernel executed
  this arm on any GPU, no timing exists, no speed claim of any kind, no
  :measured? flag, no selection answer, and no ADR-0355/0358 workgroup
  row moves. Shader validation is not a measurement.
- PROPOSED (neither accepted nor implemented): nothing new; the W >= 512
  raised-limits operational note of 2026-10-25 is unchanged.

## What moved in the repository

- docs/evidence/gpu/wgsl-inf-neutral-fixquestion-20261025/ (NEW): this
  README, spec-quotes.txt (the normative ground, with retrieval sha256),
  probes/ (9 files), compile-log.txt (both toolchains, verbatim), and the
  two gate transcripts. No POSIX .sh file anywhere (the check-workflows
  rule).
- scripts/validate-gpu-wgsl-inf-probes.mjs,
  scripts/judge-gpu-wgsl-probes-deno.ts (NEW instruments).
- Prose brackets at the five sites that named the UNDECIDED fix question
  (accelerator_subgroup_reduce.cljk, accelerator.cljk,
  accelerator_subgroup_reduce_test.cljk, ADR-0356, ADR-0363). No code
  behavior changed.
