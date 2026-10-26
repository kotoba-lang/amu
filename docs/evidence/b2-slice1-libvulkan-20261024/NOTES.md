# Route B2, slice 1: libvulkan.so.1 through the Kotoba loader (ADR 0375, JUN-377)

An Amu-built static x86_64 image (`--format b2`) maps the system `libvulkan.so.1` itself, binds its libc imports to a
libc subset written in Kotoba, runs its initializers and calls `vkEnumerateInstanceVersion` and
`vkEnumerateInstanceExtensionProperties`. There is no `ld.so`, no glibc and no C source in the route: the image's
`PT_LOAD` segments are the only executable code besides the library's own. No ICD is loaded.

## The host

gad: Linux 7.0.0-38-generic x86_64, Ubuntu 24.04, glibc 2.39-0ubuntu8.9 (the oracle only), `libvulkan1`
1.3.275.0-1build1 (`/usr/lib/x86_64-linux-gnu/libvulkan.so.1.3.275`, sha256 `e833b010…`), `mesa-vulkan-drivers`
25.2.8-0ubuntu0.24.04.2 (eight ICD manifests, none loaded).

## What ran (`scripts/seed/check-b2-libvulkan.py`, `b2-libvulkan.json`)

* **The unit.** `tools/b2/MANIFEST` (the loader, the libc subset, the probe), compiled with the complete native x86_64
  compiler `85713104…` into a 475,648-byte static image `895f2069…`. That compiler is the complete x86_64 compiler of
  PR #1558's second head (`--format b2`, main 7eb52a0e merged). #1558 merged as `ca65174c7` with the public image
  `32a10910…` after two more merges of main; the `--format b2` code and the unit are the same, gad was unreachable
  afterwards, and this receipt was not repeated with the merged image. The tests that need no GPU (below) run in CI
  with the merged compiler.
* **The result** (`run-default.stdout`, exit 0):
  * `vkEnumerateInstanceVersion` → result 0, version **1.3.275**, the version of the library file;
  * `vkEnumerateInstanceExtensionProperties` → result 0, 4 extensions: `VK_EXT_debug_report` 10, `VK_EXT_debug_utils` 2,
    `VK_KHR_portability_enumeration` 1, `VK_LUNARG_direct_driver_loading` 1.
* **The library is file-backed.** `/proc/self/maps` names `libvulkan.so.1.3.275` for five mappings, with the permissions
  and file offsets of its program headers (`r--p` 0, `r-xp` 0x6000, `r--p` 0x52000, `r--p` 0x7b000 (the RELRO page,
  read-only after relocation), `rw-p` 0x7c000). The script derives the expected rows from the file.
* **The imports.** libvulkan imports 61 symbols (parsed from its section headers, with the versions from verneed):
  56 are exported by the image at the version the library requires, 3 are weak references bound to 0
  (`__gmon_start__`, `_ITM_deregisterTMCloneTable`, `_ITM_registerTMCloneTable`), `stderr` is a data object of the image,
  and `pow` is a stub that refuses by name when called (`b2: refused: unimplemented import pow ...`). It was not
  reached. The image reports one stub (`stubs for unresolved imports: 1`).
* **The oracle** (comparison only, not part of the route): the same two calls through the system's own `ld.so` and glibc
  (Python ctypes, `oracle.stdout`) with the drivers hidden (`VK_DRIVER_FILES` names a file that does not exist) give the
  same version, the same four extensions and the same spec versions as the image, both under the default environment
  and under the same hidden-driver environment (`run-no-icd.stdout`). Under the system's loader and the default
  environment, the ICDs load and the list has 24 extensions; the image has no ICD, so it matches the hidden-driver case.
* **No ICD is loaded.** `run-driver-log.stderr` (`VK_LOADER_DEBUG=error,driver`) shows the loader finding the eight
  manifests (`virtio`, `intel_hasvk`, `radeon`, `intel`, `gfxstream`, `lvp`, `asahi`, `nouveau`) and reading them, which
  exercises the Kotoba `opendir`, `readdir`, `fopen`, `fseek`, `ftell`, `fread`, `sscanf` and `snprintf`, and then
  `dlopen` of each driver answering through `dlerror`: `cannot open shared object file: not loaded by this loader (route
  B2 slice 1 loads no ICD)`.

## The libc and loader tests (`scripts/seed/check-b2-libc.py`, `b2-libc.json`; CI runs them, no GPU needed)

* `string_t` (396 checks), `printf_t` (297), `libc_t` (67) and `elf_t` (19) pass, and 36 refusal runs end in the named
  exit.
* `elf_t` loads a shared object written by hand (`scripts/seed/b2_fixture.py`, a test fixture): two `PT_LOAD`
  segments, a zero tail where the file has `0xAA` bytes, RELATIVE, `R_X86_64_64`, GLOB_DAT and JUMP_SLOT relocations,
  versioned imports, a weak import, an import nothing implements, a 3-bucket GNU hash, `DT_INIT` and `DT_INIT_ARRAY`,
  `dlopen`/`dlsym`, RELRO; and ten variants the loader must refuse by name (ET_EXEC, `PT_TLS`, IRELATIVE, an unknown
  relocation, a missing `DT_NEEDED`, TEXTREL, RELR, a symbol version this image does not have, a file that is not ELF,
  a file shorter than a header). `readelf -d` and `-l` on gad read the fixture's headers.

## What this does not show

* Only the loader library is loaded: no ICD, no TLS (libstdc++, libgcc_s), no `IRELATIVE`, no floating-point
  arguments (`pow` is a stub), no threads, no dependency loaded from disk. Each of these refuses by name.
* No sandbox is installed in this image: the library's code runs with the process's authority. The provider confines
  itself after device creation (ADR 0371 Decision 5); that is slice 4.
* `dlopen` answers only for objects already loaded, so the Vulkan loader cannot reach an ICD at all.
* The stub page for unresolved imports is mapped read-write and its code slots are read-execute except while a stub is
  written.

The temporary directories on gad (`/tmp/claude-b2-slice1`) were removed after the runs.
