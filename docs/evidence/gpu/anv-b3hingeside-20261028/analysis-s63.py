#!/usr/bin/env python3
"""JUN-59 session 63 analysis -- THE HINGE-SIDE (HS) RANK-PAIR
SPREAD-COMPRESSION PROBE (session 62's queue third named
candidate row: the HINGE-SIDE pair sets (x_(1), x_(19)) and
(x_(57), x_(75)) -- the remaining two pairs of the HX rule's
four-rank vocabulary; the HX family itself is COMPLETE and
RETIRED at s62; the two rows ahead of it need NEW hardware and
the W5 measurement is day-slot-gated to the 2026-10-29 UTC
slot; over the SAME four windows s36/s38/s39/s51 of the
named-cell robust-scale level campaign, ANALYSIS only -- do the
two HINGE-SIDE (tail-side) rank pair sets carry the same s36 ->
s38/s39/s51 spread-level compression as every published
wide-span SYMMETRIC rank pair?).

Route (frozen in protocol.txt section 6): this script parses ONLY
the committed run logs of the four fixed evidence directories and
writes publication-s63.txt in its own directory. Deterministic:
running it twice yields byte-identical output.

NAMED, NOT HIDDEN (protocol section 0): this probe IS a fresh
pre-registered prediction -- the HS per-window levels were never
published or computed anywhere (the campaign's SIXTH fresh
pre-registered prediction after s56, s58, s59, s60, s62), and
the protocol.txt freeze (2026-10-28T19:09:28Z) fixed the null,
thresholds and joint rule BEFORE those statistics existed.

The primary statistic (named cell only): block = 3 consecutive
runs of the tw arm within one window (the s35/s36-frozen block
unit); per block over the pooled 75 samples BOTH D_HSL =
x_(19) - x_(1) (SET-L, left tail-side) and D_HSR = x_(75) -
x_(57) (SET-R, right tail-side) -- exact INTEGERs from the SAME
pooled 75; per window per axis L = median of the 12 block D
values (2*L = 6th + 7th order statistics, INTEGER half-tick
units); per contrast per axis 2*C_obs = 2*L_s36 - 2*L_w (the
pre-registered direction is C_obs > 0 -- hinge-side pair spread
compression; NAMED, NOT HIDDEN: the direction is fixed by the
published wide-span SYMMETRIC pair levels dropping s36 ->
s38/s39/s51 at every ladder step, publication-s54/56/58/59/60
D1, QUOTE-ONLY, and NOT by any hinge-side statistic). THREE
named contrasts: (s36,s38), (s36,s39), (s36,s51). The
resampling null (frozen): per contrast the 72 tw runs of the two
named windows exchangeable; per trial one rng.shuffle of a fresh
list(range(72)) split into two pseudo-windows of 36 and 12
pseudo-blocks of 3 in draw order; D_HSL AND D_HSR computed on
the SAME pseudo-blocks; p_axis = (1 + count(C*_axis >=
C_obs,axis)) / (1 + 20,000), ONE-SIDED. One
random.Random(2026102813), consumed in the frozen probe order:
(s36,s38), (s36,s39), (s36,s51). numpy 2.5.4 (int64 np.sort) is
the frozen implementation path; the resampling is vectorized
over TRIAL BATCHES (batch size a memory detail, NOT part of the
frozen contract); every C* >= C_obs comparison is exact INTEGER
arithmetic. Joint T13 = the pre-registered INTERSECTION-UNION
rule (all SIX axis x contrast letters (a); NO multiplicity
correction).
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
SEED = 2026102813
BATCH = 50
COMMITTED_C8 = 32915
NAMED_CKEY = ("max", 128, "default")
PAIRS = [("s36", "s38"), ("s36", "s39"), ("s36", "s51")]
AXES = ["HSL", "HSR"]
FREEZE = "2026-10-28T19:09:28Z"

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
# ---- quote-only level priors (D2 context; QUOTE-ONLY, NOT ----
# ---- recomputed by this probe; publication-s49/50/51 D1, ----
# ---- publication-s52 D1, publication-s53 D1, publication-s54 ----
# ---- D1, publication-s55 D1, publication-s56 D1, publication- ----
# ---- s58 D1, publication-s59 D1, publication-s60 D1, ----
# ---- publication-s62 D1; 2*L half-tick units) ----
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
             "PROFILE4": {"s36": 968, "s38": 825, "s39": 879, "s51": 875},
             "OUTER5": {"s36": 1060, "s38": 972, "s39": 1031, "s51": 1003},
             "INNER5": {"s36": 12, "s38": 7, "s39": 13, "s51": 10},
             "PROFILE5": {"s36": 1048, "s38": 965, "s39": 1018, "s51": 993},
             "HXLPAIR": {"s36": 864, "s38": 821, "s39": 832, "s51": 804},
             "HXRPAIR": {"s36": 471, "s38": 405, "s39": 441, "s51": 465}}

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
    """(...,75) int64 -> (D_HSL, D_HSR) exact INTEGER block spreads
    from the SAME sorted pooled 75: D_HSL = x_(19) - x_(1) (SET-L,
    left tail-side HS axis) and D_HSR = x_(75) - x_(57) (SET-R,
    right tail-side HS axis)."""
    srt = np.sort(pooled75, axis=-1)
    return srt[..., 18] - srt[..., 0], srt[..., 74] - srt[..., 56]

out = []
P = out.append
P("JUN-59 session 63 -- THE HINGE-SIDE (HS) RANK-PAIR SPREAD-")
P("COMPRESSION PROBE (publication)")
P("(session 62's queue third named candidate row: the HINGE-SIDE")
P("pair sets (x_(1), x_(19)) and (x_(57), x_(75)) -- the")
P("remaining two pairs of the HX rule's four-rank vocabulary;")
P("the HX family itself is COMPLETE and RETIRED at s62; the two")
P("rows ahead of it need NEW hardware and the W5 measurement is")
P("day-slot-gated to the 2026-10-29 UTC slot -- over the SAME")
P("four windows s36/s38/s39/s51 of")
P("the named-cell robust-scale level campaign, ANALYSIS only --")
P("do the two HINGE-SIDE (tail-side) rank pair sets carry the")
P("same s36 -> s38/s39/s51 spread-level compression as every")
P("published wide-span SYMMETRIC rank pair?)")
P("THE NAMED FAMILY (frozen, protocol section 0): the four-rank")
P("vocabulary {1, 19, 57, 75} has exactly SIX unordered pairs;")
P("four are already named ((x_(1), x_(75)) retired outer5,")
P("(x_(19), x_(57)) s47 IQR, the HX family (x_(1), x_(57)) /")
P("(x_(19), x_(75)) retired at s62); the REMAINING two are the")
P("HINGE-SIDE pair sets: SET-L = (x_(1), x_(19)) (sample min to")
P("the lower exclusive hinge Q1) and SET-R = (x_(57), x_(75))")
P("(the upper exclusive hinge Q3 to sample max); rank-")
P("vocabulary-closed, ASYMMETRIC about x_(38) (rank midpoints 10")
P("and 66), mirror images of each other, 18 ranks each, NO")
P("data-dependent choice. NAMED, NOT HIDDEN: with this probe the")
P("four-rank vocabulary is EXHAUSTED (all six pairs named) and")
P("the rank-pair program over this vocabulary is COMPLETE and")
P("RETIRES at this probe.")
P("NAMED, NOT HIDDEN: this probe IS a fresh pre-registered")
P("prediction -- the HS per-window levels were never published")
P("or computed anywhere")
P("and the protocol.txt freeze fixed the null,")
P("thresholds and joint rule BEFORE those statistics existed")
P(f"(freeze stamp {FREEZE}); the campaign's SIXTH fresh pre-")
P("registered prediction (after s56, s58, s59, s60, s62). THREE")
P("named contrasts (s36 vs s38, s36 vs s39, s36 vs s51), ONE-")
P("SIDED each in the pre-registered direction C_obs > 0 (hinge-")
P("side pair spread compression from s36 to the post-shift")
P("window; direction fixed by the published wide-span SYMMETRIC")
P("pair levels dropping s36 -> s38/s39/s51 at every ladder step,")
P("publication-s54/56/58/59/60 D1, QUOTE-ONLY, and NOT by any")
P("hinge-side statistic),")
P("joint T13 = the pre-registered INTERSECTION-UNION rule (all")
P("SIX axis x contrast letters (a); NO multiplicity")
P("correction).")
P("Produced ONLY by analysis-s63.py over the COMMITTED run logs of")
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
P("   joint letter (c). NAMED, NOT HIDDEN: there is NO D1 prior-")
P("   reproduction check at this probe (the HS axes are a FRESH")
P("   prediction and have no published prior to re-derive); the")
P("   independent derivation census re-derives every published")
P("   number from the logs instead.")
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
# the HS per-window levels (D1 content -- NEW statistics, no
# published prior exists to reproduce; the freshness IS the content)
# ------------------------------------------------------------------
d1 = {}
for win, _d in WINDOWS:
    dhsl_b, dhsr_b = [], []
    for i in range(12):
        runs = [3 * i + 1, 3 * i + 2, 3 * i + 3]
        xs = []
        for r in runs:
            xs += [s[2] for s in data[(win, "tw", r)][2] if s[1] == nc]
        dhslo, dhsro = pair_ds(np.array(xs, dtype=np.int64))
        dhsl_b.append(int(dhslo))
        dhsr_b.append(int(dhsro))
    l2l = sorted(dhsl_b)[5] + sorted(dhsl_b)[6]
    l2r = sorted(dhsr_b)[5] + sorted(dhsr_b)[6]
    d1[win] = (dhsl_b, dhsr_b, l2l, l2r)

# ------------------------------------------------------------------
# the PRIMARY probe (protocol sections 1/2/3): the named cell's
# three two-window HS hinge-side-pair spread-compression contrasts
# ------------------------------------------------------------------
rng = random.Random(SEED)

named_arr = {}
for win, _d in WINDOWS:
    named_arr[win] = run_arr(win, "tw")[:, [nc_pos], :][:, 0, :]   # (36,25)

def contrast(wa, wb):
    flat = np.vstack([named_arr[wa], named_arr[wb]])               # (72,25)
    obs = np.arange(72, dtype=np.int64).reshape(1, 2, 12, 3)
    sub = flat[obs].reshape(1, 2, 12, 75)
    dhsl_obs, dhsr_obs = pair_ds(sub)
    dhsl_obs, dhsr_obs = dhsl_obs[0], dhsr_obs[0]                  # (2,12) each
    l2l_obs = np.sort(dhsl_obs, axis=1)[:, 5] + np.sort(dhsl_obs, axis=1)[:, 6]
    l2r_obs = np.sort(dhsr_obs, axis=1)[:, 5] + np.sort(dhsr_obs, axis=1)[:, 6]
    c_l = int(l2l_obs[0] - l2l_obs[1])
    c_r = int(l2r_obs[0] - l2r_obs[1])
    perms = np.empty((TRIALS, 72), dtype=np.int64)
    for t in range(TRIALS):
        perm = list(range(72))
        rng.shuffle(perm)
        perms[t] = perm
    cnt_l = 0
    cnt_r = 0
    for i in range(0, TRIALS, BATCH):
        batch = perms[i:i + BATCH].reshape(-1, 2, 12, 3)
        sub = flat[batch].reshape(-1, 2, 12, 75)
        dl, dr = pair_ds(sub)                                      # (b,2,12) each
        dsl = np.sort(dl, axis=2)
        dsr = np.sort(dr, axis=2)
        l2l = dsl[:, :, 5] + dsl[:, :, 6]                          # (b,2)
        l2r = dsr[:, :, 5] + dsr[:, :, 6]                          # (b,2)
        c_l_star = l2l[:, 0] - l2l[:, 1]
        c_r_star = l2r[:, 0] - l2r[:, 1]
        cnt_l += int((c_l_star >= c_l).sum())
        cnt_r += int((c_r_star >= c_r).sum())
    pval_l = (1 + cnt_l) / (1 + TRIALS)
    pval_r = (1 + cnt_r) / (1 + TRIALS)
    return {"HSL": (int(l2l_obs[0]), int(l2l_obs[1]), c_l, cnt_l, pval_l),
            "HSR": (int(l2r_obs[0]), int(l2r_obs[1]), c_r, cnt_r, pval_r)}

prim = {}
for wa, wb in PAIRS:
    prim[wb] = contrast(wa, wb)

def contrast_letter(c_obs, pval):
    if c_obs > 0 and pval <= 0.05:
        return "(a) HINGESIDE-PAIR-SPREAD-COMPRESSION-DIFFERENT"
    if c_obs == 0:
        return "(b) NOT-DIFFERENT [EXACTLY-ZERO]"
    if c_obs < 0:
        return "(b) NOT-DIFFERENT [OPPOSITE-DIRECTION]"
    return "(b) NOT-DIFFERENT [NONZERO-NOT-SIGNIFICANT]"

def invalidated():
    inv = any(win_info[w]["vmis"] != 0 or not win_info[w]["counts_ok"]
              or not win_info[w]["knob_ok"] or not win_info[w]["fail_ok"]
              or not win_info[w]["cmap_ok"] for w, _d in WINDOWS)
    return inv or (not vec_ok) or (not anchor_ok) or (not c1_ok)

def joint_letter():
    if invalidated():
        return "(c) NOT EVALUABLE", [], "integrity violation"
    letters = {(ax, wb): contrast_letter(prim[wb][ax][2], prim[wb][ax][4])
               for ax in AXES for _, wb in PAIRS}
    fails = [f"{ax}-{wb}" for ax in AXES for _, wb in PAIRS
             if not letters[(ax, wb)].startswith("(a)")]
    if fails:
        return "(b) NOT-HINGESIDE-PAIR-SPREAD-COMPRESSION-CONSISTENT", fails, "letter(s) not (a)"
    return "(a) HINGESIDE-PAIR-SPREAD-COMPRESSION-CONSISTENT", [], ""

P("4. T13 THE ROW QUESTION (frozen letters, protocol sections 0/1/2/3):")
P(f"   the NAMED cell {ckey_str(nc)} of the tw arm, the NAMED window")
P("   contrasts s36 (pre-shift) vs each of s38/s39/s51, ONE-SIDED")
P("   each in the pre-registered direction C_obs > 0 (hinge-side-")
P("   pair spread compression from s36 to the post-shift window;")
P("   direction fixed by the published wide-span SYMMETRIC pair")
P("   levels, publication-s54/56/58/59/60 D1, QUOTE-ONLY; NAMED,")
P("   NOT HIDDEN: this probe IS a fresh pre-registered prediction")
P("   -- the HS levels are NEW statistics), on the NAMED HS")
P("   tail-side axes (per block D_HSL = x_(19) - x_(1) -- SET-L,")
P("   left tail-side -- and D_HSR = x_(75) - x_(57) -- SET-R,")
P("   right tail-side -- of the SAME pooled 75; per axis")
P(f"   2*C_obs = 2*L_s36 - 2*L_w in half-tick integer units).")
P(f"   {TRIALS} trials, seed {SEED}, frozen probe order")
P("   (s36,s38), (s36,s39), (s36,s51); per trial one shuffle of")
P("   list(range(72)) split into two pseudo-windows of 36 and 12")
P("   blocks of 3, BOTH axes computed on the SAME pseudo-blocks;")
P("   p = (1 + count(C* >= C_obs)) / (1 + 20,000),")
P(f"   ONE-SIDED; joint T13 = the pre-registered INTERSECTION-UNION")
P("   rule (all SIX axis x contrast letters (a); NO multiplicity")
P("   correction applied or needed):")
for wa, wb in PAIRS:
    for ax in AXES:
        (la, lb, c_obs, cnt, pval) = prim[wb][ax]
        P(f"   {wa}-vs-{wb} {ax}: 2*L_{wa} = {la} ({fmt_ht(la)}), "
          f"2*L_{wb} = {lb} ({fmt_ht(lb)}), 2*C_obs = {c_obs} "
          f"(C_obs = {fmt_ht(c_obs)}); "
          f"count {cnt} / {TRIALS + 1}; p = {pval:.6f}; p <= 0.05: {pval <= 0.05}; "
          f"contrast letter {contrast_letter(c_obs, pval)}")
t13, t13fails, t13why = joint_letter()
P(f"   T13 = {t13}" + (f" (named: {t13why}: {', '.join(t13fails)})" if (t13fails or t13why)
                       else ""))
P("   NAMED, NOT HIDDEN: this probe examines the FIFTEENTH and")
P("   SIXTEENTH axes on")
P("   the SAME window data (after the s48 MAD / s47 IQR scale")
P("   axes, the s49/s50/s51 descriptive families, s52's")
P("   deviation-center axis, s53's inner-quantile-pair axis,")
P("   s54's outer-quantile-pair axis, s55's composed profile")
P("   axis, s56's second-pair profile axis, s58's third-pair")
P("   profile axis, s59's fourth-pair profile axis, s60's")
P("   fifth-pair profile axis, s61's k=2 variant re-read")
P("   axis and s62's HX asymmetric-pair axes), and it is the")
P("   campaign's SIXTH fresh pre-registered")
P("   prediction; the rank pairs are the tail-side pairs of the")
P("   four-rank vocabulary, ASYMMETRIC")
P("   about x_(38), under the HINGE-SIDE family frozen in protocol")
P("   section 0 before any statistic existed;")
P("   the probe does NOT retro-correct any earlier uncorrected")
P("   family; the three contrasts share the s36 window (the")
P("   pairwise tests are dependent; the IUT does not care); (a)")
P("   names NO mechanism (thermal/scheduling/memory/driver state")
P("   all UNMEASURED) and NOT whether any movement is physical")
P("   or estimator structure -- T13 (a) is CONSISTENT WITH the")
P("   s36 -> post-shift spread compression holding at the narrow")
P("   hinge-side pairs too; T13 (b) is CONSISTENT WITH the")
P("   compression not reaching the tail-side pairs OR with a")
P("   power loss at these narrow pair sets (the HS pairs span 18")
P("   ranks vs the HX pairs' 56 and the ladder outer pairs'")
P("   70..74, and the inner family's levels scattered near their")
P("   noise floors); EITHER WAY threshold-")
P("   artifact-vs-representation and physical-vs-estimator-")
P("   structure STAY UNRESOLVED; the four windows span ~8.5 hours")
P("   in ONE UTC day on ONE host (LOW POWER; any window-specific")
P("   state can produce any letter); 20,000 trials (NOT the")
P("   s35-frozen 100,000 -- cost, same named deviation as")
P("   sessions 40-62; p resolution 1/20,001 ~= 5e-5); L2")
P("   observational ONLY; NO causal mechanism; anything off the")
P("   ANV host UNMEASURED.")
P("")
P("5. REPLICATION FRAMING (frozen): the row answer is the section-4")
P("   joint T13; the axes are the named cell's HS hinge-side-pair")
P("   spread levels ONLY; the per-contrast letters and sub-cases")
P("   are in section 4.")
P("")

P("6. DESCRIPTIVE (not the row question; NO letter):")
P("   D1 the NAMED cell's four-window per-axis HS level vectors")
P(f"      and block D values ({ckey_str(nc)}, tw arm; L = median")
P("      of the 12 block D values, half-tick exact; both axes from")
P("      the SAME pooled 75; NAMED, NOT HIDDEN: the HS levels are")
P("      NEW statistics -- no published prior exists to reproduce")
P("      -- the freshness IS the content):")
for win, _d in WINDOWS:
    dhsl_b, dhsr_b, l2l, l2r = d1[win]
    P(f"      {win} HSL: 2*L = {l2l} ({fmt_ht(l2l)}); block D values: "
      + " ".join(str(v) for v in dhsl_b))
    P(f"      {win} HSR: 2*L = {l2r} ({fmt_ht(l2r)}); block D values: "
      + " ".join(str(v) for v in dhsr_b))
P("   D2 the frozen-scale, center, quantile-pair, composed-")
P("      profile and HX-pair level context (QUOTE-ONLY priors of")
P("      publication-s49/50/51 D1, publication-s52 D1,")
P("      publication-s53 D1, publication-s54 D1, publication-")
P("      s55 D1, publication-s56 D1, publication-s58 D1,")
P("      publication-s59 D1, publication-s60 D1 and publication-")
P("      s62 D1 --")
P("      NOT recomputed by this")
P("      probe; interpretation only: the MAD/IQR scale levels and")
P("      the outer-pair, second- through fifth-pair and HX-pair")
P("      levels")
P("      dropped s36 -> s38/s39/s51, the center level held, the")
P("      inner-pair and inner2..inner5 levels scattered")
P("      near their noise floors")
P("      and the composed profile levels")
P("      dropped outer-weighted at ladder steps 1/3/4 and did NOT")
P("      consistently replicate at steps 2/5):")
for ax in ("MAD", "IQR", "CENTER", "INNERPAIR", "OUTERPAIR", "PROFILE",
           "OUTER2", "INNER2", "PROFILE2", "OUTER3", "INNER3", "PROFILE3",
           "OUTER4", "INNER4", "PROFILE4", "OUTER5", "INNER5", "PROFILE5",
           "HXLPAIR", "HXRPAIR"):
    r = REF_SCALE[ax]
    P(f"      {ax} 2*L s36/s38/s39/s51 = {r['s36']}/{r['s38']}/{r['s39']}/{r['s51']} "
      f"(L {fmt_ht(r['s36'])}/{fmt_ht(r['s38'])}/{fmt_ht(r['s39'])}/{fmt_ht(r['s51'])})")
P("   D3 the s36-vs-s51 HS hinge-side-pair level contrast table")
P("      over all 18 ok cells (per cell: HSL 2*L pair and HSR 2*L")
P("      pair with the s36-vs-s51 contrasts; 18 descriptive rows,")
P("      UNCORRECTED for multiplicity, no")
P("      letter):")
d3 = {}
for win in ("s36", "s51"):
    rows_l, rows_r = [], []
    for i in range(12):
        runs = [3 * i + 1, 3 * i + 2, 3 * i + 3]
        xs = [[] for _ in ok_cells]
        for r in runs:
            for s in data[(win, "tw", r)][2]:
                xs[cell_pos[s[1]]].append(s[2])
        pooled_t = np.array(xs, dtype=np.int64)                    # (18,75)
        dhslo, dhsro = pair_ds(pooled_t)
        rows_l.append(dhslo)
        rows_r.append(dhsro)
    rsl = np.sort(np.array(rows_l), axis=0)
    rsr = np.sort(np.array(rows_r), axis=0)
    d3[win] = (rsl[5] + rsl[6], rsr[5] + rsr[6])                   # (18,) each
for ci, k in enumerate(ok_cells):
    l36, l51 = int(d3["s36"][0][ci]), int(d3["s51"][0][ci])
    r36, r51 = int(d3["s36"][1][ci]), int(d3["s51"][1][ci])
    P(f"      tw cell {ckey_str(k)}: HSL 2*L {l36}/{l51} HSR 2*L {r36}/{r51} "
      f"(C_HSL {fmt_ht(l36 - l51)}, C_HSR {fmt_ht(r36 - r51)})")
P("")

P("7. VERDICT SUMMARY:")
P(f"   T13 = {t13}" + (f" (named: {t13why}: {', '.join(t13fails)})" if (t13fails or t13why)
                       else ""))
for wa, wb in PAIRS:
    for ax in AXES:
        (la, lb, c_obs, cnt, pval) = prim[wb][ax]
        P(f"   {wa}-vs-{wb} {ax}: C_obs = {fmt_ht(c_obs)} (2*C_obs = {c_obs}; "
          f"HS {ax} 2*L {la} -> {lb}); "
          f"count {cnt}/{TRIALS + 1}; p {pval:.6f}; "
          f"letter {contrast_letter(c_obs, pval)}")
P(f"   evaluable inputs: vector reproduction EXACT ({vec_ok}); anchor")
P(f"   rows EXACT ({anchor_ok}); C1 all four windows "
  f"({'(a)' if c1_ok else '(b)'}); per-window integrity rows in section 1")
P("   (NAMED, NOT HIDDEN: no D1 prior check -- fresh prediction).")
P("   ANALYSIS session: NO new hardware, NO new runs, NO builds this")
P("   tick (all four windows are prior sessions' committed logs).")
P("   THE BAR: NO new ledger line (no runs this session; no bar")
P("   candidate exists to log); NO day-slot consumption (the")
P("   2026-10-28 slot is s31's); the frozen evaluator is the only")
P("   source of the bar letter (bar-eval-s63.txt); verdict stays")
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
P("   (NEW hardware; the slot opens at 2026-10-29T00:00:00Z, ~4h51m")
P("   after this tick -- NAMED, not skipped silently); then the")
P("   s38 hi (sum,256,S=32) wander replication (NEW hardware --")
P("   W5's hi runs). NAMED, NOT HIDDEN: with this probe the four-")
P("   rank vocabulary is EXHAUSTED and the rank-pair program over")
P("   it is COMPLETE and RETIRED -- any further rank-pair probe")
P("   requires a NEW named vocabulary/selection rule (none exists")
P("   yet -- naming one is future design work).")
P("   Rule 4 binds: nothing moves; accelerator-targets defaults")
P("   remain provisional (:measured? false); NO vendor optimization")
P("   exists for Intel.")

open(os.path.join(HERE, "publication-s63.txt"), "w").write("\n".join(out) + "\n")
