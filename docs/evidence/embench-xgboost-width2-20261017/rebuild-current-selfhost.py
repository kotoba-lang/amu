#!/usr/bin/env python3
"""Rebuild the pinned M105 selfhost compiler from the adopted native bootstrap."""
import argparse
import hashlib
import json
import os
import platform
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent


def sha(data):
    if isinstance(data, Path):
        data = data.read_bytes()
    return hashlib.sha256(data).hexdigest()


def repo_file(name):
    path = (ROOT / name).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise SystemExit(f"missing or out-of-repository input: {name}")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise SystemExit("the pinned native bootstrap requires macOS arm64")
    out = args.out.resolve()
    if out.exists():
        raise SystemExit(f"output already exists: {out}")

    receipt_path = EVIDENCE / "m105-current-selfhost-rebuild-receipt.json"
    receipt = json.loads(receipt_path.read_text())
    source_rows = receipt["sourceFiles"]
    for row in source_rows:
        path = repo_file(row["path"])
        if path.stat().st_size != row["bytes"] or sha(path) != row["sha256"]:
            raise SystemExit(f"source pin mismatch: {row['path']}")
    manifest = repo_file(receipt["manifestPath"])
    modules = [line.strip() for line in manifest.read_text().splitlines()
               if line.strip() and not line.startswith("#")]
    if len(modules) != 16 or modules != [row["path"] for row in source_rows]:
        raise SystemExit("manifest does not match the pinned 16-module closure")
    unity = b"".join(repo_file(name).read_bytes() + b"\n" for name in modules)
    if len(unity) != receipt["sourceUnityBytes"] or sha(unity) != receipt["sourceUnitySHA256"]:
        raise SystemExit("source unity pin mismatch")

    bootstrap = repo_file(receipt["adoptedBootstrapPath"])
    loader_source = repo_file(receipt["loaderPath"])
    if sha(bootstrap) != receipt["adoptedBootstrapSHA256"]:
        raise SystemExit("adopted bootstrap image pin mismatch")
    if sha(loader_source) != receipt["loaderSourceSHA256"]:
        raise SystemExit("trusted C loader source pin mismatch")

    out.mkdir(parents=True)
    host, artifacts = out / "host", out / "artifacts"
    host.mkdir()
    artifacts.mkdir()
    source = artifacts / "seed-unity.kotoba"
    source.write_bytes(unity)
    loader = host / "kexe-loader"
    calls = []
    env = dict(os.environ)
    env.update(KEXE_COMMAND="1", KEXE_CAP_RESOURCES_35=str(artifacts),
               KEXE_FUEL="off", KEXE_VECTORS="4194304",
               KEXE_VECTOR_ITEMS="134217728", KEXE_STRING_POOL="268435456",
               KEXE_PAIRS="16777216", KEXE_CPU_SECONDS="1800",
               KEXE_WALL_SECONDS="1800", TMPDIR=str(artifacts))

    def run(argv, name):
        row = {"name": name, "argv": [str(x) for x in argv]}
        with (host / f"{name}.stdout").open("wb") as stdout, \
             (host / f"{name}.stderr").open("wb") as stderr:
            result = subprocess.run(row["argv"], cwd=artifacts, env=env,
                                    stdout=stdout, stderr=stderr, timeout=1800)
        row["exit"] = result.returncode
        calls.append(row)
        (host / "calls.json").write_text(json.dumps(calls, indent=2) + "\n")
        if result.returncode:
            raise SystemExit(f"failed {name}; raw logs preserved")

    report = {
        "status": "RUNNING",
        "sourceCommit": receipt["sourceCommit"],
        "sourceUnity": {"bytes": len(unity), "sha256": sha(unity)},
        "adoptedBootstrap": {"path": str(bootstrap), "sha256": sha(bootstrap)},
        "candidateFixedPointSHA256": receipt["candidateFixedPointSHA256"],
        "loaderSourceSHA256": sha(loader_source),
        "startedUnix": time.time(),
        "host": {"system": platform.system(), "machine": platform.machine(),
                 "version": platform.mac_ver()[0]},
        "generations": [],
        "JVMNodeOrGraalFallback": False,
    }
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    run(["clang", "-std=c11", "-O2", loader_source, "-o", loader], "loader-build")
    report["loaderBinarySHA256"] = sha(loader)

    producer = bootstrap
    for generation in range(1, 4):
        prefix = [loader, producer, "0", "0", "aarch64", "35,37,38,39", "--"]
        container = artifacts / f"G{generation}.kseed"
        native = artifacts / f"G{generation}.bin"
        run(prefix + ["compile", source, "--target", "aarch64-macos", "--output", container],
            f"G{generation}-compile")
        run(prefix + ["extract-native", container, "--symbol", "main", "--output", native],
            f"G{generation}-extract")
        image_hash = sha(native)
        if image_hash != receipt["candidateFixedPointSHA256"]:
            raise SystemExit(f"G{generation} image differs from candidate fixed point: {image_hash}")
        report["generations"].append({
            "generation": generation,
            "bytes": native.stat().st_size,
            "sha256": image_hash,
            "containerSHA256": sha(container),
        })
        producer = native
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    report["status"] = "PASS_M105_G1_G2_G3_BYTE_IDENTICAL"
    report["endedUnix"] = time.time()
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
