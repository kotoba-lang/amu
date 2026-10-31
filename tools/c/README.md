# tools/c -- route C on Tegra's nvgpu (ADR 0375 route C, JUN-701)

Route C drives the GPU with no vendor user-space code: an Amu-built image talks to the GPU's kernel driver through
its device nodes and ioctls, builds the command streams itself and (later) runs kernels that Amu compiles to the GPU's
ISA. The owner put route C first on Xavier, with nvgpu as its first vendor (2026-10-31).

The unit is one `(ns g (:export [main]))` line, the files of `MANIFEST` in order (with `@ARCH@` the host's
architecture) and one program file, which the check of that step appends. It reuses route B2's base and arch file (`tools/b2/00-base.kotoba`, `tools/b2/01-arch-*.kotoba`: the
`kxrt-b-` API, system call numbers, messages and named refusals) and is compiled with `--format b2`, whose raw system
calls are what an ioctl needs. Nothing is loaded: no `ld.so`, no libc, no vendor library.

| File | What it holds |
|---|---|
| `10-nvgpu.kotoba` | nvgpu's uapi as used so far: opening a node, the raw ioctl, `NVGPU_GPU_IOCTL_GET_CHARACTERISTICS` and the fields of `struct nvgpu_gpu_characteristics` by offset |
| `20-nvgpu-memory.kotoba` | nvmap (`/dev/nvmap`: create, alloc, dma-buf fd, kernel read, free), CPU mappings of the dma-buf, the GPU address space (alloc, VA regions, map, unmap) |
| `90-nvgpu-probe.kotoba` | step C1 program: print the GPU's characteristics |
| `91-nvgpu-memory.kotoba` | step C2 program: a buffer mapped into the CPU and at a GPU VA, a pattern written and read back |

The interface is the L4T kernel's `include/uapi/linux/nvgpu*.h` and nvmap's `include/uapi/linux/nvmap.h` and
`include/linux/nvmap.h` (JetPack 35.4.1, kernel 5.10.120-tegra; on Xavier under
`/usr/src/linux-headers-5.10.120-tegra-ubuntu20.04_aarch64/nvgpu/` and `.../nvidia/`). nvgpu's ioctls may change with the L4T version.

## Steps (JUN-701)

C1 the characteristics (done); C2 memory: buffers, the GPU address space, CPU mappings (done; GPU-side visibility is
C3's); C3 a channel and a GPFIFO
submission (a semaphore release) with its round trip measured; C4 a compute launch of a hand-encoded SM 7.2 kernel
with the dot gate and its bandwidth; C5 Amu's KIR v2 to SM 7.2 back end; C6 one token of a real model; C7 Murakumo.

## Checks

`scripts/seed/check-c-nvgpu.py`: the probe against an independent oracle (the same ioctl from Python) and a negative
control (a request number the driver refuses). `scripts/seed/check-c-nvgpu-memory.py`: step C2 against an oracle (the
same ioctl sequence from Python) and a negative control (no usable PTE kind, which the driver refuses). nvgpu hosts
only (Xavier).
