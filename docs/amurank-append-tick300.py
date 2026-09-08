#!/usr/bin/env python3
# amu-rank tick 300 busy-pass append (rank-only, host busy, no measurement).
# Inserts the tick-300 iteration entry immediately after the tick-299 entry line.
import io

DOC = "docs/codegen-coscientist.md"
MARKER = "2026-09-08 19:28 JST (amu-rank cron, tick 299):"

ENTRY = (
    "2026-09-08 19:35 JST (amu-rank cron, tick 300): host busy (pre-run monitor load1 75.59 / load5 96.73 / load15 81.93, up 3d 12:18, 8 users, threshold 7.5) - measurement refused, rank-only busy pass.\n"
    "git fetch: origin/main ADVANCED 8cc1361f -> 7b63f7ed (PR #897 conformance: an option in RETURN position, on wasm32, with a (#897)); upstream origin-namespace, NOT local-reconcilable; local branch spike/kbb-jvmfree-envread still diverged/behind origin, merge/reconcile left for the operator. local HEAD ca3ac2b6 = tick-299 busy+fold commit. guard-glob residue 144 untracked lines local-uncommitted (unchanged from tick 299; regime unchanged: append/probe scripts under docs/ + scripts/ + build-time-os sidecars + ADR 0339 untracked). The only uncommitted doc change since tick-299 commit is a 1-line H-C2 evidence-cell busy-refusal append (docs diff 1+1-, a sibling quiet-gate refusal, NOT a measured verdict); no new sibling busy-refusal to fold beyond that trivial cell append. Pre-run monitor NEXT read \"H-Y1 remain open. NEXT: H-C2\" is STALE (unchanged from the ticks 296-299 flag; H-C2 has not been rank-authority NEXT since iter-56); authoritative NEXT is the committed tick's rank line below. No new local codegen ADR since tick-299 read (0345 remains latest, first QUALIFIED imod lever verdicts on benjamin at quiet gate; perfgate.core/qualify for kotoba-native imod inlining NOT yet issued from a quiet host; ADR 0339 untracked). No new LOCAL measured verdict -> no re-rank, no status transition, no new hypothesis; population unchanged (post-284): H-Z4 registered open (port ADR-0345 imod helper-call inlining to kotoba-native), H-Z3 top of codegen ladder (quiet-host A/B still blocked by guard-glob residue + repo divergence from origin), H-C2 open ceiling-caution (static 61/61, timed notional ~4.4% unresolved), H-D/H-B/H-Z1/H-Y1 open. NEXT (unchanged, rank authority): operator merges origin/main + lands quiet-host scripts (remote-bench.cljs guard-glob), then quiet-host A/B (H-Z3 top lever, else H-C2 ceiling-check) on idlest qualifying fleet node.\n"
)

with io.open(DOC, "r", encoding="utf-8") as f:
    lines = f.readlines()

out = []
inserted = False
for ln in lines:
    out.append(ln)
    if (not inserted) and ln.startswith(MARKER):
        out.append("\n")
        out.append(ENTRY)
        inserted = True

if not inserted:
    raise SystemExit("ERROR: tick-299 marker not found; aborting without edit")

with io.open(DOC, "w", encoding="utf-8") as f:
    f.writelines(out)

print("inserted tick-300 entry after tick-299 line")