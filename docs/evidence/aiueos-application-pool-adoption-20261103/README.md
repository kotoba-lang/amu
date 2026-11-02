# JUN-757: compiler pins for the application-memory candidate

The previous50539c901 commit implemented kernel-v4 / boot-v7 but retained
older bootstrap/product pins. CI correctly refused its source identity.
This unit regenerates those candidate pins through the existing
`repin-derived-pins.py` two-phase writer; no identity check is removed or
changed. Native Linux execution qualification remains pending.

The exact61-module unity is3986446 bytes, SHA256
`ca7cbfcbaee91840355b2f204e77fd539816b83b1f7dcaf5e88f6f0902ad6e66`.
Both explicit-bootstrap and descriptor-bound native Mac F1=F2 runs match.
The root, packager, Linux ARM/x86 and host-entry artifacts are rehashed by
the writer before installation into this task checkout. The public Mac CLI
is rebuilt against the new root and passes76 native observations plus
three actual aliases. Descriptor/refusal/source-revision controls pass;
`check-native-identities.py` now passes its source/image preflight.
Preflight is not build provenance or a complete native qualification.

The existing Amu-selfhost and Kotoba-native CDCI role artifacts reproduce
their unchanged policy pins. Current and retained old compilers also emit
the same controller bytes. The previously recorded controllerImage hash
in `native-product.json` was4e50f2b5…, while both actually emit6a658b5f….
The candidate field now derives from that artifact. Qualification flags
remain false, and historical qualification evidence remains intact.

The immutable old v3 reference compiler is retained at
`seed/bootstrap/aarch64-macos/amu-kernel-v3-reference.macho`, hash eb59c20f…,
from the previous committed compiler. Its descriptor entry is separate from
the active compiler. Compatibility tests require that declared reference;
rotating the active root cannot make them compare the new compiler to itself.
It is a test input, never a runtime/compilation fallback.

The regenerated compiler repeats the complete local QEMU pool checks
(32 native calls / nine boots) and the actual ValueRuntime composition
(113 cases / twelve cursor guards). Kernel/EFI bytes match the previous
executed evidence. These are local diagnostics, not physical acceptance.

`check-aiueos-application-pool-artifacts-native.py` adds a separate
artifact check to the existing native ARM and x86 qualification jobs. It
requires their actual fixed-point receipts and both actual generations,
then compares complete v4/v7 bytes to the Mac/QEMU evidence. Old-target,
wrong-lock, no-PCI and fabricated-region refusals are required. No existing
case, plan, count, timeout, resource limit or native gate is removed. At this
unit's delivery the new Linux check has not yet executed; CI must prove it.

`receipt.json` binds the native build/cross/public/role/QEMU observations and
current derived files. `cross.json` is the exact cross-build receipt. The
canonical writer and source auditor remain unchanged. The original
application-pool receipt remains historical and unmodified.

Next acceptance: exact-head native ARM/x86 full gates and current controller
execution, followed by full1MiB/2048-part/128-assembly/4MiB reassembly and
service/port/pending-reply/fresh-consent binding. Mac/6600H app install,
actual peer/revoke/reconnect/native SSH, OS daily-use/distributed execution,
all accepted Awai L1 gates and production readiness remain open. No physical
deployment, management-route change, physical-input test or ad spend.
