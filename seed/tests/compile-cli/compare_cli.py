# compare_cli.py <host-stdout> <guest-stdout> <host-out-dir> <guest-out-dir> <host.kexe> <guest.kexe>
# The two answers of `compile` compared as data (the host prints its answer map in hash order): each side's output
# directory is replaced by one placeholder first, since the two sides write to different directories. Then the two
# .publication.edn markers: format, roles, names and sizes must be equal, and each marker must describe ITS OWN files
# (sha256 and size of the bytes written, and the marker digest = sha256 of the printed payload); the sha256 values
# themselves differ whenever the texts do (the host prints large maps in hash order; the guest in entry order).
# Prints "<stdout> <stdout-keys> <publication>": stdout SAME or DIFF (keys: the differing top-level keys, "-" when
# none); publication SAME-SHAPE (format/roles/names/sizes equal, both self-consistent), SIZE-DIFF (shape equal but a
# size differs, both self-consistent), or BAD-HOST / BAD-GUEST (a marker does not describe its files) / MISSING.
import hashlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'compile-twin'))
from compare_artifact import parse, top  # noqa: E402


def answer(path, out_dir):
    text = open(path).read().strip()
    return top(parse(text.replace(out_dir.rstrip('/') + '/', '<OUT>/')))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def marker(kexe):
    path = kexe + '.publication.edn'
    text = open(path).read()
    m = top(parse(text))
    files = [dict(f[1]) for f in m[('k', ':files')][1]]
    # self-consistency: each file's sha256 / size, and the digest over the payload text the marker was printed from
    ok = True
    for f in files:
        name = f[('k', ':name')][1]
        data = open(os.path.join(os.path.dirname(kexe), name), 'rb').read()
        ok = ok and f[('k', ':sha256')][1] == sha(data) and f[('k', ':size')][1] == len(data)
    cut = text.rfind(', :sha256 "')
    payload = text[:cut] + '}'
    ok = ok and m[('k', ':sha256')][1] == sha(payload.encode())
    shape = (m[('k', ':format')], tuple((f[('k', ':role')], f[('k', ':name')]) for f in files))
    sizes = tuple(f[('k', ':size')] for f in files)
    return ok, shape, sizes


if __name__ == '__main__':
    hs, gs, hd, gd, hk, gk = sys.argv[1:7]
    h, g = answer(hs, hd), answer(gs, gd)
    keys = sorted(k[1] for k in set(h) | set(g) if h.get(k, 'absent') != g.get(k, 'absent'))
    out = 'SAME' if not keys else 'DIFF'
    try:
        hok, hshape, hsizes = marker(hk)
        gok, gshape, gsizes = marker(gk)
        if not hok:
            pub = 'BAD-HOST'
        elif not gok:
            pub = 'BAD-GUEST'
        elif hshape != gshape:
            pub = 'SHAPE-DIFF'
        else:
            pub = 'SAME-SHAPE' if hsizes == gsizes else 'SIZE-DIFF'
    except FileNotFoundError:
        pub = 'MISSING'
    print(out, ','.join(keys) or '-', pub)
