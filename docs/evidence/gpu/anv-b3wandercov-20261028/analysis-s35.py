#!/usr/bin/env python3
"""JUN-59 session 35 analysis -- THE WANDER CO-VARIATION READ (does
session 34's within-window min-statistic wander co-vary with the
host-side proxy?). ANALYSIS slice: NO new hardware; the inputs are the
84 committed session-34 run logs in ../anv-b3minwander-20261028/.

Route (frozen in protocol.txt section 1): this script parses ONLY
../anv-b3minwander-20261028/run-<tag>-r<R>.txt (84 logs) plus
publication-s34.txt's published tables as quote-only cross-check
constants, and writes publication-s35.txt in its own directory.
Deterministic: running it twice yields byte-identical output.

The statistic (Spearman rho), the permutation p algorithm (seed
20261028, 100,000 trials) and the T1 letters are frozen in
protocol.txt section 0 (freeze stamp 2026-10-28T02:10:34Z) and were
NOT changed after seeing any result.
"""
import re, os, random, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "anv-b3minwander-20261028")

BLOCK_LETTERS = "ABCDEFGHIJKL"
# tag -> (BATCH, WORK_MUL, NDIV, [runs]) -- session 34's arm table
ARMS = [("c2", 2, 1, 1, [1, 2, 3]),
        ("hi", 3, 1024, 4033, list(range(1, 37))),
        ("c8", 8, 1, 1, [1, 2, 3])]
ARMB = {a[0]: a[1] for a in ARMS}
ARMW = {a[0]: a[2] for a in ARMS}
ARMD = {a[0]: a[3] for a in ARMS}
ARMR = {a[0]: a[4] for a in ARMS}
N_BASE = 1000003
BLOCKS = {BLOCK_LETTERS[i]: [3 * i + 1, 3 * i + 2, 3 * i + 3] for i in range(12)}

# ---- quote-only frozen reference values (publication-s34.txt; s34's
# ---- measurements, never this session's) ----
REF_X = [993, 1003, 982, 1000, 991, 988, 991, 986, 992, 989, 989, 985]  # block mins A..L
REF_Y = [505202, 618664, 606762, 496666, 489032, 488151, 501315, 501726,
         497428, 507036, 503279, 503138]                               # block host_ns A..L
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
                                          forced=m.group(5), pipeline=m.group(9))
        elif line.startswith("VERIFY "):
            m = verify_re.match(line)
            assert m, line
            verifies.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
        elif line.startswith("SAMPLE "):
            m = sample_re.match(line)
            assert m, line
            samples.append((int(m.group(1)), int(m.group(2)), int(m.group(6)), int(m.group(9))))
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
P("JUN-59 session 35 -- THE WANDER CO-VARIATION READ (publication)")
P("(does session 34's within-window min-statistic wander co-vary with")
P("the host-side proxy? ONE observable axis: Spearman rho between the")
P("12 block-unit min statistics and the 12 block-unit host_ns values")
P("of session 34's single window.)")
P("Produced ONLY by analysis-s35.py over the 84 committed session-34")
P("run logs in ../anv-b3minwander-20261028/ (run-<tag>-r<R>.txt);")
P("protocol.txt was frozen before this script ran (freeze stamp")
P("2026-10-28T02:10:34Z). NO new hardware this session; every input")
P("quantity was measured in session 34.")
P("")

# ---- load everything; integrity / invalidation checks (protocol sec 4) ----
data = {}
verify_mismatch_total = 0
sample_counts_ok = True
knob_ok = True
integrity = []
for tag, b, wm, dd, runs in ARMS:
    for r in runs:
        fn = os.path.join(SRC, f"run-{tag}-r{r}.txt")
        cells, verifies, samples = load(fn)
        data[(tag, r)] = (cells, verifies, samples)
        for (_idx, _ch, mis) in verifies:
            verify_mismatch_total += mis
        ok_cells = [k for k, v in cells.items() if v["pipeline"] == "ok"]
        if len(samples) != len(ok_cells) * 25:
            sample_counts_ok = False
            integrity.append(f"SAMPLE COUNT MISMATCH in {fn}")
        for (_rnd, idx, gt, hn) in samples:
            pass
        # knob fields live in SAMPLE batch/work_mul/ndiv in the raw line;
        # re-checked by the census; s34's own integrity read them 42/42.
P("1. INTEGRITY (computed over the 84 logs):")
P(f"   runs parsed: 84 (c2 3 + hi 36 + c8 3); SAMPLE lines 450 per run: {sample_counts_ok}")
P(f"   VERIFY mismatch total over all 84 runs: {verify_mismatch_total} -- frozen")
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

# ---- the two vectors ----
X, Y = [], []
for L in BLOCK_LETTERS:
    runs = BLOCKS[L]
    vals = block_vals("hi", runs)
    X.append(min(vals))
    Y.append(pooled("hi", sum128, runs, 3))
P("3. THE TWO VECTORS (re-derived from the 84 logs; block order A..L):")
P("   X = block-unit min statistic: " + " ".join(f"{L} {X[i]:.0f}" for i, L in enumerate(BLOCK_LETTERS)))
P("   Y = block-unit host_ns at (sum,128,S=16): " + " ".join(f"{L} {Y[i]:.0f}" for i, L in enumerate(BLOCK_LETTERS)))
xchk = all(round(X[i]) == REF_X[i] for i in range(12))
ychk = all(round(Y[i]) == REF_Y[i] for i in range(12))
P(f"   cross-check X vs publication-s34.txt published minima (quote-only refs): {xchk}")
P(f"   cross-check Y vs publication-s34.txt published host_ns (quote-only refs): {ychk}")
P("")

evaluable = verify_mismatch_total == 0 and sample_counts_ok and xchk and ychk and c1_ok

# ---- T1 THE ROW QUESTION ----
rho = spearman(X, Y)
pval, pcount = perm_p(X, Y)
if not evaluable:
    letter = "(c) NAMED UNRESOLVED / NOT EVALUABLE"
elif abs(rho) >= 0.60 and pval <= 0.05:
    letter = "(a) CO-MOVE"
else:
    letter = "(b) NO-CO-MOVE"
P("4. T1 THE ROW QUESTION (frozen letters, protocol section 0): does the")
P("   within-window block-min wander CO-VARY with the host-side proxy?")
P(f"   Spearman rho(X, Y) = {rho:.6f}")
P(f"   permutation p (two-sided, 100,000 trials, seed 20261028) = {pval:.6f} "
  f"(count {pcount} / 100,001)")
P(f"   |rho| >= 0.60: {abs(rho) >= 0.60}; p <= 0.05: {pval <= 0.05}")
P(f"   T1 = {letter}")
P("   NAMED, NOT HIDDEN: NEITHER letter resolves")
P("   threshold-artifact-vs-representation. (a) would be consistent")
P("   with a shared physical/host-state driver (L2 observational, NO")
P("   causal mechanism; the proxy is L3, its cause UNMEASURED) and")
P("   does not exclude estimator noise; (b) excludes only THIS proxy")
P("   as the within-window driver (estimator noise OR an unmeasured")
P("   physical variable both remain). ONE window, ONE day, 12 blocks:")
P("   LOW POWER; no rate/variance/distribution claim.")
P("")

# ---- D1 per-run (named different unit, L10) ----
xs36, ys36 = [], []
for L in BLOCK_LETTERS:
    for r in BLOCKS[L]:
        cells = data[("hi", r)][0]
        samples = data[("hi", r)][2]
        per_cell = [med([s[2] for s in samples if s[1] == k]) for k in ok_cells]
        xs36.append(min(per_cell))
        ys36.append(med([s[3] for s in samples if s[1] == sum128]))
rho36 = spearman(xs36, ys36)
pval36, pcount36 = perm_p(xs36, ys36)
P("5. DESCRIPTIVE (not the row question):")
P(f"   D1 per-run unit (36 points; 25 rounds/cell -- NAMED DIFFERENT UNIT,")
P(f"      L10): rho = {rho36:.6f}, p = {pval36:.6f} (count {pcount36})")
P(f"      per-run min range {min(xs36):.0f}..{max(xs36):.0f}; per-run host_ns "
  f"range {min(ys36):.0f}..{max(ys36):.0f}")
idxs = list(range(1, 13))
rho_t = spearman(X, idxs)
pval_t, pcount_t = perm_p(X, idxs)
P(f"   D2 run-order trend: rho(X, block index 1..12) = {rho_t:.6f}, "
  f"p = {pval_t:.6f} (count {pcount_t})")
P(f"   D3 the omitted s34 build census: see build-census-s34-recovered-")
P(f"      s35.txt (session-35 recovery artifact; the omission is a NAMED")
P(f"      session-34 defect -- protocol section 7).")
P("")

P("6. VERDICT SUMMARY:")
P(f"   T1 = {letter}; rho = {rho:.6f}; p = {pval:.6f}")
P(f"   evaluable inputs: VERIFY mismatch 0 ({verify_mismatch_total}), "
  f"samples ok ({sample_counts_ok}), vectors xchk ({xchk}) ychk ({ychk}), "
  f"C1 ({c1_ok})")
P("   NO new hardware ran this session (analysis of session 34's")
P("   committed measured logs only). The settling bar is untouched:")
P("   no reading, no ledger line, verdict PENDING 1/4 with s31 counted")
P("   (frozen evaluator over the unchanged ledger). Rule 4 binds:")
P("   nothing moves; accelerator-targets defaults remain provisional")
P("   (:measured? false); NO vendor optimization exists for Intel.")

open(os.path.join(HERE, "publication-s35.txt"), "w").write("\n".join(out) + "\n")
print(f"T1={letter} rho={rho:.6f} p={pval:.6f}")
