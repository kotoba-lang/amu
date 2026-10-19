#!/usr/bin/env python3
"""r19cli self-rebuild probe (tick-51, JUN-11): the r19cli combined CLI drives its own
59-module closure through compile/link/extract-native.

Driver = native-cli-current-g3-r19cli/native_cli.bin (built by G1 seed-unity in
tick-50 after the reader hot-path allocation cut). Entry offset is read from the
r19cli build report (mainOffset), not hardcoded.

`modules` self-run output is G1 format (`<ns> <path>`); the legacy check-CLI format
(`project modules=N` + `module=<ns>`) is accepted too. Namespace->source mapping is
verified against the r19cli build report either way (closure set + order checks).

Resumable: a killed run is re-invoked and continues; modules already compiled are
skipped via logs/module-NN.ok markers (report.json records resumedSkips). A fresh
run has no markers and is equivalent to the r16cli probe's exist_ok=False semantics.

Comparison note (r16cli precedent): G1(seed-unity) vs self-rebuild output did NOT
byte-match at r16; the fixpoint was G2=G3. The same comparison is recorded here
either way; a non-match is measured fact, not failure.
"""
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

BASE = Path("/Users/junkawasaki/github")
ART = BASE / "workspaces/codex/kotoba-sema-native-bridge-20261017/artifacts/kotoba-core-selfhost-refactor-20261017/artifacts"
OUT = ART / "native-cli-selfrebuild-r19cli"
OBJ = OUT / "obj"
LOGS = OUT / "logs"
ENTRY = BASE / "wt/codex/amu-selfhost-only-20261016/src/kotoba/compiler/selfhost_cli.kotoba"
IMAGE = ART / "native-cli-current-g3-r19cli/native_cli.bin"
PRIOR_REPORT = ART / "native-cli-current-g3-r19cli/report.json"
LOADER = BASE / "workspaces/codex/amu1323-rebuild-17-main-20261018/host/kexe-loader"
ROOTS = [
    BASE / "wt/codex/amu-selfhost-only-20261016/src",
    BASE / "workspaces/codex/kotoba-core-selfhost-refactor-20261017/compiler-src-with-runtime-overlay",
    BASE / "wt/codex/kotoba-runtime-selfhost-main/src",
    BASE / "kotoba-lang/kotoba-lang/src",
    BASE / "kotoba-lang/osaho/src",
    BASE / "wt/codex/artifact-core-kotoba-selfhost-20261016/src",
    BASE / "wt/codex/kotoba-hir-selfhost-20261016/src",
    BASE / "kotoba-lang/coll/src",
    BASE / "wt/codex/kotoba-text-selfhost-20261016/src",
    BASE / "kotoba-lang/bytes/src",
    BASE / "kotoba-lang/error/src",
    BASE / "workspaces/codex/kotoba-core-selfhost-refactor-20261017/artifacts/selfhost-overlay-r9probe",
]

ENTRY_OFFSET = json.loads(PRIOR_REPORT.read_text())["mainOffset"]

OUT.mkdir(parents=True, exist_ok=True)
OBJ.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)
env = dict(os.environ)
env.update(
    KEXE_COMMAND="1",
    KEXE_CAP_RESOURCES_35=":".join(str(p) for p in [OUT, *ROOTS]),
    KEXE_FUEL="off",
    KEXE_VECTORS="4194304",
    KEXE_VECTOR_ITEMS="134217728",
    KEXE_STRING_POOL="268435456",
    KEXE_PAIRS="67108864",
    KEXE_CPU_SECONDS="1800",
    KEXE_WALL_SECONDS="1800",
    TMPDIR=str(OUT),
)
prefix = [str(LOADER), str(IMAGE), str(ENTRY_OFFSET), "0", "aarch64", "3,35,37,38,39", "--"]
print(f"self-rebuild driver: {IMAGE} sha256={hashlib.sha256(IMAGE.read_bytes()).hexdigest()} offset={ENTRY_OFFSET}", flush=True)
resumed_skips = 0


def run(name, args):
    result = subprocess.run(prefix + args, cwd=OUT, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, timeout=1800)
    (LOGS / (name + ".stdout")).write_text(result.stdout)
    (LOGS / (name + ".stderr")).write_text(result.stderr)
    if result.returncode:
        raise SystemExit(f"{name} failed ({result.returncode}): {result.stderr.strip()}")
    return result.stdout


module_args = ["modules", str(ENTRY)]
for root in ROOTS:
    module_args.extend(["--source-path", str(root)])
module_args.append("--unpinned")
raw = run("modules", module_args)
prior = {m["namespace"]: Path(m["source"]) for m in json.loads(PRIOR_REPORT.read_text())["modules"]}
namespaces = []
paths = {}
header = None
for line in raw.splitlines():
    line = line.strip()
    if not line:
        continue
    if line.startswith("project modules="):
        header = int(line.split("=", 1)[1])
        continue
    if line.startswith("module="):
        namespaces.append(line.split("=", 1)[1])
        continue
    parts = line.split(" ", 1)
    if len(parts) != 2:
        raise SystemExit(f"unrecognized modules line: {line!r}")
    namespaces.append(parts[0])
    paths[parts[0]] = Path(parts[1])
if header is not None and header != len(namespaces):
    raise SystemExit(f"modules header {header} != parsed {len(namespaces)}")
missing = [ns for ns in namespaces if ns not in prior]
if missing:
    raise SystemExit(f"namespaces absent from r19cli report (closure drift): {missing}")
if set(namespaces) != set(prior):
    raise SystemExit(f"closure set drift: self-only={set(namespaces)-set(prior)} prior-only={set(prior)-set(namespaces)}")
mismatch = [ns for ns in namespaces if ns in paths and paths[ns] != prior[ns]]
if mismatch:
    raise SystemExit(f"self-run source paths disagree with r19cli report: {mismatch}")
modules = [(ns, prior[ns]) for ns in namespaces]
if not modules or modules[-1][1] != ENTRY:
    raise SystemExit("module order did not end at the combined CLI entry")
print(f"modules resolved: {len(modules)} (order from self-run, paths verified against r19cli report)", flush=True)

for index, (namespace, source) in enumerate(modules, 1):
    object_path = OBJ / (namespace + ".kso")
    marker = LOGS / f"module-{index:02d}.ok"
    if marker.exists() and object_path.exists() and object_path.stat().st_size > 0:
        resumed_skips += 1
        print(f"skipped {index}/{len(modules)} {namespace} (resume)", flush=True)
        continue
    args = ["compile", str(source), "--emit-module"]
    if source == ENTRY:
        args.append("--entry")
    args.extend(["--object-dir", str(OBJ), "--output", str(object_path)])
    run(f"module-{index:02d}", args)
    marker.write_text("")
    print(f"compiled {index}/{len(modules)} {namespace} {object_path.stat().st_size} bytes", flush=True)

root_object = OBJ / (modules[-1][0] + ".kso")
container = OUT / "native_cli.kseed"
run("link", ["link", str(root_object), "--object-dir", str(OBJ), "--output", str(container)])
native_image = OUT / "native_cli.bin"
extract = subprocess.run(prefix + ["extract-native", str(container), "--symbol", "main", "--output", str(native_image)],
                         cwd=OUT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, timeout=1800)
(LOGS / "extract-native.stdout").write_text(extract.stdout)
(LOGS / "extract-native.stderr").write_text(extract.stderr)
if extract.returncode:
    raise SystemExit(f"extract-native failed ({extract.returncode}): {extract.stderr.strip()}")
match = re.search(r":offset\s+(\d+)", extract.stdout)
if not match:
    raise SystemExit(f"extract-native omitted main offset: {extract.stdout!r}")
main_offset = int(match.group(1))
payload = container.read_bytes()
native_payload = native_image.read_bytes()
prior_report = json.loads(PRIOR_REPORT.read_text())
report = {
    "status": "linked-native-cli-closure",
    "probe": "self-rebuild-r19cli",
    "driverImage": str(IMAGE),
    "driverSha256": hashlib.sha256(IMAGE.read_bytes()).hexdigest(),
    "entryOffset": ENTRY_OFFSET,
    "entry": str(ENTRY),
    "moduleCount": len(modules),
    "resumedSkips": resumed_skips,
    "modules": [{"namespace": namespace, "source": str(path),
                 "objectBytes": (OBJ / (namespace + ".kso")).stat().st_size}
                for namespace, path in modules],
    "container": str(container),
    "containerBytes": len(payload),
    "containerSha256": hashlib.sha256(payload).hexdigest(),
    "nativeImage": str(native_image),
    "nativeImageBytes": len(native_payload),
    "nativeImageSha256": hashlib.sha256(native_payload).hexdigest(),
    "mainOffset": main_offset,
    "executed": False,
    "comparison": {
        "against": "native-cli-current-g3-r19cli",
        "containerMatch": hashlib.sha256(payload).hexdigest() == prior_report["containerSha256"],
        "nativeImageMatch": hashlib.sha256(native_payload).hexdigest() == prior_report["nativeImageSha256"],
        "priorContainerSha256": prior_report["containerSha256"],
        "priorNativeImageSha256": prior_report["nativeImageSha256"],
    },
}
(OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: report[k] for k in ("status", "moduleCount", "containerBytes", "containerSha256", "nativeImageSha256")}))
print(json.dumps(report["comparison"]))
