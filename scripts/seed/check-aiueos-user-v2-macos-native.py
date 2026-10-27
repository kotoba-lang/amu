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

    slot_names = ("v2-goal-slot.bin", "v2-goal-slot.reproduced.bin")
    for name in slot_names:
        mac.native_run(compiler, output, "package-aiueos-user-payload",
                       "v2-goal.elf", "--output", name, "--version", "v2")
    slot = (output / slot_names[0]).read_bytes()
    goal_elf = (output / "v2-goal.elf").read_bytes()
    if (len(slot) != 524288
            or struct.unpack_from("<QQQ", slot) != (0x0031444c50554941, 2, len(goal_elf))
            or slot[64:64 + len(goal_elf)] != goal_elf
            or any(slot[64 + len(goal_elf):])
            or slot != (output / slot_names[1]).read_bytes()
            or mac.pin(output / slot_names[0])["sha256"] !=
            "b88caa63c3b782a550f4aefdb84e8ad47be0c6f578cb58352a50573bc05e9b23"):
        raise ValueError("native v2 slot disagrees with the pinned guest fixture")
    slot_refusals = {}
    malformed = bytearray(goal_elf)
    malformed[24] ^= 1
    (output / "v2-wrong-entry.elf").write_bytes(malformed)
    for name, source, version, code in (
            ("wrong-entry", "v2-wrong-entry.elf", "v2", "E7111"),
            ("wrong-version", "v2-goal.elf", "v3", "E7110")):
        destination = f"v2-{name}-slot.bin"
        refused = mac.native_run(compiler, output, "package-aiueos-user-payload",
                                 source, "--output", destination, "--version", version,
                                 expected=1 if name == "wrong-entry" else 2)
        if code.encode() not in refused.stderr or (output / destination).exists():
            raise ValueError(f"v2 slot {name} did not refuse before output")
        slot_refusals[name] = {"error": code, "artifactAbsent": True}
    existing = mac.native_run(compiler, output, "package-aiueos-user-payload",
                              "v2-goal.elf", "--output", slot_names[0],
                              "--version", "v2", expected=2)
    if b"E7110" not in existing.stderr:
        raise ValueError("v2 slot packager overwrote an existing output")
    slot_refusals["existing-output"] = {"error": "E7110", "artifactAbsent": False}

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
              "userSlot": mac.pin(output / slot_names[0]),
              "userSlotReproduced": mac.pin(output / slot_names[1]),
              "userSlotRefusals": slot_refusals,
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
