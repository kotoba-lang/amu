#!/usr/bin/env python3
"""Build and observe the fixed-source ARM64 private-root worker candidate.

The supplied Amu native compiler owns the build; this host observer drives the
worker's bounded protocol and inspects only its own children. This does not
qualify OCI extraction, container isolation, a cgroup or a release.
"""
import argparse
import hashlib
import json
import os
import platform
import select
import struct
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "seed/fune/private-root-worker.kotoba"


def pin(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def outside_identity():
    try:
        st = os.lstat("/tmp/rootfs")
    except FileNotFoundError:
        return None
    return (st.st_dev, st.st_ino, st.st_mode)


def main(compiler, out):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "arm64")
    assert os.geteuid() != 0, "run on the rootless Linux host"
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    image = out / "worker.elf"
    env = {"PATH": "/nonexistent", "KEXE_ALLOW": "35,37,38,39", "KEXE_STACK_BYTES": "8388608",
           "KEXE_CAP_RESOURCES_35": f"{ROOT}:{out}"}
    built = subprocess.run([str(compiler), "fune-worker-build", "aarch64-linux", str(SOURCE), str(image)],
                           cwd=out, env=env, capture_output=True, timeout=900)
    assert built.returncode == 0 and image.is_file(), (built.returncode, built.stderr[-1000:])
    image.chmod(0o700)
    altered = out / "altered.kotoba"
    altered.write_bytes(SOURCE.read_bytes() + b"\n;; altered input\n")
    wrong = out / "altered.elf"
    refused = subprocess.run([str(compiler), "fune-worker-build", "aarch64-linux", str(altered), str(wrong)],
                             cwd=out, env=env, capture_output=True, timeout=900)
    assert refused.returncode != 0 and not wrong.exists() and b"E6015" in refused.stderr

    sentinel = out / "inherited-fd-sentinel"
    sentinel.write_bytes(b"unchanged")
    inherited = os.open(sentinel, os.O_RDONLY)
    outside = outside_identity()
    observations = []

    def frame(op, path, size, data=b""):
        path = path.encode("ascii")
        return op + struct.pack(">HI", len(path), size) + path + data

    def exchange(p, op, path, size=0, data=b"", answer=0):
        p.stdin.write(frame(op, path, size, data))
        p.stdin.flush()
        ready, _, _ = select.select([p.stdout], [], [], 20)
        assert ready, "worker command timed out"
        assert p.stdout.read(1) == b"K"
        return p.stdout.read(answer)

    def exchange_hex(p, op, path, size=0, data=b"", answer=0):
        p.stdin.write(frame(op, path, size, data).hex().encode("ascii"))
        p.stdin.flush()
        ready, _, _ = select.select([p.stdout], [], [], 20)
        assert ready and p.stdout.read(1) == b"K"
        return p.stdout.read(answer)

    def start():
        p = subprocess.Popen([str(image)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             pass_fds=(inherited,), cwd=out, env={"PATH": "/nonexistent"})
        try:
            ready, _, _ = select.select([p.stdout], [], [], 20)
            if not ready:
                raise AssertionError("worker did not become ready")
            line = p.stdout.readline()
            if line != b"fune-private-root-ready\n":
                raise AssertionError(("worker refusal", line, p.poll()))
            children = Path(f"/proc/{p.pid}/task/{p.pid}/children").read_text().split()
            assert len(children) == 1, children
            child = int(children[0])
            assert outside_identity() == outside, "worker changed the outer /tmp/rootfs entry"
            descriptors = Path(f"/proc/{p.pid}/fd")
            open_targets = []
            for entry in descriptors.iterdir():
                try:
                    open_targets.append(os.readlink(entry))
                except FileNotFoundError:
                    pass
            assert str(sentinel) not in open_targets, "inherited host FD was not closed"
            try:
                os.listdir(f"/proc/{child}/root/tmp/rootfs")
            except PermissionError:
                proc_denied = True
            else:
                raise AssertionError("private child root was reachable through /proc")
            status = Path(f"/proc/{child}/status").read_text()
            assert "\nNoNewPrivs:\t1\n" in status
            # mountinfo is readable even when /proc/PID/root is not. Check
            # the last /tmp mount and independently compare it with ours.
            rows = [row.split() for row in Path(f"/proc/{child}/mountinfo").read_text().splitlines()]
            mounts = [row for row in rows if row[4] == "/tmp"]
            assert mounts, "child has no /tmp mount"
            mount = mounts[-1]
            sep = mount.index("-")
            assert mount[sep + 1] == "tmpfs" and "nosuid" in mount[5].split(",") and "nodev" in mount[5].split(",")
            assert "size=4096k" in mount[sep + 3].split(",") and "nr_inodes=4096" in mount[sep + 3].split(",")
            assert not any(field.startswith(("shared:", "master:")) for field in mount[6:sep])
            own_ids = {row.split()[0] for row in Path("/proc/self/mountinfo").read_text().splitlines()}
            assert mount[0] not in own_ids, "private mount appeared in observer namespace"
            return p, child, proc_denied
        except BaseException:
            p.kill()
            p.communicate(timeout=20)
            raise

    try:
        for command, expected in ((b"X", 0), (b"Z", 2)):
            p, child, proc_denied = start()
            p.stdin.write(command)
            p.stdin.flush()
            stdout, stderr = p.communicate(timeout=20)
            assert p.returncode == expected and not stdout, (command, p.returncode, stdout, stderr)
            if expected:
                assert b"FREFUSE:15" in stderr
            else:
                assert not stderr
            assert outside_identity() == outside
            observations.append({"case": "close" if command == b"X" else "invalid-command",
                                 "exit": p.returncode, "procRootDenied": proc_denied})

        p, child, proc_denied = start()
        try:
            assert exchange(p, b"M", "bin") == b""
            assert exchange(p, b"F", "bin/hello", 7, b"abc\x00xyz") == b""
            assert exchange(p, b"R", "bin/hello", 7, answer=7) == b"abc\x00xyz"
            assert exchange(p, b"U", "bin/hello", 3, b"new") == b""
            assert exchange(p, b"R", "bin/hello", 3, answer=3) == b"new"
            payload = bytes(range(256)) * 65 + b"end"
            assert exchange(p, b"M", "bin/sub") == b""
            assert exchange(p, b"F", "bin/sub/large", len(payload), payload) == b""
            assert exchange(p, b"R", "bin/sub/large", len(payload), answer=len(payload)) == payload
            maximum = bytes(range(256)) * 4096
            assert exchange(p, b"F", "max", len(maximum), maximum) == b""
            assert exchange(p, b"R", "max", len(maximum), answer=len(maximum)) == maximum
            stdout, stderr = p.communicate(b"X", timeout=20)
            assert p.returncode == 0 and not stdout and not stderr
        finally:
            if p.poll() is None:
                p.kill()
                p.communicate(timeout=20)
        assert outside_identity() == outside
        observations.append({"case": "private-file-roundtrip", "binaryBytes": 7,
                             "replaceBytes": 3, "multiChunkBytes": len(payload), "maxFileBytes": len(maximum),
                             "procRootDenied": proc_denied})

        p, child, proc_denied = start()
        try:
            p.stdin.write(b"H")
            p.stdin.flush()
            payload = bytes(range(256)) * 40 + b"\x00\xff"
            assert exchange_hex(p, b"M", "hex") == b""
            assert exchange_hex(p, b"F", "hex/all-bytes", len(payload), payload) == b""
            assert exchange_hex(p, b"R", "hex/all-bytes", len(payload), answer=len(payload)) == payload
            stdout, stderr = p.communicate(b"58", timeout=20)
            assert p.returncode == 0 and not stdout and not stderr
        finally:
            if p.poll() is None:
                p.kill()
                p.communicate(timeout=20)
        assert outside_identity() == outside
        observations.append({"case": "hex-transport", "binaryBytes": len(payload)})

        p, child, proc_denied = start()
        p.stdin.write(b"H")
        p.stdin.flush()
        assert exchange_hex(p, b"F", "committed", 1, b"x") == b""
        p.stdin.write(b"430001")
        p.stdin.flush()
        assert p.stdout.read(1) == b"D"
        assert exchange_hex(p, b"R", "committed", 1, answer=1) == b"x"
        stdout, stderr = p.communicate(frame(b"F", "after", 1, b"x").hex().encode("ascii"), timeout=20)
        assert p.returncode == 2 and not stdout and b"FREFUSE:15" in stderr
        assert outside_identity() == outside
        observations.append({"case": "commit-freezes-writes", "exit": p.returncode})

        p, child, proc_denied = start()
        p.stdin.write(b"H")
        p.stdin.flush()
        assert exchange_hex(p, b"F", "committed", 1, b"x") == b""
        stdout, stderr = p.communicate(b"430002", timeout=20)
        assert p.returncode == 2 and not stdout and b"FREFUSE:19" in stderr
        assert outside_identity() == outside
        observations.append({"case": "commit-count-mismatch", "exit": p.returncode})

        p, child, proc_denied = start()
        p.stdin.write(b"H")
        p.stdin.flush()
        assert exchange_hex(p, b"F", "committed", 1, b"x") == b""
        p.stdin.write(b"430001")
        p.stdin.flush()
        assert p.stdout.read(1) == b"D"
        assert exchange_hex(p, b"R", "committed", 1, answer=1) == b"x"
        stdout, stderr = p.communicate(frame(b"R", "committed", 1).hex().encode("ascii"), timeout=20)
        assert p.returncode == 2 and not stdout and b"FREFUSE:15" in stderr
        observations.append({"case": "commit-read-limit", "exit": p.returncode})

        p, child, proc_denied = start()
        stdout, stderr = p.communicate(b"C\x00\x00X", timeout=20)
        assert p.returncode == 0 and stdout == b"D" and not stderr
        observations.append({"case": "empty-commit", "exit": p.returncode})

        # V uses fstat on the actual private inode after finalization. Separate
        # processes permit the one-read diagnostic limit to remain enforced.
        for name, target, expected in (("file", "dir/exe", 0o751), ("directory", "dir", 0o500)):
            p, child, proc_denied = start()
            assert exchange(p, b"M", "dir") == b""
            assert exchange(p, b"F", "dir/exe", 1, b"x") == b""
            assert exchange(p, b"P", "dir/exe", 0o751) == b""
            assert exchange(p, b"P", "dir", 0o500) == b""
            p.stdin.write(b"C\x00\x04")
            p.stdin.flush()
            assert p.stdout.read(1) == b"D"
            assert exchange(p, b"V", target, answer=2) == struct.pack(">H", expected)
            stdout, stderr = p.communicate(b"X", timeout=20)
            assert p.returncode == 0 and not stdout and not stderr
            observations.append({"case": "final-mode-" + name, "mode": oct(expected)})

        for expected in (0o000, 0o777):
            p, child, proc_denied = start()
            assert exchange(p, b"F", "file", 0) == b""
            assert exchange(p, b"P", "file", expected) == b""
            p.stdin.write(b"C\x00\x02")
            p.stdin.flush()
            assert p.stdout.read(1) == b"D"
            assert exchange(p, b"V", "file", answer=2) == struct.pack(">H", expected)
            stdout, stderr = p.communicate(b"X", timeout=20)
            assert p.returncode == 0 and not stdout and not stderr
            observations.append({"case": "final-mode-boundary", "mode": oct(expected)})

        p, child, proc_denied = start()
        assert exchange(p, b"F", "file", 0) == b""
        assert exchange(p, b"P", "file", 0o755) == b""
        stdout, stderr = p.communicate(frame(b"U", "file", 0), timeout=20)
        assert p.returncode == 2 and not stdout and b"FREFUSE:15" in stderr
        observations.append({"case": "finalization-freezes-writes", "exit": p.returncode})

        def spec(argv, env, cwd):
            raw = b"FPS\x01" + struct.pack(">HHH", len(argv), len(env), len(cwd)) + cwd
            for value in argv + env:
                raw += struct.pack(">I", len(value)) + value
            return raw

        for payload in (spec([b"/bin/app", b""], ["Z=雪".encode()], b"/bin"),
                        spec([b"/bin/app"] + [b"x"] * 255,
                             [f"E{i:03d}=x".encode() for i in range(128)], b"/"),
                        spec([b"/bin/app", b"x" * 9000], [], b"/"),
                        spec([b"/bin/app", b"x" * 65527], [], b"/")):
            p, child, proc_denied = start()
            assert exchange(p, b"M", "bin") == b""
            assert exchange(p, b"F", "bin/app", 0) == b""
            assert exchange(p, b"P", "bin/app", 0o755) == b""
            assert exchange(p, b"P", "bin", 0o755) == b""
            p.stdin.write(b"T" + struct.pack(">HI", 4, len(payload)) + payload)
            p.stdin.flush()
            assert p.stdout.read(1) == b"D"
            p.stdin.write(b"Q")
            p.stdin.flush()
            assert p.stdout.read(5) == b"K" + struct.pack(">I", len(payload))
            assert p.stdout.read(len(payload)) == payload
            stdout, stderr = p.communicate(b"X", timeout=20)
            assert p.returncode == 0 and not stdout and not stderr
            observations.append({"case": "process-spec-roundtrip", "bytes": len(payload)})

        for name, payload in (
            ("magic", b"BAD!" + spec([b"/bin/app"], [], b"/")[4:]),
            ("cwd-traversal", spec([b"/bin/app"], [], b"/bin/..")),
            ("argv-traversal", spec([b"/bin/../app"], [], b"/")),
            ("embedded-nul", spec([b"/bin/app", b"a\x00b"], [], b"/")),
            ("truncated-value", spec([b"/bin/app", b"xyz"], [], b"/")[:-1]),
            ("payload-budget", spec([b"/bin/app", b"x" * 65528], [], b"/")),
            ("empty-argv", spec([], [], b"/")),
            ("argv-count", spec([b"/bin/app"] + [b"x"] * 256, [], b"/")),
            ("env-count", spec([b"/bin/app"], [b"A=x"] * 129, b"/")),
        ):
            p, child, proc_denied = start()
            assert exchange(p, b"F", "file", 0) == b""
            assert exchange(p, b"P", "file", 0o755) == b""
            stdout, stderr = p.communicate(b"T" + struct.pack(">HI", 2, len(payload)) + payload, timeout=20)
            assert p.returncode == 2 and not stdout and b"FREFUSE:20" in stderr, (name, p.returncode, stdout, stderr)
            observations.append({"case": "process-spec-" + name, "exit": p.returncode})

        p, child, proc_denied = start()
        assert exchange(p, b"F", "file", 0) == b""
        stdout, stderr = p.communicate(b"T" + struct.pack(">HI", 1, 67501), timeout=20)
        assert p.returncode == 2 and not stdout and b"FREFUSE:15" in stderr
        observations.append({"case": "process-spec-before-finalization", "exit": p.returncode})

        p, child, proc_denied = start()
        assert exchange(p, b"F", "file", 0) == b""
        assert exchange(p, b"P", "file", 0o755) == b""
        stdout, stderr = p.communicate(b"T" + struct.pack(">HI", 2, 67501), timeout=20)
        assert p.returncode == 2 and not stdout and b"FREFUSE:19" in stderr
        observations.append({"case": "process-spec-size-limit", "exit": p.returncode})

        p, child, proc_denied = start()
        assert exchange(p, b"F", "file", 0) == b""
        assert exchange(p, b"P", "file", 0o755) == b""
        payload = spec([b"/file"], [], b"/")
        stdout, stderr = p.communicate(b"T" + struct.pack(">HI", 3, len(payload)) + payload, timeout=20)
        assert p.returncode == 2 and not stdout and b"FREFUSE:19" in stderr
        observations.append({"case": "process-spec-count-mismatch", "exit": p.returncode})

        p, child, proc_denied = start()
        stdout, stderr = p.communicate(b"C\x00\x00Q", timeout=20)
        assert p.returncode == 2 and stdout == b"D" and b"FREFUSE:15" in stderr
        observations.append({"case": "process-spec-not-staged", "exit": p.returncode})

        p, child, proc_denied = start()
        assert exchange(p, b"F", "file", 0) == b""
        assert exchange(p, b"P", "file", 0o755) == b""
        payload = spec([b"/file"], [], b"/")
        p.stdin.write(b"T" + struct.pack(">HI", 2, len(payload)) + payload + b"Q")
        p.stdin.flush()
        assert p.stdout.read(6 + len(payload)) == b"DK" + struct.pack(">I", len(payload)) + payload
        stdout, stderr = p.communicate(b"Q", timeout=20)
        assert p.returncode == 2 and not stdout and b"FREFUSE:15" in stderr
        observations.append({"case": "process-spec-read-limit", "exit": p.returncode})

        # Each refusal kills the worker and therefore drops the entire tmpfs.
        for name, request in (
            ("absolute", frame(b"F", "/tmp/fune-escape", 1, b"x")),
            ("parent", frame(b"F", "../fune-escape", 1, b"x")),
            ("whiteout", frame(b"F", ".wh.test", 1, b"x")),
            ("empty-component", frame(b"F", "bin//file", 1, b"x")),
            ("dot-component", frame(b"F", "bin/./file", 1, b"x")),
            ("missing-parent", frame(b"F", "missing/file", 1, b"x")),
            ("missing-replacement", frame(b"U", "missing", 1, b"x")),
            ("oversize", frame(b"F", "large", 1048577)),
            ("special-mode", frame(b"P", "file", 0o4755)),
            ("early-stat", frame(b"V", "file", 0)),
            ("short-payload", frame(b"F", "partial", 5, b"xy")),
            ("short-header", b"F\x00"),
            ("odd-hex", b"H4"),
            ("invalid-hex", b"H4G"),
        ):
            p, child, proc_denied = start()
            stdout, stderr = p.communicate(request, timeout=20)
            assert p.returncode == 2 and not stdout and b"FREFUSE:" in stderr, (name, p.returncode, stdout, stderr)
            assert outside_identity() == outside
            observations.append({"case": name, "exit": p.returncode})

        p, child, proc_denied = start()
        assert exchange(p, b"F", "once", 1, b"x") == b""
        stdout, stderr = p.communicate(frame(b"F", "once", 1, b"y"), timeout=20)
        assert p.returncode == 2 and not stdout and b"FREFUSE:" in stderr
        assert outside_identity() == outside
        observations.append({"case": "duplicate-create", "exit": p.returncode})

        p, child, proc_denied = start()
        assert exchange(p, b"F", "empty", 0, b"") == b""
        for _ in range(511):
            assert exchange(p, b"R", "empty", 0, answer=0) == b""
        stdout, stderr = p.communicate(frame(b"R", "empty", 0), timeout=20)
        assert p.returncode == 2 and not stdout and b"FREFUSE:15" in stderr
        assert outside_identity() == outside
        observations.append({"case": "operation-limit", "accepted": 512, "exit": p.returncode})

        p, child, proc_denied = start()
        p.stdin.write(b"H")
        p.stdin.flush()
        assert exchange_hex(p, b"F", "empty", 0, b"") == b""
        for _ in range(511):
            assert exchange_hex(p, b"R", "empty", 0, answer=0) == b""
        p.stdin.write(b"430200")
        p.stdin.flush()
        assert p.stdout.read(1) == b"D"
        stdout, stderr = p.communicate(b"58", timeout=20)
        assert p.returncode == 0 and not stdout and not stderr
        observations.append({"case": "commit-at-operation-limit", "accepted": 512, "exit": p.returncode})

        p, child, proc_denied = start()
        assert exchange(p, b"F", "empty", 0) == b""
        for _ in range(511):
            assert exchange(p, b"R", "empty", 0) == b""
        for _ in range(128):
            assert exchange(p, b"P", "empty", 0o600) == b""
        p.stdin.write(b"C\x02\x80")
        p.stdin.flush()
        assert p.stdout.read(1) == b"D"
        assert exchange(p, b"V", "empty", answer=2) == struct.pack(">H", 0o600)
        stdout, stderr = p.communicate(b"X", timeout=20)
        assert p.returncode == 0 and not stdout and not stderr
        observations.append({"case": "finalization-at-operation-limit", "accepted": 640})

        p, child, proc_denied = start()
        assert exchange(p, b"F", "empty", 0) == b""
        for _ in range(128):
            assert exchange(p, b"P", "empty", 0o600) == b""
        stdout, stderr = p.communicate(frame(b"P", "empty", 0o600), timeout=20)
        assert p.returncode == 2 and not stdout and b"FREFUSE:15" in stderr
        observations.append({"case": "finalization-count-limit", "accepted": 128})

        p, child, proc_denied = start()
        p.kill()
        p.communicate(timeout=20)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                status = Path(f"/proc/{child}/status").read_text()
            except FileNotFoundError:
                break
            if "\nState:\tZ" in status:
                break
            time.sleep(0.05)
        else:
            raise AssertionError("child survived parent death")
        assert outside_identity() == outside
        observations.append({"case": "parent-sigkill", "exit": p.returncode, "childGoneOrZombie": True,
                             "procRootDenied": proc_denied})
    finally:
        os.close(inherited)
    assert sentinel.read_bytes() == b"unchanged"
    report = {"status": "PASS_FUNE_PRIVATE_ROOT_CANDIDATE", "host": [platform.system(), platform.machine()],
              "compiler": pin(compiler), "source": pin(SOURCE), "worker": pin(image),
              "observations": observations, "sourceMutationRefused": True,
              "privateTmpfsMountObserved": True, "otherNamespacesIndependentlyObserved": False,
              "ociExtractionQualified": False,
              "containerIsolationQualified": False, "releaseQualified": False}
    (out / "private-root.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.compiler.resolve(), a.output.resolve())
