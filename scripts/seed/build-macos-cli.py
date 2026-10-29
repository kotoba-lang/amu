#!/usr/bin/env python3
"""Stage and observe the Amu-native Mac CLI build; no compiler/emitter here."""
import argparse
import importlib.util
import json
import platform
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def build(out):
    assert (platform.system(), platform.machine()) == ("Darwin", "arm64")
    spec = importlib.util.spec_from_file_location("mac_native", ROOT / "scripts/seed/check-aiueos-user-macos-native.py")
    mac = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mac)
    d = json.loads((ROOT / "seed/bootstrap/aarch64-macos/root.json").read_text())
    compiler, bootstrap = [ROOT / d[key]["path"] for key in ("compiler", "packager")]
    for key, image in (("compiler", compiler), ("packager", bootstrap)):
        assert mac.verify_macho(image) == {k: d[key][k] for k in ("bytes", "sha256")}
    out.mkdir(parents=True, mode=0o700, exist_ok=False)

    def native(paths, stem, packager, mode):
        source = out / (stem + ".kotoba")
        source.write_bytes(b"".join(path.read_bytes() + b"\n" for path in paths))
        mac.native_run(compiler, out, "compile", source.name, "--target", "aarch64-macos", "--output", stem + ".kseed")
        r = mac.native_run(compiler, out, "extract-native", stem + ".kseed", "--symbol", "main", "--output", stem + ".raw")
        match = re.search(rb":offset (\d+), :length (\d+), :arity 0}", r.stdout)
        assert match and int(match[2]) == (out / (stem + ".raw")).stat().st_size
        mac.native_run(packager, out, stem + "-unsigned.macho", stem + ".raw", mode, match[1].decode())
        image = out / (stem + ".macho")
        mac.sign(out / (stem + "-unsigned.macho"), image)
        mac.verify_macho(image)
        return image

    packager = native([ROOT / "seed/macos-fs2-runtime-packager.kotoba"], "packager", bootstrap, "fs2-cli-stdio-general")
    assert mac.pin(ROOT / "seed/macos-fs2-runtime-packager.kotoba") == {k: d["packagerSource"][k] for k in ("bytes", "sha256")}
    assert mac.pin(out / "packager-unsigned.macho")["sha256"] == d["expectedFixedPoint"]["packagerUnsignedSha256"]
    pins = out / "macos-cli-pins.kotoba"
    pins.write_text(f'(def MC-COMPILER-SHA256 "{mac.pin(compiler)["sha256"]}")\n'
                    f'(def MC-PACKAGER-SHA256 "{mac.pin(bootstrap)["sha256"]}")\n')
    names = []
    for name in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines():
        if name and not name.startswith("#"):
            names.append(name)
            if name == "seed/90-drv.kotoba":
                break
    assert len(names) == 17
    paths = [ROOT / name for name in names] + [ROOT / "seed/macos-cli-api.kotoba", pins, ROOT / "seed/macos-cli.kotoba"]
    cli = native(paths, "amu-cli", bootstrap, "amu-cli-host")
    report = dict(schema="amu.macos-native-cli-build.v1", status="BUILT_NATIVE_MACOS_CLI", compiler=mac.pin(compiler),
                  packager=mac.pin(bootstrap), rebuiltPackager=mac.pin(packager), cli=mac.pin(cli), unity=mac.pin(out / "amu-cli.kotoba"),
                  sources={str(p.relative_to(ROOT)): mac.pin(p) for p in paths if p.is_relative_to(ROOT)},
                  nativeBuild=True, hostedFallback=False, publicEntrySelected=False)
    (out / "cli-build.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], cli)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    build(p.parse_args().output.resolve())
