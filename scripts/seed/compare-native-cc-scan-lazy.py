#!/usr/bin/env python3
"""H27: lazy proof operand reads; native experiments, never admission."""
import argparse
import hashlib
import json
import os
import platform
import resource
import statistics
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main(out, producer=None):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "x86_64")
    arm = platform.machine() == "aarch64"
    target = "aarch64-linux" if arm else "x86_64-linux"
    producer = producer or ROOT / ("seed/bootstrap/aarch64-linux-static-root.elf" if arm else "bin/amu")
    out.mkdir(parents=True, exist_ok=False)
    paths = lambda name: [p for p in (ROOT / name).read_text().splitlines() if p and not p.startswith("#")]
    unity = lambda names: b"".join((ROOT / p).read_bytes() + b"\n" for p in names)
    fixture = ROOT / "seed/tests/native-cc-scan-lazy.kotoba"
    candidate_fragment = fixture.read_text()
    shared = (ROOT / "seed/tests/native-cc-safe-memo.kotoba").read_text()
    shared = shared[shared.index("(defn- cm-ins ["):]
    stubs = "(defn- cm-query [M :vector-i64 C :vector-i64 f :i64 n :i64 depth :i64 work :i64] :i64 (cl-safe M f n depth work))\n(defn- cm-safe [M :vector-i64 f :i64 n :i64 depth :i64 work :i64] :i64 (cl-safe M f n depth work))\n"
    extra = candidate_fragment + stubs + shared
    prefix = unity(paths("seed/CORE-STATIC-MANIFEST")[:-1]).decode()
    workload = out / "frozen-core18.kotoba"
    workload.write_bytes(unity(paths("seed/MANIFEST")))
    assert pin(workload)["sha256"] == "44faa79ad33730bd81d28329e62bfd2030adee09d1ef31c8e8800f7164e13081"
    lock = out / "workload.ksl"
    lock.write_text(f"KSL1\nentry {workload}\nfile {pin(workload)['sha256']} {workload}\n")
    cpus = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {cpus[0]})
    env = dict(PATH="/nonexistent", KEXE_STACK_BYTES="8388608", KEXE_CAP_RESOURCES_35=str(out),
               KEXE_ALLOW="35,37,38,39", KEXE_FUEL="10000000000", KEXE_COMMAND="1")
    report = dict(schema="amu.native-cc-scan-lazy-experiment.v1", nativeVerdictAuthority=False,
                  qualificationReplacement=False, candidateAdopted=False, fullQualification=False,
                  host=[platform.system(), platform.machine(), platform.release()], selectedCPU=cpus[0],
                  allowedCPUs=cpus, producer=pin(producer), fixture=pin(fixture), workload=pin(workload),
                  sourceBindings={p: pin(ROOT / p) for p in paths("seed/FULL-MANIFEST")}, calls=[])
    report["cpuModel"] = next((s for s in Path("/proc/cpuinfo").read_text().splitlines()
                                if s.startswith("model name")), "unavailable")

    def save():
        (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")

    def run(name, argv, expected=0):
        started = time.monotonic()
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        p = subprocess.run(list(map(str, argv)), cwd=out, env=env, capture_output=True, timeout=900)
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        for stream, raw in (("stdout", p.stdout), ("stderr", p.stderr)):
            (out / (name + "." + stream)).write_bytes(raw)
        row = dict(name=name, exit=p.returncode, seconds=time.monotonic() - started,
                   cpuSeconds=after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
                   minorFaults=after.ru_minflt - before.ru_minflt, loadEnd=os.getloadavg())
        report["calls"].append(row)
        save()
        print(json.dumps(row), flush=True)
        assert p.returncode == expected and not p.stderr, (name, p.returncode, p.stdout[-1500:], p.stderr[-1500:])
        return row

    def static(name, text):
        source = out / (name + ".kotoba")
        source.write_text(text)
        image = out / (name + ".elf")
        run("build-" + name, [producer, "compile", source, "--target", target,
                              "--output", image, "--format", "static"])
        image.chmod(0o755)
        return image

    image = static("grid", prefix + extra)
    run("differential-grid", [image])
    run("wrong-mode", [image, "fail"], 1)
    report["gridCases"] = 524288
    report["mutationControls"] = []
    for name, old, new, count in (
        ("work-charge", "left (dec work)", "left work", 1),
        ("float-bin", "(< (gn-sir M j IF-A) BOP-F64-ADD)", "true", 1),
        ("end-owner", "(= (gn-sir M j IF-A) f) left", "true left", 1),
        ("depth-bound", "(> depth 0)", "true", 1),
    ):
        assert extra.count(old) == count, name
        mutant = static("mutant-" + name, prefix + extra.replace(old, new))
        run("detect-" + name, [mutant], 1)
        report["mutationControls"].append(dict(name=name, image=pin(mutant), builtSuccessfully=True, executed=True))

    original = unity(paths("seed/FULL-MANIFEST")).decode()
    start = original.index("(defn- cc-safe [")
    end = original.index("(defn- di-type [", start)
    changed = candidate_fragment.replace("cl-safe", "cc-safe").replace("cl-scan", "cc-scan")
    text = original[:start] + changed + "\n" + original[end:]
    source = out / "candidate-full.kotoba"
    source.write_text(text)
    report["candidateSource"] = pin(source)
    if arm:
        payload = out / "candidate.kseed"
        run("candidate-container", [producer, "compile", source, "--target", "aarch64-macos", "--output", payload])
        runner = out / "runner.kotoba"
        runner.write_bytes((ROOT / "seed/x86_64-kx64-runner.kotoba").read_bytes())
        candidate = out / "candidate.elf"
        run("candidate-pack", [producer, "compile", runner, "--target", target, "--output", candidate,
                               "--format", "packed", "--payload", payload])
        candidate.chmod(0o755)
    else:
        candidate = static("candidate", text)
    report["candidateImage"] = pin(candidate)
    for i, name in enumerate(("baseline", "candidate", "candidate", "baseline")):
        compiler = producer if name == "baseline" else candidate
        dst = out / (str(i) + "-" + name + ".kseed")
        row = run("measure-" + str(i) + "-" + name,
                  [compiler, "compile", workload, "--source-lock", lock, "--source-lock-sha256", pin(lock)["sha256"],
                   "--target", "aarch64-macos", "--output", dst])
        row["output"] = pin(dst)
        assert row["output"]["sha256"] == "6ad407c211c16efb425f4fa4761b0421e6e180211e4d6c28b8d6fb4bf35e0070"
        save()
    samples = {v: [r["seconds"] for r in report["calls"]
                   if r["name"].startswith("measure-") and r["name"].endswith("-" + v)]
               for v in ("baseline", "candidate")}
    report.update(status="PASS_NATIVE_CC_SCAN_LAZY_EXPERIMENT", samples=samples,
                  candidateToBaselineRatio=statistics.median(samples["candidate"]) / statistics.median(samples["baseline"]),
                  allCoreOutputsByteIdentical=True, cacheLifetime="none", persistentCache=False)
    save()
    print(report["status"], report["candidateToBaselineRatio"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--compiler", type=Path)
    a = p.parse_args()
    main(a.output.resolve(), a.compiler.resolve() if a.compiler else None)
