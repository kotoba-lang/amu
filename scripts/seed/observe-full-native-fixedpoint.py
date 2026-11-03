#!/usr/bin/env python3
"""Stage the complete graph and observe three equal native generations.

This bounded observer does not replace native CDCI, update pins, or qualify a
release. An initial image can differ because its outer runtime was emitted by
the previous producer; retain it and require three equal successor images.
"""
import argparse
import hashlib
import json
import platform
import re
import struct
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def pin(path):
    data = path.read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def main(a):
    assert (platform.system(), platform.machine()) == ("Linux", "x86_64")
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    def read(name):
        if a.source_revision:
            return subprocess.check_output(["git", "show", a.source_revision + ":" + name], cwd=ROOT)
        return (ROOT / name).read_bytes()
    manifest = read("seed/FULL-MANIFEST")
    paths = [p for p in manifest.decode().splitlines() if p and not p.startswith("#")]
    sources = {p: read(p) for p in paths}
    source = out / "full.kotoba"
    source.write_bytes(b"".join(data + b"\n" for data in sources.values()))
    producer = a.bootstrap.resolve()
    bootstrap = pin(producer)
    assert bootstrap["sha256"] == a.bootstrap_sha256
    env = dict(PATH="/nonexistent", KEXE_CAP_RESOURCES_35=str(out), KEXE_STACK_BYTES="8388608")
    rows, equal, previous = [], 0, None
    for generation in range(5):
        image = out / f"G{generation}.elf"
        trace = out / f"G{generation}.execve"
        started = time.monotonic()
        p = subprocess.run(["/usr/bin/strace", "-f", "-e", "trace=execve", "-o", str(trace),
                            str(producer), "compile", str(source), "--target", "x86_64-linux",
                            "--output", str(image), "--format", "static"], cwd=out, env=env,
                           capture_output=True, timeout=1800)
        (out / f"G{generation}.stdout").write_bytes(p.stdout)
        (out / f"G{generation}.stderr").write_bytes(p.stderr)
        assert p.returncode == 0 and not p.stderr, (generation, p.returncode, p.stdout, p.stderr)
        assert len(re.findall(r"execve\(", trace.read_text())) == 1
        data = image.read_bytes()
        assert data[:8] == b"\x7fELF\x02\x01\x01\0" and struct.unpack_from("<HH", data, 16) == (2, 62)
        phoff = struct.unpack_from("<Q", data, 32)[0]
        phsize, count = struct.unpack_from("<HH", data, 54)
        assert phsize == 56 and 0 < count <= 16
        assert all(struct.unpack_from("<I", data, phoff + i * phsize)[0] not in (2, 3) for i in range(count))
        image.chmod(0o700)
        identity = pin(image)
        equal = equal + 1 if identity == previous else 1
        previous = identity
        rows.append(dict(generation=generation, **identity, seconds=time.monotonic() - started,
                         producerSha256=pin(producer)["sha256"]))
        (out / "progress.json").write_text(json.dumps(rows, indent=2) + "\n")
        if equal >= 3:
            break
        producer = image
    assert equal >= 3
    report = dict(nativeLinuxX86=True, threeEqualGenerations=rows[-3:], allGenerations=rows,
                  bootstrap=bootstrap, sourceSha256=pin(source)["sha256"], sourceModuleCount=len(paths),
                  sources={p: dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest()) for p, data in sources.items()},
                  publicReleaseQualified=False, mandatoryCDCIReplaced=False)
    (out / "fixed-point.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_THREE_EQUAL_NATIVE_GENERATIONS", rows[-1]["sha256"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bootstrap", type=Path, required=True)
    p.add_argument("--bootstrap-sha256", required=True)
    p.add_argument("--source-revision")
    p.add_argument("--output", type=Path, required=True)
    main(p.parse_args())
