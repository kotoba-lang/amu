# GPU provider receipts (ADR 0371 step 6, JUN-344)

`tools/gpu_provider.kotoba` serves `:gpu/compute` protocol v1 on a device
layer. It is a platform-linked image (`--format platform-linked`), built by
the selfhost compiler.

## Files

* `fake-x86_64-qemu.json`: `scripts/seed/check-gpu-provider.py`, with the fake
  device layer (`tools/gpu_device_fake.kotoba`).
  * The build phase ran on arm64 Linux (podman machine, native), with the
    root F as `--compiler`.
  * The run phase ran in an x86_64 Debian 12 container (glibc 2.36) under
    qemu-user.
  * The provider under the static launcher, answering a static guest's
    wire-42 session, needs a native kernel. It runs in the `qualify-x86_64`
    CI job, through `check-x86_64-native.py`'s ADR0371 list, in every tier.
* `gad-radv.json`: the same script's `gpu` phase, with the Vulkan layer
  (`tools/gpu_device_vulkan.kotoba`).
  * It ran on gad: x86_64, Linux 7.0, Radeon 8060S Graphics (RADV GFX1151),
    Vulkan 1.4.318.
  * The build phase ran on arm64 Linux.
  * By the owner's decision of 2026-10-22, libvulkan runs on GPU hosts only.
    The provider ran from a temporary directory that was removed afterwards.

* `gad-radv-confined.json`: the same `gpu` phase after the provider confines
  itself (step 6 (4)), with the grant's default `:confinement :required`.

## What the fake-device receipt shows

* **23 sessions**, each with fd 3 the grant and fd 4 the report:
  * every verb, with its exact answer;
  * the provider's refusals (19 on), and the table's refusals passed
    through;
  * a request that is not ASCII;
  * device lost and fence timeout (the fake layer's faults), which end the
    session;
  * a frame over one runtime value;
  * the buffer table (4096), the pipeline table (128) and the dispatch limit
    (2048), at their bounds;
  * answers that cannot be written;
  * ordinary device errors (the fake layer's non-terminal faults): refused
    as `gpu/device-error`, and the session goes on;
  * an artifact changed on disk after its verification: MAP refuses it as a
    digest mismatch, while PIPELINE keeps using the module bytes it verified;
  * truncated frames (a short header, a short payload), which end the
    session as `:truncated-request`, not as a clean end of file.
* **Grants**: one well-formed grant, and 11 refused ones (another key, a
  repeated key, no wire 42, a missing key, a short digest, a backslash, a
  timeout of 61, trailing bytes, an unknown kind, an empty grant, no fd 3).
  With a refused grant the provider serves nothing and exits 2. A device the
  layer lacks exits 3.
* **Report**: the image digest in each report equals the image's SHA-256,
  and `:needed` lists the image's DT_NEEDED names (`["libc.so.6"]`).
* **Confinement.** Under qemu-user the grants say `:confinement :if-available`,
  and the reports show Landlock and the seal as `:unavailable`. The default,
  `:required`, fails closed there: no request is served, the report says
  `:confinement-failed`, and the exit status is 5. Natively, in the CI job,
  the reports must show a Landlock ABI version and `:seal :ok`.

## What the gad receipt shows

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
* **Vulkan's rules where the protocol is wider**:
  * an unaligned WRITE and READ (copies are widened to 4-byte spans, and a
    write reads the span's other bytes first);
  * ZERO of a 3-byte buffer (buffers are a multiple of 4 bytes, so the
    whole-size fill covers every byte);
  * a workgroup count over the device's limit, refused as
    `gpu/device-error`, after which the session goes on.
* **Submits** took 30-50 us each, measured on the host clock.
* **Report** (fd 4): device, 59 served, 1 refused, `:eof`, the image's
  SHA-256, its DT_NEEDED names and the kernel release.
* **Confined** (`gad-radv-confined.json`): RADV ran the same requests after
  Landlock (ABI 8; read access to the three artifacts only) and the seal, with
  identical results. This includes the 70 MiB MAP, opened after Landlock
  through its rule. The report adds:
  * the driver, `radv Mesa 25.2.8-0ubuntu0.24.04.2`;
  * the mapped libraries with their SHA-256: the loader
    `libvulkan.so.1.3.275` and the ICD libraries the loader opened.

## Limits

* The fake layer has no GPU: a dispatch does nothing.
* The dot and kdot fixtures and the decode guest's argmax chain are the
  step's acceptance. They need the KIR v2 inference kernels (ADR 0372 step 3),
  which do not exist yet.
* Not covered here:
  * the launcher's fixed provider environment (the shader cache);
  * shaderFloat16 and integer dot product enablement;
  * B70 (ANV);
  * the launcher on a GPU host.
