#!/bin/sh
# CROSS-TICK TWO-BATCH SIGN PROBE (JUN-58, tick 20261020-0736):
# batch A already exists -- the 0530 tick's batch B logs (05:28:17--05:34:14
# JST, Oct 20), copied here byte-identical as run-A-*.log (sha256 in
# README). This script runs batch B NOW, in a later cron tick / fresh
# process, after batch A ended.
#
# WHY CROSS-TICK. The 2254 tick proved a >=30 min gap cannot fit this
# platform's 1800 s run budget INSIDE one tick (3 evidences); the 2337 tick
# bounded within-session stability at a 6m52s gap (no flip); the 0006 tick
# added the first >=30 min cross-tick datum (70m26s, no flip); the 0530 tick
# added the chain's longest gap (318m29s, w64t32 no flip; w64t31 anchor
# INCONCLUSIVE under load). The flip-RATE question needs more cross-session
# transitions, and each cross-tick batch adds exactly one. This probe is
# explicitly labeled CROSS-SESSION and cannot isolate "gap" from "session
# restart"; a FLIP or a no-flip is reported as a cross-tick datum only. A
# no-flip bounds nothing against a stochastic flip rate.
#
# PROBE IDENTITY. The probe bytes are the chain's pinned sha256 3696ca0d...
# (the 2254/2337/0006/0530 runs all used these exact bytes). origin/main's
# scripts/test-gpu-subgroup-reduce-chunksweep.cljk has SINCE ADVANCED and
# computes GAP differently -- so batch B runs the PINNED copy
# scripts/gpu-subgroup-reduce-chunksweep-pinned-3696ca0d.cljk (byte-identical
# to the chain, verified by sha256 before every use). Its root resolution
# (script dir / .. = repo root) is why the pinned copy lives under scripts/.
# Fixtures identical to the chain (w64 a25a6931..., self-printed by every
# SHAPE line and self-asserted by the probe before dispatch).
#
# CHAIN INPUTS AT THIS BASE (the PR #1393 staging rule). The rule says to
# run `sh scripts/gpu-sign-chain-stage-fixtures.sh` before dispatching the
# pinned probe. That script and its archive live on PR #1393's branch and
# are NOT on this base (origin/main a2a86a08); at this base
# test/fixtures/gpu/ ALREADY holds the chain's pinned pre-fix bytes (all
# four sha256 verified against the archive README's table before dispatch:
# w32 0cf6c406..., w64 a25a6931..., w128 c7931718..., w256 087107f9...),
# so the staging step is a byte-identity no-op here and the rule's invariant
# (the probe sees the bytes every prior datum ran) holds by construction.
#
# BASE NOTE. Batch A ran on origin/main e8f2ae61; batch B runs on a2a86a08.
# `git diff e8f2ae61..a2a86a08 -- tools/ src/` is EMPTY: zero runtime code
# delta between the bases (the delta is ADR/doc/merge traffic only), so the
# executed dispatch path is identical by construction.
#
# GAP PROVENANCE. The wall-clock window between batch A (ended 05:34:14 Oct
# 20) and batch B (this run) is NOT probe-idle: amu-gpu ticks 0556/0624 ran
# the post-fix subgroup-reduce EXEC probe (PRs #1391/#1392, ~05:56--06:5x)
# and tick 0715 ran the chain's staged-fixture smoke (PR #1393, ~07:1x).
# That is documented GPU traffic in the gap window -- a recorded confound
# of this datum. Other sessions' traffic on this host is not ruled out.
#
# SHAPE/PROTOCOL. lanes 2,095,104 for both cells; 3 runs per cell, cell
# order rotated per run-pair (t31,t32 / t32,t31 / t31,t32); fresh kbb
# process per run; `date; uptime` recorded per run. Idempotent: a run whose
# log exists is skipped. Usage: run-sweep.sh B
set -e
cd "$(dirname "$0")/../../../.."
EV=docs/evidence/gpu/crosstick-gap-0530B-w64t32-20261020
PROBE=scripts/gpu-subgroup-reduce-chunksweep-pinned-3696ca0d.cljk
mkdir -p "$EV"
B="$1"
case "$B" in B) ;; *) echo "usage: $0 B" >&2; exit 2;; esac

# the probe bytes are the chain's or nothing: refuse to run anything else
echo "3696ca0db0e28c5b41fa5c8551df2ae1302deb190e91722408117a06077ef652  $PROBE" | shasum -a 256 -c - >/dev/null

run() { # pair-pos cell W chunks
  log="$EV/run-$B-$1-$2.log"
  if [ -f "$log" ] && grep -q "RESULT\tverified=true" "$log"; then echo "skip $log"; return 0; fi
  echo "run $log"
  (date; uptime; time kbb --backend sci "$PROBE" "$3" 2095104 "$4") > "$log" 2>&1
  grep -q "RESULT	verified=true" "$log" || { echo "UNVERIFIED $log"; exit 1; }
}

# pair 1: t31,t32   pair 2: t32,t31   pair 3: t31,t32
run 1 w64t31 64 31
run 1 w64t32 64 32
run 2 w64t32 64 32
run 2 w64t31 64 31
run 3 w64t31 64 31
run 3 w64t32 64 32
echo "BATCH-$B-COMPLETE"
