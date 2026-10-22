#!/usr/bin/env python3
"""x86_64-linux standalone scalar ELF suite through the loaderless compiler.

Port of the retired check-x86_64-linux.py (scripts/seed/RETIRED.md): the
same 55 programs and 14 refusals, compiled by an Amu-produced static compiler
(--compiler, e.g. S3.elf from selfhost-bootstrap.py) with no C loader, then
executed as ordinary Linux processes. On a non-x86_64 kernel the ELFs run
only if the kernel can execute them (binfmt); the receipt records the
execution host. Not ported: the AArch64 fuel reference and the
adopted-vs-cross container identity, which needed the removed loader.
"""
import argparse
import hashlib
import json
import platform
import random
import re
import signal
import struct
import subprocess
from pathlib import Path

MIN = -(1 << 63)
MAX = (1 << 63) - 1


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def cases():
    rows = []

    def add(name, expr, value=None, helpers="", fuel=1000000, trap=None):
        source = f"(ns scalar-{name} (:export [main]))\n{helpers}\n(defn main [] :i64 {expr})\n"
        rows.append(dict(name=name, source=source, result=value, fuel=fuel, trap=trap))

    add("answer", "(+ 40 2)", 42)
    add("min", str(MIN), MIN)
    add("max", str(MAX), MAX)
    add("wrap-add", f"(+ {MAX} 1)", MIN)
    add("wrap-mul", f"(* {MIN} -1)", MIN)
    add("subtract", "(- -19 34)", -53)
    add("quot-neg", "(quot -103 7)", -14)
    add("quot-both-neg", "(quot -103 -7)", 14)
    add("bits", "(bit-xor (bit-and -1 255) (bit-or 256 7))", 504)
    add("bit-not", "(bit-not 5)", -6)
    add("shift-neg", "(i64-shift-left 1 -1)", MIN)
    add("shift-mask", "(u64-shift-right -1 64)", -1)
    add("shift-arithmetic", f"(i64-shift-right {MIN} 65)", -(1 << 62))
    add("signed-compare", f"(if (and (< {MIN} {MAX}) (> {MAX} -1) (<= -5 -5) (>= 7 7) (= 9 9)) 42 -1)", 42)
    add("boolean", "(if (or false (not false)) 42 -1)", 42)
    add("loop", "(loop [i 0 s 0] (if (< i 100) (recur (inc i) (+ s i)) s))", 4950)
    add("parallel-recur", "(loop [i 0 a 3 b 7] (if (< i 5) (recur (inc i) b a) (- a b)))", 4)
    add("five-args", "(mix 1 2 3 4 5)", 54321,
        "(defn- mix [a :i64 b :i64 c :i64 d :i64 e :i64] :i64 (+ a (* b 10) (* c 100) (* d 1000) (* e 10000)))")
    add("recursive-call", "(fib 10)", 55,
        "(defn- fib [n :i64] :i64 (if (< n 2) n (+ (fib (- n 1)) (fib (- n 2)))))")
    add("tail-call", "(sum 100 0)", 5050,
        "(defn- sum [n :i64 s :i64] :i64 (if (= n 0) s (sum (dec n) (+ s n))))")
    add("div-zero", "(quot 7 0)", trap="SIGFPE")
    add("div-overflow", f"(quot {MIN} -1)", trap="SIGFPE")
    add("fuel-exhausted", "(loop [i 0] (if (< i 100) (recur (inc i)) i))", fuel=2, trap="SIGILL")
    rng = random.Random(20261015)

    def signed(n):
        return ((n + (1 << 63)) % (1 << 64)) - (1 << 63)
    for i in range(32):
        a, b = rng.randrange(MIN, MAX + 1), rng.randrange(MIN, MAX + 1)
        op, expected = [
            ("+", signed(a + b)), ("-", signed(a - b)), ("*", signed(a * b)),
            ("bit-and", a & b), ("bit-or", a | b), ("bit-xor", a ^ b),
            ("i64-shift-left", signed(a << (b & 63))),
            ("u64-shift-right", signed((a % (1 << 64)) >> (b & 63))),
        ][i % 8]
        add(f"full64-{i}", f"(calculate {a} {b})", expected,
            f"(defn- calculate [a :i64 b :i64] :i64 ({op} a b))")
    return rows


def verify_elf(data, code_size):
    header = struct.unpack("<16sHHIQQQIHHHHHH", data[:64])
    assert header[:4] == (b"\x7fELF\x02\x01\x01" + b"\0" * 9, 2, 62, 1)
    assert header[4:] == (0x401000, 64, 0, 0, 64, 56, 3, 0, 0, 0)
    ph = [struct.unpack_from("<IIQQQQQQ", data, 64 + 56 * i) for i in range(3)]
    end = 4096 + code_size
    data_offset = (end + 4095) & -4096
    assert ph[0] == (1, 5, 0, 0x400000, 0x400000, end, end, 4096)
    assert ph[1] == (1, 6, data_offset, 0x400000 + data_offset, 0x400000 + data_offset, 16, 16, 4096)
    assert ph[2] == (0x6474e551, 6, 0, 0, 0, 0, 0, 16)
    assert len(data) == data_offset + 16
    assert not any(data[232:4096]) and not any(data[end:data_offset])
    return data_offset


def main(compiler, output, seccomp_if_available=False):
    assert platform.system() == "Linux"
    output.mkdir(parents=True, exist_ok=False)
    art, raw = output / "artifacts", output / "raw"
    art.mkdir()
    raw.mkdir()
    env = {"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art)}
    if seccomp_if_available:
        env["KEXE_SECCOMP"] = "if-available"

    def compile_(name, source, extra=(), sentinel=None):
        src, elf = art / (name + ".kotoba"), art / (name + ".elf")
        src.write_text(source)
        if sentinel is not None:
            elf.write_bytes(sentinel)
        r = subprocess.run([str(compiler), "compile", str(src), "--target", "x86_64-linux", "--output", str(elf), *extra],
                           cwd=art, env=env, capture_output=True, timeout=180)
        (raw / (name + ".stdout")).write_bytes(r.stdout)
        (raw / (name + ".stderr")).write_bytes(r.stderr)
        return elf, r

    rows = []
    for case in cases():
        elf, r = compile_(case["name"], case["source"], ["--fuel", str(case["fuel"])])
        assert r.returncode == 0 and not r.stderr, (case["name"], r.returncode, r.stderr)
        fields = {k.decode(): int(v) for k, v in re.findall(rb":([a-z-]+) (\d+)", r.stdout)}
        data = elf.read_bytes()
        assert fields["bytes"] == len(data)
        data_offset = verify_elf(data, fields["code-bytes"])
        assert struct.unpack_from("<QQ", data, data_offset) == (0, case["fuel"])
        assert 0 < fields["function-offset"] < fields["code-bytes"]
        elf.chmod(0o700)
        x = subprocess.run([str(elf)], env={"PATH": "/usr/bin:/bin"}, capture_output=True, timeout=15)
        (raw / (case["name"] + ".run.stdout")).write_bytes(x.stdout)
        if case["trap"]:
            assert x.returncode == -getattr(signal, case["trap"]) and not x.stdout, (case["name"], x)
        else:
            assert x.returncode == 0 and x.stdout == struct.pack("<q", case["result"]), (case["name"], x)
        rows.append(dict(name=case["name"], elf=pin(elf), exit=x.returncode,
                         stdoutSHA256=hashlib.sha256(x.stdout).hexdigest()))
    refusals = {
        "vector": "(ns refused (:export [main])) (defn main [] :i64 (vector-count [1 2]))",
        "string": '(ns refused (:export [main])) (defn main [] :i64 (string-length "hello"))',
        "float": "(ns refused (:export [main])) (defn main [] :i64 (f64-to-i64-truncating (f64-add 1.0 2.0)))",
        "unused-vector": "(ns refused (:export [main])) (defn- unused [v :vector-i64] :i64 (vector-count v)) (defn main [] :i64 42)",
        "six-params": "(ns refused (:export [main])) (defn- six [a :i64 b :i64 c :i64 d :i64 e :i64 f :i64] :i64 (+ a b c d e f)) (defn main [] :i64 42)",
        "main-arity": "(ns refused (:export [main])) (defn main [x :i64] :i64 x)",
        "extra-export": "(ns refused (:export [main other])) (defn main [] :i64 42) (defn other [] :i64 7)",
    }
    refused = []
    for name, source in refusals.items():
        elf, r = compile_("refuse-" + name, source)
        assert r.returncode != 0 and not elf.exists() and b"E710" in r.stderr, (name, r.stdout, r.stderr)
        refused.append(name)
    for name, extra in [("policy", ["--policy", "unknown"]), ("source-path", ["--source-path", "unknown"]),
                        ("zero-fuel", ["--fuel", "0"]), ("negative-fuel", ["--fuel", "-1"]),
                        ("bad-fuel", ["--fuel", "12x"]), ("overflow-fuel", ["--fuel", "99999999999999999"])]:
        elf, r = compile_("refuse-" + name, cases()[0]["source"], extra)
        assert r.returncode == 2 and b"E7100" in r.stderr and not elf.exists(), (name, r)
        refused.append(name)
    elf, r = compile_("existing-output", cases()[0]["source"], sentinel=b"preserve original")
    assert r.returncode == 2 and elf.read_bytes() == b"preserve original"
    refused.append("existing-output")
    report = dict(status="PASS_X86_64_SCALAR_ELF_LOADERLESS", compiler=pin(compiler),
                  host=[platform.system(), platform.machine(), platform.release()],
                  x86ExecutionNative=platform.machine() in ("x86_64", "AMD64"),
                  compilerSeccomp="if-available" if seccomp_if_available else "required",
                  cases=rows, refusals=refused, cCompilerOrLoader=False,
                  notPorted=["aarch64 fuel reference (needed the removed loader's structured report)",
                             "adopted vs cross-closure AArch64 container identity (cross closure retired)"])
    (output / "scalar-suite.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], len(rows), "programs", len(refused), "refusals", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True, help="an Amu-produced static compiler (e.g. S3.elf)")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seccomp-if-available", action="store_true",
                        help="run the compiler with KEXE_SECCOMP=if-available (kernels without seccomp, e.g. qemu-user); recorded")
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve(), args.seccomp_if_available)
