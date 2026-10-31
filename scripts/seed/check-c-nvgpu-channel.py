#!/usr/bin/env python3
"""JUN-714 C3: qualify a native nvgpu semaphore submission on Xavier.

Run on the nvgpu host with the Amu-built aarch64 Linux static compiler. The
Python ioctl path is an independent measurement oracle, never product code.
"""
import argparse
import hashlib
import json
import platform
import statistics
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROGRAM = "tools/c/92-nvgpu-channel.kotoba"
NS = "(ns g (:export [main]))\n"
ORACLE = r'''
import ctypes, fcntl, mmap, os, struct, time

def io(fd, req, data):
    fcntl.ioctl(fd, req, data, True)
    return data

size, sem_off = 0x100000, 0x1000
nv = os.open('/dev/nvmap', os.O_RDWR | os.O_CLOEXEC)
h = struct.unpack_from('<I', io(nv, 0xC0084E00, bytearray(struct.pack('<II', size, 0))), 4)[0]
io(nv, 0x40104E03, bytearray(struct.pack('<IIII', h, 0x40000000, 1, 4096)))
dfd = struct.unpack_from('<i', io(nv, 0xC0084E0F, bytearray(struct.pack('<II', 0, h))))[0]
cpu = mmap.mmap(dfd, size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
ctrl = os.open('/dev/nvgpu/igpu0/ctrl', os.O_RDWR | os.O_CLOEXEC)
charbuf = ctypes.create_string_buffer(1024)
io(ctrl, 0xC0104705, bytearray(struct.pack('<QQ', 1024, ctypes.addressof(charbuf))))
compute, gpfifo = struct.unpack_from('<II', charbuf.raw, 72)
assert gpfifo == 0xC36F
asfd = struct.unpack_from('<i', io(ctrl, 0xC0404708, bytearray(struct.pack('<IiIIQQQ24x', 0, 0, 2, 0, 0x200000, 0x2000000000, 0))), 4)[0]
m = io(asfd, 0xC0284107, bytearray(struct.pack('<IhhIIQQQ', 256, -1, 0, dfd, 0, 0, 0, 0)))
va = struct.unpack_from('<Q', m, 32)[0]
tsg = struct.unpack_from('<i', io(ctrl, 0xC0084709, bytearray(8)))[0]
ch = struct.unpack_from('<i', io(ctrl, 0xC004470B, bytearray(struct.pack('<i', -1))))[0]
io(asfd, 0xC0044101, bytearray(struct.pack('<i', ch)))
io(tsg, 0x40045401, bytearray(struct.pack('<i', ch)))
io(ch, 0xC010486C, bytearray(struct.pack('<IIQ', compute, 0, 0)))
bind = bytearray(80)
struct.pack_into('<I', bind, 0, 1024)
struct.pack_into('<ii', bind, 12, -1, -1)
io(ch, 0xC0504880, bind)
print('gpfifo_class', hex(gpfifo))
print('compute_class', hex(compute))
print('gpu_va', hex(va))
print('channel_setup', hex(0))
for i in range(1, 17):
    payload = 0x51430000 + i
    struct.pack_into('<I', cpu, sem_off, 0)
    # The method address field is in dwords; method 0x5c becomes 0x17.
    struct.pack_into('<6I', cpu, 0, (1 << 29) | (5 << 16) | (0x5c >> 2),
                     (va + sem_off) & 0xfffffffc, ((va + sem_off) >> 32) & 0xff,
                     payload, 0, 0x100001)
    gp = ctypes.create_string_buffer(struct.pack('<II', va & 0xfffffffc, ((va >> 32) & 0xff) | (6 << 10)))
    arg = bytearray(struct.pack('<QIIII', ctypes.addressof(gp), 1, 0, 0, 0))
    start = time.monotonic_ns()
    io(ch, 0xC018486B, arg)
    while struct.unpack_from('<I', cpu, sem_off)[0] != payload:
        if time.monotonic_ns() - start > 1_000_000_000:
            raise TimeoutError('oracle semaphore release')
    elapsed = time.monotonic_ns() - start
    print('semaphore', hex(struct.unpack_from('<I', cpu, sem_off)[0]))
    print('rt_ns', hex(elapsed))
io(asfd, 0xC0084105, bytearray(struct.pack('<Q', va)))
print('unmap', hex(0))
for fd in (ch, tsg, asfd, ctrl): os.close(fd)
cpu.close(); os.close(dfd)
fcntl.ioctl(nv, 0x4E04, h)
print('free', hex(0))
os.close(nv)
'''


def pin(path):
    b = Path(path).read_bytes()
    return {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}


def unit_files():
    return [line.replace("@ARCH@", "aarch64") for line in
            (ROOT / "tools/c/MANIFEST").read_text().splitlines()
            if line and not line.startswith("#")] + [PROGRAM]


def parse(data):
    rows = [line.split(" ", 1) for line in data.decode().splitlines()]
    timings = [int(v, 16) for k, v in rows if k == "rt_ns"]
    stable = [(k, v) for k, v in rows if k not in ("rt_ns", "gpu_va")]
    return stable, timings, dict(rows)


def main(compiler, output):
    assert platform.system() == "Linux" and platform.machine() == "aarch64"
    assert Path("/dev/nvgpu/igpu0/ctrl").exists() and Path("/dev/nvmap").exists()
    output.mkdir(parents=True, exist_ok=False)
    artifacts = output / "artifacts"
    artifacts.mkdir()
    producer = artifacts / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)
    source = NS + "".join((ROOT / f).read_text() + "\n" for f in unit_files())

    def build(name, text):
        src, img = artifacts / (name + ".kotoba"), artifacts / (name + ".elf")
        src.write_text(text)
        cp = subprocess.run([str(producer), "compile", str(src), "--target", "aarch64-linux",
                             "--output", str(img), "--format", "b2"], cwd=artifacts,
                            env={"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(artifacts)},
                            capture_output=True, timeout=900)
        assert cp.returncode == 0 and b":format :b2" in cp.stdout, (name, cp.returncode, cp.stderr[-400:])
        img.chmod(0o755)
        return img

    img = build("c3", source)
    result = subprocess.run([str(img)], capture_output=True, timeout=45)
    (output / "native.stdout").write_bytes(result.stdout)
    (output / "native.stderr").write_bytes(result.stderr)
    assert result.returncode == 0 and not result.stderr, (result.returncode, result.stderr[-400:])
    stable, native_ns, native = parse(result.stdout)
    assert len(native_ns) == 16 and all(0 < x < 1_000_000_000 for x in native_ns)
    assert native["unmap"] == native["free"] == "0x0"

    oracle = subprocess.run(["python3", "-I", "-c", ORACLE], capture_output=True, timeout=45)
    (output / "oracle.stdout").write_bytes(oracle.stdout)
    (output / "oracle.stderr").write_bytes(oracle.stderr)
    assert oracle.returncode == 0, oracle.stderr[-400:]
    oracle_stable, oracle_ns, oracle_rows = parse(oracle.stdout)
    assert stable == oracle_stable, (stable, oracle_stable)
    assert int(native["gpu_va"], 16) > 0 and int(oracle_rows["gpu_va"], 16) > 0

    before = "(def C3-GPFIFO-ENTRIES 1024)"
    assert source.count(before) == 1
    bad = build("c3-invalid-ring", source.replace(before, "(def C3-GPFIFO-ENTRIES 3)"))
    negative = subprocess.run([str(bad)], capture_output=True, timeout=45)
    (output / "negative.stdout").write_bytes(negative.stdout)
    (output / "negative.stderr").write_bytes(negative.stderr)
    assert negative.returncode == 127 and b"NVGPU_IOCTL_CHANNEL_SETUP_BIND failed" in negative.stderr
    assert b"semaphore " not in negative.stdout

    report = {"status": "PASS_C3_NVGPU_CHANNEL", "host": [platform.system(), platform.machine(), platform.release()],
              "compiler": pin(compiler), "image": pin(img), "unit": {f: pin(ROOT / f) for f in unit_files()},
              "native_ns": native_ns, "oracle_ns": oracle_ns,
              "native_median_ns": statistics.median(native_ns), "oracle_median_ns": statistics.median(oracle_ns),
              "negative": {"change": "C3-GPFIFO-ENTRIES 1024 -> 3", "exit": negative.returncode},
              "oracle": "independent Python fcntl.ioctl and mmap, measurement only; no vendor user-space product code",
              "not_claimed": "Vulkan comparison or C4 compute launch"}
    (output / "c3.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], report["native_median_ns"], report["oracle_median_ns"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    main(args.compiler.resolve(), args.output.resolve())
