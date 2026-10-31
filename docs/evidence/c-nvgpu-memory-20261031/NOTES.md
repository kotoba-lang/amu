# Route C on nvgpu, step C2: GPU memory from Kotoba (ADR 0375 route C, JUN-712)

An Amu-built static aarch64 image (`--format b2`) prepares memory the GPU can use, with raw system calls only: no
vendor user-space code, no C, no libc and no loader is in the process. Run by `scripts/seed/check-c-nvgpu-memory.py`.

* **Host.** Xavier: Linux 5.10.120-tegra aarch64, L4T R35.4.1 (JetPack 35.4.1). The ioctl numbers and struct offsets
  are those of that kernel's `nvidia/include/uapi/linux/nvmap.h`, `nvidia/include/linux/nvmap.h`,
  `nvgpu/include/uapi/linux/nvgpu-ctrl.h` and `nvgpu-as.h` (see `tools/c/20-nvgpu-memory.kotoba`).
* **Compiler.** `seed/bootstrap/aarch64-linux-static-root.elf` of the base branch (sha256 in `c-nvgpu-memory.json`),
  run on Xavier.
* **Sequence.** `/dev/nvmap`: `NVMAP_IOC_CREATE` (1 MiB), `NVMAP_IOC_ALLOC` (heap IOVMM, write-combine, align 4096),
  `NVMAP_IOC_GET_FD` (a dma-buf fd); two `mmap`s of the dma-buf; a 64-bit pattern written through the first;
  `NVMAP_IOC_READ` of the whole buffer. `/dev/nvgpu/igpu0/ctrl`: `NVGPU_GPU_IOCTL_ALLOC_AS` (no big pages, unified VA,
  [2 MiB, 128 GiB)); `NVGPU_AS_IOCTL_GET_VA_REGIONS`; `NVGPU_AS_IOCTL_MAP_BUFFER_EX` (direct kind control,
  incompressible kind 0, no compression); `NVGPU_AS_IOCTL_UNMAP_BUFFER`; `NVMAP_IOC_FREE`.
* **Result** (`memory.stdout`, exit 0, empty stderr): 0 mismatches of 131072 words through the writing mapping, a
  second CPU mapping and the kernel's read; one VA region at 0x200000 with 4 KiB pages and 0x1fffe00 pages (the
  range asked for); the buffer mapped at GPU VA 0x1fffe00000 (2 MiB aligned, inside the region), page_size returned
  0, flags 0x100 (DIRECT_KIND_CTRL) returned; unmap and free return 0.
* **Oracle** (`oracle.stdout`): the same ioctl sequence from Python (`fcntl.ioctl` and `mmap` through the system's
  libc) gives the same lines byte for byte, including the VA. A comparison only.
* **Negative control** (`negative.stderr`, `negative.stdout`): with the incompressible kind set to NV_KIND_INVALID the
  kernel answers -12 (ENOMEM; the kernel log says "No comptags and no incompressible fallback kind") and the program
  stops with a named refusal (exit 127) after the CPU readbacks and before printing a GPU VA.
* **Not claimed.** That the GPU itself reads or writes the buffer: step C3 (JUN-714) submits work.

Observed on this kernel: `NVMAP_IOC_PARAM` (declared in the header) is not implemented (ENOTTY, "Unknown NVMAP_IOC");
`ALLOC_AS` refuses an all-zero VA range (EINVAL); `MAP_BUFFER_EX` refuses a non-zero `mapping_size` without
`FIXED_OFFSET` (EINVAL, "map_size && non-fixed-mapping!"); every nvmap allocation logs a warning that it carries no
tag (the uapi headers define no tag field, so none is passed).
