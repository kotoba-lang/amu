#!/usr/bin/env python3
"""Fault injection for wire 20's setup refusals: isolation-unavailable and setup-failed (JUN-292).

The spawn helper's child (seed/77 kxrt-sp-child) sets itself up before execve: dup3 of stdin and
stdout (stage 0), close_range of fd 3 and up (stage 1), prctl(PR_SET_NO_NEW_PRIVS) (stage 2) and,
when the :fs/app-data scope is granted, fchdir to its first root (stage 3). The helper names a
failed stage 1 or 2 `spawn/isolation-unavailable` and a failed stage 0 or 3 `spawn/setup-failed`
(exit 126), and the program never runs. check-spawn-runtime.py cannot make those calls fail; this
gate runs the same guest under a seccomp profile that makes one of them return EPERM:

  --fault close_range  -> spawn/isolation-unavailable, no marker file
  --fault fchdir       -> spawn/setup-failed, no marker file
  --fault none         -> the program runs (answer "0", the marker file exists): the control

The image itself installs its own filter only after forking the helper, so the outer profile is
the one the child meets. prctl and dup3 are not injected: the runtime and the container's process
start use them too. Python stages, writes the profiles and observes; the runtime and the guest are
Kotoba. Run on Linux arm64 with the pinned static root, one fault per container, e.g.:

  python3 scripts/seed/check-spawn-fault-injection.py --write-profile close_range OUT/close_range.json
  podman run --platform linux/arm64 --network none --security-opt seccomp=OUT/close_range.json \\
    -v REPO:REPO -v OUT:OUT python:3.12-slim python3 REPO/scripts/seed/check-spawn-fault-injection.py \\
    --compiler REPO/seed/bootstrap/aarch64-linux-static-root.elf --fault close_range --output OUT/close_range
"""
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "seed/x86_64-kx64-runner.kotoba"
S = "ARG_SEP"
WANT = {"close_range": b"spawn/isolation-unavailable", "fchdir": b"spawn/setup-failed"}
GUEST = ('(ns t (:export [main]))\n'
         '(defn main [] :i64\n'
         '  (let [a (typed-cap-call :process/spawn :string :string "/bin/sh' + S + '-c' + S + 'echo ran > mark")\n'
         '        b (typed-cap-call :io/write :string :string a)]\n'
         '    7))\n')


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def profile(fault):
    # everything allowed except the one injected failure: this container exists only for the case
    return {"defaultAction": "SCMP_ACT_ALLOW", "architectures": ["SCMP_ARCH_AARCH64"],
            "syscalls": [{"names": [fault], "action": "SCMP_ACT_ERRNO", "errnoRet": 1}]}


def main(compiler, fault, output):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "arm64"), "run on Linux arm64"
    output.mkdir(parents=True, exist_ok=False)
    art, scope = output / "artifacts", output / "scope"
    art.mkdir()
    scope.mkdir()
    producer = art / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)
    (art / "guest.kotoba").write_text(GUEST)
    (art / "runner.kotoba").write_bytes(RUNNER.read_bytes())
    cenv = {"PATH": "/nonexistent", "KEXE_CAP_RESOURCES_35": str(art), "KEXE_STACK_BYTES": "8388608"}
    calls = []
    for step, argv in [("compile", [producer, "compile", art / "guest.kotoba", "--target", "aarch64-macos", "--output", art / "guest.kseed"]),
                       ("pack", [producer, "compile", art / "runner.kotoba", "--target", "aarch64-linux", "--output", art / "guest.elf",
                                 "--format", "packed", "--payload", art / "guest.kseed"])]:
        r = subprocess.run(list(map(str, argv)), cwd=art, env=cenv, capture_output=True, timeout=1800)
        calls.append(dict(step=step, exit=r.returncode))
        assert r.returncode == 0 and not r.stderr, (step, r.returncode, r.stderr[-400:])
    image = art / "guest.elf"
    image.chmod(0o755)
    env = {"PATH": "/usr/bin:/bin", "KEXE_STRUCTURED_REPORT": "1", "KEXE_FUEL": "100000000",
           "KEXE_ALLOW": "20,35,37", "KEXE_CAP_RESOURCES_20": "/bin/sh", "KEXE_CAP_RESOURCES_35": str(scope)}
    x = subprocess.run([str(image)], env=env, capture_output=True, timeout=120)
    mark = scope / "mark"
    if fault == "none":
        assert x.returncode == 0 and x.stdout.startswith(b"0\n") and mark.read_text() == "ran\n", (x.returncode, x.stdout[-200:], x.stderr[-200:])
        verdict = "program ran"
    else:
        want = b"KEXE_TRAP {:kind :capability :capability :process/spawn :reason :" + WANT[fault] + b"}\n"
        assert x.returncode == 126 and want in x.stderr and not mark.exists(), (fault, x.returncode, x.stdout[-200:], x.stderr[-300:])
        verdict = "refused " + WANT[fault].decode() + ", program did not run"
    report = dict(status="PASS_SPAWN_FAULT_INJECTION", fault=fault, verdict=verdict, compiler=pin(compiler), image=pin(image),
                  runner=pin(RUNNER), exit=x.returncode, stdout=x.stdout.decode(errors="replace"),
                  stderr=x.stderr.decode(errors="replace"), calls=calls,
                  injected=None if fault == "none" else profile(fault),
                  host=[platform.system(), platform.machine(), platform.release()],
                  notCovered=["prctl (stage 2) and dup3 (stage 0) failures: the runtime and the container start use them too"])
    (output / "spawn-fault-injection.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], fault, verdict, flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--write-profile", nargs=2, metavar=("FAULT", "PATH"), help="write the seccomp profile for FAULT and exit")
    p.add_argument("--compiler", type=Path)
    p.add_argument("--fault", choices=("close_range", "fchdir", "none"))
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    if a.write_profile:
        fault, path = a.write_profile
        assert fault in WANT, fault
        Path(path).write_text(json.dumps(profile(fault), indent=2) + "\n")
    else:
        assert a.compiler and a.fault and a.output, "--compiler, --fault and --output are required"
        main(a.compiler.resolve(), a.fault, a.output.resolve())
