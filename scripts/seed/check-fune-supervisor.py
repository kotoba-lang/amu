#!/usr/bin/env python3
"""Stage sealed native images and observe the diagnostic fune supervisor.

The observer supplies already built task-owned native images; the supervisor
runs the producer and worker and owns forwarding and status decisions. Images
are test inputs, not authenticated product artifacts. No OCI parser lives here.
"""
import argparse
import fcntl
import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path

DIGEST = "sha256:abeeb5676fc9f826390bebd952b0a8336beda3230f1dab60b8cfde84f160aebf"
ROOT = Path(__file__).resolve().parents[2]


def build_candidate(compiler, output):
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    source = ROOT / "seed/fune/private-root-supervisor.kotoba"
    image = output / "supervisor.elf"
    env = {"PATH": "/nonexistent", "KEXE_ALLOW": "35,37,38,39", "KEXE_STACK_BYTES": "8388608",
           "KEXE_CAP_RESOURCES_35": f"{ROOT}:{output}"}
    built = subprocess.run([str(compiler), "fune-supervisor-build", "aarch64-linux", str(source), str(image)],
                           cwd=output, env=env, capture_output=True, timeout=900)
    assert built.returncode == 0 and image.is_file(), (built.returncode, built.stderr[-1000:])
    image.chmod(0o700)
    altered = output / "altered.kotoba"
    altered.write_bytes(source.read_bytes() + b"\n;; changed source\n")
    wrong = output / "altered.elf"
    refused = subprocess.run([str(compiler), "fune-supervisor-build", "aarch64-linux", str(altered), str(wrong)],
                             cwd=output, env=env, capture_output=True, timeout=900)
    assert refused.returncode != 0 and not wrong.exists() and b"E6015" in refused.stderr
    return image


def image_fd(path, sealed=True, corrupt=False, padding=b""):
    fd = os.memfd_create("fune-test-image", os.MFD_ALLOW_SEALING | os.MFD_CLOEXEC)
    with path.open("rb") as src, os.fdopen(os.dup(fd), "wb") as dst:
        while data := src.read(65536):
            dst.write(data)
        dst.write(padding)
    os.lseek(fd, 0, os.SEEK_SET)
    if corrupt:
        first = os.pread(fd, 1, 0)
        assert first
        os.pwrite(fd, bytes([first[0] ^ 1]), 0)
    if sealed:
        fcntl.fcntl(fd, fcntl.F_ADD_SEALS, fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK |
                    fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE)
    return fd


def digest(path, padding=b""):
    return "sha256:" + hashlib.sha256(path.read_bytes() + padding).hexdigest()


def invoke(supervisor, worker, producer, root, *, sealed=True, wrong_digest=False, polluted=False, corrupt=False, manifest_digest=DIGEST, padding=b""):
    wf = image_fd(worker, sealed=sealed, corrupt=corrupt, padding=padding)
    pf = image_fd(producer)
    try:
        wd = "sha256:" + "0" * 64 if wrong_digest else digest(worker, padding)
        env = {"PATH": "/nonexistent"}
        if polluted:
            env["KEXE_STRUCTURED_REPORT"] = "1"
        return subprocess.run([str(supervisor), str(wf), wd, str(pf), digest(producer), str(root), manifest_digest],
                              stdin=subprocess.DEVNULL, capture_output=True, pass_fds=(wf, pf),
                              env=env, timeout=75)
    finally:
        os.close(wf)
        os.close(pf)


def parent_death(supervisor, worker, slow, root):
    wf, pf = image_fd(worker), image_fd(slow)
    p = None
    try:
        p = subprocess.Popen([str(supervisor), str(wf), digest(worker), str(pf), digest(slow), str(root), DIGEST],
                             stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             pass_fds=(wf, pf), env={"PATH": "/nonexistent"})
        deadline = time.monotonic() + 15
        descendants = []
        while time.monotonic() < deadline:
            assert p.poll() is None, (p.returncode, p.communicate())
            children = Path(f"/proc/{p.pid}/task/{p.pid}/children").read_text().split()
            if len(children) == 2:
                for child in children:
                    try:
                        grand = Path(f"/proc/{child}/task/{child}/children").read_text().split()
                    except (FileNotFoundError, ProcessLookupError):
                        continue
                    if len(grand) == 1:
                        try:
                            init = Path(f"/proc/{grand[0]}/task/{grand[0]}/children").read_text().split()
                        except (FileNotFoundError, ProcessLookupError):
                            continue
                        if len(init) == 1:
                            descendants = [int(x) for x in children + grand + init]
                            break
            if descendants:
                break
            time.sleep(0.02)
        assert len(descendants) == 4, "producer and complete worker tree did not all start"
        p.send_signal(signal.SIGKILL)
        p.communicate(timeout=20)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            alive = []
            for pid in descendants:
                try:
                    status = Path(f"/proc/{pid}/status").read_text()
                except (FileNotFoundError, ProcessLookupError):
                    continue
                if "\nState:\tZ" not in status:
                    alive.append(pid)
            if not alive:
                return
            time.sleep(0.05)
        raise AssertionError(("children survived supervisor death", alive))
    finally:
        if p is not None and p.poll() is None:
            p.kill()
            p.communicate(timeout=20)
        os.close(wf)
        os.close(pf)


def main(supervisor, worker, producer, layouts, slow, large_digest, stress, wrong_count, no_commit, repeat_digest,
         limit_layout, limit_digest, overlimit_worker):
    good = invoke(supervisor, worker, producer, layouts / "plan-binary")
    assert good.returncode == 0 and good.stdout == b"fune-supervisor-ok\n" and not good.stderr, (good.returncode, good.stdout, good.stderr)
    # The worker image is aligned to 64 bytes; trailing bytes are ignored by
    # ELF. These independently hashed variants cross SHA-256 padding edges.
    assert worker.stat().st_size % 64 == 0
    for pad in (55, 56, 63):
        boundary = invoke(supervisor, worker, producer, layouts / "plan-binary", padding=b"x" * pad)
        assert boundary.returncode == 0 and boundary.stdout == good.stdout and not boundary.stderr, (pad, boundary.stderr)
    clean_env = invoke(supervisor, worker, producer, layouts / "plan-binary", polluted=True)
    assert clean_env.returncode == 0 and clean_env.stdout == good.stdout and not clean_env.stderr
    bad = invoke(supervisor, worker, producer, layouts / "plan-binary-third-tampered")
    assert bad.returncode == 2 and not bad.stdout and b"fune/blob-digest" in bad.stderr, (bad.returncode, bad.stdout, bad.stderr)
    if wrong_count:
        wrong = invoke(supervisor, worker, wrong_count, layouts / "plan-binary")
        assert wrong.returncode == 2 and not wrong.stdout, (wrong.returncode, wrong.stdout, wrong.stderr)
    if no_commit:
        missing = invoke(supervisor, worker, no_commit, layouts / "plan-binary")
        assert missing.returncode == 2 and not missing.stdout, (missing.returncode, missing.stdout, missing.stderr)
    unsealed = invoke(supervisor, worker, producer, layouts / "plan-binary", sealed=False)
    assert unsealed.returncode == 2 and not unsealed.stdout, (unsealed.returncode, unsealed.stdout, unsealed.stderr)
    mismatch = invoke(supervisor, worker, producer, layouts / "plan-binary", wrong_digest=True)
    assert mismatch.returncode == 2 and not mismatch.stdout, (mismatch.returncode, mismatch.stdout, mismatch.stderr)
    changed = invoke(supervisor, worker, producer, layouts / "plan-binary", corrupt=True)
    assert changed.returncode == 2 and not changed.stdout, (changed.returncode, changed.stdout, changed.stderr)
    traversal = invoke(supervisor, worker, producer, layouts / "plan-binary" / ".." / "other")
    assert traversal.returncode == 2 and not traversal.stdout
    colon = invoke(supervisor, worker, producer, Path(str(layouts / "plan-binary") + ":/tmp"))
    assert colon.returncode == 2 and not colon.stdout
    broken_worker = invoke(supervisor, producer, producer, layouts / "plan-binary")
    assert broken_worker.returncode == 2 and not broken_worker.stdout, (broken_worker.returncode, broken_worker.stdout, broken_worker.stderr)
    if large_digest:
        large = invoke(supervisor, worker, producer, layouts / "plan-binary-max", manifest_digest=large_digest)
        assert large.returncode == 0 and large.stdout == good.stdout and not large.stderr
    if repeat_digest:
        repeated = invoke(supervisor, worker, producer, layouts / "plan-binary-repeat-dir", manifest_digest=repeat_digest)
        assert repeated.returncode == 0 and repeated.stdout == good.stdout and not repeated.stderr
    if limit_layout:
        limit = invoke(supervisor, worker, producer, limit_layout, manifest_digest=limit_digest)
        assert limit.returncode == 0 and limit.stdout == good.stdout and not limit.stderr, (limit.returncode, limit.stderr)
        if overlimit_worker:
            overflow = invoke(supervisor, overlimit_worker, producer, limit_layout, manifest_digest=limit_digest)
            assert overflow.returncode == 2 and not overflow.stdout, (overflow.returncode, overflow.stdout, overflow.stderr)
    if stress:
        pad = b"x" * (16777216 - worker.stat().st_size)
        at_limit = invoke(supervisor, worker, producer, layouts / "plan-binary", padding=pad)
        assert at_limit.returncode == 0 and at_limit.stdout == good.stdout, (at_limit.returncode, at_limit.stderr)
        over_limit = invoke(supervisor, worker, producer, layouts / "plan-binary", padding=pad + b"x")
        assert over_limit.returncode == 2 and not over_limit.stdout, (over_limit.returncode, over_limit.stderr)
    if slow is not None:
        parent_death(supervisor, worker, slow, layouts / "plan-binary")
        began = time.monotonic()
        timed = invoke(supervisor, worker, slow, layouts / "plan-binary")
        elapsed = time.monotonic() - began
        assert timed.returncode == 2 and not timed.stdout and 25 <= elapsed <= 45, (timed.returncode, elapsed, timed.stderr)
    report = {"status": "PASS_FUNE_SUPERVISOR_OBSERVATION", "supervisor": digest(supervisor),
              "worker": digest(worker), "producer": digest(producer), "fixtureManifest": DIGEST,
              "shaPaddingBoundaries": [55, 56, 63], "imageSizeStress": bool(stress),
              "largeLayerChecked": bool(large_digest), "parentDeathAndTimeoutChecked": slow is not None,
              "wrongCountChecked": wrong_count is not None, "missingCommitChecked": no_commit is not None,
              "repeatedDirectoryChecked": repeat_digest is not None,
              "limitFixtureAccepted": limit_layout is not None,
              "overlimitWorkerRefused": overlimit_worker is not None,
              "authenticatesDigestAuthority": False, "ociComplete": False, "releaseQualified": False}
    print(report["status"])
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--supervisor", type=Path)
    p.add_argument("--compiler", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--worker", type=Path, required=True)
    p.add_argument("--producer", type=Path, required=True)
    p.add_argument("--layouts", type=Path, required=True)
    p.add_argument("--slow-producer", type=Path)
    p.add_argument("--large-digest")
    p.add_argument("--stress", action="store_true", help="exercise executable hash size limit")
    p.add_argument("--wrong-count-producer", type=Path)
    p.add_argument("--no-commit-producer", type=Path)
    p.add_argument("--repeat-dir-digest")
    p.add_argument("--limit-layout", type=Path, help="OCI layout with exactly 640 completed worker operations")
    p.add_argument("--limit-digest", help="manifest digest for --limit-layout")
    p.add_argument("--overlimit-worker", type=Path, help="test-only worker that emits one extra K at 640")
    a = p.parse_args()
    assert bool(a.limit_layout) == bool(a.limit_digest), "limit layout and digest must be supplied together"
    assert not a.overlimit_worker or a.limit_layout, "overlimit worker requires the limit layout"
    if a.compiler:
        assert a.output and not a.supervisor
        supervisor = build_candidate(a.compiler.resolve(), a.output.resolve())
    else:
        assert a.supervisor and not a.output
        supervisor = a.supervisor.resolve()
    report = main(supervisor, a.worker.resolve(), a.producer.resolve(), a.layouts.resolve(),
                  a.slow_producer.resolve() if a.slow_producer else None, a.large_digest, a.stress,
                  a.wrong_count_producer.resolve() if a.wrong_count_producer else None,
                  a.no_commit_producer.resolve() if a.no_commit_producer else None, a.repeat_dir_digest,
                  a.limit_layout.resolve() if a.limit_layout else None, a.limit_digest,
                  a.overlimit_worker.resolve() if a.overlimit_worker else None)
    report["supervisorSource"] = digest(ROOT / "seed/fune/private-root-supervisor.kotoba")
    report["factorySourceMutationRejected"] = bool(a.compiler)
    if a.output:
        (a.output / "supervisor-observation.json").write_text(json.dumps(report, indent=2) + "\n")
