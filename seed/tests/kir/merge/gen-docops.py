#!/usr/bin/env python3
"""seed/tests/kir/merge/gen-docops.py <out> <lines> [seed] -- a deterministic op corpus for docops.cljk (agent KIR4,
BOOTSTRAP-TOOL: test input only). A model of the stack's kinds keeps most ops well-typed; set items and map keys are made
distinct by construction (a counter), so the corpus is meant to run to its end on both backends."""
import random
import sys

out, n = sys.argv[1], int(sys.argv[2])
rnd = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 7)
ALPH = ['a', 'b', 'Z', ' ', '"', '\\', '\t', '\u0001', '\u001f', 'é', 'ß', '中', '😀', '/', ':', '{', ']', '#']
cnt = [0]


def fresh_scalar():
    cnt[0] += 1
    r = rnd.random()
    if r < 0.4:
        return 'i%d' % (cnt[0] * rnd.choice([1, -1, 7919, -104729, 1000000007]) if rnd.random() < 0.9 else rnd.choice([-9223372036854775808, 9223372036854775807, 0])), 'i'
    if r < 0.8:
        return 's' + ''.join(rnd.choice(ALPH) for _ in range(rnd.randint(0, 6))) + str(cnt[0]), 's'
    return 'k%d' % (cnt[0] % 10), 'k'


lines, st, dp = [], [], []


def push(line, kind, depth=1):
    lines.append(line)
    st.append(kind)
    dp.append(depth)


def wrap(k, kind):
    d = 1 + max(dp[len(dp) - k:] or [0])
    st[len(st) - k:] = []
    dp[len(dp) - k:] = []
    st.append(kind)
    dp.append(d)


while len(lines) < n:
    if len(lines) % 40 == 39 and st:
        lines.append('R')
        st[:] = st[-1:]
        dp[:] = dp[-1:]
        continue
    if len(st) > 12:
        while len(st) > 4:
            lines.append('p')
            st.pop()
            dp.pop()
        continue
    r = rnd.random()
    top = st[-1] if st else None
    if r < 0.30 or not st:
        x = rnd.random()
        if x < 0.85:
            push(*fresh_scalar())
        else:
            push(rnd.choice(['n', 't', 'f']), 'n' if x < 0.9 else 'b')
    elif r < 0.40:
        k = rnd.randint(0, min(4, len(st)))
        if 1 + max(dp[len(dp) - k:] or [0]) > 6:
            lines.append('p'); st.pop(); dp.pop(); continue
        lines.append('v%d' % k); wrap(k, 'v')
    elif r < 0.45:
        k = rnd.randint(0, min(4, len(st)))
        if 1 + max(dp[len(dp) - k:] or [0]) > 6:
            lines.append('p'); st.pop(); dp.pop(); continue
        lines.append('l%d' % k); wrap(k, 'l')
    elif r < 0.50:  # a set of fresh distinct items
        k = rnd.randint(0, 4)
        kinds = set()
        for _ in range(k):
            ln, kd = fresh_scalar()
            if kd != 's':
                ln = 'i%d' % cnt[0]
            push(ln, 'i')
        lines.append('S%d' % k); wrap(k, 'S')
    elif r < 0.56:  # a map of fresh distinct keys
        k = rnd.randint(0, 3)
        used = set()
        for _ in range(k):
            d = rnd.randrange(10)
            while d in used:
                d = rnd.randrange(10)
            used.add(d)
            push(rnd.choice(['k%d' % d, 'i%d' % (1000 + d)]), 'x')
            ln, kd = fresh_scalar() if rnd.random() < 0.8 else (('v0', 'v'))
            push(ln, kd, 2 if kd == 'v' else 1)
        lines.append('M%d' % k); wrap(2 * k, 'M')
    else:
        ops = ['x', 'K', 'N', 'V', 'I', 'B', 'W'] + (['E'] if len(st) > 1 else [])
        if top in ('v',):
            ops += ['o', 'z', 'D0', 'D1', 'r0', 'c'] if len(st) > 1 else ['o', 'z']
        if top == 'l':
            ops += ['Z']
        if top == 'M':
            ops += ['Y']
        if len(st) > 1 and st[-2] == 'M':
            ops += ['g', 'C']
        if len(st) > 2 and st[-3] == 'M':
            ops += ['a', 'a']
        if len(st) > 1 and st[-2] == 'M' and top == 'M':
            ops += ['m']
        if len(st) > 1 and st[-2] == 'S':
            ops += ['H']
        if len(st) > 1 and st[-2] == 'v':
            ops += ['c', 'A']
        op = rnd.choice(ops)
        if op in ('N',) and top not in ('v', 'l', 'S', 'M'):
            op = 'K'
        if op in ('D1', 'r0', 'z', 'o') and top == 'v':
            pass
        lines.append(op)
        if op in ('x', 'o', 'D0', 'D1', 'r0', 'Y', 'Z', 'z'):
            st[-1] = {'o': 'v', 'D0': 'v', 'D1': 'v', 'r0': 'v', 'Y': 'v', 'Z': '?', 'z': '?'}.get(op, top)
        elif op in ('K', 'N', 'V', 'I', 'B', 'W'):
            st[-1] = {'K': 'k', 'N': 'i'}.get(op, '?')
        elif op in ('E', 'C', 'H', 'g', 'c', 'A', 'm'):
            st[-2:] = [{'E': 'b', 'C': 'b', 'H': 'b', 'g': '?', 'c': 'v', 'A': 'v', 'm': 'M'}[op]]
            d = max(dp[-2], dp[-1] + (1 if op in ('c', 'A') else 0))
            dp[-2:] = [d]
        elif op == 'a':
            st[-3:] = ['M']
            d = max(dp[-3], dp[-1] + 1, dp[-2] + 1)
            dp[-3:] = [d]
        if len(dp) and dp[-1] > 6:
            lines.append('p'); st.pop(); dp.pop()
open(out, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
