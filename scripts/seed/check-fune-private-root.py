#!/usr/bin/env python3
"""Build and observe the fixed-source ARM64 private-root worker candidate.

The supplied Amu native compiler owns the build; this host observer drives the
worker's one-byte protocol and inspects only its own children. This does not
qualify OCI extraction, container isolation, a cgroup or a release.
"""
import argparse
import hashlib
import json
import os
import platform
import select
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
