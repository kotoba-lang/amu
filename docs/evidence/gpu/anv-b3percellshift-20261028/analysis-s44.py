#!/usr/bin/env python3
"""JUN-59 session 44 analysis -- THE PER-CELL BODY-SHIFT
REPARTITION PROBE (does ANY of the 18 ok cells show a
window-to-window shift of its per-cell LEVEL -- the cell's own
pooled-median gpu_ticks, held cell by cell instead of through the
median-over-18-cells body -- that exceeds run-exchangeable
sampling noise?). ANALYSIS session: NO new hardware; the inputs
are the COMMITTED run logs of the session-36/38/39 run windows
(fixed evidence paths below).

Route (frozen in protocol.txt section 6): this script parses ONLY
the committed run-<tag>-r<R>.txt logs of the three fixed evidence
directories and writes publication-s44.txt in its own directory.
Deterministic: running it twice yields byte-identical output.

The statistic (per-cell pooled median = the exact 38th order
statistic of the block's 75 samples per ok cell; per-cell window
level L_{w,c} = median of the 12 block per-cell pooled medians of
window w -- 2*L = 6th+7th order-statistic sum; per-cell spread
S_c = max_w L_{w,c} - min_w L_{w,c} -- 2*S integer; the primary
per-arm statistic M_obs = max_c 2*S_c, the max-T), the resampling
null (run-repartition ACROSS the three windows, 20,000 trials,
random.Random(20261028) consumed in the frozen probe order hi
then tw, the max taken inside each trial) and the T1/replication
letters are frozen in protocol.txt sections 0-2 (freeze stamp
2026-10-28T06:35:39Z) and were NOT changed after seeing any
result. numpy 2.5.4 (np.median) is the frozen implementation path
for the pooled 75 (protocol section 0); the resampling is
vectorized over TRIAL BATCHES with the frozen RNG call order
unchanged; every M* >= M_obs and S*_c >= S_obs_c comparison is
exact half-tick INTEGER arithmetic.
"""
import re, os, random, statistics
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
# (window label, evidence dir name) -- the three windows in
# chronological order (frozen; S is order-independent).
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
# ---- quote-only prior (publication-s43.txt section 4/7): the
# ---- s43 BODY SPREAD S per arm (quarter-tick integers 4*S) --
# ---- D3 orientation only, never recomputed here ----
REF_BODY4 = {"hi": 9, "tw": 10}

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

def fmt_qt(q):
    """format a quarter-tick integer (4*X) in ticks with two decimals."""
    return f"{q // 4}.{(q % 4) * 25:02d}"

def fmt_ht(ht):
    """format a half-tick integer (2*X) in ticks with .0/.5."""
    return f"{ht // 2}.0" if ht % 2 == 0 else f"{ht // 2}.5"

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

def cell_levels2(triples, arr):
    """triples: (n,3,3) or (36,3) block index tensor -> per-cell
    level and spread in half-tick integers.
    Returns (n,3,18) 2*L per (pseudo-window, cell) and (n,18) 2*S
    per cell. Per-cell pooled median = the exact 38th order
    statistic of the block's 75 samples (np.median); 2*L = 6th +
    7th order-statistic sum of the 12 block values."""
    if triples.ndim == 2:
        triples = triples[None, :, :]
    n = triples.shape[0]
    sub = arr[triples]                                    # (n,36,3,18,25)
    pooled_t = sub.transpose(0, 1, 3, 2, 4).reshape(n, 36, 18, 75)
    m = np.median(pooled_t, axis=3)                       # (n,36,18) exact
    m = m.astype(np.int64)
    pw = m.reshape(n, 3, 12, 18)
    srt = np.sort(pw, axis=2)                             # (n,3,12,18)
    l2 = srt[:, :, 5, :] + srt[:, :, 6, :]                # (n,3,18) 2*L
    s2 = l2.max(axis=1) - l2.min(axis=1)                  # (n,18) 2*S
    return l2, s2

def med12_ht(mins12):
    """half-tick integer 2*median of 12 integer values: sum of the
    6th and 7th order statistics (np.sort path)."""
    s = np.sort(mins12)
    return int(s[5]) + int(s[6])

out = []
P = out.append
P("JUN-59 session 44 -- THE PER-CELL BODY-SHIFT REPARTITION")
P("PROBE (publication)")
P("(does ANY of the 18 ok cells show a window-to-window shift of")
P("its per-cell LEVEL -- the cell's own pooled-median gpu_ticks,")
P("held cell by cell instead of through the median-over-18-cells")
P("body -- that exceeds run-exchangeable sampling noise? ONE")
P("observable axis per arm: the max-T M = max_c S_c over the 18")
P("cells, S_c = max_w L_{w,c} - min_w L_{w,c} over the three")
P("probed windows (s36, s38, s39), vs a cross-window")
P("run-repartition resampling null over the same arms' 108")
P("committed runs; the max over cells is taken INSIDE each")
P("resampling trial too (family-wise over the 18 cells).)")
P("Produced ONLY by analysis-s44.py over the COMMITTED run logs of")
P("three fixed evidence directories (anv-b3commonmode-20261028 =")
P("the s36 window, anv-b3joint3-20261028 = the s38 window,")
P("anv-b3joint4-20261028 = the s39 window); protocol.txt was")
P("frozen BEFORE any statistic of this probe was computed (freeze")
P("stamp 2026-10-28T06:35:39Z). ANALYSIS slice -- NO hardware ran")
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
P("3. THE BLOCK-MIN VECTORS (re-derived from the committed logs;")
P("   block order A..L; reproduction check vs the published/")
P("   quote-only vectors of publication-s39.txt section 3 --")
P("   mismatch => (c)):")
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
# order (hi then tw); 108 runs per arm pooled across the three
# windows (window order s36, s38, s39)
# ------------------------------------------------------------------
pool_arr = {}
for tag in ("hi", "tw"):
    arrs = [run_arr(win, tag) for win, _d in WINDOWS]
    pool_arr[tag] = np.concatenate(arrs, axis=0)          # (108,18,25)

obs_triples = []
for w in range(3):
    for b in range(12):
        o = 36 * w + 3 * b
        obs_triples.append((o, o + 1, o + 2))
obs_triples = np.array(obs_triples, dtype=np.int64)       # (36,3)

rng = random.Random(SEED)

def probe(tag):
    arr = pool_arr[tag]
    l_obs, s2_obs = cell_levels2(obs_triples, arr)         # (1,3,18), (1,18)
    l_obs = l_obs[0]                                       # (3,18) 2*L
    s2_obs = s2_obs[0]                                     # (18,) 2*S
    m_obs = int(s2_obs.max())
    # frozen RNG call order: one shuffle per trial, in trial order
    perms = np.empty((TRIALS, 108), dtype=np.int64)
    for t in range(TRIALS):
        perm = list(range(108))
        rng.shuffle(perm)
        perms[t] = perm
    cnt = 0
    marg = np.zeros(len(ok_cells), dtype=np.int64)
    for i in range(0, TRIALS, BATCH):
        batch = perms[i:i + BATCH]
        triples = batch.reshape(-1, 36, 3)
        _l, s2 = cell_levels2(triples, arr)                # (b,18)
        m = s2.max(axis=1)
        cnt += int((m >= m_obs).sum())
        marg += (s2 >= s2_obs[None, :]).sum(axis=0)
    p = (1 + cnt) / (1 + TRIALS)
    return l_obs, s2_obs, m_obs, cnt, marg, p

res = {}
for tag in ("hi", "tw"):                                  # frozen probe order
    res[tag] = probe(tag)

def invalidated():
    inv = any(win_info[w]["vmis"] != 0 or not win_info[w]["counts_ok"]
              or not win_info[w]["knob_ok"] or not win_info[w]["fail_ok"]
              or not win_info[w]["cmap_ok"] for w, _d in WINDOWS)
    return inv or (not vec_ok) or (not c1_ok) or (not anchor_ok)

def letter_for(tag):
    """(a)/(b)/(c) for one arm: (c) if any invalidation; else (b)
    if p <= 0.05; else (a)."""
    if invalidated():
        return "(c) NOT EVALUABLE"
    return "(b) EXCEEDS NULL" if res[tag][5] <= 0.05 else "(a) PER-CELL-CONSISTENT"

def maxcells_str(tag):
    _l, s2, m_obs, _c, _m, _p = res[tag]
    idxs = [ok_cells[i] for i in range(len(ok_cells)) if int(s2[i]) == m_obs]
    return ", ".join(ckey_str(i) for i in idxs)

P("4. T1 THE ROW QUESTION (frozen letters, protocol sections 0/2):")
P("   does ANY ok cell's cross-window LEVEL spread S_c = max_w")
P("   L_{w,c} - min_w L_{w,c} (per-cell level L_{w,c} = median of")
P("   the 12 block per-cell pooled medians of window w) EXCEED")
P("   the cross-window run-repartition null? Primary per-arm")
P("   statistic: M = max_c S_c (the max-T; the max is taken")
P(f"   inside each resampling trial too). {TRIALS} trials, seed")
P(f"   {SEED}, probe order hi then tw; p = (1 + count(M* >= M_obs)")
P(f"   / (1 + {TRIALS}), one-sided; L, S and M in half-tick exact")
P("   arithmetic, printed in ticks; S_c marginal counts/p are")
P("   descriptive (uncorrected) and shown in section 6 D1):")
for tag in ("hi", "tw"):
    l_obs, s2_obs, m_obs, cnt, marg, p = res[tag]
    P(f"   {tag}: M_obs = {fmt_ht(m_obs)}; max cell(s) = {maxcells_str(tag)}; "
      f"count {cnt} / {TRIALS + 1}; p = {p:.6f}; p <= 0.05: {p <= 0.05}; "
      f"arm letter {letter_for(tag)}")
arms_b = [tag for tag in ("hi", "tw") if letter_for(tag) == "(b) EXCEEDS NULL"]
arms_c = [tag for tag in ("hi", "tw") if letter_for(tag) == "(c) NOT EVALUABLE"]
if arms_c:
    t1 = "(c) NOT EVALUABLE"
elif arms_b:
    t1 = "(b) EXCEEDS NULL"
else:
    t1 = "(a) PER-CELL-CONSISTENT"
P(f"   T1 = {t1}" + (f" (named arms: {', '.join(arms_b)})" if arms_b else ""))
if arms_b:
    for tag in arms_b:
        _l, _s, _m, _c, marg, _p = res[tag]
        hit = [ckey_str(ok_cells[i]) for i in range(len(ok_cells))
               if (1 + int(marg[i])) / (1 + TRIALS) <= 0.05]
        P(f"   named cells of {tag} with MARGINAL p <= 0.05: "
          + (", ".join(hit) if hit else "(none)"))
P("   NAMED, NOT HIDDEN: (a) does NOT prove 'no physical per-cell")
P("   window-level driver' -- the null is run-exchangeability")
P("   ACROSS WINDOWS and a driver acting uniformly within AND")
P("   across windows is invisible by construction; AND each per-")
P("   cell level is itself a median of 12 block values of pooled")
P("   medians of 75 samples -- shifts of only the per-cell SPREAD,")
P("   only other distribution quantiles, or only scales inside")
P("   the 25-sample/3-run units are invisible to this")
P("   construction; the max-T at n=12 blocks per window is LOW")
P("   POWER and three windows ~30-60 min apart in ONE day on ONE")
P("   host is LOW POWER (a null is not stationarity, and not")
P("   'no per-cell structure'); (b) would implicate window-")
P("   timescale PER-CELL level structure but NOT name it")
P("   (thermal/scheduling/memory/driver state all UNMEASURED);")
P("   the 18 per-cell MARGINAL p values are UNCORRECTED (36")
P("   marginal tests across two arms) and carry NO letter (the")
P("   frozen row test is the max-T); cells span 986..1,443 ticks")
P("   in level even within one block -- the frozen 1,000-tick")
P("   class boundary sits INSIDE the per-cell level range, so the")
P("   threshold-artifact-vs-representation ambiguity binds")
P("   per-cell rows directly and STAYS UNRESOLVED; exchangeability")
P("   across windows is a STRONGER assumption than session 40's")
P("   within-window exchangeability and is itself an assumption;")
P("   this letter and sessions 40/41/42/43's letters are DIFFERENT")
P("   nulls over the SAME runs -- none confirms nor overturns")
P("   another, and the probes share the same 234 logs and")
P("   resampling skeleton (NOT independent evidence); 20,000")
P("   trials (NOT the s35-frozen 100,000 -- cost, same named")
P("   deviation as sessions 40/41/42/43; p resolution")
P("   1/20,001 ~= 5e-5); L2 observational ONLY; NO causal")
P("   mechanism; direction UNMEASURED.")
P("")

P("5. REPLICATION FRAMING (frozen): hi is the primary arm and tw")
P("   the same-rule replication at the SAME three windows; the")
P("   joint T1 above is the row answer; the per-arm letters are")
P("   listed in section 4.")
P("")

P("6. DESCRIPTIVE (not the row question):")
P("   D1 the per-cell scoreboard (per arm, cells in cell-map")
P("      order; L at s36/s38/s39 in half-tick exact arithmetic;")
P("      S_c = max_w L - min_w L; marginal count/p = trials with")
P("      S*_c >= S_obs_c over the same 20,000 -- UNCORRECTED for")
P("      multiplicity (36 marginal tests), descriptive only, no")
P("      letter):")
for tag in ("hi", "tw"):
    l_obs, s2_obs, m_obs, cnt, marg, p = res[tag]
    P(f"      {tag}:")
    for ci, k in enumerate(ok_cells):
        mp = (1 + int(marg[ci])) / (1 + TRIALS)
        P(f"      {tag} cell {ci} {ckey_str(k)}: "
          f"L {fmt_ht(int(l_obs[0][ci]))} / {fmt_ht(int(l_obs[1][ci]))} / "
          f"{fmt_ht(int(l_obs[2][ci]))}; S_c {fmt_ht(int(s2_obs[ci]))}; "
          f"marginal count {int(marg[ci])} p {mp:.6f}")
P("   D2 the max-T cell identity and top-3 cells by S_c per arm")
P("      (ties in S_c named; descriptive only):")
for tag in ("hi", "tw"):
    _l, s2_obs, m_obs, _c, _m, _p = res[tag]
    order = sorted(range(len(ok_cells)), key=lambda i: (-int(s2_obs[i]), i))
    top3 = " ".join(f"{ckey_str(ok_cells[i])}={fmt_ht(int(s2_obs[i]))}"
                    for i in order[:3])
    P(f"      {tag}: max cell(s) {maxcells_str(tag)} = {fmt_ht(m_obs)}; "
      f"top3 {top3}")
P("   D3 the s43 BODY SPREAD S per arm (quote-only prior from")
P("      publication-s43.txt section 4/7 -- the median-over-cells")
P("      construction this probe replaces; quoted for orientation")
P("      only, NO recomputation):")
for tag in ("hi", "tw"):
    P(f"      {tag}: S_body(s43) = {fmt_qt(REF_BODY4[tag])} "
      f"(quarter-tick construction, different statistic)")
P("")

P("7. VERDICT SUMMARY:")
P(f"   T1 = {t1}")
for tag in ("hi", "tw"):
    _l, _s, m_obs, cnt, _m, p = res[tag]
    P(f"   {tag}: M_obs = {fmt_ht(m_obs)} (max cell(s) {maxcells_str(tag)}); "
      f"count {cnt}/{TRIALS + 1}; p {p:.6f}; letter {letter_for(tag)}")
P(f"   evaluable inputs: vector reproduction EXACT ({vec_ok}); anchor row "
  f"EXACT ({anchor_ok}); s39 C1 "
  f"({'(a)' if c1_ok else '(b)'}); per-window integrity rows in section 1")
P("   NO hardware ran this tick (ANALYSIS slice; inputs are the")
P("   committed logs of sessions 36/38/39). NO settle-bar-ledger")
P("   line (NO reading -> NO line -> NO day-slot consumption).")
P("   Rule 4 binds: nothing moves; accelerator-targets defaults")
P("   remain provisional (:measured? false); NO vendor optimization")
P("   exists for Intel.")

open(os.path.join(HERE, "publication-s44.txt"), "w").write("\n".join(out) + "\n")
