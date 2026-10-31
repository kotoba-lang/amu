#!/usr/bin/env python3
"""JUN-59 session 83 -- the T17 derivation census
(derivation-census-s82.py, the INDEPENDENT second parser for
publication-s82.txt; the s82-frozen protocol.txt section 6
implementation paths).

Independence contract (frozen at s83):
- NO regex, NO re module. Run-log parsing is split()-based k=v
  tokenising; publication parsing is find/split-based.
- The OBSERVED estimators are pure-Python sorted() order
  statistics over the explicitly pooled 75 -- the DL pair spreads
  sorted(pooled75)[b] - sorted(pooled75)[a] for the closed
  vocabulary DL4 (33,41) / DL8 (29,45) / DL16 (21,53) / DL32
  (5,69) (0-based) plus the two s78 validity pairs INNER (27,47)
  and OUTER (8,66) -- CROSS-CHECKED IN-LOOP against the
  np.partition kth paths (every observed pair spread of every
  window, block and ok cell is computed BOTH ways; the cross-check
  census is section B).
- The pooled-75 cell medians (block-min vectors, anchors, C1) are
  pure-Python sorted()[37], cross-checked in-loop against
  np.partition kth=37.
- The 12-value 2*L level statistics are sorted() explicit order
  statistics (sorted(ds)[5] + sorted(ds)[6]), cross-checked
  against np.partition kth=(5,6).
- analysis-s82.py used numpy np.sort / np.median paths and regex
  parsing -- the computational and parsing paths here are
  genuinely different.
- NO RNG anywhere (publication-s82.txt is descriptive; there is
  no resampling to re-implement).

This script re-derives, from the 390 committed run logs of the five
fixed evidence directories (no in-memory state of analysis-s82.py is
consulted), every published value of publication-s82.txt, in
two-way rows: published (the committed publication-s82.txt line,
find/split located) vs census (the same line re-derived here in
full).

BAND CONVENTION NAMED, NOT HIDDEN: the published section-5 band
lines print "band 2*L A..B (closed interval spanned by
{s38,s39,s51})" where A..B are sorted[0]..sorted[1] of the three
2*L values -- with three values sorted[1] is the MEDIAN, so the
published interval is min..median, NOT min..max (for DL4 the
{47,48,38} band prints 38..47 while s39's 48 sits above the
printed top). The census reproduces the PUBLISHED convention for
byte-equality and additionally reports, in section B, the min..max
"spanned by" intervals and the verdict-invariance check; at this
row all four band VERDICTS (INSIDE/INSIDE/OUTSIDE-BELOW/
OUTSIDE-ABOVE) are UNCHANGED under min..max.

Deterministic: running it twice yields byte-identical output (no
RNG, no set iteration). Usage: derivation-census-s82.py
[OUTPUT-PATH] (default: derivation-census-s82.txt beside this
file).
"""
import os, sys, statistics
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
GPU = os.path.join(ROOT, "docs", "evidence", "gpu")
PUB = os.path.join(HERE, "publication-s82.txt")

COMMITTED_C8 = 32915
NAMED_CKEY = ("max", 128, "default")
NEW_WIN = "s73"
WINDOWS = [("s36", "anv-b3commonmode-20261028"),
           ("s38", "anv-b3joint3-20261028"),
           ("s39", "anv-b3joint4-20261028"),
           ("s51", "anv-b3levelrep-20261028"),
           (NEW_WIN, "anv-b3w5xdayrep-20261029")]
ARMS = {"c2": (2, 1, 1, [1, 2, 3]),
        "hi": (3, 1024, 4033, list(range(1, 37))),
        "tw": (3, 2048, 8066, list(range(1, 37))),
        "c8": (8, 1, 1, [1, 2, 3])}

# THE DL VOCABULARY + the two s78 validity pairs (0-based sorted
# indices of the pooled 75).
DL = (("DL4", 33, 41), ("DL8", 29, 45), ("DL16", 21, 53), ("DL32", 5, 69))
DL_LABEL = {"DL4": "DL4 (x_(34),x_(42))", "DL8": "DL8 (x_(30),x_(46))",
            "DL16": "DL16 (x_(22),x_(54))", "DL32": "DL32 (x_(6),x_(70))"}
VALID = (("inner", "INNER (28,48)", 27, 47,
          [118, 102, 128, 113, 100],
          [42, 34, 40, 48, 74, 48, 60, 39, 74, 56, 52, 57]),
         ("outer", "OUTER (9,67)", 8, 66,
          [496, 429, 437, 446, 502],
          [267, 189, 242, 377, 340, 278, 214, 181, 255, 247, 268, 194]))
ALL_PAIRS = [(n, a, b) for (n, a, b) in DL] + \
            [(t, a, b) for (t, _l, a, b, _v, _w) in VALID]

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

def fmt_ht(x2):
    return "%.1f" % (x2 / 2)

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
    for tag in ("c2", "hi", "tw", "c8"):
        b, wm, dd, runs = ARMS[tag]
        for r in runs:
            fn = os.path.join(src, "run-%s-r%d.txt" % (tag, r))
            cells, verifies, samples = load(fn)
            data[(win, tag, r)] = (cells, verifies, samples)
            for (_i, _c, mis) in verifies:
                vmis += mis
            s8 = [k for k, v in cells.items() if v["forced"] == "8"]
            if len(s8) != 6 or any(cells[k]["pipeline"] != "FAIL" or cells[k]["void"] != "1"
                                   for k in s8):
                fail_ok = False
            if len(samples) != 450 or len(verifies) != 24:
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
    win_info[win] = (vmis, counts_ok, knob_ok, fail_ok, cmap_ok)

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
named_ok = (ckey_str(nc) == "(max,128,S=default)")

run_tbl = {}
def tbl_of(win, tag, r):
    key = (win, tag, r)
    if key not in run_tbl:
        t = {}
        for s in data[key][2]:
            t.setdefault(s[1], []).append(s[2])
        run_tbl[key] = t
    return run_tbl[key]

# ------------------------------------------------------------------
# pooled-75 cell medians: pure-Python sorted()[37] FIRST,
# cross-checked against np.partition kth=37 (XC_MED).
# ------------------------------------------------------------------
XC_MED = [0, 0]
def pooled(win, tag, idx, runs):
    xs = []
    for r in runs:
        xs += tbl_of(win, tag, r)[idx]
    s = sorted(xs)
    py = s[37]
    arr = np.asarray(xs, dtype=np.int64)
    npx = int(np.partition(arr, 37)[37])
    XC_MED[0] += 1
    if py != npx:
        XC_MED[1] += 1
    return py

def block_vals(win, tag, runs):
    return [pooled(win, tag, k, runs) for k in ok_cells]

# ------------------------------------------------------------------
# pair spreads over the block's pooled 75: pure-Python sorted()
# FIRST, cross-checked in-loop against np.partition kth=(a,b)
# (XC_D), for every window, block, ok cell and pair (the four DL
# pairs plus the two s78 validity pairs).
# ------------------------------------------------------------------
XC_D = [0, 0]
def pair_d_checked(vals75, a, b):
    s = sorted(vals75)
    py = s[b] - s[a]
    npp = np.partition(np.asarray(vals75, dtype=np.int64), (a, b))
    npx = int(npp[b] - npp[a])
    XC_D[0] += 1
    if py != npx:
        XC_D[1] += 1
    return py

dt_all = {}     # (win, pairname) -> 12 x len(ok_cells) block spreads
for win, _d in WINDOWS:
    for name, a, b in ALL_PAIRS:
        tab = [[0] * len(ok_cells) for _ in range(12)]
        for i in range(12):
            for ci in range(len(ok_cells)):
                vals = []
                for r in (3 * i + 1, 3 * i + 2, 3 * i + 3):
                    vals += tbl_of(win, "tw", r)[ok_cells[ci]]
                tab[i][ci] = pair_d_checked(vals, a, b)
        dt_all[(win, name)] = tab

# ------------------------------------------------------------------
# 2*L level statistics: sorted()[5]+sorted()[6] FIRST, cross-checked
# against np.partition kth=(5,6) (XC_L2).
# ------------------------------------------------------------------
XC_L2 = [0, 0]
def l2_checked(d12):
    s = sorted(d12)
    py = s[5] + s[6]
    npp = np.partition(np.asarray(d12, dtype=np.int64), (5, 6))
    npx = int(npp[5] + npp[6])
    XC_L2[0] += 1
    if py != npx:
        XC_L2[1] += 1
    return py

dt = {}     # (name, win) -> the 12 named-cell block D values
l2 = {}     # (name, win) -> 2*L
for name, _a, _b in ALL_PAIRS:
    for win, _d in WINDOWS:
        tab = [dt_all[(win, name)][i][nc_pos] for i in range(12)]
        dt[(name, win)] = tab
        l2[(name, win)] = l2_checked(tab)

# ------------------------------------------------------------------
# C1, block-min vectors, anchor reproduction rows (pure-Python)
# ------------------------------------------------------------------
c2_vals = block_vals(NEW_WIN, "c2", ARMS["c2"][3])
c2_cls = ("FLOOR" if all(v <= 100 for v in c2_vals) else
          "CAPTURED" if all(v >= 1000 for v in c2_vals) else "INTERMEDIATE/MIXED")
c8_m = pooled(NEW_WIN, "c8", sum128, ARMS["c8"][3])
c1_ok = (c2_cls == "FLOOR") and abs(c8_m - COMMITTED_C8) <= 0.05 * COMMITTED_C8

vec = {}
vec_ok = True
for win, _d in WINDOWS:
    X = [min(block_vals(win, "hi", [3 * i + 1, 3 * i + 2, 3 * i + 3])) for i in range(12)]
    Y = [min(block_vals(win, "tw", [3 * i + 1, 3 * i + 2, 3 * i + 3])) for i in range(12)]
    vec[win] = (X, Y)
    if win != NEW_WIN and (X != REF_X[win] or Y != REF_Y[win]):
        vec_ok = False

anchor_rows = {}
anchor_ok = True
for win, _d in WINDOWS:
    if win == NEW_WIN:
        continue   # this row computes NO anchor at W5 (protocol section 3)
    a_med = pooled(win, "hi", sum128, [1, 2, 3])
    bvals = block_vals(win, "hi", [1, 2, 3])
    anchor_rows[win] = (a_med, min(bvals), max(bvals))
    if anchor_rows[win] != REF_ANCHOR[win]:
        anchor_ok = False

# ------------------------------------------------------------------
# validity pins (the published s78 quantile-pair vectors)
# ------------------------------------------------------------------
valid_rows = []
valid_ok = True
for tag, label, _a, _b, ref_vec, ref_w5d in VALID:
    got_vec = [l2[(tag, w)] for w, _d in WINDOWS]
    got_w5d = dt[(tag, NEW_WIN)]
    ok = (got_vec == ref_vec) and (got_w5d == ref_w5d)
    valid_rows.append((label, got_vec, got_w5d, ok))
    if not ok:
        valid_ok = False

# ------------------------------------------------------------------
# the DL table + the published band convention and the min..max
# "spanned by" variant (verdict-invariance check)
# ------------------------------------------------------------------
dl_tab = {}
band_rows = []
for name, _a, _b in DL:
    for win, _d in WINDOWS:
        dl_tab[(name, win)] = (l2[(name, win)], dt[(name, win)])
    band3 = sorted(l2[(name, w)] for w in ("s38", "s39", "s51"))
    l2_w5 = l2[(name, NEW_WIN)]
    if l2_w5 < band3[0]:
        v_pub = "OUTSIDE-BELOW"
        v_mm = "OUTSIDE-BELOW"
    else:
        if l2_w5 > band3[1]:
            v_pub = "OUTSIDE-ABOVE"
        else:
            v_pub = "INSIDE"
        if l2_w5 > band3[2]:
            v_mm = "OUTSIDE-ABOVE"
        else:
            v_mm = "INSIDE"
    band_rows.append((name, band3, v_pub, v_mm))
band_verdicts_invariant = all(vp == vm for (_n, _b, vp, vm) in band_rows)

def invalidated():
    return any((v[0] != 0 or not v[1] or not v[2] or not v[3] or not v[4])
               for v in win_info.values()) or (not named_ok) or (not vec_ok) \
        or (not c1_ok) or (not anchor_ok) or (not valid_ok)

# ------------------------------------------------------------------
# independent publication reader (find/split, no regex)
# ------------------------------------------------------------------
pub_lines = open(PUB).read().split("\n")

def find_line(prefix, occurrence=0):
    hits = [l for l in pub_lines if l.startswith(prefix)]
    assert len(hits) > occurrence, (prefix, occurrence)
    return hits[occurrence]

def find_line_with(prefix, infix):
    hits = [l for l in pub_lines if l.startswith(prefix) and infix in l]
    assert len(hits) == 1, (prefix, infix, len(hits))
    return hits[0]

def find_line_without(prefix, infix):
    hits = [l for l in pub_lines if l.startswith(prefix) and infix not in l]
    assert len(hits) == 1, (prefix, infix, len(hits))
    return hits[0]

rows = []
def rec(label, published, census):
    rows.append((label, str(published), str(census)))

# ---- section 1: integrity ----
for win, _d in WINDOWS:
    vmis, cok, kok, fok, mok = win_info[win]
    rec("sec1 %s integrity" % win,
        find_line("   %s: runs parsed " % win),
        ("   %s: runs parsed 78; VERIFY mismatch total %d; counts ok %s; "
         "knobs ok %s; S=8 fail-closed %s; cell map ok %s"
         % (win, vmis, cok, kok, fok, mok)))
rec("sec1 named cell position",
    find_line("   named cell present as ok-map cell "),
    ("   named cell present as ok-map cell %d (raw idx %d == %s): %s"
     % (nc_pos, nc, ckey_str(nc), named_ok)))

# ---- section 2: C1 ----
rec("sec2 c2 class",
    find_line("   c2 class: "),
    "   c2 class: %s (FLOOR required; committed floor band 31..32)" % c2_cls)
rec("sec2 c8 pooled median",
    find_line("   c8 (sum,128,S=16) pooled median "),
    ("   c8 (sum,128,S=16) pooled median %.0f vs committed %d "
     "(%.2f%% delta; +/-5%% required)" % (c8_m, COMMITTED_C8,
                                         abs(c8_m - COMMITTED_C8) / COMMITTED_C8 * 100)))
rec("sec2 C1 branch",
    find_line("   C1 branch: "),
    "   C1 branch: %s" % ("(a) both controls replicate" if c1_ok else "(b) discrepancy"))

# ---- section 3: block-min vectors ----
for win, _d in WINDOWS:
    rec("sec3 %s X (hi)" % win,
        find_line("   %s X (hi): " % win),
        "   %s X (hi): %s" % (win, " ".join(str(v) for v in vec[win][0])))
    rec("sec3 %s Y (tw)" % win,
        find_line("   %s Y (tw): " % win),
        "   %s Y (tw): %s" % (win, " ".join(str(v) for v in vec[win][1])))
    if win != NEW_WIN:
        rec("sec3 %s reproduction EXACT" % win,
            find_line("   %s reproduction EXACT: " % win),
            "   %s reproduction EXACT: %s"
            % (win, vec[win][0] == REF_X[win] and vec[win][1] == REF_Y[win]))
rec("sec3 prior vector reproduction (8/8)",
    find_line("   all four prior windows reproduce EXACTLY (8/8): "),
    "   all four prior windows reproduce EXACTLY (8/8): %s" % vec_ok)

# ---- section 3b: anchor reproduction rows ----
for win, _d in WINDOWS:
    if win == NEW_WIN:
        continue
    a_med, a_min, a_max = anchor_rows[win]
    rec("sec3b %s anchor" % win,
        find_line("    %s: median " % win),
        ("    %s: median %d min..max %d..%d (want %d / %d..%d); "
         "reproduction EXACT: %s" % (win, a_med, a_min, a_max,
                                     REF_ANCHOR[win][0], REF_ANCHOR[win][1],
                                     REF_ANCHOR[win][2],
                                     (a_med, a_min, a_max) == REF_ANCHOR[win])))
rec("sec3b prior anchor reproduction",
    find_line("    all four prior windows reproduce EXACTLY: "),
    "    all four prior windows reproduce EXACTLY: %s" % anchor_ok)

# ---- section 4: parser validity pins ----
for (label, got_vec, got_w5d, ok), (_t, plabel, _a, _b, ref_vec, _w) in \
        zip(valid_rows, VALID):
    rec("sec4 %s" % plabel,
        find_line("   %s: 2*L s36/s38/s39/s51/s73 = " % plabel),
        ("   %s: 2*L s36/s38/s39/s51/s73 = %s (want %s); W5 block D %s "
         "(want pinned vector); EXACT: %s"
         % (plabel, "/".join(str(v) for v in got_vec),
            "/".join(str(v) for v in ref_vec),
            " ".join(str(v) for v in got_w5d), ok)))
rec("sec4 all validity pins",
    find_line("   all validity pins EXACT: "),
    "   all validity pins EXACT: %s" % valid_ok)

# ---- section 5: the DL table ----
for name, _a, _b in DL:
    vals = [dl_tab[(name, w)][0] for w, _d in WINDOWS]
    rec("sec5 %s vector" % name,
        find_line_with("   %s: 2*L " % DL_LABEL[name], "(L "),
        ("   %s: 2*L s36/s38/s39/s51/s73 = %s (L %s)"
         % (DL_LABEL[name], "/".join(str(v) for v in vals),
            "/".join(fmt_ht(v) for v in vals))))
    rec("sec5 %s W5 block D" % name,
        find_line("   %s W5 block D values: " % DL_LABEL[name]),
        ("   %s W5 block D values: %s"
         % (DL_LABEL[name],
            " ".join(str(v) for v in dl_tab[(name, NEW_WIN)][1]))))
    band3 = sorted(dl_tab[(name, w)][0] for w in ("s38", "s39", "s51"))
    l2_w5 = dl_tab[(name, NEW_WIN)][0]
    if l2_w5 < band3[0]:
        verdict = "OUTSIDE-BELOW"
    elif l2_w5 > band3[1]:
        verdict = "OUTSIDE-ABOVE"
    else:
        verdict = "INSIDE"
    rec("sec5 %s band" % name,
        find_line("   %s W5-vs-post-shift-band: " % DL_LABEL[name]),
        ("   %s W5-vs-post-shift-band: 2*L_W5 = %d vs band 2*L %d..%d "
         "(closed interval spanned by {s38,s39,s51}): %s"
         % (DL_LABEL[name], l2_w5, band3[0], band3[1], verdict)))

# ---- section 6: verdict summary ----
rec("sec6 T17 verdict",
    find_line("   T17 table: "),
    "   T17 table: EVALUABLE, DESCRIPTIVE ONLY -- NO letter exists"
    if not invalidated() else
    "   T17 table: NOT EVALUABLE (an integrity/validity criterion")
for name, _a, _b in DL:
    vals = [dl_tab[(name, w)][0] for w, _d in WINDOWS]
    rec("sec6 %s summary" % name,
        find_line_without("   %s: 2*L " % DL_LABEL[name], "s36"),
        "   %s: 2*L %s" % (DL_LABEL[name], "/".join(str(v) for v in vals)))

# ------------------------------------------------------------------
# section B: the estimator cross-check census (counts)
# ------------------------------------------------------------------
hygiene = []
def hy(label, want, got):
    hygiene.append((label, str(want), str(got), str(want) == str(got)))

hy("pair-spread cross-check mismatches (pure-Python sorted() vs np.partition kth=(a,b))",
   0, XC_D[1])
hy("pooled-median cross-check mismatches (sorted()[37] vs np.partition kth=37)",
   0, XC_MED[1])
hy("2*L cross-check mismatches (sorted()[5]+[6] vs np.partition kth=(5,6))",
   0, XC_L2[1])
hy("band verdicts unchanged under min..max 'spanned by' interval (4 DL pairs)",
   True, band_verdicts_invariant)

# ------------------------------------------------------------------
# section C: evidence hygiene
# ------------------------------------------------------------------
sh_found = []
for dirpath, _dirs, files in os.walk(GPU):
    for f in files:
        if f.endswith(".sh"):
            sh_found.append(f)
hy("evidence .sh count", 0, len(sh_found))

rw = open(os.path.join(GPU, "anv-b3w5xdayrep-20261029", "run-window.txt")).read().split("\n")
host_days = [l.split("host-date=")[1].split("T")[0] for l in rw if "host-date=" in l]
hy("W5 run-window run count (host-date lines)", 78, len(host_days))
uniq_days = sorted(set(host_days))
hy("W5 run-window UTC day", "2026-10-29",
   uniq_days[0] if len(uniq_days) == 1 else "MIXED:" + "/".join(uniq_days))

ledger_lines = open(os.path.join(GPU, "settle-bar-ledger.txt")).read().splitlines()
reading_lines = [l for l in ledger_lines if l.startswith("day=")]
hy("ledger reading-line count (this row writes NO line -- protocol section 5)",
   9, len(reading_lines))
s83_lines = [l for l in reading_lines if "session=s83" in l]
hy("ledger session=s83 line count", 0, len(s83_lines))

# ------------------------------------------------------------------
# report
# ------------------------------------------------------------------
out = []
P = out.append
P("JUN-59 session 83 -- the T17 derivation census")
P("(derivation-census-s82.py, the INDEPENDENT second parser for")
P("publication-s82.txt; the s82-frozen protocol.txt section 6")
P("implementation paths). Two-way rows: published =")
P("publication-s82.txt lines parsed find/split from the committed")
P("bytes, census = the same lines re-derived in full here from the")
P("390 committed run logs of the five fixed directories; NO")
P("in-memory state of analysis-s82.py is consulted. Split-based")
P("parsing, no re module; the observed DL/validity pair spreads")
P("are pure-Python sorted() order statistics over the explicitly")
P("pooled 75 cross-checked in-loop against the np.partition")
P("kth=(a,b) paths (analysis-s82.py used np.sort + regex); the")
P("pooled-75 cell medians are sorted()[37] cross-checked against")
P("np.partition kth=37 (analysis used np.median); the 12-value 2*L")
P("statistics are sorted()[5]+[6] cross-checked against")
P("np.partition kth=(5,6). NO RNG anywhere (the row is")
P("descriptive; no resampling exists to re-implement).")
P("")
P("BAND CONVENTION NAMED, NOT HIDDEN: the published section-5 band")
P("lines print sorted[0]..sorted[1] of the three {s38,s39,s51} 2*L")
P("values under the label 'closed interval spanned by")
P("{s38,s39,s51}' -- with three values sorted[1] is the MEDIAN, so")
P("the printed interval is min..median, NOT min..max. The census")
P("reproduces the PUBLISHED convention for byte-equality; section")
P("B reports the min..max intervals and the verdict-invariance")
P("check (all four band verdicts unchanged at this row).")
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
P("SECTION B -- estimator cross-check (the in-loop dual")
P("computation: every observed pair spread of every window, block")
P("and ok cell -- 5 windows x 12 blocks x %d ok cells x %d pairs ="
  % (len(ok_cells), len(ALL_PAIRS)))
P("%d comparisons; every pooled-75 cell median; every 2*L):"
  % XC_D[0])
P("pair-spread cross-check: %d comparisons" % XC_D[0])
P("pooled-median cross-check: %d comparisons" % XC_MED[0])
P("2*L cross-check: %d comparisons" % XC_L2[0])
mismatched_b = 0
for label, want, got, match in hygiene[:4]:
    if not match:
        mismatched_b += 1
    P("%s: want [%s] got [%s] | match %s" % (label, want, got, match))
P("band min..max 'spanned by' intervals (the convention the label")
P("describes):")
for name, band3, _vp, _vm in band_rows:
    P("   %s: 2*L {s38,s39,s51} = %d/%d/%d -> min..max %d..%d"
      % (name, band3[0], band3[1], band3[2], band3[0], band3[2]))
    P("   (published line prints min..median %d..%d); W5 %d -> verdict"
      % (band3[0], band3[1], l2[(name, NEW_WIN)]))
    P("   %s under BOTH conventions" % (_vp if _vp == _vm else
                                        "CHANGED (%s vs %s)" % (_vp, _vm)))
P("")
P("TOTAL: %d checks, %d mismatched" % (4, mismatched_b))
P("")
P("SECTION C -- evidence hygiene:")
mismatched_c = 0
for label, want, got, match in hygiene[4:]:
    if not match:
        mismatched_c += 1
    P("%s: want [%s] got [%s] | match %s" % (label, want, got, match))
P("")
P("TOTAL: %d checks, %d mismatched" % (len(hygiene) - 4, mismatched_c))
P("")
P("DETERMINISM: this generator run twice yields byte-identical")
P("output (double-run status named in the s83 record; NO RNG, no")
P("set iteration).")

outpath = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "derivation-census-s82.txt")
open(outpath, "w").write("\n".join(out) + "\n")
print("TOTAL: %d rows, %d mismatched | B: %d | C: %d"
      % (len(rows), mismatched, mismatched_b, mismatched_c))
sys.exit(0 if (mismatched + mismatched_b + mismatched_c) == 0 else 1)
