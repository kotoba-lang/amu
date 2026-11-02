#!/usr/bin/env python3
"""JUN-593: observe the Mac runtime's legacy wire-35 text requests natively.

The packager under test is rebuilt from the current source by the Mac root and
the descriptor's packager (a staged packager, as a packager change requires).
It packages seed/tests/macos-fs35.kotoba; every case runs in its own process
with FD 3 = a fresh scope. Python stages files, launches processes, and plants
a symlink that points out of the scope; the verdicts come from the native
program's exit code or, for the refusals that must not answer, its trap signal.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("macos_native_image", ROOT / "scripts/seed/macos_native_image.py")
macos = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(macos)
PACKAGER_SOURCE = ROOT / "seed/macos-fs2-runtime-packager.kotoba"
TEST_SOURCE = ROOT / "seed/tests/macos-fs35.kotoba"
CASES = ["roundtrip", "durable", "lock", "paths"]
TRAPS = ["trap-read-missing", "trap-read-link", "trap-write-dotdot", "trap-unknown", "trap-trailing"]


def pin(path):
    raw = Path(path).read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def scope(base, name):
    s = base / name
    s.mkdir(mode=0o700)
    (s / "d").mkdir(mode=0o700)
    outside = base / (name + "-outside")
    outside.mkdir(mode=0o700)
    (outside / "file").write_text("outside")
    os.symlink(outside, s / "link")
    return s, outside


def launch(image, s, args):
    fd = os.open(s, os.O_RDONLY | os.O_DIRECTORY)
    try:
        return subprocess.Popen([str(image), *args], cwd=s, env={"PATH": "/usr/bin:/bin", "LANG": "C"},
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, pass_fds=(3,),
                                preexec_fn=lambda: os.dup2(fd, 3))
    finally:
        os.close(fd)


def main(out):
    assert macos.available(), "Apple Silicon host required"
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    compiler, bootstrap = macos.root_images()
    build = out / "build"
    build.mkdir(mode=0o700)
    shutil.copyfile(PACKAGER_SOURCE, build / "packager.kotoba")
    packager, _ = macos.build(compiler, bootstrap, build, "packager.kotoba", "packager")
    shutil.copyfile(TEST_SOURCE, build / "fs35.kotoba")
    image, unsigned = macos.build(compiler, packager, build, "fs35.kotoba", "fs35")
    # Negative control: a packager whose general mode does not branch to the FS35
    # helper (the one changed binding) leaves the same request to the FS2 chain.
    source = PACKAGER_SOURCE.read_text()
    hook = '        fs35 (string=? mode "fs2-cli-stdio-general")\n'
    assert source.count(hook) == 1, "FS35 hook drifted"
    (build / "packager-control.kotoba").write_text(source.replace(hook, "        fs35 false\n"))
    packager_control, _ = macos.build(compiler, bootstrap, build, "packager-control.kotoba", "packager-control")
    control, _ = macos.build(compiler, packager_control, build, "fs35.kotoba", "fs35-control")
    report = dict(schema="amu.macos-fs35.v1", host=["Darwin", os.uname().machine], compiler=pin(compiler),
                  bootstrapPackager=pin(bootstrap), packagerSource=pin(PACKAGER_SOURCE), testSource=pin(TEST_SOURCE),
                  stagedPackager=pin(packager), image=pin(unsigned), calls=[])

    def observe(name, img, args, scope_name, expect=None, trap=False):
        s, outside = scope(out, scope_name)
        if args and args[0] == "paths":
            (s / "d" / "a").write_text("a")
        p = launch(img, s, args)
        stdout, stderr = p.communicate(timeout=120)
        report["calls"].append(dict(name=name, exit=p.returncode, stderrSHA256=hashlib.sha256(stderr).hexdigest()))
        (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")
        if trap:
            assert p.returncode == -signal.SIGTRAP, (name, p.returncode, stderr[-300:])
        else:
            assert p.returncode == expect, (name, p.returncode, stderr[-300:])
        assert (outside / "file").read_text() == "outside", (name, "outside file changed")
        assert sorted(x.name for x in outside.iterdir()) == ["file"], (name, "write escaped the scope")
        print(name, p.returncode, flush=True)
        return s

    for case in CASES:
        observe(case, image, [case], case, expect=0)
    for case in TRAPS:
        observe(case, image, [case], case, trap=True)
    # Exclusive lock across processes: a holder keeps it, a second process is refused, death releases it.
    s, _ = scope(out, "hold")
    holder = launch(image, s, ["hold"])
    deadline = time.monotonic() + 30
    while not (s / "d" / "ready").exists():
        assert holder.poll() is None and time.monotonic() < deadline, "holder did not take the lock"
        time.sleep(0.01)
    contender = launch(image, s, ["contended"])
    assert contender.wait(timeout=60) == 0, "a second process took a held lock"
    holder.kill()
    holder.wait(timeout=10)
    retry = launch(image, s, ["roundtrip"])
    assert retry.wait(timeout=60) == 0
    after = launch(image, s, ["contended"])
    assert after.wait(timeout=60) == 1, "the lock was not released by process death"
    report["calls"].append(dict(name="cross-process-lock", exit=0))
    # Negative control: without FS35 the legacy request traps instead of answering.
    observe("control-without-fs35", control, ["roundtrip"], "control", trap=True)
    report["status"] = "PASS_MACOS_FS35"
    (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    main(ap.parse_args().output.resolve())
