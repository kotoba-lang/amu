#!/usr/bin/env python3
"""JUN-59 session 77 -- the T14 derivation census
(derivation-census-s77.py, the INDEPENDENT second parser for
publication-s77.txt; the s64-frozen protocol.txt section 6
implementation paths).

Independence contract (frozen):
- NO regex, NO re module. Run-log parsing is split()-based k=v
  tokenising; publication parsing is find/split-based.
- The OBSERVED block estimators are pure-Python sorted() order
  statistics over the explicitly pooled 75 (the block's per-cell
  pooled median = sorted(pooled75)[37], the exact 38th order
  statistic, an INTEGER), CROSS-CHECKED IN-LOOP against the
  np.partition kth=37 path (every observed block median is
  computed BOTH ways; the cross-check census is section B).
- The RESAMPLING's estimators use the np.partition kth=37 path,
  NOT np.median (analysis-s77.py used np.median -- a genuinely
  different computational path).
- The repartition resampling and the RNG call order are
  re-implemented here: ONE random.Random(2026102814), 20,000
  trials, per trial ONE rng.shuffle of a fresh list(range(36))
  (the ONLY RNG calls in this probe); the primary W*, the D1
  per-cell marginals and the D2 max-T are all computed from the
  SAME per-trial repartition; p = (1 + count) / (1 + 20000).

This script re-derives, from the 390 committed run logs of the five
fixed evidence directories (no in-memory state of analysis-s77.py is
consulted), every published integer, count, p value and letter of
publication-s77.txt, in two-way rows: published (parsed find/split
from the committed publication-s77.txt bytes) vs census (recomputed
here).

Deterministic: running it twice yields byte-identical output (RNG
seeded, no set iteration). Usage: derivation-census-s77.py
[OUTPUT-PATH] (default: derivation-census-s77.txt beside this
file). Env CENSUS_SMOKE=1 caps trials at 20 for plumbing checks
only -- its output is NEVER the committed census (the committed
double-run is env-free; smoke runs mismatch the RNG count/p rows
by construction).
"""
import os, sys, random, statistics
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
GPU = os.path.join(ROOT, "docs", "evidence", "gpu")
PUB = os.path.join(HERE, "publication-s77.txt")

SMOKE = os.environ.get("CENSUS_SMOKE") == "1"
TRIALS = 20 if SMOKE else 20000
BATCH = 25
SEED = 2026102814
COMMITTED_C8 = 32915
NAMED_CKEY = ("sum", 256, "32")
NAMED_OK_POS = 10
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
named_pos_ok = (nc_pos == NAMED_OK_POS and ckey_str(nc) == "(sum,256,S=32)")

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

def pooled(win, tag, idx, runs):
    xs = []
    for r in runs:
        xs += tbl_of(win, tag, r)[idx]
    return med(xs)

def block_vals(win, tag, runs):
    return [pooled(win, tag, k, runs) for k in ok_cells]

# ------------------------------------------------------------------
# observed estimators: pure-Python sorted() FIRST, cross-checked
# in-loop against the np.partition kth=37 path (section B census)
# ------------------------------------------------------------------
XC_BLK = [0, 0]   # [comparisons, mismatches]

def med_checked(vals75):
    s = sorted(vals75)
    py = s[37]
    npx = int(np.partition(np.asarray(vals75, dtype=np.int64), 37)[37])
    XC_BLK[0] += 1
    if py != npx:
        XC_BLK[1] += 1
    return py

# the observed (12, 18) block-median table at (W5, hi) -- every
# block x ok cell pooled median computed BOTH ways
v_tab = [[0] * len(ok_cells) for _ in range(12)]
for i in range(12):
    for ci in range(len(ok_cells)):
        vals = []
        for r in (3 * i + 1, 3 * i + 2, 3 * i + 3):
            vals += tbl_of(NEW_WIN, "hi", r)[ok_cells[ci]]
        v_tab[i][ci] = med_checked(vals)

v_named = [v_tab[i][nc_pos] for i in range(12)]
w_row = [max(v_tab[i][ci] for i in range(12)) -
         min(v_tab[i][ci] for i in range(12)) for ci in range(len(ok_cells))]
W_obs = w_row[nc_pos]
m_obs = max(w_row)
m_cells = [ok_cells[i] for i in range(len(ok_cells)) if w_row[i] == m_obs]

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
    X = [int(min(block_vals(win, "hi", [3 * i + 1, 3 * i + 2, 3 * i + 3]))) for i in range(12)]
    Y = [int(min(block_vals(win, "tw", [3 * i + 1, 3 * i + 2, 3 * i + 3]))) for i in range(12)]
    vec[win] = (X, Y)
    if win != NEW_WIN and (X != REF_X[win] or Y != REF_Y[win]):
        vec_ok = False

anchor_rows = {}
anchor_ok = True
for win, _d in WINDOWS:
    if win == NEW_WIN:
        continue
    a_med = int(pooled(win, "hi", sum128, [1, 2, 3]))
    bvals = [int(v) for v in block_vals(win, "hi", [1, 2, 3])]
    anchor_rows[win] = (a_med, min(bvals), max(bvals))
    if anchor_rows[win] != REF_ANCHOR[win]:
        anchor_ok = False

def invalidated():
    return any((v[0] != 0 or not v[1] or not v[2] or not v[3] or not v[4])
               for v in win_info.values()) or (not named_pos_ok) or (not vec_ok) \
        or (not c1_ok) or (not anchor_ok)

# ------------------------------------------------------------------
# the resampling: np.partition kth=37 path (NOT np.median), the
# repartition and RNG call order re-implemented
# ------------------------------------------------------------------
arr = np.zeros((36, len(ok_cells), 25), dtype=np.int64)
for ri in range(36):
    t = tbl_of(NEW_WIN, "hi", ri + 1)
    for k in ok_cells:
        arr[ri, cell_pos[k], :] = t[k]

rng = random.Random(SEED)
perms = np.empty((TRIALS, 36), dtype=np.int64)
for t in range(TRIALS):
    perm = list(range(36))
    rng.shuffle(perm)
    perms[t] = perm

named_w = np.empty(TRIALS, dtype=np.int64)
marg_cnt = np.zeros(len(ok_cells), dtype=np.int64)
primary_cnt = 0
maxt_cnt = 0
for i in range(0, TRIALS, BATCH):
    bperm = perms[i:i + BATCH].reshape(-1, 12, 3)
    sub = arr[bperm]
    pooled_t = sub.transpose(0, 1, 3, 2, 4).reshape(-1, 12, len(ok_cells), 75)
    v = np.partition(pooled_t, 37, axis=-1)[..., 37]        # (B,12,18) INTEGER
    w = v.max(axis=1) - v.min(axis=1)                       # (B,18)
    named_w[i:i + BATCH] = w[:, nc_pos]
    primary_cnt += int((w[:, nc_pos] >= W_obs).sum())
    marg_cnt += (w >= np.asarray(w_row, dtype=np.int64)[None, :]).sum(axis=0)
    maxt_cnt += int((w.max(axis=1) >= m_obs).sum())

p_val = lambda cnt: (1 + cnt) / (1 + TRIALS)
named_sorted = sorted(int(x) for x in named_w)
null_med = (named_sorted[TRIALS // 2 - 1] + named_sorted[TRIALS // 2]) / 2

def t14_letter():
    if invalidated():
        return "(c) NOT EVALUABLE"
    if p_val(primary_cnt) <= 0.05:
        return "(a) WANDER-EXCESS-REPLICATED"
    sub = ("W_AT-OR-BELOW-NULL-MEDIAN" if W_obs <= null_med
           else "ABOVE-NULL-MEDIAN-NOT-SIGNIFICANT")
    return "(b) NOT-REPLICATED [%s]" % sub

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
l = find_line("   named cell present as ok-map cell ")
rec("sec1 named cell position",
    l.split("named cell present as ")[1],
    "ok-map cell %d (raw idx %d == %s): %s" % (NAMED_OK_POS, nc, ckey_str(nc),
                                               named_pos_ok))

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

# ---- section 3b: anchor reproduction rows ----
for win, _d in WINDOWS:
    if win == NEW_WIN:
        continue
    l = find_line("    %s: median " % win)
    rec("sec3b %s anchor" % win,
        "%s %s %s" % (l.split("median ")[1].split(" ")[0],
                      l.split("min..max ")[1].split(" ")[0],
                      l.split("reproduction EXACT: ")[1]),
        "%d %d..%d %s" % (anchor_rows[win][0], anchor_rows[win][1],
                          anchor_rows[win][2],
                          anchor_rows[win] == REF_ANCHOR[win]))
rec("sec3b prior anchor reproduction",
    find_line("    all four prior windows reproduce EXACTLY: ").split("EXACTLY: ")[1],
    str(anchor_ok))

# ---- section 4: T14 the row question ----
rec("sec4 T14 V vector",
    find_line("   V = ").split("V = ")[1],
    " ".join(str(v) for v in v_named))
rec("sec4 T14 W_obs",
    find_line("   W_obs = max V - min V = ").split("= ")[2].split()[0],
    str(W_obs))
l = find_line("   count ")
rec("sec4 T14 count/p",
    "%s / %s; p = %s" % (l.split("count ")[1].split(" /")[0],
                         l.split("/ ")[1].split(";")[0],
                         l.split("p = ")[1]),
    "%d / %d; p = %.6f" % (primary_cnt, TRIALS + 1, p_val(primary_cnt)))
rec("sec4 T14 null median",
    find_line("   null median of the 20,000 W* values = ").split("= ")[1],
    "%.1f" % null_med)
rec("sec4 T14 letter",
    find_line("   T14 = ").split("T14 = ")[1],
    t14_letter())

# ---- section 5 D1 ----
for ci, k in enumerate(ok_cells):
    l = find_line("      cell %s: " % ckey_str(k))
    rest = l.split("%s: " % ckey_str(k), 1)[1]
    rec("sec5 D1 %s" % ckey_str(k),
        "%s %s %s %s" % (rest.split("W ")[1].split(";")[0],
                         rest.split("count ")[1].split(" /")[0],
                         rest.split("/ ")[1].split(";")[0],
                         rest.split("p = ")[1]),
        "%d %d %d %.6f" % (w_row[ci], int(marg_cnt[ci]), TRIALS + 1,
                           p_val(int(marg_cnt[ci]))))

# ---- section 6 D2 ----
l = find_line("      M_obs = ")
rec("sec6 D2 max-T",
    "%s %s %s %s" % (l.split("M_obs = ")[1].split(" ")[0],
                     l.split("(max cell(s) ")[1].split("); count")[0],
                     l.split("count ")[1].split(" /")[0],
                     l.split("p = ")[1]),
    "%d %s %d %.6f" % (m_obs, ", ".join(ckey_str(i) for i in m_cells),
                       maxt_cnt, p_val(maxt_cnt)))

# ---- section 7 D3 ----
l = find_line("      W: ")
rec("sec7 D3 W",
    "%s %s" % (l.split("s73 hi ")[1].split(" ")[0],
               l.split("V ")[1].split(")")[0]),
    "%d %d..%d" % (W_obs, min(v_named), max(v_named)))
l = find_line("      marginal p: ")
rec("sec7 D3 marginal p",
    l.split("s73 hi ")[1].split(" ")[0],
    "%.6f" % p_val(int(marg_cnt[nc_pos])))

# ---- section 8 verdict ----
rec("sec8 verdict T14",
    find_line("   T14 = ", 1).split("T14 = ")[1],
    t14_letter())
l = [x for x in pub_lines
     if x.startswith("   W_obs = ") and "; count " in x][0]
rec("sec8 verdict summary",
    "%s %s %s %s" % (l.split("W_obs = ")[1].split(";")[0],
                     l.split("count ")[1].split("/")[0],
                     l.split("p ")[1].split(";")[0],
                     l.split("null median ")[1]),
    "%d %d %.6f %.1f" % (W_obs, primary_cnt, p_val(primary_cnt), null_med))

# ------------------------------------------------------------------
# section B: the observed-estimator cross-check census (counts)
# ------------------------------------------------------------------
hygiene = []
def hy(label, want, got):
    hygiene.append((label, str(want), str(got), str(want) == str(got)))

hy("block-median cross-check mismatches (pure-Python sorted()[37] vs np.partition kth=37)",
   0, XC_BLK[1])

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
s77_lines = [l for l in reading_lines if "session=s77" in l]
hy("ledger session=s77 line count", 0, len(s77_lines))

# ------------------------------------------------------------------
# report
# ------------------------------------------------------------------
out = []
P = out.append
P("JUN-59 session 77 -- the T14 derivation census")
P("(derivation-census-s77.py, the INDEPENDENT second parser for")
P("publication-s77.txt; the s64-frozen protocol.txt section 6")
P("implementation paths). Two-way rows: published =")
P("publication-s77.txt parsed find/split from the committed bytes,")
P("census = recomputed here from the 390 committed run logs of the")
P("five fixed directories; NO in-memory state of analysis-s77.py is")
P("consulted. Split-based parsing, no re module; observed block")
P("estimators are pure-Python sorted() order statistics over the")
P("explicitly pooled 75 (sorted(pooled75)[37], the exact 38th")
P("order statistic) cross-checked in-loop against the np.partition")
P("kth=37 path; the resampling's estimators use the np.partition")
P("kth=37 path, NOT np.median (analysis-s77.py used np.median);")
P("the repartition resampling and the RNG call order are")
P("re-implemented: ONE random.Random(2026102814), %d trials, one" % TRIALS)
P("fresh-list rng.shuffle of list(range(36)) per trial; the primary")
P("W*, the D1 per-cell marginals and the D2 max-T from the SAME")
P("per-trial repartition.")
P("")
if SMOKE:
    P("!!! CENSUS_SMOKE PLUMBING RUN (TRIALS=20) -- NOT the committed")
    P("!!! census; the RNG count/p rows mismatch by construction.")
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
P("computation of every observed block pooled median):")
P("block-median cross-check: %d comparisons" % XC_BLK[0])
mismatched_b = 0
for label, want, got, match in hygiene[:1]:
    if not match:
        mismatched_b += 1
    P("%s: want [%s] got [%s] | match %s" % (label, want, got, match))
P("")
P("TOTAL: %d checks, %d mismatched" % (1, mismatched_b))
P("")
P("SECTION C -- evidence hygiene:")
mismatched_c = 0
for label, want, got, match in hygiene[1:]:
    if not match:
        mismatched_c += 1
    P("%s: want [%s] got [%s] | match %s" % (label, want, got, match))
P("")
P("TOTAL: %d checks, %d mismatched" % (len(hygiene) - 1, mismatched_c))
P("")
P("DETERMINISM: this generator run twice yields byte-identical")
P("output (double-run status named in the s77 record; RNG seeded,")
P("no set iteration).")

outpath = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "derivation-census-s77.txt")
open(outpath, "w").write("\n".join(out) + "\n")
print("TOTAL: %d rows, %d mismatched | B: %d | C: %d"
      % (len(rows), mismatched, mismatched_b, mismatched_c))
sys.exit(0 if (mismatched + mismatched_b + mismatched_c) == 0 else 1)
