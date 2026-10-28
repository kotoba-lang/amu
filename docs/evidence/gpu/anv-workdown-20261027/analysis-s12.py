#!/usr/bin/env python3
"""JUN-59 session 12 analysis -- WORK-DOWN LOCALIZER at fixed B=8 (the NDIV
knob).

Route (frozen in protocol.txt section 6): this script parses ONLY the 15
committed run logs in its own directory (run-<tag>-r<R>.txt) and writes
publication-s12.txt. No other input. Deterministic: running it twice yields
byte-identical publication-s12.txt (checked by diff after the recorded run).
"""
import re, sys, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

# tag -> (BATCH, NDIV), protocol.txt section 2
ARMS = [("c2", 2, 1), ("c8", 8, 1), ("d8", 8, 8), ("d256", 8, 256), ("d4096", 8, 4096)]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMD = {a[0]: a[2] for a in ARMS}
RUNS = [1, 2, 3]
N_BASE = 1000003

# committed anchors (comparison of committed numbers only)
COMMITTED = {"c2": 31, "c8": 32915}
COMMITTED_SRC = {"c2": "sessions 1-11 floor band 31..32", "c8": "session 4 pooled median"}

cell_re = re.compile(
    r"^CELL idx=(\d+) spv=(\S+) op=(\S+) wg=(\d+) forced=(\S+) probe_size=(-?\d+) "
    r"probe_nsub=(-?\d+) probe_wg=(-?\d+) pipeline=(\S+) void=(\d)")
verify_re = re.compile(r"^VERIFY idx=(\d+) checked=(\d+) mismatch=(\d+) ok=(\d)")
sample_re = re.compile(
    r"^SAMPLE round=(\d+) idx=(\d+) batch=(\d+) work_mul=(\d+) ndiv=(\d+) gpu_ticks=(\d+) "
    r"gpu_ns=([\d.]+) per_dispatch_ns=([\d.]+) host_ns=(\d+)")

def load(path):
    cells, verifies, samples, header = {}, [], [], []
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("#"):
            header.append(line)
        elif line.startswith("CELL "):
            m = cell_re.match(line)
            assert m, line
            cells[int(m.group(1))] = dict(spv=m.group(2), op=m.group(3), wg=int(m.group(4)),
                                          forced=m.group(5), probe_size=int(m.group(6)),
                                          probe_nsub=int(m.group(7)), probe_wg=int(m.group(8)),
                                          pipeline=m.group(9), void=int(m.group(10)))
        elif line.startswith("VERIFY "):
            m = verify_re.match(line)
            assert m, line
            verifies.append((int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))))
        elif line.startswith("SAMPLE "):
            m = sample_re.match(line)
            assert m, line
            samples.append((int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)),
                            int(m.group(5)), int(m.group(6)), float(m.group(7)), float(m.group(8)),
                            int(m.group(9))))
        elif line.startswith("# done"):
            header.append(line)
    return cells, verifies, samples, header

def med(xs):
    return statistics.median(xs)

out = []
P = out.append
P("JUN-59 session 12 -- WORK-DOWN LOCALIZER at fixed B=8 (the NDIV knob), publication")
P("Produced ONLY by analysis-s12.py over the 15 committed run logs in this")
P("directory (run-<tag>-r<R>.txt); protocol.txt was frozen before the")
P("first run. Arms = binary compile-time (BATCH, NDIV); all arms run the")
P("same a-set manifest (the ARCHIVED measured spv, 16-digest corpus -- NO")
P("shader derivation this session). The instrument is session 8's")
P("committed snapshot + the 3-hunk NDIV edit (inverse check -> snapshot")
P("bytes EXACT -- derivation-census.txt).")
P("1 nominal work unit = one dispatch of the archived grid (n = 1,000,003);")
P("an arm at B with NDIV=D runs B dispatches of a 1/D grid (integer floor")
P("n -- protocol L2) = B * n / 1,000,003 total nominal units (a DEFINITION,")
P("not a cost claim -- protocol L1). 1 tick = timestampPeriod = 52.083 ns.")
P("")

# ---- load everything, integrity checks ----
data = {}          # (tag, run) -> (cells, verifies, samples, header)
cell_keys = None
integrity = []
header_ok = True
knob_field_ok = True
spv_identity_ok = True
verify_mismatch_total = 0
verify_mismatch_by_arm = {t: 0 for t in TAGS}
forcing_ok = 0
forcing_total = 0
s8_fail = 0
sample_counts_ok = True
base_header = None
for tag in TAGS:
    b, dd = ARMB[tag], ARMD[tag]
    for r in RUNS:
        fn = f"run-{tag}-r{r}.txt"
        cells, verifies, samples, header = load(os.path.join(HERE, fn))
        data[(tag, r)] = (cells, verifies, samples, header)
        keys = tuple(sorted((k, v["op"], v["wg"], v["forced"], v["pipeline"]) for k, v in cells.items()))
        if cell_keys is None:
            cell_keys = keys
        elif keys != cell_keys:
            integrity.append(f"CELL MAP MISMATCH in {fn}")
        hb = tuple(l for l in header if not l.startswith("# n="))
        if base_header is None:
            base_header = hb
        elif base_header != hb:
            header_ok = False
            integrity.append(f"HEADER MISMATCH in {fn}")
        for l in header:
            if l.startswith("# n="):
                mn = re.search(r"n=(\d+)", l)
                mb = re.search(r"batch=(\d+)", l)
                mbar = re.search(r"barrier_n=(\d+)", l)
                mmu = re.search(r"work_mul=(\d+)", l)
                mdi = re.search(r"ndiv=(\d+)", l)
                if (not mb or int(mb.group(1)) != b) or (not mbar or int(mbar.group(1)) != 0) \
                   or (not mmu or int(mmu.group(1)) != 1) or (not mdi or int(mdi.group(1)) != dd):
                    knob_field_ok = False
                    integrity.append(f"HEADER knob FIELD MISMATCH in {fn}: {l}")
                if not mn or int(mn.group(1)) != (N_BASE * 1) // dd:
                    knob_field_ok = False
                    integrity.append(f"HEADER n= FIELD MISMATCH in {fn}: {l}")
        # shader-set identity: every CELL's spv name is an archived .emitted.spv
        for k, v in cells.items():
            ok = v["spv"].endswith(".emitted.spv") and ".iter" not in v["spv"]
            if not ok:
                spv_identity_ok = False
                integrity.append(f"CELL spv SET MISMATCH in {fn} idx={k}: {v['spv']}")
        for (idx, ch, mis, ok) in verifies:
            verify_mismatch_total += mis
            verify_mismatch_by_arm[tag] += mis
            c = cells[idx]
            if c["pipeline"] == "ok":
                forcing_total += 1
                exp_s = 32 if c["forced"] == "default" else int(c["forced"])
                if (c["probe_size"] == exp_s and c["probe_nsub"] == (c["wg"] // exp_s)):
                    forcing_ok += 1
            else:
                if c["forced"] == "8":
                    s8_fail += 1
        ok_cells = [k for k, v in cells.items() if v["pipeline"] == "ok"]
        exp = len(ok_cells) * 25
        if len(samples) != exp:
            sample_counts_ok = False
            integrity.append(f"SAMPLE COUNT {len(samples)} != {exp} in {fn}")
        for (rnd, idx, bt, mt, dt, gt, gn, pdn, hn) in samples:
            if bt != b or mt != 1 or dt != dd:
                knob_field_ok = False
                integrity.append(f"SAMPLE knob FIELD {bt},{mt},{dt} != {b},1,{dd} in {fn}")

P("1. INTEGRITY (computed over the 15 logs):")
P(f"   runs parsed: 15 (5 arms x 3 runs); cell map identical across runs: {cell_keys is not None and not any('CELL MAP' in i for i in integrity)}")
P(f"   headers byte-identical across all runs outside the # n= knob line: {header_ok}")
P(f"   header batch=/work_mul=/ndiv= == run's (B,1,NDIV), barrier_n=0, n=floor(1,000,003/NDIV); every SAMPLE batch=/work_mul=/ndiv= == (B,1,NDIV): {knob_field_ok}")
P(f"   every CELL spv= name is an archived .emitted.spv (no .iter -- the corpus is byte-identical this session): {spv_identity_ok}")
P(f"   SAMPLE lines: 450 per run (18 ok cells x 25 rounds) in 15/15 runs: {sample_counts_ok}")
P(f"   VERIFY mismatch total over all runs: {verify_mismatch_total} (per-arm: "
  + ", ".join(f"{t}={verify_mismatch_by_arm[t]}" for t in TAGS)
  + ") -- bit-exact correctness re-check inside every run; frozen INVALIDATION criterion (protocol section 5): >0 in any run makes that run's NDIV derivation DEFECTIVE and the arm INVALID")
P(f"   forcing reality (pipeline-ok cell-runs where probe_size==forced and probe_nsub==wg/forced): {forcing_ok}/{forcing_total}")
P(f"   S=8 cells fail-closed (pipeline=FAIL, forced=8): {s8_fail} cell-runs (6 per run x 15 runs = 90 expected)")
if integrity:
    for i in integrity:
        P(f"   !! {i}")
P("")

# ---- per-cell pooled medians per arm ----
def pooled(tag, idx):
    xs = []
    for r in RUNS:
        cells, verifies, samples, header = data[(tag, r)]
        xs += [s[5] for s in samples if s[1] == idx]
    return med(xs)

def pooled_host(tag, idx):
    xs = []
    for r in RUNS:
        cells, verifies, samples, header = data[(tag, r)]
        xs += [s[8] for s in samples if s[1] == idx]
    return med(xs)

def run_medians(tag, idx):
    ms = []
    for r in RUNS:
        cells, verifies, samples, header = data[(tag, r)]
        ms.append(med([s[5] for s in samples if s[1] == idx]))
    return ms

ok_cells = sorted([k for k, v in data[("c2", 1)][0].items() if v["pipeline"] == "ok"])
def ckey(idx):
    c = data[("c2", 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])

sum128 = [k for k in ok_cells if ckey(k) == ("sum", 128, "16")][0]

P("2. THE MEASURED BRACKETS (pooled median gpu_ticks over 3 runs x 25 rounds per cell):")
P("   each row: (sum,128,S=16) exact value, per-run median band at that cell,")
P("   then min..max over the 18 pipeline-ok cells; host_ns at (sum,128,S=16)")
P("")
P("   arm    B  NDIV     n        nominal-tot  (sum,128,16)   run-median band    min..max over 18 cells   host_ns")
for tag in TAGS:
    b, dd = ARMB[tag], ARMD[tag]
    n = (N_BASE * 1) // dd
    vals = [pooled(tag, k) for k in ok_cells]
    v16 = pooled(tag, sum128)
    rms = run_medians(tag, sum128)
    hn = pooled_host(tag, sum128)
    tot = b * n / N_BASE
    P(f"   {tag}  {b}  {dd:<5} {n:>8}  {tot:>10.5f}  {v16:>10.0f}     {min(rms):>8.0f}..{max(rms):<8.0f}  {min(vals):>8.0f}..{max(vals):<8.0f}  {hn:>9.0f}")
P("")

# ---- classification (protocol.txt section 3 thresholds) ----
def classify(tag):
    vals = [pooled(tag, k) for k in ok_cells]
    if all(v <= 100 for v in vals):
        return "FLOOR"
    if all(v >= 1000 for v in vals):
        return "CAPTURED"
    return "INTERMEDIATE/MIXED"

CLASS = {tag: classify(tag) for tag in TAGS}

P("3. PRE-REGISTERED LETTERS (thresholds frozen in protocol.txt section 3:")
P("   FLOOR <= 100 ticks at all 18 cells; CAPTURED >= 1000 ticks at all 18;")
P("   anything else INTERMEDIATE/MIXED):")
P("")
for tag in TAGS:
    b, dd = ARMB[tag], ARMD[tag]
    n = (N_BASE * 1) // dd
    P(f"   class {tag} (B={b}, NDIV={dd}, n={n}, {b*n/N_BASE:.5f} nominal units): {CLASS[tag]}")
P("")

# INVALIDATION check first (frozen)
arms_invalid = sorted(t for t in TAGS if verify_mismatch_by_arm[t] > 0)
if arms_invalid:
    P("   INVALIDATION CRITERION FIRED (frozen): VERIFY mismatch > 0 in arm(s)")
    P(f"   {arms_invalid} -- the NDIV derivation is DEFECTIVE for those runs")
    P("   (a stored value changed: buffer sizing / PARTS_CAP / CPU reference)")
    P("   and no letter below is evaluable from those arms.")
    P("")

# C1 first (prerequisite; W1-W3 depend on it)
c1_c2_ok = CLASS["c2"] == "FLOOR"
c1_parts = [f"c2 satisfies FLOOR (committed floor band 31..32 at B=2): {c1_c2_ok}"]
v8 = pooled("c8", sum128)
c1_c8_ok = abs(v8 - COMMITTED["c8"]) <= 0.05 * COMMITTED["c8"]
c1_parts.append(f"c8 (sum,128,16) pooled median {v8:.0f} within +/-5% of committed {COMMITTED['c8']} ({COMMITTED_SRC['c8']}): {c1_c8_ok}")
c1_ok = c1_c2_ok and c1_c8_ok
P("   C1 ARCHIVED CONTROL REPLICATION (numeric agreement with the committed")
P("   value at the control's OWN (B,NDIV) -- the a-set runs the ARCHIVED")
P("   spv bytes and NDIV=1 reproduces the archived N_ELEMENTS arithmetic")
P("   exactly (protocol section 1), so this pins the derivation edit to")
P("   archived behaviour as well as the environment):")
for s in c1_parts:
    P(f"     {s}")
if c1_ok:
    P("     VERDICT: branch (a) both controls satisfy their criteria --")
    P("     W1-W3 are evaluated against the row question.")
else:
    P("     VERDICT: branch (b) replication discrepancy (bearing on the")
    P("     environment or the derivation pin); W1-W3 interpretation is")
    P("     FLAGGED; cause UNMEASURED.")
P("")

# W1 (the row question)
P("   W1 THE ROW QUESTION (capture removability at B=8 by work-down; the")
P("   class of d8 -- 8 dispatches of n=125,000 = 1.0 total nominal unit,")
P("   HALF the c2 control's 2.0 total units which FLOOR):")
if arms_invalid and "d8" in arms_invalid:
    P("     VERDICT: NOT EVALUABLE (the INVALIDATION criterion fired for d8).")
elif not c1_ok:
    P("     VERDICT: interpretation FLAGGED by the C1 discrepancy; the class")
    P("     assignments above stand as measured content.")
elif CLASS["d8"] == "CAPTURED":
    P("     VERDICT: branch (a) -- d8 is CAPTURED: the capture at B=8 is NOT")
    P("     REMOVABLE at 1/8 per-dispatch work. With sessions 8-11 (work UP")
    P("     at B<=2, never reaching the capture) the capture is not a")
    P("     total-work threshold from EITHER direction; dispatch count stays")
    P("     implicated in the strong sense. Observable only; NO causal")
    P("     mechanism claimed or measured.")
elif CLASS["d8"] == "FLOOR":
    P("     VERDICT: branch (b) -- d8 is FLOOR: the capture at B=8 IS")
    P("     REMOVABLE by work-down. A PER-DISPATCH work threshold exists at")
    P("     B=8 inside the (1/8, 1] nominal-unit band (2 grid points; no")
    P("     interpolation, no linearity claim); the capture needs BOTH")
    P("     dispatch count >= 3 (session 7's onset) AND per-dispatch work")
    P("     above that threshold, and the sessions 8-11 reading narrows to")
    P("     'not reachable by total work at B<=2' with the work axis")
    P("     re-entering at fixed B. Observable only; NO causal mechanism")
    P("     claimed or measured.")
else:
    P(f"     VERDICT: branch (c) -- d8 is {CLASS['d8']}: the work-down dose")
    P("     at 1/8 per-dispatch work does not classify cleanly at B=8;")
    P("     cell-quantified in section 2; mechanism UNMEASURED.")
P("")

# W2 (descriptive dose curve)
P("   W2 WORK-DOWN DOSE CURVE (descriptive, at B=8): classes and bracket")
P("   figures as per-dispatch work shrinks; the linear-work expectation")
P("   (bracket ~ c8/NDIV) is a descriptive comparison ONLY -- NO")
P("   linearity claim, no interpolation:")
c8_v = pooled("c8", sum128)
for tag in ["d8", "d256", "d4096"]:
    v = pooled(tag, sum128)
    exp_lin = c8_v / ARMD[tag]
    P(f"     {tag}: class {CLASS[tag]}, bracket {v:.0f} ticks (c8/{ARMD[tag]} = {exp_lin:.0f} ticks if linear in work); host_ns {pooled_host(tag, sum128):.0f}")
P("")

# W3 (descriptive parity)
v_d8 = pooled("d8", sum128)
v_c2 = pooled("c2", sum128)
P("   W3 TOTAL-WORK PARITY (descriptive): d8 (1.0 total nominal unit, 8")
P("   dispatches) vs c2 (2.0 total units, 2 dispatches):")
P(f"     d8 bracket {v_d8:.0f} ticks / c2 bracket {v_c2:.0f} ticks = {v_d8/max(v_c2,1e-9):.3f}")
P(f"     classes: d8 {CLASS['d8']} vs c2 {CLASS['c2']} -- observable split only; NO mechanism claimed.")
P("")

# X1 realization (descriptive)
h_c2 = pooled_host("c2", sum128)
P("   X1 REALIZATION (descriptive, computed from section 2's host_ns values,")
P("   NO new measurement and NO linearity claim; host_ns is the HOST-side")
P("   proxy -- protocol L3):")
for tag in TAGS:
    h = pooled_host(tag, sum128)
    P(f"     {tag}: host_ns {h:.0f} = {h/h_c2:.3f}x c2; per-dispatch host_ns {h/ARMB[tag]:.0f}")
P("")

P("4. DERIVED (arithmetic over section 2, no new measurement):")
for tag in TAGS:
    b, dd = ARMB[tag], ARMD[tag]
    n = (N_BASE * 1) // dd
    v = pooled(tag, sum128)
    hn = pooled_host(tag, sum128)
    line = (f"   {tag}: bracket {v:.0f} ticks = {v*52.083/1000:.2f} us;"
            f" host_ns {hn:.0f}; {b*n/N_BASE:.5f} nominal units (n={n})")
    if tag in COMMITTED:
        d = (v - COMMITTED[tag]) / COMMITTED[tag] * 100
        line += f"; vs committed {COMMITTED[tag]} ({COMMITTED_SRC[tag]}): {d:+.2f}%"
    else:
        line += " (no committed anchor at this NDIV -- new)"
    P(line)
P("")

P("5. RULE 4 -- NOTHING MOVES: no workgroup row, no :measured? flag, no selection")
P("   answer; accelerator-targets defaults remain provisional design assumptions")
P("   (:measured? false). This is NOT the baseline-vs-variant contract of")
P("   accelerator-subgroup-reduce.cljk. NO vendor optimization exists for Intel")
P("   and none is claimed. No causal mechanism is claimed by any letter above.")
P("")

# UNMEASURED: named list, with the L4 ambiguity kept conditional on the data
unm = [
    "6. UNMEASURED (named): any causal mechanism for the undercount, the capture,",
    "   the onset location, or any work-down transition; WHY capture turns on where",
    "   it does; the GPU-side cost inside a B<=2 bracket (unobservable on this",
    "   instrument -- protocol L3); any NDIV outside {1,8,256,4096}; any B outside",
    "   {2,8}; any WORK_MUL > 1 this session; any n outside the four protocol-L2",
    "   values; anything between the four grid points; session 2's run-1 dip cause;",
    "   cross-day replication; S=8 timing; every W outside {128,256}; shape 2; BT",
    "   ordering; any baseline-vs-variant sign; non-empty barriers; anything off",
    "   this host.",
]
if CLASS["d4096"] == "FLOOR":
    unm.insert(6, "   the L4 ambiguity AT d4096 (n=244): its FLOOR cannot be separated")
    unm.insert(7, "   between the undercount phenomenon and plain timestamp resolution at")
    unm.insert(8, "   near-empty grids on this instrument (protocol L4) -- named, not hidden;")
P("\n".join(unm))

text = "\n".join(out) + "\n"
open(os.path.join(HERE, "publication-s12.txt"), "w").write(text)
print(text)
