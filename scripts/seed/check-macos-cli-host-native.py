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
import resource
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
              for case in ("info", "files", "spawn", "refusals", "fds", "timeout", "loop", "write-failure")}
    calls = []

    def run(case, *args, expected=None, inherited=False, alarm=False, file_limit=None, exit_code=0, diagnostic=None):
        # Intentionally no inherited directory FD, external environment or PATH.
        def inherited_setup():
            if inherited:
                os.dup2(secret, 3)
                os.dup2(secret, 91)
            if alarm:
                signal.signal(signal.SIGALRM, signal.SIG_IGN)
                signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
            if file_limit is not None:
                signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
                resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))

        r = subprocess.run([str(images[case]), *map(str, args)], cwd=out,
                           env={"PATH": "/nonexistent", "LANG": "C"},
                           capture_output=True, timeout=20, close_fds=not inherited,
                           preexec_fn=inherited_setup if inherited or alarm or file_limit is not None else None)
        name = f"{len(calls):02d}-{case}"
        (out / (name + ".stdout")).write_bytes(r.stdout)
        (out / (name + ".stderr")).write_bytes(r.stderr)
        assert r.returncode == exit_code, (name, r.returncode, r.stdout, r.stderr)
        if diagnostic is None:
            assert not r.stderr, (name, r.stderr)
        else:
            assert diagnostic in r.stderr, (name, r.stderr)
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
    original = (ROOT / "seed/macos-fs2-runtime-packager.kotoba").read_text()
    partial = out / "partial-write-must-not-remain"
    run("write-failure", partial, "write", file_limit=4, expected=b"PASS_NATIVE_WRITE_FAILURE_CLEANUP\n")
    assert not partial.exists()
    chmod = "(mh-imm 1 384) (mh-sys 124) (mh-b 0x54000002 45)"
    assert original.count(chmod) == 1
    (out / "failed-fchmod.kotoba").write_text(original.replace(chmod,
        "(mh-imm 1 384) (mh-i 0x92800000) (mh-sys 124) (mh-b 0x54000002 45)"))
    failed = build([str(out / "failed-fchmod.kotoba")], "failed-fchmod-packager", bootstrap, "fs2-cli-stdio-general")
    images["failed-fchmod"] = build(["seed/tests/macos-cli-host-write-failure.kotoba", "seed/macos-cli-api.kotoba"], "failed-fchmod", failed, "amu-cli-host")
    run("failed-fchmod", out / "failed-fchmod-must-not-remain", "fchmod", expected=b"PASS_NATIVE_WRITE_FAILURE_CLEANUP\n")
    assert not (out / "failed-fchmod-must-not-remain").exists()
    cleanup = "(mh-label 47) (mh-ldr 0 23 272) (mh-sys 10)"
    assert original.count(cleanup) == 1
    (out / "removed-write-cleanup.kotoba").write_text(original.replace(cleanup,
        "(mh-label 47) (mh-ldr 0 23 272) (mh-i 0xd503201f)"))
    removed = build([str(out / "removed-write-cleanup.kotoba")], "removed-write-cleanup-packager", bootstrap, "fs2-cli-stdio-general")
    images["removed-write-cleanup"] = build(["seed/tests/macos-cli-host-write-failure.kotoba", "seed/macos-cli-api.kotoba"], "removed-write-cleanup", removed, "amu-cli-host")
    run("removed-write-cleanup", partial, "write", file_limit=4, exit_code=3)
    assert partial.read_bytes() == bytes([0, 255, 128, 42])
    partial.unlink()
    no_grant = original.replace("0xf9400a68 0xd2a00209", "0xf9400a68 0xd2800009")
    assert no_grant != original
    (out / "no-grant.kotoba").write_text(no_grant)
    no_grant_packager = build([str(out / "no-grant.kotoba")], "no-grant-packager", bootstrap, "fs2-cli-stdio-general")
    images["denied"] = build(["seed/tests/macos-cli-host-denied.kotoba", "seed/macos-cli-api.kotoba"], "denied", no_grant_packager, "amu-cli-host")
    run("denied", out, images["info"], expected=b"PASS_NATIVE_PROCESS_GRANT_DENIED\n")
    assert not (out / "must-not-exist").exists()
    guard = "(mh-b (bit-or 0xb4000000 8) 91)"
    assert no_grant.count(guard) == 1
    (out / "removed-guard.kotoba").write_text(no_grant.replace(guard, "(mh-i 0xd503201f)"))
    removed = build([str(out / "removed-guard.kotoba")], "removed-guard-packager", bootstrap, "fs2-cli-stdio-general")
    images["removed-guard"] = build(["seed/tests/macos-cli-host-denied.kotoba", "seed/macos-cli-api.kotoba"], "removed-guard", removed, "amu-cli-host")
    run("removed-guard", out, images["info"], exit_code=1)
    assert (out / "must-not-exist").read_bytes() == (str(images["info"]) + "\n").encode()
    close = "(mh-mov 0 8) (mh-sys 6)"
    assert original.count(close) == 1
    (out / "removed-fd-close.kotoba").write_text(original.replace(close, "(mh-i 0xd503201f)"))
    removed = build([str(out / "removed-fd-close.kotoba")], "removed-fd-close-packager", bootstrap, "fs2-cli-stdio-general")
    images["removed-fd-close"] = build(["seed/tests/macos-cli-host-spawn.kotoba", "seed/macos-cli-api.kotoba"], "removed-fd-close", removed, "amu-cli-host")
    (out / "child.stdout").unlink()
    secret = os.open(regular, os.O_RDONLY)
    try:
        os.set_inheritable(secret, True)
        run("removed-fd-close", out, images["fds"], exit_code=1, inherited=True)
    finally:
        os.close(secret)
    assert (out / "child.stdout").read_bytes() == b""
    (out / "bad-abi.kotoba").write_text('(ns bad (:export [main]))\n(defn main [] :i64 (let [s (typed-cap-call :fs/app-data :string :string "anything")] 0))\n')
    images["bad-abi"] = build([str(out / "bad-abi.kotoba")], "bad-abi", packager, "amu-cli-host")
    run("bad-abi", exit_code=70, diagnostic=b"EHOST invalid host ABI")
    report = dict(schema="amu.macos-cli-host-observation.v1", status="PASS_NATIVE_MACOS_CLI_HOST",
                  compiler=mac.pin(compiler), bootstrap=mac.pin(bootstrap), packager=mac.pin(packager),
                  sources=sources, images={k: mac.pin(v) for k, v in images.items()},
                  calls=calls, manualFD3=False, linuxProcess=False, hostedFallback=False,
                  builtExecutedMutants=["removed-process-grant-guard", "removed-child-fd-close", "removed-write-failure-cleanup"],
                  publicCLIIntegrated=False, independentUserQualified=False)
    (out / "host-service.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], len(calls), "native observations")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    main(p.parse_args().output.resolve())
