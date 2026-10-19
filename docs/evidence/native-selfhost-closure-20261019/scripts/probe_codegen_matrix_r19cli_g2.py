#!/usr/bin/env python3
"""JUN-11 tick-52: codegen route matrix for the r19cli SELF-REBUILD product (G2).

Driver image = native-cli-selfrebuild-r19cli-g2/native_cli.bin (the self-rebuild
fixpoint output; byte-identical to gen1 self-rebuild per tick-51). This measures
the "product 全域" codegen surface of the native-built AMU: which target/codegen
routes actually emit artifacts, which are refused, and whether the emitted
aarch64 code matches the recorded x86 evidence suite's aarch64 reference pins
(docs/evidence/native-x86_64-linux-20261015/suite.json).

Sections:
  program-codegen - 4 scalar suite programs through `compile --target
                    aarch64-macos` + `extract-native --symbol main`; compares
                    raw code against the suite's aarch64Reference.nativePin and
                    re-runs compile to test byte determinism.
  target-matrix   - `compile --target T` for x86_64-linux / x86_64-aiueos-
                    kernel-v1 / wasm32 / wasm / js: expected refusals recorded
                    verbatim (JUN-30 target-registration gap, ELF64/WASM
                    reachability from the combined CLI).
  emit-module     - `compile --emit-module` module-object route on a pinned-graph
                    module (kotoba.compiler.decimal-bits), twice, byte compare.
  inventory       - source-level facts: WASM emitter presence inside the 59-module
                    closure, x86 ELF64 emitter exclusion from the seed unity
                    MANIFEST, x86_64-aiueos-kernel-v1 absence from
                    target_names_core.parse.
"""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/Users/junkawasaki/github")
ART = BASE / "workspaces/codex/kotoba-sema-native-bridge-20261017/artifacts/kotoba-core-selfhost-refactor-20261017/artifacts"
G2 = ART / "native-cli-selfrebuild-r19cli-g2"
SUITE = BASE / "wt/codex/amu-selfhost-only-20261016/docs/evidence/native-x86_64-linux-20261015/suite.json"
SEED_ROOT = BASE / "wt/codex/amu-selfhost-only-20261016"
LOADER = BASE / "workspaces/codex/amu1323-rebuild-17-main-20261018/host/kexe-loader"
OUT = ART / "native-cli-codegen-matrix-r19cli-g2"
LOGS = OUT / "logs"
FIX = OUT / "fixtures"
OBJ = OUT / "obj"
REPORT = OUT / "report.json"

IMAGE = G2 / "native_cli.bin"
ENTRY_OFFSET = json.loads((G2 / "report.json").read_text())["mainOffset"]

# The suite cases chosen for the codegen matrix (all have aarch64Reference pins).
CASES = ["answer", "subtract", "quot-neg", "bits"]
# target-matrix spellings probed on the `answer` program.
TARGETS = ["x86_64-linux", "x86_64-aiueos-kernel-v1", "wasm32", "wasm", "js"]

OUT.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(exist_ok=True)
FIX.mkdir(exist_ok=True)
OBJ.mkdir(exist_ok=True)


def run_native(name, args, timeout=900):
    env = dict(os.environ)
    env.update(
        KEXE_COMMAND="1",
        KEXE_CAP_RESOURCES_35=":".join(str(p) for p in [OUT, FIX, OBJ, SEED_ROOT / "src"]),
        KEXE_FUEL="off",
        KEXE_VECTORS="4194304",
        KEXE_VECTOR_ITEMS="134217728",
        KEXE_STRING_POOL="268435456",
        KEXE_PAIRS="67108864",
        KEXE_CPU_SECONDS="900",
        KEXE_WALL_SECONDS="900",
        TMPDIR=str(OUT),
    )
    prefix = [str(LOADER), str(IMAGE), str(ENTRY_OFFSET), "0", "aarch64", "3,35,37,38,39", "--"]
    result = subprocess.run(prefix + args, cwd=OUT, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, timeout=timeout)
    (LOGS / (name + ".stdout")).write_text(result.stdout)
    (LOGS / (name + ".stderr")).write_text(result.stderr)
    return result.returncode, result.stdout, result.stderr


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_report():
    return json.loads(REPORT.read_text()) if REPORT.exists() else {
        "probe": "codegen-matrix-r19cli-g2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "driverImage": str(IMAGE),
        "driverNativeSha256": sha(IMAGE),
        "entryOffset": ENTRY_OFFSET,
    }


def save_report(report):
    report["timestamp"] = datetime.now(timezone.utc).isoformat()
    REPORT.write_text(json.dumps(report, indent=2) + "\n")


def section_program_codegen(report):
    suite = json.loads(SUITE.read_text())
    by_name = {c["name"]: c for c in suite["cases"]}
    results = []
    for name in CASES:
        case = by_name[name]
        src = FIX / (name + ".kotoba")
        src.write_text(case["source"])
        kseed = OUT / (name + ".kseed")
        kseed2 = OUT / (name + ".run2.kseed")
        raw = OUT / (name + ".bin")
        rc, out, err = run_native(f"compile-{name}",
                                  ["compile", str(src), "--target", "aarch64-macos", "--output", str(kseed)])
        rc2, _, _ = run_native(f"compile2-{name}",
                               ["compile", str(src), "--target", "aarch64-macos", "--output", str(kseed2)])
        entry = {"name": name, "compileRc": rc, "compileRc2": rc2,
                 "stdout": out.strip(), "stderr": err.strip()}
        if kseed.exists():
            entry["kseedBytes"] = kseed.stat().st_size
            entry["kseedSha256"] = sha(kseed)
            entry["compileDeterministic"] = (kseed2.exists() and sha(kseed2) == entry["kseedSha256"])
            rcx, outx, errx = run_native(f"extract-{name}",
                                         ["extract-native", str(kseed), "--symbol", "main", "--output", str(raw)])
            entry["extractRc"] = rcx
            entry["extractStdout"] = outx.strip()
            entry["extractStderr"] = errx.strip()
            if raw.exists():
                entry["rawBytes"] = raw.stat().st_size
                entry["rawSha256"] = sha(raw)
                ref = (case.get("aarch64Reference") or {}).get("nativePin") or {}
                entry["aarch64Reference"] = ref
                entry["matchesAarch64Reference"] = (
                    ref.get("bytes") == entry["rawBytes"]
                    and ref.get("sha256") == entry["rawSha256"])
        results.append(entry)
    report["programCodegen"] = results
    report["programCodegenAllCompiled"] = all(r["compileRc"] == 0 for r in results)
    report["programCodegenAllDeterministic"] = all(r.get("compileDeterministic") for r in results)
    report["programCodegenReferenceMatches"] = sum(1 for r in results if r.get("matchesAarch64Reference"))


def section_target_matrix(report):
    src = FIX / "answer.kotoba"
    if not src.exists():
        src.write_text(json.loads(SUITE.read_text())["cases"][0]["source"])
    matrix = []
    for target in TARGETS:
        out_path = OUT / f"target-{target.replace('/', '_')}.out"
        rc, out, err = run_native(f"target-{target}",
                                  ["compile", str(src), "--target", target, "--output", str(out_path)])
        matrix.append({"target": target, "rc": rc, "stdout": out.strip(), "stderr": err.strip(),
                       "artifactWritten": out_path.exists(),
                       "artifactSha256": sha(out_path) if out_path.exists() else None})
    report["targetMatrix"] = matrix


def section_emit_module(report):
    module = SEED_ROOT / "src/kotoba/compiler/decimal_bits.kotoba"
    runs = []
    for suffix in ("a", "b"):
        obj = OBJ / f"decimal_bits.{suffix}.kso"
        rc, out, err = run_native(f"emit-module-{suffix}",
                                  ["compile", str(module), "--emit-module",
                                   "--object-dir", str(OBJ), "--output", str(obj)])
        runs.append({"rc": rc, "stdout": out.strip(), "stderr": err.strip(),
                     "bytes": obj.stat().st_size if obj.exists() else None,
                     "sha256": sha(obj) if obj.exists() else None})
    report["emitModule"] = {
        "module": str(module), "moduleSha256": sha(module),
        "runs": runs,
        "bothRc0": all(r["rc"] == 0 for r in runs),
        "byteIdentical": (runs[0]["sha256"] is not None
                          and runs[0]["sha256"] == runs[1]["sha256"]),
    }


def section_inventory(report):
    g2_report = json.loads((G2 / "report.json").read_text())
    closure = [Path(m["source"]) for m in g2_report["modules"]]
    wasm_hits = {}
    for src in closure:
        try:
            text = src.read_text()
        except OSError:
            continue
        n = text.lower().count("wasm")
        if n:
            wasm_hits[str(src)] = n
    manifest = (SEED_ROOT / "seed/MANIFEST").read_text()
    tnc = (SEED_ROOT / "src/kotoba/compiler/target_names_core.kotoba").read_text()
    report["inventory"] = {
        "closureModuleCount": len(closure),
        "closureWasmMentions": wasm_hits,
        "wasmEmitterInClosure": any("emit" in k.lower() or "wasm_cli" in k for k in wasm_hits),
        "seedUnityManifestHasX86ElfRoute": any(
            line.strip().startswith(("seed/70-", "seed/71-", "seed/72-", "seed/73-"))
            for line in manifest.splitlines()),
        "x86ElfEmitterSource": str(SEED_ROOT / "seed/70-x86_64-linux.kotoba"),
        "x86ElfEmitterSha256": sha(SEED_ROOT / "seed/70-x86_64-linux.kotoba"),
        "aiueosTargetInTargetNamesCore": "x86_64-aiueos-kernel-v1" in tnc,
        "aiueosTargetInSeedTargetGate": False,  # drv-target-ok accepts only aarch64-macos (90-drv.kotoba)
        "targetNamesCoreSha256": sha(SEED_ROOT / "src/kotoba/compiler/target_names_core.kotoba"),
    }


def main():
    report = load_report()
    section_program_codegen(report)
    section_target_matrix(report)
    section_emit_module(report)
    section_inventory(report)
    save_report(report)
    summary = {
        "programCodegenAllCompiled": report["programCodegenAllCompiled"],
        "programCodegenAllDeterministic": report["programCodegenAllDeterministic"],
        "programCodegenReferenceMatches": report["programCodegenReferenceMatches"],
        "targetMatrix": [(m["target"], m["rc"], m["artifactWritten"]) for m in report["targetMatrix"]],
        "emitModuleBothRc0": report["emitModule"]["bothRc0"],
        "emitModuleByteIdentical": report["emitModule"]["byteIdentical"],
        "inventory": report["inventory"],
    }
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
