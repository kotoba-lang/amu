#!/usr/bin/env python3
"""Stage and observe the native FS2 sealed snapshot candidate.

Kotoba owns the positive assertions. Python only stages inputs, launches the
compiler and native fixture, and checks process status/diagnostics. This is a
supplemental gate, not a compiler fixed-point or release qualification.
"""
import argparse
import errno
import fcntl
import hashlib
import json
import os
import platform
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def pin(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main(compiler, output):
    machine = platform.machine()
    assert platform.system() == "Linux" and machine in ("aarch64", "arm64", "x86_64")
    output.mkdir(parents=True, exist_ok=False)
    scope = output / "scope"
    scope.mkdir()
    source = ROOT / "seed/tests/fs2-snapshot.kotoba"
    image = output / "snapshot.elf"
    env = dict(PATH="/nonexistent", KEXE_ALLOW="35,37,38,39", KEXE_STACK_BYTES="8388608",
               KEXE_CAP_RESOURCES_35=f"{ROOT}:{output}")
    target = "x86_64-linux" if machine == "x86_64" else "aarch64-linux"
    compiled = subprocess.run([str(compiler), "compile", str(source), "--target", target,
                               "--output", str(image), "--format", "static"],
                              cwd=output, env=env, capture_output=True, timeout=900)
    assert compiled.returncode == 0 and image.is_file(), (compiled.returncode, compiled.stderr[-2000:])
    image.chmod(0o700)
    guest = dict(PATH="/nonexistent", KEXE_ALLOW="35,37,38,39", KEXE_STACK_BYTES="8388608",
                 KEXE_CAP_RESOURCES_35=str(scope), KEXE_COMMAND="1")
    data = scope / "input"
    checks = []
    for mode in ("positive", "empty", "binary", "wrong-size", "too-large", "double-open", "wrong-path", "range", "after-close", "symlink", "directory"):
        data.write_bytes(bytes(range(256)) * 256 + b"\0" if mode == "binary" else b"abcdef")
        path = data
        if mode == "symlink":
            path = scope / "link"
            path.symlink_to(data.name)
        elif mode == "directory":
            path = scope / "dir"
            path.mkdir()
        run_mode = "double-open" if mode in ("symlink", "directory") else mode
        result = subprocess.run([str(image), run_mode, str(path)], cwd=scope, env=guest,
                                capture_output=True, timeout=90)
        ok = mode in ("positive", "empty", "binary")
        assert result.returncode == (0 if ok else 126), (mode, result.returncode, result.stderr[-1000:])
        if not ok:
            assert b":stage 15}" in result.stderr, (mode, result.stderr[-1000:])
        checks.append({"name": mode, "exit": result.returncode})
    data.write_bytes(b"abcdef")
    ready, done = scope / "input.ready", scope / "input.done"
    proc = subprocess.Popen([str(image), "observed", str(data)], cwd=scope, env=guest,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 20
        while not ready.exists() and proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.005)
        assert ready.exists(), ("snapshot observer did not reach ready", proc.poll())
        descriptors = Path(f"/proc/{proc.pid}/fd")
        memfds = [p for p in descriptors.iterdir() if os.readlink(p).startswith("/memfd:")]
        assert len(memfds) == 1, ("snapshot memfd count", memfds)
        fd = os.open(memfds[0], os.O_RDWR)
        try:
            seals = fcntl.fcntl(fd, 1034)  # F_GET_SEALS
            assert seals & 15 == 15, ("missing write/grow/shrink/seal", seals)
            try:
                os.pwrite(fd, b"X", 0)
            except OSError as error:
                assert error.errno == errno.EPERM, error
            else:
                raise AssertionError("write to sealed snapshot succeeded")
        finally:
            os.close(fd)
        data.write_bytes(b"UVWXYZ")
        done.write_bytes(b"1")
        stdout, stderr = proc.communicate(timeout=20)
        assert proc.returncode == 0, ("observed", proc.returncode, stdout, stderr)
        checks.append({"name": "kernel-seals-and-source-mutation", "exit": proc.returncode, "seals": seals})
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate()
    report = {"status": "PASS_FS2_SNAPSHOT_CANDIDATE", "host": [platform.system(), machine],
              "compiler": pin(compiler), "source": pin(source), "image": pin(image), "checks": checks,
              "nativeFixtureOwnsPositiveAssertions": True, "compilerFixedPointQualified": False,
              "crossArchitectureQualified": False, "rootfsExtractionQualified": False}
    (output / "snapshot.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], machine)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve())
