#!/usr/bin/env python3
"""Diagnostic for JUN-31's native image packaging step, not a boot/CDCI pass.

The producers must be the fixed-point F images in an actual loaderless
selfhost bootstrap receipt. Python starts them and independently inspects
their bytes; it never compiles or packages guest code. No legacy host oracle
is invoked. Complete kernel/ISR/EFI/GPT and QEMU/GOP/input remain separate.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import platform
import struct
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
TARGET = "x86_64-aiueos-kernel-v1"
DATA_SIZE = 77824


def pin(path):
    data = path.read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def verify(blob, fuel):
    """Independent image/entry/context ABI checks, including all zero slots."""
    h = struct.unpack_from("<16sHHIQQQIHHHHHH", blob)
    assert h[:4] == (b"\x7fELF\x02\x01\x01" + bytes(9), 2, 62, 1)
    assert h[4:6] == (0x101000, 64)
    shoff = h[6]
    assert h[7:] == (0, 64, 56, 2, 64, 4, 3)
    ph = [struct.unpack_from("<IIQQQQQQ", blob, 64 + i * 56) for i in range(2)]
    rx, rw = ph
    assert rx[:5] == (1, 5, 4096, 0x101000, 0x101000)
    assert 77 < rx[5] == rx[6] <= 1048576 and rx[7] == 4096
    data, context = rw[2:4]
    assert rw == (1, 6, data, context, context, DATA_SIZE, DATA_SIZE, 4096)
    assert data % 4096 == 0 and data >= 32768 and context == 0x100000 + data
    assert 4096 + rx[5] <= data and data + DATA_SIZE < len(blob)
    sh = [struct.unpack_from("<IIQQQQIIQQ", blob, shoff + i * 64) for i in range(4)]
    assert sh[0] == (0,) * 10
    assert sh[1] == (1, 1, 6, 0x101000, 4096, rx[5], 0, 0, 16, 0)
    assert sh[2] == (7, 1, 3, context, data, DATA_SIZE, 0, 0, 4096, 0)
    names = data + DATA_SIZE
    assert sh[3] == (13, 3, 0, 0, names, 23, 0, 0, 1, 0)
    assert blob[names:names + 23] == b"\0.text\0.data\0.shstrtab\0"
    assert shoff == (names + 30) & -8 and len(blob) == shoff + 256
    assert not any(blob[176:4096]) and not any(blob[4096 + rx[5]:data])
    assert not any(blob[names + 23:shoff])

    # The 77-byte entry shim from the owner ABI: CLI, private stack, GDT,
    # far-return/reload segments, LTR, saved boot-info, r9 context, call/park.
    stack, tss = context + DATA_SIZE, context + 168
    boot = (b"\xfa\x48\x8d\x25" + struct.pack("<i", stack - 0x101008)
            + b"\x48\x83\xe4\xf0\x0f\x01\x15" + struct.pack("<i", context + 152 - 0x101013)
            + bytes.fromhex("6a08488d05030000005048cb66b810008ed88ec08ed031c08ee08ee866b828000f00d8")
            + b"\x48\x89\x3d" + struct.pack("<i", context + 80 - 0x10103d)
            + b"\x4c\x8d\x0d" + struct.pack("<i", context - 0x101044))
    assert len(boot) == 68 and blob[4096:4164] == boot
    assert blob[4164] == 0xe8 and blob[4169:4173] == bytes.fromhex("faf4ebfd")
    entry = 73 + struct.unpack_from("<i", blob, 4165)[0]
    assert 77 <= entry < rx[5] and blob[4096 + entry:4100 + entry] == bytes.fromhex("554889e5")
    expected = bytearray(DATA_SIZE)
    struct.pack_into("<Q", expected, 8, fuel)
    gdt = (0, 0x00af9a000000ffff, 0x00cf92000000ffff, 0x00cff2000000ffff, 0x00affa000000ffff)
    struct.pack_into("<5Q", expected, 96, *gdt)
    expected[136:152] = (struct.pack("<H", 103) + tss.to_bytes(8, "little")[:3]
                         + b"\x89\0" + tss.to_bytes(8, "little")[3:] + bytes(4))
    struct.pack_into("<HQ", expected, 152, 55, context + 96)
    struct.pack_into("<Q", expected, 172, stack)
    struct.pack_into("<H", expected, 270, 104)
    assert blob[data:data + DATA_SIZE] == expected
    return dict(entry=0x101000, textBytes=rx[5], context=context, stackTop=stack,
                fuel=fuel, imports=[], interpreter=None)


def main(build, output):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "arm64"), platform.platform()
    receipt = json.loads((build / "selfhost-bootstrap.json").read_text())
    assert receipt["status"] == "PASS_LOADERLESS_SELFHOST_BOOTSTRAP"
    assert receipt["cCompilerOrLoader"] is False and receipt["JVMNodeOrGraalFallback"] is False
    assert len(receipt["generations"]) >= 2, "need candidate rebuilt to its own fixed point"
    assert receipt["generations"][-1]["image"] == receipt["generations"][-2]["image"]
    for rel, expected in receipt["sourceGraph"]["full"].items():
        assert pin(ROOT / rel) == expected, ("source drift", rel)
    output.mkdir(parents=True, exist_ok=False)
    producers = [build / (g["name"] + ".elf") for g in receipt["generations"][-2:]]
    baseline = build / "root.elf"
    assert pin(baseline) == receipt["root"]["image"]
    spec = importlib.util.spec_from_file_location("object_gate", ROOT / "scripts/seed/check-x86_64-aiueos-object-cfree.py")
    object_gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(object_gate)
    results, parity = [], []
    for producer in producers:
        g = next(g for g in receipt["generations"] if g["name"] == producer.stem)
        assert pin(producer) == g["image"]
        scope = output / producer.stem
        scope.mkdir()
        env = dict(os.environ, KEXE_CAP_RESOURCES_35=str(scope), KEXE_STACK_BYTES="8388608")
        commands, artifacts, refusals = [], {}, []

        def compile_(name, source, kind="image", fuel="1024", extra=(), sentinel=None):
            src, dst = scope / (name + ".kotoba"), scope / (name + ".elf")
            src.write_text(source)
            if sentinel is not None:
                dst.write_bytes(sentinel)
            args = [str(producer), "compile", str(src), "--target", TARGET,
                    "--artifact", kind, "--output", str(dst), "--fuel", fuel, *extra]
            r = subprocess.run(args, env=env, capture_output=True, timeout=120)
            commands.append(dict(name=name, exit=r.returncode, stdout=r.stdout.decode(), stderr=r.stderr.decode()))
            return dst, r

        source = "(ns probe (:export [main]))\n(defn main [] :i64 42)\n"
        loop = ("(ns loop-image (:export [main]))\n"
                "(defn- sum [n :i64 acc :i64] :i64 (if (= n 0) acc (sum (dec n) (+ acc n))))\n"
                "(defn main [] :i64 (sum 100 0))\n")
        for name, text, fuel in [("value", source, 1024), ("calls", loop, 1024),
                                 ("fuel64", source, 3000000000)]:
            dst, r = compile_(name, text, fuel=str(fuel))
            assert r.returncode == 0 and not r.stderr, (name, r.returncode, r.stderr)
            verify(dst.read_bytes(), fuel)
            artifacts[name] = pin(dst)
            # Structural validator must actually reject corrupted output.
            for offset in (4, 24, 68, 120, 4096, 4111, 4164, 32768 + 8, 32768 + 96, 32768 + 152, 32768 + 172, 32768 + 270):
                bad = bytearray(dst.read_bytes())
                bad[offset] ^= 0x80
                try:
                    verify(bad, fuel)
                except (AssertionError, struct.error, OverflowError):
                    pass
                else:
                    raise AssertionError(("validator admitted corruption", name, offset))

        bad_sources = dict(object_gate.SHAPE_REFUSALS)
        bad_sources["nonzero-entry-arity"] = "(ns arg (:export [entry]))\n(defn entry [x :i64] :i64 x)\n"
        for name, text in bad_sources.items():
            dst, r = compile_("refuse-" + name, text)
            assert r.returncode != 0 and not dst.exists(), (name, r.stdout, r.stderr)
            refusals.append(name)
        for name, kind, fuel, extra in [("unknown-artifact", "disk", "1024", ()),
                                       ("zero-fuel", "image", "0", ()),
                                       ("bad-fuel", "image", "10x", ()),
                                       ("module-lock", "image", "1024", ("--module-lock", "no.edn")),
                                       ("source-path", "image", "1024", ("--source-path", "unknown")),
                                       ("format", "image", "1024", ("--format", "static")),
                                       ("duplicate-artifact", "image", "1024", ("--artifact", "object"))]:
            dst, r = compile_("refuse-" + name, source, kind, fuel, extra)
            assert r.returncode != 0 and not dst.exists(), (name, r.stdout, r.stderr)
            refusals.append(name)
        dst, r = compile_("existing", source, sentinel=b"preserve original")
        assert r.returncode != 0 and dst.read_bytes() == b"preserve original"
        refusals.append("existing-output")
        # All object fixtures retain the original ABI with explicit object selection.
        for name, (text, symbol) in object_gate.CASES.items():
            dst, r = compile_("object-" + name, text, "object")
            assert r.returncode == 0 and not r.stderr, (name, r.stderr)
            object_gate.verify_abi(dst.read_bytes(), symbol)
            original = scope / ("baseline-object-" + name + ".o")
            r = subprocess.run([str(baseline), "compile", str(scope / ("object-" + name + ".kotoba")),
                                "--target", TARGET, "--output", str(original), "--fuel", "1024"],
                               env=env, capture_output=True, timeout=120)
            assert r.returncode == 0 and not r.stderr, ("native baseline", name, r.stderr)
            assert original.read_bytes() == dst.read_bytes(), ("object bytes changed", name)
        (scope / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        results.append(dict(producer=pin(producer), artifacts=artifacts, refusals=refusals,
                            objectRegressionCases=len(object_gate.CASES), nativeBaselineByteParity=True))
        parity.append(artifacts)
    assert parity[0] == parity[1], "fixed-point generations disagree on image bytes"
    report = dict(status="PASS_NATIVE_AIUEOS_IMAGE_PACKAGING", host=[platform.system(), platform.machine()],
                  source=receipt["sourceGraph"]["full"], routes=results,
                  cCompilerOrLoader=False, JVMNodeOrGraalFallback=False, emulation=False,
                  legacyOwnerOracle="unavailable in permitted native closure; ABI inspected independently",
                  wholeKernel=False, efi=False, gpt=False, qemuBoot=False, nativeCDCI=False)
    (output / "native-image.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], sum(len(r["artifacts"]) for r in results), "images; complete kernel/EFI/boot open")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--build", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    main(a.build.resolve(), a.output.resolve())
