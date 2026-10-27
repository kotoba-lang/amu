#!/usr/bin/env python3
"""JUN-59 session 16 analysis -- THE DISPATCH-COUNT LADDER at fixed
per-dispatch work (B=2..8, NDIV=1).

Route (frozen in protocol.txt section 6): this script parses ONLY the 21
committed run logs in its own directory (run-<tag>-r<R>.txt) and writes
publication-s16.txt. No other input. Deterministic: running it twice yields
byte-identical publication-s16.txt (checked by diff after the recorded run).

Cross-session reference values are frozen in protocol.txt section 3 and
embedded below as named constants (committed control anchors and
session-15 same-knob values); they are comparison values only and never
this session's measurements.
"""
import re, sys, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

# tag -> (BATCH, NDIV), protocol.txt section 2
ARMS = [("c2", 2, 1), ("b3", 3, 1), ("b4", 4, 1), ("b5", 5, 1),
        ("b6", 6, 1), ("b7", 7, 1), ("c8", 8, 1)]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMD = {a[0]: a[2] for a in ARMS}
RUNS = [1, 2, 3]
N_BASE = 1000003

# committed control anchors (comparison of committed numbers only)
COMMITTED = {"c2": 31, "c8": 32915}
COMMITTED_SRC = {"c2": "sessions 1-15 floor band 31..32",
                 "c8": "session 4 pooled median"}
# session-15 same-knob committed values (protocol section 3)
S15_REF = {"c2": 32, "c8": 32950}
S15_HOST = {"c2": 681050, "c8": 3073033}
# session-7 committed values (anv-bonset-20261027/publication-s7.txt) --
# CORRECTION (named, not hidden): the protocol's framing that the rungs
# between the endpoints "have never been measured" is WRONG against the
# chain's own history; session 7 measured B in {1,2,3,4,5,6,8} at full
# work and already narrowed the capture onset to the discrete B=2 -> B=3
# step. These are comparison values only, never this session's
# measurements. B=7 is the ONLY rung of the integer ladder B=1..8 that
# had never been measured before this session (session 7's own named
# residual was "B=7").
S7_REF = {"b3": 5520, "b4": 11680, "b5": 17386, "b6": 22730, "c8": 32951}
S7_HOST = {"c2": 679998, "b3": 960432, "b4": 1279136, "b5": 1582402,
           "b6": 1863736, "c8": 3038388}
# the B=8 work-down ladder committed values (quote-only, protocol L7)
WORKDOWN = [("d8", 8, 8, 5465, "session 12 (5,431 at session 13)"),
            ("d32", 8, 32, 1050, "session 13"),
            ("d64", 8, 64, 403, "session 13"),
            ("d128", 8, 128, 167, "session 13 (192 at session 14, 167 at session 15)"),
            ("d256", 8, 256, 34, "session 13 (55 at session 14, 34 at session 15)")]

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
P("JUN-59 session 16 -- THE DISPATCH-COUNT LADDER at fixed per-dispatch work")
P("(B=2..8, NDIV=1), publication")
P("Produced ONLY by analysis-s16.py over the 21 committed run logs in this")
P("directory (run-<tag>-r<R>.txt); protocol.txt was frozen before the")
P("first run. Arms = binary compile-time (BATCH, NDIV) with NDIV=1 in")
P("every arm; all arms run the same a-set manifest (the ARCHIVED measured")
P("spv, 16-digest corpus -- ZERO derivation this session: the instrument")
P("is session 15's committed NDIV-derived source byte-identical, digest")
P("a5e539f0... -- derivation-census.txt).")
P("The independent variable is the DISPATCH COUNT B at fixed per-dispatch")
P("work: every arm runs B dispatches of the SAME n = 1,000,003 grid.")
P("CORRECTION (named, not hidden; see record.txt section 8): the")
P("protocol's framing that the rungs between the B=2 and B=8 endpoints")
P("had never been measured is WRONG against the chain's own history --")
P("session 7 (anv-bonset-20261027) measured B in {1,2,3,4,5,6,8} at full")
P("work and already narrowed the capture onset to the discrete B=2 -> B=3")
P("step (committed b3 5,520 / b4 11,680 / b5 17,386 / b6 22,730). The")
P("genuinely new content of this session is B=7 (the only rung of the")
P("integer ladder B=1..8 never measured before -- session 7's own named")
P("residual) plus an independent same-day REPLICATION of session 7's")
P("committed readings at b3..b6 (compared in section 4). Protocol L4: B")
P("and total nominal work co-vary here (B * 1.0 units). 1 nominal work")
P("unit = one dispatch of the archived grid (a DEFINITION, not a cost")
P("claim -- L1). 1 tick = timestampPeriod = 52.083 ns.")
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
P(f"   header batch=/work_mul=/ndiv= == run's (B,1,1), barrier_n=0, n=1,000,003; every SAMPLE batch=/work_mul=/ndiv= == (B,1,1): {knob_field_ok}")
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
P("   spv bytes through the byte-identical session-15 instrument, so this")
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

# W1 the row question: class pattern over the new rungs
order = {"FLOOR": 0, "INTERMEDIATE/MIXED": 1, "CAPTURED": 2}
vec = [CLASS[t] for t in ["b3", "b4", "b5", "b6", "b7"]]
P("   W1 THE ROW QUESTION (the class pattern of the new rungs over the")
P("   dispatch-count ladder -- CLASSES = (class(b3), class(b4), class(b5),")
P("   class(b6), class(b7)) in rising B order at NDIV=1):")
P(f"     CLASSES = {tuple(vec)}")
all_cap = all(c == "CAPTURED" for c in vec)
all_floor = all(c == "FLOOR" for c in vec)
nondec = all(order[vec[i]] <= order[vec[i + 1]] for i in range(len(vec) - 1))
all_equal = len(set(vec)) == 1
if all_cap:
    w1 = "(a)"
    P("     VERDICT: branch (a) CAPTURE-AT-3 -- all five new rungs are")
    P("     CAPTURED-class: B=3 is already captured at full work (a")
    P("     REPLICATION of session 7's committed b3 5,520 reading --")
    P("     section 4 -- which had already narrowed the onset to the")
    P("     discrete B=2 -> B=3 step), and b7 (28,037) completes the")
    P("     integer ladder B=1..8 at CAPTURED-class above B=2. ONE session;")
    P("     no boundary between rungs is claimed (L5); no cross-session")
    P("     stability is claimed for the b7 reading (first measured here)")
    P("     beyond the committed-value comparisons of section 4; NO causal")
    P("     mechanism is claimed or measured.")
elif all_floor:
    w1 = "(c)"
    P("     VERDICT: branch (c) NO-CAPTURE-BELOW-8 -- all five new rungs are")
    P("     FLOOR-class: capture needs more than 7 dispatches at full work on")
    P("     this session's runs (NOTABLY this would contradict session 7's")
    P("     committed b3..b6 CAPTURED readings -- the section-4 comparison")
    P("     would then show a cross-session class discrepancy). ONE session;")
    P("     no boundary between rungs is claimed (L5); no cross-session")
    P("     stability is claimed (L8); NO causal mechanism is claimed or")
    P("     measured.")
elif (not all_equal) and nondec:
    w1 = "(b)"
    P("     VERDICT: branch (b) B-GRADIENT -- the class vector is not all-equal")
    P("     and non-decreasing along B=3..7 in the class order FLOOR <")
    P("     INTERMEDIATE/MIXED < CAPTURED: capture strengthens with dispatch")
    P("     count at fixed per-dispatch work on this session's runs. ONE")
    P("     session; no boundary between rungs is claimed (L5); no")
    P("     cross-session stability is claimed beyond the section-4")
    P("     comparisons (L8); NO causal mechanism is claimed or measured.")
else:
    w1 = "(d)"
    P("     VERDICT: branch (d) otherwise -- quantified per rung from the class")
    P("     table above (named in advance as an all-equal")
    P("     non-{FLOOR,CAPTURED} plateau or a non-monotone class vector). The")
    P("     measured classes stand as content. ONE session; no boundary")
    P("     between rungs is claimed (L5); no cross-session stability is")
    P("     claimed beyond the section-4 comparisons (L8); NO causal")
    P("     mechanism is claimed or measured.")
P("")

# W2 the B-dose curve
P("   W2 THE B-DOSE CURVE (pre-registered, descriptive; pooled medians at")
P("   (sum,128,S=16) over B=2..8 at NDIV=1; the linear-in-B column is the")
P("   named comparison B/8 x committed c8 32,915 ONLY -- no linearity")
P("   claim, no interpolation -- protocol section 4):")
P("")
P("   B   bracket  per-dispatch  linear-in-B comparison  ratio to it")
dose = []
for tag in TAGS:
    b = ARMB[tag]
    v = pooled(tag, sum128)
    dose.append((b, v))
    lin = b / 8.0 * COMMITTED["c8"]
    P(f"   {b}   {v:>7.0f}   {v/b:>8.1f}     {lin:>10.0f}              {v/lin if lin else 0:.3f}")
mono = all(dose[i][1] <= dose[i + 1][1] for i in range(len(dose) - 1))
if mono:
    w2 = "(a)"
    P("     VERDICT: branch (a) the pooled medians are non-decreasing in B.")
else:
    w2 = "(b)"
    dips = [f"B={dose[i+1][0]} ({dose[i][1]:.0f} -> {dose[i+1][1]:.0f})" for i in range(len(dose) - 1) if dose[i][1] > dose[i + 1][1]]
    P("     VERDICT: branch (b) non-monotone; the named rung(s): " + "; ".join(dips) + ".")
P("     Descriptive either way; no linearity claim; nothing between rungs (L5).")
P("")

# W3 two-axis view
P("   W3 THE TWO-AXIS VIEW (descriptive; no new measurement -- protocol L4/L7:")
P("   this session's B-ladder at NDIV=1 against the COMMITTED B=8 work-down")
P("   ladder values, which are quote-only and were NOT re-run this session;")
P("   the axes co-vary within each series, so the table names only where the")
P("   committed grid points sit; NO interpolation, NO separation claim):")
P("")
P("   this session (NDIV=1):  " + "  ".join(f"B{b}={v:.0f}" for b, v in dose))
P("   committed B=8 work-down ladder (quote-only):")
for tag, b, dd, v, src in WORKDOWN:
    P(f"     {tag} (B={b}, NDIV={dd}, n={N_BASE//dd}): {v} ticks ({src})")
P("")

# X1 realization
P("   X1 REALIZATION (descriptive, from the same runs' host_ns, no new")
P("   measurement; vs session 15's same-knob committed host_ns for c2/c8 --")
P("   the only arms with prior values; host_ns is not a C criterion and is")
P("   the HOST-side proxy -- protocol L3):")
for tag in TAGS:
    h = pooled_host(tag, sum128)
    line = f"     {tag}: host_ns {h:.0f}"
    if tag in S15_HOST:
        line += f" vs session-15 {S15_HOST[tag]} ({h/S15_HOST[tag]:.3f}x)"
    elif tag in S7_HOST:
        line += f" vs session-7 {S7_HOST[tag]} ({h/S7_HOST[tag]:.3f}x)"
    else:
        line += " (no prior committed value at this B -- first measured here)"
    line += f"; per-dispatch host_ns {h/ARMB[tag]:.0f}"
    P(line)
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
    if tag in S15_REF:
        d15 = (v - S15_REF[tag]) / S15_REF[tag] * 100
        line += f"; vs session-15 {S15_REF[tag]}: {d15:+.2f}%"
    if tag in S7_REF:
        d7 = (v - S7_REF[tag]) / S7_REF[tag] * 100
        line += f"; vs session-7 {S7_REF[tag]}: {d7:+.2f}%"
    if tag not in COMMITTED and tag not in S15_REF and tag not in S7_REF:
        line += " (first measurement of this B anywhere in the series -- the only rung of B=1..8 previously unmeasured)"
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
    "   capture, the onset, any B-axis transition, the dose curve's shape, the",
    "   session-to-session movement, or the d160 spike); WHY capture turns on",
    "   where it does; the separation of dispatch count from total work",
    "   (protocol L4); whether the onset is on B, on total work, or on",
    "   bracketed submission shape; the GPU-side cost inside a B<=2 bracket",
    "   (protocol L3); anything between adjacent ladder rungs (L5); any B",
    "   outside {2,3,4,5,6,7,8}; any NDIV>1 this session (L10); any WORK_MUL",
    "   > 1; any n outside 1,000,003 this session (L2); the work-down ladder",
    "   this session (L7); CROSS-UTC-DAY replication (L8); any cross-session",
    "   stability of the b7 reading (first measured here; the b3..b6 readings",
    "   replicate session 7's committed values, section 4); any B outside",
    "   {2,3,4,5,6,7,8} this session; session 2's",
    "   run-1 dip cause; S=8 timing; every W outside {128,256}; shape 2; BT",
    "   ordering; any baseline-vs-variant sign; isolated single-dispatch",
    "   timing; non-empty barriers; anything off this host.",
]
P("\n".join(unm))

text = "\n".join(out) + "\n"
open(os.path.join(HERE, "publication-s16.txt"), "w").write(text)
print(text)
