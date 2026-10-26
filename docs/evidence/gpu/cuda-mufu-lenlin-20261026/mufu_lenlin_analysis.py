#!/usr/bin/env python3
"""mufu_lenlin_analysis.py -- deterministic adjudication of the v8
LENGTH-SERIES run (gpu-mufu-lenlin-microbench, xavier sm_72) against
the predictions PRE-REGISTERED in the instrument header before the
first run (P1..P6; P7 is the SASS-side structural verdict, checked by
mufu_lenlin_verify.py). Scratch evidence script; committed verbatim
under docs/evidence. No hardware, no network: parses the archived run
log only. Two runs are byte-identical.

The length series tests AFFINITY of V in the word length k. The
edge-additive model plus ANY end-artifact (a deviation that is a
function of the first/last op only) predicts V(T^k) = a_T + k*s_T --
so a second difference beyond TOL refutes both at once. If affine, the
slope s_T is compared against the landed MEASURED cyclic prices
(e_MM 14.9966 / e_FF 4.0000): agreement = channel-consistent interior
prices; disagreement = channel-dependent interior prices (named, not
attributed). The e_MF/e_FM split stays UNMEASURED either way (P6).

Usage: mufu_lenlin_analysis.py <v8-runlog>"""
import re, sys
from collections import OrderedDict

PATH = sys.argv[1] if len(sys.argv) > 1 else "mufu-lenlin-runlog-20261026.txt"
RES = re.compile(r"^RESULT arm=(\w+) launch=(\d+) n=\d+ med_acc=\d+ "
                 r"med_per_iter=([\d.]+) mean_per_iter=([\d.]+) "
                 r"min_per_iter=([\d.]+) max_per_iter=([\d.]+)")

ORDER = ["M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5"]

# landed MEASURED quantities this instrument is compared against
# (P3/P4), CONSUMED at their commits: cyclic slopes e_MM 14.9966,
# e_FF 4.0000. v7 REPRODUCTION constants (P5): V(M) 10.1602,
# V(F) 10.1758, V(MM)-V(M) 11.0352, V(FF)-V(F) -0.0273.
E_MM_LANDED, E_FF_LANDED = 14.9966, 4.0000
V_M1_V7, V_F1_V7 = 10.1602, 10.1758
D_M2_V7, D_F2_V7 = 11.0352, -0.0273
TOL = 1.0  # cyc: the instrument header's named tolerance


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

print()
print("=== length series: first differences D_T(k) = V(T^k) - V(T^(k-1)), k=2..5")
D = {}
for t, ks in (("M", ["M1", "M2", "M3", "M4", "M5"]), ("F", ["F1", "F2", "F3", "F4", "F5"])):
    d = [V[ks[i]] - V[ks[i - 1]] for i in range(1, 5)]
    D[t] = d
    print(f"    {t}: D({t}(2))={d[0]:+.4f}  D({t}(3))={d[1]:+.4f}  "
          f"D({t}(4))={d[2]:+.4f}  D({t}(5))={d[3]:+.4f}")

print()
print("=== second differences (affine test; every |.| <= 1.0 = P1/P2 hold)")
affine = {}
for t in ("M", "F"):
    sd = [D[t][i + 1] - D[t][i] for i in range(3)]
    ok = all(abs(x) <= TOL for x in sd)
    affine[t] = ok
    print(f"    {t}: " + "  ".join(f"{x:+.4f}" for x in sd) +
          f"  -> {'AFFINE (P' + ('1' if t == 'M' else '2') + ' hold)' if ok else 'NON-AFFINE (P' + ('1' if t == 'M' else '2') + ' FAIL)'}")

print()
print("=== slopes vs the landed MEASURED cyclic prices (P3/P4; mean of first differences)")
slopes = {}
chan = {}
for t, landed in (("M", E_MM_LANDED), ("F", E_FF_LANDED)):
    s = sum(D[t]) / 4.0
    slopes[t] = s
    ok = abs(s - landed) <= TOL
    chan[t] = ok
    print(f"    s_{t} = {s:.4f} vs landed e_{t}{t} = {landed} -> delta {s - landed:+.4f} "
          f"({'ok' if ok else 'FAIL'})")

print()
print("=== P5: v7 REPRODUCTION (cross-instrument consistency, NOT a model prediction)")
p5 = []
def rp(label, got, want):
    ok = abs(got - want) <= TOL
    p5.append(ok)
    print(f"    {label}: got {got:+.4f} vs v7 {want:+.4f} -> delta {got - want:+.4f} ({'ok' if ok else 'FAIL'})")

rp("V(M1) vs v7 V(M)", V["M1"], V_M1_V7)
rp("V(F1) vs v7 V(F)", V["F1"], V_F1_V7)
rp("D_M(2) vs v7 V(MM)-V(M)", D["M"][0], D_M2_V7)
rp("D_F(2) vs v7 V(FF)-V(F)", D["F"][0], D_F2_V7)

print()
print("=== sensitivity, launch-matched indices (arms ran sequentially; pairing is nominal; NOT a prediction)")
for l in (0, 1, 2):
    Vl = {a: data[a][l][0] for a in ORDER}
    parts = []
    for t, ks in (("M", ["M1", "M2", "M3", "M4", "M5"]), ("F", ["F1", "F2", "F3", "F4", "F5"])):
        dl = [Vl[ks[i]] - Vl[ks[i - 1]] for i in range(1, 5)]
        sd = [dl[i + 1] - dl[i] for i in range(3)]
        ok = all(abs(x) <= TOL for x in sd)
        parts.append(f"{t} second-diffs " + "/".join(f"{x:+.4f}" for x in sd) +
                     f" -> {'affine' if ok else 'NON-AFFINE'}")
    print(f"    launch{l}: " + "; ".join(parts))

print()
print("=== P1..P6 VERDICT")
if affine["M"] and affine["F"] and chan["M"] and chan["F"]:
    print("    P1..P4 ALL HOLD: V is affine in length at the landed cyclic slopes.")
    print("    The pure-word interior prices are channel-consistent; the v7 closure")
    print("    failure is localized to MIXED composition (the cross edges) -- the next")
    print("    named question. P6: the e_MF/e_FM split stays UNMEASURED (nothing here")
    print("    admits the estimators).")
elif affine["M"] and affine["F"]:
    print("    P1/P2 HOLD, P3/P4 FAIL: the interior same-pipe prices are")
    print("    CHANNEL-DEPENDENT -- the entry-excluded single-instance form and the")
    print("    cyclic/loop slope form disagree on the interior edge price itself")
    print("    (named, not attributed; any first/last-op-only end artifact is ruled")
    print("    out as the explanation because it cancels across k). The landed cyclic")
    print("    values stay the only measured prices under the registered criterion.")
    print("    P6: the e_MF/e_FM split stays UNMEASURED. The v7 closure residual and")
    print("    this channel discrepancy must be explained together -- next named")
    print("    question.")
else:
    print("    P1/P2 FAIL (NON-AFFINE): the per-op increment itself depends on the")
    print("    word length. NO edge-additive-plus-end-artifact reading survives the")
    print("    pure-word length series: the measured V is REFUTED as edge-additive")
    print("    in-form at the pure-word level (the discipline's premise is implicated)")
    print("    and the end-artifact class (first/last-op-only deviations) is REFUTED")
    print("    with it. A length-dependent realization effect is named, not")
    print("    attributed. P6: the e_MF/e_FM split stays UNMEASURED.")
if not all(p5):
    print("    P5 NOT FULLY HELD (see reproduction lines above): the length-1/2 points")
    print("    do not reproduce v7's own numbers within tolerance -- named; this is a")
    print("    cross-instrument consistency fact, not a model prediction.")

print()
print("=== derived table: V(w) minus V(M1) and V(F1) (NOT an attribution)")
for base in ("M1", "F1"):
    print(f"    V(w) - V({base}): "
          + "  ".join(f"{a}={V[a] - V[base]:+.4f}" for a in ORDER if a != base))
