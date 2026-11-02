#!/usr/bin/env python3
"""Capture raw execution observations for already-built complete24 fixtures.

This diagnostic transport does not interpret output or decide a language
verdict; the source-pinned native gate remains responsible for qualification.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def main(directory):
    env = {"PATH": "/nonexistent", "KEXE_ALLOW": "-", "KEXE_STACK_BYTES": "1048576",
           "KEXE_CAP_RESOURCES_35": str(directory), "KEXE_STRUCTURED_REPORT": "1", "KEXE_FUEL": "1000000"}
    observations = []
    for i in range(24):
        image = directory / f"case-{i}.elf"
        if not image.is_file():
            observations.append({"index": i, "missing": True})
            continue
        result = subprocess.run([str(image)], cwd=directory, env=env, capture_output=True, timeout=20)
        (directory / f"observed-case-{i}.stdout").write_bytes(result.stdout)
        (directory / f"observed-case-{i}.stderr").write_bytes(result.stderr)
        observations.append({"index": i, "sha256": hashlib.sha256(image.read_bytes()).hexdigest(), "exit": result.returncode})
    (directory / "native-observed-cases.json").write_text(json.dumps(observations, indent=2) + "\n")
    print("CAPTURED_NATIVE_CASE_OUTPUTS", len(observations))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("directory", type=Path)
    main(p.parse_args().directory.resolve())
