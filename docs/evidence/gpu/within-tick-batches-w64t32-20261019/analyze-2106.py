#!/usr/bin/env python3
"""Parse the tick-2106 within-tick two-batch sign probe logs (w64t32 flip
cell + w64t31 anchor at lanes 2,095,104, one batch of 3 runs per cell per
batch, >=30 min idle gap inside ONE tick) and apply the chain's noise rule
(IQR <= 0.05 and floor share <= 1.2x the cell's IQR-clean minimum floor
share). Writes the full analysis to analyze-2106.txt next to itself; prints
it too. Line-oriented extraction (GAP/SPEEDUP/FLOORSHARE/SHAPE lines), no
assumption about the tab-separator spelling in the logs. Same rules as
analyze-2000.py / analyze-2030.py (PRs #1377 / #1378) so the batches are
directly comparable to the chain's sessions."""
import re, statistics, os

ev = os.path.dirname(os.path.abspath(__file__))
out_path = os.path.join(ev, "analyze-2106.txt")

BATCHES = ["A", "B"]
CELLS = ["w64t31", "w64t32"]

def line_of(txt, key):
    for ln in txt.splitlines():
        if key in ln:
            return ln
    raise SystemExit(f"missing line {key!r}")

def num(pat, ln):
    m = re.search(pat, ln)
    if not m:
        raise SystemExit(f"missing {pat!r} in {ln!r}")
    return float(m.group(1))

data = {}
for batch in BATCHES:
    for cell in CELLS:
        for pair in (1, 2, 3):
            p = os.path.join(ev, f"run-{batch}-{pair}-{cell}.log")
            txt = open(p).read()
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
            shape = line_of(txt, "SHAPE").split("SHAPE")[-1].strip()
            verdict = sp_line.split("vs-1.0=")[-1].strip()
            verified = "verified=true" in txt
            data.setdefault((batch, cell), []).append(
                dict(pair=pair, gap=gap, med=med, iqr=iqr, mn=mn, mx=mx,
                     fs_b=fs_b, fs_v=fs_v, load=load, verified=verified,
                     shape=shape, verdict=verdict, when=when))

lines = []
for batch in BATCHES:
    lines.append(f"===== batch {batch}")
    for cell in CELLS:
        runs = data[(batch, cell)]
        lines.append(f"== {cell}  {runs[0]['shape']}")
        for r in runs:
            lines.append(
                f"  run{r['pair']} [{r['when']}]: gap={r['gap']:.1f} ns/dispatch  "
                f"speedup median={r['med']:.4f} iqr={r['iqr']:.4f} "
                f"min={r['mn']:.4f} max={r['mx']:.4f}  "
                f"floor/baseline={r['fs_b']:.4f}  floor/variant={r['fs_v']:.4f}  "
                f"load1={r['load']}  verified={r['verified']}  vs-1.0={r['verdict']}")
        iqr_clean = [r for r in runs if r['iqr'] <= 0.05]
        clean_min = min((r['fs_b'] for r in iqr_clean), default=None)
        surv = [r for r in iqr_clean if clean_min is not None and r['fs_b'] <= 1.2 * clean_min]
        lines.append(f"  IQR-clean runs: {[r['pair'] for r in iqr_clean]}  "
                     f"clean_min_floor/baseline={clean_min and round(clean_min, 4)}")
        lines.append(f"  surviving runs: {[r['pair'] for r in surv]}")
        if surv:
            est = statistics.mean(r['gap'] for r in surv)
            lines.append(f"  clean-run est (mean of survivors): {est:.1f} ns/dispatch")
        gaps = [r['gap'] for r in runs]
        lines.append(f"  mean(3)={statistics.mean(gaps):.1f}  "
                     f"all-signs={'/'.join('+' if g > 0 else '-' for g in gaps)}  "
                     f"spread={max(gaps) - min(gaps):.1f}")
        resolved = [r['pair'] for r in runs if r['verdict'] != 'indistinguishable-at-this-noise']
        lines.append(f"  runs whose ratio stream does not straddle 1.0: {resolved}")

def estimate(runs, surv):
    """Mean gap over the SURVIVING runs only. When no run survives the
    noise filter there is NO estimate: falling back to the rejected runs
    (the old `surv or runs`) would publish exactly the conclusion the
    filter exists to suppress (review finding)."""
    return statistics.mean(r['gap'] for r in surv) if surv else None


def render_est(est):
    return "no estimate (no surviving run)" if est is None else f"{est:.1f}"


def render_sign(est):
    return "?" if est is None else ("+" if est > 0 else "-")


lines.append("")
lines.append("===== batch-vs-batch (two batches >= 30 min apart; per the run")
lines.append("timestamps and the README the batches fell in DIFFERENT cron")
lines.append("sessions -- session containment is the variable under test)")
for cell in CELLS:
    ests = {}
    for batch in BATCHES:
        runs = data[(batch, cell)]
        iqr_clean = [r for r in runs if r['iqr'] <= 0.05]
        clean_min = min((r['fs_b'] for r in iqr_clean), default=None)
        surv = [r for r in iqr_clean if clean_min is not None and r['fs_b'] <= 1.2 * clean_min]
        ests[batch] = estimate(runs, surv)
    if any(v is None for v in ests.values()):
        lines.append(f"  {cell}: no comparison -- batch A {render_est(ests['A'])}, batch B {render_est(ests['B'])}")
    else:
        same = (ests['A'] > 0) == (ests['B'] > 0)
        lines.append(f"  {cell}: batch A est={ests['A']:.1f}  batch B est={ests['B']:.1f}  "
                     f"same-sign={same}")

lines.append("")
lines.append("===== cross-session series (identical shape, ns/dispatch est, sign)")
lines.append("  w64t32 (wg=1023, lanes=2,095,104):")
lines.append("    #1369  +4,775.4 (mean 3)  +")
lines.append("    #1377  -7,546.9           -")
lines.append("    #1378  +5,425.5           +")
for batch in BATCHES:
    runs = data[(batch, 'w64t32')]
    iqr_clean = [r for r in runs if r['iqr'] <= 0.05]
    clean_min = min((r['fs_b'] for r in iqr_clean), default=None)
    surv = [r for r in iqr_clean if clean_min is not None and r['fs_b'] <= 1.2 * clean_min]
    est = estimate(runs, surv)
    lines.append(f"    tick-2106 batch {batch}  {render_est(est):>10}  {render_sign(est)}")
lines.append("  w64t31 anchor:")
lines.append("    #1369  -10,533.9  -")
lines.append("    #1377   -9,896.8  -")
lines.append("    #1378  -12,848.6  -")
for batch in BATCHES:
    runs = data[(batch, 'w64t31')]
    iqr_clean = [r for r in runs if r['iqr'] <= 0.05]
    clean_min = min((r['fs_b'] for r in iqr_clean), default=None)
    surv = [r for r in iqr_clean if clean_min is not None and r['fs_b'] <= 1.2 * clean_min]
    est = estimate(runs, surv)
    lines.append(f"    tick-2106 batch {batch}  {render_est(est):>10}  {render_sign(est)}")

open(out_path, "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
print("WROTE", out_path)
