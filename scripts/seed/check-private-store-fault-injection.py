#!/usr/bin/env python3
"""Fault injection for the KPV1 private-store frames of wire 35: create and append (AWAI-52).

check-private-store.py covers the frames when the kernel calls succeed. This gate makes one
call fail, by running the probe (seed/tests/private-store/probe.kotoba) in a container under a
seccomp profile that returns an errno for one syscall, and requires the refusal (exit 2, answer
"0 1") and the bytes left on disk:

  op      fault             exit  journal afterwards
  create  none              0     TEXT
  create  write -> ENOSPC   2     ""      the exclusive open created it; a retry refuses (exists)
  create  fsync -> EIO      2     TEXT    written but not acknowledged: journal damage
  create  flock -> EAGAIN   2     ""      created before the lock; nothing written
  append  none              0     "orig\\n" + TEXT
  append  write -> ENOSPC   2     "orig\\n"
  append  fsync -> EIO      2     "orig\\n" + TEXT   written but not acknowledged: journal damage
  append  flock -> EAGAIN   2     "orig\\n"

The no-fault run also holds the journal's flock from a second process (no seccomp): a
compare-append under an exclusive holder refuses with the journal unchanged, and a read under a
shared holder succeeds.

TEXT is 37 bytes, and the write fault matches only a 37-byte write(2) on fd >= 3, so the
container runtime and Python are unaffected. The runtime's own comment says an interrupted
append is fail-closed journal damage for the caller to detect; this gate pins which bytes that
leaves. Run on Linux arm64, one fault per container:

  python3 scripts/seed/check-private-store-fault-injection.py --write-profile fsync OUT/fsync.json
  podman run --platform linux/arm64 --network none --security-opt seccomp=OUT/fsync.json \\
    -v REPO:/repo:ro -v OUT:/out python:3.12-slim python3 \\
    /repo/scripts/seed/check-private-store-fault-injection.py \\
    --compiler /repo/seed/bootstrap/aarch64-linux-static-root.elf --fault fsync --output /out/fsync
"""
import argparse
import fcntl
import hashlib
import json
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "seed/tests/private-store/probe.kotoba"
TEXT = "x" * 36 + "\n"   # 37 bytes: the length the write fault matches
ERRNO = {"write": 28, "fsync": 5, "flock": 11}   # ENOSPC, EIO, EAGAIN
# (op, fault) -> (exit, answer, journal afterwards)
CASES = {("create", "none"): (0, "1 1 \n", TEXT), ("create", "write"): (2, "0 1 \n", ""),
         ("create", "fsync"): (2, "0 1 \n", TEXT), ("create", "flock"): (2, "0 1 \n", ""),
         ("append", "none"): (0, "1 1 \n", "orig\n" + TEXT), ("append", "write"): (2, "0 1 \n", "orig\n"),
         ("append", "fsync"): (2, "0 1 \n", "orig\n" + TEXT), ("append", "flock"): (2, "0 1 \n", "orig\n")}


def profile(fault):
    rule = {"names": [fault], "action": "SCMP_ACT_ERRNO", "errnoRet": ERRNO[fault]}
    if fault == "write":
        rule["args"] = [{"index": 0, "value": 3, "op": "SCMP_CMP_GE"},
                        {"index": 2, "value": len(TEXT), "op": "SCMP_CMP_EQ"}]
    return {"defaultAction": "SCMP_ACT_ALLOW", "architectures": ["SCMP_ARCH_AARCH64"], "syscalls": [rule]}


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def contended(image, env, output):
    """A second process holds the journal's flock (no seccomp): the probe's non-blocking lock
    must refuse a compare-append under an exclusive holder and leave the journal unchanged, and
    a read must still succeed under a shared holder."""
    private = output / "contended-private"
    private.mkdir(mode=0o700)
    journal = private / "journal"
    journal.write_text("orig\n")
    journal.chmod(0o600)
    seen = {}
    for name, mode, argv, want in [
            ("append under an exclusive holder", fcntl.LOCK_EX, ["A", str(journal), "orig\n", TEXT], (2, "0 1 \n")),
            ("read under a shared holder", fcntl.LOCK_SH, ["R", str(journal)], (0, "1 6 orig\n\n"))]:
        with open(journal) as held:
            fcntl.flock(held, mode)
            x = subprocess.run([str(image), *argv], env=env, capture_output=True, text=True, timeout=20)
        assert (x.returncode, x.stdout, x.stderr, journal.read_text()) == (*want, "", "orig\n"), \
            (name, x.returncode, x.stdout, x.stderr[-300:], journal.read_text())
        seen[name] = dict(exit=x.returncode, answer=x.stdout)
    return seen


def main(compiler, fault, output):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "arm64"), "run on Linux arm64"
    output.mkdir(parents=True, exist_ok=False)
    art = output / "artifacts"
    art.mkdir()
    producer = art / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)
    (art / "probe.kotoba").write_bytes(PROBE.read_bytes())
    image = art / "probe.elf"
    r = subprocess.run([str(producer), "compile", str(art / "probe.kotoba"), "--target", "aarch64-linux",
                        "--output", str(image), "--format", "static"], cwd=art, capture_output=True, timeout=1800,
                       env={"PATH": "/nonexistent", "KEXE_STACK_BYTES": "8388608", "KEXE_CAP_RESOURCES_35": str(art)})
    assert r.returncode == 0 and not r.stderr, ("compile", r.returncode, r.stderr[-400:])
    image.chmod(0o755)
    env = {"PATH": "/usr/bin:/bin", "KEXE_ALLOW": "35,37,38,39", "KEXE_CAP_RESOURCES_35": str(output)}
    results = []
    for op in ("create", "append"):
        private = output / f"{op}-private"
        private.mkdir(mode=0o700)
        journal = private / "journal"
        if op == "append":
            journal.write_text("orig\n")
            journal.chmod(0o600)
            argv = [str(image), "A", str(journal), "orig\n", TEXT]
        else:
            argv = [str(image), "C", str(journal), TEXT]
        x = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=20)
        want_exit, want_answer, want_disk = CASES[(op, fault)]
        on_disk = journal.read_text() if journal.exists() else None
        assert (x.returncode, x.stdout, x.stderr, on_disk) == (want_exit, want_answer, "", want_disk), \
            (op, fault, x.returncode, x.stdout, x.stderr[-300:], on_disk)
        if op == "create" and fault != "none":
            # The exclusive create left the journal behind, so a retry refuses instead of overwriting it.
            again = subprocess.run([str(image), "C", str(journal), TEXT], env=env, capture_output=True, text=True, timeout=20)
            assert again.returncode == 2 and journal.read_text() == want_disk, (op, fault, "retry", again.returncode)
        results.append(dict(op=op, exit=x.returncode, answer=x.stdout, journal=on_disk))
    contention = contended(image, env, output) if fault == "none" else None
    report = dict(status="PASS_PRIVATE_STORE_FAULT_INJECTION", fault=fault, results=results, contention=contention,
                  compiler=pin(compiler), image=pin(image), probe=pin(PROBE),
                  injected=None if fault == "none" else profile(fault),
                  host=[platform.system(), platform.machine(), platform.release()],
                  notCovered=["a power cut: an fsync that returns is what is checked, not the device",
                              "a short write: the fault refuses the whole write(2), it does not shorten it",
                              "a holder that keeps the lock across the whole operation window (contention is checked only before the probe locks)"])
    (output / "private-store-fault-injection.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], fault, " ".join(f"{r['op']}={r['exit']}:{r['journal']!r}" for r in results), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--write-profile", nargs=2, metavar=("FAULT", "PATH"), help="write the seccomp profile for FAULT and exit")
    p.add_argument("--compiler", type=Path)
    p.add_argument("--fault", choices=("none", *ERRNO))
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    if a.write_profile:
        fault, path = a.write_profile
        assert fault in ERRNO, fault
        Path(path).write_text(json.dumps(profile(fault), indent=2) + "\n")
    else:
        assert a.compiler and a.fault and a.output, "--compiler, --fault and --output are required"
        main(a.compiler.resolve(), a.fault, a.output.resolve())
