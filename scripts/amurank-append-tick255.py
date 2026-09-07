#!/usr/bin/env python3
# amu-rank tick 255 append: fold sibling busy-refusals (04:30 falsify, 04:40 bench, 04:58 falsify)
# and our own 05:03 host-busy refusal into the iteration log.
line = (
"2026-09-08 05:03 JST (amu-rank cron, tick 255): host busy (load1 17.02 / "
"5m 24.96 / " "15m 36.28, up " "2d 21:46, " "10 users, threshold" " 7.5) — measurement refused, "
"rank-only busy pass. git fetch clean (no new origin commits; HEAD" " 51e6b1ac, origin/main unchanged" " 55e47f90, "
"fleet blocker still operator-only: remote-bench exit-2 guard-glob re-measured" " 117 untracked lines this tick "
"(`git status --porcelain -- src bench scripts deps.edn` = " "117, up from" " 116 at tick" " 254) + origin" " 55e47f90 "
"unreconciled). Folded" " 3 sibling busy-refusals landed since tick" " 254 (" " 04:30 falsify load1 45.40, "
"no measurement;" " 04:40 bench load1 97.55/71.06/59.09,  ​10-core busy-fraction ~9.76 >>" " 0.10, "
"no measurement;" "  ​04:58 falsify load1 27.43, no measurement) + no new local codegen ADR beyond" " 0339 "
"(untracked, diagnostic-only, perfgate confirmation still PENDING)). No new LOCAL measured verdict -> no re-rank,"
"no status transition,no new hypothesis;; population unchanged: H-Z3 top (quiet-host A/B still blocked by guard-glob "
"residue+origin), H-C2 open ceiling-caution (static  61/61, timed A/B unresolved, notional ~4.4% awaiting quiet "
"host), H-D/H-B/H-Y1 open. NEXT (unchanged, rank authority)):: operator commits/clears the ~117-line residue + "
"merges origin/main,then quiet-host A/B on the idlest qualifying fleet node. Appended via python script at EOF.\n"
)
with open("docs/codegen-coscientist.md", "a", encoding="utf-8") as f:
    f.write(line)