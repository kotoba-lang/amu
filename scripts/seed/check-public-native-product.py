#!/usr/bin/env python3
"""Read back the published native product bytes and exercise each public alias.

Packaging/process observations only; no hosted compiler or fallback.
"""
import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(product, out, complete):
    assert platform.system() == "Linux" and platform.machine() == "x86_64"
    descriptor = json.loads((product / "native-product.json").read_text())
    entry = product / descriptor["entry"]
    assert sha(entry) == descriptor["image"]["sha256"]
    assert entry.stat().st_size == descriptor["image"]["bytes"]
    proof_path = complete / "complete-x86.json"
    proof = json.loads(proof_path.read_text())
    assert proof["status"] == "PASS_COMPLETE_NATIVE_X86_COMPILER_BUILD"
    assert len(proof["generations"]) == 3
    for i, generation in enumerate(proof["generations"], 1):
        actual = complete / f"F{i}.elf"
        assert sha(actual) == generation["sha256"] == sha(entry), "public image differs from current native compiler"
        assert actual.stat().st_size == generation["bytes"] == descriptor["image"]["bytes"]
    root = Path(__file__).resolve().parents[2]
    paths = [p for p in (root / descriptor["sourceManifest"]).read_text().splitlines()
             if p and not p.startswith("#")]
    assert len(paths) == descriptor["sourceModuleCount"]
    unity = b"".join((root / p).read_bytes() + b"\n" for p in paths)
    assert {"bytes": len(unity), "sha256": hashlib.sha256(unity).hexdigest()} == proof["sourceUnity"], "current full source differs"
    aliases = [entry, *[product / p for p in descriptor["aliases"]]]
    for p in aliases[1:]:
        assert p.is_symlink() and os.readlink(p) == "amu"
        assert sha(p) == sha(entry)
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    src = out / "public-good.kotoba"
    src.write_text("(ns public-good (:export [main]))\n(defn main [] :i64 42)\n")
    lock = out / "public-good.ksl"
    lock.write_text(f"KSL1\nentry {src}\nfile {sha(src)} {src}\n")
    env = {"PATH": "/nonexistent", "KEXE_ALLOW": "35,37,38,39",
           "KEXE_CAP_RESOURCES_35": str(out), "KEXE_STACK_BYTES": "8388608"}
    calls = []

    def run(name, argv, expected, custom=env, diagnostic=None):
        r = subprocess.run(list(map(str, argv)), env=custom, cwd=out, capture_output=True, timeout=120)
        (out / (name + ".stdout")).write_bytes(r.stdout)
        (out / (name + ".stderr")).write_bytes(r.stderr)
        assert r.returncode == expected, (name, r.returncode, r.stderr[-400:])
        if diagnostic:
            assert diagnostic.encode() in r.stderr and b"KEXE_TRAP" not in r.stderr
        else:
            assert not r.stderr, (name, r.stderr)
        calls.append(dict(name=name, exit=r.returncode,
                          stdoutSHA256=hashlib.sha256(r.stdout).hexdigest(),
                          stderrSHA256=hashlib.sha256(r.stderr).hexdigest()))
        return r

    for i, alias in enumerate(aliases):
        run(f"alias-{i}-check", [alias, "check", src, "--source-lock", lock,
                                "--source-lock-sha256", sha(lock)], 0)
    container = out / "public-good.kseed"
    run("compile-pinned", [entry, "compile", src, "--target", "aarch64-macos", "--output", container,
                           "--source-lock", lock, "--source-lock-sha256", sha(lock)], 0)
    assert sha(container) == "d9d93e2896184a1eff34a88f79cdfd9d51d96afd2af1f6d1b2020010ebc920bc"
    native = out / "hello.elf"
    run("compile-native", [aliases[1], "compile", src, "--target", "x86_64-linux",
                           "--output", native, "--format", "static"], 0)
    native.chmod(0o700)
    r = run("run-native", [native], 0,
            {"PATH": "/nonexistent", "KEXE_ALLOW": "-", "KEXE_FUEL": "1000000", "KEXE_STRUCTURED_REPORT": "1"})
    # A literal return emits no OP-FUEL. The fixed24 operation-bearing
    # corpus has its own unchanged expectations in the native gate.
    assert re.search(rb":result 42\b", r.stdout) and re.search(rb":remaining 1000000\b", r.stdout)
    run("refuse-digest", [entry, "check", src, "--source-lock", lock,
                          "--source-lock-sha256", "0" * 64], 1, diagnostic="E6015")
    run("refuse-c-linked", [entry, "compile", src, "--target", "x86_64-linux", "--output", out / "c-linked.elf", "--format", "platform-linked"], 1, diagnostic="E2")
    assert not (out / "c-linked.elf").exists()
    run("refuse-default", [entry, "compile", src, "--output", out / "refused.kseed"], 1, diagnostic="E2")
    run("refuse-worker", [aliases[2], "worker"], 2, diagnostic="E1")
    assert not (out / "refused.kseed").exists()
    report = dict(status="PASS_PUBLIC_NATIVE_PRODUCT", image=descriptor["image"],
                  sourceRevision=descriptor["sourceRevision"], aliases=len(aliases),
                  nativeResult=42, remainingFuel=1000000, calls=calls,
                  completeReceiptSHA256=sha(proof_path),
                  currentSourceUnity=proof["sourceUnity"],
                  sameAsCurrentNativeGenerations=True,
                  observerSourceSHA256=sha(Path(__file__)),
                  host=[platform.system(), platform.machine(), platform.release()],
                  legacyRuntimeFallback=False)
    (out / "public-product.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], "3 aliases, pinned check/compile, native execution and named refusals", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--product", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--complete", type=Path, required=True, help="current check-complete-x86.py output")
    a = p.parse_args()
    main(a.product.resolve(), a.output.resolve(), a.complete.resolve())
