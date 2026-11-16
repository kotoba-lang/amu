#!/usr/bin/env python3
"""JUN-59 W5 analysis PRE-BUILD (session 69, pre-GO preparation slice) --
the five-window machinery of the W5 session's analysis-s<NN>.py, built and
validated BEFORE any W5 run exists.

WHAT THIS IS (honest states): an IMPLEMENTATION pre-build of the s57-frozen
W5 protocol's analysis path (protocol.txt of anv-b3w5xdayrep-20261029,
sections 0/2/3/4 -- estimators, RNG contract, integrity machinery, T7 and
D1-D4). It is NOT the W5 session's script yet: the W5 session (the first
measurement session starting at or after 2026-10-29T00:00:00Z) adopts this
file as analysis-s<NN>.py (byte-copy or with its own header text), runs it
over the 390 committed logs, and owns every run/analysis artifact and the
record.txt of the W5 directory. NO W5 quantity exists or is computed here.

VALIDATION AVAILABLE NOW (--compat-s51 mode): the same generic machinery,
run at the FOUR prior windows in session-51 configuration (seed 20261028,
frozen probe order primary MAD / primary IQR / D3 MAD-hi / D3 MAD-tw /
D3 IQR-hi / D3 IQR-tw), must reproduce the committed publication-s51.txt
values EXACTLY (T1 counts/p, D3 counts/p, D1 vectors, D2 table, C1,
vectors, anchors, integrity). That validates the resampling and estimator
code paths end-to-end against published, frozen numbers. The W5-dependent
parts (T7 at the (s36, W5) pair, five-window D3, D1/D2/D4 at W5) cannot
be validated until the W5 logs exist -- they are UNVALIDATED here, named,
not hidden.

Deterministic: running this generator twice yields byte-identical output.

Frozen implementation paths (protocol section 0): numpy 2.5.4 (int64
np.sort over the pooled 75: MAD axis -- median sorted[..., 37],
deviations in int64, MAD = sorted deviations[..., 37]; IQR axis --
D = sorted[..., 56] - sorted[..., 18]; np.sort for the 6th+7th sums);
the resampling in vectorized TRIAL BATCHES (batch size a memory detail,
NOT part of the frozen contract; the RNG call order -- one rng.shuffle of
a fresh list per trial -- IS frozen).
"""
import re, os, sys, random, statistics
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

MODE = "compat-s51" if "--compat-s51" in sys.argv else "w5"

WIN4 = [("s36", "anv-b3commonmode-20261028"),
        ("s38", "anv-b3joint3-20261028"),
        ("s39", "anv-b3joint4-20261028"),
        ("s51", "anv-b3levelrep-20261028")]
W5_DIR = "anv-b3w5xdayrep-20261029"

if MODE == "compat-s51":
    WINDOWS = WIN4
    NEW_WIN = "s51"
    SEED = 20261028
    SESSION = 51
else:
    # the frozen naming: analysis-s<NN>.py -> the running session's number
    m = re.match(r"analysis-s(\d+)\.py$", os.path.basename(__file__))
    if not m:
        sys.exit("w5 mode requires the frozen filename analysis-s<NN>.py "
                 "(the running session's number); this file is the pre-build "
                 "-- the W5 session adopts it under that name")
    SESSION = int(m.group(1))
    NEW_WIN = "s%d" % SESSION
    WINDOWS = WIN4 + [(NEW_WIN, W5_DIR)]
    SEED = 20261029

ARMS = {"c2": (2, 1, 1, [1, 2, 3]),
        "hi": (3, 1024, 4033, list(range(1, 37))),
        "tw": (3, 2048, 8066, list(range(1, 37))),
        "c8": (8, 1, 1, [1, 2, 3])}
TRIALS = 20000
BATCH = 50
COMMITTED_C8 = 32915
NAMED_CKEY = ("max", 128, "default")

# ---- frozen reference vectors (publication-s39.txt section 3 for
# ---- s36/s38/s39; publication-s51.txt section 3 for s51) ----
REF_X = {"s39": [986, 991, 984, 985, 989, 989, 986, 990, 995, 986, 987, 981],
         "s36": [991, 989, 981, 998, 993, 985, 984, 997, 994, 994, 980, 982],
         "s38": [992, 988, 984, 1007, 985, 984, 986, 983, 992, 991, 982, 997],
         "s51": [988, 986, 1000, 986, 989, 983, 995, 983, 994, 991, 984, 985]}
REF_Y = {"s39": [988, 989, 987, 990, 990, 988, 991, 983, 985, 988, 983, 986],
         "s36": [988, 985, 994, 993, 994, 995, 992, 984, 987, 984, 993, 981],
         "s38": [988, 987, 980, 980, 991, 994, 991, 994, 988, 991, 1001, 992],
         "s51": [980, 975, 991, 979, 986, 986, 992, 991, 988, 993, 995, 996]}
# ---- anchor priors (protocol section 3: EXACT at the four prior windows) ----
REF_ANCHOR = {"s36": (1142, 991, 1438),
              "s38": (1132, 992, 1443),
              "s39": (1146, 986, 1432),
              "s51": (1137, 988, 1430)}
# ---- named-cell level priors, 2*L half-tick integer (publication-s49/50/51) ----
REF_NAMED = {"MAD": {"s36": 143, "s38": 111, "s39": 113, "s51": 118},
             "IQR": {"s36": 303, "s38": 241, "s39": 235, "s51": 240}}
# ---- quote-only D3 orientation priors (NOT recomputed) ----
REF_S49 = {"hi": ("10.0", 0.473426, "(min,256,S=16)"),
           "tw": ("16.0", 0.008600, "(max,128,S=default)")}
REF_S50 = {"hi": ("35.5", 0.083896, "(min,256,S=16)"),
           "tw": ("34.0", 0.611969, "(max,128,S=default)")}
REF_S51 = {"hi": ("13.0", 0.142243, "(min,256,S=16)"),
           "tw": ("16.0", 0.018399, "(max,128,S=default)")}
REF_S51_IQR = {"hi": ("35.5", 0.182891, "(min,256,S=16)"),
               "tw": ("34.0", 0.614169, "(max,128,S=default)")}

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
# parse the windows; integrity per protocol section 3
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

ok_cells = sorted([k for k, v in data[(WINDOWS[0][0], "c2", 1)][0].items()
                   if v["pipeline"] == "ok"])
cell_pos = {k: i for i, k in enumerate(ok_cells)}

def ckey(idx):
    c = data[(WINDOWS[0][0], "c2", 1)][0][idx]
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

def named_block_d(win, ax):
    """the named cell's 12 block D values of the tw arm of one window."""
    ds = []
    for i in range(12):
        runs = [3 * i + 1, 3 * i + 2, 3 * i + 3]
        xs = []
        for r in runs:
            xs += [s[2] for s in data[(win, "tw", r)][2] if s[1] == nc]
        dm, di = block_d(np.array(xs, dtype=np.int64))
        ds.append(int(dm) if ax == "MAD" else int(di))
    return ds

def named_l2(win, ax):
    ds = sorted(named_block_d(win, ax))
    return ds[5] + ds[6]

rng = random.Random(SEED)

# ------------------------------------------------------------------
# the PRIMARY two-window directional contrast (protocol sections 0/2)
# ------------------------------------------------------------------
named_arr = np.vstack([run_arr("s36", "tw")[:, [nc_pos], :],
                       run_arr(NEW_WIN, "tw")[:, [nc_pos], :]])   # (72,1,25)
named_flat = named_arr[:, 0, :]                                  # (72,25)

def primary(axis):
    obs = np.arange(72, dtype=np.int64).reshape(1, 2, 12, 3)
    sub = named_flat[obs].reshape(1, 2, 12, 75)
    dm, di = block_d(sub)
    d_obs = dm[0] if axis == "MAD" else di[0]
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

# ------------------------------------------------------------------
# the D{n}-window cross-window max-T repartition probes (descriptive)
# ------------------------------------------------------------------
def cell_dn(triples, arr, nwin):
    n = triples.shape[0]
    sub = arr[triples]
    pooled_t = sub.transpose(0, 1, 2, 4, 3, 5).reshape(n, nwin, 12, 18, 75)
    dm, di = block_d(pooled_t)
    dsm = np.sort(dm, axis=2)
    dsi = np.sort(di, axis=2)
    l2m = dsm[:, :, 5, :] + dsm[:, :, 6, :]
    l2i = dsi[:, :, 5, :] + dsi[:, :, 6, :]
    return dm, di, l2m, l2i

def probe_dn(axis, tag):
    nwin = len(WINDOWS)
    nruns = 36 * nwin
    arr = np.vstack([run_arr(win, tag) for win, _d in WINDOWS])   # (nruns,18,25)
    obs = np.arange(nruns, dtype=np.int64).reshape(1, nwin, 12, 3)
    _dm, _di, l2m, l2i = cell_dn(obs, arr, nwin)
    l2_obs = l2m[0] if axis == "MAD" else l2i[0]                  # (nwin,18)
    s2_obs = l2_obs.max(axis=0) - l2_obs.min(axis=0)              # (18,)
    m_obs = int(s2_obs.max())
    perms = np.empty((TRIALS, nruns), dtype=np.int64)
    for t in range(TRIALS):
        perm = list(range(nruns))
        rng.shuffle(perm)
        perms[t] = perm
    cnt = 0
    for i in range(0, TRIALS, BATCH):
        batch = perms[i:i + BATCH].reshape(-1, nwin, 12, 3)
        _dm, _di, l2m, l2i = cell_dn(batch, arr, nwin)
        l2 = l2m if axis == "MAD" else l2i
        s2 = l2.max(axis=1) - l2.min(axis=1)
        m = s2.max(axis=1)
        cnt += int((m >= m_obs).sum())
    p = (1 + cnt) / (1 + TRIALS)
    return s2_obs, m_obs, cnt, p

# frozen RNG order: (1) primary MAD (2) primary IQR (3) D MAD-hi
# (4) D MAD-tw (5) D IQR-hi (6) D IQR-tw -- primaries drawn above.
d = {}
for axis in ("MAD", "IQR"):
    for tag in ("hi", "tw"):
        d[(axis, tag)] = probe_dn(axis, tag)

def invalidated():
    inv = any(win_info[w]["vmis"] != 0 or not win_info[w]["counts_ok"]
              or not win_info[w]["knob_ok"] or not win_info[w]["fail_ok"]
              or not win_info[w]["cmap_ok"] for w, _d in WINDOWS)
    return inv or (not vec_ok) or (not c1_ok) or (not anchor_ok)

# ------------------------------------------------------------------
# C1, block-min vectors, anchor rows (protocol section 3)
# ------------------------------------------------------------------
c2_vals = block_vals(NEW_WIN, "c2", ARMS["c2"][3])
c2_cls = "FLOOR" if all(v <= 100 for v in c2_vals) else (
    "CAPTURED" if all(v >= 1000 for v in c2_vals) else "INTERMEDIATE/MIXED")
c8_m = pooled(NEW_WIN, "c8", sum128, ARMS["c8"][3], 2)
c1_ok = (c2_cls == "FLOOR") and abs(c8_m - COMMITTED_C8) <= 0.05 * COMMITTED_C8

vec = {}
vec_ok = True
for win, _d in WINDOWS:
    X = [block_min(win, "hi", [3 * i + 1, 3 * i + 2, 3 * i + 3]) for i in range(12)]
    Y = [block_min(win, "tw", [3 * i + 1, 3 * i + 2, 3 * i + 3]) for i in range(12)]
    vec[win] = (X, Y)
    if win != NEW_WIN and ([int(v) for v in X] != REF_X[win] or [int(v) for v in Y] != REF_Y[win]):
        vec_ok = False

anchor_ok = True
anchor_rows = {}
for win, _d in WINDOWS:
    a_med = pooled(win, "hi", sum128, [1, 2, 3], 2)
    bvals = [int(v) for v in block_vals(win, "hi", [1, 2, 3])]
    a_min, a_max = min(bvals), max(bvals)
    anchor_rows[win] = (a_med, a_min, a_max)
    if win != NEW_WIN and (a_med, a_min, a_max) != REF_ANCHOR[win]:
        anchor_ok = False

def axis_letter(axis):
    _d, _l2, c_obs, _cnt, p = prim[axis]
    if invalidated():
        return "(c) NOT EVALUABLE"
    if c_obs > 0 and p <= 0.05:
        return "(a) REPLICATED-CONTINUED"
    subcase = "DIRECTION-REVERSED" if c_obs <= 0 else \
        "DIRECTION-CONSISTENT-NOT-SIGNIFICANT"
    return f"(b) NOT-REPLICATED [{subcase}]"

def joint_letter():
    if invalidated():
        return "(c) NOT EVALUABLE", []
    hits = [ax for ax in ("MAD", "IQR") if not axis_letter(ax).startswith("(a)")]
    if not hits:
        if MODE == "w5":
            return "(a) CROSS-DAY-REPLICATED-ON-BOTH-LEVEL-AXES", []
        return "(a) REPLICATED-ON-BOTH-LEVEL-AXES", []
    if MODE == "w5":
        return "(b) NOT-CROSS-DAY-REPLICATED-ON-BOTH-AXES", hits
    return "(b) NOT-REPLICATED-ON-BOTH-AXES", hits

def named_l2_all(ax):
    l2 = {}
    for win, _d in WINDOWS:
        l2[win] = named_l2(win, ax)
    return l2

d_tbl = {}
for ax in ("MAD", "IQR"):
    for win, _d in WINDOWS:
        rows = []
        for i in range(12):
            runs = [3 * i + 1, 3 * i + 2, 3 * i + 3]
            xs = [[] for _ in ok_cells]
            for r in runs:
                for s in data[(win, "tw", r)][2]:
                    xs[cell_pos[s[1]]].append(s[2])
            pooled_t = np.array(xs, dtype=np.int64)               # (18,75)
            dm, di = block_d(pooled_t)
            rows.append(dm if ax == "MAD" else di)
        rows = np.array(rows)                                     # (12,18)
        rs = np.sort(rows, axis=0)
        d_tbl[(ax, win)] = rs[5] + rs[6]                          # (18,)

# ==================================================================
if MODE == "compat-s51":
    # ---- s51-compat validation report: want values parsed from the
    # ---- committed publication-s51.txt, got values computed above.
    pub = open(os.path.join(ROOT, "docs", "evidence", "gpu",
                            "anv-b3levelrep-20261028", "publication-s51.txt")).read()
    rows = []
    def row(label, want, got):
        rows.append((label, want, got, want == got))

    ire = re.compile(
        r"(s\d+): runs parsed (\d+); VERIFY mismatch total (\d+); counts ok (\w+); "
        r"knobs ok (\w+); S=8 fail-closed (\w+); cell map ok (\w+)")
    for m in ire.finditer(pub):
        win = m.group(1)
        want = "runs %s vmis %s counts %s knobs %s s8 %s cmap %s" % m.group(2, 3, 4, 5, 6, 7)
        info = win_info[win]
        got = "runs 78 vmis %d counts %s knobs %s s8 %s cmap %s" % (
            info["vmis"], info["counts_ok"], info["knob_ok"], info["fail_ok"], info["cmap_ok"])
        row("sec1 %s integrity" % win, want, got)

    m = re.search(r"c2 class: (\S+) \(FLOOR required", pub)
    row("sec2 c2 class", m.group(1), c2_cls)
    m = re.search(r"pooled median (\d+) vs committed (\d+)", pub)
    row("sec2 c8 pooled median", m.group(1), "%.0f" % c8_m)

    vre = re.compile(r"(s\d+) X \(hi\): ([\d ]+?)\n\s+(s\d+) Y \(tw\): ([\d ]+?)\n")
    for m in vre.finditer(pub):
        win = m.group(1)
        X, Y = vec[win]
        row("sec3 %s X (hi)" % win, m.group(2), " ".join(str(int(v)) for v in X))
        row("sec3 %s Y (tw)" % win, m.group(4), " ".join(str(int(v)) for v in Y))
    m = re.search(r"all three prior windows reproduce EXACTLY: (\w+)", pub)
    row("sec3 prior vector reproduction", m.group(1), str(vec_ok))

    are = re.compile(r"\n    (s\d+): median (\d+) min\.\.max (\d+)\.\.(\d+) \(want")
    for m in are.finditer(pub):
        win = m.group(1)
        a = anchor_rows[win]
        row("sec3b %s anchor" % win, "%s %s..%s" % m.group(2, 3, 4),
            "%.0f %d..%d" % (a[0], a[1], a[2]))
    m = re.search(r"\n    s51 \(NEW\): median (\d+) min\.\.max (\d+)\.\.(\d+); class (\S+)", pub)
    a = anchor_rows["s51"]
    s_cls = "FLOOR" if all(int(v) <= 100 for v in block_vals("s51", "hi", [1, 2, 3])) else (
        "CAPTURED" if all(int(v) >= 1000 for v in block_vals("s51", "hi", [1, 2, 3]))
        else "INTERMEDIATE/MIXED")
    row("sec3b s51 anchor (fresh)", "%s %s..%s %s" % m.group(1, 2, 3, 4),
        "%.0f %d..%d %s" % (a[0], a[1], a[2], s_cls))

    tre = re.compile(
        r"(MAD|IQR) axis: 2\*L_s36 = (\d+) \([\d.]+\), 2\*L_s51 = (\d+) \([\d.]+\); "
        r"C_obs = (-?[\d.]+); count (\d+) / 20001; p = ([\d.]+)")
    for m in tre.finditer(pub):
        ax = m.group(1)
        _dd, l2_obs, c_obs, cnt, p = prim[ax]
        want = "%s %s C %s count %s p %s" % m.group(2, 3, 4, 5, 6)
        got = "%d %d C %s count %d p %.6f" % (l2_obs[0], l2_obs[1],
                                              fmt_ht(c_obs), cnt, p)
        row("sec4 T1 %s" % ax, want, got)
    m = re.search(r"   T1 = (.+)", pub)
    row("sec4 T1 joint", m.group(1), joint_letter()[0])

    dre = re.compile(
        r"(MAD|IQR): 2\*L s36/s38/s39/s51 = ([\d/]+) .*EXACT: (\w+); "
        r"L_51 inside the s38/s39 pair interval: (\w+)")
    for m in dre.finditer(pub):
        ax = m.group(1)
        l2 = named_l2_all(ax)
        want = "%s repro %s inpair %s" % m.group(2, 3, 4)
        got = "%s repro %s inpair %s" % (
            "/".join(str(l2[w]) for w, _d in WINDOWS),
            all(l2[w] == REF_NAMED[ax][w] for w, _d in WINDOWS if w != "s51"),
            sorted([l2["s38"], l2["s39"], l2["s51"]])[0] <= l2["s51"] <=
            sorted([l2["s38"], l2["s39"], l2["s51"]])[-1])
        row("sec6 D1 %s" % ax, want, got)

    d2re = re.compile(
        r"tw cell (\(\S+\)): MAD 2\*L (\d+)/(\d+) C (-?[\d.]+); "
        r"IQR 2\*L (\d+)/(\d+) C (-?[\d.]+)")
    for m in d2re.finditer(pub):
        cstr = m.group(1)
        idx = [k for k in ok_cells if ckey_str(k) == cstr][0]
        ci = cell_pos[idx]
        want = "MAD %s/%s C %s IQR %s/%s C %s" % m.group(2, 3, 4, 5, 6, 7)
        l36m, l51m = int(d_tbl[("MAD", "s36")][ci]), int(d_tbl[("MAD", "s51")][ci])
        l36i, l51i = int(d_tbl[("IQR", "s36")][ci]), int(d_tbl[("IQR", "s51")][ci])
        got = "MAD %d/%d C %s IQR %d/%d C %s" % (
            l36m, l51m, fmt_ht(l36m - l51m), l36i, l51i, fmt_ht(l36i - l51i))
        row("sec6 D2 %s" % cstr, want, got)

    d3re = re.compile(
        r"(MAD|IQR)-(hi|tw): M_obs = ([\d.]+) \(max cell\(s\) (\(\S+\))\); "
        r"count (\d+) / 20001; p = ([\d.]+)")
    for m in d3re.finditer(pub):
        key = (m.group(1), m.group(2))
        s2, m_obs, cnt, p = d[key]
        want = "M_obs %s cells %s count %s p %s" % m.group(3, 4, 5, 6)
        idxs = [ok_cells[i] for i in range(len(ok_cells)) if int(s2[i]) == m_obs]
        mcs = ", ".join(ckey_str(i) for i in idxs)
        got = "M_obs %s cells %s count %d p %.6f" % (fmt_ht(m_obs), mcs, cnt, p)
        row("sec6 D3 %s-%s" % key, want, got)

    out = []
    P = out.append
    P("JUN-59 W5 analysis PRE-BUILD (session 69) -- s51-COMPAT VALIDATION")
    P("(analysis-prego.py --compat-s51: the generic primary/D3/D1/D2/C1/")
    P("vector/anchor machinery run at the FOUR prior windows in session-51")
    P("configuration -- random.Random(%d), frozen probe order primary MAD /" % SEED)
    P("primary IQR / D MAD-hi / D MAD-tw / D IQR-hi / D IQR-tw, %d trials" % TRIALS)
    P("per probe, one rng.shuffle of a fresh list per trial -- vs the want")
    P("values PARSED from the committed publication-s51.txt.)")
    P("No W5 quantity is computed anywhere in this mode; the W5-dependent")
    P("parts (T7 at the (s36, W5) pair, five-window D3, D1/D2/D4 at W5)")
    P("are UNVALIDATED until the W5 logs exist (named, not hidden).")
    P("")
    ok_n = 0
    for (label, want, got, ok) in rows:
        P("row %02d: %s: want [%s] got [%s] -> %s"
          % (len([r for r in rows[:rows.index((label, want, got, ok)) + 1]]),
             label, want, got, "ok" if ok else "FAIL"))
        ok_n += 1 if ok else 0
    P("")
    P("TOTAL: %d rows, %d failed" % (len(rows), len(rows) - ok_n))
    P("DETERMINISM: this generator run twice yields byte-identical output")
    P("(double-run status named in the s69 record; RNG seeded, no set iteration).")
    open(os.path.join(HERE, "compat-s51-validation.txt"), "w").write("\n".join(out) + "\n")
    sys.exit(0 if ok_n == len(rows) else 1)

# ==================================================================
# w5 mode: the W5 publication (five windows; T7 the row question)
# ==================================================================
out = []
P = out.append
P(f"JUN-59 session {SESSION} -- THE FIFTH-WINDOW CROSS-UTC-DAY NAMED-CELL")
P("ROBUST-SCALE LEVEL REPLICATION PROBE (publication)")
P("(at the NEW fifth window W5, does the tw arm's")
P("(max,128,S=default) cell's robust-scale LEVEL continue the")
P("post-shift regime of s38/s39/s51 rather than return to the s36")
P("pre-shift regime, on BOTH robust-scale level axes -- the")
P("s48-frozen exact-median MAD and the s47-frozen exclusive-hinge")
P(f"IQR? ONE named cell, ONE named window pair (s36 vs {NEW_WIN}), ONE")
P("named direction (L_W5 < L_s36), TWO named axes under a")
P("pre-registered intersection-union joint rule; the primary")
P("per-axis statistic C = L_s36 - L_W5 vs a two-window")
P("run-repartition resampling null over the named cell's 72 tw")
P("committed runs of the two windows.)")
P(f"Produced ONLY by analysis-s{SESSION}.py over the COMMITTED run logs of")
P("five fixed evidence directories (anv-b3commonmode-20261028 =")
P("the s36 window, anv-b3joint3-20261028 = the s38 window,")
P("anv-b3joint4-20261028 = the s39 window, anv-b3levelrep-20261028")
P("= the s51 window, anv-b3w5xdayrep-20261029 = the NEW W5 window");
P("measured THIS session); protocol.txt was")
P("frozen BEFORE the first W5 run and before any statistic of")
P("this probe was computed (freeze stamp 2026-10-28T16:15:35Z).")
P(f"MEASUREMENT session -- the W5 window ran on aiueos-6600hs")
P("Intel BMG G31 ANV (78 fresh processes; the s36/s38/s39/s51")
P("windows were MEASURED in sessions 36/38/39/51).")
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

P(f"2. C1 RE-DERIVATION (environment pin, from the {NEW_WIN} window's logs):")
P(f"   c2 class: {c2_cls} (FLOOR required; committed floor band 31..32)")
P(f"   c8 (sum,128,S=16) pooled median {c8_m:.0f} vs committed {COMMITTED_C8} "
  f"({abs(c8_m - COMMITTED_C8) / COMMITTED_C8 * 100:.2f}% delta; +/-5% required)")
P(f"   C1 branch: {'(a) both controls replicate' if c1_ok else '(b) discrepancy'}")
P("")

P("3. THE BLOCK-MIN VECTORS (re-derived from the committed logs; block")
P("   order A..L; the four PRIOR windows reproduce the")
P("   published/quote-only vectors of publication-s39.txt section 3")
P("   and publication-s51.txt section 3 EXACTLY (mismatch => (c)); the")
P("   W5 vectors are NEW measurement:")
for win, _d in WINDOWS:
    X, Y = vec[win]
    P(f"   {win} X (hi): " + " ".join(f"{int(v)}" for v in X))
    P(f"   {win} Y (tw): " + " ".join(f"{int(v)}" for v in Y))
    if win != NEW_WIN:
        P(f"   {win} reproduction EXACT: "
          f"{[int(v) for v in X] == REF_X[win] and [int(v) for v in Y] == REF_Y[win]}")
P(f"   all four prior windows reproduce EXACTLY (8/8): {vec_ok}")
P("")

P("3b. ANCHOR ROWS (hi block A -- the frozen L12 single bar candidate:")
P("    its (sum,128,S=16) pooled median and 18-cell min..max; the")
P("    four PRIOR windows reproduce the quote-only/published anchor")
P("    priors of publication-s36/38/39/51 EXACTLY (mismatch => (c));")
P("    the W5 row is NEW measurement -- the session's bar candidate,")
P("    section 4 D4):")
for win, _d in WINDOWS:
    a_med, a_min, a_max = anchor_rows[win]
    if win != NEW_WIN:
        P(f"    {win}: median {a_med:.0f} min..max {a_min}..{a_max} "
          f"(want {REF_ANCHOR[win][0]} / {REF_ANCHOR[win][1]}..{REF_ANCHOR[win][2]}); "
          f"reproduction EXACT: {(a_med, a_min, a_max) == REF_ANCHOR[win]}")
    else:
        bA = [int(v) for v in block_vals(win, "hi", [1, 2, 3])]
        s_cls = "FLOOR" if all(v <= 100 for v in bA) else (
            "CAPTURED" if all(v >= 1000 for v in bA) else "INTERMEDIATE/MIXED")
        P(f"    {win} (NEW): median {a_med:.0f} min..max {a_min}..{a_max}; "
          f"class {s_cls}")
P(f"    all four prior windows reproduce EXACTLY: {anchor_ok}")
P("")

P("4. T7 THE ROW QUESTION (frozen letters, protocol sections 0/2):")
P(f"   the NAMED cell {ckey_str(nc)} of the tw arm, the NAMED window")
P(f"   pair s36 (pre-shift) vs {NEW_WIN} (NEW this session), the NAMED")
P("   direction L_W5 < L_s36, on the two NAMED level axes (MAD =")
P("   e_(38) about x_(38); IQR = x_(57) - x_(19); L = median of 12")
P("   block D values; 2*C = 2*L_s36 - 2*L_W5 in half-tick integer")
P(f"   units). {TRIALS} trials, seed {SEED}, probe order primary MAD")
P("   then primary IQR; per trial one shuffle of list(range(72))")
P("   split into two pseudo-windows of 36 and 12 blocks of 3;")
P(f"   p = (1 + count(C* >= C_obs)) / (1 + {TRIALS}), one-sided in the")
P("   pre-registered direction; joint T7 = the pre-registered")
P("   INTERSECTION-UNION rule (both axes must read (a); NO")
P("   multiplicity correction applied or needed):")
for ax in ("MAD", "IQR"):
    d_obs, l2_obs, c_obs, cnt, p = prim[ax]
    P(f"   {ax} axis: 2*L_s36 = {int(l2_obs[0])} ({fmt_ht(int(l2_obs[0]))}), "
      f"2*L_{NEW_WIN} = {int(l2_obs[1])} ({fmt_ht(int(l2_obs[1]))}); "
      f"C_obs = {fmt_ht(c_obs)}; count {cnt} / {TRIALS + 1}; p = {p:.6f}; "
      f"p <= 0.05: {p <= 0.05}; axis letter {axis_letter(ax)}")
t7, t7hits = joint_letter()
P(f"   T7 = {t7}" + (f" (named axis(es) not replicated: {', '.join(t7hits)})"
                     if t7hits else ""))
P("   NAMED, NOT HIDDEN: the multiplicity claim is NARROW -- ONE")
P("   named cell, ONE named window pair, ONE named direction, TWO")
P("   named axes under a pre-registered IUT, tested on NEW data")
P("   (the W5 runs did not exist at freeze time); it carries NO")
P("   within-family multiplicity of its own, BUT the cell/direction")
P("   choice was made by looking at s40-51's UNCORRECTED-family")
P("   results, the discovery family STAYS uncorrected and this")
P("   replication does NOT retro-correct it; s38/s39/s51 are NOT in")
P("   the primary contrast and appear ONLY in section 6 D1; (a)")
P("   would NOT name a mechanism (thermal/scheduling/memory/driver")
P("   state all UNMEASURED) and NOT say whether the level shift is")
P("   physical or estimator structure; the window pair spans the")
P("   UTC-day boundary (n=2 windows, 12 blocks each -- LOW POWER; a")
P("   single (a) can also reflect any s36-specific or W5-specific")
P("   state); (b) does NOT overturn s49's discovery (b) -- it says")
P("   the pre-registered directional contrast did not replicate at")
P("   THIS window pair (sub-cases named above); the estimator is the")
P("   named cell's within-block robust scale level ONLY; 20,000")
P("   trials (NOT the s35-frozen 100,000 -- cost, same named")
P("   deviation as sessions 40-51; p resolution 1/20,001 ~= 5e-5);")
P("   L2 observational ONLY; NO causal mechanism; direction")
P("   UNMEASURED; threshold-artifact-vs-representation STAYS")
P("   UNRESOLVED under any letter.")
P("")

P("5. REPLICATION FRAMING (frozen): the row answer is the section-4")
P("   joint T7; the two axes are the two named robust scales (NEITHER")
P("   dominates -- a shift of one need not move the other) and the")
P("   IUT rule demands both; the per-axis letters and sub-cases are")
P("   in section 4.")
P("")

P("6. DESCRIPTIVE (not the row question; NO letter):")
P("   D1 the NAMED cell's five-window level vectors on both axes")
P(f"      ({ckey_str(nc)}, tw arm; L = median of the 12 block D values,")
P("      half-tick exact; prior windows reproduce the quote-only")
P("      s49/s50/s51 D1 priors EXACTLY -- a reproduction check on the")
P("      prior windows, descriptive) and the W5-vs-post-shift-band")
P("      consistency (L_W5 inside the closed interval spanned by")
P("      {L_s38, L_s39, L_s51}):")
for ax in ("MAD", "IQR"):
    l2 = named_l2_all(ax)
    repro = all(l2[w] == REF_NAMED[ax][w] for w, _d in WINDOWS if w != NEW_WIN)
    band = sorted([l2["s38"], l2["s39"], l2["s51"]])
    inband = band[0] <= l2[NEW_WIN] <= band[-1]
    names = "/".join(w for w, _d in WINDOWS)
    vals = "/".join(str(l2[w]) for w, _d in WINDOWS)
    tick = "/".join(fmt_ht(l2[w]) for w, _d in WINDOWS)
    P(f"      {ax}: 2*L {names} = {vals} (L {tick}); prior")
    P(f"      reproduction vs quote-only priors "
      f"{ {w: REF_NAMED[ax][w] for w, _d in WINDOWS if w != NEW_WIN} } EXACT: {repro}; "
      f"L_W5 inside the s38/s39/s51 band interval: {inband}")
P(f"   D2 the 18-cell scoreboard at {NEW_WIN} on both axes (L_W5 per ok")
P("      cell) and the full W5-vs-s36 per-cell contrast table")
P("      (C = L_s36 - L_W5 per cell per axis; 36 descriptive")
P("      contrasts, UNCORRECTED for multiplicity, no letter):")
for ci, k in enumerate(ok_cells):
    cells = []
    for ax in ("MAD", "IQR"):
        l36 = int(d_tbl[(ax, "s36")][ci])
        lw5 = int(d_tbl[(ax, NEW_WIN)][ci])
        cells.append(f"{ax} 2*L {l36}/{lw5} C {fmt_ht(l36 - lw5)}")
    P(f"      tw cell {ckey_str(k)}: " + "; ".join(cells))
P("   D3 the FIVE-WINDOW cross-window max-T repartition probes (the")
P("      s49/s50 machinery extended by s51's D3 to")
P("      s36/s38/s39/s51/W5: per-cell S_c = max_w L_{w,c} -")
P("      min_w L_{w,c} over the five windows, M = max_c 2*S_c")
P("      family-wise over the 18 cells; null = the 180 runs of one")
P("      arm repartitioned into 5 pseudo-windows of 36 then 12")
P("      blocks of 3; 20,000 trials per probe in the")
P("      frozen RNG order) -- DESCRRIPTIVE ONLY, NO letter (the four")
P("      probes are UNCORRECTED across axes/arms; this session's")
P("      LETTER source is the section-4 named-cell IUT alone):")
for ax in ("MAD", "IQR"):
    for tag in ("hi", "tw"):
        s2, m_obs, cnt, p = d[(ax, tag)]
        idxs = [ok_cells[i] for i in range(len(ok_cells)) if int(s2[i]) == m_obs]
        mcs = ", ".join(ckey_str(i) for i in idxs)
        P(f"      {ax}-{tag}: M_obs = {fmt_ht(m_obs)} (max cell(s) {mcs}); "
          f"count {cnt} / {TRIALS + 1}; p = {p:.6f}")
P("      orientation quote-only priors (NOT recomputed): s49 MAD-level")
P(f"      max-T hi {REF_S49['hi'][0]} p {REF_S49['hi'][1]:.6f} / tw "
  f"{REF_S49['tw'][0]} p {REF_S49['tw'][1]:.6f} (the discovery (b)); s50")
P(f"      IQR-level max-T hi {REF_S50['hi'][0]} p {REF_S50['hi'][1]:.6f} / tw "
  f"{REF_S50['tw'][0]} p {REF_S50['tw'][1]:.6f}; s51 five-window-precursor")
P(f"      MAD-level hi {REF_S51['hi'][0]} p {REF_S51['hi'][1]:.6f} / tw "
  f"{REF_S51['tw'][0]} p {REF_S51['tw'][1]:.6f}; IQR-level hi "
  f"{REF_S51_IQR['hi'][0]} p {REF_S51_IQR['hi'][1]:.6f} / tw "
  f"{REF_S51_IQR['tw'][0]} p {REF_S51_IQR['tw'][1]:.6f}")
P(f"   D4 the W5 anchor reading (hi block A -- the frozen L12 single")
P("      bar candidate; the ledger line of section 3b/5): "
  f"median {anchor_rows[NEW_WIN][0]:.0f} min..max {anchor_rows[NEW_WIN][1]}"
  f"..{anchor_rows[NEW_WIN][2]}, class "
  f"{'FLOOR' if all(int(v) <= 100 for v in block_vals(NEW_WIN, 'hi', [1, 2, 3])) else ('CAPTURED' if all(int(v) >= 1000 for v in block_vals(NEW_WIN, 'hi', [1, 2, 3])) else 'INTERMEDIATE/MIXED')}"
  " vs the bar's frozen refs 1,129/1,132/1,131 (descriptive; the")
P("      line's day = the W5 run's ACTUAL UTC day from run-window.txt;")
P("      W5's line is the first qualifying reading of its UTC day and")
P("      is COUNTED under the frozen construction unless another")
P("      session's qualifying reading precedes it that same day --")
P("      the frozen evaluator (settle-bar-eval.py) is ALWAYS the only")
P("      source of the bar verdict; NEVER hand-write a verdict).")
P("")

P("7. VERDICT SUMMARY:")
P(f"   T7 = {t7}")
for ax in ("MAD", "IQR"):
    _d, l2_obs, c_obs, cnt, p = prim[ax]
    P(f"   {ax}: C_obs = {fmt_ht(c_obs)} (2*L_s36 {int(l2_obs[0])} -> "
      f"2*L_{NEW_WIN} {int(l2_obs[1])}); count {cnt}/{TRIALS + 1}; p {p:.6f}; "
      f"letter {axis_letter(ax)}")
P(f"   evaluable inputs: prior vector reproduction EXACT ({vec_ok}); prior")
P(f"   anchor rows EXACT ({anchor_ok}); W5 C1 "
  f"({'(a)' if c1_ok else '(b)'}); per-window integrity rows in section 1")
P("   MEASUREMENT session: the W5 window ran on the ANV host this")
P("   session (78 fresh processes, byte-pinned builds 4/4).")
P("   THE BAR: ONE ledger line (hi block A of W5 -- the frozen L12")
P("   single candidate), day = the W5 run's actual UTC day; the")
P("   frozen evaluator is the only source of the bar letter.")
P("   Rule 4 binds: nothing moves; accelerator-targets defaults")
P("   remain provisional (:measured? false); NO vendor optimization")
P("   exists for Intel.")

open(os.path.join(HERE, f"publication-s{SESSION}.txt"), "w").write("\n".join(out) + "\n")
