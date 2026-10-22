# Native static SHA-256 decision route

Later [scope-absence work](linux-static-native-scope-absence.md) adds owning
op 48 while retaining every earlier operation. The original 52-function
snapshot and digest below describe the hash milestone, not the current full
decision source or its qualification.

Tracking: [JUN-201](https://linear.app/kotobalabs/issue/JUN-201),
[JUN-200](https://linear.app/kotobalabs/issue/JUN-200), Kotoba Labs.

This source candidate connects the existing C1 provider 9 / wire 3 to native
static handler 11 in the complete `tools/linux_static_handlers.kotoba` module.
Provider 9 with another wire still answers zero. Existing routes 1..10,
unknown-provider refusal, all 48 decision operations and the public five-i64
`decide` boundary remain. This is a routing change to an existing complete
Kotoba component, not a replacement for the hash implementation or verifier.

The complete hash mechanism is in
[kotoba-native #205](https://github.com/kotoba-lang/kotoba-native/pull/205),
with both-ISA whole-input SHA-256,
private checked workspace, exactly 64 lowercase hexadecimal result bytes,
owning op-6 pool charge, result interning and checked pair/handle admission.
Its top-level packager binds actual sealed C1/handler exports and constructs
the full loaderless ELF through the owning encoder. No host hash or successful
seal stub is introduced. A declared grant still must be a subset of effects;
this route does not grant wire 3 to a guest that lacks it.

The existing C1 provider decision already maps kind 1 / wire 3 to provider 9;
that source is unchanged. The owning static profile must separately list
wire 3 / `:hash/sha256`, together with reviewed native implementation pins.
Until the complete native path is admitted and qualified, neither this route
nor the profile declaration proves provider availability. The profile update
is prepared in its owning repository as a separate draft; no live route or
current main profile is activated here.

Historical C-loader/header equality is no longer a native build or acceptance
condition. This candidate does not regenerate, compile or run C-loader code,
invoke the old CLJK generator, or change existing workflow/protection settings.
The held merge-guard cleanup is independent and remains held.

Required integration order: owning ELF64 #8 → complete native #205 admission
and actual byte/refusal/resource qualification → Amu decision artifact and
owning profile with exact reviewed source/lock pins → compiler generations
and whole native self-rebuild → actual native-only CDCI. Required ABI and
general vector/byte/I/O helper closure remain real dependencies.

Evidence for this candidate is static source/route/arity/reference review
only. No handler, encoder/generator, compiler build, native admission,
artifact/digest/runtime or test was executed. The existing suites remain
unchanged. Keep JUN-200/201 In Progress until the actual closure is qualified.
