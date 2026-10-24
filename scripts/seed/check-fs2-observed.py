#!/usr/bin/env python3
"""Observe native FS2 kernel boundaries; no host language/compiler oracle.

The supplied image is seed/tests/fs2-product.kotoba compiled by Amu selfhost.
ptrace affects only this observer's child. Creation-window tests send a real
signal after kernel creation, before the guest can update its journal. The
EINTR case lets close consume its real fd before changing only the return.
Partial I/O tests reduce the real kernel transfer count and let Kotoba's
existing fixture assertions decide whether the reconstructed bytes are right.
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


def main(image, out, case):
    machine = platform.machine()
    assert platform.system() == "Linux" and machine in ("aarch64", "arm64", "x86_64")
    arm = machine in ("aarch64", "arm64")
    reg_count, number, result, args = (34, 8, 0, [0, 1, 2, 3, 4, 5]) if arm else (27, 15, 10, [14, 13, 12, 7, 9, 8])
    ids = dict(close=57, mkdirat=34, openat2=437, read=63, write=64) if arm else dict(close=3, mkdirat=258, openat2=437, read=0, write=1)
    out.mkdir(parents=True, exist_ok=False)
    scope = out / "scope"
    scope.mkdir()
    (scope / "sentinel").write_bytes(b"unowned-preserve")
    lib = ctypes.CDLL(None, use_errno=True)
    lib.ptrace.restype = ctypes.c_long

    class IOV(ctypes.Structure):
        _fields_ = [("base", ctypes.c_void_p), ("length", ctypes.c_size_t)]

    def trace(request, pid, address=0, data=0):
        ctypes.set_errno(0)
        r = lib.ptrace(ctypes.c_uint(request), ctypes.c_uint(pid), ctypes.c_void_p(address), ctypes.c_void_p(data))
        if r == -1:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error))
        return r

    def registers(pid):
        r = (ctypes.c_uint64 * reg_count)()
        io = IOV(ctypes.addressof(r), ctypes.sizeof(r))
        trace(0x4204, pid, 1, ctypes.addressof(io))  # GETREGSET/NT_PRSTATUS
        assert io.length == ctypes.sizeof(r)
        return r

    def write_registers(pid, r):
        io = IOV(ctypes.addressof(r), ctypes.sizeof(r))
        trace(0x4205, pid, 1, ctypes.addressof(io))

    def fd_path(pid, fd):
        try:
            return os.readlink(f"/proc/{pid}/fd/{fd}")
        except FileNotFoundError:
            return "<closed>"

    journal = case.startswith("journal-")
    if journal:
        _, window, signame = case.split("-", 2)
        selected = getattr(signal, signame.upper())
        mode, path = "managed-return", scope
    else:
        mode, path = ("raw", scope / "data") if case == "partial-read" else ("managed-publish-exclusive" if case == "partial-write" else "managed-return", scope)

    pid = os.fork()
    if pid == 0:
        stdout = os.open(out / "guest.stdout", os.O_CREAT | os.O_WRONLY, 0o600)
        stderr = os.open(out / "guest.stderr", os.O_CREAT | os.O_WRONLY, 0o600)
        os.dup2(stdout, 1)
        os.dup2(stderr, 2)
        os.close(stdout)
        os.close(stderr)
        trace(0, 0)  # TRACEME, before exec of the native fixture
        os.execve(image, [str(image), mode, str(path)], dict(PATH="/nonexistent", KEXE_ALLOW="35,37,38,39",
                  KEXE_CAP_RESOURCES_35=str(scope), KEXE_STACK_BYTES="8388608"))

    _, status = os.waitpid(pid, 0)
    assert os.WIFSTOPPED(status) and os.WSTOPSIG(status) == signal.SIGTRAP
    trace(0x4200, pid, 0, 0x100001)  # TRACESYSGOOD | EXITKILL
    entering, pending, injected, deliver = True, None, False, 0
    events, closes = [], []
    started = time.monotonic()
    try:
        while True:
            assert time.monotonic() - started < 30, "native observer deadline"
            trace(24, pid, 0, deliver)  # SYSCALL
            deliver = 0
            _, status = os.waitpid(pid, 0)
            if os.WIFEXITED(status):
                code = os.WEXITSTATUS(status)
                break
            if os.WIFSIGNALED(status):
                code = -os.WTERMSIG(status)
                break
            sig = os.WSTOPSIG(status)
            if sig == (signal.SIGTRAP | 0x80):
                r = registers(pid)
                if entering:
                    pending = None
                    if r[number] == ids["close"]:
                        name = fd_path(pid, r[args[0]])
                        closes.append(dict(fd=r[args[0]], path=name))
                        if case == "close-consumed-eintr" and not injected and name.startswith(str(scope) + "/kotoba-output-") and name.endswith("/0.tmp"):
                            pending = ("close", r[args[0]])
                    if journal and r[number] == ids["mkdirat"] and window == "directory":
                        pending = ("directory", 0)
                    if journal and r[number] == ids["openat2"] and window == "file":
                        pending = ("file", 0)
                    io_name = "read" if case == "partial-read" else "write"
                    if case in ("partial-read", "partial-write") and not injected and r[number] == ids[io_name]:
                        name = fd_path(pid, r[args[0]])
                        match = name == str(scope / "data") if case == "partial-read" else name.startswith(str(scope) + "/kotoba-output-") and name.endswith("/0.tmp")
                        if match and r[args[2]] > 1:
                            original = r[args[2]]
                            r[args[2]] = 1 if case == "partial-read" else 4
                            write_registers(pid, r)
                            pending = ("partial", r[args[2]])
                            events.append(dict(kernelTransferRequested=r[args[2]], originalRequested=original, path=name))
                elif pending is not None and not injected:
                    kind, detail = pending
                    if kind == "close":
                        assert r[result] == 0 and fd_path(pid, detail) == "<closed>", "real kernel close must consume fd"
                        r[result] = (1 << 64) - 4
                        write_registers(pid, r)
                        events.append(dict(realCloseConsumed=True, returnedErrno="EINTR"))
                        injected = True
                    elif kind == "directory" and r[result] == 0:
                        created = list(scope.glob("kotoba-output-*"))
                        if len(created) == 1:
                            os.kill(pid, selected)
                            events.append(dict(kernelCreated=str(created[0]), signal=signame.upper()))
                            injected = True
                    elif kind == "file" and r[result] < (1 << 63):
                        name = fd_path(pid, r[result])
                        if name.startswith(str(scope) + "/kotoba-output-") and name.endswith("/0.tmp"):
                            os.kill(pid, selected)
                            events.append(dict(kernelCreated=name, signal=signame.upper()))
                            injected = True
                    elif kind == "partial":
                        assert r[result] == detail, "kernel must perform the shortened transfer"
                        events.append(dict(kernelTransferred=detail))
                        injected = True
                    pending = None
                entering = not entering
            elif sig != signal.SIGTRAP:
                deliver = sig
    except BaseException:
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)
        raise

    stdout, stderr = (out / "guest.stdout").read_bytes(), (out / "guest.stderr").read_bytes()
    remaining = sorted(str(p.relative_to(scope)) for p in scope.rglob("*"))
    observation = dict(case=case, exit=code, injected=injected, events=events, closes=closes, remaining=remaining,
                       stdout=stdout.decode(errors="replace"), stderr=stderr.decode(errors="replace"))
    (out / "observations.json").write_text(json.dumps(observation, indent=2) + "\n")
    assert injected and not stdout and (scope / "sentinel").read_bytes() == b"unowned-preserve"
    if journal:
        assert code == 120 and (":signal :" + signame.upper()).encode() in stderr and b"KEXE_CLEANUP" not in stderr
        assert remaining == ["sentinel"]
    elif case == "close-consumed-eintr":
        assert code == 126 and b":stage 13}" in stderr and b"KEXE_CLEANUP" not in stderr
        assert remaining == ["sentinel"] and len([c for c in closes if c["path"].endswith("/0.tmp")]) == 1
    else:
        assert code == 0 and not stderr
        if case == "partial-read":
            assert remaining == ["data", "sentinel"] and (scope / "data").read_bytes() == bytes([0, 255, 128])
        else:
            assert remaining == ["published", "ready", "sentinel"] and (scope / "published").read_bytes() == b"preserved"
    report = dict(status="PASS_NATIVE_FS2_OBSERVED_BOUNDARY", case=case, host=[platform.system(), machine],
                  image=dict(bytes=image.stat().st_size, sha256=hashlib.sha256(image.read_bytes()).hexdigest()),
                  exit=code, kernelBoundaryObserved=True, nativeGuestUnmodified=True, events=events,
                  ownedStageRemoved=True, unownedSentinelPreserved=True, legacyRuntimeFallback=False,
                  allFaultRaceParityQualified=False)
    (out / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], case)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    cases = ["close-consumed-eintr", "partial-read", "partial-write"] + [f"journal-{window}-{sig}" for window in ("directory", "file") for sig in ("sigint", "sigterm", "sigalrm", "sigxcpu")]
    p.add_argument("--case", choices=cases, required=True)
    a = p.parse_args()
    main(a.image.resolve(), a.output.resolve(), a.case)
