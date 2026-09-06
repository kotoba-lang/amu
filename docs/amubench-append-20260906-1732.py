import datetime

entry = ("| 2026-09-06 17:3x JST (amu-bench cron, tick): no measurement runnable. "
         "Two independent gates, recorded honestly. (1) This workstation load1 = 112.88 / 5m 120.03 / 15m 105.47 "
         "(\"17:31  up 1 day, 10:14, 13 users\" via uptime probe; threshold 7.5) is ~15x above the workstation quiet gate "
         "-- but per rank ticks 155/156 this workstation load1 is the WRONG measurement quantity anyway; the correct "
         "path is a qualifying fleet node (busy-CPU < 0.10). (2) The fleet path is STILL unavailable: "
         "scripts/quiet-host.cljs and scripts/remote-bench.cljs from PR #819 do NOT exist in the local tree "
         "(ls returns \"No such file or directory\"; HEAD ec0f71cb, rank tick 161, PR #819 blocker persists -- "
         "operator merge pending per rank precedent). Even after merge, remote-bench.cljs refuses an uncommitted tree "
         "over `git status --porcelain -- src bench scripts deps.edn` (exit 2), which currently shows "
         "M docs/codegen-cosientist.md, M docs/jit-cosientist.md, ?? bench/runtime-comparison/kernel.kotoba.wasm.provenance.edn, "
         "?? bench/runtime-comparison/kernel.kotoba.wasm.publication.edn, ?? docs/adr/0339...md and ~6 untracked "
         "append/probe .py files under docs/ -- so that guard would fail until the tree is committed/cleaned. "
         "Thus: NO bench, NO perfgate.core/qualify run, NO numbers recorded this tick (fabricating fleet results is forbidden). "
         "Population unchanged: H-C2 statically confirmed 61/61 but timed A/B UNRESOLVED (two polluted local attempts), "
         "J-B replicated-diagnostic (perfgate pending, ADR 0339), H-Z3 top of codegen ladder (hand-patch A/B pending, "
         "H-Z1 folded), H-D/H-B/H-Y1 open; J-C blocked behind J-B's perfgate verdict. "
         "NEXT (rank authority, unchanged): operator merges PR #819 locally (gains scripts/quiet-host.cljs + "
         "scripts/remote-bench.cljs) AND commits/cleans the tree so remote-bench's uncommitted-tree guard passes; "
         "THEN amu-bench runs H-C2 timed hand-patch A/B via remote-bench.cljs on a qualifying fleet node "
         "(busy-CPU < 0.10, quiet-host.cljs exit=qualified), then H-Z3 quiet-host hand-patch A/B, then J-B perfgate "
         "confirmation. Until the merge lands locally, bench should not wait on this workstation's load1 - it is the wrong "
         "quantity. This entry appended via python script file (no heredoc, entry-117 convention).\n")

path = '/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md'
with open(path, 'r', encoding='utf-8') as f:
    doc = f.read()

marker = '## Standing honesty constraints'
idx = doc.rfind(marker)
if idx == -1:
    raise SystemExit('marker not found')

new_doc = doc[:idx] + entry + '\n' + doc[idx:]
with open(path, 'w', encoding='utf-8') as f:
    f.write(new_doc)

with open(path, 'r', encoding='utf-8') as f:
    check = f.read()
ok = '17:3x JST (amu-bench cron, tick): no measurement runnable' in check and marker in check
print('appended, verify:', ok, 'len:', len(check))