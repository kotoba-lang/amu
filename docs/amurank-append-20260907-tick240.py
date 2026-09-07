import os
p = 'docs/codegen-coscientist.md'
s = open(p).read()
entry = ('2026-09-07 22:50+ JST (amu-rank cron, tick 240): rank-only busy pass, no measurement by role. '
         'git fetch: origin/main ADVANCED since tick-239 read - 342e14d6 -> 69c1fd9a (two commits: PR #878 build-scaling-coscientist doc iteration 2 '
         '"the reader was the quadratic" docs/build-scaling-coscientist.md +137, and PR #877 sema-reader-line-index: pins kotoba-sema 31d0d463 '
         'reader stops re-splitting the prefix + doc rename). Both are doc/pin-only, origin-namespace, NOT local-reconcilable, NOT cited as a local '
         'verdict (rank rule: reconciliation authoritative only after operator merge); neither alters the local fleet gate. Host busy (pre-run monitor '
         '22:38 load1 20.50; live probe 22:46 load1 17.40 / 5m 17.17 / 15m 21.68, up 2d 15:29, 10 users, threshold 7.5) - measurement refused; the only '
         'correct measurement route (fleet) remains blocked locally below. Working-tree evidence reviewed since the tick-239 commit (HEAD 09928bb3, '
         'via git diff HEAD): the ONLY uncommitted doc changes are sibling busy-refusals - added to the H-C2 evidence cell amu-bench 22:24 (load1 '
         '22.89), amu-falsify 22:31 (load1 16.69), amu-falsify 22:46 (load1 17.40), and added to the Iteration-log tail amu-bench 22:50 (load1 9.96 / '
         '5m 22.18 / 15m 25.17, still above the 7.5 gate) - all busy refusals, NOT new LOCAL measured numbers; folded into this commit. No new local '
         'codegen ADR since 0339 (J-B idle-gate +7.3/+7.0/+6.4% 17-consecutive-positive separated - but ADR 0339 and predecessors 0335/0338 all stamp '
         "'diagnostic only, full quiet gate still unmet', so perfgate.core/qualify confirmation is STILL pending; ADR 0339 itself remains "
         'UNTRACKED/residue locally). No new LOCAL measured verdict -> no re-rank, no status transition, no new hypothesis; population unchanged: '
         'H-Z3 top of codegen ladder (quiet-host A/B still blocked), H-C2 open w/ ceiling-caution (statically 61/61, timed A/B UNRESOLVED, notional '
         '~4.4% pending quiet host), H-D/H-B/H-Y1 open. BLOCKER unchanged double (re-probed live this tick): scripts/quiet-host.cljs + '
         'scripts/remote-bench.cljs STILL ABSENT from this workdir (PR #819 unmerged locally) while present on origin; guard-glob '
         '`git status --porcelain -- src bench scripts deps.edn` = 106 untracked lines (residue: append/probe scripts under docs/ + scripts/, '
         'bench/runtime-comparison/kernel.kotoba.wasm.{provenance,publication}.edn sidecars, tmp/, build.sh, Q9-migration-plan.edn, '
         'test-kotoba-pipeline.sh, w1-pure.wasm.{provenance,publication}.edn), so even a merged PR #819 would exit-2 on remote-bench.cljs\'s '
         'uncommitted-tree guard until that residue is committed or cleared. Fleet-path measurement remains blocked until then. NEXT (unchanged, '
         'tick-213..239 rank authority): operator merges origin/main plus commits/clears the docs/+scripts/+bench/+tmp residue; THEN H-Z3 quiet-host '
         'A/B (top lever), then H-C2 ceiling-check A/B on a qualifying fleet node. Appended via python script file (no heredoc / no -e/-c / no shell '
         'redirect).\n\n## Standing honesty constraints')
marker = '## Standing honesty constraints'
if marker in s:
    s = s.replace(marker, entry)
    open(p, 'w').write(s)
    print('APPENDED')
else:
    print('MARKER NOT FOUND - ABORT')