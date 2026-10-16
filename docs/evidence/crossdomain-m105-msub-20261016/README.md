# M105 AArch64 MSub fusion follow-up

Status: **SELFHOST FIXED POINT, EXACT FIXTURE RESULTS, AND CODEGEN CHECKS PASS; TIMING IS EXPLORATORY AND UNQUALIFIED.**

This candidate fuses `x - q*k` into AArch64 `msub` for positive non-power-of-two constants. It also preserves the collections fast-loop divisor hoist when the product becomes fused. The prior and candidate native fixture exports, KSEED containers, full `otool -tvV` listings, exact execution reports, and the benchmark driver artifacts are pinned here.

## Fixed point and exactness

The 16-module M105 compiler was rebuilt from the adopted native bootstrap. G1, G2, and G3 are byte-identical:

- KSEED SHA-256: `a7aa4ac9868afc6d8d850cd5b20452a2f6f234138d0ca1eb0fab39f45d8e8a4f`
- Native image SHA-256: `854fad339b1317ff85309573767a305e846e23cfee13377570973ff502258a3b`
- No JVM, Node, or Graal fallback was used.

The strings and collections fixtures each passed six inputs. Candidate and prior matched on result, fuel consumption, and the full structured arena report for all 12 executions. `fixture-equivalence.json` contains the complete per-input reports and artifact hashes.

## Generated code

- Strings: the loop still uses `sdiv`. Its quotient/remainder sequence now uses one `msub` instead of rematerializing the divisor and executing a `mul` plus `sub` after division.
- Collections: the fast loop keeps the existing reciprocal `smulh` sequence and hoisted raw divisor. The four unrolled remainder sites and scalar tail each use one `msub` instead of `mul` plus `sub`. The guarded slow path also fuses the remainder calculation.

The extracted strings export shrank from 1,360 to 1,352 bytes; the collections export shrank from 3,160 to 3,128 bytes. These are code-size observations, not timing results. See `fixtures/*-prior.disasm.txt` and `fixtures/*-candidate.disasm.txt` for full listings.

## Exploratory timing

The benchmark driver calls the same fixture kernel 20,000 times per process. It was compiled by the adopted M105 compiler and the candidate G3 compiler, warmed once per arm, then timed for four samples per arm in ABBA order. Each timed interval includes native loader startup. Every run matched on result and fuel.

| Fixture | Prior median | Candidate median | Exploratory difference |
|---|---:|---:|---:|
| Strings | 111.92 ms | 97.94 ms | 14.3% shorter |
| Collections | 95.67 ms | 105.13 ms | 9.0% longer |

These measurements are **not qualified**. The machine reported macOS 26.4 arm64; the task host was identified as an M1 Max. Load averages were 31.12/31.90/38.49 before and 33.36/32.35/38.61 after. Sample ranges overlap substantially. A 100,000-iteration collections follow-up exhausted its configured 4,194,304-entry vector arena before producing a timing result; it is excluded. See `performance-exploratory.json` and `benchmark-build.json`.

No speedup claim, C comparison, Embench score, or SPEC result follows from this evidence. A quiet-host paired timing run with an adequately sized arena remains necessary.
