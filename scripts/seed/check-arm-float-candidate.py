#!/usr/bin/env python3
"""Run bounded ARM float evidence with a pinned compiler and rejecting control.

This diagnostic does not establish provenance, independent-host qualification,
or compiler adoption. Output must be a new directory on the local host.
"""
import argparse
import hashlib
import json
import platform
import resource
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES = (("sign", 42), ("compare", 42), ("arithmetic", 42),
         ("conversion", 3), ("integration", 511))


def digest(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def pin(path, expected):
    path = path.resolve(strict=True)
    if not path.is_file() or digest(path)["sha256"] != expected:
        raise SystemExit("compiler pin mismatch: " + str(path))
    return path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--compiler-sha256", required=True)
    p.add_argument("--negative-compiler", type=Path, required=True)
    p.add_argument("--negative-compiler-sha256", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if platform.system() != "Linux" or platform.machine() not in ("aarch64", "arm64"):
        raise SystemExit("reported native Linux AArch64 host required")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    compiler = pin(args.compiler, args.compiler_sha256)
    negative = pin(args.negative_compiler, args.negative_compiler_sha256)
    if args.compiler_sha256 == args.negative_compiler_sha256:
        raise SystemExit("negative control must be a different pinned compiler")
    output = args.output.absolute()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    env = {"PATH": "/nonexistent", "KEXE_ALLOW": "35,37,38,39",
           "KEXE_CAP_RESOURCES_35": str(output), "KEXE_STACK_BYTES": "8388608"}
    guest_env = {"PATH": "/nonexistent", "KEXE_ALLOW": "-", "KEXE_FUEL": "1000000",
                 "KEXE_STRUCTURED_REPORT": "1"}
    rows = []

    def run(name, command, environment):
        result = subprocess.run([str(x) for x in command], cwd=output, env=environment,
                                capture_output=True, timeout=180, check=False)
        for stream in ("stdout", "stderr"):
            (output / (name + "." + stream)).write_bytes(getattr(result, stream))
        rows.append({"name": name, "exit": result.returncode,
                     "stdout": digest(output / (name + ".stdout")),
                     "stderr": digest(output / (name + ".stderr"))})
        print(name, result.returncode, flush=True)
        return result

    artifacts = []
    for name, expected in CASES:
        src = output / (name + ".kotoba")
        src.write_bytes((ROOT / "seed/tests" / ("native-aarch64-float-" + name + ".kotoba")).read_bytes())
        image = output / (name + ".elf")
        result = run(name + "-compile", [compiler, "compile", src, "--target", "aarch64-linux",
                                          "--output", image, "--format", "static"], env)
        if result.returncode != 0 or not image.is_file():
            raise SystemExit(name + ": compilation failed")
        image.chmod(0o700)
        result = run(name + "-run", [image], guest_env)
        if result.returncode != 0 or (":result " + str(expected) + " ").encode() not in result.stdout:
            raise SystemExit(name + ": guest result mismatch")
        artifacts.append({"name": name, "source": digest(src), "image": digest(image), "expected": expected})

    src = output / "negative.kotoba"
    src.write_text("(ns negative-float (:export [main]))\n"
                   "(defn main [] :i64 (if (f64-lt -2.0 -1.0) 42 7))\n")
    image = output / "negative.elf"
    result = run("negative-compile", [negative, "compile", src, "--target", "aarch64-linux",
                                       "--output", image, "--format", "static"], env)
    if result.returncode == 0 or b"E7101" not in result.stderr or image.exists():
        raise SystemExit("negative compiler did not fail closed")
    receipt = {"status": "PASS_BOUNDED_ARM_FLOAT_DIAGNOSTIC", "compiler": digest(compiler),
               "negativeCompiler": digest(negative), "reportedPlatform": platform.platform(),
               "cases": artifacts, "negativeSource": digest(src), "calls": rows}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
