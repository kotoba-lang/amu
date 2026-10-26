#!/usr/bin/env python3
"""mufu_padgap_analysis.py -- deterministic adjudication of the v7
PAD-GAP run (gpu-mufu-padgap-microbench, xavier sm_72) against the
predictions PRE-REGISTERED in the instrument header before the first
run (P1..P6; P7 is the SASS-side pad verdict, checked by
mufu_padgap_verify.py). Scratch evidence script; committed verbatim
under docs/evidence. No hardware, no network: parses the archived run
log only. Two runs are byte-identical.

The estimators e_MF = V(MF) - V(F), e_FM = V(FM) - V(M) are computed
BUT ADMISSIBLE ONLY IF the closures P1/P2 hold (P6): a closure residual
beyond 1.0 cyc is a FAIL. On FAIL, the pad-fold reading (the v6
realization deviation as the cause) is REFUTED -- the failures persist
with a SASS-verified unfolded pad -- and the estimators MUST NOT be
reported as the split.

Usage: mufu_padgap_analysis.py <v7-runlog> [<v6-runlog>]
The optional v6 run log adds a V-table delta section (sensitivity, NOT
a prediction; the deltas are named, not attributed)."""
import re, sys
from collections import OrderedDict

PATH = sys.argv[1] if len(sys.argv) > 1 else "mufu-padgap-runlog-20261026.txt"
V6PATH = sys.argv[2] if len(sys.argv) > 2 else None
RES = re.compile(r"^RESULT arm=(\w+) launch=(\d+) n=\d+ med_acc=\d+ "
                 r"med_per_iter=([\d.]+) mean_per_iter=([\d.]+) "
                 r"min_per_iter=([\d.]+) max_per_iter=([\d.]+)")

ORDER = ["M", "F", "MM", "FF", "MF", "FM", "MFM", "FMF"]


def parse(path):
    data = OrderedDict((a, {}) for a in ORDER)
    for ln in open(path):
        m = RES.match(ln)
        if m:
            arm, l, med, mean, lo, hi = m.group(1), int(m.group(2)), \
                float(m.group(3)), float(m.group(4)), float(m.group(5)), float(m.group(6))
            data[arm][l] = (med, mean, lo, hi)
    return data


data = parse(PATH)

# landed measured quantities this instrument must reproduce (P3/P4/P5),
# CONSUMED at their commits: cyclic slope e_MM 14.9966, e_FF 4.0000,
# cycle sum e_MF+e_FM 21.0000.
E_MM_LANDED, E_FF_LANDED, SUM_LANDED = 14.9966, 4.0000, 21.0000
TOL = 1.0  # cyc: the instrument header's named closure tolerance

print("=== V(w) per-iteration deltas, per launch (med_per_iter, cyc/iter)")
print("arm   launch0    launch1    launch2    pooled(med of 3)  within-launch min..max")
V = {}
for a in ORDER:
    ls = data[a]
    meds = [ls[l][0] for l in sorted(ls)]
    pooled = sorted(meds)[len(meds) // 2] if len(meds) % 2 else \
        (sorted(meds)[len(meds) // 2 - 1] + sorted(meds)[len(meds) // 2]) / 2
    V[a] = pooled
    lo = min(ls[l][2] for l in ls)
    hi = max(ls[l][3] for l in ls)
    print(f"{a:4s}  " + "  ".join(f"{ls[l][0]:9.4f}" for l in sorted(ls))
          + f"   {pooled:9.4f}        {lo:.4f}..{hi:.4f}")

print()
print("=== launch-to-launch spread of the median (max-min over 3 launches, cyc/iter)")
for a in ORDER:
    meds = [data[a][l][0] for l in sorted(data[a])]
    print(f"    {a:4s} spread {max(meds) - min(meds):8.4f}")


def closures(Vd, tag):
    c1_pred = Vd["MF"] + Vd["FM"] - Vd["F"]
    c1_meas = Vd["MFM"]
    c2_pred = Vd["FM"] + Vd["MF"] - Vd["M"]
    c2_meas = Vd["FMF"]
    print(f"    [{tag}] C1: V(MFM)={c1_meas:.4f} vs V(MF)+V(FM)-V(F)={c1_pred:.4f} "
          f"-> residual {c1_meas - c1_pred:+.4f} "
          f"({'FAIL' if abs(c1_meas - c1_pred) > TOL else 'ok'})")
    print(f"    [{tag}] C2: V(FMF)={c2_meas:.4f} vs V(FM)+V(MF)-V(M)={c2_pred:.4f} "
          f"-> residual {c2_meas - c2_pred:+.4f} "
          f"({'FAIL' if abs(c2_meas - c2_pred) > TOL else 'ok'})")
    return (c1_meas - c1_pred, c2_meas - c2_pred)


print("=== P1/P2 closures (identity of the edge-additive + entry/exit-constant model)")
r1, r2 = closures(V, "pooled")
print("    sensitivity, launch-matched indices (arms ran sequentially; pairing is nominal):")
fail = abs(r1) > TOL or abs(r2) > TOL
for l in (0, 1, 2):
    Vl = {a: data[a][l][0] for a in ORDER}
    x1, x2 = closures(Vl, f"launch{l}")
    fail = fail or abs(x1) > TOL or abs(x2) > TOL

print()
print("=== P3/P4/P5 reproductions of the landed MEASURED cyclic quantities")
emm = V["MM"] - V["M"]
eff = V["FF"] - V["F"]
esum = (V["MF"] - V["F"]) + (V["FM"] - V["M"])
print(f"    P3: e_MM' = V(MM)-V(M) = {emm:.4f} vs landed {E_MM_LANDED} "
      f"-> delta {emm - E_MM_LANDED:+.4f} ({'FAIL' if abs(emm - E_MM_LANDED) > TOL else 'ok'})")
print(f"    P4: e_FF' = V(FF)-V(F) = {eff:.4f} vs landed {E_FF_LANDED} "
      f"-> delta {eff - E_FF_LANDED:+.4f} ({'FAIL' if abs(eff - E_FF_LANDED) > TOL else 'ok'})")
print(f"    P5: e_MF+e_FM = {esum:.4f} vs landed {SUM_LANDED} "
      f"-> delta {esum - SUM_LANDED:+.4f} ({'FAIL' if abs(esum - SUM_LANDED) > TOL else 'ok'})")

print()
if fail:
    print("=== P1/P2 VERDICT: CLOSURES STILL FAIL beyond the named 1.0 cyc tolerance.")
    print("    P6 (pre-registered falsifier stance) TRIGGERS: with the SASS-verified")
    print("    UNFOLDED pad (P7: 16 dependent IMAD in every body), the pad-fold reading")
    print("    -- the v6 realization deviation as the cause of the v6 closure failure --")
    print("    is REFUTED as that cause; the discipline's premise itself is implicated")
    print("    (P6's original wording). The e_MF/e_FM split STAYS UNMEASURED. The")
    print("    estimators below are NOT the split and must not be quoted as one.")
    emf, efm = V["MF"] - V["F"], V["FM"] - V["M"]
    print(f"    INADMISSIBLE AS THE SPLIT (P6), shown for completeness only:")
    print(f"      e_MF = V(MF)-V(F) = {emf:.4f}; e_FM = V(FM)-V(M) = {efm:.4f};")
    print(f"      their sum {emf + efm:.4f} vs the measured cyclic sum {SUM_LANDED} "
          f"(delta {emf + efm - SUM_LANDED:+.4f})")
else:
    print("=== P1/P2 VERDICT: closures hold under the unfolded pad; the estimators are")
    print("    admissible (P6 not triggered) and the pad-fold reading is CONFIRMED as")
    print("    the cause of the v6 failure.")
    emf, efm = V["MF"] - V["F"], V["FM"] - V["M"]
    print(f"    e_MF = V(MF)-V(F) = {emf:.4f}; e_FM = V(FM)-V(M) = {efm:.4f}")

if V6PATH:
    print()
    print("=== v7 vs v6 V-table delta (SENSITIVITY, NOT A PREDICTION; deltas named, not attributed)")
    v6 = parse(V6PATH)
    V6 = {}
    for a in ORDER:
        meds = [v6[a][l][0] for l in sorted(v6[a])]
        V6[a] = sorted(meds)[len(meds) // 2] if len(meds) % 2 else \
            (sorted(meds)[len(meds) // 2 - 1] + sorted(meds)[len(meds) // 2]) / 2
    for a in ORDER:
        print(f"    {a:4s} v7 {V[a]:9.4f}  v6 {V6[a]:9.4f}  delta {V[a] - V6[a]:+.4f}")

print()
print("=== derived table: V(w) minus the single-op floor candidates (NOT an attribution)")
for base in ("M", "F"):
    print(f"    V(w) - V({base}): "
          + "  ".join(f"{a}={V[a] - V[base]:+.4f}" for a in ORDER if a != base))
