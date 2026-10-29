#!/usr/bin/env python3
"""Stage unchanged original libraries and native export observations, not timing."""
import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--one", type=Path)
p.add_argument("--complete", type=Path)
p.add_argument("--out", type=Path, required=True)
a = p.parse_args()
repo = Path(__file__).resolve().parents[2]
one = a.one.resolve() if a.one else None
complete = a.complete.resolve() if a.complete else None
out = a.out.resolve()
sys.path.insert(0, str(repo / "scripts/seed"))
s = importlib.util.spec_from_file_location("candidate", repo / "scripts/seed/check-embench-native-candidate.py")
C = importlib.util.module_from_spec(s)
s.loader.exec_module(C)
compiler, machine, target, receipt, sources = C.provenance(one, complete)
package = repo / "bench/embench/reproduce-20261015"
C.verify_bundle_data(package, repo / "bench/embench/proof-v1/native-entry.kotoba")
table = json.loads((package / "round-sa-m104-20261015/expected/measured-images.json").read_text())
workloads = json.loads((package / "round-sa-m104-20261015/workloads.json").read_text())
assert len(table) == len(workloads) == 19
assert len({x["workload"] for x in workloads}) == 19
assert set(table) == {x["workload"] for x in workloads}
out.mkdir(mode=0o700, parents=True, exist_ok=False)
(out / "observer.py").write_bytes(Path(__file__).read_bytes())
report = dict(status="running", compiler=C.elf(compiler, machine), receipt=C.pin(receipt),
              observer=C.pin(Path(__file__)), sources=sources, executed=False,
              performanceQualified=False, qualificationReplacement=False, workloads=[])


def persist():
    C.atomic_json(out / "observations.json", report)


def run(row, directory, label, argv):
    try:
        r = subprocess.run(list(map(str, argv)), cwd=directory,
            env=dict(PATH="/nonexistent", KEXE_ALLOW="35,37,38,39",
                     KEXE_CAP_RESOURCES_35=str(out), KEXE_STACK_BYTES="8388608"),
            capture_output=True, timeout=300)
        status, stdout, stderr = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as e:
        status, stdout, stderr = "timeout", e.stdout or b"", e.stderr or b""
    (directory / f"{label}.stdout").write_bytes(stdout)
    (directory / f"{label}.stderr").write_bytes(stderr)
    row["calls"].append(dict(name=label, argv=list(map(str, argv)), exit=status,
        stdout=C.pin(directory / f"{label}.stdout"), stderr=C.pin(directory / f"{label}.stderr")))
    persist()
    print(row["workload"], label, status, flush=True)
    return status, stdout, stderr


persist()
for spec in workloads:
    name = spec["workload"]
    historical = table[name]
    original = package / "ports" / f"official-{name}.kotoba"
    identity = C.pin(original)
    assert identity["sha256"] == historical["sourceSHA256"]
    assert spec["nativeSHA256"] == historical["native"]["sha256"]
    assert spec["sourceFunctionsUnchanged"] is True and not spec["extraCaps"]
    assert isinstance(spec["n"], int) and spec["n"] > 0
    directory = out / name
    directory.mkdir(mode=0o700)
    src, lock, image = (directory / f"original.{suffix}" for suffix in ("kotoba", "ksl", "kseed"))
    src.write_bytes(original.read_bytes())
    assert C.pin(src) == identity
    lock.write_text(f"KSL1\nentry {src}\nfile {identity['sha256']} {src}\n")
    row = dict(workload=name, originalSource=identity, registered=spec, calls=[],
               exports=[], status="compiling", sourceUnchanged=True)
    report["workloads"].append(row)
    status, stdout, stderr = run(row, directory, "compile", [compiler, "compile", src,
        "--target", "aarch64-macos", "--output", image, "--source-lock", lock,
        "--source-lock-sha256", C.pin(lock)["sha256"]])
    if status or stderr or not image.is_file():
        row["status"] = "refused-native-library-compile"
        persist()
        continue
    row["image"] = C.pin(image)
    row["historicalContainerMatches"] = row["image"] == historical["kseed"]
    for symbol, (expected_offset, arity) in historical["exports"].items():
        assert re.fullmatch(r"[a-zA-Z0-9_-]+", symbol)
        payload = directory / f"{symbol}.bin"
        status, stdout, stderr = run(row, directory, symbol, [compiler, "extract-native",
            image, "--symbol", symbol, "--output", payload])
        header = re.fullmatch(rb'\{:ok true, :output "([^"\r\n]+)", :offset ([0-9]+), :length ([0-9]+), :arity ([0-9]+)\}\n', stdout)
        valid = status == 0 and not stderr and header is not None and payload.is_file()
        if valid:
            valid = (header[1].decode() == str(payload)
                and int(header[3]) == payload.stat().st_size and int(header[4]) == arity
                and 0 <= int(header[2]) < payload.stat().st_size and int(header[2]) % 4 == 0)
        row["exports"].append(dict(name=symbol, valid=bool(valid), arity=arity,
            offset=int(header[2]) if valid else None,
            historicalOffsetMatches=int(header[2]) == expected_offset if valid else False,
            payload=C.pin(payload) if valid else None,
            historicalPayloadMatches=C.pin(payload) == historical["native"] if valid else False))
    measured = {e["name"]: e for e in row["exports"]}
    assert spec["measuredSymbol"] in measured
    assert measured[spec["measuredSymbol"]]["arity"] == spec["measuredArity"]
    # xgboost's original verifier consumes (state, n); do not adapt its API.
    assert measured["verify-state"]["arity"] in (1, 2)
    row["verificationArguments"] = (["state"] if measured["verify-state"]["arity"] == 1
                                    else ["state", "registered-n"])
    assert spec["seedSymbol"] is None or measured[spec["seedSymbol"]]["arity"] == 1
    row["status"] = ("native-original-library-byte-identical" if
        row["historicalContainerMatches"] and all(e["valid"] and e["historicalOffsetMatches"]
        and e["historicalPayloadMatches"] for e in row["exports"])
        else "native-original-library-mismatch")
    assert C.pin(original) == identity and C.pin(src) == identity
    persist()
assert all(C.pin(repo / name) == value for name, value in sources.items())
historical = sum(row["status"] == "native-original-library-byte-identical" for row in report["workloads"])
passed = sum(row["sourceUnchanged"] and row["calls"][0]["exit"] == 0
             and bool(row["exports"]) and all(e["valid"] for e in row["exports"])
             for row in report["workloads"])
report.update(status="native-original-corpus-staged" if passed == 19 else "native-original-corpus-incomplete",
              observed=passed, historicalByteIdentical=historical)
persist()
print(report["status"], passed, "/19; historical equality", historical, "/19", flush=True)
raise SystemExit(0 if passed == 19 else 2)
