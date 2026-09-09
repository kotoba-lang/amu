import io

path = "docs/codegen-coscientist.md"
entry = """
2026-09-09 11:02 JST (amu-rank cron, tick 340): host busy (pre-run monitor
load1 83.28 / load5 104.61 / load15 107.50, up 4d 3:30, 8 users, threshold
7.5) - measurement refused, rank-only busy pass. git fetch clean (origin/main
UNCHANGED at a681d3f2 = Merge PR #894 'jvm-retire/browse-dflag-loader';
upstream conformance/infra, origin-namespace, still NOT local-reconcilable -
local branch spike/kbb-jvmfree-envread diverged/behind origin, merge/reconcile
left for the operator). local HEAD ed29de37 = tick-339 busy+fold commit.
Working tree M docs/codegen = 1 new cross-bot busy refusal landed since
tick-339 commit (amu-bench 2026-09-09 10:52 JST busy-tick: load1 122.34 /
load5 123.32 / load15 111.11, pre-run monitor 10:38, up 4d 3:21, 8 users,
macOS 26.4, 10 cores, threshold 7.5, no bench/perfgate/hand-patch number
taken or recorded, NEXT unchanged) - a busy refusal, NOT a measured verdict,
nothing to fold into the rank ladder (committed here as the working-tree doc
edit). guard-glob residue 163 untracked lines local-uncommitted (git status
--porcelain -- src bench scripts deps.edn = 163, regime unchanged:
append/probe scripts under scripts/ + Ja_harness/*.java + JFR logs +
build-time-os sidecars + Q9-migration-plan.edn + ADR 0339 untracked) - none
are codegen-ladder measured verdicts. No new local codegen ADR since tick-339
read (0345 remains latest registered; perfgate.core/qualify for kotoba-native
imod inlining NOT yet issued; ADR 0339 remains UNTRACKED/residue locally).
Pre-run monitor NEXT 'H-Y1 remain open. NEXT: H-C2' is STALE (unchanged since
iter-56 flag; H-C2 not rank-authority; authoritative NEXT is the committed
tick rank line). No new LOCAL measured verdict -> no re-rank, no status
transition, no new hypothesis; population unchanged (post-284: H-Z4
registered open, H-Z3 top of codegen ladder, H-C2 open ceiling-caution,
H-D/H-B/H-Z1/H-Y1 open). NEXT (unchanged, rank authority): operator merges/
lands the local residue + syncs local branch (onto a681d3f2#894 or newer),
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

print("appended tick 340 entry")
