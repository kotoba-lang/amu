#!/usr/bin/env python3
"""Observe native value/immutability and the unchanged runtime24 corpus.

Python stages exact sources and observes processes. The Kotoba fixture owns the
copy/value verdict; this does not replace either mandatory native CDCI role or
promote compiler/root/public pins.
"""
import argparse
import hashlib
import json
import platform
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def pin(path):
    data = path.read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def main(a):
    assert platform.system() == "Linux" and platform.machine() in ("x86_64", "aarch64", "arm64")
    target = "x86_64-linux" if platform.machine() == "x86_64" else "aarch64-linux"
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    raw = out / "raw"
    raw.mkdir()
    ledger = []
    build_env = dict(PATH="/nonexistent", KEXE_CAP_RESOURCES_35=str(out), KEXE_STACK_BYTES="8388608")
    guest_env = dict(PATH="/nonexistent", KEXE_ALLOW="-", KEXE_FUEL="1000000",
                     KEXE_STRUCTURED_REPORT="1", KEXE_ARENA_USE="1")
    compilers = {"baseline": a.baseline.resolve(), "candidate": a.compiler.resolve()}
    fixture = ROOT / "seed/tests/native-byte-copy.kotoba"
    cases = json.loads((ROOT / "seed/static-cases.json").read_text())["cases"]
    assert len(cases) == 24
    records = {"copy-fixture": fixture.read_text()}
    records.update({row["name"]: row["source"] for row in cases})
    # Deliberately wrong native value expectation must produce the fixture's
    # negative verdict, not a successful positive check or a build refusal.
    records["copy-wrong-expectation"] = fixture.read_text().replace(
        "want (bit-and (+ (* i 17) 23) 255)", "want (bit-and (+ (* i 17) 24) 255)")
    refused = {
        "bytes-negative": "(bytes-count (bytes-from-vector-i64 [-1]))",
        "bytes-256": "(bytes-count (bytes-from-vector-i64 [256]))",
        "bytes-index-end": "(bytes-at (bytes-from-vector-i64 [0 255]) 2)",
        "bytes-index-negative": "(bytes-at (bytes-from-vector-i64 [0 255]) -1)",
        "bytes-slice-reversed": "(bytes-count (bytes-slice (bytes-from-vector-i64 [0 255]) 2 1))",
    }
    records.update({k: "(ns refused (:export [main]))\n(defn main [] :i64 " + v + ")\n"
                    for k, v in refused.items()})
    observations = {}
    for name, source in records.items():
        observations[name] = {}
        for lane, compiler in compilers.items():
            src, image = out / f"{lane}-{name}.kotoba", out / f"{lane}-{name}.elf"
            src.write_text(source)
            p = subprocess.run([str(compiler), "compile", str(src), "--target", target,
                                "--output", str(image), "--format", "static"],
                               cwd=out, env=build_env, capture_output=True, timeout=180)
            (raw / f"{lane}-{name}-build.stdout").write_bytes(p.stdout)
            (raw / f"{lane}-{name}-build.stderr").write_bytes(p.stderr)
            assert p.returncode == 0 and not p.stderr, (name, lane, p.stdout, p.stderr)
            image.chmod(0o700)
            env = dict(guest_env, KEXE_FUEL="10000000") if name.startswith("copy-") else guest_env
            p = subprocess.run([str(image)], cwd=out, env=env, capture_output=True, timeout=30)
            (raw / f"{lane}-{name}.stdout").write_bytes(p.stdout)
            (raw / f"{lane}-{name}.stderr").write_bytes(p.stderr)
            observations[name][lane] = (p.returncode, p.stdout, p.stderr)
            ledger.append(dict(name=name, lane=lane, source=pin(src), image=pin(image),
                               exit=p.returncode, stdout=pin(raw / f"{lane}-{name}.stdout"),
                               stderr=pin(raw / f"{lane}-{name}.stderr")))
            (out / "calls.json").write_text(json.dumps(ledger, indent=2) + "\n")
        assert observations[name]["baseline"] == observations[name]["candidate"], ("result/fuel/arena drift", name)
        code, stdout, stderr = observations[name]["candidate"]
        if name.startswith("copy-"):
            want = -1 if name == "copy-wrong-expectation" else 42
            assert code == 0 and f":result {want} ".encode() in stdout, (name, code, stdout, stderr)
        elif name in refused:
            assert code == 120 and b"KEXE_TRAP" in stderr, (name, code, stdout, stderr)
        else:
            row = next(row for row in cases if row["name"] == name)
            assert code == row["reference"]["exit"], (name, code)
            if not row["trap"]:
                assert f":result {row['result']} ".encode() in stdout, (name, stdout)
                assert re.search(rb":remaining (\d+)", stdout)[1] == str(row["reference"]["remainingFuel"]).encode()
    report = dict(schema="amu.native-byte-copy-observation.v1", status="PASS_NATIVE_BYTE_COPY_AND_RUNTIME24",
                  host=[platform.system(), platform.machine()], compilers={k: pin(v) for k, v in compilers.items()},
                  fixture=pin(fixture), corpus=pin(ROOT / "seed/static-cases.json"), calls=ledger,
                  identicalResultsFuelAndArena=True, nativeFixturePositive=42, nativeWrongExpectation=-1,
                  runtimeCases=24, extraByteRefusals=len(refused), publicReleaseQualified=False, mandatoryCDCIReplaced=False)
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    main(p.parse_args())
