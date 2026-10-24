#!/usr/bin/env python3
"""Inject real kernel errno in one native FS2 child, after observer setup.

Python stages input and checks process/FS observations. Only the Amu-produced
image implements FS operations. The BPF filter affects no container init,
observer, service or unrelated process. No compiler or host language oracle.
"""
import argparse
import ctypes
import hashlib
import json
import os
import platform
import signal
import time
from pathlib import Path

CASES = {
    "write-eio": (64, 1, 5, 126, 13),
    "fsync-eio": (82, 74, 5, 126, 13),
    "chmod-eperm": (52, 91, 1, 126, 13),
    "unlink-eacces": (35, 263, 13, 1, None),
    "fstat-eio": (80, 5, 5, 126, 11),
    "entropy-enosys": (278, 318, 38, 126, 10),
    "rename-enosys": (276, 316, 38, 126, 3),
    "open-enosys": (437, 437, 38, 126, 3),
}


def main(image, out, case):
    machine = platform.machine()
    assert platform.system() == "Linux" and machine in ("aarch64", "arm64", "x86_64")
    arm = machine in ("aarch64", "arm64")
    arm_nr, x86_nr, error, expected, stage = CASES[case]
    number = arm_nr if arm else x86_nr
    out.mkdir(parents=True, exist_ok=False)
    scope = out / "scope"
    scope.mkdir()
    (scope / "sentinel").write_bytes(b"unowned-preserve")
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.restype = ctypes.c_long
    libc.syscall.restype = ctypes.c_long

    class Instruction(ctypes.Structure):
        _fields_ = [("code", ctypes.c_uint16), ("jt", ctypes.c_uint8), ("jf", ctypes.c_uint8), ("k", ctypes.c_uint32)]

    class Program(ctypes.Structure):
        _fields_ = [("length", ctypes.c_uint16), ("instructions", ctypes.c_void_p)]

    # Check the native audit architecture, load syscall number, then deny
    # exactly this syscall. write only targets fd >=3; diagnostics remain.
    instructions = [(0x20, 0, 0, 4), (0x15, 1, 0, 0xC00000B7 if arm else 0xC000003E), (0x06, 0, 0, 0x80000000),
                    (0x20, 0, 0, 0), (0x15, 0, 3 if case == "write-eio" else 1, number)]
    if case == "write-eio":
        instructions += [(0x20, 0, 0, 16), (0x35, 0, 1, 3)]
    instructions += [(0x06, 0, 0, 0x00050000 | error), (0x06, 0, 0, 0x7FFF0000)]
    data = (Instruction * len(instructions))(*[Instruction(*i) for i in instructions])
    program = Program(len(instructions), ctypes.addressof(data))
    (out / "filter.json").write_text(json.dumps(dict(architecture=machine, syscall=number, errno=error, instructions=instructions), indent=2) + "\n")
    pid = os.fork()
    if pid == 0:
        stdout = os.open(out / "guest.stdout", os.O_CREAT | os.O_WRONLY, 0o600)
        stderr = os.open(out / "guest.stderr", os.O_CREAT | os.O_WRONLY, 0o600)
        os.dup2(stdout, 1)
        os.dup2(stderr, 2)
        os.close(stdout)
        os.close(stderr)
        assert libc.prctl(ctypes.c_long(38), ctypes.c_long(1), ctypes.c_long(0), ctypes.c_long(0), ctypes.c_long(0)) == 0
        assert libc.syscall(ctypes.c_long(277 if arm else 317), ctypes.c_long(1), ctypes.c_long(0), ctypes.byref(program)) == 0
        mode = "managed-publish-exclusive" if case == "rename-enosys" else "managed-return"
        os.execve(image, [str(image), mode, str(scope)], dict(PATH="/nonexistent", KEXE_ALLOW="35,37,38,39",
                  KEXE_CAP_RESOURCES_35=str(scope), KEXE_STACK_BYTES="8388608"))
    deadline = time.monotonic() + 30
    while True:
        done, status = os.waitpid(pid, os.WNOHANG)
        if done:
            break
        if time.monotonic() >= deadline:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
            raise AssertionError("native errno guest deadline")
        time.sleep(0.005)
    code = os.waitstatus_to_exitcode(status)
    stdout, stderr = (out / "guest.stdout").read_bytes(), (out / "guest.stderr").read_bytes()
    remaining = sorted(str(p.relative_to(scope)) for p in scope.rglob("*"))
    (out / "observations.json").write_text(json.dumps(dict(exit=code, remaining=remaining, stdout=stdout.decode(errors="replace"),
                 stderr=stderr.decode(errors="replace")), indent=2) + "\n")
    assert code == expected and not stdout and (scope / "sentinel").read_bytes() == b"unowned-preserve"
    if stage is not None:
        assert f":stage {stage}}}".encode() in stderr
    incomplete = case in ("unlink-eacces", "fstat-eio")
    assert (b"KEXE_CLEANUP {:incomplete}" in stderr) == incomplete
    if case == "unlink-eacces":
        directory = Path((scope / "ready").read_text())
        assert directory.parent == scope and directory.name.startswith("kotoba-output-")
        assert (directory / "0.tmp").read_bytes() == b"preserved"
        assert remaining == sorted([directory.name, directory.name + "/0.tmp", "ready", "sentinel"])
    elif case == "fstat-eio":
        dirs = list(scope.glob("kotoba-output-*"))
        assert len(dirs) == 1 and dirs[0].is_dir() and list(dirs[0].iterdir()) == []
        assert remaining == sorted([dirs[0].name, "sentinel"])
    else:
        assert remaining == (["ready", "sentinel"] if case == "rename-enosys" else ["sentinel"])
    assert not (scope / "published").exists()
    report = dict(status="PASS_NATIVE_FS2_KERNEL_ERRNO", case=case, host=[platform.system(), machine],
                  image=dict(bytes=image.stat().st_size, sha256=hashlib.sha256(image.read_bytes()).hexdigest()),
                  syscall=number, kernelErrno=error, exit=code, incompleteCleanupExpected=incomplete,
                  unownedSentinelPreserved=True, noPublishedTarget=True, nativeGuestUnmodified=True,
                  legacyRuntimeFallback=False, allFaultRaceParityQualified=False)
    (out / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], case)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--case", choices=list(CASES), required=True)
    a = p.parse_args()
    main(a.image.resolve(), a.output.resolve(), a.case)
