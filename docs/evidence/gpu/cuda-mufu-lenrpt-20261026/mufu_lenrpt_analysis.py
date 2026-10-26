#!/usr/bin/env python3
"""mufu_lenrpt_analysis.py -- analysis of the v9r BYTE-IDENTICAL REPEAT
of the v9 length-extension instrument (amu-gpu tick 2026-10-26,
JUN-55/JUN-57; scratch, staged to
docs/evidence/gpu/cuda-mufu-lenrpt-20261026/). Parses the RESULT lines
of BOTH run logs (v9's committed run-log and this run's) and adjudicates
the PRE-REGISTERED predictions P0..P6 (registered in the run driver's
bytes before compile and run, and in this file's header, both written
before the first run). Deterministic: two runs produce byte-identical
output.

Definitions: V(w) = pooled median over the 3 launches of med_per_iter;
D_T(k) = V(T^k) - V(T^(k-1)), k = 2..8; D2_T(k) = D_T(k+1) - D_T(k),
k = 2..7; TOL = 1.0 cyc; the ~2.3 class = 1.5 <= |x| <= 3.0.

NO attribution beyond the registered verdicts: no e_MF/e_FM estimator
exists in this instrument (P6); nothing here moves any record,
:measured? flag or workgroup row (rule 4).
"""
import hashlib
import re
import statistics
import sys

V9_LOG = sys.argv[1] if len(sys.argv) > 1 else "v9-run-log.txt"
R2_LOG = sys.argv[2] if len(sys.argv) > 2 else "mufu-lenrpt-runlog-20261026.txt"
TOL = 1.0
LO, HI = 1.5, 3.0  # the ~2.3 class band

M_ARMS = [f"M{k}" for k in range(1, 9)]
F_ARMS = [f"F{k}" for k in range(1, 9)]
ARMS = M_ARMS + F_ARMS

# v9 pooled V values CONSUMED at the v9 commit (P4 targets; cross-checked
# below against the parse of v9's committed run-log).
V9 = {
    "M1": 10.1953, "M2": 23.4531, "M3": 48.3945, "M4": 61.1406,
    "M5": 78.3594, "M6": 81.1445, "M7": 98.4414, "M8": 111.1445,
    "F1": 10.1484, "F2": 10.3555, "F3": 14.1289, "F4": 18.1641,
    "F5": 24.3477, "F6": 26.2031, "F7": 30.5391, "F8": 34.1797,
}
V9_SASS_SHA = "9b27b9fa8d4907e356aeed02211d1e0af799436002c2a2ef9eb99747d418bf60"
CU_SHA = "b98fb39b90ef37a5aac676bbf9af16759213fe6ac422400973f765ad98324079"
VERIFY_SHA = "a917a73760cd4456f4d47a495ab5f5164d81c26e73b630f8c83ea7d77be98789"

res_re = re.compile(r"^RESULT arm=(\S+) launch=(\d+) .* med_per_iter=([0-9.]+) ")
anc_re = re.compile(r"^ANCHOR arm=(\S+) xbits=(\d+)")
recv_re = re.compile(r"^([0-9a-f]{64})  \./(\S+)$")
sass_re = re.compile(r"^([0-9a-f]{64})  microbench\.sass$")


def parse(path):
    per_launch, anchors, recv, sass_sha = {}, [], {}, None
    for ln in open(path):
        m = res_re.match(ln)
        if m:
            arm, launch, v = m.group(1), int(m.group(2)), float(m.group(3))
            per_launch.setdefault(arm, {})[launch] = v
            continue
        m = anc_re.match(ln)
        if m:
            anchors.append((m.group(1), int(m.group(2))))
            continue
        m = recv_re.match(ln)
        if m:
            recv[m.group(2)] = m.group(1)
            continue
        m = sass_re.match(ln)
        if m:
            sass_sha = m.group(1)
    pooled = {a: statistics.median([per_launch[a][l] for l in sorted(per_launch[a])])
              for a in ARMS}
    return per_launch, pooled, anchors, recv, sass_sha


def first_diffs(vs):
    return [vs[k] - vs[k - 1] for k in range(1, len(vs))]


def second_diffs(ds):
    return [ds[k] - ds[k - 1] for k in range(1, len(ds))]


def series(pooled, fam):
    return [pooled[f"{fam}{k}"] for k in range(1, 9)]


def in_class(x):
    return LO <= abs(x) <= HI


v9_pl, v9_pooled, v9_anc, v9_recv, v9_sass = parse(V9_LOG)
r2_pl, r2_pooled, r2_anc, r2_recv, r2_sass = parse(R2_LOG)

print("=== P0 VALIDITY")
print("    v9 committed run-log parse vs v9 CONSUMED pooled values (4dp):")
mismatch = [a for a in ARMS if round(v9_pooled[a], 4) != V9[a]]
print("      " + ("ALL 16 MATCH" if not mismatch else "MISMATCH: " + ", ".join(mismatch)))
print(f"    received-file shas in this run's log: cu {r2_recv.get('gpu-mufu-lenext-microbench.cu', 'ABSENT')}"
      + (" == local" if r2_recv.get("gpu-mufu-lenext-microbench.cu") == CU_SHA else " != local"))
print(f"                                     verify {r2_recv.get('mufu_lenext_verify.py', 'ABSENT')}"
      + (" == local" if r2_recv.get("mufu_lenext_verify.py") == VERIFY_SHA else " != local"))
print(f"    generated microbench.sass sha this run: {r2_sass}")
print(f"    v9's generated artifact sha (target):   {V9_SASS_SHA}")
sass_ok = (r2_sass == V9_SASS_SHA)
recv_ok = (r2_recv.get("gpu-mufu-lenext-microbench.cu") == CU_SHA
           and r2_recv.get("mufu_lenext_verify.py") == VERIFY_SHA)
print(f"    realization byte-identical to v9: {'YES' if sass_ok else 'NO'}")
p0 = sass_ok and recv_ok and not mismatch
print(f"    P0: {'HOLD -- this run adjudicates P4/P5' if p0 else 'FAIL -- the run is INVALID for P4/P5 (named; data enters nothing)'}")

print()
print("=== anchors (no-fold witnesses; the correct repeat-run check is EQUALITY with v9's anchors)")
print(f"    this run: {len(r2_anc)} ANCHOR lines; v9 run: {len(v9_anc)} ANCHOR lines")
anc_same = (r2_anc == v9_anc)
print(f"    anchor lines identical to v9's committed run-log: {'YES (16/16)' if anc_same else 'NO (named)'}")
xbits = sorted({x for _, x in r2_anc})
print(f"    distinct xbits observed: {xbits} (M arms 1065353216; F arms carry per-arm accumulated no-fold witnesses)")

print()
print("=== V(w) per-iteration deltas, per launch (med_per_iter, cyc/iter), THIS RUN")
print("arm   launch0    launch1    launch2    pooled(med of 3)  within-launch min..max")
for arm in ARMS:
    ls = sorted(r2_pl[arm])
    vs = [r2_pl[arm][l] for l in ls]
    row = "".join(f"{v:<11.4f}" for v in vs)
    print(f"{arm:<5}{row}{r2_pooled[arm]:<16.4f}{min(vs):.4f}..{max(vs):.4f}")

print()
print("=== P4: BETWEEN-RUN DELTAS, byte-identical realization (d = v9r pooled - v9 pooled)")
counts = {"within": 0, "class": 0, "other": 0}
class_arms = []
for arm in ARMS:
    d = r2_pooled[arm] - V9[arm]
    if abs(d) <= TOL:
        tag = "within TOL"
        counts["within"] += 1
    elif in_class(d):
        tag = "~2.3 CLASS"
        counts["class"] += 1
        class_arms.append(f"{arm} {d:+.4f}")
    else:
        tag = "other (named)"
        counts["other"] += 1
    print(f"    {arm:<4} v9r {r2_pooled[arm]:>10.4f}  v9 {V9[arm]:>10.4f}  d {d:+9.4f}  {tag}")
print(f"    classification: within {counts['within']}/16, ~2.3 class {counts['class']}/16, other {counts['other']}/16")
if counts["class"]:
    print("    class arms: " + "; ".join(class_arms))
p4a = counts["class"] >= 1
p4b = counts["within"] == 16
if p0:
    print(f"    P4a (predicted): {'HOLD -- the shift mode MOVES between byte-identical runs; it is DYNAMIC (run/launch level); a static-realization-only reading is EXCLUDED' if p4a else 'FAIL'}")
    print(f"    P4b: {'HOLD -- the mode does not move at this granularity; the dynamic-run reading is EXCLUDED here' if p4b else 'FAIL'}")
else:
    print("    P4: NOT ADJUDICATED (P0 FAIL)")

print()
print("=== P5: WITHIN-RUN per-launch level shifts (launch value minus the arm's pooled median, THIS RUN)")
n_class_launch = 0
for arm in ARMS:
    p = r2_pooled[arm]
    devs = [(l, r2_pl[arm][l] - p) for l in sorted(r2_pl[arm])]
    tags = []
    for l, d in devs:
        if in_class(d):
            tags.append(f"launch{l} {d:+.4f} ~2.3 CLASS")
            n_class_launch += 1
        elif abs(d) > TOL:
            tags.append(f"launch{l} {d:+.4f} (outside class, named)")
    if tags:
        print(f"    {arm:<4} " + "; ".join(tags))
p5 = n_class_launch >= 1
print(f"    P5: {'HOLD' if p5 else 'FAIL'} ({n_class_launch} per-launch shifts in the ~2.3 class)")

print()
print("=== P2: NON-AFFINITY REPRODUCTION (this run)")
for fam in ("M", "F"):
    ds = first_diffs(series(r2_pooled, fam))
    d2 = second_diffs(ds)
    d2_sub = second_diffs(ds[:4])
    v_full = "AFFINE" if max(abs(x) for x in d2) <= TOL else "NON-AFFINE"
    v_sub = "AFFINE" if max(abs(x) for x in d2_sub) <= TOL else "NON-AFFINE"
    print(f"    {fam} (k=1..5 subset): " + "  ".join(f"{x:+.4f}" for x in d2_sub) + f"  -> {v_sub}")
    print(f"    {fam} (k=1..8 full):   " + "  ".join(f"{x:+.4f}" for x in d2) + f"  -> {v_full}")
print("    launch-matched sensitivity (nominal pairing; NOT a prediction):")
for l in range(3):
    for fam in ("M", "F"):
        vs = [r2_pl[f"{fam}{k}"][l] for k in range(1, 9)]
        d2 = second_diffs(first_diffs(vs))
        v_full = "AFFINE" if max(abs(x) for x in d2) <= TOL else "NON-AFFINE"
        v_sub = "AFFINE" if max(abs(x) for x in d2[:3]) <= TOL else "NON-AFFINE"
        print(f"      launch{l}: {fam} -> {v_sub} (k=1..5) / {v_full} (k=1..8)")
p2_m = max(abs(x) for x in second_diffs(first_diffs(series(r2_pooled, "M")))) > TOL
p2_f = max(abs(x) for x in second_diffs(first_diffs(series(r2_pooled, "F")))) > TOL
p2 = p2_m and p2_f
print(f"    P2: {'HOLD (both families NON-AFFINE over k=1..8, pooled)' if p2 else 'FAIL'}")

print()
print("=== P3: F PLATEAU (this run)")
d = r2_pooled["F1"] - r2_pooled["F2"]
print(f"    V(F1) {r2_pooled['F1']:.4f} vs V(F2) {r2_pooled['F2']:.4f} -> delta {d:+.4f} "
      + ("P3 HOLD (plateau; |delta| <= TOL)" if abs(d) <= TOL else "P3 FAIL"))
print(f"    (v8's F1>F2 form would read {d:+.4f} > +1.0; it {'RETURNS' if d > TOL else 'does not return'})")

print()
print("=== between-run first-difference drift (derived, NOT a prediction)")
for fam in ("M", "F"):
    ds_r2 = first_diffs(series(r2_pooled, fam))
    ds_v9 = first_diffs(series(V9, fam))
    drift = [a - b for a, b in zip(ds_r2, ds_v9)]
    print(f"    {fam}: " + "  ".join(f"{x:+.4f}" for x in drift))

print()
print("=== P0..P6 VERDICT")
print(f"    P0: {'HOLD' if p0 else 'FAIL'}")
print("    P1: structural verdicts ride in run-log.txt (the transferred verifier output)")
print(f"    P2: {'HOLD' if p2 else 'FAIL'}")
print(f"    P3: {'HOLD' if abs(d) <= TOL else 'FAIL'}")
print(f"    P4: " + ("NOT ADJUDICATED (P0 FAIL)" if not p0 else
                    ("P4a HOLD / P4b FAIL -- DYNAMIC" if p4a else
                     ("P4b HOLD / P4a FAIL -- not dynamic at this granularity" if p4b else
                      "NEITHER branch clean (mixed classification; named)"))))
print(f"    P5: {'HOLD' if p5 else 'FAIL'}")
print("    P6: no e_MF/e_FM estimator computed anywhere (no mixed arms exist in this instrument);")
print("        the split STAYS UNMEASURED")
print("        NOTHING MOVES (rule 4): no record, no :measured? flag, no selection answer, no workgroup row")
print(f"    NOTE: same-UTC-day with every earlier probe; cross-day run 3+ does NOT move")
