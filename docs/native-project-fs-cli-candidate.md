# Candidate: declared FS35 / CLI38 in native x86 projects (AWAI-97)

The existing locked x86 project route rejects every capability with E7101,
including native filesystem adapters needed by Awai's signed admission
checkpoint service. Its ordinary single-source runtime already has the
typed capability-call emitter and host grant enforcement.

The complete replacement module
`seed/experimental/98-x86_64-project-fs-cli.kotoba` proposes extending the
production `seed/98-x86_64-project.kotoba` to admit explicitly declared wires
3 (`:io/write`), 4 (`:io/write-error`), 7 (`:clock/now`), 35
(`:fs/app-data`), and 38 (`:cli/args`). A module that calls them must declare
`:capabilities`; a missing declaration or a declared set that excludes a used
wire refuses E2176. All other wires remain E7101, including unused functions
that call them. The existing namespace, type, export, source-lock, opcode and
resource limits remain in force. Unsupported wires cannot be granted by a
namespace declaration. Emission creates no runtime grant.

The existing native runner independently requires `KEXE_ALLOW` and a scoped
filesystem grant. The exact importing fixture performs a locked write, file
fsync, rename, directory fsync, read and unlock; separate branches exercise
stdout and stderr. Native negative controls cover missing/empty declarations,
unsupported wire, ungranted stdout/stderr/clock/FS/CLI, out-of-scope paths and
symlink escape. The original multi-module project corpus and its
pin/unused-declaration refusals are also retained.

```text
python3 scripts/seed/check-x86-project-fs-native.py \
  --compiler /absolute/path/to/current-native-baseline \
  --compiler-sha256 <exact-baseline-image-sha256> \
  --runner /absolute/path/to/same-toolchain-native-runner \
  --output /absolute/private/new-output-directory --derive
```

The candidate derives from the **entire current 47-module FULL-MANIFEST**,
including the adopted compiler core. An existing Amu-produced native public
image builds F1, F1 builds F2 and F2 builds F3 on native x86 Linux; all three
must be byte-identical. No hosted compiler, C loader, emulation, source-module
flattening or alternate language resolver is used. Full-source unity here is
the compiler's established self-rebuild route, not a way to bypass project
admission for an application.

`--derive` stages every original FULL-MANIFEST source, substituting exactly
that one complete experimental module, then builds all three compiler
images and the runner with Amu native. It records every selected source and
the substitution. This is byte staging of the existing compiler build,
not a Python implementation of language resolution or compilation.

This is an experimental source proposal. The production source module,
public `bin/amu`, descriptor, ARM bootstrap root and identity policies remain
unchanged. Normal source/image preflight still applies to their exact bytes.
Full producer/root/product and controller qualification must be regenerated
before adopting the replacement into production FULL-MANIFEST. An x86 fixed
point and the bounded FS/CLI probes do not complete that adoption or qualify
other effectful project profiles. The Awai store can be tested against this
explicitly derived and pinned candidate; its ordinary pure authority gate
also continues to use the existing compiler.

## 2026-11-02 Itonami clock + filesystem follow-up

The Amu candidate source and focused fixture additionally admit declared
wall-clock wire 7 for Itonami's cron-store route and output wires 3/4 for
Kotoba CLI responses. The allowlist is limited to 3, 4, 7, 35, and 38; source
still must declare each capability, and the runtime separately requires
`KEXE_ALLOW`. Positive controls check returned wall time and exact stdout /
stderr markers. No-grant controls verify named refusal for output and clock
before any filesystem effect, and undeclared capabilities must fail compile
admission. Existing FS35/CLI38, scope, symlink, and unsupported-wire controls
remain.

This is a follow-up to the completed AWAI-97 FS35/CLI38 candidate, not public
compiler adoption. It is intended to unblock the standalone Itonami cron-store
gate. The updated 60-module selfhost derivation and exact native run must pass
before the Itonami gate is repinned; public compiler/root adoption remains a
separate qualification.
