#!/usr/bin/env python3
"""Observe current native selfbuild and full-19 one-body correctness.

Python stages fixed source bytes and records subprocess output. The current
native compiler builds all artifacts; each unchanged workload's bench-verify
owns its correctness result. This is preparation, not a timing campaign or
a claim-grade native measurement gate.
"""
import argparse
import hashlib
import json
import platform
import re
import struct
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PACKAGE = HERE.parent / "reproduce-20261015"


def pin(path):
    raw = path.read_bytes()
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def static_elf(path):
    raw = path.read_bytes()
    if raw[:8] != b"\x7fELF\x02\x01\x01\0" or struct.unpack_from("<HH", raw, 16) != (2, 62):
        raise ValueError("native x86_64 static ELF required")
    offset = struct.unpack_from("<Q", raw, 32)[0]
    size, count = struct.unpack_from("<HH", raw, 54)
    if size != 56 or not 0 < count <= 16 or offset + count * size > len(raw):
        raise ValueError("malformed ELF program headers")
    if any(struct.unpack_from("<I", raw, offset + i * size)[0] in (2, 3) for i in range(count)):
        raise ValueError("dynamic segment or interpreter refused")
    return pin(path)


def main(output, iteration_profile="one-body"):
    if (platform.system(), platform.machine()) != ("Linux", "x86_64"):
        raise SystemExit("native Linux x86_64 host required; no emulation or legacy loader fallback")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    (output / "raw").mkdir()
    product = json.loads((REPO / "native-product.json").read_text())
    compiler = REPO / "bin/amu"
    if static_elf(compiler) != product["image"]:
        raise ValueError("compiler differs from native-product.json")
    paths = [line for line in (REPO / "seed/FULL-MANIFEST").read_text().splitlines()
             if line and not line.startswith("#")]
    unity = output / "full.kotoba"
    unity.write_bytes(b"".join((REPO / path).read_bytes() + b"\n" for path in paths))
    if pin(unity) != product["sourceUnity"]:
        raise ValueError("complete source unity differs from product pin")
    report = {"schema": "amu.embench.native-preparation.v1", "status": "running",
              "host": [platform.system(), platform.machine(), platform.release()],
              "compiler": pin(compiler), "sourceUnity": pin(unity),
              "preparationScript": pin(Path(__file__)),
              "sources": {path: pin(REPO / path) for path in paths},
              "entry": pin(HERE / "native-entry.kotoba"),
              "compilerGenerations": [pin(compiler)], "calls": [], "workloads": [],
              "iterationProfile": iteration_profile, "performanceQualified": False,
              "evidenceLimit": "built-in correctness only; timing, independent accounting and process-trace gates pending"}

    def save():
        (output / "native-build.json").write_text(json.dumps(report, indent=2) + "\n")

    def observe(name, argv, env, timeout=900):
        try:
            result = subprocess.run(list(map(str, argv)), cwd=output, env=env,
                                    capture_output=True, timeout=timeout)
            code, stdout, stderr = result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as error:
            code, stdout, stderr = None, error.stdout or b"", error.stderr or b""
        logs = {}
        for suffix, raw in (("stdout", stdout), ("stderr", stderr)):
            path = output / "raw" / (name + "." + suffix)
            path.write_bytes(raw)
            logs[suffix] = {"path": path.relative_to(output).as_posix(), **pin(path)}
        report["calls"].append({"name": name, "argv": list(map(str, argv)), "exit": code, **logs})
        save()
        print(name, "exit", code, stderr.decode(errors="replace")[:250], flush=True)
        return code, stdout, stderr

    compile_env = {"PATH": "/nonexistent", "KEXE_ALLOW": "35,37,38,39",
                   "KEXE_CAP_RESOURCES_35": str(output), "KEXE_STACK_BYTES": "8388608"}
    current = compiler
    for generation in (2, 3):
        image = output / f"F{generation}.elf"
        code, _, stderr = observe(f"selfbuild-F{generation}",
                                 [current, "compile", unity, "--target", "x86_64-linux",
                                  "--output", image, "--format", "static"], compile_env)
        if code != 0 or stderr or not image.is_file() or static_elf(image) != product["image"]:
            report.update(status="rejected-selfbuild", fixedPoint=False)
            save()
            return 2
        image.chmod(0o700)
        current = image
        report["compilerGenerations"].append(pin(image))
        save()
    report["fixedPoint"] = True
    runner_source = output / "runner.kotoba"
    runner_source.write_bytes((REPO / "seed/x86_64-kx64-runner.kotoba").read_bytes())
    runner = output / "runner.elf"
    code, _, stderr = observe("native-runner-compile",
                             [current, "compile", runner_source, "--target", "x86_64-linux",
                              "--output", runner, "--format", "kx64-runner"], compile_env)
    if code != 0 or stderr or not runner.is_file():
        report.update(status="rejected-native-runner")
        save()
        return 2
    report["nativeRunner"] = {"source": pin(runner_source), "image": static_elf(runner)}
    runner.chmod(0o700)
    table = json.loads((PACKAGE / "round-sa-m104-20261015/expected/measured-images.json").read_text())
    if len(table) != 19:
        raise ValueError("complete 19-workload table required")
    workload_rows = json.loads((PACKAGE / "round-sa-m104-20261015/workloads.json").read_text())
    counts = {row["workload"]: row["n"] for row in workload_rows}
    if set(counts) != set(table):
        raise ValueError("registered workload counts differ from pinned source set")
    report["iterationTable"] = pin(PACKAGE / "round-sa-m104-20261015/workloads.json")
    entry = (HERE / "native-entry.kotoba").read_bytes()
    for workload in sorted(table):
        original = PACKAGE / "ports" / f"official-{workload}.kotoba"
        if pin(original)["sha256"] != table[workload]["sourceSHA256"]:
            raise ValueError(f"{workload}: source differs from historical source pin")
        namespace = re.match(rb"\(ns ([a-z0-9.-]+) ", original.read_bytes())
        if namespace is None:
            raise ValueError(f"{workload}: unexpected namespace header")
        module = namespace[1].decode()
        source_root = output / workload / "src"
        library = source_root / (module.replace(".", "/").replace("-", "_") + ".kotoba")
        library.parent.mkdir(parents=True)
        library.write_bytes(original.read_bytes())
        source = source_root / "proof/native_entry.kotoba"
        source.parent.mkdir()
        # No original source/exports are edited; use the compiler's existing
        # locked module linker to import the workload into a distinct entry.
        iterations = 1 if iteration_profile == "one-body" else counts[workload]
        source.write_bytes(entry.replace(b"[embench.workload :as", b"[" + namespace[1] + b" :as").replace(
            b"(workload/bench-verify 1)", f"(workload/bench-verify {iterations})".encode()))
        lock = output / f"{workload}.ksl"
        lock.write_text(f"KSL1\nentry {source}\nroot {source_root}\n" +
                        "".join(f"file {pin(path)['sha256']} {path}\n" for path in sorted((source, library))))
        image = output / f"{workload}.kx64"
        row = {"workload": workload, "originalSource": pin(original), "stagedSource": pin(library), "entrySource": pin(source),
               "sourceLock": pin(lock), "iterations": iterations, "accepted": False, "result": None}
        report["workloads"].append(row)
        code, _, stderr = observe(workload + "-compile",
                                 [current, "compile", source, "--target", "x86_64-linux", "--output", image,
                                  "--format", "kx64-v1", "--source-path", source_root,
                                  "--source-lock", lock, "--source-lock-sha256", pin(lock)["sha256"]],
                                 compile_env)
        if code != 0 or stderr or not image.is_file():
            row["reason"] = "native compile refused or failed"
            save()
            continue
        header, body = image.read_bytes().split(b"\n\n", 1)
        match = re.fullmatch(rb"KX64V1 x86_64-linux sysv-ctx-v11 ([0-9]+) 0", header)
        if not match or len(body) != int(match[1]) or body[0] != 0xe9:
            raise ValueError(f"{workload}: malformed native payload")
        payload = output / f"{workload}.bin"
        payload.write_bytes(body)
        row["image"] = pin(image)
        row["payload"] = pin(payload)
        code, stdout, stderr = observe(workload + "-run", [runner, payload, "0", "0", "x86_64", "-"],
                                      {"PATH": "/nonexistent", "KEXE_ALLOW": "-", "KEXE_FUEL": "1000000000000",
                                       "KEXE_CAP_RESOURCES_35": str(output),
                                       "KEXE_STRUCTURED_REPORT": "1", "KEXE_WALL_SECONDS": "30"}, timeout=45)
        values = re.findall(rb":result (-?[0-9]+)\b", stdout)
        row["result"] = int(values[0]) if len(values) == 1 else None
        row["accepted"] = code == 0 and not stderr and row["result"] == 1
        row["reason"] = None if row["accepted"] else "native built-in correctness probe failed"
        save()
    count = sum(row["accepted"] for row in report["workloads"])
    report.update(acceptedWorkloads=count, status="observed-native-correctness-19" if count == 19 else "rejected-incomplete-native-correctness")
    save()
    print(report["status"], f"{count}/19; performance qualification pending", flush=True)
    return 0 if count == 19 else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--iteration-profile", choices=("one-body", "m104-counts"), default="one-body")
    args = parser.parse_args()
    raise SystemExit(main(args.out.resolve(), args.iteration_profile))
