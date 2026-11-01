#!/usr/bin/env python3
"""Native Linux positive and refusal checks for loaderless :fs/browse (wire 34).

Amu compiles the standalone Kotoba guest. Python only stages isolated fixtures,
observes the native artifact, and records hashes and outputs; no legacy runtime
or emulation participates in the guest execution.
"""
import argparse
import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "seed/tests/fs-browse-product.kotoba"


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main(compiler, output):
    machine = platform.machine()
    assert platform.system() == "Linux" and machine in ("aarch64", "arm64", "x86_64", "AMD64")
    output.mkdir(parents=True, exist_ok=False)
    artifacts = output / "artifacts"
    artifacts.mkdir()
    image = artifacts / "fs-browse.elf"
    target = "aarch64-linux" if machine in ("aarch64", "arm64") else "x86_64-linux"
    build_env = dict(PATH="/usr/bin:/bin", KEXE_STACK_BYTES="8388608",
                     KEXE_CAP_RESOURCES_35=f"{ROOT}:{output}")
    compile_run = subprocess.run(
        [str(compiler), "compile", str(SOURCE), "--target", target,
         "--output", str(image), "--format", "static"],
        cwd=artifacts, env=build_env, capture_output=True, timeout=900)
    (output / "compile.stdout").write_bytes(compile_run.stdout)
    (output / "compile.stderr").write_bytes(compile_run.stderr)
    assert compile_run.returncode == 0 and not compile_run.stderr and b":ok true" in compile_run.stdout, (
        compile_run.returncode, compile_run.stderr[-1000:])
    image.chmod(0o755)

    root = output / "browse-root"
    root.mkdir()
    (root / "alpha").write_text("unchanged")
    (root / "folder").mkdir()
    (root / "link").symlink_to("alpha")
    outside = output / "outside"
    outside.mkdir()
    (outside / "secret").write_text("unchanged")
    (root / "linkdir").symlink_to(outside, target_is_directory=True)
    link_root = output / "root-link"
    link_root.symlink_to(root, target_is_directory=True)

    allow = "34,37,38"
    base = dict(PATH="/nonexistent", KEXE_ALLOW=allow, KEXE_STACK_BYTES="8388608")
    rows = []

    def run(name, request, roots, allowed=allow, data_roots=None, want=0, stdout=None, diagnostic=None):
        env = dict(base, KEXE_ALLOW=allowed,
                   KEXE_CAP_RESOURCES_34=roots)
        if data_roots is not None:
            env["KEXE_CAP_RESOURCES_35"] = data_roots
        proc = subprocess.run([str(image), str(request)], cwd=output, env=env,
                              capture_output=True, timeout=60)
        (output / (name + ".stdout")).write_bytes(proc.stdout)
        (output / (name + ".stderr")).write_bytes(proc.stderr)
        assert proc.returncode == want, (name, proc.returncode, proc.stderr[-1000:])
        if stdout is not None:
            assert proc.stdout == stdout, (name, proc.stdout, stdout)
            assert not proc.stderr, (name, proc.stderr)
        if diagnostic is not None:
            assert diagnostic in proc.stderr, (name, diagnostic, proc.stderr[-1000:])
        rows.append({"name": name, "exit": proc.returncode,
                     "stdout": proc.stdout.decode(errors="replace"),
                     "stderr": proc.stderr.decode(errors="replace")[-500:]})

    expected = b"alpha\t0\nfolder\t1\nlink\t0\nlinkdir\t0"
    run("positive-sorted-and-symlink-entry", root, str(root), stdout=expected)
    run("outside-browse-root", outside, str(root), want=120, diagnostic=b"SIGILL")
    run("parent-component-refused", str(root / ".." / "outside"), str(root), want=120, diagnostic=b"SIGILL")
    run("symlink-directory-refused", root / "linkdir", str(root), want=120, diagnostic=b"SIGILL")
    run("symlink-root-refused", root, str(link_root), want=120, diagnostic=b"SIGILL")
    run("wire-34-ungranted", root, str(root), allowed="37,38", want=120,
        diagnostic=b"KEXE_CAP {:wire 34 :refused :not-granted}")
    run("wire-35-root-does-not-grant-browse", outside, "", data_roots=str(outside),
        want=120, diagnostic=b"SIGILL")
    assert (root / "alpha").read_bytes() == b"unchanged"
    assert (outside / "secret").read_bytes() == b"unchanged"

    report = {
        "status": "PASS_NATIVE_FS_BROWSE_WIRE34",
        "host": [platform.system(), machine], "target": target,
        "source": pin(SOURCE), "compiler": pin(compiler), "artifact": pin(image),
        "cases": rows, "legacyRuntimeFallback": False, "emulation": False,
        "wholeItonamiCliQualified": False,
    }
    (output / "native-fs-browse.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], machine)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve())
