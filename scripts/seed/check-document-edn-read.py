#!/usr/bin/env python3
"""Native document-edn-read treats EDN delimiters as the spec does (JUN-650).

The document library that seed/21-check appends to a program keeps a document
as its EDN text, and every reader in it (count, get, nth, kind, ...) assumes
exactly one space between items. document-edn-read now canonicalizes its input
(comma, tab, LF, VT, FF, CR and runs of spaces are delimiters, ; starts a
comment, no space at either end, after an opener or before a closer).

This gate, on Apple Silicon:

* builds seed/tests/native-document-edn-read.kotoba with --compiler (the Mac
  fixed point of this tree) and the descriptor's packager, and runs it: exit 0;
* negative control: builds a mutant full compiler from this tree's FULL-MANIFEST
  with document-edn-read put back to the identity it was before JUN-650, builds
  the same corpus with it and runs it: it must fail at case 1 (exit 1);
* runs the corpus through the public CLI (bin/amu run), which must print 0.

Python stages sources and observes processes; every compiler and program is a
native Amu-built Mach-O.
"""

import argparse
import importlib.util
import platform
import subprocess
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "seed/tests/native-document-edn-read.kotoba"
CHECK = "seed/21-check.kotoba"
FIXED = '(defn- document-edn-read [s :string] :document (__r6-dd (__kr_dnorm s)))'
UNFIXED = '(defn- document-edn-read [s :string] :document (__r6-dd s))'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(compiler, output):
    if platform.system() != "Darwin" or platform.machine() not in ("arm64", "aarch64"):
        raise ValueError("Apple Silicon native host required")
    scope = load("scope", ROOT / "scripts/seed/check-macos-arena-scope.py")
    gate = scope.module()
    _, _, packager, _, _, _ = gate.bootstrap_inputs(SimpleNamespace(
        compiler_image=None, compiler_sha256=None, packager_image=None, packager_sha256=None))
    gate.verify_macho(compiler)
    gate.verify_macho(packager)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)

    fixed = output / "fixed"; fixed.mkdir(mode=0o700)
    image = scope.build(gate, compiler, packager, fixed, "corpus", CORPUS)
    gate.native_run(image, fixed, expected=0)
    print("fixed compiler: corpus exit 0", flush=True)

    # Negative control: the same tree with document-edn-read as the identity.
    mutant = output / "mutant"; mutant.mkdir(mode=0o700)
    names = [line for line in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines()
             if line and not line.startswith("#")]
    if CHECK not in names:
        raise ValueError("FULL-MANIFEST no longer lists " + CHECK)
    check = (ROOT / CHECK).read_text()
    if check.count(FIXED) != 1 or check.count(UNFIXED) != 0:
        raise ValueError("cannot construct the identity document-edn-read negative control")
    with (mutant / "full-unity.kotoba").open("w") as stream:
        for name in names:
            text = (ROOT / name).read_text()
            stream.write((text.replace(FIXED, UNFIXED) if name == CHECK else text) + "\n")
    mutant_compiler = scope.build(gate, compiler, packager, mutant, "full-unity",
                                  (mutant / "full-unity.kotoba").read_text())
    if gate.pin(mutant_compiler) == gate.pin(compiler):
        raise ValueError("mutant compiler is identical to the compiler under test")
    image = scope.build(gate, mutant_compiler, packager, mutant, "corpus", CORPUS)
    gate.native_run(image, mutant, expected=1)
    print("identity document-edn-read (mutant compiler): corpus exit 1", flush=True)

    # The public CLI built from this tree runs the same corpus.
    public = output / "public"; public.mkdir(mode=0o700)
    (public / "corpus.kotoba").write_bytes(CORPUS.read_bytes())
    result = subprocess.run([str(ROOT / "bin/amu"), "run", "corpus.kotoba"], cwd=public,
                            env={"PATH": "/usr/bin:/bin", "LANG": "C"},
                            capture_output=True, timeout=600)
    if result.returncode != 0 or result.stdout != b"0\n" or result.stderr:
        raise ValueError(f"bin/amu run: exit {result.returncode}, stdout {result.stdout!r}, "
                         f"stderr {result.stderr[-400:]!r}")
    print("bin/amu run corpus: 0", flush=True)
    print("PASS_NATIVE_DOCUMENT_EDN_READ_WITH_NEGATIVE_CONTROL", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
