# Explicit application transmit allocation — JUN-757

The `x86_64-aiueos-kernel-v5` diagnostic image profile adds
`kernel-application-transmit-pool`, a checked1MiB kernel region. The existing
`kernel-application-pool` remains a full8MiB receive owner. A request can be
built while reassembly or an accepted response owns the receive allocation.
No active assembly, completion or unused receive tail is borrowed.

## Allocation and version boundary

The paired boot-v8 loader allocates and zeros one additional explicit9MiB
EfiLoaderData interval: receive occupies its first8MiB, transmit its final1MiB.
These are distinct, non-overlapping compiler region roots. This changes the
new profile's allocation, not the old8MiB quota or the default target. The
grant remains image-lifetime kernel ownership, not app/service/socket consent.

The64-byte application grant at boot offset24784 uses the existing magic,
version2, exact9437184-byte size, owner1 and zero reserved field. Boot header
version8 and the kernel's0x324d5041 RW marker select this pairing. The payload
offset remains24848. The old v4/v7 grant is still version1/8388608 bytes.

Before main, the kernel checks the complete grant, page alignment, arithmetic
overflow, [16MiB,4GiB) interval, containment in a real non-runtime LoaderData
descriptor, and separation from the loaded image and private scratch. It
seals base/size/ready into the existing private context. Mutating the public
boot version later does not retarget either getter. Both getters retain the
interrupt-disabled/ring0/private-ready checks. Transmit is base+8MiB with an
independent exact1MiB region-origin fact. Literal addresses gain no region.

The new intrinsic is appended only for kernel-v5. Its whole-project collector
ID must not overlap the window intrinsics: v5 windows start at111, while old
profiles retain110. This is an ID allocation change, not a relaxation of
root/extent inference. An initial probe exposed the collision as E7106; the
failure and subsequent fixture provenance refusals are preserved.

User ABI, stack floor, ordinary request-domain capacities, RX cap and actual
ValueRuntime bodies are retained. The public CLI still defaults to its declared
Mac host target; unsupported profiles do not silently choose this allocation.
Old v1-v4 kernels and their EFI packages compare byte-identically to the
previous producer, including the real45-module old-v4 response corpus.

## Executed evidence

`docs/evidence/aiueos-application-transmit-pool-20261103/receipt.json` binds
sources, selfhost generations, native processes, packager, QEMU/firmware,
original receipts and reopened memory snapshots.

- The complete61-source compiler reaches native Mac F1=F2. The two-phase writer
  regenerates root/Linux candidate/product/CLI pins. Ordinary public Mac rebuild,
  three aliases and76 native observations pass; descriptors report current.
  Cross-produced Linux candidates are not independent Linux qualification.
- The standalone fixture compares all receive8MiB and transmit1MiB words when
  fresh, patterned and after transmit wipe. It retains the receive pattern
  across transmit writes/erasure. Seven grant/boot changes refuse before main;
  negative/past-end/cross-end dynamic offsets refuse after sealing. User-target
  admission of the new root, forged literal regions, old-target new-root and
  old-producer new-target attempts refuse. There are12 actual QEMU boots.
- Two complete61-module compiler mutants reach their own fixed points and
  normally complete full9MiB fixtures. A transmit alias corrupts262144 receive
  words and the independent whole allocation; removing the owner guard lets
  an actually wrong-owner grant finish. Build failure/traps/timeouts are not
  counted as fault detection.
- The real45-module Kekkai corpus executes both Noise roles:2081 protocol
  packets, plus3 initiator send-first triggers. A fixture adapter uses transmit
  for the native encrypted outbound request without detaching/resetting receive.
  It then overwrites/verifies all transmit1MiB while a real authenticated1MiB
  response is accepted. Exact response bytes,96B channel,512B result context,
  busy hold/release and final erasure still match. The observer independently
  reads transmit and actual supervisor/NX leaf permissions. Each role keeps
  the original53 whole-five-region refusal pairs. Transmit is separately
  observed; it is not falsely included in those five-region comparisons.
- Old real45-module v4 kernel/EFI files freshly reproduce their complete
  previously executed bytes under the new producer. This is artifact parity,
  not another old-profile boot. The prior v4 full fault matrix is retained;
  it is not described as a new v5 execution of that matrix.

The first integration adapter depended on receive reinitialization to clear
outbound codec scratch. The unchanged observer caught its residue. The final
outbound caller explicitly clears its own codec work and repeats both full
corpora. Initial failures stay unqualified. The libraries' production bodies
are unchanged by this diagnostic adapter.

The existing ARM/x86 native application-pool artifact gate retains its four
v4 refusals and exact old artifact comparisons. It binds the current complete
source proof, then also requires v5 kernel/EFI equality to the executed Mac/QEMU
files and four v5 refusals per actual native generation. Its old-v4 expected
files were freshly reproduced on Mac. Independent native Linux execution of
the extended gate remains a CI requirement, not a local pass claimed here.

## Remaining product work

Allocation is a prerequisite. General fragmented outbound scheduling,
backpressure/cancellation, buffer erasure and application integration remain.
Configured directed private-http service/port/normalized endpoint/socket checks
and fresh trusted canonical-broker operation consent must gate real effects.
The fixture never creates that consent or runs an upstream HTTP service.

Mac/6600H app install/live peers, protected production keys/entropy/time/config,
hostile CPL3 execution, independent Linux qualification, native SSH, full daily
use/distributed OS/L1 and production update/recovery acceptance remain open.
Supervisor/NX readback and user-target compile refusal are not a hostile-CPL3
execution test. No physical deployment or production cutover is performed.
Keep PXE/management/services/WIP and the physical input test pause intact.
