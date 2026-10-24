#!/usr/bin/env python3
"""Stage fixed DAG-CBOR vectors, launch native processes, transport observations.

Run on native Linux arm64/x86_64. The Amu-built Kotoba gate, not Python,
owns the ordered acceptance verdict. No evaluator or compiler lives here.
"""
import argparse
import copy
import hashlib
import json
import os
import platform
import shutil
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE = "kototama.pure-i64-aot/v1"


def head(major, count):
    if count < 24:
        return bytes([(major << 5) | count])
    size = 1 if count < 256 else 2 if count < 65536 else 4
    return bytes([(major << 5) | {1: 24, 2: 25, 4: 26}[size]]) + count.to_bytes(size, "big")


def encode(value):
    """Only serialize literal test data; no execution semantics."""
    if value is None:
        return b"\xf6"
    if isinstance(value, int):
        return head(0, value)
    if isinstance(value, str):
        raw = value.encode("utf-8")
        return head(3, len(raw)) + raw
    if isinstance(value, list):
        return head(4, len(value)) + b"".join(map(encode, value))
    if isinstance(value, dict):
        pairs = sorted(((encode(k), encode(v)) for k, v in value.items()), key=lambda p: (len(p[0]), p[0]))
        return head(5, len(pairs)) + b"".join(k + v for k, v in pairs)
    raise TypeError(type(value))


def const(value):
    return ["const", ["integer", str(value)]]


def var(name):
    return ["var", name]


def arith(op, *values):
    return ["arith", op, list(values)]


def method(body, params=()):
    return {"params": list(params), "param-types": ["i64"] * len(params), "result": "i64", "effects": [], "body": body}


def program(body, extra=None):
    return ["kototama.vm/program", 1, {"entry": "run", "exports": ["run"], "value-profile": "kotoba.i64-wrap/v1",
                                       "methods": {"run": method(body), **(extra or {})}}]


def vectors():
    # All answers and exact fuel thresholds are fixed golden values, not
    # calculated with a host evaluator. Every success also gets a one-less
    # budget control (except cost1, since this CLI requires positive fuel).
    cases = []

    def good(name, body, fuel, result, extra=None):
        wire = encode(program(body, extra))
        cases.append(dict(name=name, wire=wire, fuel=fuel, result=result, outcome="ok"))
        if fuel > 1:
            cases.append(dict(name=name + "-fuel-short", wire=wire, fuel=fuel - 1, outcome="trap"))

    def trap(name, body, fuel=100, arithmetic=True):
        cases.append(dict(name=name, wire=encode(program(body)), fuel=fuel, outcome="arithmetic" if arithmetic else "trap"))

    def refuse(name, p):
        cases.append(dict(name=name, wire=p if isinstance(p, bytes) else encode(p), fuel=100, outcome="refuse"))

    good("const", const(42), 1, 42)
    good("min", const(-9223372036854775808), 1, -9223372036854775808)
    good("max", const(9223372036854775807), 1, 9223372036854775807)
    good("add", arith("add", const(20), const(22)), 3, 42)
    good("empty-add", arith("add"), 1, 0)
    good("empty-mul", arith("mul"), 1, 1)
    good("wrap-add", arith("add", const(9223372036854775807), const(1)), 3, -9223372036854775808)
    good("wrap-mul", arith("mul", const(9223372036854775807), const(2)), 3, -2)
    good("wrap-negate", arith("sub", const(-9223372036854775808)), 2, -9223372036854775808)
    good("nary-sub", arith("sub", const(100), const(30), const(28)), 4, 42)
    good("quot-negative", arith("quot", const(-85), const(2)), 3, -42)
    good("div-negative", arith("div", const(85), const(-2)), 3, -42)
    good("rem-negative", arith("mod", const(-85), const(2)), 3, -1)
    good("rem-min-minus-one", arith("mod", const(-9223372036854775808), const(-1)), 3, 0)
    good("if-selected", ["if", const(0), arith("div", const(1), const(0)), const(42)], 3, 42)
    good("if-nonzero", ["if", const(-1), const(42), const(0)], 3, 42)
    good("do", ["do", [const(7), const(42)]], 3, 42)
    good("let-sequential", ["let", [["x", const(20)], ["y", arith("add", var("x"), const(2))]], arith("add", var("x"), var("y"))], 8, 42)
    good("let-shadow", ["let", [["x", const(1)], ["x", const(42)]], var("x")], 4, 42)
    good("loop-outer-initializers", ["let", [["x", const(10)]], ["loop", [["x", const(1)], ["y", var("x")]], arith("add", var("x"), var("y"))]], 8, 11)
    loop = ["loop", [["n", const(3)], ["sum", const(0)]],
            ["if", ["compare", "=", [var("n"), const(0)]], var("sum"),
             ["recur", [arith("sub", var("n"), const(1)), arith("add", var("sum"), var("n"))]]]]
    good("loop-recur", loop, 41, 6)
    swap = ["loop", [["n", const(1)], ["x", const(20)], ["y", const(22)]],
            ["if", var("n"), ["recur", [const(0), var("y"), var("x")]], arith("sub", var("x"), var("y"))]]
    good("recur-parallel", swap, 15, 2)
    good("call", ["call", "plus", [const(40)]], 5, 42, {"plus": method(arith("add", var("n"), const(2)), ["n"])})
    good("five-params", ["call", "fifth", [const(0), const(0), const(0), const(0), const(42)]], 7, 42,
         {"fifth": method(var("e"), ["a", "b", "c", "d", "e"])})
    good("sixteen-operands", arith("add", *([const(1)] * 16)), 17, 16)
    good("thirty-two-methods", const(42), 1, 42, {f"f{i:02d}": method(const(0)) for i in range(31)})
    good("injection-names", ["call", "(typed-cap-call)", [const(42)]], 3, 42,
         {"(typed-cap-call)": method(var("a ] :i64"), ["a ] :i64"])})
    for op, result in [("=", 0), ("<", 1), (">", 0), ("<=", 1), (">=", 0)]:
        good("compare-" + op, ["compare", op, [const(1), const(2), const(3)]], 4, result)
    trap("div-zero", arith("div", const(1), const(0)))
    trap("div-overflow", arith("div", const(-9223372036854775808), const(-1)))
    trap("rem-zero", arith("mod", const(1), const(0)))
    trap("compare-eager", ["compare", "<", [const(2), const(1), arith("div", const(1), const(0))]])
    trap("infinite-loop", ["loop", [["x", const(0)]], ["recur", [var("x")]]], 32, arithmetic=False)
    good("empty-loop", ["loop", [], const(42)], 2, 42)
    good("nested-empty-loop", ["loop", [], ["loop", [], const(42)]], 3, 42)
    trap("infinite-empty-loop", ["loop", [], ["recur", []]], 32, arithmetic=False)
    base = program(const(42))
    for name, key, value in [("effects", "effects", [["fs/read"]]), ("bad-param-types", "param-types", ["i64"]),
                              ("unknown-method-field", "provider", "anything"), ("result", "result", "value")]:
        p = copy.deepcopy(base); p[2]["methods"]["run"][key] = value; refuse(name, p)
    for name, key, value in [("imports", "imports", []), ("unknown-field", "authority", "all"),
                              ("bad-profile", "value-profile", "kototama.data-i64/v1"),
                              ("private-entry", "exports", []), ("duplicate-exports", "exports", ["run", "run"]),
                              ("missing-entry", "entry", None)]:
        p = copy.deepcopy(base); p[2][key] = value; refuse(name, p)
    p = copy.deepcopy(base); p[1] = 2; refuse("version", p)
    p = program(["call", "run", []]); refuse("recursive-method", p)
    p = program(["call", "b", []], {"b": method(["call", "run", []])}); refuse("mutual-recursion", p)
    p = program(const(42), {"unused": method(const(0))}); p[2]["methods"]["unused"]["effects"] = [["fs/read"]]; refuse("unreachable-effects", p)
    p = program(const(42)); p[2]["methods"]["run"] = method(const(42), ["n"]); refuse("entry-arguments", p)
    refuse("six-params", program(const(42), {"unused": method(const(0), ["a", "b", "c", "d", "e", "f"])}))
    refuse("thirty-three-methods", program(const(42), {f"f{i:02d}": method(const(0)) for i in range(32)}))
    for name, body in [("effect-tag", ["effect", "invoke-capability", [const(35)]]),
                       ("unbound", var("missing")), ("unknown-call", ["call", "missing", []]),
                       ("wrong-arity", ["call", "run", [const(1)]]),
                       ("recur-outside", ["recur", []]), ("recur-nontail", ["loop", [], ["do", [["recur", []], const(0)]]]),
                       ("loop-duplicate", ["loop", [["x", const(1)], ["x", const(2)]], var("x")]),
                       ("nil-constant", ["const", None]), ("empty-do", ["do", []]),
                       ("sub-arity", arith("sub")), ("div-arity", arith("div", const(1))),
                       ("compare-arity", ["compare", "<", [const(1)]]),
                       ("too-many-operands", arith("add", *([const(1)] * 17)))]:
        refuse(name, program(body))
    for literal in ["+1", "01", "-0", "9223372036854775808", "-9223372036854775809", "1)"]:
        refuse("bad-integer-" + literal, program(["const", ["integer", literal]]))
    raw = encode(base)
    refuse("trailing", raw + b"\x00")
    refuse("truncated", raw[:-1])
    refuse("overlong-array", b"\x98\x03" + raw[1:])
    refuse("indefinite", b"\x9f" + raw[1:] + b"\xff")
    refuse("duplicate-map-key", b"\x83" + encode("kototama.vm/program") + b"\x01\xa2" + encode("entry") + encode("run") + encode("entry") + encode("run"))
    refuse("unordered-map", b"\x83" + encode("kototama.vm/program") + b"\x01\xa2" + encode("methods") + b"\xa0" + encode("entry") + encode("run"))
    refuse("invalid-utf8", raw.replace(b"run", b"r\xffn", 1))
    refuse("nonascii-name", program(const(42), {"非ASCII": method(const(1))}))
    refuse("too-many-bytes", raw + b"\x00" * 65536)
    refuse("too-many-nodes", b"\x99\x10\x00" + b"\x00" * 4096)
    refuse("too-deep", b"\x81" * 66 + b"\x00")
    for label, fuel in [("zero-fuel", 0), ("negative-fuel", -1), ("too-much-fuel", 9007199254740992)]:
        cases.append(dict(name=label, wire=raw, fuel=fuel, outcome="refuse"))
    cases.append(dict(name="unknown-profile", wire=raw, fuel=1, profile="unknown", outcome="refuse"))
    cases.append(dict(name="unsupported-target", wire=raw, fuel=1, target="wasm32-browser", outcome="refuse"))
    cases.append(dict(name="unknown-flag", wire=raw, fuel=1, extra=["--unknown"], outcome="refuse"))
    cases.append(dict(name="existing-output", wire=raw, fuel=1, existing=True, outcome="refuse"))
    return cases


def gate_source(expected):
    # Fixed verdict program: compares every observed field, in order. Input
    # is the raw native process observations; it cannot supply its own plan.
    words = struct.pack(">" + "q" * len(expected), *expected).hex()
    return '''(ns kototama-i64-gate (:export [main]))
(defn- kg-path [s :string] :vector-i64
  (loop [i 0 v (vector-alloc (string-length s))]
    (if (= i (string-length s)) v (recur (inc i) (vector-assoc! v i (string-code-point-at s i))))))
(defn- kg-word [v :vector-i64 p :i64] :i64
  (loop [i 0 n 0] (if (= i 8) n (recur (inc i) (bit-or n (i64-shift-left (vector-at v (+ p i)) (* i 8)))))))
(defn- kg-expected [s :string p :i64] :i64
  (loop [i 0 n 0] (if (= i 16) n (let [c (string-code-point-at s (+ p i))]
    (recur (inc i) (bit-or (i64-shift-left n 4) (if (<= c 57) (- c 48) (- c 87))))))))
(defn main [] :i64
  (let [path (typed-cap-call :cli/args :string :string "0")
        data (vector-i64-from-bytes (typed-cap-call :fs/app-data-bytes :bytes :bytes (bytes-from-vector-i64 (kg-path path))))
        expected "''' + words + '''"
        count (quot (string-length expected) 16)
        ok (and (= (vector-count data) (* 8 count))
             (loop [i 0] (if (= i count) true
               (and (= (kg-word data (* i 8)) (kg-expected expected (* i 16))) (recur (inc i))))))
        w (typed-cap-call :io/write :string :string (if ok "PASS_KOTOTAMA_I64_NATIVE_ORDERED\\n" "FAIL_KOTOTAMA_I64_NATIVE_ORDERED\\n"))]
    (if ok 0 1)))
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--compiler", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    machine = platform.machine()
    if platform.system() != "Linux" or machine not in ("aarch64", "arm64", "x86_64"):
        raise SystemExit("native Linux arm64/x86_64 required; no emulation")
    target = "aarch64-linux" if machine in ("aarch64", "arm64") else "x86_64-linux"
    signal = -5 if target == "aarch64-linux" else -4
    out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    compiler = out / "compiler.elf"; shutil.copy2(a.compiler, compiler); compiler.chmod(0o755)
    env = {"PATH": "/nonexistent", "KEXE_CAP_RESOURCES_35": str(out), "KEXE_STACK_BYTES": "8388608"}
    observations, expected, records = [], [], []
    for i, c in enumerate(vectors()):
        prefix = f"{i:03d}"
        src, dst = out / (prefix + ".cbor"), out / (prefix + ".elf")
        src.write_bytes(c["wire"])
        if c.get("existing"):
            dst.write_bytes(struct.pack("<q", 42))
        p = subprocess.run([str(compiler), "compile-kototama", str(src), "--target", c.get("target", target), "--output", str(dst),
                            "--fuel", str(c["fuel"]), "--profile", c.get("profile", PROFILE), *c.get("extra", [])], env=env, capture_output=True, timeout=120)
        (out / (prefix + "-compile.stdout")).write_bytes(p.stdout)
        (out / (prefix + "-compile.stderr")).write_bytes(p.stderr)
        code, data = -999, b""
        if p.returncode == 0 and dst.exists():
            dst.chmod(0o755)
            r = subprocess.run([str(dst)], env={"PATH": "/nonexistent"}, capture_output=True, timeout=10)
            code, data = r.returncode, r.stdout
            (out / (prefix + "-guest.stderr")).write_bytes(r.stderr)
        exists = int(dst.exists())
        value = struct.unpack("<q", data)[0] if len(data) == 8 else 0
        saved = dst.read_bytes() if c.get("existing") and dst.exists() else b""
        observations.extend([i, p.returncode, code, len(data), value, exists,
                             len(saved), struct.unpack("<q", saved[:8])[0] if len(saved) >= 8 else 0])
        outcome = c["outcome"]
        expected.extend([i, 1 if outcome == "refuse" else 0,
                         -999 if outcome == "refuse" else -8 if outcome == "arithmetic" and target == "x86_64-linux" else signal if outcome in ("trap", "arithmetic") else 0,
                         8 if outcome == "ok" else 0, c.get("result", 0), 1 if c.get("existing") else 0 if outcome == "refuse" else 1,
                         8 if c.get("existing") else 0, 42 if c.get("existing") else 0])
        records.append(dict(index=i, name=c["name"], outcome=outcome, fuel=c["fuel"],
                            inputSHA256=hashlib.sha256(c["wire"]).hexdigest(),
                            compileExit=p.returncode, guestExit=code, outputBytes=len(data), result=value))
        print(prefix, c["name"], p.returncode, code, len(data), value, flush=True)
    raw = struct.pack("<" + "q" * len(observations), *observations)
    (out / "observations.bin").write_bytes(raw)
    (out / "gate.kotoba").write_text(gate_source(expected))
    gate = out / "gate.elf"
    p = subprocess.run([str(compiler), "compile", str(out / "gate.kotoba"), "--target", target,
                        "--output", str(gate), "--format", "static"], env=env, capture_output=True, timeout=180)
    (out / "gate-compile.stdout").write_bytes(p.stdout); (out / "gate-compile.stderr").write_bytes(p.stderr)
    if p.returncode or not gate.exists():
        raise SystemExit("native gate build failed: " + p.stderr.decode(errors="replace"))
    gate.chmod(0o755)
    verdict = subprocess.run([str(gate), str(out / "observations.bin")], env=env, capture_output=True, timeout=30)
    (out / "gate.stdout").write_bytes(verdict.stdout); (out / "gate.stderr").write_bytes(verdict.stderr)
    bad = bytearray(raw); bad[0] ^= 1; (out / "corrupt-observations.bin").write_bytes(bad)
    control = subprocess.run([str(gate), str(out / "corrupt-observations.bin")], env=env, capture_output=True, timeout=30)
    report = dict(schema="amu.kototama-i64-native-gate.v1", profile=PROFILE, target=target, machine=machine,
                  compilerSHA256=hashlib.sha256(compiler.read_bytes()).hexdigest(),
                  gateSHA256=hashlib.sha256(gate.read_bytes()).hexdigest(), cases=records,
                  verdictExit=verdict.returncode, corruptControlExit=control.returncode,
                  status="PASS" if verdict.returncode == 0 and control.returncode == 1 else "FAIL",
                  performanceMeasured=False, fullVMQualified=False)
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(verdict.stdout.decode(), report["status"], flush=True)
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
