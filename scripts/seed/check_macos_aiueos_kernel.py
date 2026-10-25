#!/usr/bin/env python3
"""Qualify a pinned Mac selfhost compiler against a staged AIUEOS kernel graph.

Python stages and observes bytes; the signed Kotoba/Amu Mach-O performs the
module discovery and both kernel builds. Run this through native_build_queue.py.
This is source-lock and image admission, not a boot or desktop qualification.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import struct
import subprocess


FUEL = 1073741824
TARGET = "x86_64-aiueos-kernel-v1"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": digest(raw)}


def virtual_path(word):
    if not word.startswith("/") or not word.isascii() or any(c.isspace() for c in word):
        raise ValueError("source lock path must be absolute bounded ASCII")
    parts = word[1:].split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("source lock path is not canonical")
    return Path(*parts)


def parse_lock(raw):
    lines = raw.decode("ascii").splitlines()
    if not lines or lines[0] != "KSL1":
        raise ValueError("expected KSL1 lock")
    entry, roots, files = None, [], {}
    phase = 0
    for line in lines[1:]:
        words = line.split(" ")
        if len(words) == 2 and words[0] == "entry" and phase == 0:
            entry = words[1]
            virtual_path(entry)
            phase = 1
        elif len(words) == 2 and words[0] == "root" and phase in (1, 2):
            virtual_path(words[1])
            roots.append(words[1])
            phase = 2
        elif len(words) == 3 and words[0] == "file" and phase in (2, 3):
            if len(words[1]) != 64 or any(c not in "0123456789abcdef" for c in words[1]):
                raise ValueError("invalid file hash")
            virtual_path(words[2])
            if words[2] in files:
                raise ValueError("duplicate locked source")
            files[words[2]] = words[1]
            phase = 3
        else:
            raise ValueError("malformed source lock")
    if entry not in files or not roots or not files or len(roots) != len(set(roots)):
        raise ValueError("incomplete source lock")
    if list(files) != sorted(files):
        raise ValueError("source lock files are not sorted")
    return entry, roots, files


def verify_image(path):
    blob = path.read_bytes()
    if len(blob) < 8192 or blob[:7] != b"\x7fELF\x02\x01\x01":
        raise ValueError("not a 64-bit ELF image")
    header = struct.unpack_from("<16sHHIQQQIHHHHHH", blob)
    if header[1:4] != (2, 62, 1) or header[4] != 0x101000 or header[9:11] != (56, 2):
        raise ValueError("unexpected AIUEOS kernel ELF header")
    program = [struct.unpack_from("<IIQQQQQQ", blob, header[5] + i * 56) for i in range(2)]
    rx, rw = program
    if rx[:2] != (1, 5) or rw[:2] != (1, 6) or rx[5] != rx[6] or rw[5] != rw[6]:
        raise ValueError("unexpected kernel segments")
    if rx[2] != 4096 or rx[3] != 0x101000 or rw[2] + rw[5] > len(blob):
        raise ValueError("kernel segment bounds invalid")
    if struct.unpack_from("<Q", blob, rw[2] + 8)[0] != FUEL:
        raise ValueError("kernel fuel disagrees")
    return {"textBytes": rx[5], "dataBytes": rw[5], "fuel": FUEL, "interpreter": False}


def main(args):
    if platform.system() != "Darwin" or platform.machine() not in ("arm64", "aarch64"):
        raise ValueError("this gate requires an Apple Silicon Mac")
    compiler, source, output = args.compiler.resolve(), args.source_root.resolve(), args.output
    if pin(compiler)["sha256"] != args.compiler_sha256:
        raise ValueError("compiler SHA-256 pin mismatch")
    binary = compiler.read_bytes()
    if len(binary) < 32 or struct.unpack_from("<IiiI", binary) != (0xfeedfacf, 0x100000c, 0, 2):
        raise ValueError("compiler is not an arm64 macOS executable")
    subprocess.run(["/usr/bin/codesign", "--verify", "--strict", str(compiler)],
                   capture_output=True, check=True)
    dylibs = subprocess.run(["/usr/bin/otool", "-L", str(compiler)],
                           capture_output=True, check=True).stdout.splitlines()
    if dylibs != [f"{compiler}:".encode()]:
        raise ValueError("compiler has undeclared dynamic library dependencies")
    if pin(args.source_lock)["sha256"] != args.source_lock_sha256:
        raise ValueError("source-lock SHA-256 pin mismatch")
    entry, roots, files = parse_lock(args.source_lock.read_bytes())
    staged = {}
    for name, expected in files.items():
        path = source / virtual_path(name)
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(source):
            raise ValueError("source missing or escaped: " + name)
        raw = path.read_bytes()
        if digest(raw) != expected:
            raise ValueError("source hash drift: " + name)
        staged[name] = raw
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in staged.items():
        dest = output / virtual_path(name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
    lock = output / "kernel.ksl"
    lock.write_bytes(args.source_lock.read_bytes())
    source_args = [value for root in roots for value in ("--source-path", root)]
    calls = []
    scope = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
    if scope != 3:
        os.dup2(scope, 3)
        os.close(scope)
        scope = 3

    def run(name, command, expected_exit, diagnostic=None):
        result = subprocess.run([str(compiler), *command], cwd=output, pass_fds=(scope,),
                                capture_output=True, timeout=3600)
        row = {"name": name, "exit": result.returncode,
               "stdout": result.stdout.decode("utf-8", "replace")[:1000],
               "stderr": result.stderr.decode("utf-8", "replace")[:1000]}
        calls.append(row)
        if (result.returncode == 0) != expected_exit or b"KEXE_TRAP" in result.stderr:
            raise ValueError(f"{name}: unexpected compiler exit: {row}")
        if diagnostic and diagnostic not in result.stderr:
            raise ValueError(f"{name}: missing diagnostic: {row}")
        return result

    def compile_args(dest, lock_name="kernel.ksl", lock_hash=args.source_lock_sha256, locked=True):
        command = ["compile", entry, "--target", TARGET, "--artifact", "image",
                   "--output", dest, "--fuel", str(FUEL), *source_args]
        if locked:
            command += ["--source-lock", lock_name, "--source-lock-sha256", lock_hash]
        return command

    try:
        found = run("modules", ["modules", entry, *source_args], True)
        discovered = {}
        for line in found.stdout.decode("ascii").splitlines():
            namespace, path = line.split(" ", 1)
            if not namespace or path in discovered:
                raise ValueError("duplicate or empty module discovery")
            discovered[path] = namespace
        if set(discovered) != set(files):
            raise ValueError("compiler discovery differs from KSL1 file set")
        run("kernel", compile_args("KERNEL.ELF"), True)
        run("reproduced", compile_args("KERNEL.reproduced.ELF"), True)
        first, second = output / "KERNEL.ELF", output / "KERNEL.reproduced.ELF"
        if pin(first) != pin(second):
            raise ValueError("kernel bytes are not reproduced")
        image = verify_image(first)
        run("wrong-lock-digest", compile_args("wrong-digest.ELF", lock_hash="0" * 64), False, b"E6015")
        run("missing-lock", compile_args("missing-lock.ELF", locked=False), False)
        run("lock-traversal", compile_args("lock-traversal.ELF", lock_name="../kernel.ksl"), False)
        (output / "alias.ksl").symlink_to("kernel.ksl")
        run("lock-symlink", compile_args("lock-symlink.ELF", lock_name="alias.ksl"), False)
        altered = lock.read_text().replace(next(iter(files.values())), "0" * 64, 1).encode("ascii")
        (output / "altered.ksl").write_bytes(altered)
        run("altered-lock", compile_args("altered-lock.ELF", lock_name="altered.ksl",
                                         lock_hash=digest(altered)), False, b"E6015")
        transitive = next(name for name in files if name != entry)
        transitive_path = output / virtual_path(transitive)
        transitive_path.write_bytes(staged[transitive] + b"\n")
        try:
            run("source-drift", compile_args("source-drift.ELF"), False, b"E6015")
        finally:
            transitive_path.write_bytes(staged[transitive])
        (output / "existing.ELF").write_bytes(b"existing-output-sentinel")
        run("existing-output", compile_args("existing.ELF"), False)
        if (output / "existing.ELF").read_bytes() != b"existing-output-sentinel":
            raise ValueError("existing output overwritten")
        for name in ("wrong-digest", "missing-lock", "lock-traversal", "lock-symlink",
                     "altered-lock", "source-drift"):
            if (output / (name + ".ELF")).exists():
                raise ValueError("refusal created output: " + name)
        if pin(lock)["sha256"] != args.source_lock_sha256 or any(
                digest((output / virtual_path(name)).read_bytes()) != sha for name, sha in files.items()):
            raise ValueError("source inputs changed during build")
        receipt = {"schema": "amu.macos-aiueos-kernel-admission.v1", "status": "PASS",
                   "scope": "Mac selfhost locked source and ELF candidate; boot and desktop untested",
                   "compiler": pin(compiler), "sourceLock": pin(lock), "modules": discovered,
                   "kernel": pin(first), "image": image, "reproduced": True, "calls": calls,
                   "linuxJVMNodeCompiler": False}
        (output / "admission.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print("MAC_AIUEOS_KERNEL_ADMISSION_OK", len(discovered), "modules", receipt["kernel"]["sha256"])
    finally:
        os.close(scope)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--compiler-sha256", required=True)
    p.add_argument("--source-root", type=Path, required=True)
    p.add_argument("--source-lock", type=Path, required=True)
    p.add_argument("--source-lock-sha256", required=True)
    p.add_argument("--output", type=Path, required=True)
    main(p.parse_args())
