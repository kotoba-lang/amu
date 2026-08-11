# ADR 0243: Pin native runtime calls through GMIR, MIR, and MC

Status: accepted

Pair, graph, string, and vector host callbacks now cross an explicit closed
IR boundary. GMIR owns the semantic operation and exact arity, MIR owns the
context-table offset and target ABI registers, and MC owns the selected target
encoding. Unknown operations, offset drift, and physical-register drift fail
closed.

Pin `kotoba-native` at `0ae92d19cda82cc739f764e6bd26578f0bb97b8f`
and `artifact` at `931f13e11113b5a348e308d845594836a7754d36`.
The x86-64 encoder preserves the hidden `r9` context in a reserved aligned
call-frame slot. AArch64 preserves `x7` around `blr x16` and saves/restores the
link register through the call frame. Real loader execution was available for
both AArch64 and x86-64.

This closes the primitive runtime-handle callback family. Capabilities,
literal/data relocation and string rewrites, target-privileged operations, and
escaping aggregate boundaries remain explicit migration work.
