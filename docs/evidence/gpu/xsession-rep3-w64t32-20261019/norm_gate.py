#!/usr/bin/env python3
"""Normalize FAIL/ERROR entries (kind + test name + failure-body digest) from
gate logs and diff them.

Usage: python3 norm_gate.py <log> [<log> ...]
Prints per-log occurrence counts and a cross-log set comparison against the
first log. Used by amu-gpu ticks to compare a tick's canonical gate against
the documented base red (PR #1359's completed gate log).

The entry key includes a digest of the failure BODY (assertion/exception
text), normalized for run-varying paths and addresses: two runs whose
headers match but whose failures are for different reasons must NOT
compare as SETS-AND-COUNTS-IDENTICAL (review finding).
"""
import hashlib
import re
import sys
from collections import Counter

HEADER = re.compile(r'^(FAIL|ERROR) in \(([^)]+)\)', re.M)


def normalize(body):
    # temp dirs and addresses vary per run; the assertion text does not
    body = re.sub(r'/\S*tmp\S*', '/TMP', body)
    body = re.sub(r'0x[0-9a-fA-F]+', '0xADDR', body)
    return body.strip()


def entries(path):
    text = open(path, encoding='utf-8', errors='replace').read()
    out = Counter()
    matches = list(HEADER.finditer(text))
    for i, m in enumerate(matches):
        kind, name = m.group(1), m.group(2)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = normalize(text[m.end():end])
        digest = hashlib.sha256(body.encode('utf-8', 'replace')).hexdigest()[:8]
        out[(kind, name, digest)] += 1
    return out


def main(argv):
    if len(argv) < 2:
        print('usage: norm_gate.py <log> [<log> ...]')
        return 2
    logs = [(p, entries(p)) for p in argv[1:]]
    for p, c in logs:
        total = sum(c.values())
        print(f'== {p}')
        print(f'occurrences: {total}, distinct kind+name+body-digest: {len(c)}')
        for (kind, name, digest), n in sorted(c.items()):
            print(f'{n:3d}  {kind} in ({name}) [{digest}]')
    if len(logs) > 1:
        base_p, base = logs[0]
        for p, c in logs[1:]:
            print(f'== diff vs {base_p}')
            only_base = set(base) - set(c)
            only_new = set(c) - set(base)
            changed = {k for k in set(base) & set(c) if base[k] != c[k]}
            print(f'entries only in base: {sorted(only_base) or "none"}')
            print(f'entries only in {p}: {sorted(only_new) or "none"}')
            for k in sorted(changed):
                print(f'count changed: {k[0]} in ({k[1]}) [{k[2]}]: base={base[k]} new={c[k]}')
            same = not (only_base or only_new or changed)
            print('SETS-AND-COUNTS-IDENTICAL' if same else 'DIFFERS')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
