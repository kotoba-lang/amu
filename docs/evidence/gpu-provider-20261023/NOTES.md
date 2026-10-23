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

## What the receipt shows

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

## Limits

* The fake layer has no GPU: a dispatch does nothing. The Vulkan layer is the
  next step, and it runs on GPU hosts only.
