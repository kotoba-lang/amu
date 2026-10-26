#!/usr/bin/env python3
"""Review the FS2 AArch64 Kotoba literals against their assembly derivation.

The assembler is only an independent observer here. The native product build
uses the Kotoba literals and does not invoke this script or a C toolchain.
"""

from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "seed/macos-fs2-runtime-packager.kotoba"
EVIDENCE = ROOT / "docs/evidence/mac-aiueos-kernel-admission-20261026"
CASES = (
    ("fs2-da-helper-words", EVIDENCE / "fs2-da-virtual-root.derivation.s", 184, {27, 179}),
    ("fs2-lock-helper-words", EVIDENCE / "ksl1-lock.derivation.s", 198, {197}),
    ("fs2-ef-helper-words",
     ROOT / "docs/evidence/mac-fs2-ef-20261026/fs2-ef.derivation.s", 293, {291, 292}),
)


def literal_words(source, function):
    start = source.index("(defn- " + function + " ")
    end = source.find("\n(defn- ", start + 1)
    body = source[start:end if end >= 0 else None]
    return [int(word, 16) for word in re.findall(r"0x([0-9a-f]{8})\b", body)]


def object_words(path):
    output = subprocess.run(["/usr/bin/objdump", "-s", str(path)],
                            capture_output=True, check=True, text=True).stdout
    section = output.split("Contents of section __TEXT,__text:\n", 1)[1]
    words = []
    for line in section.splitlines():
        match = re.match(r"^\s*[0-9a-f]{4,8}\s+((?:[0-9a-f]{8}\s+){1,4})", line)
        if match:
            words.extend(int.from_bytes(bytes.fromhex(word), "little")
                         for word in match.group(1).split())
    return words


def main():
    source = SOURCE.read_text()
    with tempfile.TemporaryDirectory(prefix="mac-fs2-derivation-") as folder:
        for function, assembly, count, patched in CASES:
            object_path = Path(folder) / (function + ".o")
            subprocess.run(["/usr/bin/clang", "-arch", "arm64", "-c",
                            str(assembly), "-o", str(object_path)], check=True)
            literal = literal_words(source, function)
            derived = object_words(object_path)
            if len(literal) != count or len(derived) != count:
                raise ValueError(f"{function}: word count {len(literal)} != {len(derived)} != {count}")
            differences = [i for i, (a, b) in enumerate(zip(literal, derived)) if a != b]
            if not set(differences).issubset(patched):
                raise ValueError(f"{function}: unexpected literal differences {differences}")
            start = source.index("(defn- " + function + " ")
            end = source.find("\n(defn- ", start + 1)
            body = source[start:end if end >= 0 else None]
            for index in patched:
                if f"(vector-assoc! {index} " not in body:
                    raise ValueError(f"{function}: missing relocation patch {index}")
            print(function, "PASS", count, "words", "relocation slots", sorted(patched))


if __name__ == "__main__":
    main()
