#!/usr/bin/env python3
# amu-rank: tick 295 host-busy fold entry. Insert before "## Standing honesty constraints".
import io

PATH = "docs/codegen-coscientist.md"
MARKER = "## Standing honesty constraints"

entry = """2026-09-08 18:03 JST (amu-rank cron, tick 295): host busy (pre-run monitor load1 32.50 / load5 32.63 / load15 40.82, up 3d 10:45, 10 users, threshold 7.5; live probe uptime 18:03: load1 32.82 / load5 32.70 / load15 40.15, os.getloadavg 32.82/32.70/40.15) - measurement refused, rank-only busy pass. git fetch: origin/main UNCHANGED since tick-294 read - still 9092ee34 (PR #893 kotoba-sema 6c895d10: an f32 literal compiles on the JVM-free path; upstream origin-namespace, NOT local-reconcilable; local branch spike/kbb-jvmfree-envread still diverged/behind origin, merge/reconcile left for the operator). local HEAD 3e38e9a9 = tick-294 busy+fold commit. guard-glob residue 140 untracked lines local-uncommitted (unchanged from tick 294; regime unchanged: append/probe scripts under docs/ + scripts/ + build-time-os sidecars + ADR 0339 untracked). Folded 1 uncommitted sibling busy-refusal landed since tick-294 commit (amu-bench 2026-09-08 17:55 JST: probe load1 29.89 / load5 34.22 / load15 45.44, up 3d 10:38, 10 users, quiet-gate refusal, no measurement, no numbers, NEXT H-C2 untouched) - a busy refusal, NOT a new local measured verdict (folding evidence, no status edit). No new local codegen ADR since tick-294 read (0345 first QUALIFIED imod lever verdicts on benjamin at full fleet quiet gate, C-proxy control :not-a-claim; perfgate.core/qualify for kotoba-native imod inlining NOT yet issued; ADR 0339 untracked). No new LOCAL measured verdict -> no re-rank, no status transition, no new hypothesis; population unchanged (post-284): H-Z4 registered open (port ADR-0345 imod helper-call inlining to kotoba-native, expected separated >=5%), H-Z3 top of codegen ladder (quiet-host A/B still blocked by guard-glob residue + repo divergence from origin), H-C2 open ceiling-caution (static 61/61, timed A/B unresolved, notional ~4.4% pending quiet host then fleet node), H-D/H-B/H-Z1/H-Y1 open. NEXT (unchanged, rank authority): operator lands/commits local residue + syncs/merges local branch onto advanced origin/main (9092ee34, incl. PR #819 fleet scripts quiet-host.cljs + remote-bench.cljs), then quiet-host A/B (H-Z3 top lever, else H-C2 ceiling-check) on idlest qualifying fleet node. Appended via python script file.\n\n"""

with io.open(PATH, "r", encoding="utf-8") as f:
    text = f.read()

if "tick 295" in text:
    print("ALREADY_PRESENT; no change")
else:
    idx = text.find(MARKER)
    if idx < 0:
        raise SystemExit("MARKER_NOT_FOUND")
    text = text[:idx] + entry + text[idx:]
    with io.open(PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print("INSERTED")