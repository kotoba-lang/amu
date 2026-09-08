import io

path = "docs/codegen-coscientist.md"
entry = """2026-09-08 22:00 JST (amu-rank cron, tick 309): host busy (pre-run monitor load1 31.00 / load5 37.82 / load15 48.23, up 3d 14:43, 6 users, threshold 7.5; live probe uptime 22:00: load1 32.12 / load5 37.66 / load15 47.94) - measurement refused, rank-only busy pass. git fetch: origin/main UNCHANGED at b1478c91 (PR #899 "K16 loader: the PE32+ embedded-kernel route amu's main does") since tick-308 read; upstream origin-namespace, NOT local-reconcilable; local branch spike/kbb-jvmfree-envread still diverged/behind origin, merge/reconcile left for the operator. local HEAD b34895c6 = tick-308 busy+fold commit. guard-glob residue 149 untracked lines local-uncommitted (`git status --porcelain -- src bench scripts deps.edn` = 149, unchanged from tick 308; regime unchanged: append/probe scripts under docs/ + scripts/ + build-time-os sidecars + ADR 0339 untracked). Folded 1 uncommitted sibling busy-refusal landed since tick-308 commit (amu-bench 2026-09-08 21:49 JST Iteration-log tail entry: pre-run monitor load1 40.01 / load5 47.84 / load15 37.75, up 3d 14:20, 7 users; own os.getloadavg probe load1 100.53 / 5m 94.72 / 15m 69.16, quiet-gate refusal, no measurement, no numbers, NEXT unchanged) - a busy refusal, NOT a new local measured verdict (folding evidence, no status edit). Pre-run monitor NEXT read "H-Y1 remain open. NEXT: H-C2" is STALE (unchanged from the ticks 296-308 flag; H-C2 has not been rank-authority NEXT since iter-56); authoritative NEXT is the committed tick's rank line below. No new local codegen ADR since tick-308 read (0345 remains latest registered, first QUALIFIED imod lever verdicts on benjamin at quiet gate; perfgate.core/qualify for kotoba-native imod inlining NOT yet issued; ADR 0339 untracked). No new LOCAL measured verdict -> no re-rank, no status transition, no new hypothesis; population unchanged (post-284): H-Z4 registered open (port ADR-0345 imod helper-call inlining to kotoba-native, expected separated >=5%), H-Z3 top of codegen ladder (quiet-host A/B still blocked by guard-glob residue + repo divergence from origin), H-C2 open ceiling-caution (static 61/61, timed A/B unresolved, notional ~4.4% pending quiet host then fleet node), H-D/H-B/H-Z1/H-Y1 open. NEXT (unchanged, rank authority): operator lands/commits local residue + syncs/merges local branch onto advanced origin/main (incl. PR #819 fleet scripts quiet-host.cljs + remote-bench.cljs), then quiet-host A/B (H-Z3 top lever, else H-C2 ceiling-check) on idlest qualifying fleet node.

"""

with io.open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
out = []
inserted = False
for ln in lines:
    if ln.startswith("## Standing honesty constraints") and not inserted:
        out.append(entry)
        inserted = True
    out.append(ln)
if not inserted:
    out.append("\n" + entry)
with io.open(path, "w", encoding="utf-8") as f:
    f.writelines(out)
print("inserted:", inserted)