# ADR 0409 -- Declared imports of OS system libraries are platform, not a legacy dependency

- Status: **Accepted**. Policy only: this change adds no target, no import and no gate.
- Date: 2026-11-06
- Owner decision, 2026-11-06: 「推奨案で確定」 on the recommendation in JUN-891.
- Amends: rule 6 of [selfhost priority](../selfhost-priority.md), which now has a rule 7.
- Related: JUN-889 (the coverage plan), JUN-284 (Android C host), ADR 0371, ADR 0405, JUN-417.

## Context

JUN-889 plans for about 99% of devices by OS share. Windows and iOS are about 48% of that share. The Linux route
reaches the kernel through raw system calls and imports nothing. That shape cannot be assumed on those two systems:

- Apple does not support binaries that make direct system calls, and gives no compatibility guarantee for the kernel
  system call interface. Compatibility is promised at the dynamically linked system libraries.
  ([QA1118](https://developer.apple.com/library/archive/qa/qa1118/_index.html))
- Windows system call numbers are not a published interface. This is general knowledge; no primary source was
  confirmed for it when this ADR was written. W1 (JUN-901) confirms it before relying on it.

Rule 6 names only the GPU driver stack as platform, and only inside a provider process. Nothing said whether a compiler
or a program may call the system library of the OS it runs on.

## Decision

An image may import the system library that the OS itself provides, when the import is declared and checked.

| OS | Allowed libraries | Notes |
|---|---|---|
| Windows | `ntdll`, `kernel32` | |
| iOS, macOS | `libSystem` | The supported way to reach the Darwin kernel |
| Android | none under this ADR | JUN-284 option (c), below |
| Linux | none | Stays loaderless, with raw system calls and no imports |

This also applies to the compiler and its selfhost closure on those systems. Windows selfhost (JUN-906) needs it.

Still refused:

- C source, a C compiler and a foreign linker in the build
- A loader written or shipped by us, other than the system's own loader
- A C runtime on top of the system library, such as `ucrtbase`, `msvcrt` or `vcruntime`, and C++ runtimes
- Any bundled library, and any library outside the table

GPU drivers stay under rule 6 and ADR 0371. This ADR does not widen where they may be loaded. Adding a library to the
table needs a new owner decision.

## Import check

Each target that uses imports gets a gate. The gate must:

1. Declare the exact set of library and symbol pairs in the image's descriptor, which is pinned like its digest.
2. Read the imports from the image itself (the PE import directory, or Mach-O load commands and bind information).
3. Refuse any library outside the table, and any undeclared or missing pair. The comparison is exact in both directions.
4. Refuse resolving symbols at run time (`GetProcAddress`, `dlsym`, `LoadLibrary`, `dlopen`) unless the pair is declared.
   This keeps the declared set from being bypassed.
5. Include a negative control: an image with one added undeclared import must fail.

Omitted checks count as not qualified. A target without this gate may not ship imports.

## Android: JUN-284 option (c)

The C host in `runtime/android/` is to be replaced by an Amu-produced image, if Android permits one.

Android does not let an app targeting API 29 or higher `execve` files in its home directory, and asks apps to load
only code embedded in the APK. ([Behavior changes, API 29+](https://developer.android.com/about/versions/10/behavior-changes-10))
So the form of the image is still open. A1 (JUN-902) measures it on a device, and A2 (JUN-908) implements it.

`runtime/android/*.c` stays in the tree for now. It is not a product route, and may not be used to qualify Android.
It is removed when A2 lands. If A1 shows that no Amu-produced image can work, this returns to the owner. If that needs
`bionic` imports, the table above needs a new decision.

## Not decided

**Whether macOS keeps its raw system calls or moves to `libSystem`.** The owner was not given a recommendation on this,
so the decision above does not cover it. Today every Amu Mac binary starts through dyld and then uses direct system calls
(ADR 0405), which QA1118 says Apple does not support. C4 (JUN-898) brings this back with a recommendation, because it
changes the public CLI: the README's statement that `bin/amu` has no dylib dependency would no longer hold.

## Consequences

- W1 (JUN-901) and I1 (JUN-903) may be designed with imports. Their gates must implement the check above.
- Nothing changes in current images, so no pin moves. The statements about Linux and the current Mac CLI remain true.
- "No C loader or runtime" now means no C or loader of ours. The OS's own loader and system library are allowed only
  within the table.
