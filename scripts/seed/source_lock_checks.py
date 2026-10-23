"""Observe native regular-file source-lock acceptance/refusal; no compiler fallback."""
import hashlib
import json
import os
import socket
import subprocess
import tempfile
from pathlib import Path


def check_source_locks(compilers, out):
    out.mkdir(mode=0o700)
    # FIFO/socket fixtures need a native Linux filesystem. A macOS shared
    # mount can reject mknod independently of the compiler under observation.
    with tempfile.TemporaryDirectory(prefix="amu-lock-") as fixtures:
        return _check_source_locks(compilers, out, Path(fixtures))


def _check_source_locks(compilers, observations, out):
    src = out / "good.kotoba"
    src.write_text("(ns lock-boundary (:export [main]))\n(defn main [] :i64 42)\n")
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    text = f"KSL1\nentry {src}\nfile {sha(src)} {src}\n"
    positives = []
    for name in ("valid.ksl", "lock-WRITE_SEP-APPEND_SEP-EXISTS_SEP.ksl", "lock-言葉-é.ksl"):
        p = out / name
        p.write_text(text)
        positives.append(p)
    directory = out / "directory.ksl"
    directory.mkdir()
    fifo = out / "fifo.ksl"
    os.mkfifo(fifo)
    endpoint = out / "socket.ksl"
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    original_cwd = Path.cwd()
    try:
        os.chdir(out)
        sock.bind(endpoint.name)
    finally:
        os.chdir(original_cwd)
    link = out / "symlink.ksl"
    link.symlink_to(positives[0].name)
    oversized = out / "oversized.ksl"
    oversized.write_bytes(b"x" * 1048577)
    empty = out / "empty.ksl"
    empty.write_bytes(b"")
    binary = out / "binary.ksl"
    binary.write_bytes(b"KSL1\n\xff\n")
    failures = [directory, fifo, endpoint, link, oversized, empty, binary, out / "missing.ksl"]
    env = {"PATH": "/nonexistent", "KEXE_ALLOW": "35,37,38,39",
           "KEXE_CAP_RESOURCES_35": str(out), "KEXE_STACK_BYTES": "8388608"}
    rows = []

    def call(name, argv, expected):
        p = subprocess.run(list(map(str, argv)), cwd=out, env=env, capture_output=True, timeout=20)
        (observations / (name + ".stdout")).write_bytes(p.stdout)
        (observations / (name + ".stderr")).write_bytes(p.stderr)
        assert p.returncode == expected, (name, p.returncode, p.stderr[-400:])
        if expected:
            assert b"E6015" in p.stderr and b"KEXE_TRAP" not in p.stderr, (name, p.stderr[-400:])
        else:
            assert not p.stderr, (name, p.stderr[-400:])
        rows.append(dict(name=name, exit=p.returncode,
                         stdoutSHA256=hashlib.sha256(p.stdout).hexdigest(),
                         stderrSHA256=hashlib.sha256(p.stderr).hexdigest()))

    try:
        for i, compiler in enumerate(compilers):
            containers = []
            for j, lock in enumerate(positives):
                call(f"alias-{i}-valid-{j}", [compiler, "check", src, "--source-lock", lock,
                                             "--source-lock-sha256", sha(lock)], 0)
                output = out / f"valid-{i}-{j}.kseed"
                call(f"alias-{i}-compile-valid-{j}", [compiler, "compile", src, "--target", "aarch64-macos",
                     "--source-lock", lock, "--source-lock-sha256", sha(lock), "--output", output], 0)
                containers.append(sha(output))
            assert len(set(containers)) == 1, "lock path changed compiled program bytes"
            for j, lock in enumerate(failures):
                call(f"alias-{i}-refuse-{j}", [compiler, "check", src, "--source-lock", lock], 1)
                output = out / f"refused-{i}-{j}.kseed"
                call(f"alias-{i}-compile-refuse-{j}", [compiler, "compile", src, "--target", "aarch64-macos",
                      "--source-lock", lock, "--output", output], 1)
                assert not output.exists()
                call(f"alias-{i}-project-refuse-{j}", [compiler, "check", src, "--source-path", out,
                                                     "--source-lock", lock], 1)
        assert not (out / "lock-").exists(), "legacy token scan wrote a path prefix"
    finally:
        sock.close()
    result = dict(status="PASS_NATIVE_SOURCE_LOCK_FILE_BOUNDARY", aliases=len(compilers),
                  positivePaths=len(positives), invalidPathKinds=len(failures),
                  namedRefusal="E6015", cases=rows, noRefusalOutput=True,
                  singleAndProjectRoutes=True, unicodeAndSeparatorPaths=True,
                  positiveCompilePathIdentity=True,
                  observerSourceSHA256=sha(Path(__file__)),
                  compilerLegacyFallback=False)
    (observations / "source-lock-boundary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
