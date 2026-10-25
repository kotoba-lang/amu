#!/usr/bin/env python3
"""The static runtime's wire 41 (:io/read): a static image reads its stdin.

Linear JUN-354. seed/76 and seed/77 answer wire 41 when it is granted
(KEXE_ALLOW holds 41): an empty request reads fd 0 to end of file; a decimal
n is one read of at most n bytes, "" only at end of file, extended by at most
3 bytes to finish a UTF-8 sequence it would split. The seccomp filter admits
read(0) only with wire 41 granted. The checker already admits the wire, so the
product compiler (--compiler, e.g. the bootstrap's F1.elf) builds the guests.

1. To end of file: from a file and from a pipe (UTF-8 text survives), and
   2 MiB at once; read again after end of file, the answer is "".
2. In pieces: n = 2 over "a" + three-byte characters + "b" answers "a" plus a
   whole character, then whole characters, then "b", then "" (a file, so each
   read returns what it asks for); n = 0 answers "".
3. Traps: stdin that is not UTF-8, a request that is not a decimal, a wire
   that is not granted.
4. The guest stays sandboxed: a control compiler whose filter has no read(0)
   rule dies of SIGSYS on the first read, when the kernel enforces seccomp.

Python only orchestrates processes and hashes; the runtime and the guests are
Kotoba. Run on Linux, e.g. through the podman machine:
  podman run --platform linux/arm64 --network none -v REPO:REPO -v OUT:OUT \\
    python:3.12-alpine python3 REPO/scripts/seed/check-io-read.py --compiler OUT/F1.elf --output OUT/io-read
"""
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELFHOST = "seed/X86_64-LINUX-SELFHOST-MANIFEST"
FUEL = "100000000"
NO_READ0_RULE = ("        i7 (if (kxrt-admitted? 41) (kxrt-allow-read-fd p i6 0) i6)\n", "        i7 i6\n", 2)

HEAD = ('(ns t (:export [main]))\n'
        '(defn- rd [s :string] :string (typed-cap-call :io/read :string :string s))\n'
        '(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string s)] 0))\n')
ALL = HEAD + '(defn main [] :i64 (let [a (say (rd ""))] 7))\n'
TWICE = HEAD + '(defn main [] :i64 (let [a (say (rd "")) b (say "|") c (say (rd "")) d (say "|")] 7))\n'
LENGTH = HEAD + '(defn main [] :i64 (let [a (say (string-from-i64 (string-byte-length (rd ""))))] 7))\n'
PIECES = HEAD + ('(defn- pieces [k :i64] :i64 (let [s (rd "2")] (if (= s "") k (let [a (say s) b (say "|")] (pieces (+ k 1))))))\n'
                 '(defn main [] :i64 (let [n (pieces 0)] 7))\n')
ZERO = HEAD + '(defn main [] :i64 (let [a (say "[") b (say (rd "0")) c (say "]")] 7))\n'
MALFORMED = HEAD + '(defn main [] :i64 (let [a (say (rd "x"))] 7))\n'


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


def main(compiler, output, target, seccomp_if_available=False):
    assert platform.system() == "Linux", "run on Linux"
    output.mkdir(parents=True, exist_ok=False)
    art, raw = output / "artifacts", output / "raw"
    for d in (art, raw):
        d.mkdir()
    producer = art / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)
    base_env = {"PATH": "/usr/bin:/bin", "KEXE_STRUCTURED_REPORT": "1", "KEXE_FUEL": FUEL, "KEXE_ALLOW": "37,41"}
    if seccomp_if_available:
        base_env["KEXE_SECCOMP"] = "if-available"

    def compile_(prod, name, source, tgt):
        src, out = art / (name + ".kotoba"), art / (name + ".elf")
        src.write_text(source)
        r = subprocess.run([str(prod), "compile", str(src), "--target", tgt, "--output", str(out), "--format", "static"],
                           cwd=art, env={"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art)},
                           capture_output=True, timeout=1800)
        (raw / (name + ".compile.stdout")).write_bytes(r.stdout)
        (raw / (name + ".compile.stderr")).write_bytes(r.stderr)
        assert r.returncode == 0 and not r.stderr and b":ok true" in r.stdout, (name, r.returncode, r.stderr[-400:])
        out.chmod(0o755)
        return out

    rows = []

    def case(name, elf, data, via="file", env=None, want_exit=0, stdout_is=None, stderr_has=(), stderr_lacks=()):
        e = dict(base_env, **(env or {}))
        if via == "file":
            f = art / (name + ".stdin")
            f.write_bytes(data)
            with open(f, "rb") as fh:
                x = subprocess.run([str(elf)], stdin=fh, env=e, capture_output=True, timeout=120)
        else:
            x = subprocess.run([str(elf)], input=data, env=e, capture_output=True, timeout=120)
        (raw / (name + ".stdout")).write_bytes(x.stdout)
        (raw / (name + ".stderr")).write_bytes(x.stderr)
        assert x.returncode == want_exit, (name, x.returncode, x.stdout[-300:], x.stderr[-300:])
        if stdout_is is not None:
            assert x.stdout.startswith(stdout_is + b"{:status :ok :result 7 "), (name, x.stdout[-300:])
        for s in stderr_has:
            assert s in x.stderr, (name, s, x.stderr[-300:])
        for s in stderr_lacks:
            assert s not in x.stderr, (name, s, x.stderr[-300:])
        rows.append(dict(name=name, via=via, stdinBytes=len(data), exit=x.returncode,
                         stdout=x.stdout.decode(errors="replace")[:400], stderr=x.stderr.decode(errors="replace")[:400]))

    text_in = "hello\nこんにちは\n".encode()
    all_ = compile_(producer, "all", ALL, target)
    case("all-from-file", all_, text_in, stdout_is=text_in)
    case("all-from-pipe", all_, text_in, via="pipe", stdout_is=text_in)
    case("all-empty", all_, b"", stdout_is=b"")
    case("twice", compile_(producer, "twice", TWICE, target), b"hello", stdout_is=b"hello||")
    case("two-mib", compile_(producer, "length", LENGTH, target), b"x" * 2097152, stdout_is=b"2097152")
    pieces = compile_(producer, "pieces", PIECES, target)
    case("pieces-complete-characters", pieces, "aこんb".encode(), stdout_is="aこ|ん|b|".encode())
    case("pieces-ascii", pieces, b"abcde", stdout_is=b"ab|cd|e|")
    case("zero", compile_(producer, "zero", ZERO, target), b"abc", stdout_is=b"[]")
    sigill = b":signal :SIGILL"
    case("not-utf8", all_, b"\xff\xfe", want_exit=120, stderr_has=[sigill])
    # an ungranted wire is refused by name (KEXE_CAP, as seed/82 does); a granted wire's bad request is not
    named = b"KEXE_CAP {:wire 41 :refused :not-granted}\n"
    case("malformed-request", compile_(producer, "malformed", MALFORMED, target), b"abc", want_exit=120, stderr_has=[sigill],
         stderr_lacks=[b"KEXE_CAP"])
    case("wire-not-granted", all_, b"abc", env={"KEXE_ALLOW": "37"}, want_exit=120, stderr_has=[sigill, named])

    host = {"aarch64": "aarch64-linux", "arm64": "aarch64-linux", "x86_64": "x86_64-linux", "AMD64": "x86_64-linux"}[platform.machine()]
    text, unity_pins = unity_text()
    control = compile_(producer, "control-compiler-no-read0-rule", patched(text, [NO_READ0_RULE]), host)
    enforced = not seccomp_if_available
    if enforced:
        case("control-no-read0-rule", compile_(control, "control-all", ALL, target), b"abc", want_exit=120,
             stderr_has=[b":signal :SIGSYS"])
    report = dict(status="PASS_IO_READ_RUNTIME", target=target, compiler=pin(compiler),
                  host=[platform.system(), platform.machine(), platform.release()],
                  imageSeccomp="if-available" if seccomp_if_available else "required", cases=rows,
                  controlCompiler={"mutation": "no read(0) rule in the seccomp filter, in both runtimes", "pin": pin(control)},
                  unity=unity_pins, cCompilerOrLoader=False,
                  notCovered=["a read that fails with an error other than EINTR (EBADF, EIO)",
                              "stdin closed in the middle of a UTF-8 sequence that a piece read completes"]
                             + ([] if enforced else ["control-no-read0-rule: this kernel does not enforce seccomp (KEXE_SECCOMP=if-available)"]))
    (output / "io-read.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(report["status"], target, len(rows), "cases", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--compiler", type=Path, required=True, help="an Amu-produced static compiler built from these sources")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", choices=["aarch64-linux", "x86_64-linux"], default="aarch64-linux")
    parser.add_argument("--seccomp-if-available", action="store_true",
                        help="run the images with KEXE_SECCOMP=if-available (qemu-user has no seccomp); recorded")
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve(), args.target, args.seccomp_if_available)
