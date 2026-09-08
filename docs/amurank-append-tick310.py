path = "docs/codegen-coscientist.md"
marker = "## Standing honesty constraints"

with open(path, "r", encoding="utf-8") as f:
    lines = f.read().split("\n")

head = ("2026-09-08 22:05 JST (amu-rank cron, tick 310): host busy (pre-run monitor "
        "load1 19.88 / load5 28.18 / load15 41.01, up 3d 14:47, 6 users, threshold "
        "7.5; live probe uptime 22:05: load1 18.56 / load5 26.69 / load15 39.80) - "
        "measurement refused, rank-only busy pass. git fetch: origin/main UNCHANGED "
        "at b1478c91 (PR #899 K16 loader: the PE32+ embedded-kernel route amu main "
        "does) since tick-309 read; upstream origin-namespace, NOT local-reconcilable; "
        "local branch spike/kbb-jvmfree-envread still diverged/behind origin, "
        "merge/reconcile left for the operator. local HEAD 17f978b4 = tick-309 "
        "busy+fold commit. guard-glob residue 149 untracked lines local-uncommitted "
        "(git status --porcelain -- src bench scripts deps.edn = 149, unchanged from "
        "tick 309; regime unchanged: append/probe scripts under docs/ + scripts/ + "
        "build-time-os sidecars + ADR 0339 untracked). No uncommitted sibling "
        "busy-refusal landed since the tick-309 commit (checked 21:50-22:05 window: "
        "no new bench/falsify entries; tick-309 already folded the 21:49 bench "
        "refusal) - no fold this tick. Pre-run monitor NEXT read H-Y1 remain open. "
        "NEXT: H-C2 is STALE (unchanged from the ticks 296-309 flag; H-C2 has not "
        "been rank-authority NEXT since iter-56); authoritative NEXT is the "
        "committed tick rank line below. No new local codegen ADR since tick-309 "
        "read (0345 remains latest registered, first QUALIFIED imod lever verdicts "
        "on benjamin at quiet gate; perfgate.core/qualify for kotoba-native imod "
        "inlining NOT yet issued; ADR 0339 untracked). No new LOCAL measured "
        "verdict -> no re-rank, no status transition, no new hypothesis; population "
        "unchanged (post-284): H-Z4 registered open (port ADR-0345 imod "
        "helper-call inlining to kotoba-native, expected separated >=5%), H-Z3 top "
        "of codegen ladder (quiet-host A/B still blocked by guard-glob residue + "
        "repo divergence from origin), H-C2 open ceiling-caution (static 61/61, "
        "timed A/B unresolved, notional ~4.4% pending quiet host then fleet node), "
        "H-D/H-B/H-Z1/H-Y1 open. NEXT (unchanged, rank authority): operator "
        "lands/commits local residue (149-line guard-glob + build-time-os sidecars "
        "+ untracked ADR 0339) + syncs/merges local branch "
        "spike/kbb-jvmfree-envread onto origin/main (b1478c91, incl. PR #819 fleet "
        "scripts quiet-host.cljs + remote-bench.cljs), then quiet-host A/B (H-Z3 "
        "top lever, else H-C2 ceiling-check) on the idlest qualifying fleet node. "
        "Appended via python script file (no heredoc, no -e/-c, no shell redirect).")

idx = lines.index(marker)
lines[idx:idx] = [head, ""]

with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("OK inserted tick-310 before marker; new line count:", len(lines))