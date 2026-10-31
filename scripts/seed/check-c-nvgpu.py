#!/usr/bin/env python3
"""Route C on Tegra's nvgpu, step 1 (ADR 0375 route C, JUN-701 C1): a Kotoba program reads the GPU's characteristics
from the kernel driver itself. Xavier (or another nvgpu host) only.

The unit tools/c/MANIFEST (route B2's base and arch file, then tools/c) is compiled with --compiler as a --format b2
image for this host and run. It opens /dev/nvgpu/igpu0/ctrl and issues NVGPU_GPU_IOCTL_GET_CHARACTERISTICS with raw
system calls; no vendor user-space code, no C and no libc is in the process. Checked, with the receipt in
--output/c-nvgpu.json:
* the image exits 0 and prints the characteristics (arch, impl, rev, GPC/TPC counts, L2 size, the compute, GPFIFO
  and copy classes, the SM version, the warp count, the VA width, the chip name);
* an independent oracle, only to compare: the same ioctl from Python (fcntl.ioctl through the system's libc) prints
  the same lines byte for byte;
* the negative control: the same image with the ioctl's request number changed by one bit is refused by the kernel
  and the program stops with a named refusal (exit 127).

  python3 check-c-nvgpu.py --compiler F.elf --output OUT      (Xavier, as a user who may open /dev/nvgpu/igpu0/ctrl)
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
ORACLE = r'''
import fcntl, os, struct, ctypes
fd = os.open("/dev/nvgpu/igpu0/ctrl", os.O_RDWR | os.O_CLOEXEC)
buf = ctypes.create_string_buffer(1024)
arg = bytearray(struct.pack("<QQ", 1024, ctypes.addressof(buf)))
fcntl.ioctl(fd, 0xC0104705, arg, True)
b = buf.raw
print("nvgpu characteristics size", struct.unpack_from("<Q", arg, 0)[0])
for name, off, w in [("arch",0,4),("impl",4,4),("rev",8,4),("num_gpc",12,4),("L2_cache_size",16,8),("num_tpc_per_gpc",32,4),
                     ("big_page_size",40,4),("compute_class",72,4),("gpfifo_class",76,4),("dma_copy_class",84,4),("gpc_mask",88,4),
                     ("sm_arch_sm_version",92,4),("sm_arch_spa_version",96,4),("sm_arch_warp_count",100,4),("gpu_va_bit_count",114,1)]:
    print(name, hex(struct.unpack_from({4:"<I",8:"<Q",1:"<B"}[w], b, off)[0]))
print("chipname", b[152:160].split(b"\0")[0].decode())
'''


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def unit_files(arch):
    return [l.replace("@ARCH@", arch) for l in (ROOT / "tools/c/MANIFEST").read_text().splitlines() if l and not l.startswith("#")]


def main(compiler, output):
    arch = {"aarch64": "aarch64", "arm64": "aarch64", "x86_64": "x86_64"}.get(platform.machine())
    assert platform.system() == "Linux" and arch and Path(CTRL).exists(), "an nvgpu host (Xavier)"
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
    img = build("c-nvgpu-probe", text)
    z = subprocess.run([str(img)], env={"PATH": "/usr/bin:/bin"}, capture_output=True, timeout=120)
    (output / "probe.stdout").write_bytes(z.stdout)
    (output / "probe.stderr").write_bytes(z.stderr)
    assert z.returncode == 0 and not z.stderr, (z.returncode, z.stderr[-300:])
    o = subprocess.run(["python3", "-I", "-c", ORACLE], capture_output=True, timeout=120)
    (output / "oracle.stdout").write_bytes(o.stdout)
    assert o.returncode == 0, o.stderr[-300:]
    assert z.stdout == o.stdout, ("the image and the oracle differ", z.stdout, o.stdout)
    # the negative control: a request number the driver does not know
    old = "(def NVGPU-GPU-IOCTL-GET-CHARACTERISTICS 0xC0104705)"
    assert text.count(old) == 1
    bad = build("c-nvgpu-probe-bad-request", text.replace(old, "(def NVGPU-GPU-IOCTL-GET-CHARACTERISTICS 0xC0104785)"))
    n = subprocess.run([str(bad)], env={"PATH": "/usr/bin:/bin"}, capture_output=True, timeout=120)
    (output / "negative.stderr").write_bytes(n.stderr)
    assert n.returncode == 127 and b"b2: refused: nvgpu: GET_CHARACTERISTICS failed: " in n.stderr, (n.returncode, n.stderr[-300:])
    rows = dict(line.split(" ", 1) for line in z.stdout.decode().splitlines())
    report = dict(status="PASS_C_NVGPU_CHARACTERISTICS", compiler=pin(compiler), image=pin(img),
                  unit={f: pin(ROOT / f) for f in unit_files(arch)}, host=[platform.system(), platform.machine(), platform.release()],
                  device=CTRL, characteristics=rows,
                  negativeControl=dict(request="0xC0104785", exit=n.returncode, stderr=n.stderr.decode(errors="replace").strip()[-200:]),
                  oracle="the same ioctl from Python (fcntl.ioctl through the system libc); compared, not used by the product route",
                  vendorUserSpaceCode=False, cCompilerOrLoader=False)
    (output / "c-nvgpu.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], rows.get("chipname"), "sm", rows.get("sm_arch_sm_version"), "compute", rows.get("compute_class"), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve())
