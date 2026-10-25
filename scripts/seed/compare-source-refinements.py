#!/usr/bin/env python3
"""Screen explicit implementation annotations, then compare B/C/C/B natively.

This changes three source parameter annotations, not the compiler algorithm.
Every complete-prefix output must be byte-identical to the independently
qualified original image, and its semantic/refusal entry executes afresh.
Python stages fixed source edits and observes processes; it infers no types.
"""
import argparse
import hashlib
import json
import os
import platform
import resource
import statistics
import struct
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANNOTATIONS = {
    "doctail": ("(defn- ck-r6c-doctail [M :vector-i64 S c :i64]", "(defn- ck-r6c-doctail [M :vector-i64 S :string c :i64]"),
    "dt": ("(defn- ck-r6c-dt [M :vector-i64 S b :i64]", "(defn- ck-r6c-dt [M :vector-i64 S :string b :i64]"),
    "lit": ("(defn- ck-r6c-lit [M :vector-i64 S m :i64]", "(defn- ck-r6c-lit [M :vector-i64 S :string m :i64]"),
}
SOURCE_SHA = "daa88291555eb738df9d0dd36a1a498d69d550eff89f97931318c20627fb5a8b"
INPUT_REVISION = "4abac3fd612de050fd7f7a4635deb80ca9a0cb73"
IMAGE_SHA = {"aarch64": "18c5b8d07c9722fb135127b81b1bb8389fe0b80eef13a06572bee38e4c17facc",
             "x86_64": "378fd3cd99fcd9951654612e2df4e2b055d00bf6c068c1b4eeec325325712591"}


def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main(out, workload_file=None):
    assert platform.system() == "Linux" and platform.machine() in IMAGE_SHA
    host = platform.machine()
    machine = 183 if host == "aarch64" else 62
    assert struct.unpack_from("<H", Path("/proc/self/exe").read_bytes(), 18)[0] == machine
    producer = ROOT / ("seed/bootstrap/aarch64-linux-static-root.elf" if host == "aarch64" else "bin/amu")
    assert struct.unpack_from("<H", producer.read_bytes(), 18)[0] == machine
    out.mkdir(parents=True, exist_ok=False)
    if workload_file:
        original = workload_file.read_bytes()
    else:
        def frozen(path):
            return subprocess.run(["git", "show", INPUT_REVISION + ":" + path], cwd=ROOT,
                                  capture_output=True, check=True).stdout
        paths = [p for p in frozen("seed/CORE-STATIC-MANIFEST").decode().splitlines() if p and not p.startswith("#")]
        original = b"".join(frozen(p) + b"\n" for p in paths[:-1]) + frozen("seed/tests/native-label-index.kotoba")
    assert hashlib.sha256(original).hexdigest() == SOURCE_SHA
    affinity = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {affinity[0]})
    report = dict(schema="amu.native-source-refinement-comparison.v1", nativeVerdictAuthority=False,
                  qualificationReplacement=False, candidateAdopted=False, compilerAlgorithmChanged=False,
                  sourceWorkloadChanged=True, emulation=False, originalSourceSHA256=SOURCE_SHA,
                  workloadRevision=INPUT_REVISION,
                  producer=pin(producer), host=[platform.system(), host, platform.release()],
                  allowedCPUs=affinity, selectedCPU=affinity[0], variants={}, calls=[])
    cpuinfo = Path("/proc/cpuinfo").read_text()
    report["cpuModel"] = next((s for s in cpuinfo.splitlines() if s.startswith("model name")), "unavailable")
    report["cgroup"] = {}
    for name in ("cpu.max", "cpu.stat", "memory.max"):
        p = Path("/sys/fs/cgroup") / name
        if p.exists():
            report["cgroup"][name] = p.read_text()
    sources = {}
    for variant in ("baseline", "doctail", "dt", "lit", "all"):
        text = original.decode()
        selected = list(ANNOTATIONS) if variant == "all" else ([] if variant == "baseline" else [variant])
        for name in selected:
            old, new = ANNOTATIONS[name]
            assert text.count(old) == 1
            text = text.replace(old, new)
        source = out / (variant + ".kotoba")
        source.write_text(text)
        sources[variant] = source
        report["variants"][variant] = dict(source=pin(source), explicitAnnotations=selected)
    env = dict(PATH="/nonexistent", KEXE_STACK_BYTES="8388608", KEXE_CAP_RESOURCES_35=str(out),
               KEXE_ALLOW="35,37,38,39", KEXE_FUEL="10000000000", KEXE_COMMAND="1")
    target = "aarch64-linux" if host == "aarch64" else "x86_64-linux"

    def run(name, argv, expected, runtime_env=env):
        started = time.monotonic()
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        load = os.getloadavg()
        p = subprocess.run(list(map(str, argv)), cwd=out, env=runtime_env, capture_output=True, timeout=900)
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        for stream, raw in (("stdout", p.stdout), ("stderr", p.stderr)):
            (out / (name + "." + stream)).write_bytes(raw)
        row = dict(name=name, exit=p.returncode, seconds=time.monotonic() - started,
                   cpuSeconds=after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
                   loadStart=load, loadEnd=os.getloadavg())
        report["calls"].append(row)
        (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(row), flush=True)
        assert p.returncode == expected and not p.stderr, (name, p.returncode, p.stderr[-1000:])
        return row

    # Screen the isolated edits first, then an actual B/C/C/B comparison of
    # original vs fully annotated source under the identical producing image.
    order = ["doctail", "dt", "lit", "baseline", "all", "all", "baseline"]
    for i, variant in enumerate(order):
        name = f"{i}-{variant}"
        image = out / (name + ".elf")
        row = run("build-" + name, [producer, "compile", sources[variant], "--target", target,
                                    "--output", image, "--format", "static"], 0)
        row["image"] = pin(image)
        assert row["image"]["sha256"] == IMAGE_SHA[host], (variant, "emitted program changed")
        image.chmod(0o755)
        runtime_env = dict(env, KEXE_ALLOW="38")
        run("semantic-" + name, [image], 0, runtime_env)
        run("refusal-" + name, [image, "fail-control"], 1, runtime_env)
    samples = {v: [r["seconds"] for r in report["calls"] if r["name"].startswith("build-") and r["name"].endswith("-" + v)]
               for v in ("baseline", "all")}
    report.update(status="PASS_NATIVE_EXPLICIT_ANNOTATION_COMPARISON", samples=samples,
                  candidateToBaselineRatio=statistics.median(samples["all"]) / statistics.median(samples["baseline"]),
                  allImagesByteIdentical=True, freshSemanticExecutions=7, freshRefusalExecutions=7)
    (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], report["candidateToBaselineRatio"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--workload-file", type=Path)
    a = p.parse_args()
    main(a.output.resolve(), a.workload_file and a.workload_file.resolve())
