#!/usr/bin/env python3
"""Native source compiler: AArch64 bridge -> x86 G1 -> Linux x86 G2/G3."""
import argparse
import hashlib
import importlib.util
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "seed/X86_64-LINUX-SELFHOST-MANIFEST"
LOADER = "seed/bootstrap/adopted-loader-20261012.c"


def pin(p):
    data = p.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def dump(p, obj):
    p.write_text(json.dumps(obj, indent=2) + "\n")


def environment(out, command=True):
    env = {k: v for k, v in os.environ.items() if not k.startswith("KEXE_")}
    env.update(KEXE_FUEL="off", KEXE_VECTORS="4194304", KEXE_VECTOR_ITEMS="134217728",
               KEXE_STRING_POOL="268435456", KEXE_PAIRS="16777216",
               KEXE_CPU_SECONDS="1800", KEXE_WALL_SECONDS="1800", TMPDIR=str(out))
    if command:
        env.update(KEXE_COMMAND="1", KEXE_CAP_RESOURCES_35=str(out))
    else:
        env.update(KEXE_STRUCTURED_REPORT="1", KEXE_FUEL="1000000")
    return env


class Runs:
    def __init__(self, out, source_pins):
        self.out, self.source_pins, self.calls = out, source_pins, []
        (out / "raw").mkdir(exist_ok=True)

    def run(self, name, args, watched=(), env=None, success=True):
        before = {str(p): pin(p) for p in watched}
        assert all(pin(ROOT / p) == v for p, v in self.source_pins.items()), "repository input drift"
        result = subprocess.run(list(map(str, args)), cwd=self.out, env=env or environment(self.out),
                                capture_output=True, timeout=1800)
        (self.out / "raw" / (name + ".stdout")).write_bytes(result.stdout)
        (self.out / "raw" / (name + ".stderr")).write_bytes(result.stderr)
        after = {str(p): pin(p) if p.is_file() else None for p in watched}
        self.calls.append(dict(name=name, argv=list(map(str, args)), exit=result.returncode,
                               before=before, after=after))
        dump(self.out / "calls.json", self.calls)
        assert before == after, "active source/producer/loader mutation"
        assert all(pin(ROOT / p) == v for p, v in self.source_pins.items()), "repository input drift"
        if success:
            assert result.returncode == 0 and not result.stderr, (name, result.returncode, result.stderr.decode(errors="replace"))
        return result


def extract_kseed(src, dst):
    header, payload = src.read_bytes().split(b"\n\n", 1)
    lines = header.splitlines()
    assert len(lines) == 2 and lines[0].split()[:1] == [b"KSEED1"]
    assert lines[0].split()[2] == b"1" and re.fullmatch(rb"main [0-9]+ 0", lines[1])
    assert len(payload) == int(lines[0].split()[1])
    dst.write_bytes(payload)
    return int(lines[1].split()[1])


def extract_kx64(src, dst):
    header, payload = src.read_bytes().split(b"\n\n", 1)
    match = re.fullmatch(rb"KX64V1 x86_64-linux sysv-ctx-v11 ([0-9]+) 0", header)
    assert match and 0 < len(payload) == int(match[1]) < 4194304, "invalid x86 runtime container"
    assert payload[0] == 0xE9, "missing bounded entry trampoline"
    dst.write_bytes(payload)


def command(prefix, source, output):
    return [*prefix, "compile", source, "--target", "x86_64-linux", "--output", output, "--format", "kx64-v1"]


def cases():
    rows = []
    def add(name, expression, result=None, helpers="", trap=False):
        rows.append(dict(name=name, source=f"(ns runtime-{name} (:export [main]))\n{helpers}\n(defn main [] :i64 {expression})\n",
                         result=result, trap=trap))
    add("string-literal", '(string-length "hello")', 5)
    add("string-concat", '(if (string=? (string-concat "ab" "cd") "abcd") 42 -1)', 42)
    add("string-view", '(string-code-point-at (string-substring (string-concat "xx" "abcd") 2 6) 1)', 98)
    add("string-unicode", '(+ (string-length "日é") (string-code-point-at "日é" 3))', 238)
    add("string-empty-nul", '(if (string=? (string-concat "" "a\\u0000b") "a\\u0000b") 42 -1)', 42)
    add("string-search", '(+ (string-index-of (string-concat "ab" "cd") "bc") (string-compare "a" "b"))', 0)
    add("string-call", '(string-length (decorate "hello"))', 7,
        '(defn- decorate [s :string] :string (string-concat "[" (string-concat s "]")))')
    add("vector-literal", '(vector-at [11 22 33] 1)', 22)
    add("vector-dynamic", '(let [x 7 v [x (+ x 1)]] (+ (vector-at v 0) (vector-at v 1)))', 15)
    add("vector-persistent", '(let [v [10 20] w (vector-assoc v 0 30)] (+ (vector-at v 0) (vector-at w 0)))', 40)
    add("vector-mutate", '(let [v (vector-alloc 5) w (vector-assoc! v 3 42)] (vector-at w 3))', 42)
    add("vector-drop-conj", '(let [v (vector-conj [1 2] 9) w (vector-drop v 1)] (+ (vector-count w) (vector-at w 1)))', 11)
    add("vector-pooled", '(vector-count [' + ' '.join(map(str, range(80))) + '])', 80)
    # Keep the index dynamic: the A64 leaf fuel cache does not publish its
    # pending charge when a statically negative TAB traps before RET. The
    # preserved qual-v7 failure records that older-reference accounting gap.
    add("vector-negative", '(vector-at [10 20] (negative))', helpers='(defn- negative [] :i64 -1)', trap=True)
    add("vector-oob", '(let [v [10 20]] (vector-at v 2))', trap=True)
    add("string-oob", '(string-length (string-substring "hello" 0 10))', trap=True)
    add("string-boundary", '(string-length (string-substring "日é" 1 3))', trap=True)
    add("wide-args", '(wide 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16)', 136,
        '(defn- wide [' + ' '.join(f'p{i} :i64' for i in range(16)) + '] :i64 (+ ' + ' '.join(f'p{i}' for i in range(16)) + '))')
    add("closure", '(let [k 9 f (fn [x] (+ x k))] (invoke f 33))', 42)
    add("closure-env", '(let [a 10 b 20 f (fn [x] (+ x a b))] (invoke f 12))', 42)
    add("state-results", '(handle (do (perform :state/put 42) (perform :state/get)) (with tally 0))', 42,
        '(defhandler tally [:state :i64] (get [s] (resume s s)) (put [s v] (resume v v)))')
    add("bytes-roundtrip", '(string-code-point-at (string-from-utf8 (bytes-from-vector-i64 [65 66])) 1)', 66)
    add("capability-denied", '(let [x (typed-cap-call :io/write :string :string "denied")] 42)', trap=True)
    return rows


def prepare(out):
    assert (platform.system(), platform.machine()) == ("Darwin", "arm64")
    out.mkdir(parents=True, exist_ok=False)
    paths = [p for p in (ROOT / MANIFEST).read_text().splitlines() if p and not p.startswith("#")]
    source_pins = {p: pin(ROOT / p) for p in [MANIFEST, LOADER, *paths]}
    spec = importlib.util.spec_from_file_location("adopted", ROOT / "scripts/seed/build-adopted.py")
    adopted = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adopted)
    receipt, _, producer, loader_source = adopted.inputs(ROOT / "seed/adoption-20261012.json")
    source_pins[str(producer.relative_to(ROOT))] = pin(producer)
    run = Runs(out, source_pins)
    source = out / "seed-unity.kotoba"
    source.write_bytes(b"".join((ROOT / p).read_bytes() + b"\n" for p in paths))
    loader = out / "a64-loader"
    run.run("loader-build", ["clang", "-std=c11", "-O2", loader_source, "-o", loader])
    a64 = [loader, producer, 0, 0, "aarch64", "35,37,38,39", "--"]
    run.run("bridge-build", [*a64, "compile", source, "--target", "aarch64-macos", "--output", out / "bridge.kseed"], [source, producer, loader])
    bridge = out / "bridge.bin"
    assert extract_kseed(out / "bridge.kseed", bridge) == 0
    prefix = [loader, bridge, 0, 0, "aarch64", "35,37,38,39", "--"]
    run.run("x86-G1-build", command(prefix, source, out / "G1.kx64"), [source, bridge, loader])
    extract_kx64(out / "G1.kx64", out / "G1.bin")
    rows = cases()
    for row in rows:
        name = row["name"]
        src = out / (name + ".kotoba")
        src.write_text(row["source"])
        run.run(name + "-cross", command(prefix, src, out / (name + ".kx64")), [src, bridge, loader])
        extract_kx64(out / (name + ".kx64"), out / (name + ".bin"))
        run.run(name + "-reference-compile", [*a64, "compile", src, "--target", "aarch64-macos", "--output", out / (name + ".a64.kseed")], [src, producer, loader])
        offset = extract_kseed(out / (name + ".a64.kseed"), out / (name + ".a64.bin"))
        result = run.run(name + "-reference-execute", [loader, out / (name + ".a64.bin"), offset, 0, "aarch64", "-"],
                         [loader, out / (name + ".a64.bin")], environment(out, False), success=False)
        row["reference"] = inspect(result, row)
        row["nativePin"] = pin(out / (name + ".bin"))
        row["containerPin"] = pin(out / (name + ".kx64"))
    report = dict(status="PASS_NATIVE_X86_RUNTIME_PREPARE", sourcePins=source_pins, sourceUnity=pin(source),
                  compiler=pin(out / "G1.bin"), container=pin(out / "G1.kx64"), bridge=pin(bridge), cases=rows,
                  trustedCLoader=True, JVMNodeOrGraalFallback=False, linuxSelfhost=False, performanceMeasured=False)
    dump(out / "prepare.json", report)
    print(report["status"], report["compiler"], flush=True)


def inspect(result, case):
    fuel = re.search(rb":fuel \{:initial ([0-9]+) :remaining ([0-9]+)\}", result.stdout)
    assert fuel and int(fuel[1]) == 1000000, (case["name"], result.stdout, result.stderr)
    if case["trap"]:
        assert result.returncode == 120 and b":status :trap" in result.stdout, (case["name"], result)
    else:
        value = re.search(rb":result (-?[0-9]+)", result.stdout)
        assert result.returncode == 0 and value and int(value[1]) == case["result"], (case["name"], result)
    return dict(exit=result.returncode, remainingFuel=int(fuel[2]))


def execute(out, rosetta):
    host = platform.system(), platform.machine()
    assert host == ("Darwin", "arm64") if rosetta else host[0] == "Linux" and host[1] in ("x86_64", "AMD64")
    prepared = json.loads((out / "prepare.json").read_text())
    assert pin(out / "seed-unity.kotoba") == prepared["sourceUnity"]
    paths = [p for p in (ROOT / MANIFEST).read_text().splitlines() if p and not p.startswith("#")]
    assert (out / "seed-unity.kotoba").read_bytes() == b"".join((ROOT / p).read_bytes() + b"\n" for p in paths)
    assert pin(out / "G1.bin") == prepared["compiler"] and pin(out / "G1.kx64") == prepared["container"]
    run = Runs(out, prepared["sourcePins"])
    loader = out / ("rosetta-loader" if rosetta else "linux-loader")
    run.run("x86-loader-build", ["clang", "-std=c11", "-O2", *(["-arch", "x86_64"] if rosetta else []), ROOT / LOADER, "-o", loader])
    arch = ["/usr/bin/arch", "-x86_64"] if rosetta else []
    producer, source = out / "G1.bin", out / "seed-unity.kotoba"
    generations = [dict(native=prepared["compiler"], container=prepared["container"])]
    for generation in (2, 3):
        prefix = [*arch, loader, producer, 0, 0, "x86_64", "35,37,38,39", "--"]
        container = out / f"G{generation}.kx64"
        native = out / f"G{generation}.bin"
        run.run(f"x86-G{generation}-build", command(prefix, source, container), [source, producer, loader])
        extract_kx64(container, native)
        assert pin(native) == prepared["compiler"] and pin(container) == prepared["container"], "x86 selfhost fixed point mismatch"
        generations.append(dict(native=pin(native), container=pin(container)))
        producer = native
    prefix = [*arch, loader, producer, 0, 0, "x86_64", "35,37,38,39", "--"]
    results = []
    for case in prepared["cases"]:
        name = case["name"]
        src, container, native = out / (name + ".kotoba"), out / (name + ".rebuilt.kx64"), out / (name + ".rebuilt.bin")
        assert src.read_text() == case["source"] and pin(out / (name + ".kx64")) == case["containerPin"]
        run.run(name + "-native-compile", command(prefix, src, container), [src, producer, loader])
        extract_kx64(container, native)
        assert pin(container) == case["containerPin"] and pin(native) == case["nativePin"], "host-dependent compiler output"
        result = run.run(name + "-x86-execute", [*arch, loader, native, 0, 0, "x86_64", "-"], [native, loader], environment(out, False), success=False)
        observed = inspect(result, case)
        assert observed == case["reference"], (name, observed, case["reference"])
        results.append(dict(name=name, **observed))
    refused = []
    for name, text, flags in [
        ("float", '(ns refused (:export [main])) (defn main [] :i64 (f64-to-i64-truncating (f64-add 1.0 2.0)))', ["--format", "kx64-v1"]),
        ("unused-float", '(ns refused (:export [main])) (defn- unused [x :f64] :f64 x) (defn main [] :i64 42)', ["--format", "kx64-v1"]),
        ("policy", '(ns refused (:export [main])) (defn main [] :i64 42)', ["--policy", "unknown"]),
        ("source-path", '(ns refused (:export [main])) (defn main [] :i64 42)', ["--source-path", "unknown"]),
        ("unknown-format", '(ns refused (:export [main])) (defn main [] :i64 42)', ["--format", "unknown"]),
        ("existing-output", '(ns refused (:export [main])) (defn main [] :i64 42)', ["--format", "kx64-v1"]),
    ]:
        src, dst = out / ("refuse-" + name + ".kotoba"), out / ("refuse-" + name + ".out")
        src.write_text(text)
        if name == "existing-output":
            dst.write_bytes(b"preserve original")
        result = run.run("refuse-" + name, [*prefix, "compile", src, "--target", "x86_64-linux", "--output", dst, *flags],
                         [src, producer, loader], success=False)
        assert result.returncode != 0 and b"E" in result.stderr
        assert dst.read_bytes() == b"preserve original" if name == "existing-output" else not dst.exists()
        refused.append(name)
    report = dict(status="PASS_ROSETTA_X86_SELF_REBUILD" if rosetta else "PASS_LINUX_X86_NATIVE_SELFHOST",
                  host=list(host), linuxSelfhost=not rosetta, generations=generations, sourceUnity=prepared["sourceUnity"],
                  cases=results, refusals=refused, trustedCLoader=True, JVMNodeOrGraalFallback=False, performanceMeasured=False)
    dump(out / ("rosetta-selfhost.json" if rosetta else "linux-selfhost.json"), report)
    print(report["status"], len(results), "cases; G1=G2=G3", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--execute-linux", action="store_true")
    group.add_argument("--execute-rosetta", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        prepare(args.output.resolve())
    else:
        execute(args.output.resolve(), args.execute_rosetta)
