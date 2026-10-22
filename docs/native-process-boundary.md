# Complete canonical process wire and native boundary

Tracking: [JUN-241](https://linear.app/kotobalabs/issue/JUN-241),
[JUN-202](https://linear.app/kotobalabs/issue/JUN-202), Kotoba Labs.

`process_wire.kotoba` implements all three public functions of the former
pure CLJK wire codec, with the same public names/argument counts and successful
wire meanings. `process.kotoba` connects that complete codec to the native
`:process/spawn` capability. Neither imports a host mechanism or grants a
program/environment/shell by itself.

## Complete codec contract

| Function | Canonical result |
| --- | --- |
| `request(program,args)` | `Result<String,Document>` |
| `answer-exit(answer)` | `Result<I64,Document>` |
| `answer-out(answer)` | `Result<String,Document>` |

Arguments are an ordered typed list of strings. Request encoding preserves
program plus every argument, including empty strings and Unicode, separated
by the exact `ARG_SEP` token. A token anywhere inside any individual part
refuses with `:phase :spawn`, the original message and the complete ordered
program/arguments document. It cannot silently split one argument into two.
Scanning each part directly has the same collision decision as the old NUL
join, without a host text/collection library. No smaller argument count or
extra command whitelist is invented in this pure codec.

Exit parsing finds the first newline and uses the complete canonical decimal
module: optional minus sign and 1..18 ASCII digits, including signal exit -1.
Missing newline and invalid decimal retain named spawn errors; the malformed
line remains in the error data. The constructor does not replace a real exit
with zero or truncate it to an unsafe host Number.

Stdout parsing returns the exact complete suffix after the first newline,
including empty output, embedded further newlines and Unicode. It does not
trim, split all lines or require the exit prefix to be decimal: the original
`answer-out` contract parsed only the newline. It still refuses missing LF.
Native provider UTF-8/handle/resource checks precede the codec's string input.

The native API replaces host exceptions with explicit typed errors. Callers
must inspect each Result; the old exception-oriented classpath consumer is
migration inventory, not a compatible native caller or qualified resolver.

## Native process API and authority

`process/spawn(request)` calls only the string/string wire-20 capability.
`process/run(program,args)` encodes, invokes it, and decodes both exit and
stdout, returning `Result<compiler.process/answer,Document>` with real
`:exit` and `:out` fields. Encoding/response errors propagate before a success
record can be constructed. Accessor defaults occur only behind successful
Result guards; no synthetic successful empty response is used.

Actual program selection, bare-name lookup, passed environment, NUL/empty
program refusal, argv/output/deadline limits, descriptor/privilege/root
isolation and child cleanup belong to the existing complete native provider
and its sealed packaging grant. The codec does not broaden them or replace
provider refusal with a host subprocess. Native authority/provider traps
remain terminal named refusals; `run` does not catch them as exit 0, -1 or an
empty successful result. A real nonzero child exit remains a decoded child
exit for the owning caller to handle.

The complete canonical mechanism is in
[native #205](https://github.com/kotoba-lang/kotoba-native/pull/205), including
both-ISA spawn and the C1/C3 gate. It remains unqualified draft source with
its exact source/lock/provider/ABI integration still required. This wrapper
does not make wire 20 available by declaration alone.

## Whole input closure remains open

The [complete filesystem tree source](native-filesystem-boundary.md) now
supplies all six exports with acknowledged native FS2 framing. Whole
resolver/materializer caller integration and provider qualification remain
open. No native dependency resolver/writer, source farm or full compiler
self-rebuild is claimed by this component port. Those
callers must consume the typed errors and preserve digest/pin/path/alias/order,
fresh-checkout cleanup and authority/refusal behavior. Raw byte I/O/digest and
required general list/document/ABI runtime helpers remain actual work.
The legacy CLJK codec/host process/classpath sources remain labelled migration
inputs until their complete caller integration is retired; they are not a
required native oracle or a final CLJK syntax-sugar exception.

Evidence is source/API/record/arity/dataflow/reference and source/Git digest
inspection only. No codec/handler/project implementation, compiler/generator,
native admission/build/artifact/runtime, child process or test was executed.
No workflow/protection, live service or production route changed.

The source inventory reads four modules/21 functions, eight internal imports,
one result-record construction and 20 Result operations, with no structural
findings. All original public codec names/arities and refusal messages remain.
Codec SHA-256: `ecde99e001371ce0d3a856ae1bafd1806fd1e3201f54bad30fd78eb7eaacedf4`;
native process boundary SHA-256:
`f10b3ec543756e8d0eb7ac611bd921fca296b0b42b1cd7a210fb99456006250b`.
