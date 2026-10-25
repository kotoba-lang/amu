#!/usr/bin/env python3
"""Compile the same pinned 19 Kotoba ports with an evidenced intermediate selfhost compiler."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PKG = REPO / "bench/embench/reproduce-20261015"
EVIDENCE = Path(__file__).resolve().parent
sys.path.insert(0, str(PKG / "tools"))
import repro_lib as R


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_selfhost_record(variant, spec, unity_hash, unity_bytes, compiler_hash):
    record = json.loads((REPO / spec["selfhostEvidence"]).read_text())
    if spec["selfhostEvidenceKind"] == "reciprocal-codegen":
        require(record["sourceTreeCommit"] == spec["compilerSourceCommit"], "reciprocal source commit does not match evidence")
        require(record["seedUnity"]["sha256"] == unity_hash and record["seedUnity"]["bytes"] == unity_bytes,
                "reciprocal unity does not match selfhost evidence")
        fixed = record["fixedPoint"]
        require(fixed["allStagesByteIdentical"] and fixed["stages"] == ["G1", "G2", "G3"],
                "reciprocal compiler is not recorded as a G1=G2=G3 fixed point")
        require(fixed["nativeImage"]["sha256"] == compiler_hash, "reciprocal fixed-point image hash mismatch")
        require(record["bootstrap"]["sha256"] == sha256(REPO / "seed/bootstrap/adopted-20261012.bin"),
                "reciprocal evidence names a different adopted bootstrap")
    elif spec["selfhostEvidenceKind"] == "msub-fixed-point":
        require(record["status"] == "PASS" and record["native_selfhost"], "MSub selfhost record did not pass")
        require(record["source_bytes"] == unity_bytes and record["source_sha256"] == unity_hash,
                "MSub unity does not match selfhost evidence")
        require(record["backend_source_sha256"] == R.sha(R.git_show(spec["compilerSourceCommit"], "seed/41-a64gen.kotoba")),
                "MSub backend source hash mismatch")
        stages = record["stages"]
        require([stage["generation"] for stage in stages] == [1, 2, 3], "MSub fixed-point stages are incomplete")
        require({stage["native_sha256"] for stage in stages} == {compiler_hash}, "MSub fixed-point image hash mismatch")
        require(record["adopted_bootstrap_sha256"] == sha256(REPO / "seed/bootstrap/adopted-20261012.bin"),
                "MSub evidence names a different adopted bootstrap")
    else:
        raise SystemExit(f"{variant}: unknown selfhost evidence kind")


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("reciprocal", "msub"), required=True)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    args = parser.parse_args()
    R.require_macos_arm64()
    config = json.loads((EVIDENCE / "compiler-variants.json").read_text())
    spec = config["variants"][args.variant]
    compiler = REPO / spec["compilerImage"]
    expected_sources = json.loads((REPO / config["portImageTable"]).read_text())
    workloads = R.load(config["workloads"])
    names = sorted(row["workload"] for row in workloads)
    require(set(expected_sources) == set(names), "pinned port image table is not full-19")
    require(args.loader.is_file(), "trusted native loader is missing")
    require(compiler.stat().st_size == spec["compilerImageBytes"] and sha256(compiler) == spec["compilerImageSHA256"],
            "intermediate compiler image differs from its fixed-point pin")
    unity, modules = R.unity(spec["compilerSourceCommit"])
    unity_hash = R.sha(unity)
    require(len(unity) == spec["sourceUnityBytes"] and unity_hash == spec["sourceUnitySHA256"],
            "compiler source unity differs from its registered source pin")
    verify_selfhost_record(args.variant, spec, unity_hash, len(unity), sha256(compiler))
    require(args.record.exists() is False or not any(args.record.iterdir()), "record directory already contains files")
    args.record.mkdir(parents=True, exist_ok=True)
    out = R.fresh_dir(args.out)
    report = {
        "status": "RUNNING",
        "variant": args.variant,
        "compilerSourceCommit": spec["compilerSourceCommit"],
        "compilerSourceModules": len(modules),
        "compilerSourceUnity": {"bytes": len(unity), "sha256": unity_hash},
        "compilerImage": {"bytes": compiler.stat().st_size, "sha256": sha256(compiler)},
        "selfhostEvidence": spec["selfhostEvidence"],
        "portsSourceCommit": config["portsSourceCommit"],
        "loader": {"bytes": args.loader.stat().st_size, "sha256": sha256(args.loader)},
        "started": time.time(),
        "images": {},
    }
    table = {}
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    for workload in names:
        source = PKG / "ports" / f"official-{workload}.kotoba"
        source_hash = sha256(source)
        require(source_hash == expected_sources[workload]["sourceSHA256"], f"{workload}: port source pin mismatch")
        result = R.compile_port(args.loader, compiler, source.read_bytes(), out, f"official-{workload}")
        table[workload] = {
            "sourceSHA256": source_hash,
            "kseed": result["kseed"],
            "native": result["native"],
            "exports": result["exports"],
        }
        report["images"][workload] = table[workload]
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"{args.variant:10} {workload:15} {result['native']['sha256'][:16]}", flush=True)
    report["status"] = "PASS_COMPILED_19_PINNED_PORTS"
    report["ended"] = time.time()
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.record / "build-report.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.record / "images.json").write_text(json.dumps(table, indent=2, sort_keys=True) + "\n")
    print(f"PASS {args.variant}: {len(table)}/19 ports compiled")


if __name__ == "__main__":
    main()
