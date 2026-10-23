# Selfhost CI tiers and the F root (2026-10-23, JUN-339 / JUN-341)

## Why

Before this change, every pull request touching `seed/**` or `scripts/seed/**`
ran the whole chain:

- `bootstrap-arm64` took 90–100 minutes, and `qualify-x86_64` added 3–20.
- About 60–70 minutes went to one call: C0, the core compiled by the
  stack-machine emitter, compiling the core.
- Each run derived the adoption image five times and built the 24 cases four
  ways.
- 24 of the last 40 runs were cancelled when a newer push superseded them.

## The root is F

The pinned root (`seed/bootstrap/aarch64-linux-static-root.elf`) is F, the
combined compiler (`seed/FULL-MANIFEST`: the adopted core plus the Linux
targets) packed as an aarch64-linux static image. F is optimized. It rebuilds
itself, and compiles the core, in about 1.5 minutes each.

F was derived C-free from the previous root:

1. The previous root built S1 = S2 = S3 from the Linux selfhost closure.
2. S2 built C0 from `CORE-STATIC-MANIFEST`.
3. C0 compiled `CORE-STATIC-MANIFEST` to Kw, and S2 packed Kw as Pw.
4. Pw compiled `FULL-MANIFEST` to F1, which S2 packed.
5. F1 rebuilt and packed itself: F2 = F1.

The root receipt records each hash. The full tier re-derives this chain from
source every day.

## Tiers

| Tier | Trigger | arm64 (`selfhost-bootstrap.py --tier`) | x86_64 (`check-x86_64-native.py --tier`) |
|---|---|---|---|
| `pr` | pull request | F → F′ (= root; otherwise F′ must rebuild itself); F's runners and x86_64 compiler; F's core route = adoption image; packed arity refusal (E7105); named diagnostic with a source span (E2101, JUN-334); runtime boundary corpus; 24 cases; hardening; capabilities | X2 = cross-built compiler; runtime boundary corpus; 24 cases; hardening |
| `main` | push to main | + G2/G3 through the aarch64 runner (= adoption image); P = pack(G3) rebuilds the core; the Linux selfhost closure S built by F and S′ = S | + X3 = X2; KX64V1 runner G1 = G2 = G3; scalar ELF suite; aiueos objects |
| `full` | daily schedule, `workflow_dispatch` | + the `00-ns-static` guard; C0 (from S) → the adoption image; C0 → Kw → Pw → F's own container | same as `main` |

## Where each previous check now runs

| Previous check | Now |
|---|---|
| root → S1 = S2 = S3 (root reproduces) | F → F′ = root (pr); S → S′ (main) |
| S3 builds R-aarch64, S-x86_64, R-x86_64 | F builds them (pr) |
| C0 → G1 = adoption image | full (F's core route gives the adoption image in pr) |
| G2, G3 through the runner | main |
| P packs G3 and rebuilds the core; arity refusal | P in main; arity refusal in pr |
| `check-one-compiler.py` (Pw → F1 = F2 = F3; F's core route; F's images = S3's) | F's fixed point and core route in pr; Pw → F in full. Its byte-identity checks against S3 were the evidence for making F the root, and F now builds those images itself. |
| runtime boundary corpus, cases, hardening, capabilities | pr (built by F) |
| x86: X2 = X3 = cross-built | X2 = cross-built in pr; X3 in main |
| x86: KX64V1 runner, scalar suite, aiueos objects | main |

Content-addressed reuse (`scripts/seed/content_reuse.py`, JUN-332) remains
available for C0's compiles (`--reuse` / `--store`). The workflow does not use
it: pull requests no longer run C0, and the full tier reuses nothing.
