#!/usr/bin/env python3
"""JUN-59 session 43 analysis -- THE CROSS-WINDOW BODY-LEVEL
REPARTITION PROBE (does the window-to-window variation of the
BODY level -- the median over the 18 ok cells of the block's
per-cell pooled-median gpu_ticks -- exceed run-exchangeable
sampling noise?). ANALYSIS session: NO new hardware; the inputs
are the COMMITTED run logs of the session-36/38/39 run windows
(fixed evidence paths below).

Route (frozen in protocol.txt section 6): this script parses ONLY
the committed run-<tag>-r<R>.txt logs of the three fixed evidence
directories and writes publication-s43.txt in its own directory.
Deterministic: running it twice yields byte-identical output.

The statistic (per-cell pooled median = the exact 38th order
statistic of the block's 75 samples per ok cell; block-body =
median over the 18 ok cells of those per-cell pooled medians;
L_w = median of the 12 block-bodies of window w; S = max_w L_w -
min_w L_w), the resampling null (run-repartition ACROSS the three
windows, 20,000 trials, random.Random(20261028) consumed in the
frozen probe order hi then tw) and the T1/replication letters are
frozen in protocol.txt sections 0-2 (freeze stamp
2026-10-28T06:07:08Z) and were NOT changed after seeing any
result. The per-cell pooled median of 75 integer samples is the
exact 38th order statistic; numpy 2.5.4 (np.median) is the frozen
implementation path (protocol section 0); the half-tick (2*B =
9th+10th order-statistic sum) and quarter-tick (4*L = 6th+7th
order-statistic sum of the doubled block-bodies) levels are
handled in INTEGER units so every S* >= S_obs comparison is exact
integer arithmetic.
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
# ---- quote-only anchor priors (protocol section 1 (i)): hi block
# ---- A's (sum,128,S=16) pooled median and its 18-cell min..max,
# ---- published by the s36/s38/s39 anchor readings (the
# ---- settle-bar ledger median/min fields and
# ---- publication-s36/38/39 section D) ----
REF_ANCHOR = {"s36": (1142, 991, 1438),
              "s38": (1132, 992, 1443),
              "s39": (1146, 986, 1432)}

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
            ok_cells = [k for k, v in cells.items() if v["pipeline"] == "ok"]
            s8 = [k for k, v in cells.items() if v["forced"] == "8"]
            if len(s8) != 6 or any(cells[k]["pipeline"] != "FAIL" or cells[k]["void"] != "1"
                                   for k in s8):
                fail_ok = False
                problems.append(f"S=8 fail-closed violation in {fn}")
            if len(samples) != len(ok_cells) * 25 or len(verifies) != 24:
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

def body2_ht(vals18):
    """half-tick integer 2*block-body of 18 integer per-cell pooled
    medians: sum of the 9th and 10th order statistics (np.sort path)."""
    s = np.sort(np.asarray(vals18, dtype=np.int64))
    return int(s[8]) + int(s[9])

def block_body2(win, tag, runs):
    return body2_ht(block_vals(win, tag, runs))

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

def triple_bodies2(arr, triples):
    """triples: (n,3) int index array -> (n,) half-tick integers
    2*block-body (median over the 18 ok cells of the pooled median
    of the 75 samples -- the exact 38th order statistic via
    np.median)."""
    sub = arr[triples]                                    # (n,3,18,25)
    pooled_t = sub.transpose(0, 2, 1, 3).reshape(-1, 18, 75)
    m = np.median(pooled_t, axis=2)                       # (n,18) exact
    s = np.sort(m.astype(np.int64), axis=1)
    return s[:, 8] + s[:, 9]                              # (n,) 2*B

def levels4_ht(bodies2, nw=3):
    """quarter-tick integers 4*L per pseudo-window from the 36
    half-tick block-body values: 6th + 7th order-statistic sum of
    the doubled values."""
    out = []
    for w in range(nw):
        seg = np.sort(bodies2[12 * w:12 * w + 12])
        out.append(int(seg[5]) + int(seg[6]))
    return out

def med12_ht(mins12):
    """half-tick integer 2*median of 12 integer values: sum of the
    6th and 7th order statistics (np.sort path)."""
    s = np.sort(mins12)
    return int(s[5]) + int(s[6])

out = []
P = out.append
P("JUN-59 session 43 -- THE CROSS-WINDOW BODY-LEVEL REPARTITION")
P("PROBE (publication)")
P("(does the window-to-window variation of the BODY level -- the")
P("median over the 18 ok cells of the block's per-cell pooled-")
P("median gpu_ticks -- exceed run-exchangeable sampling noise? ONE")
P("observable axis: S = max_w L_w - min_w L_w over the three")
P("probed windows (s36, s38, s39) per arm vs a cross-window")
P("run-repartition resampling null over the same arms' 108")
P("committed runs.)")
P("Produced ONLY by analysis-s43.py over the COMMITTED run logs of")
P("three fixed evidence directories (anv-b3commonmode-20261028 =")
P("the s36 window, anv-b3joint3-20261028 = the s38 window,")
P("anv-b3joint4-20261028 = the s39 window); protocol.txt was")
P("frozen BEFORE any statistic of this probe was computed (freeze")
P("stamp 2026-10-28T06:07:08Z). ANALYSIS slice -- NO hardware ran")
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

# ---- the anchor reproduction row (protocol section 3, NEW) ----
anchor_ok = True
anchor_rows = {}
for win, _d in WINDOWS:
    a_med = pooled(win, "hi", sum128, [1, 2, 3], 2)
    bvals = [int(v) for v in block_vals(win, "hi", [1, 2, 3])]
    a_min, a_max = min(bvals), max(bvals)
    anchor_rows[win] = (a_med, a_min, a_max)
    if (a_med, a_min, a_max) != REF_ANCHOR[win]:
        anchor_ok = False
P("3b. ANCHOR REPRODUCTION ROW (protocol section 3, pre-registered;")
P("    hi block A's (sum,128,S=16) pooled median and 18-cell")
P("    min..max vs the quote-only anchor priors of publication-")
P("    s36/38/39 section D -- mismatch => (c)):")
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
    obs = triple_bodies2(arr, obs_triples)                # (36,) 2*B
    l_obs = levels4_ht(obs)                               # [4*L per window]
    s_obs = max(l_obs) - min(l_obs)                       # quarter-ticks
    cnt = 0
    for _ in range(TRIALS):
        perm = list(range(108))
        rng.shuffle(perm)
        triples = np.array(perm, dtype=np.int64).reshape(36, 3)
        bs = triple_bodies2(arr, triples)
        ls = levels4_ht(bs)
        s = max(ls) - min(ls)
        if s >= s_obs:
            cnt += 1
    p = (1 + cnt) / (1 + TRIALS)
    return l_obs, s_obs, cnt, p

res = {}
for tag in ("hi", "tw"):                                  # frozen probe order
    res[tag] = probe(tag)

def letter_for(tag):
    """(a)/(b)/(c) for one arm: (c) if any invalidation; else (b)
    if p <= 0.05; else (a)."""
    inv = any(win_info[w]["vmis"] != 0 or not win_info[w]["counts_ok"]
              or not win_info[w]["knob_ok"] or not win_info[w]["fail_ok"]
              or not win_info[w]["cmap_ok"] for w, _d in WINDOWS)
    inv = inv or (not vec_ok) or (not c1_ok) or (not anchor_ok)
    if inv:
        return "(c) NOT EVALUABLE"
    return "(b) EXCEEDS NULL" if res[tag][3] <= 0.05 else "(a) BODY-LEVEL-CONSISTENT"

P("4. T1 THE ROW QUESTION (frozen letters, protocol sections 0/2):")
P("   does the window-to-window spread of the BODY LEVEL (the")
P("   median over the 18 ok cells of the block's per-cell pooled")
P(f"   medians) EXCEED the cross-window run-repartition null?")
P(f"   (S = max_w L_w - min_w L_w; {TRIALS}")
P(f"   trials, seed {SEED}, probe order hi then tw; p = (1 +")
P(f"   count(S* >= S_obs)) / (1 + {TRIALS}), one-sided; L and S")
P("   in quarter-tick exact arithmetic, printed in ticks):")
for tag in ("hi", "tw"):
    l_obs, s_obs, cnt, p = res[tag]
    P(f"   {tag}: L per window (s36, s38, s39) = "
      f"{fmt_qt(l_obs[0])}, {fmt_qt(l_obs[1])}, {fmt_qt(l_obs[2])}; "
      f"S_obs = {fmt_qt(s_obs)}; "
      f"count {cnt} / {TRIALS + 1}; p = {p:.6f}; p <= 0.05: {p <= 0.05}; "
      f"arm letter {letter_for(tag)}")
arms_b = [tag for tag in ("hi", "tw") if letter_for(tag) == "(b) EXCEEDS NULL"]
arms_c = [tag for tag in ("hi", "tw") if letter_for(tag) == "(c) NOT EVALUABLE"]
if arms_c:
    t1 = "(c) NOT EVALUABLE"
elif arms_b:
    t1 = "(b) EXCEEDS NULL"
else:
    t1 = "(a) BODY-LEVEL-CONSISTENT"
P(f"   T1 = {t1}" + (f" (named arms: {', '.join(arms_b)})" if arms_b else ""))
P("   NAMED, NOT HIDDEN: (a) does NOT prove 'no physical window-")
P("   level driver' -- the null is run-exchangeability ACROSS")
P("   WINDOWS and a driver acting uniformly within AND across")
P("   windows is invisible by construction; AND the BODY statistic")
P("   is the MEDIAN OVER 18 HETEROGENEOUS CELLS (different")
P("   ops/workgroups span 986..1,438 ticks even within one block)")
P("   -- a window-level shift that moves only SOME cells' levels")
P("   (per-cell structure) can cancel in the median over cells and")
P("   is invisible to this construction (named limitation of the")
P("   row question; a per-cell shift probe is a named candidate")
P("   row); the body level sits ABOVE the frozen 1,000-tick class")
P("   boundary while the min-tail sits AT it -- the threshold-")
P("   artifact-vs-representation ambiguity binds this probe less")
P("   directly but STAYS UNRESOLVED; (b) would implicate window-")
P("   timescale structure in the BODY LEVEL but NOT name it")
P("   (thermal/scheduling/memory/driver state all UNMEASURED);")
P("   exchangeability across windows is a STRONGER assumption than")
P("   session 40's within-window exchangeability and is itself an")
P("   assumption; three windows ~30-60 min apart in ONE day on ONE")
P("   host is LOW POWER (a null at three windows is not evidence")
P("   of stationarity); this letter and sessions 40/41/42's")
P("   letters are DIFFERENT nulls over the SAME runs -- none")
P("   confirms nor overturns another, and the probes share the")
P("   same 234 logs and resampling skeleton (NOT independent")
P("   evidence); L2 observational ONLY; NO causal mechanism;")
P("   direction UNMEASURED; threshold-artifact-vs-representation")
P("   STAYS UNRESOLVED under any letter.")
P("")

P("5. REPLICATION FRAMING (frozen): hi is the primary arm and tw")
P("   the same-rule replication at the SAME three windows; the")
P("   joint T1 above is the row answer; the per-arm letters are")
P("   listed in section 4.")
P("")

P("6. DESCRIPTIVE (not the row question):")
P("   D1 per-run-unit body analog (36 points per (window, arm);")
P("      median over 18 per-cell medians of 25 -- NAMED DIFFERENT")
P("      UNIT L10, no letter): median and range of the 36 per-run")
P("      body values:")
for win, _d in WINDOWS:
    for tag in ("hi", "tw"):
        prv = []
        for r in range(1, 37):
            cm = sorted(int(med([s[2] for s in data[(win, tag, r)][2] if s[1] == k]))
                        for k in ok_cells)
            prv.append(cm[8] + cm[9])                     # 2*body, half-ticks
        srt = sorted(prv)
        qmed = srt[17] + srt[18]                          # 4*median of 36
        P(f"      {win} {tag} per-run body median {fmt_qt(qmed)} "
          f"range {fmt_ht(min(prv))}..{fmt_ht(max(prv))}")
P("   D2 the L/S scoreboard (descriptive only -- three windows are")
P("      not a rate, variance or distribution):")
for tag in ("hi", "tw"):
    l_obs, s_obs, _c, _p = res[tag]
    P(f"      {tag}: L s36 {fmt_qt(l_obs[0])} / s38 {fmt_qt(l_obs[1])} / "
      f"s39 {fmt_qt(l_obs[2])}; S {fmt_qt(s_obs)}")
P("   D3 per-window MEAN of the 12 block-bodies per arm (second")
P("      level summary; descriptive only, no letter):")
bodies2 = {}
for win, _d in WINDOWS:
    for tag in ("hi", "tw"):
        b2 = [block_body2(win, tag, [3 * i + 1, 3 * i + 2, 3 * i + 3])
              for i in range(12)]
        bodies2[(win, tag)] = b2
        P(f"      {win} {tag} block-body mean {sum(b2) / 24:.2f} "
          f"(range {fmt_ht(min(b2))}..{fmt_ht(max(b2))})")
P("   D4 anchor-cell level scoreboard (block A's (sum,128,S=16)")
P("      pooled median + 18-cell min..max; the hi values are the")
P("      section 3b reproduction row's -- quote-only priors exist")
P("      for hi only):")
for win, _d in WINDOWS:
    a_med, a_min, a_max = anchor_rows[win]
    tw_med = pooled(win, "tw", sum128, [1, 2, 3], 2)
    tw_b = [int(v) for v in block_vals(win, "tw", [1, 2, 3])]
    P(f"      {win} hi: median {a_med:.0f} 18-cell {a_min}..{a_max}")
    P(f"      {win} tw: median {tw_med:.0f} 18-cell {min(tw_b)}..{max(tw_b)}")
P("")

P("7. VERDICT SUMMARY:")
P(f"   T1 = {t1}")
for tag in ("hi", "tw"):
    l_obs, s_obs, cnt, p = res[tag]
    P(f"   {tag}: L (s36, s38, s39) = ({fmt_qt(l_obs[0])}, {fmt_qt(l_obs[1])}, "
      f"{fmt_qt(l_obs[2])}); S_obs {fmt_qt(s_obs)}; count {cnt}/{TRIALS + 1}; "
      f"p {p:.6f}; letter {letter_for(tag)}")
P(f"   evaluable inputs: vector reproduction EXACT ({vec_ok}); anchor row "
  f"EXACT ({anchor_ok}); s39 C1 "
  f"({'(a)' if c1_ok else '(b)'}); per-window integrity rows in section 1")
P("   NO hardware ran this tick (ANALYSIS slice; inputs are the")
P("   committed logs of sessions 36/38/39). NO settle-bar-ledger")
P("   line (NO reading -> NO line -> NO day-slot consumption).")
P("   Rule 4 binds: nothing moves; accelerator-targets defaults")
P("   remain provisional (:measured? false); NO vendor optimization")
P("   exists for Intel.")

open(os.path.join(HERE, "publication-s43.txt"), "w").write("\n".join(out) + "\n")
