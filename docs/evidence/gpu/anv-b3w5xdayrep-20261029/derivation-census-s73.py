#!/usr/bin/env python3
"""JUN-59 session 76 -- the five-window derivation census
(derivation-census-s73.py, the INDEPENDENT second parser for
publication-s73.txt; the s73 carry-forward's named 3(b) / record-s75.txt
section 5(a); protocol.txt section 0 "IMPLEMENTATION PATHS", frozen at
the s57 pre-registration).

Independence contract (frozen):
- NO regex, NO re module. Run-log parsing is split()-based k=v
  tokenising; publication parsing is find/split-based.
- The OBSERVED block estimators are pure-Python sorted() order
  statistics over the explicitly pooled 75 (MAD = sorted(|x -
  sorted(pooled75)[37]|)[37]; IQR = sorted(pooled75)[56] -
  sorted(pooled75)[18]), CROSS-CHECKED IN-LOOP against the
  np.partition kth paths (every observed block D and every observed
  12-value level median is computed BOTH ways; the cross-check
  census is section B).
- The RESAMPLING's estimators use the np.partition kth paths, NOT a
  sort (analysis-s73.py used np.sort -- a genuinely different
  computational path); the resampling's 12-value level medians use
  np.partition kth=(5,6).
- The repartition resampling and the RNG call order are
  re-implemented here: ONE random.Random(20261029) consumed in the
  frozen probe order primary MAD / primary IQR / D MAD-hi / D MAD-tw
  / D IQR-hi / D IQR-tw; per trial ONE rng.shuffle of a fresh list
  (list(range(72)) for the primaries, list(range(180)) for the
  five-window D probes); 20,000 trials per probe; p = (1 + count) /
  (1 + 20000).

This script re-derives, from the 390 committed run logs of the five
fixed evidence directories (no in-memory state of analysis-s73.py is
consulted), every published integer, count, p value and letter of
publication-s73.txt, in two-way rows: published (parsed find/split
from the committed publication-s73.txt bytes) vs census (recomputed
here). It resolves record-s75.txt section 5(a): the s73 T7 values are
no longer two runs of ONE validated generator alone -- they are
cross-checked by an independent parser.

Deterministic: running it twice yields byte-identical output (RNG
seeded, no set iteration). Usage: derivation-census-s73.py
[OUTPUT-PATH] (default: derivation-census-s73.txt beside this
file). Env CENSUS_SMOKE=1 caps trials at 20 for plumbing checks
only -- its output is NEVER the committed census (the committed
double-run is env-free; smoke runs mismatch the six RNG count/p rows
by construction).
"""
import os, sys, random, statistics
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
GPU = os.path.join(ROOT, "docs", "evidence", "gpu")
PUB = os.path.join(HERE, "publication-s73.txt")

SMOKE = os.environ.get("CENSUS_SMOKE") == "1"
TRIALS = 20 if SMOKE else 20000
BATCH = 25
SEED = 20261029
COMMITTED_C8 = 32915
NAMED_CKEY = ("max", 128, "default")
NEW_WIN = "s73"
WINDOWS = [("s36", "anv-b3commonmode-20261028"),
           ("s38", "anv-b3joint3-20261028"),
           ("s39", "anv-b3joint4-20261028"),
           ("s51", "anv-b3levelrep-20261028"),
           ("s73", "anv-b3w5xdayrep-20261029")]
ARMS = {"c2": (2, 1, 1, [1, 2, 3]),
        "hi": (3, 1024, 4033, list(range(1, 37))),
        "tw": (3, 2048, 8066, list(range(1, 37))),
        "c8": (8, 1, 1, [1, 2, 3])}
# frozen reference vectors / anchors / named-cell priors (the
# published/quote-only priors the publication itself checks against)
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

run_tbl = {}
def tbl_of(win, tag, r):
    key = (win, tag, r)
    if key not in run_tbl:
        t = {}
        for s in data[key][2]:
            t.setdefault(s[1], []).append(s[2])
        run_tbl[key] = t
    return run_tbl[key]

def med(xs):
    return statistics.median(xs)

def fmt_ht(x2):
    return "%.1f" % (x2 / 2)

def pooled(win, tag, idx, runs):
    xs = []
    for r in runs:
        xs += tbl_of(win, tag, r)[idx]
    return med(xs)

def block_vals(win, tag, runs):
    return [pooled(win, tag, k, runs) for k in ok_cells]

# ------------------------------------------------------------------
# observed estimators: pure-Python sorted() FIRST, cross-checked
# in-loop against the np.partition kth paths (section B census)
# ------------------------------------------------------------------
XC_BLK = [0, 0]   # [comparisons, mismatches]
XC_L2 = [0, 0]

def block_d_checked(vals75):
    s = sorted(vals75)
    m = s[37]
    mad_py = sorted(abs(x - m) for x in vals75)[37]
    iqr_py = s[56] - s[18]
    a = np.asarray(vals75, dtype=np.int64)
    part = np.partition(a, (18, 37, 56))
    med_np = int(part[37])
    mad_np = int(np.partition(np.abs(a - med_np), 37)[37])
    iqr_np = int(part[56]) - int(part[18])
    XC_BLK[0] += 2
    if mad_py != mad_np:
        XC_BLK[1] += 1
    if iqr_py != iqr_np:
        XC_BLK[1] += 1
    return mad_py, iqr_py

def l2_checked(ds12):
    s = sorted(ds12)
    py = s[5] + s[6]
    p = np.partition(np.asarray(ds12, dtype=np.int64), (5, 6))
    npx = int(p[5]) + int(p[6])
    XC_L2[0] += 1
    if py != npx:
        XC_L2[1] += 1
    return py

# the full observed block-D table (every window x arm x ok cell x block)
blk = {}
for win, _d in WINDOWS:
    for tag in ("hi", "tw"):
        for ci in range(len(ok_cells)):
            idx = ok_cells[ci]
            for b in range(12):
                vals = []
                for r in (3 * b + 1, 3 * b + 2, 3 * b + 3):
                    vals += tbl_of(win, tag, r)[idx]
                blk[(win, tag, ci, b)] = block_d_checked(vals)

def named_l2(win, ax):
    j = 0 if ax == "MAD" else 1
    return l2_checked([blk[(win, "tw", nc_pos, b)][j] for b in range(12)])

# ------------------------------------------------------------------
# C1, block-min vectors, anchor rows (pure-Python pooled medians)
# ------------------------------------------------------------------
c2_vals = block_vals(NEW_WIN, "c2", ARMS["c2"][3])
c2_cls = ("FLOOR" if all(v <= 100 for v in c2_vals) else
          "CAPTURED" if all(v >= 1000 for v in c2_vals) else "INTERMEDIATE/MIXED")
c8_m = pooled(NEW_WIN, "c8", sum128, ARMS["c8"][3])
c1_ok = (c2_cls == "FLOOR") and abs(c8_m - COMMITTED_C8) <= 0.05 * COMMITTED_C8

vec = {}
vec_ok = True
for win, _d in WINDOWS:
    X = [int(min(block_vals(win, "hi", [3 * i + 1, 3 * i + 2, 3 * i + 3]))) for i in range(12)]
    Y = [int(min(block_vals(win, "tw", [3 * i + 1, 3 * i + 2, 3 * i + 3]))) for i in range(12)]
    vec[win] = (X, Y)
    if win != NEW_WIN and (X != REF_X[win] or Y != REF_Y[win]):
        vec_ok = False

anchor_rows = {}
anchor_ok = True
for win, _d in WINDOWS:
    a_med = int(pooled(win, "hi", sum128, [1, 2, 3]))
    bvals = [int(v) for v in block_vals(win, "hi", [1, 2, 3])]
    anchor_rows[win] = (a_med, min(bvals), max(bvals))
    if win != NEW_WIN and anchor_rows[win] != REF_ANCHOR[win]:
        anchor_ok = False

bA_new = [int(v) for v in block_vals(NEW_WIN, "hi", [1, 2, 3])]
s_cls = ("FLOOR" if all(v <= 100 for v in bA_new) else
         "CAPTURED" if all(v >= 1000 for v in bA_new) else "INTERMEDIATE/MIXED")

def invalidated():
    return any((v[0] != 0 or not v[1] or not v[2] or not v[3] or not v[4])
               for v in win_info.values()) or (not vec_ok) or (not c1_ok) or (not anchor_ok)

# ------------------------------------------------------------------
# observed primary contrast and D-tables (pure-Python paths above)
# ------------------------------------------------------------------
prim = {}
for ax in ("MAD", "IQR"):
    l2a = named_l2("s36", ax)
    l2b = named_l2(NEW_WIN, ax)
    prim[ax] = (l2a, l2b, l2a - l2b)

d_tbl = {}
for ax in ("MAD", "IQR"):
    j = 0 if ax == "MAD" else 1
    for win, _d in WINDOWS:
        d_tbl[(ax, win)] = [l2_checked([blk[(win, "tw", ci, b)][j] for b in range(12)])
                            for ci in range(len(ok_cells))]

d3_obs = {}
for ax in ("MAD", "IQR"):
    j = 0 if ax == "MAD" else 1
    for tag in ("hi", "tw"):
        l2w = {}
        for win, _d in WINDOWS:
            l2w[win] = [l2_checked([blk[(win, tag, ci, b)][j] for b in range(12)])
                        for ci in range(len(ok_cells))]
        s2 = [max(l2w[w][ci] for w, _d in WINDOWS) -
              min(l2w[w][ci] for w, _d in WINDOWS) for ci in range(len(ok_cells))]
        d3_obs[(ax, tag)] = (s2, max(s2))

# ------------------------------------------------------------------
# the resampling: np.partition kth paths (NOT a sort), the
# repartition and RNG call order re-implemented
# ------------------------------------------------------------------
def resample_block_d(pooled75, axis):
    part = np.partition(pooled75, (18, 37, 56), axis=-1)
    if axis == "IQR":
        return part[..., 56] - part[..., 18]
    med75 = part[..., 37]
    dev = np.abs(pooled75 - med75[..., None])
    return np.partition(dev, 37, axis=-1)[..., 37]

named_flat = np.array([gt for w in ("s36", NEW_WIN) for r in range(1, 37)
                       for gt in tbl_of(w, "tw", r)[nc]],
                      dtype=np.int64).reshape(72, 25)
assert named_flat.shape == (72, 25), named_flat.shape

def run_arr_np(win, tag):
    arr = np.zeros((36, len(ok_cells), 25), dtype=np.int64)
    for ri in range(36):
        t = tbl_of(win, tag, ri + 1)
        for k in ok_cells:
            arr[ri, cell_pos[k], :] = t[k]
    return arr

rng = random.Random(SEED)

def draw_perms(n):
    perms = np.empty((TRIALS, n), dtype=np.int64)
    for t in range(TRIALS):
        perm = list(range(n))
        rng.shuffle(perm)
        perms[t] = perm
    return perms

# frozen probe order: (1) primary MAD (2) primary IQR (3) D MAD-hi
# (4) D MAD-tw (5) D IQR-hi (6) D IQR-tw
prim_counts = {}
for ax in ("MAD", "IQR"):
    l2a, l2b, c_obs = prim[ax]
    perms = draw_perms(72)
    cnt = 0
    for i in range(0, TRIALS, BATCH):
        bperm = perms[i:i + BATCH].reshape(-1, 2, 12, 3)
        pooled_t = named_flat[bperm].reshape(-1, 2, 12, 75)
        d = resample_block_d(pooled_t, ax)
        ds = np.partition(d, (5, 6), axis=2)
        l2 = ds[:, :, 5] + ds[:, :, 6]
        cnt += int(((l2[:, 0] - l2[:, 1]) >= c_obs).sum())
    prim_counts[ax] = cnt

arr_cache = {}
d3_counts = {}
for ax in ("MAD", "IQR"):
    for tag in ("hi", "tw"):
        if tag not in arr_cache:
            arr_cache[tag] = np.concatenate([run_arr_np(w, tag) for w, _d in WINDOWS])
        arr = arr_cache[tag]
        s2, m_obs = d3_obs[(ax, tag)]
        perms = draw_perms(180)
        cnt = 0
        for i in range(0, TRIALS, BATCH):
            bperm = perms[i:i + BATCH].reshape(-1, 5, 12, 3)
            sub = arr[bperm]
            pooled_t = sub.transpose(0, 1, 2, 4, 3, 5).reshape(-1, 5, 12, 18, 75)
            d = resample_block_d(pooled_t, ax)
            ds = np.partition(d, (5, 6), axis=2)
            l2 = ds[:, :, 5, :] + ds[:, :, 6, :]
            s2t = l2.max(axis=1) - l2.min(axis=1)
            cnt += int((s2t.max(axis=1) >= m_obs).sum())
        d3_counts[(ax, tag)] = cnt

p_val = lambda cnt: (1 + cnt) / (1 + TRIALS)

def axis_letter(ax):
    _l2a, _l2b, c_obs = prim[ax]
    if invalidated():
        return "(c) NOT EVALUABLE"
    if c_obs > 0 and p_val(prim_counts[ax]) <= 0.05:
        return "(a) REPLICATED-CONTINUED"
    subcase = ("DIRECTION-REVERSED" if c_obs <= 0
               else "DIRECTION-CONSISTENT-NOT-SIGNIFICANT")
    return "(b) NOT-REPLICATED [%s]" % subcase

def joint_letter():
    if invalidated():
        return "(c) NOT EVALUABLE", []
    hits = [ax for ax in ("MAD", "IQR") if not axis_letter(ax).startswith("(a)")]
    if not hits:
        return "(a) CROSS-DAY-REPLICATED-ON-BOTH-LEVEL-AXES", []
    return "(b) NOT-CROSS-DAY-REPLICATED-ON-BOTH-AXES", hits

# ------------------------------------------------------------------
# independent publication reader (find/split, no regex)
# ------------------------------------------------------------------
pub_lines = open(PUB).read().split("\n")

def find_line(prefix, occurrence=0):
    hits = [l for l in pub_lines if l.startswith(prefix)]
    assert len(hits) > occurrence, (prefix, occurrence)
    return hits[occurrence]

rows = []
def rec(label, published, census):
    rows.append((label, str(published), str(census)))

# ---- section 1: integrity ----
for win, _d in WINDOWS:
    l = find_line("   %s: runs parsed " % win)
    parts = l.split("; ")
    want = "runs %s vmis %s counts %s knobs %s s8 %s cmap %s" % (
        parts[0].split("runs parsed ")[1],
        parts[1].split("total ")[1],
        parts[2].split(" ")[-1], parts[3].split(" ")[-1],
        parts[4].split(" ")[-1], parts[5].split(" ")[-1])
    vmis, cok, kok, fok, mok, nlogs = win_info[win]
    census = "runs %d vmis %d counts %s knobs %s s8 %s cmap %s" % (
        nlogs, vmis, cok, kok, fok, mok)
    rec("sec1 %s integrity" % win, want, census)

# ---- section 2: C1 ----
rec("sec2 c2 class",
    find_line("   c2 class: ").split("c2 class: ")[1].split(" ")[0], c2_cls)
rec("sec2 c8 pooled median",
    find_line("   c8 (sum,128,S=16) pooled median ").split("pooled median ")[1].split(" ")[0],
    "%.0f" % c8_m)
rec("sec2 C1 branch",
    find_line("   C1 branch: ").split("C1 branch: ")[1],
    "(a) both controls replicate" if c1_ok else "(b) discrepancy")

# ---- section 3: block-min vectors ----
for win, _d in WINDOWS:
    rec("sec3 %s X (hi)" % win,
        find_line("   %s X (hi): " % win).split(" (hi): ")[1],
        " ".join(str(v) for v in vec[win][0]))
    rec("sec3 %s Y (tw)" % win,
        find_line("   %s Y (tw): " % win).split(" (tw): ")[1],
        " ".join(str(v) for v in vec[win][1]))
    if win != NEW_WIN:
        rec("sec3 %s reproduction EXACT" % win,
            find_line("   %s reproduction EXACT: " % win).split("reproduction EXACT: ")[1],
            str(vec[win][0] == REF_X[win] and vec[win][1] == REF_Y[win]))
rec("sec3 prior vector reproduction (8/8)",
    find_line("   all four prior windows reproduce EXACTLY (8/8): ").split("(8/8): ")[1],
    str(vec_ok))

# ---- section 3b: anchor rows ----
for win, _d in WINDOWS:
    if win != NEW_WIN:
        l = find_line("    %s: median " % win)
        rec("sec3b %s anchor" % win,
            "%s %s" % (l.split("median ")[1].split(" ")[0],
                       l.split("min..max ")[1].split(" ")[0]),
            "%d %d..%d" % anchor_rows[win])
    else:
        l = find_line("    %s (NEW): median " % win)
        rec("sec3b %s anchor (fresh)" % win,
            "%s %s %s" % (l.split("median ")[1].split(" ")[0],
                          l.split("min..max ")[1].split(";")[0],
                          l.split("class ")[1]),
            "%d %d..%d %s" % (anchor_rows[win][0], anchor_rows[win][1],
                              anchor_rows[win][2], s_cls))
rec("sec3b prior anchor reproduction",
    find_line("    all four prior windows reproduce EXACTLY: ").split("EXACTLY: ")[1],
    str(anchor_ok))

# ---- section 4: T7 ----
for ax in ("MAD", "IQR"):
    l = find_line("   %s axis: " % ax)
    want = "%s %s C %s count %s p %s letter %s" % (
        l.split("2*L_s36 = ")[1].split(" ")[0],
        l.split("2*L_s73 = ")[1].split(" ")[0],
        l.split("C_obs = ")[1].split(";")[0],
        l.split("count ")[1].split(" /")[0],
        l.split("p = ")[1].split(";")[0],
        l.split("axis letter ")[1])
    l2a, l2b, c_obs = prim[ax]
    census = "%d %d C %s count %d p %.6f letter %s" % (
        l2a, l2b, fmt_ht(c_obs), prim_counts[ax], p_val(prim_counts[ax]),
        axis_letter(ax))
    rec("sec4 T7 %s axis" % ax, want, census)
t7, t7hits = joint_letter()
rec("sec4 T7 joint",
    find_line("   T7 = ").split("T7 = ")[1],
    t7 + ((" (named axis(es) not replicated: %s)" % ", ".join(t7hits))
          if t7hits else ""))

# ---- section 6 D1 ----
for ax in ("MAD", "IQR"):
    idx = [i for i, ll in enumerate(pub_lines)
           if ll.startswith("      %s: 2*L s36/s38/s39/s51/s73 = " % ax)][0]
    l = pub_lines[idx]
    nxt = pub_lines[idx + 1]
    want = "%s repro %s inband %s" % (
        l.split(" = ")[1].split(" (L")[0],
        nxt.split("EXACT: ")[1].split(";")[0],
        nxt.split("band interval: ")[1])
    vals = "/".join(str(named_l2(w, ax)) for w, _d in WINDOWS)
    repro = all(named_l2(w, ax) == REF_NAMED[ax][w]
                for w, _d in WINDOWS if w != NEW_WIN)
    band = sorted([named_l2(w, ax) for w in ("s38", "s39", "s51")])
    inband = band[0] <= named_l2(NEW_WIN, ax) <= band[-1]
    rec("sec6 D1 %s" % ax, want,
        "%s repro %s inband %s" % (vals, repro, inband))

# ---- section 6 D2 ----
for ci, k in enumerate(ok_cells):
    l = find_line("      tw cell %s: " % ckey_str(k))
    rest = l.split("%s: " % ckey_str(k), 1)[1]
    mpart, ipart = rest.split("; ")
    mt = mpart.split()
    it = ipart.split()
    want = "MAD %s C %s IQR %s C %s" % (mt[2], mt[4], it[2], it[4])
    l36m, l73m = d_tbl[("MAD", "s36")][ci], d_tbl[("MAD", NEW_WIN)][ci]
    l36i, l73i = d_tbl[("IQR", "s36")][ci], d_tbl[("IQR", NEW_WIN)][ci]
    census = "MAD %d/%d C %s IQR %d/%d C %s" % (
        l36m, l73m, fmt_ht(l36m - l73m), l36i, l73i, fmt_ht(l36i - l73i))
    rec("sec6 D2 %s" % ckey_str(k), want, census)

# ---- section 6 D3 ----
for ax in ("MAD", "IQR"):
    for tag in ("hi", "tw"):
        l = find_line("      %s-%s: M_obs = " % (ax, tag))
        m_and_cells = l.split("M_obs = ")[1]
        want = "M_obs %s cells %s count %s p %s" % (
            m_and_cells.split(" (max cell(s) ")[0],
            m_and_cells.split("(max cell(s) ")[1].split("); count")[0],
            l.split("count ")[1].split(" /")[0],
            l.split("p = ")[1])
        s2, m_obs = d3_obs[(ax, tag)]
        idxs = [ok_cells[i] for i in range(len(ok_cells)) if s2[i] == m_obs]
        mcs = ", ".join(ckey_str(i) for i in idxs)
        census = "M_obs %s cells %s count %d p %.6f" % (
            fmt_ht(m_obs), mcs, d3_counts[(ax, tag)], p_val(d3_counts[(ax, tag)]))
        rec("sec6 D3 %s-%s" % (ax, tag), want, census)

# ---- section 6 D4 ----
l = [ll for ll in pub_lines if "the ledger line of section 3b/5): median " in ll][0]
rec("sec6 D4 W5 anchor reading",
    "%s %s %s" % (l.split("median ")[1].split(" ")[0],
                  l.split("min..max ")[1].split(",")[0],
                  l.split("class ")[1].split(" vs ")[0]),
    "%d %d..%d %s" % (anchor_rows[NEW_WIN][0], anchor_rows[NEW_WIN][1],
                      anchor_rows[NEW_WIN][2], s_cls))

# ------------------------------------------------------------------
# section B: the observed-estimator cross-check census (counts)
# ------------------------------------------------------------------
hygiene = []
def hy(label, want, got):
    hygiene.append((label, str(want), str(got), str(want) == str(got)))

hy("block-D cross-check mismatches (pure-Python sorted() vs np.partition)",
   0, XC_BLK[1])
hy("level-median cross-check mismatches (sorted()[5]+[6] vs np.partition kth=(5,6))",
   0, XC_L2[1])

# ------------------------------------------------------------------
# section C: evidence hygiene
# ------------------------------------------------------------------
sh_found = []
for dirpath, _dirs, files in os.walk(GPU):
    for f in files:
        if f.endswith(".sh"):
            sh_found.append(f)
hy("evidence .sh count", 0, len(sh_found))

rw = open(os.path.join(HERE, "run-window.txt")).read().split("\n")
host_days = [l.split("host-date=")[1].split("T")[0] for l in rw if "host-date=" in l]
hy("W5 run-window run count (host-date lines)", 78, len(host_days))
uniq_days = sorted(set(host_days))
hy("W5 run-window UTC day", "2026-10-29",
   uniq_days[0] if len(uniq_days) == 1 else "MIXED:" + "/".join(uniq_days))
run_day = uniq_days[0] if len(uniq_days) == 1 else "UNKNOWN"

ledger_lines = open(os.path.join(GPU, "settle-bar-ledger.txt")).read().splitlines()
reading_lines = [l for l in ledger_lines if l.startswith("day=")]
hy("ledger reading-line count", 9, len(reading_lines))
s73_lines = [l for l in reading_lines if "session=s73" in l]
hy("ledger s73 line count", 1, len(s73_lines))
hy("ledger s73 line (derived from the census D4 reading)",
   "day=%s session=s73 class=%s median=%d min=%d flag=none"
   % (run_day, s_cls, anchor_rows[NEW_WIN][0], anchor_rows[NEW_WIN][1]),
   s73_lines[0] if s73_lines else "(none)")

# ------------------------------------------------------------------
# report
# ------------------------------------------------------------------
out = []
P = out.append
P("JUN-59 session 76 -- the five-window derivation census")
P("(derivation-census-s73.py, the INDEPENDENT second parser for")
P("publication-s73.txt; s73 carry-forward 3(b), protocol.txt")
P("section 0 implementation paths). Two-way rows: published =")
P("publication-s73.txt parsed find/split from the committed bytes,")
P("census = recomputed here from the 390 committed run logs of the")
P("five fixed directories; NO in-memory state of analysis-s73.py is")
P("consulted. Split-based parsing, no re module; observed block")
P("estimators are pure-Python sorted() order statistics over the")
P("explicitly pooled 75 (MAD = sorted(|x - sorted(pooled75)[37]|)")
P("[37]; IQR = sorted(pooled75)[56] - sorted(pooled75)[18])")
P("cross-checked in-loop against the np.partition kth paths; the")
P("resampling's estimators use the np.partition kth paths, NOT a")
P("sort (analysis-s73.py used np.sort); the resampling's 12-value")
P("level medians use np.partition kth=(5,6); the repartition")
P("resampling and the RNG call order are re-implemented: ONE")
P("random.Random(20261029) consumed in the frozen probe order")
P("primary MAD / primary IQR / D MAD-hi / D MAD-tw / D IQR-hi /")
P("D IQR-tw, %d trials per probe, one fresh-list rng.shuffle per" % TRIALS)
P("trial). The published T7 values are now cross-checked by an")
P("independent parser (record-s75.txt 5(a)).")
P("")
if SMOKE:
    P("!!! CENSUS_SMOKE PLUMBING RUN (TRIALS=20) -- NOT the committed")
    P("!!! census; the six RNG count/p rows mismatch by construction.")
    P("")
mismatched = 0
for i, (label, published, census) in enumerate(rows):
    match = published == census
    if not match:
        mismatched += 1
    P("row %02d: %s: published [%s] | census [%s] | match %s"
      % (i + 1, label, published, census, match))
P("")
P("TOTAL: %d rows, %d mismatched" % (len(rows), mismatched))
P("")
P("SECTION B -- observed-estimator cross-check (the in-loop dual")
P("computation of every observed block D and level median):")
P("block-D cross-check: %d comparisons (2 per block: MAD + IQR)" % XC_BLK[0])
P("level-median cross-check: %d comparisons" % XC_L2[0])
mismatched_b = 0
for label, want, got, match in hygiene[:2]:
    if not match:
        mismatched_b += 1
    P("%s: want [%s] got [%s] | match %s" % (label, want, got, match))
P("")
P("TOTAL: %d checks, %d mismatched" % (2, mismatched_b))
P("")
P("SECTION C -- evidence hygiene:")
mismatched_c = 0
for label, want, got, match in hygiene[2:]:
    if not match:
        mismatched_c += 1
    P("%s: want [%s] got [%s] | match %s" % (label, want, got, match))
P("")
P("TOTAL: %d checks, %d mismatched" % (len(hygiene) - 2, mismatched_c))
P("")
P("DETERMINISM: this generator run twice yields byte-identical")
P("output (double-run status named in the s76 record; RNG seeded,")
P("no set iteration).")

outpath = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "derivation-census-s73.txt")
open(outpath, "w").write("\n".join(out) + "\n")
print("TOTAL: %d rows, %d mismatched | B: %d | C: %d"
      % (len(rows), mismatched, mismatched_b, mismatched_c))
sys.exit(0 if (mismatched + mismatched_b + mismatched_c) == 0 else 1)
