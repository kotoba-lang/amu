"""Cheap source/image preflight; not compiler or controller qualification."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def identity(data):
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def main():
    product = json.loads((ROOT / "native-product.json").read_text())
    root = json.loads((ROOT / "seed/bootstrap/aarch64-linux-static-root.json").read_text())
    paths = [line for line in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines()
             if line and not line.startswith("#")]
    assert len(paths) == product["sourceModuleCount"]
    unity = b"".join((ROOT / path).read_bytes() + b"\n" for path in paths)
    assert identity(unity) == product["sourceUnity"] == root["sourceUnity"]
    assert identity((ROOT / "bin/amu").read_bytes()) == product["image"]
    for alias in product["aliases"]:
        assert (ROOT / alias).resolve() == (ROOT / "bin/amu").resolve()
    assert identity((ROOT / "seed/bootstrap/aarch64-linux-static-root.elf").read_bytes()) == root["image"] == product["rootImage"]
    spec = importlib.util.spec_from_file_location("native_cdci_check", ROOT / "scripts/seed/check-native-cdci.py")
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    policy = json.loads((ROOT / "seed/cdci/policy.json").read_text())
    checker.controller_pin_metadata(policy)
    print("PASS_NATIVE_IDENTITIES_PREFLIGHT_ONLY", len(paths), "production modules")


if __name__ == "__main__":
    main()
