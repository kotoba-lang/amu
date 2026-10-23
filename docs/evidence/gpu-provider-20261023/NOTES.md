# GPU provider receipts (ADR 0371 step 6, JUN-344)

`tools/gpu_provider.kotoba` serves `:gpu/compute` protocol v1 on a device
layer. It is a platform-linked image (`--format platform-linked`), built by
the selfhost compiler.

## Files

* `gad-radv.json`: `scripts/seed/check-gpu-provider.py`.
  * The build phase ran on arm64 Linux (podman machine, native), with a
    compiler built from these sources.
  * The `gpu` phase ran on gad: x86_64, Linux 7.0, Radeon 8060S Graphics
    (RADV GFX1151), Vulkan 1.4.318.
  * By the owner's decision of 2026-10-22, libvulkan runs on GPU hosts only.
    The provider ran from a temporary directory that was removed afterwards.

## What the receipt shows

* **INFO** is `Radeon 8060S Graphics (RADV GFX1151)|1.4.318|1024|1`, and
  **DEVCLASS** is `integrated`. Among RADV and lavapipe, the device choice
  took the integrated GPU, as the C broker did.
* **Transfers.** WRITE, WRITEDEC, READ and ZERO go through the staging buffer.
  A MAP of 70 MiB spans more than one 64 MiB staging chunk. It was read back
  at the start, across the chunk edge and at the end. The MAP took 5.4 s,
  which includes the provider's own SHA-256 of the file.
* **Kernels.** These are KIR v1 modules written by Amu (ADR 0372), not glslang.
  * `z = x + y` for n = 1000 ran:
    * at once;
    * in a recording whose second dispatch reads the first's output (the
      barrier);
    * in a kept command buffer, submitted and then replayed;
    * as two independent DISPATCHC.
  * Per-workgroup sums of 1..1000.
  * Every value is exact in f32, so each READ is compared byte for byte.
* **Submits** took 30-50 us each, measured on the host clock.
* **Report** (fd 4): device, 48 served, 0 refused, `:eof`, the image's
  SHA-256 and the kernel release.

## Limits

* The dot and kdot fixtures and the decode guest's argmax chain are the
  step's acceptance. They need the KIR v2 inference kernels (ADR 0372 step 3),
  which do not exist yet.
* Not covered here:
  * confinement after device creation;
  * the libvulkan/ICD paths and digests in the report;
  * the driver properties;
  * shaderFloat16 and integer dot product enablement;
  * B70 (ANV);
  * the launcher on a GPU host.
