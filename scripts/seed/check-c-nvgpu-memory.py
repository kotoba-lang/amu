#!/usr/bin/env python3
"""Route C on Tegra's nvgpu, step 2 (ADR 0375 route C, JUN-712 C2): a Kotoba program prepares memory the GPU can use,
talking to the kernel drivers itself. Xavier (or another nvgpu host) only.

The unit tools/c/MANIFEST (route B2's base and arch file, then tools/c) and tools/c/91-nvgpu-memory.kotoba is compiled
with --compiler as a --format b2 image for this host and run. With raw system calls only (no vendor user-space code,
no C, no libc) it allocates a 1 MiB buffer through nvmap (/dev/nvmap: CREATE, ALLOC from IOVMM write-combined,
GET_FD), maps the dma-buf into the CPU, writes a pattern, reads it back through a second CPU mapping and through the
kernel (NVMAP_IOC_READ), creates a GPU address space (NVGPU_GPU_IOCTL_ALLOC_AS on /dev/nvgpu/igpu0/ctrl), lists its
VA regions, maps the buffer at a GPU VA (NVGPU_AS_IOCTL_MAP_BUFFER_EX), unmaps it and frees the handle. Checked, with
the receipt in --output/c-nvgpu-memory.json:
* the image exits 0, every readback has 0 mismatches, the GPU VA is page aligned and inside the address space's VA
  region, and the unmap and free return 0;
* an independent oracle, only to compare: the same ioctl sequence from Python (fcntl.ioctl and mmap through the
  system's libc) prints the same lines (the shape: sizes, readbacks, the VA region and its page size, the VA's
  alignment, the map's page_size and flags); the raw VA of both is recorded, and must agree as well;
* the negative control: the same image with the map's incompressible kind set to NV_KIND_INVALID (no kind at all) is
  refused by the kernel (ENOMEM: no comptags and no incompressible fallback kind) and the program stops with a named
  refusal (exit 127).
That the GPU itself sees the buffer is step C3's (JUN-714); nothing here claims it.

  python3 check-c-nvgpu-memory.py --compiler F.elf --output OUT   (Xavier, as a user who may open /dev/nvmap and ctrl)
"""
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NS = "(ns g (:export [main]))\n"
CTRL = "/dev/nvgpu/igpu0/ctrl"
PROGRAM = "tools/c/91-nvgpu-memory.kotoba"
ORACLE = r'''
import ctypes, fcntl, mmap, os, struct
SIZE, WORDS = 1 << 20, 1 << 17
def io(fd, req, b):
    fcntl.ioctl(fd, req, b, True)
    return b
pat = lambda i: ((i << 32) + 0xA5A5A5A5 - i) & (2**64 - 1)
nv = os.open("/dev/nvmap", os.O_RDWR | os.O_CLOEXEC)
h = struct.unpack_from("<I", io(nv, 0xC0084E00, bytearray(struct.pack("<II", SIZE, 0))), 4)[0]
io(nv, 0x40104E03, bytearray(struct.pack("<IIII", h, 1 << 30, 1, 4096)))
dfd = struct.unpack_from("<i", io(nv, 0xC0084E0F, bytearray(struct.pack("<II", 0, h))), 0)[0]
print("nvmap buffer size 0x100000 heap 0x40000000 flags 0x1")
cpu = mmap.mmap(dfd, SIZE, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
cpu[:] = b"".join(struct.pack("<Q", pat(i)) for i in range(WORDS))
cpu2 = mmap.mmap(dfd, SIZE, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
k = ctypes.create_string_buffer(SIZE)
io(nv, 0x40384E07, bytearray(struct.pack("<QI4xQQQQQ", ctypes.addressof(k), h, 0, SIZE, SIZE, SIZE, 1)))
bad = lambda b: sum(1 for i in range(WORDS) if struct.unpack_from("<Q", b, 8 * i)[0] != pat(i))
print("pattern_words", hex(WORDS))
print("mismatches_cpu_mapping", hex(bad(cpu)))
print("mismatches_second_cpu_mapping", hex(bad(cpu2)))
print("mismatches_kernel_read", hex(bad(k.raw)))
print("last_word", hex(struct.unpack_from("<Q", cpu2, 8 * (WORDS - 1))[0]))
ctrl = os.open("/dev/nvgpu/igpu0/ctrl", os.O_RDWR | os.O_CLOEXEC)
asfd = struct.unpack_from("<i", io(ctrl, 0xC0404708, bytearray(struct.pack("<IiIIQQQ24x", 0, 0, 2, 0, 0x200000, 0x2000000000, 0))), 4)[0]
rb = ctypes.create_string_buffer(8 * 24)
nr = struct.unpack_from("<I", io(asfd, 0xC0104108, bytearray(struct.pack("<QII", ctypes.addressof(rb), 8 * 24, 0))), 8)[0] // 24
print("va_regions", hex(nr))
regions = [struct.unpack_from("<QIIQ", rb.raw, 24 * i) for i in range(nr)]
for i, (off, ps, _, pages) in enumerate(regions):
    print("va_region %d offset %s page_size %s pages %s" % (i, hex(off), hex(ps), hex(pages)))
m = io(asfd, 0xC0284107, bytearray(struct.pack("<IhhIIQQQ", 256, -1, 0, dfd, 0, 0, 0, 0)))
flags, _, _, _, page, _, _, va = struct.unpack("<IhhIIQQQ", m)
print("gpu_va", hex(va))
print("gpu_va_alignment_log2", hex((va & -va).bit_length() - 1))
off, ps, _, pages = regions[0]
print("gpu_va_in_region", hex(int(va >= off and va + SIZE <= off + pages * ps)))
print("map_page_size", hex(page))
print("map_flags", hex(flags))
print("unmap", hex(fcntl.ioctl(asfd, 0xC0084105, bytearray(struct.pack("<Q", va)), True)))
cpu.close(); cpu2.close(); os.close(dfd); os.close(asfd); os.close(ctrl)
print("free", hex(fcntl.ioctl(nv, 0x4E04, h)))
os.close(nv)
'''


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def unit_files(arch):
    return [l.replace("@ARCH@", arch) for l in (ROOT / "tools/c/MANIFEST").read_text().splitlines() if l and not l.startswith("#")] + [PROGRAM]


def main(compiler, output):
    arch = {"aarch64": "aarch64", "arm64": "aarch64", "x86_64": "x86_64"}.get(platform.machine())
    assert platform.system() == "Linux" and arch and Path(CTRL).exists() and Path("/dev/nvmap").exists(), "an nvgpu host (Xavier)"
    output.mkdir(parents=True, exist_ok=False)
    art = output / "artifacts"
    art.mkdir()
    producer = art / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)
    target = "aarch64-linux" if arch == "aarch64" else "x86_64-linux"

    def build(name, text):
        src, img = art / (name + ".kotoba"), art / (name + ".elf")
        src.write_text(text)
        z = subprocess.run([str(producer), "compile", str(src), "--target", target, "--output", str(img), "--format", "b2"],
                           cwd=art, env={"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art)}, capture_output=True, timeout=900)
        assert z.returncode == 0 and not z.stderr and b":format :b2" in z.stdout, (name, z.returncode, z.stderr[-400:])
        img.chmod(0o755)
        return img

    text = NS + "".join((ROOT / f).read_text() + "\n" for f in unit_files(arch))
    img = build("c-nvgpu-memory", text)
    z = subprocess.run([str(img)], env={"PATH": "/usr/bin:/bin"}, capture_output=True, timeout=120)
    (output / "memory.stdout").write_bytes(z.stdout)
    (output / "memory.stderr").write_bytes(z.stderr)
    assert z.returncode == 0 and not z.stderr, (z.returncode, z.stderr[-300:])
    rows = dict(line.split(" ", 1) for line in z.stdout.decode().splitlines())
    for k in ("mismatches_cpu_mapping", "mismatches_second_cpu_mapping", "mismatches_kernel_read", "unmap", "free"):
        assert rows[k] == "0x0", (k, rows[k])
    assert rows["gpu_va_in_region"] == "0x1" and int(rows["gpu_va_alignment_log2"], 16) >= 12, rows
    o = subprocess.run(["python3", "-I", "-c", ORACLE], capture_output=True, timeout=300)
    (output / "oracle.stdout").write_bytes(o.stdout)
    assert o.returncode == 0, o.stderr[-300:]
    assert z.stdout == o.stdout, ("the image and the oracle differ", z.stdout, o.stdout)
    # the negative control: no PTE kind the driver can use
    old = "(def C2-INCOMPR-KIND 0)"
    assert text.count(old) == 1
    bad = build("c-nvgpu-memory-no-kind", text.replace(old, "(def C2-INCOMPR-KIND -1)"))
    n = subprocess.run([str(bad)], env={"PATH": "/usr/bin:/bin"}, capture_output=True, timeout=120)
    (output / "negative.stdout").write_bytes(n.stdout)
    (output / "negative.stderr").write_bytes(n.stderr)
    assert n.returncode == 127 and b"b2: refused: nvgpu: NVGPU_AS_IOCTL_MAP_BUFFER_EX failed: -12" in n.stderr, (n.returncode, n.stderr[-300:])
    assert b"gpu_va " not in n.stdout and b"mismatches_kernel_read 0x0" in n.stdout, n.stdout[-300:]
    report = dict(status="PASS_C_NVGPU_MEMORY", compiler=pin(compiler), image=pin(img),
                  unit={f: pin(ROOT / f) for f in unit_files(arch)}, host=[platform.system(), platform.machine(), platform.release()],
                  devices=["/dev/nvmap", CTRL], memory=rows,
                  negativeControl=dict(change="C2-INCOMPR-KIND 0 -> -1 (NV_KIND_INVALID)", exit=n.returncode,
                                       stderr=n.stderr.decode(errors="replace").strip()[-200:]),
                  oracle="the same ioctl sequence from Python (fcntl.ioctl and mmap through the system libc); compared, not used by the product route",
                  notClaimed="GPU-side visibility of the buffer (step C3, JUN-714)",
                  vendorUserSpaceCode=False, cCompilerOrLoader=False)
    (output / "c-nvgpu-memory.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], "gpu_va", rows["gpu_va"], "region", rows.get("va_region"), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve())
