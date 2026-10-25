#!/usr/bin/env python3
"""The static runtime's wire-42 (:gpu/compute) transport, against a scripted provider.

ADR 0371 step 2. seed/76 and seed/77 carry :gpu/compute requests over two
inherited fds (KEXE_CAP_RESOURCES_42=REQUEST,ANSWER), framed as a u32
little-endian length and the bytes. Two parts:

1. The start-up check, with --compiler (the Amu-produced static compiler
   built from these sources, e.g. S3.elf from selfhost-bootstrap.py). With
   wire 42 granted in KEXE_ALLOW, a missing or invalid knob must exit 2: no
   knob, one fd, not a number, fd < 3, fd > 1023, the same fd twice, a closed
   fd, a regular file. Valid pipes run; a knob without the grant is ignored.
   The checker admits wire 42 (ADR 0371 step 3), so --compiler compiles a
   guest that calls it.

2. The transport end to end, with guests from --compiler. They run against
   a scripted provider in this script, which replays fixed answers and checks
   every request byte. Cases: answers round-trip,
   including an empty frame and a 4 MiB answer; a named refusal and a bare one
   trap with a KEXE_TRAP line; end of file, a closed request pipe (SIGPIPE
   is ignored, so EPIPE traps), and an answer frame over 8 MiB all trap
   with exit 120. No wire-35 scope is granted, so the seccomp filter admits
   read only through the new rule. A control compiler whose read rule names
   another fd must die of SIGSYS on the first answer, when the kernel enforces
   seccomp.

Python only orchestrates processes, pipes and hashes; the runtime and the
guests are Kotoba. Run on Linux, e.g. through the podman machine:
  podman run --platform linux/arm64 -v REPO:REPO -v OUT:OUT python:3.12-alpine \
    python3 REPO/scripts/seed/check-gpu-runtime-transport.py --compiler OUT/S3.elf --output OUT/gpu
"""
import argparse
import hashlib
import json
import os
import platform
import subprocess
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELFHOST = "seed/X86_64-LINUX-SELFHOST-MANIFEST"
FUEL = "100000000"

# The control: the read rule names another fd, in both runtimes.
WRONG_READ_FD = ("(kxrt-allow-read-fd p i2 (kxrt-gl 312))", "(kxrt-allow-read-fd p i2 (+ (kxrt-gl 312) 100))", 2)

PLAIN = "(ns t (:export [main]))\n(defn main [] :i64 42)\n"
GPU_DEFS = ('(defn- gpu [s :string] :string (typed-cap-call 42 :string :string s))\n'
            '(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string (string-concat s "\\n"))] 0))\n')
ROUND = ("(ns t (:export [main]))\n" + GPU_DEFS +
         '(defn main [] :i64\n'
         '  (let [a (gpu "INFO") x (say a) b (gpu "ALLOC 4096") y (say b)\n'
         '        c (gpu "WRITE 1 0 00ff") z (say c) d (gpu "") w (say d)]\n'
         '    (string-length a)))\n')
ONE = "(ns t (:export [main]))\n" + GPU_DEFS + '(defn main [] :i64 (string-length (gpu "MAP /m 0 8")))\n'

INFO = b"Scripted GPU|1.3.0|1024|1"
ROUND_SCRIPT = [(b"INFO", INFO), (b"ALLOC 4096", b"1"), (b"WRITE 1 0 00ff", b"1"), (b"", b"")]
REFUSAL = b"!gpu/while-recording MAP while recording (BEGIN open): finish with SUBMIT first"
BIG = b"a" * 4194304


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def unity_text():
    paths = [p for p in (ROOT / SELFHOST).read_text().splitlines() if p and not p.startswith("#")]
    return "".join((ROOT / p).read_text() + "\n" for p in paths), {p: pin(ROOT / p) for p in [SELFHOST, *paths]}


def patched(text, edits):
    for old, new, *count in edits:
        n = count[0] if count else 1
        assert text.count(old) == n, ("patch anchor", old[:60], text.count(old))
        text = text.replace(old, new)
    return text


def read_exact(fd, n):
    buf = b""
    while len(buf) < n:
        chunk = os.read(fd, n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def write_frame(fd, data):
    os.write(fd, len(data).to_bytes(4, "little"))
    view = memoryview(data)
    while view:
        view = view[os.write(fd, view):]


class Provider(threading.Thread):
    """Replays SCRIPT: per step, read one request frame, compare, then act."""

    def __init__(self, req_r, ans_w, script, mode):
        super().__init__(daemon=True)
        self.req_r, self.ans_w, self.script, self.mode, self.got = req_r, ans_w, script, mode, []

    def run(self):
        try:
            if self.mode == "close-request":
                fd, self.req_r = self.req_r, None
                os.close(fd)
                return
            for _request, answer in self.script:
                head = read_exact(self.req_r, 4)
                if head is None:
                    return
                body = read_exact(self.req_r, int.from_bytes(head, "little"))
                self.got.append(body)
                if self.mode == "eof":
                    return
                if self.mode == "oversize":
                    os.write(self.ans_w, (8388609).to_bytes(4, "little"))
                    return
                write_frame(self.ans_w, answer)
        except OSError:
            pass
        finally:
            for fd in (self.req_r, self.ans_w):
                if fd is not None:
                    try:
                        os.close(fd)
                    except OSError:
                        pass


def main(compiler, output, target, seccomp_if_available=False):
    assert platform.system() == "Linux", "run on Linux"
    output.mkdir(parents=True, exist_ok=False)
    art, raw = output / "artifacts", output / "raw"
    art.mkdir()
    raw.mkdir()
    producer = art / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)
    base_env = {"PATH": "/usr/bin:/bin", "KEXE_STRUCTURED_REPORT": "1", "KEXE_FUEL": FUEL}
    if seccomp_if_available:
        base_env["KEXE_SECCOMP"] = "if-available"

    def compile_(prod, name, source, tgt, fmt="static", success=True):
        src, out = art / (name + ".kotoba"), art / (name + ".elf")
        src.write_text(source)
        r = subprocess.run([str(prod), "compile", str(src), "--target", tgt, "--output", str(out), "--format", fmt],
                           cwd=art, env={"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art)},
                           capture_output=True, timeout=1800)
        (raw / (name + ".compile.stdout")).write_bytes(r.stdout)
        (raw / (name + ".compile.stderr")).write_bytes(r.stderr)
        if success:
            assert r.returncode == 0 and not r.stderr and b":ok true" in r.stdout, (name, r.returncode, r.stderr[-400:])
            out.chmod(0o755)
        return out, r

    # ---- part 1: the start-up check, with the compiler under test ----
    plain, _ = compile_(producer, "plain", PLAIN, target)
    compile_(producer, "checker-admits-42", ONE, target)
    regular = art / "regular.txt"
    regular.write_text("not a pipe\n")
    knob_rows = []

    def knob(name, allow, value, fds="pipes", want_exit=2):
        env = dict(base_env, KEXE_ALLOW=allow)
        pass_fds, opened = (), []
        if fds == "pipes":
            r1, w1 = os.pipe()
            r2, w2 = os.pipe()
            opened = [r1, w1, r2, w2]
            pass_fds, req, ans = (w1, r2), w1, r2
        elif fds == "files":
            f1, f2 = os.open(regular, os.O_RDONLY), os.open(regular, os.O_RDONLY)
            opened = [f1, f2]
            pass_fds, req, ans = (f1, f2), f1, f2
        else:
            req, ans = 900, 901
        if value is not None:
            env["KEXE_CAP_RESOURCES_42"] = value.format(req=req, ans=ans)
        x = subprocess.run([str(plain)], env=env, pass_fds=pass_fds, capture_output=True, timeout=60)
        for fd in opened:
            os.close(fd)
        (raw / ("knob-" + name + ".stdout")).write_bytes(x.stdout)
        (raw / ("knob-" + name + ".stderr")).write_bytes(x.stderr)
        assert x.returncode == want_exit, (name, x.returncode, x.stdout, x.stderr)
        if want_exit == 0:
            assert b":status :ok :result 42" in x.stdout, (name, x.stdout)
        knob_rows.append(dict(name=name, allow=allow, knob=value, fds=fds, exit=x.returncode))

    knob("no-knob", "37,42", None)
    knob("one-fd", "37,42", "{req}")
    knob("not-a-number", "37,42", "{req},x")
    knob("fd-below-3", "37,42", "2,{ans}")
    knob("fd-above-1023", "37,42", "1024,{ans}")
    knob("same-fd", "37,42", "{req},{req}")
    knob("closed-fds", "37,42", "{req},{ans}", fds="closed")
    knob("regular-files", "37,42", "{req},{ans}", fds="files")
    knob("valid-pipes", "37,42", "{req},{ans}", want_exit=0)
    knob("not-granted-ignored", "37", "x", want_exit=0)

    # ---- part 2: the transport, through a test-only compiler ----
    text, unity_pins = unity_text()
    control = patched(text, [WRONG_READ_FD])
    test_compiler = producer
    control_compiler, _ = compile_(producer, "control-compiler-wrong-read-fd", control, "aarch64-linux")

    def e2e(name, prod, source, script, mode="replay", want_exit=0, stdout_has=(), stderr_has=()):
        elf, _ = compile_(prod, "e2e-" + name, source, target)
        r1, w1 = os.pipe()
        r2, w2 = os.pipe()
        env = dict(base_env, KEXE_ALLOW="37,42", KEXE_CAP_RESOURCES_42=f"{w1},{r2}")
        p = subprocess.Popen([str(elf)], env=env, pass_fds=(w1, r2), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        os.close(w1)
        os.close(r2)
        prov = Provider(r1, w2, script, mode)
        prov.start()
        out, err = p.communicate(timeout=120)
        prov.join(timeout=30)
        (raw / ("e2e-" + name + ".stdout")).write_bytes(out)
        (raw / ("e2e-" + name + ".stderr")).write_bytes(err)
        assert p.returncode == want_exit, (name, p.returncode, out[-300:], err[-300:])
        for s in stdout_has:
            assert s in out, (name, s, out[-300:])
        for s in stderr_has:
            assert s in err, (name, s, err[-300:])
        if mode == "replay" and want_exit == 0:
            assert prov.got == [req for req, _ in script], (name, prov.got)
        return dict(name=name, exit=p.returncode, requests=len(prov.got), image=pin(elf))

    trap = b"KEXE_TRAP {:kind :capability :wire 42 :refusal :"
    rows = [
        e2e("round-trip", test_compiler, ROUND, ROUND_SCRIPT,
            stdout_has=[INFO + b"\n1\n1\n\n", b":status :ok :result %d" % len(INFO)]),
        e2e("four-mib-answer", test_compiler, ONE, [(b"MAP /m 0 8", BIG)], stdout_has=[b":status :ok :result 4194304"]),
        e2e("named-refusal", test_compiler, ONE, [(b"MAP /m 0 8", REFUSAL)], want_exit=120,
            stderr_has=[trap + b"gpu/while-recording}\n"]),
        e2e("bare-refusal", test_compiler, ONE, [(b"MAP /m 0 8", b"!MAP short read")], want_exit=120,
            stderr_has=[trap + b"unnamed}\n"]),
        e2e("provider-eof", test_compiler, ONE, [(b"MAP /m 0 8", b"")], mode="eof", want_exit=120),
        e2e("request-pipe-closed", test_compiler, ONE, [], mode="close-request", want_exit=120),
        e2e("oversize-answer", test_compiler, ONE, [(b"MAP /m 0 8", b"")], mode="oversize", want_exit=120,
            stderr_has=[b"string/too-large"]),
    ]
    enforced = not seccomp_if_available
    if enforced:
        rows.append(e2e("control-wrong-read-fd", control_compiler, ROUND, ROUND_SCRIPT, mode="control",
                        want_exit=120, stderr_has=[b":signal :SIGSYS"]))
    report = dict(status="PASS_GPU_RUNTIME_TRANSPORT", target=target, compiler=pin(compiler),
                  host=[platform.system(), platform.machine(), platform.release()],
                  executionNative=target.split("-")[0] == {"arm64": "aarch64", "AMD64": "x86_64"}.get(platform.machine(), platform.machine()),
                  imageSeccomp="if-available" if seccomp_if_available else "required",
                  checkerAdmitsWire42=True, knob=knob_rows, transport=rows,
                  testOnlyCompilers={"controlWrongReadFd": pin(control_compiler)},
                  unity=unity_pins, cCompilerOrLoader=False,
                  notCovered=[] if enforced else ["control-wrong-read-fd: this kernel does not enforce seccomp (KEXE_SECCOMP=if-available)"])
    (output / "gpu-runtime-transport.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], target, len(knob_rows), "start-up cases", len(rows), "transport cases", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--compiler", type=Path, required=True, help="an Amu-produced static compiler built from these sources")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", choices=["aarch64-linux", "x86_64-linux"], default="aarch64-linux")
    parser.add_argument("--seccomp-if-available", action="store_true",
                        help="run the images with KEXE_SECCOMP=if-available (qemu-user has no seccomp); recorded")
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve(), args.target, args.seccomp_if_available)
