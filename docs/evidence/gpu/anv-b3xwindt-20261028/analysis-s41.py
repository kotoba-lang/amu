#!/usr/bin/env python3
"""JUN-59 session 41 analysis -- THE CROSS-WINDOW T-SPREAD
REPARTITION PROBE (does the window-to-window variation of the
block-min spread T ITSELF exceed run-exchangeable sampling noise?).
ANALYSIS session: NO new hardware; the inputs are the COMMITTED run
logs of the session-36/38/39 run windows (fixed evidence paths
below).

Route (frozen in protocol.txt section 6): this script parses ONLY
the committed run-<tag>-r<R>.txt logs of the three fixed evidence
directories and writes publication-s41.txt in its own directory.
Deterministic: running it twice yields byte-identical output.

The statistic (block-min = min over the 18 ok cells of the pooled
median gpu_ticks of the block's 75 samples; T_w = range of the 12
block-min values of window w; R = max_w T_w - min_w T_w), the
resampling null (run-repartition ACROSS the three windows, 20,000
trials, random.Random(20261028) consumed in the frozen probe order
hi then tw) and the T1/replication letters are frozen in
protocol.txt sections 0-2 (freeze stamp 2026-10-28T05:05:50Z) and
were NOT changed after seeing any result. The pooled median of 75
integer samples is the exact 38th order statistic; numpy 2.5.4
(np.median) is the frozen implementation path (protocol section 2).
"""
import re, os, random, statistics
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
# (window label, evidence dir name) -- the three windows in
# chronological order (frozen; R is order-independent).
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

def triple_mins(arr, triples):
    """triples: (n,3) int index array -> (n,) block-min ints (min
    over 18 ok cells of the pooled median of the 75 samples --
    the exact 38th order statistic via np.median)."""
    sub = arr[triples]                                    # (n,3,18,25)
    pooled_t = sub.transpose(0, 2, 1, 3).reshape(-1, 18, 75)
    m = np.median(pooled_t, axis=2)                       # (n,18) exact
    return m.min(axis=1).astype(np.int64)

out = []
P = out.append
P("JUN-59 session 41 -- THE CROSS-WINDOW T-SPREAD REPARTITION")
P("PROBE (publication)")
P("(does the window-to-window variation of the block-min spread T")
P("ITSELF exceed run-exchangeable sampling noise? ONE observable")
P("axis: R = max_w T_w - min_w T_w over the three probed windows")
P("(s36, s38, s39) per arm vs a cross-window run-repartition")
P("resampling null over the same arms' 108 committed runs.)")
P("Produced ONLY by analysis-s41.py over the COMMITTED run logs of")
P("three fixed evidence directories (anv-b3commonmode-20261028 =")
P("the s36 window, anv-b3joint3-20261028 = the s38 window,")
P("anv-b3joint4-20261028 = the s39 window); protocol.txt was")
P("frozen BEFORE any statistic of this probe was computed (freeze")
P("stamp 2026-10-28T05:05:50Z). ANALYSIS slice -- NO hardware ran")
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
    obs = triple_mins(arr, obs_triples)                   # (36,)
    t_obs = [int(obs[12 * w:12 * w + 12].max() - obs[12 * w:12 * w + 12].min())
             for w in range(3)]
    r_obs = max(t_obs) - min(t_obs)
    cnt = 0
    for _ in range(TRIALS):
        perm = list(range(108))
        rng.shuffle(perm)
        triples = np.array(perm, dtype=np.int64).reshape(36, 3)
        mins = triple_mins(arr, triples)
        ts = [int(mins[12 * w:12 * w + 12].max() - mins[12 * w:12 * w + 12].min())
              for w in range(3)]
        r = max(ts) - min(ts)
        if r >= r_obs:
            cnt += 1
    p = (1 + cnt) / (1 + TRIALS)
    return t_obs, r_obs, cnt, p

res = {}
for tag in ("hi", "tw"):                                  # frozen probe order
    res[tag] = probe(tag)

def letter_for(tag):
    """(a)/(b)/(c) for one arm: (c) if any invalidation; else (b)
    if p <= 0.05; else (a)."""
    inv = any(win_info[w]["vmis"] != 0 or not win_info[w]["counts_ok"]
              or not win_info[w]["knob_ok"] or not win_info[w]["fail_ok"]
              or not win_info[w]["cmap_ok"] for w, _d in WINDOWS)
    inv = inv or (not vec_ok) or (not c1_ok)
    if inv:
        return "(c) NOT EVALUABLE"
    return "(b) EXCEEDS NULL" if res[tag][3] <= 0.05 else "(a) WINDOW-CONSISTENT"

P("4. T1 THE ROW QUESTION (frozen letters, protocol sections 0/2):")
P("   does the window-to-window spread of T EXCEED the cross-window")
P(f"   run-repartition null? (R = max_w T_w - min_w T_w; {TRIALS}")
P(f"   trials, seed {SEED}, probe order hi then tw; p = (1 +")
P(f"   count(R* >= R_obs)) / (1 + {TRIALS}), one-sided):")
for tag in ("hi", "tw"):
    t_obs, r_obs, cnt, p = res[tag]
    P(f"   {tag}: T per window (s36, s38, s39) = "
      f"{t_obs[0]}, {t_obs[1]}, {t_obs[2]}; R_obs = {r_obs}; "
      f"count {cnt} / {TRIALS + 1}; p = {p:.6f}; p <= 0.05: {p <= 0.05}; "
      f"arm letter {letter_for(tag)}")
arms_b = [tag for tag in ("hi", "tw") if letter_for(tag) == "(b) EXCEEDS NULL"]
arms_c = [tag for tag in ("hi", "tw") if letter_for(tag) == "(c) NOT EVALUABLE"]
if arms_c:
    t1 = "(c) NOT EVALUABLE"
elif arms_b:
    t1 = "(b) EXCEEDS NULL"
else:
    t1 = "(a) WINDOW-CONSISTENT"
P(f"   T1 = {t1}" + (f" (named arms: {', '.join(arms_b)})" if arms_b else ""))
P("   NAMED, NOT HIDDEN: (a) does NOT prove 'no physical window-")
P("   level driver' -- the null is run-exchangeability ACROSS")
P("   WINDOWS and a driver acting uniformly within AND across")
P("   windows is invisible by construction; R tests the window-to-")
P("   window variation of the SPREAD of the 12 block-mins ONLY --")
P("   window-level shifts in LEVEL do not enter R (named")
P("   limitation of the row question); (b) would implicate")
P("   window-timescale structure in the spread but NOT name it")
P("   (thermal/scheduling/memory/driver state all UNMEASURED);")
P("   exchangeability across windows is a STRONGER assumption than")
P("   session 40's within-window exchangeability and is itself an")
P("   assumption; three windows ~30-60 min apart in ONE day on ONE")
P("   host is LOW POWER (a null at three windows is not evidence")
P("   of stationarity); session 40's per-window (a) letters and")
P("   this letter are DIFFERENT nulls -- neither confirms nor")
P("   overturns the other; L2 observational ONLY; NO causal")
P("   mechanism; direction UNMEASURED; threshold-artifact-vs-")
P("   representation STAYS UNRESOLVED under any letter.")
P("")

P("5. REPLICATION FRAMING (frozen): hi is the primary arm and tw")
P("   the same-rule replication at the SAME three windows; the")
P("   joint T1 above is the row answer; the per-arm letters are")
P("   listed in section 4.")
P("")

P("6. DESCRIPTIVE (not the row question):")
P("   D1 per-run-unit min ranges (36 points per (window, arm); min")
P("      over 18 per-cell medians of 25 -- NAMED DIFFERENT UNIT")
P("      L10, no letter):")
for win, _d in WINDOWS:
    for tag in ("hi", "tw"):
        prm = [min(med([s[2] for s in data[(win, tag, r)][2] if s[1] == k])
                   for k in ok_cells) for r in range(1, 37)]
        P(f"      {win} {tag} per-run minima {min(prm):.0f}..{max(prm):.0f}")
P("   D2 the T/R scoreboard (descriptive only -- three windows are")
P("      not a rate, variance or distribution):")
for tag in ("hi", "tw"):
    t_obs, r_obs, _c, _p = res[tag]
    P(f"      {tag}: T s36 {t_obs[0]} / s38 {t_obs[1]} / s39 {t_obs[2]}; "
      f"R {r_obs}")
P("   D3 per-window median of the 12 block-mins per arm (LEVEL")
P("      content -- R does not test level; descriptive only):")
for win, _d in WINDOWS:
    for tag, xi in (("hi", 0), ("tw", 1)):
        X = [int(v) for v in vec[win][xi]]
        P(f"      {win} {tag} block-min median {med(X):.1f} "
          f"(range {min(X)}..{max(X)})")
P("")

P("7. VERDICT SUMMARY:")
P(f"   T1 = {t1}")
for tag in ("hi", "tw"):
    t_obs, r_obs, cnt, p = res[tag]
    P(f"   {tag}: T (s36, s38, s39) = ({t_obs[0]}, {t_obs[1]}, {t_obs[2]}); "
      f"R_obs {r_obs}; count {cnt}/{TRIALS + 1}; p {p:.6f}; "
      f"letter {letter_for(tag)}")
P(f"   evaluable inputs: vector reproduction EXACT ({vec_ok}); s39 C1 "
  f"({'(a)' if c1_ok else '(b)'}); per-window integrity rows in section 1")
P("   NO hardware ran this tick (ANALYSIS slice; inputs are the")
P("   committed logs of sessions 36/38/39). NO settle-bar-ledger")
P("   line (NO reading -> NO line -> NO day-slot consumption).")
P("   Rule 4 binds: nothing moves; accelerator-targets defaults")
P("   remain provisional (:measured? false); NO vendor optimization")
P("   exists for Intel.")

open(os.path.join(HERE, "publication-s41.txt"), "w").write("\n".join(out) + "\n")
