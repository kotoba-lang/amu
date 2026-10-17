#!/usr/bin/env python3
"""Build the optional AArch64-native scalar x86_64 Linux cross-compiler."""
import argparse
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]


def pin(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def build(output):
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise SystemExit("the pinned bootstrap requires macOS arm64")
    spec = importlib.util.spec_from_file_location("adopted_build", ROOT / "scripts/seed/build-adopted.py")
    adopted = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adopted)
    receipt, _, producer, loader_source = adopted.inputs(ROOT / "seed/adoption-20261018.json")
    manifest = ROOT / "seed/X86_64-LINUX-MANIFEST"
    paths = [ROOT / x for x in manifest.read_text().splitlines() if x and not x.startswith("#")]
    unity = b"".join(p.read_bytes() + b"\n" for p in paths)
    inputs = [pin(p) for p in [manifest, loader_source, producer, *paths]]
    output.mkdir(parents=True, exist_ok=False)
    host = output / "host"
    artifacts = output / "artifacts"
    host.mkdir()
    artifacts.mkdir()
    source = artifacts / "seed-unity.kotoba"
    source.write_bytes(unity)
    env = {k: v for k, v in os.environ.items() if not k.startswith("KEXE_")}
    env.update(KEXE_COMMAND="1", KEXE_CAP_RESOURCES_35=str(artifacts), KEXE_FUEL="off",
               KEXE_VECTORS="4194304", KEXE_VECTOR_ITEMS="134217728",
               KEXE_STRING_POOL="268435456", KEXE_PAIRS="16777216",
               KEXE_CPU_SECONDS="1800", KEXE_WALL_SECONDS="1800", TMPDIR=str(artifacts))
    calls = []

    def run(name, args):
        watched = [source, producer] + ([loader] if loader.exists() else [])
        before = {str(p): pin(p) for p in watched}
        with (host / (name + ".stdout")).open("wb") as stdout, (host / (name + ".stderr")).open("wb") as stderr:
            result = subprocess.run(list(map(str, args)), cwd=artifacts, env=env,
                                    stdout=stdout, stderr=stderr, timeout=1800)
        after = {str(p): pin(p) if p.is_file() else None for p in watched}
        calls.append({"name": name, "argv": list(map(str, args)), "exit": result.returncode,
                      "invocationInputPins": before, "inputPinsAfter": after})
        (host / "calls.json").write_text(json.dumps(calls, indent=2) + "\n")
        if before != after:
            raise SystemExit("active source/producer/loader changed during native invocation; raw logs preserved")
        if result.returncode:
            raise SystemExit("failed " + name + "; raw logs preserved in " + str(host))
        for row in inputs:
            if pin(Path(row["path"])) != row:
                raise SystemExit("source/bootstrap changed during native build")

    loader = host / "kexe-loader"
    run("loader-build", ["clang", "-std=c11", "-O2", loader_source, "-o", loader])
    generations = []
    for generation in (1, 2, 3):
        prefix = [loader, producer, "0", "0", "aarch64", "35,37,38,39", "--"]
        container = artifacts / f"G{generation}.kseed"
        native = artifacts / f"G{generation}.bin"
        run(f"G{generation}-compile", prefix + ["compile", source, "--target", "aarch64-macos", "--output", container])
        run(f"G{generation}-extract", prefix + ["extract-native", container, "--symbol", "main", "--output", native])
        generations.append({"native": pin(native), "container": pin(container)})
        producer = native
    if generations[1]["native"]["sha256"] != generations[2]["native"]["sha256"]:
        raise SystemExit("native G2/G3 fixed point failed: " + json.dumps(generations))
    if generations[1]["container"]["sha256"] != generations[2]["container"]["sha256"]:
        raise SystemExit("container G2/G3 fixed point failed: " + json.dumps(generations))
    report = {"status": "PASS_NATIVE_X86_64_LINUX_CROSS_COMPILER_BUILD",
              "hostTarget": "aarch64-macos", "outputTarget": "x86_64-linux",
              "outputProfile": "scalar ELF64, main()->i64, at most five scalar arguments",
              "x86CompilerSelfhostClaim": False, "JVMNodeOrGraalFallback": False,
              "trustedCLoader": True,
              "adoptedBootstrap": receipt.get("bootstrapSHA256", receipt["nativeImageSHA256"]),
              "sourceUnitySHA256": hashlib.sha256(unity).hexdigest(),
              "inputs": inputs, "generations": generations, "performanceMeasured": False}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], generations[-1]["native"]["sha256"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    build(parser.parse_args().output.resolve())
