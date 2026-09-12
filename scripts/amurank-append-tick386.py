import datetime
line = ("\n2026-09-12 14:0x JST (amu-rank cron, tick 386): rank-only pass; host busy "
        "(load1 45.37 / 5m 27.10 / 15m 19.17 at 14:03, threshold 7.5) - measurement refused. "
        "git fetch/review: local HEAD c3d9dbca (tick 385); origin/main 18ef21dd unchanged since "
        "tick 385's review - no new commits, no re-rank. Sibling in-flight edits "
        "(M docs/codegen-coscientist.md, M docs/jit-cosientist.md, D scripts/quiet-host.cljk) untouched; "
        "no new measured evidence since the last committed tick -> no status transition, no new hypothesis. "
        "Population unchanged: benjamin imod hand-patch (J-B2/H-Z3) first, fallback H-C2; H-D, H-B, H-Y1 open. "
        "NEXT: H-Z3 quiet-host hand-patch A/B (only measured above-bar effect, needs a sustained idle>=9/10 window), fallback H-C2.\n")
p = 'docs/codegen-coscientist.md'
s = open(p).read()
marker = '## Standing honesty constraints'
i = s.rindex(line[:30]) if line[:30] in s else -1
j = s.index(marker)
open(p, 'w').write(s[:j] + line.lstrip('\n') + '\n' + s[j:])
print('ok')
