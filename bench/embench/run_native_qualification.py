#!/usr/bin/env python3
"""Run every Amu Embench port with the standalone native compiler.

The script deliberately supplies an environment containing only system PATH,
HOME, and TMPDIR. It records compiler and artifact hashes, check/compile wall
times, five execution samples, code sizes, target ISA, and port fidelity.
"""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import time

FULL = {
    "aha-mont64", "crc32", "depthconv", "matmult-int", "md5sum",
    "nettle-sha256", "tarfind", "ud", "xgboost",
}
ADAPTED = {
    "edn", "huffbench", "nettle-aes", "nsichneu", "picojpeg", "qrduino",
    "sglib-combined", "slre", "statemate", "wikisort",
}

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def invoke(argv, env=None):
    started = time.perf_counter_ns()
    result = subprocess.run(argv, text=True, capture_output=True, env=env)
    elapsed = time.perf_counter_ns() - started
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {argv}\n{result.stdout}{result.stderr}")
    return result, elapsed

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", required=True, type=Path)
    parser.add_argument("--runner", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--upstream", required=True, type=Path)
    parser.add_argument("--samples", type=int, default=5)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    ports = root / "bench" / "embench" / "ports"
    args.output.mkdir(parents=True, exist_ok=True)
    isolated_bin = args.output / "isolated-empty-path"
    isolated_bin.mkdir(exist_ok=True)
    if any(isolated_bin.iterdir()):
        raise RuntimeError(f"isolated PATH is not empty: {isolated_bin}")
    clean_env = {"PATH": str(isolated_bin), "HOME": str(Path.home()), "TMPDIR": "/tmp"}
    compiler_deps = subprocess.run(["otool", "-L", str(args.compiler)], text=True,
                                   capture_output=True, check=True).stdout
    forbidden = [x for x in ("node", "javascript", "jvm", "libjvm") if x in compiler_deps.lower()]
    if forbidden:
        raise RuntimeError(f"native compiler has forbidden runtime dependencies: {forbidden}")
    upstream_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=args.upstream,
                                     text=True, capture_output=True, check=True).stdout.strip()
    rows = []
    for source in sorted(ports.glob("*.kotoba")):
        name = source.stem
        header = source.read_text().splitlines()[0]
        exports = re.search(r":export \[([^]]+)\]", header).group(1).split()
        symbol = next(x for x in exports if x.startswith("test-"))
        directory = args.output / name
        directory.mkdir(exist_ok=True)
        kexe, raw = directory / f"{name}.kexe", directory / f"{name}.bin"
        check_times, compile_times = [], []
        for index in range(args.samples):
            result, elapsed = invoke([str(args.compiler), "check", str(source), "--jvm-free"], clean_env)
            check_times.append(elapsed)
            (directory / f"check-{index}.stdout").write_text(result.stdout)
            (directory / f"check-{index}.stderr").write_text(result.stderr)
        for index in range(args.samples):
            target = kexe if index == args.samples - 1 else directory / f"sample-{index}.kexe"
            result, elapsed = invoke([str(args.compiler), "compile", str(source), "--target",
                                      "aarch64-macos", "--jvm-free", "--output", str(target)], clean_env)
            compile_times.append(elapsed)
            (directory / f"compile-{index}.stdout").write_text(result.stdout)
            (directory / f"compile-{index}.stderr").write_text(result.stderr)
        extracted, _ = invoke([str(args.compiler), "extract-native", str(kexe), "--symbol",
                               symbol, "--output", str(raw)], clean_env)
        (directory / "extract.stdout").write_text(extracted.stdout)
        match = re.search(r":offset\s+(\d+)", extracted.stdout)
        if not match:
            raise RuntimeError(f"missing offset for {name}")
        offset = match.group(1)
        execution = []
        for index in range(args.samples):
            result, _ = invoke([str(args.runner), "raw", str(raw), offset, "aarch64",
                                "0", "1", "0", "16777216"])
            sample = json.loads(result.stdout)
            if sample["result"] != 1:
                raise RuntimeError(f"{name} returned {sample['result']}, expected 1")
            execution.append(sample)
            (directory / f"run-{index}.json").write_text(json.dumps(sample, indent=2) + "\n")
        row = {
            "workload": name,
            "fidelity": "full-correctness-translation" if name in FULL else "adapted-algorithmic-probe",
            "correct": True,
            "check_ns": check_times,
            "compile_ns": compile_times,
            "execution": execution,
            "source_bytes": source.stat().st_size,
            "source_sha256": sha256(source),
            "kexe_bytes": kexe.stat().st_size,
            "kexe_sha256": sha256(kexe),
            "raw_code_bytes": raw.stat().st_size,
            "raw_code_sha256": sha256(raw),
            "export": symbol,
            "offset": int(offset),
        }
        rows.append(row)
    if {x["workload"] for x in rows} != FULL | ADAPTED:
        raise RuntimeError("port inventory differs from the declared 19 workloads")
    report = {
        "format": "amu.embench-native-qualification/v1",
        "created_epoch_seconds": int(time.time()),
        "official_embench_score": False,
        "host": {"system": platform.system(), "release": platform.release(),
                 "machine": platform.machine(), "processor": platform.processor()},
        "target": {"isa": "aarch64", "os": "macos", "artifact": "KEXE/raw AArch64"},
        "compiler": {"path": str(args.compiler.resolve()), "sha256": sha256(args.compiler),
                     "bytes": args.compiler.stat().st_size, "otool_L": compiler_deps,
                     "isolated_environment": clean_env, "javascript_node_dependency": False,
                     "jvm_dependency": False},
        "runner": {"path": str(args.runner.resolve()), "sha256": sha256(args.runner)},
        "upstream": {"repository": "https://github.com/embench/embench-iot",
                     "commit": upstream_commit},
        "workloads": rows,
    }
    (args.output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    with open(args.output / "summary.csv", "w", newline="") as stream:
        fields = ["workload", "fidelity", "correct", "check_median_ms", "compile_median_ms",
                  "execute_median_ns", "kexe_bytes", "raw_code_bytes", "source_sha256", "kexe_sha256"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            checks, compiles = sorted(row["check_ns"]), sorted(row["compile_ns"])
            executes = sorted(x["elapsedNanoseconds"] for x in row["execution"])
            writer.writerow({"workload": row["workload"], "fidelity": row["fidelity"], "correct": True,
                             "check_median_ms": checks[len(checks)//2] / 1e6,
                             "compile_median_ms": compiles[len(compiles)//2] / 1e6,
                             "execute_median_ns": executes[len(executes)//2],
                             "kexe_bytes": row["kexe_bytes"], "raw_code_bytes": row["raw_code_bytes"],
                             "source_sha256": row["source_sha256"], "kexe_sha256": row["kexe_sha256"]})
    print(args.output / "qualification.json")

if __name__ == "__main__":
    main()
