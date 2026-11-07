# ADR 0410: what 99% coverage means

- Status: Accepted (owner decision, 2026-11-06, JUN-890).
- Date: 2026-11-06
- Related: JUN-889 (the coverage plan), JUN-890, ADR 0409, ADR 0407.

## Context

JUN-889 aims for Amu selfhost to run on 99% of the world's devices. That number needs a denominator, a meaning for "runs", and a way to measure it that cannot overclaim.

## Decision

### Denominator

The denominator is StatCounter's worldwide operating system share across all platforms, pinned to one month in `docs/qualification/target-coverage/table.json`. The current pin is 2026-10:

| OS | Share | Targets listed |
| --- | --- | --- |
| Android | 44.56% | `aarch64-android`, `armv7-android`, `x86_64-android` |
| Windows | 29.08% | `x86_64-windows`, `aarch64-windows` |
| iOS | 17.45% | `aarch64-ios` |
| macOS | 5.94% (OS X 3.74 + macOS 2.2) | `aarch64-macos`, `x86_64-macos` |
| Linux | 2.15% | `x86_64-linux`, `aarch64-linux` |
| Total | 99.18% | |

The pin changes only by a pull request. The month matters: between 2026-09 and 2026-10 the page moved iOS from 19.45% to 17.45% and Android from 42.54% to 44.56%.

Servers and embedded devices are not added to this number. They would need a different unit of measure, and a server's targets are the two Linux rows already listed. AIUEOS bare metal and GPUs stay out of scope, as in JUN-889.

### Levels

- **L1 target**: a program compiled by Amu runs natively on the target.
- **L2 host**: the public CLI's check, compile and run work natively on the target.
- **L3 selfhost**: the compiler rebuilds itself natively on the target and reaches a fixed point.

The 99% is judged at L1. Linux, macOS and Windows are also expected to reach L3, and this is reported separately.

This changes one word of JUN-889, which defined L1 as compiled "from another host". Where a program was compiled does not change what a user gets, and macOS signing happens on the Mac, so a cross-compiling rule would count a working Mac as 0.

### What counts as evidence

A cell passes only when every receipt it names is in the snapshot, unchanged, says the required status and fields, and records the native host. A cell without evidence counts as 0.

- Emulation and simulators never count.
- Hardware virtualization of the same ISA does count, for Linux, macOS and Windows. GitHub's hosted runners are virtual machines, and `seed/bootstrap/aarch64-macos/root.json` records `physicalHardware: false`. Android and iOS require a physical device.
- Evidence older than 30 days counts as 0.
- All receipts in a snapshot must come from successful runs of one commit.

### Unmeasured ISA splits

No public source gives these splits:

- Android's 32-bit and x86 share
- Windows on Arm's share
- Intel's share of Macs

So the report gives two bounds. The **lower** bound credits an OS only when every listed target passes. The **upper** bound credits it when any target passes. A measured split can be added to the table, and then both bounds use it.

**99% is met only by the lower bound.**

### Current number

From the 2026-11-06 snapshot at commit `f6c6ea215`:

| | |
| --- | --- |
| Lower bound | 2.15% (Linux) |
| Upper bound | 8.09% (Linux and macOS) |
| Development hosts at L3 | `x86_64-linux`, `aarch64-macos` |

`aarch64-linux` passes L1 and L3 but has no L2, because it has no public entry (JUN-899). The Mac cells pass with `fullRuntimeQualified: false` and `independentUserQualified: false`, which the report lists as caveats. The report does not measure a common corpus yet, because the common gate does not exist yet (JUN-897). Until it does, passing cells show that each target's own gate passed, not that all targets passed the same tests.

## What the numbers imply

The listed total is 99.18%, which leaves a margin of 0.18 points. Any ISA slice above 0.18% of the world must therefore be supported or measured as smaller. Intel Macs would have to be under about 3% of Macs to be dropped, and 32-bit Android under about 0.4% of Android.

JUN-889 expected x86_64 and aarch64 to be enough. That is unproven, and 32-bit Android could disprove it.

## Platform limits checked in primary sources

- **iOS**: [App Review Guideline 2.5.2](https://developer.apple.com/app-store/review/guidelines/) says apps may not "download, install, or execute code which introduces or changes features or functionality". It has a narrow exception for educational apps. L2 and L3 are recorded as prohibited for App Store apps, and JUN-909 sets the final level. L1 is not affected, because the code ships in the bundle.
- **Android**: [Android 10's behavior changes](https://developer.android.com/about/versions/10/behavior-changes-10) say untrusted apps targeting API 29 or higher cannot `execve()` files in the app's home directory. L2 and L3 stay open in JUN-909.

## Refused and not decided

- This report is not a gate. `AGENTS.md` keeps verdicts with the native controller, so the report sets `gateVerdict: false`. A digest shows that a receipt has not changed since collection. It does not authenticate the receipt.
- `armv7-android` and `x86_64-android` stay listed until a share is measured, so they hold the lower bound down. Whether to drop them later is **not decided**: that needs a measured share, and how to measure it is open (JUN-890).
- Refreshing a snapshot is manual (`scoreboard.cljc collect`). Nothing regenerates it after each merge.

## Consequences

- JUN-890's `verify-target-qualification` does not exist on `main` or in its history, so this report is new rather than an extension. The inputs are the receipts CI already uploads.
- Without a refreshed snapshot, the number falls to 0 after 30 days.
- `scripts/coverage/test_scoreboard.cljc` damages copies of the snapshot and requires the number to fall.
