#!/usr/bin/env python3
"""JUN-59 session 17 analysis -- THE CONSTANT-TOTAL-WORK CROSSING
(NDIV=B ladder; total nominal work ~1.0 on the crossing rungs).

Route (frozen in protocol.txt section 6): this script parses ONLY the 27
committed run logs in its own directory (run-<tag>-r<R>.txt) and writes
publication-s17.txt. No other input. Deterministic: running it twice
yields byte-identical publication-s17.txt (checked by diff after the
recorded run).

Cross-session reference values are frozen in protocol.txt section 3 and
embedded below as named constants (committed control anchors, the
committed d8 anchor, the committed NDIV=1 B-ladder, the committed B=8
work-down ladder); they are comparison values only and never this
session's measurements.
"""
import re, sys, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

# tag -> (BATCH, NDIV), protocol.txt section 2
ARMS = [("c2", 2, 1), ("x2", 2, 2), ("x3", 3, 3), ("x4", 4, 4),
        ("x5", 5, 5), ("x6", 6, 6), ("x7", 7, 7), ("x8", 8, 8),
        ("c8", 8, 1)]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMD = {a[0]: a[2] for a in ARMS}
CROSS = ["x2", "x3", "x4", "x5", "x6", "x7", "x8"]
RUNS = [1, 2, 3]
N_BASE = 1000003

# committed control anchors (comparison of committed numbers only)
COMMITTED = {"c2": 31, "c8": 32915}
COMMITTED_SRC = {"c2": "sessions 1-16 floor band 31..32",
                 "c8": "session 4 pooled median"}
# session-16 same-knob committed values (protocol section 3)
S16_REF = {"c2": 32, "c8": 32955}
S16_HOST = {"c2": 681672, "c8": 2401681}
# x8 == d8's committed knob pair (BATCH=8, NDIV=8), protocol C2
D8_REF = 5431          # session 13 pooled median (5,465 at session 12)
D8_SRC = "session 13 pooled median (5,465 at session 12)"
D8_HOST = 987632       # session 13 host_ns
# the NDIV=1 B-ladder committed values (quote-only, protocol L7)
NDIV1 = [("b3", 3, 5520, "session 7 (5,546 s8; 5,555 s16)"),
         ("b4", 4, 11680, "session 7"),
         ("b5", 5, 17386, "session 7"),
         ("b6", 6, 22730, "session 7"),
         ("b7", 7, 28037, "session 16")]
# the B=8 work-down ladder committed values (quote-only, protocol L7)
WORKDOWN = [("d8", 8, 8, 5465, "session 12 (5,431 at session 13 -- re-run this session as x8/C2)"),
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
P("JUN-59 session 17 -- THE CONSTANT-TOTAL-WORK CROSSING (NDIV=B ladder;")
P("total nominal work ~1.0 on the crossing rungs), publication")
P("Produced ONLY by analysis-s17.py over the 27 committed run logs in this")
P("directory (run-<tag>-r<R>.txt); protocol.txt was frozen before the")
P("first run. Arms = binary compile-time (BATCH, NDIV); the crossing rungs")
P("x2..x8 have NDIV=B so every rung carries B*n/1,000,003 = 0.999996..")
P("0.999999 nominal units (the computed totals of derivation-census.txt;")
P("NAMED, NOT HIDDEN: protocol L1's stated range 0.999999..1.000002 is an")
P("arithmetic slip in the frozen text -- the computed values govern and")
P("the design claim (constant to a few parts per million) holds). c2/c8")
P("are the archived environment controls (totals 2.0 and 8.0). ZERO")
P("derivation this session: the instrument is session 16's committed")
P("NDIV-derived source byte-identical (digest a5e539f0... --")
P("derivation-census.txt); the a-set manifest runs the ARCHIVED measured")
P("spv (16-digest corpus).")
P("The row question (protocol section 0): at CONSTANT total nominal work,")
P("what is the class vector over B=2..8 -- the dispatch-count signature")
P("(rise), the total-work signature (flat) or the per-dispatch-work/grid")
P("signature (fall)? Protocol L2: per-dispatch work and grid size co-vary")
P("with B here BY CONSTRUCTION; the signatures are observational")
P("discriminators among three named hypotheses, never a mechanism.")
P("1 tick = timestampPeriod = 52.083 ns.")
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

P("1. INTEGRITY (computed over the 27 logs):")
P(f"   runs parsed: 27 (9 arms x 3 runs); cell map identical across runs: {cell_keys is not None and not any('CELL MAP' in i for i in integrity)}")
P(f"   headers byte-identical across all runs outside the # n= knob line: {header_ok}")
P(f"   header batch=/work_mul=/ndiv= == run's (B,1,NDIV) and n == 1,000,003//NDIV; every SAMPLE batch=/work_mul=/ndiv= == (B,1,NDIV): {knob_field_ok}")
P(f"   every CELL spv= name is an archived .emitted.spv (no .iter -- the corpus is byte-identical this session): {spv_identity_ok}")
P(f"   SAMPLE lines: 450 per run (18 ok cells x 25 rounds) in 27/27 runs: {sample_counts_ok}")
P(f"   VERIFY mismatch total over all runs: {verify_mismatch_total} (per-arm: "
  + ", ".join(f"{t}={verify_mismatch_by_arm[t]}" for t in TAGS)
  + ") -- bit-exact correctness re-check inside every run; frozen INVALIDATION criterion (protocol section 5): >0 in any run makes that run DEFECTIVE and the arm INVALID")
P(f"   forcing reality (pipeline-ok cell-runs where probe_size==forced and probe_nsub==wg/forced): {forcing_ok}/{forcing_total}")
P(f"   S=8 cells fail-closed (pipeline=FAIL, forced=8): {s8_fail} cell-runs (6 per run x 27 runs = 162 expected)")
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
P("   arm  B  NDIV     n        total-nominal  (sum,128,16)   run-median band    min..max over 18 cells   host_ns")
for tag in TAGS:
    b, dd = ARMB[tag], ARMD[tag]
    n = (N_BASE * 1) // dd
    vals = [pooled(tag, k) for k in ok_cells]
    v16 = pooled(tag, sum128)
    rms = run_medians(tag, sum128)
    hn = pooled_host(tag, sum128)
    tot = b * n / N_BASE
    P(f"   {tag}  {b}  {dd:<5} {n:>8}  {tot:>12.6f}  {v16:>10.0f}     {min(rms):>8.0f}..{max(rms):<8.0f}  {min(vals):>8.0f}..{max(vals):<8.0f}  {hn:>9.0f}")
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
    P(f"   class {tag} (B={b}, NDIV={dd}, n={n}, {b*n/N_BASE:.6f} nominal units): {CLASS[tag]}")
P("")

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
P("   spv bytes through the byte-identical session-16 instrument, so this")
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

# C2 the work-down anchor replication at x8 == d8's knob pair
vx8 = pooled("x8", sum128)
c2x_ok = abs(vx8 - D8_REF) <= 0.05 * D8_REF
P("   C2 WORK-DOWN ANCHOR REPLICATION (x8 is the committed d8 knob pair")
P("   BATCH=8,NDIV=8; its rebuilt binary is BYTE-IDENTICAL to session 13's")
P("   committed d8 binary -- build-census-s17.txt):")
P(f"     x8 (sum,128,16) pooled median {vx8:.0f} within +/-5% of committed d8 {D8_REF} ({D8_SRC}): {c2x_ok}")
P(f"     x8 class {CLASS['x8']} (committed d8 class CAPTURED); vs session-12 committed 5,465: {(vx8-5465)/5465*100:+.2f}%")
if c2x_ok:
    P("     VERDICT: branch (a) -- the top rung of the crossing ladder")
    P("     replicates the work-down ladder's committed top rung and the")
    P("     two ladders join at that grid point.")
else:
    P("     VERDICT: branch (b) -- replication discrepancy at the joining")
    P("     grid point; W letters interpretation is FLAGGED; cause UNMEASURED.")
P("")

# W1 the row question: class pattern over the crossing ladder
order = {"FLOOR": 0, "INTERMEDIATE/MIXED": 1, "CAPTURED": 2}
vec = [CLASS[t] for t in CROSS]
P("   W1 THE ROW QUESTION (the class pattern of the crossing ladder at")
P("   constant total nominal work ~0.999996..0.999999 -- CLASSES =")
P("   (class(x2), class(x3), class(x4), class(x5), class(x6), class(x7),")
P("   class(x8)) in rising B order; per-dispatch work and grid size")
P("   co-vary with B BY CONSTRUCTION, protocol L2):")
P(f"     CLASSES = {tuple(vec)}")
all_cap_rest = all(c == "CAPTURED" for c in vec[1:])
all_equal = len(set(vec)) == 1
nondec = all(order[vec[i]] <= order[vec[i + 1]] for i in range(len(vec) - 1))
noninc = all(order[vec[i]] >= order[vec[i + 1]] for i in range(len(vec) - 1))
strict_rise = any(order[vec[i]] < order[vec[i + 1]] for i in range(len(vec) - 1))
strict_fall = any(order[vec[i]] > order[vec[i + 1]] for i in range(len(vec) - 1))
# NAMED, NOT HIDDEN: the first recorded run of this script dispatched W1
# to branch (c) for the (a)-shape -- its (a) test used
# all(c == "CAPTURED" for c in vec) over the WHOLE vector (including x2)
# and so could never fire when x2 is FLOOR. The protocol's branch letters
# (written once, never rewritten) are the frozen reference; this is a
# mechanical dispatch bug in the analysis script, fixed before commit.
# The measured numbers are unchanged by the fix (sections 1/2/4 are
# computed identically either way).
if vec[0] == "FLOOR" and all_cap_rest and not all_equal:
    w1 = "(a)"
    P("     VERDICT: branch (a) RISE-AT-3 -- x2 FLOOR and x3..x8 all")
    P("     CAPTURED: at constant total work ~1.0 the capture still turns")
    P("     on at the discrete B=2 -> B=3 step (the dispatch-count")
    P("     signature at constant total work), and 'B=2 never captures'")
    P("     extends to n=500,001. ONE session; per-dispatch work/grid")
    P("     co-vary with B here by construction (L2); no boundary between")
    P("     rungs is claimed (L5); NO causal mechanism is claimed or")
    P("     measured.")
elif all_equal:
    w1 = "(b)"
    P("     VERDICT: branch (b) FLAT -- all seven classes equal")
    P(f"     ({vec[0]}): the class is constant along the constant-total")
    P("     ladder (the total-work signature). NAMED IN ADVANCE (protocol")
    P("     section 4): with C2 placing x8 at the committed d8 CAPTURED")
    P("     reading, a FLAT all-CAPTURED vector would include x2 (B=2,")
    P("     n=500,001) CAPTURED and so contradict the committed 'B=2 never")
    P("     captures' readings (c2 FLOOR at n=1,000,003; session 8's")
    P("     b2m3/b2m8 FLOOR) -- the contradiction stands as measured")
    P("     content and is NOT resolved here. ONE session; L2 co-variation")
    P("     applies; NO causal mechanism is claimed or measured.")
elif nondec and strict_rise:
    w1 = "(c)"
    P("     VERDICT: branch (c) RISE-GRADIENT -- the class vector is")
    P("     non-decreasing along rising B with at least one strict rise")
    P("     but is not shape (a): capture strengthens with dispatch count")
    P("     at constant total work on this session's runs (gradual). ONE")
    P("     session; no boundary between rungs is claimed (L5); NO causal")
    P("     mechanism is claimed or measured.")
elif noninc and strict_fall:
    w1 = "(d)"
    P("     VERDICT: branch (d) FALL -- the class vector is non-increasing")
    P("     along rising B with at least one strict decrease: capture")
    P("     weakens as per-dispatch work shrinks at constant total work")
    P("     (the per-dispatch-work/grid signature of L2). ONE session; no")
    P("     boundary between rungs is claimed (L5); NO causal mechanism is")
    P("     claimed or measured.")
else:
    w1 = "(e)"
    P("     VERDICT: branch (e) otherwise -- quantified per rung from the")
    P("     class table above (named in advance: x2 CAPTURED while later")
    P("     rungs are not; a non-monotone class vector; anything not")
    P("     covered above). The measured classes stand as content. ONE")
    P("     session; no boundary between rungs is claimed (L5); NO causal")
    P("     mechanism is claimed or measured.")
P("")

# W2 the constant-total dose curve
P("   W2 THE CONSTANT-TOTAL DOSE CURVE (pre-registered, descriptive; pooled")
P("   medians at (sum,128,S=16) over the crossing rungs x2..x8 at total")
P("   ~1.0; the last column is the named comparison against the COMMITTED")
P("   NDIV=1 same-B value (quote-only, protocol L7) -- no linearity claim,")
P("   no interpolation):")
P("")
P("   B   bracket  per-dispatch  committed NDIV=1 same-B  ratio")
ndiv1_ref = {"x2": ("c2", 31), "x3": ("b3", 5520), "x4": ("b4", 11680),
             "x5": ("b5", 17386), "x6": ("b6", 22730), "x7": ("b7", 28037),
             "x8": ("c8", 32915)}
dose = []
for tag in CROSS:
    b = ARMB[tag]
    v = pooled(tag, sum128)
    dose.append((b, v))
    nm, ref = ndiv1_ref[tag]
    P(f"   {b}   {v:>7.0f}   {v/b:>8.1f}     {nm} {ref:>6}                 {v/ref:.3f}")
mono = all(dose[i][1] <= dose[i + 1][1] for i in range(len(dose) - 1))
if mono:
    w2 = "(a)"
    P("     VERDICT: branch (a) the pooled medians are non-decreasing in B")
    P("     along the constant-total ladder.")
else:
    w2 = "(b)"
    dips = [f"B={dose[i+1][0]} ({dose[i][1]:.0f} -> {dose[i+1][1]:.0f})" for i in range(len(dose) - 1) if dose[i][1] > dose[i + 1][1]]
    P("     VERDICT: branch (b) non-monotone; the named rung(s): " + "; ".join(dips) + ".")
P("     Descriptive either way; the committed NDIV=1 column is quote-only")
P("     (L7) and sits at TOTAL work = B units, not ~1.0 -- the ratio column")
P("     compares across total-work levels and is a named comparison only.")
P("")

# W3 the cross table
P("   W3 THE CROSS TABLE (descriptive; protocol L7 quote-only rows marked;")
P("   NO interpolation, NO claim between grid points; L2 applies to the")
P("   measured row -- per-dispatch work/grid co-vary with B there):")
P("")
P("   row (i) COMMITTED NDIV=1 B-ladder (quote-only; totals = B units):")
P("     " + "  ".join(f"B{b}={v:.0f}" for _, b, v, _ in NDIV1) + "  (c2 31 FLOOR, c8 32,915 CAPTURED)")
P("   row (ii) THIS session, total ~1.0 (the only measured row):")
P("     " + "  ".join(f"B{b}={v:.0f}" for b, v in dose))
P("   row (iii) COMMITTED B=8 work-down ladder (quote-only except d8,")
P("   re-run as x8/C2; totals = 1 unit):")
for tag, b, dd, v, src in WORKDOWN:
    P(f"     {tag} (B={b}, NDIV={dd}, n={N_BASE//dd}): {v} ticks ({src})")
P("")

# X1 realization
P("   X1 REALIZATION (descriptive, from the same runs' host_ns, no new")
P("   measurement; vs committed same-knob host_ns where they exist -- c2/c8:")
P("   session 16, x8: session 13's d8; host_ns is not a C criterion and is")
P("   the HOST-side proxy -- protocol L3):")
for tag in TAGS:
    h = pooled_host(tag, sum128)
    line = f"     {tag}: host_ns {h:.0f}"
    if tag in S16_HOST:
        line += f" vs session-16 {S16_HOST[tag]} ({h/S16_HOST[tag]:.3f}x)"
    elif tag == "x8":
        line += f" vs session-13 d8 {D8_HOST} ({h/D8_HOST:.3f}x)"
    else:
        line += " (no prior committed value at this (B,NDIV) -- first measured here)"
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
            f" host_ns {hn:.0f}; {b*n/N_BASE:.6f} nominal units (n={n})")
    if tag in COMMITTED:
        d = (v - COMMITTED[tag]) / COMMITTED[tag] * 100
        line += f"; vs committed {COMMITTED[tag]} ({COMMITTED_SRC[tag]}): {d:+.2f}%"
    if tag in S16_REF:
        d16 = (v - S16_REF[tag]) / S16_REF[tag] * 100
        line += f"; vs session-16 {S16_REF[tag]}: {d16:+.2f}%"
    if tag == "x8":
        d8d = (v - D8_REF) / D8_REF * 100
        line += f"; vs committed d8 {D8_REF} ({D8_SRC}): {d8d:+.2f}%"
    if tag in ("x2", "x3", "x4", "x5", "x6", "x7"):
        line += " (first measurement of this (B,NDIV) pair anywhere in the series)"
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
    "   capture, the onset, any B-axis transition, any total-work transition,",
    "   the dose curve's shape, the session-to-session movement, or the d160",
    "   spike); WHY capture turns on where it does; whether the operative axis",
    "   is dispatch count, total work, per-dispatch work, grid size, or",
    "   bracketed submission shape (protocol L2 -- the three signatures",
    "   discriminate among the three NAMED hypotheses only); the GPU-side cost",
    "   inside a B<=2 bracket (protocol L3); anything between adjacent ladder",
    "   rungs (L5); any B outside {2,3,4,5,6,7,8}; any (B,NDIV) pair with",
    "   NDIV != B other than the c2/c8 controls (L10); any total work outside",
    "   the crossing rungs' 0.999996..0.999999; any WORK_MUL value; any n",
    "   outside the nine arm values this session; the NDIV=1 B-ladder and the",
    "   d32..d256 rungs this session (L7); CROSS-UTC-DAY replication (L4); any",
    "   cross-session stability of the x2..x7 readings (first measured here;",
    "   x8 replicates the committed d8 values, section 3 C2); session 2's",
    "   run-1 dip cause; S=8 timing; every W outside {128,256}; shape 2; BT",
    "   ordering; any baseline-vs-variant sign; isolated single-dispatch",
    "   timing; non-empty barriers; anything off this host.",
]
P("\n".join(unm))

text = "\n".join(out) + "\n"
open(os.path.join(HERE, "publication-s17.txt"), "w").write(text)
print(text)
