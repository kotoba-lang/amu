#!/usr/bin/env python3
"""Cross-build Linux compiler candidates from the Mac native Amu fixed point.

This is a Mac producer gate. It does not execute or qualify the Linux images.
Python stages source bytes, checks identities, and observes native Amu calls.

By default the candidates must equal the checked-in root and public images, so
a source change is refused here as stale. --produce-candidates is for adopting
such a change: it skips that comparison, records the receipt status
MAC_NATIVE_CROSS_CANDIDATES_UNADOPTED, and leaves every descriptor and image
untouched. write-bootstrap-descriptors.py turns that receipt into the new pins.
"""

import argparse
import hashlib
import importlib.util
import json
import platform
import shutil
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAC_GATE = Path(__file__).with_name("check-aiueos-user-macos-native.py")
DESCRIPTOR = ROOT / "seed/bootstrap/aarch64-macos/root.json"
FULL = ROOT / "seed/FULL-MANIFEST"
SELFHOST = ROOT / "seed/X86_64-LINUX-SELFHOST-MANIFEST"
RUNNER = ROOT / "seed/x86_64-kx64-runner.kotoba"
PRODUCT = ROOT / "native-product.json"
ARM_ROOT = ROOT / "seed/bootstrap/aarch64-linux-static-root.json"
ARM_IMAGE = ROOT / "seed/bootstrap/aarch64-linux-static-root.elf"
X86_IMAGE = ROOT / "bin/amu-linux-x86_64"


def module():
    spec = importlib.util.spec_from_file_location("mac_native_gate", MAC_GATE)
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    return gate


def pin(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def stage(manifest, output):
    names = [name for name in manifest.read_text().splitlines()
             if name and not name.startswith("#")]
    if not names or len(names) != len(set(names)):
        raise ValueError("empty or duplicate manifest entries")
    with output.open("wb") as stream:
        for name in names:
            part = Path(name)
            if (part.is_absolute() or ".." in part.parts or
                    not part.parts or part.parts[0] != "seed"):
                raise ValueError("invalid manifest source path")
            source = ROOT / part
            if source.is_symlink() or not source.is_file():
                raise ValueError("manifest source must be a regular file")
            stream.write(source.read_bytes() + b"\n")
    return {"modules": len(names), "manifest": pin(manifest), "unity": pin(output)}


def static_elf(path, machine):
    raw = path.read_bytes()
    if raw[:8] != b"\x7fELF\x02\x01\x01\0" or struct.unpack_from("<HH", raw, 16) != (2, machine):
        raise ValueError("wrong static ELF target: " + path.name)
    offset = struct.unpack_from("<Q", raw, 32)[0]
    size, count = struct.unpack_from("<HH", raw, 54)
    if size != 56 or not 0 < count <= 16 or offset + count * size > len(raw):
        raise ValueError("invalid ELF program headers: " + path.name)
    types = [struct.unpack_from("<I", raw, offset + i * size)[0] for i in range(count)]
    if 2 in types or 3 in types:
        raise ValueError("dynamic image or interpreter: " + path.name)
    return pin(path)


def check_product_bindings(full, arm, x86):
    """Refuse stale checked-in images before the costly native ISA gates."""
    product = json.loads(PRODUCT.read_text())
    root = json.loads(ARM_ROOT.read_text())
    if (full["unity"] != product["sourceUnity"] or
            full["unity"] != root["sourceUnity"] or
            full["modules"] != product["sourceModuleCount"] or
            product["sourceManifest"] != "seed/FULL-MANIFEST" or
            root["sourceManifest"] != "seed/FULL-MANIFEST"):
        raise ValueError("Mac candidate source differs from root/product descriptors")
    if arm != root["image"] or arm != product["rootImage"] or arm != pin(ARM_IMAGE):
        raise ValueError("Mac ARM fixed point differs from checked-in root image")
    if x86 != product["image"] or x86 != pin(X86_IMAGE):
        raise ValueError("Mac x86 fixed point differs from checked-in public image")


def main(mac_build, output, produce=False):
    if platform.system() != "Darwin" or platform.machine() not in ("arm64", "aarch64"):
        raise ValueError("Apple Silicon native host required")
    if mac_build.is_symlink() or not mac_build.is_dir():
        raise ValueError("regular Mac build directory required")
    gate = module()
    descriptor = json.loads(DESCRIPTOR.read_text())
    report_path = mac_build / "mac-aiueos-user-target.json"
    report = json.loads(report_path.read_text())
    if (report.get("status") != "PASS_MAC_NATIVE_USER_TARGET_SELFHOST" or
            report.get("bootstrapDescriptor") != pin(DESCRIPTOR) or
            report.get("source") != descriptor["fullSource"] or
            report.get("fixedPointGeneration") != len(report["generations"]) or
            len(report["generations"]) < 2):
        raise ValueError("Mac selfhost report is not bound to this source and root")
    final, previous = report["generations"][-1], report["generations"][-2]
    if any(final[key] != previous[key] for key in ("container", "raw", "unsigned")):
        raise ValueError("Mac compiler source fixed point is absent")
    producer = mac_build / f"F{final['number']}-signed.macho"
    if gate.verify_macho(producer) != final["signed"]:
        raise ValueError("Mac fixed-point image changed")

    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    full = stage(FULL, output / "full-unity.kotoba")
    selfhost = stage(SELFHOST, output / "selfhost-unity.kotoba")
    if full["unity"] != report["source"]:
        raise ValueError("current full source differs from Mac gate")
    shutil.copyfile(RUNNER, output / "runner.kotoba")
    runner = pin(output / "runner.kotoba")

    gate.native_run(producer, output, "compile", "full-unity.kotoba",
                    "--target", "aarch64-macos", "--output", "F.kseed")
    container = pin(output / "F.kseed")
    if container["sha256"] != descriptor["expectedFixedPoint"]["compilerContainerSha256"]:
        raise ValueError("Mac producer changed the full compiler container")
    gate.native_run(producer, output, "compile", "runner.kotoba",
                    "--target", "aarch64-linux", "--output", "F-aarch64.elf",
                    "--format", "packed", "--payload", "F.kseed")
    arm = static_elf(output / "F-aarch64.elf", 183)
    gate.native_run(producer, output, "compile", "full-unity.kotoba",
                    "--target", "x86_64-linux", "--output", "F-x86_64.elf",
                    "--format", "static")
    x86 = static_elf(output / "F-x86_64.elf", 62)
    if not produce:
        check_product_bindings(full, arm, x86)
    gate.native_run(producer, output, "compile", "selfhost-unity.kotoba",
                    "--target", "x86_64-linux", "--output", "S-x86_64.elf",
                    "--format", "static")
    x86_selfhost = static_elf(output / "S-x86_64.elf", 62)
    if gate.verify_macho(producer) != final["signed"] or pin(DESCRIPTOR) != report["bootstrapDescriptor"]:
        raise ValueError("Mac producer inputs changed during cross build")
    report = {"schema": "amu.mac-cross-linux-candidates.v1",
              "status": ("MAC_NATIVE_CROSS_CANDIDATES_UNADOPTED" if produce
                         else "MAC_NATIVE_CROSS_ARTIFACTS_UNEXECUTED"),
              "macSelfhostReport": pin(report_path), "producer": final["signed"],
              "fullSource": full, "selfhostSource": selfhost, "runnerSource": runner,
              "container": container, "aarch64Root": arm,
              "x86FullCompiler": x86, "x86SelfhostCompiler": x86_selfhost,
              "linuxProcessInThisGate": False, "nativeLinuxExecutionQualified": False,
              "observer": pin(Path(__file__))}
    (output / "cross.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], arm["sha256"], x86["sha256"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mac-build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--produce-candidates", action="store_true",
                        help="skip the comparison with the checked-in images (adopting a source change)")
    args = parser.parse_args()
    main(args.mac_build.resolve(), args.output.resolve(), args.produce_candidates)
