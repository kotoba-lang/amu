#!/bin/sh
# CROSS-TICK TWO-BATCH SIGN PROBE (JUN-58, tick 20261020-0949):
# batch A already exists -- the 0916 tick's batch B logs (09:20:39--09:24:18
# JST, Oct 20), copied here byte-identical as run-A-*.log (sha256 in
# README). This script runs batch B NOW, in a later cron tick / fresh
# process, after batch A ended.
#
# WHY CROSS-TICK. The 2254 tick proved a >=30 min gap cannot fit this
# platform's 1800 s run budget INSIDE one tick (3 evidences); the 2337 tick
# bounded within-session stability at a 6m52s gap (no flip); the 0006/0530/
# 0736/0805/0840/0916 ticks hold the cross-tick series (70m26s no flip /
# 318m29s w64t32 no flip, anchor INCONCLUSIVE under load / 124m20s no flip /
# 27m27s no flip, chain's first 12/12-IQR-clean comparison / 29m21s flip
# cell no flip (noise-labeled), anchor INCONCLUSIVE under load / 30m14s flip
# cell no flip (noise-labeled), anchor sign-unanimous -/-/-
# clean-vs-noise). The flip-RATE question needs more cross-session
# transitions, and each cross-tick batch adds exactly one. This probe is
# explicitly labeled CROSS-SESSION and cannot isolate "gap" from "session
# restart"; a FLIP or a no-flip is reported as a cross-tick datum only. A
# no-flip bounds nothing against a stochastic flip rate.
#
# PROBE IDENTITY. The probe bytes are the chain's pinned sha256 3696ca0d...
# (the 2254/2337/0006/0530/0736/0805/0840/0916 runs all used these exact
# bytes). origin/main's scripts/test-gpu-subgroup-reduce-chunksweep.cljk has
# SINCE ADVANCED and computes GAP differently -- so batch B runs the PINNED
# copy scripts/gpu-subgroup-reduce-chunksweep-pinned-3696ca0d.cljk
# (byte-identical to the chain, verified by sha256 before every use). Its
# root resolution (script dir / .. = repo root) is why the pinned copy lives
# under scripts/. Fixtures identical to the chain (w64 a25a6931...,
# self-printed by every SHAPE line and self-asserted by the probe before
# dispatch).
#
# CHAIN INPUTS AT THIS BASE (the PR #1393 staging rule). This worktree's
# base is origin/main 2f04a37e -- the chain's FIRST base on/after #1393's
# merge, so the staging rule is NOT a no-op here: test/fixtures/gpu/ in the
# checkout holds the regenerated post-fix bytes, and
# `sh scripts/gpu-sign-chain-stage-fixtures.sh.txt` was run from this
# worktree root before dispatch, restoring the chain's pinned pre-fix bytes
# over them (all four sha256 re-verified against the archive README's table:
# w32 0cf6c406..., w64 a25a6931..., w128 c7931718..., w256 087107f9...).
# The rule's invariant (the probe sees the bytes every prior datum ran) is
# preserved by that staging step.
#
# BASE NOTE. Batch A ran on origin/main 9b084efe (tick 0916's worktree);
# batch B runs on origin/main 2f04a37e -- the chain's first cross-tick pair
# with a non-empty base delta. The delta (9b084efe..2f04a37e) lands #1391
# and #1393 (exec-postfix partial-matrix fail/INFO recording, the fixed
# subgroup-reduce emitter + test, fixture regeneration + .sh driver
# renames). The executed variant arm is byte-identical to every earlier
# datum (the SHAPE line's fixture sha256 is the check) and the probe bytes
# are the chain's pinned bytes, so the dispatched computation is unchanged;
# the base delta is recorded here as a chain-note input, not analyzed as an
# executed-path change.
#
# GAP PROVENANCE. The wall-clock window between batch A (ended 09:24:18 Oct
# 20) and batch B (first run this tick) carried NO documented amu-gpu GPU
# dispatch: this tick's pre-dispatch work was git reads/fetch, worktree
# creation, the fixture staging run, file copies and sha256 checks only.
# Other sessions' GPU traffic on this host is not ruled out. Recorded as a
# confound of this datum.
#
# SHAPE/PROTOCOL. lanes 2,095,104 for both cells; 3 runs per cell, cell
# order rotated per run-pair (t31,t32 / t32,t31 / t31,t32); fresh kbb
# process per run; `date; uptime` recorded per run. Idempotent: a run whose
# log exists is skipped. Usage: run-sweep.sh B
set -e
cd "$(dirname "$0")/../../../.."
EV=docs/evidence/gpu/crosstick-gap-0916B-w64t32-20261020
PROBE=scripts/gpu-subgroup-reduce-chunksweep-pinned-3696ca0d.cljk
mkdir -p "$EV"
B="$1"
case "$B" in B) ;; *) echo "usage: $0 B" >&2; exit 2;; esac

# the probe bytes are the chain's or nothing: refuse to run anything else
echo "3696ca0db0e28c5b41fa5c8551df2ae1302deb190e91722408117a06077ef652  $PROBE" | shasum -a 256 -c - >/dev/null

run() { # pair-pos cell W chunks
  log="$EV/run-$B-$1-$2.log"
  if [ -f "$log" ]; then echo "skip $log"; return 0; fi
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
