# ADR-0374 -- Where GPU execution lives after the platform-linked refusal

- Status: **accepted** (the owner, 2026-10-24): option D. C stays open as a
  later, separate decision.
- **Amended by ADR 0375** (the owner, later the same day): the executor is
  Amu's, not the consuming product's own C stack. Routes B (a Kotoba loader)
  and C are the base, and W (browser WebGPU) is supported too. The artifact
  contract below stands.
- Date: 2026-10-24
- Tracking: JUN-365 (this decision); JUN-375 (the inference-side work);
  JUN-344 (ADR 0371, the provider), JUN-356 (ADR 0372, the kernels)

## Context

ADR 0371 gave GPU work a route out of Amu's static images. A separate
provider process, which the static launcher starts, speaks wire 42 and
reaches the GPU through the system's Vulkan stack. The provider was built
with `--format platform-linked`: an ELF whose `DT_NEEDED` names libc, run by
the system's dynamic loader.

Since #1510 (main 0007e50f), two things hold:
* Main's compiler refuses `--format platform-linked` (`E2`).
* Main's `AGENTS.md` excludes the provider's fake-device, Vulkan and libc
  qualifications from mandatory native CDCI. Provider qualification "is
  blocked until an Amu/Kotoba-native route exists".

On 2026-10-24 the owner also said not to bring back the old C-loader route.

What is in place, and stays:
* ADR 0372's kernels. KIR v2 writes the GPU kernels the decode path uses as
  SPIR-V, built by Amu selfhost as static images.
  * `spirv-val` and the Kotoba checker accept every module (105).
  * On RADV and ANV, every module ran byte-identical to glslang's module of
    the same kernel, including on real model tensors (`gpu-kernel-*`
    evidence).

  Those GPU runs used providers that the root before #1510 built, so they
  are historical receipts.

What is blocked, all for one reason (no route main can build that reaches a
GPU):
* ADR 0371 step 6's provider work (#1534);
* step 7 (aarch64-linux, then Xavier);
* step 8 (macOS);
* ADR 0372 step 5 (retiring glslang from the product route; no product
  route runs these kernels now);
* the whole decode guest on the KIR v2 kernels.

The facts that bound the choice:
* **Every user-space GPU stack is C, loaded by the system's loader.** That
  covers Mesa's RADV, ANV and NVK, NVIDIA's L4T driver on Xavier, and
  Metal.framework on macOS. Each is a shared library that expects ld.so and
  its libc (or libSystem), and each carries its own compiler from SPIR-V to
  the GPU's ISA.
* **On Linux, the kernel interfaces are stable.** The DRM render nodes
  (amdgpu, xe/i915) and Tegra's nvgpu are ioctl ABIs a static image can call
  directly, with no loader. Commands and shaders must then be in the
  hardware's own formats.
* **macOS has no stable syscall or kernel GPU ABI** (ADR 0371 Decision 8).
  A GPU program there links libSystem and Metal.framework and is signed.

## Options

### A. A provider exception to the platform-linked refusal

Re-admit `--format platform-linked` for the provider class only, confined as
ADR 0371 specified (the grant, Landlock and the seal after device creation).
This is what ADR 0371 did and #1510 removed.

**Rejected** by the owner's instruction of 2026-10-24, unless the owner
reverses it.

### B. A Kotoba loader for the system Vulkan stack

The provider stays a static Kotoba image and maps libvulkan, the ICD and
their libc itself, replacing ld.so with Kotoba code. It still runs the
vendor's C code in the process.
* Loading glibc without its own ld.so is the hard part: TLS setup, IRELATIVE
  relocations, rtld's global state, `dlopen` from inside the ICD.
* It is fragile across driver and libc versions.
* It gains no independence from C: only the loader changes language.

**Not recommended.**

### C. A native kernel-driver route

The provider calls the GPU's kernel driver directly over its ioctl ABI, from
a static image. It submits its own command buffers and runs shaders that Amu
compiles to the GPU's ISA:
* RDNA for amdgpu;
* Xe2 for xe/i915;
* Volta for Xavier's nvgpu, whose ISA is undocumented.

This is the only fully Amu-native GPU route. It is a compiler back end and a
driver per vendor, and none of it applies on macOS.

**The long-term native option**, if GPU execution must sit inside Amu's own
closure.

### D. GPU execution outside Amu's route

Amu's contract ends at verified GPU artifacts:
* KIR v2's modules, built by Amu selfhost;
* checked by the Kotoba checker and, as an oracle, `spirv-val`;
* pinned by digest (ADR 0371 Decision 9).

Executing them is a separate product's qualification under its own policy,
for example kotoba-lang/inference's runtime on GPU hosts. Amu keeps:
* ADR 0372 steps 1–3, the build and oracle phases of
  `check-gpu-kernel-spirv.py`;
* the receipts of the provider era, as historical evidence.

The gpu and exec phases' scripts stay as that product's acceptance harness,
run where it qualifies them.

**Cheapest, and consistent with the native-only policy.**

## Recommendation

Take **D** now, and keep **C** open as a later, separate decision.

What D means for the blocked items:
* **ADR 0371 steps 6–8.** The provider work (#1534), Xavier and the macOS
  ADR move to the executing product's plan. On macOS, Metal through
  Metal.framework is the only route either way.
* **ADR 0372 step 5.** Retirement means the executing product consumes KIR
  v2's modules instead of compiling glslang output. glslang and the
  hand-written `.comp` files stay as oracles and baselines in Amu's test
  phases.
* **The whole decode guest.** It is the executing product's acceptance test,
  on its own route. It is not generated by the retired CLJK tooling.

## Decision

The owner answered the three open questions on 2026-10-24:

1. **D is accepted.** kotoba-lang/inference owns GPU execution and qualifies
   it under its own policy. Amu's contract ends at the verified KIR v2
   modules.
2. **C is decided later**, as its own decision. Nothing in Amu starts on it
   now.
3. **The provider-era scripts stay in Amu as history:**
   * `check-gpu-provider.py`;
   * the gpu and exec phases of `check-gpu-kernel-spirv.py` and
     `check-gpu-kernel-exec.py`.

   They are not native CDCI gates. They remain the acceptance harness that
   the provider-era receipts were made with.

What changes in Amu:
* **ADR 0371 steps 6–8** move to inference's plan:
  * the rest of the provider work, including #1534's device features;
  * aarch64-linux and Xavier;
  * the macOS route.

  Amu keeps the launcher, wire 42 and the protocol table.
* **ADR 0372 step 5.** Amu's part is done: no Amu product route compiles
  glslang output, and the accelerator CLJK's source belongs to the hosted
  CLI's migration (JUN-280). The rest is inference consuming KIR v2's
  modules in place of `emit-kernel.cljk` and glslang.
* **The whole decode guest** is inference's acceptance test, on its own
  route.

Tracking: JUN-365 (this decision). The inference-side work is JUN-375.
