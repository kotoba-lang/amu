import io, sys

P = "docs/codegen-coscientist.md"
anchor = "## Standing honesty constraints"

entry = (
    "| 2026-09-07 16:19 JST (amu-rank cron, tick 220): rank-only pass, no measurement by "
    "role. git fetch: origin/main ADVANCED 78cdc2e1 -> f57e8142 via PR #859 "
    "(agent/defcid-probe, ADR-0342 + README) - a DOC-ONLY merge: `git diff --stat "
    "78cdc2e1..f57e8142` = README.md (+34/-9) + one new ADR (docs/adr/0342-the-readme-kept-a-rule-the-adr-had-already-retired.md), "
    "NO change under src/, bench/, scripts/. Origin MVP ladder NOT advanced; "
    "origin-namespace fact, not local-reconcilable (reconciliation authoritative only "
    "after operator merge). Host busy and irrelevant to rank: pre-run HOST LOAD 57.61 / "
    "69.56 / 66.58 (up 2 days 9:01, 12 users, threshold 7.5) - measurement refused; the "
    "only correct measurement route (fleet) remains blocked below. Working-tree evidence "
    "reviewed since the tick-219 commit (HEAD 1e779349): the only uncommitted append on "
    "top of that commit is the small sibling busy-refusal residue (amu-falsify H-C2 "
    "evidence-row 16:02 load1 28.23 + trailing blank) - a busy refusal, NOT a new LOCAL "
    "measured number; no new local codegen ADR (0339 remains newest local measured "
    "landing, J-B idle-gate +7.3/+7.0/+6.4% 17-consecutive-positive, perfgate.core/"
    "qualify confirmation still pending). No new LOCAL measured verdict -> no re-rank, "
    "no status transition, no new hypothesis; population unchanged: H-Z3 top of codegen "
    "ladder (quiet-host A/B still blocked; ledger-145 caution: kill div without adding a "
    "serial chain), H-C2 open w/ ceiling-caution (statically 61/61, timed A/B "
    "UNRESOLVED, notional ~4.4% pending quiet host), H-D/H-B/H-Y1 open. BLOCKER "
    "unchanged (re-probed live this tick): scripts/quiet-host.cljs + scripts/remote-bench.cljs "
    "STILL ABSENT (PR #819 unmerged locally), guard-glob `git status --porcelain -- src "
    "bench scripts deps.edn` stays 101 untracked lines, so even a merged PR #819 would "
    "exit-2 on remote-bench.cljs's uncommitted-tree guard until residue is committed/"
    "cleared. NEXT (unchanged, rank authority): operator merges origin/main and commits/"
    "clears the docs/+scripts/+bench/+tmp residue (incl. untracked ADR 0339), then H-Z3 "
    "quiet-host A/B, then H-C2 ceiling-check A/B on a qualifying fleet node. Appended "
    "via python script (no heredoc / no -e/-c).\n"
)

with io.open(P, "r", encoding="utf-8") as f:
    text = f.read()

if anchor not in text:
    sys.exit("anchor not found; aborting without edit")

if "tick 220" in text:
    sys.exit("tick 220 entry already present; skipping (re-run detection)")

text = text.replace(anchor, entry + "\n" + anchor, 1)

with io.open(P, "w", encoding="utf-8") as f:
    f.write(text)

print("ok: tick 220 entry appended before", anchor)