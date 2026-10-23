# Exact native project sources and scalar scopes

This ports the source-pin and scalar-scope changes onto Amu main
`1585cb488ea9a0b4f87c1fd319ea71fa3ceb09a0`. The complete adopted
`seed/MANIFEST` frontend, lowering, optimizer and AArch64 backend remain in
that lineage. The baseline history in `seed/compiler-core.json` is preserved;
the candidate has 18 modules, adding pure SHA-256 and KSL1 parsing. The older
branch's receipts below are historical prototype evidence. They do not qualify
this port, its main integration, or its filesystem provider.

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
scalar runtime routines and private vector growth metadata are implemented in
both static runtime strings (`seed/76` and `seed/77`), following the separate
owning-native assembler implementation. Scope depth remains bounded at 256;
all five saved counters are checked before any restore. Retained prefixes,
assoc and views keep persistent semantics. Optional doubled capacity falls
back to the original exact copy size when space is insufficient. Guest arena
limits and grants are unchanged; no hosted allocator or loader is added here.

## Historical prototype receipts

See [correctness.json](evidence/native-source-lock-20261023/correctness.json)
and its separately labelled intermediate pin-refusal receipt. Those older
18-module unity bytes match the prototype source used to build G5. G5 rebuilt
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

MIR's whole linked ordinary suite and both-target allocator pressure run on
this compiler. Its separate source/lock receipt records the large-case work.
No old compiler host, C loader or Python semantic materializer was executed.
Host tools only inspected/edited source bytes, hashed receipts and orchestrated
the existing VM's native executables. Process tracing remains unavailable.

That was experimental AAPCS64 emission framed for an existing AArch64 Linux
guest. Public CLI/target/profile/seal, x86_64-linux-static CDCI controller,
owning main/resolver/CID integration, generic abort/recur cleanup and the full
historical corpus remain open. The current main reader and runtime are separate
integration inputs; these historical receipts identify only the tested core.
