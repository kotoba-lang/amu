"""Build and run one Amu program as a signed macOS arm64 image (JUN-586).

Shared by the native definition gates when they run on Apple Silicon. The Mac
root compiler emits a KSEED container, extracts the native `main`, and the Mac
packager wraps it in the fs2-cli-stdio-general runtime. Python only stages
bytes, launches the native programs and signs a copy with the system
codesign. File access goes through FD 3 (the output directory) and file names
are basenames, as the Mac runtime requires (KOTOBA-169).
"""
import importlib.util
import json
import os
import platform
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESCRIPTOR = ROOT / "seed/bootstrap/aarch64-macos/root.json"


def available():
    return platform.system() == "Darwin" and platform.machine() in ("arm64", "aarch64")


def _mac():
    spec = importlib.util.spec_from_file_location("mac_native", ROOT / "scripts/seed/check-aiueos-user-macos-native.py")
    mac = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mac)
    return mac


def root_images():
    """The descriptor's compiler and packager, verified against their pins."""
    mac = _mac()
    d = json.loads(DESCRIPTOR.read_text())
    images = {}
    for role in ("compiler", "packager"):
        image = ROOT / d[role]["path"]
        assert mac.verify_macho(image) == {k: d[role][k] for k in ("bytes", "sha256")}, role
        images[role] = image
    return images["compiler"], images["packager"]


def build(compiler, packager, out, source_name, stem):
    """Compile out/source_name and return (signed image, unsigned image)."""
    mac = _mac()
    mac.native_run(compiler, out, "compile", source_name, "--target", "aarch64-macos", "--output", stem + ".kseed")
    r = mac.native_run(compiler, out, "extract-native", stem + ".kseed", "--symbol", "main", "--output", stem + ".raw")
    match = re.search(rb":offset (\d+), :length (\d+), :arity 0}", r.stdout)
    assert match and int(match[2]) == (out / (stem + ".raw")).stat().st_size, r.stdout[-300:]
    mac.native_run(packager, out, stem + "-unsigned.macho", stem + ".raw", "fs2-cli-stdio-general", match[1].decode())
    image = out / (stem + ".macho")
    mac.sign(out / (stem + "-unsigned.macho"), image)
    mac.verify_macho(image)
    return image, out / (stem + "-unsigned.macho")


def run(image, out, args, timeout=900):
    """Run a packaged image with FD 3 = out, cwd = out; arguments must be basenames."""
    for a in args:
        assert "/" not in str(a), ("the Mac runtime takes basenames only", a)
    fd = os.open(out, os.O_RDONLY | os.O_DIRECTORY)
    try:
        return subprocess.run([str(image), *map(str, args)], cwd=out, env={"PATH": "/usr/bin:/bin", "LANG": "C"},
                              capture_output=True, timeout=timeout, pass_fds=(3,), preexec_fn=lambda: os.dup2(fd, 3))
    finally:
        os.close(fd)
