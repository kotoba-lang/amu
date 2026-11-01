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
    cli_spec = importlib.util.spec_from_file_location("macos_cli_builder", ROOT / "scripts/seed/build-macos-cli.py")
    cli_builder = importlib.util.module_from_spec(cli_spec)
    cli_spec.loader.exec_module(cli_builder)
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    compiler, bootstrap = macos.root_images()
    build = out / "build"
    build.mkdir(mode=0o700)
    shutil.copyfile(PACKAGER_SOURCE, build / "packager.kotoba")
    packager, _ = macos.build(compiler, bootstrap, build, "packager.kotoba", "packager")
    shutil.copyfile(TEST_SOURCE, build / "fs35.kotoba")
    image, unsigned = macos.build(compiler, packager, build, "fs35.kotoba", "fs35")
    # Package the identical native entry in the explicit app-data-granted
    # amu-program-fs35 profile and in default amu-program (no wire-35 grant).
    # The bundle fixture tests helper placement/dispatch, not locked replay.
    source_bundle = build / "source.bundle"
    source_bundle.write_bytes(b"\x00FS2\x00fs35-runtime-gate")
    mac = macos._mac()
    (build / "fs35-program.kotoba").write_text(
        (build / "fs35.kotoba").read_text().replace(
            '(typed-cap-call :cli/args :string :string "0")',
            '(typed-cap-call :cli/args :string :string "1")'))
    mac.native_run(compiler, build, "compile", "fs35-program.kotoba", "--target", "aarch64-macos", "--output", "fs35-program.kseed")
    extracted = mac.native_run(compiler, build, "extract-native", "fs35-program.kseed", "--symbol", "main", "--output", "fs35-program.raw")
    import re
    match = re.search(rb":offset (\d+), :length (\d+), :arity 0}", extracted.stdout)
    assert match and int(match[2]) == (build / "fs35-program.raw").stat().st_size, extracted.stdout[-300:]
    mac.native_run(packager, build, "fs35-program-unsigned.macho", "fs35-program.raw", "amu-program-fs35", match[1].decode(), "source.bundle")
    program_image = build / "fs35-program.macho"
    mac.sign(build / "fs35-program-unsigned.macho", program_image)
    mac.verify_macho(program_image)
    mac.native_run(packager, build, "fs35-program-ungranted-unsigned.macho", "fs35-program.raw", "amu-program", match[1].decode(), "source.bundle")
    program_ungranted = build / "fs35-program-ungranted.macho"
    mac.sign(build / "fs35-program-ungranted-unsigned.macho", program_ungranted)
    mac.verify_macho(program_ungranted)
    # Negative control: disabling the helper branch leaves the request to the
    # FS2 chain even when the explicit profile is selected.
    source = PACKAGER_SOURCE.read_text()
    hook = '        fs35 (or (string=? mode "fs2-cli-stdio-general") (amu-program-fs35? mode))\n'
    assert source.count(hook) == 1, "FS35 hook drifted"
    (build / "packager-control.kotoba").write_text(source.replace(hook, "        fs35 false\n"))
    packager_control, _ = macos.build(compiler, bootstrap, build, "packager-control.kotoba", "packager-control")
    control, _ = macos.build(compiler, packager_control, build, "fs35.kotoba", "fs35-control")
    mac.native_run(packager_control, build, "fs35-program-control-unsigned.macho", "fs35-program.raw", "amu-program-fs35", match[1].decode(), "source.bundle")
    program_control = build / "fs35-program-control.macho"
    mac.sign(build / "fs35-program-control-unsigned.macho", program_control)
    mac.verify_macho(program_control)
    report = dict(schema="amu.macos-fs35.v1", host=["Darwin", os.uname().machine], compiler=pin(compiler),
                  bootstrapPackager=pin(bootstrap), packagerSource=pin(PACKAGER_SOURCE), testSource=pin(TEST_SOURCE),
                  stagedPackager=pin(packager), image=pin(unsigned), amuProgramFs35Image=pin(build / "fs35-program-unsigned.macho"),
                  amuProgramUngrantImage=pin(build / "fs35-program-ungranted-unsigned.macho"), calls=[])

    def observe(name, img, args, scope_name, expect=None, trap=False, expected_stdout=None):
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
        if expected_stdout is not None:
            assert stdout == expected_stdout, (name, "unexpected program result", stdout)
        assert (outside / "file").read_text() == "outside", (name, "outside file changed")
        assert sorted(x.name for x in outside.iterdir()) == ["file"], (name, "write escaped the scope")
        print(name, p.returncode, flush=True)
        return s

    for case in CASES:
        observe(case, image, [case], case, expect=0)
    for case in CASES:
        observe("amu-program-" + case, program_image, ["amu-program", case], "amu-program-" + case, expect=0, expected_stdout=b"0\n")
    ungranted_scope = observe("amu-program-no-wire35-grant", program_ungranted,
                              ["amu-program", "roundtrip"], "amu-program-ungranted", trap=True)
    assert not (ungranted_scope / "d" / "a").exists(), "default amu-program performed an ungranted write"
    for case in TRAPS:
        observe(case, image, [case], case, trap=True)
    for case in TRAPS:
        observe("amu-program-" + case, program_image, ["amu-program", case], "amu-program-" + case, trap=True)
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
    observe("amu-program-fs35-profile-without-helper", program_control,
            ["amu-program", "roundtrip"], "amu-program-control", trap=True)

    # Exercise the public Amu CLI path that Itonami's locked project builder
    # will use. The explicit profile must package the scoped wire-35 helper;
    # the default profile must keep refusing the same request.
    cli_dir = out / "public-cli"
    cli_builder.build(cli_dir)
    (cli_dir / "amu-full-root.macho").write_bytes(compiler.read_bytes())
    (cli_dir / "kotoba-packager-root.macho").write_bytes(bootstrap.read_bytes())
    (cli_dir / "amu-full-root.macho").chmod(0o755)
    (cli_dir / "kotoba-packager-root.macho").chmod(0o755)
    project = out / "locked-fs35-project"
    project.mkdir(mode=0o700)
    entry = project / "fs35-program.kotoba"
    entry.write_text((build / "fs35-program.kotoba").read_text())
    entry_digest = pin(entry)["sha256"]
    lock = project / "project.ksl"
    lock.write_text(f"KSL2\nentry {entry}\nmodule seed.tests.macos-fs35 {entry}\n"
                    f"file {entry_digest} {entry}\n")
    public_explicit = project / "explicit.macho"
    public_default = project / "default.macho"
    cli = cli_dir / "amu-cli.macho"
    explicit_build = subprocess.run(
        [str(cli), "compile", str(entry), "--source-lock", str(lock),
         "--runtime-profile", "amu-program-fs35", "-o", str(public_explicit)],
        cwd=project, capture_output=True, timeout=180)
    assert explicit_build.returncode == 0, explicit_build.stderr[-800:]
    default_build = subprocess.run(
        [str(cli), "compile", str(entry), "--source-lock", str(lock), "-o", str(public_default)],
        cwd=project, capture_output=True, timeout=180)
    assert default_build.returncode == 0, default_build.stderr[-800:]
    refused_build = subprocess.run(
        [str(cli), "compile", str(entry), "--source-lock", str(lock),
         "--runtime-profile", "unknown-profile", "-o", str(project / "refused.macho")],
        cwd=project, capture_output=True, timeout=30)
    assert refused_build.returncode == 2 and b"usage:" in refused_build.stderr
    mac.verify_macho(public_explicit)
    mac.verify_macho(public_default)
    observe("public-cli-fs35-profile-roundtrip", public_explicit,
            ["amu-program", "roundtrip"], "public-cli-fs35", expect=0,
            expected_stdout=b"0\n")
    # The command profile keeps native CLI semantics: application stdout is
    # preserved and main's signed result is the process status. This matters
    # for Itonami's launcher, which consumes ordinary command exit codes.
    command_project = out / "locked-fs35-command-project"
    command_project.mkdir(mode=0o700)
    command_entry = command_project / "fs35-command.kotoba"
    command_source = (build / "fs35-program.kotoba").read_text()
    command_source = command_source.replace(
        "(:capabilities [:fs/app-data :cli/args])",
        "(:capabilities [:fs/app-data :cli/args :io/write])")
    command_source = command_source.replace(
        ":else 99)))",
        ':else 99)\n    (let [written (typed-cap-call :io/write :string :string "artifact-output\\n")] 7)))')
    command_entry.write_text(command_source)
    command_lock = command_project / "project.ksl"
    command_digest = pin(command_entry)["sha256"]
    command_lock.write_text(f"KSL2\nentry {command_entry}\nmodule seed.tests.macos-fs35 {command_entry}\n"
                           f"file {command_digest} {command_entry}\n")
    command_image = command_project / "command.macho"
    command_build = subprocess.run(
        [str(cli), "compile", str(command_entry), "--source-lock", str(command_lock),
         "--runtime-profile", "amu-command-fs35", "-o", str(command_image)],
        cwd=command_project, capture_output=True, timeout=180)
    assert command_build.returncode == 0, command_build.stderr[-800:]
    mac.verify_macho(command_image)
    observe("public-cli-command-fs35-positive", command_image,
            ["amu-program", "roundtrip"], "public-cli-command-positive", expect=7,
            expected_stdout=b"artifact-output\n")
    command_refusal = observe("public-cli-command-fs35-refusal", command_image,
                              ["amu-program", "trap-read-missing"],
                              "public-cli-command-refusal", trap=True,
                              expected_stdout=b"")
    # A command profile without FS35 is available for Kotoba programs whose
    # declared capabilities are limited to CLI arguments and stdio.
    plain_project = out / "locked-command-project"
    plain_project.mkdir(mode=0o700)
    plain_entry = plain_project / "command.kotoba"
    plain_entry.write_text('(ns command-gate (:export [main]) (:capabilities [:cli/args :io/write]))\n'
                           '(defn main [] :i64 (let [written (typed-cap-call :io/write :string :string "command-output\\n")] 7))\n')
    plain_lock = plain_project / "project.ksl"
    plain_digest = pin(plain_entry)["sha256"]
    plain_lock.write_text(f"KSL2\nentry {plain_entry}\nmodule command-gate {plain_entry}\n"
                          f"file {plain_digest} {plain_entry}\n")
    plain_image = plain_project / "command.macho"
    plain_build = subprocess.run(
        [str(cli), "compile", str(plain_entry), "--source-lock", str(plain_lock),
         "--runtime-profile", "amu-command", "-o", str(plain_image)],
        cwd=plain_project, capture_output=True, timeout=180)
    assert plain_build.returncode == 0, plain_build.stderr[-800:]
    mac.verify_macho(plain_image)
    observe("public-cli-command-no-fs35", plain_image, [], "public-cli-command-no-fs35",
            expect=7, expected_stdout=b"command-output\n")
    default_scope = observe("public-cli-default-no-wire35", public_default,
                            ["amu-program", "roundtrip"], "public-cli-default", trap=True)
    assert not (default_scope / "d" / "a").exists(), "default public CLI profile performed an ungranted write"
    report["publicCli"] = pin(cli)
    report["publicCliSourceLock"] = pin(lock)
    report["publicCliFs35Artifact"] = pin(public_explicit)
    report["publicCliDefaultArtifact"] = pin(public_default)
    report["publicCliCommandFs35Artifact"] = pin(command_image)
    report["publicCliCommandFs35SourceLock"] = pin(command_lock)
    report["publicCliCommandRefusal"] = command_refusal.name
    report["publicCliCommandNoFs35Artifact"] = pin(plain_image)
    report["unknownRuntimeProfileRefused"] = refused_build.returncode == 2

    report["status"] = "PASS_MACOS_FS35"
    (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    main(ap.parse_args().output.resolve())
