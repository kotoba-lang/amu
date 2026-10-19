#!/usr/bin/env python3
"""Parse the tick-1937 grid-F sweep logs (e24/e32/e33/e34 at lanes
2,297,856) and apply the chain's noise rule (IQR <= 0.05 and floor share
<= 1.2x the cell's IQR-clean minimum floor share). Writes the full
analysis to analyze-1937.txt next to itself; prints it too.
Line-oriented extraction (GAP/SPEEDUP/FLOORSHARE/SHAPE lines), no
assumption about the tab-separator spelling in the logs."""
import re, statistics, os

ev = os.path.dirname(os.path.abspath(__file__))
out_path = os.path.join(ev, "analyze-1937.txt")

CELLS = ["e24", "e32", "e33", "e34"]

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

cells = {}
for cyc in (1, 2, 3):
    for cell in CELLS:
        p = os.path.join(ev, f"run-{cyc}-{cell}.log")
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
        shape = line_of(txt, "SHAPE").split("SHAPE")[-1].strip()
        verdict = sp_line.split("vs-1.0=")[-1].strip()
        verified = "verified=true" in txt
        cells.setdefault(cell, []).append(
            dict(cyc=cyc, gap=gap, med=med, iqr=iqr, mn=mn, mx=mx, fs_b=fs_b,
                 fs_v=fs_v, load=load, verified=verified, shape=shape,
                 verdict=verdict))

lines = []
for cell in CELLS:
    runs = cells[cell]
    lines.append(f"== {cell}  {runs[0]['shape']}")
    for r in runs:
        lines.append(
            f"  run{r['cyc']}: gap(marginal)={r['gap']:.1f} ns/dispatch  paired_sign={'+' if r['med'] < 1 else '0' if r['med'] == 1 else '-'}  speedup "
            f"median={r['med']:.4f} iqr={r['iqr']:.4f} min={r['mn']:.4f} "
            f"max={r['mx']:.4f}  floor/baseline={r['fs_b']:.4f}  "
            f"floor/variant={r['fs_v']:.4f}  load1={r['load']}  "
            f"verified={r['verified']}  vs-1.0={r['verdict']}")
    iqr_clean = [r for r in runs if r['verified'] and r['iqr'] <= 0.05]
    clean_min = min((r['fs_b'] for r in iqr_clean), default=None)
    surv = [r for r in iqr_clean if clean_min is not None and r['fs_b'] <= 1.2 * clean_min]
    lines.append(f"  IQR-clean runs: {[r['cyc'] for r in iqr_clean]}  "
                 f"clean_min_floor/baseline={clean_min and round(clean_min, 4)}")
    lines.append(f"  surviving runs: {[r['cyc'] for r in surv]}")
    if surv:
        est = statistics.mean(r['gap'] for r in surv)
        lines.append(f"  clean-run est (mean of survivors): {est:.1f} ns/dispatch")
    gaps = [r['gap'] for r in runs]
    # Signs derive from the PAIRED per-round statistic (paired speedup
    # median: GAP>0 <=> baseline/variant < 1), not from the marginal gap
    # values, whose sign can contradict the paired rounds (review P1).
    paired_signs = '/'.join('+' if r['med'] < 1 else '0' if r['med'] == 1 else '-' for r in runs)
    lines.append(f"  mean(3, marginal)={statistics.mean(gaps):.1f}  "
                 f"all-signs(paired)={paired_signs}  "
                 f"all-signs(marginal, superseded)={'/'.join('+' if g > 0 else '0' if g == 0 else '-' for g in gaps)}  "
                 f"spread(marginal)={max(gaps) - min(gaps):.1f}")
    resolved = [r['cyc'] for r in runs if r['verdict'] != 'indistinguishable-at-this-noise']
    lines.append(f"  runs whose ratio stream does not straddle 1.0: {resolved}")

open(out_path, "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
print("WROTE", out_path)
