# Native incremental build: session checkpoint, 2026-10-27

Tracking: JUN-358 (implementation and ordered resume), JUN-332 (CI timing),
JUN-15 (review and merge). Thread: 01a166b0-9394-76a2-9a14-48a7c47f90a5.
This is a closing record, not a new qualification or performance claim.

## Landed scope

PRs #1628, #1630, #1631, #1632, #1633 and #1634 were merged and independently
read back. #1634 merged as
`7b7f0892167670f8c0102f8e48ca8e70b6148592`.
The earlier five clean owned task worktrees and local branches were removed after
ancestry/content verification; other owners' work and four stashes remain.
The #1634 and closing-record worktrees are removed after their final readback.

The #1630 final native run 40480745902 completed in 29m08s with all six
workflows successful and 39 artifact groups audited. Every original x86
gate row/argv remains; the split uses two shards, two builds per runner,
and refuses a later shard-job failure. This is scheduling evidence, not
a same-host compiler improvement or the requested <=20-minute result.

## Newly integrated prototype

PR #1634, head `a70d2c1afb446a42ec1fdc84dd7b50f564a341d1`, preserves
checked generic collection identities. Native ARM/x86 source qualification
40489282612 passed: 61 identity triples, 94 guest executions, 40 atomic
refusals, 16 runtime refusals and nine built/executed mutants per ISA.
Source, primitive, effect, resource, namespace and graph artifact audits
passed against this frozen head. All previous cases remain mandatory.

Full native run 40489282446 subsequently completed successfully in 30m27s;
the source workflow took 19m28s. All six native workflows passed. All 39
artifact groups were downloaded and digest-verified; nine independent
source-bound audits passed, including original19, native24/refusal18,
controller receipts and all17 x86 gate rows. #1634 was then reviewed and
merged. This prototype remains outside FULL-MANIFEST, and CI20 is unmet.
The post-merge main-tier run is separate and is not claimed passed here.

Production FULL48 sourceUnity remains
`5254afb12561ee609e8cd27420c6c5ddbb3e2e484cab5311b3674a1f11b04d05`;
root/public/compiler/controller pins are unchanged by these prototypes.
The whole source still refuses atomically at `DSB:BRIDGE:3:34668`.

## Preserved experiments

- `codex/native-abort-result-identity-20261027`, local-only WIP checkpoint
  `0be32f9d6c829d9bc2dfdf1d45cbb14a589a11e2`: canonical abort-to-result
  semantic lowering. Ten fresh KIR cases, two bottom-try refusals and 32
  source/KIR native ARM executions pass. No source DefCID, sealed control
  row, source-resource equivalence or native x86 qualification is claimed.
  The fresh source has 11 escaping-abort functions, all with `:i64` error
  and `:vector-i64` result. The experiment reaches
  `DSA:LOWERING:2:2766 fn=ck-rec-flds ctor=0`; that function's nominal
  `[:list [:ref :seed/ck-fld]]` schema still refuses without type erasure.
- `codex/native-checker-closures-20261027`, local-only WIP checkpoint
  `effcc7300e8e2682fa51ec1a87171af0efe6cad8`: unadopted helper experiment,
  not a demonstrated whole-compile speed improvement.

Both clean worktrees are retained. Verified incremental Git bundles and
patches are under the canonical task scratch directory
`workspaces/codex/native-generic-collections-20261027/session-checkpoints/`.
The abort probe's raw reports and prototype-summary.json are under
`workspaces/codex/native-abort-result-identity-20261027/`.
The scratch directories are not production runtime inputs.

## Resume order and acceptance

1. Inspect the separate post-merge main-tier run before treating the new
   main as freshly qualified; preserve every native gate and uncached tier.
2. Bind abort-to-result identities to fresh original-source facts. `:abort`
   is a non-propagating control effect: a catching caller does not inherit
   its callee's abort row. External checked flags are not source proof.
3. Bridge nominal/schema closure beginning at seed/ck-fld and the remaining
   whole-source constructs. Aborting loop helpers still refuse in the probe.
4. Qualify full-source SCCs beyond eight members with canonical minimum,
   rank/tie, codec/index and resource proofs.
5. Bind the actual trusted producer image and dependency/interface closure,
   ABI/layout/profile/resource proofs and symbolic relocation to native
   persistent reuse. Link, fuel/context and admission always run freshly.
6. Measure actual cold/warm/invalidated native x86 builds, complete PR CI
   <=20 minutes, and retain successful uncached main/full qualification.
   Regenerate production/consumer pins when their inputs change, then finish
   review, merge, readback and safe task cleanup.

Whole-source identity, production persistent reuse and CI20 remain open.
AGENTS.md's historical FULL47 prose differs from the actual FULL48 manifest;
the current code/descriptors were followed and owner policy was not rewritten.
