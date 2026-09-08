import io

path = "docs/codegen-coscientist.md"
entry = """
2026-09-08 16:20 JST (amu-rank cron, tick 291): host busy (pre-run monitor 16:17: load1 52.53 / load5 35.35 / load15 31.61, up 3d 9:03, 8 users, threshold 7.5; live probe sysctl vm.loadavg 16:20: load1 45.58 / load5 41.28 / load15 35.08) - measurement refused, rank-only busy pass. git fetch: origin/main UNCHANGED since tick-290 read - still a169d7bf (merge PR #890 advance kotoba-script to aefd1f07, regenerate lock; upstream dep/infra, origin-namespace, NOT local-reconcilable; local branch still diverged/behind origin, merge/reconcile left for the operator). local HEAD 1f745c10 = lang-cosientist iteration 30 (landed on top of tick-290 busy-pass commit 38c9e6c4; lang scope, not a codegen-ladder number). guard-glob residue 133 -> 134 untracked lines local-uncommitted (`git status --porcelain -- src bench scripts deps.edn` = 134, regime unchanged: append/probe scripts under docs/ + scripts/ + 2 build-time-os sidecars bench/runtime-comparison/kernel.kotoba.wasm.{provenance,publication}.edn + Q9-migration-plan.edn + build.sh + ADR 0339). Folded 1 uncommitted sibling busy-refusal landed since tick-290 commit (amu-falsify 2026-09-08 16:18 JST H-C2-row busy entry: load1 52.35 / load5 38.89 / load15 33.21, up 3d 9h, 8 users, above 7.5 quiet gate, no measurement, no numbers, NEXT H-C2 untouched) - busy refusal, NOT a new LOCAL measured verdict (folding evidence, no status edit). No new local codegen ADR since tick-289 folded 0345 (first QUALIFIED imod lever verdicts on benjamin at full fleet quiet gate, C-proxy control :not-a-claim; perfgate.core/qualify for kotoba-native imod inlining NOT yet issued; ADR 0339 itself remains UNTRACKED local residue). No new LOCAL measured verdict -> no re-rank, no status transition, no new hypothesis; population unchanged (post-284): H-Z4 registered open (port ADR-0345 imod helper-call inlining to kotoba-native, expected separated >=5%), H-Z3 top of codegen ladder (quiet-host A/B blocked by guard-glob residue + repo divergence from origin), H-C2 open ceiling-caution (static 61/61, timed A/B unresolved, notional ~4.4% pending quiet host then fleet node), H-D/H-B/H-Z1/H-Y1 open. NEXT (unchanged, rank authority): operator lands/commits local residue + syncs/merges local branch onto advanced origin/main (incl. PR #819 fleet scripts quiet-host.cljs + remote-bench.cljs), then quiet-host A/B (H-Z3 top lever, else H-C2 ceiling-check) on a qualifying fleet node.
"""

with io.open(path, "r", encoding="utf-8") as f:
    content = f.read()

marker = "## Standing honesty constraints"
idx = content.rfind(marker)
if idx == -1:
    content = content + "\n" + entry
else:
    content = content[:idx] + entry + "\n" + content[idx:]

with io.open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("appended tick 291 entry")
