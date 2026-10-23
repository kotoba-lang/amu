#!/usr/bin/env python3
"""The combined compiler (JUN-331): the adopted core plus the Linux targets in one image.

Input (--bootstrap) is a selfhost-bootstrap.py output (arm64 Linux): S3.elf,
P-aarch64.elf (the packed core) and runner.kotoba. No C compiler or loader, no
emulation. Records, natively:

1. Pw: P compiles seed/CORE-STATIC-MANIFEST (the core with the static-profile
   namespace) to Kw, S3 packs it; Pw rebuilds Kw (fixed point);
2. F: Pw compiles seed/FULL-MANIFEST to F1, S3 packs it; F1 compiles the same
   source to F2 and packs F2 itself; F2 compiles it to F3. F1 = F2 = F3 and
   the image F packs equals the one S3 packed;
3. F's core route: F compiles seed/MANIFEST to the adoption receipt's image;
4. F's Linux targets emit the same bytes as S3: the runtime cases
   (seed/static-cases.json) as aarch64-linux static images, which then run
   against the pinned results, and the Linux selfhost closure as an x86_64
   static compiler (= S-x86_64.elf of the bootstrap).

Python only orchestrates processes and hashes.
"""
import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STACK = "8388608"


def pin(p):
    data = Path(p).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main(boot, out):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "arm64"), "run on arm64 Linux"
    out.mkdir(parents=True, exist_ok=False)
    (out / "raw").mkdir()
    calls = []

    def run(name, argv, env, ok=True, timeout=3600):
        r = subprocess.run(list(map(str, argv)), cwd=out, env={"PATH": "/usr/bin:/bin", **env}, capture_output=True, timeout=timeout)
        (out / "raw" / (name + ".stdout")).write_bytes(r.stdout)
        (out / "raw" / (name + ".stderr")).write_bytes(r.stderr)
        calls.append(dict(name=name, argv=list(map(str, argv)), env=env, exit=r.returncode))
        if ok:
            assert r.returncode == 0 and not r.stderr, (name, r.returncode, r.stderr[-400:])
        return r

    for name in ("S3.elf", "P-aarch64.elf", "S-x86_64.elf", "runner.kotoba"):
        shutil.copy2(boot / name, out / name)
    for name in ("S3.elf", "P-aarch64.elf"):
        (out / name).chmod(0o755)
    S, P, runner = out / "S3.elf", out / "P-aarch64.elf", out / "runner.kotoba"
    env = {"KEXE_CAP_RESOURCES_35": str(out), "KEXE_STACK_BYTES": STACK}

    def unity(manifest, dst):
        paths = [p for p in (ROOT / manifest).read_text().splitlines() if p and not p.startswith("#")]
        dst.write_bytes(b"".join((ROOT / p).read_bytes() + b"\n" for p in paths))
        return {p: pin(ROOT / p) for p in [manifest, *paths]}

    sources = {m: unity(m, out / f"{n}.kotoba") for m, n in (("seed/CORE-STATIC-MANIFEST", "core-static"),
                                                           ("seed/FULL-MANIFEST", "full"),
                                                           ("seed/MANIFEST", "adopted"),
                                                           ("seed/X86_64-LINUX-SELFHOST-MANIFEST", "selfhost"))}

    def core(prod, src, name):
        run(name, [prod, "compile", out / f"{src}.kotoba", "--target", "aarch64-macos", "--output", out / f"{name}.kseed"], env)
        return pin(out / f"{name}.kseed")

    def pack(prod, kseed, name):
        run(f"{name}-pack", [prod, "compile", runner, "--target", "aarch64-linux", "--output", out / f"{name}.elf",
                             "--format", "packed", "--payload", out / f"{kseed}.kseed"], env)
        (out / f"{name}.elf").chmod(0o755)
        return pin(out / f"{name}.elf")

    # 1. Pw, the packed core with the static-profile capacities
    kw = core(P, "core-static", "Kw")
    pw = pack(S, "Kw", "Pw")
    assert core(out / "Pw.elf", "core-static", "K2") == kw, "Pw fixed point"

    # 2. F, the combined compiler
    f1 = core(out / "Pw.elf", "full", "F1")
    f1_image = pack(S, "F1", "F1")
    f2 = core(out / "F1.elf", "full", "F2")
    f2_image = pack(out / "F1.elf", "F2", "F2")
    f3 = core(out / "F2.elf", "full", "F3")
    assert f1 == f2 == f3, "combined compiler fixed point"
    assert f1_image == f2_image, "the image F packs differs from the one S3 packs"
    F = out / "F2.elf"

    # 3. F's core route reproduces the adoption image
    adoption = json.loads((ROOT / "seed/adoption-20261022.json").read_text())
    assert pin(out / "adopted.kotoba")["sha256"] == adoption["sourceUnitySHA256"], "adopted source drift"
    core(F, "adopted", "A")
    run("A-extract", [F, "extract-native", out / "A.kseed", "--symbol", "main", "--output", out / "A.bin"], env)
    assert pin(out / "A.bin")["sha256"] == adoption["nativeImageSHA256"], "F's core route differs from the adoption image"

    # 4. F's Linux targets emit S3's bytes; the cases run against the pinned results
    results = []
    for case in json.loads((ROOT / "seed/static-cases.json").read_text())["cases"]:
        src = out / f"case-{case['name']}.kotoba"
        src.write_text(case["source"])
        images = []
        for who, prod in (("S3", S), ("F", F)):
            dst = out / f"case-{case['name']}-{who}.elf"
            run(f"case-{case['name']}-{who}", [prod, "compile", src, "--target", "aarch64-linux", "--output", dst, "--format", "static"], env)
            dst.chmod(0o755)
            images.append(pin(dst))
        assert images[0] == images[1], ("case image differs", case["name"])
        r = run(f"case-{case['name']}", [out / f"case-{case['name']}-F.elf"],
                {"KEXE_STRUCTURED_REPORT": "1", "KEXE_FUEL": "1000000", "KEXE_ALLOW": "-"}, ok=False)
        fuel = re.search(rb":remaining ([0-9]+)", r.stdout)
        observed = dict(exit=r.returncode, remainingFuel=int(fuel[1]) if fuel else None)
        assert observed == case["reference"], (case["name"], observed, case["reference"])
        results.append(dict(name=case["name"], image=images[1], **observed))
    run("x86-compiler", [F, "compile", out / "selfhost.kotoba", "--target", "x86_64-linux", "--output", out / "X-F.elf", "--format", "static"], env)
    assert pin(out / "X-F.elf") == pin(out / "S-x86_64.elf"), "F's x86_64 compiler differs from S3's"

    report = dict(status="PASS_COMBINED_COMPILER", host=[platform.system(), platform.machine(), platform.release()],
                  sources=sources, bootstrap=dict(S3=pin(S), P=pin(P), receipt=pin(boot / "selfhost-bootstrap.json")),
                  Pw=dict(container=kw, image=pw),
                  F=dict(containers=[f1, f2, f3], image=f1_image, packedByF=f2_image),
                  coreRoute=dict(native=pin(out / "A.bin"), expected=adoption["nativeImageSHA256"]),
                  cases=results, x86_64Compiler=pin(out / "X-F.elf"),
                  cCompilerOrLoader=False, emulation=False)
    (out / "calls.json").write_text(json.dumps(calls, indent=1) + "\n")
    (out / "one-compiler.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], "F1=F2=F3", f1["sha256"][:16], "image", f1_image["sha256"][:16], len(results), "cases", flush=True)


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", type=Path, required=True, help="selfhost-bootstrap.py output (arm64 Linux)")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.bootstrap.resolve(), args.output.resolve())
