# Wire-42 protocol table: the SUBGROUP entries (ADR-0362 slice 1 of 3), 2026-10-23

Tick: amu-gpu chain (bot/amu-gpu-chain). Tracking: JUN-56 (the dispatch
contract), parent JUN-55.

## What landed (implemented, with tests)

ADR-0362 named three implementation slices. This is slice 1, the
protocol-table entries (`tools/gpu_compute_protocol.kotoba` and its test):

- Verb `SUBGROUP`, code 18 (the next free after `FREE` = 17; the table was
  read first, nothing used 18). No arguments: arity 1 field, like
  `INFO`/`DEVCLASS`; admitted while recording, like `INFO`.
- Answer shape pinned as constant 17 = 2 (fields of the SUBGROUP answer),
  mirroring constant 14 (fields of the INFO answer). The `<size>|<ops>`
  content contract is the consumer's (slice 3); this slice pins the count.
- Refusal `gpu/no-compute-subgroups`, appended at index 35 (the list is
  public ABI: "append, never renumber"; 1..34 were renumbered nowhere).
  Constant 16 (the last refusal index) moved 34 -> 35 because its meaning
  is "last", not an identity. The refusal is a PROVIDER refusal (19..35),
  named and formatted here, decided by the provider.

Test additions (`tools/gpu_compute_protocol_test.kotoba`): SUBGROUP admitted
in both recording states, `SUBGROUP extra` -> `!gpu/arity SUBGROUP`, the
verb round-trip now covers 1..18, "no verb 19", the pinned literals
`(constant 16) = 35`, `(constant 17) = 2`, `refusal-name 35`, and the full
refusal answer `!gpu/no-compute-subgroups SUBGROUP: the provider reports
no compute-stage subgroups`. CASES 107 -> 114 (the runner counts the expect
calls itself and refuses a mismatch).

## Verification (runner output, not paraphrase)

    PASS_GPU_COMPUTE_PROTOCOL_V1 aarch64-linux 114 cases control failed 1
    PASS_GPU_COMPUTE_PROTOCOL_V1 x86_64-linux 114 cases control failed 1

Both receipts in this directory (the runner's own
`gpu-compute-protocol.json`, one per target). Both: the unit image reports
114 cases / 0 failed / result 0; the CONTROL 1 image reports 114 cases /
exactly 1 failed (the ALLOC 0 case) / result 1. Host: arm64 Linux, podman
machine (applehv) on macOS arm64; the x86_64 row ran under qemu-user binfmt
with `--seccomp-if-available` (recorded as imageSeccomp if-available in the
receipt), the aarch64 row native with seccomp required. Compiler: the pinned
root `seed/bootstrap/aarch64-linux-static-root.elf` (sha256 pinned in the
receipts). No C compiler, no GPU, no provider.

The full `run-tests.cljk` gate is NOT claimed: no compiler namespace was
touched by this slice (tools/*.kotoba and one Python runner string), and the
suite is red at base at namespace load ("Could not find namespace:
kotoba.form" via kotoba.compiler.js-value-target, upstream W3 port) --
unchanged and named in the chain PR.

## State honesty

- IMPLEMENTED: the protocol-table half of ADR-0362 (verb, field count,
  refusal) with the table's own tests, 114 cases green on both targets.
- STILL UNIMPLEMENTED: the provider's `SUBGROUP` answer (slice 2; the ADR
  0371 provider does not exist) and the consumer parser (slice 3). Until
  they land, no rule-6 fact has a producer and every rule-6 row still
  answers `:baseline` for a descriptor without facts -- behavior unchanged
  except that the wire grammar now knows the verb.
- UNMEASURED: no measurement was taken; nothing here is optimization
  evidence. No `:measured?` flag moved, no workgroup row (ADR-0355/0358)
  touched, and the four variant rows stay UNMEASURED on their own contracts.
- Old guests: they send no SUBGROUP line and see no new answer shape, so
  ADR 0371 decision 3's byte-compatibility (as amended by ADR-0362) holds.
