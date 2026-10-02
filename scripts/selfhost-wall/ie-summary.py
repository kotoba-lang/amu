#!/usr/bin/env python3
"""Summarise an infer differential: ie-summary.py CASES ANSWERS... (answers in the order of the cases, parts interleaved
as ie-diff.sh splits them). Prints per-op counts and the first few disagreements."""
import sys, re, collections
cases = [l for l in open(sys.argv[1]).read().split('\n') if l.strip()]
parts = int(sys.argv[2]); answers = sys.argv[3:]
rows = []
for k, fn in enumerate(answers):
    mine = cases[(k - 1) % parts::parts]   # ie-diff.sh: awk NR%parts puts 1-based line NR in part NR%parts
    outs = open(fn).read().split('\n')
    for c, o in zip(mine, outs):
        rows.append((re.match(r'^\["(\w+)"', c).group(1), o.split(' ')[0], c, o))
cnt = collections.Counter((op, k) for op, k, _, _ in rows)
for key, v in sorted(cnt.items()): print(key, v)
print('total', len(rows), 'of', len(cases))
shown = 0
for op, k, c, o in rows:
    if k not in ('OK', 'OKERR') and shown < 10:
        print('==', op, k, o[:300].replace('\n', ' ')); shown += 1
