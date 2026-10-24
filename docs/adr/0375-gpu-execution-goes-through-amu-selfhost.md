# ADR-0375 -- GPU execution goes through Amu selfhost: a Kotoba loader, native drivers and WebGPU

- Status: **accepted direction** (the owner, 2026-10-24). The order of the
  implementation steps below is proposed. Nothing here is implemented.
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

## Implementation steps (proposed order)

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

1. Is the order above right: B, then W, then C?
2. Is amdgpu the first vendor for C?
3. Once B runs natively, should the GPU-host gates become a named,
   GPU-host-only gate set beside mandatory CDCI?
