# Proposed explicit large-vector native profile

Status: owner approved implementation on2026-10-26; qualification pending.
Tracking: KOTOBA-144 / KOTOBA-140. The approval preserves every default and
region/item/authority invariant below; it is not artifact qualification.

## Executable reason for the proposal

The complete native M104-count preparation built all19 original workloads.
The standard runner stopped aha-mont64 at exactly4,194,304 vector descriptors.
An unchanged-payload diagnostic reproduced that named refusal in2.706 seconds
with168,960KiB peak RSS. Its native report recorded4,194,304 vectors and
9,033,888 items. This is a capacity boundary, not a wall-time inference.

The independently retained historical M104 reference for the original count
3,866,624 requires50,266,113 vectors and108,265,476 items. Other18 historical
workloads fit the existing vector bound. CRC32 completed its original count
in37.009 process seconds with the standard runtime; its17 native arena
counters matched the reference. The old30-second diagnostic deadline remains
on record and does not imply incorrect output.

AGENTS.md requires: "Keep all vector/item/region limits, five rollback
counters, fuel and refusal conditions." A new larger profile therefore needs
an explicit owner decision and corresponding contract amendment. The existing
standard profile, current failures and original workload sources must remain.

## Approved product behavior

Add a generic, explicitly selected native runtime profile for caller-declared
large vector tables. Its selection belongs to the artifact build/launch
contract and must be pinned in the artifact descriptor and measurement
manifest. Never select it from a workload name, program contents, failure,
timeout, or observed speed.

The same full Amu compiler, frontend, lowering and code generator produce
both profiles. There is no separate benchmark compiler or replacement
implementation. The public default remains the standard profile.

Native Linux builds select `--runtime-profile standard-v1` or
`--runtime-profile large-vectors-v1` after their format/payload arguments.
Omission means standard-v1. A profile belongs to the built runtime, not to a
guest-controlled environment variable; record exact build argv, profile and
image digest in the artifact descriptor and later measurement manifest.

| Resource | Existing standard | Proposed explicit profile |
| --- | ---: | ---: |
| Vector descriptors | 4,194,304 | 67,108,864 |
| Vector items | 268,435,456 | unchanged |
| Individual vector length | 33,554,432 | unchanged |
| Pairs | 16,777,216 | unchanged |
| String pool bytes | 268,435,456 | unchanged |
| Private growth-region rows | 4,194,304 | unchanged |
| Capability grants | explicit existing grants | unchanged |
| Fuel/clock/refusal semantics | existing | unchanged |

The current implementation couples growth-row capacity to KXRT-VECTORS.
Separate that private region limit before adding the new profile so that
increasing vector descriptor capacity does not also increase region limits.
The per-vector region map must still cover every valid descriptor. Preserve
all current index, scope rollback, absolute item-highwater and refusal checks.

Reject unknown profiles, malformed descriptors and conflicting resource
declarations before execution. Denial must not cause a profile switch. The
compiler/product/root/controller source and image pins must be rebuilt and
qualified through the normal native route before adoption.

## Resource cost and measurement boundary

For the existing aha-mont64 reference count, descriptor bytes are804,257,808;
its private region map adds402,128,904 bytes; item bytes are866,123,808.
Their sum is2,072,510,520 bytes, about1.93GiB, before other runtime/process
overhead. This is a structural RSS estimate, not a measured new-profile result.
Anonymous mapping reservations at the proposed limits are larger; report
actual RSS and host memory pressure and admit the run only on a suitable host.

Do not change the original iteration counts or source functions to make this
proposal pass. Retain the standard-profile refusal and the new-profile result
as separate observations with distinct runner hashes. Profile identity and
resource costs must accompany any later speed statement.

## Required acceptance before performance use

1. Review the profile descriptor, source selection and resource accounting.
2. Preserve the standard profile's complete positive/refusal/resource corpus.
3. Execute new-profile descriptor and vector boundary controls; built mutants
   must demonstrate detection of missing bounds, wrong profile selection,
   region-limit broadening and invalid rollback/highwater behavior.
4. Rebuild current full compiler/root/public/native roles and require all
   mandatory ARM/x86 native gates. Source admission is insufficient.
5. Execute all19 original registered-count workloads. Verify result, fuel and
   all17 arena counters using independent references, preserving all failures.
6. Run the preregistered same-host comparison, executable negative controls
   and two independent external reruns before a marketing performance claim.

If the owner retains the existing vector limit for every profile, this
proposal is refused. Investigate another explicitly reviewed measurement
profile or native route; do not relabel a shortened/partial campaign as the
original full-count result.
