# ADR 0384: exports with up to eight parameters (R4B raised to 8)

Status: accepted (owner, 2026-10-30; JUN-556)

## Context

R4B capped an explicit export at five parameters for every target (seed/21-check, E2108), and the
aiueos kernel object route capped every function at five (seed/74). The next C file to replace on that
route, AIUEOS `kernel/tls_aes_gcm.c`, has two entry points with eight parameters
(`aiueos_aes128_gcm_encrypt` / `_decrypt`) called that way from about twenty sites in `tls13.c` and
`pci.c`. ADR 0383 already lets the object route *call* C with up to eight arguments; this ADR lets C
call an object *export* with up to eight. The owner chose to raise R4B for every target, rather than
only for the object route or by repacking the C arguments into a record.

## Decision

* **Frontend (seed/21-check).** An explicit export takes at most eight parameters (E2108 above that).
  A variadic clause stays at five and an ordinary clause at sixteen. An *implicit* export (R1, a module
  without an `:export` clause) is still only exportable with at most five, so a `defn` of six to eight
  parameters is not silently promoted to an export by this change. The export type check reads
  parameter types through `ck-pt`, which covers parameters past the fifth (it previously read
  `FF-PT0 + k`, which is only valid for k < 5 and had never been reached).
* **aiueos object route (seed/74).** An exported function may take up to eight parameters; a private
  function stays at five. An export of six to eight parameters gets a long entry shim:
  `push rbp; mov rbp,rsp; sub rsp,F; mov [rsp],r9; mov rax,[rbp+16+8(j-6)]; mov [rsp+8(j-5)],rax ...;
  lea r9,[rip+context]; mov qword [r9+8],fuel; call entry; leave; ret`. It stores System V's sixth
  argument (`r9`) and its stack words where the internal convention expects parameters past the fifth
  (`[rsp+8(k-5)]` at the call, the layout seed/98's export thunk already relies on), then sets the
  context and fuel exactly as the short shim does. `F` rounds `8(n-5)` up to 16, so the callee sees the
  same alignment. Exports of at most five parameters keep the short shim byte for byte, so every
  existing object is unchanged; shim offsets, symbol sizes and the context relocation come from a
  per-export table instead of a fixed stride.
* **aarch64 (seed/41).** Parameters past the fifth travel on the stack internally, where AAPCS64 passes
  them in `x5..x7`, and no aarch64 entry shim converts them yet. An explicit export of more than five
  parameters is therefore refused (E4102) instead of producing an entry that a native caller would call
  with the wrong arguments.
* **Other targets.** x86_64-linux static admits only `main` (no parameters) as an export and refuses
  the rest (E7102), unchanged; the shared-object route (seed/98) already handles up to sixteen; the
  locked-project route admits its own fixed export shapes; wasm32 exports no functions.

## Consequences

* `check-aiueos-object-exports.py` adds six- and eight-parameter exports (the shim bytes against an
  encoding assembled in the gate, the relocation at the LEA displacement, the symbol size), a mixed
  object (a six-parameter shim followed by the short shim), and refusals of a nine-parameter export
  (E2108) and a six-parameter private function (E7102). The one-export digest is unchanged.
* Execution on x86_64 under QEMU (TCG), from a C-convention caller passing eight arguments, gave the
  expected results with the stack balanced; two mutant compilers (the stack-word copy and the `r9`
  store) gave wrong results. See `docs/evidence/exports-eight-params-20261030/`.
* An aarch64 entry shim for six to eight parameters is not part of this decision; until it exists those
  exports are refused on aarch64.
