# ADR-0357 -- The accelerator pipeline enters the CLI

- Status: accepted and implemented (JUN-85 emit stage)
- Date: 2026-10-18

> **Dated note (2026-10-24, ADR 0371).** The GPU execution path this ADR
> refers to is deleted: the C loader `tools/kexe_loader.c`, and wire 42's
> `:gpu/compute` brokered by `tools/kexe_gpu_vulkan.c`. ADR 0371 replaced
> it with a provider process that the static launcher starts and that
> speaks the same wire-42 protocol. Since #1510 two things hold: main's
> compiler refuses that provider's `--format platform-linked` build, and
> its qualifications are outside mandatory native CDCI (`AGENTS.md`). So
> no current route executes a GPU artifact. The text below is kept as
> written.

## Decision

`amu gpu-compile <spec.edn> --device <device.edn> [--output <artifact>]`
connects the accelerator pipeline on the bin/amu route: one kernel SPEC and
one device descriptor become one sealed GPU artifact through
`kotoba.compiler.accelerator-targets`' deterministic vendor dispatch and
`kotoba.compiler.accelerator`'s deterministic emitters. Before this the
emitters were library-only: KIR reached them, but nothing carried a device
descriptor through dispatch to a sealed artifact.

1. The command is target-independent (routed with the target-less commands):
   the DEVICE, not `--target`, chooses the emission target. `--target` and the
   project/lock flags are refused by name, never silently ignored.
2. The workgroup size is the SPEC's when it names one, else the provisional
   dispatch default (ADR-0355). The answer carries `:workgroup-source`
   (`:spec` / `:dispatch`) and `:measured?`, which is true only when a
   MEASURED dispatch row supplied the default -- today never, since every
   ADR-0355 row is provisional.
3. `classify-vendor` also matches a `:vendor-id` given as the kotoba reader's
   BigInt (every integer token is one on the nbb route -- i64 exactness,
   `cli_support`). Measured: `{:vendor-id 4203}` read through `bin/amu`
   classified as `:unknown` before this, silently sending an Apple device to
   `:wgsl-v1`; the id lookup now also compares the decimal spelling. A string
   `:vendor "apple"` and the id form answer byte-identical artifacts.
4. Same SPEC and DEVICE in, byte-identical artifact out (the emitters and the
   dispatch table are both deterministic; the artifact's `:kir-sha256` /
   `:code-sha256` say so).

The same entry exists on the in-process CLI (`cli.cljk`), sharing
`kotoba.compiler.accelerator-pipeline/compile-spec` -- the established
module-lock pattern of one implementation, two command surfaces.

## Non-claims

- Emit only. Nothing here EXECUTES a GPU artifact; the wire-42 `:gpu/compute`
  probe route (scripts/test-gpu-compute.cljk) is separate and stays the
  execution surface.
- The workgroup defaults remain unmeasured design values. Nothing here is
  optimization evidence (JUN-57..60, JUN-84 still own measurement).
- Source-to-accelerator-KIR lowering is not part of this: a SPEC describes the
  kernel (name/op/operator), the emitters remain deterministic KIR→code.
