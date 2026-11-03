#!/usr/bin/env python3
"""Stage pure-i64 frontend observations for an Amu-native ordered verdict.

The compiler validates programs. Python stages the existing literal corpus,
starts processes and transports observations; the generated Kotoba gate owns
the comparison and its corrupted-observation negative control.
"""
import argparse
import hashlib
import importlib.util
import json
import platform
import shutil
import struct
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("i64_vectors", Path(__file__).with_name("check-kototama-i64.py"))
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
PROFILES = ("kototama.pure-i64-aot/v1", "kototama.pure-i64-receipt/v2")
OK = b"{:ok true, :phase :pure-i64-frontend-check, :authority :none}\n"
SKIP = {"zero-fuel", "negative-fuel", "too-much-fuel", "unknown-profile",
        "unsupported-target", "unknown-flag", "existing-output"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--compiler", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    machine = platform.machine()
    if platform.system() != "Linux" or machine not in ("aarch64", "arm64", "x86_64"):
        raise SystemExit("native Linux arm64/x86_64 required; no emulation")
    target = "aarch64-linux" if machine in ("aarch64", "arm64") else "x86_64-linux"
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    compiler = out / "compiler.elf"
    shutil.copy2(args.compiler, compiler)
    compiler.chmod(0o755)
    env = {"PATH": "/nonexistent", "KEXE_CAP_RESOURCES_35": str(out), "KEXE_STACK_BYTES": "8388608"}
    cases = [case for case in v.vectors() if case["name"] not in SKIP]
    observations, expected, records = [], [], []

    for i, case in enumerate(cases):
        source = out / f"{i:03d}.cbor"
        source.write_bytes(case["wire"])
        for profile in PROFILES:
            before = {path.name for path in out.iterdir()}
            result = subprocess.run([str(compiler), "check-kototama", str(source), "--profile", profile],
                                    env=env, capture_output=True, timeout=120)
            accepted = case["outcome"] != "refuse"
            observations.extend([result.returncode, len(result.stdout), int(result.stdout == OK),
                                 int(bool(result.stderr)), int(source.read_bytes() == case["wire"]),
                                 int(before == {path.name for path in out.iterdir()})])
            expected.extend([0 if accepted else 1, len(OK) if accepted else 0,
                             1 if accepted else 0, 0 if accepted else 1, 1, 1])
            records.append({"case": case["name"], "profile": profile,
                            "inputSHA256": hashlib.sha256(case["wire"]).hexdigest(),
                            "exit": result.returncode, "stdoutBytes": len(result.stdout),
                            "stderrBytes": len(result.stderr)})

    # Command-line refusals are independent of the input's validity.
    source = out / "000.cbor"
    for name, extra in [("missing-profile", []), ("wrong-flag", ["--wrong", PROFILES[0]]),
                        ("unknown-profile", ["--profile", "unknown"]),
                        ("extra-flag", ["--profile", PROFILES[0], "--unknown"])]:
        result = subprocess.run([str(compiler), "check-kototama", str(source), *extra],
                                env=env, capture_output=True, timeout=120)
        observations.extend([result.returncode, len(result.stdout), int(bool(result.stderr))])
        expected.extend([1, 0, 1])
        records.append({"case": name, "exit": result.returncode,
                        "stdoutBytes": len(result.stdout), "stderrBytes": len(result.stderr)})

    empty = out / "empty.cbor"
    empty.write_bytes(b"")
    narrow = out / "narrow-scope"
    narrow.mkdir(mode=0o700)
    for name, path, scoped in [("empty-input", empty, out), ("missing-input", out / "missing.cbor", out),
                               ("outside-scope", source, narrow)]:
        result = subprocess.run([str(compiler), "check-kototama", str(path), "--profile", PROFILES[0]],
                                env=dict(env, KEXE_CAP_RESOURCES_35=str(scoped)), capture_output=True, timeout=120)
        observations.extend([result.returncode, len(result.stdout), int(bool(result.stderr))])
        expected.extend([1, 0, 1])
        records.append({"case": name, "exit": result.returncode,
                        "stdoutBytes": len(result.stdout), "stderrBytes": len(result.stderr)})

    raw = struct.pack("<" + "q" * len(observations), *observations)
    (out / "observations.bin").write_bytes(raw)
    (out / "gate.kotoba").write_text(v.gate_source(expected))
    gate = out / "gate.elf"
    built = subprocess.run([str(compiler), "compile", str(out / "gate.kotoba"), "--target", target,
                            "--output", str(gate), "--format", "static"], env=env, capture_output=True, timeout=180)
    (out / "gate-compile.stdout").write_bytes(built.stdout)
    (out / "gate-compile.stderr").write_bytes(built.stderr)
    if built.returncode or not gate.exists():
        raise SystemExit("native gate build failed: " + built.stderr.decode(errors="replace"))
    gate.chmod(0o755)
    positive = subprocess.run([str(gate), str(out / "observations.bin")], env=env, capture_output=True, timeout=30)
    (out / "gate.stdout").write_bytes(positive.stdout)
    (out / "gate.stderr").write_bytes(positive.stderr)
    corrupt = bytearray(raw)
    corrupt[0] ^= 1
    (out / "corrupt.bin").write_bytes(corrupt)
    negative = subprocess.run([str(gate), str(out / "corrupt.bin")], env=env, capture_output=True, timeout=30)
    (out / "corrupt.stdout").write_bytes(negative.stdout)
    (out / "corrupt.stderr").write_bytes(negative.stderr)
    report = {"schema": "amu.kototama-pure-i64-check-native.v1", "compilerSHA256": hashlib.sha256(compiler.read_bytes()).hexdigest(),
              "target": target, "cases": records, "verdictExit": positive.returncode,
              "corruptControlExit": negative.returncode}
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("cases", len(records), "native-verdict", positive.returncode, "corrupt-control", negative.returncode, flush=True)
    if positive.returncode != 0 or negative.returncode == 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
