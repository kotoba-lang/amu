#!/usr/bin/env python3
"""The Mac diagnostic runtime refuses arena-scope cleanly (JUN-546).

The generated code calls context ABI slots 224 and 232, the scalar arena-scope
enter and leave routines. This runtime does not implement them. Left at zero the
call went to address 0 (SIGSEGV, exit 139); the packager now points both slots
at a refusal that writes one line to stderr and exits 70. This gate compiles two
sources with the descriptor's root, packages them with the descriptor's
packager, signs and runs them:

* a program without arena-scope exits 0 (the refusal is not in its path);
* a program with arena-scope exits 70 with exactly the refusal line on stderr,
  and not 139 or any other status.

Python stages and observes; the compiler and packager are the pinned native
images. This is a refusal, not an implementation of scope: the Linux oracles
that need real scopes are not run on this runtime.
"""

import argparse
import importlib.util
import platform
import re
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
MAC_GATE = Path(__file__).with_name("check-aiueos-user-macos-native.py")
MESSAGE = "seed: arena-scope unsupported (Mac runtime, JUN-546)\n"
SOURCES = {
    "plain": "(ns plain (:export [main]))\n(defn main [] :i64 (if true 0 1))\n",
    "scoped": "(ns scoped (:export [main]))\n(defn main [] :i64 (if (arena-scope true) 0 1))\n",
}


def module():
    spec = importlib.util.spec_from_file_location("mac_native_gate", MAC_GATE)
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    return gate


def main(output):
    if platform.system() != "Darwin" or platform.machine() not in ("arm64", "aarch64"):
        raise ValueError("Apple Silicon native host required")
    gate = module()
    compiler, _, packager, _, _, _ = gate.bootstrap_inputs(
        SimpleNamespace(compiler_image=None, compiler_sha256=None,
                        packager_image=None, packager_sha256=None))
    gate.verify_macho(compiler)
    gate.verify_macho(packager)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    results = {}
    for name, source in SOURCES.items():
        (output / f"{name}.kotoba").write_text(source)
        gate.native_run(compiler, output, "compile", f"{name}.kotoba",
                        "--target", "aarch64-macos", "--output", f"{name}.kseed")
        extracted = gate.native_run(compiler, output, "extract-native", f"{name}.kseed",
                                    "--symbol", "main", "--output", f"{name}.raw")
        match = re.search(rb":offset (\d+), :length (\d+), :arity 0}", extracted.stdout)
        if match is None or int(match.group(2)) != (output / f"{name}.raw").stat().st_size:
            raise ValueError("native main extraction did not match raw bytes")
        gate.native_run(packager, output, f"{name}-unsigned.macho", f"{name}.raw",
                        "fs2-cli-stdio-general", match.group(1).decode())
        gate.sign(output / f"{name}-unsigned.macho", output / f"{name}.macho")
        expected = 0 if name == "plain" else 70
        results[name] = gate.native_run(output / f"{name}.macho", output, expected=expected)
    if results["scoped"].stderr.decode(errors="replace") != MESSAGE:
        raise ValueError("arena-scope refusal text changed: " + repr(results["scoped"].stderr))
    if results["plain"].stderr:
        raise ValueError("a program without arena-scope wrote to stderr")
    print("PASS_MAC_ARENA_SCOPE_REFUSED exit 70, control exit 0", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output.resolve())
