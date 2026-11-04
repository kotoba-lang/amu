#!/usr/bin/env python3
"""One Q8_0 matvec on the Apple GPU from Amu selfhost (JUN-819, ADR 0375, ADR 0405).

GPU-host gate, Mac arm64, outside mandatory CDCI. `bin/amu compile
--runtime-profile amu-program-metal` builds the program; Python only stages
sources, runs the programs and compares. `cc` is a test-time oracle for the C
twin; with no C compiler that row is reported as not run.

  exact           Metal = the Kotoba CPU twin = the C twin
  mutant          one changed kernel operator changes the answer
  refused-kernel  a kernel Metal cannot compile prints the error and traps
  ordinary        the same program in the default profile traps at wire 42
  dylibs          the Metal image names only libSystem; the ordinary image none

Timings are diagnostics: quiet host or not, they are not a published benchmark.
"""
import argparse
import json
import os
import platform
import resource
import shutil
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "seed/tests/macos-metal"
AMU = ROOT / "bin/amu"
ROWS, COLS = 4864, 896
LC_LOAD_DYLIB = 12


def render(name, reps, op="+="):
    text = (TESTS / name).read_text()
    for key, value in (("@ROWS@", ROWS), ("@COLS@", COLS), ("@REPS@", reps),
                       ("@BLOCKS@", COLS // 32), ("@OP@", op)):
        text = text.replace(key, str(value))
    return text


def build(work, name, source, profile=None):
    path = work / f"{name}.kotoba"
    path.write_text(source)
    output = work / name
    command = [AMU, "compile", path]
    if profile:
        command += ["--runtime-profile", profile]
    subprocess.run([*command, "-o", output], check=True, capture_output=True, timeout=600)
    return output


def run(image, timeout=120):
    r = subprocess.run([image], capture_output=True, text=True, timeout=timeout,
                       env={"PATH": "/usr/bin:/bin", "LANG": "C"})
    return r.returncode, r.stdout.strip(), r.stderr


def dylibs(image):
    data = image.read_bytes()
    magic, _, _, _, count = struct.unpack_from("<IIIII", data)
    if magic != 0xfeedfacf:
        raise ValueError("not a thin 64-bit Mach-O: " + image.name)
    found, at = [], 32
    for _ in range(count):
        cmd, size = struct.unpack_from("<II", data, at)
        if cmd == LC_LOAD_DYLIB:
            start = at + struct.unpack_from("<I", data, at + 8)[0]
            found.append(data[start:data.index(b"\0", start)].decode())
        at += size
    return found


def c_twin(work, reps):
    cc = shutil.which("cc")
    if cc is None:
        return None
    output = work / f"q8c-{reps}"
    subprocess.run([cc, "-O2", f"-DROWS={ROWS}", f"-DCOLS={COLS}", f"-DREPS={reps}",
                    TESTS / "q8_matvec.c", "-o", output], check=True, capture_output=True)
    return output


def per_rep_cpu_ms(low, high, reps):
    def cost(image):
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        code, _, _ = run(image)
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        if code != 0:
            raise ValueError("timing run failed: " + image.name)
        return (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)
    return round(min(cost(high) - cost(low) for _ in range(3)) * 1000 / reps, 3)


def main(work):
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise SystemExit("the Metal gate runs on Mac arm64")
    work.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {"schema": "amu.macos-metal.v1", "rows": ROWS, "cols": COLS, "amu": str(AMU.relative_to(ROOT))}

    metal = build(work, "metal", render("q8_metal.kotoba.in", 3), "amu-program-metal")
    cpu = build(work, "cpu", render("q8_cpu.kotoba.in", 3))
    code, got, err = run(metal)
    if code != 0 or "metal-dispatch-ns" not in err:
        raise ValueError(f"Metal program failed ({code}): {err[-400:]}")
    cpu_code, want, _ = run(cpu)
    if cpu_code != 0 or got != want:
        raise ValueError(f"Metal {got} differs from the Kotoba CPU twin {want}")
    twin = c_twin(work, 3)
    if twin is not None and run(twin)[1] != got:
        raise ValueError("Metal result differs from the C twin")
    report["exact"] = {"result": got, "kotobaCpu": want, "cTwin": "equal" if twin else "not run"}

    code, mutated, _ = run(build(work, "mutant", render("q8_metal.kotoba.in", 3, "-="), "amu-program-metal"))
    if code != 0 or mutated == got:
        raise ValueError("the mutated kernel did not change the answer")
    report["mutant"] = {"operator": "sumi -=", "result": mutated}

    code, out, err = run(build(work, "refused", render("q8_metal.kotoba.in", 1, "@@"), "amu-program-metal"))
    if code == 0 or out or "program_source" not in err:
        raise ValueError(f"a broken kernel was not refused ({code}): {err[-300:]}")
    report["refusedKernel"] = {"exit": code, "compilerError": err.splitlines()[0][:120]}

    ordinary = build(work, "ordinary", render("q8_metal.kotoba.in", 1))
    code, out, _ = run(ordinary)
    if code == 0 or out:
        raise ValueError(f"the default profile reached the Metal route ({code})")
    report["ordinary"] = {"exit": code}

    names = dylibs(metal)
    if names != ["/usr/lib/libSystem.B.dylib"] or dylibs(ordinary) or dylibs(cpu):
        raise ValueError(f"unexpected dylibs: {names}")
    report["dylibs"] = {"metal": names, "ordinary": []}

    reps = 64
    timed = build(work, "timed", render("q8_metal.kotoba.in", reps), "amu-program-metal")
    code, _, err = run(timed)
    words = err.split()
    if code != 0 or words[:2] != ["metal-dispatch-ns", "best"]:
        raise ValueError("timing run failed: " + err[-200:])
    best, total = int(words[2]), int(words[4])
    macs = ROWS * COLS
    cpu_ms = per_rep_cpu_ms(build(work, "cpu1", render("q8_cpu.kotoba.in", 1)),
                            build(work, "cpu65", render("q8_cpu.kotoba.in", 65)), 64)
    c_ms = None
    if twin is not None:
        c_ms = per_rep_cpu_ms(c_twin(work, 1), c_twin(work, 65), 64)
    report["timing"] = {
        "diagnostic": True, "loadAverage": os.getloadavg(), "dispatches": reps,
        "metalBestUs": round(best / 1000, 1), "metalMeanUs": round(total / reps / 1000, 1),
        "metalBestGMacPerS": round(macs / best, 2), "kotobaCpuMs": cpu_ms, "cCpuMs": c_ms,
    }
    (work / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_MACOS_METAL_KERNEL", got, json.dumps(report["timing"]), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output.resolve())
