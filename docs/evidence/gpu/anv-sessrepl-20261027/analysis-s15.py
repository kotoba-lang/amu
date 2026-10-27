#!/usr/bin/env python3
"""JUN-59 session 15 analysis -- THE SESSION-REPLICATION TRIPLE (third
same-day session at the boundary anchors).

Route (frozen in protocol.txt section 6): this script parses ONLY the 21
committed run logs in its own directory (run-<tag>-r<R>.txt) and writes
publication-s15.txt. No other input. Deterministic: running it twice yields
byte-identical publication-s15.txt (checked by diff after the recorded run).

Cross-session reference values are frozen in protocol.txt section 3 and
embedded below as named constants (session-13 / session-14 committed
values); they are comparison values only and never this session's
measurements.
"""
import re, sys, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

# tag -> (BATCH, NDIV), protocol.txt section 2
ARMS = [("c2", 2, 1), ("c8", 8, 1), ("d128", 8, 128), ("d160", 8, 160),
        ("d192", 8, 192), ("d224", 8, 224), ("d256", 8, 256)]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMD = {a[0]: a[2] for a in ARMS}
RUNS = [1, 2, 3]
N_BASE = 1000003

# committed control anchors (comparison of committed numbers only)
COMMITTED = {"c2": 31, "c8": 32915}
COMMITTED_SRC = {"c2": "sessions 1-14 floor band 31..32",
                 "c8": "session 4 pooled median"}
# cross-session anchors (protocol section 3; (sum,128,S=16) pooled medians)
S13_REF = {"d128": 167, "d256": 34}          # publication-s13.txt
S13_CLS = {"d128": "INTERMEDIATE/MIXED", "d256": "FLOOR"}
S13_HOST = {"d128": 80501, "d256": 82303}
S14_REF = {"d128": 192, "d160": 285, "d192": 84, "d224": 56, "d256": 55}
S14_CLS = {"d128": "INTERMEDIATE/MIXED", "d160": "INTERMEDIATE/MIXED",
           "d192": "INTERMEDIATE/MIXED", "d224": "INTERMEDIATE/MIXED",
           "d256": "INTERMEDIATE/MIXED"}
S14_HOST = {"c2": 677584, "c8": 2434831, "d128": 91050, "d160": 114033,
            "d192": 107701, "d224": 109484, "d256": 121587}

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
P("JUN-59 session 15 -- THE SESSION-REPLICATION TRIPLE (third same-day session")
P("at the boundary anchors), publication")
P("Produced ONLY by analysis-s15.py over the 21 committed run logs in this")
P("directory (run-<tag>-r<R>.txt); protocol.txt was frozen before the")
P("first run. Arms = binary compile-time (BATCH, NDIV); all arms run the")
P("same a-set manifest (the ARCHIVED measured spv, 16-digest corpus --")
P("ZERO derivation this session: the instrument is session 14's committed")
P("NDIV-derived source byte-identical, digest a5e539f0... -- derivation-census.txt).")
P("The independent variable is the SESSION: this is the third same-day")
P("replication point (session 13 14:53Z, session 14 15:24Z, session 15")
P("15:55Z -- all UTC 2026-10-27; protocol L8: cross-UTC-day stays UNMEASURED).")
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

P("1. INTEGRITY (computed over the 21 logs):")
P(f"   runs parsed: 21 (7 arms x 3 runs); cell map identical across runs: {cell_keys is not None and not any('CELL MAP' in i for i in integrity)}")
P(f"   headers byte-identical across all runs outside the # n= knob line: {header_ok}")
P(f"   header batch=/work_mul=/ndiv= == run's (B,1,NDIV), barrier_n=0, n=floor(1,000,003/NDIV); every SAMPLE batch=/work_mul=/ndiv= == (B,1,NDIV): {knob_field_ok}")
P(f"   every CELL spv= name is an archived .emitted.spv (no .iter -- the corpus is byte-identical this session): {spv_identity_ok}")
P(f"   SAMPLE lines: 450 per run (18 ok cells x 25 rounds) in 21/21 runs: {sample_counts_ok}")
P(f"   VERIFY mismatch total over all runs: {verify_mismatch_total} (per-arm: "
  + ", ".join(f"{t}={verify_mismatch_by_arm[t]}" for t in TAGS)
  + ") -- bit-exact correctness re-check inside every run; frozen INVALIDATION criterion (protocol section 5): >0 in any run makes that run DEFECTIVE and the arm INVALID")
P(f"   forcing reality (pipeline-ok cell-runs where probe_size==forced and probe_nsub==wg/forced): {forcing_ok}/{forcing_total}")
P(f"   S=8 cells fail-closed (pipeline=FAIL, forced=8): {s8_fail} cell-runs (6 per run x 21 runs = 126 expected)")
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
    P(f"   {arms_invalid} -- the knob arithmetic is WRONG at those rungs")
    P("   (a stored value changed: buffer sizing / PARTS_CAP / CPU reference)")
    P("   and no letter below is evaluable from those arms.")
    P("")

# C1 first (prerequisite; W letters depend on it)
c1_c2_ok = CLASS["c2"] == "FLOOR"
c1_parts = [f"c2 satisfies FLOOR (committed floor band 31..32 at B=2): {c1_c2_ok}"]
v8 = pooled("c8", sum128)
c1_c8_ok = abs(v8 - COMMITTED["c8"]) <= 0.05 * COMMITTED["c8"]
c1_parts.append(f"c8 (sum,128,16) pooled median {v8:.0f} within +/-5% of committed {COMMITTED['c8']} ({COMMITTED_SRC['c8']}): {c1_c8_ok}")
c1_ok = c1_c2_ok and c1_c8_ok
P("   C1 ARCHIVED CONTROL REPLICATION (numeric agreement with the committed")
P("   value at the control's OWN (B,NDIV) -- the a-set runs the ARCHIVED")
P("   spv bytes through the byte-identical session-14 instrument, so this")
P("   pins the environment as well):")
for s in c1_parts:
    P(f"     {s}")
if c1_ok:
    P("     VERDICT: branch (a) both controls satisfy their criteria --")
    P("     the W letters are evaluated against the row question.")
else:
    P("     VERDICT: branch (b) replication discrepancy (bearing on the")
    P("     environment pin); W letters interpretation is FLAGGED; cause UNMEASURED.")
P("")

# C2 cross-session anchor placement
def band5(ref):
    return (ref * 0.95, ref * 1.05)

vd128 = pooled("d128", sum128)
vd256 = pooled("d256", sum128)
c2_parts = []
# d256 branches
lo13, hi13 = band5(S13_REF["d256"])   # 32.3..35.7 (class band for FLOOR is the class criterion)
lo14, hi14 = band5(S14_REF["d256"])   # 52.25..57.75
if CLASS["d256"] == "FLOOR":
    d256_branch = "(a)"
    c2_parts.append(f"d256 class FLOOR (session 13's committed class FLOOR): TRUE -- branch (a)")
elif CLASS["d256"] == "CAPTURED":
    d256_branch = "(d)"
    c2_parts.append(f"d256 class CAPTURED (a class neither session saw): TRUE -- branch (d)")
elif lo14 <= vd256 <= hi14:
    d256_branch = "(b)"
    c2_parts.append(f"d256 class INTERMEDIATE/MIXED AND pooled median {vd256:.0f} within +/-5% of session-14 committed {S14_REF['d256']} ({lo14:.1f}..{hi14:.1f}): TRUE -- branch (b)")
else:
    d256_branch = "(c)"
    c2_parts.append(f"d256 class INTERMEDIATE/MIXED AND pooled median {vd256:.0f} outside +/-5% of session-14 committed {S14_REF['d256']} ({lo14:.1f}..{hi14:.1f}): TRUE -- branch (c) -- a third distinct bracket")
# d128 branches (the two +/-5% bands are disjoint)
lo13d, hi13d = band5(S13_REF["d128"])  # 158.65..175.35
lo14d, hi14d = band5(S14_REF["d128"])  # 182.40..201.60
if lo13d <= vd128 <= hi13d:
    d128_branch = "(a)"
    c2_parts.append(f"d128 pooled median {vd128:.0f} within +/-5% of session-13 committed {S13_REF['d128']} ({lo13d:.2f}..{hi13d:.2f}): TRUE -- branch (a)")
elif lo14d <= vd128 <= hi14d:
    d128_branch = "(b)"
    c2_parts.append(f"d128 pooled median {vd128:.0f} within +/-5% of session-14 committed {S14_REF['d128']} ({lo14d:.2f}..{hi14d:.2f}): TRUE -- branch (b)")
else:
    d128_branch = "(c)"
    c2_parts.append(f"d128 pooled median {vd128:.0f} outside BOTH +/-5% bands (session-13 {lo13d:.2f}..{hi13d:.2f} around {S13_REF['d128']}; session-14 {lo14d:.2f}..{hi14d:.2f} around {S14_REF['d128']}): TRUE -- branch (c)")
P("   C2 CROSS-SESSION ANCHOR PLACEMENT (the two anchors whose readings moved")
P("   between sessions 13 and 14, judged against BOTH prior sessions' committed")
P("   values at their OWN (B,NDIV); branches frozen in protocol section 4):")
for s in c2_parts:
    P(f"     {s}")
P(f"     d256 branch {d256_branch}; d128 branch {d128_branch}.")
P("")

# W1 the row question
P("   W1 THE ROW QUESTION (the session-stability of the boundary anchors,")
P("   combining the C2 outcomes):")
s13_like = (d256_branch == "(a)" and d128_branch == "(a)")
s14_like = (d256_branch == "(b)" and d128_branch == "(b)")
if s13_like:
    w1 = "(a)"
    P("     VERDICT: branch (a) S13-LIKE -- both anchors land with session 13")
    P("     (d256 FLOOR; d128 inside the 167 band). The third point joins")
    P("     session 13's reading; the session-14 divergence is not reproduced")
    P("     at this time point. Three same-day sessions bind no distribution;")
    P("     the boundary is NOT narrowed by this session; NO causal mechanism")
    P("     is claimed or measured.")
elif s14_like:
    w1 = "(b)"
    P("     VERDICT: branch (b) S14-LIKE -- both anchors land with session 14")
    P("     (d256 INTERMEDIATE/MIXED inside the 55 band; d128 inside the 192")
    P("     band). The third point joins session 14's reading. Three same-day")
    P("     sessions bind no distribution; the boundary is NOT narrowed by this")
    P("     session; NO causal mechanism is claimed or measured.")
elif (d256_branch in ("(a)", "(b)") and d128_branch in ("(a)", "(b)")):
    w1 = "(c)"
    P("     VERDICT: branch (c) MIXED -- one anchor lands with session 13 and")
    P("     the other with session 14 (d256 branch " + d256_branch + ", d128 branch " + d128_branch + ").")
    P("     The session-sensitivity finding is EXTENDED: no single prior")
    P("     session's pair of readings reproduces at the third point. Three")
    P("     same-day sessions bind no distribution; the boundary is NOT")
    P("     narrowed; NO causal mechanism is claimed or measured.")
else:
    w1 = "(d)"
    P("     VERDICT: branch (d) THIRD DISTINCT -- at least one anchor outcome")
    P("     is outside {s13-like, s14-like} (d256 branch " + d256_branch + ", d128 branch " + d128_branch + ";")
    P("     quantified per anchor in the C2 table). The session-sensitivity")
    P("     finding is EXTENDED at a third distinct outcome. Three same-day")
    P("     sessions bind no distribution; the boundary is NOT narrowed; NO")
    P("     causal mechanism is claimed or measured.")
P("")

# W2 the d160 spike replication
vd160 = pooled("d160", sum128)
vd192 = pooled("d192", sum128)
P("   W2 THE d160 SPIKE REPLICATION (the session-14 anomaly d160 > both")
P("   neighbours on the descending-n ladder d128 > d160 > d192):")
lo_s14d160, hi_s14d160 = band5(S14_REF["d160"])
P(f"     this session: d128 {vd128:.0f}, d160 {vd160:.0f}, d192 {vd192:.0f} (pooled medians);")
P(f"     session-14 committed d160 = {S14_REF['d160']} (+/-5% band {lo_s14d160:.1f}..{hi_s14d160:.1f})")
if vd160 > vd128 and vd160 > vd192:
    w2 = "(a)"
    P("     VERDICT: branch (a) SPIKE REPRODUCES -- d160 sits ABOVE both")
    P("     neighbours in this session's runs. The non-monotone dose curve is")
    P("     seen at a third same-day session; no mechanism claimed.")
elif vd128 >= vd160 >= vd192:
    w2 = "(b)"
    P("     VERDICT: branch (b) NO SPIKE -- d128 >= d160 >= d192 (monotone")
    P("     descent). The session-14 spike does NOT reproduce at this time")
    P("     point; no mechanism claimed.")
else:
    w2 = "(c)"
    P("     VERDICT: branch (c) otherwise (not (a) and not (b)); the three")
    P("     brackets stand as measured content; no mechanism claimed.")
P("")

# W3 three-session spread
P("   W3 THREE-SESSION SPREAD (descriptive; comparison of committed numbers")
P("   only -- the session-13/14 columns are committed values, never this")
P("   session's measurements; d160/d192/d224 have NO session-13 committed")
P("   value -- first measured in session 14 -- named, not hidden):")
P("")
P("   arm    s15 (sum,128,16)  s15 class            s14 committed  s14 class            s13 committed  s13 class")
for tag in TAGS:
    v = pooled(tag, sum128)
    s14v = f"{S14_REF[tag]}" if tag in S14_REF else "n/a"
    s14c = S14_CLS.get(tag, "--")
    s13v = f"{S13_REF[tag]}" if tag in S13_REF else "n/a"
    s13c = S13_CLS.get(tag, "--")
    P(f"   {tag}  {v:>10.0f}       {CLASS[tag]:<20} {s14v:>8}       {s14c:<20} {s13v:>8}       {s13c}")
P("")
P("   (c2/c8 s13/s14 columns: session 13 read c2 FLOOR 31..32 / c8 32,906;")
P("   session 14 read c2 FLOOR 31 / c8 32,957 -- controls, section C1.)")
P("   NO linearity claim, no interpolation; three same-day sessions bind no")
P("   distribution and say nothing about a third UTC day (protocol L8).")
P("")

# X1 realization vs s14
P("   X1 REALIZATION (descriptive, from the same runs' host_ns, no new")
P("   measurement; vs session 14's same-knob committed host_ns -- protocol")
P("   section 3; host_ns is not a C criterion and is the HOST-side proxy")
P("   -- protocol L3):")
for tag in TAGS:
    h = pooled_host(tag, sum128)
    ref = S14_HOST[tag]
    P(f"     {tag}: host_ns {h:.0f} vs session-14 {ref} ({h/ref:.3f}x); per-dispatch host_ns {h/ARMB[tag]:.0f}")
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
    if tag in S14_REF:
        d14 = (v - S14_REF[tag]) / S14_REF[tag] * 100
        line += f"; vs session-14 {S14_REF[tag]}: {d14:+.2f}%"
    if tag in S13_REF:
        d13 = (v - S13_REF[tag]) / S13_REF[tag] * 100
        line += f"; vs session-13 {S13_REF[tag]}: {d13:+.2f}%"
    if tag not in COMMITTED and tag not in S14_REF and tag not in S13_REF:
        line += " (no committed anchor at this NDIV)"
    P(line)
P("")

P("5. RULE 4 -- NOTHING MOVES: no workgroup row, no :measured? flag, no selection")
P("   answer; accelerator-targets defaults remain provisional design assumptions")
P("   (:measured? false). This is NOT the baseline-vs-variant contract of")
P("   accelerator-subgroup-reduce.cljk. NO vendor optimization exists for Intel")
P("   and none is claimed. No causal mechanism is claimed by any letter above.")
P("")

unm = [
    "6. UNMEASURED (named): any causal mechanism (for the undercount, the",
    "   capture, the onset, any work-down transition, the descent's shape, the",
    "   d256 class flip, the d128 movement, the d160 spike, the boundary's",
    "   existence as a boundary, or the session-to-session movement itself);",
    "   WHY capture turns on where it does; whether the boundary is on n,",
    "   workgroup count or grid shape (protocol L4 -- n and workgroup count",
    "   co-vary on this instrument); the GPU-side cost inside a B<=2 bracket",
    "   (protocol L3); anything between adjacent ladder rungs (L5); any NDIV",
    "   outside {1,128,160,192,224,256}; any B outside {2,8}; any WORK_MUL > 1;",
    "   any n outside the seven L2 values; d8/d32/d64 this session (L7);",
    "   CROSS-UTC-DAY replication (L8 -- all three sessions share the UTC day);",
    "   any fourth session; session 2's run-1 dip cause; S=8 timing; every W",
    "   outside {128,256}; shape 2; BT ordering; any baseline-vs-variant sign;",
    "   isolated single-dispatch timing; non-empty barriers; anything off this",
    "   host.",
]
P("\n".join(unm))

text = "\n".join(out) + "\n"
open(os.path.join(HERE, "publication-s15.txt"), "w").write(text)
print(text)
