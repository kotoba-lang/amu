# Statemate compare-zero branch fusion

Status: **selfhost fixed point and exactness passed; loaded-host timing is inconclusive; not promoted**.

## Hypothesis

The `sm` state-machine emitter contains compare-zero and conditional-branch
sequences around fuel updates. When the compared temporary is dead on both
successor paths, AArch64 can branch directly on the source register with
`cbz`/`cbnz`, removing the separate `cmp` while leaving the fuel update and
branch destination in place. The counter-hypothesis is that these instructions
are not a meaningful runtime cost, or that branch layout and flag dependencies
make the fused form no faster.

## Candidate and exactness

The candidate was isolated in the attempt-4 workspace and built from the
previous selfhost fixed-point compiler. G1, G2, and G3 converged to native
image SHA-256
`23671d91b6a5cbf742f886fb3dc8ca2adc80f1b2140e6bb72f4f2c1dfd791abc`.
The candidate altered only statemate relative to the preceding candidate's
19-image set. Its statemate payload is 264,084 bytes with SHA-256
`942cd6e2f7ec5c3c719e776b17770f0931cb5c9437f434d603be5099e48a2f8e`; the
preceding payload is the pinned M104 image at 264,184 bytes.

The changed set relative to the M104 record contains 16 images because the
preceding M105 candidate already includes other compiler changes. The official
exactness harness passed all 16 changed images, including the registered
result, fuel, and arena accounting. The report is
`workspaces/codex/amu-statemate-cbz-fusion-20261017/attempt-4/exactness-17-vs-m104/report.json`.

Wrapping each flat payload as an AArch64 object and disassembling it shows the
expected instruction-count change: `cbnz` 111 to 136, `cmp` 4,584 to 4,559,
and `b.ne` 901 to 876; `cbz` remains at 711. This is 25 compare/branch pairs
replaced by register tests. The disassemblies are in the attempt-4 workspace.

## Timing and verdict

Five exploratory ABBA pairs on the loaded M1 Max produced candidate/base
ratios `0.9510, 1.1973, 0.3798, 0.8154, 1.1127`. All 20 invocations matched
the exact result, fuel, and arena expectation. Load averages ranged from about
122 to 134 and CPU idle stayed below 22%, so the run is not host-qualified.
The spread is too wide to establish a speedup. Keep the candidate unpromoted;
repeat on a quiet host only if the broader `sm` branch-lowering work remains a
priority after testing other workload domains.

## Reproduction artifacts

- `workspaces/codex/amu-statemate-cbz-fusion-20261017/attempt-4/build/build-report.json`
- `workspaces/codex/amu-statemate-cbz-fusion-20261017/attempt-4/all19-candidate/report.json`
- `workspaces/codex/amu-statemate-cbz-fusion-20261017/attempt-4/timing-statemate-5-abba-v2/report.json`
- `workspaces/codex/amu-statemate-cbz-fusion-20261017/attempt-4/disassembly/`

The shared `seed/41-a64gen.kotoba` was not changed for this candidate.
