#!/usr/bin/env python3
"""Guest code cannot reach the static runtime by name (JUN-325).

The runtime text (seed/76, seed/77) is appended to the guest and compiled in
the same unit, so its names resolve from guest code. seed/75 refuses a guest
call of a runtime function (E7101). Until 2026-10-22 it decided "runtime" by
the symbol's first appearance in the source: a guest that named a runtime
function made it a guest function, and an intrinsic named that way (for
example kxrt-syscall or kxrt-store64) was emitted inline in guest code. Now
the definition's position decides.

--compiler (an Amu-produced static compiler from these sources) must refuse
every probe below with E7101 and write no image, for --format static and
--format launcher on aarch64-linux and x86_64-linux; a plain guest compiles
(the positive control). With --previous-root, each probe is also compiled
by the previous root and its outcome recorded, and a plain guest gives the
same bytes from both compilers in every format.

Python only orchestrates processes and hashes. Run on Linux, e.g.
  podman run --platform linux/arm64 -v REPO:REPO -v OUT:OUT python:3.12-alpine \
    python3 REPO/scripts/seed/check-runtime-boundary.py --compiler BOOT/S3.elf --output OUT
"""
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# name -> (body, formats it applies to)
PROBES = {
    "kxrt-syscall": "(kxrt-syscall 172 0 0 0 0 0 0)",
    "kxrt-load64": "(kxrt-load64 4194304)",
    "kxrt-store64": "(kxrt-store64 4194304 0)",
    "kxrt-load8": "(kxrt-load8 4194304)",
    "kxrt-store8": "(kxrt-store8 4194304 0)",
    "kxrt-ctx": "(kxrt-ctx)",
    "kxrt-call-main": "(kxrt-call-main 0)",
    "kxrt-trap": "(kxrt-trap 0)",
    "kxrt-call-at": "(kxrt-call-at 0 0 0)",
    "kxrt-exit": "(kxrt-exit 9)",
    "kxrt-gl": "(kxrt-gl 72)",
    "kxrt-gs": "(kxrt-gs 72 0)",
    "kxrt-allow-bit": "(kxrt-allow-bit 20)",
    "kxrt-map": "(kxrt-map 4096)",
    "kxrt-slot-56": "(kxrt-slot-56 0 0 0)",
}
LAUNCHER_ONLY = {"kxrt-l-run": "(kxrt-l-run 0 0)", "kxrt-l-take": "(kxrt-l-take 0 0 0 0 false)"}
# The impact on the previous root: set every allow bit in the context, then use
# wire 3 (:hash/sha256), which KEXE_ALLOW=37,38,39 did not grant.
IMPACT = ('(ns g (:export [main]))\n(defn main [] :i64 (let [c (kxrt-ctx) a (kxrt-store64 (+ c 16) -1)]'
          ' (string-length (typed-cap-call :hash/sha256 :string :string "x"))))\n')
PLAIN = "(ns g (:export [main]))\n(defn main [] :i64 (let [w (typed-cap-call :io/write :string :string \"plain\\n\")] 42))\n"
FORMATS = [("aarch64-linux", "static"), ("aarch64-linux", "launcher"), ("x86_64-linux", "static"), ("x86_64-linux", "launcher")]


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def guest(body):
    return f"(ns g (:export [main]))\n(defn main [] :i64 {body})\n"


def main(compiler, output, previous_root):
    assert platform.system() == "Linux", "run on Linux"
    output.mkdir(parents=True, exist_ok=False)
    art = output / "artifacts"
    art.mkdir()
    producers = {"new": art / "compiler.elf"}
    producers["new"].write_bytes(compiler.read_bytes())
    if previous_root:
        producers["previous"] = art / "previous-root.elf"
        producers["previous"].write_bytes(previous_root.read_bytes())
    for p in producers.values():
        p.chmod(0o755)
    calls = []

    def compile_(who, name, source, tgt, fmt):
        src, out = art / f"{who}-{name}-{tgt}-{fmt}.kotoba", art / f"{who}-{name}-{tgt}-{fmt}.elf"
        src.write_text(source)
        z = subprocess.run([str(producers[who]), "compile", src.name, "--target", tgt, "--output", out.name, "--format", fmt],
                           cwd=art, env={"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art)}, capture_output=True, timeout=900)
        err = z.stderr.decode(errors="replace").strip()
        calls.append(dict(compiler=who, name=name, target=tgt, format=fmt, exit=z.returncode, stderr=err[-200:]))
        return z, out, err

    rows: dict = dict(refused={}, previous={}, plain={}, sameBytes={})
    for tgt, fmt in FORMATS:
        probes = dict(PROBES, **(LAUNCHER_ONLY if fmt == "launcher" else {}))
        for name, body in probes.items():
            z, out, err = compile_("new", name, guest(body), tgt, fmt)
            assert z.returncode != 0 and "E7101" in err and not out.exists(), (name, tgt, fmt, z.returncode, err[-300:])
            rows["refused"][f"{name} {tgt} {fmt}"] = "E7101"
            if previous_root and tgt == "aarch64-linux":
                z, out, err = compile_("previous", name, guest(body), tgt, fmt)
                rows["previous"][f"{name} {fmt}"] = "compiled" if z.returncode == 0 and out.exists() else err.split(": ")[-1][:60]
        z, out, err = compile_("new", "plain", PLAIN, tgt, fmt)
        assert z.returncode == 0 and out.exists() and not err, (tgt, fmt, err)
        rows["plain"][f"{tgt} {fmt}"] = pin(out)
        if previous_root:
            z, old, err = compile_("previous", "plain", PLAIN, tgt, fmt)
            assert z.returncode == 0 and old.read_bytes() == out.read_bytes(), ("plain output changed", tgt, fmt)
            rows["sameBytes"][f"{tgt} {fmt}"] = True
    if previous_root:
        admitted = sorted({k.split()[0] for k, v in rows["previous"].items() if v == "compiled"})
        assert "kxrt-syscall" in admitted, ("the previous root is expected to admit the kxrt-syscall probe", rows["previous"])
        rows["previousAdmitted"] = admitted
        host = {"aarch64": "aarch64-linux", "arm64": "aarch64-linux"}.get(platform.machine())
        if host:
            z, img, err = compile_("previous", "impact", IMPACT, host, "static")
            assert z.returncode == 0 and img.exists(), err
            img.chmod(0o755)
            x = subprocess.run([str(img)], cwd=art, env={"PATH": "/usr/bin:/bin", "KEXE_ALLOW": "37,38,39", "KEXE_STRUCTURED_REPORT": "1"},
                               capture_output=True, timeout=60)
            rows["previousImpact"] = dict(grant="KEXE_ALLOW=37,38,39", guest="sets the context allow bits, then calls wire 3",
                                          exit=x.returncode, stdout=x.stdout.decode(errors="replace").strip()[-160:],
                                          stderr=x.stderr.decode(errors="replace").strip()[-160:])
            z, img, err = compile_("new", "impact", IMPACT, host, "static")
            assert z.returncode != 0 and "E7101" in err and not img.exists(), err
    report = dict(status="PASS_RUNTIME_BOUNDARY", compiler=pin(compiler), previousRoot=pin(previous_root) if previous_root else None,
                  host=[platform.system(), platform.machine(), platform.release()],
                  probes=len(PROBES), launcherOnlyProbes=len(LAUNCHER_ONLY), results=rows, calls=calls, cCompilerOrLoader=False)
    (output / "runtime-boundary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], len(rows["refused"]), "probe compiles refused (E7101)",
          f"previous root admitted {len(rows.get('previousAdmitted', []))}" if previous_root else "", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--previous-root", type=Path, help="the root before JUN-325: records which probes it admitted")
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve(), args.previous_root.resolve() if args.previous_root else None)
