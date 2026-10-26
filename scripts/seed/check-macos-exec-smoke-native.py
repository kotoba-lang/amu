#!/usr/bin/env python3
"""Build and execute the bounded Darwin probe using only the Mac native root.

Python stages bytes and observes native Amu, the native Kotoba packager and
platform signing/inspection tools. No Linux, assembler or hosted compiler.
This diagnostic does not qualify the complete Darwin runtime or a release.
"""
import argparse
import importlib.util
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(file))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main(mac_build, out):
    gate = module("mac_native", "check-aiueos-user-macos-native.py")
    observer = module("mac_smoke", "check-macos-exec-smoke.py")
    report_path = mac_build / "mac-aiueos-user-target.json"
    descriptor_path = ROOT / "seed/bootstrap/aarch64-macos/root.json"
    report_pin, descriptor_pin = gate.pin(report_path), gate.pin(descriptor_path)
    report = json.loads(report_path.read_text())
    descriptor = json.loads(descriptor_path.read_text())
    assert report["status"] == "PASS_MAC_NATIVE_USER_TARGET_SELFHOST"
    assert report["bootstrapDescriptor"] == descriptor_pin
    assert report["source"] == descriptor["fullSource"]
    row = report["generations"][-1]
    producer = mac_build / f"F{row['number']}-signed.macho"
    packager = ROOT / descriptor["packager"]["path"]
    assert gate.verify_macho(producer) == row["signed"]
    assert gate.verify_macho(packager) == {
        key: descriptor["packager"][key] for key in ("bytes", "sha256")}
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    source = ROOT / "seed/macos-exec-smoke.kotoba"
    source_pin = gate.pin(source)
    shutil.copyfile(source, out / "probe.kotoba")
    gate.native_run(producer, out, "compile", "probe.kotoba", "--target", "aarch64-macos", "--output", "probe.kseed")
    extracted = gate.native_run(producer, out, "extract-native", "probe.kseed", "--symbol", "main", "--output", "probe.raw")
    match = re.search(rb":offset (\d+), :length (\d+), :arity 0}", extracted.stdout)
    assert match and int(match.group(2)) == (out / "probe.raw").stat().st_size
    gate.native_run(packager, out, "probe-unsigned.macho", "probe.raw", "fs2-cli-stdio-general", match.group(1).decode())
    emitter = out / "probe-signed.macho"
    gate.sign(out / "probe-unsigned.macho", emitter)
    gate.native_run(emitter, out, "smoke-unsigned.macho")
    gate.native_run(emitter, out, "smoke-repeat.macho")
    assert (out / "smoke-unsigned.macho").read_bytes() == (out / "smoke-repeat.macho").read_bytes()
    gate.native_run(emitter, out, "", expected=2)
    assert gate.pin(source) == source_pin
    observed = observer.check(out / "smoke-unsigned.macho", out / "execution")
    assert gate.verify_macho(producer) == row["signed"]
    assert gate.pin(packager) == {key: descriptor["packager"][key] for key in ("bytes", "sha256")}
    assert gate.pin(source) == source_pin
    assert gate.pin(report_path) == report_pin and gate.pin(descriptor_path) == descriptor_pin
    result = dict(schema="amu.mac-native-exec-smoke.v1", status="PASS_MAC_NATIVE_EXEC_SMOKE",
                  bootstrapReport=report_pin, bootstrapDescriptor=descriptor_pin,
                  observer=gate.pin(Path(__file__)),
                  compiler=gate.pin(producer), packager=gate.pin(packager),
                  source=source_pin, emitter=gate.pin(emitter),
                  image=gate.pin(out / "smoke-unsigned.macho"), observation=observed,
                  repeatByteIdentical=True, emptyOutputPathRefused=True,
                  linuxProcessInThisGate=False, fullRuntimeQualified=False)
    (out / "native-smoke.json").write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"], result["image"]["sha256"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mac-build", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.mac_build.resolve(), a.output.resolve())
