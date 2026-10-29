#!/usr/bin/env python3
"""The Mac diagnostic runtime implements arena-scope (JUN-546).

The generated code calls context ABI slots 224 and 232, the scalar arena-scope
enter and leave routines. The Mac runtime keeps a bounded LIFO of its four
allocator counters (pairs, pool, vector handles, vector items), refuses depth
257 and any inconsistent restore with exit 70, and zeroes the vector items it
releases. This gate compiles the repository's scope oracles with the
descriptor's compiler, packages them with its packager, signs and runs them
natively:

* native-arena-scope.kotoba main: 600,000 scoped allocations that only fit if
  every counter is restored on leave, nested scopes, f64 results, outer data
  untouched (exit 0);
* deep-main: depth 256 (exit 0); overflow-main: depth 257 (exit 70, one line on
  stderr); unscoped-main: the same allocations without scopes must still be
  refused at the original budget (negative control, any non-zero exit but not 0);
* native-zero-watermark.kotoba: released vector items read back as zero;
* leave without enter (a raw main calling slot 232 first): exit 70;
* a positive control (a program without scopes) and the smallest scoped program.

The compiler and packager are the descriptor's pinned images (the descriptor
also pins the packager source, so a runtime change moves through the JUN-545
staged run before this gate sees it).
Python stages and observes; compiler, packager and the programs are native.
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
MESSAGE = "seed: arena-scope failed (Mac runtime)\n"
SCOPE_ORACLE = ROOT / "seed/tests/native-arena-scope.kotoba"
ZERO_ORACLE = ROOT / "seed/tests/native-zero-watermark.kotoba"
PLAIN = "(ns plain (:export [main]))\n(defn main [] :i64 (if true 0 1))\n"
SMALL = "(ns small (:export [main]))\n(defn main [] :i64 (if (arena-scope true) 0 1))\n"
NESTED = ("(ns nested (:export [main]))\n"
          "(defn main [] :i64 (arena-scope (+ (arena-scope 40) 2)))\n")


def module():
    spec = importlib.util.spec_from_file_location("mac_native_gate", MAC_GATE)
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    return gate


def build(gate, compiler, packager, output, name, source, symbol="main"):
    (output / f"{name}.kotoba").write_text(source if isinstance(source, str) else source.read_text())
    gate.native_run(compiler, output, "compile", f"{name}.kotoba",
                    "--target", "aarch64-macos", "--output", f"{name}.kseed")
    extracted = gate.native_run(compiler, output, "extract-native", f"{name}.kseed",
                                "--symbol", symbol, "--output", f"{name}.raw")
    match = re.search(rb":offset (\d+), :length (\d+), :arity 0}", extracted.stdout)
    if match is None or int(match.group(2)) != (output / f"{name}.raw").stat().st_size:
        raise ValueError("native extraction did not match raw bytes: " + name)
    gate.native_run(packager, output, f"{name}-unsigned.macho", f"{name}.raw",
                    "fs2-cli-stdio-general", match.group(1).decode())
    gate.sign(output / f"{name}-unsigned.macho", output / f"{name}.macho")
    return output / f"{name}.macho"


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
    runs = output / "runs"; runs.mkdir(mode=0o700)
    expectations = [
        ("plain", PLAIN, "main", 0, False),
        ("small", SMALL, "main", 0, False),
        ("nested", NESTED, "main", 42, False),
        ("scope-main", SCOPE_ORACLE, "main", 0, False),
        ("scope-deep", SCOPE_ORACLE, "deep-main", 0, False),
        ("scope-overflow", SCOPE_ORACLE, "overflow-main", 70, True),
        ("zero-watermark", ZERO_ORACLE, "main", 0, False),
    ]
    for name, source, symbol, expected, refused in expectations:
        image = build(gate, compiler, packager, runs, name, source, symbol)
        result = gate.native_run(image, runs, expected=expected)
        stderr = result.stderr.decode(errors="replace")
        if refused and stderr != MESSAGE:
            raise ValueError(f"{name}: failure text changed: {stderr!r}")
        if not refused and stderr:
            raise ValueError(f"{name}: unexpected stderr {stderr!r}")
        print(f"{name}: exit {expected}", flush=True)
    # Leave without enter: no source form emits it, so the fixture is a six-word main
    # (stp x29,x30; mov x0,x7; ldr x16,[x0,#232]; blr x16; ldp; ret) packaged as raw.
    (runs / "underflow.raw").write_bytes(b"".join(
        word.to_bytes(4, "little") for word in
        (0xa9bf7bfd, 0xaa0703e0, 0xf9407410, 0xd63f0200, 0xa8c17bfd, 0xd65f03c0)))
    gate.native_run(packager, runs, "underflow-unsigned.macho", "underflow.raw",
                    "fs2-cli-stdio-general", "0")
    gate.sign(runs / "underflow-unsigned.macho", runs / "underflow.macho")
    result = gate.native_run(runs / "underflow.macho", runs, expected=70)
    if result.stderr.decode(errors="replace") != MESSAGE:
        raise ValueError("leave without enter did not report the scope failure")
    print("underflow: exit 70", flush=True)
    # Negative control: the same allocations without scopes must still be refused.
    image = build(gate, compiler, packager, runs, "unscoped", SCOPE_ORACLE, "unscoped-main")
    result = gate.process([image], cwd=runs, timeout=600) if hasattr(gate, "process") else None
    print("unscoped-main exit", result.returncode if result else "not run", flush=True)
    if result is None or result.returncode == 0:
        raise ValueError("unscoped allocations were not refused at the original budget")
    print("PASS_MAC_ARENA_SCOPE exit 0 controls, depth 257 -> 70, unscoped refused", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output.resolve())
