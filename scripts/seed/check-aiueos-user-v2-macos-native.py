#!/usr/bin/env python3
"""Build Amu to a Mac native fixed point, then check user-v2 Goal ELFs.

Python stages and observes; the signed Amu images compile every Kotoba source
and emit every ELF. This gate does not claim an AIUEOS guest or Itonami turn.
"""

import argparse
import importlib.util
import json
from pathlib import Path
import struct


HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(args):
    mac_path = HERE / "check-aiueos-user-macos-native.py"
    v2_path = HERE / "check-aiueos-user-v2-native.py"
    mac = load("mac_user_gate", mac_path)
    v2 = load("v2_user_gate", v2_path)
    v2_pin = mac.require_regular(v2_path)
    mac.main(args)
    output = args.output.resolve()
    v1_receipt = output / "mac-aiueos-user-target.json"
    v1 = json.loads(v1_receipt.read_text())
    if v1["status"] != "PASS_MAC_NATIVE_USER_TARGET_SELFHOST":
        raise ValueError("v1 Mac native fixed point was not verified")
    compiler = output / f"F{v1['fixedPointGeneration']}-signed.macho"
    if mac.pin(compiler) != v1["generations"][-1]["signed"]:
        raise ValueError("fixed-point compiler digest mismatch")

    positives = {}
    for name, source in (("goal", v2.SOURCE), ("constant", v2.CONSTANT)):
        src, elf = output / f"v2-{name}.kotoba", output / f"v2-{name}.elf"
        src.write_text(source)
        mac.native_run(compiler, output, "compile", src.name, "--target", v2.TARGET,
                       "--output", elf.name)
        v2.verify(elf.read_bytes())
        positives[name] = {"source": mac.pin(src), "elf": mac.pin(elf)}

    # The verifier must reject a different memory contract and an embedded
    # nonzero context, rather than merely recognizing its positive image.
    mutation = bytearray((output / "v2-goal.elf").read_bytes())
    struct.pack_into("<Q", mutation, 120 + 40, 321)
    try:
        v2.verify(mutation)
    except ValueError:
        pass
    else:
        raise ValueError("wrong v2 request region size was accepted")
    mutation = bytearray((output / "v2-goal.elf").read_bytes())
    mutation[8192 + 24] = 1
    try:
        v2.verify(mutation)
    except ValueError:
        pass
    else:
        raise ValueError("nonzero embedded context was accepted")

    refusals = {}
    for name, (source, code) in v2.REFUSALS.items():
        src, elf = output / f"v2-{name}.kotoba", output / f"v2-{name}.elf"
        src.write_text(source)
        refused = mac.native_run(compiler, output, "compile", src.name,
                                 "--target", v2.TARGET, "--output", elf.name,
                                 expected=1)
        if code.encode() not in refused.stderr or elf.exists():
            raise ValueError(f"v2 {name} did not refuse with {code} and no artifact")
        refusals[name] = {"source": mac.pin(src), "error": code,
                          "artifactAbsent": True}

    if mac.pin(v2_path) != v2_pin or mac.pin(compiler) != v1["generations"][-1]["signed"]:
        raise ValueError("v2 gate input changed during qualification")
    report = {"schema": "amu.mac-aiueos-user-v2-goal.v1",
              "status": "PASS_MAC_NATIVE_USER_V2_GOAL_ELF",
              "v1FixedPointReceipt": mac.pin(v1_receipt),
              "fixedPointGeneration": v1["fixedPointGeneration"],
              "compiler": mac.pin(compiler), "source": v1["source"],
              "checker": v2_pin, "observer": mac.pin(Path(__file__)),
              "target": v2.TARGET, "positives": positives, "refusals": refusals,
              "regionMutationRejected": True, "contextMutationRejected": True,
              "guestExecution": False, "ItonamiTurn": False,
              "releaseAdmission": False, "linuxProcessInThisGate": False}
    (output / "mac-aiueos-user-v2-goal.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], positives["goal"]["elf"]["sha256"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler-image", type=Path, required=True)
    parser.add_argument("--compiler-sha256", required=True)
    parser.add_argument("--packager-image", type=Path, required=True)
    parser.add_argument("--packager-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
