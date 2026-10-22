# ADR-0359 -- The Vulkan arm: GLSL admission and a sealed SPIR-V build step

- Status: decisions 1 and 3 are IMPLEMENTED (2026-10-22; code + tests in
  kotoba.compiler.accelerator{,-kir,-targets,-subgroup-reduce} and their
  tests). Decision 2 is IMPLEMENTED: its pure half (2026-10-22; code +
  tests in kotoba.compiler.accelerator-spirv{,-test}: payload construction,
  sealing, and integrity-plus-provenance verification of the
  :kotoba.gpu-spirv-artifact/v1 format) and its host half (2026-10-22; code
  + tests in kotoba.compiler.accelerator-spirv-compile{,-test}: the `amu
  gpu-spirv-compile <artifact.edn> --output <file.spv>` entry point on both
  CLI routes, the tool-identity recording, and the loader-cache file written
  from the sealed bytes with the pre-dispatch hash check). The sealed record
  is written beside the cache as `<file.spv>.edn` (the surface named where
  the record lands). STILL UNIMPLEMENTED: the measurement harnesses
  consuming compiler-sealed artifacts (they keep their own glslang
  invocations), and the dispatch-side call of verify-loader-cache!. The
  default runner's process spawn against real glslangValidator is exercised
  by hand on this host, not by the suite (the suite drives the seam with a
  fake runner). UNMEASURED where a measurement is owed.
- Date: 2026-10-22
- Tracking: closes ADR-0356's execution-path honesty gap "(a)" on paper.
  The Intel row (JUN-59) and the ARM row (JUN-60) both block on (a); parent
  JUN-55. The implementation of this decision is the next slice.

## The gap being closed

ADR-0356, execution-path honesty: implementing the Intel row "needs (a) a
Vulkan-side emission admitted for `:subgroup-reduce` -- and a specified
GLSL/WGSL -> SPIR-V compilation step (a `glslangValidator` invocation in the
pipeline, or a build step whose compiled artifact is the file the loader
opens) that the current wire-42 path lacks -- before `select-variant` may
ever answer it". Measured state of the gap, 2026-10-22 at chain HEAD:

- The emission half exists and has EXECUTED. The Vulkan-side emission is
  `kotoba.compiler.accelerator-subgroup-reduce/emit-glsl` (its tests pin the
  text; the execution ladder `scripts/test-gpu-subgroup-reduce-exec.cljk`
  compiled that text with `glslangValidator` and ran it on the M1 Max through
  wire 42 -- a TOOLCHAIN measurement of what compiles and executes, not an
  optimization measurement).
- The compile half exists only in measurement harnesses. Every
  `glslangValidator` invocation in the repository lives under `scripts/`
  (grep measured 2026-10-22: 13 files there -- 12 `.cljk` harnesses and
  `gpu-workgroup-sweep/gen-wg-shaders.py` -- and none in `src/`, `tools/`,
  `bin/`). The pipeline emits and seals SOURCE:
  `lower`/`compile-kernel`/`verify-artifact!`. The loader opens an ALREADY
  COMPILED SPIR-V blob: `kgpu_new_pipeline`
  (`tools/kexe_gpu_vulkan.c:423`, chain HEAD) reads the file and the wire is
  `PIPELINE <spv-path> <bindings>` (entry "main"). Nothing in the compiler
  turns one into the other.
- Consequently the seal cannot bind the file the loader opens, and the GLSL
  arm has no target: `accelerator/targets` is `#{:wgsl-v1 :cuda-v1 :msl-v1}`
  and `lower` admits `:subgroup-reduce` for none of them. One inconsistency
  is already visible at HEAD: `verify-artifact!`'s variant vocabulary names
  `:subgroup-reduce` while `lower` refuses it ("unsupported kernel variant"),
  so no `:subgroup-reduce` artifact can verify today.

## Decision 1 -- `:glsl-v1` is a fourth emission target (ADR-0002 amended)

`targets` gains `:glsl-v1`: GLSL 450 compute, the language the Vulkan arm
actually compiles. `lower` admits `:glsl-v1` for `:baseline` (the same
elementwise and tree-reduce shapes the wire-42 sweeps execute) and for
`:subgroup-reduce` (routed to the existing `emit-glsl`, so the seal regime
covers that emission like any other). `:warp-shuffle-reduce` stays CUDA-only
(rule 3: a variant the target's emitter does not admit is never emitted).
`verify-artifact!`'s vocabulary and `lower`'s admission converge on the same
set.

Why a target and not a variant property of the WGSL arm: the seal binds
`(target, kir, variant)` and hostile verification re-lowers from exactly
that key. GLSL text sealed under a `:wgsl-v1` label would make the
artifact's own record false, and ADR-0002's verification regime would be
blessing the lie. The WGSL, CUDA and MSL targets keep their present
admissions unchanged.

## Decision 2 -- SPIR-V is a build step with its own sealed artifact

GLSL/WGSL -> SPIR-V is NOT a KIR syntax and NOT a fifth target. It is a
build step over a verified source artifact, answering a new artifact format
`:kotoba.gpu-spirv-artifact/v1` (this realizes ADR-0002's "SPIR-V ... future
versioned" consequence as a new artifact format over unchanged v1 KIR; the
KIR schema is untouched).

The payload binds, at minimum:

- the source artifact's `:kir-sha256` and `:code-sha256` (the provenance
  chain back to KIR), plus `:target` and `:variant` (the regeneration key
  of ADR-0356 rule 5);
- the SPIR-V bytes' SHA-256 over the exact compiled bytes, with the bytes
  carried inline in deterministic encoding;
- the TOOL IDENTITY that produced them: tool name, its `--version` output
  verbatim, and the exact argv. A binary with no recorded tool identity is
  refused, not sealed -- an unattributed blob is not a verified artifact.

Verification of this format is integrity plus provenance, NOT re-lowering
(SPIR-V does not re-lower to KIR):

1. the source artifact passes the full hostile re-lower check, unchanged;
2. the bytes hash to the sealed `:spirv-sha256`;
3. the tool identity is present and well-formed;
4. optional claim upgrade: when the recorded tool is present on the
   verifying host AND its version matches, recompile the sealed source code
   and require byte equality with the sealed bytes ("verified-by-rebuild").
   With the tool absent or a different version, the claim stays provenance
   and is labeled so.

Byte-identity, scoped honestly: source artifacts remain byte-identical
exactly as ADR-0002 defines. SPIR-V artifacts are byte-identical only for
the same recorded tool identity -- glslang output is tool-version specific
(the exec ladder records acceptance quirks of glslang 11:16.6.0 on this
host). No cross-tool or cross-version byte identity is claimed.

The file the loader opens is written FROM the sealed bytes and is a cache:
before dispatch its SHA-256 must equal the sealed one (the wire contract
stays `PIPELINE <spv-path> <bindings>`; the bindings count is derived from
the KIR op and recorded in the payload).

Surface: the pure half (payload construction, sealing, verification) lives
in the compiler and never shells out. Exactly one host-invoking entry point
performs the compilation -- `amu gpu-spirv-compile <artifact.edn> --output
<file.spv>`, the sibling of ADR-0357's `amu gpu-compile` -- and records what
it ran. The measurement harnesses keep calling their own invocations until
the implementation lands; afterwards they consume compiler-sealed bytes.

## Decision 3 -- the route amendment (ADR-0355 rule 2): `:vulkan` answers `:glsl-v1`

`target-for` becomes: `:cuda` -> `:cuda-v1`, `:metal` -> `:msl-v1`,
`:vulkan` -> `:glsl-v1`, `:webgpu` -> `:wgsl-v1`. Vulkan names no shading
language; it opens compiled SPIR-V, and the only source-to-SPIR-V path this
repository owns is glslang from GLSL. WebGPU keeps its language. The
api-less vendor defaults are UNCHANGED (nvidia `:cuda-v1`, apple `:msl-v1`,
intel/arm/amd/unknown `:wgsl-v1`): an api-less descriptor is a portable
shading-language choice, not an execution claim.

Blast radius (grep measured 2026-10-22): `target-for`'s cond and docstring,
`accelerator-targets-test` pins at lines 29 and 112, and the four
`:wgsl-v1` pins in `accelerator-pipeline-test` -- all inside the GPU
namespace family. Evidence directories are historical records and are not
rewritten. Implemented 2026-10-22 (this ADR's implementation slices): the
`target-for` route and its pins moved; the four `:wgsl-v1` pipeline pins
are api-less vendor defaults and are UNCHANGED by design, re-verified green.

## What this decision does NOT do

- It creates no selection row. `select-variant` still answers `:baseline`
  for every `:subgroup-reduce` shape; the JUN-59/60 rows land next, with
  their now-admitted emission and their route (ADR-0356 rule 3's ordering:
  emission admission before selection -- this ADR is the admission half).
- It changes no `:measured?` flag and no workgroup row. The barrier-count
  argument of ADR-0356/0357 remains a design assumption
  (`:measured? false`); the JUN-59/60 measurement contracts are unchanged.
- Rule 6 (device capability, not vendor identity) is unchanged: selection
  will still require the probed subgroup properties, and a device that does
  not confirm them answers `:baseline`.
- It adds no execution path for CUDA, MSL or WGSL. Those arms stay
  source-only; `:wgsl-v1` keeps no execution path in this repository.

## Consequences

- ADR-0356 gap (a) is fully decided: admission (`:glsl-v1`) plus the compile
  step (a sealed build step). "Until (a) lands the selection row must not
  exist" releases when the implementation of THIS decision lands -- not
  before, and this ADR is not that implementation.
- ADR-0002's "three emission targets" is amended to four, and its SPIR-V
  future becomes an artifact format rather than v1 KIR syntax.
- The loader's input file becomes a verified compiler output instead of a
  harness-private temp file; the exec harnesses' hand-recorded provenance
  blocks (emitter sha256, transcription self-checks) shrink to consuming a
  sealed artifact.
