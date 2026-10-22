# gpu-vendor-dispatch: first hardware measurement -- M1 Max INFO probe (2026-10-18)

Tracker: JUN-58 (Apple, parent JUN-55). Machine-readable twin: `info-probe.json`.

## What ran

```
$ date "+%Y-%m-%dT%H:%M:%S%z"     # 2026-10-18T20:36:18+0900
$ git rev-parse HEAD              # bea7b9b24a44ebd3d5108e8e356a39c6bed5912d
$ kbb --backend sci scripts/test-gpu-compute.cljk
GPU-COMPUTE	OK	Apple M1 Max|1.3.357|1024|1	aarch64-macos
$ echo $?                         # 0
```

Host: Apple M1 Max, macOS 26.4 (BuildVersion 25E246), aarch64.
The probe answered the identical string on two consecutive runs (20:33 and
20:36 JST). Prerequisites present: `/opt/homebrew/include/vulkan/vulkan.h`,
`/opt/homebrew/lib/libvulkan.dylib` (MoltenVK via Homebrew). A fresh worktree
needs `npm ci` first or the amu compile refuses (`nbb engine must name an
existing cli.js file`) and the script exits 3 -- that is a could-not-run, not
a measurement.

## What the fields mean

`scripts/test-gpu-compute.cljk` requires exactly four fields;
`tools/kexe_gpu_vulkan.c` lines 544-546 format them as
`"%s|%u.%u.%u|%u|%d"` from `VkPhysicalDeviceProperties`:

| field | source | value on this host |
|-------|--------|--------------------|
| device | `deviceName` | `Apple M1 Max` |
| api | `apiVersion` major.minor.patch | `1.3.357` (MoltenVK) |
| maxWgX | `limits.maxComputeWorkGroupSize[0]` | `1024` |
| unified | `deviceType == VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU` | `1` |

## What this measures (MEASURED)

- The device name, so vendor classification (:apple) is now checked against
  real hardware, not a string literal in a test.
- The device's Vulkan apiVersion as the loader reports it: 1.3.357.
- `maxComputeWorkGroupSize[0] = 1024`: on this device ADR-0002's [1, 1024]
  workgroup bound reaches exactly the hardware limit at the top end.
- The device classifies as integrated (the `unified` field is 1).

## What this does NOT measure (still UNMEASURED)

- **The optimal workgroup size.** The probe reports a limit, not a tuning
  result. The apple row in `kotoba.compiler.accelerator-targets`
  (`:size 256`) stays `:measured? false`; replacing it needs a per-vendor
  workgroup sweep (JUN-56 follow-up / JUN-58 next slice).
- Any performance or timing number.
- MSL or CUDA execution: no execution path exists. The wire is Vulkan only,
  so the dispatch answer for this device through the runtime path is
  `:wgsl-v1` (`:vulkan` api decides), even though the vendor default is
  `:msl-v1`.
- Any other vendor's hardware (JUN-57/59/60 remain hardware-less).

## Wiring

`kotoba.compiler.accelerator-targets/device-from-info` parses this probe
answer into a device descriptor whose facts carry `:measured? true`; feeding
that descriptor to `recommend` still answers `:measured? false` for the
workgroup row. The test
`kotoba.compiler.accelerator-targets-test/info-answers-parse-into-measured-device-facts`
replays the exact recorded string.
