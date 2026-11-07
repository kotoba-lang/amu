# Android A1: does the Linux ARM64 static image run on a device? (JUN-902)

Measured 2026-11-06 on one physical device. This is an observation, not a qualification. It adds no target, no gate and no receipt that `scripts/coverage/scoreboard.cljc` reads, so the coverage number does not change.

## Answer

**The existing `aarch64-linux` static image runs unchanged inside a normal Android app, as long as the image ships in the APK.** No `bionic` import, no recompile and no C host were needed. This answers the question ADR 0409 left to A1: an Amu-produced image can work.

| Question | Result |
| --- | --- |
| Does a compiled program run in a normal app? | Yes, from `nativeLibraryDir`, with `extractNativeLibs=true` |
| Does the runtime's seccomp filter install under the app's filter? | Yes (`Seccomp: 2` before start; the SIGSYS control still fires) |
| Does every wire that was run work in the app? | Yes. Wire 42 was not run |
| Does the compiler run in the app? | Yes. It reproduces the pinned root byte for byte |
| Can the app run what it just compiled? | **No.** SELinux denies `execute_no_trans` on `app_data_file` |
| Does `extractNativeLibs=false` work? | **No.** The library directory is empty, so there is nothing to `exec` |
| Does it work on a 16 KB kernel? | **Not measured.** The layout is at risk, see below |

So L1 looks reachable through the APK. In-app L2 is blocked by the platform on what it can run, not by what Amu can compile: that stays with JUN-909.

## Device

Google Pixel 10 Pro Fold (`rango`), Tensor G5, Android 17 (SDK 37), build `CP3A.261005.005`, patch 2026-10-05, kernel `6.6.127-android15-8-...-4k`, page size 4096, SELinux Enforcing, bootloader locked, verified boot green, 15.2 GiB RAM. Details are in [`out/device.txt`](out/device.txt). JUN-862 records the same device.

**No emulator was used.** Every Android result here comes from the physical device. The control is an arm64 Linux container (`debian:12-slim`, kernel 6.15, on Apple silicon under hardware virtualization). It is not Android.

## Inputs

Root `seed/bootstrap/aarch64-linux-static-root.elf`, 4,178,432 bytes, sha256 `e53fedb6...a764f`, at `c265c6503`. The root, `seed/FULL-MANIFEST` and modules 77 and 80 are unchanged at this document's base, `960aff161`.

## Results by environment

| | `adb shell` (`u:r:shell:s0`, no seccomp) | Normal app (`untrusted_app_34`, `Seccomp: 2`, target SDK 36, not debuggable) | Linux control |
| --- | --- | --- | --- |
| hello compiled on the device, exit 42 | pass | pass | not run |
| seccomp installs, SIGSYS on a call outside the filter (exit 120) | pass | pass | not run |
| `KEXE_CPU_SECONDS` SIGXCPU, `KEXE_WALL_SECONDS` SIGALRM, stack SIGSEGV | pass | pass | not run |
| Rebuild the compiler; F1 equals the pinned root | yes | yes | not run |
| F1 compile and pack, seconds | 29 + 2 | 205 + 16 (screen off, background cgroup) | not run |
| Peak RSS of the compile | 239,484 kB | not sampled (236,160 kB seen in `ps` during the compile) | not run |

The hardening results match the arm64 CI receipt for the same probes. The compiler used about 240 MB on a 16 GB device. It was not killed in the background. A low-memory device was not measured.

The app's F1 compile was slower because the screen was off and the process stayed in the `bg` policy. The foreground speed of an app was not measured.

## Wires

Pass means the guest's expected result, and a run without the grant was refused by name (`KEXE_CAP {:wire N :refused :not-granted}`, exit 120). Syscalls are read from `seed/77-aarch64-static-rt.kotoba` at the input commit. They are not traced.

| Wire | Name | Main syscalls | `adb shell` | Normal app | Linux control |
| --- | --- | --- | --- | --- | --- |
| 3 | `:hash/sha256` | none | pass | pass | pass |
| 7 | `:clock/now` | `clock_gettime` | pass | pass | pass |
| 20 | `:process/spawn` | helper: `clone`, `execve`, `pipe2`, `dup3`, `close_range`, `prctl`, `wait4` | pass (`/system/bin/toybox`) | pass (`/system/bin/toybox`) | pass (`/usr/bin/echo`) |
| 23 | `:entropy/draw` | `getrandom` | pass | pass | pass |
| 35 | `:fs/app-data` | `openat2`, `openat`, `pread64`, `fstat`, `flock`, `fsync`, `renameat2`, `unlinkat`, `mkdirat`, `fchmod` | pass (13 cases) | pass (13 cases) | pass (13 cases) |
| 37 | `:io/write` | `write` | pass | pass | pass |
| 38 | `:cli/args` | none | pass | pass | pass |
| 39 | `:io/write-error` | `write` | pass | pass | pass |
| 40 | `:sys/cwd` | `getcwd` | pass | pass | pass |
| 41 | `:io/read` | `read` on fd 0 | pass | pass | pass |
| 42 | `:gpu/compute` | not measured, needs a provider | not run | not run | not run |
| 43-47 | net | `socket`, `bind`, `listen`, `connect`, `accept4`, `sendto`, `recvfrom`, `ppoll` | pass (loopback) | pass (loopback) | pass (loopback) |

The FS2 results use the scope set-up from `scripts/seed/check-native-fs2.py`. The `adb shell` and control transcripts are identical once the directory is normalized.

Net was loopback only. It also passed in an app **without** the `INTERNET` permission, which was not what I expected. External network was not measured, so this says nothing about whether `INTERNET` is needed to leave the device.

## Where a normal app can execute from

| Path | Result |
| --- | --- |
| `nativeLibraryDir` (`apk_data_file`), `extractNativeLibs=true` | runs |
| `nativeLibraryDir`, `extractNativeLibs=false` | no file: the directory has 0 entries |
| `filesDir` after `chmod 755` | `EACCES`; audit log shows `avc: denied { execute_no_trans }` on `app_data_file` |
| Output the compiler just wrote to `filesDir` | `EACCES`, same denial |
| `/system/bin/sh -c <filesDir path>` | exit 126, same denial |
| External files directory | `EACCES` |
| `/data/local/tmp` | `EACCES` |

`adb shell` can execute from `/data/local/tmp`, so it overstates what an app can do. Results from it alone would have been misleading.

`memfd` and similar routes were not tried. They would work around this rule, and whether to go near it belongs to JUN-909.

## 16 KB pages: not measured, and at risk

This kernel is 4 KB. No 16 KB image is installed on this machine, and the "Boot with 16 KB" option would change the device, which this spike must not do.

The layout, read from the ELF headers:

| Image | LOAD | `p_align` | Segments in the same 16 KB page? |
| --- | --- | --- | --- |
| `hello.elf` | R-X `0x400000`-`0x44d3d0`, RW- `0x44e000`-`0x45e000` | `0x1000` | **Yes**, page `0x44c000` |
| root | R-X `0x400000`-`0x7fb988`, RW- `0x7fc000` | `0x1000` | No, by luck of size |

A 16 KB kernel maps whole 16 KB pages, so `hello.elf`'s data page would overlap the last of its code. That is a prediction from the layout, not a result. `seed/80-aarch64-linux.kotoba:408` rounds the data segment to 4096.

The [Android documentation](https://developer.android.com/guide/practices/page-sizes) says apps targeting API 35 or higher must support 16 KB pages to release updates on Google Play from 2027-02-01, and that LOAD alignment below `2**14` is not compliant. It also describes a backcompat mode, but only for ELF files with an `.so` extension, and a static executable was not tested against it.

## Proposal for A2 (JUN-908)

1. **Form: the static ELF, packaged as `lib/arm64-v8a/lib<name>.so`, with `extractNativeLibs=true`.** Not a real shared library. This keeps one image for Linux and Android, and ADR 0409's table does not need `bionic`.
2. **A thin launcher is required.** An APK needs an entry point, and here a small Java `Activity` started the image with `ProcessBuilder`. This is non-Amu code, though not C. Whether that is acceptable is an owner decision.
3. **Change the ELF layout to 16 KB (`p_align` `0x4000`, data on a 16 KB boundary) before relying on this.** Then measure on a 16 KB kernel.
4. **Then remove `runtime/android/*.c`,** as ADR 0409 says.

A real `.so` loaded through JNI remains the fallback if a future Android blocks `exec` from `nativeLibraryDir`. That would return to the owner, because it needs `bionic` or an equivalent.

## Not measured

- A 16 KB kernel, or any emulator.
- Other devices, SoCs and older Android versions. `openat2` needs Linux 5.6 and `close_range` needs 5.9, and devices on older kernels may lack them.
- Low-memory devices, and an app in the foreground.
- Termux: it is not installed here, and installing it was not needed once a normal app had been measured directly.
- Wire 42, external network, and `clock_nanosleep`.
- Play Store behavior. The APK was installed with `adb install -t`.

## Device state

`adb` wrote only to `/data/local/tmp/jun902` and installed `dev.kotoba.jun902` four times with a throwaway key. Both were removed afterwards and [`out/device-cleanup.txt`](out/device-cleanup.txt) shows the result. The device was not flashed, and no setting was changed.

## Mistakes during measurement

Kept in the transcripts, so nothing has been cleaned up to look better:

- `:io/error` in the first wire run is my wrong keyword. The correct name is `:io/write-error`, and [`out/fs-device.txt`](out/fs-device.txt) has the wire 39 result.
- The FS2 `DIFF` lines in `out/wires-*.txt` come from my missing scope set-up. They are the same on Android and the control, and `out/fs-*.txt` is the correct run.
- `out/app-x-run1-w3deny-harness-bug.txt` has a false `w3-deny` failure, because my harness kept the grant. `out/app-x.txt` is the corrected run.
- The 5 `DIFF` lines in `out/app-x.txt` are the `exec` probes that are expected to be denied. They were written as "would this run" with `want=42`.
- The `w20` spawn output differs between Android and the control because of the arguments I gave it.

## Files

`in/` has the scripts and guests, except `w35fs.kotoba`, which is `seed/tests/fs2-product.kotoba`. `app/` has the probe source and manifests (`x` extracted, `n` not extracted, `i` no `INTERNET`). `out/` has the transcripts. ELF images, APKs and the signing key are not committed: all can be rebuilt from these inputs.

## Tools, used once on the developer's machine

The APK build used a JVM as a one-off local tool, as the workspace rules allow. It is not in any CI, gate or product path.

`adb` 37.0.0-14910828, `javac` 21.0.1, `d8` 9.0.3-dev, `aapt2` 2.20-14042983, `apksigner` 0.9 (build-tools 36.1.0, `android-36`), `podman` 5.6.0, `debian:12-slim` `sha256:ec8534cd...757a`.

```bash
adb shell sh /data/local/tmp/jun902/probe1.sh
adb shell sh /data/local/tmp/jun902/probe2.sh
adb shell sh /data/local/tmp/jun902/wires.sh /data/local/tmp/jun902 /system/bin/toybox ARG_SEPecho
adb shell sh /data/local/tmp/jun902/fs.sh /data/local/tmp/jun902
adb shell sh /data/local/tmp/jun902/fixed.sh
```

```bash
adb install -t x.apk
adb shell am start -n dev.kotoba.jun902/.Probe
```
