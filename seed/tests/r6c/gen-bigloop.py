#!/usr/bin/env python3
"""seed/tests/r6c/gen-bigloop.py <out.kotoba> -- the loop-node-width gate case (agent R6C, 2026-10-03; BOOTSTRAP-TOOL).

FRONT found (seed/CONTRACT-REQUESTS.md, 2026-10-03) that 30-lower packed a loop's node index in 17 bits, so a `loop` whose
read node is >= 131,072 recurred to the wrong header; R6B widened it to 20 bits. This writes a program whose `loop` nodes
sit above node 131,072 (filler defns first), prints the read-node index of the first `loop` form and the value main must
answer (computed here, in Python, from the same arithmetic), as `nodes <first-loop-node> want <value>`.
"""
import sys

N = 7600            # filler functions: ~18 read nodes each
MASK = (1 << 64) - 1


def wrap(v):
    v &= MASK
    return v - (1 << 64) if v >> 63 else v


def f(k, x):  # (defn- fK [x :i64] :i64 (+ (* x K) (- x 1) (bit-xor x K)))
    return wrap(wrap(x * k) + (x - 1) + (x ^ k))


lines = ['(ns r6c.bigloop (:export [main]))']
for k in range(N):
    lines.append(f'(defn- f{k} [x :i64] :i64 (+ (* x {k}) (- x 1) (bit-xor x {k})))')
# two loops late in the file: a nested pair, so a wrong header is observable either way
lines.append('(defn- g [n :i64] :i64 (loop [i 0 acc 0] (if (< i n) (recur (+ i 1) (+ acc (loop [j 0 s 0] (if (< j i) (recur (+ j 1) (+ s (f7 j))) s)))) acc)))')
lines.append(f'(defn main [] :i64 (+ (g 12) (f{N - 1} 3)))')
src = '\n'.join(lines) + '\n'

# read-node count before the first `loop` list: root 1; per form, a list/vector = 1 + children, an atom = 1 (11-read)
def count_nodes(s, stop):
    n = 1  # the root
    i = 0
    while i < stop:
        c = s[i]
        if c in '([{':
            n += 1; i += 1
        elif c in ')]} \n\t,':
            i += 1
        else:
            j = i
            while j < len(s) and s[j] not in '()[]{} \n\t,':
                j += 1
            n += 1; i = j
    return n

first_loop = src.index('(loop')
node = count_nodes(src, first_loop)  # index of the `(loop` list node = nodes created before it (node 0 is the null record)
acc = 0
for i in range(12):
    acc = wrap(acc + sum(f(7, j) for j in range(i)))
want = wrap(acc + f(N - 1, 3))
open(sys.argv[1], 'w').write(src)
print(f'nodes {node} want {want}')
