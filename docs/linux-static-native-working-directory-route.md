# Native working-directory route

Tracking: [JUN-236](https://linear.app/kotobalabs/issue/JUN-236),
[JUN-201](https://linear.app/kotobalabs/issue/JUN-201), Kotoba Labs.

`tools/linux_static_handlers.kotoba` now routes C1 provider 0 / wire 40 to
handler 12. Entropy 23 and spawn 20 keep their provider-0 branches, hash keeps
provider 9 / wire 3 -> handler 11, and all other branches retain their source
forms. All 52 function names, all 48 operations and the public five-i64
`decide` form remain unchanged. C1's provider decision is unchanged.

The complete operation mechanism is part of
[kotoba-native #205](https://github.com/kotoba-lang/kotoba-native/pull/205):
empty request only, physical startup cwd captured by raw `getcwd`, checked
private span and nonzero length, owning pool charge, checked string/pair
allocation and UTF-8 validation. It uses neither `PWD` nor a spawned `pwd`.
The canonical `kotoba.compiler.working-directory/current` boundary invokes
that capability directly. It does not replace the old sys namespace's
unrelated Node process facts or silently supply fake values for them.

The matching wire-40 profile declaration is prepared in
[kotoba-lang #805](https://github.com/kotoba-lang/kotoba-lang/pull/805).
It grants no ambient authority: declared effects, narrowed grant and sealed
ISA-matched decisions remain required. Keep these drafts together until
native admission and actual positive/refusal/resource qualification are
complete. Current main, source/lock pins and native product entry do not yet
consume this candidate. Native lock authoring/replay remains JUN-202 work;
root lock retirement alone does not supply it.

Only source forms/namespace/arity/reference and source-digest inspection was
performed. No generator, compiler, native implementation/admission/artifact,
runtime or test was executed. No C loader/header generation, Node wrapper,
workflow/protection change or service retirement is required by this route.

Handler source SHA-256:
`90d88bfe973b533692608d8bf53fa3cb2490e6162a89d6346e86347477df6744`.
Working-directory boundary SHA-256:
`2668782e9ae5e35cc370d19a514dd63323400719ccfe5bc33dc0713cdd883e53`.
