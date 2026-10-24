# What route B's loader must bring up (ADR 0375, JUN-377)

Route B replaces ld.so with Amu's own loader, so that the static provider can
reach the system Vulkan stack. These files measure that stack on gad:
* Ubuntu 24.04.2, x86_64;
* glibc 2.39-0ubuntu8.9;
* libvulkan1 1.3.275;
* Mesa (`mesa-vulkan-drivers`) 25.2.8, the same version as the B70's;
* libllvm20 20.1.2.

The measurement is read-only. It runs readelf over the `DT_NEEDED` closure of
`libvulkan.so.1` plus one ICD, in the system search order:
* `radv.json`: with `libvulkan_radeon.so` (gad's RADV);
* `anv.json`: with `libvulkan_intel.so` (ANV, the B70's driver).

`*-libc.json` list the glibc symbols that the closure's non-glibc libraries
import, and the `GLIBC_PRIVATE` symbols that glibc's own libraries need from
ld.so. The scripts that wrote them stayed in the run's workspace. The
temporary directories on gad were removed.

## What the closures hold

| | RADV | ANV |
|---|---|---|
| Libraries | 35 (203 MB) | 26 (30 MB) |
| LLVM | libLLVM 20, which pulls in libstdc++, ICU and libxml2 | none |
| Relocations | 376,806 RELATIVE, 23,830 64, 6,090 GLOB_DAT, 3,237 JUMP_SLOT | 13,379 RELATIVE, 3,137 64, 721 GLOB_DAT, 2,070 JUMP_SLOT |
| IRELATIVE | 68 (libc, libm, ld.so) | 68 (the same) |
| TLS | libc, libstdc++, libgcc_s, RADV, libLLVM, libelf; TLSDESC in RADV | libc, libstdc++, libgcc_s |
| `dlopen` callers | libvulkan, libLLVM, libxml2, ICU | libvulkan |
| `pthread_create` callers | the ICD, libLLVM, libzstd, libstdc++, liblzma | the ICD, libzstd, libstdc++ |
| glibc symbols imported | 564, over 26 versions | 404, over 24 versions |

Both ICDs link the X11 and Wayland client libraries (xcb, wayland-client) even
for compute. libstdc++ defines `GNU_UNIQUE` symbols.

## What this means for route B

There are two ways to build the loader.

**B1. Load the real glibc behind a Kotoba ld.so.**
* `libc.so.6` needs 16 `GLIBC_PRIVATE` symbols from ld.so, including:
  * `_rtld_global` and `_rtld_global_ro`;
  * `_dl_allocate_tls` and `_dl_find_dso_for_object`;
  * the tunables.
* `_rtld_global` and `_rtld_global_ro` are internal structures whose layout
  belongs to one glibc build. This is the fragility that ADR 0374 option B
  named.

**B2. Replace glibc with a Kotoba libc.**
* The loader exports glibc's public, versioned ABI to the vendor libraries:
  * 404 symbols for ANV;
  * 564 for RADV.
* These include pthreads, malloc, the `dl*` family, `__tls_get_addr`,
  `dl_iterate_phdr` and `__cxa_thread_atexit_impl`.
* That ABI is stable across glibc versions, because symbol versioning
  exists to keep it so.
* glibc's own libraries are not loaded.

B2 is the narrower and more durable design. ANV is the smaller first target:
no LLVM, 26 libraries, and TLS only in the C and C++ runtimes. RADV adds
libLLVM's closure.
