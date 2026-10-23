#!/usr/bin/env python3
"""Observe the fixed Kotoba provider gate on a native x86 kernel.

Amu builds the guest; the guest checks time/entropy without printing random
bytes. Python stages/observes and adds an inherited restrictive syscall
filter for the ENOSYS probe. The guest's own filter and grants stay intact.
This is not a compiler, provider implementation or runtime fallback.
"""
import argparse
import ctypes
import hashlib
import json
import platform
import re
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "seed/tests/native-clock-entropy.kotoba"
SOURCE_SHA256 = "83c64d0d27d10ce08d4150fe659f4d739cb5750c6060725c79746426fccf4861"


def enosys_filter():
    # Restrict getrandom only, before exec; the native guest adds its own filter.
    # Unlike ptrace syscall replacement, this never fabricates a negative syscall
    # number that would correctly trigger the guest's x32/negative-number refusal.
    class Filter(ctypes.Structure):
        _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte),
                    ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint32)]

    class Program(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ushort),
                    ("filter", ctypes.POINTER(Filter))]

    operations = [(0x20, 0, 0, 0), (0x15, 0, 1, 318),
                  (0x06, 0, 0, 0x00050000 | 38), (0x06, 0, 0, 0x7fff0000)]
    instructions = (Filter * len(operations))(*(Filter(*op) for op in operations))
    program = Program(len(operations), instructions)
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.argtypes = [ctypes.c_int] + [ctypes.c_ulong] * 4

    def install():
        if libc.prctl(38, 1, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "PR_SET_NO_NEW_PRIVS")
        if libc.prctl(22, 2, ctypes.addressof(program), 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "PR_SET_SECCOMP")

    return install, dict(method="inherited getrandom ERRNO38 filter",
                         filterSHA256=hashlib.sha256(bytes(instructions)).hexdigest(),
                         guestFilterUnchanged=True, grantsUnchanged=True)


def pin(path):
    data = path.read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def static_x86(path):
    data = path.read_bytes()
    assert data[:6] == b"\x7fELF\x02\x01"
    assert struct.unpack_from("<HH", data, 16) == (2, 62)
    phoff = struct.unpack_from("<Q", data, 32)[0]
    size, count = struct.unpack_from("<HH", data, 54)
    assert all(struct.unpack_from("<I", data, phoff + i * size)[0] not in (2, 3)
               for i in range(count)), "dynamic segment or ELF interpreter"
    return dict(**pin(path), interpreter=False, dynamic=False)


def main(compiler, out):
    assert platform.system() == "Linux" and platform.machine() == "x86_64"
    assert pin(ROOT / SOURCE)["sha256"] == SOURCE_SHA256, "provider fixture source drift"
    static_x86(compiler)
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    src, guest = out / "provider-gate.kotoba", out / "provider-gate.elf"
    src.write_bytes((ROOT / SOURCE).read_bytes())
    calls = []

    def observe(name, argv, env, expected, result=None, diagnostic=None, preexec_fn=None):
        completed = subprocess.run(list(map(str, argv)), cwd=out, env=env,
                                   capture_output=True, timeout=300, preexec_fn=preexec_fn)
        # This fixed guest returns booleans/status only; it never prints entropy.
        (out / (name + ".stdout")).write_bytes(completed.stdout)
        (out / (name + ".stderr")).write_bytes(completed.stderr)
        assert completed.returncode == expected, (name, completed.returncode, completed.stderr[-400:])
        if expected == 0:
            assert not completed.stderr, (name, completed.stderr[-400:])
        if expected == 120:
            combined = completed.stdout + completed.stderr
            assert not any(marker in combined for marker in
                           (b"SIGSEGV", b"SIGBUS", b"SIGFPE", b"SIGALRM", b"SIGXCPU",
                            b"SIGSYS", b":kind :fuel", b":kind :budget")), (name, combined[-400:])
        if result is not None:
            assert re.search(rb":result " + str(result).encode() + rb"\b", completed.stdout), name
        if diagnostic:
            assert diagnostic.encode() in completed.stderr, name
        calls.append(dict(name=name, exit=completed.returncode, expectedExit=expected,
                          expectedNativeResult=result,
                          stdoutSHA256=hashlib.sha256(completed.stdout).hexdigest(),
                          stderrSHA256=hashlib.sha256(completed.stderr).hexdigest()))
        (out / "calls.json").write_text(json.dumps(calls, indent=2) + "\n")

    observe("compile", [compiler, "compile", src, "--target", "x86_64-linux",
                        "--output", guest, "--format", "static"],
            {"PATH": "/nonexistent", "KEXE_ALLOW": "35,37,38,39",
             "KEXE_CAP_RESOURCES_35": str(out), "KEXE_STACK_BYTES": "8388608"}, 0)
    image = static_x86(guest)
    guest.chmod(0o700)

    def runtime(grants):
        return {"PATH": "/nonexistent", "KEXE_ALLOW": grants,
                "KEXE_FUEL": "1000000", "KEXE_STRUCTURED_REPORT": "1"}

    observe("clock", [guest, "clock"], runtime("7,38"), 0, result=1)
    observe("entropy", [guest, "entropy"], runtime("23,38"), 0, result=1)
    invalid = [("clock-empty", "clock-request", "", "7,38"),
               ("clock-case", "clock-request", "Wall", "7,38"),
               ("clock-space", "clock-request", "monotonic ", "7,38"),
               ("clock-newline", "clock-request", "wall\n", "7,38"),
               ("entropy-empty", "entropy-request", "", "23,38"),
               ("entropy-zero", "entropy-request", "0", "23,38"),
               ("entropy-over", "entropy-request", "257", "23,38"),
               ("entropy-negative", "entropy-request", "-1", "23,38"),
               ("entropy-suffix", "entropy-request", "1x", "23,38"),
               ("entropy-overflow", "entropy-request", "18446744073709551616", "23,38"),
               ("entropy-padded-zero", "entropy-request", "0000000000000000000", "23,38")]
    for name, mode, value, grants in invalid:
        observe(name, [guest, mode, value], runtime(grants), 120)
    observe("clock-no-grant", [guest, "clock"], runtime("38"), 120)
    observe("entropy-no-grant", [guest, "entropy"], runtime("38"), 120)
    install, filter_receipt = enosys_filter()
    observe("entropy-enosys", [guest, "entropy"], runtime("23,38"), 126,
            diagnostic="entropy/unavailable", preexec_fn=install)
    fault = out / "enosys-filter.json"
    fault.write_text(json.dumps(filter_receipt, indent=2) + "\n")
    report = dict(status="PASS_NATIVE_X86_CLOCK_ENTROPY", compiler=pin(compiler),
                  source=dict(path=SOURCE, **pin(ROOT / SOURCE)), image=image,
                  host=[platform.system(), platform.machine(), platform.release()],
                  positiveCases=2, malformedRequests=len(invalid), missingGrants=2,
                  getrandomENOSYS=dict(exit=126, fallback=False, filter=pin(fault)),
                  randomBytesPrintedOrSaved=False, statisticalRNGCertification=False,
                  nativeGuestOwnsPositiveVerdict=True, cCompilerOrLoader=False,
                  legacyRuntimeFallback=False, emulation=False)
    (out / "native-clock-entropy.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], "2 positives /11 malformed /2 missing grants /ENOSYS", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve())
