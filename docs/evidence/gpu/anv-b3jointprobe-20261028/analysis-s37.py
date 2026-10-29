#!/usr/bin/env python3
"""JUN-59 session 37 analysis -- THE SAME-WINDOW JOINT PROBE (at ONE
window, do the block-unit min statistics couple to the host-side
proxy within each arm AND across the two arms?). ANALYSIS slice: NO
new hardware; the inputs are session 36's 78 committed run logs in
../anv-b3commonmode-20261028/.

Route (frozen in protocol.txt section 6): this script parses ONLY
../anv-b3commonmode-20261028/run-<tag>-r<R>.txt (78 logs) plus
publication-s36.txt's published tables as quote-only cross-check
constants, and writes publication-s37.txt in its own directory.
Deterministic: running it twice yields byte-identical output.

The statistic (Spearman rho, tie-corrected average ranks), the
permutation p algorithm (seed 20261028, 100,000 trials -- the
s35-frozen algorithm, reused UNCHANGED) and the T1 letters are
frozen in protocol.txt section 0 (freeze stamp 2026-10-28T03:06:03Z)
and were NOT changed after seeing any result.
"""
import re, os, random, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "anv-b3commonmode-20261028")

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

# ---- quote-only frozen reference values (publication-s36.txt; s36's
# ---- measurements, never this session's) ----
REF_X = [991, 989, 981, 998, 993, 985, 984, 997, 994, 994, 980, 982]
REF_Y = [988, 985, 994, 993, 994, 995, 992, 984, 987, 984, 993, 981]
REF_HI_HOST = [311901, 309627, 308465, 311051, 309968, 310649, 307113,
               310719, 310348, 310720, 308987, 309547]
REF_TW_HOST = [310259, 308936, 311031, 311871, 465709, 307253, 310520,
               310319, 309598, 309477, 307814, 311300]
REF_C_RHO = -0.251762     # s36's published cross-arm rho (rounded 6)
REF_C_PCNT = 42507        # s36's published permutation count / 100,001
REF_C_P = 0.425076        # s36's published permutation p (rounded 6)
COMMITTED_C2 = 31
COMMITTED_C8 = 32915

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

def comove(x, y):
    rho = spearman(x, y)
    pval, pcnt = perm_p(x, y)
    return rho, pval, pcnt, (abs(rho) >= 0.60 and pval <= 0.05)

out = []
P = out.append
P("JUN-59 session 37 -- THE SAME-WINDOW JOINT PROBE (publication)")
P("(at ONE window, do the block-unit min statistics couple to the")
P("host-side proxy within each arm AND across the two arms? ONE")
P("observable axis: the joint coupling pattern over the three frozen")
P("sub-statistics A/B/C at session 36's single window -- (A) rho(hi")
P("block-min, hi block host_ns), (B) rho(tw block-min, tw block")
P("host_ns), (C) rho(hi block-min, tw block-min), all block unit")
P("n=12.)")
P("Produced ONLY by analysis-s37.py over session 36's 78 committed")
P("run logs in ../anv-b3commonmode-20261028/ (run-<tag>-r<R>.txt);")
P("protocol.txt was frozen before the statistic was computed (freeze")
P("stamp 2026-10-28T03:06:03Z). NO HARDWARE RAN this session (named;")
P("every input quantity was MEASURED in session 36).")
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
        fn = os.path.join(SRC, f"run-{tag}-r{r}.txt")
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

# ---- C1 re-derivation (prerequisite; protocol section 4) ----
c2_vals = block_vals("c2", ARMR["c2"])
c2_cls = "FLOOR" if all(v <= 100 for v in c2_vals) else (
    "CAPTURED" if all(v >= 1000 for v in c2_vals) else "INTERMEDIATE/MIXED")
c8_m = pooled("c8", sum128, ARMR["c8"], 2)
c1_ok = (c2_cls == "FLOOR") and abs(c8_m - COMMITTED_C8) <= 0.05 * COMMITTED_C8
P("2. C1 RE-DERIVATION (environment pin, from the s36 logs):")
P(f"   c2 class: {c2_cls} (FLOOR required; committed floor band 31..32)")
P(f"   c8 (sum,128,S=16) pooled median {c8_m:.0f} vs committed {COMMITTED_C8} "
  f"({abs(c8_m - COMMITTED_C8) / COMMITTED_C8 * 100:.2f}% delta; +/-5% required)")
P(f"   C1 branch: {'(a) both controls replicate' if c1_ok else '(b) discrepancy'}")
P("")

# ---- the four vectors (the three couplings' inputs) + quote-only anchor ----
X, Y, HH, TH = [], [], [], []
for L in BLOCK_LETTERS:
    runs = BLOCKS[L]
    X.append(block_min("hi", runs))
    Y.append(block_min("tw", runs))
    HH.append(pooled("hi", sum128, runs, 3))
    TH.append(pooled("tw", sum128, runs, 3))
anchor_ok = (X == REF_X and Y == REF_Y and HH == REF_HI_HOST and TH == REF_TW_HOST)
P("3. THE FOUR VECTORS (re-derived from the 78 logs; block order A..L):")
P("   X = hi block-min:     " + " ".join(f"{L} {X[i]:.0f}" for i, L in enumerate(BLOCK_LETTERS)))
P("   Y = tw block-min:     " + " ".join(f"{L} {Y[i]:.0f}" for i, L in enumerate(BLOCK_LETTERS)))
P("   HH = hi block host_ns: " + " ".join(f"{L} {HH[i]:.0f}" for i, L in enumerate(BLOCK_LETTERS)))
P("   TH = tw block host_ns: " + " ".join(f"{L} {TH[i]:.0f}" for i, L in enumerate(BLOCK_LETTERS)))
P(f"   quote-only anchor (publication-s36.txt section 3 + D3, byte-exact): {anchor_ok}")
P("")

evaluable = (verify_mismatch_total == 0 and sample_counts_ok and knob_ok
             and failclosed_ok and cellmap_ok and c1_ok)

# ---- T1 THE ROW QUESTION: the three frozen couplings ----
rhoA, pA, cntA, cmA = comove(X, HH)
rhoB, pB, cntB, cmB = comove(Y, TH)
rhoC, pC, cntC, cmC = comove(X, Y)
anchor_c = (round(rhoC, 6) == REF_C_RHO and cntC == REF_C_PCNT and round(pC, 6) == REF_C_P)
if not evaluable or not anchor_c:
    letter = "(c) NAMED UNRESOLVED / NOT EVALUABLE"
elif not (cmA or cmB or cmC):
    letter = "(a) JOINT NO-COUPLE"
else:
    letter = "(b) ANY COUPLE"
P("4. T1 THE ROW QUESTION (frozen letters, protocol section 0): the joint")
P("   coupling pattern of (A) hi proxy, (B) tw proxy, (C) cross-arm at")
P("   session 36's single window (block unit, n=12; Spearman rho +")
P("   two-sided permutation p, 100,000 trials, seed 20261028):")
P(f"   (A) hi proxy:  rho = {rhoA:.6f}, p = {pA:.6f} (count {cntA} / 100,001), "
  f"|rho| >= 0.60: {abs(rhoA) >= 0.60}, p <= 0.05: {pA <= 0.05}, CO-MOVE: {cmA}")
P(f"   (B) tw proxy:  rho = {rhoB:.6f}, p = {pB:.6f} (count {cntB} / 100,001), "
  f"|rho| >= 0.60: {abs(rhoB) >= 0.60}, p <= 0.05: {pB <= 0.05}, CO-MOVE: {cmB}")
P(f"   (C) cross-arm: rho = {rhoC:.6f}, p = {pC:.6f} (count {cntC} / 100,001), "
  f"|rho| >= 0.60: {abs(rhoC) >= 0.60}, p <= 0.05: {pC <= 0.05}, CO-MOVE: {cmC}")
P(f"   (C) integrity anchor vs s36's published letter: rho {REF_C_RHO:.6f} / "
  f"count {REF_C_PCNT} / p {REF_C_P:.6f} reproduced exactly: {anchor_c}")
P(f"   T1 = {letter}")
P("   NAMED, NOT HIDDEN: NEITHER letter resolves")
P("   threshold-artifact-vs-representation. (a) says the s35 (b) +")
P("   s36 (b) pattern REPLICATES at one common window -- consistent")
P("   with per-arm estimator noise or arm-specific effects, and")
P("   excludes ONLY these three couplings at this window and this")
P("   power. (b) names which coupling reads CO-MOVE at this window --")
P("   L2 OBSERVATIONAL ONLY (NO causal mechanism; a shared driver")
P("   could move both members of a pair). ONE window, ONE day, 12")
P("   blocks: LOW POWER; the three sub-statistics share the same 12")
P("   blocks (L15 -- not independent tests); the block-pair adjacency")
P("   (~1s) is the resolution (L14); no rate/variance/distribution")
P("   claim.")
P("")

# ---- D1 per-run-unit analogs (different unit, L10; descriptive) ----
def per_run_min(tag, r):
    return min(med([s[2] for s in data[(tag, r)][2] if s[1] == k]) for k in ok_cells)

def per_run_host(tag, r):
    return med([s[3] for s in data[(tag, r)][2] if s[1] == sum128])

hi_pm = [per_run_min("hi", r) for r in ARMR["hi"]]
tw_pm = [per_run_min("tw", r) for r in ARMR["tw"]]
hi_ph = [per_run_host("hi", r) for r in ARMR["hi"]]
tw_ph = [per_run_host("tw", r) for r in ARMR["tw"]]
rhoA1, pA1, _cA1, _m = comove(hi_pm, hi_ph)
rhoB1, pB1, _cB1, _m = comove(tw_pm, tw_ph)
P("5. DESCRIPTIVE (not the row question):")
P(f"   D1 per-run-unit analogs (36 points per arm; 25 rounds/cell;")
P(f"      NAMED DIFFERENT UNIT L10 -- no letter):")
P(f"      (A1) hi per-run min vs per-run host_ns: rho = {rhoA1:.6f}, p = {pA1:.6f}")
P(f"      (B1) tw per-run min vs per-run host_ns: rho = {rhoB1:.6f}, p = {pB1:.6f}")
P(f"      per-run min ranges: hi {min(hi_pm):.0f}..{max(hi_pm):.0f}, tw {min(tw_pm):.0f}..{max(tw_pm):.0f}")

# ---- D2 (B) leave-one-out block E (named in the freeze; descriptive) ----
idx_no_E = [i for i in range(12) if BLOCK_LETTERS[i] != "E"]
rhoB_loo = spearman([Y[i] for i in idx_no_E], [TH[i] for i in idx_no_E])
pB_loo, cntB_loo = perm_p([Y[i] for i in idx_no_E], [TH[i] for i in idx_no_E])
P(f"   D2 (B) without block E (tw block E host_ns {TH[4]:.0f} = the session-36")
P(f"      named L3 excursion, cause UNMEASURED; leave-one-out NAMED in the")
P(f"      freeze, descriptive only, the T1 letter always uses all 12 blocks):")
P(f"      rho = {rhoB_loo:.6f}, p = {pB_loo:.6f} (count {cntB_loo} / 100,001)")
P("")

P("6. VERDICT SUMMARY:")
P(f"   T1 = {letter}")
P(f"   (A) rho {rhoA:.6f} / p {pA:.6f} CO-MOVE {cmA}; (B) rho {rhoB:.6f} / p {pB:.6f} "
  f"CO-MOVE {cmB}; (C) rho {rhoC:.6f} / p {pC:.6f} CO-MOVE {cmC}")
P(f"   evaluable inputs: VERIFY mismatch 0 ({verify_mismatch_total}), "
  f"samples ok ({sample_counts_ok}), knobs ok ({knob_ok}), S=8 fail-closed ({failclosed_ok}), "
  f"cell map ok ({cellmap_ok}), C1 ({c1_ok}), s36 anchor ({anchor_c})")
P("   NO HARDWARE RAN this session (analysis over session 36's 78 committed")
P("   logs; every input quantity was MEASURED in session 36).")
P("   The settling bar: NO reading -> NO ledger line, NO day-slot")
P("   consumption (bar-eval-s37.txt, the frozen evaluator over the")
P("   unchanged ledger). Rule 4 binds: nothing moves; accelerator-targets")
P("   defaults remain provisional (:measured? false); NO vendor")
P("   optimization exists for Intel.")

open(os.path.join(HERE, "publication-s37.txt"), "w").write("\n".join(out) + "\n")
