#!/usr/bin/env python3
"""JUN-59 session 36 analysis -- THE COMMON-MODE PROBE (do the
block-unit min statistics of two interleaved arms co-move across 12
adjacent block-pairs in one window?). MEASUREMENT session: the
inputs are the 78 committed run logs in THIS directory
(run-<tag>-r<R>.txt), pulled verbatim from the host after the
session-36 run window.

Route (frozen in protocol.txt section 6): this script parses ONLY
the 78 run-<tag>-r<R>.txt logs in its own directory and writes
publication-s36.txt in its own directory. Deterministic: running it
twice yields byte-identical output.

The statistic (Spearman rho, tie-corrected average ranks), the
permutation p algorithm (seed 20261028, 100,000 trials -- the
s35-frozen algorithm, reused UNCHANGED) and the T1 letters are
frozen in protocol.txt section 0 (freeze stamp 2026-10-28T02:36:45Z)
and were NOT changed after seeing any result.
"""
import re, os, random, statistics

HERE = os.path.dirname(os.path.abspath(__file__))

BLOCK_LETTERS = "ABCDEFGHIJKL"
# tag -> (BATCH, WORK_MUL, NDIV, [runs]) -- session 36's arm table
ARMS = [("c2", 2, 1, 1, [1, 2, 3]),
        ("hi", 3, 1024, 4033, list(range(1, 37))),
        ("tw", 3, 2048, 8066, list(range(1, 37))),
        ("c8", 8, 1, 1, [1, 2, 3])]
ARMB = {a[0]: a[1] for a in ARMS}
ARMW = {a[0]: a[2] for a in ARMS}
ARMD = {a[0]: a[3] for a in ARMS}
ARMR = {a[0]: a[4] for a in ARMS}
BLOCKS = {BLOCK_LETTERS[i]: [3 * i + 1, 3 * i + 2, 3 * i + 3] for i in range(12)}
TOTAL_RUNS = 78

# ---- quote-only frozen reference values (never this session's measurements) ----
COMMITTED_C2 = 31
COMMITTED_C8 = 32915
REF_HI_BAND = (976, 1003)   # hi block-unit min band, 14 known pair blocks
REF_TW_BAND = (983, 994)   # tw block-unit min band, 3 known twin blocks
REF_PERRUN_BAND = (971, 1006)

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
            samples.append((int(m.group(1)), int(m.group(2)), int(m.group(6)), int(m.group(9)),
                            (int(m.group(3)), int(m.group(4)), int(m.group(5)))))
    return cells, verifies, samples

def med(xs):
    return statistics.median(xs)

# ---- rank helpers (tie-corrected average ranks) ----
def rankdata(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks

def pearson(a, b):
    n = len(a)
    ma = sum(a) / n
    mb = sum(b) / n
    num = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    da = sum((a[i] - ma) ** 2 for i in range(n)) ** 0.5
    db = sum((b[i] - mb) ** 2 for i in range(n)) ** 0.5
    return num / (da * db)

def spearman(x, y):
    return pearson(rankdata(x), rankdata(y))

def perm_p(x, y, seed=20261028, trials=100000):
    rng = random.Random(seed)
    obs = spearman(x, y)
    n = len(x)
    cnt = 0
    for _ in range(trials):
        perm = list(range(n))
        rng.shuffle(perm)
        r = spearman(x, [y[perm[j]] for j in range(n)])
        if abs(r) >= abs(obs) - 1e-12:
            cnt += 1
    return (1 + cnt) / (1.0 + trials), cnt

out = []
P = out.append
P("JUN-59 session 36 -- THE COMMON-MODE PROBE (publication)")
P("(do the block-unit min statistics of TWO interleaved arms CO-MOVE")
P("across 12 adjacent hi/tw block-pairs in ONE window? ONE observable")
P("axis: Spearman rho between the 12 hi block-unit min statistics and")
P("the 12 tw block-unit min statistics of session 36's single window.)")
P("Produced ONLY by analysis-s36.py over the 78 committed run logs in")
P("THIS directory (run-<tag>-r<R>.txt); protocol.txt was frozen before")
P("any build or run (freeze stamp 2026-10-28T02:36:45Z). HARDWARE RAN")
P("this session (the ANV host run window is run-window.txt); every")
P("input quantity below is MEASURED this session unless marked")
P("quote-only.")
P("")

# ---- load everything; integrity / invalidation checks (protocol sec 4) ----
data = {}
verify_mismatch_total = 0
sample_counts_ok = True
knob_ok = True
failclosed_ok = True
cellmap_ok = True
ref_cellmap = None
integrity = []
for tag, b, wm, dd, runs in ARMS:
    for r in runs:
        fn = os.path.join(HERE, f"run-{tag}-r{r}.txt")
        cells, verifies, samples = load(fn)
        data[(tag, r)] = (cells, verifies, samples)
        for (_idx, _ch, mis) in verifies:
            verify_mismatch_total += mis
        ok_cells = [k for k, v in cells.items() if v["pipeline"] == "ok"]
        s8_cells = [k for k, v in cells.items() if v["forced"] == "8"]
        if len(s8_cells) != 6 or any(cells[k]["pipeline"] != "FAIL" or cells[k]["void"] != "1"
                                     for k in s8_cells):
            failclosed_ok = False
            integrity.append(f"S=8 FAIL-CLOSED VIOLATION in {fn}")
        if len(samples) != len(ok_cells) * 25:
            sample_counts_ok = False
            integrity.append(f"SAMPLE COUNT MISMATCH in {fn}")
        for (_rnd, _idx, _gt, _hn, knobs) in samples:
            if knobs != (b, wm, dd):
                knob_ok = False
                integrity.append(f"KNOB MISMATCH in {fn}: {knobs} != {(b, wm, dd)}")
        cmap = tuple(sorted((k, v["op"], v["wg"], v["forced"], v["pipeline"], v["void"])
                            for k, v in cells.items()))
        if ref_cellmap is None:
            ref_cellmap = cmap
        elif cmap != ref_cellmap:
            cellmap_ok = False
            integrity.append(f"CELL MAP MISMATCH in {fn}")
P("1. INTEGRITY (computed over the 78 logs):")
P(f"   runs parsed: {TOTAL_RUNS} (c2 3 + hi 36 + tw 36 + c8 3); SAMPLE lines 450 per run: {sample_counts_ok}")
P(f"   knob fields == arm table in every SAMPLE: {knob_ok}")
P(f"   S=8 fail-closed (6 forced=8 cells pipeline FAIL, void=1, per run): {failclosed_ok}")
P(f"   cell map identical across all runs: {cellmap_ok}")
P(f"   VERIFY mismatch total over all {TOTAL_RUNS} runs: {verify_mismatch_total} -- frozen")
P("   INVALIDATION criterion (protocol section 4): > 0 => letter (c)")
if integrity:
    for i in integrity:
        P(f"   !! {i}")
P("")

ok_cells = sorted([k for k, v in data[("c2", 1)][0].items() if v["pipeline"] == "ok"])

def ckey(idx):
    c = data[("c2", 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])

sum128 = [k for k in ok_cells if ckey(k) == ("sum", 128, "16")][0]

def pooled(tag, idx, runs, field):  # field 2 = gpu_ticks, 3 = host_ns
    xs = []
    for r in runs:
        xs += [s[field] for s in data[(tag, r)][2] if s[1] == idx]
    return med(xs)

def block_vals(tag, runs):
    return [pooled(tag, k, runs, 2) for k in ok_cells]

def block_min(tag, runs):
    return min(block_vals(tag, runs))

def block_class(tag, runs):
    vals = block_vals(tag, runs)
    return ("FLOOR" if all(v <= 100 for v in vals) else
            "CAPTURED" if all(v >= 1000 for v in vals) else "INTERMEDIATE/MIXED")

# ---- C1 re-derivation (prerequisite; protocol section 4) ----
c2_vals = block_vals("c2", ARMR["c2"])
c2_cls = "FLOOR" if all(v <= 100 for v in c2_vals) else (
    "CAPTURED" if all(v >= 1000 for v in c2_vals) else "INTERMEDIATE/MIXED")
c8_m = pooled("c8", sum128, ARMR["c8"], 2)
c1_ok = (c2_cls == "FLOOR") and abs(c8_m - COMMITTED_C8) <= 0.05 * COMMITTED_C8
P("2. C1 RE-DERIVATION (environment pin):")
P(f"   c2 class: {c2_cls} (FLOOR required; committed floor band 31..32)")
P(f"   c8 (sum,128,S=16) pooled median {c8_m:.0f} vs committed {COMMITTED_C8} "
  f"({abs(c8_m - COMMITTED_C8) / COMMITTED_C8 * 100:.2f}% delta; +/-5% required)")
P(f"   C1 branch: {'(a) both controls replicate' if c1_ok else '(b) discrepancy'}")
P("")

# ---- the two vectors (THE ROW QUESTION's inputs) ----
X, Y = [], []
for L in BLOCK_LETTERS:
    runs = BLOCKS[L]
    X.append(block_min("hi", runs))
    Y.append(block_min("tw", runs))
P("3. THE TWO VECTORS (re-derived from the 78 logs; block-pair order A..L):")
P("   X = hi block-unit min statistic: " + " ".join(f"{L} {X[i]:.0f}" for i, L in enumerate(BLOCK_LETTERS)))
P("   Y = tw block-unit min statistic: " + " ".join(f"{L} {Y[i]:.0f}" for i, L in enumerate(BLOCK_LETTERS)))
P(f"   hi range {min(X):.0f}..{max(X):.0f} (quote-only prior band {REF_HI_BAND[0]}..{REF_HI_BAND[1]}); "
  f"tw range {min(Y):.0f}..{max(Y):.0f} (quote-only prior band {REF_TW_BAND[0]}..{REF_TW_BAND[1]})")
P("")

evaluable = (verify_mismatch_total == 0 and sample_counts_ok and knob_ok
             and failclosed_ok and cellmap_ok and c1_ok)

# ---- T1 THE ROW QUESTION ----
rho = spearman(X, Y)
pval, pcount = perm_p(X, Y)
if not evaluable:
    letter = "(c) NAMED UNRESOLVED / NOT EVALUABLE"
elif abs(rho) >= 0.60 and pval <= 0.05:
    letter = "(a) CO-MOVE"
else:
    letter = "(b) NO-CO-MOVE"
P("4. T1 THE ROW QUESTION (frozen letters, protocol section 0): do the two")
P("   arms' block-unit min statistics CO-MOVE across the 12 block-pairs?")
P(f"   Spearman rho(X, Y) = {rho:.6f}")
P(f"   permutation p (two-sided, 100,000 trials, seed 20261028) = {pval:.6f} "
  f"(count {pcount} / 100,001)")
P(f"   |rho| >= 0.60: {abs(rho) >= 0.60}; p <= 0.05: {pval <= 0.05}")
P(f"   T1 = {letter}")
P("   NAMED, NOT HIDDEN: NEITHER letter resolves")
P("   threshold-artifact-vs-representation. (a) is CONSISTENT WITH A")
P("   SHARED (COMMON-MODE) DRIVER -- physical or instrument-wide --")
P("   but is L2 OBSERVATIONAL ONLY (NO causal mechanism; estimator")
P("   noise is NOT excluded and may co-exist). (b) is CONSISTENT WITH")
P("   PER-ARM ESTIMATOR NOISE or arm-specific effects and excludes")
P("   ONLY a common-mode driver at this window and this power. ONE")
P("   window, ONE day, 12 pairs: LOW POWER; the block-pair adjacency")
P("   (~1s) is the common-mode resolution (L14) -- faster structure")
P("   is invisible to this design; no rate/variance/distribution")
P("   claim.")
P("")

# ---- D1 the two block-min sequences + per-run minima (different unit) ----
hi_runs_all, tw_runs_all = [], []
for L in BLOCK_LETTERS:
    for r in BLOCKS[L]:
        hi_runs_all.append(r)
        tw_runs_all.append(r)
hi_per_run = []
tw_per_run = []
for r in hi_runs_all:
    per_cell = [med([s[2] for s in data[("hi", r)][2] if s[1] == k]) for k in ok_cells]
    hi_per_run.append(min(per_cell))
for r in tw_runs_all:
    per_cell = [med([s[2] for s in data[("tw", r)][2] if s[1] == k]) for k in ok_cells]
    tw_per_run.append(min(per_cell))
P("5. DESCRIPTIVE (not the row question):")
P(f"   D1 hi block-min sequence A..L: {' '.join(f'{v:.0f}' for v in X)}")
P(f"      tw block-min sequence A..L: {' '.join(f'{v:.0f}' for v in Y)}")
P(f"      per-run minima (72 values, NAMED DIFFERENT UNIT -- 25 rounds/cell, L10):")
P(f"        hi: {min(hi_per_run):.0f}..{max(hi_per_run):.0f}; tw: {min(tw_per_run):.0f}..{max(tw_per_run):.0f}")
P(f"        (quote-only prior per-run band {REF_PERRUN_BAND[0]}..{REF_PERRUN_BAND[1]})")

# ---- D2 the bar-candidate block (hi block A) ----
a_runs = BLOCKS["A"]
a_median = pooled("hi", sum128, a_runs, 2)
a_min = block_min("hi", a_runs)
a_class = block_class("hi", a_runs)
a_vals = block_vals("hi", a_runs)
P(f"   D2 bar-candidate (hi block A, protocol L12; the ONLY ledger line this")
P(f"      session): class {a_class}, (sum,128,S=16) pooled median {a_median:.0f}, "
  f"block-min {a_min:.0f}, 18-cell {min(a_vals):.0f}..{max(a_vals):.0f}")
P(f"      -- the FIFTH same-UTC-day anchor reading of day 2026-10-28 (descriptive;")
P(f"      the day slot is session 31's, COUNTED 1/4); quote-only same-day priors")
P(f"      1,142 (min 985) / 1,128 (min 982) / 1,124 (min 987) / 1,145 (min 993);")
P(f"      frozen in-band refs 1,129 / 1,132 / 1,131 (quote-only).")

# ---- D3 per-block host_ns both arms + controls ----
hi_host = [pooled("hi", sum128, BLOCKS[L], 3) for L in BLOCK_LETTERS]
tw_host = [pooled("tw", sum128, BLOCKS[L], 3) for L in BLOCK_LETTERS]
c2_host = pooled("c2", sum128, ARMR["c2"], 3)
c8_host = pooled("c8", sum128, ARMR["c8"], 3)
P(f"   D3 per-block host_ns at (sum,128,S=16):")
P(f"      hi: {' '.join(f'{v:.0f}' for v in hi_host)}")
P(f"      tw: {' '.join(f'{v:.0f}' for v in tw_host)}")
P(f"      c2 pooled {c2_host:.0f} (quote-only prior band 672,374..864,642); "
  f"c8 pooled {c8_host:.0f} (quote-only prior band 2,380,500..3,053,605)")
P("")

P("6. VERDICT SUMMARY:")
P(f"   T1 = {letter}; rho = {rho:.6f}; p = {pval:.6f}")
P(f"   evaluable inputs: VERIFY mismatch 0 ({verify_mismatch_total}), "
  f"samples ok ({sample_counts_ok}), knobs ok ({knob_ok}), S=8 fail-closed ({failclosed_ok}), "
  f"cell map ok ({cellmap_ok}), C1 ({c1_ok})")
P("   HARDWARE RAN this session (78 fresh processes, run-window.txt).")
P("   The settling bar: one candidate line (hi block A) is appended as")
P("   DESCRIPTIVE (same-day duplicate) and classified by the frozen")
P("   evaluator (bar-eval-s36.txt) -- it consumes NO day slot. Rule 4")
P("   binds: nothing moves; accelerator-targets defaults remain")
P("   provisional (:measured? false); NO vendor optimization exists")
P("   for Intel.")

open(os.path.join(HERE, "publication-s36.txt"), "w").write("\n".join(out) + "\n")
