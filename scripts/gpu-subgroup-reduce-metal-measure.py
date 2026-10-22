#!/usr/bin/env python3
"""JUN-58 hardware measurement driver: :baseline vs :subgroup-reduce MSL arms
on this host's Apple GPU, from the emitters' own bytes.

    python3 scripts/gpu-subgroup-reduce-metal-measure.py [--runs N]

Pipeline (every step's transcript lands in the evidence directory):

  1. emit   -- kbb scripts/gpu-subgroup-reduce-metal-measure.cljk writes the
               six emitted sources into docs/evidence/gpu-subgroup-reduce-
               m1max-20261023/shaders/ (both arms, three operators, W = 256).
  2. build  -- xcrun metal compiles each source to AIR and links one metallib
               per (arm, operator) (the emitted sources collide on their
               shared `combine` helper if linked together); xcrun clang builds
               the harness
               (scripts/gpu-subgroup-reduce-metal-measure.m) and the probe
               instrument (the [[threads_per_simdgroup]] reporter).
  3. run    -- the harness binary runs as FRESH PROCESSES (--runs, default 6),
               interleaved paired samples with alternating order per ADR-0358's
               protocol, verified read-back of the partials.
  4. record -- raw runs -> run-log.txt; transcripts -> compile-log.txt;
               statistics -> summary.md.

This measurement runs emitted code on the Apple GPU through the Metal API
directly -- NOT through wire 42, which has no route since the C loader
removal (ADR 0371). See summary.md for what that does and does not license.
"""

import argparse
import pathlib
import re
import shutil
import statistics
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
EVID = ROOT / "docs" / "evidence" / "gpu-subgroup-reduce-m1max-20261023"
PROBE = """\
#include <metal_stdlib>
using namespace metal;
// Instrument (measurement harness, not emitted code): report the SIMD-group
// width this device's compute dispatches actually use.
kernel void probe_sg(device uint* out [[buffer(0)]],
                     uint sgsize [[threads_per_simdgroup]],
                     uint i [[thread_position_in_grid]]) {
  if (i == 0u) { out[0] = sgsize; }
}
"""


def sh(cmd, log, cwd=ROOT):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    log.append("$ " + " ".join(str(c) for c in cmd))
    log.append(r.stdout)
    if r.stderr:
        log.append(r.stderr)
    if r.returncode != 0:
        sys.stderr.write("FATAL: " + " ".join(str(c) for c in cmd) + "\n")
        sys.stderr.write(r.stdout + r.stderr)
        sys.exit(2)
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=6)
    args = ap.parse_args()

    EVID.mkdir(parents=True, exist_ok=True)
    (EVID / "shaders").mkdir(exist_ok=True)
    build = pathlib.Path(tempfile.mkdtemp(prefix="sg-measure-"))
    log = []

    # 1. emit
    cp = sh(["kbb", "-Spath", "-M:test"], log).strip()
    sh(["kbb", "--backend", "sci", "--classpath", f"src:test:{cp}",
        "scripts/gpu-subgroup-reduce-metal-measure.cljk"], log)

    # 2. build
    arms = {}
    for arm in ("baseline", "subgroup"):
        for op in ("sum", "max", "min"):
            src = EVID / "shaders" / f"{arm}-reduce-{op}.emitted.metal"
            air = build / f"{arm}-reduce-{op}.air"
            sh(["xcrun", "-sdk", "macosx", "metal", "-c", str(src), "-o", str(air)], log)
            # one metallib per (arm, operator): the subgroup arm's sources all
            # define the same emitted `combine` helper, which collides at link
            # time -- the emitted bytes stay untouched, the libraries split.
            lib = build / f"{arm}-{op}.metallib"
            sh(["xcrun", "-sdk", "macosx", "metal", str(air), "-o", str(lib)], log)
            arms[(arm, op)] = lib
    (build / "probe.metal").write_text(PROBE)
    sh(["xcrun", "-sdk", "macosx", "metal", "-c", str(build / "probe.metal"),
        "-o", str(build / "probe.air")], log)
    sh(["xcrun", "-sdk", "macosx", "metal", str(build / "probe.air"),
        "-o", str(build / "probe.metallib")], log)
    exe = build / "measure"
    sh(["xcrun", "-sdk", "macosx", "clang", "-fobjc-arc", "-O2",
        str(SCRIPTS / "gpu-subgroup-reduce-metal-measure.m"), "-o", str(exe),
        "-framework", "Metal", "-framework", "Foundation",
        "-framework", "QuartzCore"], log)

    # 3. run: fresh processes
    runs = []
    for i in range(args.runs):
        out = sh([str(exe), str(build)], log)
        runs.append(out)

    (EVID / "compile-log.txt").write_text("\n".join(log) + "\n")
    (EVID / "run-log.txt").write_text(
        "".join(f"===== fresh-process run {i + 1} =====\n{o}"
                for i, o in enumerate(runs)))

    # 4. record
    samples = {}   # (op, arm) -> [gpu ns]
    per_run = {}   # (op, arm, run) -> [gpu ns]
    host = {}
    ver = []
    device = sg = n = wg = pairs = warmup = None
    for ri, out in enumerate(runs):
        for line in out.splitlines():
            m = re.match(r"sample op=(\w+) pair=(\d+) order=(\S) arm=(\w+) "
                         r"gpu_ns=([\d.]+) host_ns=([\d.]+)", line)
            if m:
                op, _p, _o, arm, gpu, hostns = m.groups()
                samples.setdefault((op, arm), []).append(float(gpu))
                per_run.setdefault((op, arm, ri), []).append(float(gpu))
                host.setdefault((op, arm), []).append(float(hostns))
                continue
            if line.startswith("verify "):
                ver.append((ri + 1, line))
                continue
            for key, pat in (("device", r"device=(.*)"),
                             ("simdgroup_size", r"simdgroup_size=(\d+)"),
                             ("n", r"n=(\d+)"),
                             ("workgroup", r"workgroup=(\d+)"),
                             ("pairs", r"pairs=(\d+)"),
                             ("warmup", r"warmup=(\d+)")):
                m = re.match(pat, line)
                if m:
                    if key == "device":
                        device = m.group(1)
                    else:
                        vals = {"simdgroup_size": sg, "n": n, "workgroup": wg,
                                "pairs": pairs, "warmup": warmup}
                        vals[key] = m.group(1)
                        sg, n, wg, pairs, warmup = (vals["simdgroup_size"], vals["n"],
                                                    vals["workgroup"], vals["pairs"],
                                                    vals["warmup"])

    lines = []
    lines.append("# JUN-58: :baseline vs :subgroup-reduce on Apple M1 Max -- "
                 "the first hardware comparison of the emitted arms\n")
    lines.append(f"- device: {device}")
    lines.append(f"- reported subgroup size ([[threads_per_simdgroup]]): {sg}")
    lines.append(f"- n = {n} elements, workgroup W = {wg} (the measured Apple "
                 f"row, ADR-0358), {args.runs} fresh-process runs")
    lines.append(f"- protocol: {pairs} interleaved pairs per operator per run, "
                 f"alternating AB/BA order, {warmup} warmup submits per arm "
                 "discarded (ADR-0358's sweep protocol)")
    lines.append("- timer: Metal GPU timestamps (command buffer "
                 "GPUStartTime->GPUEndTime) around one reduce dispatch; host "
                 "submit->completion ns recorded as secondary")
    lines.append("")
    lines.append("| operator | arm | samples | median gpu ns | per-run medians | "
                 "median host ns |")
    lines.append("|---|---|---|---|---|---|")
    summary_rows = {}
    for op in ("sum", "max", "min"):
        for arm in ("baseline", "variant"):
            key = (op, arm)
            vals = samples[key]
            med = statistics.median(vals)
            summary_rows[key] = med
            run_meds = [statistics.median(per_run[(op, arm, ri)])
                        for ri in range(args.runs)]
            lines.append(f"| {op} | {arm} | {len(vals)} | {med:.0f} | "
                         f"{', '.join(f'{m:.0f}' for m in run_meds)} | "
                         f"{statistics.median(host[key]):.0f} |")
    lines.append("")
    lines.append("Paired within-run comparison (the statistic of ADR-0358: "
                 "per fresh process, median over its pairs of "
                 "variant/baseline gpu-ns ratio, then the median of those):")
    lines.append("")
    lines.append("| operator | per-run ratios | median ratio |")
    lines.append("|---|---|---|")
    for op in ("sum", "max", "min"):
        ratios = []
        for ri in range(args.runs):
            b = per_run[(op, "baseline", ri)]
            v = per_run[(op, "variant", ri)]
            ratios.append(statistics.median(v) / statistics.median(b))
        lines.append(f"| {op} | {', '.join(f'{r:.3f}' for r in ratios)} | "
                     f"{statistics.median(ratios):.3f} |")
    lines.append("")
    lines.append("Verified read-back (every fresh process):")
    lines.append("")
    lines.append("```")
    for ri, line in ver:
        lines.append(f"run {ri}: {line}")
    lines.append("```")
    lines.append("")
    lines.append("## What this is, and what it is not\n")
    lines.append(
        "This is a REAL hardware measurement: the emitter's own bytes for the "
        "two arms ran on the Apple M1 Max GPU, interleaved, with verified "
        "read-back. It is NOT the measurement ADR-0360's contract names: that "
        "contract requires the wire-42 route, which does not exist since the "
        "C loader removal (ADR 0371 -- the provider is the replacement track "
        "and is not implemented). This run dispatches the MSL arms through the "
        "Metal API directly instead. No `:measured?` flag moves and no "
        "workgroup row is touched: the row's flip stays blocked on the "
        "contract's route clause (and on the per-tested-device scoping the "
        "flip would need). Whether a native Metal harness satisfies the "
        "measurement contract is a design decision, PROPOSED by this evidence "
        "and decided nowhere.")
    (EVID / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    shutil.rmtree(build, ignore_errors=True)


if __name__ == "__main__":
    main()
