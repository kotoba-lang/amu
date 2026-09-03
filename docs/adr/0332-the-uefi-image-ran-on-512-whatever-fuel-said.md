# ADR 0332: the UEFI image ran on 512, whatever `--fuel` said

Status: accepted. Date: 2026-09-03.

## Context

`package-efi` wrote the constant `512` into its context, and had since it was
written:

```clojure
context (into (vec (repeat 8 0))
              (concat (le 512 8) (repeat (- data-size 16) 0)))
```

`--fuel` is parsed by `cli-support/emit-metadata`, range-checked by
`native-fuel!`, sealed into `:limits :fuel` and `:fuel-abi :initial`, re-derived
by `kotoba.verifier`, and hashed into the provenance receipt. Then the one
place that decides what the machine actually gets ignored all of it.

Measured 2026-09-03 through `bin/amu`:

```
--fuel 512      -> fc742834811b311822a4ab6ffb4e72c6e481c56f9fff4ccb4adfe564ed04afe5
--fuel 1048576  -> fc742834811b311822a4ab6ffb4e72c6e481c56f9fff4ccb4adfe564ed04afe5
```

A 2048× difference that changes nothing. `--fuel 250000000` *was* refused
("native fuel budget is not admitted"), which is what made the flag look alive.

**The cost was found from the other end.** The LOADER stream bisected in-guest
over four boots: a scratch write and read-back, a 64-byte `kernel-subregion` of
a `bytes-literal`, `store32`/`load32` and `sha-init` all pass — only
`sha-block` fails. `sha256-region` costs 1,772 fuel per 64-byte block, so **one
SHA-256 block does not fit in 512**, and the UEFI loader's `integrity` module
had never returned. The diagnosis was not a guess before the cause was known.

## Decision

**`package-efi` reads `artifact-fuel`.**

The helper is `kotoba.native.elf64/artifact-fuel`'s two checks, restated rather
than shared, because this repository owns the PE32+ route and kotoba-native
owns ELF:

- the budget is a positive integer;
- `:limits :fuel` **agrees with** `:fuel-abi :initial`.

The agreement check is what makes this a seam rather than a second opinion. The
verifier re-derives `:fuel-abi` from `:limits`, so a packager that read one of
the two could ship an image whose running budget contradicts its own receipt.
`:reason :efi-fuel-bound-invalid`.

**The fix is a no-op at the default.** `--fuel 512` still produces
`fc742834811b3118…`, the same bytes as before, so no UEFI artifact ever built
at the default budget changes. After:

```
--fuel 512          -> fc742834811b3118…   (unchanged)
--fuel 1048576      -> afd98b7d398a63a6…
--fuel 4300000000   -> 40465ebce7df517b…
```

## The test is differential, not positional

Reading the fuel word at a fixed file offset would go stale the first time the
context or a section moved — and this packager's section RVAs became *derived*
rather than frozen for exactly that reason (ADR-0002). "Two budgets must not
produce the same bytes" needs no offset, and it is the observation that found
the defect.

`a-uefi-image-carries-the-declared-budget` requires five distinct digests for
five budgets (512, 2^20, 2^31, the object probe tier, the ceiling).
`the-default-budget-produces-the-image-it-always-did` pins the no-op, and adds
512-against-513 so that "different" cannot be a coincidence of layout.

## Consequences

- The loader's `integrity` module can be given a budget. LOADER has the two
  lines that wire it in.
- This is the same class as the imm32 replenish ceiling one layer down
  (kotoba-native ADR 0078), and the pair is worth naming: **a budget that
  cannot be raised past 2^31, and a budget that is silently discarded, are both
  "the number the machine runs on is not the number anybody wrote."** One was
  found by reasoning from an ADR that quoted the wrong ceiling; the other by
  four boots of in-guest bisection. Neither was found by a test, because
  neither layer had one that compared two budgets.
- Measuring for the reported route rather than *for the class* would have left
  the second instance in place: `kotoba.native.elf64/package-user` had the same
  line, and kotoba-native ADR 0079 is that fix.
