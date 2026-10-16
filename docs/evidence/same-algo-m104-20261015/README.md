# Same-algorithm compiler m104 (a9edc1f0): adoption evidence, 15 October 2026

This directory records why the seed compiler built from `a9edc1f0d5021efabf6864e70c5b92d59257f348` (branch
`claude/embench-same-algo-m104-20261015`, measured in the m104 round), with one SIR capacity raise, is adopted as the
pinned native bootstrap.

## What is adopted

* **Sources:** the `seed/MANIFEST` modules of `a9edc1f0`, merged with `main`, plus one capacity raise (below). `main`'s
  changes since the merge base are the additive x86_64-linux modules and manifests; no file was changed on both sides.
  Unity sha256 `01abc96f46279e3958a0df8f704ef0648d7d011497d1c621d524c6fe1b9e34e9`.
* **Capacity raise:** with the m104 code generator, `seed/X86_64-LINUX-MANIFEST` (this compiler plus the x86 backend)
  overflowed the SIR table (`E3001` in `scripts/seed/build-x86_64-linux.py`). `MM-SIR-CAP` goes from 393,216 to 491,520
  records; every later base, `MM-HEAP-END` and `MM-WORDS` move by 393,216 words (`MM-WORDS` 16,646,144, below the
  loader's 16M-item vector limit). `MM-SIR-CAP` is used only as a capacity bound.
* **Bootstrap:** `seed/bootstrap/adopted-20261012.bin` = `510599927df88117d22809f751593c6f38e8afbc4bb8881e0ce989549aae2e94`
  (2,549,048 bytes); container `seed/bootstrap/adopted-20261012.kseed` = `ace5b839b5ce32da21fd19bc8c1e20a26c124fc4b3a0283bf044f251685a8bd0`.
  * It is a fixed point: G1 = G2 = G3, and `scripts/seed/build-adopted.py --generations 2` reproduces it.
  * **It differs from the measured m104 compiler `e5fc0ca2…` (source `a9edc1f0`) only by the capacity raise.** It
    compiles the 19 official Embench ports to images byte-identical to the 19 measured in the m104 round (native image,
    container and exports), and the 19 policy-native golden sources to the same 19 images as `e5fc0ca2`. The published
    results and the reproduction package stay pinned to `a9edc1f0` / `e5fc0ca2`.
* **Previous bootstrap:** the replaced image `87efe842…` (source `ffa4cfc1`) is kept here as `previous-bootstrap.bin` and
  `.kseed`. The static single-feature audits of the `check-*.py` scripts run against it (see below).
* **Chain from the previous public bootstrap:** `87efe842` builds stage A = `ffa4cfc1`'s sources with the `a9edc1f0`
  memory map (22 generated constants differ), which gives `5583a2fd…`. Stage A builds the measured fixed point
  `e5fc0ca2…` (G1 = G2 = G3; `bench/embench/reproduce-20261015/b_build.py --round rounds/sa-m104-20261015.json` re-runs
  this). `e5fc0ca2` builds the raised sources: `51059992…` = G1 = G2 = G3.
* **Policy-native golden:** regenerated per the #1313 convention by `native19-golden.py`, as
  `seed/main-same-algo-m104-native19.json` and `main-same-algo-m104-native19.tgz`. The archive is unchanged from the
  `e5fc0ca2` images.

## Qualification

* **Validation** (`tools/validate.py`): 39 images, 483/483 result/fuel/state observations, and 19/19 official images exact
  in result, fuel and all 17 arena counters.
* **Differential test:** 71,496 cases, 0 mismatches, over four shards.
* **Fuzz campaign** (random differential testing against the adopted `main` compiler):
  * Three bugs were found and fixed: b01 (nested short-circuit jump threading), b02 (stale fuel at host stack exhaustion)
    and b03 (latch coalescing, fixed in `e8f4ebe4`).
  * No wrong-result mismatch has been found since b03 in the m43 to m92 campaigns, for example m92b with 3,629 programs
    and 700,387 cases.
  * One m92a record was a compile wall-clock timeout (SIGALRM after 97 s on a heavily loaded host). The same program
    compiles in 4.9 s with this compiler.
* **Kernel scope:** same algorithm only. The policy and the per-kernel audit tables are in
  `bench/embench/reproduce-20261015/audit/`. The SHA-256 crypto instructions are off; sha256 runs on the scalar path.

## Official Embench rounds

Both were run on an Apple M4 with translated Kotoba ports, the upstream Embench driver and fresh C in the same cycle. The
reproduction package `bench/embench/reproduce-20261015/` (README in English and Japanese) re-checks and re-runs both.

| round | source | Kotoba / C (GM of (4/m_w)·K/C) | kernel scope |
|---|---|---|---|
| m93 | `be7f0ce3` | 0.7999 | contained substitution kernels and the SHA-256 instructions (see the audit) |
| corrected m104 | `a9edc1f0` (this compiler) | **0.8213** | same algorithm only; all 38 runs accepted on the first attempt, all exact |

## CI checks on this branch

Six `scripts/seed/check-*.py` scripts paired a behavioural part with a static audit of one historical optimization:
`native-gate.audit` attributes the whole image difference to that one feature, or bounded-lookup pins the whole
image. m104 adds the T2 tier and many other changes, so these audits no longer apply to the current image. Each
script now runs its static audit against `previous-bootstrap.bin` (`87efe842`, the compiler at which it was established
and last held), and every behavioural case still runs on the current adopted compiler with exact result, fuel, traps
and all 17 arena counters. check-bounded-lookup also checks the lookup structure on the current image directly: the
private tree enters a lookup core no longer than the audited one, followed by the 128 audited table entries, and the
exported tree is byte-identical to the audited region and still refused.

**Caveat:** m104's new fuel optimizations (T2 fuel regions, deferred fuel publication, batched block and call-block
charges) have behavioural assurance only: the differential test (71,496 cases, 0 mismatches, fuel compared exactly),
the fuzz campaign and the control rows of these checks. No static check covers them yet.
