#!/usr/bin/env python3
"""PRE-REGISTERED analyzer for the load-manipulation experiment ROUND 2
(JUN-58, tick 20261020-16xx, parent JUN-55). This file's rules were fixed
BEFORE the first dispatched run (its sha256 is recorded in the README next
to the dispatch timestamps); outcomes are read through it unchanged.

WHY ROUND 2. Round 1 (../load-manip-20261020/) completed 8/8 verified runs
but adjudicated NOTHING: INCONCLUSIVE-DOSE, because the host's NATURAL load
rose through the pre-registered arm-I threshold (load1 <= 16) during the
idle arm (run-start load1 15.70-20.88, three of four above 16), so the two
arms' doses overlapped from below. Round 1's README prescribed exactly one
of: a quieter window, a matched-load design, or a dose threshold chosen
from the observed idle floor, re-registered BEFORE dispatch. This round 2
takes the third option plus the first as a gate.

DESIGN (fixed here before dispatch). Same pinned probe, same cells, same
fixture bytes as every chain datum and as round 1; the ONLY manipulated
variable is host CPU load.
- Arms: I = natural host load, no induced load; L = induced CPU load
  (12 CPU-burner processes started >=120 s before the first L run and
  killed after the last). Blocked order I then L, unchanged from round 1 --
  the fixed order still confounds dose with time drift, still recorded as
  a confound and not claimed away.
- Runs: 2 run-pairs per arm (pairs 1-2 = I, 3-4 = L), each pair one run
  per cell w64t31 (anchor) / w64t32 (flip cell) at lanes 2,095,104, cell
  order rotated t31,t32 / t32,t31 / t31,t32 / t32,t31. n = 2 per cell per
  arm; the per-run iqr (within-run over 32 round-ratios) is the endpoint.
- DOSE RULE (RE-REGISTERED from round 1's observed idle floor, BEFORE this
  dispatch): a run is dose-valid iff its run-START load1 AND its run-END
  load1 are both inside its arm's band -- arm I: load1 <= 25.0; arm L:
  load1 > 40.0. The contrast is DOSE-VALID iff all four I runs are in the
  I band AND all four L runs are in the L band. Bands are non-overlapping
  (25.0 < 40.0). Threshold provenance, disclosed: round 1 observed arm-I
  run-start load1 15.70-20.88 and arm-L 45.87-78.39, so 25.0 = the
  observed idle floor's top + headroom and 40.0 = the observed loaded
  floor's bottom - headroom. The check tests ARM SEPARATION (the two arms'
  doses must not overlap), not that the host is idle; the threshold swap
  is a design repair made in response to round 1's failure mode and is
  not claimed as anything else. The end-load clause is new: round 1 failed
  by load rising THROUGH the arm, which a start-only check cannot see.
- QUIET-WINDOW GATE (new; dispatch side, ../load-manip2-20261020/
  run-manip2.sh): before every arm-I run attempt the dispatcher polls
  uptime every 5 s and starts the run only when load1 <= 22.0 (gate below
  the check threshold 25.0, headroom for the 1-minute damping to move
  during the 2-minute run). If no window occurs within 600 s the slot is
  left missing and logged GATE-TIMEOUT -- reported, never silently dropped.
- Retention: only runs with `RESULT verified=true` enter any count; failed
  or truncated attempts are preserved as attempt-*.log and counted as
  failures. Rounds 1 and 2 are SEPARATE pre-registrations and are never
  pooled.

ENDPOINTS (fixed here before dispatch; unchanged from round 1).
- Primary: per-run SPEEDUP iqr per cell per arm; chain-clean = iqr <= 0.05
  (the chain's rule, carried unchanged). The claim under test: clean runs
  concentrate in arm I and IQR-dirty runs in arm L at w64t32 (the cell
  where the corpus's load-noise association lives).
- Pooled: exact two-sided Mann-Whitney U on SPEEDUP-iqr (I vs L), exact
  by exhaustive enumeration of label splits -- no seed, no approximation.
- Dose-response (descriptive): Spearman rho(load1, iqr) over all retained
  runs (run-START load1), exact two-sided permutation p by exhaustive
  permutation (n <= 8).
- Secondary (observational ONLY): sign of the gap per cell per arm. This
  experiment is NOT a cross-tick sign probe: it never adjudicates the
  transition series and the series count is untouched.

INTERPRETATION RULES (fixed here before dispatch).
- I-arm iqr < L-arm iqr at w64t32 with the clean contrast I-clean / L-
  dirty, and dose-valid: "manipulated CPU load degrades flip-cell
  precision -- supports (does not prove) the causal direction load->noise
  on the CPU-load axis". It still does not attribute the corpus's load
  SOURCE, and CPU load may only proxy whatever else the load tracks.
- No separation: "no effect detected at this dose and n"; the causal
  direction stays UNMEASURED. A null at n=2 per cell per arm bounds
  little and is reported as such.
- Everything else (dose-invalid, gate-timeout slots, partial batch,
  failures): reported exactly as observed, labeled, adjudicated as
  nothing.
- This analyzer never touches kotoba.compiler.accelerator-targets and
  never flips :measured? on any row.
"""
import re, statistics, itertools, os

ev = os.path.dirname(os.path.abspath(__file__))
out_path = os.path.join(ev, "analyze-manip2.txt")

PAIRS = [1, 2, 3, 4]
CELLS = ["w64t31", "w64t32"]
ARM = {1: "I", 2: "I", 3: "L", 4: "L"}
DOSE_I_MAX = 25.0   # re-registered from round 1's observed idle floor
DOSE_L_MIN = 40.0   # re-registered from round 1's observed loaded floor


def line_of(txt, key):
    for ln in txt.splitlines():
        if key in ln:
            return ln
    return None


def lines_of(txt, key):
    return [ln for ln in txt.splitlines() if key in ln]


def num(pat, ln):
    m = re.search(pat, ln)
    if not m:
        raise SystemExit(f"missing {pat!r} in {ln!r}")
    return float(m.group(1))


data = {}
missing = []
for pair in PAIRS:
    for cell in CELLS:
        p = os.path.join(ev, f"run-{pair}-{cell}.log")
        if not os.path.exists(p):
            missing.append(f"run-{pair}-{cell}.log")
            continue
        txt = open(p).read()
        if "RESULT\tverified=true" not in txt:
            missing.append(f"run-{pair}-{cell}.log (NOT verified)")
            continue
        gap = num(r"ns/dispatch=(-?[\d.]+)", line_of(txt, "GAP"))
        sp_line = line_of(txt, "SPEEDUP")
        med = num(r"median=([\d.]+)", sp_line)
        iqr = num(r"iqr=([\d.]+)", sp_line)
        mn = num(r"min=([\d.]+)", sp_line)
        mx = num(r"max=([\d.]+)", sp_line)
        fs_line = line_of(txt, "FLOORSHARE")
        fs_b = num(r"floor/baseline=([\d.]+)", fs_line)
        fs_v = num(r"floor/variant=([\d.]+)", fs_line)
        ls = lines_of(txt, "load averages")
        load_s = num(r"load averages: ([\d.]+)", ls[0])
        load_e = num(r"load averages: ([\d.]+)", ls[-1])
        when = line_of(txt, "Oct").strip()
        data[(pair, cell)] = dict(
            arm=ARM[pair], gap=gap, med=med, iqr=iqr, mn=mn, mx=mx,
            fs_b=fs_b, fs_v=fs_v, load_s=load_s, load_e=load_e, when=when,
            verdict=sp_line.split("vs-1.0=")[-1].strip())

lines = []
lines.append("===== load-manipulation experiment ROUND 2 (JUN-58): manipulated CPU load vs SPEEDUP-iqr")
lines.append(f"retained runs: {len(data)} of {len(PAIRS) * len(CELLS)};  missing/unverified: {missing if missing else 'none'}")
lines.append("arms: I = natural load (pairs 1-2), L = 12 CPU burners (pairs 3-4); per-run iqr is within-run over 32 round-ratios")
lines.append("dose rule RE-REGISTERED before dispatch: I runs load1<=25.0 and L runs load1>40.0, checked at run START and run END")

for pair in PAIRS:
    for cell in CELLS:
        r = data.get((pair, cell))
        if r is None:
            lines.append(f"pair{pair} {cell} [{ARM[pair]}]: MISSING")
            continue
        lines.append(
            f"pair{pair} {cell} [{r['arm']}] [{r['when']}]: gap={r['gap']:.1f} ns/dispatch  "
            f"speedup median={r['med']:.4f} iqr={r['iqr']:.4f} min={r['mn']:.4f} max={r['mx']:.4f}  "
            f"floor/baseline={r['fs_b']:.4f}  floor/variant={r['fs_v']:.4f}  "
            f"load1 start={r['load_s']} end={r['load_e']}  vs-1.0={r['verdict']}")

# per-cell per-arm summaries
lines.append("")
lines.append("===== per-cell per-arm (primary endpoint)")
for cell in CELLS:
    for arm in ("I", "L"):
        runs = [data[(p, cell)] for p in PAIRS if ARM[p] == arm and (p, cell) in data]
        if not runs:
            lines.append(f"{cell} arm{arm}: no retained runs")
            continue
        iqrs = [r["iqr"] for r in runs]
        clean = sum(1 for i in iqrs if i <= 0.05)
        gaps = [r["gap"] for r in runs]
        lines.append(
            f"{cell} arm{arm}: n={len(runs)}  iqr={[round(i, 4) for i in iqrs]}  "
            f"median_iqr={statistics.median(iqrs):.4f}  clean(iqr<=0.05)={clean}/{len(runs)}  "
            f"signs={'/'.join('+' if g > 0 else '-' for g in gaps)}  "
            f"load1 start={[r['load_s'] for r in runs]} end={[r['load_e'] for r in runs]}")

# manipulation check (dose validity, re-registered thresholds, both endpoints)
lines.append("")
lines.append("===== manipulation check (RE-REGISTERED: I runs load1<=25.0, L runs load1>40.0, start AND end)")
allr = [data[k] for k in data]
il = [(r["load_s"], r["load_e"]) for r in allr if r["arm"] == "I"]
ll = [(r["load_s"], r["load_e"]) for r in allr if r["arm"] == "L"]
i_ok = bool(il) and all(s <= DOSE_I_MAX and e <= DOSE_I_MAX for s, e in il)
l_ok = bool(ll) and all(s > DOSE_L_MIN and e > DOSE_L_MIN for s, e in ll)
dose_valid = i_ok and l_ok and len(il) == 4 and len(ll) == 4
lines.append(f"arm I load1 (start,end): {il}  band ok={i_ok} ({len(il)}/4 runs)")
lines.append(f"arm L load1 (start,end): {ll}  band ok={l_ok} ({len(ll)}/4 runs)")
lines.append(f"DOSE-VALID={dose_valid}")

# exact Mann-Whitney U on pooled iqr (I vs L); iqr is sign-independent so
# pooling the two cells is pre-registered as admissible
lines.append("")
lines.append("===== pooled iqr contrast (exact two-sided Mann-Whitney U, exhaustive)")
xi = [data[k]["iqr"] for k in data if data[k]["arm"] == "I"]
xl = [data[k]["iqr"] for k in data if data[k]["arm"] == "L"]
if xi and xl:
    allv = xi + xl
    n1, n2 = len(xi), len(xl)
    u_obs = sum(1 for a in xi for b in xl if a < b) + 0.5 * sum(1 for a in xi for b in xl if a == b)
    u_c = n1 * n2 / 2.0
    dev_obs = abs(u_obs - u_c)
    ge = 0
    total = 0
    for idx in itertools.combinations(range(n1 + n2), n1):
        s1 = [allv[i] for i in idx]
        s2 = [allv[i] for i in range(n1 + n2) if i not in idx]
        u = sum(1 for a in s1 for b in s2 if a < b) + 0.5 * sum(1 for a in s1 for b in s2 if a == b)
        total += 1
        if abs(u - u_c) >= dev_obs - 1e-12:
            ge += 1
    lines.append(f"arm I iqr: {[round(i, 4) for i in xi]} (median {statistics.median(xi):.4f})")
    lines.append(f"arm L iqr: {[round(i, 4) for i in xl]} (median {statistics.median(xl):.4f})")
    lines.append(f"U={u_obs} (chance {u_c})  exact two-sided p={ge}/{total} = {ge / total:.4f}")

# dose-response, descriptive, exact permutation p (exhaustive)
lines.append("")
lines.append("===== dose-response (descriptive): Spearman rho(load1-start, iqr), exact permutation p")
if len(allr) >= 3:
    loads = [r["load_s"] for r in allr]
    iqrs = [r["iqr"] for r in allr]

    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        rk = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                rk[order[k]] = avg
            i = j + 1
        return rk

    def pearson(a, b):
        ma, mb = statistics.mean(a), statistics.mean(b)
        num_ = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
        return num_ / den if den else 0.0

    rl, ri = ranks(loads), ranks(iqrs)
    rho = pearson(rl, ri)
    ge = 0
    total = 0
    for perm in itertools.permutations(ri):
        total += 1
        if abs(pearson(rl, list(perm))) >= abs(rho) - 1e-12:
            ge += 1
    lines.append(f"n={len(allr)}  rho={rho:.4f}  exact two-sided p={ge}/{total} = {ge / total:.4f}")

lines.append("")
lines.append("===== what this bounds, honestly (pre-registered)")
if not allr:
    lines.append("no retained runs -- nothing measured")
elif len(il) < 4 or len(ll) < 4:
    lines.append("INCONCLUSIVE-PARTIAL: a gate-timeout slot left an arm short of its 4 runs; no outcome pattern is read as evidence")
elif not dose_valid:
    lines.append("INCONCLUSIVE-DOSE: the manipulation check failed; no outcome pattern is read as evidence")
else:
    ci = [data[(p, "w64t32")]["iqr"] for p in PAIRS if ARM[p] == "I" and (p, "w64t32") in data]
    cl = [data[(p, "w64t32")]["iqr"] for p in PAIRS if ARM[p] == "L" and (p, "w64t32") in data]
    if ci and cl and max(ci) <= 0.05 and min(cl) > 0.05:
        lines.append("flip cell w64t32: arm I all clean, arm L all dirty -> manipulated CPU load degrades flip-cell precision; supports (does not prove) load->noise causality on the CPU-load axis; load SOURCE stays UNATTRIBUTED; n=2 per cell per arm is pilot replication")
    else:
        lines.append("no clean/dirty separation at w64t32 at this dose and n -> no effect detected; causal direction stays UNMEASURED (a null at n=2 per cell per arm bounds little)")
lines.append("the transition series is untouched (this is not a cross-tick sign probe); :measured? rows untouched; sign counts above are observational only")
lines.append("rounds 1 and 2 are separate pre-registrations and are never pooled")

text = "\n".join(lines) + "\n"
open(out_path, "w").write(text)
print(text)
