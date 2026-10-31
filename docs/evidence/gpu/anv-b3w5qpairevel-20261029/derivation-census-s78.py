#!/usr/bin/env python3
"""JUN-59 session 78 -- the T15 derivation census
(derivation-census-s78.py, the INDEPENDENT second parser for
publication-s78.txt; the s65-frozen protocol.txt section 6
implementation paths).

Independence contract (frozen):
- NO regex, NO re module. Run-log parsing is split()-based k=v
  tokenising; publication parsing is find/split-based.
- The OBSERVED block estimators are pure-Python sorted() order
  statistics over the explicitly pooled 75 -- inner
  sorted(pooled75)[47] - sorted(pooled75)[27], outer
  sorted(pooled75)[66] - sorted(pooled75)[8] -- CROSS-CHECKED
  IN-LOOP against the np.partition kth paths (every observed block
  quantile-pair spread is computed BOTH ways; the cross-check
  census is section B).
- The RESAMPLING's estimators use the np.partition kth paths,
  NOT np.sort (analysis-s78.py used np.sort -- a genuinely
  different computational path): block D via np.partition
  kth=(27,47)/(8,66); the 12-value level medians via
  np.partition kth=(5,6).
- The 12-value observed level medians are sorted() explicit order
  statistics (sorted(ds)[5] + sorted(ds)[6]).
- The two-window repartition resampling and the RNG call order are
  re-implemented here: ONE random.Random(2026102815), consumed in
  the frozen probe order INNER then OUTER, 20,000 trials per
  probe, per trial ONE rng.shuffle of a fresh list(range(72)) (the
  ONLY RNG calls in this probe); p = (1 + count) / (1 + 20000).

This script re-derives, from the 390 committed run logs of the five
fixed evidence directories (no in-memory state of analysis-s78.py is
consulted), every published integer, count, p value and letter of
publication-s78.txt, in two-way rows: published (the committed
publication-s78.txt line, find/split located) vs census (the same
line re-derived here in full).

Deterministic: running it twice yields byte-identical output (RNG
seeded, no set iteration). Usage: derivation-census-s78.py
[OUTPUT-PATH] (default: derivation-census-s78.txt beside this
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
PUB = os.path.join(HERE, "publication-s78.txt")

SMOKE = os.environ.get("CENSUS_SMOKE") == "1"
TRIALS = 20 if SMOKE else 20000
BATCH = 25
SEED = 2026102815
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
AXES = ("inner", "outer")
AXE_LABEL = {"inner": "INNER (28,48)", "outer": "OUTER (9,67)"}
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
REF_QP_PRIOR = {"inner": [118, 102, 128, 113],
                "outer": [496, 429, 437, 446]}

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
# in-loop against the np.partition kth paths (section B census).
# Every observed block quantile-pair spread of every window, axis,
# block and ok cell is computed BOTH ways.
# ------------------------------------------------------------------
XC_BLK = [0, 0]   # [comparisons, mismatches]

def d_checked(vals75, axis):
    s = sorted(vals75)
    if axis == "inner":
        py = s[47] - s[27]
        npp = np.partition(np.asarray(vals75, dtype=np.int64), (27, 47))
        npx = int(npp[47] - npp[27])
    else:
        py = s[66] - s[8]
        npp = np.partition(np.asarray(vals75, dtype=np.int64), (8, 66))
        npx = int(npp[66] - npp[8])
    XC_BLK[0] += 1
    if py != npx:
        XC_BLK[1] += 1
    return py

dt = {}
l2_tab = {}
for win, _d in WINDOWS:
    for axis in AXES:
        tab = [[0] * len(ok_cells) for _ in range(12)]
        for i in range(12):
            for ci in range(len(ok_cells)):
                vals = []
                for r in (3 * i + 1, 3 * i + 2, 3 * i + 3):
                    vals += tbl_of(win, "tw", r)[ok_cells[ci]]
                tab[i][ci] = d_checked(vals, axis)
        dt[(win, axis)] = tab
        l2_tab[(win, axis)] = [sorted(tab[i][ci] for i in range(12))[5] +
                               sorted(tab[i][ci] for i in range(12))[6]
                               for ci in range(len(ok_cells))]

def l2_named(win, axis):
    return l2_tab[(win, axis)][nc_pos]

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
               for v in win_info.values()) or (not named_ok) or (not vec_ok) \
        or (not c1_ok) or (not anchor_ok)

# ------------------------------------------------------------------
# the resampling: np.partition kth paths (NOT np.sort), the
# two-window repartition and RNG call order re-implemented (ONE
# random.Random(2026102815), probe order INNER then OUTER, per
# trial one rng.shuffle of a fresh list(range(72)))
# ------------------------------------------------------------------
def axis_d_part(pooled75, axis):
    if axis == "inner":
        npp = np.partition(pooled75, (27, 47), axis=-1)
        return npp[..., 47] - npp[..., 27]
    npp = np.partition(pooled75, (8, 66), axis=-1)
    return npp[..., 66] - npp[..., 8]

named_flat = np.zeros((72, 25), dtype=np.int64)
for wi, win in (("s36", "s36"), (NEW_WIN, NEW_WIN)):
    base = 0 if win == "s36" else 36
    for ri in range(36):
        named_flat[base + ri, :] = tbl_of(win, "tw", ri + 1)[nc]

rng = random.Random(SEED)

def probe(axis):
    d_obs = [[0] * 12, [0] * 12]
    for w_i, win in ((0, "s36"), (1, NEW_WIN)):
        for i in range(12):
            d_obs[w_i][i] = dt[(win, axis)][i][nc_pos]
    l2_obs = [sorted(d_obs[w_i])[5] + sorted(d_obs[w_i])[6] for w_i in (0, 1)]
    c2_obs = l2_obs[0] - l2_obs[1]
    perms = np.empty((TRIALS, 72), dtype=np.int64)
    for t in range(TRIALS):
        perm = list(range(72))
        rng.shuffle(perm)
        perms[t] = perm
    cnt = 0
    for i in range(0, TRIALS, BATCH):
        batch = perms[i:i + BATCH].reshape(-1, 2, 12, 3)
        sub = named_flat[batch].reshape(-1, 2, 12, 75)
        d = axis_d_part(sub, axis)                            # (b, 2, 12)
        part = np.partition(d, (5, 6), axis=2)
        l2p = part[:, :, 5] + part[:, :, 6]                   # (b, 2)
        c2 = l2p[:, 0] - l2p[:, 1]
        cnt += int((c2 >= c2_obs).sum())
    p = (1 + cnt) / (1 + TRIALS)
    return l2_obs, c2_obs, cnt, p

prim = {}
for axis in AXES:            # frozen probe order: INNER then OUTER
    prim[axis] = probe(axis)

def axis_letter(axis):
    if invalidated():
        return "(c) NOT EVALUABLE"
    l2_obs, c2_obs, cnt, p = prim[axis]
    if c2_obs > 0 and p <= 0.05:
        return "(a) LEVEL-REPLICATED-CONTINUED"
    if c2_obs <= 0:
        return "(b) NOT-REPLICATED [DIRECTION-REVERSED]"
    return "(b) NOT-REPLICATED [DIRECTION-CONSISTENT-NOT-SIGNIFICANT]"

def t15_letter():
    if invalidated():
        return "(c) NOT EVALUABLE"
    la = {axis: axis_letter(axis) for axis in AXES}
    fails = [axis for axis in AXES if not la[axis].startswith("(a)")]
    if not fails:
        return "(a) QUANTILE-PAIR-CROSS-DAY-REPLICATED-ON-BOTH-AXES"
    named = "|".join("%s %s" % (AXE_LABEL[axis], la[axis]) for axis in fails)
    return "(b) NOT-CROSS-DAY-REPLICATED-ON-BOTH-AXES (named failing: %s)" % named

def axis_line(axis):
    l2_obs, c2_obs, cnt, p = prim[axis]
    return ("   %s: 2*L_s36 = %d (%s); 2*L_s73 = %d (%s); 2*C_obs = %d "
            "(C_obs = %s); count %d / %d; p = %.6f; axis letter %s"
            % (AXE_LABEL[axis], int(l2_obs[0]), fmt_ht(int(l2_obs[0])),
               int(l2_obs[1]), fmt_ht(int(l2_obs[1])), c2_obs, fmt_ht(c2_obs),
               cnt, TRIALS + 1, p, axis_letter(axis)))

def qp_vector_line(axis):
    vals = [l2_named(w, axis) for w, _d in WINDOWS]
    return ("      %s: 2*L s36/s38/s39/s51/s73 = %s (L %s)"
            % (AXE_LABEL[axis],
               "/".join(str(v) for v in vals),
               "/".join(fmt_ht(v) for v in vals)))

def qp_blockd_line(axis):
    return ("      %s W5 block D values: %s"
            % (AXE_LABEL[axis],
               " ".join(str(int(v)) for v in
                        [dt[(NEW_WIN, axis)][i][nc_pos] for i in range(12)])))

def qp_band_line(axis):
    l2_w5 = l2_named(NEW_WIN, axis)
    band = sorted(l2_named(w, axis) for w in ("s38", "s39", "s51"))
    if l2_w5 < band[0]:
        verdict = "OUTSIDE-BELOW"
    elif l2_w5 > band[1]:
        verdict = "OUTSIDE-ABOVE"
    else:
        verdict = "INSIDE"
    return ("      %s W5-vs-post-shift-band: 2*L_W5 = %d vs band 2*L %d..%d "
            "(closed interval spanned by {s38,s39,s51}): %s"
            % (AXE_LABEL[axis], l2_w5, band[0], band[1], verdict))

def qp_prior_line(axis):
    recomputed = [l2_named(w, axis) for w in ("s36", "s38", "s39", "s51")]
    return ("      %s prior-window reproduction vs quote-only s53/s54 priors "
            "2*L %s: EXACT %s"
            % (AXE_LABEL[axis],
               "/".join(str(v) for v in REF_QP_PRIOR[axis]),
               recomputed == REF_QP_PRIOR[axis]))

def d2_score_line(k):
    ci = cell_pos[k]
    return ("      scoreboard cell %s: INNER 2*L_W5 = %d (%s); OUTER 2*L_W5 = %d (%s)"
            % (ckey_str(k),
               l2_tab[(NEW_WIN, "inner")][ci],
               fmt_ht(l2_tab[(NEW_WIN, "inner")][ci]),
               l2_tab[(NEW_WIN, "outer")][ci],
               fmt_ht(l2_tab[(NEW_WIN, "outer")][ci])))

def d2_contrast_line(k):
    ci = cell_pos[k]
    parts = []
    for axis in AXES:
        a = l2_tab[("s36", axis)][ci]
        b = l2_tab[(NEW_WIN, axis)][ci]
        parts.append("%s 2*L %d/%d C %s" % (AXE_LABEL[axis], a, b, fmt_ht(a - b)))
    return "      contrast cell %s: %s" % (ckey_str(k), "; ".join(parts))

def sec6_axis_line(axis):
    l2_obs, c2_obs, cnt, p = prim[axis]
    return ("   %s: 2*L_s36 %d -> 2*L_s73 %d (2*C_obs %d); count %d/%d; "
            "p %.6f; letter %s"
            % (AXE_LABEL[axis], int(l2_obs[0]), int(l2_obs[1]), c2_obs,
               cnt, TRIALS + 1, p, axis_letter(axis)))

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

rows = []
def rec(label, published, census):
    rows.append((label, str(published), str(census)))

# ---- section 1: integrity ----
for win, _d in WINDOWS:
    vmis, cok, kok, fok, mok, nlogs = win_info[win]
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

# ---- section 4: T15 the row question ----
for axis in AXES:
    rec("sec4 T15 %s axis" % axis,
        find_line("   %s: 2*L_s36 = " % AXE_LABEL[axis]),
        axis_line(axis))
rec("sec4 T15 joint letter",
    find_line("   T15 = "),
    "   T15 = %s" % t15_letter())

# ---- section 5 D1 ----
for axis in AXES:
    rec("sec5 D1 %s vector" % axis,
        find_line("      %s: 2*L s36/s38/s39/s51/s73 = " % AXE_LABEL[axis]),
        qp_vector_line(axis))
    rec("sec5 D1 %s W5 block D" % axis,
        find_line("      %s W5 block D values: " % AXE_LABEL[axis]),
        qp_blockd_line(axis))
    rec("sec5 D1 %s band" % axis,
        find_line("      %s W5-vs-post-shift-band: " % AXE_LABEL[axis]),
        qp_band_line(axis))
    rec("sec5 D1 %s prior reproduction" % axis,
        find_line("      %s prior-window reproduction vs quote-only " % AXE_LABEL[axis]),
        qp_prior_line(axis))

# ---- section 5 D2 ----
for k in ok_cells:
    rec("sec5 D2 scoreboard %s" % ckey_str(k),
        find_line("      scoreboard cell %s: " % ckey_str(k)),
        d2_score_line(k))
for k in ok_cells:
    rec("sec5 D2 contrast %s" % ckey_str(k),
        find_line("      contrast cell %s: " % ckey_str(k)),
        d2_contrast_line(k))

# ---- section 6 verdict ----
rec("sec6 verdict T15",
    find_line("   T15 = ", 1),
    "   T15 = %s" % t15_letter())
for axis in AXES:
    rec("sec6 verdict %s" % axis,
        find_line_with("   %s: 2*L_s36 " % AXE_LABEL[axis], " -> "),
        sec6_axis_line(axis))

# ------------------------------------------------------------------
# section B: the observed-estimator cross-check census (counts)
# ------------------------------------------------------------------
hygiene = []
def hy(label, want, got):
    hygiene.append((label, str(want), str(got), str(want) == str(got)))

hy("block-D cross-check mismatches (pure-Python sorted() vs np.partition kth paths)",
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
s78_lines = [l for l in reading_lines if "session=s78" in l]
hy("ledger session=s78 line count", 0, len(s78_lines))

# ------------------------------------------------------------------
# report
# ------------------------------------------------------------------
out = []
P = out.append
P("JUN-59 session 78 -- the T15 derivation census")
P("(derivation-census-s78.py, the INDEPENDENT second parser for")
P("publication-s78.txt; the s65-frozen protocol.txt section 6")
P("implementation paths). Two-way rows: published =")
P("publication-s78.txt lines parsed find/split from the committed")
P("bytes, census = the same lines re-derived in full here from the")
P("390 committed run logs of the five fixed directories; NO")
P("in-memory state of analysis-s78.py is consulted. Split-based")
P("parsing, no re module; observed block quantile-pair spreads are")
P("pure-Python sorted() order statistics over the explicitly")
P("pooled 75 (inner sorted(pooled75)[47] - sorted(pooled75)[27],")
P("outer sorted(pooled75)[66] - sorted(pooled75)[8]) cross-checked")
P("in-loop against the np.partition kth paths; the resampling's")
P("estimators use the np.partition kth paths, NOT np.sort")
P("(analysis-s78.py used np.sort); the observed 12-value level")
P("medians via sorted() explicit order statistics, the resampling's")
P("via np.partition kth=(5,6); the two-window repartition")
P("resampling and the RNG call order are re-implemented: ONE")
P("random.Random(2026102815), consumed in the frozen probe order")
P("INNER then OUTER, %d trials per probe, one fresh-list" % TRIALS)
P("rng.shuffle of list(range(72)) per trial.")
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
P("computation of every observed block quantile-pair spread: 5")
P("windows x 2 axes x 12 blocks x %d ok cells):" % len(ok_cells))
P("block-D cross-check: %d comparisons" % XC_BLK[0])
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
P("output (double-run status named in the s78 record; RNG seeded,")
P("no set iteration).")

outpath = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "derivation-census-s78.txt")
open(outpath, "w").write("\n".join(out) + "\n")
print("TOTAL: %d rows, %d mismatched | B: %d | C: %d"
      % (len(rows), mismatched, mismatched_b, mismatched_c))
sys.exit(0 if (mismatched + mismatched_b + mismatched_c) == 0 else 1)
