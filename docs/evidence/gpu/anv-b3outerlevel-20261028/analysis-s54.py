#!/usr/bin/env python3
"""JUN-59 session 54 analysis -- THE NAMED-CELL OUTER-QUANTILE-PAIR
LEVEL PROBE (the named outer counterpart of session 53's inner-
quantile-pair row; over the SAME four windows s36/s38/s39/s51 of the
named-cell robust-scale level campaign, ANALYSIS only -- does the
tw arm's (max,128,S=default) cell's OUTER-QUANTILE-PAIR spread
level, a third robust-scale level at a quantile-pair location
straddling OUTSIDE the frozen IQR hinges, also distinguish the s36
pre-shift window from each post-shift window, and does it move WITH
the frozen MAD/IQR scale levels?).

Route (frozen in protocol.txt section 6): this script parses ONLY
the committed run logs of the four fixed evidence directories and
writes publication-s54.txt in its own directory. Deterministic:
running it twice yields byte-identical output.

The primary statistic (named cell only): block = 3 consecutive
runs of the tw arm within one window (the s35/s36-frozen block
unit); D = the block's OUTER-QUANTILE-PAIR spread over the pooled
75 samples = x_(67) - x_(9) (ranks symmetric about the deviation-
center x_(38), strictly OUTSIDE the s47-frozen IQR hinges x_(19),
x_(57); exact INTEGER); L_w = median of the 12 block D values of
window w (2*L = 6th + 7th order statistics, INTEGER half-tick
units); 2*C_w,obs = 2*L_s36 - 2*L_w (signed; the pre-registered
direction is C > 0, fixed by the prior published MAD/IQR scale
letters -- QUOTE-ONLY priors -- NOT by any outer-pair statistic).
THREE named contrasts: (s36,s38), (s36,s39), (s36,s51). The
resampling null (frozen): per contrast the 72 tw runs of the two
named windows exchangeable; per trial one rng.shuffle of a fresh
list(range(72)) split into two pseudo-windows of 36 and 12
pseudo-blocks of 3 in draw order; p = (1 + count(C* >= C_obs)) /
(1 + 20,000), ONE-SIDED. One random.Random(2026102804), consumed
in the frozen probe order: (s36,s38), (s36,s39), (s36,s51).
numpy 2.5.4 (int64 np.sort) is the frozen implementation path; the
resampling is vectorized over TRIAL BATCHES (batch size a memory
detail, NOT part of the frozen contract); every C* >= C_obs
comparison is exact INTEGER arithmetic. Joint T4 = the pre-
registered INTERSECTION-UNION rule (all three contrasts (a); NO
multiplicity correction).
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
SEED = 2026102804
BATCH = 50
COMMITTED_C8 = 32915
NAMED_CKEY = ("max", 128, "default")
PAIRS = [("s36", "s38"), ("s36", "s39"), ("s36", "s51")]

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
# ---- INNERPAIR: publication-s53 D1; 2*L half-tick units; ----
# ---- QUOTE-ONLY, NOT recomputed by this probe) ----
REF_SCALE = {"MAD": {"s36": 143, "s38": 111, "s39": 113, "s51": 118},
             "IQR": {"s36": 303, "s38": 241, "s39": 235, "s51": 240},
             "CENTER": {"s36": 2833, "s38": 2845, "s39": 2826, "s51": 2825},
             "INNERPAIR": {"s36": 118, "s38": 102, "s39": 128, "s51": 113}}

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

def outer_d(pooled75):
    """(...,75) int64 -> exact INTEGER block OUTER-QUANTILE-PAIR spread
    D = x_(67) - x_(9) (ranks symmetric about x_(38), strictly outside
    the IQR hinges x_(19), x_(57))."""
    srt = np.sort(pooled75, axis=-1)
    return srt[..., 66] - srt[..., 8]

out = []
P = out.append
P("JUN-59 session 54 -- THE NAMED-CELL OUTER-QUANTILE-PAIR LEVEL")
P("PROBE (publication)")
P("(the named outer counterpart of session 53's inner-quantile-pair")
P("row; over the SAME four windows s36/s38/s39/s51 of the named-cell")
P("robust-scale level campaign, ANALYSIS only -- does the tw arm's")
P("(max,128,S=default) cell's OUTER-QUANTILE-PAIR spread level, a")
P("third robust-scale level at a quantile-pair location straddling")
P("OUTSIDE the frozen IQR hinges, also distinguish the s36 pre-shift")
P("window from each post-shift window, and does it move WITH the")
P("frozen MAD/IQR scale levels? THREE named contrasts (s36 vs s38,")
P("s36 vs s39, s36 vs s51), ONE-SIDED each in the pre-registered")
P("direction C > 0 (scale-drop continuation; the direction is fixed")
P("by the prior published MAD/IQR scale letters, QUOTE-ONLY priors,")
P("NOT by any outer-pair statistic), joint T4 = the pre-registered")
P("INTERSECTION-UNION rule (all three (a); NO multiplicity")
P("correction).)")
P("Produced ONLY by analysis-s54.py over the COMMITTED run logs of")
P("four fixed evidence directories (anv-b3commonmode-20261028 =")
P("the s36 window, anv-b3joint3-20261028 = the s38 window,")
P("anv-b3joint4-20261028 = the s39 window, anv-b3levelrep-20261028")
P("= the s51 window); protocol.txt was frozen BEFORE any statistic")
P("of this probe was computed (freeze stamp 2026-10-28T14:35:25Z).")
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
# the PRIMARY probe (protocol sections 1/2/3): the named cell's
# three two-window outer-quantile-pair contrasts
# ------------------------------------------------------------------
rng = random.Random(SEED)

named_arr = {}
for win, _d in WINDOWS:
    named_arr[win] = run_arr(win, "tw")[:, [nc_pos], :][:, 0, :]   # (36,25)

def contrast(wa, wb):
    flat = np.vstack([named_arr[wa], named_arr[wb]])               # (72,25)
    obs = np.arange(72, dtype=np.int64).reshape(1, 2, 12, 3)
    sub = flat[obs].reshape(1, 2, 12, 75)
    d_obs = outer_d(sub)[0]                                        # (2,12)
    l2_obs = np.sort(d_obs, axis=1)[:, 5] + np.sort(d_obs, axis=1)[:, 6]  # (2,)
    c_obs = int(l2_obs[0] - l2_obs[1])
    perms = np.empty((TRIALS, 72), dtype=np.int64)
    for t in range(TRIALS):
        perm = list(range(72))
        rng.shuffle(perm)
        perms[t] = perm
    cnt = 0
    for i in range(0, TRIALS, BATCH):
        batch = perms[i:i + BATCH].reshape(-1, 2, 12, 3)
        sub = flat[batch].reshape(-1, 2, 12, 75)
        d = outer_d(sub)                                           # (b,2,12)
        ds = np.sort(d, axis=2)
        l2 = ds[:, :, 5] + ds[:, :, 6]                             # (b,2)
        c = l2[:, 0] - l2[:, 1]
        cnt += int((c >= c_obs).sum())
    p = (1 + cnt) / (1 + TRIALS)
    return l2_obs, c_obs, cnt, p

prim = {}
for wa, wb in PAIRS:
    prim[wb] = contrast(wa, wb)

def contrast_letter(c_obs, p):
    if c_obs > 0 and p <= 0.05:
        return "(a) OUTER-DIFFERENT-CONTINUED"
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
    letters = {wb: contrast_letter(prim[wb][1], prim[wb][3]) for _, wb in PAIRS}
    fails = [wb for _, wb in PAIRS if not letters[wb].startswith("(a)")]
    if fails:
        return "(b) NOT-SHIFTED-CONSISTENT", fails, "pair(s) not (a)"
    return "(a) OUTER-SPREAD-LEVEL-SHIFTED-CONSISTENT", [], ""

P("4. T4 THE ROW QUESTION (frozen letters, protocol sections 0/1/2/3):")
P(f"   the NAMED cell {ckey_str(nc)} of the tw arm, the NAMED window")
P("   contrasts s36 (pre-shift) vs each of s38/s39/s51, ONE-SIDED")
P("   each in the pre-registered direction C > 0 (scale-drop")
P("   continuation; direction fixed by prior published MAD/IQR")
P("   scale letters -- QUOTE-ONLY -- NOT by any outer-pair")
P("   statistic), on the NAMED outer-quantile-pair axis (D =")
P("   x_(67) - x_(9) of the block's pooled 75; L = median of 12")
P("   block D values; 2*C = 2*L_s36 - 2*L_w in half-tick integer")
P(f"   units). {TRIALS} trials, seed {SEED}, frozen probe order")
P("   (s36,s38), (s36,s39), (s36,s51); per trial one shuffle of")
P("   list(range(72)) split into two pseudo-windows of 36 and 12")
P("   blocks of 3; p = (1 + count(C* >= C_obs)) / (1 + 20,000),")
P(f"   ONE-SIDED; joint T4 = the pre-registered INTERSECTION-UNION")
P("   rule (all three contrasts (a); NO multiplicity correction")
P("   applied or needed):")
for wa, wb in PAIRS:
    l2_obs, c_obs, cnt, p = prim[wb]
    P(f"   {wa}-vs-{wb}: 2*L_{wa} = {int(l2_obs[0])} ({fmt_ht(int(l2_obs[0]))}), "
      f"2*L_{wb} = {int(l2_obs[1])} ({fmt_ht(int(l2_obs[1]))}); "
      f"C_obs = {fmt_ht(c_obs)} (2*C_obs = {c_obs}); count {cnt} / {TRIALS + 1}; "
      f"p = {p:.6f}; p <= 0.05: {p <= 0.05}; "
      f"contrast letter {contrast_letter(c_obs, p)}")
t4, t4fails, t4why = joint_letter()
P(f"   T4 = {t4}" + (f" (named: {t4why}: {', '.join(t4fails)})" if (t4fails or t4why)
                     else ""))
P("   NAMED, NOT HIDDEN: this probe examines a SIXTH axis on the")
P("   SAME window data (after the s48 MAD / s47 IQR scale axes, the")
P("   s49/s50/s51 descriptive families, s52's deviation-center")
P("   axis and s53's inner-quantile-pair axis); the axis/pair/")
P("   direction choice and the three-pair contrast set were made")
P("   AFTER the scale, center and inner-pair results on these")
P("   windows were known; the probe is a SEPARATE named family and")
P("   does NOT retro-correct any earlier uncorrected family; the")
P("   three contrasts share the s36 window (the pairwise tests are")
P("   dependent; the IUT does not care); (a) names NO mechanism")
P("   (thermal/scheduling/memory/driver state all UNMEASURED) and")
P("   NOT whether any movement is physical or estimator structure")
P("   -- (a) on the outer pair COMBINED WITH s53's inner-pair (b)")
P("   is CONSISTENT WITH a change confined to the outer spread; (a)")
P("   on both pairs is CONSISTENT WITH a whole-spread compression;")
P("   (b) on the outer pair is CONSISTENT WITH a change localized")
P("   at the hinges/edges (estimator structure); EITHER WAY")
P("   threshold-artifact-vs-representation and physical-vs-")
P("   estimator-structure STAY UNRESOLVED; the four windows span")
P("   ~8.5 hours in ONE UTC day on ONE host (LOW POWER; any")
P("   window-specific state can produce any letter); 20,000 trials")
P("   (NOT the s35-frozen 100,000 -- cost, same named deviation as")
P("   sessions 40-53; p resolution 1/20,001 ~= 5e-5); the rank pair")
P("   (9,67) is NAMED by pre-registration and NOT canonical (no")
P("   prior publication fixes a quantile pair beyond the IQR")
P("   hinges and the s53 inner pair); L2 observational ONLY; NO")
P("   causal mechanism; anything off the ANV host UNMEASURED.")
P("")

P("5. REPLICATION FRAMING (frozen): the row answer is the section-4")
P("   joint T4; the axis is the named cell's within-block outer-")
P("   quantile-pair spread level ONLY; the per-contrast letters and")
P("   sub-cases are in section 4.")
P("")

P("6. DESCRIPTIVE (not the row question; NO letter):")
P("   D1 the NAMED cell's four-window OUTER-QUANTILE-PAIR level")
P(f"      vectors ({ckey_str(nc)}, tw arm; L = median of the 12 block D")
P("      values, half-tick exact; the 12 block D values per window")
P("      are printed for the census; NEW axis, no priors exist):")
for win, _d in WINDOWS:
    ds = []
    for i in range(12):
        runs = [3 * i + 1, 3 * i + 2, 3 * i + 3]
        xs = []
        for r in runs:
            xs += [s[2] for s in data[(win, "tw", r)][2] if s[1] == nc]
        ds.append(int(outer_d(np.array(xs, dtype=np.int64))))
    l2 = sorted(ds)[5] + sorted(ds)[6]
    P(f"      {win}: 2*L = {l2} ({fmt_ht(l2)}); block D values: "
      + " ".join(str(v) for v in ds))
P("   D2 the frozen-scale, center and inner-pair level context")
P("      (QUOTE-ONLY priors of publication-s49/50/51 D1,")
P("      publication-s52 D1 and publication-s53 D1 -- NOT")
P("      recomputed by this probe; interpretation only: the")
P("      MAD/IQR scale levels dropped s36 -> s38/s39/s51 on both")
P("      frozen scale axes and the center level held, while D1")
P("      shows the outer-pair level):")
for ax in ("MAD", "IQR", "CENTER", "INNERPAIR"):
    r = REF_SCALE[ax]
    P(f"      {ax} 2*L s36/s38/s39/s51 = {r['s36']}/{r['s38']}/{r['s39']}/{r['s51']} "
      f"(L {fmt_ht(r['s36'])}/{fmt_ht(r['s38'])}/{fmt_ht(r['s39'])}/{fmt_ht(r['s51'])})")
P("   D3 the s36-vs-s51 OUTER-QUANTILE-PAIR contrast table over all")
P("      18 ok cells (C = 2*L_s36 - 2*L_s51 per cell; 18 descriptive")
P("      contrasts, UNCORRECTED for multiplicity, no letter):")
ctr = {}
for win in ("s36", "s51"):
    rows = []
    for i in range(12):
        runs = [3 * i + 1, 3 * i + 2, 3 * i + 3]
        xs = [[] for _ in ok_cells]
        for r in runs:
            for s in data[(win, "tw", r)][2]:
                xs[cell_pos[s[1]]].append(s[2])
        pooled_t = np.array(xs, dtype=np.int64)                    # (18,75)
        rows.append(outer_d(pooled_t))
    rows = np.array(rows)                                          # (12,18)
    rs = np.sort(rows, axis=0)
    ctr[win] = rs[5] + rs[6]                                       # (18,)
for ci, k in enumerate(ok_cells):
    l36 = int(ctr["s36"][ci])
    l51 = int(ctr["s51"][ci])
    P(f"      tw cell {ckey_str(k)}: OUTERPAIR 2*L {l36}/{l51} C {fmt_ht(l36 - l51)}")
P("")

P("7. VERDICT SUMMARY:")
P(f"   T4 = {t4}" + (f" (named: {t4why}: {', '.join(t4fails)})" if (t4fails or t4why)
                     else ""))
for wa, wb in PAIRS:
    l2_obs, c_obs, cnt, p = prim[wb]
    P(f"   {wa}-vs-{wb}: C_obs = {fmt_ht(c_obs)} (2*L_{wa} {int(l2_obs[0])} -> "
      f"2*L_{wb} {int(l2_obs[1])}); count {cnt}/{TRIALS + 1}; p {p:.6f}; "
      f"letter {contrast_letter(c_obs, p)}")
P(f"   evaluable inputs: vector reproduction EXACT ({vec_ok}); anchor")
P(f"   rows EXACT ({anchor_ok}); C1 all four windows "
  f"({'(a)' if c1_ok else '(b)'}); per-window integrity rows in section 1")
P("   ANALYSIS session: NO new hardware, NO new runs, NO builds this")
P("   tick (all four windows are prior sessions' committed logs).")
P("   THE BAR: NO new ledger line (no runs this session; no bar")
P("   candidate exists to log); NO day-slot consumption (the")
P("   2026-10-28 slot is s31's); the frozen evaluator is the only")
P("   source of the bar letter (bar-eval-s54.txt); verdict stays")
P("   PENDING 1/4 with s31 counted; next executable day slot")
P("   2026-10-29.")
P("   UNMEASURED (named): what moves the per-cell robust-scale")
P("   level on the tw arm (no mechanism named by any letter);")
P("   whether any movement is physical or estimator structure;")
P("   whether four counted days settle the bar (PENDING 1/4); the")
P("   s31/s34/s36 excursion causes; threshold-artifact-vs-")
P("   representation; anything off the ANV host. NAMED CANDIDATE")
P("   ROWS for later sessions: (first) the INNER-vs-OUTER")
P("   COMPRESSION-PROFILE read over the same windows (the formal")
P("   juxtaposition of the two named quantile-pair level axes --")
P("   analysis; no hardware; available on any tick); then a")
P("   FIFTH-window replication on another UTC day (needs NEW")
P("   hardware; the bar's next day slot 2026-10-29 is then")
P("   reachable); the s38 hi (sum,256,S=32) wander replication.")
P("   Rule 4 binds: nothing moves; accelerator-targets defaults")
P("   remain provisional (:measured? false); NO vendor optimization")
P("   exists for Intel.")

open(os.path.join(HERE, "publication-s54.txt"), "w").write("\n".join(out) + "\n")
