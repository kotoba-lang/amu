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
    assert identity((ROOT / "bin/amu-linux-x86_64").read_bytes()) == product["image"]
    for alias in product["aliases"]:
        assert (ROOT / alias).resolve() == (ROOT / "bin/amu-linux-x86_64").resolve()
    assert identity((ROOT / "seed/bootstrap/aarch64-linux-static-root.elf").read_bytes()) == root["image"] == product["rootImage"]
    mac = json.loads((ROOT / "seed/bootstrap/aarch64-macos/root.json").read_text())
    assert mac["fullSource"] == product["sourceUnity"]
    mac_image = ROOT / mac["compiler"]["path"]
    assert identity(mac_image.read_bytes()) == {k: mac["compiler"][k] for k in ("bytes", "sha256")}
    assert mac_image.read_bytes()[:8] == bytes.fromhex("cffaedfe0c000001")
    cli = json.loads((ROOT / "seed/bootstrap/aarch64-macos/cli.json").read_text())
    assert cli["schema"] == "amu.macos-native-cli.v1"
    assert cli["compiler"] == mac["compiler"] and cli["packager"] == mac["packager"], "stale public Mac dependency pins"
    assert cli["image"]["path"] == "seed/bootstrap/aarch64-macos/amu-cli.macho"
    public_image = ROOT / cli["image"]["path"]
    assert identity(public_image.read_bytes()) == {k: cli["image"][k] for k in ("bytes", "sha256")}, "public Mac image pin mismatch"
    assert public_image.read_bytes()[:8] == bytes.fromhex("cffaedfe0c000001")
    for role in ("packager", "packagerSource"):
        assert identity((ROOT / mac[role]["path"]).read_bytes()) == {k: mac[role][k] for k in ("bytes", "sha256")}
    core = paths[:paths.index("seed/90-drv.kotoba") + 1]
    assert len(core) == 17
    source_names = core + ["seed/macos-cli-api.kotoba", "seed/macos-cli.kotoba"]
    assert set(cli["sources"]) == set(source_names), "public Mac source recipe mismatch"
    for name in source_names:
        assert identity((ROOT / name).read_bytes()) == cli["sources"][name], "public Mac source pin mismatch: " + name
    pins = (f'(def MC-COMPILER-SHA256 "{mac["compiler"]["sha256"]}")\n'
            f'(def MC-PACKAGER-SHA256 "{mac["packager"]["sha256"]}")\n').encode()
    cli_unity = b"".join((ROOT / name).read_bytes() + b"\n" for name in core + ["seed/macos-cli-api.kotoba"])
    cli_unity += pins + b"\n" + (ROOT / "seed/macos-cli.kotoba").read_bytes() + b"\n"
    assert identity(cli_unity) == cli["unity"], "public Mac unity pin mismatch"
    for name in ("amu", "kotoba", "kotoba-compiler"):
        alias = ROOT / "bin" / name
        assert alias.is_symlink() and alias.resolve(strict=True) == public_image.resolve(strict=True), "public Mac alias mismatch"
    spec = importlib.util.spec_from_file_location("native_cdci_check", ROOT / "scripts/seed/check-native-cdci.py")
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    policy = json.loads((ROOT / "seed/cdci/policy.json").read_text())
    checker.controller_pin_metadata(policy)
    print("PASS_NATIVE_IDENTITIES_PREFLIGHT_ONLY", len(paths), "production modules")


if __name__ == "__main__":
    main()
