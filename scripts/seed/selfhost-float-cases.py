#!/usr/bin/env python3
"""Float runtime cases on the loaderless selfhost chain. Companion to
selfhost-bootstrap.py. No C compiler or C loader. Python only orchestrates
processes and hashes.

Needs a completed selfhost-bootstrap.py output directory (S3.elf, C0.elf,
R-aarch64.elf) and asserts both measured boundaries of every case in
seed/float-cases.json:

1. the x86_64-linux S-route refuses it at SIR admission (E7101 from
   xg-check-sir in seed/70-x86_64-linux.kotoba), and
2. the C0 -> aarch64-macos payload -> extract-native -> R-aarch64 runner
   route executes it with the recorded result and fuel.

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
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
CASES = "seed/float-cases.json"
STACK = "8388608"


def pin(p):
    data = Path(p).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--run", type=Path, required=True, help="selfhost-bootstrap output dir")
    ap.add_argument("--output", type=Path, required=True, help="receipt JSON path")
    args = ap.parse_args()
    S3, C0, RUNNER = (args.run / n for n in ("S3.elf", "C0.elf", "R-aarch64.elf"))
    for p in (S3, C0, RUNNER):
        assert p.exists(), f"missing {p}"
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

        # 1. S-route: refused at SIR admission (measured boundary)
        refused = run(f"{name}-s-refuse", [S3, "compile", src, "--target", "x86_64-linux",
                                           "--output", work / f"{name}-s.elf", "--format", "static"],
                      {"KEXE_CAP_RESOURCES_35": str(work)}, success=False)
        assert refused.returncode != 0 and b"E7101" in refused.stderr, (name, refused.returncode)
        rec["sRouteRefused"] = refused.stderr.decode(errors="replace").strip()

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
        assert (b":status :trap" in r.stdout) == case["trap"], name
        assert res is not None and int(res[1]) == case["result"], (name, res, case["result"])
        rec.update(payload=pin(work / f"{name}.bin"), observed=observed, result=case["result"])
        results.append(rec)
        print(name, observed, "result", case["result"], flush=True)

    receipt = dict(status="PASS_SELFHOST_FLOAT_CASES",
                   producers=dict(S3=pin(S3), C0=pin(C0), runner=pin(RUNNER)),
                   cases=results,
                   cCompilerOrLoader=False, JVMNodeOrGraalFallback=False, emulation=False)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print("PASS_SELFHOST_FLOAT_CASES", len(results), "cases", flush=True)


if __name__ == "__main__":
    main()
