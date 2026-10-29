#!/usr/bin/env python3
"""Build/observe the native Darwin CLI service; Python only stages bytes.

Every compiler, emitter, filesystem/process operation and probe runs as an
Amu-built Mach-O. No C compiler, assembler, Linux process or hosted launcher.
"""
import argparse
import importlib.util
import json
import os
import platform
import re
import shutil
import signal
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main(out):
    assert (platform.system(), platform.machine()) == ("Darwin", "arm64")
    spec = importlib.util.spec_from_file_location("mac_native", ROOT / "scripts/seed/check-aiueos-user-macos-native.py")
    mac = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mac)
    d = json.loads((ROOT / "seed/bootstrap/aarch64-macos/root.json").read_text())
    compiler, bootstrap = [ROOT / d[key]["path"] for key in ("compiler", "packager")]
    for key, image in (("compiler", compiler), ("packager", bootstrap)):
        assert mac.verify_macho(image) == {k: d[key][k] for k in ("bytes", "sha256")}
    out.mkdir(parents=True, mode=0o700, exist_ok=False)
    sources = {}

    def build(paths, stem, packager, mode):
        data = b"".join((ROOT / p).read_bytes() + b"\n" for p in paths)
        (out / (stem + ".kotoba")).write_bytes(data)
        sources[stem] = {p: mac.pin(ROOT / p) for p in paths}
        mac.native_run(compiler, out, "compile", stem + ".kotoba", "--target", "aarch64-macos", "--output", stem + ".kseed")
        r = mac.native_run(compiler, out, "extract-native", stem + ".kseed", "--symbol", "main", "--output", stem + ".raw")
        m = re.search(rb":offset (\d+), :length (\d+), :arity 0}", r.stdout)
        assert m and int(m[2]) == (out / (stem + ".raw")).stat().st_size
        mac.native_run(packager, out, stem + "-unsigned.macho", stem + ".raw", mode, m[1].decode())
        image = out / (stem + ".macho")
        mac.sign(out / (stem + "-unsigned.macho"), image)
        mac.verify_macho(image)
        return image

    packager = build(["seed/macos-fs2-runtime-packager.kotoba"], "packager", bootstrap, "fs2-cli-stdio-general")
    images = {case: build([f"seed/tests/macos-cli-host-{case}.kotoba", "seed/macos-cli-api.kotoba"], case, packager, "amu-cli-host")
              for case in ("info", "files", "spawn", "refusals", "fds", "timeout", "loop")}
    calls = []

    def run(case, *args, expected=None, inherited=False, alarm=False):
        # Intentionally no inherited directory FD, external environment or PATH.
        def inherited_setup():
            if inherited:
                os.dup2(secret, 3)
                os.dup2(secret, 91)
            if alarm:
                signal.signal(signal.SIGALRM, signal.SIG_IGN)
                signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})

        r = subprocess.run([str(images[case]), *map(str, args)], cwd=out,
                           env={"PATH": "/nonexistent", "LANG": "C"},
                           capture_output=True, timeout=20, close_fds=not inherited,
                           preexec_fn=inherited_setup if inherited or alarm else None)
        name = f"{len(calls):02d}-{case}"
        (out / (name + ".stdout")).write_bytes(r.stdout)
        (out / (name + ".stderr")).write_bytes(r.stderr)
        assert r.returncode == 0 and not r.stderr, (name, r.returncode, r.stdout, r.stderr)
        if expected is not None:
            assert r.stdout == expected
        calls.append(dict(name=name, exit=r.returncode, stdout=mac.pin(out / (name + ".stdout"))))

    run("info", expected=(str(images["info"]) + "\n").encode())
    run("files", out / "native paths 日本語", expected=b"PASS_NATIVE_HOST_FILES\n")
    run("spawn", out, images["info"], expected=b"PASS_NATIVE_HOST_SPAWN\n")
    assert (out / "child.stdout").read_bytes() == (str(images["info"]) + "\n").encode()
    (out / "child.stdout").unlink()
    secret = os.open(out / "info.kotoba", os.O_RDONLY)
    try:
        os.set_inheritable(secret, True)
        run("spawn", out, images["fds"], expected=b"PASS_NATIVE_HOST_SPAWN\n", inherited=True)
    finally:
        os.close(secret)
    assert (out / "child.stdout").read_bytes() == b"PASS_NATIVE_CHILD_FDS_CLOSED\n"
    run("timeout", out, images["loop"], expected=b"PASS_NATIVE_CHILD_DEADLINE\n", alarm=True)
    regular = out / "regular"
    regular.write_bytes(b"private")
    link, fifo = out / "symlink", out / "fifo"
    link.symlink_to(regular)
    os.mkfifo(fifo, 0o600)
    oversized = out / "oversized"
    with oversized.open("wb") as f:
        f.truncate(8388608)
    for path in (out / "missing", link, fifo, out, oversized):
        run("refusals", path)
    assert regular.read_bytes() == b"private"
    assert not (out / "native paths 日本語").exists()
    report = dict(schema="amu.macos-cli-host-observation.v1", status="PASS_NATIVE_MACOS_CLI_HOST",
                  compiler=mac.pin(compiler), bootstrap=mac.pin(bootstrap), packager=mac.pin(packager),
                  sources=sources, images={k: mac.pin(v) for k, v in images.items()},
                  calls=calls, manualFD3=False, linuxProcess=False, hostedFallback=False,
                  publicCLIIntegrated=False, independentUserQualified=False)
    (out / "host-service.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], len(calls), "native observations")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    main(p.parse_args().output.resolve())
