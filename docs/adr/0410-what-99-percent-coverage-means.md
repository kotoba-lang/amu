# ADR 0410: what 99% coverage means

- Status: Accepted (owner decision, 2026-11-06, JUN-890).
- Date: 2026-11-06
- Related: JUN-889 (the coverage plan), JUN-890, ADR 0409, ADR 0407.

## Context

JUN-889 aims for Amu selfhost to run on 99% of the world's devices. That number needs a denominator, a meaning for "runs", and a way to measure it that cannot overclaim.

## Decision

### Denominator

The denominator is StatCounter's share of worldwide page views by operating system across all platforms, pinned to one month in `docs/qualification/target-coverage/table.json`. The current pin is 2026-10:

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

The scoreboard has no measured split for these slices:

- Android's 32-bit and x86 share
- Windows on Arm's share
- Intel's share of Macs

So the report gives two bounds. The **lower** bound credits an OS only when every listed target passes. The **upper** bound credits it when any target passes. A measured split can be added to the table, and then both bounds use it.

**99% is met only by the lower bound.**

### Android ABI measurement (KOTOBA-238)

The shares for `armv7-android` and `x86_64-android` are unknown. The public StatCounter chart has no ABI dimension.
On 2026-11-26, the October worldwide all-platform HTML summary showed the pinned 44.56% Android share. The
single-month CSV returned 44.70% Android and only OS totals. StatCounter allows revisions for 45 days, so record
the source, retrieval date and bytes for any proposed update. All calculations below use the accepted 44.56% pin.
[StatCounter chart](https://gs.statcounter.com/os-market-share/all/worldwide/) · [October CSV](https://gs.statcounter.com/chart.php?device_hidden=desktop%2Bmobile%2Btablet%2Bconsole&statType_hidden=os_combined&region_hidden=ww&granularity=monthly&fromInt=202610&toInt=202610&fromMonthYear=2026-10&toMonthYear=2026-10&csv=1) · [StatCounter methodology and revision policy](https://gs.statcounter.com/faq)

The public sources reviewed supplied no comparable October ABI counts. Play Console's device catalog CSV lists
model specifications and supported ABIs. Reach and devices can break down install-base data by ABI, with
Google Play-wide active-device data available to select partners. A device can appear under multiple supported
ABIs. These sources measure models or active devices in Play cohorts. The October StatCounter numerator and
denominator both count page views. [Play device catalog](https://support.google.com/googleplay/android-developer/answer/9859371) · [Play Reach and devices](https://support.google.com/googleplay/android-developer/answer/10770882) · [Android distribution dashboard](https://developer.android.com/about/dashboards/)

1. Request aggregate counts for October 2026 from StatCounter, if the underlying records support ABI classification.
   Specify the same worldwide, all-platform OS page-view population and revision as the pin, including the same month
   boundary, OS classification and filters. Ask for total page views, Android page views, Android page views by mutually
   exclusive native ABI, unclassified counts and the classification method. Reconcile those totals to the pinned OS
   series before using them.
2. Assign each Android page view to one bucket using the widest natively usable Android app ABI on the device and OS.
   Use `arm64-v8a` for native Arm64 even when `armeabi-v7a` also works, and `armeabi-v7a` for Arm devices whose Android
   app ABI is limited to Armv7. An Arm64 CPU with a 32-bit Android userspace can belong to the latter bucket. Count
   `x86_64` only with evidence that Android can run 64-bit x86 code on x86-64 hardware without translation. Track native
   `x86` (32-bit) and other known unlisted ABIs as uncovered. Keep separately identified ChromeOS in its OS category,
   including where it runs Android apps through Arm translation. Keep ambiguous Android-attributed views, including
   possible emulation, translation or ChromeOS misclassification, in the unclassified bucket.
   [Android NDK ABIs](https://developer.android.com/ndk/guides/abis) · [ChromeOS app compatibility](https://developer.android.com/develop/devices/chromeos/learn/device-support)
3. If aligned October data is unavailable, run a future full-month page-view cohort and label it with its own month,
   sites and population. Instrument participating sites to count eligible page views once, including first-page visits
   and missing hints, across regions, platforms and browser families. Where an opt-in device sample is available,
   validate the classifier against the hardware ISA, Android userspace and native ABI capability. `Build.SUPPORTED_ABIS`
   supplies an ordered capability list. Browser architecture and bitness hints can describe the browser environment and
   can be missing or ambiguous. Record disagreement and non-response. Keep the cohort result as a proxy unless the sampling
   frame is aligned and validated against the StatCounter population for that month and the owner approves a same-month
   denominator pin. Use Play or app data, vendor and OS version only to inform the investigation. Derive any proposed
   scoreboard weights from aligned page views.
   [Android Build API](https://developer.android.com/reference/android/os/Build#SUPPORTED_ABIS) · [Chrome User-Agent Client Hints](https://developer.chrome.com/docs/privacy-security/user-agent-client-hints) · [Chromium hint implementation](https://chromium.googlesource.com/chromium/src/+/1e8e9dc69d467/components/embedder_support/user_agent_utils.cc)
4. Preserve source metadata, the classifier version, filters and aggregate counts by geography, platform and browser so
   the result can be recomputed. Let `N` be all Android page views, `n` the confirmed page views for an ABI or a group of
   ABIs, and `u` the unclassified Android views. Confirmed share is `n / N`. The classification-only range is `n / N` to
   `(n + u) / N`, with the unknown pool allocated at most once for the group. Multiply by the pinned Android share to
   convert to worldwide percentage points. Report sampling and population-coverage uncertainty as well, including
   unsupported browsers and missing regions or sites. Use a defensible upper bound on the **combined** uncovered share
   for an omission decision, including unresolved traffic that could be uncovered. If the uncertainty cannot be bounded
   against the pinned population, the share remains unknown.

The report marks the Android split `isaSplitMeasured: false`. A measured split in the current schema must cover exactly
the listed targets and total 100% of the Android slice. It takes point weights, so carrying uncovered or unresolved mass
into a future split requires an explicit way to account for that mass without credit. Review any scoring input update with
the owner. ABI counts determine market weight. Each Android L1 pass separately requires the physical-device evidence
above. The Android A1 result remains a device observation outside the scoreboard's receipt set.
[Android A1 observation](../qualification/android-a1/20261106/README.md)

### Receipt snapshot

From the 2026-11-06 snapshot at commit `f6c6ea215`:

| | |
| --- | --- |
| Lower bound | 2.15% (Linux) |
| Upper bound | 8.09% (Linux and macOS) |
| Development hosts at L3 | `x86_64-linux`, `aarch64-macos` |

`aarch64-linux` passes L1 and L3 but has no L2, because it has no public entry (JUN-899). The Mac cells pass with `fullRuntimeQualified: false` and `independentUserQualified: false`, which the report lists as caveats. The report does not measure a common corpus yet, because the common gate does not exist yet (JUN-897). Until it does, passing cells show that each target's own gate passed, not that all targets passed the same tests.

## What the numbers imply

The listed total is 99.18%, leaving **0.18 percentage points** for all uncovered traffic within that total. The joint
share for `armv7-android` and `x86_64-android` could be anywhere from 0 to 44.56 worldwide percentage points. Both draw
from the same Android slice, so the 44.56-point limit applies once. If every other listed requirement qualifies, the
largest possible allowance for omitting both is 0.18 points, about 0.404% of Android page views (`0.18 / 44.56`).
The same margin, if spent entirely on Intel Macs, would cover about 3.03% of macOS page views. Other uncovered traffic
within the listed total reduces the allowance. A measured omission is defensible only if the L1 lower bound still
reaches 99.00% after charging the joint upper bound of all uncovered listed traffic and applying the report's
basis-point flooring.

Android contributes 0.00 points to both bounds in the stored snapshot because none of its rows passes L1. The snapshot's
8.09% upper bound comes from Linux and macOS. If `aarch64-android` alone gained L1 while the other rows kept their snapshot
states, the current unmeasured-split rules would give 2.15% lower and 52.65% upper. If every other listed OS slice also
earned full L1 credit, the bounds would be **54.62% lower and 99.18% upper**. The 44.56-point gap in the latter scenario
is the unresolved Android slice. With an accepted split, the loss from the 99.18% ceiling would be the measured uncovered
worldwide share, with any other gaps and basis-point flooring also charged against the margin.

JUN-889 expected x86_64 and aarch64 to be enough. That is unproven, and 32-bit Android could disprove it.

## Platform limits checked in primary sources

- **iOS**: [App Review Guideline 2.5.2](https://developer.apple.com/app-store/review/guidelines/) says apps may not "download, install, or execute code which introduces or changes features or functionality". It has a narrow exception for educational apps. L2 and L3 are recorded as prohibited for App Store apps, and JUN-909 sets the final level. L1 is not affected, because the code ships in the bundle.
- **Android**: [Android 10's behavior changes](https://developer.android.com/about/versions/10/behavior-changes-10) say untrusted apps targeting API 29 or higher cannot `execve()` files in the app's home directory. L2 and L3 stay open in JUN-909.

## Refused and not decided

- This report is not a gate. `AGENTS.md` keeps verdicts with the native controller, so the report sets `gateVerdict: false`. A digest shows that a receipt has not changed since collection. It does not authenticate the receipt.
- `armv7-android` and `x86_64-android` stay listed pending an approved decision based on measured shares. The measured-share acceptance condition in KOTOBA-238 remains open.
- Refreshing a snapshot is manual (`scoreboard.cljc collect`). Nothing regenerates it after each merge.

## Consequences

- JUN-890's `verify-target-qualification` does not exist on `main` or in its history, so this report is new rather than an extension. The inputs are the receipts CI already uploads.
- Without a refreshed snapshot, the number falls to 0 after 30 days.
- `scripts/coverage/test_scoreboard.cljc` damages copies of the snapshot and requires the number to fall.
