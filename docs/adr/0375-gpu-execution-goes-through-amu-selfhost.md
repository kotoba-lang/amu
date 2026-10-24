# ADR-0375 -- GPU execution goes through Amu selfhost: a Kotoba loader, native drivers and WebGPU

- Status: **accepted direction** (the owner, 2026-10-24). The owner set the
  order the same day: B, then W, then C. Nothing here is implemented.
- Date: 2026-10-24
- Amends: ADR 0374 (where GPU execution lives) and ADR 0371 (the provider
  route).
- Tracking: JUN-377 (this ADR), JUN-375 (inference's side).

## Context

ADR 0374 (accepted the same day, option D) left execution to the product
that runs the kernels, kotoba-lang/inference, under its own policy. Working
on JUN-375 showed that inference has no executor that the workspace rules
allow:
* **Its old route is gone.** Inference's GPU route was Amu's C loader
  (`kexe_loader.c` built with `-DKEXE_GPU_VULKAN -lvulkan`), removed in
  #1459/#1460.
* **Amu's Kotoba provider can't be built.** Main refuses its
  `--format platform-linked` build (#1510).
* **The rules rule out the alternatives.** The workspace rules
  (`com-junkawasaki/root/AGENTS.md`) remove C compiler, loader and runtime
  dependencies, and inference has no AGENTS.md of its own.

Two ways out were rejected for that reason:
* a platform-linked provider built with a pinned root from before #1510;
* a new C provider in inference.

The owner's answers on 2026-10-24:
* 「時間がかかっても良いので amu selfhost, kotoba 経由を優先する。ただ, kotoba
  から gpu 各言語に transpile するのもok」
* 「C, B をベースにしつつ, W も対応といのがいいのでは? kototama, amu で
  loader, driver も最適化できるよね.」

## Decision

1. **GPU execution goes through Amu selfhost and Kotoba**, even if that takes
   longer. The executor is an Amu-built program, not a C program and not the
   system's dynamic loader.
   * A platform-linked provider built by an older root is not adopted.
   * A new C provider is not adopted.
2. **Kernels are written in Kotoba (KIR v2) and may be transpiled to each
   GPU language:**
   * SPIR-V, as now;
   * WGSL;
   * MSL;
   * the GPU's own ISA, for route C.
3. **Three routes, all Amu's.** B and C are the base, and W is supported too.
   * **B, a Kotoba loader for the platform GPU stack.** The provider
     (`tools/gpu_provider.kotoba`, `tools/gpu_device_vulkan.kotoba`) stays a
     static image. In place of ld.so, Amu's own loader maps libvulkan, the
     ICD and their dependencies:
     * it applies relocations, including IRELATIVE;
     * it sets up TLS and resolves versioned symbols;
     * it serves the ICD's `dlopen`.

     The vendor driver's code still runs in the process, as it does under
     any loader.
     * **What stays from ADR 0371:** wire 42, the launcher, the grant, the
       confinement after device creation and the provider receipt.
     * **What it replaces:** ADR 0371's platform-linked format.
     * **What it reuses:** the 105 verified SPIR-V modules, unchanged.
   * **C, the native kernel-driver route.** A static image opens the
     render node (amdgpu, xe/i915) or nvgpu. It allocates buffers and
     submits command streams it builds, with shaders that Amu compiles to
     the GPU's ISA. No vendor user-space code runs.
   * **W, browser WebGPU.** Amu's `wasm32-browser` target hosts the work.
     Kernels are transpiled to WGSL, and WebGPU features (`shader-f16`,
     subgroups) are used where the browser offers them.
     * This matches the workspace contract that the user's browser is
       user-side execution.
     * The headless-Chrome harness in `scripts/seed/check-wasm32-browser.py`
       already runs Amu-built modules there, with no Node.
4. **Kototama and Amu own the loader and the drivers, and optimize them.**
   They are Amu code, under Amu selfhost's build and provenance rules.
5. **ADR 0374's artifact contract stands:** the modules are built by Amu
   selfhost, checked by the Kotoba checker and `spirv-val`, and pinned by
   digest. What changes is the executor: it is Amu's (B, C or W), no longer
   the consuming product's own C stack. Inference consumes both the modules
   and the executors (JUN-375).

## Implementation steps (in the owner's order)

1. **B on x86_64-linux** (gad and the B70):
   * a Kotoba ELF loader that can bring up the system Vulkan stack: glibc,
     libvulkan and the RADV/ANV ICDs;
   * the provider as a static image on top of it.

   The provider-era gates are its acceptance: `check-gpu-provider.py` and
   the gpu and exec phases of the kernel gates. With a native provider they
   become current receipts again. They run on the GPU hosts, outside
   mandatory CDCI.
2. **W.** A KIR v2 back end for WGSL, checked against a WGSL validator as a
   test-time oracle, as `spirv-val` is for SPIR-V. The decode host runs in
   the `wasm32-browser` target. The numeric gates run in headless Chrome
   with WebGPU on gad and the B70.
3. **C on amdgpu first** (gad, gfx1151):
   * render-node buffers and one compute dispatch;
   * then a KIR back end for the RDNA ISA;
   * then xe (the B70) and nvgpu (Xavier).
4. **aarch64-linux and Xavier**, through B (L4T's Vulkan) and then C.
5. **macOS.** There is no stable syscall ABI, so B there means a Kotoba
   Mach-O loader for libSystem and Metal.framework, with kernels in MSL.
   W through the browser is the other route.

## Measured: what B's loader must bring up (2026-10-24)

On gad (Ubuntu 24.04, glibc 2.39, Mesa 25.2.8, the B70's Mesa version), the
`DT_NEEDED` closure of libvulkan plus one ICD was measured
(`docs/evidence/gpu-loader-closure-20261024/`):
* **RADV:** 35 libraries, 203 MB. It links libLLVM 20, which brings
  libstdc++, ICU and libxml2. It imports 564 glibc symbols.
* **ANV:** 26 libraries, 30 MB, with no LLVM. It imports 404 glibc symbols.
* **Both:** 68 IRELATIVE relocations, TLS (TLSDESC in RADV), `dlopen` and
  pthreads.

Two loader designs follow:
* **B1. A Kotoba ld.so under the real glibc.** It has to provide the 16
  `GLIBC_PRIVATE` symbols libc needs, including `_rtld_global` and
  `_rtld_global_ro`, whose layout belongs to one glibc build.
* **B2. A Kotoba libc in place of glibc.** It exports glibc's public,
  versioned ABI: 404 symbols for ANV.

B2 is the narrower and more durable design. ANV (the B70) is the smaller
first target, and RADV adds libLLVM's closure. So step 1 above becomes:
1. B2 on ANV;
2. then RADV.

## B2 in slices (proposed, 2026-10-24)

**What main has today** (origin/main `fea41f39`):
* **Calls out to C.** `kxrt-ccall` takes 6 register arguments and up to 8
  stack arguments, returns in rax, and is admitted only in mode 3
  (`seed/75-x86_64-static.kotoba`). A static mode-3 build exists
  (`xs-build ... 3`).
* **Raw syscalls**, including mmap, mprotect, openat and pread
  (`seed/76-x86_64-static-rt.kotoba`).
* **Some ELF parsing:** headers, phdrs and the dynamic section
  (`tools/gpu_provider.kotoba`), and symbol tables
  (`re_disasm/disasm.kotoba`).
* **The provider** reaches Vulkan through a single import,
  `vkGetInstanceProcAddr`.

**What main lacks:**
* **E1. Calls in from C.** There is no C-callable entry point:
  `seed/X86_64-LINUX-ABI` says "No externally callable scalar ABI". Every
  libc function that the vendor code calls is such a call. It needs a SysV
  entry thunk per exported function, plus an export table by name and
  version. The thunk must:
  * move the arguments so that r9 (Kotoba's context register) is free;
  * set up the context and fuel;
  * preserve the callee-saved registers;
  * return rax.

  The aiueos object route's thunk (`seed/74`) and the signal-handler slot
  (`kxrt-slot-400`) are the precedents.
* **E2. Memory access:** 16- and 32-bit loads and stores, atomics
  (cmpxchg, xadd, xchg) and fences.
* **E3. Threads:** `clone` with `CLONE_THREAD` and `CLONE_SETTLS`, futex,
  and per-thread runtime state. Today the state is one G region per
  process.
* **E4. The FS base and TLS:**
  * a TCB whose self pointer is at fs:0 and stack-protector canary at
    fs:0x28;
  * static TLS blocks for loaded objects;
  * TPOFF, DTPMOD and DTPOFF relocations and `__tls_get_addr`.
* **E5. Floating-point arguments.** The x86 profiles refuse floating point,
  but ANV imports 22 libm and float functions (`powf`, `log2f`, `strtod`
  and others). As a minimum, thunks move xmm arguments and results.
* **E6. A loader:**
  * maps PT_LOAD segments;
  * applies RELATIVE, 64, GLOB_DAT and JUMP_SLOT relocations;
  * looks up symbols with versions (versym/verneed, GNU_HASH);
  * runs init_array;
  * serves `dlopen`, `dlsym` and `dl_iterate_phdr`.

  Imports with no implementation yet bind to a stub that refuses by name,
  so the libc grows only with what the compute path calls.

**Slices:**
1. **The Vulkan loader alone.** Load `libvulkan.so.1` and call
   `vkEnumerateInstanceVersion` and `vkEnumerateInstanceExtensionProperties`,
   with no ICD.
   * Its closure is just libc and libm, about 58 functions: malloc, the
     strings, `getenv`, stdio, `opendir`/`readdir`, `sscanf`, `snprintf`,
     `qsort` and pthread mutexes.
   * Its relocations are 123 RELATIVE, 5 GLOB_DAT and 56 JUMP_SLOT, with
     no TLS.
   * It needs E1, E2 (for 32-bit fields), E6, and E4's TCB with the
     canary.
2. **The ANV ICD.** `dlopen` the ICD and its closure (26 libraries), then
   run `vkCreateInstance` and `vkEnumeratePhysicalDevices` with their
   properties, as the provider's INFO and DEVCLASS. It adds:
   * E4's full TLS (libstdc++, libgcc_s);
   * GNU_UNIQUE symbols and the C++ runtime's init;
   * E5 where it is called.
3. **A device and one dispatch.** Create the device, a compute pipeline from
   a KIR v2 module, and one dispatch. E3 comes in here, for Mesa's worker
   threads.
4. **The provider on B2.** The provider runs as a static image on B2,
   behind the launcher with its confinement. The provider-era gates run on
   the B70 and replace the historical receipts: INFO and DEVCLASS, the dot
   and kdot fixtures, and the exec gate.
5. **RADV** (gad). It adds libLLVM's closure (35 libraries, 564 symbols).

E1–E5 are changes to the seed (the compiler and runtime). Each slice that
changes the seed regenerates and verifies the root, product, gate and
controller pins, as #1522 did.

## Consequences

* **B depends on glibc and driver internals.** The GPU hosts pin their
  library versions, and the provider receipt already records libvulkan's
  and the ICD's paths and digests. A loader failure is a named refusal,
  never a fallback.
* **C is large and per vendor.** It is the only route with no vendor
  user-space code.
* **W is bounded by WebGPU's limits:** binding sizes, subgroup and f16
  availability, and dispatch overhead. Its numbers are measured against
  the Vulkan receipts.
* **Nothing returns to C source in Amu or in inference.**

## Open questions for the owner

1. **Decided (2026-10-24):** B, then W, then C. B2's slice 1 runs in its own
   session.
2. Is amdgpu the first vendor for C?
3. Once B runs natively, should the GPU-host gates become a named,
   GPU-host-only gate set beside mandatory CDCI?
