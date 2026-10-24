# Bounded pure i64 native cache (JUN-371)

This development profile separates immutable code from each invocation's
fuel and resource context. The adopted Amu frontend/lowerer and scalar
emitters remain authoritative. It retains the closed language of v2:
zero-argument entry, acyclic methods, tail recur, empty effects/imports,
arena0 and a conservative static stack bound. It is not whole-VM, signed
Murakumo Cell, remote cache, or effectful host qualification.

## Identity and the invocation boundary

`compile-kototama-cache` takes an explicit
`kototama.pure-i64-cache/v3` profile, target, compiler SHA-256 and complete
compiler source SHA-256. It emits an ELF containing no invocation budget.
The original canonical DAG-CBOR bytes retain their CIDv1/dag-cbor/sha2-256
Program identity. The ELF has a separate CIDv1/raw/sha2-256 identity.

The cache key is SHA-256 over the exact newline-terminated `KTI64CACHE3`
binding emitted by the compiler. Every variable field is bounded and
canonical. The binding includes:

| Code identity | Bound value |
| --- | --- |
| Original program | canonical Program CID |
| Compiler | complete native image SHA-256 and complete source SHA-256 |
| Target | `aarch64-linux` or `x86_64-linux` |
| VM/decoder | `kototama.vm/program-v1`, `canonical-dag-cbor/ascii-bounded-v1` |
| Values/fuel | `i64-wrap/v1`, `expression-charge/v1` |
| Engine/ABI | `kototama.pure-i64-cache/v3`, `stdin72-receipt64/v3` |
| CPU/optimizer | baseline ISA, adopted core default pipeline |
| Bindings/entry | empty imports, zero-argument entry |

The executable embeds the 32 key bytes. Its sealed envelope reads exactly
72 bytes followed by EOF from stdin before entering any guest expression:

| Byte offset | Little-endian i64 / bytes |
| --- | --- |
| 0 | magic bytes `KTI64C3\0` |
| 8 | fresh fuel, 0..9007199254740991 |
| 16 | approved stack limit, at least the emitted bound and at most262144 |
| 24 | arena limit0 |
| 32 | authority0 |
| 40..71 | exact embedded cache key |

Missing, truncated, trailing, mismatched or out-of-range context exits76
without a guest receipt. No environment variable supplies fuel or authority.
Valid executions use the existing v2 64-byte receipt and typed failures.
The initial budget/remaining fields are initialized afresh for each process;
the stored ELF never contains a prior invocation's mutable data.

## Native local cache host

`seed/cache/host.kotoba` reuses the existing native CDCI supervisor's
confined opens, SHA-256, sealed image and bounded child mechanisms. It is
built through a dedicated pinned factory, separate from the two mandatory
CDCI roles. The currently implemented cache host is Linux x86_64, matching
the qualified public compiler host; the code/context ABI has native tests
on ARM and x86. An ARM cache supervisor is a separate qualification.

```
amu kototama-cache-host-build ENTRY COMMON HOST --compiler-sha256 SHA256 --source-sha256 SHA256 --output NEW
cache-host.elf ABSOLUTE_REQUEST REQUEST_SHA256
```

ENTRY/COMMON are the canonical `seed/cdci/entry.kotoba` and
`seed/cdci/runtime.kotoba`; HOST is `seed/cache/host.kotoba`. The factory
accepts only the reviewed exact source hashes. Only two validated 256-bit
digests are elaborated into its policy; a request cannot choose another
compiler or source lineage. The native image digest and complete source
digest must come from the independently qualified selfhost build. The
request hash binds input bytes; it is not an authorization token.

The 16-line request has this exact order, with a final newline:

```
KTI64RUN3
ABSOLUTE_PRIVATE_CACHE_ROOT
ABSOLUTE_PROGRAM_CBOR
EXPECTED_PROGRAM_CID
ABSOLUTE_COMPILER_ELF
BAKED_COMPILER_SHA256
BAKED_COMPLETE_SOURCE_SHA256
x86_64-linux
FRESH_FUEL
FRESH_STACK_LIMIT
0
0
0
0
none
allow
```

Lines10..13 are arena, requested authority, approvals and host-supported
authority. They all must be0. The lease must be `none`; any effectful grant,
cached approval/lease, unknown profile or CPU target is refused. The trusted
local caller supplies this request for each invocation. It is not an RPC
admission interface exposed to a guest or remote caller, and cannot stand
in for the trusted operation consent required by end-user apps.

Every hit rechecks request integrity, policy, Program CID, the pinned native
compiler, metadata binding, native image CID, and fresh resource limits.
The compiler and cached executable are copied to sealed memfds before exec,
so the verified snapshot is the executed image. The child gets a fresh
72-byte context and an empty environment. The cache stores only `binding`
and `image.elf`; it stores no allow result, approvals, lease, fuel context,
guest result or receipt.

The root must already be owned by the effective user with mode0700. Opens
reject symlinks and escaping paths; cache files must be private, regular,
single-link files. This is a trusted local build cache: remote or unsigned
artifact import has no admitted route. A same-user actor able to replace
the trusted host or its private cache is outside this local trust boundary.
Digest integrity, source provenance and semantic conformance are separate
checks; no digital signature is inferred from a CID or source pin. Signed
remote provenance, revocation, effectful admission and Cell receipts remain
JUN-372 work.

## Bounds and failure behavior

Bounds apply per configured private root. A node adapter must select that
root in trusted configuration; guests do not select cache roots.

- At most16 immutable slots. A full cache refuses; there is no implicit eviction.
- Each admitted image is at most1MiB and its binding at most2048 bytes.
- One nonblocking root lock bounds compilation and invocation concurrency to1.
- A miss has a120-second wall/CPU deadline and1MiB per-file output limit.
  Input retains the existing65536-byte/4096-node/depth64 frontend bounds.
- A guest has a5-second wall/CPU deadline,32MiB address-space limit and an
  OS stack limit equal to its approved guest bound plus16384 bytes of process
  startup overhead. The static guest stack bound remains at most262144.
- The build directory is published with no-replace rename after synchronization.
  Compile failure/timeout removes only its owned fixed build files. A stale
  `building` directory after a host crash refuses a new build and is preserved
  for explicit recovery.

Exhaustion of a host deadline, malformed native output, write failure or a
killed process is a host/protocol failure, not a fabricated VM fuel receipt.
All normal and failing receipts must match their admitted budget, status,
arena and static stack bound. Code is RX, mutable context is RW and stack NX.

## Gates

`check-kototama-cache-abi.py` stages code reuse, CIDs, bindings, v2 conformance,
context refusals and raw process output. `check-kototama-cache-host.py` stages
miss/hit, fresh admission, resource bounds, policy and cache tampering,
concurrency/capacity, deadlines, and owned cleanup. Amu-built native ordered
gates own the verdicts and reject corrupted observations. Python only stages
literal fixtures, hashes, files and processes; it does not evaluate a VM.

These sources are development candidates until current integrated source/pin,
compiler generations, native gates, public entry and required CI qualify them.
