#!/usr/bin/env python3
"""Load-vs-noise attribution analysis over the amu-gpu chain's FULL run
corpus (JUN-58; the #1396 attribution question).

Question (one): does the host 1-minute load average at run start predict
the chain's IQR noise metric (the SPEEDUP iqr, chain-clean rule iqr<=0.05)
across every retained verified GPU-SGRE-CHUNK run in docs/evidence/gpu/?

Population, fixed before looking at the answer:
  - every *.log under docs/evidence/gpu/ (recursive) that carries
    (a) a `GPU-SGRE-CHUNK\tSPEEDUP` line (the sign-series probe family --
        GPU-SGRE-LOAD / GPU-SGRE-WSWEEP families are EXCLUDED: different
        probe/protocol, not pooled),
    (b) `RESULT verified=true` (retained runs only; failed/truncated
        attempt logs carry no SPEEDUP line and drop out automatically),
    (c) an `uptime` line with `load averages: <load1> ...`;
  - DE-DUPLICATED by whole-file sha256: several dirs hold byte-identical
    copies of earlier runs (chain carry convention). A physical run counts
    once; the copy count is reported.

Metrics:
  1. Spearman rank correlation load1 vs SPEEDUP-iqr (deterministic
     permutation p-value, seed 20261020, 20000 permutations).
  2. Clean rate (iqr<=0.05) and median iqr in fixed load bands
     load1<=8 / (8,16] / >16 (bands chosen before inspecting outcomes;
     tertiles printed as a robustness view).
  3. Two-sided Fisher exact, clean rate, band >16 vs band <=8.
  4. Secondary, sign series only (SHAPE W=64 chunks=31|32): gap sign vs
     load1 band.

Caveats printed in the output and the README: observational (load was
never manipulated; the load source is UNATTRIBUTED), same host / same
probe family, runs are not independent, correlation is not cause. This
analysis adjudicates whether load PREDICTS noise in the recorded corpus;
it does not identify the noise source.
"""
import os, re, hashlib, math, random, statistics, collections

EV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # docs/evidence/gpu
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analyze-load-noise.txt")

FAM = "GPU-SGRE-CHUNK"
CLEAN = 0.05
BANDS = [("load1<=8", lambda x: x <= 8),
         ("8<load1<=16", lambda x: 8 < x <= 16),
         ("load1>16", lambda x: x > 16)]
SEED, NPERM = 20261020, 20000


def parse_log(path):
    txt = open(path, "rb").read().decode("utf-8", "replace")
    if "\tSPEEDUP\t" not in txt or f"{FAM}\tSPEEDUP" not in txt:
        return None, "no-chunk-speedup"
    if "verified=true" not in txt:
        return None, "no-verified"
    m_load = re.search(r"load averages: ([\d.]+)", txt)
    if not m_load:
        return None, "no-load"
    sp = [ln for ln in txt.splitlines() if ln.startswith(FAM + "\tSPEEDUP")][0]
    m_iqr = re.search(r"iqr=([\d.]+)", sp)
    m_med = re.search(r"median=([\d.]+)", sp)
    if not (m_iqr and m_med):
        return None, "unparsable-speedup"
    shape = ""
    for ln in txt.splitlines():
        if ln.startswith(FAM + "\tSHAPE\t"):
            shape = ln.split("\tSHAPE\t")[1].strip()
    gap = None
    for ln in txt.splitlines():
        if ln.startswith(FAM + "\tGAP\t"):
            m_gap = re.search(r"ns/dispatch=(-?[\d.]+)", ln)
            if m_gap:
                gap = float(m_gap.group(1))
    when = ""
    for ln in txt.splitlines()[:3]:
        if "Oct" in ln:
            when = ln.strip()
    m_w = re.search(r"W=(\d+)", shape)
    m_c = re.search(r"chunks=(\d+)", shape)
    return dict(load=float(m_load.group(1)),
                iqr=float(re.search(r"iqr=([\d.]+)", sp).group(1)),
                med=float(re.search(r"median=([\d.]+)", sp).group(1)),
                gap=gap, when=when, shape=shape,
                w=int(m_w.group(1)) if m_w else None,
                chunks=int(m_c.group(1)) if m_c else None), None


def spearman(xs, ys):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else 0.0


def perm_p(xs, ys, nperm=NPERM, seed=SEED):
    rng = random.Random(seed)
    obs = spearman(xs, ys)
    ge = 0
    ys2 = list(ys)
    for _ in range(nperm):
        rng.shuffle(ys2)
        if abs(spearman(xs, ys2)) >= abs(obs):
            ge += 1
    return obs, (ge + 1) / (nperm + 1)


def fisher_two_sided(a, b, c, d):
    # table [[a,b],[c,d]]; two-sided by summing tables with prob <= observed
    n = a + b + c + d
    r1, c1 = a + b, a + c
    def lp(x):
        return (math.comb(r1, x) * math.comb(n - r1, c1 - x)) / math.comb(n, c1)
    obs = lp(a)
    lo, hi = max(0, c1 - (n - r1)), min(r1, c1)
    return sum(lp(x) for x in range(lo, hi + 1) if lp(x) <= obs + 1e-12)


lines = []
def emit(s=""):
    lines.append(s)
    print(s)

# ---- population ----
seen, runs, dup_copies, skips = {}, [], collections.Counter(), collections.Counter()
for dirpath, _, files in os.walk(EV):
    for fn in sorted(files):
        if not fn.endswith(".log"):
            continue
        p = os.path.join(dirpath, fn)
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        if h in seen:
            dup_copies[seen[h]] += 1
            continue
        rec, why = parse_log(p)
        if rec is None:
            skips[why] += 1
            continue
        seen[h] = os.path.relpath(p, EV)
        rec["rel"] = seen[h]
        rec["sha"] = h
        runs.append(rec)

emit("load-noise attribution (JUN-58 / #1396 question) -- corpus analysis")
emit("corpus root: docs/evidence/gpu/ (recursive), family GPU-SGRE-CHUNK only")
emit(f"population: {len(runs)} unique verified runs (whole-file sha256 de-duplicated)")
emit(f"log files scanned: {len(seen) + sum(dup_copies.values()) + sum(skips.values())}; "
     f"byte-identical duplicate copies skipped: {sum(dup_copies.values())}")
emit(f"skipped unique logs: {dict(skips)}")
emit()

loads = [r["load"] for r in runs]
iqrs = [r["iqr"] for r in runs]
emit(f"load1 at run start: min {min(loads):.2f} median {statistics.median(loads):.2f} max {max(loads):.2f}")
emit(f"SPEEDUP iqr:        min {min(iqrs):.4f} median {statistics.median(iqrs):.4f} max {max(iqrs):.4f}")
emit(f"chain-clean (iqr<={CLEAN}): {sum(1 for r in runs if r['iqr'] <= CLEAN)}/{len(runs)} runs")
emit()

# ---- 1. Spearman ----
rho, p = perm_p(loads, iqrs)
emit(f"1. Spearman rho(load1, SPEEDUP-iqr) = {rho:+.4f}, permutation p = {p:.4f} "
     f"(n={len(runs)}, {NPERM} permutations, seed {SEED})")
emit()

# ---- 2. bands ----
emit("2. fixed load bands (chosen before inspecting outcomes):")
rows = []
for name, pred in BANDS:
    sub = [r for r in runs if pred(r["load"])]
    if not sub:
        emit(f"   {name:14s} n=0")
        continue
    cl = sum(1 for r in sub if r["iqr"] <= CLEAN)
    rows.append((name, sub, cl))
    emit(f"   {name:14s} n={len(sub):3d}  clean={cl:3d} ({cl/len(sub):.2%})  "
         f"median iqr={statistics.median(r['iqr'] for r in sub):.4f}  "
         f"median load1={statistics.median(r['load'] for r in sub):.2f}")
qs = statistics.quantiles(loads, n=3) if len(loads) >= 3 else []
emit(f"   (load1 tertile cutpoints: {qs[0]:.2f} / {qs[1]:.2f})")
emit()

# ---- 3. Fisher ----
if len(rows) == 3 and rows[0][1] and rows[2][1]:
    lo_name, lo_sub, lo_cl = rows[0]
    hi_name, hi_sub, hi_cl = rows[2]
    a, b = hi_cl, len(hi_sub) - hi_cl
    c, d = lo_cl, len(lo_sub) - lo_cl
    fp = fisher_two_sided(a, b, c, d)
    emit(f"3. Fisher exact (clean rate, {hi_name} vs {lo_name}): "
         f"table [[clean {a}, dirty {b}], [clean {c}, dirty {d}]], two-sided p = {fp:.4f}")
else:
    emit("3. Fisher exact: not computable (empty band)")
emit()

# ---- 4. sign series secondary, PER CELL (the two cells have different
#        expected signs; pooling them would confound the question) ----
sig = [r for r in runs if r["w"] == 64 and r["chunks"] in (31, 32) and r["gap"] is not None]
emit(f"4. secondary -- sign-series cells, per cell (SHAPE W=64, n={len(sig)}):")
for cell in (31, 32):
    sub_cell = [r for r in sig if r["chunks"] == cell]
    emit(f"   chunks={cell} (n={len(sub_cell)}):")
    for name, pred in BANDS:
        sub = [r for r in sub_cell if pred(r["load"])]
        if not sub:
            emit(f"      {name:14s} n=0")
            continue
        pos = sum(1 for r in sub if r["gap"] > 0)
        emit(f"      {name:14s} n={len(sub):3d}  gap>0: {pos}/{len(sub)}  "
             f"gap median {statistics.median(r['gap'] for r in sub):+.1f} ns/dispatch")
emit()

# ---- 5. robustness ----
emit("5. robustness:")
sub30 = [r for r in runs if r["load"] <= 30]
rho30, p30 = perm_p([r["load"] for r in sub30], [r["iqr"] for r in sub30])
emit(f"   excluding load1>30 (n={len(sub30)}): rho = {rho30:+.4f}, p = {p30:.4f}")
strata = collections.defaultdict(list)
for r in runs:
    strata[(r["w"], r["chunks"])].append(r)
emit("   within-shape strata (n>=15) -- shape pooling confound check:")
for key in sorted(strata, key=lambda k: (-len(strata[k]), k)):
    sub = strata[key]
    if len(sub) < 15:
        continue
    rs, ps = perm_p([r["load"] for r in sub], [r["iqr"] for r in sub])
    cl = sum(1 for r in sub if r["iqr"] <= CLEAN)
    emit(f"      W={key[0]} chunks={key[1]}: n={len(sub):3d}  rho = {rs:+.4f} (p={ps:.4f})  "
         f"clean={cl}/{len(sub)}  load1 range {min(r['load'] for r in sub):.2f}-{max(r['load'] for r in sub):.2f}")
emit()

emit("Caveats: observational -- load was never manipulated and its source is")
emit("UNATTRIBUTED; one host (Apple M1 Max / MoltenVK), one probe family;")
emit("runs are not independent; correlation is not cause. This adjudicates")
emit("whether load PREDICTS the chain's IQR noise in the recorded corpus,")
emit("not where the noise comes from.")

open(OUT, "w").write("\n".join(lines) + "\n")
