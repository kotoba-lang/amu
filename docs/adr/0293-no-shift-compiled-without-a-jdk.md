# ADR-0293: No shift compiled without a JDK, and nothing here could see it

- Status: accepted
- Date: 2026-09-02
- Numbered 0293 at merge time: 0291 went to the boot stream, and 0292 was
  taken twice on the same day (the kernel-object-import and f32 streams).
  Three concurrent streams, one hand-picked counter.

## Context

Measured 2026-09-02 at amu `b1fdaad2`, on
`(defn shl [x] (i64-shift-left x 4))`:

```
$ bin/amu compile probe.kotoba --target x86_64 --jvm-free --output probe.o
{:format :kotoba.cli-error/v1, :ok false, :error :verify,
 :diagnostic {:code :kotoba/verification-failed, :source "probe.kotoba"},
 :message "runtime KIR i64 shift count rejected"}                     exit 65

$ clojure -M:run compile probe.kotoba --target x86_64 --output probe-jvm.o
{:ok true, :target :x86_64-kotoba-v1, ...}                            2213 bytes
```

`kotoba-verifier` re-derives the rule that a shift count must be an integer
LITERAL in `[0,63]` — the restriction that lets the native backends lower onto
`CL` / `x1` with no range check. It re-derived it with bare `integer?`. On the
JVM a `.kotoba` literal is a `long`; under nbb it is a JavaScript `bigint`, and
cljs `integer?` does not recognize one. So the count of every shift failed the
literal test and **no artifact using an i64 (or i32) shift could be built on
this CLI's JDK-free route.** The refusal named the count, and the count was a
perfectly good literal, so to the caller it read as "your program is wrong".

Nothing in this repository could see it, and the reason is structural rather
than an oversight:

- `clojure -M:test` runs the JVM route, where the rule holds.
- `scripts/jdk-free-native-conformance.cljs` runs the JDK-free route — and its
  fixtures (`i64-semantics`, `structured`, `nested-record`, `held-operations`,
  `many-constants`) contain no shift. It could have seen it and had nothing to
  look at.
- No driver compared the two routes' output at all. The conformance driver
  structurally cannot: it shadows `java`/`javac`/`clojure`/`clj` with failing
  stubs and asserts they are never invoked, which is the right shape for "this
  route needs no JDK" and the wrong shape for "the two routes agree".

The same absence explains why this is the second route-specific defect this
driver has caught by fixture rather than by rule: `many-constants.kotoba` is
there because an i64 literal is a bigint that `goog.getUid` cannot hash past
the PersistentArrayMap boundary. Same host difference, different symptom.

## Decision

1. `examples/i64-shift.kotoba` covers all three i64 shifts, and joins the
   executed case list in `scripts/jdk-free-native-conformance.cljs` with
   `mixed(-8) = -67` measured by running the artifact under the W^X loader.
   The `+1` at `x = -8` is contributed only by the LOGICAL right shift, so
   swapping `u64-shift-right` for `i64-shift-right` gives `-68` and the three
   table entries cannot be confused for each other.

   i32 shifts are deliberately absent from the fixture: their gate had the
   identical defect and takes the identical fix, but `:i32` typed values are
   not admitted on native at all, so there is no artifact to execute. That
   half is pinned in kotoba-verifier's own `.cljc` test, which runs on both
   hosts.

2. `scripts/native-route-parity.cljs` (`npm run test-native-route-parity`)
   compiles a fixture on both routes and compares the object bytes. It needs a
   JDK, which is why it is a separate driver rather than a case in the
   conformance script. It exits **3**, not 0 and not 1, when it cannot reach
   the comparison — a run that never measured must not be readable as a run
   that measured and found no difference.

3. The `kotoba-verifier` pin advances `58a02b4` → `c2ce475` (branch tip; the
   reason to move is `3d7a6f0`, kotoba-verifier ADR-0022), which re-derives
   the literal rule with a
   predicate that recognizes a guest literal on both hosts and adds that
   repository's first nbb test entry. Fail-closed is unchanged: a non-literal
   or out-of-range count reaches the same refusal, with the same reason
   literal, on both routes.

## Consequences

- Break-checked. With the pin reverted to `58a02b4` and the lock regenerated,
  `test-jdk-free-native` exits 1 with `runtime KIR i64 shift count rejected`
  on `i64-shift.kotoba`, and `test-native-route-parity` exits 1 with
  `ROUTES DISAGREE ... the JDK-free route refused what the JVM route is being
  asked to build`. With the pin restored both pass. Measured, not reasoned.
- All three of `native-route-parity`'s exit codes were exercised, not just the
  green one: **0** with the pin in place, **1** with it reverted, and **3**
  with `clojure` shadowed by a stub that exits 127 (`could not measure: this
  driver compares the JDK-free route against the JVM route, and \`clojure\` is
  not runnable here`). A driver whose failure path has never run is a driver
  whose failure path is a guess.
- Byte parity measured, not assumed: `examples/i64-shift.kotoba` and
  `examples/i64-semantics.kotoba` are identical on both routes on aarch64
  (`02061a9e…` and `da158c84…`). Only the OBJECT is compared. The provenance
  sidecar is not, because the two routes are already known to differ there in
  project mode.
- `test-native-route-parity` is registered in `package.json` and is NOT wired
  into `.github/workflows/test.yml`, deliberately: this workspace's CI is the
  murakumo fleet and new workflow files are not written here. Until a fleet
  gate names it, it is a driver a person or an agent runs, not an automated
  gate — and stating that is the point, because an unwired script described as
  a gate is the failure mode this ADR is about.
- By the time this branch merged, `main` had already moved the verifier pin to
  `3d7a6f0` on its own — two other streams bumped it the same day for their own
  reasons. So the shift defect was already fixed here before this ADR landed,
  and what this PR actually contributes is the pin's remaining distance to the
  tip plus **the two gates**. That is the useful reading of it: a fix arrives
  in a pin bump whether or not anyone knows what it fixed, and the thing that
  keeps it from silently going away again is the fixture.
- The pin advance spans more than this fix, because it goes to the branch tip
  rather than to the fix. Between `58a02b4` and `c2ce475` sit the boot stream's
  firmware boundary (`8158aa8`, kotoba-verifier ADR-0020, this repo's
  ADR-0291), this fix (`3d7a6f0`), and the SYSOPS stream's interrupt entry
  address gate (`7070ec0`) — every one a fast-forward ancestor. Verified as one
  tree: `clojure -M:test` 1227 tests / 8859 assertions, 158 of 158 namespaces,
  0 failures. The only assertion this branch had to move is the pinned SHA in
  `aggregate_abi_test.clj`, which exists so a pin cannot advance silently.
- Not addressed: the general rule. Every predicate in the verified closure that
  tests a guest literal has this hazard, and only the two shift gates were
  measured wrong today. kotoba-verifier now names one `guest-integer?` so a new
  site has something to reach for, but nothing prevents the next bare
  `integer?`.
