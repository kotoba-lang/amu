#!/usr/bin/env python3
"""Rebuild the selected 19-module core from the signed Mac Amu fixed point."""

import argparse
import importlib.util
import json
import platform
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def mac_gate():
    path = Path(__file__).with_name("check-aiueos-user-macos-native.py")
    spec = importlib.util.spec_from_file_location("mac_native_gate", path)
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    return gate


def main(mac_build, output):
    if platform.system() != "Darwin" or platform.machine() not in ("arm64", "aarch64"):
        raise ValueError("native Apple Silicon required")
    gate = mac_gate()
    descriptor_path = ROOT / "seed/bootstrap/aarch64-macos/root.json"
    descriptor = json.loads(descriptor_path.read_text())
    report_path = mac_build / "mac-aiueos-user-target.json"
    report = json.loads(report_path.read_text())
    if (report.get("status") != "PASS_MAC_NATIVE_USER_TARGET_SELFHOST" or
            report.get("bootstrapDescriptor") != gate.pin(descriptor_path) or
            report.get("source") != descriptor["fullSource"]):
        raise ValueError("Mac source fixed point is not bound to this descriptor")
    final = report["generations"][-1]
    producer = mac_build / f"F{final['number']}-signed.macho"
    if gate.verify_macho(producer) != final["signed"]:
        raise ValueError("Mac compiler changed")
    packager = ROOT / descriptor["packager"]["path"]
    if gate.verify_macho(packager) != {k: descriptor["packager"][k] for k in ("bytes", "sha256")}:
        raise ValueError("Mac packager changed")
    core = json.loads((ROOT / "seed/compiler-core.json").read_text())
    adoption_path = ROOT / core["adoptionReceipt"]
    adoption = json.loads(adoption_path.read_text())
    if adoption["sourceManifest"] != "seed/MANIFEST":
        raise ValueError("wrong core manifest")
    names = [name for name in (ROOT / adoption["sourceManifest"]).read_text().splitlines()
             if name and not name.startswith("#")]
    if len(names) != 19 or len(names) != len(set(names)) or "seed/19-decimal.kotoba" not in names:
        raise ValueError("core manifest must contain 19 unique modules including decimal")
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    sources = []
    with (output / "adopted-unity.kotoba").open("wb") as stream:
        for name in names:
            path = Path(name)
            if path.is_absolute() or ".." in path.parts or path.parts[0] != "seed":
                raise ValueError("invalid core source path")
            source = ROOT / path
            sources.append({"path": name, **gate.require_regular(source)})
            stream.write(source.read_bytes() + b"\n")
    unity = gate.pin(output / "adopted-unity.kotoba")
    if (sources != adoption["sources"] or sources != core["sources"] or
            unity != {"bytes": adoption["sourceUnityBytes"],
                      "sha256": adoption["sourceUnitySHA256"]} or
            unity != {"bytes": core["sourceUnityBytes"],
                      "sha256": core["sourceUnitySHA256"]}):
        raise ValueError("selected core source drift")
    generations = []
    current = producer
    for number in (1, 2, 3):
        container = output / f"G{number}.kseed"
        raw = output / f"G{number}.bin"
        unsigned = output / f"G{number}-unsigned.macho"
        signed = output / f"G{number}-signed.macho"
        gate.native_run(current, output, "compile", "adopted-unity.kotoba",
                        "--target", "aarch64-macos", "--output", container.name)
        extracted = gate.native_run(current, output, "extract-native", container.name,
                                    "--symbol", "main", "--output", raw.name)
        match = re.search(rb":offset (\d+), :length (\d+), :arity 0}", extracted.stdout)
        if match is None or int(match.group(2)) != raw.stat().st_size:
            raise ValueError("core main extraction mismatch")
        gate.native_run(packager, output, unsigned.name, raw.name,
                        "fs2-cli-stdio-general", match.group(1).decode())
        gate.sign(unsigned, signed)
        row = {"name": f"G{number}", "native": gate.pin(raw),
               "container": gate.pin(container)}
        if row != adoption["generations"][number - 1]:
            raise ValueError("core generation differs from selected adoption")
        generations.append(row)
        current = signed
    if not all(row["native"] == generations[0]["native"] and
               row["container"] == generations[0]["container"] for row in generations):
        raise ValueError("core source fixed point absent")
    if (generations[0]["native"] != {"bytes": adoption["nativeImageBytes"],
                                      "sha256": adoption["nativeImageSHA256"]} or
            generations[0]["container"] != adoption["container"] or
            gate.verify_macho(producer) != final["signed"] or
            gate.pin(descriptor_path) != report["bootstrapDescriptor"]):
        raise ValueError("core output or producer changed")
    receipt = {"schema": "amu.mac-core-adoption.v1", "status": "PASS_MAC_CORE_ADOPTION_FIXED_POINT",
               "bootstrapReport": gate.pin(report_path), "adoption": gate.pin(adoption_path),
               "sourceUnity": unity, "generations": generations,
               "nativeLinuxQualified": False, "coldC0Qualified": False,
               "observer": gate.pin(Path(__file__))}
    (output / "mac-core-adoption.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["status"], unity["sha256"], generations[0]["native"]["sha256"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mac-build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.mac_build.resolve(), args.output.resolve())
