#!/usr/bin/env python3
"""Observe the closed native ARM measurement-host candidate, not a score.

Amu builds the host and every workload. This observer stages unchanged bytes,
captures all process outputs and checks records; it is not native verdict or
performance authority. x86 host/payload admission and built semantic mutation
controls remain separate mandatory work.
"""
import argparse
import json
import importlib.util
import shutil
import subprocess
from pathlib import Path

from native_process_profile import atomic_json

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("candidate", ROOT / "scripts/seed/check-embench-native-candidate.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


def unique_fields(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate native receipt field")
    return result


def valid_observation(row, index, n, diagnostic):
    scalars = ("elapsedNs", "benchmarkFuel", "verifyFuel", "warmSeed", "highwaterAfterReset", "highwaterAfterVerify")
    integers = dict(workloadId=index, iterations=n, diagnostic=diagnostic, result=1, warmupBodies=1, calls=1)
    flags = dict(verifyOutsideTiming=True, sameContextVerify=True, resetIncluded=False, performanceQualified=False)
    keys = {"schema", "benchmarkArena", "finalArena", *scalars, *integers, *flags}
    return (isinstance(row, dict) and set(row) == keys
        and row["schema"] == "KOTOBA_NATIVE_BENCH_CANDIDATE_V1"
        and all(type(row[k]) is int and row[k] == value for k, value in integers.items())
        and all(row[k] is value for k, value in flags.items())
        and all(type(row[k]) is int and row[k] >= 0 for k in scalars)
        and all(type(row[k]) is list and len(row[k]) == 17
                and all(type(v) is int and v >= 0 for v in row[k]) for k in ("benchmarkArena", "finalArena"))
        and row["highwaterAfterVerify"] >= row["highwaterAfterReset"])


def main(a):
    compiler, machine, target, receipt, sources = C.provenance(
        a.one.resolve() if a.one else None, a.complete.resolve() if a.complete else None)
    assert (machine == 183 and not a.arm_controls) or (machine == 62 and a.arm_controls and a.full_counts)
    corpus = a.corpus.resolve()
    original_report = json.loads((corpus / "observations.json").read_text())
    assert original_report["compiler"] == C.elf(compiler, machine)
    assert original_report["sources"] == sources
    rows = original_report["workloads"]
    assert len(rows) == 19 and len({r["workload"] for r in rows}) == 19
    assert all(r["sourceUnchanged"] and r["calls"][0]["exit"] == 0
               and r["exports"] and all(e["valid"] for e in r["exports"]) for r in rows)
    out = a.output.resolve()
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    (out / "observer.py").write_bytes(Path(__file__).read_bytes())
    host_source = out / "host.kotoba"
    registry_source = out / "registry.kotoba"
    shutil.copy2(a.host_source.resolve() if a.host_source else ROOT / "seed/bench/host-arm.kotoba", host_source)
    shutil.copy2(ROOT / "seed/bench/registry-arm.kotoba", registry_source)
    host = out / "host.elf"
    report = dict(status="running", compiler=C.elf(compiler, machine), receipt=C.pin(receipt),
        sources=sources, hostSource=C.pin(host_source), registry=C.pin(registry_source),
        observer=C.pin(Path(__file__)), calls=[], workloads=[],
        performanceQualified=False, nativeVerdictAuthority=False,
        fullQualification=False, builtSemanticMutationControls=False,
        mode="registered" if a.full_counts else "diagnostic-one-body")
    reference_path = ROOT / "bench/embench/reproduce-20261015/round-sa-m104-20261015/records/round/expected-accounting-mw.json"
    assert C.pin(reference_path)["sha256"] == C.DATA_PINS["round-sa-m104-20261015/records/round/expected-accounting-mw.json"]
    references = {row["workload"]: row for row in json.loads(reference_path.read_text())}
    assert len(references) == 19
    report["accountingReference"] = C.pin(reference_path)

    def persist():
        atomic_json(out / "observations.json", report)

    def run(name, argv, env, timeout=300):
        try:
            r = subprocess.run(list(map(str, argv)), cwd=out, env={"PATH": "/nonexistent", **env},
                               capture_output=True, timeout=timeout)
            code, stdout, stderr = r.returncode, r.stdout, r.stderr
        except subprocess.TimeoutExpired as e:
            code, stdout, stderr = "observer-timeout", e.stdout or b"", e.stderr or b""
        (out / f"{name}.stdout").write_bytes(stdout)
        (out / f"{name}.stderr").write_bytes(stderr)
        report["calls"].append(dict(name=name, argv=list(map(str, argv)), exit=code,
            stdout=C.pin(out / f"{name}.stdout"), stderr=C.pin(out / f"{name}.stderr")))
        persist()
        print(name, code, stdout[:180].decode(errors="replace"), stderr[:180].decode(errors="replace"), flush=True)
        return code, stdout, stderr

    compile_env = dict(KEXE_ALLOW="35,37,38,39", KEXE_CAP_RESOURCES_35=str(out), KEXE_STACK_BYTES="8388608")
    argv = [compiler, "bench-build", "aarch64-linux", host_source, registry_source, host,
            "--runtime-profile", "large-vectors-v1"]
    persist()
    code, stdout, stderr = run("build", argv, compile_env)
    if code or stderr or not host.is_file():
        report["status"] = "refused-host-build"
        persist()
        return 2
    assert b":runtime-profile :large-vectors-v1" in stdout
    host.chmod(0o755)
    report["host"] = C.elf(host, 183)
    refusals = []
    mutated = out / "mutated-host.kotoba"
    mutated.write_bytes(host_source.read_bytes() + b"\n;; not the pinned source\n")
    bad_registry = out / "mutated-registry.kotoba"
    bad_registry.write_bytes(registry_source.read_bytes() + b"\n;; not the pinned registry\n")
    for label, args in (
        ("wrong-host-source", ["aarch64-linux", mutated, registry_source]),
        ("wrong-registry", ["aarch64-linux", host_source, bad_registry]),
        ("unsupported-x86-host", ["x86_64-linux", host_source, registry_source]),
    ):
        destination = out / f"{label}.elf"
        code, stdout, stderr = run(label, [compiler, "bench-build", *args, destination,
            "--runtime-profile", "large-vectors-v1"], compile_env)
        refusals.append(dict(name=label, passed=code in (1, 2) and not destination.exists()))
    for label, suffix in (
        ("missing-profile", []),
        ("unknown-profile", ["--runtime-profile", "unknown"]),
        ("standard-profile", ["--runtime-profile", "standard-v1"]),
        ("duplicate-profile", ["--runtime-profile", "large-vectors-v1", "--runtime-profile", "large-vectors-v1"]),
    ):
        destination = out / f"{label}.elf"
        code, stdout, stderr = run(label, [compiler, "bench-build", "aarch64-linux",
            host_source, registry_source, destination, *suffix], compile_env)
        refusals.append(dict(name=label, passed=code in (1, 2) and not destination.exists()))
    existing_pin = C.pin(host)
    code, stdout, stderr = run("existing-output", argv, compile_env)
    refusals.append(dict(name="existing-output", passed=code in (1, 2) and C.pin(host) == existing_pin))

    if machine == 62:
        # Public x86 compiler executes natively, but this closed command emits
        # only ARM hosts. Bind its exact bytes/exports to the actually executed
        # ARM qualification; never execute ARM code under x86 emulation.
        arm = json.loads(a.arm_controls.read_text())
        assert arm["status"] == "native-candidate-observed" and arm["mode"] == "registered"
        assert arm["sources"] == sources and arm["hostSource"] == report["hostSource"]
        assert arm["registry"] == report["registry"] and arm["host"] == report["host"]
        assert arm["observedWorkloads"] == arm["referenceMatchedWorkloads"] == 19
        assert len(arm["workloads"]) == 19 and all(r["valid"] and r["exit"] == 0 for r in arm["workloads"])
        assert all(r["passed"] for r in arm["factoryRefusals"] + arm["runtimeRefusals"])
        by_name = {r["workload"]: r for r in arm["workloads"]}
        for row in rows:
            name, symbol = row["workload"], row["registered"]["measuredSymbol"]
            exported = {e["name"]: e for e in row["exports"]}
            payload = corpus / name / (symbol + ".bin")
            assert C.pin(payload) == exported[symbol]["payload"] == by_name[name]["payload"]
            assert row["originalSource"] == by_name[name]["source"]
            report["workloads"].append(dict(workload=name, source=row["originalSource"],
                payload=C.pin(payload), exports=row["exports"], registered=row["registered"],
                matchesExecutedArmPayload=True, executedHere=False))
        assert all(r["passed"] for r in refusals)
        assert all(C.pin(ROOT / name) == value for name, value in sources.items())
        report.update(status="PASS_NATIVE_X86_BENCHMARK_FACTORY", factoryRefusals=refusals,
            armExecutionReference=C.pin(a.arm_controls), emittedArmHostMatches=True,
            observedWorkloads=19, executedArmHostHere=False, x86MeasurementHostSupported=False)
        persist()
        return 0

    # Exercise the real pinned host's admission and fuel failures. Keep every
    # failed input/output; never mutate an original source or payload in place.
    crc = rows[1]
    assert crc["workload"] == "crc32"
    good_payload = out / "control-crc32.bin"
    shutil.copy2(corpus / "crc32" / "benchmark-unchecked.bin", good_payload)
    assert C.pin(good_payload) == crc["exports"][0]["payload"]
    damaged = out / "control-damaged.bin"
    data = bytearray(good_payload.read_bytes())
    data[0] ^= 1
    damaged.write_bytes(data)
    truncated = out / "control-truncated.bin"
    truncated.write_bytes(good_payload.read_bytes()[:-1])
    appended = out / "control-appended.bin"
    appended.write_bytes(good_payload.read_bytes() + b"\0")
    symlink = out / "control-symlink.bin"
    symlink.symlink_to(good_payload.name)
    runtime_env = dict(KEXE_ALLOW="-", KEXE_FUEL="1000000000000", KEXE_STACK_BYTES="8388608",
                       KEXE_CPU_SECONDS="10", KEXE_WALL_SECONDS="10")
    runtime_refusals = []
    for label, args, fuel in (
        ("payload-hash", [1, damaged, 1, 1], "1000000000000"),
        ("payload-truncated", [1, truncated, 1, 1], "1000000000000"),
        ("payload-appended", [1, appended, 1, 1], "1000000000000"),
        ("payload-symlink", [1, symlink, 1, 1], "1000000000000"),
        ("payload-directory", [1, out, 1, 1], "1000000000000"),
        ("unknown-workload", [19, good_payload, 1, 1], "1000000000000"),
        ("negative-workload", [-1, good_payload, 1, 1], "1000000000000"),
        ("nondecimal-workload", ["1x", good_payload, 1, 1], "1000000000000"),
        ("reduced-registered-count", [1, good_payload, 1, 0], "1000000000000"),
        ("increased-diagnostic-count", [1, good_payload, 2, 1], "1000000000000"),
        ("unknown-execution-profile", [1, good_payload, 1, 2], "1000000000000"),
        ("missing-argument", [1, good_payload, 1], "1000000000000"),
        ("extra-argument", [1, good_payload, 1, 1, 0], "1000000000000"),
        ("unmetered-fuel", [1, good_payload, 1, 1], "off"),
        ("empty-fuel", [1, good_payload, 1, 1], ""),
        ("zero-fuel", [1, good_payload, 1, 1], "0"),
        ("insufficient-fuel", [1, good_payload, 1, 1], "1"),
    ):
        code, stdout, stderr = run(label, [host, *args], {**runtime_env, "KEXE_FUEL": fuel}, 20)
        runtime_refusals.append(dict(name=label,
            passed=code == (120 if label == "insufficient-fuel" else 2) and b'"result":1' not in stdout))
    report["runtimeRefusals"] = runtime_refusals
    for index, row in enumerate(rows):
        name = row["workload"]
        exported = {e["name"]: e for e in row["exports"]}
        symbol = row["registered"]["measuredSymbol"]
        payload = out / f"{name}.bin"
        shutil.copy2(corpus / name / f"{symbol}.bin", payload)
        assert C.pin(payload) == exported[symbol]["payload"]
        original = ROOT / "bench/embench/reproduce-20261015/ports" / f"official-{name}.kotoba"
        assert C.pin(original) == row["originalSource"]
        n = row["registered"]["n"] if a.full_counts else 1
        env = dict(KEXE_ALLOW="-", KEXE_FUEL="1000000000000", KEXE_STACK_BYTES="8388608",
                   KEXE_CPU_SECONDS=str(a.wall_seconds), KEXE_WALL_SECONDS=str(a.wall_seconds))
        code, stdout, stderr = run(name, [host, index, payload, n, 0 if a.full_counts else 1],
                                   env, a.wall_seconds + 30)
        observation = None
        if code == 0 and not stderr:
            try:
                observation = json.loads(stdout, object_pairs_hook=unique_fields)
            except (UnicodeDecodeError, ValueError):
                pass
        valid = valid_observation(observation, index, n, 0 if a.full_counts else 1)
        comparison = None
        if valid and a.full_counts:
            reference = references[name]
            expected_arena = C.arena(reference["expectedStderr"].encode())
            assert expected_arena is not None and reference["n"] == n
            comparison = dict(benchmarkFuel=observation["benchmarkFuel"] == reference["expectedSample"]["benchmarkFuel"],
                verifyFuel=observation["verifyFuel"] == reference["expectedSample"]["verifyFuel"],
                finalArena=observation["finalArena"] == [expected_arena[field] for field in C.FIELDS])
        report["workloads"].append(dict(workload=name, source=row["originalSource"],
            payload=C.pin(payload), observation=observation, valid=bool(valid), exit=code,
            observerReferenceComparison=comparison))
        persist()
    # Factory/source refusal is only part of qualification: no pass promotion.
    report["factoryRefusals"] = refusals
    report["observedWorkloads"] = sum(r["valid"] for r in report["workloads"])
    report["referenceMatchedWorkloads"] = (sum(r["observerReferenceComparison"] is not None
        and all(r["observerReferenceComparison"].values()) for r in report["workloads"]) if a.full_counts else None)
    report["status"] = ("native-candidate-observed" if report["observedWorkloads"] == 19
        and all(r["passed"] for r in refusals + runtime_refusals)
        and (not a.full_counts or report["referenceMatchedWorkloads"] == 19)
        else "native-candidate-incomplete")
    assert all(C.pin(ROOT / name) == value for name, value in sources.items())
    persist()
    return 0 if report["status"] == "native-candidate-observed" else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    producers = parser.add_mutually_exclusive_group(required=True)
    producers.add_argument("--one", type=Path)
    producers.add_argument("--complete", type=Path)
    parser.add_argument("--arm-controls", type=Path)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--host-source", type=Path)
    parser.add_argument("--full-counts", action="store_true")
    parser.add_argument("--wall-seconds", type=int, default=300)
    args = parser.parse_args()
    assert 1 <= args.wall_seconds <= 86400
    raise SystemExit(main(args))
