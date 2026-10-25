#!/usr/bin/env python3
"""H21 native experiment only: fresh-map zeros, scope reuse, mutants and builds.

Production sources/pins stay unchanged. Python stages text, starts native Amu
and records observations. Every compiler, executable and container is emitted
by Amu. This experiment never substitutes for the full native qualification.
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
MARK_OLD = "r (kxrt-store64 (+ (kxrt-gl 688) (* u 8)) 0) w (kxrt-gs 48 (inc u))"
MARK_NEW = "r (kxrt-store64 (+ (kxrt-gl 688) (* u 8)) 0) high (if (> (+ off n) (kxrt-gl 760)) (kxrt-gs 760 (+ off n)) 0) w (kxrt-gs 48 (inc u))"
ZERO_OLD = """(let [z (loop [i 0] (if (= i n) 0 (let [w (kxrt-store64 (kxrt-item u i) 0)] (recur (inc i)))))
            w (kxrt-gs 64 (+ u n))]"""
ZERO_NEW = """(let [high (kxrt-gl 760) stop (if (< high (+ u n)) high (+ u n))
            count (if (> stop u) (- stop u) 0)
            z (loop [i 0] (if (= i count) 0 (let [w (kxrt-store64 (kxrt-item u i) 0)] (recur (inc i)))))
            w (kxrt-gs 64 (+ u n))]"""


def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main(out):
    arm = platform.machine() == "aarch64"
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "x86_64")
    machine = 183 if arm else 62
    assert struct.unpack_from("<H", Path("/proc/self/exe").read_bytes(), 18)[0] == machine
    producer = ROOT / ("seed/bootstrap/aarch64-linux-static-root.elf" if arm else "bin/amu")
    assert struct.unpack_from("<H", producer.read_bytes(), 18)[0] == machine
    out.mkdir(parents=True, exist_ok=False)
    paths = [p for p in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines() if p and not p.startswith("#")]
    original = b"".join((ROOT / p).read_bytes() + b"\n" for p in paths).decode()
    # Exactly the two native runtime templates. Cell760 is private, initially
    # zero, and excluded from all five arena rollback counters. Every item
    # writer finishes through vnew, or writes inside an already described view.
    assert original.count(MARK_OLD) == 2 and original.count(ZERO_OLD) == 2
    # Wasm owns a different context and already uses its own cell760. Audit
    # the selected native templates, never conflate the two private ABIs.
    for path in ("seed/76-x86_64-static-rt.kotoba", "seed/77-aarch64-static-rt.kotoba"):
        native = (ROOT / path).read_text()
        assert native.count(MARK_OLD) == 1 and native.count(ZERO_OLD) == 1
        assert "(kxrt-gl 760)" not in native and "(kxrt-gs 760 " not in native
    text = original.replace(MARK_OLD, MARK_NEW).replace(ZERO_OLD, ZERO_NEW)
    source = out / "candidate-full.kotoba"
    source.write_text(text)
    fixture = out / "oracle.kotoba"
    fixture.write_bytes((ROOT / "seed/tests/native-zero-watermark.kotoba").read_bytes())
    tiny = out / "tiny.kotoba"
    tiny.write_text("(ns zero.tiny (:export [main]))\n(defn main [] :i64 (+ 20 22))\n")
    runner = out / "runner.kotoba"
    runner.write_bytes((ROOT / "seed/x86_64-kx64-runner.kotoba").read_bytes())
    cpus = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {cpus[0]})
    env = dict(PATH="/nonexistent", KEXE_STACK_BYTES="8388608", KEXE_CAP_RESOURCES_35=str(out),
               KEXE_ALLOW="35,37,38,39", KEXE_FUEL="10000000000", KEXE_COMMAND="1")
    report = dict(schema="amu.native-zero-watermark-experiment.v1", nativeVerdictAuthority=False,
                  qualificationReplacement=False, candidateAdopted=False, fullQualification=False,
                  wholeWorkflowQualified=False, compilerAlgorithmChanged=False, runtimeChanged=True,
                  sourceWorkloadChanged=False, emulation=False,
                  host=[platform.system(), platform.machine(), platform.release()], allowedCPUs=cpus,
                  selectedCPU=cpus[0], producer=pin(producer), source=pin(source), fixture=pin(fixture),
                  workload=pin(tiny), sourceBindings={p: pin(ROOT / p) for p in paths}, calls=[], batches=[])
    cpuinfo = Path("/proc/cpuinfo").read_text()
    report["cpuModel"] = next((s for s in cpuinfo.splitlines() if s.startswith("model name")), "unavailable")

    def save():
        (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")

    def run(name, argv, expected=0):
        start = time.monotonic()
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        p = subprocess.run(list(map(str, argv)), cwd=out, env=env, capture_output=True, timeout=900)
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        for stream, data in (("stdout", p.stdout), ("stderr", p.stderr)):
            (out / (name + "." + stream)).write_bytes(data)
        row = dict(name=name, exit=p.returncode, seconds=time.monotonic() - start,
                   cpuSeconds=after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
                   minorFaults=after.ru_minflt - before.ru_minflt)
        report["calls"].append(row)
        save()
        print(json.dumps(row), flush=True)
        assert p.returncode == expected and not p.stderr, (name, p.returncode, p.stderr[-1000:])

    target = "aarch64-linux" if arm else "x86_64-linux"

    def static(name, compiler, src):
        image = out / (name + ".elf")
        run(name, [compiler, "compile", src, "--target", target, "--output", image, "--format", "static"])
        image.chmod(0o755)
        return image

    def pack(name, compiler, payload):
        image = out / (name + ".elf")
        run(name, [compiler, "compile", runner, "--target", target, "--output", image,
                   "--format", "packed", "--payload", payload])
        image.chmod(0o755)
        return image

    def old_engine(name, src):
        if not arm:
            return static(name, producer, src), None
        container = out / (name + ".kseed")
        run(name + "-container", [producer, "compile", src, "--target", "aarch64-macos", "--output", container])
        return pack(name, producer, container), container

    first, payload = old_engine("F1-original-engine", source)
    for name, compiler in (("baseline", producer), ("candidate", first)):
        image = static("build-" + name + "-oracle", compiler, fixture)
        run("execute-" + name + "-oracle", [image])
    report["mutationControls"] = []
    for name, changed in (("missing-marker", text.replace(MARK_NEW, MARK_OLD)),
                           ("relative-marker", text.replace("(kxrt-gs 760 (+ off n))", "(kxrt-gs 760 n)"))):
        src = out / (name + ".kotoba")
        src.write_text(changed)
        # The original engine emits a broken guest runtime, so successful
        # compilation followed by exit1 is an actual oracle detection.
        mutant, _ = old_engine(name + "-original-engine", src)
        image = static("build-" + name + "-oracle", mutant, fixture)
        run("detect-" + name, [image], 1)
        report["mutationControls"].append(dict(name=name, builtSuccessfully=True, detectedByNativeOracle=True))
    if arm:
        candidate = pack("F1-new-engine", first, payload)
        second = out / "F2.kseed"
        run("F2", [candidate, "compile", source, "--target", "aarch64-macos", "--output", second])
        assert second.read_bytes() == payload.read_bytes()
        final = pack("F2-new-engine", candidate, second)
        assert candidate.read_bytes() == final.read_bytes()
    else:
        candidate = static("F2-new-engine", first, source)
        final = static("F3-new-engine", candidate, source)
        assert candidate.read_bytes() == final.read_bytes()
    report["candidateImage"] = pin(final)
    report["nativeFixedPoint"] = True
    golden = None
    for i, (name, compiler) in enumerate((("baseline", producer), ("candidate", final),
                                         ("candidate", final), ("baseline", producer))):
        start = time.monotonic()
        for j in range(8):
            dst = out / (str(i) + "-" + name + "-" + str(j) + ".kseed")
            run("tiny-" + str(i) + "-" + name + "-" + str(j),
                [compiler, "compile", tiny, "--target", "aarch64-macos", "--output", dst])
            if golden is None:
                golden = dst.read_bytes()
            assert dst.read_bytes() == golden, "emitted tiny workload changed"
        report["batches"].append(dict(name=name, compiles=8, seconds=time.monotonic() - start))
        save()
    samples = {v: [r["seconds"] for r in report["batches"] if r["name"] == v] for v in ("baseline", "candidate")}
    report.update(status="PASS_NATIVE_ZERO_WATERMARK_EXPERIMENT", samples=samples,
                  candidateToBaselineRatio=statistics.median(samples["candidate"]) / statistics.median(samples["baseline"]),
                  allTinyOutputsByteIdentical=True, scopeReuseOraclePassed=True)
    save()
    print(report["status"], report["candidateToBaselineRatio"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.output.resolve())
