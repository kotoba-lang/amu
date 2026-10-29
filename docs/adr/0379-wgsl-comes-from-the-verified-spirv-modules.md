# ADR-0379 -- WGSL comes from the verified SPIR-V modules, written in Kotoba

- Status: **proposed**; slice 1 (`dot_rows`) is implemented and measured below.
  Nothing here changes a seed, an artifact or a pin.
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

## Slice 1: `tools/spirv_to_wgsl.kotoba`, built and run on this Mac (2026-10-28)

`spw-translate` takes a module vector (as `spirv_encode.kotoba` builds it) and
returns WGSL text, or text that starts with `//ERROR` for anything outside the
subset. It makes one pass for the id table and decorations and a second pass
over the function body, keeping a small stack to rebuild `if` and `loop`
(`continuing` for the continue block) from `OpSelectionMerge`,
`OpBranchConditional` and `OpLoopMerge`. Identifiers are generated (`b<n>`,
`s<id>`, `f<id>`, `v<id>`, `i<id>`) because WGSL reserves words such as `meta`.

Apple Silicon is a host for this: Amu's pinned Mac-native compiler
(`seed/bootstrap/aarch64-macos/amu-full-root.macho`, the `diagnostic-candidate`
row of `root.json`) and packager run here with no Linux. The route, as
`scripts/seed/check-aiueos-user-macos-native.py` runs it:

1. `amu compile unit.kotoba --target aarch64-macos --output u.kseed`
2. `amu extract-native u.kseed --symbol main --output u.raw` (the `:offset`)
3. `kotoba-packager-root.macho u.unsigned u.raw fs2-cli-stdio-general <offset>`
4. `codesign -s - -f` on a copy, then run it with the output directory as fd 3.

The unit is `spirv_encode`, `spirv_check`, `gpu_kernel_kir2`, `gpu_kernels_v2`
and `spirv_to_wgsl` (ns lines dropped) plus a `main` that prints
`(spw-translate (kir2-dot-rows))`. It compiles in about 13 s. On this host
`spc-check` accepts the module (612 words) and `spirv-val --target-env vulkan1.1`
accepts the words printed from it. Two limits of the Mac runtime showed up:
`spv-write` (`:fs/app-data-bytes`) traps there, so the translator reads the
module from memory and the unit prints text to stdout instead of writing files.

The output is [`tools/gpu_kernel_refs/dot-rows.wgsl`](../../tools/gpu_kernel_refs/dot-rows.wgsl),
the translator's own text. In the browser's WebGPU on this Mac:

| item | value |
|---|---|
| device | Apple M1 Max, Metal 3 (WebGPU `info.architecture` `metal-3`) |
| features offered | `shader-f16`, `subgroups`, `timestamp-query` |
| compile messages | 0 |
| shape | 4096 x 4096 f32, one 256-thread workgroup per row |
| max relative error vs an f64 CPU sum (111 rows) | 1.5e-5, identical to a hand-written WGSL of the same kernel |
| 200 back-to-back dispatches, one submit | 0.213 ms each, 314 GB/s of weight reads |

The 314 GB/s is the cached figure for a 64 MiB matrix; it is not a model
decode rate and is not comparable to `llama-bench`.

## Slice 2: the kdot family (2026-10-28)

The translator now covers `OpSelect`, `OpBitcast`, the `OpConvert*` family,
`OpCompositeConstruct`, `OpDot`, `OpBitFieldSExtract`, the packed 4x8 integer
dot product (`dot4I8Packed`, with `requires packed_4x8_integer_dot_product;`),
GLSL.std.450 instructions that have a WGSL builtin, Function-variable arrays
and vector elements. `spw-unsupported` reports the opcodes a module uses that
are still refused, and `spw-ok?` says whether the text holds an `//ERROR`.

Seven kernels translate with no refusal and pass wgpu's validator (the
evidence README has the table); the validator found three real defects that
the first pass missed, now fixed: a generated name `f32` for id 32 (every
generated name now has an underscore, `f_32`), a signed shift amount (WGSL
needs a `u32`), and packed-dot operands typed `i32` (cast to `u32`).
`kdot-f32-r1`, the decode kernel, matches an f64 sum on synthetic Q8_0 data to
5.2e-6 at 64 x 1024 and 1.5e-4 at 4096 x 4096, where it reads weights at
41 GB/s. Evidence: [`docs/evidence/spirv-to-wgsl-20261028/`](../evidence/spirv-to-wgsl-20261028/README.md).

## What this does not show

* Seven kernels of 89 are translated; the deltanet, embed, nex-op, h2 and
  subgroup kernels are not, and Float16 and subgroup output are not written.
  `break` / `continue` branches are refused.
* The checks ran by hand with Deno's WebGPU and one browser tab. There is no
  product-route gate yet (headless Chrome, no Node).
* Numerics were checked for `dot-rows` and `kdot-f32-r1` (Q8_0 arm) only; the
  other types and kernels pass validation, not parity.
* The 41 GB/s is one microbenchmark. No selfhost decode, batched prefill or
  serving loop runs through WGSL, and no vLLM or llama.cpp comparison was
  taken.
* The browser and Deno here are test oracles, as `spirv-val` is for SPIR-V.
  They are not the product route.
* The Mac runtime is a diagnostic profile (its own arena sizes, no file
  write); JUN-417 owns qualifying it.

## Next steps

1. The headless-Chrome gate: feed the generated text to `createShaderModule`
   and the f64 twins, replacing the by-hand checks.
2. The remaining kernels, each with a feature report (`enable f16;`,
   `enable subgroups;`), then parity for every tensor type of `kdot-f32-r1`.
3. Kernel bandwidth (AWAI-6): the dequantising kdot reads at 41 GB/s where the
   f32 stream reads 300+, in WGSL as in SPIR-V.
4. The language-neutral IR (option 2) once two or more back ends need it.
