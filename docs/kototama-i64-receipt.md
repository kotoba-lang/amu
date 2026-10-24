# Bounded pure i64 native receipts

JUN-370 adds the explicit `kototama.pure-i64-receipt/v2` engine profile.
The canonical wire format, validated language, private methods, empty guest
authority, heap0 and acyclic call graph are the same as
[`kototama.pure-i64-aot/v1`](kototama-i64-aot.md). The v1 command and its
eight-byte/signal protocol remain available unchanged. This profile does
not admit runtime arguments, recursion, imports, heap values or effects.

```sh
KEXE_ALLOW=35,37,38,39 KEXE_CAP_RESOURCES_35="$PWD" bin/amu compile-kototama program.cbor --target x86_64-linux --output run.elf --fuel 0 --profile kototama.pure-i64-receipt/v2
chmod +x run.elf
./run.elf > receipt.bin
```

The other explicit target is `aarch64-linux`. Fuel may now be exactly `0`;
positive budgets retain the bound 9007199254740991. Negative, malformed and
out-of-range budgets refuse compilation. Fuel is embedded in this standalone
process image. It cannot be overridden through guest environment variables.
This is still not a budget-independent cached executable or node admission.

## Receipt and failure protocol

The trusted process envelope emits exactly 64 bytes, eight little-endian
64-bit words. Signed fields use two's complement.

| Word | Meaning |
| --- | --- |
| 0 | Magic bytes `KTI64R2\0` (`0x003252343649544b`) |
| 1 | Status: 0 success, 1 fuel exhaustion, 2 division by zero, 3 signed division overflow |
| 2 | Returned i64 on success; zero on failure |
| 3 | Initial admitted budget |
| 4 | Canonical spent fuel, including the unsuccessful exhausting charge |
| 5 | Signed remaining fuel = budget − spent; −1 on fuel exhaustion |
| 6 | Guest arena bytes: zero |
| 7 | Conservative static stack bound, including the 64-byte envelope buffer |

A valid success exits0; a typed guest failure exits70. A returned short or
failed receipt write exits74. An OS signal, missing/truncated receipt,
unexpected status/exit or inconsistent fields is a process/protocol failure,
never a successful guest result. A future host must check these fields and
the admitted artifact/profile identity; it must not infer admission from
the presence of magic bytes.

One unit is charged before each original expression. The exhausting charge
is retained: budget0 stops before the first expression with spent1, and
budgetN stops at the next attempted expression with spentN+1. A quotient
fault happens after both operands have evaluated; if fuel runs out first,
the failure is fuel exhaustion. MIN rem −1 remains zero. Wrap arithmetic,
eager operand order, selected branches and simultaneous recur updates retain
the v1 semantics. Every method shares the same two-word budget context.

## Implementation and resource boundary

`seed/84-kototama-i64-receipt.kotoba` uses the existing bounded frontend and
adopted reader/name/type checking/lowering. It delegates ordinary SIR
instructions to the existing x86/ARM scalar emitters. It emits the sealed
OP-FUEL decrement/test and guarded quotient fault edges into a fixed
receipt writer. The adopted core and existing emitter sources are unchanged.
There is no alternate compiler, bytecode interpreter or hosted fallback.

Each fuel site decrements remaining before testing for exhaustion. No guest
operation executes after a failed charge or quotient guard. Failure jumps
directly to the trusted envelope and exits the standalone process; it is
not an in-process exception/unwind ABI. The kernel reclaims process memory.

The complete acyclic method/frame sum plus links and64 receipt bytes must
fit262144 bytes. Every native frame still fits4096 bytes. At most32 methods
give at most31 logical method edges even when the existing emitter performs
tail calls. Both tail and non-tail32-method chains preserve canonical fuel.
Recursive methods remain refused pending a logical-depth counter/profile.
The existing admission limits imply the sum is already below262144, so
that outer limit is conservative rather than a newly reachable stack size.
The source checker's local-slot ceiling also applies to compiler-generated
operand bindings: it refuses slot256 with E2120. The corpus exercises the
largest accepted and next refused nested-operand shape with64 original
bindings; a canonical lexical environment alone does not bound generated
temporaries. Refusals are checked by their native diagnostic prefix.

Code is RX; the shared16-byte budget context is RW; stack is NX. Scalar SIR
admission still rejects capabilities, runtime allocation, imports and indirect
calls across every method, including unreachable methods. No operation can
mint a grant. Effects before failure are empty in this profile; state/effect
rollback and host capabilities need their separate JUN-372 qualification.

## Native qualification

```sh
python3 scripts/seed/check-kototama-receipt.py --compiler /absolute/native/amu --output /new/output
```

The transport stages fixed DAG-CBOR bytes, launches native compiler/guest
processes and stores raw observations. The Amu-built Kotoba ordered gate
checks statuses, values, exact spent/remaining fields, compile refusals,
transport failure and stack/arena bounds. It includes the v1 corpus, zero,
below/exact/above budgets, fault priority, max budget, eager comparison and
first-failure ordering,32-method chains, bindings64/65, depth64/66,
decoder nodes4095/4096, and input bytes65535/65536/65537.
It also covers generated local-slot admission and explicit arena/data/state/
import/capability/indirect-call refusals.

Corrupted observations must fail. A second negative control removes the
actual charge instruction from a generated guest image and executes it;
the original native plan must reject that execution. Existing authority
expansion/effect/import attempts remain compile refusals. Guest environment
variables cannot refuel or grant authority. The same corpus runs on both
native Linux ISAs; v1 regression qualification remains required.

These fixed conformance goldens follow the pinned canonical migration
sources recorded in the v1 document. The retired CLJK evaluator is not
executed. Whole-VM differential parity, signed Murakumo receipts, fresh
node admission, cache identity, in-process unwind and performance remain
unqualified. JUN-371 and JUN-372 own the cache/admission and host bindings.
