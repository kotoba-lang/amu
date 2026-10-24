#!/usr/bin/env python3
"""Build the canonical FS2 fixture and observe native Linux qualification.

Amu compiles the source; Kotoba asserts bytes and FS form semantics. Python
stages files and observes exits, diagnostics, ownership and cleanup. Fault
observers affect only their own children, with no hosted runtime fallback.
"""
import argparse
import hashlib
import json
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def pin(path):
    data = path.read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def main(compiler, out):
    machine = platform.machine()
    assert platform.system() == "Linux" and machine in ("aarch64", "arm64", "x86_64")
    out.mkdir(parents=True, exist_ok=False)
    calls = []
    source = ROOT / "seed/tests/fs2-product.kotoba"
    source_pin = pin(source)
    image = out / "fs2.elf"
    env = dict(PATH="/nonexistent", KEXE_ALLOW="35,37,38,39", KEXE_CAP_RESOURCES_35=":".join(map(str, [ROOT, out])), KEXE_STACK_BYTES="8388608")

    def observe(name, args, custom, expected=0, diagnostic=None, timeout=180):
        p = subprocess.run(list(map(str, args)), cwd=out, env=custom, capture_output=True, timeout=timeout)
        (out / (name + ".stdout")).write_bytes(p.stdout)
        (out / (name + ".stderr")).write_bytes(p.stderr)
        calls.append(dict(name=name, exit=p.returncode))
        (out / "calls.json").write_text(json.dumps(calls, indent=2) + "\n")
        assert p.returncode == expected, (name, p.returncode, p.stderr[-1000:])
        if diagnostic:
            assert diagnostic in p.stderr and b"KEXE_CLEANUP" not in p.stderr
        else:
            assert not p.stderr, (name, p.stderr[-1000:])
        return p

    target = "x86_64-linux" if machine == "x86_64" else "aarch64-linux"
    observe("compile", [compiler, "compile", source, "--target", target, "--output", image, "--format", "static"], env, timeout=900)
    image.chmod(0o755)

    def scope_for(name):
        scope = out / ("scope-" + name)
        scope.mkdir()
        return scope, dict(PATH="/nonexistent", KEXE_ALLOW="35,37,38,39", KEXE_CAP_RESOURCES_35=str(scope), KEXE_STACK_BYTES="8388608")

    positives = ("original-forms", "raw", "managed", "no-replace", "large", "managed-return", "managed-publish", "managed-publish-exclusive")
    for case in positives:
        scope, guest = scope_for(case)
        path = scope / "data" if case in ("raw", "large") else scope
        result = observe(case, [image, case, path], guest, timeout=300)
        assert not result.stdout
        assert not list(scope.glob("kotoba-output-*")), (case, "owned stage remains")
        if case in ("managed-publish", "managed-publish-exclusive"):
            assert (scope / "published").read_bytes() == b"preserved"

    for name, mode, extra, diagnostic in [
        ("fault", "managed-fault", {}, b":kind :signal"),
        ("fuel", "managed-fuel", {"KEXE_FUEL": "1000000"}, b":kind :signal"),
        ("cpu", "managed-signal", {"KEXE_CPU_SECONDS": "1"}, b":signal :SIGXCPU"),
        ("wall", "managed-signal", {"KEXE_WALL_SECONDS": "2"}, b":signal :SIGALRM"),
    ]:
        scope, guest = scope_for(name)
        observe(name, [image, mode, scope], {**guest, **extra}, expected=120, diagnostic=diagnostic, timeout=30)
        assert not list(scope.glob("kotoba-output-*")), (name, "owned stage remains")

    for sig in (signal.SIGINT, signal.SIGTERM):
        name = "external-" + sig.name
        scope, guest = scope_for(name)
        p = subprocess.Popen([str(image), "managed-signal", str(scope)], cwd=out, env=guest, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        deadline = time.monotonic() + 15
        try:
            while not (scope / "ready").exists() and time.monotonic() < deadline and p.poll() is None:
                time.sleep(0.005)
            assert (scope / "ready").exists(), (name, "fixture did not stage")
            p.send_signal(sig)
            stdout, stderr = p.communicate(timeout=15)
        except BaseException:
            p.kill()
            p.communicate()
            raise
        (out / (name + ".stdout")).write_bytes(stdout)
        (out / (name + ".stderr")).write_bytes(stderr)
        assert p.returncode == 120 and (":signal :" + sig.name).encode() in stderr and b"KEXE_CLEANUP" not in stderr
        assert not stdout and not list(scope.glob("kotoba-output-*"))
        calls.append(dict(name=name, exit=p.returncode))

    boundary_cases = ["close-consumed-eintr", "partial-read", "partial-write"] + [f"journal-{window}-{sig}" for window in ("directory", "file") for sig in ("sigint", "sigterm", "sigalrm", "sigxcpu")]
    errno_cases = ("write-eio", "fsync-eio", "chmod-eperm", "unlink-eacces", "fstat-eio", "entropy-enosys", "rename-enosys", "open-enosys")
    for script, cases in (("check-fs2-observed.py", boundary_cases), ("check-fs2-errno.py", errno_cases)):
        for case in cases:
            observe(case, [sys.executable, ROOT / "scripts/seed" / script, "--image", image, "--output", out / case, "--case", case], os.environ.copy(), timeout=45)
    assert pin(source) == source_pin
    report = dict(status="PASS_NATIVE_FS2_CURRENT_MATRIX", host=[platform.system(), machine], source=source_pin,
                  compiler=pin(compiler), image=pin(image), calls=calls, positiveFixtureCases=len(positives),
                  observedKernelBoundaries=len(boundary_cases), kernelErrnoCases=len(errno_cases),
                  nativeGuestOwnsPositiveAssertions=True, legacyRuntimeFallback=False, emulation=False,
                  allFaultRaceParityQualified=False, wholePublicCLIQualified=False)
    (out / "native-fs2.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], machine)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.compiler.resolve(), a.output.resolve())
