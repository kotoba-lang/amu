#!/usr/bin/env python3
"""Stage literal conformance vectors and observations for the native receipt gate.

No host evaluator. The Amu-built Kotoba ordered gate owns every verdict.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import platform
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("i64_vectors", Path(__file__).with_name("check-kototama-i64.py"))
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
PROFILE = "kototama.pure-i64-receipt/v2"
MAGIC = 0x003252343649544b
STACK = -9000000000000000


def tree(expressions):
    while len(expressions) > 1:
        expressions = [["do", expressions[i:i + 16]] for i in range(0, len(expressions), 16)]
    return expressions[0]


def vectors():
    cases = []

    def add(name, body, budget, status, spent, result=0, extra=None):
        cases.append(dict(name=name, wire=v.encode(v.program(body, extra)), fuel=budget,
                          status=status, spent=spent, result=result))

    # Preserve the full v1 positive/refusal corpus under the explicit v2 ABI.
    arithmetic = {"div-zero": (2, 3), "div-overflow": (3, 3), "rem-zero": (2, 3), "compare-eager": (2, 6)}
    for old in v.vectors():
        c = copy.deepcopy(old)
        outcome = c.pop("outcome")
        c["refuse"] = outcome == "refuse"
        if c["name"] == "zero-fuel":
            c.update(refuse=False, status=1, spent=1)
        elif c["name"] in arithmetic:
            c["status"], c["spent"] = arithmetic[c["name"]]
        elif outcome == "trap":
            c.update(status=1, spent=c["fuel"] + 1)
        elif not c["refuse"]:
            c.update(status=0, spent=c["fuel"])
            # Fixed cost, independent of the varied invocation budget.
            for label, budget in [("zero", 0), ("above", c["fuel"] + 1)]:
                d = copy.deepcopy(c); d["name"] += "-budget-" + label; d["fuel"] = budget
                if budget == 0:
                    d.update(status=1, spent=1, result=0)
                cases.append(d)
        cases.append(c)
    add("max-budget", v.const(42), 9007199254740991, 0, 1, 42)
    add("environment-cannot-refuel-or-grant", v.const(42), 0, 1, 1)
    cases[-1]["guestEnv"] = {"KEXE_FUEL": "9007199254740991", "KEXE_ALLOW": "all", "KEXE_UNMETERED": "1"}
    for op, status in [("div", 2), ("quot", 2), ("mod", 2)]:
        for budget in range(5):
            add(op + "-zero-budget-" + str(budget), v.arith(op, v.const(1), v.const(0)), budget,
                1 if budget < 3 else status, budget + 1 if budget < 3 else 3)
    for op in ["div", "quot"]:
        for budget in range(5):
            add(op + "-overflow-budget-" + str(budget), v.arith(op, v.const(-9223372036854775808), v.const(-1)), budget,
                1 if budget < 3 else 3, budget + 1 if budget < 3 else 3)
    for budget in range(8):
        body = ["compare", "<", [v.const(2), v.const(1), v.arith("div", v.const(1), v.const(0))]]
        add("eager-failure-budget-" + str(budget), body, budget, 1 if budget < 6 else 2,
            budget + 1 if budget < 6 else 6)
    add("first-failure-stops-do", ["do", [v.arith("div", v.const(1), v.const(0)),
         ["loop", [], ["recur", []]]]], 100, 2, 4)
    chain = {f"f{i:02d}": v.method(v.const(42) if i == 30 else ["call", f"f{i + 1:02d}", []]) for i in range(31)}
    for budget in [0, 31, 32, 33]:
        add("tail-chain32-budget-" + str(budget), ["call", "f00", []], budget,
            1 if budget < 32 else 0, budget + 1 if budget < 32 else 32, 0 if budget < 32 else 42, chain)
    chain = {f"f{i:02d}": v.method(v.const(42) if i == 30 else v.arith("add", v.const(0), ["call", f"f{i + 1:02d}", []])) for i in range(31)}
    for budget in [93, 94, 95]:
        add("non-tail-chain32-budget-" + str(budget), v.arith("add", v.const(0), ["call", "f00", []]), budget,
            1 if budget < 94 else 0, budget + 1 if budget < 94 else 94, 0 if budget < 94 else 42, chain)
    # Structural boundaries: construction counts/encodes data, never evaluates it.
    for depth in [29, 30]:
        body = v.const(42)
        for _ in range(depth):
            body = ["do", [body]]
        add("decoder-depth-" + str(6 + 2 * depth), body, 0, 1, 1)
        cases[-1]["refuse"] = depth == 30
    for count in [64, 65]:
        body = v.const(42)
        remaining = count
        while remaining:
            n = min(16, remaining); remaining -= n
            body = ["let", [["x", v.const(0)] for _ in range(n)], body]
        add("lexical-bindings-" + str(count), body, 0, 1, 1)
        cases[-1]["refuse"] = count == 65
    for k in [1, 2]:
        body = tree([v.const(0)] * k + [v.arith("add")] * (968 - k))
        add("decoder-nodes-" + str(4094 + k), body, 0, 1, 1)
        cases[-1]["refuse"] = k == 2
    for size, short in [(65535, 59), (65536, 58), (65537, 57)]:
        a, b = "a" * 63, "b" * 64
        body = ["let", [[a, v.const(0)], [b, v.const(0)]], tree([v.var(a)] * short + [v.var(b)] * (915 - short))]
        add("input-bytes-" + str(size), body, 0, 1, 1)
        assert len(cases[-1]["wire"]) == size
        cases[-1]["refuse"] = size > 65536
    for size in [64, 65]:
        name = "x" * size
        add("binding-name-" + str(size), ["let", [[name, v.const(42)]], v.var(name)], 0, 1, 1)
        cases[-1]["refuse"] = size == 65
    for raw in ["-0", "00", "+1", "1x", "9007199254740992"]:
        add("invalid-budget-" + raw, v.const(42), raw, 0, 0)
        cases[-1]["refuse"] = True
    return cases


def gate_source(expected):
    source = v.gate_source(expected).replace("kototama-i64-gate", "kototama-receipt-gate").replace("KOTOTAMA_I64", "KOTOTAMA_RECEIPT")
    return source.replace(
        "(= (kg-word data (* i 8)) (kg-expected expected (* i 16)))",
        "(let [actual (kg-word data (* i 8)) want (kg-expected expected (* i 16))] "
        "(if (= want -9000000000000000) (and (>= actual 64) (<= actual 262144) (= (bit-and actual 15) 0)) (= actual want)))")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "arm64", "x86_64"), "native kernel required"
    target = "x86_64-linux" if platform.machine() == "x86_64" else "aarch64-linux"
    out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    compiler = out / "compiler.elf"; shutil.copy2(a.compiler, compiler); compiler.chmod(0o755)
    env = {"PATH": "/nonexistent", "KEXE_CAP_RESOURCES_35": str(out), "KEXE_STACK_BYTES": "8388608"}
    observations, expected, records = [], [], []
    zero_case = None
    for i, c in enumerate(vectors()):
        src, dst = out / f"{i:03d}.cbor", out / f"{i:03d}.elf"
        src.write_bytes(c["wire"])
        if c.get("existing"):
            dst.write_bytes(struct.pack("<q", 42))
        r = subprocess.run([str(compiler), "compile-kototama", str(src), "--target", c.get("target", target), "--output", str(dst),
                            "--fuel", str(c["fuel"]), "--profile", c.get("profile", PROFILE), *c.get("extra", [])],
                           env=env, capture_output=True, timeout=120)
        (out / f"{i:03d}-compile.stdout").write_bytes(r.stdout); (out / f"{i:03d}-compile.stderr").write_bytes(r.stderr)
        code, data, err = -999, b"", b""
        if r.returncode == 0 and dst.exists():
            dst.chmod(0o755)
            guest = subprocess.run([str(dst)], env={"PATH": "/nonexistent", **c.get("guestEnv", {})}, capture_output=True, timeout=10)
            code, data, err = guest.returncode, guest.stdout, guest.stderr
        (out / f"{i:03d}-guest.stdout").write_bytes(data); (out / f"{i:03d}-guest.stderr").write_bytes(err)
        words = list(struct.unpack("<8q", data)) if len(data) == 64 else [0] * 8
        saved = dst.read_bytes() if c.get("existing") and dst.exists() else b""
        observations.extend([i, r.returncode, code, len(data), *words, len(err), int(dst.exists()),
                             len(saved), struct.unpack("<q", saved)[0] if len(saved) == 8 else 0])
        refuse = c.get("refuse", False)
        status = c.get("status", 0)
        planned = [0] * 8 if refuse else [MAGIC, status, c.get("result", 0), int(c["fuel"]), c["spent"],
                                                   int(c["fuel"]) - c["spent"], 0, STACK]
        expected.extend([i, 1 if refuse else 0, -999 if refuse else 70 if status else 0, 0 if refuse else 64,
                         *planned, 0, 1 if c.get("existing") else 0 if refuse else 1,
                         8 if c.get("existing") else 0, 42 if c.get("existing") else 0])
        records.append(dict(index=i, name=c["name"], inputSHA256=hashlib.sha256(c["wire"]).hexdigest(),
                            budget=c["fuel"], expected=planned, compileExit=r.returncode, guestExit=code, receipt=words, outputBytes=len(data)))
        if c["name"] == "const-budget-zero":
            zero_case = (i, dst)
        print(i, c["name"], r.returncode, code, words[1:6], flush=True)
    # Fixed envelope I/O failure is also raw process evidence consumed by the
    # same native gate, never an observation substituted into program source.
    with open("/dev/full", "wb") as full:
        io = subprocess.run([str(zero_case[1])], env={"PATH": "/nonexistent"}, stdout=full, stderr=subprocess.PIPE, timeout=10)
    observations.extend([len(records), 0, io.returncode, *([0] * 13)])
    expected.extend([len(records), 0, 74, *([0] * 13)])
    raw = struct.pack("<" + "q" * len(observations), *observations)
    (out / "observations.bin").write_bytes(raw); (out / "gate.kotoba").write_text(gate_source(expected))
    gate = out / "gate.elf"
    r = subprocess.run([str(compiler), "compile", str(out / "gate.kotoba"), "--target", target,
                        "--output", str(gate), "--format", "static"], env=env, capture_output=True, timeout=180)
    (out / "gate-compile.stdout").write_bytes(r.stdout); (out / "gate-compile.stderr").write_bytes(r.stderr)
    assert r.returncode == 0, r.stderr[-1000:]
    gate.chmod(0o755)

    def verdict(name, data):
        path = out / (name + ".bin"); path.write_bytes(data)
        r = subprocess.run([str(gate), str(path)], env=env, capture_output=True, timeout=30)
        (out / (name + ".stdout")).write_bytes(r.stdout); (out / (name + ".stderr")).write_bytes(r.stderr)
        return r.returncode

    positive = verdict("gate", raw)
    corrupt = bytearray(raw); corrupt[0] ^= 1
    corrupt_code = verdict("corrupt-control", corrupt)
    # Mutate the actual charge instructions in one generated negative-control
    # image. The guest now bypasses metering; the original native plan must fail.
    index, image = zero_case
    mutated = bytearray(image.read_bytes())
    needle = bytes.fromhex("498b410848ffc849894108") if target == "x86_64-linux" else struct.pack("<III", 0xF94004F0, 0xF1000610, 0xF90004F0)
    matches = 0
    at = mutated.find(needle)
    while at >= 0:
        if target == "x86_64-linux":
            mutated[at + 4:at + 7] = b"\x90\x90\x90"
        else:
            struct.pack_into("<I", mutated, at + 4, 0xF1000210)
        matches += 1; at = mutated.find(needle, at + len(needle))
    assert matches > 0
    mutant = out / "metering-removed.elf"; mutant.write_bytes(mutated); mutant.chmod(0o755)
    r = subprocess.run([str(mutant)], env={"PATH": "/nonexistent"}, capture_output=True, timeout=10)
    changed = observations.copy(); pos = index * 16
    changed[pos + 2:pos + 12] = [r.returncode, len(r.stdout), *(struct.unpack("<8q", r.stdout) if len(r.stdout) == 64 else [0] * 8)]
    meter_code = verdict("metering-removal-control", struct.pack("<" + "q" * len(changed), *changed))
    report = dict(schema="amu.kototama-receipt-native-gate.v2", profile=PROFILE, target=target,
                  compilerSHA256=hashlib.sha256(compiler.read_bytes()).hexdigest(), gateSHA256=hashlib.sha256(gate.read_bytes()).hexdigest(),
                  cases=records, verdictExit=positive, corruptControlExit=corrupt_code, meteringRemovalControlExit=meter_code,
                  mutatedChargeSites=matches, transportFailureExit=io.returncode,
                  status="PASS" if (positive, corrupt_code, meter_code) == (0, 1, 1) else "FAIL",
                  fullVMQualified=False, hostedOracleExecuted=False, performanceMeasured=False)
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], len(records), positive, corrupt_code, meter_code, flush=True)
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
