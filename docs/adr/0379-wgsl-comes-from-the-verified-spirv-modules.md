# ADR-0379 -- WGSL comes from the verified SPIR-V modules, written in Kotoba

- Status: **proposed** (nothing here changes a seed, an artifact or a pin).
- Date: 2026-10-28
- Tracking: JUN-377 (ADR 0375 route W), JUN-375 (inference's side).
- Follows: ADR 0372 (KIR v2), ADR 0375 (routes B, W, C).

## Context

ADR 0375 decision 2 lets Kotoba kernels be transpiled to WGSL, and route W
runs the work in the browser. The owner's direction of 2026-10-28 is that
Kotoba must be able to output WebGPU/WGSL, with Kotoba/Amu selfhost as the
premise: WGSL is an output, not the place the kernels are written.

What main has: `tools/gpu_kernel_kir2.kotoba` is a SPIR-V *word builder*.
Each `kb-*` call appends SPIR-V instructions (`kb-op2 B 128 ...` is `OpIAdd`),
and the 89 kernels in `tools/gpu_kernels_v2.kotoba` (2780 lines) are written
against it. 105 modules are verified (the Kotoba checker, `spirv-val`, and
byte identity with glslang on RADV and ANV).

## Options

1. **A second builder that emits WGSL text with the same `kb-*` API.** Every
   kernel would have to take a back-end parameter, or be written twice.
   Rejected: 2780 lines of kernels change, and the two outputs could drift.
2. **A language-neutral IR between the kernels and both back ends.** The
   right end state, and a rewrite of all 89 kernels. Not the first step.
3. **A translator from the verified SPIR-V modules to WGSL, in Kotoba.**
   The kernels do not change, the input is already pinned by SHA-256, and
   the existing oracle (`spirv-val`) still guards the input. The translator
   only has to cover the subset the kernels use (ADR 0372 lists it: storage
   buffers in std430, workgroup arrays, Function-storage variables,
   structured `OpSelectionMerge` / `OpLoopMerge` control flow, the GLSL.std.450
   subset, Float16, subgroup arithmetic, the packed 4x8 dot product).

## Decision (proposed)

Take option 3 first. A Kotoba unit (`tools/spirv_to_wgsl.kotoba`) reads a
module's words and writes WGSL text:

* Structured control flow maps to `if` / `loop` / `for` directly, because the
  builder only emits the glslang four-block loop and `OpSelectionMerge` forms.
  A module outside that shape is refused, not guessed at.
* Function-storage `OpVariable`s become `var`; every other result id becomes a
  `let` in dominance order.
* **Every identifier is generated** (`b<binding>`, `s<n>` for workgroup
  arrays, `v<id>` for values). This is a measured requirement, not a style
  choice: a hand-written WGSL of `dot_rows` that named its Meta binding
  `meta` was rejected by the browser (`'meta' is a reserved keyword`).
* `Float16` needs the `shader-f16` feature (`enable f16;`), and the subgroup
  ops need `subgroups`. The translator reports the features a module needs;
  the host decides whether to run it.
* Option 2 stays the end state. The translator is the bridge that lets the
  numeric gates exist now.

## Measured: the target output is valid and correct (2026-10-28)

Hand-written WGSL for `dot_rows` (`tools/gpu_kernel_refs/dot-rows.wgsl`, the
golden text the translator's output for `kir2-dot-rows` must equal up to
identifier names), run through the browser's WebGPU on this Mac:

| item | value |
|---|---|
| device | Apple M1 Max, Metal 3 (WebGPU `info.architecture` `metal-3`) |
| features offered | `shader-f16`, `subgroups`, `timestamp-query` |
| shape | 4096 x 4096 f32, one 256-thread workgroup per row |
| max relative error vs an f64 CPU sum | 1.5e-5 (rows sampled every 37) |
| 200 back-to-back dispatches, one submit | 0.227 ms each, 296 GB/s of weight reads |

The 296 GB/s is the cached figure for a 64 MiB matrix; it is not a model
decode rate and is not comparable to `llama-bench`.

## What this does not show

* Nothing here was built or run by Amu. **This Mac cannot run the Amu
  compiler:** `bin/amu`, `bin/kotoba` and `bin/kotoba-compiler` are Linux
  x86-64 static ELFs, and the host has no Linux VM. The translator therefore
  has not been written; the build and test phases of
  `scripts/seed/check-gpu-kernel-spirv.py` are Linux phases.
* No selfhost decode, batched prefill or serving loop runs through WGSL.
  No vLLM or llama.cpp comparison was taken.
* The browser here is a test oracle, as `spirv-val` is for SPIR-V. It is not
  the product route.

## Next steps

1. A Linux host that can build and run Amu units (gad, or a VM): write
   `spirv_to_wgsl.kotoba` for `dot_rows` first, with the golden text above.
2. Browser gate: `createShaderModule` reports no error and the numbers match
   the f64 twin, in headless Chrome with WebGPU
   (`scripts/seed/check-wasm32-browser.py` already runs Amu modules there).
3. Widen to the kdot family, then the nex ops, then the Float16 and subgroup
   kernels, each with its feature report.
