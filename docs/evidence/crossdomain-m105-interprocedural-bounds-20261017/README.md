# Interprocedural minimum-length bounds-check candidate

Status: **fixed point reproduced; no official port image changed; source change reverted**.

The candidate connected the per-value minimum vector length (`t2-hm`) directly
to `t2-bch-covered?`. It rebuilt from the previous native selfhost compiler and
reached G1=G2=G3 at SHA-256
`77d48ee4c3d73fbcbd64566258287ea0a96e8b5940c0fa50de16708b13a6a9ed`.
The compiler regenerated all 19 pinned ports successfully. Every native image
matched the previous candidate at
`workspaces/codex/amu-statemate-recursive-inliner-20261017/attempt-3/all19-candidate/images.json`.

The attempted emitter change duplicated an existing proof. T2's `t2-chk`
invokes `t2-chk-vals`; that pass already calls `t2-hm` for constant indices
and sets the unchecked flag when the index is below the proven minimum vector
length. The added predicate therefore did not change any workload code and was
removed from `seed/41-a64gen.kotoba`.

Build report: `workspaces/codex/amu-interprocedural-bounds-20261017/attempt-1/build/build-report.json`.
Port compile report: `workspaces/codex/amu-interprocedural-bounds-20261017/attempt-1/all19-candidate/report.json`.
No new exactness run was needed because every output image was unchanged from
the previously exact candidate. No timing was collected on the loaded M1 Max.
