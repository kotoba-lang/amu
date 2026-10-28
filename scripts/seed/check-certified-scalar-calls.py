#!/usr/bin/env python3
"""Certified scalar calls: OFF/ON paired controls through the C-free aarch64 runner.

Port of the script retired with the C loader (scripts/seed/RETIRED.md). Run it
on arm64 Linux after selfhost-bootstrap.py (--bootstrap is that output, which
holds the aarch64 runner R-aarch64.elf and the adopted fixed-point image
G3.bin). Both producers (the pre-optimization OFF bootstrap and the adopted
ON image) compile seed/tests/certified-scalar-calls/controls.kotoba through
the runner; the payloads must equal the pinned native-structure.json. Each of
the 54 cases then runs on both payloads with its argument: result, fuel and
the KEXE_ARENA_USE line must be raw-identical between OFF and ON.

Arena fields are the runner's (seed/76-77): peaks equal final use, and the
growth-region fields are 0, unlike the removed loader's.
"""
import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "seed/tests/certified-scalar-calls"
OFF = ROOT / "docs/evidence/certified-scalar-calls-20261013/previous-lookup-bootstrap.bin"
FIELDS = {"pairs", "string-pool-bytes", "vectors", "vector-items", "heap-bytes", "conj", "conj-tail", "conj-region",
          "conj-copy", "copied-words", "reserved-words", "regions", "scope-releases", "string-regions",
          "string-region-appends", "string-copied-bytes", "string-reserved-bytes"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(boot, out):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "arm64")
    out.mkdir(parents=True, exist_ok=False)
    structure = json.loads((FIXTURE / "native-structure.json").read_text())
    cases = json.loads((FIXTURE / "cases.json").read_text())
    assert len(cases) == 54
    assert sha(FIXTURE / "controls.kotoba") == structure["sourceSHA256"] and sha(FIXTURE / "cases.json") == structure["casesSHA256"]
    adoption = json.loads((ROOT / "seed/adoption-20261022.json").read_text())
    runner = out / "R-aarch64.elf"
    shutil.copy2(boot / "R-aarch64.elf", runner)
    runner.chmod(0o755)
    source = out / "controls.kotoba"
    shutil.copy2(FIXTURE / "controls.kotoba", source)
    producers = {"OFF": out / "OFF-producer.bin", "ON": out / "ON-producer.bin"}
    shutil.copy2(OFF, producers["OFF"])
    shutil.copy2(boot / "G3.bin", producers["ON"])
    assert sha(producers["OFF"]) == "09ee805e5f0feef246922026023e75d7d92e4531245466c9827883ff5baf9f62"
    assert sha(producers["ON"]) == adoption["nativeImageSHA256"]
    env = {"PATH": "/usr/bin:/bin", "KEXE_COMMAND": "1", "KEXE_CAP_RESOURCES_35": str(out), "KEXE_STACK_BYTES": "8388608"}
    calls = []

    def run(argv, name, e, check=True):
        z = subprocess.run(list(map(str, argv)), cwd=out, env=e, capture_output=True, timeout=1800)
        (out / (name + ".stdout")).write_bytes(z.stdout)
        (out / (name + ".stderr")).write_bytes(z.stderr)
        calls.append(dict(name=name, exit=z.returncode))
        if check:
            assert z.returncode == 0, (name, z.returncode, z.stderr[-400:])
        return z

    arms = {}
    for tag, producer in producers.items():
        container, native = out / (tag + ".kseed"), out / (tag + ".bin")
        prefix = [runner, producer, 0, 0, "aarch64", "35,37,38,39", "--"]
        z = run(prefix + ["compile", source, "--target", "aarch64-macos", "--output", container], tag + "-compile", env)
        assert not z.stderr
        z = run(prefix + ["extract-native", container, "--symbol", "pure-chain", "--output", native], tag + "-extract", env)
        assert not z.stderr
        head, payload = container.read_bytes().split(b"\n\n", 1)
        lines = head.decode().splitlines()
        exports = {n: [int(p), int(a)] for n, p, a in map(str.split, lines[1:])}
        assert lines[0] == f"KSEED1 {len(payload)} {len(exports)}" and payload == native.read_bytes()
        assert dict(bytes=len(payload), sha256=sha(native), exports=exports) == structure[tag], (tag, "payload differs from the pinned structure")
        arms[tag] = (native, exports)
    guest = {"PATH": "/usr/bin:/bin", "KEXE_ARENA_USE": "1", "KEXE_STRUCTURED_REPORT": "1", "KEXE_FUEL": "100000",
             "KEXE_STACK_BYTES": "8388608"}
    rows = []
    for i, c in enumerate(cases):
        pair = []
        for tag, (native, exports) in arms.items():
            offset, arity = exports[c["symbol"]]
            assert arity == 1
            z = run([runner, native, offset, 1, "aarch64", "37", c["x"]], f"{i:02d}-{tag}", guest)
            m = re.search(rb":status :ok :result (-?\d+)", z.stdout)
            assert m and int(m[1]) == c["result"], (i, tag, z.stdout)
            f = re.search(rb":fuel \{:initial (\d+) :remaining (\d+)\}", z.stdout)
            assert f and int(f[1]) == 100000 and 0 <= int(f[2]) <= 100000
            arena = re.findall(rb"^KEXE_ARENA_USE.*$", z.stderr, re.M)
            assert len(arena) == 1
            fields = {k.decode(): int(v) for k, v in re.findall(rb":([a-z-]+) (\d+)", arena[0])}
            assert set(fields) == FIELDS
            pair.append((z.stdout, z.stderr))
        assert pair[0] == pair[1], ("EXACT_RAW_FUEL_ARENA_MISMATCH", i)
        rows.append(dict(case=i, symbol=c["symbol"], result=c["result"],
                         remainingFuel=int(re.search(rb":remaining (\d+)", pair[0][0])[1])))
    report = dict(status="PASS_CERTIFIED_SCALAR_CALL_54_OFF_ON_EXACT_THROUGH_C_FREE_RUNNER", pairs=54, guestCalls=108,
                  compilerCalls=4, runner=dict(bytes=runner.stat().st_size, sha256=sha(runner)),
                  producers={t: sha(p) for t, p in producers.items()},
                  payloads={t: structure[t]["sha256"] for t in arms}, cases=rows,
                  host=[platform.system(), platform.machine(), platform.release()],
                  cCompilerOrLoader=False, arenaFields="runner (seed/76-77): growth-region fields are 0")
    (out / "certified-scalar-calls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", type=Path, required=True, help="output directory of selfhost-bootstrap.py")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.bootstrap.resolve(), args.output.resolve())
