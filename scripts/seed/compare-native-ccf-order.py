#!/usr/bin/env python3
"""Bounded H18 experiment: native oracle/mutants then matched frozen-core builds.

This stages a separate compiler candidate. It never changes production sources,
pins, proof authority or admission. Amu alone compiles and emits every image.
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
REVISION = "4abac3fd612de050fd7f7a4635deb80ca9a0cb73"
SOURCE_SHA = "026d87a058f4f8b7006e2f09ea26d3713633cf3b4585329d818caab1280bc79d"
OUTPUT_SHA = "6ad407c211c16efb425f4fa4761b0421e6e180211e4d6c28b8d6fb4bf35e0070"


def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def manifest(name, read):
    return [p for p in read(name).decode().splitlines() if p and not p.startswith("#")]


def main(out, workload_file=None, current_core=False, producer_override=None, variant="order", controls_only=False):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "x86_64")
    arm = platform.machine() == "aarch64"
    machine = 183 if arm else 62
    assert struct.unpack_from("<H", Path("/proc/self/exe").read_bytes(), 18)[0] == machine
    producer = producer_override or ROOT / ("seed/bootstrap/aarch64-linux-static-root.elf" if arm else "bin/amu")
    assert struct.unpack_from("<H", producer.read_bytes(), 18)[0] == machine
    out.mkdir(parents=True, exist_ok=False)
    read = lambda p: (ROOT / p).read_bytes()
    paths = manifest("seed/FULL-MANIFEST", read)
    original = b"".join(read(p) + b"\n" for p in paths).decode()
    fixture = ROOT / ("seed/tests/native-ccf-addressed-candidate.kotoba" if variant == "addressed" else ("seed/tests/native-ccf-filtered-candidate.kotoba" if variant == "filtered" else "seed/tests/native-ccf-order-candidate.kotoba"))
    extra = fixture.read_text()
    first = extra.index("(defn- ccf-code-reference [" if variant == "addressed" else "(defn- ccf-code-ordered [")
    last = extra.index("(defn- ccf-order-word", first)
    ordered = extra[first:last].replace("ccf-code-ordered", "ccf-code")
    start = original.index("(defn- ccf-code [")
    end = original.index(";; Preserve direct returned-value comparison", start)
    candidate_source = out / "candidate-full.kotoba"
    candidate_source.write_text(original[:start] + ordered + original[end:])

    def frozen(path):
        return subprocess.run(["git", "show", REVISION + ":" + path], cwd=ROOT,
                              capture_output=True, check=True).stdout

    if current_core:
        assert workload_file is None
        raw = b"".join(read(p) + b"\n" for p in manifest("seed/MANIFEST", read))
    elif workload_file:
        raw = workload_file.read_bytes()
    else:
        raw = b"".join(frozen(p) + b"\n" for p in manifest("seed/MANIFEST", frozen))
    workload = out / "workload.kotoba"
    workload.write_bytes(raw)
    expected_source = "44faa79ad33730bd81d28329e62bfd2030adee09d1ef31c8e8800f7164e13081" if current_core else SOURCE_SHA
    assert pin(workload)["sha256"] == expected_source
    lock = out / "workload.ksl"
    lock.write_text(f"KSL1\nentry {workload}\nfile {expected_source} {workload}\n")
    affinity = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {affinity[0]})
    env = dict(PATH="/nonexistent", KEXE_STACK_BYTES="8388608", KEXE_CAP_RESOURCES_35=str(out),
               KEXE_ALLOW="35,37,38,39", KEXE_FUEL="10000000000", KEXE_COMMAND="1")
    report = dict(schema="amu.native-ccf-order-experiment.v1", nativeVerdictAuthority=False,
                  qualificationReplacement=False, candidateAdopted=False, fullQualification=False,
                  compilerAlgorithmChanged=True, sourceWorkloadChanged=False, emulation=False, variant=variant,
                  host=[platform.system(), platform.machine(), platform.release()],
                  allowedCPUs=affinity, selectedCPU=affinity[0], producer=pin(producer),
                  sourceBindings={p: pin(ROOT / p) for p in paths}, candidateSource=pin(candidate_source),
                  fixture=pin(fixture), workloadRevision=("current-source-pinned-by-hash" if current_core else REVISION), workload=pin(workload), calls=[])
    cpuinfo = Path("/proc/cpuinfo").read_text()
    report["cpuModel"] = next((s for s in cpuinfo.splitlines() if s.startswith("model name")), "unavailable")

    def save():
        (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")

    def run(name, argv, expected=0):
        start = time.monotonic()
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        load = os.getloadavg()
        p = subprocess.run(list(map(str, argv)), cwd=out, env=env, capture_output=True, timeout=900)
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        for stream, data in (("stdout", p.stdout), ("stderr", p.stderr)):
            (out / (name + "." + stream)).write_bytes(data)
        row = dict(name=name, exit=p.returncode, seconds=time.monotonic() - start,
                   cpuSeconds=after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
                   loadStart=load, loadEnd=os.getloadavg())
        report["calls"].append(row)
        save()
        print(json.dumps(row), flush=True)
        assert p.returncode == expected and not p.stderr, (name, p.returncode, p.stderr[-1000:])
        return row

    target = "aarch64-linux" if arm else "x86_64-linux"
    prefix = manifest("seed/CORE-STATIC-MANIFEST", read)[:-1]
    grid = out / "grid.kotoba"
    grid.write_bytes(b"".join(read(p) + b"\n" for p in prefix) + fixture.read_bytes())

    def static(name, source):
        image = out / (name + ".elf")
        run("build-" + name, [producer, "compile", source, "--target", target,
                              "--output", image, "--format", "static"])
        image.chmod(0o755)
        return image

    image = static("grid", grid)
    run("differential-grid", [image])
    run("grid-wrong-mode", [image, "fail-control"], 1)
    report["gridCases"] = 131072 if variant == "filtered" else 65536
    report["mutationControls"] = []
    text = grid.read_text()
    a = text.index("(defn- ccf-code-absolute [" if variant == "addressed" else "(defn- ccf-code-ordered [")
    b = text.index("(defn- ccf-code-ordered [" if variant == "addressed" else "(defn- ccf-order-word", a + 1)
    fragment = text[a:b]
    mutations = [("word-bound", "(and (>= w 0) (<= w 4294967295)", "(and true true"),
                 ("adrp", "(not= page 2415919104)", "true")]
    if variant == "filtered":
        mutations += [("class-adr-bit", "67835469688274944", "67835469688209408"),
                      ("class-literal-bit", "67835469688274944", "67835469671497728")]
    for name, old, new in mutations:
        assert fragment.count(old) == 1
        source = out / ("mutant-" + name + ".kotoba")
        source.write_text(text[:a] + fragment.replace(old, new) + text[b:])
        mutant = static("mutant-" + name, source)
        run("detect-" + name, [mutant], 1)
        report["mutationControls"].append(dict(name=name, builtSuccessfully=True, detectedByNativeGrid=True))

    if controls_only:
        report.update(status="PASS_NATIVE_CCF_CONTROLS_ONLY", performanceMeasured=False)
        save()
        print(report["status"], flush=True)
        return
    if arm:
        container = out / "candidate.kseed"
        run("build-candidate", [producer, "compile", candidate_source, "--target", "aarch64-macos", "--output", container])
        runner = out / "runner.kotoba"
        runner.write_bytes(read("seed/x86_64-kx64-runner.kotoba"))
        candidate = out / "candidate.elf"
        run("pack-candidate", [producer, "compile", runner, "--target", target, "--output", candidate,
                               "--format", "packed", "--payload", container])
        candidate.chmod(0o755)
    else:
        candidate = static("candidate", candidate_source)
    report["candidateImage"] = pin(candidate)
    for i, (name, compiler) in enumerate((("baseline", producer), ("candidate", candidate),
                                         ("candidate", candidate), ("baseline", producer))):
        dst = out / (str(i) + "-" + name + ".kseed")
        row = run("measure-" + str(i) + "-" + name,
                  [compiler, "compile", workload, "--source-lock", lock, "--source-lock-sha256", pin(lock)["sha256"],
                   "--target", "aarch64-macos", "--output", dst])
        row["output"] = pin(dst)
        assert row["output"]["sha256"] == OUTPUT_SHA, "frozen core output changed"
    samples = {v: [r["seconds"] for r in report["calls"]
                   if r["name"].startswith("measure-") and r["name"].endswith("-" + v)]
               for v in ("baseline", "candidate")}
    report.update(status="PASS_NATIVE_CCF_ORDER_EXPERIMENT", samples=samples,
                  candidateToBaselineRatio=statistics.median(samples["candidate"]) / statistics.median(samples["baseline"]),
                  allCoreOutputsByteIdentical=True)
    save()
    print(report["status"], report["candidateToBaselineRatio"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--workload-file", type=Path)
    p.add_argument("--current-core", action="store_true")
    p.add_argument("--compiler", type=Path)
    p.add_argument("--variant", choices=("order", "addressed", "filtered"), default="order")
    p.add_argument("--controls-only", action="store_true")
    a = p.parse_args()
    main(a.output.resolve(), a.workload_file and a.workload_file.resolve(), a.current_core, a.compiler.resolve() if a.compiler else None, a.variant, a.controls_only)
