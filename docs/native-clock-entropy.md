# Native Linux clock and entropy candidate

Tracking: AWAI-52; required by kagi JUN-299. This change extends the owning
seed frontend/lowering and the existing loaderless Linux runtimes. It does
not introduce a hosted provider, C loader, second compiler core or runtime
fallback. The original candidate receipts remain historical; the merge review below pins the integrated source and stable native root.

`typed-cap-call :clock/now :string :string request` (wire 7) accepts exactly
`wall` for nonnegative epoch milliseconds and `monotonic` for nondecreasing
nanoseconds. The kernel supplies time through `clock_gettime`; caller text
cannot supply a timestamp. Malformed requests, syscall failure, invalid
timespec, i64 overflow or a backward monotonic reading trap. Last monotonic
time is process-local; wall time remains a trusted host input, not a proof
against OS clock rollback or a durable time authority.

`typed-cap-call :entropy/draw :string :string count` (wire 23) accepts decimal
1..256 and returns 2N lowercase hex characters from kernel `getrandom`.
Existing decimal parsing, including leading zeros, is preserved. EINTR and
partial reads retry, invalid counts/failure refuse. ENOSYS emits
`:entropy/unavailable`, exit 126; no random file, test seed or hosted service
fallback exists. The native seccomp filter admits getrandom only with wire
23's grant. Both providers still require the outer capability grant.

Entropy raw/hex scratch is erased after copying into the guest string pool.
The returned string itself is not secret-memory erasure qualification. Do
not infer private key custody or a secure keystore from this provider.

The clock route needed checker admission **and** `lw-wire` lowering; adding
only checker/runtime dispatch still trapped because the intermediate wire
was wrong. Integer and keyword spellings are both exercised by the native
gate at `seed/tests/native-clock-entropy.kotoba`. The separate i64 clock
effect form is not redefined as this string protocol.

## Observed candidate verification

Built by the combined selfhost native root at
`116306620688f3c0c962b371c7d3a21088d828d2`, SHA-256
`61ee2d3870612c7f8ed6bd2d25f40c8cc68b26d2b5b5336204b1ff2651fe60bb`.
Execution used arm64 Linux directly in the local VM, direct ELF entrypoint,
read-only container root, no network and no C loader/JVM/Node compiler host.
The cached OCI image has amd64 metadata; its shell was never executed and
the actual candidate ELF machine is AArch64. No x86 emulation was used.

- Native clock gate: wall units, 128 monotonic reads, keyword/integer wires.
- Native entropy gate: 1/256-byte boundaries, hex shape, separate 32-byte
  draws, 19-digit zero-padded count and both wire spellings. Random bytes
  were neither printed nor persisted. This sanity check is not a statistical
  certification of the kernel RNG.
- Nine malformed requests and both missing-grant cases trap as expected.
- Fault injection retained the VM's default seccomp rules and changed only
  getrandom to ENOSYS. The candidate emitted `:entropy/unavailable`, exit 126.
- Full combined compiler payload F1 = F2 = F3. The initial F1 wrapper was
  packed by the admitted old-runtime compiler; its bytes differ as expected
  from the new runtime wrapper. New-runtime F2 = F3 packed ELF byte-for-byte.
- The new F2 compiler builds all 24 existing `seed/static-cases.json` cases.
  Actual result/trap **and exact remaining fuel** match all fixed expectations.
- x86_64 provider-gate ELF is cross-built only; no x86 native execution claim.

Receipts: `evidence/native-clock-entropy-20261023/providers.json` and
`runtime-regression.json`. Diagnostic source staging/hash inspection and
tool orchestration are not a qualified native CDCI controller.

## Integrated merge review

The first review integrated main `b09d9635`; the final merge also retains main
`b5026e2d` and its GPU provider platform API. The18 core modules and ARM runtime
are unchanged between these two reviewed rounds.
The full compiler payload is F1=F2=F3; stable new wrappers F2=F3. The complete18
core rebuilds G1=G2=G3. All19 native images match the existing golden images,
and all19 native `bench-verify(1)` calls pass. The24 runtime cases retain exact
result/trap/fuel; all175 boundary refusals and five seccomp/resource probes pass.
The clock/entropy positive gates, nine malformed inputs, two missing grants
and getrandom ENOSYS are rerun on the integrated runtime. No entropy is logged.

`seed/compiler-core.json`, the new adoption receipt and the bootstrap receipt
now describe this source. The first reviewed F2 root rebuilds F3 byte-identically. The final combined
compiler J1, including the latest main platform API, rebuilds identical J2;
J1 is the pinned root. `merge-review.json` records the chain and results.
This does not rerun the full C0 deep-provenance tier or qualify project/arena
coverage beyond the unchanged native golden corpus and listed runtime cases.

## Open gates

Native x86 provider execution, broader fault/mutation coverage, a native CDCI
controller and release qualification remain open. This is no new benchmark
or production release. Private file
creation, metadata/ownership checks, durable replay/audit journals and
long-lived signer custody remain separate work; existing native wire-35
WRITE creates mode 0644 and must not be used for new secret keys.
