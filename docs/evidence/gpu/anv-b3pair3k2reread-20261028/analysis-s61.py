#!/usr/bin/env python3
"""JUN-59 session 61 analysis -- THE K=2 INNER3 ROUNDING-VARIANT
T8 RE-READ WITH OUTER3 HELD (session 60's queue third named
candidate row: "the k=2 inner3 variant's T8 re-read with OUTER3
held (its inner axis is the retired step-4 IN4 axis) and any
non-ladder rank pairs (both ANALYSIS)" -- taken FIRST on the k=2
inner3 rounding-variant re-read; the non-ladder rank pairs stay
named candidate rows; over the SAME four windows s36/s38/s39/s51
of the named-cell robust-scale level campaign, ANALYSIS only --
does s58's joint T8 (a) letter survive when the third inner pair
sits at the s58-named ALTERNATIVE rounding k=2 (x_(36), x_(40))
instead of the frozen tie-break k=3 (x_(35), x_(41)), OUTER3
held at (x_(3), x_(73))?).

Route (frozen in protocol.txt section 6): this script parses ONLY
the committed run logs of the four fixed evidence directories and
writes publication-s61.txt in its own directory. Deterministic:
running it twice yields byte-identical output.

NAMED, NOT HIDDEN (protocol section 0): this probe is a RE-READ,
NOT a fresh pre-registered prediction -- both axes' per-window
levels are published priors (publication-s58 D1 OUTER3;
publication-s59 D1 INNER4 -- the k=2 inner pair IS exactly the
retired step-4 IN4 axis), so every observed statistic is a
deterministic recombination of published numbers and only the
permutation p values are new.

The primary statistic (named cell only): block = 3 consecutive
runs of the tw arm within one window (the s35/s36-frozen block
unit); per block over the pooled 75 samples BOTH D_out3 =
x_(73) - x_(3) (the s58 OUTER3 axis, HELD unchanged) and D_in3K2
= x_(40) - x_(36) (the s58-named k=2 alternative rounding of the
third inner pair -- identical to the s59 IN4 axis) -- exact
INTEGERs from the SAME pooled 75; per window per axis L = median
of the 12 block D values (2*L = 6th + 7th order statistics,
INTEGER half-tick units); per contrast 2*C_out3 = 2*Lout3_s36 -
2*Lout3_w, 2*C_in3K2 = 2*Lin3K2_s36 - 2*Lin3K2_w and the
difference-in-differences 2*P3K2_obs = 2*C_out3 - 2*C_in3K2 (the
pre-registered direction is P3K2 > 0 -- outer-weighted
compression at the variant pair set; NAMED, NOT HIDDEN: the
direction is fixed by s55's published T5 (a) reading and the s58
T8 framing, both QUOTE-ONLY, and its truth value is already
determined by the published components). THREE named contrasts:
(s36,s38), (s36,s39), (s36,s51). The resampling null (frozen):
per contrast the 72 tw runs of the two named windows
exchangeable; per trial one rng.shuffle of a fresh list(range(72))
split into two pseudo-windows of 36 and 12 pseudo-blocks of 3 in
draw order; D_out3 AND D_in3K2 computed on the SAME pseudo-blocks;
p = (1 + count(P3K2* >= P3K2_obs)) / (1 + 20,000), ONE-SIDED. One
random.Random(2026102811), consumed in the frozen probe order:
(s36,s38), (s36,s39), (s36,s51). numpy 2.5.4 (int64 np.sort) is
the frozen implementation path; the resampling is vectorized over
TRIAL BATCHES (batch size a memory detail, NOT part of the frozen
contract); every P3K2* >= P3K2_obs comparison is exact INTEGER
arithmetic. Joint T11 = the pre-registered INTERSECTION-UNION
rule (all three contrasts (a); NO multiplicity correction).
"""
import re, os, random, statistics
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
WINDOWS = [("s36", "anv-b3commonmode-20261028"),
           ("s38", "anv-b3joint3-20261028"),
           ("s39", "anv-b3joint4-20261028"),
           ("s51", "anv-b3levelrep-20261028")]
ARMS = {"c2": (2, 1, 1, [1, 2, 3]),
        "hi": (3, 1024, 4033, list(range(1, 37))),
        "tw": (3, 2048, 8066, list(range(1, 37))),
        "c8": (8, 1, 1, [1, 2, 3])}
TRIALS = 20000
SEED = 2026102811
BATCH = 50
COMMITTED_C8 = 32915
NAMED_CKEY = ("max", 128, "default")
PAIRS = [("s36", "s38"), ("s36", "s39"), ("s36", "s51")]
FREEZE = "2026-10-28T18:08:07Z"

# ---- quote-only frozen reference vectors ----
# ---- (publication-s39.txt section 3: s36/s38/s39 published + ----
# ---- quote-only; publication-s51.txt section 3: s51) ----
REF_X = {"s39": [986, 991, 984, 985, 989, 989, 986, 990, 995, 986, 987, 981],
         "s36": [991, 989, 981, 998, 993, 985, 984, 997, 994, 994, 980, 982],
         "s38": [992, 988, 984, 1007, 985, 984, 986, 983, 992, 991, 982, 997],
         "s51": [988, 986, 1000, 986, 989, 983, 995, 983, 994, 991, 984, 985]}
REF_Y = {"s39": [988, 989, 987, 990, 990, 988, 991, 983, 985, 988, 983, 986],
         "s36": [988, 985, 994, 993, 994, 995, 992, 984, 987, 984, 993, 981],
         "s38": [988, 987, 980, 980, 991, 994, 991, 994, 988, 991, 1001, 992],
         "s51": [980, 975, 991, 979, 986, 986, 992, 991, 988, 993, 995, 996]}
# ---- quote-only anchor priors (publication-s36/38/39 section D; ----
# ---- publication-s51.txt section 3b for s51) ----
REF_ANCHOR = {"s36": (1142, 991, 1438),
              "s38": (1132, 992, 1443),
              "s39": (1146, 986, 1432),
              "s51": (1137, 988, 1430)}
# ---- quote-only level priors (D2 context; MAD/IQR: ----
# ---- publication-s49/50/51 D1; CENTER: publication-s52 D1; ----
# ---- INNERPAIR: publication-s53 D1; OUTERPAIR: publication- ----
# ---- s54 D1; PROFILE (2*Lout - 2*Lin): publication-s55 D1; ----
# ---- SECONDPAIR2 OUT2/IN2/PROFILE2: publication-s56 D1; ----
# ---- THIRDPAIR3 OUT3/IN3/PROFILE3: publication-s58 D1; ----
# ---- FOURTHPAIR4 OUT4/IN4/PROFILE4: publication-s59 D1; ----
# ---- 2*L half-tick units; QUOTE-ONLY except OUTER3 and INNER4, ----
# ---- which this probe's D1 prior check RE-DERIVES against) ----
REF_SCALE = {"MAD": {"s36": 143, "s38": 111, "s39": 113, "s51": 118},
             "IQR": {"s36": 303, "s38": 241, "s39": 235, "s51": 240},
             "CENTER": {"s36": 2833, "s38": 2845, "s39": 2826, "s51": 2825},
             "INNERPAIR": {"s36": 118, "s38": 102, "s39": 128, "s51": 113},
             "OUTERPAIR": {"s36": 496, "s38": 429, "s39": 437, "s51": 446},
             "PROFILE": {"s36": 378, "s38": 327, "s39": 309, "s51": 333},
             "OUTER2": {"s36": 713, "s38": 606, "s39": 659, "s51": 612},
             "INNER2": {"s36": 63, "s38": 54, "s39": 62, "s51": 56},
             "PROFILE2": {"s36": 650, "s38": 552, "s39": 597, "s51": 556},
             "OUTER3": {"s36": 902, "s38": 721, "s39": 811, "s51": 776},
             "INNER3": {"s36": 36, "s38": 36, "s39": 37, "s51": 29},
             "PROFILE3": {"s36": 866, "s38": 685, "s39": 774, "s51": 747},
             "OUTER4": {"s36": 987, "s38": 846, "s39": 903, "s51": 895},
             "INNER4": {"s36": 19, "s38": 21, "s39": 24, "s51": 20},
             "PROFILE4": {"s36": 968, "s38": 825, "s39": 879, "s51": 875}}

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
            samples.append((int(m.group(1)), int(m.group(2)),
                            int(m.group(6)), int(m.group(9)),
                            (int(m.group(3)), int(m.group(4)), int(m.group(5)))))
    return cells, verifies, samples

def med(xs):
    return statistics.median(xs)

def fmt_ht(x2):
    return f"{x2 / 2:.1f}"

# ------------------------------------------------------------------
# parse the four windows; integrity per protocol section 4
# ------------------------------------------------------------------
data = {}
win_info = {}
ref_cellmap = None
for win, dirname in WINDOWS:
    src = os.path.join(ROOT, "docs", "evidence", "gpu", dirname)
    vmis = 0
    counts_ok = knob_ok = fail_ok = cmap_ok = True
    problems = []
    for tag in ("c2", "hi", "tw", "c8"):
        b, wm, dd, runs = ARMS[tag]
        for r in runs:
            fn = os.path.join(src, f"run-{tag}-r{r}.txt")
            cells, verifies, samples = load(fn)
            data[(win, tag, r)] = (cells, verifies, samples)
            for (_i, _c, mis) in verifies:
                vmis += mis
            okc = [k for k, v in cells.items() if v["pipeline"] == "ok"]
            s8 = [k for k, v in cells.items() if v["forced"] == "8"]
            if len(s8) != 6 or any(cells[k]["pipeline"] != "FAIL" or cells[k]["void"] != "1"
                                   for k in s8):
                fail_ok = False
                problems.append(f"S=8 fail-closed violation in {fn}")
            if len(samples) != len(okc) * 25 or len(verifies) != 24:
                counts_ok = False
                problems.append(f"sample/verify count mismatch in {fn}")
            for (_rnd, _idx, _gt, _hn, knobs) in samples:
                if knobs != (b, wm, dd):
                    knob_ok = False
                    problems.append(f"knob mismatch in {fn}")
            cmap = tuple(sorted((k, v["op"], v["wg"], v["forced"], v["pipeline"], v["void"])
                                for k, v in cells.items()))
            if ref_cellmap is None:
                ref_cellmap = cmap
            elif cmap != ref_cellmap:
                cmap_ok = False
                problems.append(f"cell map mismatch in {fn}")
    win_info[win] = dict(vmis=vmis, counts_ok=counts_ok, knob_ok=knob_ok,
                         fail_ok=fail_ok, cmap_ok=cmap_ok, problems=problems)

ok_cells = sorted([k for k, v in data[("s51", "c2", 1)][0].items() if v["pipeline"] == "ok"])
cell_pos = {k: i for i, k in enumerate(ok_cells)}

def ckey(idx):
    c = data[("s51", "c2", 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])

def ckey_str(idx):
    op, wg, s = ckey(idx)
    return f"({op},{wg},S={s})"

sum128 = [k for k in ok_cells if ckey(k) == ("sum", 128, "16")][0]
nc = [k for k in ok_cells if ckey(k) == NAMED_CKEY][0]
nc_pos = cell_pos[nc]

def pooled(win, tag, idx, runs, field):
    xs = []
    for r in runs:
        xs += [s[field] for s in data[(win, tag, r)][2] if s[1] == idx]
    return med(xs)

def block_vals(win, tag, runs):
    return [pooled(win, tag, k, runs, 2) for k in ok_cells]

def block_min(win, tag, runs):
    return min(block_vals(win, tag, runs))

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

def pair_ds(pooled75):
    """(...,75) int64 -> (D_out3, D_in3K2) exact INTEGER block spreads
    from the SAME sorted pooled 75: D_out3 = x_(73) - x_(3) (the s58
    OUTER3 axis, HELD), D_in3K2 = x_(40) - x_(36) (the s58-named k=2
    alternative rounding of the third inner pair -- identical to the
    retired step-4 IN4 axis of s59)."""
    srt = np.sort(pooled75, axis=-1)
    return srt[..., 72] - srt[..., 2], srt[..., 39] - srt[..., 35]

out = []
P = out.append
P("JUN-59 session 61 -- THE K=2 INNER3 ROUNDING-VARIANT T8")
P("RE-READ WITH OUTER3 HELD (publication)")
P("(session 60's queue third named candidate row: the k=2 inner3")
P("variant's T8 re-read with OUTER3 held and any non-ladder rank")
P("pairs (both ANALYSIS) -- taken FIRST on the k=2 inner3")
P("rounding-variant re-read; over the SAME four windows")
P("s36/s38/s39/s51 of")
P("the named-cell robust-scale level campaign, ANALYSIS only --")
P("does s58's joint T8 (a) letter survive when the third inner")
P("pair sits at the s58-named ALTERNATIVE rounding k=2 (36,40)")
P("instead of the frozen tie-break k=3 (35,41), OUTER3 held at")
P("(3,73)?")
P("OUTER3 = (x_(3), x_(73)) -- HELD at the s58-named pair; the")
P("inner variant = (x_(36), x_(40)) -- the s58-named k=2")
P("alternative rounding of the third inner pair (the s58 freeze")
P("named (35,41)/(36,40) as the two candidates and broke the")
P("k=2.5 tie toward k=3 by the frozen ROUND-HALF-AWAY-FROM-ZERO")
P("rule; this probe reads the OTHER rounding of that SAME tie --")
P("no new rule choice, no new rank pair; NAMED, NOT HIDDEN: the")
P("k=2 inner pair IS exactly the retired step-4 IN4 axis of s59).")
P("NAMED, NOT HIDDEN: this probe is a RE-READ, NOT a fresh")
P("pre-registered prediction -- both axes' per-window levels are")
P("published priors (publication-s58 D1 OUTER3")
P("902/721/811/776; publication-s59 D1 INNER4 19/21/24/20, both")
P("QUOTE-ONLY here), so every observed statistic is a")
P("deterministic recombination of published numbers and only the")
P("permutation p values are new (the protocol.txt freeze fixed")
P("the null, thresholds and joint rule BEFORE those p values")
P("existed; freeze stamp below). THREE")
P("named contrasts (s36 vs s38, s36 vs s39, s36 vs s51), ONE-SIDED")
P("each in the pre-registered direction P3K2 > 0 (outer-weighted")
P("compression at the variant pair set; direction fixed by")
P("s55's published T5 (a) reading and the s58 T8 framing, both")
P("QUOTE-ONLY, and its truth value is already determined by the")
P("published components),")
P("joint T11 = the pre-registered INTERSECTION-UNION rule (all")
P("three (a); NO multiplicity correction).")
P("Produced ONLY by analysis-s61.py over the COMMITTED run logs of")
P("four fixed evidence directories (anv-b3commonmode-20261028 =")
P("the s36 window, anv-b3joint3-20261028 = the s38 window,")
P("anv-b3joint4-20261028 = the s39 window, anv-b3levelrep-20261028")
P(f"= the s51 window); protocol.txt was frozen BEFORE any statistic")
P(f"of this probe was computed (freeze stamp {FREEZE}).")
P("ANALYSIS session -- NO new hardware, NO new runs, NO builds;")
P("the four windows were MEASURED in sessions 36/38/39/51 on")
P("aiueos-6600hs Intel BMG G31 ANV at 2026-10-28T02:40:49Z /")
P("03:39:14Z / 04:09:48Z / 11:45:26Z (their committed logs are")
P("the only input).")
P("")
P("1. INTEGRITY (computed over each window's committed logs;")
P("   protocol section 4):")
for win, _d in WINDOWS:
    info = win_info[win]
    nlogs = 3 + 36 + 36 + 3
    P(f"   {win}: runs parsed {nlogs}; VERIFY mismatch total {info['vmis']}; "
      f"counts ok {info['counts_ok']}; knobs ok {info['knob_ok']}; "
      f"S=8 fail-closed {info['fail_ok']}; cell map ok {info['cmap_ok']}")
    for pr in info["problems"]:
        P(f"   !! {pr}")
P("   INVALIDATION criterion (protocol section 4): any violation =>")
P("   joint letter (c).")
P("")

# ---- C1 at ALL FOUR windows ----
c1 = {}
for win, _d in WINDOWS:
    c2_vals = block_vals(win, "c2", ARMS["c2"][3])
    c2_cls = "FLOOR" if all(v <= 100 for v in c2_vals) else (
        "CAPTURED" if all(v >= 1000 for v in c2_vals) else "INTERMEDIATE/MIXED")
    c8_m = pooled(win, "c8", sum128, ARMS["c8"][3], 2)
    ok = (c2_cls == "FLOOR") and abs(c8_m - COMMITTED_C8) <= 0.05 * COMMITTED_C8
    c1[win] = (c2_cls, c8_m, ok)
P("2. C1 RE-DERIVATION (environment pin, all four windows):")
for win, _d in WINDOWS:
    c2_cls, c8_m, ok = c1[win]
    P(f"   {win}: c2 class {c2_cls} (FLOOR required; committed floor band 31..32); "
      f"c8 (sum,128,S=16) pooled median {c8_m:.0f} vs committed {COMMITTED_C8} "
      f"({abs(c8_m - COMMITTED_C8) / COMMITTED_C8 * 100:.2f}% delta; +/-5% required)")
c1_ok = all(c1[w][2] for w, _d in WINDOWS)
P(f"   C1 branch (all four windows): {'(a) all four controls replicate' if c1_ok else '(b) discrepancy'}")
P("")

# ---- block-min vectors: all four windows reproduce their ----
# ---- published/quote-only priors EXACTLY ----
vec_ok = True
vec = {}
for win, _d in WINDOWS:
    X = [block_min(win, "hi", [3 * i + 1, 3 * i + 2, 3 * i + 3]) for i in range(12)]
    Y = [block_min(win, "tw", [3 * i + 1, 3 * i + 2, 3 * i + 3]) for i in range(12)]
    vec[win] = (X, Y)
    if [int(v) for v in X] != REF_X[win] or [int(v) for v in Y] != REF_Y[win]:
        vec_ok = False
P("3. THE BLOCK-MIN VECTORS (re-derived from the committed logs; block")
P("   order A..L; every window reproduces its published/quote-only")
P("   prior EXACTLY -- s36/s38/s39 vs publication-s39.txt section 3,")
P("   s51 vs publication-s51.txt section 3 (mismatch => (c))):")
for win, _d in WINDOWS:
    X, Y = vec[win]
    P(f"   {win} X (hi): " + " ".join(f"{int(v)}" for v in X))
    P(f"   {win} Y (tw): " + " ".join(f"{int(v)}" for v in Y))
    P(f"   {win} reproduction EXACT: "
      f"{[int(v) for v in X] == REF_X[win] and [int(v) for v in Y] == REF_Y[win]}")
P(f"   all four windows reproduce EXACTLY: {vec_ok}")
P("")

# ---- anchor rows: all four reproduce their priors EXACTLY ----
anchor_ok = True
anchor_rows = {}
for win, _d in WINDOWS:
    a_med = pooled(win, "hi", sum128, [1, 2, 3], 2)
    bvals = [int(v) for v in block_vals(win, "hi", [1, 2, 3])]
    a_min, a_max = min(bvals), max(bvals)
    anchor_rows[win] = (a_med, a_min, a_max)
    if (a_med, a_min, a_max) != REF_ANCHOR[win]:
        anchor_ok = False
P("3b. ANCHOR ROWS (hi block A -- the frozen L12 single bar candidate:")
P("    its (sum,128,S=16) pooled median and 18-cell min..max; every")
P("    window reproduces its published/quote-only prior EXACTLY")
P("    (s36/s38/s39 vs publication-s36/38/39 section D; s51 vs")
P("    publication-s51.txt section 3b; mismatch => (c)):")
for win, _d in WINDOWS:
    a_med, a_min, a_max = anchor_rows[win]
    P(f"    {win}: median {a_med:.0f} min..max {a_min}..{a_max} "
      f"(want {REF_ANCHOR[win][0]} / {REF_ANCHOR[win][1]}..{REF_ANCHOR[win][2]}); "
      f"reproduction EXACT: {(a_med, a_min, a_max) == REF_ANCHOR[win]}")
P(f"    all four windows reproduce EXACTLY: {anchor_ok}")
P("")

# ------------------------------------------------------------------
# the variant third-pair per-window levels (D1 content, computed
# BEFORE section 4 because the protocol-section-4 invalidation
# includes the deterministic-recombination prior check)
# ------------------------------------------------------------------
d1 = {}
for win, _d in WINDOWS:
    dout_b, din_b = [], []
    for i in range(12):
        runs = [3 * i + 1, 3 * i + 2, 3 * i + 3]
        xs = []
        for r in runs:
            xs += [s[2] for s in data[(win, "tw", r)][2] if s[1] == nc]
        do, di = pair_ds(np.array(xs, dtype=np.int64))
        dout_b.append(int(do))
        din_b.append(int(di))
    l2o = sorted(dout_b)[5] + sorted(dout_b)[6]
    l2i = sorted(din_b)[5] + sorted(din_b)[6]
    d1[win] = (dout_b, din_b, l2o, l2i,
               l2o == REF_SCALE["OUTER3"][win], l2i == REF_SCALE["INNER4"][win])
prior_ok = all(d1[w][4] and d1[w][5] for w, _d in WINDOWS)

# ------------------------------------------------------------------
# the PRIMARY probe (protocol sections 1/2/3): the named cell's
# three two-window variant third-pair outer-vs-inner compression-
# profile contrasts
# ------------------------------------------------------------------
rng = random.Random(SEED)

named_arr = {}
for win, _d in WINDOWS:
    named_arr[win] = run_arr(win, "tw")[:, [nc_pos], :][:, 0, :]   # (36,25)

def contrast(wa, wb):
    flat = np.vstack([named_arr[wa], named_arr[wb]])               # (72,25)
    obs = np.arange(72, dtype=np.int64).reshape(1, 2, 12, 3)
    sub = flat[obs].reshape(1, 2, 12, 75)
    dout_obs, din_obs = pair_ds(sub)
    dout_obs, din_obs = dout_obs[0], din_obs[0]                   # (2,12) each
    l2out_obs = np.sort(dout_obs, axis=1)[:, 5] + np.sort(dout_obs, axis=1)[:, 6]
    l2in_obs = np.sort(din_obs, axis=1)[:, 5] + np.sort(din_obs, axis=1)[:, 6]
    c_out = int(l2out_obs[0] - l2out_obs[1])
    c_in = int(l2in_obs[0] - l2in_obs[1])
    p_obs = c_out - c_in
    perms = np.empty((TRIALS, 72), dtype=np.int64)
    for t in range(TRIALS):
        perm = list(range(72))
        rng.shuffle(perm)
        perms[t] = perm
    cnt = 0
    for i in range(0, TRIALS, BATCH):
        batch = perms[i:i + BATCH].reshape(-1, 2, 12, 3)
        sub = flat[batch].reshape(-1, 2, 12, 75)
        dout, din = pair_ds(sub)                                   # (b,2,12) each
        dso = np.sort(dout, axis=2)
        dsi = np.sort(din, axis=2)
        l2o = dso[:, :, 5] + dso[:, :, 6]                          # (b,2)
        l2i = dsi[:, :, 5] + dsi[:, :, 6]                          # (b,2)
        p = (l2o[:, 0] - l2o[:, 1]) - (l2i[:, 0] - l2i[:, 1])
        cnt += int((p >= p_obs).sum())
    pval = (1 + cnt) / (1 + TRIALS)
    return (int(l2out_obs[0]), int(l2out_obs[1]), int(l2in_obs[0]),
            int(l2in_obs[1]), c_out, c_in, p_obs, cnt, pval)

prim = {}
for wa, wb in PAIRS:
    prim[wb] = contrast(wa, wb)

def contrast_letter(p_obs, pval):
    if p_obs > 0 and pval <= 0.05:
        return "(a) THIRDPAIR-K2VARIANT-OUTER-WEIGHTED-DIFFERENT"
    if p_obs == 0:
        return "(b) NOT-DIFFERENT [EXACTLY-ZERO]"
    if p_obs < 0:
        return "(b) NOT-DIFFERENT [OPPOSITE-DIRECTION]"
    return "(b) NOT-DIFFERENT [NONZERO-NOT-SIGNIFICANT]"

def invalidated():
    inv = any(win_info[w]["vmis"] != 0 or not win_info[w]["counts_ok"]
              or not win_info[w]["knob_ok"] or not win_info[w]["fail_ok"]
              or not win_info[w]["cmap_ok"] for w, _d in WINDOWS)
    return inv or (not vec_ok) or (not anchor_ok) or (not c1_ok) or (not prior_ok)

def joint_letter():
    if invalidated():
        return "(c) NOT EVALUABLE", [], "integrity violation"
    letters = {wb: contrast_letter(prim[wb][6], prim[wb][8]) for _, wb in PAIRS}
    fails = [wb for _, wb in PAIRS if not letters[wb].startswith("(a)")]
    if fails:
        return "(b) NOT-THIRDPAIR-K2VARIANT-PROFILE-OUTER-WEIGHTED-CONSISTENT", fails, "pair(s) not (a)"
    return "(a) THIRDPAIR-K2VARIANT-PROFILE-OUTER-WEIGHTED-CONSISTENT", [], ""

P("4. T11 THE ROW QUESTION (frozen letters, protocol sections 0/1/2/3):")
P(f"   the NAMED cell {ckey_str(nc)} of the tw arm, the NAMED window")
P("   contrasts s36 (pre-shift) vs each of s38/s39/s51, ONE-SIDED")
P("   each in the pre-registered direction P3K2 > 0 (outer-weighted")
P("   compression at the variant pair set; direction fixed by")
P("   s55's published T5 (a) reading and the s58 T8 framing, both")
P("   QUOTE-ONLY; NAMED, NOT HIDDEN: this probe is a RE-READ, not")
P("   a fresh prediction -- the observed")
P("   statistics are deterministic recombinations of published")
P("   s58/s59 D1 priors and only the p values are new), on")
P("   the NAMED variant profile axis (per block D_out3 =")
P("   x_(73) - x_(3) -- OUTER3 HELD at the s58 pair -- and")
P("   D_in3K2 = x_(40) - x_(36) -- the s58-named k=2 alternative")
P("   rounding, identical to the retired step-4 IN4 axis -- of the")
P("   SAME pooled 75; 2*C_out3 = 2*Lout3_s36 - 2*Lout3_w,")
P("   2*C_in3K2 = 2*Lin3K2_s36 - 2*Lin3K2_w;")
P(f"   2*P3K2_obs = 2*C_out3 - 2*C_in3K2 in half-tick integer units).")
P(f"   {TRIALS} trials, seed {SEED}, frozen probe order")
P("   (s36,s38), (s36,s39), (s36,s51); per trial one shuffle of")
P("   list(range(72)) split into two pseudo-windows of 36 and 12")
P("   blocks of 3, BOTH axes computed on the SAME pseudo-blocks;")
P("   p = (1 + count(P3K2* >= P3K2_obs)) / (1 + 20,000),")
P(f"   ONE-SIDED; joint T11 = the pre-registered INTERSECTION-UNION")
P("   rule (all three contrasts (a); NO multiplicity correction")
P("   applied or needed):")
for wa, wb in PAIRS:
    (lo_a, lo_b, li_a, li_b, c_out, c_in, p_obs, cnt, pval) = prim[wb]
    P(f"   {wa}-vs-{wb}: OUT3 2*L_{wa} = {lo_a} ({fmt_ht(lo_a)}), "
      f"2*L_{wb} = {lo_b} ({fmt_ht(lo_b)}), 2*C_out3 = {c_out}; "
      f"IN3K2 2*L_{wa} = {li_a} ({fmt_ht(li_a)}), "
      f"2*L_{wb} = {li_b} ({fmt_ht(li_b)}), 2*C_in3K2 = {c_in}; "
      f"2*P3K2_obs = {p_obs} (P3K2_obs = {fmt_ht(p_obs)}); "
      f"count {cnt} / {TRIALS + 1}; p = {pval:.6f}; p <= 0.05: {pval <= 0.05}; "
      f"contrast letter {contrast_letter(p_obs, pval)}")
t11, t11fails, t11why = joint_letter()
P(f"   T11 = {t11}" + (f" (named: {t11why}: {', '.join(t11fails)})" if (t11fails or t11why)
                       else ""))
P("   NAMED, NOT HIDDEN: this probe examines a TWELFTH axis on")
P("   the SAME window data (after the s48 MAD / s47 IQR scale")
P("   axes, the s49/s50/s51 descriptive families, s52's")
P("   deviation-center axis, s53's inner-quantile-pair axis,")
P("   s54's outer-quantile-pair axis, s55's composed profile")
P("   axis, s56's second-pair profile axis, s58's third-pair")
P("   profile axis, s59's fourth-pair profile axis and s60's")
P("   fifth-pair profile axis), and it is the campaign's FIRST")
P("   probe that is NOT a fresh pre-registered prediction (the")
P("   observed statistics are deterministic recombinations of")
P("   published s58/s59 D1 priors; only the permutation p values")
P("   are new -- section 1's D1 check below re-derives the priors")
P("   EXACTLY); the rank pairs are the s58-named alternative")
P("   rounding of the third inner pair (k=2 vs the frozen k=3")
P("   tie-break), OUTER3 held -- no new rule choice, no new pair;")
P("   the probe is a rounding-variant RE-READ of the s58 T8")
P("   family and")
P("   does NOT retro-correct any earlier uncorrected family; the")
P("   three contrasts share the s36 window (the pairwise tests")
P("   are dependent; the IUT does not care); (a) names NO")
P("   mechanism (thermal/scheduling/memory/driver state all")
P("   UNMEASURED) and NOT whether any movement is physical or")
P("   estimator structure -- T11 (a) AGREEING with s58's T8 (a)")
P("   is CONSISTENT WITH the T8 letter being robust to the k=2/k=3")
P("   rounding tie-break at the third inner pair; T11 (b)")
P("   DISSENTING from s58's T8 (a) is CONSISTENT WITH rounding-")
P("   variant fragility of the T8 letter (the k=2 inner pair")
P("   spans 4 ranks vs the k=3 pair's 6, so the two inner axes")
P("   sit at different noise floors); EITHER WAY threshold-")
P("   artifact-vs-representation and physical-vs-estimator-")
P("   structure STAY UNRESOLVED; the four windows span ~8.5 hours")
P("   in ONE UTC day on ONE host (LOW POWER; any window-specific")
P("   state can produce any letter); 20,000 trials (NOT the")
P("   s35-frozen 100,000 -- cost, same named deviation as")
P("   sessions 40-60; p resolution 1/20,001 ~= 5e-5); L2")
P("   observational ONLY; NO causal mechanism; anything off the")
P("   ANV host UNMEASURED.")
P("")
P("5. REPLICATION FRAMING (frozen): the row answer is the section-4")
P("   joint T11; the axis is the named cell's third-pair outer-")
P("   minus-k=2-inner variant profile ONLY; the per-contrast")
P("   letters and sub-cases are in section 4.")
P("")

P("6. DESCRIPTIVE (not the row question; NO letter):")
P("   D1 the NAMED cell's four-window per-axis VARIANT THIRD-PAIR")
P(f"      level vectors and block D values ({ckey_str(nc)}, tw arm; L = median")
P("      of the 12 block D values, half-tick exact; both axes from")
P("      the SAME pooled 75; NAMED, NOT HIDDEN: the OUT3 levels")
P("      reproduce publication-s58 D1 EXACTLY and the IN3K2")
P("      levels reproduce publication-s59 D1 EXACTLY (the")
P("      deterministic recombination of protocol section 0); only")
P("      the PROFILE3K2 level is new content of this publication,")
P("      and it too is the exact difference of two published")
P("      priors):")
for win, _d in WINDOWS:
    dout_b, din_b, l2o, l2i, ro, ri = d1[win]
    P(f"      {win} OUT3: 2*L = {l2o} ({fmt_ht(l2o)}); block D values: "
      + " ".join(str(v) for v in dout_b))
    P(f"      {win} IN3K2: 2*L = {l2i} ({fmt_ht(l2i)}); block D values: "
      + " ".join(str(v) for v in din_b))
    P(f"      {win} PROFILE3K2: 2*Lout3 - 2*Lin3K2 = {l2o - l2i} ({fmt_ht(l2o - l2i)})")
    P(f"      {win} prior reproduction EXACT: OUT3 {ro} (publication-s58 D1 "
      f"{REF_SCALE['OUTER3'][win]}); IN3K2 {ri} (publication-s59 D1 "
      f"{REF_SCALE['INNER4'][win]})")
P("   D2 the frozen-scale, center, quantile-pair and composed-")
P("      profile level context (QUOTE-ONLY priors of")
P("      publication-s49/50/51 D1, publication-s52 D1,")
P("      publication-s53 D1, publication-s54 D1, publication-")
P("      s55 D1, publication-s56 D1, publication-s58 D1 and")
P("      publication-s59 D1 --")
P("      NOT recomputed by this")
P("      probe; interpretation only: the MAD/IQR scale levels and")
P("      the outer-pair, second-, third- and fourth-pair levels")
P("      dropped s36 -> s38/s39/s51, the center level held, the")
P("      inner-pair, inner2, inner3 and inner4 levels scattered")
P("      near their noise floors")
P("      and the composed profile levels")
P("      dropped outer-weighted):")
for ax in ("MAD", "IQR", "CENTER", "INNERPAIR", "OUTERPAIR", "PROFILE",
           "OUTER2", "INNER2", "PROFILE2", "OUTER3", "INNER3", "PROFILE3",
           "OUTER4", "INNER4", "PROFILE4"):
    r = REF_SCALE[ax]
    P(f"      {ax} 2*L s36/s38/s39/s51 = {r['s36']}/{r['s38']}/{r['s39']}/{r['s51']} "
      f"(L {fmt_ht(r['s36'])}/{fmt_ht(r['s38'])}/{fmt_ht(r['s39'])}/{fmt_ht(r['s51'])})")
P("   D3 the s36-vs-s51 VARIANT THIRD-PAIR PROFILE contrast table")
P("      over all 18 ok cells (per cell: OUT3 2*L pair, IN3K2 2*L")
P("      pair and the profile P3K2 = C_out3 - C_in3K2; 18")
P("      descriptive contrasts, UNCORRECTED for multiplicity, no")
P("      letter):")
d3 = {}
for win in ("s36", "s51"):
    rows_o, rows_i = [], []
    for i in range(12):
        runs = [3 * i + 1, 3 * i + 2, 3 * i + 3]
        xs = [[] for _ in ok_cells]
        for r in runs:
            for s in data[(win, "tw", r)][2]:
                xs[cell_pos[s[1]]].append(s[2])
        pooled_t = np.array(xs, dtype=np.int64)                    # (18,75)
        do, di = pair_ds(pooled_t)
        rows_o.append(do)
        rows_i.append(di)
    rso = np.sort(np.array(rows_o), axis=0)
    rsi = np.sort(np.array(rows_i), axis=0)
    d3[win] = (rso[5] + rso[6], rsi[5] + rsi[6])                   # (18,) each
for ci, k in enumerate(ok_cells):
    o36, o51 = int(d3["s36"][0][ci]), int(d3["s51"][0][ci])
    i36, i51 = int(d3["s36"][1][ci]), int(d3["s51"][1][ci])
    P(f"      tw cell {ckey_str(k)}: OUT3 2*L {o36}/{o51} IN3K2 2*L {i36}/{i51} "
      f"P3K2 (C_out3 {fmt_ht(o36 - o51)}, C_in3K2 {fmt_ht(i36 - i51)}, "
      f"P3K2 {fmt_ht((o36 - o51) - (i36 - i51))})")
P("")

P("7. VERDICT SUMMARY:")
P(f"   T11 = {t11}" + (f" (named: {t11why}: {', '.join(t11fails)})" if (t11fails or t11why)
                       else ""))
for wa, wb in PAIRS:
    (lo_a, lo_b, li_a, li_b, c_out, c_in, p_obs, cnt, pval) = prim[wb]
    P(f"   {wa}-vs-{wb}: P3K2_obs = {fmt_ht(p_obs)} (2*P3K2_obs = {p_obs}; "
      f"OUT3 2*L {lo_a} -> {lo_b} (2*C_out3 {c_out}); "
      f"IN3K2 2*L {li_a} -> {li_b} (2*C_in3K2 {c_in})); "
      f"count {cnt}/{TRIALS + 1}; p {pval:.6f}; "
      f"letter {contrast_letter(p_obs, pval)}")
P(f"   evaluable inputs: vector reproduction EXACT ({vec_ok}); anchor")
P(f"   rows EXACT ({anchor_ok}); C1 all four windows "
  f"({'(a)' if c1_ok else '(b)'}); D1 prior reproduction EXACT "
  f"({prior_ok}); per-window integrity rows in section 1")
P("   ANALYSIS session: NO new hardware, NO new runs, NO builds this")
P("   tick (all four windows are prior sessions' committed logs).")
P("   THE BAR: NO new ledger line (no runs this session; no bar")
P("   candidate exists to log); NO day-slot consumption (the")
P("   2026-10-28 slot is s31's); the frozen evaluator is the only")
P("   source of the bar letter (bar-eval-s61.txt); verdict stays")
P("   PENDING 1/4 with s31 counted; next executable day slot")
P("   2026-10-29.")
P("   UNMEASURED (named): what moves the per-cell robust-scale")
P("   level on the tw arm (no mechanism named by any letter);")
P("   whether any movement is physical or estimator structure;")
P("   whether four counted days settle the bar (PENDING 1/4); the")
P("   s31/s34/s36 excursion causes; threshold-artifact-vs-")
P("   representation; anything off the ANV host. NAMED CANDIDATE")
P("   ROWS for later sessions: (first, STARTED in s57) the FIFTH-")
P("   window measurement + T7 read in the 2026-10-29 UTC slot")
P("   (NEW hardware; the slot opens at 2026-10-29T00:00:00Z, ~5h52m")
P("   after this tick -- NAMED, not skipped silently); then the")
P("   s38 hi (sum,256,S=32) wander replication (NEW hardware --")
P("   W5's hi runs); then any non-ladder rank pairs (ANALYSIS; a")
P("   NEW named selection rule is required -- the halving ladder")
P("   is retired and the k=2 inner3 variant re-read is DONE at")
P("   this probe) stay named candidate rows.")
P("   Rule 4 binds: nothing moves; accelerator-targets defaults")
P("   remain provisional (:measured? false); NO vendor optimization")
P("   exists for Intel.")

open(os.path.join(HERE, "publication-s61.txt"), "w").write("\n".join(out) + "\n")
