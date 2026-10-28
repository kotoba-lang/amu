#!/usr/bin/env python3
"""PRE-REGISTERED analyzer for the load-manipulation experiment (JUN-58,
tick 20261020-15xx, parent JUN-55). This file's rules were fixed BEFORE the
first dispatched run (its sha256 is recorded in the README next to the
dispatch timestamps); outcomes are read through it unchanged.

QUESTION. The corpus analysis (docs/evidence/gpu/load-noise-attribution-
20261020/) found load1 PREDICTS SPEEDUP-iqr (rho +0.27) and the flip cell's
sign stability is load-graded, but its causal direction is UNMEASURED --
"needs a manipulated or low-load-matched comparison". This experiment is
that manipulated comparison: same pinned probe, same cells, same fixture
bytes as every chain datum; the ONLY manipulated variable is host CPU load.

DESIGN (fixed here before dispatch).
- Arms: I = natural host load, no induced load; L = induced CPU load
  (12 CPU-burner processes started >=120 s before the first L run and
  killed after the last). Blocked order I then L: load1 is a 1-minute
  damped average, so a LOADED->IDLE interleaving leaves residual load1 in
  the I runs; fixed order instead confounds dose with time drift, which is
  recorded as a confound and is not claimed away.
- Runs: 2 run-pairs per arm (pairs 1-2 = I, 3-4 = L), each pair one run
  per cell w64t31 (anchor) / w64t32 (flip cell) at lanes 2,095,104, cell
  order rotated t31,t32 / t32,t31. n = 2 per cell per arm (pilot
  replication; each run's iqr is itself a within-run statistic over 32
  round-ratios, so the per-run iqr is the endpoint and runs are
  replication on top).
- Manipulation check (fixed threshold, from the corpus's pre-registered
  load bands): the contrast is DOSE-VALID only if every arm-I run records
  load1 <= 16 and every arm-L run records load1 > 16. If the check fails
  the result is INCONCLUSIVE-DOSE regardless of the outcome pattern.
- Retention: only runs with `RESULT verified=true` (machine-checked bit-
  exact verification inside the pinned probe) enter any count; failed or
  truncated attempts are preserved as attempt-*.log and counted as
  failures, never silently dropped.

ENDPOINTS (fixed here before dispatch).
- Primary: per-run SPEEDUP iqr per cell per arm; chain-clean = iqr <= 0.05
  (the chain's rule, carried unchanged). The claim under test: clean runs
  concentrate in arm I and IQR-dirty runs in arm L at w64t32 (the cell
  where the corpus's load-noise association lives).
- Pooled: exact two-sided Mann-Whitney U on SPEEDUP-iqr (I vs L), exact
  by exhaustive enumeration of label splits -- no seed, no approximation.
- Dose-response (descriptive): Spearman rho(load1, iqr) over all retained
  runs, exact two-sided permutation p by exhaustive permutation (n <= 8).
- Secondary (observational ONLY): sign of the gap (gap>0 count) per cell
  per arm. This experiment is NOT a cross-tick sign probe: it never
  adjudicates the transition series and the series count is untouched.

INTERPRETATION RULES (fixed here before dispatch).
- I-arm iqr < L-arm iqr at w64t32 with the clean contrast I-clean / L-
  dirty, and dose-valid: "manipulated CPU load degrades flip-cell
  precision -- supports (does not prove) the causal direction load->noise
  on the CPU-load axis". It still does not attribute the corpus's load
  SOURCE, and CPU load may only proxy whatever else the load tracks.
- No separation: "no effect detected at this dose and n"; the causal
  direction stays UNMEASURED. A null at n=2 per cell per arm bounds
  little and is reported as such.
- Everything else (dose-invalid, partial batch, failures): reported
  exactly as observed, labeled, adjudicated as nothing.
- This analyzer never touches kotoba.compiler.accelerator-targets and
  never flips :measured? on any row.
"""
import re, statistics, itertools, os

ev = os.path.dirname(os.path.abspath(__file__))
out_path = os.path.join(ev, "analyze-manip.txt")

PAIRS = [1, 2, 3, 4]
CELLS = ["w64t31", "w64t32"]
ARM = {1: "I", 2: "I", 3: "L", 4: "L"}
DOSE_THRESHOLD = 16.0  # corpus band boundary, pre-registered


def line_of(txt, key):
    for ln in txt.splitlines():
        if key in ln:
            return ln
    return None


def num(pat, ln):
    m = re.search(pat, ln)
    if not m:
        raise SystemExit(f"missing {pat!r} in {ln!r}")
    return float(m.group(1))


data = {}
missing = []
for pair in PAIRS:
    for cell in CELLS:
        p = os.path.join(ev, f"run-{pair}-{cell}.log")
        if not os.path.exists(p):
            missing.append(f"run-{pair}-{cell}.log")
            continue
        txt = open(p).read()
        if "RESULT\tverified=true" not in txt:
            missing.append(f"run-{pair}-{cell}.log (NOT verified)")
            continue
        gap = num(r"ns/dispatch=(-?[\d.]+)", line_of(txt, "GAP"))
        sp_line = line_of(txt, "SPEEDUP")
        med = num(r"median=([\d.]+)", sp_line)
        iqr = num(r"iqr=([\d.]+)", sp_line)
        mn = num(r"min=([\d.]+)", sp_line)
        mx = num(r"max=([\d.]+)", sp_line)
        fs_line = line_of(txt, "FLOORSHARE")
        fs_b = num(r"floor/baseline=([\d.]+)", fs_line)
        fs_v = num(r"floor/variant=([\d.]+)", fs_line)
        load = num(r"load averages: ([\d.]+)", line_of(txt, "load averages"))
        when = line_of(txt, "Oct").strip()
        data[(pair, cell)] = dict(
            arm=ARM[pair], gap=gap, med=med, iqr=iqr, mn=mn, mx=mx,
            fs_b=fs_b, fs_v=fs_v, load=load, when=when,
            verdict=sp_line.split("vs-1.0=")[-1].strip())

lines = []
lines.append("===== load-manipulation experiment (JUN-58): manipulated CPU load vs SPEEDUP-iqr")
lines.append(f"retained runs: {len(data)} of {len(PAIRS) * len(CELLS)};  missing/unverified: {missing if missing else 'none'}")
lines.append("arms: I = natural load (pairs 1-2), L = 12 CPU burners (pairs 3-4); per-run iqr is within-run over 32 round-ratios")

for pair in PAIRS:
    for cell in CELLS:
        r = data.get((pair, cell))
        if r is None:
            lines.append(f"pair{pair} {cell} [{ARM[pair]}]: MISSING")
            continue
        lines.append(
            f"pair{pair} {cell} [{r['arm']}] [{r['when']}]: gap={r['gap']:.1f} ns/dispatch  "
            f"speedup median={r['med']:.4f} iqr={r['iqr']:.4f} min={r['mn']:.4f} max={r['mx']:.4f}  "
            f"floor/baseline={r['fs_b']:.4f}  floor/variant={r['fs_v']:.4f}  "
            f"load1={r['load']}  vs-1.0={r['verdict']}")

# per-cell per-arm summaries
lines.append("")
lines.append("===== per-cell per-arm (primary endpoint)")
for cell in CELLS:
    for arm in ("I", "L"):
        runs = [data[(p, cell)] for p in PAIRS if ARM[p] == arm and (p, cell) in data]
        if not runs:
            lines.append(f"{cell} arm{arm}: no retained runs")
            continue
        iqrs = [r["iqr"] for r in runs]
        clean = sum(1 for i in iqrs if i <= 0.05)
        gaps = [r["gap"] for r in runs]
        lines.append(
            f"{cell} arm{arm}: n={len(runs)}  iqr={[round(i, 4) for i in iqrs]}  "
            f"median_iqr={statistics.median(iqrs):.4f}  clean(iqr<=0.05)={clean}/{len(runs)}  "
            f"signs={'/'.join('+' if g > 0 else '-' for g in gaps)}  "
            f"load1={[r['load'] for r in runs]}")

# manipulation check (dose validity)
lines.append("")
lines.append("===== manipulation check (pre-registered: I runs load1<=16, L runs load1>16)")
allr = [data[k] for k in data]
il = [r["load"] for r in allr if r["arm"] == "I"]
ll = [r["load"] for r in allr if r["arm"] == "L"]
dose_valid = bool(il and ll and max(il) <= DOSE_THRESHOLD and min(ll) > DOSE_THRESHOLD)
lines.append(f"arm I load1: {il}  arm L load1: {ll}")
lines.append(f"DOSE-VALID={dose_valid}")

# exact Mann-Whitney U on pooled iqr (I vs L); iqr is sign-independent so
# pooling the two cells is pre-registered as admissible
lines.append("")
lines.append("===== pooled iqr contrast (exact two-sided Mann-Whitney U, exhaustive)")
xi = [data[k]["iqr"] for k in data if data[k]["arm"] == "I"]
xl = [data[k]["iqr"] for k in data if data[k]["arm"] == "L"]
if xi and xl:
    allv = xi + xl
    n1, n2 = len(xi), len(xl)
    u_obs = sum(1 for a in xi for b in xl if a < b) + 0.5 * sum(1 for a in xi for b in xl if a == b)
    u_c = n1 * n2 / 2.0
    dev_obs = abs(u_obs - u_c)
    ge = 0
    total = 0
    for idx in itertools.combinations(range(n1 + n2), n1):
        s1 = [allv[i] for i in idx]
        s2 = [allv[i] for i in range(n1 + n2) if i not in idx]
        u = sum(1 for a in s1 for b in s2 if a < b) + 0.5 * sum(1 for a in s1 for b in s2 if a == b)
        total += 1
        if abs(u - u_c) >= dev_obs - 1e-12:
            ge += 1
    lines.append(f"arm I iqr: {[round(i, 4) for i in xi]} (median {statistics.median(xi):.4f})")
    lines.append(f"arm L iqr: {[round(i, 4) for i in xl]} (median {statistics.median(xl):.4f})")
    lines.append(f"U={u_obs} (chance {u_c})  exact two-sided p={ge}/{total} = {ge / total:.4f}")

# dose-response, descriptive, exact permutation p (exhaustive)
lines.append("")
lines.append("===== dose-response (descriptive): Spearman rho(load1, iqr), exact permutation p")
if len(allr) >= 3:
    loads = [r["load"] for r in allr]
    iqrs = [r["iqr"] for r in allr]

    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        rk = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                rk[order[k]] = avg
            i = j + 1
        return rk

    def pearson(a, b):
        ma, mb = statistics.mean(a), statistics.mean(b)
        num_ = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
        return num_ / den if den else 0.0

    rl, ri = ranks(loads), ranks(iqrs)
    rho = pearson(rl, ri)
    ge = 0
    total = 0
    for perm in itertools.permutations(ri):
        total += 1
        if abs(pearson(rl, list(perm))) >= abs(rho) - 1e-12:
            ge += 1
    lines.append(f"n={len(allr)}  rho={rho:.4f}  exact two-sided p={ge}/{total} = {ge / total:.4f}")

lines.append("")
lines.append("===== what this bounds, honestly (pre-registered)")
if not allr:
    lines.append("no retained runs -- nothing measured")
elif not dose_valid:
    lines.append("INCONCLUSIVE-DOSE: the manipulation check failed; no outcome pattern is read as evidence")
else:
    ci = [data[(p, "w64t32")]["iqr"] for p in PAIRS if ARM[p] == "I" and (p, "w64t32") in data]
    cl = [data[(p, "w64t32")]["iqr"] for p in PAIRS if ARM[p] == "L" and (p, "w64t32") in data]
    if ci and cl and max(ci) <= 0.05 and min(cl) > 0.05:
        lines.append("flip cell w64t32: arm I all clean, arm L all dirty -> manipulated CPU load degrades flip-cell precision; supports (does not prove) load->noise causality on the CPU-load axis; load SOURCE stays UNATTRIBUTED; n=2 per cell per arm is pilot replication")
    else:
        lines.append("no clean/dirty separation at w64t32 at this dose and n -> no effect detected; causal direction stays UNMEASURED (a null at n=2 per cell per arm bounds little)")
lines.append("the transition series is untouched (this is not a cross-tick sign probe); :measured? rows untouched; sign counts above are observational only")

text = "\n".join(lines) + "\n"
open(out_path, "w").write(text)
print(text)
