#!/usr/bin/env python3
"""JUN-59 session 51 analysis -- THE FOURTH-WINDOW NAMED-CELL
ROBUST-SCALE LEVEL REPLICATION PROBE (at the NEW fourth window s51
measured this session on the ANV host, does the tw arm's
(max,128,S=default) cell's robust-scale LEVEL continue the
post-shift regime of s38/s39 rather than return to the s36
pre-shift regime, on BOTH robust-scale level axes -- the s48-frozen
exact-median MAD and the s47-frozen exclusive-hinge IQR?).
MEASUREMENT session: the s51 inputs are this session's 78 committed
run logs; the s36/s38/s39 inputs are the committed run logs of
sessions 36/38/39.

Route (frozen in protocol.txt section 6): this script parses ONLY
the committed run logs of the four fixed evidence directories and
writes publication-s51.txt in its own directory. Deterministic:
running it twice yields byte-identical output.

The primary statistic (named cell only; per axis): block = 3
consecutive runs of the tw arm within one window (the s35/s36-
frozen block unit); D = the block's within-block robust scale over
the pooled 75 samples -- MAD axis: e_(38) about m = x_(38) (the
s48-frozen exact-median MAD, exact INTEGER); IQR axis: x_(57) -
x_(19) (the s47-frozen exclusive-hinge IQR, exact INTEGER);
L_w = median of the 12 block D values of window w (2*L = 6th + 7th
order statistics, INTEGER half-tick units); 2*C_obs = 2*L_s36 -
2*L_s51 (the pre-registered direction C > 0). The resampling null
(frozen): the 72 tw runs of the two named windows exchangeable;
per trial one rng.shuffle of a fresh list(range(72)) split into two
pseudo-windows of 36 and 12 pseudo-blocks of 3 in draw order;
p = (1 + count(C* >= C_obs)) / (1 + 20,000), one-sided in the
pre-registered direction. One random.Random(20261028), consumed in
the frozen probe order: primary MAD, primary IQR, D3 MAD-hi, D3
MAD-tw, D3 IQR-hi, D3 IQR-tw. numpy 2.5.4 (int64 np.sort) is the
frozen implementation path; the resampling is vectorized over
TRIAL BATCHES (batch size a memory detail, NOT part of the frozen
contract); every C* >= C_obs comparison is exact INTEGER arithmetic
in half-tick units.
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
SEED = 20261028
BATCH = 50
COMMITTED_C8 = 32915
NAMED_CKEY = ("max", 128, "default")

# ---- quote-only frozen reference vectors (publication-s39.txt
# ---- section 3: s39 published + s36/s38 quote-only) ----
REF_X = {"s39": [986, 991, 984, 985, 989, 989, 986, 990, 995, 986, 987, 981],
         "s36": [991, 989, 981, 998, 993, 985, 984, 997, 994, 994, 980, 982],
         "s38": [992, 988, 984, 1007, 985, 984, 986, 983, 992, 991, 982, 997]}
REF_Y = {"s39": [988, 989, 987, 990, 990, 988, 991, 983, 985, 988, 983, 986],
         "s36": [988, 985, 994, 993, 994, 995, 992, 984, 987, 984, 993, 981],
         "s38": [988, 987, 980, 980, 991, 994, 991, 994, 988, 991, 1001, 992]}
# ---- quote-only anchor priors (protocol section 3) ----
REF_ANCHOR = {"s36": (1142, 991, 1438),
              "s38": (1132, 992, 1443),
              "s39": (1146, 986, 1432)}
# ---- quote-only named-cell level priors (publication-s49.txt /
# ---- publication-s50.txt section 6 D1; the s49 MAD-level and s50
# ---- IQR-level L of the NAMED cell at s36/s38/s39; 2*L in
# ---- half-tick integer units; D1 orientation + reproduction) ----
REF_NAMED = {"MAD": {"s36": 143, "s38": 111, "s39": 113},
             "IQR": {"s36": 303, "s38": 241, "s39": 235}}
# ---- quote-only s49/s50 max-T priors (D3 orientation only) ----
REF_S49 = {"hi": ("10.0", 0.473426, "(min,256,S=16)"),
           "tw": ("16.0", 0.008600, "(max,128,S=default)")}
REF_S50 = {"hi": ("35.5", 0.083896, "(min,256,S=16)"),
           "tw": ("34.0", 0.611969, "(max,128,S=default)")}

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

def med(xs):
    return statistics.median(xs)

def fmt_ht(x2):
    return f"{x2 / 2:.1f}"

# ------------------------------------------------------------------
# parse the four windows; integrity per protocol section 3
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

def block_d(pooled75):
    """(...,75) int64 -> exact INTEGER block robust scale per axis.
    MAD: e_(38) about m = x_(38); IQR: x_(57) - x_(19)."""
    srt = np.sort(pooled75, axis=-1)
    med75 = srt[..., 37]
    dev = np.abs(pooled75 - med75[..., None])
    dsrt = np.sort(dev, axis=-1)
    return dsrt[..., 37], srt[..., 56] - srt[..., 18]

out = []
P = out.append
P("JUN-59 session 51 -- THE FOURTH-WINDOW NAMED-CELL ROBUST-SCALE")
P("LEVEL REPLICATION PROBE (publication)")
P("(at the NEW fourth window s51, does the tw arm's")
P("(max,128,S=default) cell's robust-scale LEVEL continue the")
P("post-shift regime of s38/s39 rather than return to the s36")
P("pre-shift regime, on BOTH robust-scale level axes -- the")
P("s48-frozen exact-median MAD and the s47-frozen exclusive-hinge")
P("IQR? ONE named cell, ONE named window pair (s36 vs s51), ONE")
P("named direction (L_s51 < L_s36), TWO named axes under a")
P("pre-registered intersection-union joint rule; the primary")
P("per-axis statistic C = L_s36 - L_s51 vs a two-window")
P("run-repartition resampling null over the named cell's 72 tw")
P("committed runs of the two windows.)")
P("Produced ONLY by analysis-s51.py over the COMMITTED run logs of")
P("four fixed evidence directories (anv-b3commonmode-20261028 =")
P("the s36 window, anv-b3joint3-20261028 = the s38 window,")
P("anv-b3joint4-20261028 = the s39 window, anv-b3levelrep-20261028")
P("= the NEW s51 window measured THIS session); protocol.txt was")
P("frozen BEFORE the first s51 run and before any statistic of")
P("this probe was computed (freeze stamp 2026-10-28T11:42:02Z).")
P("MEASUREMENT session -- the s51 window ran on aiueos-6600hs")
P("Intel BMG G31 ANV at 2026-10-28T11:45:26Z..11:46:13Z (78 fresh")
P("processes; the s36/s38/s39 windows were MEASURED in sessions")
P("36/38/39 at 2026-10-28T02:40:49Z / 03:39:14Z / 04:09:48Z).")
P("")

P("1. INTEGRITY (computed over each window's committed logs;")
P("   protocol section 3):")
for win, _d in WINDOWS:
    info = win_info[win]
    nlogs = 3 + 36 + 36 + 3
    P(f"   {win}: runs parsed {nlogs}; VERIFY mismatch total {info['vmis']}; "
      f"counts ok {info['counts_ok']}; knobs ok {info['knob_ok']}; "
      f"S=8 fail-closed {info['fail_ok']}; cell map ok {info['cmap_ok']}")
    for pr in info["problems"]:
        P(f"   !! {pr}")
P("   INVALIDATION criterion (protocol section 3): any violation =>")
P("   letter (c).")
P("")

# ---- C1 at the s51 window ----
c2_vals = block_vals("s51", "c2", ARMS["c2"][3])
c2_cls = "FLOOR" if all(v <= 100 for v in c2_vals) else (
    "CAPTURED" if all(v >= 1000 for v in c2_vals) else "INTERMEDIATE/MIXED")
c8_m = pooled("s51", "c8", sum128, ARMS["c8"][3], 2)
c1_ok = (c2_cls == "FLOOR") and abs(c8_m - COMMITTED_C8) <= 0.05 * COMMITTED_C8
P("2. C1 RE-DERIVATION (environment pin, from the s51 window's logs):")
P(f"   c2 class: {c2_cls} (FLOOR required; committed floor band 31..32)")
P(f"   c8 (sum,128,S=16) pooled median {c8_m:.0f} vs committed {COMMITTED_C8} "
  f"({abs(c8_m - COMMITTED_C8) / COMMITTED_C8 * 100:.2f}% delta; +/-5% required)")
P(f"   C1 branch: {'(a) both controls replicate' if c1_ok else '(b) discrepancy'}")
P("")

# ---- block-min vectors (3 prior reproduction + s51 fresh) ----
vec = {}
vec_ok = True
for win, _d in WINDOWS:
    X = [block_min(win, "hi", [3 * i + 1, 3 * i + 2, 3 * i + 3]) for i in range(12)]
    Y = [block_min(win, "tw", [3 * i + 1, 3 * i + 2, 3 * i + 3]) for i in range(12)]
    vec[win] = (X, Y)
    if win != "s51" and ([int(v) for v in X] != REF_X[win] or [int(v) for v in Y] != REF_Y[win]):
        vec_ok = False
P("3. THE BLOCK-MIN VECTORS (re-derived from the committed logs; block")
P("   order A..L; the three PRIOR windows reproduce the")
P("   published/quote-only vectors of publication-s39.txt section 3")
P("   EXACTLY (mismatch => (c)); the s51 vectors are NEW measurement:")
for win, _d in WINDOWS:
    X, Y = vec[win]
    P(f"   {win} X (hi): " + " ".join(f"{int(v)}" for v in X))
    P(f"   {win} Y (tw): " + " ".join(f"{int(v)}" for v in Y))
    if win != "s51":
        P(f"   {win} reproduction EXACT: "
          f"{[int(v) for v in X] == REF_X[win] and [int(v) for v in Y] == REF_Y[win]}")
P(f"   all three prior windows reproduce EXACTLY: {vec_ok}")
P("")

# ---- anchor rows: 3 prior reproduction + s51 fresh (D4) ----
anchor_ok = True
anchor_rows = {}
for win, _d in WINDOWS:
    a_med = pooled(win, "hi", sum128, [1, 2, 3], 2)
    bvals = [int(v) for v in block_vals(win, "hi", [1, 2, 3])]
    a_min, a_max = min(bvals), max(bvals)
    anchor_rows[win] = (a_med, a_min, a_max)
    if win != "s51" and (a_med, a_min, a_max) != REF_ANCHOR[win]:
        anchor_ok = False
P("3b. ANCHOR ROWS (hi block A -- the frozen L12 single bar candidate:")
P("    its (sum,128,S=16) pooled median and 18-cell min..max; the")
P("    three PRIOR windows reproduce the quote-only anchor priors of")
P("    publication-s36/38/39 section D EXACTLY (mismatch => (c)); the")
P("    s51 row is NEW measurement -- the session's bar candidate,")
P("    section 4 D4):")
for win, _d in WINDOWS:
    a_med, a_min, a_max = anchor_rows[win]
    if win != "s51":
        P(f"    {win}: median {a_med:.0f} min..max {a_min}..{a_max} "
          f"(want {REF_ANCHOR[win][0]} / {REF_ANCHOR[win][1]}..{REF_ANCHOR[win][2]}); "
          f"reproduction EXACT: {(a_med, a_min, a_max) == REF_ANCHOR[win]}")
    else:
        bA = [int(v) for v in block_vals(win, "hi", [1, 2, 3])]
        s_cls = "FLOOR" if all(v <= 100 for v in bA) else (
            "CAPTURED" if all(v >= 1000 for v in bA) else "INTERMEDIATE/MIXED")
        P(f"    {win} (NEW): median {a_med:.0f} min..max {a_min}..{a_max}; "
          f"class {s_cls}")
P(f"    all three prior windows reproduce EXACTLY: {anchor_ok}")
P("")

# ------------------------------------------------------------------
# the PRIMARY probes (protocol sections 0/2): the named cell's
# two-window directional contrast, per axis
# ------------------------------------------------------------------
rng = random.Random(SEED)

named_arr = np.vstack([run_arr("s36", "tw")[:, [nc_pos], :],
                       run_arr("s51", "tw")[:, [nc_pos], :]])   # (72,1,25)
named_flat = named_arr[:, 0, :]                                  # (72,25)

def primary(axis):
    obs = np.arange(72, dtype=np.int64).reshape(1, 2, 12, 3)
    sub = named_flat[obs].reshape(1, 2, 12, 75)
    d_obs, _ = block_d(sub)                       # (1,2,12) both axes, take one
    d_obs = d_obs[0] if axis == "MAD" else _[0]
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
        sub = named_flat[batch].reshape(-1, 2, 12, 75)
        dm, di = block_d(sub)
        d = dm if axis == "MAD" else di
        ds = np.sort(d, axis=2)
        l2 = ds[:, :, 5] + ds[:, :, 6]            # (b,2)
        c = l2[:, 0] - l2[:, 1]
        cnt += int((c >= c_obs).sum())
    p = (1 + cnt) / (1 + TRIALS)
    return d_obs, l2_obs, c_obs, cnt, p

prim = {}
prim["MAD"] = primary("MAD")
prim["IQR"] = primary("IQR")

def axis_letter(axis):
    _d, _l2, c_obs, _cnt, p = prim[axis]
    if invalidated():
        return "(c) NOT EVALUABLE"
    if c_obs > 0 and p <= 0.05:
        return "(a) REPLICATED-CONTINUED"
    subcase = "DIRECTION-REVERSED" if c_obs <= 0 else \
        "DIRECTION-CONSISTENT-NOT-SIGNIFICANT"
    return f"(b) NOT-REPLICATED [{subcase}]"

# ------------------------------------------------------------------
# the D3 four-window max-T probes (descriptive only, no letter)
# ------------------------------------------------------------------
def cell_d4(triples, arr):
    n = triples.shape[0]
    sub = arr[triples]
    pooled_t = sub.transpose(0, 1, 2, 4, 3, 5).reshape(n, 4, 12, 18, 75)
    dm, di = block_d(pooled_t)
    dsm = np.sort(dm, axis=2)
    dsi = np.sort(di, axis=2)
    l2m = dsm[:, :, 5, :] + dsm[:, :, 6, :]
    l2i = dsi[:, :, 5, :] + dsi[:, :, 6, :]
    return dm, di, l2m, l2i

def probe_d4(axis, tag):
    arr = np.vstack([run_arr(win, tag) for win, _d in WINDOWS])   # (144,18,25)
    obs = np.arange(144, dtype=np.int64).reshape(1, 4, 12, 3)
    _dm, _di, l2m, l2i = cell_d4(obs, arr)
    l2_obs = l2m[0] if axis == "MAD" else l2i[0]                  # (4,18)
    s2_obs = l2_obs.max(axis=0) - l2_obs.min(axis=0)              # (18,)
    m_obs = int(s2_obs.max())
    perms = np.empty((TRIALS, 144), dtype=np.int64)
    for t in range(TRIALS):
        perm = list(range(144))
        rng.shuffle(perm)
        perms[t] = perm
    cnt = 0
    for i in range(0, TRIALS, BATCH):
        batch = perms[i:i + BATCH].reshape(-1, 4, 12, 3)
        _dm, _di, l2m, l2i = cell_d4(batch, arr)
        l2 = l2m if axis == "MAD" else l2i
        s2 = l2.max(axis=1) - l2.min(axis=1)
        m = s2.max(axis=1)
        cnt += int((m >= m_obs).sum())
    p = (1 + cnt) / (1 + TRIALS)
    return s2_obs, m_obs, cnt, p

d4 = {}
for axis in ("MAD", "IQR"):
    for tag in ("hi", "tw"):
        d4[(axis, tag)] = probe_d4(axis, tag)

def invalidated():
    inv = any(win_info[w]["vmis"] != 0 or not win_info[w]["counts_ok"]
              or not win_info[w]["knob_ok"] or not win_info[w]["fail_ok"]
              or not win_info[w]["cmap_ok"] for w, _d in WINDOWS)
    return inv or (not vec_ok) or (not c1_ok) or (not anchor_ok)

def joint_letter():
    if invalidated():
        return "(c) NOT EVALUABLE", []
    hits = [ax for ax in ("MAD", "IQR") if not axis_letter(ax).startswith("(a)")]
    if not hits:
        return "(a) REPLICATED-ON-BOTH-LEVEL-AXES", []
    return "(b) NOT-REPLICATED-ON-BOTH-AXES", hits

P("4. T1 THE ROW QUESTION (frozen letters, protocol sections 0/2):")
P(f"   the NAMED cell {ckey_str(nc)} of the tw arm, the NAMED window")
P("   pair s36 (pre-shift) vs s51 (NEW this session), the NAMED")
P("   direction L_s51 < L_s36, on the two NAMED level axes (MAD =")
P("   e_(38) about x_(38); IQR = x_(57) - x_(19); L = median of 12")
P("   block D values; 2*C = 2*L_s36 - 2*L_s51 in half-tick integer")
P(f"   units). {TRIALS} trials, seed {SEED}, probe order primary MAD")
P("   then primary IQR; per trial one shuffle of list(range(72))")
P("   split into two pseudo-windows of 36 and 12 blocks of 3;")
P(f"   p = (1 + count(C* >= C_obs)) / (1 + {TRIALS}), one-sided in the")
P("   pre-registered direction; joint T1 = the pre-registered")
P("   INTERSECTION-UNION rule (both axes must read (a); NO")
P("   multiplicity correction applied or needed):")
for ax in ("MAD", "IQR"):
    d_obs, l2_obs, c_obs, cnt, p = prim[ax]
    P(f"   {ax} axis: 2*L_s36 = {int(l2_obs[0])} ({fmt_ht(int(l2_obs[0]))}), "
      f"2*L_s51 = {int(l2_obs[1])} ({fmt_ht(int(l2_obs[1]))}); "
      f"C_obs = {fmt_ht(c_obs)}; count {cnt} / {TRIALS + 1}; p = {p:.6f}; "
      f"p <= 0.05: {p <= 0.05}; axis letter {axis_letter(ax)}")
t1, t1hits = joint_letter()
P(f"   T1 = {t1}" + (f" (named axis(es) not replicated: {', '.join(t1hits)})"
                     if t1hits else ""))
P("   NAMED, NOT HIDDEN: the multiplicity claim is NARROW -- ONE")
P("   named cell, ONE named window pair, ONE named direction, TWO")
P("   named axes under a pre-registered IUT, tested on NEW data")
P("   (the s51 runs did not exist at freeze time); it carries NO")
P("   within-family multiplicity of its own, BUT the cell/direction")
P("   choice was made by looking at s40-50's UNCORRECTED-family")
P("   results, the discovery family STAYS uncorrected and this")
P("   replication does NOT retro-correct it; s38/s39 are the")
P("   DISCOVERY windows and appear ONLY in section 6 D1; (a) would")
P("   NOT name a mechanism (thermal/scheduling/memory/driver state")
P("   all UNMEASURED) and NOT say whether the level shift is")
P("   physical or estimator structure; the window pair spans ~8.5")
P("   hours in ONE UTC day on ONE host (n=2 windows, 12 blocks each")
P("   -- LOW POWER; a single (a) can also reflect any s36-specific")
P("   or s51-specific state); (b) does NOT overturn s49's discovery")
P("   (b) -- it says the pre-registered directional contrast did")
P("   not replicate at THIS window pair (sub-cases named above);")
P("   the estimator is the named cell's within-block robust scale")
P("   level ONLY; 20,000 trials (NOT the s35-frozen 100,000 --")
P("   cost, same named deviation as sessions 40-50; p resolution")
P("   1/20,001 ~= 5e-5); L2 observational ONLY; NO causal")
P("   mechanism; direction UNMEASURED;")
P("   threshold-artifact-vs-representation STAYS UNRESOLVED under")
P("   any letter.")
P("")

P("5. REPLICATION FRAMING (frozen): the row answer is the section-4")
P("   joint T1; the two axes are the two named robust scales (NEITHER")
P("   dominates -- a shift of one need not move the other) and the")
P("   IUT rule demands both; the per-axis letters and sub-cases are")
P("   in section 4.")
P("")

P("6. DESCRIPTIVE (not the row question; NO letter):")
P("   D1 the NAMED cell's four-window level vectors on both axes")
P(f"      ({ckey_str(nc)}, tw arm; L = median of the 12 block D values,")
P("      half-tick exact; prior windows reproduce the quote-only")
P("      s49/s50 D1 priors EXACTLY -- a reproduction check on the")
P("      prior windows, descriptive) and the s51-vs-discovery-pair")
P("      consistency (L_51 inside the closed interval spanned by")
P("      {L_s38, L_s39}):")
for ax in ("MAD", "IQR"):
    # prior-window L for the named cell, computed from the logs
    l2_prior = {}
    for win in ("s36", "s38", "s39"):
        ds = []
        for i in range(12):
            runs = [3 * i + 1, 3 * i + 2, 3 * i + 3]
            xs = []
            for r in runs:
                xs += [s[2] for s in data[(win, "tw", r)][2] if s[1] == nc]
            dm, di = block_d(np.array(xs, dtype=np.int64))
            ds.append(int(dm) if ax == "MAD" else int(di))
        ds.sort()
        l2_prior[win] = ds[5] + ds[6]
    d_obs, l2_obs, _c, _cnt, _p = prim[ax]
    l2_prior["s51"] = int(l2_obs[1])
    repro = all(l2_prior[w] == REF_NAMED[ax][w] for w in ("s36", "s38", "s39"))
    lo, hi = sorted([l2_prior["s38"], l2_prior["s39"]])
    inpair = lo <= l2_prior["s51"] <= hi
    P(f"      {ax}: 2*L s36/s38/s39/s51 = {l2_prior['s36']}/{l2_prior['s38']}"
      f"/{l2_prior['s39']}/{l2_prior['s51']} "
      f"(L {fmt_ht(l2_prior['s36'])}/{fmt_ht(l2_prior['s38'])}"
      f"/{fmt_ht(l2_prior['s39'])}/{fmt_ht(l2_prior['s51'])}); prior")
    P(f"      reproduction vs quote-only priors {REF_NAMED[ax]} EXACT: {repro}; "
      f"L_51 inside the s38/s39 pair interval: {inpair}")
P("   D2 the 18-cell scoreboard at s51 on both axes (L_s51 per ok")
P("      cell) and the full s51-vs-s36 per-cell contrast table")
P("      (C = L_s36 - L_s51 per cell per axis; 36 descriptive")
P("      contrasts, UNCORRECTED for multiplicity, no letter):")
d_tbl = {}
for ax in ("MAD", "IQR"):
    for win in ("s36", "s51"):
        rows = []
        for i in range(12):
            runs = [3 * i + 1, 3 * i + 2, 3 * i + 3]
            xs = [[] for _ in ok_cells]
            for r in runs:
                for s in data[(win, "tw", r)][2]:
                    xs[cell_pos[s[1]]].append(s[2])
            # xs: 18 lists of 75
            pooled_t = np.array(xs, dtype=np.int64)               # (18,75)
            dm, di = block_d(pooled_t)
            rows.append(dm if ax == "MAD" else di)
        rows = np.array(rows)                                     # (12,18)
        rs = np.sort(rows, axis=0)
        d_tbl[(ax, win)] = rs[5] + rs[6]                          # (18,)
for ci, k in enumerate(ok_cells):
    cells = []
    for ax in ("MAD", "IQR"):
        l36 = int(d_tbl[(ax, "s36")][ci])
        l51 = int(d_tbl[(ax, "s51")][ci])
        cells.append(f"{ax} 2*L {l36}/{l51} C {fmt_ht(l36 - l51)}")
    P(f"      tw cell {ckey_str(k)}: " + "; ".join(cells))
P("   D3 the FOUR-WINDOW cross-window max-T repartition probes (the")
P("      s49/s50 machinery extended to s36/s38/s39/s51: per-cell")
P("      S_c = max_w L_{w,c} - min_w L_{w,c} over the four windows,")
P("      M = max_c 2*S_c family-wise over the 18 cells; null = the")
P("      144 runs of one arm repartitioned into 4 pseudo-windows of")
P("      36 then 12 blocks of 3; 20,000 trials per probe in the")
P("      frozen RNG order) -- DESCRRIPTIVE ONLY, NO letter (the four")
P("      probes are UNCORRECTED across axes/arms; this session's")
P("      LETTER source is the section-4 named-cell IUT alone):")
for ax in ("MAD", "IQR"):
    for tag in ("hi", "tw"):
        s2, m_obs, cnt, p = d4[(ax, tag)]
        idxs = [ok_cells[i] for i in range(len(ok_cells)) if int(s2[i]) == m_obs]
        mcs = ", ".join(ckey_str(i) for i in idxs)
        P(f"      {ax}-{tag}: M_obs = {fmt_ht(m_obs)} (max cell(s) {mcs}); "
          f"count {cnt} / {TRIALS + 1}; p = {p:.6f}")
P("      orientation quote-only priors (NOT recomputed): s49 MAD-level")
P(f"      max-T hi {REF_S49['hi'][0]} p {REF_S49['hi'][1]:.6f} / tw "
  f"{REF_S49['tw'][0]} p {REF_S49['tw'][1]:.6f} (the discovery (b)); s50")
P(f"      IQR-level max-T hi {REF_S50['hi'][0]} p {REF_S50['hi'][1]:.6f} / tw "
  f"{REF_S50['tw'][0]} p {REF_S50['tw'][1]:.6f}")
P("   D4 the s51 anchor reading (hi block A -- the frozen L12 single")
P("      bar candidate; the ledger line of section 3b/7): "
  f"median {anchor_rows['s51'][0]:.0f} min..max {anchor_rows['s51'][1]}"
  f"..{anchor_rows['s51'][2]}, class "
  f"{'FLOOR' if all(int(v) <= 100 for v in block_vals('s51', 'hi', [1, 2, 3])) else ('CAPTURED' if all(int(v) >= 1000 for v in block_vals('s51', 'hi', [1, 2, 3])) else 'INTERMEDIATE/MIXED')}"
  " vs the bar's frozen refs 1,129/1,132/1,131 (descriptive; the")
P("      bar's 2026-10-28 day slot is s31's -- same-day duplicate,")
P("      NO day-slot consumption, section 7).")
P("")

P("7. VERDICT SUMMARY:")
P(f"   T1 = {t1}")
for ax in ("MAD", "IQR"):
    _d, l2_obs, c_obs, cnt, p = prim[ax]
    P(f"   {ax}: C_obs = {fmt_ht(c_obs)} (2*L_s36 {int(l2_obs[0])} -> "
      f"2*L_s51 {int(l2_obs[1])}); count {cnt}/{TRIALS + 1}; p {p:.6f}; "
      f"letter {axis_letter(ax)}")
P(f"   evaluable inputs: prior vector reproduction EXACT ({vec_ok}); prior")
P(f"   anchor rows EXACT ({anchor_ok}); s51 C1 "
  f"({'(a)' if c1_ok else '(b)'}); per-window integrity rows in section 1")
P("   MEASUREMENT session: the s51 window ran on the ANV host this")
P("   tick (78 fresh processes, byte-pinned builds 4/4).")
P("   THE BAR: ONE ledger line (hi block A of s51 -- the frozen L12")
P("   single candidate), day=2026-10-28, same-day duplicate of s31's")
P("   COUNTED slot -> DESCRIPTIVE, NO day-slot consumption; the frozen")
P("   evaluator is the only source of the bar letter (section 7 of")
P("   bar-eval-s51.txt). Next executable day slot 2026-10-29.")
P("   Rule 4 binds: nothing moves; accelerator-targets defaults")
P("   remain provisional (:measured? false); NO vendor optimization")
P("   exists for Intel.")

open(os.path.join(HERE, "publication-s51.txt"), "w").write("\n".join(out) + "\n")
