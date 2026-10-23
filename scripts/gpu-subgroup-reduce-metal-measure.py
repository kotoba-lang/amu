#!/usr/bin/env python3
"""JUN-58 hardware measurement driver: :baseline vs :subgroup-reduce MSL arms
on this host's Apple GPU, from the emitters' own bytes.

    python3 scripts/gpu-subgroup-reduce-metal-measure.py [--runs N] [--workgroup W] [--elements N] [--out DIR] [--compare-historical HIST.md]

Pipeline (every step's transcript lands in the evidence directory):

  1. emit   -- kbb scripts/gpu-subgroup-reduce-metal-measure.cljk writes the
               six emitted sources into <out>/shaders/ (both arms, three
               operators, at W = --workgroup; default 256, the measured
               Apple workgroup row of ADR-0358).
  2. build  -- xcrun metal compiles each source to AIR and links one metallib
               per (arm, operator) (the emitted sources collide on their
               shared `combine` helper if linked together); xcrun clang builds
               the harness
               (scripts/gpu-subgroup-reduce-metal-measure.m) and the probe
               instrument (the [[threads_per_simdgroup]] reporter).
  3. run    -- the harness binary runs as FRESH PROCESSES (--runs, default 6),
               interleaved paired samples with alternating order per ADR-0358's
               protocol, verified read-back of the partials.

The reduction shape n is a measurement variable (--elements, default 1000003
-- the shape every cell before the shape-2 run used, a padded non-multiple
of W). The shape-2 cells pass 1048576 = 2^20 (a clean multiple of every W
in [32, 1024]: no padded-lane tail). The emitted kernels read n at runtime
(buffer 2), so the same emitted bytes serve every shape -- the arms stay
byte-identical and only the shape changes.
  4. record -- raw runs -> <out>/run-log.txt; transcripts ->
               <out>/compile-log.txt; statistics -> <out>/summary.md.
               With --compare-historical HIST.md (a prior record's
               summary.md, read once and never modified) the summary
               additionally carries the claim-protocol rule-3
               regime-matched comparison section against that record,
               auto-wired through
               gpu_regime_classify.append_comparison_section -- the
               section is drawn from the exact text being published and
               names this driver as its publication path (no manual
               --compare consumption step).

<out> defaults to docs/evidence/gpu-subgroup-reduce-m1max-20261023 (the
historical W = 256 cell). A W-sweep cell passes its own --out (e.g.
docs/evidence/gpu-subgroup-reduce-m1max-wsweep-20261023/w512) so the
historical cell's record is never rewritten by a sweep run. FOOTGUN, named:
a default run rewrites the historical run-log/compile-log/summary in place
(the emitted shaders under shaders/ are deterministic by design and may be
rewritten to check the emitters; the run logs are not).

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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gpu_regime_classify

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


VIA_AUTO_WIRE = ("the measurement driver's --compare-historical auto-wiring "
                 "(scripts/gpu-subgroup-reduce-metal-measure.py; rule-3 "
                 "machinery: scripts/gpu_regime_classify.py)")


def finalize_summary(summary_text, compare_historical, new_label):
    """Rule-3 auto-wiring: with --compare-historical, append the
    regime-matched comparison section against that record to the summary
    text about to be published. Without it the text passes through
    unchanged. The historical file is READ ONLY here and never modified.
    """
    if not compare_historical:
        return summary_text
    hist_path = pathlib.Path(compare_historical)
    return gpu_regime_classify.append_comparison_section(
        hist_path.read_text(), str(hist_path), summary_text, new_label,
        via=VIA_AUTO_WIRE)


def self_test():
    """Hardware-free check of the --compare-historical auto-wiring path
    (the exact function main() calls), over two committed corpus records.
    No GPU, no Metal, no measurement: every input is a committed
    summary.md.
    """
    evid = ROOT / "docs" / "evidence"
    hist_rel = "gpu-subgroup-reduce-m1max-shape2-band-20261023/w512/summary.md"
    new_rel = "gpu-subgroup-reduce-m1max-shape2-resweep-20261023/w512/summary.md"
    hist_text = (evid / hist_rel).read_text()
    new_text = (evid / new_rel).read_text()
    n = 0

    def _expect(cond, msg):
        nonlocal n
        assert cond, msg
        n += 1

    _expect(finalize_summary(new_text, None, new_rel) == new_text,
            "no --compare-historical leaves the summary untouched")
    out = finalize_summary(new_text, str(evid / hist_rel), new_rel)
    _expect(out.startswith(new_text.rstrip("\n") + "\n\n"),
            "the single-record sections stand byte-identical as prefix")
    section = gpu_regime_classify.render_rule3_section(
        gpu_regime_classify.load_comparison_cell(hist_text, str(evid / hist_rel)),
        gpu_regime_classify.load_comparison_cell(new_text, new_rel),
        via=VIA_AUTO_WIRE)
    _expect(out.endswith(section + "\n"),
            "the appended section is the --compare machinery's own output, "
            "under this driver's via name")
    _expect("Published by " + VIA_AUTO_WIRE + ": " in out,
            "the section names this driver as its publication path")
    for fn in (gpu_regime_classify.parse_summary_per_run_baseline,
               gpu_regime_classify.parse_summary_per_run_ratios,
               gpu_regime_classify.parse_summary_published_medians):
        _expect(fn(out) == fn(new_text),
                f"{fn.__name__} round-trips through the appended summary")
    print(f"driver auto-wiring self-test: {n} assertions passed, 0 failed")


def main():
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=6)
    ap.add_argument("--workgroup", type=int, default=256)
    ap.add_argument("--elements", type=int, default=1000003)
    ap.add_argument("--op-order", type=str, default="sum,max,min")
    ap.add_argument("--out", type=str, default=None)
    ap.add_argument("--compare-historical", type=str, default=None,
                    help="a prior record's summary.md; the published summary "
                         "then carries the claim-protocol rule-3 "
                         "regime-matched comparison against it (the file is "
                         "read once, never modified)")
    args = ap.parse_args()
    order_names = [t.strip() for t in args.op_order.split(",")]
    if sorted(order_names) != ["max", "min", "sum"]:
        sys.stderr.write(f"REFUSED --op-order {args.op_order}: need a "
                         "comma-separated permutation of sum,max,min\n")
        sys.exit(2)
    wg_want = args.workgroup
    if wg_want < 32 or wg_want > 1024 or (wg_want & (wg_want - 1)) != 0:
        sys.stderr.write(f"REFUSED --workgroup {wg_want}: "
                         "need a power of two in [32, 1024]\n")
        sys.exit(2)
    n_want = args.elements
    if n_want < 1 or n_want > 16777216:
        sys.stderr.write(f"REFUSED --elements {n_want}: "
                         "need an integer in [1, 16777216]\n")
        sys.exit(2)
    out = pathlib.Path(args.out) if args.out else EVID

    out.mkdir(parents=True, exist_ok=True)
    (out / "shaders").mkdir(exist_ok=True)
    build = pathlib.Path(tempfile.mkdtemp(prefix="sg-measure-"))
    log = []

    # 1. emit (at the cell's width -- the subgroup arm's threadgroup partials
    #    array is sized from the emitted W, so the sources are W-specific)
    cp = sh(["kbb", "-Spath", "-M:test"], log).strip()
    sh(["kbb", "--backend", "sci", "--classpath", f"src:test:{cp}",
        "scripts/gpu-subgroup-reduce-metal-measure.cljk",
        "--width", str(wg_want), "--out", str(out / "shaders")], log)

    # 2. build
    arms = {}
    for arm in ("baseline", "subgroup"):
        for op in ("sum", "max", "min"):
            src = out / "shaders" / f"{arm}-reduce-{op}.emitted.metal"
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
        proc_out = sh([str(exe), str(build), str(wg_want), str(n_want),
                       args.op_order], log)
        runs.append(proc_out)

    (out / "compile-log.txt").write_text("\n".join(log) + "\n")
    (out / "run-log.txt").write_text(
        "".join(f"===== fresh-process run {i + 1} =====\n{o}"
                for i, o in enumerate(runs)))

    # 4. record
    samples = {}   # (op, arm) -> [gpu ns]
    per_run = {}   # (op, arm, run) -> [gpu ns]
    host = {}
    ver = []
    device = sg = n = wg = pairs = warmup = None
    op_order_seen = None
    for ri, run_out in enumerate(runs):
        for line in run_out.splitlines():
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
            if line.startswith("op_order="):
                op_order_seen = line.split("=", 1)[1]
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

    if wg is None or sg is None:
        sys.stderr.write("FATAL: no workgroup=/simdgroup_size= line in any run "
                         "output -- nothing was measured\n")
        sys.exit(2)

    lines = []
    lines.append(f"# JUN-58: :baseline vs :subgroup-reduce on Apple M1 Max at "
                 f"W = {wg} -- the MSL arms on the native Metal route\n")
    lines.append(f"- device: {device}")
    lines.append(f"- reported subgroup size ([[threads_per_simdgroup]]): {sg}")
    lines.append(f"- n = {n} elements, workgroup W = {wg}"
                 + (" (the measured Apple row, ADR-0358)" if int(wg) == 256
                    else " (a W-sweep cell, NOT the ADR-0358 row)")
                 + f", {args.runs} fresh-process runs")
    if int(n) == 1000003:
        shape_note = ("the historical shape (not a multiple of W: the "
                      "padded-lane tail is exercised)")
    elif int(n) == 1048576:
        shape_note = ("SHAPE 2: n = 2^20, a clean multiple of every W in "
                      "[32, 1024] -- no padded-lane tail; the only variable "
                      "changed from the historical cells (same LCG input "
                      "prefix, byte-identical emitted arms)")
    else:
        shape_note = ("a NON-HISTORICAL shape (the historical shape is "
                      "n = 1000003); read as measured data, not as an anchor")
    lines.append(f"- shape: {shape_note}")
    lines.append(f"- emitted at W = {wg_want} by the emitters' own bytes "
                 f"(shaders/; the subgroup arm's threadgroup partials array "
                 f"is sized from this W)"
                 + ("" if int(wg) == wg_want
                    else f" -- MISMATCH: the harness dispatched W = {wg}"))
    lines.append(f"- protocol: {pairs} interleaved pairs per operator per run, "
                 f"alternating AB/BA order, {warmup} warmup submits per arm "
                 "discarded (ADR-0358's sweep protocol)")
    lines.append(f"- operator dispatch order: "
                 f"{op_order_seen or args.op_order}"
                 + (" (the default fixed order every earlier cell used)"
                    if (op_order_seen or args.op_order) == "sum,max,min"
                    else " (OP-ORDER VARIANT, named: under the fixed "
                         "sum,max,min order the fresh-process clock ramp "
                         "left :sum with no fast-regime sample on any cell -- "
                         "the shape-2 record's structural blocker on the "
                         "W = 32 regime question; this order puts :sum's "
                         "block after the ramp on purpose)"))
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
    per_op_ratios = {}
    for op in ("sum", "max", "min"):
        ratios = []
        for ri in range(args.runs):
            b = per_run[(op, "baseline", ri)]
            v = per_run[(op, "variant", ri)]
            ratios.append(statistics.median(v) / statistics.median(b))
        per_op_ratios[op] = ratios
        lines.append(f"| {op} | {', '.join(f'{r:.3f}' for r in ratios)} | "
                     f"{statistics.median(ratios):.3f} |")
    lines.append("")
    # Claim protocol rules 1 and 2 (the 2026-10-23 regime-robust magnitude
    # claim protocol, ADR-0360): the regime clusters this session observed,
    # published from the same per-run baseline medians the first table
    # lists (rule 1), and the sign classification over the per-run paired
    # ratios just tabulated (rule 2). Implemented in
    # scripts/gpu_regime_classify.py (GAP-1.15 clustering + sign verdicts).
    lines.append(gpu_regime_classify.render_section(
        {op: {ri + 1: statistics.median(per_run[(op, "baseline", ri)])
              for ri in range(args.runs)}
         for op in ("sum", "max", "min")},
        ratios=per_op_ratios))
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
        "read-back. ADR-0360 question (1)'s 2026-10-23 decision admits this "
        "native-Metal channel as contract-satisfying FOR THE MSL ARM: wire 42 "
        "executes SPIR-V through Vulkan and can never run MSL, so a "
        "wire-42-only contract could never measure this arm at all (the GLSL "
        "arm is a different story and keeps its LABELED BOOTSTRAP status). No "
        "`:measured?` flag moves in THIS run: the honesty-lock flip set is "
        "code (accelerator_variants' :measured-cell W set) and extends in its "
        "own slice, and no workgroup row (ADR-0355/0358) is touched.")
    (out / "summary.md").write_text(finalize_summary(
        "\n".join(lines) + "\n", args.compare_historical,
        str(out / "summary.md")))
    print((out / "summary.md").read_text(), end="")
    shutil.rmtree(build, ignore_errors=True)


if __name__ == "__main__":
    main()
