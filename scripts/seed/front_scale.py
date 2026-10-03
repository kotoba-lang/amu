#!/usr/bin/env python3
"""scripts/seed/front_scale.py <in.kotoba> <K> <out.kotoba> -- a K-times larger closed program for the native analyze
ladder (agent ARENA, 2026-10-04). BOOTSTRAP-TOOL (python3), measurement input only.

The input is one of MEM2's ladder programs (scripts/selfhost-wall/analyze-memory-inputs.py: a seed MANIFEST prefix as a
closed one-namespace program that analyses to the end). Copy 1 is the input unchanged; copies 2..K repeat everything after
the `ns` form with every top-level `def`/`defn`/`defn-` name NAME renamed NAME__cK at every symbol occurrence, so the
copies are independent definitions of the same shape. The program means the same (copy 1's `main` is the export), and
its analysis does K times the per-definition work; the ladder then shows how the per-byte cost grows past one module.
"""
import re
import sys

DELIM = r'[\s()\[\]{}"\';,@^`~#]'


def main():
    src, k, dst = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    s = open(src).read()
    m = re.match(r'\(ns [^\n]*\n', s)
    if not m:
        sys.exit('front_scale: the first line must be the (ns ...) form')
    head, body = s[:m.end()], s[m.end():]
    names = set(re.findall(r'^\(defn?-? ([^\s\[\]()]+)', body, re.M))
    pat = re.compile(r'(?<![^\s()\[\]{}"\';,@^`~#])(' + '|'.join(re.escape(n) for n in sorted(names, key=len, reverse=True)) +
                     r')(?![^\s()\[\]{}"\';,@^`~#])')
    out = [head, body]
    for c in range(2, k + 1):
        out.append('\n;; ---- copy %d (front_scale.py) ----\n' % c)
        out.append(pat.sub(lambda mm: mm.group(1) + '__c%d' % c, body))
    open(dst, 'w').write(''.join(out))
    print('front_scale: %d names, %d copies, %d bytes' % (len(names), k, sum(len(x) for x in out)))


if __name__ == '__main__':
    main()
