#!/usr/bin/env python3
"""JUN-59 session 77 -- THE S38-HI (sum,256,S=32) PER-CELL WANDER
REPLICATION PROBE AT THE W5 WINDOW'S HI ARM -- ANALYSIS HALF
(analysis-s77.py; the s64-frozen protocol.txt of THIS directory,
sections 0/1/2/3/4/5/6 -- construction, inputs, resampling,
invalidation machinery, letters, the D-family and the route).

WHAT THIS IS (honest states): the IMPLEMENTED analysis half of the
s64 pre-registered T14 row (the freeze is
docs/evidence/gpu/anv-b3w5hiwander-20261029/protocol.txt, frozen
2026-10-28T19:49:29Z BEFORE any W5 run exists). It parses the
COMMITTED run logs only: NO hardware runs, NO builds, NO compiles,
NO GO stamp at this session (protocol section 5: NO reading -> NO
settle-bar-ledger line, NO day-slot consumption -- the analysis
session never writes a ledger line).

THE ROW QUESTION (protocol section 0): at the NEW fifth window W5
does the NAMED cell (sum,256,S=32)'s per-cell within-window
block-level wander EXCEED the within-window run-repartition null
at the hi arm, replicating the s38-hi s45 (b) on pre-registered
NEW data? ONE named cell, ONE named (window, arm), ONE named
upper-tail test. THE LETTER SOURCE IS THE ONE NAMED-CELL TEST
ALONE (the s45-letter-construction max-T runs alongside as D2
DESCRIPTIVE ONLY and NEVER carries a letter under this freeze).

Frozen implementation paths (protocol section 6): numpy 2.5.4 --
np.median exact at the 38th order statistic for the pooled 75;
integer max/min reductions; the resampling in vectorized TRIAL
BATCHES (batch size a memory detail, NOT part of the frozen
contract) with the frozen RNG call order -- ONE
random.Random(2026102814) (the s64 freeze seed; DISTINCT from the
T7 probes' 20261029), per trial ONE rng.shuffle of a fresh
list(range(36)); the primary W*, the D1 per-cell marginals and
the D2 max-T are all computed from the SAME per-trial repartition
(NO additional RNG calls exist in this probe).

Deterministic: running this generator twice yields byte-identical
output (RNG seeded, no set iteration).
"""
import os, sys, random, statistics
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
GPU = os.path.join(ROOT, "docs", "evidence", "gpu")

SESSION = 77
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
SEED = 2026102814
COMMITTED_C8 = 32915
NAMED_CKEY = ("sum", 256, "32")
NAMED_OK_POS = 10          # protocol section 3: present as cell 10

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
# quote-only s45 priors (protocol section 1 / D3 -- NOT recomputed)
REF_S45_W = {"s38 hi": (84, 1082, 1166), "s36 hi": (43, 1108, 1151),
             "s39 hi": (38, 1105, 1143)}
REF_S45_P = {"s38 hi": 0.035348, "s36 hi": 0.764662, "s39 hi": 0.995500}

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
named_pos_ok = (nc_pos == NAMED_OK_POS and ckey_str(nc) == "(sum,256,S=32)")

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
    return inv or (not named_pos_ok) or (not vec_ok) or (not c1_ok) or (not anchor_ok)

# ------------------------------------------------------------------
# THE T14 CONSTRUCTION (protocol section 0): the named cell's 12
# block pooled medians at (W5, hi); W_obs = max - min (INTEGER)
# ------------------------------------------------------------------
def block_med_table(win, tag):
    """(12, 18) float64 exact-int block pooled medians (38th order stat)."""
    rows = []
    for i in range(12):
        runs = [3 * i + 1, 3 * i + 2, 3 * i + 3]
        xs = [[] for _ in ok_cells]
        for r in runs:
            for s in data[(win, tag, r)][2]:
                xs[cell_pos[s[1]]].append(s[2])
        pooled_t = np.array(xs, dtype=np.int64)            # (18, 75)
        rows.append(np.median(pooled_t, axis=1))           # (18,)
    return np.array(rows)                                  # (12, 18)

v_tab = block_med_table(NEW_WIN, "hi")                     # (12, 18)
v_named = [int(x) for x in v_tab[:, nc_pos]]               # 12 block medians
w_row = (v_tab.max(axis=0) - v_tab.min(axis=0)).astype(np.int64)   # (18,)
w_obs_row = w_row
W_obs = int(w_row[nc_pos])
m_obs = int(w_row.max())
m_cells = [ok_cells[i] for i in range(len(ok_cells)) if int(w_row[i]) == m_obs]

# ------------------------------------------------------------------
# THE RESAMPLING (protocol section 2): ONE random.Random(2026102814),
# 20,000 trials, per trial ONE rng.shuffle of a fresh list(range(36)),
# split into 12 blocks of 3 in draw order; the primary W*, the D1
# marginals and the D2 max-T from the SAME per-trial repartition
# ------------------------------------------------------------------
arr = run_arr(NEW_WIN, "hi")                               # (36, 18, 25)
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
    sub = arr[bperm]                                       # (B,12,3,18,25)
    pooled_t = sub.transpose(0, 1, 3, 2, 4).reshape(-1, 12, len(ok_cells), 75)
    v = np.median(pooled_t, axis=-1)                       # (B,12,18) exact
    w = (v.max(axis=1) - v.min(axis=1)).astype(np.int64)   # (B,18)
    named_w[i:i + BATCH] = w[:, nc_pos]
    primary_cnt += int((w[:, nc_pos] >= W_obs).sum())
    marg_cnt += (w >= w_obs_row[None, :]).sum(axis=0)
    maxt_cnt += int((w.max(axis=1) >= m_obs).sum())

p_val = lambda cnt: (1 + cnt) / (1 + TRIALS)
named_sorted = sorted(int(x) for x in named_w)
null_med = (named_sorted[TRIALS // 2 - 1] + named_sorted[TRIALS // 2]) / 2

# ------------------------------------------------------------------
# THE LETTERS (protocol section 0): ONE pre-registered test
# ------------------------------------------------------------------
def t14_letter():
    if invalidated():
        return "(c) NOT EVALUABLE"
    if p_val(primary_cnt) <= 0.05:
        return "(a) WANDER-EXCESS-REPLICATED"
    sub = ("W_AT-OR-BELOW-NULL-MEDIAN" if W_obs <= null_med
           else "ABOVE-NULL-MEDIAN-NOT-SIGNIFICANT")
    return "(b) NOT-REPLICATED [%s]" % sub

# ==================================================================
# the publication
# ==================================================================
out = []
P = out.append
P("JUN-59 session 77 -- THE S38-HI (sum,256,S=32) PER-CELL WANDER")
P("REPLICATION PROBE AT THE W5 WINDOW'S HI ARM (publication)")
P("(at the NEW fifth window W5 -- the campaign's first window on a")
P("UTC day other than 2026-10-28 -- does the NAMED cell")
P("(sum,256,S=32)'s per-cell within-window block-level wander")
P("EXCEED the within-window run-repartition null at the hi arm,")
P("replicating the s38-hi s45 (b) on pre-registered NEW data? ONE")
P("named cell, ONE named (window, arm), ONE named upper-tail test;")
P("the letter source is the ONE named-cell test alone -- the")
P("s45-letter-construction max-T runs alongside as D2 DESCRIPTIVE")
P("ONLY and NEVER carries a letter under this freeze.)")
P("Produced ONLY by analysis-s77.py over the COMMITTED run logs of")
P("five fixed evidence directories (anv-b3commonmode-20261028 =")
P("the s36 window, anv-b3joint3-20261028 = the s38 window,")
P("anv-b3joint4-20261028 = the s39 window, anv-b3levelrep-20261028")
P("= the s51 window, anv-b3w5xdayrep-20261029 = the W5 window,")
P("measured by s73); protocol.txt was frozen BEFORE any fifth-")
P("window run exists and before ANY statistic of this probe was")
P("computed (freeze stamp 2026-10-28T19:49:29Z). ANALYSIS session")
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
  % (NAMED_OK_POS, nc, ckey_str(nc), named_pos_ok))
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
P("   3 EXACTLY (mismatch => (c)); no vector enters the T14")
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

P("4. T14 THE ROW QUESTION (frozen letters, protocol sections 0/2):")
P("   the NAMED cell %s (ok-map cell %d) at the NAMED (window, arm)"
  % (ckey_str(nc), NAMED_OK_POS))
P("   (s73 W5, hi); V_b = the block's per-cell pooled median (the")
P("   exact 38th order statistic of the block's 75 samples;")
P("   INTEGER), block = 3 consecutive hi runs (runs 1..36 -> 12")
P("   blocks of 3):")
P("   V = %s" % " ".join(str(v) for v in v_named))
P("   W_obs = max V - min V = %d ticks" % W_obs)
P("   the null (protocol section 0/2): WITHIN-WINDOW RUN-")
P("   EXCHANGEABILITY of W5's 36 hi runs; %d trials, seed %d (ONE" % (TRIALS, SEED))
P("   random.Random, one shuffle of a fresh list(range(36)) per")
P("   trial; the D1/D2 statistics share the same repartition); per")
P("   trial W* = max_b V*_b - min_b V*_b over 12 pseudo-blocks of 3;")
P("   p = (1 + count(W* >= W_obs)) / (1 + %d), ONE-SIDED upper:" % TRIALS)
P("   count %d / %d; p = %.6f" % (primary_cnt, TRIALS + 1, p_val(primary_cnt)))
P("   null median of the 20,000 W* values = %.1f" % null_med)
P("   T14 = %s" % t14_letter())
P("   NAMED, NOT HIDDEN (frozen): the multiplicity claim is NARROW")
P("   -- ONE named cell, ONE named (window, arm), ONE named upper-")
P("   tail test at 0.05 on NEW data (the W5 runs did not exist at")
P("   freeze time); this IS the route named in the s57 carry-")
P("   forward from one uncorrected (b) to a letter that survives")
P("   multiplicity. The s45 (b) came from the max-T family-wise")
P("   probe at (s38, hi) whose cell identity was DATA-DEPENDENT and")
P("   whose probe was UNCORRECTED across the six s45 probes and")
P("   three windows; freezing the cell and (window, arm) BEFORE W5")
P("   exists removes the cell family and the probe family by pre-")
P("   registration. (a) would NOT name a mechanism")
P("   (thermal/scheduling/memory/driver state all UNMEASURED) and")
P("   NOT say whether the wander is physical or estimator")
P("   structure; STILL LOW POWER (n=12 blocks, ONE window, ONE")
P("   host, ONE cell; the wander is a tail-to-tail RANGE statistic,")
P("   NOT a scale estimate); a (b) is NOT evidence of no per-cell")
P("   structure; 20,000 trials (p resolution 1/20,001 ~= 5e-5); L2")
P("   observational ONLY; NO causal mechanism; threshold-artifact-")
P("   vs-representation STAYS UNRESOLVED under any letter.")
P("")

P("5. SECONDARY NAMED DESCRIPTIVE CONTENT (protocol section 4;")
P("   NONE of it is the row question; NO letter under this freeze):")
P("   D1 the 18-cell per-cell wander scoreboard at (s73, hi): per")
P("   ok cell its identity key (op, wg, S), W_c in ticks, and the")
P("   cell's MARGINAL resample count and p (count of trials with")
P("   W*_c >= W_obs_c over the same 20,000 trials -- the s45 D1")
P("   construction, UNCORRECTED across the 18 cells, descriptive")
P("   only):")
for ci, k in enumerate(ok_cells):
    P("      cell %s: W %d; count %d / %d; p = %.6f"
      % (ckey_str(k), int(w_row[ci]), int(marg_cnt[ci]), TRIALS + 1,
         p_val(int(marg_cnt[ci]))))
P("   D2 the max-T probe at (s73, hi): M_obs = max_c W_c, which")
P("   cell(s) achieve M_obs (ties named), family-wise")
P("   p = (1 + count(M* >= M_obs)) / (1 + %d) from the same frozen" % TRIALS)
P("   loop (M* = max_c W*_c per trial) -- the s45 letter")
P("   construction run at (s73, hi), DESCRIPTIVE ONLY under this")
P("   freeze (it NEVER carries a letter):")
P("      M_obs = %d (max cell(s) %s); count %d / %d; p = %.6f"
  % (m_obs, ", ".join(ckey_str(i) for i in m_cells), maxt_cnt,
     TRIALS + 1, p_val(maxt_cnt)))
P("   D3 the named cell's W at (s73, hi) beside its quote-only s45")
P("   prior W values and block pooled medians (NOT recomputed) and")
P("   its marginal p beside the quote-only s45 marginal p values:")
P("      W: s73 hi %d (V %d..%d) vs quote-only s45 priors "
  "s38 hi 84 (1082..1166) / s36 hi 43 (1108..1151) / "
  "s39 hi 38 (1105..1143)" % (W_obs, min(v_named), max(v_named)))
P("      marginal p: s73 hi %.6f vs quote-only s45 priors "
  "0.035348 / 0.764662 / 0.995500" % p_val(int(marg_cnt[nc_pos])))
P("")

P("6. VERDICT SUMMARY:")
P("   T14 = %s" % t14_letter())
P("   W_obs = %d; count %d/%d; p %.6f; null median %.1f"
  % (W_obs, primary_cnt, TRIALS + 1, p_val(primary_cnt), null_med))
P("   evaluable inputs: prior vector reproduction EXACT (%s); prior"
  % vec_ok)
P("   anchor rows EXACT (%s); s73 C1 ((%s)); named cell at ok-map"
  % (anchor_ok, "a" if c1_ok else "b"))
P("   cell %d (%s); per-window integrity rows in section 1."
  % (NAMED_OK_POS, named_pos_ok))
P("   ANALYSIS session: NO hardware runs -> NO reading -> NO")
P("   settle-bar-ledger line, NO day-slot consumption (protocol")
P("   section 5; settle-bar-ledger.txt byte-identical to HEAD).")
P("   Rule 4 binds: NOTHING MOVES; accelerator-targets defaults")
P("   remain provisional (:measured? false); NO vendor optimization")
P("   exists for Intel.")

open(os.path.join(HERE, "publication-s%d.txt" % SESSION), "w").write("\n".join(out) + "\n")
