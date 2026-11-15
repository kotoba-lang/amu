#!/usr/bin/env python3
"""JUN-59 session 90 -- the W6 READING PRE-BUILD's INDEPENDENT second
parser (derivation-census-prego.py; the census twin of
reading-prego.py, named by the s80 protocol section 6 implementation
paths -- "derivation-census-s<NN>.py is the independent second parser").
Pre-built here under the pre-name so the W6 session adopts both files.

Independence contract (frozen at session 90):
- NO regex, NO re module.  Run-log parsing is split()-based k=v
  tokenising; publication parsing is find/split-based
  (reading-prego.py parses with re.compile regexes).
- The pooled-median estimators are computed on the numpy np.partition
  kth paths (reading-prego.py is pure stdlib -- statistics.median --
  and imports NO numpy at all), CROSS-CHECKED IN-LOOP against pure-
  Python sorted() explicit order statistics (the algorithm family
  reading-prego.py used); every pooled median and every block min/max
  is computed BOTH ways (the cross-check census is section B).
- NO RNG anywhere, no clock.

This script re-derives, from the 390 committed run logs of the five
fixed evidence directories (no in-memory state of reading-prego.py is
consulted), the same 14 two-way rows reading-prego.py validates
against the committed publication-s73.txt bytes (want parsed
find/split from the committed bytes, never transcribed; got recomputed
here).  Deterministic: running it twice yields byte-identical output.
Usage: derivation-census-prego.py [OUTPUT-PATH] (default:
derivation-census-prego.txt beside this file).

NAMED, NOT HIDDEN: this census validates the pre-build machinery on
the five COMMITTED windows only.  NO W6 quantity exists or is computed
here (the W6 run logs do not exist); the W6-dependent parts of the
reading stay UNVALIDATED until the W6 session runs.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
GPU = os.path.join(ROOT, "docs", "evidence", "gpu")
PUB = os.path.join(GPU, "anv-b3w5xdayrep-20261029", "publication-s73.txt")

WIN5 = [("s36", "anv-b3commonmode-20261028"),
        ("s38", "anv-b3joint3-20261028"),
        ("s39", "anv-b3joint4-20261028"),
        ("s51", "anv-b3levelrep-20261028"),
        ("s73", "anv-b3w5xdayrep-20261029")]
NEW_WIN = "s73"

ARMS = {"c2": (2, 1, 1, [1, 2, 3]),
        "hi": (3, 1024, 4033, list(range(1, 37))),
        "tw": (3, 2048, 8066, list(range(1, 37))),
        "c8": (8, 1, 1, [1, 2, 3])}
COMMITTED_C8 = 32915
CELLKEY_SUM128 = ("sum", 128, "16")

# split()-based run-log parsing (k=v tokenising; NO regex)
def load(path):
    cells, verifies, samples = {}, [], []
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("CELL "):
            kv = {}
            for tok in line.split()[1:]:
                k, _, v = tok.partition("=")
                kv[k] = v
            cells[int(kv["idx"])] = dict(op=kv["op"], wg=int(kv["wg"]),
                                         forced=kv["forced"], pipeline=kv["pipeline"],
                                         void=kv["void"])
        elif line.startswith("VERIFY "):
            kv = {}
            for tok in line.split()[1:]:
                k, _, v = tok.partition("=")
                kv[k] = v
            verifies.append((int(kv["idx"]), int(kv["checked"]), int(kv["mismatch"])))
        elif line.startswith("SAMPLE "):
            kv = {}
            for tok in line.split()[1:]:
                k, _, v = tok.partition("=")
                kv[k] = v
            samples.append((int(kv["round"]), int(kv["idx"]), int(kv["gpu_ticks"]),
                            (int(kv["batch"]), int(kv["work_mul"]), int(kv["ndiv"]))))
    return cells, verifies, samples


# ------------------------------------------------------------------
# dual-path estimators: np.partition kth vs pure-Python sorted()
# (in-loop cross-check; every pooled median and every min/max is
# computed BOTH ways)
# ------------------------------------------------------------------
XCHECKS = [0, 0]   # [comparisons, mismatches]


def cmedian(xs):
    """Exact pooled median of an odd-length int list (the 38th of 75)."""
    a = np.asarray(xs, dtype=np.int64)
    k = len(xs) // 2
    fast = int(np.partition(a, k)[k])
    slow = sorted(xs)[k]
    XCHECKS[0] += 1
    if fast != slow:
        XCHECKS[1] += 1
    return slow


def cminmax(xs):
    a = np.asarray(xs, dtype=np.int64)
    fmin = int(np.partition(a, 0)[0])
    fmax = int(np.partition(a, len(xs) - 1)[len(xs) - 1])
    smin, smax = min(xs), max(xs)
    XCHECKS[0] += 2
    if fmin != smin:
        XCHECKS[1] += 1
    if fmax != smax:
        XCHECKS[1] += 1
    return smin, smax


# ------------------------------------------------------------------
# parse the windows (integrity, independently re-derived)
# ------------------------------------------------------------------
data = {}
win_info = {}
for win, dirname in WIN5:
    src = os.path.join(GPU, dirname)
    vmis = 0
    counts_ok = knob_ok = fail_ok = cmap_ok = True
    nlogs = 0
    ref_cellmap = None
    for tag in ("c2", "hi", "tw", "c8"):
        b, wm, dd, runs = ARMS[tag]
        for r in runs:
            fn = os.path.join(src, "run-%s-r%d.txt" % (tag, r))
            cells, verifies, samples = load(fn)
            data[(win, tag, r)] = (cells, verifies, samples)
            nlogs += 1
            for (_i, _c, mis) in verifies:
                vmis += mis
            okc = [k for k, v in cells.items() if v["pipeline"] == "ok"]
            s8 = [k for k, v in cells.items() if v["forced"] == "8"]
            if len(s8) != 6 or any(cells[k]["pipeline"] != "FAIL" or cells[k]["void"] != "1"
                                   for k in s8):
                fail_ok = False
            if len(samples) != len(okc) * 25 or len(verifies) != 24:
                counts_ok = False
            for (_rnd, _idx, _gt, knobs) in samples:
                if knobs != (b, wm, dd):
                    knob_ok = False
            cmap = tuple(sorted((k, v["op"], v["wg"], v["forced"], v["pipeline"], v["void"])
                                for k, v in cells.items()))
            if ref_cellmap is None:
                ref_cellmap = cmap
            elif cmap != ref_cellmap:
                cmap_ok = False
    win_info[win] = dict(vmis=vmis, counts_ok=counts_ok, knob_ok=knob_ok,
                         fail_ok=fail_ok, cmap_ok=cmap_ok, nlogs=nlogs)

ok_cells = sorted([k for k, v in data[("s36", "c2", 1)][0].items()
                   if v["pipeline"] == "ok"])


def ckey(idx):
    c = data[("s36", "c2", 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])


sum128 = [k for k in ok_cells if ckey(k) == CELLKEY_SUM128][0]


def pooled(win, tag, idx, runs):
    xs = []
    for r in runs:
        xs += [s[2] for s in data[(win, tag, r)][2] if s[1] == idx]
    assert len(xs) == 25 * len(runs)
    return cmedian(xs)


def block_vals(win, tag, runs):
    return [pooled(win, tag, k, runs) for k in ok_cells]


def bar_class(bvals):
    if all(v <= 100 for v in bvals):
        return "FLOOR"
    if all(v >= 1000 for v in bvals):
        return "CAPTURED"
    return "INTERMEDIATE/MIXED"


anchor_rows = {}
for win, _d in WIN5:
    a_med = pooled(win, "hi", sum128, [1, 2, 3])
    bvals = block_vals(win, "hi", [1, 2, 3])
    a_min, a_max = cminmax(bvals)
    anchor_rows[win] = (a_med, a_min, a_max, bar_class(bvals))

c2_vals = block_vals(NEW_WIN, "c2", ARMS["c2"][3])
c2_cls = bar_class(c2_vals)
c8_m = pooled(NEW_WIN, "c8", sum128, ARMS["c8"][3])
c1_ok = (c2_cls == "FLOOR") and abs(c8_m - COMMITTED_C8) <= 0.05 * COMMITTED_C8


def integrity_row(win):
    info = win_info[win]
    return ("runs %d vmis %d counts %s knobs %s s8 %s cmap %s" %
            (info["nlogs"], info["vmis"], info["counts_ok"], info["knob_ok"],
             info["fail_ok"], info["cmap_ok"]))


# ------------------------------------------------------------------
# find/split publication parsing (NO regex)
# ------------------------------------------------------------------
pub = open(PUB).read()
lines = pub.splitlines()
rows = []


def row(label, want, got):
    rows.append((label, want, got, want == got))


def after(text, token, start=0):
    i = text.find(token, start)
    assert i >= 0, token
    return i + len(token)


def parse_anchor_tail(tail):
    """'median M min..max A..B' -> ('M', 'A', 'B'); leading text stripped."""
    i = after(tail, "median ")
    j = tail.find(" ", i)
    med = tail[i:j]
    k = after(tail, "min..max ", j)
    l = tail.find(".", k)
    a = tail[k:l]
    m2 = l + 2
    n = len(tail)
    while m2 < n and tail[m2].isdigit():
        m2 += 1
    b = tail[l + 2:m2]
    return med, a, b


# 1. sec1 integrity rows (5)
for line in lines:
    s = line.strip()
    if ": runs parsed " in s:
        win = s.split(":")[0]
        segs = [t.strip() for t in s.split(":", 1)[1].split(";")]
        kv = {}
        for seg in segs:
            key, _, val = seg.rpartition(" ")
            kv[key] = val
        want = "runs %s vmis %s counts %s knobs %s s8 %s cmap %s" % (
            kv["runs parsed"], kv["VERIFY mismatch total"], kv["counts ok"],
            kv["knobs ok"], kv["S=8 fail-closed"], kv["cell map ok"])
        row("sec1 %s integrity" % win, want, integrity_row(win))

# 2. sec2 C1 rows (3)
i = after(pub, "c2 class: ")
row("sec2 c2 class", pub[i:pub.find(" (", i)], c2_cls)
i = after(pub, "c8 (sum,128,S=16) pooled median ")
row("sec2 c8 pooled median", pub[i:pub.find(" ", i)], "%d" % c8_m)
i = after(pub, "C1 branch: ")
row("sec2 C1 branch", pub[i:pub.find("\n", i)].strip(),
    "(a) both controls replicate" if c1_ok else "(b) discrepancy")

# 3. sec3b anchor rows (4 prior + 1 fresh)
pos = 0
for line in lines:
    s = line.strip()
    if s.startswith("s") and ": median " in s and "(want" in s:
        win = s.split(":")[0]
        med, a, b = parse_anchor_tail(s.split(":", 1)[1].split(" (want")[0])
        aw = anchor_rows[win]
        row("sec3b %s anchor" % win, "%s %s..%s" % (med, a, b),
            "%d %d..%d" % (aw[0], aw[1], aw[2]))
i = after(pub, "s73 (NEW): median ")
tail = pub[i - len("median "):]
med, a, b = parse_anchor_tail(tail)
pos_new = pub.find("s73 (NEW):")
j = after(pub, "; class ", pos_new)
cls = pub[j:pub.find("\n", j)]
aw = anchor_rows["s73"]
row("sec3b s73 anchor (fresh)", "%s %s..%s %s" % (med, a, b, cls),
    "%d %d..%d %s" % (aw[0], aw[1], aw[2], aw[3]))

# 4. sec6-D4 bar row (1)
i = after(pub, "D4 the W5 anchor reading")
i = after(pub, "median ", i)
tail = pub[i - len("median "):]
med, a, b = parse_anchor_tail(tail)
j = after(tail, "class ")
cls = tail[j:tail.find(" vs the bar", j)]
row("sec6-D4 s73 bar reading", "%s %s..%s %s" % (med, a, b, cls),
    "%d %d..%d %s" % (aw[0], aw[1], aw[2], aw[3]))

# ------------------------------------------------------------------
out = []
out.append("JUN-59 session 90 -- W6 READING PRE-BUILD derivation census")
out.append("(derivation-census-prego.py, the INDEPENDENT second parser for")
out.append("reading-prego.py's --compat validation; s80 protocol section 6")
out.append("implementation paths, pre-built under the pre-name). NO W6")
out.append("quantity exists or is computed here.")
out.append("")
out.append("Independence contract: NO re module (split()-based k=v run-log")
out.append("parsing, find/split publication parsing -- reading-prego.py")
out.append("parsed with re.compile regexes); the pooled-median and")
out.append("min/max estimators are computed on the numpy np.partition kth")
out.append("paths (reading-prego.py is pure stdlib statistics.median/min/max")
out.append("and imports NO numpy at all), CROSS-CHECKED IN-LOOP against")
out.append("pure-Python sorted() explicit order statistics. NO RNG, no")
out.append("clock.")
out.append("")
out.append("A. TWO-WAY ROWS (want = find/split-parsed from the committed")
out.append("   publication-s73.txt bytes; got = recomputed here from the 390")
out.append("   committed run logs):")
nfail = 0
for (label, want, got, ok) in rows:
    out.append("%-28s want: %-42s got: %-42s %s" %
               (label, want, got, "EXACT" if ok else "MISMATCH"))
    if not ok:
        nfail += 1
out.append("")
out.append("   TOTAL: %d rows, %d mismatched" % (len(rows), nfail))
out.append("")
out.append("B. IN-LOOP DUAL-COMPUTATION CROSS-CHECK (np.partition kth path")
out.append("   vs pure-Python sorted() explicit order statistics):")
out.append("   pooled-median + min/max dual computations: %d comparisons,"
           % XCHECKS[0])
out.append("   %d mismatched" % XCHECKS[1])
out.append("")
out.append("C. HYGIENE: evidence .sh count below is checked by the standing")
out.append("   gate set (find docs/evidence/gpu -name '*.sh' -> 0); this")
out.append("   census writes NO run logs, NO ledger line.")
text = "\n".join(out) + "\n"

if len(sys.argv) > 1:
    with open(sys.argv[1], "w") as f:
        f.write(text)
else:
    default_out = os.path.join(HERE, "derivation-census-prego.txt")
    with open(default_out, "w") as f:
        f.write(text)
    sys.stdout.write(text)

sys.exit(0 if (nfail == 0 and XCHECKS[1] == 0) else 1)
