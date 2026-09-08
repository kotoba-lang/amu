import io

path = "docs/codegen-coscientist.md"
entry = """
2026-09-08 16:11 JST (amu-rank cron, tick 290): host busy (pre-run monitor 16:09: load1 51.78 / load5 40.56 / load15 32.20, up 3d 8:52, 7 users, threshold 7.5; live probe sysctl vm.loadavg 16:11: load1 39.69 / load5 39.91 / load15 32.70) - measurement refused, rank-only busy pass. git fetch: origin/main UNCHANGED since tick-289 read - still a169d7bf (merge PR #890 advance kotoba-script to aefd1f07, regenerate lock; upstream dep/infra, origin-namespace, NOT local-reconcilable; local branch still diverged/behind origin, merge/reconcile left for the operator). local HEAD 4b575cfb = tick-289 busy-pass commit. guard-glob residue 130 -> 133 untracked lines local-uncommitted (`git status --porcelain -- src bench scripts deps.edn` = 133, regime unchanged: append/probe scripts under docs/ + scripts/ + 2 build-time-os sidecars bench/runtime-comparison/kernel.kotoba.wasm.{provenance,publication}.edn + Q9-migration-plan.edn + build.sh + ADR 0339). Folded 2 uncommitted sibling busy-refusals landed since tick-289 commit (amu-bench 2026-09-08 15:54 JST busy-tick entry: pre-run load1 21.06 / load5 18.92 / load15 21.46, own probe load1 17.83 / 5m 18.58 / 15m 21.00, up 3d 8:35, 7 users, above 7.5 quiet gate, no measurement, no numbers, NEXT H-C2 untouched; amu-bench 2026-09-08 16:08 JST busy-tick entry: pre-run load1 37.37 / load5 33.76 / load15 28.90, own probe load1 47.41 / 5m 36.59 / 15m 30.10, up 3d 8:51, 7 users, far above 7.5 quiet gate, no measurement, no numbers, NEXT H-C2 untouched) - busy refusals, NOT a new LOCAL measured verdict (folding evidence, no status edit). No new local codegen ADR since tick-289 folded 0345 (first QUALIFIED imod lever verdicts on benjamin at full fleet quiet gate, C-proxy control :not-a-claim; perfgate.core/qualify for kotoba-native imod inlining NOT yet issued; ADR 0339 itself remains UNTRACKED local residue). No new LOCAL measured verdict -> no re-rank, no status transition, no new hypothesis; population unchanged (post-284): H-Z4 registered open (port ADR-0345 imod helper-call inlining to kotoba-native, expected separated >=5%), H-Z3 top of codegen ladder (quiet-host A/B still blocked by guard-glob residue + repo divergence from origin), H-C2 open ceiling-caution (static 61/61, timed A/B unresolved, notional ~4.4% pending quiet host then fleet node), H-D/H-B/H-Z1/H-Y1 open. NEXT (unchanged, rank authority): operator lands/commits local residue + syncs/merges local branch onto advanced origin/main (incl. PR #819 fleet scripts quiet-host.cljs + remote-bench.cljs), then quiet-host A/B (H-Z3 top lever, else H-C2 ceiling-check) on idlest qualifying fleet node.
"""

with io.open(path, "r", encoding="utf-8") as f:
    content = f.read()

# append before the standing honesty constraints section, preserving the trailing entries
marker = "## Standing honesty constraints"
idx = content.rfind(marker)
if idx == -1:
    content = content + "\n" + entry
else:
    content = content[:idx] + entry + "\n" + content[idx:]

with io.open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("appended tick 290 entry")
