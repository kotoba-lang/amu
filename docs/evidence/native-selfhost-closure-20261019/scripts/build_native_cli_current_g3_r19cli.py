#!/usr/bin/env python3
"""Build the Kotoba-native AMU combined CLI and its semantic frontend. r19cli (tick-50, JUN-11):
reader hot-path allocation cut on top of r18cli — kotoba_reader.kotoba
token-check now returns the end offset as :i64 (negative codes for its two
errors) so the per-token success path stops minting a result record +
nil-form + no-forms; skip-as reuses the atom reader's own form/forms fields
at kind 4 instead of minting nil-form + no-forms per skipped token; and the
read-form span wrapper reuses the inner result's forms field instead of
minting a fresh no-forms per form. All three are observation-identical
(rd-forms is only read at kind 2 or on read-delimited results; kind 4 is
counted by kind and consumed by pos). Closure = r16cli's 59 modules
(builder = G1 seed-unity). Output sha must not be compared byte-wise to
r18cli (reader module source changed); the fixture/locked probes and the
vector-slope probe gate it instead.
"""
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

BASE = Path("/Users/junkawasaki/github")
OUT = BASE / "workspaces/codex/kotoba-sema-native-bridge-20261017/artifacts/kotoba-core-selfhost-refactor-20261017/artifacts/native-cli-current-g3-r19cli"
OBJ = OUT / "obj"
LOGS = OUT / "logs"
ENTRY = BASE / "wt/codex/amu-selfhost-only-20261016/src/kotoba/compiler/selfhost_cli.kotoba"
IMAGE = BASE / "workspaces/codex/amu1323-rebuild-17-main-20261018/artifacts/G1.bin"
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

OUT.mkdir(parents=True, exist_ok=False)
OBJ.mkdir()
LOGS.mkdir()
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
prefix = [str(LOADER), str(IMAGE), "0", "0", "aarch64", "3,35,37,38,39", "--"]


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
modules = []
for line in run("modules", module_args).splitlines():
    if line.strip():
        namespace, path = line.split(" ", 1)
        modules.append((namespace, Path(path)))
if not modules or modules[-1][1] != ENTRY:
    raise SystemExit("module order did not end at the combined CLI entry")

for index, (namespace, source) in enumerate(modules, 1):
    object_path = OBJ / (namespace + ".kso")
    args = ["compile", str(source), "--emit-module"]
    if source == ENTRY:
        args.append("--entry")
    args.extend(["--object-dir", str(OBJ), "--output", str(object_path)])
    run(f"module-{index:02d}", args)
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
report = {
    "status": "linked-native-cli-closure",
    "entry": str(ENTRY),
    "moduleCount": len(modules),
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
}
(OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: report[k] for k in ("status", "moduleCount", "containerBytes", "containerSha256", "executed")}))
