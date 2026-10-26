#!/usr/bin/env python3
"""Check the bounded Amu user-v3 syscall ELF with a pinned Mac selfhost image.

This checks compiler isolation and ELF bytes. Guest behavior has a separate
AIUEOS QEMU gate; this script does not claim an Itonami turn.
"""

import argparse
import importlib.util
import json
from pathlib import Path
import struct


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / "seed/tests/aiueos-user-v3-local-model.kotoba"
TRAMPOLINE = bytes.fromhex("b8050000004883ec080f054883c408c3")
ELF_SHA256 = "108174e896008ac4b523450acd57d16b2b37ba3eb31f6b21d3ad3874344ca4ec"
LLM_SOURCE = """(ns aiueos-user-v3-llm (:export [main]))
(defn main [request :i64 request-bytes :i64] :i64
  (llm/generate request))
"""
LLM_DECLARED_SOURCE = """(ns aiueos-user-v3-llm
  (:export [main])
  (:capabilities #{:llm/generate}))
(defn main [request :i64 request-bytes :i64] :i64
  (llm/generate request))
"""


def load_mac():
    spec = importlib.util.spec_from_file_location(
        "mac_user_gate", HERE / "check-aiueos-user-macos-native.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(data):
    if len(data) != 8280 or data[:4] != b"\x7fELF":
        raise ValueError("wrong user-v3 ELF size or header")
    if struct.unpack_from("<Q", data, 24)[0] != 0x220000:
        raise ValueError("wrong user-v3 entry")
    if struct.unpack_from("<Q", data, 64 + 32)[0] != 478:
        raise ValueError("wrong user-v3 executable extent")
    if struct.unpack_from("<Q", data, 120 + 40)[0] != 320:
        raise ValueError("wrong user-v3 writable extent")
    if data[4096 + 48:4096 + 64] != TRAMPOLINE:
        raise ValueError("syscall trampoline did not align the stack")
    if (struct.unpack_from("<Q", data, 8192 + 8)[0] != 256
            or struct.unpack_from("<Q", data, 8192 + 48)[0] != 0x220030
            or any(data[8192:8192 + 8])
            or any(data[8192 + 16:8192 + 48])
            or any(data[8192 + 56:8280])):
        raise ValueError("user-v3 ELF has unexpected initial context")


def main(args):
    mac = load_mac()
    if args.mac_build:
        if args.compiler_image or args.compiler_sha256:
            raise ValueError("choose the Mac build receipt or an explicit compiler pin")
        build = args.mac_build.resolve(strict=True)
        receipt = build / "mac-aiueos-user-target.json"
        mac.require_regular(receipt)
        root = json.loads((HERE.parents[1] / "seed/bootstrap/aarch64-macos/root.json").read_text())
        report = json.loads(receipt.read_text())
        generations = report.get("generations", [])
        if (report.get("status") != "PASS_MAC_NATIVE_USER_TARGET_SELFHOST"
                or report.get("source") != root["fullSource"]
                or len(generations) < 2
                or generations[-1]["container"] != generations[-2]["container"]
                or generations[-1]["container"]["sha256"] !=
                root["expectedFixedPoint"]["compilerContainerSha256"]):
            raise ValueError("Mac root receipt does not bind the current fixed point")
        compiler = build / f"F{generations[-1]['number']}-signed.macho"
        compiler_pin = mac.require_regular(compiler, generations[-1]["signed"]["sha256"])
        if compiler_pin != generations[-1]["signed"]:
            raise ValueError("Mac root compiler size changed")
    else:
        if not args.compiler_image or not args.compiler_sha256:
            raise ValueError("explicit compiler requires path and SHA-256 pin")
        compiler = args.compiler_image.resolve(strict=True)
        compiler_pin = mac.require_regular(compiler, args.compiler_sha256)
    mac.verify_macho(compiler)
    source_pin = mac.require_regular(SOURCE)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = output / "user.kotoba"
    source.write_bytes(SOURCE.read_bytes())
    results = []
    for name in ("user.elf", "user.reproduced.elf"):
        mac.native_run(compiler, output, "compile", source.name,
                       "--target", "x86_64-aiueos-user-v3", "--output", name)
        result = output / name
        verify(result.read_bytes())
        identity = mac.pin(result)
        if identity["sha256"] != ELF_SHA256:
            raise ValueError("user-v3 ELF changed from the pinned guest image")
        results.append(identity)
    if results[0] != results[1]:
        raise ValueError("user-v3 native build was not reproducible")
    refused = mac.native_run(compiler, output, "compile", source.name,
                             "--target", "x86_64-aiueos-user-v2",
                             "--output", "forbidden-v2.elf", expected=1)
    if (output / "forbidden-v2.elf").exists() or not refused.stderr:
        raise ValueError("v2 target accepted the v3-only operation")
    # Preserve the measured gap as a fail-closed baseline. This is not a kit
    # qualification: the target still lacks a typed request/result ABI and a
    # declared-capability manifest. JUN-444 must replace both refusals with
    # a positive whole-kit gate when that path is implemented.
    llm_refusals = {}
    for name, text, diagnostic in (
            ("llm-undeclared", LLM_SOURCE, b"E2115"),
            ("llm-declared", LLM_DECLARED_SOURCE, b"E2004")):
        candidate = output / (name + ".kotoba")
        artifact = output / (name + ".elf")
        candidate.write_text(text)
        result = mac.native_run(compiler, output, "compile", candidate.name,
                                "--target", "x86_64-aiueos-user-v3",
                                "--output", artifact.name, expected=1)
        if diagnostic not in result.stderr or artifact.exists():
            raise ValueError(f"{name} did not refuse without an ELF")
        llm_refusals[name] = {"source": mac.pin(candidate),
                              "diagnostic": diagnostic.decode(),
                              "artifactAbsent": True}
    if mac.pin(source) != source_pin or mac.pin(compiler) != compiler_pin:
        raise ValueError("qualification inputs changed")
    report = {"schema": "amu.mac-aiueos-user-v3-local-call.v1",
              "status": "PASS_MAC_NATIVE_USER_V3_LOCAL_CALL_ELF",
              "compiler": compiler_pin, "source": source_pin,
              "elf": results[0], "reproducedElf": results[1],
              "v2Refusal": True, "llmKitRefusals": llm_refusals,
              "observer": mac.pin(Path(__file__)),
              "guestExecution": False, "externalOperation": False,
              "agentLoop": False, "linuxProcessInThisGate": False}
    (output / "mac-aiueos-user-v3-local-call.json").write_text(
        json.dumps(report, indent=2) + "\n")
    print(report["status"], ELF_SHA256, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mac-build", type=Path)
    parser.add_argument("--compiler-image", type=Path)
    parser.add_argument("--compiler-sha256")
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
