import datetime

path = '/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md'
entry = (
    " | 2026-09-06 15:31 JST bench tick: host busy (load1 12.14-15.01 "
    "sustained across 10 sysctl vm.loadavg samples 15:27-15:31, "
    "load5 13.13-13.68, load15 26.80-26.97, up 1d8h, 10 users, threshold 7.5) - "
    "quiet window (load1 5.85 at 15:22) closed before start; no "
    "bench/runtime-comparison, no perfgate run, no numbers. H-C2 timed A/B "
    "(amu-mut vs clang kernel stream, ~4.4% gap, static 61/61 confirmed) still "
    "needs a window that holds load1<7.5 sustained THROUGH all trials "
    "(two prior attempts 14:00-14:03 and ~14:43 polluted by load spikes 98-119)"
)

txt = open(path).read()
lines = txt.splitlines()
target = None
for i, l in enumerate(lines):
    if l.startswith('| H-C2 | the remaining ~4.4% vs Clang'):
        target = i
        break
if target is None:
    raise SystemExit('H-C2 row not found')
lines[target] = lines[target] + entry
open(path, 'w').write('\n'.join(lines) + '\n')
print('appended busy-refusal to H-C2 row line', target + 1)