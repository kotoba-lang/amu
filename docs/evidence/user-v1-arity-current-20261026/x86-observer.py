"""Observe native x86 regeneration and user-v1 refusal; not a full gate substitute."""
import hashlib
import importlib.util
import json
import os
import platform
import resource
import struct
import subprocess
import time
from pathlib import Path

root = Path(__file__).resolve().parent
assert platform.system() == "Linux" and platform.machine() == "x86_64"
resource.setrlimit(resource.RLIMIT_STACK, (8388608, 8388608))

def pin(path):
    data = path.read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())

inputs = json.loads((root / "inputs.json").read_text())
for name, identity in inputs.items():
    assert Path(name).name == name and not (root / name).is_symlink()
    assert pin(root / name) == identity, name
out = root / "result"
out.mkdir(mode=0o700)
env = {"PATH": "/nonexistent", "KEXE_CAP_RESOURCES_35": str(out),
       "KEXE_STACK_BYTES": "8388608"}
calls = []

def run(name, argv, expected=0):
    started = time.monotonic()
    r = subprocess.run(list(map(str, argv)), cwd=out, env=env,
                       capture_output=True, timeout=900)
    (out / (name + ".stdout")).write_bytes(r.stdout)
    (out / (name + ".stderr")).write_bytes(r.stderr)
    calls.append(dict(name=name, exit=r.returncode, seconds=time.monotonic()-started))
    assert r.returncode == expected and not r.stderr, (name, r.returncode, r.stderr[-500:])

source = out / "full-unity.kotoba"
source.write_bytes((root / "full-unity.kotoba").read_bytes())
previous = root / "F0.elf"
previous.chmod(0o700)
generations = []
for n in (1, 2, 3):
    image = out / f"F{n}.elf"
    run(f"F{n}", [previous, "compile", source, "--target", "x86_64-linux",
                   "--output", image, "--format", "static"])
    image.chmod(0o700)
    assert pin(image) == inputs["F0.elf"], (n, pin(image))
    generations.append(pin(image))
    previous = image
src = out / "positive.kotoba"
src.write_text("(ns native-positive (:export [main]))\n(defn main [] :i64 42)\n")
run("check", [previous, "check", src])
binary = out / "positive.elf"
run("compile", [previous, "compile", src, "--target", "x86_64-linux",
                "--output", binary, "--format", "static"])
binary.chmod(0o700)
run("execute", [binary], expected=42)
spec = importlib.util.spec_from_file_location("user_check", root / "check-aiueos-user-elf-native.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
checker.main(previous, out / "user-v1")
for name, identity in inputs.items():
    assert pin(root / name) == identity, name
report = dict(schema="amu.native-x86-user-arity-review.v1", status="PASS",
              host=dict(system=platform.system(), machine=platform.machine()),
              source=pin(source), image=inputs["F0.elf"], generations=generations,
              calls=calls, userAbi=json.loads((out / "user-v1/aiueos-user-elf-native.json").read_text()),
              inputs=inputs, controllerQualifiedByThisObserver=False,
              fullTierQualifiedByThisObserver=False, performanceClaim=False)
(out / "qualified-native-x86.json").write_text(json.dumps(report, indent=2)+"\n")
print("PASS_NATIVE_X86_ARITY F1=F2=F3", report["image"]["sha256"], flush=True)
