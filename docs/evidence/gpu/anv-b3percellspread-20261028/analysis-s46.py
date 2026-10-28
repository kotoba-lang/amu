#!/usr/bin/env python3
"""JUN-59 session 46 analysis -- THE PER-CELL WITHIN-BLOCK SPREAD
REPARTITION PROBE (does ANY ok cell's within-block sample scale --
the RANGE of the cell's own 75 gpu_ticks samples inside one 3-run
block -- wander across the 12 blocks of one (window, arm) beyond
WITHIN-window run-exchangeable sampling noise?). ANALYSIS
session: NO new hardware; the inputs are the COMMITTED run logs of
the session-36/38/39 run windows (fixed evidence paths below).

Route (frozen in protocol.txt section 6): this script parses ONLY the
committed run-<tag>-r<R>.txt logs of the three fixed evidence
directories and writes publication-s46.txt in its own directory.
Deterministic: running it twice yields byte-identical output.

The statistic (per-cell within-block spread D_{b,c} = max - min of
the block's 75 samples per ok cell, an exact INTEGER; per-cell
spread wander W_c = max_b D_{b,c} - min_b D_{b,c} over the 12
blocks of one (window, arm) -- an exact INTEGER; the primary
per-probe statistic M_obs = max_c W_c, the max-T), the resampling
null (within-window run-repartition, 20,000 trials per probe,
random.Random(20261028) consumed in the frozen probe order s39 hi /
s39 tw / s36 hi / s36 tw / s38 hi / s38 tw, the max taken inside
each trial) and the T1/replication letters are frozen in
protocol.txt sections 0-2 (freeze stamp 2026-10-28T07:51:32Z) and
were NOT changed after seeing any result. numpy 2.5.4 (int64
max/min reductions over the pooled 75) is the frozen implementation
path for the block spread (protocol section 0); the resampling is
vectorized over TRIAL BATCHES with the frozen RNG call order
unchanged; every M* >= M_obs and W*_c >= W_obs_c comparison is
exact INTEGER arithmetic.
"""
import re, os, random, statistics
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
# (window label, evidence dir name) -- the three windows in
# chronological order (frozen).
WINDOWS = [("s36", "anv-b3commonmode-20261028"),
           ("s38", "anv-b3joint3-20261028"),
           ("s39", "anv-b3joint4-20261028")]
ARMS = {"c2": (2, 1, 1, [1, 2, 3]),
        "hi": (3, 1024, 4033, list(range(1, 37))),
        "tw": (3, 2048, 8066, list(range(1, 37))),
        "c8": (8, 1, 1, [1, 2, 3])}
TRIALS = 20000
SEED = 20261028
BATCH = 200
COMMITTED_C8 = 32915

# ---- quote-only frozen reference vectors (publication-s39.txt
# ---- section 3: s39 published + s36/s38 quote-only; prior
# ---- sessions' measurements, never recomputed from those
# ---- sessions' numbers) ----
REF_X = {"s39": [986, 991, 984, 985, 989, 989, 986, 990, 995, 986, 987, 981],
         "s36": [991, 989, 981, 998, 993, 985, 984, 997, 994, 994, 980, 982],
         "s38": [992, 988, 984, 1007, 985, 984, 986, 983, 992, 991, 982, 997]}
REF_Y = {"s39": [988, 989, 987, 990, 990, 988, 991, 983, 985, 988, 983, 986],
         "s36": [988, 985, 994, 993, 994, 995, 992, 984, 987, 984, 993, 981],
         "s38": [988, 987, 980, 980, 991, 994, 991, 994, 988, 991, 1001, 992]}
# ---- quote-only anchor priors (protocol section 3): hi block
# ---- A's (sum,128,S=16) pooled median and its 18-cell min..max,
# ---- published by the s36/s38/s39 anchor readings (the
# ---- settle-bar ledger median/min fields and
# ---- publication-s36/38/39 section D) ----
REF_ANCHOR = {"s36": (1142, 991, 1438),
              "s38": (1132, 992, 1443),
              "s39": (1146, 986, 1432)}
# ---- quote-only prior (publication-s45.txt sections 4/5): the
# ---- s45 per-cell block-median wander max-T M and p per
# ---- (window, arm) -- the LEVEL-structure construction this
# ---- probe complements; D3 orientation only, never recomputed
# ---- here ----
REF_S45 = {("s39", "hi"): (72, 0.471176), ("s39", "tw"): (70, 0.493875),
           ("s36", "hi"): (84, 0.154792), ("s36", "tw"): (68, 0.644518),
           ("s38", "hi"): (84, 0.047398), ("s38", "tw"): (56, 0.994550)}

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

# ------------------------------------------------------------------
# parse the three windows; integrity per protocol section 3
# ------------------------------------------------------------------
data = {}          # (win, tag, run) -> (cells, verifies, samples)
win_info = {}      # win -> dict of integrity facts
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

ok_cells = sorted([k for k, v in data[("s39", "c2", 1)][0].items() if v["pipeline"] == "ok"])
cell_pos = {k: i for i, k in enumerate(ok_cells)}

def ckey(idx):
    c = data[("s39", "c2", 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])

def ckey_str(idx):
    op, wg, s = ckey(idx)
    return f"({op},{wg},S={s})"

sum128 = [k for k in ok_cells if ckey(k) == ("sum", 128, "16")][0]

def pooled(win, tag, idx, runs, field):
    xs = []
    for r in runs:
        xs += [s[field] for s in data[(win, tag, r)][2] if s[1] == idx]
    return med(xs)

def block_vals(win, tag, runs):
    return [pooled(win, tag, k, runs, 2) for k in ok_cells]

def block_min(win, tag, runs):
    return min(block_vals(win, tag, runs))

# ---- per-run sample tensors (for the resampling) ----
def run_arr(win, tag):
    """(36, 18, 25) int64 tensor: run x ok-cell x the run's 25
    gpu_ticks values in SAMPLE order."""
    arr = np.zeros((36, len(ok_cells), 25), dtype=np.int64)
    for ri in range(36):
        tbl = {k: [] for k in ok_cells}
        for (_rnd, idx, gt, _hn, _kn) in data[(win, tag, ri + 1)][2]:
            tbl[idx].append(gt)
        for k in ok_cells:
            assert len(tbl[k]) == 25
            arr[ri, cell_pos[k], :] = tbl[k]
    return arr

def cell_spread(triples, arr):
    """triples: (n,12,3) block index tensor -> per-cell within-block
    spread wander in INTEGER ticks. Returns (n,12,18) per-cell
    within-block ranges D and (n,18) W = max_b D - min_b D.
    D = max - min of the block's 75 samples per cell (exact)."""
    n = triples.shape[0]
    sub = arr[triples]                                    # (n,12,3,18,25)
    pooled_t = sub.transpose(0, 1, 3, 2, 4).reshape(n, 12, 18, 75)
    d = pooled_t.max(axis=3) - pooled_t.min(axis=3)       # (n,12,18) exact
    w = d.max(axis=1) - d.min(axis=1)                     # (n,18) W_c
    return d, w

out = []
P = out.append
P("JUN-59 session 46 -- THE PER-CELL WITHIN-BLOCK SPREAD")
P("REPARTITION PROBE")
P("(publication)")
P("(does ANY ok cell's within-block sample scale -- the RANGE of")
P("the cell's own 75 gpu_ticks samples inside one 3-run block --")
P("wander across the 12 blocks of one (window, arm) beyond")
P("WITHIN-window run-exchangeable sampling noise? ONE observable")
P("axis per (window, arm): the max-T M = max_c W_c over the 18")
P("cells, W_c = max_b D_{b,c} - min_b D_{b,c} over the 12 blocks")
P("of that (window, arm), D_{b,c} = max - min of the block's 75")
P("samples for cell c, vs a within-window run-repartition")
P("resampling null over the same (window, arm)'s 36 committed")
P("runs; the max over cells is taken INSIDE each resampling trial")
P("too (family-wise over the 18 cells).)")
P("Produced ONLY by analysis-s46.py over the COMMITTED run logs of")
P("three fixed evidence directories (anv-b3commonmode-20261028 =")
P("the s36 window, anv-b3joint3-20261028 = the s38 window,")
P("anv-b3joint4-20261028 = the s39 window); protocol.txt was")
P("frozen BEFORE any statistic of this probe was computed (freeze")
P("stamp 2026-10-28T07:51:32Z). ANALYSIS slice -- NO hardware ran")
P("this tick; every input quantity was MEASURED on aiueos-6600hs")
P("Intel BMG G31 ANV in sessions 36/38/39 (run windows")
P("2026-10-28T02:40:49Z, 03:39:14Z, 04:09:48Z respectively).")
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

# ---- C1 re-derivation at the s39 window (prerequisite) ----
c2_vals = block_vals("s39", "c2", ARMS["c2"][3])
c2_cls = "FLOOR" if all(v <= 100 for v in c2_vals) else (
    "CAPTURED" if all(v >= 1000 for v in c2_vals) else "INTERMEDIATE/MIXED")
c8_m = pooled("s39", "c8", sum128, ARMS["c8"][3], 2)
c1_ok = (c2_cls == "FLOOR") and abs(c8_m - COMMITTED_C8) <= 0.05 * COMMITTED_C8
P("2. C1 RE-DERIVATION (environment pin, from the s39 window's logs):")
P(f"   c2 class: {c2_cls} (FLOOR required; committed floor band 31..32)")
P(f"   c8 (sum,128,S=16) pooled median {c8_m:.0f} vs committed {COMMITTED_C8} "
  f"({abs(c8_m - COMMITTED_C8) / COMMITTED_C8 * 100:.2f}% delta; +/-5% required)")
P(f"   C1 branch: {'(a) both controls replicate' if c1_ok else '(b) discrepancy'}")
P("")

# ---- the block-min vectors per window + reproduction check ----
vec = {}
vec_ok = True
for win, _d in WINDOWS:
    X = [block_min(win, "hi", [3 * i + 1, 3 * i + 2, 3 * i + 3]) for i in range(12)]
    Y = [block_min(win, "tw", [3 * i + 1, 3 * i + 2, 3 * i + 3]) for i in range(12)]
    vec[win] = (X, Y)
    if [int(v) for v in X] != REF_X[win] or [int(v) for v in Y] != REF_Y[win]:
        vec_ok = False
P("3. THE BLOCK-MIN VECTORS (re-derived from the committed logs; block")
P("   order A..L; reproduction check vs the published/quote-only")
P("   vectors of publication-s39.txt section 3 -- mismatch => (c)):")
for win, _d in WINDOWS:
    X, Y = vec[win]
    P(f"   {win} X (hi): " + " ".join(f"{int(v)}" for v in X))
    P(f"   {win} Y (tw): " + " ".join(f"{int(v)}" for v in Y))
    P(f"   {win} reproduction EXACT: "
      f"{[int(v) for v in X] == REF_X[win] and [int(v) for v in Y] == REF_Y[win]}")
P(f"   all three windows reproduce EXACTLY: {vec_ok}")
P("")

# ---- the anchor reproduction row (protocol section 3) ----
anchor_ok = True
anchor_rows = {}
for win, _d in WINDOWS:
    a_med = pooled(win, "hi", sum128, [1, 2, 3], 2)
    bvals = [int(v) for v in block_vals(win, "hi", [1, 2, 3])]
    a_min, a_max = min(bvals), max(bvals)
    anchor_rows[win] = (a_med, a_min, a_max)
    if (a_med, a_min, a_max) != REF_ANCHOR[win]:
        anchor_ok = False
P("3b. ANCHOR REPRODUCTION ROW (pre-registered; hi block A's")
P("    (sum,128,S=16) pooled median and 18-cell min..max vs the")
P("    quote-only anchor priors of publication-s36/38/39 section")
P("    D -- mismatch => (c)):")
for win, _d in WINDOWS:
    a_med, a_min, a_max = anchor_rows[win]
    P(f"    {win}: median {a_med:.0f} min..max {a_min}..{a_max} "
      f"(want {REF_ANCHOR[win][0]} / {REF_ANCHOR[win][1]}..{REF_ANCHOR[win][2]}); "
      f"reproduction EXACT: {(a_med, a_min, a_max) == REF_ANCHOR[win]}")
P(f"    all three windows reproduce EXACTLY: {anchor_ok}")
P("")

# ------------------------------------------------------------------
# the resampling (protocol sections 0/2): one rng, frozen probe
# order (s39 hi, s39 tw, s36 hi, s36 tw, s38 hi, s38 tw); each
# probe is WITHIN one (window, arm): 36 runs shuffled into 12
# pseudo-blocks of 3
# ------------------------------------------------------------------
arrs = {(win, tag): run_arr(win, tag) for win, _d in WINDOWS
        for tag in ("hi", "tw")}

obs_triples = np.array([[(3 * b + j) for j in range(3)] for b in range(12)],
                       dtype=np.int64)                    # (12,3)

rng = random.Random(SEED)

def probe(win, tag):
    arr = arrs[(win, tag)]
    d_obs, w_obs = cell_spread(obs_triples[None, :, :], arr)   # (1,12,18), (1,18)
    d_obs = d_obs[0]                                           # (12,18) D
    w_obs = w_obs[0]                                           # (18,) W_c
    m_obs = int(w_obs.max())
    # frozen RNG call order: one shuffle per trial, in trial order
    perms = np.empty((TRIALS, 36), dtype=np.int64)
    for t in range(TRIALS):
        perm = list(range(36))
        rng.shuffle(perm)
        perms[t] = perm
    cnt = 0
    marg = np.zeros(len(ok_cells), dtype=np.int64)
    for i in range(0, TRIALS, BATCH):
        batch = perms[i:i + BATCH]
        triples = batch.reshape(-1, 12, 3)
        _d, w = cell_spread(triples, arr)                      # (b,18)
        m = w.max(axis=1)
        cnt += int((m >= m_obs).sum())
        marg += (w >= w_obs[None, :]).sum(axis=0)
    p = (1 + cnt) / (1 + TRIALS)
    return d_obs, w_obs, m_obs, cnt, marg, p

PROBE_ORDER = [("s39", "hi"), ("s39", "tw"), ("s36", "hi"), ("s36", "tw"),
               ("s38", "hi"), ("s38", "tw")]
res = {}
for win, tag in PROBE_ORDER:
    res[(win, tag)] = probe(win, tag)

def invalidated():
    inv = any(win_info[w]["vmis"] != 0 or not win_info[w]["counts_ok"]
              or not win_info[w]["knob_ok"] or not win_info[w]["fail_ok"]
              or not win_info[w]["cmap_ok"] for w, _d in WINDOWS)
    return inv or (not vec_ok) or (not c1_ok) or (not anchor_ok)

def probe_letter(win, tag):
    """(a)/(b)/(c) for one (window, arm) probe: (c) if any
    invalidation; else (b) if p <= 0.05; else (a)."""
    if invalidated():
        return "(c) NOT EVALUABLE"
    return "(b) EXCEEDS NULL" if res[(win, tag)][5] <= 0.05 \
        else "(a) PER-CELL-SPREAD-NOISE-CONSISTENT"

def window_letter(win):
    """the letter unit (session 40's rule): (c) if invalidated;
    (b) if any arm reads (b) (named which); else (a)."""
    if invalidated():
        return "(c) NOT EVALUABLE", []
    hits = [tag for tag in ("hi", "tw") if res[(win, tag)][5] <= 0.05]
    if hits:
        return "(b) EXCEEDS NULL", hits
    return "(a) PER-CELL-SPREAD-NOISE-CONSISTENT", []

def maxcells_str(win, tag):
    _d, w, m_obs, _c, _m, _p = res[(win, tag)]
    idxs = [ok_cells[i] for i in range(len(ok_cells)) if int(w[i]) == m_obs]
    return ", ".join(ckey_str(i) for i in idxs)

def margcells_str(win, tag):
    _d, _w, _m, _c, marg, _p = res[(win, tag)]
    hit = [ckey_str(ok_cells[i]) for i in range(len(ok_cells))
           if (1 + int(marg[i])) / (1 + TRIALS) <= 0.05]
    return ", ".join(hit) if hit else "(none)"

P("4. T1 THE ROW QUESTION (frozen letters, protocol sections 0/2):")
P("   at the s39 window (the primary window, session 40's framing)")
P("   does ANY ok cell's within-block spread wander W_c =")
P("   max_b D_{b,c} - min_b D_{b,c} (D = max - min of the block's")
P("   75 samples for that cell) EXCEED the within-window")
P("   run-repartition null? Primary per-probe statistic: M = max_c")
P("   W_c (the max-T; the max is taken inside each resampling")
P(f"   trial too). {TRIALS} trials per probe, seed {SEED}, frozen")
P("   probe order s39 hi / s39 tw / s36 hi / s36 tw / s38 hi /")
P(f"   s38 tw; p = (1 + count(M* >= M_obs)) / (1 + {TRIALS}),")
P("   one-sided; D, W and M in exact INTEGER ticks; W_c marginal")
P("   counts/p are descriptive (uncorrected, 108 marginal tests")
P("   across the six probes) and shown in section 6 D1):")
for tag in ("hi", "tw"):
    _d, w, m_obs, cnt, marg, p = res[("s39", tag)]
    P(f"   s39 {tag}: M_obs = {int(m_obs)}; max cell(s) = {maxcells_str('s39', tag)}; "
      f"count {cnt} / {TRIALS + 1}; p = {p:.6f}; p <= 0.05: {p <= 0.05}; "
      f"probe letter {probe_letter('s39', tag)}")
t1, t1hits = window_letter("s39")
P(f"   T1 = {t1}" + (f" (named arms: {', '.join(t1hits)})" if t1hits else ""))
for tag in t1hits:
    P(f"   named cells of s39 {tag} achieving M_obs: {maxcells_str('s39', tag)}; "
      f"cells with MARGINAL p <= 0.05: {margcells_str('s39', tag)}")
P("   NAMED, NOT HIDDEN: (a) does NOT prove 'estimator noise is")
P("   the mechanism' -- the null is RUN-EXCHANGEABILITY at the")
P("   fresh-process granularity within one window and a physical")
P("   driver acting uniformly within the window would also read")
P("   (a); AND each per-cell within-block spread D is itself a")
P("   tail-to-tail RANGE (max-min) of 75 samples -- a scale")
P("   SURROGATE, not a robust scale estimate (IQR/MAD/other")
P("   quantiles and any spread change that keeps the extremes is")
P("   invisible); this probe tests the WANDER of D across blocks")
P("   only -- a per-cell spread LEVEL shift uniform across all 12")
P("   blocks cancels in W_c and is invisible (the D level is")
P("   descriptive only, section 6 D1, no letter); the max-T at")
P("   n=12 blocks is LOW POWER and three windows in ONE day on")
P("   ONE host is LOW POWER (a null is not stationarity, and not")
P("   'no per-cell scale structure'); (b) would implicate")
P("   block-timescale (~3-run / few-second) PER-CELL SCALE")
P("   structure but NOT name it (thermal/scheduling/memory/driver")
P("   state all UNMEASURED); the 18 per-cell MARGINAL p values")
P("   per probe are UNCORRECTED (108 marginal tests across the")
P("   six probes) and carry NO letter (the frozen row test is the")
P("   max-T); the six probe p values / three window letters are")
P("   UNCORRECTED across probes/windows too (the row answer is")
P("   the s39 window letter alone); the frozen 1,000-tick class")
P("   boundary sits INSIDE the per-cell level range (986..1,443")
P("   ticks) and threshold-artifact-vs-representation STAYS")
P("   UNRESOLVED (it binds this level-free probe less directly but")
P("   nothing here resolves it); exchangeability of runs is")
P("   itself an assumption; this letter and sessions")
P("   40/41/42/43/44/45's letters are DIFFERENT statistics over")
P("   the SAME runs -- none confirms nor overturns another, and")
P("   the probes share the same 234 logs and resampling skeleton")
P("   (NOT independent evidence); 20,000 trials (NOT the s35-frozen")
P("   100,000 -- cost, same named deviation as sessions 40-45; p")
P("   resolution 1/20,001 ~= 5e-5); L2 observational ONLY; NO")
P("   causal mechanism; direction UNMEASURED.")
P("")

P("5. REPLICATION LETTERS (pre-registered, same rule per window")
P("   at the s36 and s38 windows; NO cross-window joint letter):")
for win in ("s36", "s38"):
    lw, hits = window_letter(win)
    for tag in ("hi", "tw"):
        _d, _w, m_obs, cnt, _m, p = res[(win, tag)]
        P(f"   {win} {tag}: M_obs = {int(m_obs)} (max cell(s) {maxcells_str(win, tag)}); "
          f"count {cnt} / {TRIALS + 1}; p = {p:.6f}; p <= 0.05: {p <= 0.05}; "
          f"probe letter {probe_letter(win, tag)}")
    P(f"   {win} letter = {lw}" + (f" (named arms: {', '.join(hits)})" if hits else ""))
    for tag in hits:
        P(f"   named cells of {win} {tag} achieving M_obs: {maxcells_str(win, tag)}; "
          f"cells with MARGINAL p <= 0.05: {margcells_str(win, tag)}")
P("")

P("6. DESCRIPTIVE (not the row question):")
P("   D1 the per-cell scoreboard (per probe, cells in cell-map")
P("      order; W_c = max_b D - min_b D over the 12 blocks of the")
P("      probe's (window, arm); D min..max = the cell's 12 block")
P("      within-block ranges' range; D median = the per-cell")
P("      spread LEVEL (descriptive only, no letter); marginal")
P("      count/p = trials with W*_c >= W_obs_c over the same")
P("      20,000 -- UNCORRECTED for multiplicity (108 marginal")
P("      tests), descriptive only, no letter):")
for win, tag in PROBE_ORDER:
    d, w, _m, _c, marg, _p = res[(win, tag)]
    P(f"      {win} {tag}:")
    for ci, k in enumerate(ok_cells):
        mp = (1 + int(marg[ci])) / (1 + TRIALS)
        dmed = statistics.median([int(v) for v in d[:, ci]])
        P(f"      {win} {tag} cell {ci} {ckey_str(k)}: "
          f"W {int(w[ci])} (block D {int(d[:, ci].min())}..{int(d[:, ci].max())}, "
          f"D median {dmed:.1f}); "
          f"marginal count {int(marg[ci])} p {mp:.6f}")
P("   D2 the max-T cell identity and top-3 cells by W_c per probe")
P("      (ties in W_c named; descriptive only):")
for win, tag in PROBE_ORDER:
    _d, w, m_obs, _c, _m, _p = res[(win, tag)]
    order = sorted(range(len(ok_cells)), key=lambda i: (-int(w[i]), i))
    top3 = " ".join(f"{ckey_str(ok_cells[i])}={int(w[i])}"
                    for i in order[:3])
    P(f"      {win} {tag}: max cell(s) {maxcells_str(win, tag)} = {int(m_obs)}; "
      f"top3 {top3}")
P("   D3 the session-45 per-cell block-median wander max-T M and p")
P("      per (window, arm) (quote-only prior from")
P("      publication-s45.txt sections 4/5 -- the LEVEL-structure")
P("      construction this probe complements; quoted for")
P("      orientation only, NO recomputation):")
for win, tag in PROBE_ORDER:
    m45, p45 = REF_S45[(win, tag)]
    P(f"      {win} {tag}: M(s45) = {m45}, p(s45) = {p45:.6f} "
      f"(block-median wander, different statistic)")
P("")

P("7. VERDICT SUMMARY:")
P(f"   T1 (s39 window) = {t1}")
for win, tag in PROBE_ORDER:
    _d, _w, m_obs, cnt, _m, p = res[(win, tag)]
    P(f"   {win} {tag}: M_obs {int(m_obs)} count {cnt}/{TRIALS + 1} p {p:.6f} "
      f"letter {probe_letter(win, tag)}")
for win in ("s36", "s38"):
    lw, _h = window_letter(win)
    P(f"   {win} window letter = {lw}")
P(f"   evaluable inputs: vector reproduction EXACT ({vec_ok}); anchor row "
  f"EXACT ({anchor_ok}); s39 C1 "
  f"({'(a)' if c1_ok else '(b)'}); per-window integrity rows in section 1")
P("   NO hardware ran this tick (ANALYSIS slice; inputs are the")
P("   committed logs of sessions 36/38/39). NO settle-bar-ledger")
P("   line (NO reading -> NO line -> NO day-slot consumption).")
P("   Rule 4 binds: nothing moves; accelerator-targets defaults")
P("   remain provisional (:measured? false); NO vendor optimization")
P("   exists for Intel.")

open(os.path.join(HERE, "publication-s46.txt"), "w").write("\n".join(out) + "\n")
