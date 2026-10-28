# Exact native project sources and scalar scopes

This ports the source-pin and scalar-scope changes onto Amu main
`1585cb488ea9a0b4f87c1fd319ea71fa3ceb09a0`. The complete adopted
`seed/MANIFEST` frontend, lowering, optimizer and AArch64 backend remain in
that lineage. The baseline history in `seed/compiler-core.json` is preserved;
the candidate has 18 modules, adding pure SHA-256 and KSL1 parsing. The older
branch's receipts below are historical prototype evidence. They do not qualify
this port, its main integration, or its filesystem provider.

## Current-main port verification (2026-10-23)

[The actual current-main receipt](evidence/native-source-lock-20261023/current-main-correctness.json)
pins all 18 sources, the native compiler and runner, all workload inputs,
linked source locks and execution outputs. The complete compiler rebuilt
G11 = G12 (KSEED SHA-256 `f354ca247a0d1683dc5a6966198f3e1e77db4381caf29d7b54a93e7d74b5658e`).
All19 Embench correctness workloads freshly compiled and executed with exit0.
This is not a performance measurement.

[The input ledger](evidence/native-source-lock-20261023/embench-inputs.json)
identifies all19 checked-in `bench/embench/reproduce-20261015/ports` files.
Each canonical body is unchanged. Its explicit correctness fixture exports
`main` and appends the same checked-in literal shown in the ledger, calling
`bench-verify 1` and returning zero only on success. The exact staged hashes
were checked; all19 generated native code bodies are byte-identical to the
prior complete corpus. No host tool interprets or translates the workload.

The exact merged GMIR source (`40ef6c95`) passed all8 entrypoints. The exact
merged MIR source (`b9a570a5`) passed ordinary main, module/reentry/table/
schedule/counted/allocator large, and aggregate large-main. The aggregate
exceeded an initial 300-second outer timeout, then finished with exit0 under
a 900-second outer deadline; its artifact, full input closure, native arena
limits and grants were identical. GMIR/MIR outputs from G9 and G11 were
byte-identical. No case or dependency was dropped.

SHA-256 and KSL1 units, all17 E6015 pin refusals, scalar-reference escape
refusal E2104, and native scope normal/depth256/overflow257 controls passed.
KGraph uses bounded last-write-wins storage; unsupported public command,
resolver-lock/CID and generic abort/recur cleanup qualification remain open.
These proofs establish the recorded source port; adoption and owning-main
integration are tracked separately from public CLI/CDCI qualification.

## Final platform integration

[The final native receipt](evidence/native-source-lock-20261023/final-main-correctness.json)
records the runtime after incorporating main `e06dbba7` (packed mode and
JUN-325 direct/function-address refusal). The native platform root reached
S2 = S3 = S4 (`cd85f3fc6e68511f6de3e71692dfd9b90133bab3fe2c85285bb423a7dc80ad60`).
It built the complete18 C0; C0 produced G1, followed by G2 and G3 through
the native runner. G1 = G2 = G3 = G11. A standalone packed compiler rebuilt
the same complete source to the same container and native code. The previous
16-module adoption and measured performance baseline remain historical pins.

The final runtime passed all19 freshly compiled workloads, all8 GMIR and
all8 MIR entrypoints including whole-large, all17 pin refusals, both units,
scalar-reference refusal, scope/growth/KGraph controls and vector-budget
refusal. MIR whole-large ended with zero tracked arena use and recorded
155,688,217 scope-release events. These are final use/events, not peak-memory
measurements. The static profile's exact-copy fallback under constrained
20/18-item limits remains separately unqualified; its ordinary fixture does
not force that branch at this profile's unchanged capacities.

This integrates the tested native compiler lineage. Public command/target/
profile/seal, x86 native execution, resolver/module-lock/Definition CID,
generic abort/recur cleanup, historical assertion parity and the native CDCI
controller remain separate qualification work.

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
owning-native assembler implementation. The recorded baseline bounds scope depth at 256;
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

The AWAI-81 AArch64 follow-on raises that target's bound to 4,096 with an explicit
negative control; see [native-scalar-depth.md](native-scalar-depth.md). The
historical receipts above and x86 bound are unchanged.
