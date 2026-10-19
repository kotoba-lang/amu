#!/usr/bin/env python3
"""Carried byte-identical from analyze-2254.py / analyze-2221.py (ticks
20261019-2254 / 20261019-2221) so the noise rule cannot drift; only the
output filename and this docstring differ. Parses this dir's in-session
two-batch sign probe logs (w64t32 flip cell + w64t31 anchor at lanes
2,095,104, one batch of 3 runs per cell per batch, probe-idle gap held
INSIDE ONE cron session) and apply the chain's noise rule (IQR <= 0.05 and
floor share <= 1.2x the cell's IQR-clean minimum floor share). Writes the
full analysis to analyze-2337.txt next to itself; prints it too.
Line-oriented extraction (GAP/SPEEDUP/FLOORSHARE/SHAPE lines). Same rules
as analyze-2000.py / analyze-2030.py / analyze-2106.py (PRs #1377 /
#1378 / #1380) so the batches are directly comparable to the chain's
sessions."""
import re, statistics, os

ev = os.path.dirname(os.path.abspath(__file__))
out_path = os.path.join(ev, "analyze-2337.txt")

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
                dict(pair=pair, gap=gap, med=med, iqr=iqr, mn=mn, mx=mx, txt=txt,
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
                     f"unanimous={len(set(g > 0 for g in gaps)) == 1}")
    lines.append("")

lines.append("===== cross-batch sign comparison")
for cell in CELLS:
    a = data[("A", cell)]
    b = data[("B", cell)]
    sa = set(r['gap'] > 0 for r in a)
    sb = set(r['gap'] > 0 for r in b)
    est_a = statistics.mean(r['gap'] for r in a)
    est_b = statistics.mean(r['gap'] for r in b)
    lines.append(f"{cell}: batchA mean(3)={est_a:.1f} signs={'/'.join('+' if r['gap'] > 0 else '-' for r in a)}"
                 f"  batchB mean(3)={est_b:.1f} signs={'/'.join('+' if r['gap'] > 0 else '-' for r in b)}"
                 f"  FLIP={'YES' if sa != sb else 'no'}")
# wall-clock gap between batches: last run of A -> first run of B
import datetime
def stamp(when):
    # FIX vs analyze-2221/2254.py (timestamp parse only; the noise rule is
    # untouched): the inherited stamp() expected "%b %d %H:%M:%S %Y" but the
    # `date` line is "Mon Oct 19 23:37:38 JST 2026"; it was latent in those
    # ticks because their batch B logs never existed for the script to reach
    # this line.
    m = re.match(r"\w+ (\w+ \d+ \d+:\d+:\d+) \w+ (\d{4})", when.strip())
    return datetime.datetime.strptime(f"{m.group(1)} {m.group(2)}", "%b %d %H:%M:%S %Y")
def dur(txt):
    m = re.search(r"real\s+(\d+)m([\d.]+)s", txt)
    return (int(m.group(1)) * 60 + float(m.group(2))) if m else 0.0
lastA = max(stamp(r['when']) + datetime.timedelta(seconds=dur(r['txt']))
            for cell in CELLS for r in data[("A", cell)])
firstB = min(stamp(r['when']) for cell in CELLS for r in data[("B", cell)])
delta = (firstB - lastA).total_seconds()
lines.append(f"probe-idle gap batchA-end -> batchB-start: {int(delta // 60)}m{int(delta % 60)}s")
lines.append(f"batchA window: {min(stamp(r['when']) for cell in CELLS for r in data[('A', cell)])} .. {lastA}")
lines.append(f"batchB window: {firstB} .. {max(stamp(r['when']) for cell in CELLS for r in data[('B', cell)])}")

text = "\n".join(lines) + "\n"
open(out_path, "w").write(text)
print(text)
