# Native Linux ARM C-reference preparation — 2026-10-26

Tracking: KOTOBA-140. This is the separately declared C comparator, not an
Amu compiler/runtime/CDCI dependency or a performance result.

## Environment and boundary

The existing local ARM image
`703c3aa026ac7338c371501b9fa119b204f14bbf1098d92d3d9a5a6e13372093`
ran with network disabled, a read-only container root and repository/upstream
mounts, no capabilities, no-new-privileges, and one admitted command through
the existing shared two-slot native build queue. No image pull or package
installation occurred. Native Linux reported aarch64; the selected GCC and
every generated C executable are actual machine183 ELF artifacts.

The container ran under the existing AppleHV Linux ARM VM. That VM is useful
for correctness/build preparation, not an admitted quiet measurement host.
Its missing physical thermal/frequency qualification is not supplied by this
packet. No other machine received source/binaries, and no service changed.

An initial tool-version inspection of the cached full Python bookworm image
found amd64, not ARM. No C workload was built or measured with that image;
it was rejected for native ARM evidence. This packet uses only the exact
ARM image above, native GCC13.3.0 and Python3.12.3.

## Preserved preflight failure

The first C-stager preflight rejected the real GCC image because its new
C-only ELF reader initially admitted SysV OSABI0 but not GNU/Linux OSABI3.
The observed GCC identification bytes were
`7f454c46020101030000000000000000`, type2, machine183. It exited2 before
creating the preparation directory or invoking a C compiler/workload.
`preflight-r1.json` preserves the observation and its evidence limit: the
first script source snapshot/hash was not captured. It is not represented
as a successfully built corpus or retrospectively pinned source version.

The C-only reader now handles Linux OSABI0/3 while refusing foreign OSABIs,
foreign ISAs and malformed program headers. Amu's ELF/runtime rules and all
native guest/resource boundaries were not changed.

## Original C corpus and executed verifier control

All40 pinned upstream inputs match revision
`09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`. All37 C/header inputs are covered;
extra/ignored or missing C/header inputs and symlinks refuse. Positive builds
use only a private byte-identical snapshot, original main/verifiers and the
existing pinned timing board. The GPL-3.0-or-later notices and exact COPYING
file are retained with the snapshot. Kotoba's license is not changed.

All19 original workloads built with explicit GCC13.3.0 and fixed flags
`-O2 -std=gnu11 -DWARMUP_HEAT=1 -DGLOBAL_SCALE_FACTOR=32768` and passed their
original verification exits with empty runtime stderr. No source body,
registered C count, warmup policy or positive verifier was changed. All
compiler/build/executable hashes, arguments and sanitized child environment
are in `observations-r2.json`; raw process streams and exact observer/source
copies are in the companion record archive. Generated ELF binaries remain
in task scratch, identified by their exact recorded hashes, and are excluded
from the compact Git archive.

A separate CRC32 source changes only the expected verifier value11433→11434.
It is built with the same flags/counts and actually returns1 with empty
stderr and the expected raw timing frame. It never enters the positive
corpus. This is C-side verification rejection, not a claim that the complete
seven protocol controls or the native Kotoba campaign gate have passed.

Preparation terminated successfully after159.3 seconds. That is preparation
wall time, not a workload measurement, speed ratio or score. All41 process
stdout/stderr hashes, staged input/observer hashes,19 actual ARM ELF hashes,
verification exits and the exact changed control were read back and matched.
Sixteen source/record tests and the previous54 proof tests pass; synthetic
tests do not replace the actual C executions described above.

## Still open

All performance/campaign/authority/algorithm-equivalence/protocol-completeness
flags remain false. C raw timing frames are retained only as correctness
diagnostics. Same-host Kotoba/C builds and equivalence review, actual CPU/
thermal/power admission,760 scheduled samples, paired statistics, complete
executed protocol controls, external independent reruns and upstream/official
disposition remain required. The Linux x86 C path has not been executed in
this packet. No C preparation command was added to mandatory native CDCI.

## Count-binding checkpoint r3 and final observer r4

The next observer verifies the frozen count-table hash, matches every
upstream LOCAL_SCALE_FACTOR to that mapping, checks the signed scaled-count
bound, and records C scale iterations, original Kotoba count and declared
normalization for each of the19 rows. These are metadata/consistency checks,
not changed counts or a new measurement profile. Original C bodies, flags,
positive verifiers and isolated expected-value mutation are unchanged.

`observations-r3.json` and `native-arm-r3-records.tar.gz` retain that successful
full19 execution, including its exact observer/source/raw copies; the earlier
r2 records remain historical observations of their own observer. A final r4
observer additionally records the isolated control's actual ELF hash beside
its source/count/verifier exit, so it does not rely on a success boolean.
The final r4 observer executed the complete19 and control again; earlier
success was not relabeled as current-observer evidence. Its preparation
terminated successfully after159.5 seconds (not a performance sample).
All19 original verification exits and the actual wrong-expected exit1 passed
readback. All41 raw stdout/stderr pairs,40 staged source hashes,19 native ARM
ELF hashes, registered count bindings, the control source and control ELF
hash, and the retained current observer matched. The compact archive has127
regular files and no ELF binaries. Nineteen C source/record tests plus the
existing54 proof tests pass; all six qualification/authority flags remain
false.

Pinned retained artifacts:

| Artifact | SHA-256 |
|---|---|
| observations-r2.json | `6a017727790278eb237caf6f643944f65ac110a5581f3fd04a84e99691ce1cc2` |
| native-arm-r2-records.tar.gz | `d790dafcbb5b3a3060b18951517ca99ad12f093b983a008a3e53c01c4fe714e4` |
| observations-r3.json | `4af49324b67382b9780ae737a119cd256402c07797655791d6fba80e43997d61` |
| native-arm-r3-records.tar.gz | `93cc0334c91f279cc9d3f742485100dbc6ca31b74b377bcae72f051d5404113a` |
| observations-r4.json | `68fa78f7fefac41a7f56b4292e190c3dd1c3f829b0cb6ddb428b93e7c1533a7e` |
| native-arm-r4-records.tar.gz | `aa280d5e386b272440e6d3c0b8db19dcc6711baad02cfa3479ebaabc312af85c` |

All archives exclude generated ELF binaries; complete ELF outputs remain in
task scratch. They retain original GPL notices/COPYING alongside copied C
sources and the isolated expected-value-only control. No performance or
native qualification authority follows from these preparation observations.
