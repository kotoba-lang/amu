#!/usr/bin/env python3
"""Build an adoption candidate for changed seed/MANIFEST sources, C-free.

selfhost-bootstrap.py step 3 checks the adopted closure against the pinned
receipt: the source unity must equal its sourceUnitySHA256, and G1, G2 and G3
must equal its nativeImageSHA256. An adoption round changes those sources on
purpose, so step 3 cannot pass until a new receipt exists. This script makes
the candidate the round records:

* the unity of seed/MANIFEST and the pin of every listed file;
* G1 = the pinned adopted compiler (seed/bootstrap/adopted-20261012.bin, the
  receipt's bootstrapSHA256) compiling that unity through the C-free aarch64
  runner of a selfhost-bootstrap.py output (--bootstrap); G2 = G1 compiling
  it; G3 = G2 compiling it;
* G1 = G2 = G3 is required (exit 1 otherwise).

It writes adoption-candidate.json; a person turns it into the new
seed/adoption-*.json together with the round's other evidence. It changes
nothing in the repository. Run on arm64 Linux.
"""
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADOPTED = "seed/MANIFEST"
ADOPTED_BIN = "seed/bootstrap/adopted-20261012.bin"
ADOPTED_STACK = "8388608"


def pin(p):
    data = Path(p).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main(boot, out):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "arm64"), "run on arm64 Linux"
    out.mkdir(parents=True, exist_ok=False)
    receipt = json.loads((boot / "selfhost-bootstrap.json").read_text()) if (boot / "selfhost-bootstrap.json").exists() else None
    runner = out / "R-aarch64.elf"
    runner.write_bytes((boot / "R-aarch64.elf").read_bytes())
    runner.chmod(0o755)
    paths = [p for p in (ROOT / ADOPTED).read_text().splitlines() if p and not p.startswith("#")]
    unity = out / "adopted-unity.kotoba"
    unity.write_bytes(b"".join((ROOT / p).read_bytes() + b"\n" for p in paths))
    source_files = {p: pin(ROOT / p)["sha256"] for p in paths}
    payload = out / "G0.bin"
    payload.write_bytes((ROOT / ADOPTED_BIN).read_bytes())
    env = {"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(out), "KEXE_COMMAND": "1", "KEXE_STACK_BYTES": ADOPTED_STACK}
    gens, calls = [], []
    for g in (1, 2, 3):
        prefix = [str(runner), str(payload), "0", "0", "aarch64", "35,37,38,39", "--"]
        container, native = out / f"G{g}.kseed", out / f"G{g}.bin"
        for name, argv in ((f"G{g}-compile", prefix + ["compile", str(unity), "--target", "aarch64-macos", "--output", str(container)]),
                           (f"G{g}-extract", prefix + ["extract-native", str(container), "--symbol", "main", "--output", str(native)])):
            r = subprocess.run(argv, cwd=out, env=env, capture_output=True, timeout=3600)
            (out / (name + ".stdout")).write_bytes(r.stdout)
            (out / (name + ".stderr")).write_bytes(r.stderr)
            calls.append(dict(name=name, exit=r.returncode))
            assert r.returncode == 0 and not r.stderr, (name, r.returncode, r.stderr[-400:])
        gens.append(dict(generation=g, native=pin(native), container=pin(container)))
        payload = native
    fixed = gens[0]["native"] == gens[1]["native"] == gens[2]["native"]
    # the static compiler whose runner this used: the bootstrap's root, else its S3
    runner_from = receipt["root"]["image"] if receipt else (pin(boot / "S3.elf") if (boot / "S3.elf").exists() else None)
    report = dict(status="ADOPTION_CANDIDATE_FIXED_POINT" if fixed else "ADOPTION_CANDIDATE_NO_FIXED_POINT",
                  host=[platform.system(), platform.machine(), platform.release()],
                  manifestPath=ADOPTED, sourceUnity=pin(unity), sourceFiles=source_files,
                  bootstrap=pin(ROOT / ADOPTED_BIN), runner=pin(runner),
                  runnerFrom=runner_from,
                  generations=gens, nativeImage=gens[2]["native"] if fixed else None,
                  calls=calls, cCompilerOrLoader=False)
    (out / "adoption-candidate.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], "unity", report["sourceUnity"]["sha256"][:16], "G", [x["native"]["sha256"][:16] for x in gens], flush=True)
    raise SystemExit(0 if fixed else 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bootstrap", type=Path, required=True, help="a selfhost-bootstrap.py output directory (its R-aarch64.elf)")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.bootstrap.resolve(), args.output.resolve())
