# Route B2 on aarch64-linux: libvulkan.so.1 through the Kotoba loader (ADR 0375, JUN-701, JUN-377)

An Amu-built static aarch64 image (`--format b2`, seed/80 and seed/77) maps the system `libvulkan.so.1` itself, binds
its libc imports to the libc subset written in Kotoba (`tools/b2`, with `01-arch-aarch64.kotoba`), runs its
initializers and calls `vkEnumerateInstanceVersion` and `vkEnumerateInstanceExtensionProperties`. No `ld.so`, no
glibc and no C source is in the route. No ICD is loaded. This is slice 1 of ADR 0375 on aarch64; it is not a GPU
dispatch, not an ICD and not a qualification of the provider.

## The host

Xavier: Linux 5.10.120-tegra aarch64, Ubuntu 20.04, glibc 2.31 (the oracle only), NVIDIA's
`/usr/lib/aarch64-linux-gnu/tegra/libvulkan.so.1.3.204` (sha256 `d58ba320f2d1…`), one ICD manifest
(`/etc/vulkan/icd.d/nvidia_icd.json`, `libGLX_nvidia.so.0`, not loaded). 4 KiB pages.

## What ran

* **`b2-libvulkan.json`** (`scripts/seed/check-b2-libvulkan.py` on Xavier). The compiler is
  `seed/bootstrap/aarch64-linux-static-root.elf` of this branch's pin commit (sha256 `ef02411b029e…`), which
  compiled the unit there into the image `f7d571ff63a7…`.
  * `vkEnumerateInstanceVersion` → 0, version **1.3.204** (the library file's version);
    `vkEnumerateInstanceExtensionProperties` → 0, 2 extensions: `VK_EXT_debug_report` 10, `VK_EXT_debug_utils` 2.
  * The same two calls through the system's own `ld.so` and glibc (Python ctypes), drivers hidden
    (`VK_DRIVER_FILES` and `VK_ICD_FILENAMES` name a missing file): the same version, count, names and spec versions
    (`oracle.stdout`). A comparison only, not part of the product route.
  * The 64 imports: 58 exported by the image (60 are at `GLIBC_2.17`, aarch64's base version, met by exports at
    `GLIBC_2.17` or older; `pow` is at `GLIBC_2.29`), `stderr` and `__stack_chk_guard` as data objects, three weak
    references bound to 0, and four declared stubs that refuse by name and are not reached: `pow`, `floor`,
    `localtime`, `mktime` ("stubs for unresolved imports: 4").
  * `/proc/self/maps` names the library file for three mappings with the permissions and offsets of its program
    headers (`r-xp` 0, `r--p` 0x89000 = RELRO read-only after relocation, `rw-p` 0x8c000), each at base + its page
    address in the object (the 64 KiB-aligned gap between the segments stays the PROT_NONE reservation).
  * The library has `DT_TEXTREL`: one `R_AARCH64_RELATIVE` lands in its read-execute segment. The loader makes the
    read-only segments writable for the relocations, restores their protection and synchronizes the instruction
    cache over the executable one (`dc cvau` / `ic ivau` from the helper page), as glibc does.
  * The negative control (`run-driver-log.stderr`, `VK_LOADER_DEBUG=error,driver`): the loader finds the NVIDIA
    manifest through the Kotoba `opendir`/`readdir`/`fopen`/`fread` and `dlopen("libGLX_nvidia.so.0")` refuses by name.
* **`b2-image-aarch64.json`**: `scripts/seed/check-b2-image.py --target aarch64-linux`, built on Mac arm64 with a Mac
  compiler from the same seed sources, run on Xavier (8 runs).
* **`b2-image-x86_64.json`, `b2-libc-x86_64.json`**: the x86_64 checks on an x86_64 Linux host (Ubuntu, kernel of the
  murakumo CI box) with `bin/amu-linux-x86_64` of the pin commit: image build and run PASS, libc 396 / 297 / 19 / 67
  checks with every refusal, and the `textrel` fixture now loads (DT_TEXTREL, 20 checks) instead of refusing.

## Not shown

The aarch64 libc tests (`tools/b2/tests/*_t.kotoba` hold x86_64 machine code and system call numbers, and the ELF
fixture is an x86_64 object); TLS (PT_TLS, TLSDESC), the C++ runtime, float arguments (E5) and threads (E3); any ICD
(slice 2); any GPU dispatch. The image runs without a sandbox, as on x86_64.
