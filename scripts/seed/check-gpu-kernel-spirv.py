#!/usr/bin/env python3
"""GPU kernels as SPIR-V from Kotoba, through the loaderless compiler (ADR 0372 steps 1-2).

Modules: KIR v1 elementwise (4 operators x 2 workgroup sizes), workgroup
reductions (3 x 2), the ADR 0358 workgroup-sweep FMA kernel (LocalSize 32..1024)
and the subgroup reductions (3, GroupNonUniformArithmetic).

Phase "refs" (a host with glslangValidator): glslang compiles the hand-written
oracle kernels tools/gpu_kernel_refs/*.comp into OUT/refs/ref-*.spv. The
build phase puts them into the scope, and the Kotoba checker must accept
them: a structural check of modules that Amu did not write.

Phase "build" (Linux): one unit is built from the test's ns line, then
tools/spirv_encode.kotoba, tools/spirv_check.kotoba and
tools/gpu_kernel_kir1.kotoba without their ns lines, then the rest of
tools/gpu_kernel_spirv_test.kotoba (as seed/MANIFEST units are built). An
Amu-produced static compiler (--compiler: the pinned root or S3.elf) compiles
it with --format static, and the image runs with a writable :fs/app-data scope
(KEXE_CAP_RESOURCES_35) into which it writes the .spv modules. Checked in
both directions:
* the unit: every case passes, and CASES equals the expect calls counted in
  the test source;
* the control (CONTROL 1, one expected refusal made wrong): exactly one fails.
The modules written are hashed into the receipt.

Phase "oracle" (any host with SPIRV-Tools): spirv-val (--target-env
vulkan1.1, i.e. SPIR-V 1.3) and spirv-dis run on every module of a build
output and their results join the receipt. They are test oracles only: the
product route has no C or C++ tool (ADR 0372).

Python only orchestrates processes and hashes. Examples:
  podman run --platform linux/arm64 -v REPO:REPO -v OUT:OUT python:3.12-alpine \
    python3 REPO/scripts/seed/check-gpu-kernel-spirv.py build \
    --compiler REPO/seed/bootstrap/aarch64-linux-static-root.elf --output OUT
  python3 scripts/seed/check-gpu-kernel-spirv.py oracle --output OUT
(run "refs --output OUT" on the host first.)
"""
import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULES = ["tools/spirv_encode.kotoba", "tools/spirv_check.kotoba", "tools/gpu_kernel_kir1.kotoba"]
TEST = "tools/gpu_kernel_spirv_test.kotoba"
FUEL = 100000000
EXPECT_CALL = re.compile(r"\(expect ")
REPORT = re.compile(rb"\{:status :(\w+) :result (-?\d+) :fuel \{:initial (\d+) :remaining (\d+)\}\}")


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def split_ns(text, name):
    first, rest = text.split("\n", 1)
    assert first.startswith("(ns ") and first.endswith("))") and first.count("(") == first.count(")"), (name, first)
    return first, rest


def units():
    bodies = [split_ns((ROOT / m).read_text(), m)[1] for m in MODULES]
    test_ns, test_body = split_ns((ROOT / TEST).read_text(), TEST)
    counted = len(EXPECT_CALL.findall(test_body))
    assert counted > 0 and f"(def CASES {counted})" in test_body, ("CASES must equal the expect calls", counted)
    assert test_body.count("(def CONTROL 0)") == 1
    unit = "\n".join([test_ns, *bodies, test_body])
    return counted, unit, unit.replace("(def CONTROL 0)", "(def CONTROL 1)")


REFS = ROOT / "tools/gpu_kernel_refs"


def refs(output):
    glslang = shutil.which("glslangValidator")
    assert glslang, "glslangValidator is needed for the refs phase (oracle input only)"
    out = output / "refs"
    out.mkdir(parents=True, exist_ok=False)
    rows = {}
    for comp in sorted(REFS.glob("*.comp")):
        spv = out / ("ref-" + comp.stem + ".spv")
        r = subprocess.run([glslang, "-V", "--target-env", "vulkan1.1", str(comp), "-o", str(spv)], capture_output=True, text=True)
        assert r.returncode == 0, (comp.name, r.stdout, r.stderr)
        rows[spv.name] = dict(source=pin(comp), module=pin(spv))
    version = subprocess.run([glslang, "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    (out / "refs.json").write_text(json.dumps(dict(tool=version, host=[platform.system(), platform.machine()], modules=rows,
                                                   note="oracle input only; not part of the product route"), indent=2) + "\n")
    print("REFS", len(rows), "glslang modules", flush=True)


def build(compiler, output, target, seccomp_if_available=False):
    assert platform.system() == "Linux", "run the build phase on Linux"
    refs_dir = output / "refs"
    assert (refs_dir / "refs.json").exists(), "run the refs phase first (on a host with glslangValidator)"
    art = output / "artifacts"
    art.mkdir(exist_ok=False)
    counted, unit, control = units()
    producer = art / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)

    def build_and_run(name, source, scope):
        scope.mkdir()
        for ref in refs_dir.glob("ref-*.spv"):
            shutil.copy(ref, scope / ref.name)
        src, elf = art / (name + ".kotoba"), art / (name + ".elf")
        src.write_text(source)
        c = subprocess.run([str(producer), "compile", str(src), "--target", target, "--output", str(elf), "--format", "static"],
                           cwd=art, env={"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art)}, capture_output=True, timeout=600)
        (art / (name + ".compile.stderr")).write_bytes(c.stderr)
        assert c.returncode == 0 and not c.stderr and b":ok true" in c.stdout, (name, c.returncode, c.stderr[-400:])
        elf.chmod(0o700)
        x = subprocess.run([str(elf)], cwd=scope,
                           env={"PATH": "/usr/bin:/bin", "KEXE_STRUCTURED_REPORT": "1", "KEXE_FUEL": str(FUEL),
                                "KEXE_CAP_RESOURCES_35": str(scope), **({"KEXE_SECCOMP": "if-available"} if seccomp_if_available else {})},
                           capture_output=True, timeout=300)
        (art / (name + ".run.stdout")).write_bytes(x.stdout)
        (art / (name + ".run.stderr")).write_bytes(x.stderr)
        assert x.returncode == 0 and not x.stderr, (name, x.returncode, x.stderr[-400:])
        lines = x.stdout.decode().splitlines()
        report = REPORT.search(x.stdout)
        assert report and report.group(1) == b"ok", (name, x.stdout[-400:])
        cases = [int(l.split()[1]) for l in lines if l.startswith("CASES ")]
        failed = [int(l.split()[1]) for l in lines if l.startswith("FAILED ")]
        fails = [l for l in lines if l.startswith("FAIL ")]
        assert len(cases) == 1 and len(failed) == 1, (name, lines[-5:])
        return dict(name=name, source=pin(src), image=pin(elf), result=int(report.group(2)),
                    fuelUsed=int(report.group(3)) - int(report.group(4)), cases=cases[0], failed=failed[0],
                    failLines=fails), cases[0], failed[0], fails

    spv = output / "spv"
    u, cases, failed, fails = build_and_run("kernel-test", unit, spv)
    assert cases == counted and failed == 0 and not fails, u
    k, cases, failed, fails = build_and_run("kernel-control", control, output / "spv-control")
    assert cases == counted and failed == 1 and len(fails) == 1 and fails[0].startswith("FAIL label inside an open block"), fails
    modules = {p.name: pin(p) for p in sorted(spv.glob("kir1-*.spv"))}
    sizes = {"ewise": 1004, "reduce-sum": 1740, "reduce-max": 1748, "reduce-min": 1748,
             "sweep": 856, "subgroup-sum": 1896, "subgroup-max": 1904, "subgroup-min": 1904}
    assert len(modules) == 23 and all(m["bytes"] == next(v for k, v in sizes.items() if k in n) for n, m in modules.items()), modules
    report = dict(status="PASS_GPU_KERNEL_SPIRV_BUILD", target=target, compiler=pin(compiler),
                  host=[platform.system(), platform.machine(), platform.release()],
                  imageSeccomp="if-available" if seccomp_if_available else "required",
                  sources={p: pin(ROOT / p) for p in [*MODULES, TEST]}, casesCounted=counted, runs=[u, k],
                  modules=modules, glslangReferences=json.loads((refs_dir / "refs.json").read_text()), cCompilerOrLoader=False)
    (output / "gpu-kernel-spirv.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], target, counted, "cases", len(modules), "modules", flush=True)


def oracle(output):
    receipt_path = output / "gpu-kernel-spirv.json"
    report = json.loads(receipt_path.read_text())
    val, dis = shutil.which("spirv-val"), shutil.which("spirv-dis")
    assert val and dis, "spirv-val and spirv-dis are needed for the oracle phase"
    version = subprocess.run([val, "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    rows = {}
    for name, expected in report["modules"].items():
        path = output / "spv" / name
        assert pin(path) == expected, (name, "module changed since the build")
        v = subprocess.run([val, "--target-env", "vulkan1.1", str(path)], capture_output=True, text=True)
        d = subprocess.run([dis, "--raw-id", str(path)], capture_output=True, text=True)
        (output / (name + ".dis")).write_text(d.stdout)
        assert v.returncode == 0 and not v.stdout.strip() and not v.stderr.strip(), (name, v.stdout, v.stderr)
        assert d.returncode == 0 and "OpEntryPoint GLCompute" in d.stdout, (name, d.stderr)
        rows[name] = dict(spirvVal="valid (vulkan1.1)", disassembledSHA256=hashlib.sha256(d.stdout.encode()).hexdigest())
    report["oracle"] = dict(tool=version, host=[platform.system(), platform.machine()], modules=rows,
                            note="test oracle only; not part of the product route")
    report["status"] = "PASS_GPU_KERNEL_SPIRV_BUILD_AND_ORACLE"
    receipt_path.write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], len(rows), "modules valid", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("phase", choices=["refs", "build", "oracle"])
    parser.add_argument("--compiler", type=Path, help="build: an Amu-produced static compiler (the pinned root or S3.elf)")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", choices=["aarch64-linux", "x86_64-linux"], default="aarch64-linux")
    parser.add_argument("--seccomp-if-available", action="store_true",
                        help="build: run the tool image with KEXE_SECCOMP=if-available (qemu-user has no seccomp); recorded")
    args = parser.parse_args()
    if args.phase == "refs":
        refs(args.output.resolve())
    elif args.phase == "build":
        assert args.compiler, "--compiler is required for the build phase"
        build(args.compiler.resolve(), args.output.resolve(), args.target, args.seccomp_if_available)
    else:
        oracle(args.output.resolve())
