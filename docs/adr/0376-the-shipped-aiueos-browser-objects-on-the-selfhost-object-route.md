# 0376 — the shipped aiueos browser objects on the selfhost object route (measured; options)

Date: 2026-10-24

## Status

Historical measurement and options, retained for provenance. The measurements
below describe e8f77af3 on 2026-10-24, not the current native compiler. This
document changes no seed, artifact or pin. It follows ADR 0373 (bounded kernel
memory windows, merged as #1539) and the aiueos `:browser-component` floor.

Review update, 2026-10-25: Amu #1563/#1564 and AIUEOS #497/#498 integrated the
locked complete kernel/live-runtime/native-media route, guarded region and
queue/ABI contracts, and the diagnostic desktop. Complete46 retained all18
adopted core modules; exact-head native ARM/x86/controller/public qualification
passed in run 40136966836. The AIUEOS source-owner consumer separately verified
full30 desktop/QEMU input at 4cc72740. These are later gates and do not make the
five historical objects below the current product dependency.

JUN-93 still requires the actual `kotoba-lang/browser` surface/input/text-edit,
CSSOM and DOM graph to replace the kernel's Browser-frame2 behavioral adapter.
Rebuilding a mirror object or booting its numeric app cards does not qualify
shared Browser, Itonami dapps, broker consent or persistent state restoration.

## Measured (amu e8f77af3, the pinned native root, `compile <src> --target x86_64-aiueos-kernel-v1`, capability env `KEXE_CAP_RESOURCES_35`)

The five objects in that snapshot (`browser-reduce`, `-ime`, `-frame`, `-frame2`, `-damage`; then built by the old nbb route at amu 74ca4aa6):

1. **All five are refused `E7102` first**, at the SECOND exported defn. Each exports its entry point and a `main` stub (`(defn main [] 0)`), and
   the object profile admits exactly one export. The detail number is that function's index. Dropping the `main` export (a source edit, in a scratch
   copy) moves four of them on.
2. **`browser-frame2` also has a 6-parameter function** (`note-text`); the profile admits at most five. Splitting it is a source edit.
3. **The other four then stop at `E7106`, ADR 0373's rooting rule, at their first memory access.** Their accessors are shaped like
   `(defn w-at [st i] (kernel-load-u32 (kernel-subregion st 128 (* i 4) 4) 4 0))`: a helper that takes the surface `st` alone and gives
   `kernel-subregion` the literal length 128 (or 8192). Under ADR 0373 a helper's base is rooted only when its region length is the NEXT parameter
   and every caller passes the matching length; here the length is a literal the helper cannot verify, and the exported entry points
   (`aiueos-browser-reduce [st sb kind a b]` and the like) check `sb` against 8192 (or 128) by an ordinary `if` that the rule does not see.
   This refusal is correct: nothing in the object proves the region is as long as the literal.

Counts that size the choices below: `browser-reduce` 56 defns, `-ime` 149, `-frame` 14, `-frame2` 112, `-damage` 26; the memory intrinsics appear in only
a few accessor helpers per object (`kernel-subregion` 3 to 7, loads 1 to 3, stores 1 to 3), but those accessors are called from hundreds of sites.

## Options

A. **Thread the length.** Give every accessor and every function between the entry point and the accessors an adjacent `(st sb ...)` pair. Sound with
   the rule as built; touches every signature and call site of the objects, pushes several functions past the five-parameter limit, and is a large
   refactor of working, gated code for no behavioural gain.
B. **A declared constant region.** Let an exported function declare its region lengths (for example a contract `(:regions {st [128 8192]})`), have the
   object entry check that `sb` is one of them before any access (the check the sources already do), and admit a literal length L for a base derived
   from `st` only when L is within the declared lengths and the entry check dominates the access. Sound if the dominance is checked (the entry guard is
   the first thing the function does and every other path returns), and it keeps the sources as they are. It needs a small, careful analysis in
   `xk-check` and a contract syntax; both are new surface to review.
C. **Relax ADR 0373 for literal lengths.** Not recommended: it reopens exactly the gap (b) that #1539 closed, where an access names a length that is
   not the region's.

## Recommendation

At the measured revision, B was recommended as its own slice with its own cases (a guard that does not dominate, a guard on the wrong parameter, a literal outside the declared set, a path that
reaches the access without the guard) and the same independent read ADR 0373 got. Before that, the two source edits in 1 and 2 are small and can be
done on the aiueos side whenever those historical objects are rebuilt. This is
not an instruction to restore the 74ca4aa6 build or the retired nbb pipeline.
Current integration must preserve the adopted native contracts and qualify
the complete shared source graph, with refusals and actual native execution.
