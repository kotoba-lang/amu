#!/usr/bin/env python3
"""mufu_lenext_analysis.py -- analysis of the v9 LENGTH-EXTENSION run
(amu-gpu tick 2026-10-26, JUN-55/JUN-57; scratch, staged to
docs/evidence/gpu/cuda-mufu-lenext-20261026/). Parses the RESULT lines
of mufu-lenext-runlog-20261026.txt and adjudicates the PRE-REGISTERED
predictions P1..P7 from the instrument header (written before the
first run). Deterministic: two runs produce byte-identical output.

Definitions (header): V(w) = pooled median over the 3 launches of
med_per_iter; D_T(k) = V(T^k) - V(T^(k-1)), k = 2..8; D2_T(k) =
D_T(k+1) - D_T(k), k = 2..7; s_T = mean of T's first differences over
k = 2..8; TOL = 1.0 cyc.

NO attribution beyond the registered verdicts: the e_MF/e_FM
estimators are NOT computed (P6); nothing here moves any record,
:measured? flag or workgroup row (rule 4)."""
import re
import statistics
import sys

LOG = sys.argv[1] if len(sys.argv) > 1 else "mufu-lenext-runlog-20261026.txt"
TOL = 1.0

M_ARMS = [f"M{k}" for k in range(1, 9)]
F_ARMS = [f"F{k}" for k in range(1, 9)]
ARMS = M_ARMS + F_ARMS

# v8 pooled V values CONSUMED at the v8 commit (P1 targets).
V8 = {
    "M1": 10.2148, "M2": 23.5156, "M3": 46.2617, "M4": 61.2227, "M5": 76.2266,
    "F1": 12.5039, "F2": 10.2266, "F3": 14.3711, "F4": 18.8359, "F5": 22.3047,
}
# v8 launch-to-launch spreads that exceeded TOL (P1 noise-limited arms).
V8_NOISY = {"M1": 2.8750, "M3": 2.3008, "F4": 2.3125, "F5": 2.2852}
E_MM = 14.9966  # landed MEASURED cyclic slope (CONSUMED at its commit)
E_FF = 4.0000   # landed MEASURED cyclic slope (CONSUMED at its commit)

res_re = re.compile(r"^RESULT arm=(\S+) launch=(\d+) .* med_per_iter=([0-9.]+) ")

per_launch = {}  # arm -> {launch: med_per_iter}
order = []
for ln in open(LOG):
    m = res_re.match(ln)
    if m:
        arm, launch, v = m.group(1), int(m.group(2)), float(m.group(3))
        per_launch.setdefault(arm, {})[launch] = v
        if arm not in order:
            order.append(arm)

pooled = {}
for arm in ARMS:
    vals = [per_launch[arm][l] for l in sorted(per_launch[arm])]
    pooled[arm] = statistics.median(vals)

print("=== V(w) per-iteration deltas, per launch (med_per_iter, cyc/iter)")
print("arm   launch0    launch1    launch2    pooled(med of 3)  within-launch min..max")
for arm in ARMS:
    ls = sorted(per_launch[arm])
    vs = [per_launch[arm][l] for l in ls]
    row = "".join(f"{v:<11.4f}" for v in vs)
    print(f"{arm:<5}{row}{pooled[arm]:<16.4f}{min(vs):.4f}..{max(vs):.4f}")

print()
print("=== launch-to-launch spread of the median (max-min over 3 launches, cyc/iter)")
for arm in ARMS:
    vs = [per_launch[arm][l] for l in sorted(per_launch[arm])]
    print(f"    {arm:<4} spread  {max(vs) - min(vs):.4f}")


def series(fam):
    return [pooled[f"{fam}{k}"] for k in range(1, 9)]


def first_diffs(vs):
    return [vs[k] - vs[k - 1] for k in range(1, len(vs))]


def second_diffs(ds):
    return [ds[k] - ds[k - 1] for k in range(1, len(ds))]


print()
print("=== length series: first differences D_T(k) = V(T^k) - V(T^(k-1)), k=2..8")
for fam in ("M", "F"):
    ds = first_diffs(series(fam))
    txt = "  ".join(f"D({fam}({k + 2}))={d:+.4f}" for k, d in enumerate(ds))
    print(f"    {fam}: {txt}")

print()
print("=== second differences (affine test; every |.| <= 1.0 = affine)")
for fam in ("M", "F"):
    ds = first_diffs(series(fam))
    d2 = second_diffs(ds)
    d2_sub = second_diffs(ds[:4])  # k = 1..5 subset = v8's range
    verdict_full = "AFFINE" if max(abs(x) for x in d2) <= TOL else "NON-AFFINE"
    verdict_sub = "AFFINE" if max(abs(x) for x in d2_sub) <= TOL else "NON-AFFINE"
    print(f"    {fam} (k=1..5 subset): " + "  ".join(f"{x:+.4f}" for x in d2_sub)
          + f"  -> {verdict_sub}")
    print(f"    {fam} (k=1..8 full):   " + "  ".join(f"{x:+.4f}" for x in d2)
          + f"  -> {verdict_full}")

print()
print("=== slopes vs the landed MEASURED cyclic prices (P4/P5; mean of first differences)")
for fam, e in (("M", E_MM), ("F", E_FF)):
    s = statistics.mean(first_diffs(series(fam)))
    print(f"    s_{fam} = {s:.4f} vs landed e_{fam}{fam} = {e} -> delta {s - e:+.4f} "
          + ("(ok)" if abs(s - e) <= TOL else "(FAIL)"))

print()
print("=== P1: v8 REPRODUCTION (cross-run consistency, NOT a model prediction)")
for arm in sorted(V8):
    got = pooled[arm]
    d = got - V8[arm]
    tag = "ok" if abs(d) <= TOL else "FAIL"
    noise = (" [v8-noise-limited arm, spread %.4f]" % V8_NOISY[arm]) if arm in V8_NOISY else ""
    print(f"    {arm}: v9 {got:.4f} vs v8 {V8[arm]:.4f} -> delta {d:+.4f} ({tag}){noise}")

print()
print("=== P2: F non-monotonicity reproduction")
d = pooled["F1"] - pooled["F2"]
print(f"    V(F1) = {pooled['F1']:.4f} vs V(F2) = {pooled['F2']:.4f} -> delta {d:+.4f} "
      + ("(P2 HOLD: the non-monotonicity REPRODUCES)" if d > TOL
         else "(P2 FAIL: the named non-monotonicity does NOT reproduce; downgraded to run-specific)"))

print()
print("=== sensitivity, launch-matched indices (arms ran sequentially; pairing is nominal; NOT a prediction)")
for l in range(3):
    for fam in ("M", "F"):
        vs = [per_launch[f"{fam}{k}"][l] for k in range(1, 9)]
        d2 = second_diffs(first_diffs(vs))
        d2_sub = d2[:3]
        v_sub = "AFFINE" if max(abs(x) for x in d2_sub) <= TOL else "NON-AFFINE"
        v_full = "AFFINE" if max(abs(x) for x in d2) <= TOL else "NON-AFFINE"
        print(f"    launch{l}: {fam} second-diffs(k=1..5) " + "/".join(f"{x:+.4f}" for x in d2_sub)
              + f" -> {v_sub}; (k=1..8) " + "/".join(f"{x:+.4f}" for x in d2) + f" -> {v_full}")

print()
print("=== P1..P7 VERDICT")
p1_fail = [a for a in sorted(V8) if abs(pooled[a] - V8[a]) > TOL]
p2_hold = pooled["F1"] - pooled["F2"] > TOL
p3 = {}
for fam in ("M", "F"):
    d2 = second_diffs(first_diffs(series(fam)))
    p3[fam] = max(abs(x) for x in d2) > TOL
print(f"    P1: {len(V8) - len(p1_fail)}/10 arms reproduce v8 within TOL; failing: "
      + (", ".join(p1_fail) if p1_fail else "none"))
print(f"    P2: {'HOLD' if p2_hold else 'FAIL'}")
print(f"    P3: M {'NON-AFFINE (extends)' if p3['M'] else 'AFFINE over k=1..8 (refutation range-limited)'}; "
      f"F {'NON-AFFINE (extends)' if p3['F'] else 'AFFINE over k=1..8 (refutation range-limited)'}")
sM = statistics.mean(first_diffs(series("M")))
sF = statistics.mean(first_diffs(series("F")))
print(f"    P4: {'ok' if abs(sM - E_MM) <= TOL else 'FAIL'} (s_M {sM:.4f} vs {E_MM})")
print(f"    P5: {'ok' if abs(sF - E_FF) <= TOL else 'FAIL'} (s_F {sF:.4f} vs {E_FF})")
print("    P6: the e_MF/e_FM estimators are NOT computed; the split STAYS UNMEASURED")
print("        (structural verdicts ride in run-log.txt; P7 adjudicated there)")
print("    NOTHING MOVES (rule 4): no record, no :measured? flag, no selection answer, no workgroup row")

print()
print("=== derived table: V(w) minus V(M1) and V(F1) (NOT an attribution)")
m1, f1 = pooled["M1"], pooled["F1"]
print("    V(w) - V(M1): " + "  ".join(f"{a}={pooled[a] - m1:+.4f}" for a in ARMS if a != "M1"))
print("    V(w) - V(F1): " + "  ".join(f"{a}={pooled[a] - f1:+.4f}" for a in ARMS if a != "F1"))
