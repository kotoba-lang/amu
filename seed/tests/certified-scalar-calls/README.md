# Descriptor reuse across certified scalar calls

The two positive callers normalize a signed 16-bit value twice between vector reads. Normalization is idempotent, so all 54 original full-width result oracles remain unchanged. Other callers cover payload alias writes, local rebinding, grow and drop.

The compiler preserves a checked vector descriptor only across complete typed scalar-call certificates. The first successful certificate marks the saved slot and arms descriptor reuse; the second certificate band is also accepted. Every vector read resets the count. Writes to the tracked slot invalidate both certificate bands. Unknown instructions, effects, fixes, owner or type domains retain the original checks. The index comparison, traps and payload load remain in place. No runtime ABI or metadata fields are added.

Native qualification of the current fixture observed three exact first-instruction replacements by branches to the original index comparison. Original checked seeds dominate both paths; cached registers and the vector handle are preserved, and temporary registers 16 and 17 are killed before observation. All 54 paired executions preserve the full 64-bit result, fuel and all 17 arena counters.

This fixture is independent of Embench workload names; names do not participate in optimization admission.
