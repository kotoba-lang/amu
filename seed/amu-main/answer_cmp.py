# answer_cmp.py <host-out> <image-out> <host-err> <image-err> <host-case-dir>
# usage-parity.sh's `H:` cases (2026-10-10): the image's product compile/check against bin/amu (the host route of the
# same code). The answer maps on stdout are compared as EDN data (the host prints large maps in hash order, the image in
# entry order), after the host's absolute case directory is removed (bin/amu makes caller paths absolute; the image has
# no cwd wire and prints the path it was given). The refusal reports on stderr are compared by :error phase and
# :message (the image's report is cli-support's reduced one: no :diagnostic / :details). Prints
# "<stdout> <keys> <stderr>": stdout SAME/DIFF (keys = the differing top-level keys, "-"), stderr SAME/DIFF/-.
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests', 'compile-twin'))
from compare_artifact import parse, top  # noqa: E402


def load(path, cut=None):
    text = open(path, errors='replace').read().strip()
    if cut:
        text = text.replace(cut.rstrip('/') + '/', '')
    return text


def keys_of(h, g):
    if not h and not g:
        return 'SAME', '-'
    try:
        a, b = top(parse(h)), top(parse(g))
    except Exception:
        return ('SAME', '-') if h == g else ('DIFF', 'unparsed')
    ks = sorted(k[1] for k in set(a) | set(b) if a.get(k, 'absent') != b.get(k, 'absent'))
    return ('SAME' if not ks else 'DIFF'), (','.join(ks) or '-')


def report(text):
    try:
        m = top(parse(text))
        return m.get(('k', ':error')), m.get(('k', ':message'))
    except Exception:
        return text


ho, io, he, ie, d = sys.argv[1:6]
o, ks = keys_of(load(ho, d), load(io))
h_err, i_err = load(he, d), load(ie)
e = '-' if not h_err and not i_err else ('SAME' if report(h_err) == report(i_err) else 'DIFF')
print(o, ks, e)
