#!/usr/bin/env python3
"""H33: compare exact qualified public/core-role kernels, never replace a gate.

The controller's rebuild is slower than separately observed public compiles.
Different runners cannot establish why. Measure both kernels with the same
source, lock, native host, CPU and controller environment before refactoring.
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
PUBLIC_SHA = "dd289a234cb781248b29924139d8903865dd6337cb82c2ee8dcba7f261e31d98"
ROLE_SHA = "3d9ae898c59c01c448db68aa2c5777354c8d010b6292ec7753ba337fe358a090"
SOURCE_SHA = "44faa79ad33730bd81d28329e62bfd2030adee09d1ef31c8e8800f7164e13081"
OUTPUT_SHA = "6ad407c211c16efb425f4fa4761b0421e6e180211e4d6c28b8d6fb4bf35e0070"


def pin(path):
    b = path.read_bytes()
    return dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())


def main(compiler, out):
    assert platform.system() == "Linux" and platform.machine() == "x86_64"
    assert struct.unpack_from("<H", Path("/proc/self/exe").read_bytes(), 18)[0] == 62
    assert pin(compiler)["sha256"] == PUBLIC_SHA
    out.mkdir(parents=True, exist_ok=False)

    def unity(manifest, name):
        paths = [p for p in (ROOT / manifest).read_text().splitlines() if p and not p.startswith("#")]
        assert len(paths) == 18
        p = out / name
        p.write_bytes(b"".join((ROOT / n).read_bytes() + b"\n" for n in paths))
        return p, {n: pin(ROOT / n) for n in paths}

    source, bindings = unity("seed/MANIFEST", "core.kotoba")
    static, static_bindings = unity("seed/CORE-STATIC-MANIFEST", "core-static.kotoba")
    assert pin(source)["sha256"] == SOURCE_SHA
    lock = out / "core.ksl"
    lock.write_text(f"KSL1\nentry {source}\nfile {SOURCE_SHA} {source}\n")
    cpus = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {cpus[0]})
    # Exact four entries prepared by native kc-prepare-env(mode0), with this
    # experiment's own root. No extra fuel/command override or scope widening.
    env = dict(PATH="/nonexistent", KEXE_ALLOW="35,37,38,39", KEXE_STACK_BYTES="8388608",
               KEXE_CAP_RESOURCES_35=str(out))
    report = dict(schema="amu.native-compiler-kernel-comparison.v1", nativeVerdictAuthority=False,
                  qualificationReplacement=False, candidateAdopted=False, controllerSandbox=False,
                  host=[platform.system(), platform.machine(), platform.release()], selectedCPU=cpus[0],
                  producer=pin(compiler), source=pin(source), staticSource=pin(static), sourceLock=pin(lock),
                  sourceBindings=bindings, staticBindings=static_bindings, environment=env, calls=[])
    report["cpuModel"] = next((v for v in Path("/proc/cpuinfo").read_text().splitlines()
                                if v.startswith("model name")), "unavailable")

    def save():
        (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")

    def run(name, argv):
        start = time.monotonic()
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        p = subprocess.run(list(map(str, argv)), cwd=out, env=env, capture_output=True, timeout=900)
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        for stream, raw in (("stdout", p.stdout), ("stderr", p.stderr)):
            (out / (name + "." + stream)).write_bytes(raw)
        row = dict(name=name, exit=p.returncode, seconds=time.monotonic() - start,
                   cpuSeconds=after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
                   loadEnd=os.getloadavg())
        report["calls"].append(row)
        save()
        print(json.dumps(row), flush=True)
        assert p.returncode == 0 and not p.stderr, (name, p.returncode, p.stderr[-1000:])
        return row

    role = out / "amu-selfhost.elf"
    run("build-exact-role", [compiler, "compile", static, "--target", "x86_64-linux",
                              "--output", role, "--format", "static"])
    role.chmod(0o755)
    assert pin(role)["sha256"] == ROLE_SHA
    report["roleImage"] = pin(role)

    def measure(i, name):
        image = role if name == "role" else compiler
        output = out / f"{i}-{name}.kseed"
        row = run(f"measure-{i}-{name}", [image, "compile", source, "--target", "aarch64-macos",
                  "--output", output, "--source-lock", lock, "--source-lock-sha256", pin(lock)["sha256"]])
        row["output"] = pin(output)
        assert row["output"]["sha256"] == OUTPUT_SHA
        save()
        return row["seconds"]

    role_time = measure(0, "role")
    public_time = measure(1, "public")
    # A bounded screen avoids two more slow compiles when the suspected
    # kernel gap is absent. Record the screen rather than invent an ABBA score.
    if public_time < 0.9 * role_time:
        measure(2, "public")
        measure(3, "role")
        report["completedABBA"] = True
    else:
        report["completedABBA"] = False
    samples = {v: [c["seconds"] for c in report["calls"] if c["name"].startswith("measure-")
                   and c["name"].endswith("-" + v)] for v in ("role", "public")}
    report.update(status="PASS_NATIVE_COMPILER_KERNEL_COMPARISON", samples=samples,
                  publicToRoleRatio=statistics.median(samples["public"]) / statistics.median(samples["role"]),
                  allCoreOutputsByteIdentical=True, productionRoleChanged=False)
    save()
    print(report["status"], report["publicToRoleRatio"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.compiler.resolve(), a.output.resolve())
