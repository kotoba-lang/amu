# ADR-0403 -- the object route proves each helper parameter's region once (JUN-708)

- Status: **implemented** (seed/74 `xk-check`, `xk-object-param-region`, `xk-region`, `xk-pair-ok?`).
- Date: 2026-11-01
- Tracking: JUN-708 (Kotoba Labs). Unblocks the native-route port of kotoba's ecdsa-p256 / aes128-gcm / tls13-record /
  hkdf-sha256 objects, which the old walk refused with E7106.
- Amends: ADR 0373 (rooted bases; the depth-12 / 40000-visit limits of 2026-10-24).

## Context

The `x86_64-aiueos-kernel-v1` object route (and the `xi` image and `xu` user routes that share `xk-check`) admits a
window access only when its base is ROOTED (ADR 0373). For a private helper's parameter `p` that means: every call of
the helper passes, at `p`, a rooted base whose region length is either the source of the argument at `p + 1` (a paired
length) or one literal shared by all callers.

`xk-object-param-region` proved this by calling `xk-region` at every call site of the helper. Each of those can reach
another helper parameter, which walks all of its callers again. There was no memo, so the work was the number of
caller paths from the access up to the export. Two limits stopped it: a call-chain depth of 12 and 40000 `xk-region`
visits per checked operand (M[198], reset by `xk-pair-ok?`). Past either one the base counted as unrooted, so the
object was refused with E7106.

So a helper chain with fan-in 4 compiled at 6 levels (4^6 = 4096 paths) and was refused at 8 levels (65536 paths). A
plain chain longer than 12 helpers was refused too. kotoba's crypto objects have both shapes: every helper compiles on
its own, but the whole object is refused.

## Decision

A helper parameter's answer depends only on the pair (helper `f`, parameter `b`) and on the SIR. It does not depend on
which access asked, or on the depth at which it was asked. So `xk-check` now keeps a table of answers for the object
profiles (`xg-get 4 = 0`) and proves each pair once.

- **Table:** `MM-FN-N x 16` words at the current heap top. Cell 213 (`XK-REGION-MEMO`) holds its base; 0 means no
  table. The words are saved into a scratch vector and zeroed before the check. Afterwards they are restored, along
  with `MM-HEAP-TOP` and M[198], and cells 213 and 214 are cleared. Nothing after admission can see the table.
  - The table's cell for `(f, b)` holds 0 (not yet), 1 (open: its walk is running), 2 (refused), or the proven source
    itself (always >= 2^32).
- **Lookup** (`xk-object-param-region`):
  - On 0, it marks the cell open and runs the unchanged all-caller walk (`xk-object-param-walk`, the old body) from
    depth 0. Then it stores the answer.
  - On 1, the pair has reached itself through a cycle of calls. It answers -1.
  - On 2, it answers -1. On any other value, it answers that source.
- **Budget:** one total for the whole check (cell 214), `40000 + 256 x MM-SIR-N`, replacing 40000 per operand.
  `xk-pair-ok?` no longer resets the counter while the table is on.
- **Depth:** the call-chain depth limit of 12 still applies, but inside one pair's walk and each root, not across
  helpers.
- **What is unchanged:**
  - The closed project route (`xg-get 4 = 2`) keeps its own contract tables (`kg-contracts`).
  - If the heap has no room for the table, the original walk runs with its original limits.
  - The emitted code is unchanged: admission only decides whether an artifact is written.

## Why the admitted set does not change, except at the limits

Every way a value reaches refusal in `xk-region` is absorbing. A -1 from a call site makes the helper -1, a -1 base
makes a `kernel-subregion` -1, and a -1 at a checked operand is E7106.

- **Admitted programs:** in a program the old walk admitted, no walk hit a limit or a cycle (a cycle exceeds the depth
  limit). So every answer it computed is the exact, limit-free value of its pair, and the memo returns the same values.
  The program is admitted again, with the same bytes, because emission does not read the proof.
- **Refused programs:** a program the old walk refused for a reason other than a limit has a pair or root whose
  limit-free value is -1. The memo computes that value once and keeps it.
- **Cycles:** a pair that reaches itself has no finite proof. The old walk refused it through the depth limit, and the
  memo answers -1 at the open cell. Every pair whose walk reaches the cycle is refused, as in the old walk with no
  limit.
  - Tail self-calls are lowered to identity assignments and never were calls (`ok_tail_recursive_helper`), so they are
    unaffected.
- **Programs that become admitted:** only those whose refusal came from the depth or visit limit and whose proof is
  finite.

## Termination and the work bound

- **The table:** each of the at most `16 x MM-FN-N` pairs is walked at most once. A pair is marked open before its walk
  and is never walked again: a later query returns at once.
- **One walk:** a walk visits each call instruction of its helper once. At each one it starts one `xk-region` chain
  inside the caller's function, which follows local assignments and `kernel-subregion` bases and is bounded by the
  depth limit of 12.
- **Roots:** each checked operand (at most two per instruction) starts one chain.
- **The total:** at most `13 x (2 + 16) x MM-SIR-N = 234 x MM-SIR-N` `xk-region` steps. The budget of
  `40000 + 256 x MM-SIR-N` is above that, so it is a fail-closed safety net that scales with program size: if it is
  ever exceeded, the base is unrooted and the object is refused, never admitted.
  - An admitted program under the old rule took at most the old per-operand work in each check, so it cannot reach the
    new bound either.
- **Recursion depth:** native recursion is bounded by the number of pairs times 13.

## Measured (2026-11-01, Apple Silicon, amu main be50101d root vs this source)

- **`seed/tests/kernel-memory`** (59 cases):
  - Every one of the 34 refusal cases on main is still refused with the same code and detail, except
    `no_call_site_blowup_is_refused_not_hung`. That case was refused only by the visit budget (8^10 paths); it is
    renamed `ok_call_site_fan_in_8_depth_10` and is now admitted.
  - Every case admitted on main is admitted with identical object bytes.
- **New cases:**
  - `ok_fan_in_4_depth_6`: admitted by both compilers, with identical bytes.
  - `ok_fan_in_4_depth_8` and `ok_fan_in_4_depth_24`: refused on main, admitted here.
  - `ok_helper_chain_depth_40`: refused on main by the depth limit, admitted here.
  - `no_recursive_helper_has_no_proof` and `no_mutual_recursion_has_no_proof` (non-tail cycles),
    `no_helper_second_base_unrooted`, `no_helper_second_window_length_lie` and
    `no_shared_helper_one_bad_caller_deep` (one bad caller under a fan-in-4 tree): all refused with E7106 by both
    compilers.
  - Larger programs: fan-in 4 over 200 levels and fan-in 8 over 100 levels each check in under 0.2 s.
- **Mutants**, each built and run against the case directory, all caught:
  - key the table by helper only: admits `no_helper_second_base_unrooted`;
  - let an open cell assume the paired length: admits both recursion cases;
  - answer every hit with the paired length: admits `no_helper_second_window_length_lie`, and refuses seven ok cases.
- **Byte identity, kotoba main 35b00b82:**
  - all 92 provenance-pinned native-route objects (`git archive`) recompile identically with main's root and this
    source;
  - all 164 `os/aiueos/kotoba` sources give the same bytes, or the same refusal, on both compilers (138 compiled,
    26 refused).
- **Object-route gates:** the 24 `check-aiueos-object-*` / `-kernel-tier-maximum` / `-user-plc-native` gates pass on
  this source's compiler.
