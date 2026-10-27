#!/usr/bin/env python3
"""JUN-59 session 20 analysis -- THE NDIV=2 DISPATCH LADDER (fixed
per-dispatch work at 1/2 grid).

Route (frozen in protocol.txt section 6): this script parses ONLY the 27
committed run logs in its own directory (run-<tag>-r<R>.txt) and writes
publication-s20.txt. No other input. Deterministic: running it twice
yields byte-identical publication-s20.txt (checked by diff after the
recorded run).

Cross-session reference values are frozen in protocol.txt section 3/4 and
embedded below as named constants (committed control anchors, the
committed x2 anchor, the committed NDIV=1 B-ladder, the committed
session-17 NDIV=B crossing, the committed session-18 NDIV=8 ladder, the
committed session-19 NDIV=4 ladder, the committed B=8 work-down ladder);
they are comparison values only and never this session's measurements.
"""
import re, sys, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

# tag -> (BATCH, NDIV), protocol.txt section 2 arm table (9 rows = 27 logs)
ARMS = [("c2", 2, 1), ("w2", 2, 2), ("w3", 3, 2), ("w4", 4, 2), ("w5", 5, 2),
        ("w6", 6, 2), ("w7", 7, 2), ("w8", 8, 2), ("c8", 8, 1)]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMD = {a[0]: a[2] for a in ARMS}
LADDER = ["w2", "w3", "w4", "w5", "w6", "w7", "w8"]   # W1 letter vector (w2 = C2 anchor, foot rung)
DOSE = ["w2", "w3", "w4", "w5", "w6", "w7", "w8"]      # W2 dose ladder
RUNS = [1, 2, 3]
N_BASE = 1000003

# committed control anchors (comparison of committed values only)
COMMITTED = {"c2": 31, "c8": 32915}
COMMITTED_SRC = {"c2": "sessions 1-19 floor band 31..32",
                 "c8": "session 4 pooled median"}
# session-17/18/19 same-knob committed values (protocol section 3)
S17_REF = {"c2": 32, "c8": 32868}
S17_HOST = {"c2": 679458, "c8": 2395127}
S18_REF = {"c2": 32, "c8": 32830}
S18_HOST = {"c2": 680159, "c8": 2385078}
S19_REF = {"c2": 31, "c8": 32830}
S19_HOST = {"c2": 676171, "c8": 2399435}
# w2 == x2's committed knob pair (BATCH=2, NDIV=2), protocol C2
X2_REF = 32           # session 17 pooled median (run-median band 31..32)
X2_SRC = "session 17 pooled median (the NDIV=B crossing rung x2)"
X2_CLASS = "FLOOR"
X2_HOST = 394546      # session 17 host_ns
# the committed NDIV=1 B-ladder (quote-only, protocol L7)
NDIV1 = [("c2", 2, 31, "committed control"), ("b3", 3, 5520, "session 7 (5,546 s8; 5,555 s16)"),
         ("b4", 4, 11680, "session 7"), ("b5", 5, 17386, "session 7"), ("b6", 6, 22730, "session 7"),
         ("b7", 7, 28037, "session 16"), ("c8", 8, 32915, "session 4")]
# the committed session-17 NDIV=B crossing (quote-only, protocol L7)
NDIVB = [("x2", 2, 32, "session 17"), ("x3", 3, 1578, "session 17"),
         ("x4", 4, 3108, "session 17"), ("x5", 5, 4012, "session 17"),
         ("x6", 6, 4738, "session 17"), ("x7", 7, 5191, "session 17"),
         ("x8", 8, 5458, "session 17 (== committed d8 knob pair)")]
# the committed session-18 NDIV=8 ladder (quote-only, protocol L7)
NDIV8 = [("y2", 2, 31, "session 18"), ("y3", 3, 599, "session 18"),
         ("y4", 4, 1497, "session 18"), ("y5", 5, 2496, "session 18"),
         ("y6", 6, 3476, "session 18"), ("y7", 7, 4463, "session 18"),
         ("y8", 8, 5419, "session 18 (== committed d8 knob pair)")]
# the committed session-19 NDIV=4 ladder (quote-only, protocol L7)
NDIV4 = [("z2", 2, 31, "session 19"), ("z3", 3, 1140, "session 19"),
         ("z4", 4, 3112, "session 19"), ("z5", 5, 5021, "session 19"),
         ("z6", 6, 7065, "session 19"), ("z7", 7, 9008, "session 19"),
         ("z8", 8, 10988, "session 19")]
# the committed B=8 work-down ladder (quote-only, protocol L7)
WORKDOWN = [("d32", 8, 32, 31250, 1050, "session 13"),
            ("d64", 8, 64, 15625, 403, "session 13"),
            ("d128", 8, 128, 7812, 167, "session 13 (192 s14; 167 s15)"),
            ("d256", 8, 256, 3906, 34, "session 13 (55 s14; 34 s15)")]

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
P("JUN-59 session 20 -- THE NDIV=2 DISPATCH LADDER (fixed per-dispatch")
P("work n=500,001 = 1/2 grid), publication")
P("Produced ONLY by analysis-s20.py over the 27 committed run logs in this")
P("directory (run-<tag>-r<R>.txt); protocol.txt was frozen before the")
P("first run. Arms = binary compile-time (BATCH, NDIV); the ladder rungs")
P("w2..w8 carry NDIV=2 so every rung has the same per-dispatch work")
P("n = 1,000,003//2 = 500,001 (0.4999995 units) and total nominal work")
P("B*500,001/1,000,003 = 0.9999990..3.9999960 (computed in")
P("derivation-census-s20.txt). c2/c8 are the archived environment")
P("controls (totals 2.0 and 8.0). ZERO derivation this session: the")
P("instrument is session 19's committed NDIV-derived source byte-identical")
P("(digest a5e539f0... -- derivation-census-s20.txt); the a-set manifest")
P("runs the ARCHIVED measured spv (16-digest corpus).")
P("The row question (protocol section 0): at FIXED per-dispatch work (1/2")
P("grid), where does the capture turn on as B rises 2 -> 8 -- at the")
P("discrete B=2 -> B=3 step (the later-onset of sessions 18/19 is specific")
P("to per-dispatch work <= 1/4 and the B=3 capture threshold in")
P("per-dispatch work sits in (1/4, 1/3]), or later (the later-onset shape")
P("extends to 1/2 -- which would make the B=3 class-vs-per-dispatch-work")
P("picture NON-MONOTONE across the measured grid points, since B=3 is")
P("CAPTURED at 1/3 and 1.0)? Protocol L2: dispatch count and TOTAL work")
P("co-vary with B here BY CONSTRUCTION (total = B*0.5); the signatures are")
P("observational discriminators among named hypotheses, never a mechanism.")
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
P("   spv bytes through the byte-identical session-19 instrument, so this")
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

# C2 the crossing anchor replication at w2 == x2's knob pair
vw2 = pooled("w2", sum128)
c2w_ok = abs(vw2 - X2_REF) <= 0.05 * X2_REF and CLASS["w2"] == X2_CLASS
P("   C2 CROSSING ANCHOR REPLICATION (w2 is the committed x2 knob pair")
P("   BATCH=2,NDIV=2; its rebuilt binary is BYTE-IDENTICAL to session 17's")
P("   anv-xt-x2 (0fe9f403...) -- build-census-s20.txt):")
P(f"     w2 (sum,128,16) pooled median {vw2:.0f} within +/-5% of committed x2 {X2_REF} ({X2_SRC}): {abs(vw2 - X2_REF) <= 0.05 * X2_REF}")
P(f"     w2 class {CLASS['w2']} (committed x2 class {X2_CLASS})")
if c2w_ok:
    P("     VERDICT: branch (a) -- the foot rung replicates the NDIV=B")
    P("     crossing's same grid point and the NDIV=2 column joins the NDIV=B")
    P("     ladder there.")
else:
    P("     VERDICT: branch (b) -- replication discrepancy at the joining grid")
    P("     point; W letters interpretation is FLAGGED; cause UNMEASURED.")
P("")

# W1 the row question: class pattern over the ladder at fixed per-dispatch work
order = {"FLOOR": 0, "INTERMEDIATE/MIXED": 1, "CAPTURED": 2}
vec = [CLASS[t] for t in LADDER]
P("   W1 THE ROW QUESTION (the class pattern of the ladder at fixed")
P("   per-dispatch work n=500,001 (0.5 units) -- CLASSES =")
P("   (class(w2), class(w3), class(w4), class(w5), class(w6), class(w7),")
P("   class(w8)) in rising B order; w2 is the C2 anchor (committed x2);")
P("   dispatch count and TOTAL work co-vary with B BY CONSTRUCTION,")
P("   protocol L2):")
P(f"     CLASSES = {tuple(vec)}")
all_cap_rest = all(c == "CAPTURED" for c in vec[1:])
all_equal = len(set(vec)) == 1
nondec = all(order[vec[i]] <= order[vec[i + 1]] for i in range(len(vec) - 1))
noninc = all(order[vec[i]] >= order[vec[i + 1]] for i in range(len(vec) - 1))
strict_rise = any(order[vec[i]] < order[vec[i + 1]] for i in range(len(vec) - 1))
strict_fall = any(order[vec[i]] > order[vec[i + 1]] for i in range(len(vec) - 1))
if vec[0] == "FLOOR" and all_cap_rest and not all_equal:
    w1 = "(a)"
    P("     VERDICT: branch (a) ONSET-AT-3 -- w2 FLOOR and w3..w8 all")
    P("     CAPTURED: at per-dispatch work 1/2 the capture-class transition")
    P("     sits at the SAME discrete B=2 -> B=3 step as at NDIV=1 (session")
    P("     7/16) and NDIV=B (session 17), so the later-onset shape of")
    P("     sessions 18/19 is specific to per-dispatch work <= 1/4 among the")
    P("     measured grid points and the B=3 capture threshold in")
    P("     per-dispatch work sits in (1/4, 1/3] with 1/2 above it (the five")
    P("     measured B=3 grid points -- 1.0 and 1/3 CAPTURED, 1/2 as measured")
    P("     here, 1/4 and 1/8 INTERMEDIATE/MIXED -- stand; nothing between")
    P("     them is interpolated, L5); 'B=2 never captures' extends to")
    P("     n=500,001 at total work 1.0. ONE session; dispatch count and")
    P("     total work co-vary here by construction (L2); NO causal")
    P("     mechanism is claimed or measured.")
elif all_equal:
    w1 = "(b)"
    P("     VERDICT: branch (b) FLAT -- all seven classes equal")
    P(f"     ({vec[0]}): the class is constant along the fixed-per-dispatch-work")
    P("     ladder. NAMED IN ADVANCE (protocol section 4): with C2 placing w2")
    P("     at the committed x2 FLOOR reading and the committed 'B=2 never")
    P("     captures' readings (c2 FLOOR; session 8's b2m3/b2m8 FLOOR; session")
    P("     17's x2 FLOOR; session 18's y2 FLOOR; session 19's z2 FLOOR), a")
    P("     FLAT all-CAPTURED vector would include w2 (B=2) CAPTURED and so")
    P("     contradict the committed picture -- the contradiction stands as")
    P("     measured content and is NOT resolved here. ONE session; L2")
    P("     co-variation applies; NO causal mechanism is claimed or measured.")
elif nondec and strict_rise:
    w1 = "(c)"
    P("     VERDICT: branch (c) RISE-GRADIENT / LATER-ONSET -- the class")
    P("     vector is non-decreasing along rising B with at least one strict")
    P("     rise but is not shape (a): at 1/2 per-dispatch work the capture")
    P("     strengthens with dispatch count but does not reach CAPTURED at")
    P("     B=3 (the onset sits later than the discrete 2 -> 3 step, or is")
    P("     gradual). NAMED IN ADVANCE: this shape at 1/2 makes the B=3")
    P("     class-vs-per-dispatch-work picture NON-MONOTONE across the")
    P("     measured grid points (B=3 is CAPTURED at 1/3, session 17, and at")
    P("     1.0, sessions 7/16) -- the session-19 reading ('the B=3 capture")
    P("     threshold in per-dispatch work sits in (1/4, 1/3]') does NOT")
    P("     extend and the contradiction stands as measured content, not")
    P("     resolved here (L5: nothing between grid points is interpolated).")
    P("     ONE session; NO causal mechanism is claimed or measured.")
elif noninc and strict_fall:
    w1 = "(d)"
    P("     VERDICT: branch (d) FALL -- the class vector is non-increasing")
    P("     along rising B with at least one strict decrease: capture")
    P("     weakens as the dispatch count rises at fixed per-dispatch work.")
    P("     ONE session; no boundary between rungs is claimed (L5); NO causal")
    P("     mechanism is claimed or measured.")
else:
    w1 = "(e)"
    P("     VERDICT: branch (e) otherwise -- quantified per rung from the")
    P("     class table above (named in advance: w2 CAPTURED while later")
    P("     rungs are not; a non-monotone class vector; anything not covered")
    P("     above). The measured classes stand as content. ONE session; no")
    P("     boundary between rungs is claimed (L5); NO causal mechanism is")
    P("     claimed or measured.")
P("")

# W2 the NDIV=2 dose curve
P("   W2 THE NDIV=2 DOSE CURVE (pre-registered, descriptive; pooled")
P("   medians at (sum,128,S=16) over w2..w8; the last four columns are the")
P("   named comparisons against the COMMITTED NDIV=1 same-B value, the")
P("   COMMITTED session-17 NDIV=B same-B value, the COMMITTED session-19")
P("   NDIV=4 same-B value and the COMMITTED session-18 NDIV=8 same-B value")
P("   (quote-only, protocol L7 -- all sit at DIFFERENT total-work levels:")
P("   B units, ~1.0, B/4, B/8 vs B/2 units here) -- no linearity claim, no")
P("   interpolation):")
P("")
P("   B   bracket  per-dispatch  total     NDIV=1 ref (ratio)   NDIV=B ref (ratio)   NDIV=4 ref (ratio)   NDIV=8 ref (ratio)")
ndiv1_ref = {"w2": 31, "w3": 5520, "w4": 11680, "w5": 17386, "w6": 22730, "w7": 28037, "w8": 32915}
ndiv1_name = {"w2": "c2", "w3": "b3", "w4": "b4", "w5": "b5", "w6": "b6", "w7": "b7", "w8": "c8"}
ndivb_ref = {"w2": 32, "w3": 1578, "w4": 3108, "w5": 4012, "w6": 4738, "w7": 5191, "w8": 5458}
ndivb_name = {"w2": "x2", "w3": "x3", "w4": "x4", "w5": "x5", "w6": "x6", "w7": "x7", "w8": "x8"}
ndiv4_ref = {"w2": 31, "w3": 1140, "w4": 3112, "w5": 5021, "w6": 7065, "w7": 9008, "w8": 10988}
ndiv4_name = {"w2": "z2", "w3": "z3", "w4": "z4", "w5": "z5", "w6": "z6", "w7": "z7", "w8": "z8"}
ndiv8_ref = {"w2": 31, "w3": 599, "w4": 1497, "w5": 2496, "w6": 3476, "w7": 4463, "w8": 5419}
ndiv8_name = {"w2": "y2", "w3": "y3", "w4": "y4", "w5": "y5", "w6": "y6", "w7": "y7", "w8": "y8"}
dose = []
for tag in DOSE:
    b = ARMB[tag]
    v = pooled(tag, sum128)
    tot = b * 500001 / N_BASE
    dose.append((b, v))
    r1, rb, r4, r8 = ndiv1_ref[tag], ndivb_ref[tag], ndiv4_ref[tag], ndiv8_ref[tag]
    P(f"   {b}   {v:>7.0f}   {v/b:>8.1f}  {tot:.4f}  {ndiv1_name[tag]} {r1:>6} ({v/r1:.3f})   {ndivb_name[tag]} {rb:>6} ({v/rb:.3f})   {ndiv4_name[tag]} {r4:>6} ({v/r4:.3f})   {ndiv8_name[tag]} {r8:>6} ({v/r8:.3f})")
mono = all(dose[i][1] <= dose[i + 1][1] for i in range(len(dose) - 1))
if mono:
    w2 = "(a)"
    P("     VERDICT: branch (a) the pooled medians are non-decreasing in B")
    P("     along the fixed-per-dispatch-work ladder.")
else:
    w2 = "(b)"
    dips = [f"B={dose[i+1][0]} ({dose[i][1]:.0f} -> {dose[i+1][1]:.0f})" for i in range(len(dose) - 1) if dose[i][1] > dose[i + 1][1]]
    P("     VERDICT: branch (b) non-monotone; the named rung(s): " + "; ".join(dips) + ".")
P("     Descriptive either way; the four comparison columns are quote-only")
P("     (L7) and sit at different total-work levels -- the ratio columns")
P("     compare across total-work levels and are named comparisons only.")
P("")

# W3 the cross table
P("   W3 THE CROSS TABLE (descriptive; protocol L7 quote-only rows marked;")
P("   NO interpolation, NO claim between grid points; L2 applies to row")
P("   (v) -- dispatch count and total work co-vary with B there):")
P("")
P("   row (i) COMMITTED NDIV=1 B-ladder (quote-only; totals = B units):")
P("     " + "  ".join(f"B{b}={v:.0f}" for _, b, v, _ in NDIV1))
P("   row (ii) COMMITTED NDIV=B constant-total, session 17 (quote-only;")
P("     totals ~1.0):")
P("     " + "  ".join(f"B{b}={v:.0f}" for _, b, v, _ in NDIVB))
P("   row (iii) COMMITTED NDIV=8, session 18 (quote-only; totals = B/8")
P("     units):")
P("     " + "  ".join(f"B{b}={v:.0f}" for _, b, v, _ in NDIV8))
P("   row (iv) COMMITTED NDIV=4, session 19 (quote-only; totals = B/4")
P("     units):")
P("     " + "  ".join(f"B{b}={v:.0f}" for _, b, v, _ in NDIV4))
P("   row (v) THIS session, NDIV=2 at fixed per-dispatch work (the ONLY")
P("     measured row; totals = B/2 units):")
P("     " + "  ".join(f"B{b}={v:.0f}" for b, v in dose))
P("   equal-total shape comparisons (quote-only vs measured, NO mechanism):")
p_w2 = pooled("w2", sum128)
p_w4 = pooled("w4", sum128)
P(f"     total 1.0 units: w2 (2 dispatches x 500,001) = {p_w2:.0f} ticks measured")
P("       -- itself the committed x2 grid point (C2 anchor) --")
P("       vs z4 (4 x 250,000, session 19) = 3,112 ticks CAPTURED (quote-only)")
P("       vs y8 (8 x 125,000, session 18) = 5,419 ticks CAPTURED (quote-only)")
P(f"     total 2.0 units: w4 (4 dispatches x 500,001) = {p_w4:.0f} ticks measured")
P("       vs z8 (8 x 250,000, session 19) = 10,988 ticks CAPTURED (quote-only)")
P("       vs c2 (2 x 1,000,003, committed control) = 31 ticks FLOOR (quote-only)")
P("")

# X1 realization
P("   X1 REALIZATION (descriptive, from the same runs' host_ns, no new")
P("   measurement; vs committed same-knob host_ns where they exist -- c2/c8:")
P("   sessions 17, 18 and 19; w2: session 17's x2; host_ns is not a C")
P("   criterion and is the HOST-side proxy -- protocol L3):")
for tag in TAGS:
    h = pooled_host(tag, sum128)
    line = f"     {tag}: host_ns {h:.0f}"
    if tag in S17_HOST:
        line += f" vs session-17 {S17_HOST[tag]} ({h/S17_HOST[tag]:.3f}x); vs session-18 {S18_HOST[tag]} ({h/S18_HOST[tag]:.3f}x); vs session-19 {S19_HOST[tag]} ({h/S19_HOST[tag]:.3f}x)"
    elif tag == "w2":
        line += f" vs session-17 x2 {X2_HOST} ({h/X2_HOST:.3f}x)"
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
    if tag in S17_REF:
        d17 = (v - S17_REF[tag]) / S17_REF[tag] * 100
        d18 = (v - S18_REF[tag]) / S18_REF[tag] * 100
        d19 = (v - S19_REF[tag]) / S19_REF[tag] * 100
        line += f"; vs session-17 {S17_REF[tag]}: {d17:+.2f}%; vs session-18 {S18_REF[tag]}: {d18:+.2f}%; vs session-19 {S19_REF[tag]}: {d19:+.2f}%"
    if tag == "w2":
        x2d = (v - X2_REF) / X2_REF * 100
        line += f"; vs committed x2 {X2_REF} ({X2_SRC}): {x2d:+.2f}%"
    if tag in ("w3", "w4", "w5", "w6", "w7", "w8"):
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
    "   capture, the onset, any B-axis transition at 1/2 per-dispatch work,",
    "   the dose curve's shape, the session-to-session movement, or the d160",
    "   spike); WHY capture turns on where it does; the B=3 capture threshold",
    "   in per-dispatch work BETWEEN the measured grid points 1/8 and 1.0 (and",
    "   between 1/2 and every other measured point -- L5, no interpolation);",
    "   whether the operative axis is dispatch count, total work, per-dispatch",
    "   work, grid size, or bracketed submission shape (protocol L2 -- dispatch",
    "   count and total work co-vary here by construction; the signatures",
    "   discriminate among the NAMED hypotheses only); the GPU-side cost inside",
    "   a B<=2 bracket (protocol L3); anything between adjacent ladder rungs",
    "   (L5); any B outside {2,3,4,5,6,7,8}; any (B,NDIV) pair with NDIV",
    "   outside {1,2,4,8} and NDIV != B (the rest of session 17's L10 grid --",
    "   this session closes the NDIV=2 column only, L8); any per-dispatch work",
    "   outside 500,001/1,000,003; any WORK_MUL value; any n outside the arm",
    "   values this session; the NDIV=1 B-ladder, the NDIV=B crossing, the",
    "   NDIV=8 ladder and the NDIV=4 ladder this session (L7 -- quote-only);",
    "   CROSS-UTC-DAY replication (L4); any cross-session stability of the w3",
    "   ..w8 readings (first measured here; w2 replicates the committed x2",
    "   value if C2 holds); session 2's run-1 dip cause; S=8 timing; every W",
    "   outside {128,256}; shape 2; BT ordering; any baseline-vs-variant sign;",
    "   isolated single-dispatch timing; non-empty barriers; anything off this",
    "   host.",
]
P("\n".join(unm))

text = "\n".join(out) + "\n"
open(os.path.join(HERE, "publication-s20.txt"), "w").write(text)
print(text)
