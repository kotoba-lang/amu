#!/usr/bin/env python3
"""Observe the actual public Mac aliases, compiler and Kotoba packager.

Python stages source/lock bytes and records processes; native Amu performs
checking, compilation and extraction, and the native packager emits Mach-O.
This bounded first run does not qualify the complete Darwin runtime.
"""
import argparse
import importlib.util
import json
import platform
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main(out):
    assert (platform.system(), platform.machine()) == ("Darwin", "arm64")
    spec = importlib.util.spec_from_file_location(
        "mac_native", ROOT / "scripts/seed/check-aiueos-user-macos-native.py")
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    descriptor_path = ROOT / "seed/bootstrap/aarch64-macos/root.json"
    descriptor = json.loads(descriptor_path.read_text())
    aliases = [ROOT / "bin" / name for name in ("amu", "kotoba", "kotoba-compiler")]
    compiler = ROOT / descriptor["compiler"]["path"]
    packager = ROOT / descriptor["packager"]["path"]
    for path, key in ((compiler, "compiler"), (packager, "packager")):
        assert gate.verify_macho(path) == {k: descriptor[key][k] for k in ("bytes", "sha256")}
    for alias in aliases:
        assert alias.is_symlink() and alias.resolve(strict=True) == compiler.resolve(strict=True)
        assert gate.verify_macho(alias) == gate.pin(compiler)
    names = [s for s in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines()
             if s and not s.startswith("#")]
    unity = b"".join((ROOT / s).read_bytes() + b"\n" for s in names)
    import hashlib
    assert {"bytes": len(unity), "sha256": hashlib.sha256(unity).hexdigest()} == descriptor["fullSource"]
    out.mkdir(parents=True, mode=0o700, exist_ok=False)
    calls = []

    def run(name, image, *args, expected=0, diagnostic=None):
        r = gate.native_run(image, out, *args, expected=expected)
        (out / (name + ".stdout")).write_bytes(r.stdout)
        (out / (name + ".stderr")).write_bytes(r.stderr)
        if diagnostic:
            assert diagnostic in r.stderr and b"KEXE_TRAP" not in r.stderr
        calls.append(dict(name=name, exit=r.returncode,
                          stdout=gate.pin(out / (name + ".stdout")),
                          stderr=gate.pin(out / (name + ".stderr"))))
        return r

    src = out / "hello.kotoba"
    src.write_text("(ns hello (:export [main]))\n(defn main [] :i64 42)\n")
    lock = out / "hello.ksl"
    lock.write_text(f"KSL1\nentry /hello.kotoba\nfile {gate.pin(src)['sha256']} /hello.kotoba\n")
    locked = ("--source-lock", "hello.ksl", "--source-lock-sha256", gate.pin(lock)["sha256"])
    for i, alias in enumerate(aliases):
        run(f"alias-{i}-check", alias, "check", "/hello.kotoba", *locked)
    run("wrong-lock", aliases[0], "check", "/hello.kotoba", "--source-lock", "hello.ksl",
        "--source-lock-sha256", "0" * 64, expected=1, diagnostic=b"E6015")
    run("missing-target", aliases[0], "compile", "hello.kotoba", "--output", "refused.kseed",
        expected=1, diagnostic=b"E2")
    assert not (out / "refused.kseed").exists()
    results = []
    for value in (42, 43):
        src.write_text(f"(ns hello (:export [main]))\n(defn main [] :i64 {value})\n")
        lock.write_text(f"KSL1\nentry /hello.kotoba\nfile {gate.pin(src)['sha256']} /hello.kotoba\n")
        locked = ("--source-lock", "hello.ksl", "--source-lock-sha256", gate.pin(lock)["sha256"])
        stem = f"hello{value}"
        run(stem + "-compile", aliases[0], "compile", "/hello.kotoba", "--target",
            "aarch64-macos", "--output", stem + ".kseed", *locked)
        r = run(stem + "-extract", aliases[1], "extract-native", stem + ".kseed",
                "--symbol", "main", "--output", stem + ".raw")
        match = re.search(rb":offset (\d+), :length (\d+), :arity 0}", r.stdout)
        assert match and int(match[2]) == (out / (stem + ".raw")).stat().st_size
        run(stem + "-package", packager, stem + "-unsigned.macho", stem + ".raw",
            "fs2-cli-stdio-general", match[1].decode())
        image = out / (stem + ".macho")
        gate.sign(out / (stem + "-unsigned.macho"), image)
        gate.verify_macho(image)
        run(stem + "-execute", image, expected=value)
        results.append(value)
    assert gate.pin(compiler) == {k: descriptor["compiler"][k] for k in ("bytes", "sha256")}
    result = dict(schema="amu.public-macos-product.v1", status="PASS_PUBLIC_MACOS_PRODUCT",
                  descriptor=gate.pin(descriptor_path), compiler=gate.pin(compiler),
                  packager=gate.pin(packager), sourceUnity=descriptor["fullSource"],
                  aliases=[str(p.relative_to(ROOT)) for p in aliases], calls=calls,
                  nativeExitResults=results, explicitDirectoryFD=3,
                  linuxProcessInThisGate=False, legacyRuntimeFallback=False,
                  fullRuntimeQualified=False, independentUserQualified=False)
    (out / "public-macos-product.json").write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"], "native Mac aliases, pinned check, native results 42 -> 43")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    main(p.parse_args().output.resolve())
