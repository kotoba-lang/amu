"""Build the JUN-29 C-free seed runner spike image (2026-10-20).

Measures the interpreter-route premise for the C-free seed runner: the runner's
logic (kotoba.runtime + the evaluator stack + this entry) compiles and links
through the closure recipe into a raw image, and the execution semantics
(read -> check -> evaluate) run with no C loader (see README.md in this
directory for the measured results).

This driver follows build_native_cli_current_g3_r19cli.py's flow exactly
(modules -> compile --emit-module -> link -> extract-native), with ENTRY
swapped for the spike entry and ROOTS covering the runtime module set. Module
enumeration is automatic: the `modules` subcommand resolves the entry's
require graph.

Machine-local paths are supplied through environment variables:

  CFREE_LOADER   path to the kexe-loader host binary (build-time executor)
  CFREE_IMAGE    path to the G1 seed-unity builder image
  CFREE_OUT      output directory (created; must not already exist)
  CFREE_ROOTS    os.pathsep-separated source roots for module resolution

ENTRY defaults to this directory's spike_cfree_runner.kotoba.
"""
import hashlib
import os
import re
import subprocess
from pathlib import Path

BASE = Path("/Users/junkawasaki/github")
HERE = Path(__file__).resolve().parent

OUT = Path(os.environ["CFREE_OUT"])
LOADER = Path(os.environ["CFREE_LOADER"])
IMAGE = Path(os.environ["CFREE_IMAGE"])
ENTRY = Path(os.environ.get("CFREE_ENTRY", HERE / "spike_cfree_runner.kotoba"))
ROOTS = [Path(p) for p in os.environ["CFREE_ROOTS"].split(os.pathsep) if p]

OBJ = OUT / "obj"
LOGS = OUT / "logs"
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
    raise SystemExit("module order did not end at the spike entry")

for index, (namespace, source) in enumerate(modules, 1):
    object_path = OBJ / (namespace + ".kso")
    args = ["compile", str(source), "--emit-module"]
    if source == ENTRY:
        args.append("--entry")
    args.extend(["--object-dir", str(OBJ), "--output", str(object_path)])
    run(f"module-{index:02d}", args)
    print(f"compiled {index}/{len(modules)} {namespace} {object_path.stat().st_size} bytes", flush=True)

root_object = OBJ / (modules[-1][0] + ".kso")
container = OUT / "cfree_runner.kseed"
run("link", ["link", str(root_object), "--object-dir", str(OBJ), "--output", str(container)])
native_image = OUT / "cfree_runner.bin"
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

print(f"{{\"status\": \"linked-cfree-runner-spike\", \"moduleCount\": {len(modules)}, "
      f"\"containerBytes\": {container.stat().st_size}, "
      f"\"containerSha256\": \"{hashlib.sha256(container.read_bytes()).hexdigest()}\", "
      f"\"mainOffset\": {main_offset}, \"executed\": false}}")
