#!/usr/bin/env python3
"""JUN-59 session 79 -- THE SECOND-PAIR PROFILE AXIS (the s56
halving-rule pairs) AT THE W5 WINDOW -- ANALYSIS HALF
(analysis-s79.py; the s66-frozen protocol.txt of THIS directory,
sections 0/1/2/3/4/5/6 -- construction, inputs, resampling,
invalidation machinery, letters, the D-family and the route).

WHAT THIS IS (honest states): the IMPLEMENTED analysis half of the
s66 pre-registered T16 row (the freeze is
docs/evidence/gpu/anv-b3w5pair2profile-20261029/protocol.txt,
frozen 2026-10-28T20:38:43Z BEFORE any W5 run exists and before
ANY statistic of this probe was computed). It parses the
COMMITTED run logs only: NO hardware runs, NO builds, NO
compiles, NO GO stamp at this session (protocol section 5: NO
reading -> NO settle-bar-ledger line, NO day-slot consumption --
the analysis session never writes a ledger line).

THE ROW QUESTION (protocol section 0): at the NEW fifth window W5
does the tw arm's (max,128,S=default) cell's outer-weighted
compression profile at the SECOND named rank-pair set (the s56
halving-rule pairs OUTER2 (5,71) / INNER2 (33,43)) continue
across the UTC-day boundary -- the difference-in-differences
2*P2_obs = 2*C_out2 - 2*C_in2 in the pre-registered direction
P2_obs > 0 (the OUTER2 spread level drops MORE from s36 to W5
than the INNER2 spread level)? ONE named cell, ONE named window
pair (s36 vs W5), ONE named direction, ONE named statistic.

Frozen implementation paths (protocol section 0/6): numpy 2.5.4 --
int64 np.sort over the pooled 75 (D_out2 = sorted[..., 70] -
sorted[..., 4]; D_in2 = sorted[..., 42] - sorted[..., 32];
np.sort for the 6th+7th sums); the resampling in vectorized
TRIAL BATCHES (batch size a memory detail, NOT part of the
frozen contract) with the frozen RNG call order -- ONE
random.Random(2026102816) (the s66 freeze seed; DISTINCT from
T7's 20261029, T14's 2026102814 and T15's 2026102815), the ONE
named probe consuming it: 20,000 trials; per trial ONE
rng.shuffle of a fresh list(range(72)) -- the ONLY RNG calls in
this probe; BOTH axes evaluated on the SAME shuffles (the s56
contract).

Deterministic: running this generator twice yields byte-identical
output (RNG seeded, no set iteration).
"""
import os, sys, random, statistics
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
GPU = os.path.join(ROOT, "docs", "evidence", "gpu")

SESSION = 79
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
SEED = 2026102816
COMMITTED_C8 = 32915
NAMED_CKEY = ("max", 128, "default")
AXES = ("out2", "in2")
AXE_LABEL = {"out2": "OUTER2 (5,71)", "in2": "INNER2 (33,43)"}
AXE_CNAME = {"out2": "2*C_out2", "in2": "2*C_in2"}

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
# s56 D1 second-pair levels of the named cell at s36/s38/s39/s51,
# 2*L half-tick units; NOT recomputed there -- recomputed HERE
# only as D1 descriptive content)
REF_QP_PRIOR = {"out2": [713, 606, 659, 612],
                "in2": [63, 54, 62, 56]}

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
# THE T16 CONSTRUCTION (protocol section 0): the named cell's block
# second-pair spreads over the tw arm; per block D over the block's
# pooled 75 gpu_ticks samples -- OUTER2 D = x_(71)-x_(5),
# INNER2 D = x_(43)-x_(33) (both exact INTEGER); per-axis L_w =
# median of the 12 block D values (2*L = 6th+7th order statistics,
# INTEGER half-tick); 2*C_out2 = 2*Lout2_s36 - 2*Lout2_W5;
# 2*C_in2 = 2*Lin2_s36 - 2*Lin2_W5; the PRIMARY STATISTIC
# 2*P2_obs = 2*C_out2 - 2*C_in2 (pre-registered direction
# P2_obs > 0).
# ------------------------------------------------------------------
def axis_d(pooled75, axis):
    """(...,75) int64 -> exact INTEGER block second-pair spread."""
    srt = np.sort(pooled75, axis=-1)
    if axis == "out2":
        return srt[..., 70] - srt[..., 4]
    return srt[..., 42] - srt[..., 32]

def named_block_d(win, axis):
    """(12,) int64 named-cell block second-pair spreads, tw arm."""
    rows = []
    for i in range(12):
        runs = [3 * i + 1, 3 * i + 2, 3 * i + 3]
        xs = []
        for r in runs:
            for s in data[(win, "tw", r)][2]:
                if s[1] == nc:
                    xs.append(s[2])
        rows.append(int(axis_d(np.asarray(xs, dtype=np.int64), axis)))
    return np.asarray(rows, dtype=np.int64)

dt = {}    # (win, axis) -> (12,) int64 named-cell block D values
l2 = {}    # (win, axis) -> 2*L int64
for win, _d in WINDOWS:
    for axis in AXES:
        tab = named_block_d(win, axis)
        dt[(win, axis)] = tab
        rs = np.sort(tab)
        l2[(win, axis)] = int(rs[5] + rs[6])   # 2*L, INTEGER half-tick

# ------------------------------------------------------------------
# THE RESAMPLING (protocol section 2): ONE random.Random(2026102816),
# the ONE named probe (the second-pair profile contrast, s36 vs W5);
# 20,000 trials; per trial ONE rng.shuffle of a fresh
# list(range(72)), split into pseudo-windows A then B of 36 in draw
# order, each into 12 blocks of 3 in draw order; both axes computed
# on the SAME pooled 75 of each pseudo-block; 2*L* per pseudo-window
# and axis = 6th+7th order statistics of the 12 block D values;
# 2*P2* = (2*Lout2*_A - 2*Lout2*_B) - (2*Lin2*_A - 2*Lin2*_B);
# p = (1 + count(P2* >= P2_obs)) / (1 + 20,000), ONE-SIDED in the
# pre-registered direction. All arithmetic exact INTEGER int64.
# ------------------------------------------------------------------
named_flat = np.vstack([run_arr("s36", "tw")[:, nc_pos, :],
                        run_arr(NEW_WIN, "tw")[:, nc_pos, :]])   # (72, 25)
rng = random.Random(SEED)

# observed per-axis 2*L and 2*C, and the primary 2*P2_obs
l2_s36 = {axis: l2[("s36", axis)] for axis in AXES}
l2_w5 = {axis: l2[(NEW_WIN, axis)] for axis in AXES}
c2_obs = {axis: l2_s36[axis] - l2_w5[axis] for axis in AXES}
p2_obs = c2_obs["out2"] - c2_obs["in2"]

perms = np.empty((TRIALS, 72), dtype=np.int64)
for t in range(TRIALS):
    perm = list(range(72))
    rng.shuffle(perm)
    perms[t] = perm
cnt = 0
for i in range(0, TRIALS, BATCH):
    batch = perms[i:i + BATCH].reshape(-1, 2, 12, 3)
    sub = named_flat[batch].reshape(-1, 2, 12, 75)      # (b, 2, 12, 75)
    srt = np.sort(sub, axis=-1)
    d_out2 = srt[..., 70] - srt[..., 4]                  # (b, 2, 12)
    d_in2 = srt[..., 42] - srt[..., 32]
    ds_o = np.sort(d_out2, axis=2)
    ds_i = np.sort(d_in2, axis=2)
    l2o = ds_o[:, :, 5] + ds_o[:, :, 6]                  # (b, 2)
    l2i = ds_i[:, :, 5] + ds_i[:, :, 6]
    p2 = (l2o[:, 0] - l2o[:, 1]) - (l2i[:, 0] - l2i[:, 1])
    cnt += int((p2 >= p2_obs).sum())
p = (1 + cnt) / (1 + TRIALS)

# ------------------------------------------------------------------
# THE LETTERS (protocol section 0)
# ------------------------------------------------------------------
def test_letter():
    if invalidated():
        return "(c) NOT EVALUABLE"
    if p <= 0.05:
        return "(a) SECONDPAIR-W5-OUTER-WEIGHTED-DIFFERENT"
    if p2_obs == 0:
        return "(b) NOT-DIFFERENT [EXACTLY-ZERO]"
    if p2_obs < 0:
        return "(b) NOT-DIFFERENT [OPPOSITE-DIRECTION]"
    return "(b) NOT-DIFFERENT [NONZERO-NOT-SIGNIFICANT]"

def t16_letter():
    if invalidated():
        return "(c) NOT EVALUABLE"
    if p <= 0.05:
        return "(a) SECONDPAIR-PROFILE-W5-OUTER-WEIGHTED-CONSISTENT"
    if p2_obs == 0:
        return "(b) NOT-SECONDPAIR-PROFILE-W5-OUTER-WEIGHTED-CONSISTENT [EXACTLY-ZERO]"
    if p2_obs < 0:
        return "(b) NOT-SECONDPAIR-PROFILE-W5-OUTER-WEIGHTED-CONSISTENT [OPPOSITE-DIRECTION]"
    return "(b) NOT-SECONDPAIR-PROFILE-W5-OUTER-WEIGHTED-CONSISTENT [NONZERO-NOT-SIGNIFICANT]"

def axis_line(axis):
    return ("%s: 2*L_s36 = %d (%s); 2*L_s73 = %d (%s); %s = %d (%s)"
            % (AXE_LABEL[axis], l2_s36[axis], fmt_ht(l2_s36[axis]),
               l2_w5[axis], fmt_ht(l2_w5[axis]),
               AXE_CNAME[axis], c2_obs[axis], fmt_ht(c2_obs[axis])))

def p2_line():
    return ("2*P2_obs = 2*C_out2 - 2*C_in2 = %d (P2_obs = %s); count %d / %d; "
            "p = %.6f; test letter %s"
            % (p2_obs, fmt_ht(p2_obs), cnt, TRIALS + 1, p, test_letter()))

def qp_vector_line(axis):
    vals = [l2[(w, axis)] for w, _d in WINDOWS]
    return ("%s: 2*L s36/s38/s39/s51/s73 = %s (L %s)"
            % (AXE_LABEL[axis],
               "/".join(str(v) for v in vals),
               "/".join(fmt_ht(v) for v in vals)))

def qp_blockd_line(axis):
    return ("%s W5 block D values: %s"
            % (AXE_LABEL[axis],
               " ".join(str(int(v)) for v in dt[(NEW_WIN, axis)])))

def qp_band_line(axis):
    l2_w5_v = l2[(NEW_WIN, axis)]
    band = sorted(l2[(w, axis)] for w in ("s38", "s39", "s51"))
    if l2_w5_v < band[0]:
        verdict = "OUTSIDE-BELOW"
    elif l2_w5_v > band[1]:
        verdict = "OUTSIDE-ABOVE"
    else:
        verdict = "INSIDE"
    return ("%s W5-vs-post-shift-band: 2*L_W5 = %d vs band 2*L %d..%d "
            "(closed interval spanned by {s38,s39,s51}): %s"
            % (AXE_LABEL[axis], l2_w5_v, band[0], band[1], verdict))

def qp_prior_line(axis):
    recomputed = [l2[(w, axis)] for w in ("s36", "s38", "s39", "s51")]
    return ("%s prior-window reproduction vs quote-only s56 D1 priors "
            "2*L %s: EXACT %s"
            % (AXE_LABEL[axis],
               "/".join(str(v) for v in REF_QP_PRIOR[axis]),
               recomputed == REF_QP_PRIOR[axis]))

def qp_contrast_line(axis):
    return ("%s directional contrast at (s36, W5): 2*L %d -> %d; %s = %d (%s)"
            % (AXE_LABEL[axis], l2_s36[axis], l2_w5[axis],
               AXE_CNAME[axis], c2_obs[axis], fmt_ht(c2_obs[axis])))

def sec6_axis_line(axis):
    return ("%s: 2*L_s36 %d -> 2*L_s73 %d (%s %d)"
            % (AXE_LABEL[axis], l2_s36[axis], l2_w5[axis],
               AXE_CNAME[axis], c2_obs[axis]))

def sec6_p2_line():
    return ("2*P2_obs = %d (P2_obs = %s); count %d/%d; p %.6f; test letter %s"
            % (p2_obs, fmt_ht(p2_obs), cnt, TRIALS + 1, p, test_letter()))

# ==================================================================
# the publication
# ==================================================================
out = []
P = out.append
P("JUN-59 session 79 -- THE SECOND-PAIR PROFILE AXIS (the s56")
P("halving-rule pairs OUTER2 (5,71) / INNER2 (33,43)) AT THE W5")
P("WINDOW (publication)")
P("(at the NEW fifth window W5 -- the campaign's first window on a")
P("UTC day other than 2026-10-28 -- does the tw arm's")
P("(max,128,S=default) cell's outer-weighted compression profile")
P("at the SECOND named rank-pair set continue across the UTC-day")
P("boundary? ONE named cell, ONE named window pair (s36 vs W5),")
P("ONE named direction (P2_obs > 0 -- the OUTER2 spread level")
P("drops MORE from s36 to W5 than the INNER2 spread level), ONE")
P("named statistic (the difference-in-differences 2*P2_obs =")
P("2*C_out2 - 2*C_in2).")
P("Produced ONLY by analysis-s79.py over the COMMITTED run logs of")
P("five fixed evidence directories (anv-b3commonmode-20261028 =")
P("the s36 window, anv-b3joint3-20261028 = the s38 window,")
P("anv-b3joint4-20261028 = the s39 window, anv-b3levelrep-20261028")
P("= the s51 window, anv-b3w5xdayrep-20261029 = the W5 window,")
P("measured by s73); protocol.txt was frozen BEFORE any fifth-")
P("window run exists and before ANY statistic of this probe was")
P("computed (freeze stamp 2026-10-28T20:38:43Z). ANALYSIS session")
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
P("   3 EXACTLY (mismatch => (c)); no vector enters the T16")
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

P("4. T16 THE ROW QUESTION (frozen letters, protocol sections 0/2):")
P("   the NAMED cell %s of the tw arm; block = 3 consecutive tw runs" % ckey_str(nc))
P("   (runs 1..36 -> 12 blocks of 3); per-block D over the block's")
P("   pooled 75 gpu_ticks samples -- OUTER2 D = x_(71) - x_(5),")
P("   INNER2 D = x_(43) - x_(33) (both exact INTEGER); per-axis")
P("   L_w = median of the 12 block D values (2*L = 6th + 7th order")
P("   statistics, INTEGER half-tick); 2*C_out2 = 2*Lout2_s36 -")
P("   2*Lout2_W5; 2*C_in2 = 2*Lin2_s36 - 2*Lin2_W5; the PRIMARY")
P("   STATISTIC 2*P2_obs = 2*C_out2 - 2*C_in2 (the pre-registered")
P("   direction is P2_obs > 0). The two-window run-exchangeability")
P("   null (protocol section 0/2): the 72 tw runs (36 of s36 + 36")
P("   of W5) exchangeable; ONE probe, %d trials, seed %d (ONE" % (TRIALS, SEED))
P("   random.Random; per trial ONE rng.shuffle of a fresh")
P("   list(range(72)), split into pseudo-windows A then B of 36 in")
P("   draw order and 12 pseudo-blocks of 3 in draw order; BOTH")
P("   axes evaluated on the SAME shuffles); p = (1 + count")
P("   (P2* >= P2_obs)) / (1 + 20,000), ONE-SIDED:")
for axis in AXES:
    P("   " + axis_line(axis))
P("   " + p2_line())
P("   T16 = %s" % t16_letter())
P("   NAMED, NOT HIDDEN (frozen): the multiplicity claim is NARROW")
P("   -- ONE named cell, ONE named window pair, ONE named")
P("   direction, ONE named statistic (NO multiplicity correction")
P("   applied or needed), tested on NEW data (the W5 runs did not")
P("   exist at freeze time). The axes/cell/direction choice was")
P("   made from PUBLISHED s55 T5 (a) and the published s56")
P("   second-pair priors ALONE (QUOTE-ONLY); the earlier")
P("   exploration families STAY uncorrected and this row does NOT")
P("   retro-correct them. THE T6 PRIOR NAMED, NOT HIDDEN: T6's")
P("   published joint letter is (b) NOT-SECONDPAIR-PROFILE-OUTER-")
P("   WEIGHTED-CONSISTENT (QUOTE-ONLY: only the (s36,s38) contrast")
P("   cleared 0.05 -- 2*P2_obs 98/53/94, p 0.021849/0.193840/")
P("   0.055847 at s38/s39/s51) -- so this row is a SINGLE-CONTRAST")
P("   read of a profile axis whose three-contrast IUT failed on the")
P("   2026-10-28 windows; a T16 (a) is a single named test's letter")
P("   and NOT a repair of T6's (b), and a T16 (b) is CONSISTENT")
P("   WITH the s56-era power loss at this pair set AND EQUALLY")
P("   CONSISTENT WITH genuine non-replication of the outer-weighted")
P("   profile at the second pair set -- NEITHER reading names a")
P("   mechanism (thermal/scheduling/memory/driver state all")
P("   UNMEASURED) and NOT physical-vs-estimator-structure. THE")
P("   COMPOSITION STRUCTURE NAMED, NOT HIDDEN: P2 is a")
P("   DIFFERENCE-IN-DIFFERENCES, so a near-zero P2 can arise while")
P("   BOTH axis levels still move together -- the per-axis")
P("   directional contrasts 2*C_out2 and 2*C_in2 and the per-axis")
P("   levels are named and printed (section 5 D1, descriptive")
P("   only, NO letter) and visible under any T16 letter. THE")
P("   NOVELTY OF THIS ROW (named): the campaign's first")
P("   pre-registered read of the second-pair profile axis at a")
P("   window on another UTC day (the W5 second-pair levels were")
P("   never published or computed anywhere at freeze time). STILL")
P("   LOW POWER (n=2 windows, 12 blocks each, ONE host, ONE named")
P("   cell; a single (a) can also reflect any s36-specific or")
P("   W5-specific state); 20,000 trials (p resolution 1/20,001 ~=")
P("   5e-5); L2 observational ONLY; NO causal mechanism;")
P("   threshold-artifact-vs-representation STAYS UNRESOLVED under")
P("   any letter.")
P("")

P("5. SECONDARY NAMED DESCRIPTIVE CONTENT (protocol section 4;")
P("   NONE of it is the row question; NO letter under this freeze):")
P("   D1 the NAMED cell's five-window second-pair level vectors on")
P("   BOTH axes (2*L half-tick INTEGER; the 12 block D values at W5")
P("   printed for the census), the per-axis directional contrasts")
P("   at (s36, W5) and the W5-vs-post-shift-band consistency")
P("   (L_W5 vs the closed interval spanned by {L_s38, L_s39, L_s51})")
P("   per axis -- descriptive only:")
for axis in AXES:
    P("      " + qp_vector_line(axis))
    P("      " + qp_blockd_line(axis))
    P("      " + qp_band_line(axis))
    P("      " + qp_prior_line(axis))
    P("      " + qp_contrast_line(axis))
P("")

P("6. VERDICT SUMMARY:")
P("   T16 = %s" % t16_letter())
for axis in AXES:
    P("   " + sec6_axis_line(axis))
P("   " + sec6_p2_line())
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
