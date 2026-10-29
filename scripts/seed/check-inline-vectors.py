#!/usr/bin/env python3
"""Inline vector, pair and string access in the plain emitters (seed/70-71 x86_64, seed/80 aarch64).

The runtime-profile emitters no longer call the vector-at (176),
vector-assoc! (208), count (168), pair-first (64) and pair-second /
string-length (72) helpers, store a fresh VEC/VECP vector's items directly,
and read a code-relative string's ASCII byte for string-code-point-at (144) in
line under the R4 rule (seed/X86_64-LINUX-ABI, "Inline vector access" and
"Inline pair and string access"). The contract is that nothing observable
changes: result, fuel, trap kind and all seventeen arena counters stay those
of the helper calls.

seed/inline-vector-cases.json holds a corpus of in-range, boundary and trap
programs (negative, one-past-the-end and extreme indices, assoc! out of range,
count, vector literals and pooled literals, persistent assoc, conj, drop
views, arena-scope rollback, fuel exhaustion inside a vector or string loop;
string literals, multi-byte UTF-8 lead and continuation bytes, pool strings,
substring views, string ops after an in-line read, pair handles 0, past the
end and negative) with the observations of the helper-call compiler (the
x86_64 static compiler, then bin/amu,
aa021865659c6d889f1fa633167f80bd2e842c79a41275ff03f3389a0b11c1d2), per target
and per fuel budget. This check compiles every case with --compiler as a
static image for --target, runs it, and requires the exact exit status,
stdout and stderr.

Python only stages bytes and runs processes; the compiler and the images are
Kotoba. Run on Linux with a kernel of the target ISA, e.g.
  python3 scripts/seed/check-inline-vectors.py --compiler OUT/F1.elf --output OUT/inline-vectors
  python3 scripts/seed/check-inline-vectors.py --compiler bin/amu-linux-x86_64 --target x86_64-linux --output OUT/inline-vectors-x86
"""
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "seed/inline-vector-cases.json"
MACHINE = {"aarch64-linux": ("aarch64", "arm64"), "x86_64-linux": ("x86_64", "amd64")}


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def observe(elf, fuel):
    env = {"PATH": "/usr/bin:/bin", "KEXE_STRUCTURED_REPORT": "1", "KEXE_FUEL": str(fuel),
           "KEXE_ALLOW": "-", "KEXE_ARENA_USE": "1"}
    r = subprocess.run([str(elf)], env=env, capture_output=True, timeout=120)
    return {"exit": r.returncode, "stdout": r.stdout.decode(), "stderr": r.stderr.decode()}


def main(compiler, output, target, record=False):
    assert platform.system() == "Linux" and platform.machine() in MACHINE[target], ("run on a native", target, "kernel")
    spec = json.loads(CASES.read_text())
    output.mkdir(parents=True, exist_ok=False)
    art = output / "artifacts"
    art.mkdir()
    rows, failures = [], []
    for case in spec["cases"]:
        src, elf = art / (case["name"] + ".kotoba"), art / (case["name"] + ".elf")
        src.write_text(case["source"])
        r = subprocess.run([str(compiler), "compile", str(src), "--target", target, "--output", str(elf), "--format", "static"],
                           cwd=art, env={"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art), "KEXE_STACK_BYTES": "8388608"},
                           capture_output=True, timeout=1800)
        assert r.returncode == 0 and not r.stderr and b":ok true" in r.stdout, (case["name"], r.returncode, r.stderr[-400:])
        elf.chmod(0o755)
        for fuel in spec["fuel"]:
            seen = observe(elf, fuel)
            key = f"{target} {fuel}"
            if record:
                case.setdefault("expected", {})[key] = seen
            elif case["expected"][key] != seen:
                failures.append(dict(name=case["name"], fuel=fuel, expected=case["expected"][key], observed=seen))
            rows.append(dict(name=case["name"], fuel=fuel, image=pin(elf), **seen))
    if record:
        CASES.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    report = dict(status="PASS_INLINE_VECTOR_CORPUS" if not failures else "FAIL_INLINE_VECTOR_CORPUS",
                  target=target, host=[platform.system(), platform.machine(), platform.release()],
                  compiler=pin(compiler), corpus=pin(CASES), cases=len(spec["cases"]), runs=rows, failures=failures)
    (output / "inline-vectors.json").write_text(json.dumps(report, indent=1) + "\n")
    for f in failures:
        print("MISMATCH", f["name"], f["fuel"], json.dumps(f["observed"])[:300])
    print(report["status"], target, len(spec["cases"]), "cases", len(rows), "runs")
    return 0 if not failures else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--compiler", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--target", choices=sorted(MACHINE), default="aarch64-linux")
    ap.add_argument("--record", action="store_true", help="write the observations into the corpus (reference compiler only)")
    a = ap.parse_args()
    raise SystemExit(main(a.compiler.resolve(), a.output.resolve(), a.target, a.record))
