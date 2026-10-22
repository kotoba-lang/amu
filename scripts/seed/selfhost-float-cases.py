#!/usr/bin/env python3
"""Float runtime cases on the loaderless selfhost chain. Companion to
selfhost-bootstrap.py. No C compiler or C loader. Python only orchestrates
processes and hashes.

Needs a completed selfhost-bootstrap.py output directory (selfhost-bootstrap.json,
S3.elf, C0.elf, R-aarch64.elf). Before certifying anything it loads
selfhost-bootstrap.json, requires its PASS status, and matches its recorded
S3 / C0 / runner pins against the producer files in --run: a partial bootstrap
directory or artifacts from the retired C-loader route must fail here, not be
certified as `cCompilerOrLoader=False`. The host is checked and recorded like
selfhost-bootstrap.py; `emulation=False` is only claimed on the verified arm64
Linux host.

Then it asserts both measured boundaries of every case in seed/float-cases.json:

1. the x86_64-linux S-route refuses it at SIR admission with the recorded
   E7101 detail (xg-check-sir in seed/70-x86_64-linux.kotoba; the detail is the
   first float SIR opcode the admission sees, so a different refusal cannot
   masquerade as this boundary), and
2. the C0 -> aarch64-macos payload -> extract-native -> R-aarch64 runner
   route executes it with the recorded result and fuel (result is only parsed
   for non-trap cases, mirroring selfhost-bootstrap.py; trap reports carry no
   :result field).

Run it on arm64 Linux, for example:
  podman run --platform linux/arm64 -v REPO:REPO -v RUN:RUN -v OUT:OUT \
    python:3.12-alpine python3 REPO/scripts/seed/selfhost-float-cases.py \
    --repo REPO --run RUN --output OUT/float-cases.json

Pitfall (measured): the runner environment (KEXE_COMMAND / KEXE_FUEL /
KEXE_ALLOW ...) must only be set for the run step. KEXE_FUEL=1000000 starves
the compile step (budget/fuel trap) and KEXE_ALLOW=- raises SIGILL there;
the compile step is unmetered and capability-quiet, exactly like
selfhost-bootstrap.py's compile_().
"""
import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
CASES = "seed/float-cases.json"
STACK = "8388608"
BOOTSTRAP = "selfhost-bootstrap.json"
PASS_STATUS = "PASS_LOADERLESS_SELFHOST_BOOTSTRAP"


def pin(p):
    data = Path(p).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--run", type=Path, required=True, help="selfhost-bootstrap output dir")
    ap.add_argument("--output", type=Path, required=True, help="receipt JSON path")
    args = ap.parse_args()
    # Resolve every CLI path before the subprocess cwd changes: relative --repo /
    # --run / --output would otherwise resolve against the wrong directory.
    args.repo, args.run, args.output = (p.resolve() for p in (args.repo, args.run, args.output))
    # Native-host precondition (same check as selfhost-bootstrap.py): the
    # emulation=False claim below is only made once this is established.
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "arm64"), "run on arm64 Linux"
    host = [platform.system(), platform.machine(), platform.release()]
    S3, C0, RUNNER = (args.run / n for n in ("S3.elf", "C0.elf", "R-aarch64.elf"))
    for p in (S3, C0, RUNNER):
        assert p.exists(), f"missing {p}"

    # Validate the bootstrap receipt before certifying its producers.
    bootstrap_path = args.run / BOOTSTRAP
    assert bootstrap_path.exists(), f"missing {bootstrap_path}"
    bootstrap = json.loads(bootstrap_path.read_text())
    assert bootstrap.get("status") == PASS_STATUS, bootstrap.get("status")
    assert bootstrap.get("cCompilerOrLoader") is False, "bootstrap ran a C compiler or loader"
    assert bootstrap.get("emulation") is False, "bootstrap ran emulated"
    expected = dict(
        S3=next(g["pin"] for g in bootstrap["generations"] if g["name"] == "S3"),
        C0=bootstrap["adopted"]["coreStatic"]["image"],
        runner=bootstrap["built"]["aarch64Runner"])
    producers = dict(S3=pin(S3), C0=pin(C0), runner=pin(RUNNER))
    assert producers == expected, ("producer mismatch against " + BOOTSTRAP, producers, expected)

    cases = json.loads((args.repo / CASES).read_text())["cases"]
    work = args.output.parent / "float-case-work"
    work.mkdir(parents=True, exist_ok=True)

    def run(name, argv, env, success=True):
        r = subprocess.run(list(map(str, argv)), cwd=work, env={"PATH": "/usr/bin:/bin", **env},
                           capture_output=True, timeout=3600)
        (work / (name + ".stdout")).write_bytes(r.stdout)
        (work / (name + ".stderr")).write_bytes(r.stderr)
        if success:
            assert r.returncode == 0 and not r.stderr, (name, r.returncode, r.stderr.decode(errors="replace"))
        return r

    results = []
    for case in cases:
        name = case["name"]
        src = work / f"{name}.kotoba"
        src.write_text(case["source"])
        rec = {"name": name}

        # 1. S-route: refused at SIR admission with the exact recorded detail
        refused = run(f"{name}-s-refuse", [S3, "compile", src, "--target", "x86_64-linux",
                                           "--output", work / f"{name}-s.elf", "--format", "static"],
                      {"KEXE_CAP_RESOURCES_35": str(work)}, success=False)
        refusal = refused.stderr.decode(errors="replace").strip()
        assert refused.returncode != 0 and b"E7101" in refused.stderr, (name, refused.returncode)
        assert f"detail {case['refusalDetail']}" in refusal, (name, refusal, case["refusalDetail"])
        rec["sRouteRefused"] = refusal

        # 2. runner route: compile (unmetered), extract, run (metered)
        scope = {"KEXE_CAP_RESOURCES_35": str(work), "KEXE_STACK_BYTES": STACK}
        run(f"{name}-compile", [C0, "compile", src, "--target", "aarch64-macos",
                                "--output", work / f"{name}.kseed"], scope)
        run(f"{name}-extract", [C0, "extract-native", work / f"{name}.kseed",
                                "--symbol", "main", "--output", work / f"{name}.bin"], scope)
        r = run(f"{name}-run", [RUNNER, work / f"{name}.bin", 0, 0, "aarch64", "35,37,38,39", "--"],
                {"KEXE_CAP_RESOURCES_35": str(work), "KEXE_STACK_BYTES": STACK, "KEXE_COMMAND": "1",
                 "KEXE_STRUCTURED_REPORT": "1", "KEXE_FUEL": "1000000", "KEXE_ALLOW": "-"}, success=False)
        fuel = re.search(rb":remaining ([0-9]+)", r.stdout)
        res = re.search(rb":result (-?[0-9]+)", r.stdout)
        observed = dict(exit=r.returncode, remainingFuel=int(fuel[1]) if fuel else None)
        assert observed == case["reference"], (name, observed, case["reference"])
        if case["trap"]:
            # Structured trap reports carry no :result field (selfhost-bootstrap.py
            # checks the same way), so expected-trap cases skip result parsing.
            assert b":status :trap" in r.stdout and res is None, name
        else:
            assert b":status :trap" not in r.stdout, name
            assert res is not None and int(res[1]) == case["result"], (name, res, case["result"])
            rec["result"] = case["result"]
        rec.update(payload=pin(work / f"{name}.bin"), observed=observed)
        results.append(rec)
        print(name, observed, "result", rec.get("result"), "trap", case["trap"], flush=True)

    receipt = dict(status="PASS_SELFHOST_FLOAT_CASES", host=host,
                   bootstrap=dict(receipt=pin(bootstrap_path), status=bootstrap["status"]),
                   producers=producers,
                   cases=results,
                   cCompilerOrLoader=False, JVMNodeOrGraalFallback=False, emulation=False)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print("PASS_SELFHOST_FLOAT_CASES", len(results), "cases", flush=True)


if __name__ == "__main__":
    main()
