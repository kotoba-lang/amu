# judge.py <case-dir> <case-id> <host-cut-dir> <named.tsv>
# One `check` case of the native image against `bin/amu check` (BOOTSTRAP-REFERENCE: the nbb route of the same product
# entry; agent claude, 2026-10-10). <case-dir> holds h.out h.err h.rc (bin/amu) and g.out g.err g.rc (the image).
# Prints one line "<class>\t<detail>". The comparison:
#   exit status first (a different exit is DIFF, whatever the texts say);
#   both accept -> the stdout answer maps as EDN data (compare_artifact.parse: sets and maps unordered, types kept);
#   both refuse -> the :kotoba.cli-error/v1 report maps as data, on the same stream (stdout, stderr apart);
#   a different exit -> DIFF, unless a GAP row names the case's :exit pair AND its :error / :message pairs (STUB when
#   the image answers exit 69 :not-available: a declared stub, never a pass).
# Classes: SAME (exit, stdout, stderr byte-identical once the host's absolute case dir is cut), SAME-DATA (equal as
# data), NAMED (every difference is one row of named.tsv, matched by case, key AND both values; detail = the row ids),
# STUB, DIFF (detail = the unnamed differences). No difference is ignored by key alone: a named row fixes the value on
# both sides (or `absent`; `*` on the host side only for the two whole-corpus rules, each with its own extra condition
# below). A trap (exit 120, KEXE_TRAP) is always DIFF.
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'compile-twin'))
from compare_artifact import parse, top  # noqa: E402

d, case, cut, named_path = sys.argv[1:5]


def rd(name):
    text = open(os.path.join(d, name), errors='replace').read()
    return text.replace(cut.rstrip('/') + '/', '') if cut and cut != '-' else text


def edn(text):
    try:
        return parse(text)
    except Exception:
        return ('unparsed', text.strip())


def first_map(*texts):
    for t in texts:
        for line in t.split('\n'):
            line = line.strip()
            if line.startswith('{'):
                v = edn(line)
                if v[0] == 'm':
                    return top(v)
    return None


ABSENT = ('absent',)
named = []
for line in open(named_path, encoding='utf-8'):
    if not line.strip() or line.startswith('#'):
        continue
    f = line.rstrip('\n').split('\t')
    rid, kind, scope, key, hv, gv = f[:6]
    named.append((rid, kind, scope, key,
                  '*' if hv == '*' else (ABSENT if hv == 'absent' else edn(hv)),
                  ABSENT if gv == 'absent' else edn(gv)))


def match(key, h, g, a, b):
    """The named row explaining key's difference h (host) / g (image), or None. a, b: the whole maps."""
    for rid, kind, scope, k, hv, gv in named:
        if k != key or (scope != '*' and scope != case) or gv != g:
            continue
        if hv == '*':
            # whole-corpus rules; each holds only in the shape named, with its own condition
            if rid == 'definitions-marker' and isinstance(h, tuple) and h[0] == 'm' \
               and top(h).get(('k', ':contract')) == top(g).get(('k', ':contract')):
                return rid + ':' + kind
            if rid in ('reduced-report-diagnostic', 'reduced-report-details') and h is not ABSENT:
                return rid + ':' + kind
            continue
        if hv == h:
            return rid + ':' + kind
    return None


def compare(a, b):
    rows, bad = [], []
    for k in sorted(set(a) | set(b)):
        h, g = a.get(k, ABSENT), b.get(k, ABSENT)
        if h == g:
            continue
        m = match(k[1], h, g, a, b)
        (rows if m else bad).append(m or k[1])
    return rows, bad


hs, gs = rd('h.rc').strip(), rd('g.rc').strip()
ho, he, go, ge = rd('h.out'), rd('h.err'), rd('g.out'), rd('g.err')
if 'KEXE_TRAP' in ge or gs == '120':
    cls, det = 'DIFF', 'image trap exit %s: %s' % (gs, ge.strip().split('\n')[0][:120])
elif hs != gs:
    if gs == '69' and ':not-available' in (go + ge):
        cls, det = 'STUB', 'image stub, host exit ' + hs
    else:
        # a behaviour gap may be named too (kind GAP); it is never SAME
        a, b = first_map(ho, he) or {}, first_map(go, ge) or {}
        m = match(':exit', ('i', int(hs)), ('i', int(gs)), a, b) if hs.isdigit() and gs.isdigit() else None
        if m:
            # a named exit split: the refusal's identity (:error, :message) must be named too, value for value
            key = lambda mp: {k: v for k, v in mp.items() if k in (('k', ':error'), ('k', ':message'))}
            rows, bad = compare(key(a), key(b))
            cls, det = ('NAMED', ','.join([m] + rows)) if not bad else ('DIFF', 'exit %s/%s; %s' % (hs, gs, ','.join(bad)))
        else:
            cls, det = 'DIFF', 'exit %s/%s' % (hs, gs)
elif (ho, he) == (go, ge):
    cls, det = 'SAME', '-'
else:
    # stream by stream: equal texts, or both one answer/report map equal as data (or differing only by named rows)
    rows, bad = [], []
    for name, h, g in (('stdout', ho, go), ('stderr', he, ge)):
        if h == g:
            continue
        a, b = first_map(h), first_map(g)
        if a is None or b is None:
            bad.append('%s: no answer map (host %s, image %s)' % (name, a is not None, b is not None))
            continue
        r, x = compare(a, b)
        rows += r
        bad += x
    if bad:
        cls, det = 'DIFF', ','.join(bad) + ((' (named: ' + ','.join(rows) + ')') if rows else '')
    elif rows:
        cls, det = 'NAMED', ','.join(rows)
    else:
        cls, det = 'SAME-DATA', '-'
print('%s\t%s' % (cls, det))
