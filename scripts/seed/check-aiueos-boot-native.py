#!/usr/bin/env python3
"""Native transition packager diagnostics. Python inspects, never packages.

This is a bounded packaging gate, not native CDCI, a full OS boot or K16
qualification. Run the QEMU entry check separately against the emitted pair.
"""
import argparse
import hashlib
import json
import os
import platform
import struct
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from aiueos_native_proof import load_native_producers
ROOT = Path(__file__).resolve().parents[2]


def pin(path):
    b = path.read_bytes()
    return dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())


def verify(efi, kernel, payload):
    pe = struct.unpack_from("<I", efi, 60)[0]
    assert efi[:2] == b"MZ" and pe == 128 and efi[pe:pe + 4] == b"PE\0\0"
    assert struct.unpack_from("<HHIIIHH", efi, pe + 4) == (0x8664, 3, 0, 0, 0, 240, 0x22)
    opt = pe + 24
    assert struct.unpack_from("<H", efi, opt)[0] == 0x20b
    entry, code, loader_base, alignment, file_alignment = struct.unpack_from("<IIQII", efi, opt + 16)
    assert (entry, code, alignment, file_alignment) == (4096,4096,4096,512)
    assert struct.unpack_from("<HH", efi, opt + 68) == (10, 0x160)
    assert struct.unpack_from("<I", efi, opt + 108)[0] == 16
    image_size, header_size = struct.unpack_from("<II", efi, opt + 56)
    phoff=struct.unpack_from('<Q',kernel,32)[0]
    segments=[struct.unpack_from('<IIQQQQQQ',kernel,phoff+i*56) for i in range(2)]
    choices=[base for base in (0x400000,0x1000000,0x2000000)
             if all(base+image_size<=p[3] or p[3]+p[5]<=base for p in segments)]
    assert choices and loader_base==choices[0], 'loader overlaps a fixed kernel segment'
    assert header_size == 512
    sections = []
    for i, name in enumerate((b".text", b".data", b".reloc")):
        row = struct.unpack_from("<8sIIIIIIHHI", efi, opt + 240 + 40 * i)
        assert row[0].rstrip(b"\0") == name
        size, rva, raw, off = row[1:5]
        assert size > 0 and rva % 4096 == off % 512 == raw % 512 == 0
        assert raw == (size + 511) & -512 and len(efi) >= off + raw
        assert row[5:9] == (0, 0, 0, 0)
        assert row[9] == (0x60000020, 0xc0000040, 0x42000040)[i]
        if sections:
            prev = sections[-1]
            assert rva >= (prev[1] + prev[0] + 4095) & -4096
            assert off == prev[3] + prev[2]
        else:
            assert rva == 4096 and off == 512
        assert not any(efi[off + size:off + raw])
        sections.append((size, rva, raw, off))
    assert len(efi) == sections[-1][2] + sections[-1][3]
    assert image_size == (sections[-1][1] + sections[-1][0] + 4095) & -4096
    for i in range(16):
        directory = struct.unpack_from("<II", efi, opt + 112 + i * 8)
        assert directory == ((sections[2][1], 12) if i == 5 else (0, 0))
    assert efi[sections[2][3]:sections[2][3] + 12] == struct.pack("<III", 0, 12, 0)
    d = efi[sections[1][3]:sections[1][3] + sections[1][0]]
    ph = struct.unpack_from("<Q", kernel, 32)[0]
    rx = struct.unpack_from("<8Q", kernel, ph)
    rw = struct.unpack_from("<8Q", kernel, ph + 56)
    assert struct.unpack_from("<4Q", d) == (rx[3], rw[3], 0x544f4f4245554941, 5)
    assert not any(d[32:72])
    assert struct.unpack_from("<5Q", d, 72) == ((rx[3] + rx[5] + 4095) & -4096,
                                               rw[3], rw[3] + rw[5], 0, 15)
    assert not any(d[112:16560])
    assert d[16560:16560 + len(payload)] == payload
    ko = (16560 + len(payload) + 15) & -16
    assert d[ko:ko + len(kernel)] == kernel
    assert efi.count(kernel) == 1
    guid = (ko + len(kernel) + 7) & -8
    assert not any(d[16560 + len(payload):ko]) and not any(d[ko + len(kernel):guid])
    assert d[guid:] == bytes.fromhex("dea94290dc23384a96fb7aded080516a") + bytes(8)
    assert bytes.fromhex("41ff9640010000") in efi[512:512 + sections[0][0]]
    return dict(sections=sections, embeddedKernelOffset=sections[1][3] + ko)


def main(build, output, complete=None):
    source_graph, producers, _ = load_native_producers(build, complete)
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for producer in producers:
        scope = output / producer.stem
        scope.mkdir()
        env = dict(os.environ, KEXE_CAP_RESOURCES_35=str(scope), KEXE_STACK_BYTES="8388608")
        src, kernel = scope / "kernel.kotoba", scope / "KERNEL.ELF"
        src.write_text("(ns boot-entry (:export [main]))\n(defn main [] :i64 42)\n")
        cmd = [str(producer), "compile", str(src), "--target", "x86_64-aiueos-kernel-v1",
               "--artifact", "image", "--output", str(kernel), "--fuel", "1024"]
        r = subprocess.run(cmd, env=env, capture_output=True, timeout=120)
        assert r.returncode == 0 and kernel.exists(), (r.returncode, r.stderr)
        blob = kernel.read_bytes()
        commands, positive, refused = [], {}, []

        def package(name, k=kernel, payload=None, extra=(), sentinel=None):
            dst = scope / (name + ".EFI")
            if sentinel is not None:
                dst.write_bytes(sentinel)
            cmd = [str(producer), "package-aiueos-boot", str(k), "--output", str(dst)]
            if payload is not None:
                cmd += ["--payload", str(payload)]
            cmd += list(extra)
            r = subprocess.run(cmd, env=env, capture_output=True, timeout=120)
            commands.append(dict(name=name, exit=r.returncode, stdout=r.stdout.decode(), stderr=r.stderr.decode()))
            return dst, r

        for name, payload in (("plain", b""), ("payload", b"native payload\x00\xff"), ("payload-max", bytes(524288))):
            path = scope / (name + ".bin")
            path.write_bytes(payload)
            dst, r = package(name, payload=path if payload else None)
            assert r.returncode == 0 and not r.stderr, (name, r.returncode, r.stderr)
            verify(dst.read_bytes(), blob, payload)
            positive[name] = pin(dst)
        bads = [("magic", 0, "<I", 0), ("class", 4, "<B", 1), ("type", 16, "<H", 1),
                ("machine", 18, "<H", 183), ("phnum", 56, "<H", 3), ("phoff", 32, "<Q", 2**64 - 1),
                ("phalign", 32, "<Q", 65), ("entry", 24, "<Q", 0x108000),
                ("rwx", 68, "<I", 7), ("zero-size", 96, "<Q", 0), ("memory-size", 104, "<Q", 999999),
                ("high-address", 88, "<Q", 0x40000000), ("unaligned", 88, "<Q", 0x101001),
                ("file-offset", 72, "<Q", len(blob)), ("overlap", 144, "<Q", 0x101000)]
        for name, off, fmt, value in bads:
            bad = bytearray(blob)
            struct.pack_into(fmt, bad, off, value)
            if name == "overlap":
                # Keep p_vaddr == p_paddr so this exercises the overlap
                # predicate, rather than failing the segment's alias check.
                struct.pack_into("<Q", bad, 136, value)
            path = scope / (name + ".ELF")
            path.write_bytes(bad)
            dst, r = package("bad-" + name, path)
            assert r.returncode != 0 and not dst.exists(), (name, r.stdout, r.stderr)
            refused.append(name)
        for name, data in (("empty", b""), ("short", blob[:100])):
            path = scope / (name + ".ELF")
            path.write_bytes(data)
            dst, r = package("bad-" + name, path)
            assert r.returncode != 0 and not dst.exists(), (name, r.stdout, r.stderr)
            refused.append(name)
        payload = scope / "too-large.bin"
        payload.write_bytes(bytes(524289))
        dst, r = package("too-large", payload=payload)
        assert r.returncode != 0 and not dst.exists()
        refused.append("payload-too-large")
        for flag in ("--resident", "--k16-preflight", "--jvm-free"):
            dst, r = package("bad-" + flag[2:], extra=(flag,))
            assert r.returncode != 0 and not dst.exists()
            refused.append(flag)
        dst, r = package("existing", sentinel=b"preserve")
        assert r.returncode != 0 and dst.read_bytes() == b"preserve"
        refused.append("existing-output")
        (scope / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        rows.append(dict(producer=pin(producer), kernel=pin(kernel), artifacts=positive, refusals=refused))
    assert rows[0]["kernel"] == rows[1]["kernel"] and rows[0]["artifacts"] == rows[1]["artifacts"]
    report = dict(status="PASS_NATIVE_AIUEOS_BOOT_PACKAGING", source=source_graph, routes=rows,
                  host=[platform.system(), platform.machine()], cCompilerOrLoader=False, JVMNodeOrGraalFallback=False,
                  nativeCDCI=False, completeKernel=False, qemuBoot=False, gpt=False, resident=False, k16Tender=False)
    (output / "native-boot.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], sum(len(r["artifacts"]) for r in rows), "EFI images; QEMU entry gate separate")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--build", type=Path)
    group.add_argument("--complete", type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    main(a.build.resolve() if a.build else None, a.output.resolve(), a.complete.resolve() if a.complete else None)
