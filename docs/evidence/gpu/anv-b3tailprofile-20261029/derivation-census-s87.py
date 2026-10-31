#!/usr/bin/env python3
"""JUN-59 session 89 -- the T19 derivation census
(derivation-census-s87.py, the INDEPENDENT second parser for
publication-s87.txt; the s87-frozen protocol.txt section 6
implementation paths).

Independence contract (frozen at s89, the s83 contract adapted):
- NO regex, NO re module. Run-log parsing is split()-based k=v
  tokenising; publication parsing is find/split-based.
  (analysis-s87.py parsed with re.compile regexes.)
- The OBSERVED estimators are computed on the numpy np.partition
  kth paths (analysis-s87.py is pure stdlib -- sorted() order
  statistics and a pure-Python float median -- and imports NO
  numpy at all) -- the computational path here is genuinely
  different -- CROSS-CHECKED IN-LOOP against pure-Python sorted()
  explicit order statistics (the algorithm family analysis-s87.py
  used): every named-cell block half-pair/pair spread of every
  window and block (the 8 TS half-pairs + the 4 DL pairs + the 2
  s78 validity pairs = 14 pairs x 5 windows x 12 blocks), every
  pooled-75 cell median (sorted()[37] vs np.partition kth=37),
  every 12-value 2*L (sorted()[5]+[6] vs np.partition kth=(5,6)).
- The DL decomposition identity HL_k + HR_k = D_k is re-checked
  per block (4 families x 5 windows x 12 blocks = 240 checks)
  against the independently computed DL pair spread.
- NO RNG anywhere (publication-s87.txt is descriptive; there is
  no resampling to re-implement), no clock.

This script re-derives, from the 390 committed run logs of the five
fixed evidence directories (no in-memory state of analysis-s87.py is
consulted), every published computed value of publication-s87.txt,
in two-way rows: published (the committed publication-s87.txt line,
find/split located) vs census (the same line re-derived here in
full). Wrapped publication segments (the decomposition-identity
line, the section-6 T19 verdict line, the evaluable-inputs
fragment) are compared whitespace-normalized.

BAND CONVENTION NAMED, NOT HIDDEN (the s83 precedent applied):
the published section-5 band lines print sorted[0]..sorted[1] of
the three {s38,s39,s51} 2*L values (and judge W5 against
sorted[1]) while BOTH the frozen protocol.txt section 5 AND the
printed label itself name "the closed interval [MIN,MAX] spanned
by {s38,s39,s51}" -- with three values sorted[1] is the MEDIAN,
so the printed interval is min..median, NOT min..MAX. The census
reproduces the PUBLISHED (min..median) computation for
byte-equality; SECTION D audits the frozen [MIN,MAX] convention
separately and reports every verdict that changes under it.

Deterministic: running it twice yields byte-identical output (no
RNG, no set iteration). Usage: derivation-census-s87.py
[OUTPUT-PATH] (default: derivation-census-s87.txt beside this
file).
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
GPU = os.path.join(ROOT, "docs", "evidence", "gpu")
PUB = os.path.join(HERE, "publication-s87.txt")
PUB_SHA256 = "ebe4daa741bf97c49762cb45635fad406773d778f6df189360178561aa88b174"
PUB_BYTES = 13188

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

# THE TAIL-SIDE HALF-PAIR VOCABULARY (the s86 freeze; 0-based
# sorted indices of the pooled 75): TS-Lk = (x_(38-k), x_(38)),
# TS-Rk = (x_(38), x_(38+k)); deviation-center rank x_(38).
TS = (("TS-L4", 4, 33, 37), ("TS-R4", 4, 37, 41),
      ("TS-L8", 8, 29, 37), ("TS-R8", 8, 37, 45),
      ("TS-L16", 16, 21, 37), ("TS-R16", 16, 37, 53),
      ("TS-L32", 32, 5, 37), ("TS-R32", 32, 37, 69))
TS_LABEL = {"TS-L4": "TS-L4 (x_(34),x_(38))", "TS-R4": "TS-R4 (x_(38),x_(42))",
            "TS-L8": "TS-L8 (x_(30),x_(38))", "TS-R8": "TS-R8 (x_(38),x_(46))",
            "TS-L16": "TS-L16 (x_(22),x_(38))", "TS-R16": "TS-R16 (x_(38),x_(54))",
            "TS-L32": "TS-L32 (x_(6),x_(38))", "TS-R32": "TS-R32 (x_(38),x_(70))"}
# the four k families: (k, TS-L name, TS-R name, DL name, DL 0-based pair)
FAMILIES = ((4, "TS-L4", "TS-R4", "DL4", 33, 41),
            (8, "TS-L8", "TS-R8", "DL8", 29, 45),
            (16, "TS-L16", "TS-R16", "DL16", 21, 53),
            (32, "TS-L32", "TS-R32", "DL32", 5, 69))
DL_LABEL = {"DL4": "DL4 (x_(34),x_(42))", "DL8": "DL8 (x_(30),x_(46))",
            "DL16": "DL16 (x_(22),x_(54))", "DL32": "DL32 (x_(6),x_(70))"}
NARROW = (4, 8)   # s86 caveat: spans 4/8 sit in the narrow-span noise band

# PARSER VALIDITY PINS (published s78 quantile-pair vectors AND
# published s82 DL vectors; committed quote-only pins).
VALID = (("INNER (28,48)", 27, 47,
          [118, 102, 128, 113, 100],
          [42, 34, 40, 48, 74, 48, 60, 39, 74, 56, 52, 57]),
         ("OUTER (9,67)", 8, 66,
          [496, 429, 437, 446, 502],
          [267, 189, 242, 377, 340, 278, 214, 181, 255, 247, 268, 194]),
         ("DL4 (x_(34),x_(42))", 33, 41,
          [46, 47, 48, 38, 40],
          [20, 17, 18, 21, 33, 17, 20, 15, 36, 20, 16, 23]),
         ("DL8 (x_(30),x_(46))", 29, 45,
          [97, 84, 99, 79, 83],
          [35, 27, 34, 44, 61, 38, 48, 25, 57, 42, 41, 45]),
         ("DL16 (x_(22),x_(54))", 21, 53,
          [238, 187, 201, 188, 178],
          [74, 63, 70, 87, 116, 91, 96, 70, 113, 103, 92, 81]),
         ("DL32 (x_(6),x_(70))", 5, 69,
          [655, 537, 572, 564, 658],
          [360, 261, 287, 429, 430, 399, 277, 279, 323, 335, 368, 297]))

REF_X = {"s36": [991, 989, 981, 998, 993, 985, 984, 997, 994, 994, 980, 982],
         "s38": [992, 988, 984, 1007, 985, 984, 986, 983, 992, 991, 982, 997],
         "s39": [986, 991, 984, 985, 989, 989, 986, 990, 995, 986, 987, 981],
         "s51": [988, 986, 1000, 986, 989, 983, 995, 983, 994, 991, 984, 985]}
REF_Y = {"s36": [988, 985, 994, 993, 994, 995, 992, 984, 987, 984, 993, 981],
         "s38": [988, 987, 980, 980, 991, 994, 991, 994, 988, 991, 1001, 992],
         "s39": [988, 989, 987, 990, 990, 988, 991, 983, 985, 988, 983, 986],
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
    runs_seen = 0
    for tag in ("c2", "hi", "tw", "c8"):
        b, wm, dd, runs = ARMS[tag]
        for r in runs:
            fn = os.path.join(src, "run-%s-r%d.txt" % (tag, r))
            cells, verifies, samples = load(fn)
            data[(win, tag, r)] = (cells, verifies, samples)
            runs_seen += 1
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
    win_info[win] = (runs_seen, vmis, counts_ok, knob_ok, fail_ok, cmap_ok)

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
# pooled-75 cell medians: np.partition kth=37 FIRST, cross-checked
# against pure-Python sorted()[37] (XC_MED).
# ------------------------------------------------------------------
XC_MED = [0, 0]


def pooled(win, tag, idx, runs):
    xs = []
    for r in runs:
        xs += tbl_of(win, tag, r)[idx]
    assert len(xs) == 75
    arr = np.asarray(xs, dtype=np.int64)
    npx = int(np.partition(arr, 37)[37])
    py = sorted(xs)[37]
    XC_MED[0] += 1
    if py != npx:
        XC_MED[1] += 1
    return npx


def block_vals(win, tag, runs):
    return [pooled(win, tag, k, runs) for k in ok_cells]


# ------------------------------------------------------------------
# pair spreads over the block's pooled 75: np.partition kth=(a,b)
# FIRST, cross-checked in-loop against pure-Python sorted() (XC_D),
# for every window, block and pair (8 TS half-pairs + 4 DL pairs +
# 2 s78 validity pairs).
# ------------------------------------------------------------------
XC_D = [0, 0]


def pair_d_checked(vals75, a, b):
    npp = np.partition(np.asarray(vals75, dtype=np.int64), (a, b))
    npx = int(npp[b] - npp[a])
    py = sorted(vals75)[b] - sorted(vals75)[a]
    XC_D[0] += 1
    if py != npx:
        XC_D[1] += 1
    return npx


def named_pooled75(win):
    rows = []
    for i in range(12):
        xs = []
        for r in (3 * i + 1, 3 * i + 2, 3 * i + 3):
            xs += tbl_of(win, "tw", r)[nc]
        assert len(xs) == 75
        rows.append(xs)
    return rows


pooled75 = {win: named_pooled75(win) for win, _d in WINDOWS}

ALL_TS = [(n, k, a, b) for (n, k, a, b) in TS]
ALL_FULL = [("DL4", 33, 41), ("DL8", 29, 45), ("DL16", 21, 53), ("DL32", 5, 69)] + \
           [(t, a, b) for (t, a, b, _v, _w) in VALID]

ts_tab = {}       # (pair, win) -> (2*L, [12 block values])
for name, _k, a, b in ALL_TS:
    for win, _d in WINDOWS:
        d = [pair_d_checked(pooled75[win][i], a, b) for i in range(12)]
        ts_tab[(name, win)] = d

dl_tab = {}       # (DL name, win) -> [12 block D]
for name, a, b in ALL_FULL:
    for win, _d in WINDOWS:
        dl_tab[(name, win)] = [pair_d_checked(pooled75[win][i], a, b) for i in range(12)]

# the DL half decomposition identity (240 checks)
decomp_bad = 0
for _k, ln, rn, dn, _da, _db in FAMILIES:
    for win, _d in WINDOWS:
        for i in range(12):
            if ts_tab[(ln, win)][i] + ts_tab[(rn, win)][i] != dl_tab[(dn, win)][i]:
                decomp_bad += 1
decomp_ok = (decomp_bad == 0)

# ------------------------------------------------------------------
# 2*L level statistics: np.partition kth=(5,6) FIRST, cross-checked
# against sorted()[5]+[6] (XC_L2).
# ------------------------------------------------------------------
XC_L2 = [0, 0]


def l2_checked(d12):
    npp = np.partition(np.asarray(d12, dtype=np.int64), (5, 6))
    npx = int(npp[5] + npp[6])
    py = sorted(d12)[5] + sorted(d12)[6]
    XC_L2[0] += 1
    if py != npx:
        XC_L2[1] += 1
    return npx


l2 = {}     # (name, win) -> 2*L
for name, _k, _a, _b in ALL_TS:
    for win, _d in WINDOWS:
        l2[(name, win)] = l2_checked(ts_tab[(name, win)])
for name, _a, _b in ALL_FULL:
    for win, _d in WINDOWS:
        l2[(name, win)] = l2_checked(dl_tab[(name, win)])

# ------------------------------------------------------------------
# C1, block-min vectors, anchor reproduction rows
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
# validity pins (published s78/s82 vectors at the named cell)
# ------------------------------------------------------------------
valid_rows = []
valid_ok = True
for label, a, b, ref_vec, ref_w5d in VALID:
    got_vec = [l2[(label, w)] for w, _d in WINDOWS]
    got_w5d = dl_tab[(label, NEW_WIN)]
    ok = (got_vec == ref_vec) and (got_w5d == ref_w5d)
    valid_rows.append((label, got_vec, got_w5d, ref_vec, ref_w5d, ok))
    if not ok:
        valid_ok = False


def invalidated():
    inv = any(v[1] != 0 or not v[2] or not v[3] or not v[4] or not v[5]
              for v in win_info.values())
    return inv or (not named_ok) or (not vec_ok) or (not c1_ok) or (not anchor_ok) \
        or (not valid_ok) or (not decomp_ok)


# ------------------------------------------------------------------
# independent publication reader (find/split, no regex)
# ------------------------------------------------------------------
pub_text = open(PUB).read()
pub_lines = pub_text.split("\n")


def norm(s):
    return " ".join(s.split())


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


def find_wrapped(prefix, n):
    hits = [i for i, l in enumerate(pub_lines) if l.startswith(prefix)]
    assert len(hits) == 1, (prefix, len(hits))
    return " ".join(pub_lines[hits[0]:hits[0] + n])


rows = []


def rec(label, published, census):
    rows.append((label, str(published), str(census)))


# ---- section 1: integrity ----
for win, _d in WINDOWS:
    runs_seen, vmis, cok, kok, fok, mok = win_info[win]
    rec("sec1 %s integrity" % win,
        find_line("   %s: runs parsed " % win),
        ("   %s: runs parsed %d; VERIFY mismatch total %d; counts ok %s; "
         "knobs ok %s; S=8 fail-closed %s; cell map ok %s"
         % (win, runs_seen, vmis, cok, kok, fok, mok)))
rec("sec1 named cell position",
    find_line("   named cell present as ok-map cell "),
    ("   named cell present as ok-map cell %d (raw idx %d == %s): %s"
     % (nc_pos, nc, ckey_str(nc), named_ok)))
rec("sec1 decomposition identity (whitespace-normalized)",
    norm(find_wrapped("   DL decomposition identity", 2)),
    norm("   DL decomposition identity HL_k+HR_k = D_k per block (all 4"
         " families x 5 windows x 12 blocks = 240 checks): %s"
         % ("EXACT everywhere" if decomp_ok else "VIOLATED")))

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
    X, Y = vec[win]
    rec("sec3 %s X (hi)" % win,
        find_line("   %s X (hi): " % win),
        "   %s X (hi): %s" % (win, " ".join(str(v) for v in X)))
    rec("sec3 %s Y (tw)" % win,
        find_line("   %s Y (tw): " % win),
        "   %s Y (tw): %s" % (win, " ".join(str(v) for v in Y)))
    if win != NEW_WIN:
        rec("sec3 %s reproduction EXACT" % win,
            find_line("   %s reproduction EXACT: " % win),
            "   %s reproduction EXACT: %s"
            % (win, X == REF_X[win] and Y == REF_Y[win]))
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
for (label, got_vec, got_w5d, ref_vec, ref_w5d, ok), (plabel, _a, _b, _rv, _rw) in \
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

# ---- section 5: the T19 table ----
rec("sec5 named cell identity",
    find_line("   the NAMED cell "),
    "   the NAMED cell %s of the tw arm; block = 3 consecutive tw" % ckey_str(nc))
for name, k, a, b in TS:
    label = TS_LABEL[name]
    vals = [l2[(name, w)] for w, _d in WINDOWS]
    rec("sec5 %s vector" % name,
        find_line_with("   %s: 2*L " % label, "(L "),
        ("   %s: 2*L s36/s38/s39/s51/s73 = %s (L %s)"
         % (label, "/".join(str(v) for v in vals),
            "/".join(fmt_ht(v) for v in vals))))
    rec("sec5 %s W5 block values" % name,
        find_line("   %s W5 block values: " % label),
        ("   %s W5 block values: %s"
         % (label, " ".join(str(v) for v in ts_tab[(name, NEW_WIN)]))))
    band3 = sorted(l2[(name, w)] for w in ("s38", "s39", "s51"))
    l2_w5 = l2[(name, NEW_WIN)]
    if l2_w5 < band3[0]:
        verdict = "OUTSIDE-BELOW"
    elif l2_w5 > band3[1]:
        verdict = "OUTSIDE-ABOVE"
    else:
        verdict = "INSIDE"
    tag = ""
    if k in NARROW:
        tag = "  [UNINFORMATIVE-BY-S86-CAVEAT: span %d sits in the narrow-span noise band]" % k
    rec("sec5 %s band (PUBLISHED min..median convention)" % name,
        find_line("   %s W5-vs-post-shift-band: " % label),
        ("   %s W5-vs-post-shift-band: 2*L_W5 = %d vs band 2*L %d..%d "
         "(closed interval [MIN,MAX] spanned by {s38,s39,s51}): %s%s"
         % (label, l2_w5, band3[0], band3[1], verdict, tag)))

# ---- section 5b: the four k families side by side ----
for k, ln, rn, dn, da, db in FAMILIES:
    lv = [l2[(ln, w)] for w, _d in WINDOWS]
    rv = [l2[(rn, w)] for w, _d in WINDOWS]
    dv = [l2[(dn, w)] for w, _d in WINDOWS]
    rec("sec5b k=%d %s level" % (k, ln),
        find_line("     k=%d (span %d): %s 2*L " % (k, k, TS_LABEL[ln])),
        "     k=%d (span %d): %s 2*L %s" % (k, k, TS_LABEL[ln], "/".join(str(v) for v in lv)))
    rec("sec5b k=%d %s level" % (k, rn),
        find_line("     k=%d (span %d): %s 2*L " % (k, k, TS_LABEL[rn])),
        "     k=%d (span %d): %s 2*L %s" % (k, k, TS_LABEL[rn], "/".join(str(v) for v in rv)))
    rec("sec5b k=%d R-L difference" % k,
        find_line("     k=%d (span %d): R-L level difference" % (k, k)),
        ("     k=%d (span %d): R-L level difference (descriptive) %s"
         % (k, k, "/".join(str(rv[i] - lv[i]) for i in range(5)))))
    rec("sec5b k=%d DL level" % k,
        find_line("     k=%d (span %d): 2*L %s " % (k, k, DL_LABEL[dn])),
        ("     k=%d (span %d): 2*L %s %s"
         % (k, k, DL_LABEL[dn], "/".join(str(v) for v in dv))))
    rec("sec5b k=%d sum-of-levels" % k,
        find_line("     k=%d (span %d): sum-of-levels" % (k, k)),
        ("     k=%d (span %d): sum-of-levels vs 2*L(D_k) %s -- levels do NOT add"
         % (k, k, " ".join("%d/%d" % (lv[i] + rv[i], dv[i]) for i in range(5)))))

# ---- section 6: verdict summary ----
rec("sec6 T19 verdict (whitespace-normalized)",
    norm(find_wrapped("   T19 table: ", 2)),
    norm("   T19 table: EVALUABLE, DESCRIPTIVE ONLY -- NO letter exists"
         " in this row (by frozen design).")
    if not invalidated() else
    norm("   T19 table: NOT EVALUABLE (an integrity/validity criterion"
         " of protocol section 3/4 is violated -- named above)."))
for name, k, a, b in TS:
    vals = [l2[(name, w)] for w, _d in WINDOWS]
    rec("sec6 %s summary" % name,
        find_line_without("   %s: 2*L " % TS_LABEL[name], "s36"),
        "   %s: 2*L %s" % (TS_LABEL[name], "/".join(str(v) for v in vals)))
rec("sec6 evaluable inputs (whitespace-normalized)",
    norm(find_wrapped("   evaluable inputs: ", 5)),
    norm("   evaluable inputs: prior vector reproduction EXACT (%s); prior"
         " anchor rows EXACT (%s); parser validity pins EXACT (%s);"
         " decomposition identity EXACT (%s);"
         " s73 C1 ((%s)); named cell identity %s (%s); per-window"
         " integrity rows in section 1."
         % (vec_ok, anchor_ok, valid_ok, decomp_ok,
            "a" if c1_ok else "b", ckey_str(nc), named_ok)))

# ------------------------------------------------------------------
# section B: the estimator cross-check census (counts)
# ------------------------------------------------------------------
hygiene = []


def hy(label, want, got):
    hygiene.append((label, str(want), str(got), str(want) == str(got)))


hy("pair-spread cross-check mismatches (np.partition kth=(a,b) vs pure-Python sorted())",
   0, XC_D[1])
hy("pooled-median cross-check mismatches (np.partition kth=37 vs sorted()[37])",
   0, XC_MED[1])
hy("2*L cross-check mismatches (np.partition kth=(5,6) vs sorted()[5]+[6])",
   0, XC_L2[1])
hy("decomposition identity block checks violated (HL_k+HR_k = D_k, 240 checks)",
   0, decomp_bad)

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
hy("ledger reading-line count (this row writes NO line)", 9, len(reading_lines))
s89_lines = [l for l in reading_lines if "session=s89" in l]
hy("ledger session=s89 line count", 0, len(s89_lines))

import hashlib
hy("publication-s87.txt bytes", PUB_BYTES, len(pub_text.encode("utf-8")))
hy("publication-s87.txt sha256", PUB_SHA256,
   hashlib.sha256(pub_text.encode("utf-8")).hexdigest())

# ------------------------------------------------------------------
# section D: band convention audit (the s83 precedent applied)
# ------------------------------------------------------------------
band_audit = []
for name, k, _a, _b in TS:
    label = TS_LABEL[name]
    triple = [l2[(name, w)] for w in ("s38", "s39", "s51")]
    s3 = sorted(triple)
    l2_w5 = l2[(name, NEW_WIN)]
    if l2_w5 < s3[0]:
        vp = "OUTSIDE-BELOW"
    elif l2_w5 > s3[1]:
        vp = "OUTSIDE-ABOVE"
    else:
        vp = "INSIDE"
    if l2_w5 < s3[0]:
        vm = "OUTSIDE-BELOW"
    elif l2_w5 > s3[2]:
        vm = "OUTSIDE-ABOVE"
    else:
        vm = "INSIDE"
    band_audit.append((name, k, label, triple, s3, l2_w5, vp, vm))

changed = [(n, k, lb) for (n, k, lb, _t, _s, _w, vp, vm) in band_audit if vp != vm]
tops_stated = sum(1 for (_n, _k, _lb, _t, s3, _w, _vp, _vm) in band_audit
                  if s3[1] != s3[2])
informative_changed = [t for t in changed if t[1] not in NARROW]

# ------------------------------------------------------------------
# report
# ------------------------------------------------------------------
out = []
P = out.append
P("JUN-59 session 89 -- the T19 derivation census")
P("(derivation-census-s87.py, the INDEPENDENT second parser for")
P("publication-s87.txt; the s87-frozen protocol.txt section 6")
P("implementation paths). Two-way rows: published =")
P("publication-s87.txt lines parsed find/split from the committed")
P("bytes, census = the same lines re-derived in full here from the")
P("390 committed run logs of the five fixed directories; NO")
P("in-memory state of analysis-s87.py is consulted. Split-based")
P("parsing, no re module (analysis-s87.py used regex); the")
P("observed half-pair/pair spreads, pooled-75 cell medians and 2*L")
P("statistics are computed on the numpy np.partition kth paths")
P("(analysis-s87.py is pure stdlib, imports NO numpy) and are")
P("cross-checked in-loop against pure-Python sorted() explicit")
P("order statistics (the algorithm family analysis-s87.py used).")
P("NO RNG anywhere, no clock.")
P("")
P("BAND CONVENTION NAMED, NOT HIDDEN (the s83 precedent): the")
P("published section-5 band lines print sorted[0]..sorted[1] of the")
P("three {s38,s39,s51} 2*L values and judge W5 against sorted[1]")
P("while BOTH the frozen protocol.txt section 5 AND the printed")
P("label name 'the closed interval [MIN,MAX] spanned by")
P("{s38,s39,s51}' -- with three values sorted[1] is the MEDIAN, so")
P("the printed interval is min..median, NOT min..MAX. The census")
P("reproduces the PUBLISHED (min..median) computation for")
P("byte-equality; SECTION D audits the frozen [MIN,MAX] convention")
P("separately and names every verdict that changes under it.")
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
P("computation: every named-cell block pair/half-pair spread of")
P("every window and block -- 5 windows x 12 blocks x 14 pairs = %d"
  % XC_D[0])
P("comparisons; every pooled-75 cell median; every 2*L):")
P("pair-spread cross-check: %d comparisons" % XC_D[0])
P("pooled-median cross-check: %d comparisons" % XC_MED[0])
P("2*L cross-check: %d comparisons" % XC_L2[0])
mismatched_b = 0
for label, want, got, match in hygiene[:4]:
    if not match:
        mismatched_b += 1
    P("%s: want [%s] got [%s] | match %s" % (label, want, got, match))
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
P("SECTION D -- band convention audit (the s83 precedent applied;")
P("the frozen protocol.txt section-5 convention is the closed")
P("interval [MIN,MAX] of {2*L_s38, 2*L_s39, 2*L_s51}):")
for name, k, label, triple, s3, l2_w5, vp, vm in band_audit:
    P("   %s: {s38,s39,s51} 2*L = %d/%d/%d -> published band %d..%d"
      % (label, triple[0], triple[1], triple[2], s3[0], s3[1]))
    P("   (min..median) vs protocol [MIN,MAX] %d..%d (min..MAX); W5 %d"
      % (s3[0], s3[2], l2_w5))
    P("   -> published verdict %s (judged vs printed top %d) | protocol"
      % (vp, s3[1]))
    P("   verdict %s (judged vs MAX %d) | %s"
      % (vm, s3[2], "INVARIANT" if vp == vm else "VERDICT CHANGED"))
P("interval tops understated (printed min..median vs protocol")
P("[MIN,MAX]): %d of 8" % tops_stated)
P("VERDICTS CHANGED under the frozen protocol convention: %d of 8"
  % len(changed))
for name, k, label in changed:
    P("   CHANGED: %s (span %d)%s" % (label, k,
      " -- UNINFORMATIVE-BY-S86-CAVEAT family" if k in NARROW else ""))
P("informative-family verdicts CHANGED (k=16/32): %d"
  % len(informative_changed))
P("NAMED NOT HIDDEN: analysis-s87.py prints band[0]..band[1] and")
P("judges l2_w5 vs band[1] while protocol.txt section 5 (and the")
P("printed label) freeze [MIN,MAX] -- the s82 min..median")
P("recurrence despite the named s83 correction. T19's five-window")
P("2*L vectors (the content any frozen row quotes as priors) are")
P("UNAFFECTED (the section 5/6 vector two-way rows are EXACT); the")
P("band subsection is descriptive, quoted by NO frozen row.")
P("")
P("TOTAL: 8 pairs audited, %d verdicts changed, %d informative"
  % (len(changed), len(informative_changed)))
P("")
P("DETERMINISM: this generator run twice yields byte-identical")
P("output (double-run status named in the s89 record; NO RNG, no")
P("set iteration).")

outpath = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "derivation-census-s87.txt")
open(outpath, "w").write("\n".join(out) + "\n")
print("TOTAL: %d rows, %d mismatched | B: %d | C: %d | D: %d of 8 verdicts changed"
      % (len(rows), mismatched, mismatched_b, mismatched_c, len(changed)))
sys.exit(0 if (mismatched + mismatched_b + mismatched_c) == 0 else 1)
