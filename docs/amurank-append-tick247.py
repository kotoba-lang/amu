"""Append amu-rank cron tick 247 entry to docs/codegen-coscientist.md.
Inserts before the '## Standing honesty constraints' marker (sibling convention).
"""
import io

PATH = "docs/codegen-coscientist.md"
MARKER = "## Standing honesty constraints"

ENTRY = (
    "2026-09-08 01:36 JST (amu-rank cron, tick 247): rank-only busy pass, "
    "no measurement by role. git fetch: origin/main UNCHANGED since tick-246 "
    "read - still 55e47f90 (PR #880 build-scaling delivery-note, doc-only; "
    "origin-namespace, NOT local-reconcilable, NOT cited as a local verdict; "
    "reconciliation authoritative only after operator merge; does not alter "
    "the local fleet gate). Host busy (pre-run monitor 01:34 load1 54.82 / "
    "5m 42.48 / 15m 35.53, up 2d 18:17, 10 users, threshold 7.5) - measurement "
    "refused; the only correct measurement route (fleet) remains blocked "
    "locally. Working-tree reviewed via git diff HEAD (HEAD 5357e042, tick 246): "
    "the single uncommitted doc change on top of tick-246's commit is a sibling "
    "amu-falsify 2026-09-08 01:33 busy-refusal folded into the H-C2 evidence "
    "row (pre-run monitor load1 30.90 / 5m 24.08 / 15m 28.17, up 2d 18:13, "
    "10 users, threshold 7.5; no measurement, no numbers, NEXT remains H-C2) "
    "- a busy refusal, NOT a new LOCAL measured number; folded into this commit "
    "(preserved as evidence, not status-edited). No new local codegen ADR since "
    "0339 (J-B idle-gate +7.3/+7.0/+6.4% 17-consecutive-positive separated - "
    "but ADR 0339 and predecessors 0335/0338 still stamp 'diagnostic only, full "
    "quiet gate not yet met', so perfgate.core/qualify confirmation remains "
    "PENDING; ADR 0339 itself remains UNTRACKED/residue). No new LOCAL measured "
    "verdict -> no re-rank, no status transition, no new hypothesis; population "
    "unchanged: H-Z3 top of codegen ladder (quiet-host A/B still blocked), "
    "H-C2 open w/ ceiling-caution (statically 61/61, timed A/B UNRESOLVED, "
    "notional ~4.4% pending quiet host), H-D/H-B/H-Y1 open. BLOCKER unchanged "
    "(re-probed this tick via ls): scripts/quiet-host.cljs + "
    "scripts/remote-bench.cljs STILL ABSENT from this workdir (PR #819 unmerged "
    "locally) while present on origin; guard-glob `git status --porcelain -- "
    "src bench scripts deps.edn` stays 106 untracked lines (append/probe "
    "scripts under docs/ + scripts/, bench/runtime-comparison/kernel.kotoba."
    "wasm.{provenance,publication}.edn sidecars, tmp/, build.sh, "
    "Q9-migration-plan.edn, test-kotoba-pipeline.sh), so even a merged PR "
    "#819 would exit-2 on remote-bench.cljs's uncommitted-tree guard until "
    "that residue is committed or cleared. NEXT (unchanged, rank authority): "
    "operator merges origin/main and commits/clears the docs/+scripts/+bench/"
    "+tmp residue; then H-Z3 quiet-host A/B on a qualifying fleet node, then "
    "H-C2 ceiling-check A/B. "
    "Appended via python script (no heredoc, no -e/-c, insert-before marker)."
)

with io.open(PATH, "r", encoding="utf-8") as f:
    text = f.read()

idx = text.index(MARKER)
block = text[:idx].rstrip("\n") + "\n\n" + ENTRY + "\n\n" + text[idx:]

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(block)

print("appended tick 247 entry, before marker")