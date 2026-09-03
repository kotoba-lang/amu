# ADR 0333: amu is where the fuel ceiling's four statements meet

Status: accepted. Date: 2026-09-03.

## Context

The ceiling on a native execution budget was stated in four places at three
values, and no two of them had ever been compared:

| where | value | what it bound |
|---|---|---|
| `kotoba.native.elf64` replenish | 2,147,483,647 | an object's per-call tier — and this was an **immediate width**, not a decision |
| `kotoba.verifier/max-native-fuel` | 1,048,576 | every sealed native artifact |
| `kotoba.compiler.nbb.cli/native-fuel!` | 1,048,576 | the same, on the JVM-free route |
| `kotoba.kir` | none | the interpreter's own counter |

The shipped aiueos objects run at 250,000,000 and 2,147,483,647 through a
verifier that admits 1,048,576, and nothing noticed — because the object route
does not read the sealed budget at all. `package-kernel-object` picks a tier by
symbol name and writes 512 into the artifact's own context.

Meanwhile `native-fuel!` was *already* enforcing 2^53−1 through
`js/Number.isSafeInteger`, beside a `max-native-fuel` test four hundred million
times tighter that hid it.

## Decision

**`max-native-fuel` is `ir/max-fuel`, and amu is where the restatements are
compared.**

kotoba-kir ADR 0268 decides the number and carries the measurement: `charge!`
is `(vswap! fuel dec)` on a plain host number, which is a double on Node, and
`x - 1 === x` is already true at 2^53+4. `kotoba.verifier` reads it (ADR 0049 —
a ceiling is not a set). `kotoba.native.elf64` restates it as
`max-object-fuel`, on purpose: the packager must not require the interpreter,
or `kotoba.compiler.nbb.native-package` would load the whole evaluator for one
integer.

**No single classpath holds more than two of those.** The packager and the
interpreter never meet inside kotoba-native; the verifier never loads the
packager's object route. This repository loads all of them, so
`kotoba.compiler.fuel64-ceiling-test` is the only place the comparison can
happen — and a restatement nobody compares is a copy, which drifts.

That the drift is not hypothetical is on the record in the repository next
door: `elf64_twin_parity_test` exists because the *same table in two files of
one repository* diverged in both directions and shipped, and the symptom was an
aiueos object taking an unexpected vector 6 that read as a protocol bug.

The JVM-free route's own bound cannot be called from a JVM test, so that file
is read as text — the same technique and the same reason as the twin-parity
test — asserting that it names `ir/max-fuel` and that the `1048576` literal has
not come back.

## Pins

| repo | from | to | why |
|---|---|---|---|
| kotoba-kir | `ad6db332` | `233bd6bb` | exports `max-fuel` |
| kotoba-native | `91033a9d` | `95361f3f` | the widened replenish (ADR 0078) and `package-user`'s budget (ADR 0079) |
| kotoba-verifier | `6a743c30` | `d1985d62` | reads the ceiling (ADR 0049) |

All three fast-forward, checked with `gh api compare` rather than assumed:
ahead 11 / 21 / 6, behind 0 / 0 / 0.

**The three move together and cannot be split.** This driver would otherwise
admit a budget the pinned verifier refuses, and the verifier would enforce a
ceiling the pinned interpreter does not export.

## Consequences

- `--fuel 4300000000` compiles for the kernel-image routes on the JVM-free
  route, end to end. Measured: three distinct images at 512 / 2^20 / 4.3e9.
- A budget past 2^31 has now been **spent on a CPU**: aiueos ADR 0195 runs a
  probe under QEMU that burns 2,200,000,005 fuel out of a sealed 2,500,000,000
  and returns, with a same-bytes-but-the-budget control at 2,000,000,000 that
  stops where the arithmetic says. Measured rate 58,367,824 charges/second
  under TCG on this host.
- `evaluate_token`'s ≈2.8×10^10 (aiueos ADR-0175) is now four orders of
  magnitude inside the ceiling. That says the road is open. It does not say the
  object exists, and nothing here has built it.
