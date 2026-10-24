# Private PCI resource consumer candidate

The full37 ARM compiler reaches F1=F2, SHA256
dffb92704da855ace032e1a9d2567ee2be79a56938d83a5031217373be0bf140,
with all24 runtime cases and all18 adopted core modules retained. Both
native producer generations reproduce the fixture images/EFI bytes and
source-lock positive/refusal behavior. Native source/artifact readback
binds13 QEMU pass receipts to these exact F2 artifacts; a valid-image
negative control produces no guard pass.

The v6 bootstrap validates the collector catalog, copies it before main,
and rejects resources overlapping RAM/ACPI/runtime descriptors. The closed
policy accepts only absent map entries or non-runtime reserved(type0)
overlap, with the exact PCI BAR resource as the independent device input.
A firmware memory type by itself never grants MMIO. The requested BDF and
bounded extent must match that private catalog. A null base represents an
absent device; consumers retain non-null guards. The static extent is the
constructor's exact bytes operand.

v6 reserves128KiB RW, including low64KiB private state and a catalog at
context20480. v5 project floor remains20KiB; single-source image/object
bytes retain their own ABI. A PCI-dependent image refuses v5 packaging.
The live queue/capability/domain layout is not implemented by this change.

QEMU observes all3 real memory BARs matching QMP. The VGA BAR fixture reads,
writes, verifies and restores the original value, result42/fuel999999
(one source charge site; inline intrinsics add no source charges). Public
header pointer/bytes forged to a RAM catalog leave the private copy intact;
a request through that forged grant refuses. Bad BDF, outside BAR, RAM,
zero/oversized requests reach the exact constructor UD2. A deliberately
corrupted EFI record points at RAM and reaches the trusted bootstrap's
refusal; it is a negative handoff input, never positive device evidence.

The same compiler passes native helper/region/window/width/lock/ISR
packaging, image/v5/v6 regressions and27 original memory admissions. The
emitted-guard Python emulator conformance and intentional corruption
control are separate observations, not native guest execution. QEMU also
executes INT3/callback/IRETQ, bounded stack exhaustion and shallow return.

This is a local candidate. No successor native x86/controller adoption,
full kernel/live runtime, media/GPT, desktop/input or physical NIC
qualification is claimed. The full15 kernel stops at submit-bus3-frame
region proof(E7106/SIR8339); live27 stops at kernel-value-provider-queue.
Public/root/controller pins remain the admitted full31 from PR1547.
