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

With --staged-native-root, the descriptor-pinned full ARM compiler builds
the runner and an intermediate G0 from the current source before the three
generations. This is a distinct, unadopted candidate when the historical G0
cannot compile the enlarged source; it does not certify the old bootstrap or
change an adoption receipt.

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


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main(boot, out, staged_native_root=False):
    require(platform.system() == "Linux" and platform.machine() in ("aarch64", "arm64"), "run on arm64 Linux")
    out.mkdir(parents=True, exist_ok=False)
    receipt = json.loads((boot / "selfhost-bootstrap.json").read_text()) if boot and (boot / "selfhost-bootstrap.json").exists() else None
    runner = out / "R-aarch64.elf"
    paths = [p for p in (ROOT / ADOPTED).read_text().splitlines() if p and not p.startswith("#")]
    unity = out / "adopted-unity.kotoba"
    unity.write_bytes(b"".join((ROOT / p).read_bytes() + b"\n" for p in paths))
    source_files = {p: pin(ROOT / p)["sha256"] for p in paths}
    payload = out / "G0.bin"
    env = {"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(out), "KEXE_COMMAND": "1", "KEXE_STACK_BYTES": ADOPTED_STACK}
    gens, calls = [], []
    staged_root_pin = None
    if staged_native_root:
        descriptor = json.loads((ROOT / "seed/bootstrap/aarch64-linux-static-root.json").read_text())
        root = ROOT / "seed/bootstrap/aarch64-linux-static-root.elf"
        staged_root_pin = pin(root)
        require(staged_root_pin == descriptor["image"], "staged root image mismatch")
        require(descriptor["sourceManifest"] == "seed/FULL-MANIFEST", "unexpected full manifest")
        full_names = [p for p in (ROOT / descriptor["sourceManifest"]).read_text().splitlines()
                      if p and not p.startswith("#")]
        full = out / "full-unity.kotoba"
        full.write_bytes(b"".join((ROOT / p).read_bytes() + b"\n" for p in full_names))
        require(pin(full) == descriptor["sourceUnity"], "staged root source mismatch")
        runner_source = out / "runner.kotoba"
        runner_source.write_bytes((ROOT / "seed/x86_64-kx64-runner.kotoba").read_bytes())
        for name, argv in (
            ("stage-runner", [root, "compile", runner_source, "--target", "aarch64-linux", "--output", runner, "--format", "runner"]),
            ("stage-G0-compile", [root, "compile", unity, "--target", "aarch64-macos", "--output", out / "G0.kseed"]),
            ("stage-G0-extract", [root, "extract-native", out / "G0.kseed", "--symbol", "main", "--output", payload]),
        ):
            result = subprocess.run(list(map(str, argv)), cwd=out, env=env, capture_output=True, timeout=3600)
            (out / (name + ".stdout")).write_bytes(result.stdout)
            (out / (name + ".stderr")).write_bytes(result.stderr)
            calls.append(dict(name=name, exit=result.returncode,
                              stdoutSHA256=hashlib.sha256(result.stdout).hexdigest(),
                              stderrSHA256=hashlib.sha256(result.stderr).hexdigest()))
            require(result.returncode == 0 and not result.stderr, (name, result.returncode, result.stderr[-400:]))
    else:
        require(boot is not None, "--bootstrap is required without --staged-native-root")
        runner.write_bytes((boot / "R-aarch64.elf").read_bytes())
        payload.write_bytes((ROOT / ADOPTED_BIN).read_bytes())
    runner.chmod(0o755)
    bootstrap_pin = pin(payload)
    for g in (1, 2, 3):
        prefix = [str(runner), str(payload), "0", "0", "aarch64", "35,37,38,39", "--"]
        container, native = out / f"G{g}.kseed", out / f"G{g}.bin"
        for name, argv in ((f"G{g}-compile", prefix + ["compile", str(unity), "--target", "aarch64-macos", "--output", str(container)]),
                           (f"G{g}-extract", prefix + ["extract-native", str(container), "--symbol", "main", "--output", str(native)])):
            r = subprocess.run(argv, cwd=out, env=env, capture_output=True, timeout=3600)
            (out / (name + ".stdout")).write_bytes(r.stdout)
            (out / (name + ".stderr")).write_bytes(r.stderr)
            calls.append(dict(name=name, exit=r.returncode,
                              stdoutSHA256=hashlib.sha256(r.stdout).hexdigest(),
                              stderrSHA256=hashlib.sha256(r.stderr).hexdigest()))
            require(r.returncode == 0 and not r.stderr, (name, r.returncode, r.stderr[-400:]))
        gens.append(dict(generation=g, native=pin(native), container=pin(container)))
        payload = native
    require(source_files == {p: pin(ROOT / p)["sha256"] for p in paths}, "core source changed during generation")
    if staged_native_root:
        require(pin(root) == staged_root_pin, "staged root changed during generation")
        full_now = b"".join((ROOT / p).read_bytes() + b"\n" for p in full_names)
        require({"bytes": len(full_now), "sha256": hashlib.sha256(full_now).hexdigest()} == descriptor["sourceUnity"], "full source changed during generation")
    fixed = all(gens[0][key] == gens[1][key] == gens[2][key] for key in ("native", "container"))
    # the static compiler whose runner this used: the bootstrap's root, else its S3
    runner_from = staged_root_pin if staged_native_root else (receipt["root"]["image"] if receipt else (pin(boot / "S3.elf") if (boot / "S3.elf").exists() else None))
    status = ("STAGED_ADOPTION_CANDIDATE_FIXED_POINT" if fixed else "STAGED_ADOPTION_CANDIDATE_NO_FIXED_POINT") if staged_native_root else ("ADOPTION_CANDIDATE_FIXED_POINT" if fixed else "ADOPTION_CANDIDATE_NO_FIXED_POINT")
    report = dict(status=status, stagedNativeRoot=staged_native_root,
                  host=[platform.system(), platform.machine(), platform.release()],
                  manifestPath=ADOPTED, sourceUnity=pin(unity), sourceFiles=source_files,
                  bootstrap=bootstrap_pin, runner=pin(runner),
                  runnerFrom=runner_from,
                  generations=gens, nativeImage=gens[2]["native"] if fixed else None,
                  calls=calls, cCompilerOrLoader=False)
    (out / "adoption-candidate.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], "unity", report["sourceUnity"]["sha256"][:16], "G", [x["native"]["sha256"][:16] for x in gens], flush=True)
    raise SystemExit(0 if fixed else 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bootstrap", type=Path, help="a selfhost-bootstrap.py output directory (its R-aarch64.elf)")
    parser.add_argument("--staged-native-root", action="store_true", help="derive a staged runner and G0 from the descriptor-pinned native ARM root")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if bool(args.bootstrap) == args.staged_native_root:
        parser.error("choose exactly one of --bootstrap or --staged-native-root")
    main(args.bootstrap.resolve() if args.bootstrap else None, args.output.resolve(), args.staged_native_root)
