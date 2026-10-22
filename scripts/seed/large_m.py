#!/usr/bin/env python3
"""scripts/seed/large_m.py <MEMORY-MAP> -- rewrite a seed MEMORY-MAP into the LARGE-M build profile (agent ARENA,
2026-10-04; seed/profiles/README.md). BOOTSTRAP-TOOL (python3). In place.

M grows from 8 Mi to 16 Mi words (= the loader's 16,777,216-item per-vector boundary). Every fixed region keeps its
record width W and gets the capacity below; regions are re-based in file order from word 256, the heap takes the rest.
The table is FRONT's/COMPOSE's (CONTRACT-REQUESTS 2026-10-03 FRONT, COMPOSE): it holds the whole linked kotoba-sema
frontend (~435k KIR tokens) as one compile-kir program.

Checked here (refuse instead of a silent miscompile):
  - the regions and the heap fit in M (heap >= 1 Mi words);
  - 30-lower packs a loop context as tail + 2*node + 2^21*label and masks the node with 2^20-1 (lw-kn / lw-kl /
    lw-kmk, the FRONT fix): NODE-CAP must stay <= 2^20. The mask is read from seed/30-lower.kotoba when it sits next
    to the map, so a narrower mask is caught too.
"""
import os
import re
import sys

WORDS = 16777216
CAPS = [('TOK', 655360), ('NODE', 458752), ('SYM', 65536), ('HASH', 131072), ('FN', 16384), ('SCOPE', 65536),
        ('SIR', 458752), ('LABEL', 262144), ('CODE', 1048576), ('FIX', 131072), ('LIT', 32768), ('LITB', 524288),
        ('EXP', 8192), ('OUT', 3145728)]


def die(msg):
    sys.stderr.write('large_m: ' + msg + '\n')
    sys.exit(1)


def main():
    p = sys.argv[1]
    s = open(p).read()
    if s.count('[:c MM-WORDS 8388608') != 1:
        die('MM-WORDS 8388608 not found exactly once (already large, or the map changed)')
    s = s.replace('[:c MM-WORDS 8388608', '[:c MM-WORDS %d' % WORDS, 1)
    names = re.findall(r'\[:c MM-([A-Z0-9]+)-BASE \d+\] \[:c MM-\1-W \d+\] \[:c MM-\1-CAP \d+\]', s)
    if names != [n for n, _ in CAPS]:
        die('region list differs from the profile table: %s' % names)
    base = 256
    for name, cap in CAPS:
        m = re.search(r'\[:c MM-%s-BASE (\d+)\] \[:c MM-%s-W (\d+)\] \[:c MM-%s-CAP (\d+)\]' % (name, name, name), s)
        w = int(m.group(2))
        if cap < int(m.group(3)):
            die('%s: the profile capacity %d is below the default %s' % (name, cap, m.group(3)))
        s = s[:m.start()] + '[:c MM-%s-BASE %d] [:c MM-%s-W %d] [:c MM-%s-CAP %d]' % (name, base, name, w, name, cap) + s[m.end():]
        base += w * cap
    if WORDS - base < 1048576:
        die('heap below 1 Mi words (%d)' % (WORDS - base))
    s, n = re.subn(r'\[:c MM-HEAP-BASE \d+\] \[:c MM-HEAP-END \d+\]',
                   '[:c MM-HEAP-BASE %d] [:c MM-HEAP-END %d]' % (base, WORDS), s)
    if n != 1:
        die('MM-HEAP-BASE/END not found exactly once')
    lower = os.path.join(os.path.dirname(os.path.abspath(p)), '30-lower.kotoba')
    if os.path.exists(lower):
        m = re.search(r'\(defn- lw-kn \[k :i64\] :i64 \(bit-and \(u64-shift-right k 1\) (\d+)\)\)', open(lower).read())
        if not m:
            die('30-lower lw-kn not found: cannot check the loop-node mask')
        node_cap = dict(CAPS)['NODE']
        if node_cap > int(m.group(1)) + 1:
            die('NODE-CAP %d exceeds the 30-lower loop-node mask %s' % (node_cap, m.group(1)))
    open(p, 'w').write(s)
    print('large_m: M %d words, regions end %d, heap %d words' % (WORDS, base, WORDS - base))


if __name__ == '__main__':
    main()
