import io

path = "docs/codegen-coscientist.md"
entry = """
2026-09-09 11:17 JST (amu-rank cron, tick 341): host busy (pre-run monitor
load1 47.94 / load5 60.11 / load15 78.21, up 4d 3:45, 8 users, threshold 7.5)
- measurement refused, rank-only busy pass. git fetch ADVANCED (origin/main
moved a681d3f2 -> ba3cde51 = Merge PR #904 'definition-identity and
fuel-estimate file-free assertions run on both hosts' - upstream test/infra,
origin-namespace, NOT codegen-ladder and NOT local-reconcilable - local branch
spike/kbb-jvmfree-envread diverged/behind origin, merge/reconcile left for the
operator). local HEAD 9b7153f1 = tick-340 busy+fold commit. Working tree
M docs/codegen = 1 new cross-bot busy refusal landed since tick-340 commit
(amu-bench 2026-09-09 11:07 JST Standing-honesty block: pre-run monitor 10:52
load1 51.26 / load5 77.21 / load15 94.31, up 4d 3:35, 8 users, macOS 26.4,
10 cores, far past the 7.5 quiet-host limit; no bench/perfgate/hand-patch
number was taken or recorded this tick) - a busy refusal, NOT a measured
verdict, nothing to fold into the rank ladder (committed here as the
working-tree doc edit). Untracked residue regime unchanged (append/probe
scripts under docs/ + scripts/, Ja_harness/*.java + JFR logs, build-time-os
sidecars, Q9-migration-plan.edn, build.sh, ADR 0339) - none are
codegen-ladder measured verdicts. No new local codegen ADR since tick-340
read (0345 remains latest registered; perfgate.core/qualify for kotoba-native
imod inlining NOT yet issued; ADR 0339 remains UNTRACKED/residue locally).
Pre-run monitor NEXT 'H-Y1 remain open. NEXT: H-C2' is STALE (unchanged since
iter-56 flag; H-C2 not rank-authority; authoritative NEXT is the committed
tick rank line). No new LOCAL measured verdict -> no re-rank, no status
transition, no new hypothesis; population unchanged (post-284: H-Z4
registered open, H-Z3 top of codegen ladder, H-C2 open ceiling-caution,
H-D/H-B/H-Z1/H-Y1 open). NEXT (unchanged, rank authority): operator merges/
lands the local residue + syncs local branch (onto ba3cde51 #904 or newer),
then quiet-host A/B (H-Z3 top lever, else H-C2 ceiling-check) on a qualifying
fleet node.
"""

with io.open(path, "r", encoding="utf-8") as f:
    text = f.read()

marker = "\n## Standing honesty constraints"
assert marker in text, "marker missing"
text = text.replace(marker, entry + marker, 1)

with io.open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("appended tick 341 entry")
