# tools/b2 -- route B2: the Kotoba loader and libc subset (ADR 0375, JUN-377)

Route B2 loads the platform's GPU stack with an Amu-built program instead of the system's `ld.so`: a static
x86_64 image (`--format b2`, seed module 98) maps a vendor shared object itself, binds the object's libc imports to
the functions of this directory, and calls into it. No C source, no C compiler, no system loader and no system
libc is part of the route. The vendor driver's code still runs in the process, as under any loader.

The unit is one `(ns g (:export [main]))` line and the files of `MANIFEST` in order, each followed by a newline.
`90-vk-probe.kotoba` is the program of slice 1 (it loads `libvulkan.so.1`); a later slice replaces it with the
provider.

| File | What it holds |
|---|---|
| `00-base.kotoba` | the state map, short load/store names, system-call helpers, C-string helpers, messages and named refusals |
| `10-string.kotoba` | `mem*`, `str*`, the fortified `*_chk`, the ctype table, `strtol` |
| `20-printf.kotoba` | `snprintf`, `__snprintf_chk`, `__vsnprintf_chk`, `sscanf` |
| `30-malloc.kotoba` | `malloc`, `calloc`, `realloc`, `free` |
| `40-stdio.kotoba` | read-only `FILE`, `stderr`, directories, `access`, `readlink`, `getenv`, `qsort`, mutexes, `abort` |
| `50-elf.kotoba` | the ELF loader: mapping, relocation, versioned symbol resolution, refusing stubs, `init_array`, `dlopen`/`dlsym`/`dlerror`/`dlclose`, the thread control block |
| `60-fault.kotoba` | the fatal-signal report (signal, fault address, the object and offset of the instruction pointer) |
| `70-init.kotoba` | `b2-init`: argc/argv/envp, the standard streams, the TCB, the fault reporter |
| `90-vk-probe.kotoba` | slice 1: load libvulkan, run its initializers, call `vkEnumerateInstanceVersion` and `vkEnumerateInstanceExtensionProperties` |

## Conventions

* **Exports.** A function named `cx-NAME-VERSION` is a C-callable entry: the compiler gives it a SysV thunk and lists
  it in the image's export table by symbol name and glibc symbol version (`seed/X86_64-LINUX-ABI`, "Route B2
  image"). The loader binds a library's import only to an export with the version the library requires; an
  export of the name at another version refuses by name.
* **int arguments.** A C caller passes `int` with undefined upper 32 bits: normalize with `(i32 x)` or `(u32 x)`.
* **Refusals, never fallbacks.** An import nothing implements binds to a stub that refuses by name when it is called
  (`b2: refused: unimplemented import NAME ...`, exit 127). A libc function that is asked for something it does not do
  (`fopen` for writing, a floating-point `printf`, a mutex that is already held) refuses by name too.
* **State.** The program's own 32 KiB (`kxrt-b-state`); `00-base.kotoba` has the map of which file owns which range.
* **One thread.** One context and one fuel word (ADR 0375 E3 adds threads).

## Checks

* `scripts/seed/check-b2-image.py`: the image format (any x86_64 Linux kernel; wired into the native CI job).
* `scripts/seed/check-b2-libc.py`: the libc subset, from Kotoba, with the tests of `tests/` (any x86_64 Linux kernel;
  wired into the native CI job).
* `scripts/seed/check-b2-libvulkan.py`: the system `libvulkan.so.1` through the loader, against an independent
  oracle (the same calls through the system's own loader, drivers hidden). GPU hosts only: gad or the B70.
