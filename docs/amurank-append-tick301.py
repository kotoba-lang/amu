#!/usr/bin/env python3
# amu-rank tick 301 busy-pass append. Inserts the tick entry after tick-300's detail line.
import io

path = "docs/codegen-coscientist.md"
entry = (
    "\n"
    "2026-09-08 19:53 JST (amu-rank cron, tick 301): host busy (pre-run monitor load1 16.57 / load5 27.23 / load15 43.24, up 3d 12:36, 8 users, threshold 7.5; live probe uptime 19:53: load1 15.69 / load5 25.87 / load15 42.10) - measurement refused, rank-only busy pass.\n"
    "git fetch: origin/main UNCHANGED at 7b63f7ed (PR #897 conformance: an option in RETURN position, on wasm32) since tick-300 read; upstream origin-namespace, NOT local-reconcilable; local branch spike/kbb-jvmfree-envread still diverged/behind origin, merge/reconcile left for the operator. local HEAD 53e8f7ea = tick-300 busy+fold commit. guard-glob residue 144 untracked lines local-uncommitted (`git status --porcelain -- src bench scripts deps.edn` = 144, unchanged from tick 300; regime unchanged: append/probe scripts under docs/ + scripts/ + build-time-os sidecars + ADR 0339 untracked). Folded 1 sibling busy-refusal landed since tick-300 commit (amu-falsify 2026-09-08 19:46 JST H-C2 evidence cell: load1 28.30 / load5 39.27 / load15 55.48, up 3d 12:28, threshold 7.5, quiet-gate refusal, no measurement, no numbers, NEXT H-C2 untouched) - a busy refusal, NOT a new local measured verdict (folding evidence, no status edit). Pre-run monitor NEXT read \"H-Y1 remain open. NEXT: H-C2\" is STALE (unchanged from the ticks 296-300 flag; H-C2 has not been rank-authority NEXT since iter-56); authoritative NEXT is the committed tick's rank line below. No new local codegen ADR since tick-300 read (0345 remains latest, first QUALIFIED imod lever verdicts on benjamin at quiet gate; perfgate.core/qualify for kotoba-native imod inlining NOT yet issued from a quiet host; ADR 0339 untracked). No new LOCAL measured verdict -> no re-rank, no status transition, no new hypothesis; population unchanged (post-284): H-Z4 registered open (port ADR-0345 imod helper-call inlining to kotoba-native), H-Z3 top of codegen ladder (quiet-host A/B still blocked by guard-glob residue + repo divergence from origin), H-C2 open ceiling-caution (static 61/61, timed notional ~4.4% unresolved), H-D/H-B/H-Z1/H-Y1 open. NEXT (unchanged, rank authority): operator merges origin/main + lands quiet-host scripts (remote-bench.cljs guard-glob), then quiet-host A/B (H-Z3 top lever, else H-C2 ceiling-check) on idlest qualifying fleet node.\n"
)

with io.open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

anchor = "8cc1361f -> 7b63f7ed"
idx = None
for i, ln in enumerate(lines):
    if anchor in ln:
        idx = i
        break

if idx is None:
    raise SystemExit("anchor not found")

# insert after the tick-300 detail line (idx)
lines.insert(idx + 1, entry)

with io.open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("inserted after line", idx + 1)