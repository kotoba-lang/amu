#!/usr/bin/env python3
"""Stage and observe the independent Linux C comparator, never Amu's closure.

This command requires an explicitly selected C compiler. It cannot compile or
load Kotoba, grant a native CDCI verdict, admit a host, or produce a score.
Only unmodified pinned upstream C inputs enter positive builds. Raw timing
frames are retained as correctness diagnostics, not campaign samples.
"""
import argparse
import hashlib
import json
import os
import platform
import re
import signal
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PACKAGE = HERE.parent / "reproduce-20261015"
UPSTREAM = "09c2ed8c3b7008c95d08b038de4a3f6dc103ed70"
CUSTODY_SHA = "fa0075b0a805e212b7d7671a4fd9f0a8b24cb19c0f68faa3b9371e7ca1e10bec"
BOARD_SHA = "0e58ae7ab3c9f813e4fd7b2738bb60a39c2f3d8da57168b00163c9b7f7cd02c0"
LICENSE_SHA = "3c3099e7c092d71a81f14eae5322365afdb2aae1f3d84ff23a41e4ec0b74176a"
COUNTS_SHA = "c83550918d2125497d5ed75ca5d9a9ff83d509ce87f33dbc33f2ca95678d56c8"
FLAGS = ("-O2", "-std=gnu11", "-DWARMUP_HEAT=1", "-DGLOBAL_SCALE_FACTOR=32768")
MACHINES = {"aarch64": 183, "x86_64": 62}


def require(value, message):
    if not value:
        raise ValueError(message)


def pin_bytes(raw):
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def pin(path):
    return pin_bytes(Path(path).read_bytes())


def unique(pairs):
    result = dict(pairs)
    require(len(result) == len(pairs), "duplicate metadata key")
    return result


def load(path):
    return json.loads(Path(path).read_bytes(), object_pairs_hook=unique)


def read_source(root, relative):
    path = Path(relative)
    require(not path.is_absolute() and path.parts and ".." not in path.parts,
            "bounded source path required")
    current = root
    for part in path.parts:
        current = current / part
        require(not current.is_symlink(), "symlink source input refused")
    require(current.is_file() and current.stat().st_size <= 4 * 1024 * 1024,
            "bounded regular source input required")
    return current.read_bytes()


def source_snapshot(upstream, expected):
    require(len(expected) == 40, "complete40 source custody required")
    actual = {p.relative_to(upstream).as_posix() for sub in ("src", "support")
              for p in (upstream / sub).rglob("*") if p.suffix in (".c", ".h")}
    selected = {p for p in expected if Path(p).suffix in (".c", ".h")}
    require(actual == selected, "extra or missing C/header input")
    result = {name: read_source(upstream, name) for name in sorted(expected)}
    require(all(pin_bytes(raw)["sha256"] == expected[name] for name, raw in result.items()),
            "pinned upstream source differs")
    return result


def elf_record(path, machine):
    raw = Path(path).read_bytes()
    require(len(raw) >= 64 and raw[:7] == b"\x7fELF\x02\x01\x01" and raw[7] in (0, 3),
            "Linux ELF64 little-endian required")
    kind, actual = struct.unpack_from("<HH", raw, 16)
    require(kind in (2, 3) and actual == machine, "C executable ISA differs from selected native host")
    offset = struct.unpack_from("<Q", raw, 32)[0]
    size, count = struct.unpack_from("<HH", raw, 54)
    require(size == 56 and 0 < count <= 128 and offset + count * size <= len(raw),
            "invalid ELF program headers")
    interpreters = []
    for index in range(count):
        at = offset + index * size
        if struct.unpack_from("<I", raw, at)[0] == 3:
            start = struct.unpack_from("<Q", raw, at + 8)[0]
            length = struct.unpack_from("<Q", raw, at + 32)[0]
            require(1 < length <= 4096 and start + length <= len(raw), "invalid ELF interpreter")
            value = raw[start:start + length]
            require(value[-1:] == b"\0" and b"\0" not in value[:-1], "invalid ELF interpreter string")
            interpreters.append(value[:-1].decode("utf-8"))
    require(len(interpreters) <= 1, "multiple ELF interpreters refused")
    return dict(**pin_bytes(raw), machine=actual, elfType=kind,
                interpreter=interpreters[0] if interpreters else None,
                role="c-reference-only-not-kotoba-loader")


def count_bindings(snapshots, registered):
    result = {}
    for row in registered:
        name = row["workload"]
        prefix = "src/" + name + "/"
        factors = [int(match[1]) for path, raw in snapshots.items()
                   if path.startswith(prefix) and path.endswith(".c")
                   for match in re.finditer(rb"#define\s+LOCAL_SCALE_FACTOR\s+(\d+)", raw)]
        require(factors == [row["LSF"]], "C local scale factor differs from registered mapping")
        factor = factors[0]
        require(0 < factor * 32768 < 2147483647 and row["n"] == factor * 8192 * row["multiplier"],
                "registered C/Kotoba scale count differs")
        result[name] = dict(localScaleFactor=factor, globalScaleFactor=32768,
                            cScaleIterations=factor * 32768, kotobaRegisteredCount=row["n"],
                            declaredNormalization=4 / row["multiplier"])
    return result


def correctness(code, stdout, stderr):
    # No timing floor/host-admission assertion: this is a prerequisite probe.
    return type(code) is int and code == 0 and not stderr and re.fullmatch(rb"EMBENCH_NS=[1-9][0-9]*\n", stdout) is not None


def main(args):
    require(platform.system() == "Linux" and platform.machine() == args.expected_arch,
            "explicit native Linux architecture required; no emulation fallback")
    machine = MACHINES[args.expected_arch]
    require(1 <= args.wall_seconds <= 3600, "wall budget must be1..3600 seconds")
    custody_path = PACKAGE / "records/fresh-C/source-custody.json"
    require(pin(custody_path)["sha256"] == CUSTODY_SHA, "source custody pin differs")
    expected = load(custody_path)["sourceHashes"]
    upstream = args.upstream.resolve()
    snapshots = source_snapshot(upstream, expected)
    license_raw = read_source(upstream, "COPYING")
    require(pin_bytes(license_raw)["sha256"] == LICENSE_SHA, "upstream license pin differs")
    speed = json.loads(snapshots["baseline-data/speed.json"], object_pairs_hook=unique)
    counts_path = PACKAGE / "round-sa-m104-20261015/workloads.json"
    require(pin(counts_path)["sha256"] == COUNTS_SHA, "registered count table pin differs")
    registered = load(counts_path)
    names = sorted(row["workload"] for row in registered)
    require(len(names) == 19 and sorted(speed) == names, "full19 workload identity required")
    bindings = count_bindings(snapshots, registered)
    board = (PACKAGE / "c/boardsupport.c").read_bytes()
    require(pin_bytes(board)["sha256"] == BOARD_SHA, "C timing board source pin differs")
    compiler = args.cc.resolve(strict=True)
    require(args.cc.is_absolute(), "explicit absolute C compiler path required")
    compiler_record = elf_record(compiler, machine)
    out = args.out.resolve()
    require(upstream != out and upstream not in out.parents, "output must be outside upstream source")
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    source_root, raw_root, temporary = (out / name for name in ("source", "raw", "tmp"))
    source_root.mkdir(mode=0o700)
    raw_root.mkdir(mode=0o700)
    temporary.mkdir(mode=0o700)
    for relative, raw in snapshots.items():
        destination = source_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        destination.chmod(0o444)
    (source_root / "boardsupport.c").write_bytes(board)
    (source_root / "COPYING").write_bytes(license_raw)
    report = dict(schema="amu.embench.c-reference-preparation.v1", status="running", arm="c-reference",
                  upstreamRevision=UPSTREAM, sourceCustody=pin(custody_path),
                  sources={name: pin_bytes(raw) for name, raw in snapshots.items()},
                  board=pin_bytes(board), license=dict(spdx="GPL-3.0-or-later", **pin_bytes(license_raw)),
                  flags=list(FLAGS), globalScaleFactor=32768, warmupHeat=1,
                  registeredCounts=pin(counts_path),
                  host=dict(os=platform.system(), architecture=platform.machine(), kernel=platform.release()),
                  compiler=dict(path=str(compiler), image=compiler_record), observer=pin(Path(__file__)),
                  calls=[], workloads=[], controls=[], performanceQualified=False, campaignReady=False,
                  nativeVerdictAuthority=False, fullQualification=False,
                  sameAlgorithmQualified=False, protocolNegativeControlsComplete=False,
                  limitations=["C comparator only; never an Amu build/runtime fallback",
                               "preparation observations, not admitted paired samples or a score",
                               "no host-admission, same-algorithm or full protocol-control qualification"])
    environment = dict(PATH="/usr/bin:/bin", LANG="C", LC_ALL="C", TZ="UTC",
                       SOURCE_DATE_EPOCH="1792022400", TMPDIR=str(temporary))
    report["childEnvironment"] = environment
    (out / "observer.py").write_bytes(Path(__file__).read_bytes())

    def save():
        pending = out / "observations.json.tmp"
        pending.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        pending.replace(out / "observations.json")

    def observe(name, argv, timeout):
        try:
            process = subprocess.Popen(list(map(str, argv)), cwd=out, env=environment,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                code = process.returncode
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                stdout, stderr = process.communicate()
                code = "observer-timeout"
        except OSError as error:
            code, stdout, stderr = "launch-error", b"", str(error).encode()
        logs = {}
        for suffix, raw in (("stdout", stdout), ("stderr", stderr)):
            destination = raw_root / (name + "." + suffix)
            destination.write_bytes(raw)
            logs[suffix] = dict(path=destination.relative_to(out).as_posix(), **pin_bytes(raw))
        report["calls"].append(dict(name=name, argv=list(map(str, argv)), exit=code, **logs))
        save()
        return code, stdout, stderr

    save()
    code, version, error = observe("compiler-version", [compiler, "--version"], 30)
    if code != 0 or not version or error:
        report.update(status="C_REFERENCE_PREPARATION_INCOMPLETE", reason="declared C compiler version query failed")
        save()
        return 2
    report["compiler"]["version"] = version.decode("utf-8")
    common = [source_root / "support/main.c", source_root / "support/beebsc.c", source_root / "boardsupport.c"]
    for name in names:
        directory = out / name
        directory.mkdir()
        image = directory / name
        sources = sorted((source_root / "src" / name).glob("*.c"))
        command = [compiler, *FLAGS, "-I", source_root / "support", "-I", source_root / "src" / name,
                   *sources, *common, "-lm", "-o", image]
        row = dict(workload=name, **bindings[name], buildObserved=False, correctnessObserved=False)
        report["workloads"].append(row)
        code, stdout, stderr = observe(name + "-build", command, args.wall_seconds)
        if code == 0 and image.is_file():
            try:
                row["image"] = elf_record(image, machine)
                row["buildObserved"] = True
            except ValueError as error:
                row["reason"] = str(error)
        if row["buildObserved"]:
            code, stdout, stderr = observe(name + "-correctness", [image], args.wall_seconds)
            row["correctnessObserved"] = bool(correctness(code, stdout, stderr))
        save()
        print(name, "C build", row["buildObserved"], "correctness", row["correctnessObserved"], flush=True)

    # Isolate a changed expected value, not a changed timed body or primary input.
    control = out / "wrong-expected-crc32"
    control.mkdir()
    original = snapshots["src/crc32/crc_32.c"]
    require(original.count(b"return 11433 == r;") == 1, "CRC expected-value control anchor differs")
    changed = original.replace(b"return 11433 == r;", b"return 11434 == r;")
    source, image = control / "crc_32.c", control / "crc32"
    source.write_bytes(changed)
    code, stdout, stderr = observe("wrong-expected-build",
        [compiler, *FLAGS, "-I", source_root / "support", source, *common, "-lm", "-o", image], args.wall_seconds)
    detected = False
    control_image = None
    if code == 0 and image.is_file():
        control_image = elf_record(image, machine)
        code, stdout, stderr = observe("wrong-expected-run", [image], args.wall_seconds)
        detected = code == 1 and not stderr and re.fullmatch(rb"EMBENCH_NS=[1-9][0-9]*\n", stdout) is not None
    report["controls"].append(dict(name="wrong-expected-crc32", source=pin_bytes(changed),
                                   image=control_image,
                                   cScaleIterations=bindings["crc32"]["cScaleIterations"],
                                   passed=bool(detected), scope="C verifier exit only, not full protocol gate"))
    report["sourcesStable"] = (all(pin(source_root / name)["sha256"] == expected[name] for name in snapshots)
                               and pin(source_root / "boardsupport.c")["sha256"] == BOARD_SHA)
    report["compilerStable"] = elf_record(compiler, machine) == compiler_record
    report.update(observedBuilds=sum(row["buildObserved"] for row in report["workloads"]),
                  observedCorrectness=sum(row["correctnessObserved"] for row in report["workloads"]))
    okay = (report["observedCorrectness"] == report["observedBuilds"] == 19 and detected
            and report["sourcesStable"] and report["compilerStable"])
    report["status"] = "C_REFERENCE_PREPARATION_OBSERVED" if okay else "C_REFERENCE_PREPARATION_INCOMPLETE"
    save()
    print(report["status"], "no campaign qualification or score", flush=True)
    return 0 if okay else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--cc", required=True, type=Path)
    parser.add_argument("--expected-arch", required=True, choices=tuple(MACHINES))
    parser.add_argument("--wall-seconds", type=int, default=300)
    try:
        raise SystemExit(main(parser.parse_args()))
    except (ValueError, OSError, KeyError, UnicodeError, struct.error) as error:
        print("C_REFERENCE_PREPARATION REJECTED: " + str(error), file=sys.stderr)
        raise SystemExit(2)
