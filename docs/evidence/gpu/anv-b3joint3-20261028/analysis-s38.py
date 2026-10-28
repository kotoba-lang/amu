#!/usr/bin/env python3
"""JUN-59 session 38 analysis -- THE THIRD-WINDOW JOINT PROBE (does
the session-37 joint coupling pattern replicate at a THIRD window?).
MEASUREMENT session: the inputs are the 78 committed run logs in
THIS directory (run-<tag>-r<R>.txt), pulled verbatim from the host
after the session-38 run window.

Route (frozen in protocol.txt section 6): this script parses ONLY
the 78 run-<tag>-r<R>.txt logs in its own directory and writes
publication-s38.txt in its own directory. Deterministic: running it
twice yields byte-identical output.

The statistic (Spearman rho, tie-corrected average ranks), the
permutation p algorithm (seed 20261028, 100,000 trials -- the
s35-frozen algorithm, reused UNCHANGED) and the T1 letters are
frozen in protocol.txt section 0 (freeze stamp
2026-10-28T03:36:21Z) and were NOT changed after seeing any result.
"""
import re, os, random, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = HERE

BLOCK_LETTERS = "ABCDEFGHIJKL"
# tag -> (BATCH, WORK_MUL, NDIV, [runs]) -- session 38's arm table
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

# ---- quote-only frozen reference values (publication-s36.txt /
# ---- s37's publication; prior sessions' measurements, never this
# ---- session's) ----
REF_X_S36 = [991, 989, 981, 998, 993, 985, 984, 997, 994, 994, 980, 982]
REF_Y_S36 = [988, 985, 994, 993, 994, 995, 992, 984, 987, 984, 993, 981]
REF_HI_HOST_S36 = [311901, 309627, 308465, 311051, 309968, 310649, 307113,
                   310719, 310348, 310720, 308987, 309547]
REF_TW_HOST_S36 = [310259, 308936, 311031, 311871, 465709, 307253, 310520,
                   310319, 309598, 309477, 307814, 311300]
COMMITTED_C2 = 31
COMMITTED_C8 = 32915
# bar quote-only
REF_BAR = (1129, 1132, 1131)
SAMEDAY = [("s31", 1142, 985), ("s32", 1128, 982), ("s33", 1124, 987),
           ("s34", 1145, 993), ("s36", 1142, 991)]

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
P("JUN-59 session 38 -- THE THIRD-WINDOW JOINT PROBE (publication)")
P("(does the session-37 joint coupling pattern replicate at a THIRD")
P("window? ONE observable axis: the joint coupling pattern over the")
P("three frozen sub-statistics A/B/C at this third session window --")
P("(A) rho(hi block-min, hi block host_ns), (B) rho(tw block-min, tw")
P("block host_ns), (C) rho(hi block-min, tw block-min), all block")
P("unit n=12.)")
P("Produced ONLY by analysis-s38.py over THIS directory's 78")
P("committed run logs (run-<tag>-r<R>.txt); protocol.txt was frozen")
P("before the runs (freeze stamp 2026-10-28T03:36:21Z). HARDWARE")
P("RAN (MEASURED, aiueos-6600hs Intel BMG G31 ANV): 78 fresh")
P("processes, run window 2026-10-28T03:39:14Z..03:39:31Z.")
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
P("2. C1 RE-DERIVATION (environment pin, from this window's logs):")
P(f"   c2 class: {c2_cls} (FLOOR required; committed floor band 31..32)")
P(f"   c8 (sum,128,S=16) pooled median {c8_m:.0f} vs committed {COMMITTED_C8} "
  f"({abs(c8_m - COMMITTED_C8) / COMMITTED_C8 * 100:.2f}% delta; +/-5% required)")
P(f"   C1 branch: {'(a) both controls replicate' if c1_ok else '(b) discrepancy'}")
P("")

# ---- the four vectors (the three couplings' inputs) ----
X, Y, HH, TH = [], [], [], []
for L in BLOCK_LETTERS:
    runs = BLOCKS[L]
    X.append(block_min("hi", runs))
    Y.append(block_min("tw", runs))
    HH.append(pooled("hi", sum128, runs, 3))
    TH.append(pooled("tw", sum128, runs, 3))
P("3. THE FOUR VECTORS (re-derived from the 78 logs; block order A..L):")
P("   X = hi block-min:     " + " ".join(f"{L} {X[i]:.0f}" for i, L in enumerate(BLOCK_LETTERS)))
P("   Y = tw block-min:     " + " ".join(f"{L} {Y[i]:.0f}" for i, L in enumerate(BLOCK_LETTERS)))
P("   HH = hi block host_ns: " + " ".join(f"{L} {HH[i]:.0f}" for i, L in enumerate(BLOCK_LETTERS)))
P("   TH = tw block host_ns: " + " ".join(f"{L} {TH[i]:.0f}" for i, L in enumerate(BLOCK_LETTERS)))
P("   quote-only s36 vectors (publication-s36.txt section 3 + D3; prior")
P("   session's measurements, NEVER this window's):")
P("   X36:  " + " ".join(f"{v}" for v in REF_X_S36))
P("   Y36:  " + " ".join(f"{v}" for v in REF_Y_S36))
P("   HH36: " + " ".join(f"{v}" for v in REF_HI_HOST_S36))
P("   TH36: " + " ".join(f"{v}" for v in REF_TW_HOST_S36))
P("")

evaluable = (verify_mismatch_total == 0 and sample_counts_ok and knob_ok
             and failclosed_ok and cellmap_ok and c1_ok)

# ---- T1 THE ROW QUESTION: the three frozen couplings at this window ----
rhoA, pA, cntA, cmA = comove(X, HH)
rhoB, pB, cntB, cmB = comove(Y, TH)
rhoC, pC, cntC, cmC = comove(X, Y)
if not evaluable:
    letter = "(c) NAMED UNRESOLVED / NOT EVALUABLE"
elif not (cmA or cmB or cmC):
    letter = "(a) JOINT NO-COUPLE"
else:
    letter = "(b) ANY COUPLE"
P("4. T1 THE ROW QUESTION (frozen letters, protocol section 0): the joint")
P("   coupling pattern of (A) hi proxy, (B) tw proxy, (C) cross-arm at")
P("   THIS third window (block unit, n=12; Spearman rho +")
P("   two-sided permutation p, 100,000 trials, seed 20261028):")
P(f"   (A) hi proxy:  rho = {rhoA:.6f}, p = {pA:.6f} (count {cntA} / 100,001), "
  f"|rho| >= 0.60: {abs(rhoA) >= 0.60}, p <= 0.05: {pA <= 0.05}, CO-MOVE: {cmA}")
P(f"   (B) tw proxy:  rho = {rhoB:.6f}, p = {pB:.6f} (count {cntB} / 100,001), "
  f"|rho| >= 0.60: {abs(rhoB) >= 0.60}, p <= 0.05: {pB <= 0.05}, CO-MOVE: {cmB}")
P(f"   (C) cross-arm: rho = {rhoC:.6f}, p = {pC:.6f} (count {cntC} / 100,001), "
  f"|rho| >= 0.60: {abs(rhoC) >= 0.60}, p <= 0.05: {pC <= 0.05}, CO-MOVE: {cmC}")
P(f"   T1 = {letter}")
P("   NAMED, NOT HIDDEN: NEITHER letter resolves")
P("   threshold-artifact-vs-representation. THREE windows do not")
P("   make a settled pattern -- the letter is a third-window fact and")
P("   the cross-window scoreboard (D2) is descriptive only. (b) names")
P("   which coupling reads CO-MOVE at this window -- L2 OBSERVATIONAL")
P("   ONLY (NO causal mechanism; a shared driver could move both")
P("   members of a pair; direction UNMEASURED). ONE window, ONE day,")
P("   12 blocks: LOW POWER; the three sub-statistics share the same")
P("   12 blocks (L15 -- not independent tests); the block-pair")
P("   adjacency (~1s) is the resolution (L14); no rate/variance/")
P("   distribution claim.")
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
P("   D1 per-run-unit analogs (36 points per arm; 25 rounds/cell;")
P("      NAMED DIFFERENT UNIT L10 -- no letter):")
P(f"      (A1) hi per-run min vs per-run host_ns: rho = {rhoA1:.6f}, p = {pA1:.6f}")
P(f"      (B1) tw per-run min vs per-run host_ns: rho = {rhoB1:.6f}, p = {pB1:.6f}")
P(f"      per-run min ranges: hi {min(hi_pm):.0f}..{max(hi_pm):.0f}, tw {min(tw_pm):.0f}..{max(tw_pm):.0f}")
P("   D2 THE THREE-WINDOW LETTER SCOREBOARD (quote-only s35/s37 + this")
P("      session's letters; descriptive ONLY -- three windows are not")
P("      a rate, variance or distribution):")
P("      window s34 (session 35, A-axis only): NO-CO-MOVE (rho -0.038597 / p 0.907841)")
P("      window s36 (session 37, joint): ANY COUPLE -- (A) CO-MOVE (rho 0.774082 / p 0.004060), (B) NO-CO-MOVE, (C) NO-CO-MOVE")
P(f"      window s38 (this session, joint): {letter} -- (A) {'CO-MOVE' if cmA else 'NO-CO-MOVE'} (rho {rhoA:.6f} / p {pA:.6f}), "
      f"(B) {'CO-MOVE' if cmB else 'NO-CO-MOVE'} (rho {rhoB:.6f} / p {pB:.6f}), "
      f"(C) {'CO-MOVE' if cmC else 'NO-CO-MOVE'} (rho {rhoC:.6f} / p {pC:.6f})")

# ---- D3 the bar-candidate block (hi block A; L12) ----
hiA = BLOCKS["A"]
hiA_cell_vals = {k: pooled("hi", k, hiA, 2) for k in ok_cells}
hiA_median = pooled("hi", sum128, hiA, 2)
hiA_min = min(hiA_cell_vals.values())
hiA_class = "FLOOR" if all(v <= 100 for v in hiA_cell_vals.values()) else (
    "CAPTURED" if all(v >= 1000 for v in hiA_cell_vals.values()) else "INTERMEDIATE/MIXED")
hiA_lo = min(hiA_cell_vals.values())
hiA_hi = max(hiA_cell_vals.values())
inband = all(abs(hiA_median - ref) <= 0.05 * ref for ref in REF_BAR)
P(f"   D3 bar-candidate block (hi block A; frozen L12 -- the ONLY")
P(f"      candidate; day 2026-10-28's SIXTH anchor reading; the day")
P(f"      slot is session 31's, COUNTED 1/4; same-day descriptive):")
P(f"      class {hiA_class} at (sum,128,S=16) pooled median {hiA_median:.0f}, "
  f"18-cell {hiA_lo:.0f}..{hiA_hi:.0f}, block-min {hiA_min:.0f}")
P(f"      in-band vs frozen refs 1129/1132/1131 (within +/-5% of EACH): {inband}")
P("      same-day readings (quote-only): " + "; ".join(
    f"{s} {m} (min {mn})" for s, m, mn in SAMEDAY))

# ---- D4 host-side proxy (X1 content) ----
c2_host = pooled("c2", sum128, ARMR["c2"], 3)
c8_host = pooled("c8", sum128, ARMR["c8"], 3)
P("   D4 host_ns at (sum,128,S=16) (host-side proxy L3; the s31,")
P("      s34-window and s36 tw block-E excursions' causes stay")
P("      UNMEASURED):")
P(f"      c2 {c2_host:.0f}; c8 {c8_host:.0f}")
P(f"      hi per-block min..max {min(HH):.0f}..{max(HH):.0f}; tw per-block min..max {min(TH):.0f}..{max(TH):.0f}")
P("")

P("6. VERDICT SUMMARY:")
P(f"   T1 = {letter}")
P(f"   (A) rho {rhoA:.6f} / p {pA:.6f} CO-MOVE {cmA}; (B) rho {rhoB:.6f} / p {pB:.6f} "
  f"CO-MOVE {cmB}; (C) rho {rhoC:.6f} / p {pC:.6f} CO-MOVE {cmC}")
P(f"   evaluable inputs: VERIFY mismatch 0 ({verify_mismatch_total}), "
  f"samples ok ({sample_counts_ok}), knobs ok ({knob_ok}), S=8 fail-closed ({failclosed_ok}), "
  f"cell map ok ({cellmap_ok}), C1 ({c1_ok})")
P("   HARDWARE RAN (MEASURED): 78 fresh processes at the byte-identical")
P("   rebuilt pins (build-census-s38.txt), run window")
P("   2026-10-28T03:39:14Z..03:39:31Z.")
P("   The settling bar: the hi block A candidate line is same-day")
P("   descriptive content (bar-eval-s38.txt, the frozen evaluator; the")
P("   day's slot is session 31's). Rule 4 binds: nothing moves;")
P("   accelerator-targets defaults remain provisional (:measured?")
P("   false); NO vendor optimization exists for Intel.")

open(os.path.join(HERE, "publication-s38.txt"), "w").write("\n".join(out) + "\n")
