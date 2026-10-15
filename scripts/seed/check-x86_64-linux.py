#!/usr/bin/env python3
"""Qualify the optional native scalar cross-compiler and its Linux ELF output."""
import argparse
import hashlib
import json
import os
import platform
import random
import re
import signal
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIN = -(1 << 63)
MAX = (1 << 63) - 1


def pin(path):
    data = path.read_bytes()
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


def prepare(build, output):
    output.mkdir(parents=True, exist_ok=False)
    artifacts = output / "artifacts"
    raw = output / "raw"
    artifacts.mkdir()
    raw.mkdir()
    report = json.loads((build / "report.json").read_text())
    loader = build / "host/kexe-loader"
    producer = build / "artifacts/G2.bin"
    assert pin(producer)["sha256"] == report["generations"][-1]["native"]["sha256"]
    for row in report["inputs"]:
        assert pin(Path(row["path"])) == {k: row[k] for k in ("bytes", "sha256")}, "build source pin mismatch"
    inputs = {p: pin(p) for p in [loader, producer, build / "report.json",
                                *[Path(x["path"]) for x in report["inputs"]]]}
    env = {k: v for k, v in os.environ.items() if not k.startswith("KEXE_")}
    env.update(KEXE_COMMAND="1", KEXE_CAP_RESOURCES_35=str(artifacts), KEXE_FUEL="off",
               KEXE_VECTORS="4194304", KEXE_VECTOR_ITEMS="134217728",
               KEXE_STRING_POOL="268435456", KEXE_PAIRS="16777216",
               KEXE_CPU_SECONDS="120", KEXE_WALL_SECONDS="120")
    prefix = [loader, producer, "0", "0", "aarch64", "35,37,38,39", "--"]

    def compile(name, source, extra=(), sentinel=None):
        src, elf = artifacts / (name + ".kotoba"), artifacts / (name + ".elf")
        src.write_text(source)
        if sentinel is not None:
            elf.write_bytes(sentinel)
        source_before = pin(src)
        args = prefix + ["compile", src, "--target", "x86_64-linux", "--output", elf, *extra]
        result = subprocess.run(list(map(str, args)), cwd=artifacts, env=env, capture_output=True, timeout=180)
        (raw / (name + ".stdout")).write_bytes(result.stdout)
        (raw / (name + ".stderr")).write_bytes(result.stderr)
        assert pin(src) == source_before, "guest source changed during compilation"
        assert all(pin(p) == v for p, v in inputs.items()), "input mutation"
        return elf, result

    def reference_a64(case):
        name = case["name"]
        src = artifacts / (name + ".kotoba")
        container, native = artifacts / (name + ".a64.kseed"), artifacts / (name + ".a64.bin")
        for tag, args in [
            ("compile", ["compile", src, "--target", "aarch64-macos", "--output", container]),
            ("extract", ["extract-native", container, "--symbol", "main", "--output", native]),
        ]:
            source_before = pin(src)
            result = subprocess.run(list(map(str, prefix + args)), env=env, cwd=artifacts,
                                    capture_output=True, timeout=180)
            (raw / (name + ".a64-" + tag + ".stdout")).write_bytes(result.stdout)
            (raw / (name + ".a64-" + tag + ".stderr")).write_bytes(result.stderr)
            assert result.returncode == 0 and not result.stderr, (name, tag, result)
            assert pin(src) == source_before and all(pin(p) == v for p, v in inputs.items()), "reference input mutation"
        offset = int(re.search(rb":offset (\d+)", result.stdout)[1])
        guest_env = {k: v for k, v in env.items() if not k.startswith("KEXE_")}
        guest_env.update(KEXE_FUEL=str(case["fuel"]), KEXE_STRUCTURED_REPORT="1",
                         KEXE_CPU_SECONDS="10", KEXE_WALL_SECONDS="10")
        result = subprocess.run(list(map(str, [loader, native, offset, 0, "aarch64", "-"])),
                                env=guest_env, capture_output=True, timeout=15)
        (raw / (name + ".a64-execute.stdout")).write_bytes(result.stdout)
        (raw / (name + ".a64-execute.stderr")).write_bytes(result.stderr)
        fuel = re.search(rb":fuel \{:initial (\d+) :remaining (\d+)\}", result.stdout)
        assert fuel and int(fuel[1]) == case["fuel"]
        if case["trap"]:
            assert result.returncode == 120 and b":status :trap" in result.stdout, (name, result)
        else:
            value = re.search(rb":result (-?\d+)", result.stdout)
            assert result.returncode == 0 and value and int(value[1]) == case["result"], (name, result)
        return {"remainingFuel": int(fuel[2]), "nativePin": pin(native), "exit": result.returncode}

    rows = []
    for case in cases():
        elf, result = compile(case["name"], case["source"], ["--fuel", str(case["fuel"])])
        assert result.returncode == 0 and not result.stderr, (case["name"], result.returncode, result.stderr)
        fields = {k.decode(): int(v) for k, v in re.findall(rb":([a-z-]+) (\d+)", result.stdout)}
        data = elf.read_bytes()
        assert fields["bytes"] == len(data)
        data_offset = verify_elf(data, fields["code-bytes"])
        assert struct.unpack_from("<QQ", data, data_offset) == (0, case["fuel"])
        code = artifacts / (case["name"] + ".bin")
        code.write_bytes(data[4096:4096 + fields["code-bytes"]])
        assert 0 < fields["function-offset"] < fields["code-bytes"]
        rows.append({**case, "elf": str(elf.relative_to(output)), "native": str(code.relative_to(output)),
                     "offset": fields["function-offset"], "elfPin": pin(elf), "nativePin": pin(code),
                     "aarch64Reference": reference_a64(case)})
    # The optional entry must preserve the adopted AArch64 route byte-for-byte.
    a64_identity = []
    for case in cases()[:3]:
        src = artifacts / (case["name"] + ".kotoba")
        images = []
        for label, compiler in [("adopted", ROOT / "seed/bootstrap/adopted-20261012.bin"), ("extended", producer)]:
            container = artifacts / (case["name"] + "." + label + ".kseed")
            args = [loader, compiler, "0", "0", "aarch64", "35,37,38,39", "--", "compile", src,
                    "--target", "aarch64-macos", "--output", container]
            result = subprocess.run(list(map(str, args)), cwd=artifacts, env=env, capture_output=True, timeout=180)
            (raw / (case["name"] + "." + label + ".stdout")).write_bytes(result.stdout)
            (raw / (case["name"] + "." + label + ".stderr")).write_bytes(result.stderr)
            assert result.returncode == 0 and not result.stderr, result
            images.append(container.read_bytes())
        assert images[0] == images[1], "existing AArch64 route changed"
        a64_identity.append({"name": case["name"], "containerSHA256": hashlib.sha256(images[0]).hexdigest()})
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
        elf, result = compile("refuse-" + name, source)
        assert result.returncode != 0 and not elf.exists(), (name, result.stdout, result.stderr)
        assert b"E710" in result.stderr, (name, result.stderr)
        refused.append(name)
    for name, extra in [("policy", ["--policy", "unknown"]), ("source-path", ["--source-path", "unknown"]),
                        ("zero-fuel", ["--fuel", "0"]), ("negative-fuel", ["--fuel", "-1"]),
                        ("bad-fuel", ["--fuel", "12x"]), ("overflow-fuel", ["--fuel", "99999999999999999"])]:
        elf, result = compile("refuse-" + name, cases()[0]["source"], extra)
        assert result.returncode == 2 and b"E7100" in result.stderr and not elf.exists()
        refused.append(name)
    elf, result = compile("existing-output", cases()[0]["source"], sentinel=b"preserve original")
    assert result.returncode == 2 and elf.read_bytes() == b"preserve original"
    refused.append("existing-output")
    suite = {"status": "PASS_NATIVE_CROSS_COMPILE_ELF_AND_REFUSALS", "cases": rows, "refusals": refused,
             "existingAArch64WholeContainerIdentity": a64_identity,
             "compiler": report["generations"][-1]["native"], "nativeCompilerHost": "aarch64-macos",
             "linuxExecution": False, "performanceMeasured": False}
    (output / "suite.json").write_text(json.dumps(suite, indent=2) + "\n")
    print(suite["status"], len(rows), "programs", len(refused), "refusals", flush=True)


def execute(output, rosetta):
    suite = json.loads((output / "suite.json").read_text())
    host = platform.system(), platform.machine()
    if rosetta:
        assert host == ("Darwin", "arm64"), host
        loader = output / "x86_64-kexe-loader"
        subprocess.run(["clang", "-std=c11", "-O2", "-arch", "x86_64",
                        ROOT / "seed/bootstrap/adopted-loader-20261012.c", "-o", loader], check=True)
    else:
        assert host[0] == "Linux" and host[1] in ("x86_64", "AMD64"), host
    rows = []
    for case in suite["cases"]:
        elf, native = output / case["elf"], output / case["native"]
        assert pin(elf) == case["elfPin"] and pin(native) == case["nativePin"]
        env = {k: v for k, v in os.environ.items() if not k.startswith("KEXE_")}
        if rosetta:
            env.update(KEXE_FUEL=str(case["fuel"]), KEXE_STRUCTURED_REPORT="1",
                       KEXE_CPU_SECONDS="10", KEXE_WALL_SECONDS="10")
            args = ["/usr/bin/arch", "-x86_64", loader, native, str(case["offset"]), "0", "x86_64", "-"]
        else:
            elf.chmod(0o700)
            args = [elf]
        result = subprocess.run(list(map(str, args)), env=env, capture_output=True, timeout=15)
        suffix = "rosetta" if rosetta else "linux"
        (output / "raw" / (case["name"] + "." + suffix + ".stdout")).write_bytes(result.stdout)
        (output / "raw" / (case["name"] + "." + suffix + ".stderr")).write_bytes(result.stderr)
        if case["trap"]:
            if rosetta:
                assert result.returncode == 120 and case["trap"].encode() in result.stderr, (case["name"], result)
            else:
                assert result.returncode == -getattr(signal, case["trap"]), (case["name"], result)
                assert not result.stdout
        elif rosetta:
            match = re.search(rb":result (-?\d+)", result.stdout)
            assert result.returncode == 0 and match and int(match[1]) == case["result"], (case["name"], result)
        else:
            assert result.returncode == 0 and result.stdout == struct.pack("<q", case["result"]), (case["name"], result)
        if rosetta:
            fuel = re.search(rb":fuel \{:initial (\d+) :remaining (\d+)\}", result.stdout)
            assert fuel and int(fuel[1]) == case["fuel"] and 0 <= int(fuel[2]) <= case["fuel"]
            assert int(fuel[2]) == case["aarch64Reference"]["remainingFuel"], (case["name"], fuel[2])
            exact_charges = {"answer": 0, "loop": 100, "parallel-recur": 5}
            if case["name"] in exact_charges:
                assert int(fuel[2]) == case["fuel"] - exact_charges[case["name"]]
            if case["name"] == "fuel-exhausted":
                assert int(fuel[2]) == 0
        rows.append({"name": case["name"], "exit": result.returncode, "stdoutSHA256": hashlib.sha256(result.stdout).hexdigest()})
    record = {"status": "PASS_X86_64_GUEST_ROSETTA" if rosetta else "PASS_NATIVE_LINUX_X86_64_ELF_EXECUTION",
              "host": host, "linuxExecution": not rosetta, "rows": rows, "performanceMeasured": False}
    (output / ("rosetta-report.json" if rosetta else "linux-report.json")).write_text(json.dumps(record, indent=2) + "\n")
    print(record["status"], len(rows), "programs", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--selfbuild-output", type=Path)
    mode.add_argument("--execute-linux", action="store_true")
    mode.add_argument("--execute-rosetta", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.selfbuild_output:
        prepare(args.selfbuild_output.resolve(), args.output.resolve())
    else:
        execute(args.output.resolve(), args.execute_rosetta)
