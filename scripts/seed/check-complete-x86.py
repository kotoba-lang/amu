#!/usr/bin/env python3
"""Qualify the complete public compiler on an actual native Linux x86_64 kernel.

Transport/hash/process orchestration only. The product compiler emits every
image; the canonical native controller and native Kotoba gate own CDCI's
verdict, including all24 result/fuel/refusal cases.
"""
import argparse
import hashlib
import json
import platform
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def static_elf(path):
    b = Path(path).read_bytes()
    assert b[:8] == b"\x7fELF\x02\x01\x01\0"
    assert struct.unpack_from("<HH", b, 16) == (2, 62)
    off = struct.unpack_from("<Q", b, 32)[0]
    size, count = struct.unpack_from("<HH", b, 54)
    assert size == 56 and 0 < count <= 16 and off + count * size <= len(b)
    types = [struct.unpack_from("<I", b, off + i * size)[0] for i in range(count)]
    assert 2 not in types and 3 not in types, "dynamic loader/segment"
    return {**pin(path), "elf": "ET_EXEC/EM_X86_64", "interpreter": False, "dynamic": False}


def main(compiler, arm_proof, out):
    assert platform.system() == "Linux" and platform.machine() == "x86_64", "native Linux x86_64 required"
    proof = json.loads(arm_proof.read_text())
    assert pin(compiler) == proof["completeX86Compiler"]
    out.mkdir(parents=True, exist_ok=False)
    (out / "raw").mkdir()
    calls = []
    env = {"PATH": "/nonexistent", "KEXE_CAP_RESOURCES_35": str(out), "KEXE_STACK_BYTES": "8388608"}

    def run(name, argv, custom=None, ok=True, timeout=900):
        started = time.monotonic()
        r = subprocess.run(list(map(str, argv)), cwd=out, env=env if custom is None else custom,
                           capture_output=True, timeout=timeout)
        (out / "raw" / (name + ".stdout")).write_bytes(r.stdout)
        (out / "raw" / (name + ".stderr")).write_bytes(r.stderr)
        calls.append(dict(name=name, argv=list(map(str, argv)), exit=r.returncode,
                          seconds=round(time.monotonic() - started, 3)))
        (out / "calls.json").write_text(json.dumps(calls, indent=2) + "\n")
        if ok:
            assert r.returncode == 0 and not r.stderr, (name, r.returncode, r.stderr[-600:])
        return r

    manifest = ROOT / "seed/FULL-MANIFEST"
    paths = [s for s in manifest.read_text().splitlines() if s and not s.startswith("#")]
    for p, identity in proof["sources"]["seed/FULL-MANIFEST"].items():
        assert pin(ROOT / p) == identity, ("source drift", p)
    full = out / "full.kotoba"
    full.write_bytes(b"".join((ROOT / p).read_bytes() + b"\n" for p in paths))
    f1 = out / "F1.elf"
    shutil.copy2(compiler, f1)
    f1.chmod(0o755)
    generations = [static_elf(f1)]
    previous = f1
    for g in (2, 3):
        image = out / f"F{g}.elf"
        run(f"F{g}", [previous, "compile", full, "--target", "x86_64-linux", "--output", image, "--format", "static"])
        image.chmod(0o755)
        generations.append(static_elf(image))
        previous = image
    assert generations[0] == generations[1] == generations[2], "complete native x86 fixed point"
    F = previous

    roles = {}
    core_source = out / "core-static.kotoba"
    core_paths = [s for s in (ROOT / "seed/CORE-STATIC-MANIFEST").read_text().splitlines() if s and not s.startswith("#")]
    core_source.write_bytes(b"".join((ROOT / p).read_bytes() + b"\n" for p in core_paths))
    amu_gate = out / "cdci-amu-selfhost.elf"
    run("build-amu-selfhost", [F, "compile", core_source, "--target", "x86_64-linux", "--output", amu_gate, "--format", "static"])
    amu_gate.chmod(0o755)
    roles["amu-selfhost"] = static_elf(amu_gate)
    assert pin(amu_gate) == proof["cdci"]["images"]["amu-selfhost"]
    for name in ("entry.kotoba", "runtime.kotoba", "controller.kotoba", "kotoba-gate.kotoba"):
        dst = out / ("cdci-" + name)
        shutil.copy2(ROOT / "seed/cdci" / name, dst)
        assert pin(dst) == proof["cdci"]["sources"][name]
    for role, name in (("controller", "controller.kotoba"), ("kotoba-native", "kotoba-gate.kotoba")):
        dst = out / ("cdci-" + role + ".elf")
        run("build-" + role, [F, "cdci-build", role, out / "cdci-entry.kotoba", out / "cdci-runtime.kotoba", out / ("cdci-" + name), dst])
        dst.chmod(0o755)
        roles[role] = static_elf(dst)
        assert pin(dst) == proof["cdci"]["images"][role], ("role differs by producing kernel", role)

    cases = json.loads((ROOT / "seed/static-cases.json").read_text())["cases"]
    assert len(cases) == 24
    ledger = []
    for case in cases:
        src = out / ("case-" + case["name"] + ".kotoba")
        src.write_text(case["source"])
        dst = out / ("case-" + case["name"] + ".elf")
        run("compile-case-" + case["name"], [F, "compile", src, "--target", "x86_64-linux", "--output", dst, "--format", "static"])
        dst.chmod(0o755)
        ledger.append(dict(name=case["name"], source=pin(src), image=static_elf(dst),
                           result=case["result"], reference=case["reference"]))

    # Exercise the actual complete x86 product entry with pinned bytes. These
    # observations supplement, rather than substitute for, the native verdict.
    good = out / "public-good.kotoba"
    good.write_text("(ns public-good (:export [main]))\n(defn main [] :i64 42)\n")
    lock = out / "public-good.ksl"
    lock.write_text(f"KSL1\nentry {good}\nfile {pin(good)['sha256']} {good}\n")
    digest = pin(lock)["sha256"]
    run("native-public-check", [F, "check", good, "--source-lock", lock, "--source-lock-sha256", digest])
    run("native-public-compile", [F, "compile", good, "--target", "aarch64-macos", "--output", out / "public-good.kseed",
                                 "--source-lock", lock, "--source-lock-sha256", digest])
    unknown = out / "public-unknown.kotoba"
    unknown.write_text("(ns public-unknown (:export [main]))\n(defn main [] :i64 (amu-unresolved 0))\n")
    refusals = []
    for name, args, code in [
        ("digest-mismatch", ["check", good, "--source-lock", lock, "--source-lock-sha256", "0" * 64], b"E6015"),
        ("missing-lock", ["check", good, "--source-lock", out / "missing.ksl"], b"E6015"),
        ("unknown-form", ["check", unknown], b"E2101"),
        ("unsupported-default", ["compile", good, "--output", out / "refused.kseed"], b"E2"),
        ("unsupported-verb", ["worker"], b"E1"),
        ("unsupported-seal", ["compile", good, "--target", "aarch64-macos", "--output", out / "refused.kseed", "--seal", "unknown"], b"E1")]:
        r = run("native-public-refuse-" + name, [F, *args], ok=False)
        assert r.returncode in (1, 2) and code in r.stderr and b"KEXE_TRAP" not in r.stderr
        refusals.append(dict(name=name, exit=r.returncode, diagnostic=code.decode()))
    assert not (out / "refused.kseed").exists()

    report = dict(status="PASS_COMPLETE_NATIVE_X86_COMPILER_BUILD", host=[platform.system(), platform.machine(), platform.release()],
                  generations=generations, sourceUnity=pin(full), armBuildReceipt=pin(arm_proof),
                  coreAdoption=json.loads((ROOT / json.loads((ROOT / "seed/compiler-core.json").read_text())["adoptionReceipt"]).read_text()),
                  cdci=roles, cases=ledger, nativeCDCIExecutionQualified=False,
                  publicNativeEntry=dict(pinnedCheck=True, pinnedCompile=pin(out / "public-good.kseed"), refusals=refusals),
                  cCompilerOrLoader=False, JVMNodeOrGraalFallback=False, emulation=False)
    (out / "complete-x86.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], "F1=F2=F3", generations[0]["sha256"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--arm-proof", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.compiler.resolve(), a.arm_proof.resolve(), a.output.resolve())
