#!/usr/bin/env python3
"""JUN-59 session 71 derivation census -- INDEPENDENT second-parser
TWIN for the s69 W5 analysis pre-build's s51-compat validation
(the 44 rows of anv-b3w5prego-20261028/compat-s51-validation.txt,
whose want values were parsed from the committed publication-s51.txt
and whose got values were computed by analysis-prego.py's numpy
machinery).

Independence contract (the s63 census contract, unchanged):
- NO regex, NO re module: all run-log parsing is split()-based
  k=v tokenising; all publication/report parsing is find/split-based.
- NO numpy: every order statistic is a pure-Python sorted() index
  over the SAME pooled 75 (exact-median MAD block scale =
  sorted(|x - sorted(pooled75)[37]|)[37]; exclusive-hinge IQR block
  scale = sorted(pooled75)[56] - sorted(pooled75)[18]; 2*L =
  sorted(ds)[5] + sorted(ds)[6]).
- The resampling is an independent pure-Python shuffle loop that
  re-implements the frozen RNG call contract exactly (ONE
  random.Random(20261028); per probe 20,000 fresh-list
  rng.shuffle calls in the frozen probe order primary MAD /
  primary IQR / D MAD-hi / D MAD-tw / D IQR-hi / D IQR-tw;
  primaries shuffle list(range(72)) into two pseudo-windows of 36
  then 12 blocks of 3; the D probes shuffle list(range(144)) into
  four pseudo-windows of 36 then 12 blocks of 3; p = (1 + count) /
  (1 + 20000)).

This script re-derives, from the committed run logs of the four
prior windows only (NO W5 quantity exists here -- the W5 window
cannot open before 2026-10-29T00:00:00Z and nothing in this script
touches anv-b3w5xdayrep-20261029), every published integer, count,
p value and letter of the prego validation, in three-way rows:
published (publication-s51.txt, parsed find/split) vs prego report
(compat-s51-validation.txt got column) vs census (recomputed here).
It also re-derives the published D1 content that the prego's report
rows do NOT cover (named, not hidden: the prego's D1 regex is
single-line while publication-s51.txt's D1 text wraps across two
lines, so that loop matched 0 rows and the 44-row report contains
no D1 row), and checks evidence hygiene.

Deterministic: running it twice yields byte-identical output (RNG
seeded, no set iteration). Usage: derivation-census-s71.py
[OUTPUT-PATH] (default: derivation-census-s71.txt beside this
file). Env CENSUS_SMOKE=1 caps trials at 20 for plumbing checks
only -- its output is NEVER the committed census (the committed
double-run is env-free).
"""
import os, sys, random, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
GPU = os.path.join(ROOT, "docs", "evidence", "gpu")
PREGO = os.path.join(GPU, "anv-b3w5prego-20261028")
PUB = os.path.join(GPU, "anv-b3levelrep-20261028", "publication-s51.txt")
REPORT = os.path.join(PREGO, "compat-s51-validation.txt")

SMOKE = os.environ.get("CENSUS_SMOKE") == "1"
TRIALS = 20 if SMOKE else 20000
SEED = 20261028
COMMITTED_C8 = 32915
NAMED_CKEY = ("max", 128, "default")
NEW_WIN = "s51"
WINDOWS = [("s36", "anv-b3commonmode-20261028"),
           ("s38", "anv-b3joint3-20261028"),
           ("s39", "anv-b3joint4-20261028"),
           ("s51", "anv-b3levelrep-20261028")]
ARMS = {"c2": (2, 1, 1, [1, 2, 3]),
        "hi": (3, 1024, 4033, list(range(1, 37))),
        "tw": (3, 2048, 8066, list(range(1, 37))),
        "c8": (8, 1, 1, [1, 2, 3])}
REF_X = {"s39": [986, 991, 984, 985, 989, 989, 986, 990, 995, 986, 987, 981],
         "s36": [991, 989, 981, 998, 993, 985, 984, 997, 994, 994, 980, 982],
         "s38": [992, 988, 984, 1007, 985, 984, 986, 983, 992, 991, 982, 997],
         "s51": [988, 986, 1000, 986, 989, 983, 995, 983, 994, 991, 984, 985]}
REF_Y = {"s39": [988, 989, 987, 990, 990, 988, 991, 983, 985, 988, 983, 986],
         "s36": [988, 985, 994, 993, 994, 995, 992, 984, 987, 984, 993, 981],
         "s38": [988, 987, 980, 980, 991, 994, 991, 994, 988, 991, 1001, 992],
         "s51": [980, 975, 991, 979, 986, 986, 992, 991, 988, 993, 995, 996]}
REF_ANCHOR = {"s36": (1142, 991, 1438), "s38": (1132, 992, 1443),
              "s39": (1146, 986, 1432), "s51": (1137, 988, 1430)}
REF_NAMED = {"MAD": {"s36": 143, "s38": 111, "s39": 113, "s51": 118},
             "IQR": {"s36": 303, "s38": 241, "s39": 235, "s51": 240}}

# ------------------------------------------------------------------
# independent split-based run-log parser (no regex)
# ------------------------------------------------------------------
def kv(tokens):
    d = {}
    for t in tokens:
        if "=" in t:
            k, v = t.split("=", 1)
            d[k] = v
    return d

def load(path):
    cells, verifies, samples = {}, [], []
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("CELL "):
            d = kv(line.split())
            cells[int(d["idx"])] = dict(op=d["op"], wg=int(d["wg"]),
                                        forced=d["forced"],
                                        pipeline=d["pipeline"], void=d["void"])
        elif line.startswith("VERIFY "):
            d = kv(line.split())
            verifies.append((int(d["idx"]), int(d["checked"]), int(d["mismatch"])))
        elif line.startswith("SAMPLE "):
            d = kv(line.split())
            samples.append((int(d["round"]), int(d["idx"]), int(d["gpu_ticks"]),
                            (int(d["batch"]), int(d["work_mul"]), int(d["ndiv"]))))
    return cells, verifies, samples

data = {}
win_info = {}
ref_cellmap = None
for win, dirname in WINDOWS:
    src = os.path.join(GPU, dirname)
    vmis = 0
    counts_ok = knob_ok = fail_ok = cmap_ok = True
    nlogs = 0
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
    win_info[win] = (vmis, counts_ok, knob_ok, fail_ok, cmap_ok, nlogs)

ok_cells = sorted([k for k, v in data[("s36", "c2", 1)][0].items()
                   if v["pipeline"] == "ok"])
cell_pos = {k: i for i, k in enumerate(ok_cells)}

def ckey(idx):
    c = data[("s36", "c2", 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])

def ckey_str(idx):
    op, wg, s = ckey(idx)
    return "(%s,%d,S=%s)" % (op, wg, s)

sum128 = [k for k in ok_cells if ckey(k) == ("sum", 128, "16")][0]
nc = [k for k in ok_cells if ckey(k) == NAMED_CKEY][0]
nc_pos = cell_pos[nc]

def med(xs):
    return statistics.median(xs)

def fmt_ht(x2):
    return "%.1f" % (x2 / 2)

def pooled(win, tag, idx, runs):
    xs = []
    for r in runs:
        xs += [s[2] for s in data[(win, tag, r)][2] if s[1] == idx]
    return med(xs)

def block_vals(win, tag, runs):
    return [pooled(win, tag, k, runs) for k in ok_cells]

# independent pure-Python order statistics (no numpy)
def block_mad(vals75):
    s = sorted(vals75)
    m = s[37]
    return sorted(abs(x - m) for x in vals75)[37]

def block_iqr(vals75):
    s = sorted(vals75)
    return s[56] - s[18]

def l2_of(ds12):
    s = sorted(ds12)
    return s[5] + s[6]

def named_runs(win):
    out = []
    for r in range(1, 37):
        out.append([s[2] for s in data[(win, "tw", r)][2] if s[1] == nc])
    return out

def named_block_d(win, ax):
    ds = []
    for i in range(12):
        vals = []
        for r in range(3 * i + 1, 3 * i + 4):
            vals += [s[2] for s in data[(win, "tw", r)][2] if s[1] == nc]
        ds.append(block_mad(vals) if ax == "MAD" else block_iqr(vals))
    return ds

def named_l2(win, ax):
    return l2_of(named_block_d(win, ax))

# ------------------------------------------------------------------
# independent publication/report readers (find/split, no regex)
# ------------------------------------------------------------------
pub_lines = open(PUB).read().split("\n")
rep_lines = open(REPORT).read().split("\n")

def find_line(lines, prefix, occurrence=0):
    hits = [l for l in lines if l.startswith(prefix)]
    assert len(hits) > occurrence, (prefix, occurrence)
    return hits[occurrence]

# the prego report's got column, by label (find/split)
prego_got = {}
for l in rep_lines:
    if l.startswith("row ") and ": want [" in l:
        prefix, rest = l.split(": want [", 1)
        label = prefix.split(": ", 1)[1]
        got = rest.split("] got [")[1].split("] ->")[0]
        prego_got[label] = got

rows_a = []   # the prego report's 44 validation rows
rows_b = []   # published D1 content not covered by the report's rows

def rec(rows, label, pub, report, recomputed):
    rows.append((label, str(pub), str(report), str(recomputed)))

# ---- section 1: integrity ----
for win, _d in WINDOWS:
    l = find_line(pub_lines, "   %s: runs parsed " % win)
    parts = l.split("; ")
    want = "runs %s vmis %s counts %s knobs %s s8 %s cmap %s" % (
        parts[0].split("runs parsed ")[1],
        parts[1].split("total ")[1],
        parts[2].split(" ")[-1], parts[3].split(" ")[-1],
        parts[4].split(" ")[-1], parts[5].split(" ")[-1])
    vmis, cok, kok, fok, mok, nlogs = win_info[win]
    census = "runs %d vmis %d counts %s knobs %s s8 %s cmap %s" % (
        nlogs, vmis, str(cok), str(kok), str(fok), str(mok))
    rec(rows_a, "sec1 %s integrity" % win, want, prego_got["sec1 %s integrity" % win], census)

# ---- section 2: C1 ----
l = find_line(pub_lines, "   c2 class: ")
rec(rows_a, "sec2 c2 class", l.split("c2 class: ")[1].split(" ")[0],
    prego_got["sec2 c2 class"], None)  # census filled after computation
c2_cls_row = len(rows_a) - 1
l = find_line(pub_lines, "   c8 (sum,128,S=16) pooled median ")
rec(rows_a, "sec2 c8 pooled median", l.split("pooled median ")[1].split(" ")[0],
    prego_got["sec2 c8 pooled median"], None)
c8_row = len(rows_a) - 1

# ---- section 3: block-min vectors ----
vec = {}
vec_ok = True
for win, _d in WINDOWS:
    X = [int(min(block_vals(win, "hi", [3 * i + 1, 3 * i + 2, 3 * i + 3]))) for i in range(12)]
    Y = [int(min(block_vals(win, "tw", [3 * i + 1, 3 * i + 2, 3 * i + 3]))) for i in range(12)]
    vec[win] = (X, Y)
    rec(rows_a, "sec3 %s X (hi)" % win,
        find_line(pub_lines, "   %s X (hi): " % win).split(": ")[1],
        prego_got["sec3 %s X (hi)" % win], " ".join(str(v) for v in X))
    rec(rows_a, "sec3 %s Y (tw)" % win,
        find_line(pub_lines, "   %s Y (tw): " % win).split(": ")[1],
        prego_got["sec3 %s Y (tw)" % win], " ".join(str(v) for v in Y))
    if win != NEW_WIN and (X != REF_X[win] or Y != REF_Y[win]):
        vec_ok = False
rec(rows_a, "sec3 prior vector reproduction",
    find_line(pub_lines, "   all three prior windows reproduce EXACTLY: ").split(": ")[1],
    prego_got["sec3 prior vector reproduction"], str(vec_ok))

# ---- section 3b: anchor rows ----
anchor_rows = {}
anchor_ok = True
for win, _d in WINDOWS:
    a_med = pooled(win, "hi", sum128, [1, 2, 3])
    bvals = [int(v) for v in block_vals(win, "hi", [1, 2, 3])]
    a_min, a_max = min(bvals), max(bvals)
    anchor_rows[win] = (a_med, a_min, a_max)
    if win == NEW_WIN:
        l = find_line(pub_lines, "    %s (NEW): median " % win)
        want = "%s %s %s" % (l.split("median ")[1].split(" ")[0],
                             l.split("min..max ")[1].split(";")[0],
                             l.split("class ")[1])
        s_cls = ("FLOOR" if all(int(v) <= 100 for v in bvals) else
                 "CAPTURED" if all(int(v) >= 1000 for v in bvals) else
                 "INTERMEDIATE/MIXED")
        census = "%.0f %d..%d %s" % (a_med, a_min, a_max, s_cls)
        rec(rows_a, "sec3b %s anchor (fresh)" % win, want,
            prego_got["sec3b %s anchor (fresh)" % win], census)
    else:
        l = find_line(pub_lines, "    %s: median " % win)
        want = "%s %s" % (l.split("median ")[1].split(" ")[0],
                          l.split("min..max ")[1].split(" ")[0])
        census = "%.0f %d..%d" % (a_med, a_min, a_max)
        rec(rows_a, "sec3b %s anchor" % win, want,
            prego_got["sec3b %s anchor" % win], census)
        if (a_med, a_min, a_max) != REF_ANCHOR[win]:
            anchor_ok = False

# ---- C1 computation (section 2 census column) ----
c2_vals = block_vals(NEW_WIN, "c2", ARMS["c2"][3])
c2_cls = ("FLOOR" if all(v <= 100 for v in c2_vals) else
          "CAPTURED" if all(v >= 1000 for v in c2_vals) else "INTERMEDIATE/MIXED")
c8_m = pooled(NEW_WIN, "c8", sum128, ARMS["c8"][3])
c1_ok = (c2_cls == "FLOOR") and abs(c8_m - COMMITTED_C8) <= 0.05 * COMMITTED_C8
rows_a[c2_cls_row] = (rows_a[c2_cls_row][0], rows_a[c2_cls_row][1],
                      rows_a[c2_cls_row][2], c2_cls)
rows_a[c8_row] = (rows_a[c8_row][0], rows_a[c8_row][1],
                  rows_a[c8_row][2], "%.0f" % c8_m)

# ---- the named-cell level vectors (D1 content) ----
d1 = {}
for ax in ("MAD", "IQR"):
    for win, _d in WINDOWS:
        d1[(ax, win)] = named_l2(win, ax)

def invalidated():
    return any((v[0] != 0 or not v[1] or not v[2] or not v[3] or not v[4])
               for v in win_info.values()) or (not vec_ok) or (not c1_ok) or (not anchor_ok)

# ------------------------------------------------------------------
# the PRIMARY two-window directional contrast (frozen RNG contract)
# ------------------------------------------------------------------
named_flat = named_runs("s36") + named_runs(NEW_WIN)   # (72,25)

def primary(axis, rng):
    l2_s36 = l2_of([block_mad(named_flat[3 * i] + named_flat[3 * i + 1] +
                              named_flat[3 * i + 2]) if axis == "MAD"
                    else block_iqr(named_flat[3 * i] + named_flat[3 * i + 1] +
                                   named_flat[3 * i + 2]) for i in range(12)])
    l2_new = l2_of([block_mad(named_flat[36 + 3 * i] + named_flat[36 + 3 * i + 1] +
                              named_flat[36 + 3 * i + 2]) if axis == "MAD"
                    else block_iqr(named_flat[36 + 3 * i] + named_flat[36 + 3 * i + 1] +
                                   named_flat[36 + 3 * i + 2]) for i in range(12)])
    c_obs = l2_s36 - l2_new
    cnt = 0
    for _t in range(TRIALS):
        perm = list(range(72))
        rng.shuffle(perm)
        ds0, ds1 = [], []
        for i in range(12):
            p0 = named_flat[perm[3 * i]] + named_flat[perm[3 * i + 1]] + named_flat[perm[3 * i + 2]]
            ds0.append(block_mad(p0) if axis == "MAD" else block_iqr(p0))
        for i in range(12):
            p1 = (named_flat[perm[36 + 3 * i]] + named_flat[perm[36 + 3 * i + 1]] +
                  named_flat[perm[36 + 3 * i + 2]])
            ds1.append(block_mad(p1) if axis == "MAD" else block_iqr(p1))
        if l2_of(ds0) - l2_of(ds1) >= c_obs:
            cnt += 1
    return l2_s36, l2_new, c_obs, cnt, (1 + cnt) / (1 + TRIALS)

rng = random.Random(SEED)
prim = {}
prim["MAD"] = primary("MAD", rng)
prim["IQR"] = primary("IQR", rng)

# ---- section 4: T1 rows ----
for ax in ("MAD", "IQR"):
    l2a, l2b, c_obs, cnt, p = prim[ax]
    l = find_line(pub_lines, "   %s axis: 2*L_s36 = " % ax)
    want = "%s %s C %s count %s p %s" % (
        l.split("2*L_s36 = ")[1].split(" ")[0],
        l.split("2*L_s51 = ")[1].split(" ")[0],
        l.split("C_obs = ")[1].split(";")[0],
        l.split("count ")[1].split(" ")[0],
        l.split("p = ")[1].split(";")[0])
    census = "%d %d C %s count %d p %.6f" % (l2a, l2b, fmt_ht(c_obs), cnt, p)
    rec(rows_a, "sec4 T1 %s" % ax, want, prego_got["sec4 T1 %s" % ax], census)

def axis_letter(axis):
    _l2a, _l2b, c_obs, _cnt, p = prim[axis]
    if invalidated():
        return "(c) NOT EVALUABLE"
    if c_obs > 0 and p <= 0.05:
        return "(a) REPLICATED-CONTINUED"
    subcase = "DIRECTION-REVERSED" if c_obs <= 0 else "DIRECTION-CONSISTENT-NOT-SIGNIFICANT"
    return "(b) NOT-REPLICATED [%s]" % subcase

def joint_letter():
    if invalidated():
        return "(c) NOT EVALUABLE"
    if all(axis_letter(ax).startswith("(a)") for ax in ("MAD", "IQR")):
        return "(a) REPLICATED-ON-BOTH-LEVEL-AXES"
    return "(b) NOT-REPLICATED-ON-BOTH-AXES"

rec(rows_a, "sec4 T1 joint",
    find_line(pub_lines, "   T1 = ").split("T1 = ")[1],
    prego_got["sec4 T1 joint"], joint_letter())

# ------------------------------------------------------------------
# the D{n}-window cross-window max-T repartition probes (frozen RNG
# contract; per probe only the probe's own axis is evaluated)
# ------------------------------------------------------------------
def probe_dn(axis, tag, rng):
    nwin = len(WINDOWS)
    nruns = 36 * nwin
    arr = {}
    for wi, (win, _d) in enumerate(WINDOWS):
        for r in range(1, 37):
            tbl = {}
            for s in data[(win, tag, r)][2]:
                tbl.setdefault(s[1], []).append(s[2])
            row = {}
            for k in ok_cells:
                assert len(tbl[k]) == 25
                row[cell_pos[k]] = tbl[k]
            arr[wi * 36 + r - 1] = row
    def l2_win(runs3):
        out = []
        for ci in range(len(ok_cells)):
            ds = []
            for b in range(12):
                pool = []
                for j in range(3):
                    pool += arr[runs3[3 * b + j]][ci]
                ds.append(block_mad(pool) if axis == "MAD" else block_iqr(pool))
            out.append(l2_of(ds))
        return out
    l2_obs = [l2_win(list(range(wi * 36, wi * 36 + 36))) for wi in range(nwin)]
    s2_obs = [max(l2_obs[w][c] for w in range(nwin)) -
              min(l2_obs[w][c] for w in range(nwin)) for c in range(len(ok_cells))]
    m_obs = max(s2_obs)
    cnt = 0
    for _t in range(TRIALS):
        perm = list(range(nruns))
        rng.shuffle(perm)
        l2s = [l2_win(perm[wi * 36:wi * 36 + 36]) for wi in range(nwin)]
        s2 = [max(l2s[w][c] for w in range(nwin)) -
              min(l2s[w][c] for w in range(nwin)) for c in range(len(ok_cells))]
        if max(s2) >= m_obs:
            cnt += 1
    return s2_obs, m_obs, cnt, (1 + cnt) / (1 + TRIALS)

# frozen RNG order: (1) primary MAD (2) primary IQR (3) D MAD-hi
# (4) D MAD-tw (5) D IQR-hi (6) D IQR-tw -- primaries drawn above.
d = {}
for axis in ("MAD", "IQR"):
    for tag in ("hi", "tw"):
        d[(axis, tag)] = probe_dn(axis, tag, rng)

# ---- section 6 D2: the 18-cell tw-arm level table (no RNG) ----
d_tbl = {}
for ax in ("MAD", "IQR"):
    for win, _d in WINDOWS:
        rows12 = []
        for i in range(12):
            per = [[] for _ in ok_cells]
            for r in range(3 * i + 1, 3 * i + 4):
                for s in data[(win, "tw", r)][2]:
                    per[cell_pos[s[1]]].append(s[2])
            rows12.append([block_mad(per[ci]) if ax == "MAD" else block_iqr(per[ci])
                           for ci in range(len(ok_cells))])
        d_tbl[(ax, win)] = [l2_of([rows12[b][ci] for b in range(12)])
                            for ci in range(len(ok_cells))]

for k in ok_cells:
    ci = cell_pos[k]
    l = find_line(pub_lines, "      tw cell %s: " % ckey_str(k))
    rest = l.split(": ")[1]
    mpart, ipart = rest.split("; ")
    mt = mpart.split()
    it = ipart.split()
    want = "%s %s %s %s %s %s %s %s" % (mt[0], mt[2], mt[3], mt[4],
                                        it[0], it[2], it[3], it[4])
    l36m, l51m = d_tbl[("MAD", "s36")][ci], d_tbl[("MAD", NEW_WIN)][ci]
    l36i, l51i = d_tbl[("IQR", "s36")][ci], d_tbl[("IQR", NEW_WIN)][ci]
    census = "MAD %d/%d C %s IQR %d/%d C %s" % (
        l36m, l51m, fmt_ht(l36m - l51m), l36i, l51i, fmt_ht(l36i - l51i))
    rec(rows_a, "sec6 D2 %s" % ckey_str(k), want,
        prego_got["sec6 D2 %s" % ckey_str(k)], census)

# ---- section 6 D3: the four repartition probes ----
for axis in ("MAD", "IQR"):
    for tag in ("hi", "tw"):
        s2, m_obs, cnt, p = d[(axis, tag)]
        l = find_line(pub_lines, "      %s-%s: M_obs = " % (axis, tag))
        want = "M_obs %s cells %s count %s p %s" % (
            l.split("M_obs = ")[1].split(" ")[0],
            l.split("(max cell(s) ")[1].split("); count")[0],
            l.split("count ")[1].split(" ")[0],
            l.split("p = ")[1])
        idxs = [ok_cells[i] for i in range(len(ok_cells)) if s2[i] == m_obs]
        mcs = ", ".join(ckey_str(i) for i in idxs)
        census = "M_obs %s cells %s count %d p %.6f" % (fmt_ht(m_obs), mcs, cnt, p)
        rec(rows_a, "sec6 D3 %s-%s" % (axis, tag), want,
            prego_got["sec6 D3 %s-%s" % (axis, tag)], census)

# ------------------------------------------------------------------
# section B: published D1 content (the prego report has NO D1 row)
# ------------------------------------------------------------------
for ax in ("MAD", "IQR"):
    idx = [i for i, ll in enumerate(pub_lines)
           if ll.startswith("      %s: 2*L s36/s38/s39/s51 = " % ax)][0]
    l = pub_lines[idx]
    nxt = pub_lines[idx + 1]
    want = "%s repro %s inpair %s" % (
        l.split(" = ")[1].split(" ")[0],
        nxt.split("EXACT: ")[1].split(";")[0].strip(),
        nxt.split("pair interval: ")[1].strip())
    vals = "/".join(str(d1[(ax, w)]) for w, _d in WINDOWS)
    repro = all(d1[(ax, w)] == REF_NAMED[ax][w] for w, _d in WINDOWS if w != NEW_WIN)
    lo = min(d1[(ax, "s38")], d1[(ax, "s39")])
    hi = max(d1[(ax, "s38")], d1[(ax, "s39")])
    inpair = lo <= d1[(ax, NEW_WIN)] <= hi
    census = "%s repro %s inpair %s" % (vals, repro, inpair)
    rec(rows_b, "sec6 D1 %s" % ax, want, "(no prego row)", census)

# ------------------------------------------------------------------
# hygiene
# ------------------------------------------------------------------
hygiene = []
def hy(label, want, got):
    hygiene.append((label, str(want), str(got), str(want) == str(got)))

sh_found = []
for dirpath, _dirs, files in os.walk(GPU):
    for f in files:
        if f.endswith(".sh"):
            sh_found.append(f)
hy("evidence .sh count", 0, len(sh_found))
ledger_lines = open(os.path.join(GPU, "settle-bar-ledger.txt")).read().splitlines()
reading_lines = [l for l in ledger_lines if l.startswith("day=")]
hy("ledger reading-line count", 8, len(reading_lines))
hy("ledger has no s71 line", False,
   any("session=s71" in l for l in reading_lines))
hy("prego report TOTAL line", "TOTAL: 44 rows, 0 failed",
   [l for l in rep_lines if l.startswith("TOTAL: ")][0])

# ------------------------------------------------------------------
# report
# ------------------------------------------------------------------
out = []
P = out.append
P("JUN-59 session 71 derivation census -- INDEPENDENT second-parser")
P("TWIN for the s69 W5 analysis pre-build's s51-compat validation")
P("(the 44 rows of anv-b3w5prego-20261028/compat-s51-validation.txt;")
P("three-way rows: published = publication-s51.txt parsed")
P("find/split, prego = the report's got column, census =")
P("recomputed here from the committed run logs; split-based")
P("parsing, no re module, no numpy; pure-Python sorted() order")
P("statistics from ONE shared sort per pooled 75 (MAD =")
P("sorted(|x - sorted(pooled75)[37]|)[37]; IQR =")
P("sorted(pooled75)[56] - sorted(pooled75)[18]); independent")
P("pure-Python shuffle loop re-implementing the frozen RNG")
P("contract random.Random(20261028) consumed in the frozen probe")
P("order primary MAD / primary IQR / D MAD-hi / D MAD-tw /")
P("D IQR-hi / D IQR-tw, %d trials per probe, one fresh-list" % TRIALS)
P("rng.shuffle per trial). Four prior windows only -- NO W5")
P("quantity is computed anywhere in this script.")
P("")
if SMOKE:
    P("!!! CENSUS_SMOKE PLUMBING RUN (TRIALS=20) -- NOT the committed")
    P("!!! census; the RNG rows' counts/p are expected to mismatch.")
    P("")
mismatched = 0
for i, (label, pub, report, census) in enumerate(rows_a):
    match = pub == report == census
    if not match:
        mismatched += 1
    P("row %02d: %s: published [%s] | prego [%s] | census [%s] | match %s"
      % (i + 1, label, pub, report, census, match))
P("")
P("TOTAL: %d rows, %d mismatched" % (len(rows_a), mismatched))
P("")
P("SECTION B -- published D1 content NOT covered by the prego")
P("report's rows (NAMED, NOT HIDDEN: the prego's D1 regex is")
P("single-line while publication-s51.txt's D1 text wraps across")
P("two lines, so that loop matched 0 rows and the 44-row report")
P("contains no D1 row; the D1 level vectors and the")
P("pair-interval flag are re-derived here against the published")
P("text -- the published flag uses the CLOSED INTERVAL SPANNED BY")
P("{L_s38, L_s39}, whose endpoints exclude L_s51):")
mismatched_b = 0
for label, pub, report, census in rows_b:
    match = pub == census
    if not match:
        mismatched_b += 1
    P("%s: published [%s] | prego [%s] | census [%s] | match %s"
      % (label, pub, report, census, match))
P("")
P("TOTAL: %d rows, %d mismatched" % (len(rows_b), mismatched_b))
P("")
P("SECTION C -- evidence hygiene:")
mismatched_c = 0
for label, want, got, match in hygiene:
    if not match:
        mismatched_c += 1
    P("%s: want [%s] got [%s] | match %s" % (label, want, got, match))
P("")
P("TOTAL: %d checks, %d mismatched" % (len(hygiene), mismatched_c))
P("")
P("DETERMINISM: this generator run twice yields byte-identical")
P("output (double-run status named in the s71 record; RNG seeded,")
P("no set iteration).")

outpath = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "derivation-census-s71.txt")
open(outpath, "w").write("\n".join(out) + "\n")
print("TOTAL: %d rows, %d mismatched" % (len(rows_a), mismatched))
sys.exit(0 if (mismatched + mismatched_b + mismatched_c) == 0 else 1)
