#!/usr/bin/env python3
"""The Mac diagnostic runtime implements keyword interning (JUN-707).

The prelude's keyword paths (keyword-from-string, keyword-name,
document-keyword-value, every __r6-kwreg caller) call context ABI slots 96 and
104, the private keyword intern rows (seed/73-keyword-intern.kotoba on Linux).
The Mac runtime keeps them in a 6 MiB anonymous mapping made on first use,
outside every arena, at most 262144 rows, and refuses a wrong context tag, a
failed mapping or a full table with one line on stderr and exit 70. Before
JUN-707 neither slot was installed and these programs died of SIGSEGV (exit
139). This gate compiles the oracles with the descriptor's compiler, packages
them with its packager, signs and runs them natively:

* macos-keyword-intern.kotoba main: 1,800 Unicode keywords interned twice with
  identity and name round trips, a literal keyword, document-keyword-value and
  a keyword interned inside arena-scope surviving the scope's rollback (exit 0);
* exhaust-main: more names than 262144 rows hold (exit 70, the refusal line);
* a raw main calling slot 96 with a context whose tag is not 11 (exit 70);
* a positive control without keywords.

Python stages and observes; compiler, packager and the programs are native.
"""

import argparse
import importlib.util
import platform
import re
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
MAC_GATE = Path(__file__).with_name("check-aiueos-user-macos-native.py")
MESSAGE = "seed: keyword intern failed (Mac runtime)\n"
ORACLE = ROOT / "seed/tests/macos-keyword-intern.kotoba"
PLAIN = "(ns plain (:export [main]))\n(defn main [] :i64 (if true 0 1))\n"


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
        ("keywords", ORACLE, "main", 0, False),
        ("exhaust", ORACLE, "exhaust-main", 70, True),
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
    # A wrong context tag: no source form passes one, so the fixture is a six-word
    # main (stp x29,x30,[sp,#-16]!; mov x0,sp; ldr x16,[x7,#96]; blr x16; ldp; ret)
    # whose "context" is the saved frame pointer on the stack.
    (runs / "badtag.raw").write_bytes(b"".join(
        word.to_bytes(4, "little") for word in
        (0xa9bf7bfd, 0x910003e0, 0xf94030f0, 0xd63f0200, 0xa8c17bfd, 0xd65f03c0)))
    gate.native_run(packager, runs, "badtag-unsigned.macho", "badtag.raw",
                    "fs2-cli-stdio-general", "0")
    gate.sign(runs / "badtag-unsigned.macho", runs / "badtag.macho")
    result = gate.native_run(runs / "badtag.macho", runs, expected=70)
    if result.stderr.decode(errors="replace") != MESSAGE:
        raise ValueError("a wrong context tag did not report the keyword intern failure")
    print("badtag: exit 70", flush=True)
    print("PASS_MAC_KEYWORD_INTERN keywords exit 0, 262144-row table full -> 70, wrong tag -> 70", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output.resolve())
