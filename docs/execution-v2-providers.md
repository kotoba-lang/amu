# Scoped synchronous v2 providers

The optional `execution-v2` composition now accepts an explicit
`kotoba.target-execution-artifact/v3` through `compile-effect-envelope`.
The existing v2 pure artifact, v1 admission defaults and wire/CID contracts
retain their meaning. V3 has the closed keys `format/source/target/limits/bindings/output`;
each binding has exactly `id/scope`; the numeric ID names this artifact-local typed import, while scope is capability CID, resource CID
and purpose. Every executable typed i64 import must have exactly one binding;
duplicate IDs/scopes, generic calls, other effects and unsupported targets fail closed.

The guest is a checked scalar `main() -> i64` with i64/bool helper signatures,
closed arithmetic/control/function operations and `typed-cap-call`. Allocation,
unbounded shifts and other operations require a separate reviewed profile;
this is a target acceptance boundary, not a restriction on Kotoba's language.
All artifact output is independently reproduced from checked source, bindings
and bounds before runtime binding. Artifact/interface identities include the
exact scopes. Canonical output is never replaced with guest-supplied JavaScript.

Wasm imports are named `kotoba:lease/v2.call_<id>` and the actual module import
set must match exactly. Script uses a fresh Node VM context containing only the
frozen typed grant adapters; its canonical compiler output is adapted from ESM,
with dynamic string/Wasm code generation disabled. This is trusted generated
scalar code, not a general JavaScript sandbox or a host-code isolation claim.

The trusted executor receives the scope set derived by Kototama from signed
leases. It checks equality before instantiation, then every call goes through
the scoped `call!` closure. The durable ledger reserves a use before the provider
runs; exhaustion, revocation, traps and result-type errors never refund a use.
Providers own their exact resource and must be bounded synchronous mechanisms.
The guest supplies only signed i64 values; it cannot supply a pathname, policy,
provider callback, import descriptor or authority.

Wasm retains fuel/pages; Script retains fuel/frames and VM timeout. Both check
monotone deadlines before/after provider calls and before accepting completion.
Wasm boundary checks cannot preempt an arbitrary blocking trusted callback;
the launcher must enforce that provider's own bounds. Async, general native loader
provider transport, other hosts, global quota/finality and Q9 remain separate gates.

Run `scripts/test-execution-v2-providers.cljk` with the generated `execution-v2`
lock alias. Actual Wasm and Script guests append to a provider-owned private
file and return `42`. Acceptance includes signed completion, exact scope refusal,
use exhaustion, provider trap/type errors, mid-execution revocation/expiry,
reopened-ledger replay, fuel exhaustion and deadline overrun. Existing pure
Wasm/Script/EVM results `42` are also rechecked against current KIR v3/v4 support.

Reservation and external resource commit are not one distributed transaction.
A trap/crash can burn a use with no or partial resource effect; the completion
receipt attests the executor's observed outcome and is not an external-sink
commit proof or a list of per-use audit CIDs. Keep sink idempotency, effect
receipts and domain-specific finality as separate acceptance units.

## Native per-call host transport

The optional `native-run` composition now forwards closed unary i64 native imports
to the Kototama host lease callback through measured POSIX loader pipes and a
bounded Node IO worker. It reserves each effect, rather than precharging a run.
See [transport owner](https://github.com/kotoba-lang/kototama-native/blob/main/docs/native-lease-transport.md).
`test-execution-v2-native-providers.cljk` tests actual signed compiled guests;
`test-native-lease-transport.cljk` tests mechanism faults. General values, Windows,
async hosting and whole-component Q9/selfhost remain separate qualifications.

Packaged commands keep their baked providers: `KEXE_LEASE_TRANSPORT` and
inherited fd 3/4 cannot opt them into the external host transport. Only the
non-embedded measured loader invocation accepts that explicit mode.
