#!/usr/bin/env python3
"""Create and verify proof-v1 schedules and result manifests.

This module is intentionally independent from the platform timing driver.  The
driver must execute the emitted schedule verbatim and append one attempt record
for every scheduled position, including rejected and failed observations.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import random
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ZERO_HASH = "0" * 64
ARM_FOR = {"A": "kotoba-amu", "B": "c-reference"}
ORDERS = ("ABBA", "BAAB") * 5
BOOTSTRAP_SAMPLES = 10000
BOOTSTRAP_SEED = 104
PENDING_NATIVE_GATE = "native-measurement-gate-pending"


def canonical_bytes(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def sealed_hash(manifest: dict) -> str:
    copy = dict(manifest)
    copy["bundleSha256"] = ZERO_HASH
    return hashlib.sha256(canonical_bytes(copy)).hexdigest()


def workload_names() -> list[str]:
    data = json.loads((ROOT.parent / "reproduce-20261015" / "round-sa-m104-20261015" / "workloads.json").read_text())
    return sorted(row["workload"] for row in data)


def make_schedule() -> dict:
    events = []
    for workload in workload_names():
        for round_number, order in enumerate(ORDERS, 1):
            for position, symbol in enumerate(order, 1):
                events.append({
                    "workload": workload,
                    "round": round_number,
                    "order": order,
                    "sequencePosition": position,
                    "arm": ARM_FOR[symbol],
                })
    return {
        "schemaVersion": 1,
        "protocolId": "kotoba-amu-embench-proof-v1",
        "events": events,
    }


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_schedule(schedule: dict) -> None:
    expected = make_schedule()
    require(schedule == expected, "schedule differs from the preregistered 19 x 10 x 4 order")
    require(len(schedule["events"]) == 760, "schedule must contain exactly 760 positions")


def _attempt_key(item: dict) -> tuple:
    return tuple(item[key] for key in ("workload", "round", "order", "sequencePosition", "arm"))


def _percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * p
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - index) + ordered[upper] * (index - lower)


def summarize(manifest: dict) -> dict:
    schedule = make_schedule()
    attempts = manifest.get("attempts", [])
    require(760 <= len(attempts) <= 2280, "manifest must retain 760 scheduled positions and at most three attempts each")
    groups = [(key, list(rows)) for key, rows in itertools.groupby(attempts, key=_attempt_key)]
    require([key for key, _ in groups] == [_attempt_key(event) for event in schedule["events"]],
            "attempts do not follow the fixed schedule")
    selected = []
    for key, rows in groups:
        numbers = [item.get("attemptNumber") for item in rows]
        require(all(type(number) is int for number in numbers) and
                numbers == list(range(1, len(rows) + 1)), f"non-contiguous attempt numbers for {key}")
        require(len(rows) <= 3, f"more than three attempts for {key}")
        for index, item in enumerate(rows):
            require(type(item.get("accepted")) is bool and type(item.get("selected")) is bool,
                    f"attempt acceptance/selection must be booleans for {key}")
            require(item.get("reasons") == [] if item["accepted"] else bool(item.get("reasons")),
                    f"acceptance and rejection reasons disagree for {key}")
            if index < len(rows) - 1:
                require(not item["accepted"], f"attempts continued after acceptance for {key}")
                require(item.get("reasons") == ["cpu-qualification"] and
                        item.get("correctness", {}).get("passed") is True and
                        item.get("cpuQualification", {}).get("passed") is False,
                        f"retry is allowed only for CPU qualification for {key}")
        accepted_indexes = [index for index, item in enumerate(rows) if item.get("accepted")]
        selected_rows = [item for item in rows if item.get("selected")]
        if accepted_indexes:
            first = accepted_indexes[0]
            require(first == len(rows) - 1, f"attempts continued after acceptance for {key}")
            require(selected_rows == [rows[first]], f"first accepted attempt must be selected for {key}")
            selected.append(rows[first])
        else:
            require(not selected_rows, f"rejected attempts cannot be selected for {key}")

    reasons = []
    ratios = []
    per_workload = []
    normalization = manifest.get("normalization", {})
    expected_normalization = {row["workload"]: 4 / row["multiplier"] for row in json.loads(
        (ROOT.parent / "reproduce-20261015/round-sa-m104-20261015/workloads.json").read_text())}
    require(normalization == expected_normalization, "normalization differs from the pinned iteration counts")
    for workload in workload_names():
        accepted = [item for item in selected if item["workload"] == workload]
        summary = {"workload": workload, "acceptedPositions": len(accepted), "pairedRatios": [], "medianRatio": None}
        per_workload.append(summary)
        if len(accepted) != 40:
            reasons.append(f"{workload}: accepted {len(accepted)}/40")
            continue
        if not all(type(item.get("elapsedNs")) is int and item["elapsedNs"] >= 1000000000
                   for item in accepted):
            reasons.append(f"{workload}: elapsed time below the one-second floor or invalid")
            continue
        if not all(item.get("correctness", {}).get("passed") is True for item in accepted):
            reasons.append(f"{workload}: correctness did not pass")
            continue
        if not all(cpu_passes(item.get("cpuQualification", {})) for item in accepted):
            reasons.append(f"{workload}: CPU qualification did not pass")
            continue
        factor = normalization.get(workload)
        if type(factor) not in (int, float) or not math.isfinite(factor) or factor <= 0:
            reasons.append(f"{workload}: invalid normalization factor")
            continue
        paired = []
        for round_number in range(1, 11):
            round_rows = [item for item in accepted if item["round"] == round_number]
            a = [item["elapsedNs"] for item in round_rows if item["arm"] == "kotoba-amu"]
            b = [item["elapsedNs"] for item in round_rows if item["arm"] == "c-reference"]
            require(len(a) == 2 and len(b) == 2, f"{workload}: incomplete round {round_number}")
            paired.append(factor * statistics.median(a) / statistics.median(b))
        ratio = statistics.median(paired)
        ratios.append(ratio)
        summary.update(pairedRatios=paired, medianRatio=ratio)

    complete = len(ratios) == 19 and not reasons
    geometric_mean = math.exp(statistics.mean(math.log(value) for value in ratios)) if complete else None
    seed = manifest.get("statistics", {}).get("bootstrapSeed")
    require(type(seed) is int and seed == BOOTSTRAP_SEED, "statistics.bootstrapSeed must be the preregistered 104")
    ci = None
    if complete:
        rng = random.Random(seed)
        boot = []
        for _ in range(BOOTSTRAP_SAMPLES):
            # The 19 workloads are a fixed corpus, not samples from a workload
            # population. Resample paired rounds WITHIN each workload instead.
            sample = [statistics.median(rng.choices(row["pairedRatios"], k=10))
                      for row in per_workload]
            boot.append(math.exp(statistics.mean(math.log(value) for value in sample)))
        ci = [_percentile(boot, 0.025), _percentile(boot, 0.975)]
    return {
        "complete": complete,
        "perWorkload": per_workload,
        "geometricMean": geometric_mean,
        "confidenceInterval95": ci,
        "bootstrapSeed": seed,
        "rejectionReasons": reasons,
    }


def cpu_passes(cpu: dict) -> bool:
    names = ("preIdlePercent", "duringIdlePercent", "backgroundIdlePercent")
    return (cpu.get("passed") is True and all(
        type(cpu.get(name)) in (int, float) and math.isfinite(cpu[name]) and 70 <= cpu[name] <= 100
        for name in names) and cpu.get("thermalState") == "nominal")


def check_schema(value, schema: dict, root: dict, location: str = "manifest") -> None:
    """Validate the checked-in schema's deliberately small vocabulary.

    Unsupported keywords fail closed rather than silently skipping a constraint.
    This keeps verification offline and does not require pip dependencies.
    """
    supported = {"$schema", "$id", "$ref", "$defs", "title", "description", "type", "const", "enum",
                 "required", "properties", "additionalProperties", "items", "prefixItems", "minItems",
                 "maxItems", "uniqueItems", "minProperties", "maxProperties", "minimum", "maximum",
                 "exclusiveMinimum", "pattern"}
    require(not set(schema) - supported, f"unsupported schema keyword at {location}")
    if "$ref" in schema:
        require(schema["$ref"].startswith("#/$defs/"), "only local definition references are supported")
        check_schema(value, root["$defs"][schema["$ref"].split("/")[-1]], root, location)
        return
    if "const" in schema:
        require(type(value) is type(schema["const"]) and value == schema["const"], f"constant mismatch at {location}")
    if "enum" in schema:
        require(any(type(value) is type(entry) and value == entry for entry in schema["enum"]),
                f"enum mismatch at {location}")
    kinds = {"object": type(value) is dict, "array": type(value) is list,
             "string": type(value) is str, "integer": type(value) is int,
             "number": type(value) in (int, float) and math.isfinite(value),
             "boolean": type(value) is bool, "null": value is None}
    types = schema.get("type", list(kinds))
    if isinstance(types, str):
        types = [types]
    require(any(kinds[kind] for kind in types), f"type mismatch at {location}")
    if type(value) is dict:
        require(set(schema.get("required", [])) <= set(value), f"missing required fields at {location}")
        require(schema.get("minProperties", 0) <= len(value) <= schema.get("maxProperties", math.inf),
                f"property count at {location}")
        for key, entry in value.items():
            child = schema.get("properties", {}).get(key, schema.get("additionalProperties", {}))
            require(child is not False, f"unexpected field at {location}.{key}")
            if child is not True:
                check_schema(entry, child, root, location + "." + key)
    if type(value) is list:
        require(schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", math.inf), f"array length at {location}")
        if schema.get("uniqueItems"):
            require(len({json.dumps(entry, sort_keys=True) for entry in value}) == len(value), f"duplicate at {location}")
        for index, entry in enumerate(value):
            prefix = schema.get("prefixItems", [])
            child = prefix[index] if index < len(prefix) else schema.get("items", {})
            check_schema(entry, child, root, f"{location}[{index}]")
    if type(value) in (int, float):
        require(math.isfinite(value), f"nonfinite value at {location}")
        require(schema.get("minimum", -math.inf) <= value <= schema.get("maximum", math.inf), f"number bounds at {location}")
        require(value > schema.get("exclusiveMinimum", -math.inf), f"exclusive minimum at {location}")
    if type(value) is str and "pattern" in schema:
        import re
        require(re.search(schema["pattern"], value) is not None, f"pattern mismatch at {location}")


def verify_artifacts(manifest: dict, bundle_dir: Path) -> None:
    paths = set()
    bundle_dir = bundle_dir.resolve()
    for artifact in manifest["artifacts"]:
        relative = Path(artifact["path"])
        require(not relative.is_absolute() and ".." not in relative.parts and relative.parts,
                "artifact must have a bounded relative path")
        require(relative.as_posix() not in paths, "duplicate artifact path")
        paths.add(relative.as_posix())
        path = bundle_dir / relative
        require(path.resolve().is_relative_to(bundle_dir), "artifact escapes bundle directory")
        require(not path.is_symlink() and path.is_file(), f"missing artifact: {relative}")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"], f"artifact hash mismatch: {relative}")


def verify_manifest(manifest: dict, bundle_dir: Path) -> None:
    schema = json.loads((ROOT / "result-manifest.schema.json").read_text())
    check_schema(manifest, schema, schema)
    require(manifest.get("protocolId") == "kotoba-amu-embench-proof-v1", "protocol ID mismatch")
    require(manifest.get("workloads") == workload_names(), "workload list must be the sorted full-19 set")
    require(manifest.get("bundleSha256") == sealed_hash(manifest), "bundle hash mismatch")
    verify_artifacts(manifest, bundle_dir)
    verify_runtime_profile(manifest, bundle_dir)
    controls = manifest["negativeControls"]
    expected_controls = json.loads((ROOT / "protocol.json").read_text())["negativeControls"]
    require([row["name"] for row in controls] == expected_controls, "negative control names/order differ")
    paths = {row["path"] for row in manifest["artifacts"]}
    for control in controls:
        if control["status"] in ("passed", "failed"):
            require(control["evidencePath"] in paths, "executed control must reference a verified artifact")
        else:
            require(control["evidencePath"] is None, "pending control cannot have an execution artifact")
    calculated = summarize(manifest)
    require(manifest.get("statistics") == {key: calculated[key] for key in (
        "complete", "perWorkload", "geometricMean", "confidenceInterval95", "bootstrapSeed"
    )}, "statistics differ from deterministic recomputation")
    qualification = manifest.get("qualification", {})
    # Record validation does not prove native selfhost, process closure,
    # same-algorithm equivalence or executable negative controls. No qualified
    # result may pass this entry until that native measurement gate is wired.
    require(qualification.get("status") == "rejected" and
            qualification.get("evidenceLevel") == "unqualified",
            "native measurement qualification is pending; records cannot grant claim-grade status")
    require(qualification.get("reasons") == calculated["rejectionReasons"] + [PENDING_NATIVE_GATE],
            "rejection reasons differ")


def verify_runtime_profile(manifest: dict, bundle_dir: Path) -> None:
    """Bind declared resources to hashed build records, never grant provenance.

    A native measurement gate must still authenticate compiler generations,
    executed images and their actual resource/refusal behavior.
    """
    import re
    profile = manifest["runtimeProfile"]
    limit = {"standard-v1": 4194304, "large-vectors-v1": 67108864}[profile["id"]]
    require(profile["vectorDescriptors"] == limit, "runtime profile/vector descriptor mismatch")
    formats = {"x86_64-linux": {"static", "kx64-runner", "launcher"},
               "aarch64-linux": {"static", "runner", "launcher", "packed"}}
    require(profile["format"] in formats[profile["target"]], "runtime profile target/format mismatch")
    architectures = {"x86_64-linux": {"x86_64", "AMD64"},
                     "aarch64-linux": {"aarch64", "arm64"}}
    require(manifest["host"]["architecture"] in architectures[profile["target"]],
            "runtime profile does not match execution host architecture")
    artifacts = {item["path"]: item for item in manifest["artifacts"]}

    def bound(artifact):
        require(artifacts.get(artifact["path"]) == artifact,
                "runtime profile must reference a verified artifact")
        return bundle_dir / artifact["path"]

    bound(profile["compilerArtifact"])
    covered = []
    for binding in profile["executableBindings"]:
        covered.extend(binding["workloads"])
        image, record = bound(binding["image"]), bound(binding["buildRecord"])
        require(len({image, record, bound(profile["compilerArtifact"])}) == 3,
                "runtime profile compiler/image/build record must be distinct")
        match = re.fullmatch(
            rb"\{:ok true, :target :([a-z0-9_-]+), :format :([a-z0-9_-]+), :code-bytes ([0-9]+), "
            rb":bytes ([0-9]+), :runtime-profile :([a-z0-9_-]+), :vector-descriptors ([0-9]+)\}\n",
            record.read_bytes())
        require(match is not None, "runtime profile build record is not canonical")
        target, fmt, code_bytes, size, name, vectors = match.groups()
        require((target.decode(), fmt.decode(), name.decode(), int(vectors)) ==
                (profile["target"], profile["format"], profile["id"], limit),
                "runtime profile build record disagrees with descriptor")
        require(0 < int(code_bytes) < int(size) == image.stat().st_size,
                "runtime profile build record image size mismatch")
    require(sorted(covered) == workload_names(), "runtime profile bindings must cover all19 exactly once")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    emit = sub.add_parser("schedule")
    emit.add_argument("--out", type=Path)
    verify = sub.add_parser("verify")
    verify.add_argument("manifest", type=Path)
    args = parser.parse_args()
    if args.command == "schedule":
        value = canonical_bytes(make_schedule()).decode()
        if args.out:
            args.out.write_text(value)
        else:
            print(value, end="")
    else:
        manifest = json.loads(args.manifest.read_text())
        verify_manifest(manifest, args.manifest.parent)
        print("PROOF_V1_RECORDS PASS; QUALIFICATION REJECTED: " + PENDING_NATIVE_GATE)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
