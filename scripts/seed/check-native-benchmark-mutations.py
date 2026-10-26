#!/usr/bin/env python3
"""Build and execute semantic host mutations; Python only stages/observes.

Each mutation gets an isolated test compiler whose factory admits exactly
that mutant's hash instead of the production host hash. No production
whitelist, private guest escape, original library or runtime limit changes.
The candidate native host's fixed oracle and ordered guards must refuse the
executed mutant with its named native refusal, not a timeout or build error.
"""
import argparse
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

from native_process_profile import atomic_json

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("candidate", ROOT / "scripts/seed/check-embench-native-candidate.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def mutations(host):
    def change(old, new):
        assert host.count(old) == 1, old
        return host.replace(old, new)

    verify = "verified (kb-verifier verifier state (if (= (kb-verify-arity id) 2) count 0))"
    end = "end (kb-now 1) "
    before = "        " + verify
    assert host.count(end) == host.count(before) == 1
    inside = host.replace(end, "").replace(before, before + "\n        end (kb-now 1)")
    begin = "begin (kb-now 0)"
    reset = host.replace(begin, "").replace("seed-ok (kb-pure) high (kb-reset)", "seed-ok (kb-pure) " + begin + " high (kb-reset)")
    warm = host.replace(begin, "").replace("warm-phase (if", begin + "\n        warm-phase (if")
    assert host.count(begin) == host.count("seed-ok (kb-pure) high (kb-reset)") == host.count("warm-phase (if") == 1
    return [
        ("wrong-warm-count", "tarfind", 3201, change("warm (kb-invoke benchmark 1 0)", "warm (kb-invoke benchmark 2 0)")),
        ("missing-warm-seed", "tarfind", 3201, change(
            "seed (if (< (kb-seed id) 0) 0 (kb-invoke (+ payload (kb-seed id)) warm 0))", "seed 0")),
        ("missing-second-reset", "depthconv", 3203, change("seed-ok (kb-pure) high (kb-reset)", "seed-ok (kb-pure) high (kxrt-gl 760)")),
        ("verification-inside-clock", "crc32", 3003, inside),
        ("missing-verification", "crc32", 3003, change(verify, "verified 1")),
        ("wrong-benchmark-fuel", "crc32", 3202, change("(- initial after-bench)", "(inc (- initial after-bench))")),
        ("wrong-verification-fuel", "crc32", 3202, change("(- after-bench after-verify)", "(inc (- after-bench after-verify))")),
        ("missing-benchmark-snapshot", "depthconv", 3203, change("snap1 (kb-snapshot (+ (kxrt-g) 22000))", "snap1 (kb-zero (+ (kxrt-g) 22000) 136)")),
        ("missing-final-snapshot", "depthconv", 3203, change("snap2 (kb-snapshot (+ (kxrt-g) 22200))", "snap2 (kb-zero (+ (kxrt-g) 22200) 136)")),
        ("lowered-absolute-highwater", "depthconv", 2003, change("d (kxrt-gs 64 0)", "d (kxrt-gs 64 0) lowered (kxrt-gs 760 0)")),
        ("missing-fuel-reset", "depthconv", 2003, change("fuel (kxrt-store64 (+ (kxrt-ctx) 8) (kxrt-gl 168))", "fuel 0")),
        ("reset-inside-clock", "depthconv", 2004, reset),
        ("warmup-inside-clock", "crc32", 3003, warm),
    ]


def main(a):
    compiler, machine, target, receipt, sources = C.provenance(a.one.resolve(), None)
    assert machine == 183
    one = a.one.resolve()
    basis = a.controls.resolve()
    observed = json.loads((basis / "observations.json").read_text())
    assert observed["status"] == "native-candidate-observed" and observed["mode"] == "registered"
    assert observed["sources"] == sources and observed["compiler"] == C.elf(compiler, machine)
    assert observed["observedWorkloads"] == observed["referenceMatchedWorkloads"] == 19
    assert all(r["passed"] for r in observed["factoryRefusals"] + observed["runtimeRefusals"])
    host = (ROOT / "seed/bench/host-arm.kotoba").read_bytes()
    registry = ROOT / "seed/bench/registry-arm.kotoba"
    assert C.pin(ROOT / "seed/bench/host-arm.kotoba") == observed["hostSource"]
    assert C.pin(registry) == observed["registry"]
    paths = [p for p in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines() if p and not p.startswith("#")]
    unity = b"".join((ROOT / p).read_bytes() + b"\n" for p in paths)
    assert unity == (one / "full.kotoba").read_bytes()
    admitted = digest(host).encode()
    assert unity.count(admitted) == 1
    out = a.output.resolve()
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    (out / "observer.py").write_bytes(Path(__file__).read_bytes())
    staged_registry = out / "registry.kotoba"
    staged_registry.write_bytes(registry.read_bytes())
    runner = out / "runner.kotoba"
    runner.write_bytes((one / "runner.kotoba").read_bytes())
    report = dict(schema="amu.native-benchmark-semantic-controls.v1", status="running",
        performanceQualified=False, fullQualification=False, qualificationReplacement=False,
        nativeVerdictAuthority=False, nativeGuardAuthority=True,
        compiler=C.elf(compiler, machine), sources=sources, receipt=C.pin(receipt),
        positiveObservation=C.pin(basis / "observations.json"), hostSource=C.pin(ROOT / "seed/bench/host-arm.kotoba"),
        observer=C.pin(Path(__file__)), calls=[], mutations=[])

    def save():
        atomic_json(out / "observations.json", report)

    def run(directory, name, argv, env, expected=0):
        r = subprocess.run(list(map(str, argv)), cwd=out,
            env={"PATH": "/nonexistent", **env}, capture_output=True, timeout=360)
        (directory / (name + ".stdout")).write_bytes(r.stdout)
        (directory / (name + ".stderr")).write_bytes(r.stderr)
        report["calls"].append(dict(name=directory.name + "/" + name, argv=list(map(str, argv)),
            exit=r.returncode, stdout=C.pin(directory / (name + ".stdout")),
            stderr=C.pin(directory / (name + ".stderr"))))
        save()
        print(directory.name, name, r.returncode, flush=True)
        assert r.returncode == expected, (directory.name, name, r.returncode, r.stderr[-500:])
        if expected == 0:
            assert not r.stderr
        return r

    build_env = dict(KEXE_ALLOW="35,37,38,39", KEXE_CAP_RESOURCES_35=str(out), KEXE_STACK_BYTES="8388608")
    run_env = dict(KEXE_ALLOW="-", KEXE_FUEL="1000000000000", KEXE_STACK_BYTES="8388608",
                   KEXE_CPU_SECONDS="120", KEXE_WALL_SECONDS="120")
    rows = {r["workload"]: r for r in observed["workloads"]}
    save()
    for name, workload, refusal, changed in mutations(host.decode()):
        directory = out / name
        directory.mkdir(mode=0o700)
        mutant_source = directory / "host.kotoba"
        mutant_source.write_bytes(changed.encode())
        mutant_digest = digest(changed.encode()).encode()
        assert mutant_digest != admitted
        # Only the isolated test compiler's closed admission constant changes.
        source = directory / "compiler.kotoba"
        source.write_bytes(unity.replace(admitted, mutant_digest))
        container, producer, image = (directory / n for n in ("compiler.kseed", "compiler.elf", "host.elf"))
        run(directory, "compiler-build", [compiler, "compile", source, "--target", "aarch64-macos", "--output", container], build_env)
        run(directory, "compiler-pack", [compiler, "compile", runner, "--target", "aarch64-linux", "--output", producer,
            "--format", "packed", "--payload", container], build_env)
        producer.chmod(0o700)
        run(directory, "host-build", [producer, "bench-build", "aarch64-linux", mutant_source, staged_registry, image,
            "--runtime-profile", "large-vectors-v1"], build_env)
        image.chmod(0o700)
        # An emitted real host and a real original-count run are mandatory.
        row = rows[workload]
        index = row["observation"]["workloadId"]
        count = row["observation"]["iterations"]
        payload = basis / (workload + ".bin")
        assert C.pin(payload) == row["payload"]
        result = run(directory, "detect", [image, index, payload, count, 0], run_env, expected=2)
        assert not result.stdout and result.stderr == f"KREFUSE:{refusal}\n".encode(), (name, result.stdout, result.stderr)
        report["mutations"].append(dict(name=name, workload=workload, iterations=count,
            builtSuccessfully=True, executed=True, detectedBy="native named guard refusal", refusal=refusal,
            compilerSource=C.pin(source), compilerContainer=C.pin(container), compiler=C.elf(producer, 183),
            hostSource=C.pin(mutant_source), host=C.elf(image, 183), payload=C.pin(payload)))
        save()
    assert len(report["mutations"]) == 13
    assert all(C.pin(ROOT / name) == value for name, value in sources.items())
    assert C.pin(ROOT / "seed/bench/host-arm.kotoba") == report["hostSource"]
    report["status"] = "PASS_EXECUTED_NATIVE_BENCHMARK_MUTATIONS"
    save()
    print(report["status"], len(report["mutations"]), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--one", type=Path, required=True)
    parser.add_argument("--controls", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
