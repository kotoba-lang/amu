#!/usr/bin/env python3
"""Run the native reader delimiter corpus and an unfixed-lexer negative control.

Python stages source and observes exit codes. Both readers and all checks execute
in Amu-built native Mach-O images; no hosted language runtime is a compiler.
"""
import argparse
import importlib.util
import pathlib
import platform
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[2]


def main(output):
    if platform.system() != "Darwin" or platform.machine() not in ("arm64", "aarch64"):
        raise ValueError("Apple Silicon native host required")
    spec = importlib.util.spec_from_file_location("scope", ROOT / "scripts/seed/check-macos-arena-scope.py")
    scope = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scope)
    gate = scope.module()
    compiler, _, packager, _, _, _ = gate.bootstrap_inputs(SimpleNamespace(
        compiler_image=None, compiler_sha256=None, packager_image=None, packager_sha256=None))
    gate.verify_macho(compiler)
    gate.verify_macho(packager)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    paths = ["seed/00-ns-static.kotoba", "seed/01-mem.kotoba", "seed/02-io.kotoba", "seed/10-lex.kotoba"]
    lexer = (ROOT / paths[-1]).read_text()
    fixed = "(= (lx-ch S q) want) (+ q 1)\n          (lx-closer? (lx-ch S q)) -1"
    unfixed = "(lx-closer? (lx-ch S q)) (+ q 1)"
    if lexer.count(fixed) != 1:
        raise ValueError("cannot construct unfixed-lexer negative control")
    for name, source_lexer, expected in (("unfixed", lexer.replace(fixed, unfixed), 4),
                                          ("fixed", lexer, 0)):
        source = "\n".join(source_lexer if p == paths[-1] else (ROOT / p).read_text() for p in paths)
        source += "\n" + (ROOT / "seed/tests/native-reader-delimiters.kotoba").read_text()
        image = scope.build(gate, compiler, packager, output, name, source)
        gate.native_run(image, output, expected=expected)
        print(name, "exit", expected, flush=True)
    print("PASS_NATIVE_READER_DELIMITERS_WITH_NEGATIVE_CONTROL", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, required=True)
    main(parser.parse_args().output.resolve())
