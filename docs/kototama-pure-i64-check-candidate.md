# Pure-i64 frontend check candidate

JUN-792 adds a candidate `check-kototama` command to the existing selfhost
compiler. It validates canonical Kototama bytes against one of the two
bounded pure-i64 frontend profiles without creating a native image:

```text
amu check-kototama PROGRAM.cbor --profile kototama.pure-i64-aot/v1
amu check-kototama PROGRAM.cbor --profile kototama.pure-i64-receipt/v2
```

The candidate requires an explicit profile and rejects extra arguments,
unknown profiles, absent/out-of-scope input and malformed or unsupported
programs. It reuses the existing bounded decoder, whole-program validation,
compiler reader/name/type/lowering stages and scalar SIR checks. It also
enforces the selected profile's existing static stack ceiling. Success
prints `{:ok true, :phase :pure-i64-frontend-check, :authority :none}`.
Neither success nor a content digest grants authority, executes a program,
proves an emitted target will work, or qualifies a host. This is not a
general Kototama decoder or a full VM conformance declaration.

## Candidate validation, 2026-11-03

On Linux x86-64, the full 61-module candidate source had SHA-256
`9f2f880c948e5e45d20d2f09f24dae4b61815550f2c744bc12352c491bbe4436`.
Native F1, F2 and F3 were identical at SHA-256
`8ad04ceaddaf0f27b19f8ec8b0057ba3d55ac25e9508f4937841dcb091f22902`.
The existing v1 and v2 native ordered gates passed 131 and 275 cases,
respectively; their corrupted-observation controls refused, and the v2
metering-removal control refused. The new
`scripts/seed/check-kototama-check.py` gate passed 255 observations across
the two explicit profiles, including unknown fields, unreachable invalid
content, noncanonical encodings, invalid options, missing/out-of-scope input,
input preservation and absence of output files. Its native corrupted-input
control refused.

As a separate source-mutation control, changing the program field-count check
from exact equality to a lower bound admitted an unknown top-level field; the
new native gate failed on the mutated compiler. The mutated compiler SHA-256
was `2572367993e76bcf371993db8378971cde1ef32d7f688270805ded83c71ba854`.

These results apply to this locally built x86-64 candidate and fixed corpus.
The checked-in public binary and native-product source/image pins are not
updated by this change; their complete qualification, ARM validation,
exact-head CI and release are still required. No runtime or production
cutover is implied.
