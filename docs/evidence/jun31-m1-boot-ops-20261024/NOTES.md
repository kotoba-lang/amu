# JUN-31 M1/W2: seed/74 boot ops measured, fixed point re-pinned (2026-10-24)

Scope of this evidence: the amu side of the JUN-31 M1 boot proof. The boot
measurement itself (kernel image ELF facts, `out dx,al`/`out dx,eax`
disassembly, loader smoke to exit 43) is kotoba-lang/aiueos
`docs/evidence/aiueos-jun31-m1-selfhost-boot-proof-20261024/`.

## What changed and what it measured

1. **`seed/74-x86_64-aiueos-object.kotoba` (commit `228455e7b`)** —
   `kernel-out-u8` / `kernel-out-u32` as route intrinsics (W2). The boot
   fixture's `:boot` evidence operations had no spelling in the seed closure
   (E2101 on `(kernel-out-u8 233 66)`), so no debug-console-answering kernel
   could be expressed through the seed route at all. xk-lib stub + intrinsic
   4/5 (`port -> dx, value -> rax, out dx,al / out dx,eax`, kotoba-native
   `emit-kernel-out` semantics), `XK-INTR-N 4 -> 6`; the ADR 0373 rooted-base
   rule now covers the window intrinsics only.

2. **Fixed point rebuilt from the changed closure**
   (`scripts/seed/selfhost-bootstrap.py --tier main`, arm64 Linux podman
   python:3.12-alpine, C-free, no emulation; 120 steps, 739 s) —
   `selfhost-bootstrap.json` in this directory is the raw receipt:
   * `rootReproduces false` (expected: the closure changed) and the chain
     converged to the fixed point in two generations: **F1 = F2**
     (container `3755e64f…`, image `86da3c52…`, 3,293,696 B).
   * Linux selfhost closure fixed point **S = S2 = `63474bc8…`**.
   * Core route **G1 = G2 = G3 = `6d94e9b5…`** = the adoption image; packed P
     reproduced it; the arity refusal (E7105) and the named diagnostic
     (E2101) held; 24 runtime cases, the runtime boundary corpus (175
     refusals, 7 positives) and the hardening probes passed.

3. **Root re-pinned to the fixed point** (`seed/bootstrap/aarch64-linux-static-root.*`,
   previous root `fa86314c…` demoted to `history[0]`). The receipt's
   `producedBy.chain` is the measured F1/F2 pair above. Re-verification
   (`F -> F' = root`, `rootReproduces true` against the new pin) is the next
   run's measurement, not claimed here.

4. **Boot proof on the same fixed point** — F (= F1 = F2 = the new root) built
   `os/aiueos/uefi/boot-fixture.kotoba` (`018a939c…`) through the seed image
   route (`--target x86_64-aiueos-kernel-v1 --artifact image`) to a 110,872 B
   kernel (`d6db84da…`, all nine fixture window clauses pass) that ran through
   the Kotoba loader: `exit=43`, `debugcon="KHSCNAbcdefPWghvonkrxTUMXZB"`,
   `bootall=4` (kernel-jump-to), segments at their own `p_paddr`. See the
   aiueos evidence named above.

## Boundary

* W1's E7100 wall was a **stale fixed-point compiler**, not a missing route —
  the image packager (`xi-build`) already existed in the closure; no packaging
  code changed in this branch.
* M2 (desktop/GOP input) needs the D1/D3 owner decisions (ADR-0180/0131);
  the C-free whole-build gate (JUN-64, 25 `zig cc` calls in the object-route
  build) remains open. JUN-31 acceptance overall remains NOT MET — this is the
  M1 milestone.
