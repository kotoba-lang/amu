#!/usr/bin/env python3
"""JUN-59 session 78 -- THE QUANTILE-PAIR LEVEL AXES (the s53/s54
named pairs) AT THE W5 WINDOW -- ANALYSIS HALF (analysis-s78.py; the
s65-frozen protocol.txt of THIS directory, sections 0/1/2/3/4/5/6 --
construction, inputs, resampling, invalidation machinery, letters,
the D-family and the route).

WHAT THIS IS (honest states): the IMPLEMENTED analysis half of the
s65 pre-registered T15 row (the freeze is
docs/evidence/gpu/anv-b3w5qpairevel-20261029/protocol.txt, frozen
2026-10-28T20:10:55Z BEFORE any W5 run exists and before ANY
statistic of this probe was computed). It parses the COMMITTED run
logs only: NO hardware runs, NO builds, NO compiles, NO GO stamp at
this session (protocol section 5: NO reading -> NO
settle-bar-ledger line, NO day-slot consumption -- the analysis
session never writes a ledger line).

THE ROW QUESTION (protocol section 0): at the NEW fifth window W5
does the tw arm's (max,128,S=default) cell's INNER-QUANTILE-PAIR
(28,48) and OUTER-QUANTILE-PAIR (9,67) spread LEVEL continue the
s36-to-post-shift movement on the two OTHER named quantile-pair
level axes (narrower at W5 than at s36 -- the pre-registered
direction C_obs > 0)? ONE named cell, ONE named window pair
(s36 vs W5), ONE named direction, TWO named axes under the
pre-registered INTERSECTION-UNION joint rule.

Frozen implementation paths (protocol section 0/6): numpy 2.5.4 --
int64 np.sort over the pooled 75 (inner D = sorted[...,47] -
sorted[...,27]; outer D = sorted[...,66] - sorted[...,8]; np.sort
for the 6th+7th sums); the resampling in vectorized TRIAL BATCHES
(batch size a memory detail, NOT part of the frozen contract) with
the frozen RNG call order -- ONE random.Random(2026102815) (the s65
freeze seed; DISTINCT from T7's 20261029 and T14's 2026102814),
consumed in the frozen probe order (1) INNER (28,48), (2) OUTER
(9,67); per probe 20,000 trials; per trial ONE rng.shuffle of a
fresh list(range(72)) -- the ONLY RNG calls in this probe.

Deterministic: running this generator twice yields byte-identical
output (RNG seeded, no set iteration).
"""
import os, sys, random, statistics
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
GPU = os.path.join(ROOT, "docs", "evidence", "gpu")

SESSION = 78
NEW_WIN = "s73"   # the W5 window tag of the xdayrep row (its run logs)
WINDOWS = [("s36", "anv-b3commonmode-20261028"),
           ("s38", "anv-b3joint3-20261028"),
           ("s39", "anv-b3joint4-20261028"),
           ("s51", "anv-b3levelrep-20261028"),
           (NEW_WIN, "anv-b3w5xdayrep-20261029")]
ARMS = {"c2": (2, 1, 1, [1, 2, 3]),
        "hi": (3, 1024, 4033, list(range(1, 37))),
        "tw": (3, 2048, 8066, list(range(1, 37))),
        "c8": (8, 1, 1, [1, 2, 3])}
TRIALS = 20000
BATCH = 50
SEED = 2026102815
COMMITTED_C8 = 32915
NAMED_CKEY = ("max", 128, "default")
AXES = ("inner", "outer")
AXE_LABEL = {"inner": "INNER (28,48)", "outer": "OUTER (9,67)"}

# frozen reference vectors / anchors (publication-s39.txt section 3
# for s36/s38/s39; publication-s51.txt section 3 for s51)
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
# QUOTE-ONLY level priors (protocol section 1 -- the published
# s53 D1 inner / s54 D1 outer quantile-pair levels of the named
# cell at s36/s38/s39/s51, 2*L half-tick units; NOT recomputed
# there -- recomputed HERE only as D1 descriptive content)
REF_QP_PRIOR = {"inner": [118, 102, 128, 113],
                "outer": [496, 429, 437, 446]}

import re
cell_re = re.compile(
    r"^CELL idx=(\d+) spv=(\S+) op=(\S+) wg=(\d+) forced=(\S+) probe_size=(-?\d+) "
    r"probe_nsub=(-?\d+) probe_wg=(-?\d+) pipeline=(\S+) void=(\d)")
verify_re = re.compile(r"^VERIFY idx=(\d+) checked=(\d+) mismatch=(\d+) ok=(\d)")
sample_re = re.compile(
    r"^SAMPLE round=(\d+) idx=(\d+) batch=(\d+) work_mul=(\d+) ndiv=(\d+) gpu_ticks=(\d+) "
    r"gpu_ns=([\d.]+) per_dispatch_ns=([\d.]+) host_ns=(\d+)")

def load(path):
    cells, verifies, samples = {}, [], []
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("CELL "):
            m = cell_re.match(line)
            assert m, line
            cells[int(m.group(1))] = dict(op=m.group(3), wg=int(m.group(4)),
                                          forced=m.group(5), pipeline=m.group(9),
                                          void=m.group(10))
        elif line.startswith("VERIFY "):
            m = verify_re.match(line)
            assert m, line
            verifies.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
        elif line.startswith("SAMPLE "):
            m = sample_re.match(line)
            assert m, line
            samples.append((int(m.group(1)), int(m.group(2)), int(m.group(6)),
                            int(m.group(9)), (int(m.group(3)), int(m.group(4)), int(m.group(5)))))
    return cells, verifies, samples

def fmt_ht(x2):
    return "%.1f" % (x2 / 2)

# ------------------------------------------------------------------
# parse the five windows; integrity per protocol section 3
# ------------------------------------------------------------------
data = {}
win_info = {}
ref_cellmap = None
for win, dirname in WINDOWS:
    src = os.path.join(GPU, dirname)
    vmis = 0
    counts_ok = knob_ok = fail_ok = cmap_ok = True
    problems = []
    for tag in ("c2", "hi", "tw", "c8"):
        b, wm, dd, runs = ARMS[tag]
        for r in runs:
            fn = os.path.join(src, "run-%s-r%d.txt" % (tag, r))
            cells, verifies, samples = load(fn)
            data[(win, tag, r)] = (cells, verifies, samples)
            for (_i, _c, mis) in verifies:
                vmis += mis
            okc = [k for k, v in cells.items() if v["pipeline"] == "ok"]
            s8 = [k for k, v in cells.items() if v["forced"] == "8"]
            if len(s8) != 6 or any(cells[k]["pipeline"] != "FAIL" or cells[k]["void"] != "1"
                                   for k in s8):
                fail_ok = False
                problems.append("S=8 fail-closed violation in %s" % fn)
            if len(samples) != 450 or len(verifies) != 24:
                counts_ok = False
                problems.append("SAMPLE/VERIFY count mismatch in %s" % fn)
            for (_rnd, _idx, _gt, _hn, knobs) in samples:
                if knobs != (b, wm, dd):
                    knob_ok = False
                    problems.append("knob mismatch in %s" % fn)
            cmap = tuple(sorted((k, v["op"], v["wg"], v["forced"], v["pipeline"], v["void"])
                                for k, v in cells.items()))
            if ref_cellmap is None:
                ref_cellmap = cmap
            elif cmap != ref_cellmap:
                cmap_ok = False
                problems.append("cell map mismatch in %s" % fn)
    win_info[win] = dict(vmis=vmis, counts_ok=counts_ok, knob_ok=knob_ok,
                         fail_ok=fail_ok, cmap_ok=cmap_ok, problems=problems)

ok_cells = sorted([k for k, v in data[(WINDOWS[0][0], "c2", 1)][0].items()
                   if v["pipeline"] == "ok"])
cell_pos = {k: i for i, k in enumerate(ok_cells)}

def ckey(idx):
    c = data[(WINDOWS[0][0], "c2", 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])

def ckey_str(idx):
    op, wg, s = ckey(idx)
    return "(%s,%d,S=%s)" % (op, wg, s)

sum128 = [k for k in ok_cells if ckey(k) == ("sum", 128, "16")][0]
nc = [k for k in ok_cells if ckey(k) == NAMED_CKEY][0]
nc_pos = cell_pos[nc]
named_ok = (ckey_str(nc) == "(max,128,S=default)")   # section-0 named cell identity

def pooled(win, tag, idx, runs):
    xs = []
    for r in runs:
        xs += [s[2] for s in data[(win, tag, r)][2] if s[1] == idx]
    return float(np.median(np.asarray(xs, dtype=np.int64)))

def block_vals(win, tag, runs):
    return [pooled(win, tag, k, runs) for k in ok_cells]

def run_arr(win, tag):
    arr = np.zeros((36, len(ok_cells), 25), dtype=np.int64)
    for ri in range(36):
        tbl = {k: [] for k in ok_cells}
        for (_rnd, idx, gt, _hn, _kn) in data[(win, tag, ri + 1)][2]:
            tbl[idx].append(gt)
        for k in ok_cells:
            assert len(tbl[k]) == 25
            arr[ri, cell_pos[k], :] = tbl[k]
    return arr

# ------------------------------------------------------------------
# C1, block-min vectors, anchor reproduction rows (section 3)
# ------------------------------------------------------------------
c2_vals = block_vals(NEW_WIN, "c2", ARMS["c2"][3])
c2_cls = "FLOOR" if all(v <= 100 for v in c2_vals) else (
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
        continue   # this row computes NO anchor at W5 (protocol section 3)
    a_med = int(pooled(win, "hi", sum128, [1, 2, 3]))
    bvals = [int(v) for v in block_vals(win, "hi", [1, 2, 3])]
    anchor_rows[win] = (a_med, min(bvals), max(bvals))
    if anchor_rows[win] != REF_ANCHOR[win]:
        anchor_ok = False

def invalidated():
    inv = any(win_info[w]["vmis"] != 0 or not win_info[w]["counts_ok"]
              or not win_info[w]["knob_ok"] or not win_info[w]["fail_ok"]
              or not win_info[w]["cmap_ok"] for w, _d in WINDOWS)
    return inv or (not named_ok) or (not vec_ok) or (not c1_ok) or (not anchor_ok)

# ------------------------------------------------------------------
# THE T15 CONSTRUCTION (protocol section 0): the named cell's block
# quantile-pair spreads over the tw arm; per block D over the
# block's pooled 75 gpu_ticks samples -- inner D = x_(48)-x_(28),
# outer D = x_(67)-x_(9) (both exact INTEGER); L_w = median of the
# 12 block D values (2*L = 6th+7th order statistics, INTEGER
# half-tick); 2*C_obs = 2*L_s36 - 2*L_W5 (pre-registered direction
# C_obs > 0 -- NARROWER at W5).
# ------------------------------------------------------------------
def axis_d(pooled75, axis):
    """(...,75) int64 -> exact INTEGER block quantile-pair spread."""
    srt = np.sort(pooled75, axis=-1)
    if axis == "inner":
        return srt[..., 47] - srt[..., 27]
    return srt[..., 66] - srt[..., 8]

def d_tab(win, axis):
    """(12, 18) int64 block quantile-pair spreads, tw arm, all ok cells."""
    rows = []
    for i in range(12):
        runs = [3 * i + 1, 3 * i + 2, 3 * i + 3]
        xs = [[] for _ in ok_cells]
        for r in runs:
            for s in data[(win, "tw", r)][2]:
                xs[cell_pos[s[1]]].append(s[2])
        pooled_t = np.array(xs, dtype=np.int64)            # (18, 75)
        rows.append(axis_d(pooled_t, axis))                # (18,)
    return np.array(rows)                                  # (12, 18)

dt = {}
l2_tab = {}
for win, _d in WINDOWS:
    for axis in AXES:
        tab = d_tab(win, axis)
        dt[(win, axis)] = tab
        rs = np.sort(tab, axis=0)
        l2_tab[(win, axis)] = (rs[5] + rs[6]).astype(np.int64)   # (18,)

def l2_named(win, axis):
    return int(l2_tab[(win, axis)][nc_pos])

# ------------------------------------------------------------------
# THE RESAMPLING (protocol section 2): ONE random.Random(2026102815),
# consumed in the frozen probe order INNER then OUTER; per probe
# 20,000 trials; per trial ONE rng.shuffle of a fresh
# list(range(72)), split into pseudo-windows A then B of 36 in draw
# order, each into 12 blocks of 3 in draw order; 2*L* per pseudo-
# window = 6th+7th order statistics of the 12 block D values;
# 2*C* = 2*L*_A - 2*L*_B; p = (1 + count(C* >= C_obs)) / (1 +
# 20,000), ONE-SIDED in the pre-registered direction.
# ------------------------------------------------------------------
named_flat = np.vstack([run_arr("s36", "tw")[:, nc_pos, :],
                        run_arr(NEW_WIN, "tw")[:, nc_pos, :]])   # (72, 25)
rng = random.Random(SEED)

def probe(axis):
    obs = np.arange(72, dtype=np.int64).reshape(1, 2, 12, 3)
    sub = named_flat[obs].reshape(1, 2, 12, 75)
    d_obs = axis_d(sub, axis)[0]                             # (2, 12)
    ds_obs = np.sort(d_obs, axis=1)
    l2_obs = (ds_obs[:, 5] + ds_obs[:, 6]).astype(np.int64)  # (2,)
    c2_obs = int(l2_obs[0] - l2_obs[1])                      # 2*C_obs
    perms = np.empty((TRIALS, 72), dtype=np.int64)
    for t in range(TRIALS):
        perm = list(range(72))
        rng.shuffle(perm)
        perms[t] = perm
    cnt = 0
    for i in range(0, TRIALS, BATCH):
        batch = perms[i:i + BATCH].reshape(-1, 2, 12, 3)
        sub = named_flat[batch].reshape(-1, 2, 12, 75)
        d = axis_d(sub, axis)                                # (b, 2, 12)
        ds = np.sort(d, axis=2)
        l2p = ds[:, :, 5] + ds[:, :, 6]                      # (b, 2)
        c2 = l2p[:, 0] - l2p[:, 1]
        cnt += int((c2 >= c2_obs).sum())
    p = (1 + cnt) / (1 + TRIALS)
    return l2_obs, c2_obs, cnt, p

prim = {}
for axis in AXES:            # frozen probe order: INNER then OUTER
    prim[axis] = probe(axis)

# ------------------------------------------------------------------
# THE LETTERS (protocol section 0)
# ------------------------------------------------------------------
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
    return ("%s: 2*L_s36 = %d (%s); 2*L_s73 = %d (%s); 2*C_obs = %d "
            "(C_obs = %s); count %d / %d; p = %.6f; axis letter %s"
            % (AXE_LABEL[axis], int(l2_obs[0]), fmt_ht(int(l2_obs[0])),
               int(l2_obs[1]), fmt_ht(int(l2_obs[1])), c2_obs, fmt_ht(c2_obs),
               cnt, TRIALS + 1, p, axis_letter(axis)))

def qp_vector_line(axis):
    vals = [l2_named(w, axis) for w, _d in WINDOWS]
    return ("%s: 2*L s36/s38/s39/s51/s73 = %s (L %s)"
            % (AXE_LABEL[axis],
               "/".join(str(v) for v in vals),
               "/".join(fmt_ht(v) for v in vals)))

def qp_blockd_line(axis):
    return ("%s W5 block D values: %s"
            % (AXE_LABEL[axis],
               " ".join(str(int(v)) for v in dt[(NEW_WIN, axis)][:, nc_pos])))

def qp_band_line(axis):
    l2_w5 = l2_named(NEW_WIN, axis)
    band = sorted(l2_named(w, axis) for w in ("s38", "s39", "s51"))
    if l2_w5 < band[0]:
        verdict = "OUTSIDE-BELOW"
    elif l2_w5 > band[1]:
        verdict = "OUTSIDE-ABOVE"
    else:
        verdict = "INSIDE"
    return ("%s W5-vs-post-shift-band: 2*L_W5 = %d vs band 2*L %d..%d "
            "(closed interval spanned by {s38,s39,s51}): %s"
            % (AXE_LABEL[axis], l2_w5, band[0], band[1], verdict))

def qp_prior_line(axis):
    recomputed = [l2_named(w, axis) for w in ("s36", "s38", "s39", "s51")]
    return ("%s prior-window reproduction vs quote-only s53/s54 priors "
            "2*L %s: EXACT %s"
            % (AXE_LABEL[axis],
               "/".join(str(v) for v in REF_QP_PRIOR[axis]),
               recomputed == REF_QP_PRIOR[axis]))

def d2_score_line(k):
    return ("scoreboard cell %s: INNER 2*L_W5 = %d (%s); OUTER 2*L_W5 = %d (%s)"
            % (ckey_str(k),
               l2_tab[(NEW_WIN, "inner")][cell_pos[k]],
               fmt_ht(int(l2_tab[(NEW_WIN, "inner")][cell_pos[k]])),
               l2_tab[(NEW_WIN, "outer")][cell_pos[k]],
               fmt_ht(int(l2_tab[(NEW_WIN, "outer")][cell_pos[k]]))))

def d2_contrast_line(k):
    ci = cell_pos[k]
    parts = []
    for axis in AXES:
        a = int(l2_tab[("s36", axis)][ci])
        b = int(l2_tab[(NEW_WIN, axis)][ci])
        parts.append("%s 2*L %d/%d C %s" % (AXE_LABEL[axis], a, b, fmt_ht(a - b)))
    return "contrast cell %s: %s" % (ckey_str(k), "; ".join(parts))

# ==================================================================
# the publication
# ==================================================================
out = []
P = out.append
P("JUN-59 session 78 -- THE QUANTILE-PAIR LEVEL AXES (the s53/s54")
P("named pairs) AT THE W5 WINDOW (publication)")
P("(at the NEW fifth window W5 -- the campaign's first window on a")
P("UTC day other than 2026-10-28 -- does the tw arm's")
P("(max,128,S=default) cell's INNER-QUANTILE-PAIR (28,48) and")
P("OUTER-QUANTILE-PAIR (9,67) spread LEVEL continue the s36-to-")
P("post-shift movement on the two OTHER named quantile-pair level")
P("axes? ONE named cell, ONE named window pair (s36 vs W5), ONE")
P("named direction (C_obs > 0 -- NARROWER at W5), TWO named axes")
P("under the pre-registered INTERSECTION-UNION joint rule.")
P("Produced ONLY by analysis-s78.py over the COMMITTED run logs of")
P("five fixed evidence directories (anv-b3commonmode-20261028 =")
P("the s36 window, anv-b3joint3-20261028 = the s38 window,")
P("anv-b3joint4-20261028 = the s39 window, anv-b3levelrep-20261028")
P("= the s51 window, anv-b3w5xdayrep-20261029 = the W5 window,")
P("measured by s73); protocol.txt was frozen BEFORE any fifth-")
P("window run exists and before ANY statistic of this probe was")
P("computed (freeze stamp 2026-10-28T20:10:55Z). ANALYSIS session")
P("-- NO hardware runs this session; the W5 quantities were")
P("MEASURED on aiueos-6600hs Intel BMG G31 ANV in session 73.")
P("")

P("1. INTEGRITY (computed over each window's committed logs;")
P("   protocol section 3):")
for win, _d in WINDOWS:
    info = win_info[win]
    P("   %s: runs parsed 78; VERIFY mismatch total %d; counts ok %s; "
      "knobs ok %s; S=8 fail-closed %s; cell map ok %s"
      % (win, info["vmis"], info["counts_ok"], info["knob_ok"],
         info["fail_ok"], info["cmap_ok"]))
    for pr in info["problems"]:
        P("   !! %s" % pr)
P("   named cell present as ok-map cell %d (raw idx %d == %s): %s"
  % (nc_pos, nc, ckey_str(nc), named_ok))
P("   INVALIDATION criterion (protocol section 3): any violation =>")
P("   letter (c).")
P("")

P("2. C1 RE-DERIVATION (environment pin, from the s73 W5 window's")
P("   logs):")
P("   c2 class: %s (FLOOR required; committed floor band 31..32)" % c2_cls)
P("   c8 (sum,128,S=16) pooled median %.0f vs committed %d "
  "(%.2f%% delta; +/-5%% required)" % (c8_m, COMMITTED_C8,
                                      abs(c8_m - COMMITTED_C8) / COMMITTED_C8 * 100))
P("   C1 branch: %s" % ("(a) both controls replicate" if c1_ok else "(b) discrepancy"))
P("")

P("3. THE BLOCK-MIN VECTORS (re-derived from the committed logs;")
P("   the four PRIOR windows reproduce the published vectors of")
P("   publication-s39.txt section 3 and publication-s51.txt section")
P("   3 EXACTLY (mismatch => (c)); no vector enters the T15")
P("   statistic -- the row question is section 4):")
for win, _d in WINDOWS:
    X, Y = vec[win]
    P("   %s X (hi): %s" % (win, " ".join(str(v) for v in X)))
    P("   %s Y (tw): %s" % (win, " ".join(str(v) for v in Y)))
    if win != NEW_WIN:
        P("   %s reproduction EXACT: %s" % (win, X == REF_X[win] and Y == REF_Y[win]))
P("   all four prior windows reproduce EXACTLY (8/8): %s" % vec_ok)
P("")

P("3b. ANCHOR REPRODUCTION ROWS (hi block A's (sum,128,S=16) pooled")
P("    median and 18-cell min..max at the four PRIOR windows vs the")
P("    quote-only/published anchor priors, EXACTLY (mismatch =>")
P("    (c)); this row computes NO anchor at W5 -- the W5 anchor is")
P("    the anv-b3w5xdayrep-20261029 row's D4):")
for win, _d in WINDOWS:
    if win == NEW_WIN:
        continue
    a_med, a_min, a_max = anchor_rows[win]
    P("    %s: median %d min..max %d..%d (want %d / %d..%d); "
      "reproduction EXACT: %s" % (win, a_med, a_min, a_max,
                                  REF_ANCHOR[win][0], REF_ANCHOR[win][1],
                                  REF_ANCHOR[win][2],
                                  (a_med, a_min, a_max) == REF_ANCHOR[win]))
P("    all four prior windows reproduce EXACTLY: %s" % anchor_ok)
P("")

P("4. T15 THE ROW QUESTION (frozen letters, protocol sections 0/2):")
P("   the NAMED cell %s of the tw arm; block = 3 consecutive tw runs" % ckey_str(nc))
P("   (runs 1..36 -> 12 blocks of 3); per-block D over the block's")
P("   pooled 75 gpu_ticks samples -- inner D = x_(48) - x_(28),")
P("   outer D = x_(67) - x_(9) (both exact INTEGER); L_w = median")
P("   of the 12 block D values (2*L = 6th + 7th order statistics,")
P("   INTEGER half-tick); 2*C_obs = 2*L_s36 - 2*L_W5 (the pre-")
P("   registered direction is C_obs > 0 -- the spread level is")
P("   NARROWER at W5 than at s36). The two-window run-exchangeability")
P("   null (protocol section 0/2): the 72 tw runs (36 of s36 + 36 of")
P("   W5) exchangeable; per probe %d trials, seed %d (ONE" % (TRIALS, SEED))
P("   random.Random, consumed in the frozen probe order INNER then")
P("   OUTER; per trial ONE rng.shuffle of a fresh list(range(72)),")
P("   split into pseudo-windows A then B of 36 in draw order and 12")
P("   pseudo-blocks of 3 in draw order); p = (1 + count(C* >= C_obs))")
P("   / (1 + 20,000), ONE-SIDED:")
for axis in AXES:
    P("   " + axis_line(axis))
P("   T15 = %s" % t15_letter())
P("   NAMED, NOT HIDDEN (frozen): the multiplicity claim is NARROW")
P("   -- ONE named cell, ONE named window pair, ONE named direction,")
P("   TWO named axes under a pre-registered IUT joint rule (both")
P("   axes (a) at 0.05 controls the joint type-I error at 0.05; NO")
P("   multiplicity correction applied or needed), tested on NEW")
P("   data (the W5 runs did not exist at freeze time). The axes/")
P("   cell/direction choice was made from PUBLISHED s53/s54 and")
P("   frozen-scale content ALONE (QUOTE-ONLY priors); the earlier")
P("   exploration families STAY uncorrected and this row does NOT")
P("   retro-correct them. THE AXIS-ASYMMETRY NAMED, NOT HIDDEN: the")
P("   outer level dropped at every post-shift window (s54 T4 (a))")
P("   while the inner level scattered (s53 T3 (b)), so the joint")
P("   (a) is DEMANDING on the inner axis; a joint (b) driven by the")
P("   inner axis is CONSISTENT WITH the s53-era scatter of the")
P("   narrow inner pair near its noise floor AND EQUALLY CONSISTENT")
P("   WITH genuine non-replication at the inner pair -- the per-")
P("   axis letters are named, so the OUTER axis's W5 letter is")
P("   visible under any joint letter (section 4). (a) would NOT")
P("   name a mechanism (thermal/scheduling/memory/driver state all")
P("   UNMEASURED) and NOT say whether any level movement is")
P("   physical or estimator structure. STILL LOW POWER (n=2")
P("   windows, 12 blocks each; a single (a) can also reflect any")
P("   s36-specific or W5-specific state; ONE host; only the named")
P("   cell's within-block quantile-pair spread level on the two")
P("   named axes is tested); 20,000 trials per probe (p resolution")
P("   1/20,001 ~= 5e-5); L2 observational ONLY; NO causal")
P("   mechanism; threshold-artifact-vs-representation STAYS")
P("   UNRESOLVED under any letter.")
P("")

P("5. SECONDARY NAMED DESCRIPTIVE CONTENT (protocol section 4;")
P("   NONE of it is the row question; NO letter under this freeze):")
P("   D1 the NAMED cell's five-window quantile-pair level vectors on")
P("   BOTH axes (2*L half-tick INTEGER; the 12 block D values at W5")
P("   printed for the census) and the W5-vs-post-shift-band")
P("   consistency (L_W5 vs the closed interval spanned by {L_s38,")
P("   L_s39, L_s51}) per axis -- descriptive only:")
for axis in AXES:
    P("      " + qp_vector_line(axis))
    P("      " + qp_blockd_line(axis))
    P("      " + qp_band_line(axis))
    P("      " + qp_prior_line(axis))
P("   D2 the 18-cell scoreboard at W5 on both quantile-pair axes")
P("   (L_W5 per ok cell) and the full W5-vs-s36 per-cell contrast")
P("   table (all 18 cells x 2 axes: L_s36, L_W5, C; 36 descriptive")
P("   contrasts, UNCORRECTED for multiplicity, NO letter):")
for k in ok_cells:
    P("      " + d2_score_line(k))
for k in ok_cells:
    P("      " + d2_contrast_line(k))
P("")

P("6. VERDICT SUMMARY:")
P("   T15 = %s" % t15_letter())
for axis in AXES:
    l2_obs, c2_obs, cnt, p = prim[axis]
    P("   %s: 2*L_s36 %d -> 2*L_s73 %d (2*C_obs %d); count %d/%d; "
      "p %.6f; letter %s"
      % (AXE_LABEL[axis], int(l2_obs[0]), int(l2_obs[1]), c2_obs,
         cnt, TRIALS + 1, p, axis_letter(axis)))
P("   evaluable inputs: prior vector reproduction EXACT (%s); prior"
  % vec_ok)
P("   anchor rows EXACT (%s); s73 C1 ((%s)); named cell identity"
  % (anchor_ok, "a" if c1_ok else "b"))
P("   %s (%s); per-window integrity rows in section 1."
  % (ckey_str(nc), named_ok))
P("   ANALYSIS session: NO hardware runs -> NO reading -> NO")
P("   settle-bar-ledger line, NO day-slot consumption (protocol")
P("   section 5; settle-bar-ledger.txt byte-identical to HEAD).")
P("   Rule 4 binds: NOTHING MOVES; accelerator-targets defaults")
P("   remain provisional (:measured? false); NO vendor optimization")
P("   exists for Intel.")

open(os.path.join(HERE, "publication-s%d.txt" % SESSION), "w").write("\n".join(out) + "\n")
