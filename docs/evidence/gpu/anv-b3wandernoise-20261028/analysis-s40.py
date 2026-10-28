#!/usr/bin/env python3
"""JUN-59 session 40 analysis -- THE WANDER-NOISE REPARTITION PROBE
(is the within-window block-min wander CONSISTENT WITH
RUN-EXCHANGEABLE SAMPLING NOISE?). ANALYSIS session: NO new hardware;
the inputs are the COMMITTED run logs of the session-36/38/39 run
windows (fixed evidence paths below).

Route (frozen in protocol.txt section 6): this script parses ONLY the
committed run-<tag>-r<R>.txt logs of the three fixed evidence
directories and writes publication-s40.txt in its own directory.
Deterministic: running it twice yields byte-identical output.

The statistic (block-min = min over the 18 ok cells of the pooled
median gpu_ticks of the block's 75 samples; T = range of the 12
block-min values), the resampling null (run-repartition, 20,000
trials, random.Random(20261028) consumed in the frozen probe order)
and the T1/replication letters are frozen in protocol.txt sections 0-3
(freeze stamp 2026-10-28T04:40:07Z) and were NOT changed after seeing
any result.
"""
import re, os, random, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
# (window label, session, evidence dir name) -- frozen probe order 1-6
# is (s39 hi, s39 tw, s36 hi, s36 tw, s38 hi, s38 tw).
WINDOWS = [("s39", "anv-b3joint4-20261028"),
           ("s36", "anv-b3commonmode-20261028"),
           ("s38", "anv-b3joint3-20261028")]
ARMS = {"c2": (2, 1, 1, [1, 2, 3]),
        "hi": (3, 1024, 4033, list(range(1, 37))),
        "tw": (3, 2048, 8066, list(range(1, 37))),
        "c8": (8, 1, 1, [1, 2, 3])}
BLOCK_LETTERS = "ABCDEFGHIJKL"
TRIALS = 20000
SEED = 20261028
COMMITTED_C8 = 32915

# ---- quote-only frozen reference vectors (publication-s39.txt section
# ---- 3: s39 published + s36/s38 quote-only; prior sessions'
# ---- measurements, never recomputed from those sessions' numbers) ----
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
# parse the three windows; integrity per protocol section 4
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

# ---- per-run sorted sample tables (for the resampling) ----
def run_cell_sorted(win, tag, r):
    """cell index -> sorted list of the run's 25 gpu_ticks values."""
    tbl = {k: [] for k in ok_cells}
    for (_rnd, idx, gt, _hn, _kn) in data[(win, tag, r)][2]:
        tbl[idx].append(gt)
    return {k: sorted(v) for k, v in tbl.items()}

def triple_min(tbls, triple):
    """block-min of a 3-run pseudo-block: min over 18 cells of the
    pooled median (38th order statistic of 75 values)."""
    a, b, c = triple
    best = None
    for k in ok_cells:
        m = sorted(tbls[a][k] + tbls[b][k] + tbls[c][k])[37]
        if best is None or m < best:
            best = m
    return best

def triple_min_fast(cache, tbls, triple):
    key = (triple[0], triple[1], triple[2])
    v = cache.get(key)
    if v is None:
        v = triple_min(tbls, key)
        cache[key] = v
    return v

out = []
P = out.append
P("JUN-59 session 40 -- THE WANDER-NOISE REPARTITION PROBE (publication)")
P("(is the within-window block-min wander CONSISTENT WITH")
P("RUN-EXCHANGEABLE SAMPLING NOISE? ONE observable axis: the range T")
P("of the 12 block-unit min statistics of one arm at one window vs a")
P("run-repartition resampling null over the same window's committed")
P("runs.)")
P("Produced ONLY by analysis-s40.py over the COMMITTED run logs of")
P("three fixed evidence directories (anv-b3joint4-20261028 = the s39")
P("window, anv-b3commonmode-20261028 = the s36 window,")
P("anv-b3joint3-20261028 = the s38 window); protocol.txt was frozen")
P("BEFORE any statistic of this probe was computed (freeze stamp")
P("2026-10-28T04:40:07Z). ANALYSIS slice -- NO hardware ran this")
P("tick; every input quantity was MEASURED on aiueos-6600hs Intel BMG")
P("G31 ANV in sessions 36/38/39 (run windows 2026-10-28T02:40:49Z,")
P("03:39:14Z, 04:09:48Z respectively).")
P("")

P("1. INTEGRITY (computed over each window's committed logs; protocol")
P("   section 4):")
for win, _d in WINDOWS:
    info = win_info[win]
    nlogs = 3 + 36 + 36 + 3
    P(f"   {win}: runs parsed {nlogs}; VERIFY mismatch total {info['vmis']}; "
      f"counts ok {info['counts_ok']}; knobs ok {info['knob_ok']}; "
      f"S=8 fail-closed {info['fail_ok']}; cell map ok {info['cmap_ok']}")
    for pr in info["problems"]:
        P(f"   !! {pr}")
P("   INVALIDATION criterion (protocol section 4): any violation =>")
P("   letter (c) for that window.")
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

# ------------------------------------------------------------------
# the resampling (protocol section 2): one rng, frozen probe order
# ------------------------------------------------------------------
rng = random.Random(SEED)

def probe(win, tag):
    tbls = {i: run_cell_sorted(win, tag, i + 1) for i in range(36)}
    cache = {}
    obs_blocks = [triple_min_fast(cache, tbls, (3 * i, 3 * i + 1, 3 * i + 2))
                  for i in range(12)]
    t_obs = max(obs_blocks) - min(obs_blocks)
    cnt = 0
    for _ in range(TRIALS):
        perm = list(range(36))
        rng.shuffle(perm)
        mins = [triple_min_fast(cache, tbls, tuple(perm[3 * i:3 * i + 3])) for i in range(12)]
        t = max(mins) - min(mins)
        if t >= t_obs:
            cnt += 1
    p = (1 + cnt) / (1 + TRIALS)
    return t_obs, obs_blocks, cnt, p

PROBE_ORDER = [("s39", "hi"), ("s39", "tw"), ("s36", "hi"), ("s36", "tw"),
               ("s38", "hi"), ("s38", "tw")]
res = {}
for win, tag in PROBE_ORDER:
    res[(win, tag)] = probe(win, tag)

def letter_for(win):
    """(a)/(b)/(c) for one window: (c) if any invalidation; else
    (b) if any arm p <= 0.05 (named which); else (a)."""
    info = win_info[win]
    inv = (info["vmis"] != 0 or not info["counts_ok"] or not info["knob_ok"]
           or not info["fail_ok"] or not info["cmap_ok"] or not vec_ok)
    if win == "s39" and not c1_ok:
        inv = True
    if inv:
        return "(c) NOT EVALUABLE", None
    hits = [tag for tag in ("hi", "tw") if res[(win, tag)][3] <= 0.05]
    if hits:
        return "(b) EXCEEDS NULL", hits
    return "(a) NOISE-CONSISTENT", None

t1, t1hits = letter_for("s39")
P("4. T1 THE ROW QUESTION (frozen letters, protocol section 3): does")
P("   the s39-window block-min wander EXCEED run-exchangeable")
P(f"   sampling noise? (T = range of 12 block-mins; {TRIALS} trials,")
P(f"   seed {SEED}; p = (1 + count(T* >= T_obs)) / (1 + {TRIALS}),")
P("   one-sided):")
for tag in ("hi", "tw"):
    t_obs, _b, cnt, p = res[("s39", tag)]
    P(f"   s39 {tag}: T_obs = {int(t_obs)} (block-mins {min(int(v) for v in vec['s39'][0 if tag == 'hi' else 1])}.."
      f"{max(int(v) for v in vec['s39'][0 if tag == 'hi' else 1])}); count {cnt} / {TRIALS + 1}; "
      f"p = {p:.6f}; p <= 0.05: {p <= 0.05}")
P(f"   T1 = {t1}" + (f" (named arms: {', '.join(t1hits)})" if t1hits else ""))
P("   NAMED, NOT HIDDEN: (a) does NOT prove 'estimator noise is the")
P("   mechanism' -- the null is RUN-EXCHANGEABILITY at the fresh-")
P("   process granularity and a physical driver acting uniformly")
P("   within the window would also read (a); (b) would implicate")
P("   block-timescale (~3-run / few-second) structure but NOT name it")
P("   (thermal/scheduling/memory/driver state all UNMEASURED). L2")
P("   observational ONLY; NO causal mechanism; direction UNMEASURED;")
P("   exchangeability of runs is itself an assumption; the three")
P("   windows are ONE day / ONE host and the comparison below is")
P("   descriptive only; threshold-artifact-vs-representation STAYS")
P("   UNRESOLVED under any letter.")
P("")

P("5. REPLICATION LETTERS (pre-registered, same rule per (window,")
P("   arm) at the s36 and s38 windows; NO cross-window joint letter):")
rep_lines = []
for win in ("s36", "s38"):
    lw, hits = letter_for(win)
    for tag in ("hi", "tw"):
        t_obs, _b, cnt, p = res[(win, tag)]
        P(f"   {win} {tag}: T_obs = {int(t_obs)}; count {cnt} / {TRIALS + 1}; "
          f"p = {p:.6f}; p <= 0.05: {p <= 0.05}")
    P(f"   {win} letter = {lw}" + (f" (named arms: {', '.join(hits)})" if hits else ""))
    rep_lines.append((win, lw))
P("")

P("6. DESCRIPTIVE (not the row question):")
P("   D1 per-run-unit min ranges (36 points/arm; min over 18 per-cell")
P("      medians of 25 -- NAMED DIFFERENT UNIT L10, no letter):")
for win, _d in WINDOWS:
    for tag in ("hi", "tw"):
        prm = [min(med([s[2] for s in data[(win, tag, r)][2] if s[1] == k])
                   for k in ok_cells) for r in range(1, 37)]
        P(f"      {win} {tag} per-run minima {min(prm):.0f}..{max(prm):.0f}")
P("   D2 T scoreboard (descriptive only -- three windows are not a")
P("      rate, variance or distribution):")
for win in ("s39", "s36", "s38"):
    P(f"      {win}: hi T {int(res[(win, 'hi')][0])}, tw T {int(res[(win, 'tw')][0])}")
P("")

P("7. VERDICT SUMMARY:")
P(f"   T1 = {t1}")
for win, tag in PROBE_ORDER:
    t_obs, _b, cnt, p = res[(win, tag)]
    P(f"   {win} {tag}: T_obs {int(t_obs)} count {cnt}/{TRIALS + 1} p {p:.6f}")
P(f"   evaluable inputs: vector reproduction EXACT ({vec_ok}); s39 C1 "
  f"({'(a)' if c1_ok else '(b)'}); per-window integrity rows in section 1")
P("   NO hardware ran this tick (ANALYSIS slice; inputs are the")
P("   committed logs of sessions 36/38/39). NO settle-bar-ledger line")
P("   (NO reading -> NO line -> NO day-slot consumption). Rule 4")
P("   binds: nothing moves; accelerator-targets defaults remain")
P("   provisional (:measured? false); NO vendor optimization exists")
P("   for Intel.")

open(os.path.join(HERE, "publication-s40.txt"), "w").write("\n".join(out) + "\n")
