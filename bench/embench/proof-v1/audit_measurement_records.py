#!/usr/bin/env python3
"""Audit retained ARM candidate records, never grant campaign qualification.

No compiler, benchmark, shell command or network request is executed. The
reviewed repository anchors the byte graph; input process reports remain
unsigned observations, not independent execution or native verdict authority.
"""
import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

from campaign import canonical_bytes, require, workload_names

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/seed"))
SPEC = importlib.util.spec_from_file_location(
    "measurement_observer", ROOT / "scripts/seed/check-native-benchmark-host.py")
H = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(H)
C = H.C
PACKAGE = ROOT / "bench/embench/reproduce-20261015"
ANCHOR = ROOT / "docs/evidence/native-benchmark-host-20261026/measurement-host-controls-r4.json"
FACTORY = ("wrong-host-source", "wrong-registry", "unsupported-x86-host", "missing-profile",
           "unknown-profile", "standard-profile", "duplicate-profile", "existing-output")
RUNTIME = ("payload-hash", "payload-truncated", "payload-appended", "payload-symlink",
           "payload-directory", "unknown-workload", "negative-workload", "nondecimal-workload",
           "reduced-registered-count", "increased-diagnostic-count", "unknown-execution-profile",
           "missing-argument", "extra-argument", "unmetered-fuel", "empty-fuel", "zero-fuel",
           "insufficient-fuel")


def read_record(base, relative):
    path = Path(relative)
    require(not path.is_absolute() and path.parts and
            all(part not in (".", "..") for part in path.parts), "bounded record path required")
    current = base
    for part in path.parts:
        current = current / part
        require(not current.is_symlink(), "symlink record refused")
    require(current.is_file() and current.stat().st_size <= 16 * 1024 * 1024,
            "bounded regular record required")
    return current.read_bytes()


def decode(raw):
    def invalid_constant(value):
        raise ValueError("non-finite JSON value refused: " + value)
    return json.loads(raw, object_pairs_hook=H.unique_fields, parse_constant=invalid_constant)


def pin_bytes(raw):
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def pinned(raw, expected, label):
    require(type(expected) is dict and set(expected) == {"bytes", "sha256"}
            and type(expected["bytes"]) is int and expected["bytes"] == len(raw)
            and expected["sha256"] == hashlib.sha256(raw).hexdigest(), label + " pin differs")


def audit(directory):
    directory = directory.resolve()
    raw_report = read_record(directory, "observations.json")
    report = decode(raw_report)
    anchor = decode(ANCHOR.read_bytes())
    require(report["status"] == "native-candidate-observed" and report["mode"] == "registered",
            "registered complete ARM candidate required")
    require(all(report[key] is False for key in
                ("performanceQualified", "nativeVerdictAuthority", "fullQualification")),
            "observer cannot promote qualification")
    for key in ("compiler", "host", "hostSource", "registry"):
        require(canonical_bytes(report[key]) == canonical_bytes(anchor[key]),
                "reviewed " + key + " identity differs")
    for key in ("hostSource", "registry"):
        staged = "host.kotoba" if key == "hostSource" else "registry.kotoba"
        pinned(read_record(directory, staged), report[key], "staged " + key)
    paths = [p for p in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines()
             if p and not p.startswith("#")]
    sources = {p: C.pin(ROOT / p) for p in ("seed/FULL-MANIFEST", *paths)}
    require(report["sources"] == anchor["sources"], "reviewed complete source graph differs")
    source_current = report["sources"] == sources and all(
        C.pin(ROOT / path) == report[key] for key, path in
        (("hostSource", "seed/bench/host-arm.kotoba"), ("registry", "seed/bench/registry-arm.kotoba")))
    current_observer = C.pin(ROOT / "scripts/seed/check-native-benchmark-host.py")
    require(report["observer"] in (current_observer, anchor["observer"]), "reviewed observer identity differs")
    pinned(read_record(directory, "observer.py"), report["observer"], "staged observer")
    for relative, digest in C.DATA_PINS.items():
        require(C.pin(PACKAGE / relative)["sha256"] == digest, "reference source pin differs")
    reference_path = PACKAGE / "round-sa-m104-20261015/records/round/expected-accounting-mw.json"
    pinned(reference_path.read_bytes(), report["accountingReference"], "accounting reference")
    references = {row["workload"]: row for row in decode(reference_path.read_bytes())}
    counts = {row["workload"]: row["n"] for row in decode(
        (PACKAGE / "round-sa-m104-20261015/workloads.json").read_bytes())}
    names = workload_names()
    require(sorted(references) == sorted(counts) == names, "full19 reference coverage required")
    calls = report["calls"]
    require([row["name"] for row in calls] == ["build", *FACTORY, *RUNTIME, *names],
            "complete ordered process record coverage required")
    streams = {}
    for call in calls:
        name = call["name"]
        require(type(call["exit"]) is int, "terminal process exit required")
        streams[name] = {}
        for suffix in ("stdout", "stderr"):
            raw = read_record(directory, name + "." + suffix)
            pinned(raw, call[suffix], name + "." + suffix)
            streams[name][suffix] = raw
    build = streams["build"]
    argv = calls[0]["argv"]
    require(len(argv) == 8 and Path(argv[0]).name == "F2.elf"
            and argv[1:3] == ["bench-build", "aarch64-linux"]
            and [Path(value).name for value in argv[3:6]] == ["host.kotoba", "registry.kotoba", "host.elf"]
            and argv[6:] == ["--runtime-profile", "large-vectors-v1"], "host build invocation differs")
    host_path = argv[5]
    compiler_path = argv[0]
    host_directory = Path(host_path).parent
    require(argv[3:5] == [str(host_directory / name) for name in ("host.kotoba", "registry.kotoba")],
            "staged build source paths differ")
    require(calls[0]["exit"] == 0 and not build["stderr"], "successful host build required")
    match = re.fullmatch(rb"\{:ok true, :target :aarch64-linux, :format :static, :code-bytes ([0-9]+), "
                         rb":bytes ([0-9]+), :runtime-profile :large-vectors-v1, "
                         rb":vector-descriptors 67108864\}\n", build["stdout"])
    require(match and 0 < int(match[1]) < int(match[2]) == report["host"]["bytes"],
            "explicit ARM large-vectors host build record required")
    for field, expected in (("factoryRefusals", FACTORY), ("runtimeRefusals", RUNTIME)):
        rows = report[field]
        require([row["name"] for row in rows] == list(expected)
                and all(row["passed"] is True for row in rows), "complete refusal observations required")
    by_call = {call["name"]: call for call in calls}
    for name in FACTORY:
        require(by_call[name]["exit"] in (1, 2) and by_call[name]["argv"][0] == compiler_path
                and b":ok true" not in streams[name]["stdout"], "factory refusal process differs")
    for name in RUNTIME:
        require(by_call[name]["exit"] == (120 if name == "insufficient-fuel" else 2)
                and by_call[name]["argv"][0] == host_path
                and b'"result":1' not in streams[name]["stdout"], "runtime refusal process differs")
    require(type(report["observedWorkloads"]) is int and report["observedWorkloads"] == 19
            and type(report["referenceMatchedWorkloads"]) is int
            and report["referenceMatchedWorkloads"] == 19, "full19 observation count required")
    require([row["workload"] for row in report["workloads"]] == names, "full sorted19 records required")
    floor_count = 0
    for index, row in enumerate(report["workloads"]):
        name = row["workload"]
        pinned((PACKAGE / "ports" / ("official-" + name + ".kotoba")).read_bytes(), row["source"], name)
        require(row["payload"] == anchor["workloads"][index]["payload"], "reviewed payload identity differs")
        require(row["valid"] is True and type(row["exit"]) is int and row["exit"] == 0
                and by_call[name]["exit"] == 0 and not streams[name]["stderr"], "successful workload process required")
        argv = by_call[name]["argv"]
        require(len(argv) == 5 and argv[0] == host_path and argv[1] == str(index)
                and argv[2] == str(host_directory / (name + ".bin")) and argv[3:] == [str(counts[name]), "0"],
                "registered workload invocation differs")
        observation = decode(streams[name]["stdout"])
        require(H.valid_observation(observation, index, counts[name], 0), "registered native receipt required")
        require(canonical_bytes(observation) == canonical_bytes(row["observation"]),
                "stored observation differs from raw stdout")
        expected = references[name]
        arena = C.arena(expected["expectedStderr"].encode())
        require(arena is not None and expected["n"] == counts[name], "reference arena/count differs")
        expected_arena = [arena[field] for field in C.FIELDS]
        require(observation["benchmarkFuel"] == expected["expectedSample"]["benchmarkFuel"]
                and observation["verifyFuel"] == expected["expectedSample"]["verifyFuel"]
                and observation["benchmarkArena"] == observation["finalArena"] == expected_arena
                and observation["warmSeed"] == (615896958 if name == "tarfind" else 0),
                "independent accounting differs")
        floor_count += observation["elapsedNs"] >= 1_000_000_000
    return dict(schema="amu.embench.measurement-record-audit.v1", records="consistent",
                inputObservation=pin_bytes(raw_report),
                reviewedAnchor=C.pin(ANCHOR), compiler=report["compiler"], host=report["host"],
                sourceGraphCurrent=source_current,
                observerSourceCurrent=report["observer"] == current_observer,
                originalCountWorkloads=19, rawRefusalRecords=len(FACTORY) + len(RUNTIME),
                observedOneSecondFloorWorkloads=floor_count, performanceQualified=False,
                nativeVerdictAuthority=False, campaignReady=False,
                limitation="unsigned retained records; no binary replay, host admission, C comparison, paired rounds or protocol-control qualification")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="retained ARM host directory, not an x86 factory directory")
    args = parser.parse_args()
    try:
        result = audit(args.directory)
    except (ValueError, KeyError, TypeError, OSError) as error:
        print("MEASUREMENT_RECORD_AUDIT REJECTED: " + str(error), file=sys.stderr)
        return 2
    print(canonical_bytes(result).decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
