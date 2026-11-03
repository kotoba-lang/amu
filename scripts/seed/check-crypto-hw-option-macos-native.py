#!/usr/bin/env python3
"""Check the SHA-256 crypto-hardware compile option on the signed Mac Amu (JUN-578).

An ordinary compile uses the ARMv8 SHA-256 instructions for the certified sha256 shape; `compile --no-crypto-hw`
selects the scalar paths. Both builds must give the exact digest, a changed expected byte must fail in both, the flag
must be refused by `check`, and the instruction counts must differ in the documented direction.
"""

import argparse
import json
import platform
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PORT = ROOT / "bench/embench/reproduce-20261015/ports/official-nettle-sha256.kotoba"
FIRST_BYTE = "(if (= i 0) 36 (if (= i 1) 141"
MASKS = {"sha256h": (0xFFE0FC00, 0x5E004000), "sha256h2": (0xFFE0FC00, 0x5E005000),
         "sha256su1": (0xFFE0FC00, 0x5E006000), "sha256su0": (0xFFFFFC00, 0x5E282800)}


def mac_gate():
    import importlib.util
    path = Path(__file__).with_name("check-aiueos-user-macos-native.py")
    spec = importlib.util.spec_from_file_location("mac_native_gate", path)
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    return gate


def instruction_counts(kseed):
    native = kseed.read_bytes().split(b"\n\n", 1)[1]
    words = struct.unpack(f"<{len(native) // 4}I", native[:len(native) // 4 * 4])
    return {name: sum((word & mask) == value for word in words) for name, (mask, value) in MASKS.items()}


def main(mac_build, output):
    if platform.system() != "Darwin" or platform.machine() not in ("arm64", "aarch64"):
        raise ValueError("native Apple Silicon required")
    gate = mac_gate()
    report = json.loads((mac_build / "mac-aiueos-user-target.json").read_text())
    final = report["generations"][-1]
    compiler = mac_build / f"F{final['number']}-signed.macho"
    if gate.verify_macho(compiler) != final["signed"]:
        raise ValueError("Mac compiler changed")
    descriptor = json.loads((ROOT / "seed/bootstrap/aarch64-macos/root.json").read_text())
    packager = ROOT / descriptor["packager"]["path"]
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    port = PORT.read_text()
    if port.count(FIRST_BYTE) != 1 or "(:export [bench observe" not in port:
        raise ValueError("port shape changed")
    port = port.replace("(:export [bench observe", "(:export [main bench observe", 1)
    good = port + "\n(defn main [] :i64 (+ (bench 5) (* 10 (bench 1))))\n"
    cases = {"good": good, "bad": good.replace(FIRST_BYTE, FIRST_BYTE.replace("36", "37", 1), 1)}
    expected = {"good": 11, "bad": 0}
    counts = {}
    for label, source in cases.items():
        (output / f"{label}.kotoba").write_text(source)
        for mode, flags in (("hw", []), ("scalar", ["--no-crypto-hw"])):
            tag = f"{label}-{mode}"
            gate.native_run(compiler, output, "compile", f"{label}.kotoba", "--target", "aarch64-macos",
                            *flags, "--output", f"{tag}.kseed")
            extracted = gate.native_run(compiler, output, "extract-native", f"{tag}.kseed", "--symbol", "main",
                                        "--output", f"{tag}.raw")
            match = re.search(rb":offset (\d+), :length (\d+), :arity 0}", extracted.stdout)
            if match is None or int(match.group(2)) != (output / f"{tag}.raw").stat().st_size:
                raise ValueError("main extraction mismatch: " + tag)
            gate.native_run(packager, output, f"{tag}-unsigned", f"{tag}.raw", "fs2-cli-stdio-general",
                            match.group(1).decode())
            gate.sign(output / f"{tag}-unsigned", output / tag)
            gate.native_run(output / tag, output, expected=expected[label])
            if label == "good":
                counts[mode] = instruction_counts(output / f"{tag}.kseed")
    if any(count == 0 for count in counts["hw"].values()) or any(counts["scalar"].values()):
        raise ValueError(f"instruction counts not as documented: {counts}")
    gate.native_run(compiler, output, "check", "good.kotoba", "--no-crypto-hw", expected=2)
    receipt = {"schema": "amu.mac-crypto-hw-option.v1", "status": "PASS_MAC_CRYPTO_HW_OPTION",
               "compiler": final["signed"], "sha256InstructionCounts": counts,
               "digestExactBothModes": True, "negativeControlFailsBothModes": True,
               "checkWithFlagRefused": True, "nativeLinuxQualified": False,
               "observer": gate.pin(Path(__file__))}
    (output / "mac-crypto-hw-option.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["status"], json.dumps(counts), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mac-build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.mac_build.resolve(), args.output.resolve())
