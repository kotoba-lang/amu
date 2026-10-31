# Route C on nvgpu, step C1: the GPU's characteristics from Kotoba (ADR 0375 route C, JUN-701)

An Amu-built static aarch64 image (`--format b2`) opens `/dev/nvgpu/igpu0/ctrl` and issues
`NVGPU_GPU_IOCTL_GET_CHARACTERISTICS` with raw system calls. No vendor user-space code, no C, no libc and no loader is
in the process. This is the first step of route C; it allocates no GPU memory and submits no work.

* **Host.** Xavier: Linux 5.10.120-tegra aarch64, JetPack 35.4.1 (nvgpu uapi from that kernel's headers).
* **Compiler.** `seed/bootstrap/aarch64-linux-static-root.elf` of amu#1734 (sha256 in `c-nvgpu.json`), run on Xavier.
* **Result** (`probe.stdout`, exit 0): chip `gv11b`, arch 0x150, impl 0xb, rev 0xa2, 1 GPC (mask 0x1) with 4 TPCs,
  L2 512 KiB, compute class 0xc3c0 (VOLTA_COMPUTE_A), GPFIFO class 0xc36f, copy class 0xc3b5, SM 7.2 (0x702) for
  both the SM and the instruction set, 128 warps, a 40-bit GPU VA; the kernel reports a 312-byte structure.
* **Oracle** (`oracle.stdout`): the same ioctl from Python (`fcntl.ioctl` through the system's libc) gives the same
  lines byte for byte. A comparison only.
* **Negative control** (`negative.stderr`): with the request number changed by one bit the kernel answers -22
  (EINVAL) and the program stops with a named refusal (exit 127).
