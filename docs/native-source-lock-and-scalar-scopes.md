# Exact native project sources and scalar scopes

This extends the adopted measured `seed/MANIFEST` lineage at `17cb10b3`.
The complete frontend, lowering, optimizer and AArch64 backend remain in that
lineage. The immutable measured baseline in `seed/compiler-core.json` is kept;
its explicit successor has 18 modules, adding pure SHA-256 and KSL1 parsing.

## Project input contract

`check` and `compile` accept one `--source-lock` with an exact KSL1 manifest.
The manifest contains its entry, all ordered `--source-path` roots, and every
unique source path with a full lower-case SHA-256 digest. It is ASCII, ends
in LF, uses canonical absolute paths and `.kotoba` sources, and is bounded at
1 MiB, 16 roots and 256 sorted unique files. Discovery must consume exactly
that file closure. Each discovery, compile and final-header reread hashes the
same bytes that it then decodes. Stale, missing, extra or malformed inputs
fail closed with E6015; a failed read cannot be erased by the next phase reset.
The driver rejects the old `--unpinned` escape. This format does not claim
compatibility with a resolver/module lock or Definition CID.

## Scalar lifetime

The checker retains a structural scope marker after checking the existing
scalar-only result contract. Lowering emits context ABI slots 224/232 around
the body and preserves the i64/bool/f64 result. No source head exposes manual
enter/leave. Collection/reference results are refused. The corresponding
native arena runtime and vector growth metadata live in the owning native
repository; no hosted allocator or loader is added here.

## Native receipts

See [correctness.json](evidence/native-source-lock-20261023/correctness.json)
and its separately labelled intermediate pin-refusal receipt. The first
18-module unity bytes exactly match the source used to build G5. G5 rebuilt
G6 to an identical 2,573,947-byte KSEED, SHA-256
`bb94ca3692b4bf1f62fbdb3447a916aec48145dc3da3ab814e57421bd162042c`.
The G5 ELF is `aca405b65c0313aee4b672a5c5c65839b6fe7e941aeaf957865c81da50b3843f`.

Native runs cover pure SHA-256 empty/abc/NIST/million-byte cases, 21 KSL1
conditions, 17 CLI pin refusals across the recorded generations, a locked
two-module project, and scalar cleanup with 600,000 repetitions. Depth 256
passes, depth 257 retains SIGILL/exit 70, and the unscoped control retains
vector-budget exit 72. All 19 complete correctness workloads were freshly
compiled by G5 and packaged/executed with the growth runtime. Their KSEED/raw
code matches the earlier G2 receipt; the new ELF runtime hashes are separate.
These are correctness results, without a fresh performance score.

The parent reader updates through `588a96a4` were subsequently retained by a
normal merge. [integrated-correctness.json](evidence/native-source-lock-20261023/integrated-correctness.json)
records the current 2,811,561-byte unity, SHA-256
`6155de09d2226d8183e8bda5ff609149bc8dc7dead000db98654d87ab7a1c92e`.
G7 rebuilt G8 byte-identically, KSEED SHA-256
`870b7ba49b28edf44d325594ce46aa5e5df212046c9ccc294f9a48db29fc1fbb`.
G7's ELF SHA-256 is
`f3a4b31d4219c5e8d920885093f565388ffe0e1ea8dc81073094e435bb94751d`.
G7 freshly passes all 19 correctness workloads, SHA/KSL1 units, all 17 pin
refusals, reference-escape refusal, and the locked two-module compile/run.
It checks/compiles the whole 33-source MIR project to the exact same KSEED
bytes as the G5 image whose eight ordinary/large entries were executed.

MIR's whole linked ordinary suite and both-target allocator pressure run on
this compiler. Its separate source/lock receipt records the large-case work.
No old compiler host, C loader or Python semantic materializer was executed.
Host tools only inspected/edited source bytes, hashed receipts and orchestrated
the existing VM's native executables. Process tracing remains unavailable.

This is experimental AAPCS64 emission framed for an existing AArch64 Linux
guest. Public CLI/target/profile/seal, x86_64-linux-static CDCI controller,
owning main/resolver/CID integration, generic abort/recur cleanup and the full
historical corpus remain open. Every receipt identifies its exact tested core;
the later integrated generation does not rewrite the earlier evidence.
