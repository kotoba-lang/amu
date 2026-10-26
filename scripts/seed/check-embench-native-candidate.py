#!/usr/bin/env python3
"""Stage original full19 through a native candidate, not a timing campaign.

Amu alone compiles/links/extracts every payload and builds the native runner.
Python stages exact bytes/locks, observes processes and compares old reference
records. No result here qualifies performance, adoption or external validation.
"""
import argparse
import hashlib
import json
import os
import platform
import re
import struct
import subprocess
import time
from pathlib import Path

from native_process_profile import atomic_json

ROOT = Path(__file__).resolve().parents[2]
ENTRY_SHA = "3572dfb834b5479d4694e9554e67ad6b7e02e517d19c480c4943955bb79c4849"
DATA_PINS = {
    "round-sa-m104-20261015/expected/measured-images.json": "c0c9a31deba334a8c5402554719e1b012c02debe8c5963e9316fe322f3bf179a",
    "round-sa-m104-20261015/workloads.json": "c83550918d2125497d5ed75ca5d9a9ff83d509ce87f33dbc33f2ca95678d56c8",
    "round-sa-m104-20261015/records/round/expected-accounting-mw.json": "6368bd343086a6c88e0645e31dde82bcdf64742c7b4727cdd56103ef72e9b4cc"
}
FIELDS = ("pairs", "string-pool-bytes", "vectors", "vector-items", "heap-bytes",
          "conj", "conj-tail", "conj-region", "conj-copy", "copied-words",
          "reserved-words", "regions", "scope-releases", "string-regions",
          "string-region-appends", "string-copied-bytes", "string-reserved-bytes")


def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def elf(path, machine):
    raw = path.read_bytes()
    assert raw[:8] == b"\x7fELF\x02\x01\x01\0" and struct.unpack_from("<HH", raw, 16) == (2, machine)
    offset = struct.unpack_from("<Q", raw, 32)[0]
    size, count = struct.unpack_from("<HH", raw, 54)
    assert size == 56 and 0 < count <= 16 and offset + size * count <= len(raw)
    assert all(struct.unpack_from("<I", raw, offset + size * i)[0] not in (2, 3) for i in range(count))
    return pin(path)


def arena(raw):
    match = re.fullmatch(rb"KEXE_ARENA_USE \{(.+)\}\n", raw)
    if not match:
        return None
    pairs = re.findall(rb":([a-z-]+) ([0-9]+)", match[1])
    if tuple(k.decode() for k, _ in pairs) != FIELDS:
        return None
    if b" ".join(b":" + k + b" " + v for k, v in pairs) != match[1]:
        return None
    return {k.decode(): int(v) for k, v in pairs}


def provenance(one, complete):
    arch = platform.machine()
    assert platform.system() == "Linux" and arch in ("aarch64", "x86_64")
    paths = [p for p in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines() if p and not p.startswith("#")]
    source = {p: pin(ROOT / p) for p in ["seed/FULL-MANIFEST", *paths]}
    unity = b"".join((ROOT / p).read_bytes() + b"\n" for p in paths)
    if arch == "aarch64":
        assert one and not complete
        receipt = one / "one-compiler.json"
        proof = json.loads(receipt.read_text())
        assert proof["status"] == "PASS_COMBINED_COMPILER" and proof["host"][:2] == ["Linux", arch]
        assert not proof["cCompilerOrLoader"] and not proof["emulation"]
        assert source == proof["sources"]["seed/FULL-MANIFEST"]
        assert len(proof["F"]["containers"]) == 3 and all(x == proof["F"]["containers"][0] for x in proof["F"]["containers"])
        assert proof["F"]["image"] == proof["F"]["packedByF"]
        for i in (1, 2, 3):
            assert pin(one / f"F{i}.kseed") == proof["F"]["containers"][i - 1]
        for i in (1, 2):
            assert elf(one / f"F{i}.elf", 183) == proof["F"]["image"]
        compiler, machine, target = one / "F2.elf", 183, "aarch64-linux"
    else:
        assert complete and not one
        receipt = complete / "complete-x86.json"
        proof = json.loads(receipt.read_text())
        assert proof["status"] == "PASS_COMPLETE_NATIVE_X86_COMPILER_BUILD" and proof["host"][:2] == ["Linux", arch]
        assert not proof["cCompilerOrLoader"] and not proof["JVMNodeOrGraalFallback"] and not proof["emulation"]
        assert proof["sourceUnity"] == dict(bytes=len(unity), sha256=hashlib.sha256(unity).hexdigest())
        assert len(proof["generations"]) == 3 and proof["generations"][0] == proof["generations"][1] == proof["generations"][2]
        for i in (1, 2, 3):
            assert elf(complete / f"F{i}.elf", 62) == {k: proof["generations"][i - 1][k] for k in ("bytes", "sha256")}
        compiler, machine, target = complete / "F3.elf", 62, "x86_64-linux"
    return compiler, machine, target, receipt, source


def main(args):
    compiler, machine, target, receipt, sources = provenance(args.one, args.complete)
    package, entry, out = args.package.resolve(), args.entry.resolve(), args.output.resolve()
    assert pin(entry)["sha256"] == ENTRY_SHA
    assert all(pin(package / name)["sha256"] == digest for name, digest in DATA_PINS.items())
    table_path = package / "round-sa-m104-20261015/expected/measured-images.json"
    count_path = package / "round-sa-m104-20261015/workloads.json"
    reference_path = package / "round-sa-m104-20261015/records/round/expected-accounting-mw.json"
    table = json.loads(table_path.read_text())
    counts = {r["workload"]: r["n"] for r in json.loads(count_path.read_text())}
    reference = {r["workload"]: r for r in json.loads(reference_path.read_text())}
    assert len(table) == 19 and set(table) == set(counts) == set(reference)
    assert all(reference[name]["n"] == counts[name] for name in table)
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    (out / "raw").mkdir()
    report = dict(schema="amu.embench.native-candidate-preparation.v1", status="running",
                  performanceQualified=False, qualificationReplacement=False,
                  benchmarkVerifyFuelSeparatelyMeasured=False, publicProductAdopted=False,
                  host=[platform.system(), platform.machine(), platform.release()],
                  compiler=elf(compiler, machine), candidateReceipt=pin(receipt), sources=sources,
                  observer=pin(Path(__file__)), entryTemplate=pin(entry), target=target,
                  runtimeProfile=args.runtime_profile, iterationProfile=args.iteration_profile,
                  wallSeconds=args.wall_seconds, iterationTable=pin(count_path),
                  originalSourceTable=pin(table_path), historicalAccountingReference=pin(reference_path),
                  route="adopted-core-locked-aarch64" if machine == 183 else "locked-x86-project",
                  calls=[], workloads=[dict(workload=n, status="not-run") for n in sorted(table)])

    def save():
        atomic_json(out / "observations.json", report)

    def call(name, argv, env, timeout=900):
        logs = {s: out / "raw" / (name + "." + s) for s in ("stdout", "stderr")}
        start, timed_out = time.monotonic(), False
        with logs["stdout"].open("xb") as stdout, logs["stderr"].open("xb") as stderr:
            process = subprocess.Popen(list(map(str, argv)), cwd=out, env=env, stdout=stdout, stderr=stderr)
            while True:
                pid, status, usage = os.wait4(process.pid, os.WNOHANG)
                if pid:
                    process.returncode = os.waitstatus_to_exitcode(status)
                    break
                if time.monotonic() - start > timeout:
                    timed_out = True
                    process.kill()
                    _, status, usage = os.wait4(process.pid, 0)
                    process.returncode = os.waitstatus_to_exitcode(status)
                    break
                time.sleep(0.05)
        row = dict(name=name, argv=list(map(str, argv)), exit=process.returncode, observerTimeout=timed_out,
                   seconds=time.monotonic() - start, cpuSeconds=usage.ru_utime + usage.ru_stime,
                   maxRSSKiB=usage.ru_maxrss,
                   **{s: dict(path=logs[s].relative_to(out).as_posix(), **pin(logs[s])) for s in logs})
        report["calls"].append(row)
        save()
        print(name, process.returncode, flush=True)
        return process.returncode, logs["stdout"].read_bytes(), logs["stderr"].read_bytes()

    save()
    compile_env = dict(PATH="/nonexistent", KEXE_ALLOW="35,37,38,39",
                       KEXE_CAP_RESOURCES_35=str(out), KEXE_STACK_BYTES="8388608")
    runner_source = out / "runner.kotoba"
    runner_source.write_bytes((ROOT / "seed/x86_64-kx64-runner.kotoba").read_bytes())
    runner = out / "runner.elf"
    fmt = "runner" if machine == 183 else "kx64-runner"
    code, stdout, stderr = call("runner-build", [compiler, "compile", runner_source, "--target", target,
        "--output", runner, "--format", fmt, "--runtime-profile", args.runtime_profile], compile_env)
    if code or stderr or not runner.is_file():
        report.update(status="rejected-runner-build")
        save()
        return 2
    assert f":runtime-profile :{args.runtime_profile}".encode() in stdout
    runner.chmod(0o700)
    report["runner"] = dict(source=pin(runner_source), image=elf(runner, machine))
    for row in report["workloads"]:
        name = row["workload"]
        original = package / "ports" / f"official-{name}.kotoba"
        assert pin(original)["sha256"] == table[name]["sourceSHA256"]
        namespace = re.match(rb"\(ns ([a-z0-9.-]+) ", original.read_bytes())
        assert namespace
        module = namespace[1].decode()
        root = out / name / "src"
        library = root / (module.replace(".", "/").replace("-", "_") + ".kotoba")
        library.parent.mkdir(parents=True)
        library.write_bytes(original.read_bytes())
        source = root / "proof/native_entry.kotoba"
        source.parent.mkdir()
        n = 1 if args.iteration_profile == "one-body" else counts[name]
        source.write_bytes(entry.read_bytes().replace(b"[embench.workload :as", b"[" + namespace[1] + b" :as").replace(
            b"(workload/bench-verify 1)", f"(workload/bench-verify {n})".encode()))
        lock = out / f"{name}.ksl"
        lock.write_text(f"KSL1\nentry {source}\nroot {root}\n" +
                        "".join(f"file {pin(p)['sha256']} {p}\n" for p in sorted((library, source))))
        image, payload = out / f"{name}.container", out / f"{name}.bin"
        row.update(iterations=n, originalSource=pin(original), stagedSource=pin(library),
                   entry=pin(source), sourceLock=pin(lock), status="building")
        flags = ["--source-path", root, "--source-lock", lock, "--source-lock-sha256", pin(lock)["sha256"]]
        argv = [compiler, "compile", source, "--target", "aarch64-macos" if machine == 183 else target,
                "--output", image] + ([] if machine == 183 else ["--format", "kx64-v1"]) + flags
        code, _, stderr = call(name + "-compile", argv, compile_env)
        if code or stderr or not image.is_file():
            row.update(status="rejected-native-compile")
            save()
            continue
        if machine == 183:
            code, _, stderr = call(name + "-extract", [compiler, "extract-native", image,
                                       "--symbol", "main", "--output", payload], compile_env)
            if code or stderr or not payload.is_file():
                row.update(status="rejected-native-extract")
                save()
                continue
        else:
            header, raw = image.read_bytes().split(b"\n\n", 1)
            match = re.fullmatch(rb"KX64V1 x86_64-linux sysv-ctx-v11 ([0-9]+) 0", header)
            assert match and len(raw) == int(match[1]) and raw[0] == 0xe9
            payload.write_bytes(raw)
        row.update(image=pin(image), payload=pin(payload), status="running")
        save()
        env = dict(PATH="/nonexistent", KEXE_ALLOW="-", KEXE_FUEL="1000000000000",
                   KEXE_STRUCTURED_REPORT="1", KEXE_ARENA_USE="1", KEXE_WALL_SECONDS=str(args.wall_seconds))
        code, stdout, stderr = call(name + "-run", [runner, payload, "0", "0",
                   "aarch64" if machine == 183 else "x86_64", "-"], env, args.wall_seconds + 15)
        result = re.fullmatch(rb"\{:status :ok :result 1 :fuel \{:initial ([0-9]+) :remaining ([0-9]+)\}\}\n", stdout)
        counters = arena(stderr)
        valid = result is not None and int(result[1]) == 1000000000000 and 0 <= int(result[2]) <= int(result[1])
        fuel = int(result[1]) - int(result[2]) if valid else None
        expected = reference[name]
        predicted = expected["expectedSample"]["benchmarkFuel"] + expected["expectedSample"]["verifyFuel"] + 2
        row.update(status="native-result-one" if code == 0 and valid and counters is not None else "rejected-native-execution",
                   resultOne=code == 0 and valid, arena=counters, totalFuel=fuel,
                   finalArenaMatchesReference=counters == arena(expected["expectedStderr"].encode()) if n == counts[name] else None,
                   predictedTotalFuelWithAdapter=predicted if n == counts[name] else None,
                   totalFuelMatchesAdapterPrediction=fuel == predicted if n == counts[name] else None)
        save()
    assert all(pin(ROOT / p) == v for p, v in sources.items())
    passed = sum(row.get("status") == "native-result-one" for row in report["workloads"])
    arena_count = sum(row.get("finalArenaMatchesReference") is True for row in report["workloads"])
    fuel_count = sum(row.get("totalFuelMatchesAdapterPrediction") is True for row in report["workloads"])
    report.update(status="completed-diagnostic-only", nativeResultOneCount=passed,
                  all17ArenaReferenceMatchCount=arena_count, adapterFuelPredictionMatchCount=fuel_count)
    save()
    return 0 if passed == 19 and (args.iteration_profile == "one-body" or arena_count == fuel_count == 19) else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    proof = parser.add_mutually_exclusive_group(required=True)
    proof.add_argument("--one", type=Path)
    proof.add_argument("--complete", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runtime-profile", required=True, choices=("standard-v1", "large-vectors-v1"))
    parser.add_argument("--iteration-profile", choices=("one-body", "m104-counts"), default="m104-counts")
    parser.add_argument("--wall-seconds", type=int, choices=range(1, 601), default=300)
    parser.add_argument("--package", type=Path, default=ROOT / "bench/embench/reproduce-20261015")
    parser.add_argument("--entry", type=Path, default=ROOT / "bench/embench/proof-v1/native-entry.kotoba")
    args = parser.parse_args()
    args.one = args.one.resolve() if args.one else None
    args.complete = args.complete.resolve() if args.complete else None
    try:
        raise SystemExit(main(args))
    except Exception as error:
        path = args.output.resolve() / "observations.json"
        if path.is_file():
            report = json.loads(path.read_text())
            report.update(status="rejected-observer", error=type(error).__name__ + ": " + str(error))
            atomic_json(path, report)
        raise
