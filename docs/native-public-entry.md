# Current native product candidate

The source-lock correction from `e29ef6b1cabb4874aecbec773e484326a5cc1453` retains the complete18 adopted core
and complete29 compiler. The public `bin/amu` candidate is a static x86_64
Linux image, SHA-256 `67476a255ba9115fead86b9fa54d5f0240b4e275786d1c42a97953c440e0d11d`; both aliases resolve to it.
The ARM packed root is `f782f3f2a8298c39feeedf873896c9858535a8e371786337632cc60f9e971b9f`. Native generation
already confirms complete containers F1=F2=F3 and packed F2=F3.

## Qualification in progress

The new private framed lock read checks a single nonblocking/no-follow FD,
regular-file metadata, a1MiB maximum and complete bytes before passing the
lock to its owning parser. Directory, FIFO, socket, symlink, oversized,
empty, malformed and missing lock inputs must refuse E6015. Positive lock
paths cover Unicode and the old separator tokens. The ARM prototype passed
30 positive/refusal observations. Final ARM/x86 public and controller
execution, warm/cold/locked/canonical self-rebuild, all19 Embench/MIR all
large/GMIR/resource cases, exact-head PR/main CI and cleanup are pending.
`native-product.json` and the current evidence index retain candidate state.
Historical source35 success is preserved under `range-source35-scope.json`.

No old language host, C compiler, loader, runtime or emulation is a fallback.
Static capacities remain TOK786432/MM-WORDS29,491,200/LitB1MiB/OUT12MiB
with unchanged heap1765120 words, fixture results, locks, fuel and grants.
The controller report now binds its actual positive gate receipt and its
ledger/image identity; current execution evidence is still required.

## Remaining broader contracts

Engine-neutral defaults, full CLI verb/target compatibility, module/package
locks, resolver/Definition CID, profile/seal and historical full assertion
or general FS fault/race parity remain separate. Unsupported paths refuse.
Platform-linked providers and production cutovers are not qualified here.
