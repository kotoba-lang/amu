#!/usr/bin/env python3
"""Build and execute the reader corpus and negative control with native Amu."""
import argparse
import os
import pathlib
import platform
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]


def main(compiler, output):
    if platform.system() != "Linux" or platform.machine() not in ("aarch64", "x86_64"):
        raise ValueError("native Linux arm64 or x86_64 required")
    target = "aarch64-linux" if platform.machine() == "aarch64" else "x86_64-linux"
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    env = dict(PATH="/nonexistent", KEXE_STACK_BYTES="8388608", KEXE_FUEL="10000000000",
               KEXE_ALLOW="35,37,38,39", KEXE_CAP_RESOURCES_35=str(output))
    paths = ["seed/00-ns-static.kotoba", "seed/01-mem.kotoba", "seed/02-io.kotoba", "seed/10-lex.kotoba"]
    lexer = (ROOT / paths[-1]).read_text()
    fixed = "(= (lx-ch S q) want) (+ q 1)\n          (lx-closer? (lx-ch S q)) -1"
    if lexer.count(fixed) != 1:
        raise ValueError("cannot construct unfixed-lexer negative control")
    for name, source_lexer, expected in (("unfixed", lexer.replace(fixed, "(lx-closer? (lx-ch S q)) (+ q 1)"), 4),
                                          ("fixed", lexer, 0)):
        source = "\n".join(source_lexer if p == paths[-1] else (ROOT / p).read_text() for p in paths)
        source += "\n" + (ROOT / "seed/tests/native-reader-delimiters.kotoba").read_text()
        src, image = output / (name + ".kotoba"), output / (name + ".elf")
        src.write_text(source)
        subprocess.run([compiler, "compile", src, "--target", target, "--output", image, "--format", "static"],
                       cwd=output, env=env, check=True, timeout=900)
        image.chmod(0o755)
        result = subprocess.run([image], cwd=output, env=env, capture_output=True, timeout=120)
        if result.returncode != expected or result.stdout or result.stderr:
            raise ValueError(f"{name}: exit {result.returncode}, stdout {result.stdout!r}, stderr {result.stderr!r}")
        print(name, "exit", expected, flush=True)
    print("PASS_NATIVE_READER_DELIMITERS_WITH_NEGATIVE_CONTROL", target, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve())
