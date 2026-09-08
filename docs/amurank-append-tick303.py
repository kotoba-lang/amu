#!/usr/bin/env python3
# amu-rank tick 303 busy-pass append. Inserts the tick entry before the last
# "## Standing honesty constraints" anchor (the Iteration-log section end).
import io

DOC = "docs/codegen-coscientist.md"
ANCHOR = "## Standing honesty constraints"

entry = (
    "\n"
    "2026-09-08 20:18 JST (amu-rank cron, tick 303): host busy (pre-run monitor "
    "load1 37.45 / load5 41.51 / load15 40.01, up 3d 13:01, 8 users, threshold 7.5; "
    "live probe uptime 20:18: load1 34.56 / load5 40.46 / load15 39.69, up 3d 13:01, "
    "8 users) - measurement refused, rank-only busy pass.\n"
    "git fetch: origin/main UNCHANGED at 7b63f7ed (PR #897 conformance: an option "
    "in RETURN position, on wasm32) since tick-302 read; upstream origin-namespace, "
    "NOT local-reconcilable; local branch spike/kbb-jvmfree-envread still "
    "diverged/behind origin, merge/reconcile left for the operator. local HEAD "
    "7801157e = tick-302 busy+fold commit. guard-glob residue 148 untracked lines "
    "local-uncommitted (`git status --porcelain -- src bench scripts deps.edn` "
    "= 148, unchanged from tick 302; regime unchanged: append/probe scripts under "
    "docs/ + scripts/ + build-time-os sidecars + ADR 0339 untracked). No sibling "
    "busy-refusal landed since tick-302 commit (iteration log ends at tick 302; "
    "last falsify 20:01 H-C2 cell + amu-bench 20:02/20:07 + H-C2 08:25 already "
    "folded in tick 302) - nothing new to fold, NOT a new LOCAL measured verdict. "
    "Pre-run monitor NEXT read \"H-Y1 remain open. NEXT: H-C2\" is STALE (unchanged "
    "from the ticks 296-302 flag; H-C2 has not been rank-authority NEXT since "
    "iter-56); authoritative NEXT is the committed tick's rank line below. No new "
    "local codegen ADR since tick-302 read (0345 remains latest, first QUALIFIED "
    "imod lever verdicts on benjamin at quiet gate; perfgate.core/qualify for "
    "kotoba-native imod inlining NOT yet issued from a quiet host; ADR 0339 "
    "untracked). No new LOCAL measured verdict -> no re-rank, no status transition, "
    "no new hypothesis; population unchanged (post-284): H-Z4 registered open (port "
    "ADR-0345 imod helper-call inlining to kotoba-native), H-Z3 top of codegen "
    "ladder (quiet-host A/B still blocked by guard-glob residue + repo divergence "
    "from origin), H-C2 open ceiling-caution (static 61/61, timed notional ~4.4% "
    "unresolved), H-D/H-B/H-Z1/H-Y1 open. NEXT (unchanged, rank authority): "
    "operator merges origin/main + lands quiet-host scripts (remote-bench.cljs "
    "guard-glob), then quiet-host A/B (H-Z3 top lever, else H-C2 ceiling-check) on "
    "idlest qualifying fleet node.\n"
)

with io.open(DOC, "r", encoding="utf-8") as f:
    text = f.read()

idx = text.rfind(ANCHOR)
if idx < 0:
    raise SystemExit("anchor not found: " + ANCHOR)

new_text = text[:idx] + entry + text[idx:]

with io.open(DOC, "w", encoding="utf-8") as f:
    f.write(new_text)

print("inserted tick 303 entry before anchor at char", idx)