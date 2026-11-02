# Opt-in AIUEOS application memory candidate (JUN-757)

The `x86_64-aiueos-kernel-v4` target and its paired boot-info-v7 EFI
loader reserve a separate eight-MiB allocation for one image-lifetime
kernel application host. `kernel-application-pool` takes no arguments and
returns that exact region. This is a prerequisite for Kekkai's full
one-MiB message / 2048 parts / 128 assemblies / four-MiB buffered
reassembly contract. Reassembly and application authority are still open.

This is an unadopted compiler candidate. Existing root/public/role pins
are bootstrap inputs, not qualification of the changed FULL-MANIFEST.
Do not select this target for a production release until those pins and
both native ISA/CDCI qualifications are completed. No physical device,
PXE service, management route or installed OS was changed by this probe.

## Allocation and ownership

The target retains v3's two-MiB text cap, RW placement, four user domains,
stack, tables, desktop and fifteen scratch/DMA pages. EFI separately calls
`AllocatePages(AllocateMaxAddress, EfiLoaderData, 2048, ...)`, with an initial
maximum of `0xffffffff`. It refuses failure, a result below16MiB, or an end
above4GiB. It zeroes all eight MiB before the final memory-map/exit pair.
There is no smaller-allocation fallback or caller-chosen pointer/size.

The kernel seals the grant before main. It checks the exact version,
owner, size, reserved word, alignment, address bounds, loader/scratch
non-overlap and containment in a non-runtime EfiLoaderData descriptor of
the actual sealed memory map. The getter checks CPL0, disabled interrupts
and the private ready marker. It uses the sealed base, not mutable public
boot metadata. The checker recognizes only that intrinsic as the new
region root; a numeric address does not become a region.

Owner1 is the trusted kernel application host. This is not an arbitrary
allocator, per-user/process isolation mechanism, Kekkai peer grant, socket
permission, fresh operation consent or executable application artifact.
The host must partition, reset and erase the pool according to the actual
application lifecycle. The existing user-profile trailer does not expose
the getter. After v5 user paging is enabled, the external allocation stays
in supervisor RW/NX huge pages; it is not added to any domain's RW pages.

Private seal cells33536/33544/33552 hold base/size/ready. They are after
the user fault record and before the non-evicting domain table, below the
existing private stack floor. RW file offset496 carries the explicit
`0x314d5041` packaging marker. Neither marker authenticates a kernel.
Signature/release authority remains the existing separate acceptance gate.

## Paired v7 handoff

The160-byte boot prefix,16KiB map and full PCI catalog keep their layout.
A64-byte application grant follows the catalog at boot-info+`0x60c0`:

| Offset | Word |
| --- | --- |
| 0 | `0x314c4f4f5050414b` |
| 8 | grant version1 |
| 16 | actual separately allocated base |
| 24 | 8388608 bytes |
| 32 | kernel application host owner1 |
| 40 | actual relocated PE base |
| 48 | bounded PE image size |
| 56 | reserved0 |

Before boot, word40 holds the boot header RVA; loader code derives and
stores the actual relocated PE base. Font/payload now starts at
boot-info+`0x6100`; dual payload sizes and user slot version remain unchanged.
The v4 kernel demands boot version7; packaging without the required PCI
loader refuses. Older targets keep their original trailer and v5/v6 bytes.

## Executed evidence

`docs/evidence/aiueos-application-pool-20261103/receipt.json` binds the
complete61-module native Mac F1=F2 source/container/raw/image fixed point,
native packager self-rebuild, existing scalar user/FS2 refusals and these
additional executable observations:

* `check-aiueos-application-pool-macos-native.py`: two full eight-MiB
  zero/pattern/read/wipe boots, full independent memory equality, stable
  ownership after public boot-version mutation, seven malformed-grant/
  old-boot refusals at the actual pre-main instruction, six CLI/region
  refusals, and old v1/v2/v3 kernel+EFI byte equality. All new artifacts
  reproduce.32 native calls and nine QEMU boots, not32 runtime scenarios.
* `check-aiueos-application-pool-composition.py`: a hash-pinned previously
  qualified public Kekkai fixture supplies native Amu discovery for17
  modules, including the unchanged11 actual ValueRuntime modules. The
  old v3 kernel/EFI remain byte-identical to the previous qualified run.
  The new v4 boot keeps both pool-end canaries through113 chunk cases and
  twelve cursor guards, with all return pairs/full hashes matching,
  assertions0 and private work erased. Actual CR3 and all five covering
  supervisor/NX huge leaves are read back. The two real256KiB request
  regions remain separate from the new pool. Font/slot bytes are exact,
  RW stays2359296 bytes and the6582272-byte EFI fits the existing medium.
* `check-aiueos-application-pool-owner-fault.py`: one whole61-module
  compiler fault removes only the owner check. Native F1=F2 and both
  valid/wrong-owner boots complete every memory check. Acceptance of the
  wrong owner detects the fault against the baseline's refusal. This is
  one targeted fault, not a full mutation corpus.

Each observer requires new output directories and hash-pinned tools.
Run heavyweight commands through `scripts/seed/native_build_queue.py`.
First build the full compiler with the existing
`check-aiueos-user-macos-native.py` and explicit current bootstrap image
paths/digests, since this candidate has not replaced the bootstrap pins.
Pass its `--output` directory as `--mac-build` to these observers.
The composition observer additionally requires `--fixture-run` and its
`--fixture-receipt-sha256`; it verifies every graph, font and slot input,
then hashes the native discovery output into a lock. Python does not
resolve source namespaces or compile/package guest code.

The QEMU fixtures use virtual FAT firmware input. They do not qualify an
installer, physical RAM policy, a running CPL3 denial probe, production
authority or an installed/connected Kekkai app. Retained initial failing
probes are not promoted to passes. Both native ISA gates, updated adopted
pins, complete runtime/resource/refusal qualification, full message
reassembly, directed service/port/pending-reply/fresh-consent binding and
actual Mac/6600H peer/revoke/reconnect/native SSH remain required.
