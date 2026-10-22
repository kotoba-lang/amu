#!/usr/bin/env python3
"""Loaderless x86_64-linux-static compiler: bootstrap S1, then S1 -> S2 -> S3 on Linux.

--prepare (macOS arm64) is the one recorded bootstrap step: the pinned
AArch64 loader runs the bridge compiler to emit S1 and the reference
artifacts. --execute-linux (Linux x86_64) runs only the static images: no C
loader, no interpreter, no host compiler. Python only orchestrates and hashes.
"""
import argparse
import importlib.util
import json
import platform
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("selfhost", ROOT / "scripts/seed/check-x86_64-selfhost.py")
selfhost = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selfhost)
pin, dump, Runs, MANIFEST = selfhost.pin, selfhost.dump, selfhost.Runs, selfhost.MANIFEST
RUNTIME = ("seed/75-x86_64-static.kotoba", "seed/76-x86_64-static-rt.kotoba")


def compile_args(prefix, source, output, fmt):
    return [*prefix, "compile", source, "--target", "x86_64-linux", "--output", output, "--format", fmt]


def static_env(out, report=False):
    """The static image reads only these variables; everything else is dropped."""
    env = {"PATH": "/usr/bin:/bin"}
    if report:
        env.update(KEXE_STRUCTURED_REPORT="1", KEXE_FUEL="1000000", KEXE_ALLOW="-")
    else:
        env.update(KEXE_CAP_RESOURCES_35=str(out))
    return env


def prepare(out):
    assert (platform.system(), platform.machine()) == ("Darwin", "arm64")
    out.mkdir(parents=True, exist_ok=False)
    paths = [p for p in (ROOT / MANIFEST).read_text().splitlines() if p and not p.startswith("#")]
    assert all(p in paths for p in RUNTIME)
    source_pins = {p: pin(ROOT / p) for p in [MANIFEST, selfhost.LOADER, *paths]}
    spec = importlib.util.spec_from_file_location("adopted", ROOT / "scripts/seed/build-adopted.py")
    adopted = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adopted)
    _, _, producer, loader_source = adopted.inputs(ROOT / "seed/adoption-20261017.json")
    source_pins[str(producer.relative_to(ROOT))] = pin(producer)
    run = Runs(out, source_pins)
    source = out / "seed-unity.kotoba"
    source.write_bytes(b"".join((ROOT / p).read_bytes() + b"\n" for p in paths))
    loader = out / "a64-loader"
    run.run("loader-build", ["clang", "-std=c11", "-O2", loader_source, "-o", loader])
    a64 = [loader, producer, 0, 0, "aarch64", "35,37,38,39", "--"]
    run.run("bridge-build", [*a64, "compile", source, "--target", "aarch64-macos", "--output", out / "bridge.kseed"], [source, producer, loader])
    bridge = out / "bridge.bin"
    assert selfhost.extract_kseed(out / "bridge.kseed", bridge) == 0
    prefix = [loader, bridge, 0, 0, "aarch64", "35,37,38,39", "--"]
    # Bootstrap: the only C-loader run that produces a static artifact.
    run.run("S1-bootstrap", compile_args(prefix, source, out / "S1.elf", "static"), [source, bridge, loader])
    run.run("G1-kx64-reference", compile_args(prefix, source, out / "G1.kx64", "kx64-v1"), [source, bridge, loader])
    rows = selfhost.cases()
    for row in rows:
        name = row["name"]
        src = out / (name + ".kotoba")
        src.write_text(row["source"])
        run.run(name + "-static", compile_args(prefix, src, out / (name + ".elf"), "static"), [src, bridge, loader])
        run.run(name + "-reference-compile", [*a64, "compile", src, "--target", "aarch64-macos", "--output", out / (name + ".a64.kseed")], [src, producer, loader])
        offset = selfhost.extract_kseed(out / (name + ".a64.kseed"), out / (name + ".a64.bin"))
        result = run.run(name + "-reference-execute", [loader, out / (name + ".a64.bin"), offset, 0, "aarch64", "-"],
                         [loader, out / (name + ".a64.bin")], selfhost.environment(out, False), success=False)
        row["reference"] = selfhost.inspect(result, row)
        row["staticPin"] = pin(out / (name + ".elf"))
    report = dict(status="PASS_STATIC_BOOTSTRAP_PREPARE", sourcePins=source_pins, sourceUnity=pin(source),
                  runtimeModules={p: pin(ROOT / p) for p in RUNTIME}, bridge=pin(bridge), S1=pin(out / "S1.elf"),
                  G1kx64=pin(out / "G1.kx64"), cases=rows, bootstrapCLoader=True, linuxRunUsesCLoader=False)
    dump(out / "static-prepare.json", report)
    print(report["status"], report["S1"], flush=True)


def elf_facts(path):
    data = path.read_bytes()
    assert data[:4] == b"\x7fELF" and data[4] == 2 and int.from_bytes(data[16:18], "little") == 2
    phoff, phnum = int.from_bytes(data[32:40], "little"), int.from_bytes(data[56:58], "little")
    types = [int.from_bytes(data[phoff + 56 * i:phoff + 56 * i + 4], "little") for i in range(phnum)]
    assert 3 not in types and 2 not in types, "static image must have no PT_INTERP / PT_DYNAMIC"
    return dict(type="ET_EXEC", machine=int.from_bytes(data[18:20], "little"), programHeaders=types,
                interpreter=None, dynamic=False)


def execute(out):
    assert platform.system() == "Linux" and platform.machine() in ("x86_64", "AMD64")
    prepared = json.loads((out / "static-prepare.json").read_text())
    paths = [p for p in (ROOT / MANIFEST).read_text().splitlines() if p and not p.startswith("#")]
    source = out / "seed-unity.kotoba"
    assert source.read_bytes() == b"".join((ROOT / p).read_bytes() + b"\n" for p in paths)
    assert pin(source) == prepared["sourceUnity"] and pin(out / "S1.elf") == prepared["S1"]
    run = Runs(out, {p: v for p, v in prepared["sourcePins"].items() if p.startswith("seed/") and not p.startswith("seed/bootstrap")})
    facts = elf_facts(out / "S1.elf")
    producer = out / "S1.elf"
    producer.chmod(0o755)
    generations = [dict(name="S1", pin=prepared["S1"], producedBy="bootstrap (pinned loader + bridge)")]
    for generation in (2, 3):
        image = out / f"S{generation}.elf"
        run.run(f"S{generation}-build", compile_args([producer], source, image, "static"), [source, producer], static_env(out))
        assert pin(image) == prepared["S1"], "static selfhost fixed point mismatch"
        image.chmod(0o755)
        generations.append(dict(name=f"S{generation}", pin=pin(image), producedBy=f"S{generation - 1} on Linux, no loader"))
        producer = image
    run.run("G1-kx64-from-S3", compile_args([producer], source, out / "G1.static.kx64", "kx64-v1"), [source, producer], static_env(out))
    assert pin(out / "G1.static.kx64") == prepared["G1kx64"], "static and loader-run compilers disagree"
    results = []
    for case in prepared["cases"]:
        name = case["name"]
        src, image = out / (name + ".kotoba"), out / (name + ".rebuilt.elf")
        assert src.read_text() == case["source"]
        run.run(name + "-static-compile", compile_args([producer], src, image, "static"), [src, producer], static_env(out))
        assert pin(image) == case["staticPin"], "host-dependent compiler output"
        image.chmod(0o755)
        result = run.run(name + "-static-execute", [image], [image], static_env(out, True), success=False)
        observed = selfhost.inspect(result, case)
        assert observed == case["reference"], (name, observed, case["reference"])
        results.append(dict(name=name, **observed))
    refused = []
    for name, text, flags in [
        ("float", '(ns refused (:export [main])) (defn main [] :i64 (f64-to-i64-truncating (f64-add 1.0 2.0)))', ["--format", "static"]),
        ("runtime-call", '(ns refused (:export [main])) (defn main [] :i64 (kxrt-exit 0))', ["--format", "static"]),
        ("unknown-format", '(ns refused (:export [main])) (defn main [] :i64 42)', ["--format", "unknown"]),
        ("existing-output", '(ns refused (:export [main])) (defn main [] :i64 42)', ["--format", "static"]),
    ]:
        src, dst = out / ("refuse-" + name + ".kotoba"), out / ("refuse-" + name + ".out")
        src.write_text(text)
        if name == "existing-output":
            dst.write_bytes(b"preserve original")
        result = run.run("refuse-" + name, [producer, "compile", src, "--target", "x86_64-linux", "--output", dst, *flags],
                         [src, producer], static_env(out), success=False)
        assert result.returncode != 0 and b"E" in result.stderr
        assert dst.read_bytes() == b"preserve original" if name == "existing-output" else not dst.exists()
        refused.append(name)
    outside = out / "outside"
    outside.mkdir()
    (outside / "o.kotoba").write_text('(ns o (:export [main])) (defn main [] :i64 42)')
    result = run.run("refuse-outside-scope", compile_args([producer], outside / "o.kotoba", out / "o.elf", "static"),
                     [producer], dict(static_env(out), KEXE_CAP_RESOURCES_35=str(out / "scope")), success=False)
    assert result.returncode != 0 and not (out / "o.elf").exists()
    refused.append("outside-scope")
    report = dict(status="PASS_LINUX_X86_STATIC_SELFHOST", host=[platform.system(), platform.machine()],
                  runner=dict(modules=prepared["runtimeModules"], form="linked into each image (x86_64-linux-static)"),
                  compiler=prepared["S1"], image=facts, sourceGraph=dict(unity=prepared["sourceUnity"], pins=prepared["sourcePins"]),
                  generations=generations, kx64CrossCheck=dict(loaderRun=prepared["G1kx64"], staticRun=pin(out / "G1.static.kx64")),
                  cases=results, refusals=refused, linuxRunUsesCLoader=False, bootstrapCLoader=True,
                  JVMNodeOrGraalFallback=False)
    dump(out / "static-selfhost.json", report)
    print(report["status"], len(results), "cases; S1=S2=S3", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--execute-linux", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        prepare(args.output.resolve())
    else:
        execute(args.output.resolve())
