#!/usr/bin/env python3
"""JUN-59 session 25 analysis -- THE B=3 PER-DISPATCH-WORK THRESHOLD
BISECT, FIFTH CUT (one new grid point at n = 252,604 = the exact floor
midpoint of the session-24 bracket (250,000, 255,208]).

Route (frozen in protocol.txt section 6): this script parses ONLY the 21
committed run logs in its own directory (run-<tag>-r<R>.txt) and writes
publication-s25.txt. No other input. Deterministic: running it twice
yields byte-identical publication-s25.txt (checked by diff after the
recorded run).

Cross-session reference values are frozen in protocol.txt section 3 and
embedded below as named constants (committed controls, the committed z3
bracket end, session-24's mid = this session's hi anchor, the committed
B=3 class-vs-per-dispatch-work row); they are comparison values only and
never this session's measurements.
"""
import re, sys, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

# tag -> (BATCH, WORK_MUL, NDIV), protocol.txt section 0 arm table (7 rows = 21 logs)
ARMS = [("c2", 2, 1, 1), ("lo", 3, 1, 4), ("mid", 3, 97, 384),
        ("eq3", 3, 194, 768), ("hi", 3, 1213, 4753), ("b2m", 2, 97, 384),
        ("c8", 8, 1, 1)]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMW = {a[0]: a[2] for a in ARMS}
ARMD = {a[0]: a[3] for a in ARMS}
RUNS = [1, 2, 3]
N_BASE = 1000003

# committed control anchors (comparison of committed values only)
COMMITTED = {"c2": 31, "c8": 32915}
COMMITTED_SRC = {"c2": "sessions 1-24 floor band 31..32",
                 "c8": "session 4 pooled median"}
S24_REF = {"c2": 32, "c8": 32679}
# the bracket anchors (protocol section 3, quote-only L7)
Z3_REF = 1140        # session 19 pooled median (BATCH=3, NDIV=4); class INTERMEDIATE/MIXED
Z3_SRC = "session 19 pooled median (the NDIV=4 ladder rung z3)"
Z3_CLASS = "INTERMEDIATE/MIXED"
S21_Z3_REPL = 1162   # session 21's in-session replication of the z3 pair
S22_Z3_REPL = 1141   # session 22's in-session replication of the z3 pair
S23_Z3_REPL = 1129   # session 23's in-session replication of the z3 pair
S24_Z3_REPL = 1141   # session 24's in-session replication of the z3 pair
S24_MID_REF = 1166   # session 24 pooled median (BATCH=3, WM=1213, NDIV=4753); class CAPTURED
S24_MID_SRC = "session 24 pooled median (its bisect arm mid, the (1213,4753) pair)"
S24_MID_CLASS = "CAPTURED"
S24_MID_MIN = 1000   # session 24 18-cell min at the (1213,4753) pair (exactly at threshold)
# the B=3 class-vs-per-dispatch-work row (quote-only L7 except this session's lo/mid/hi)
B3ROW = [("1/8", 125000, 599, "INTERMEDIATE/MIXED", "session 18"),
         ("1/4", 250000, 1140, "INTERMEDIATE/MIXED", "session 19"),
         ("0.2552072", 255208, 1166, "CAPTURED", "session 24"),
         ("0.2604162", 260417, 1186, "CAPTURED", "session 23"),
         ("0.2708332", 270834, 1224, "CAPTURED", "session 22"),
         ("0.2916657", 291667, 1330, "CAPTURED", "session 21"),
         ("1/3", 333334, 1578, "CAPTURED", "session 17"),
         ("1/2", 500001, 2739, "CAPTURED", "session 20"),
         ("1.0", 1000003, 5520, "CAPTURED", "sessions 7/16")]

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
P("JUN-59 session 25 -- THE B=3 PER-DISPATCH-WORK THRESHOLD BISECT,")
P("FIFTH CUT (one new grid point at n = 252,604 -- the EXACT floor")
P("midpoint of the session-24 bracket (250,000, 255,208], reachable at")
P("the knob -- 41 in-box pairs, smallest (97,384); 13 pairs have their")
P("same-ratio double in-box, so eq3 IS in-box this cut), publication")
P("Produced ONLY by analysis-s25.py over the 21 committed run logs in this")
P("directory (run-<tag>-r<R>.txt); protocol.txt was frozen before the")
P("first run. Arms = binary compile-time (BATCH, WORK_MUL, NDIV); n =")
P("(1,000,003*WORK_MUL)/NDIV (integer floor). lo/hi re-run the committed")
P("bracket-end knob pairs in-session (n=250,000 = 1,000,003//4 = z3's;")
P("n=255,208 = (1,000,003*1213)//4753 = session 24's mid pair (1213,4753));")
P("mid is THE bisect point n = (1,000,003*97)//384 = 252,604 = (250,000+")
P("255,208)//2 (the smallest of 41 knob pairs mapping to it in the")
P("WM<=2,048 x NDIV<=8,192 search box -- derivation-census-s25.txt); eq3")
P("is the same-ratio (194,768) pair-representation check at mid's grid")
P("(the double of (97,384) -- in-box this time, unlike session 24's cut);")
P("b2m is the B=2 control at the bisect n. c2/c8 are the archived")
P("environment controls. ZERO derivation this session: the instrument is")
P("session 24's committed NDIV-derived source byte-identical")
P("(digest a5e539f0... -- derivation-census-s25.txt); the a-set manifest")
P("runs the ARCHIVED measured spv (16-digest corpus).")
P("The row question (protocol section 0): AT FIXED DISPATCH COUNT B=3,")
P("WHERE IN (250,000, 255,208] DOES THE B=3 CLASS FLIP FROM")
P("INTERMEDIATE/MIXED TO CAPTURED? -- mid CAPTURED narrows the flip to")
P("(250,000, 252,604]; mid INTERMEDIATE/MIXED narrows it to (252,604,")
P("255,208]; mid FLOOR is a pre-named non-monotone contradiction and is")
P("not resolved here. Protocol L2: at fixed B=3 the per-dispatch grid n")
P("and TOTAL nominal work co-vary BY CONSTRUCTION (total =")
P("3*n/1,000,003); the letters are observational discriminators among")
P("named hypotheses, never a mechanism. 1 tick = timestampPeriod =")
P("52.083 ns.")
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
    b, wm, dd = ARMB[tag], ARMW[tag], ARMD[tag]
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
                   or (not mmu or int(mmu.group(1)) != wm) or (not mdi or int(mdi.group(1)) != dd):
                    knob_field_ok = False
                    integrity.append(f"HEADER knob FIELD MISMATCH in {fn}: {l}")
                if not mn or int(mn.group(1)) != (N_BASE * wm) // dd:
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
            if bt != b or mt != wm or dt != dd:
                knob_field_ok = False
                integrity.append(f"SAMPLE knob FIELD {bt},{mt},{dt} != {b},{wm},{dd} in {fn}")

P("1. INTEGRITY (computed over the 21 logs):")
P(f"   runs parsed: 21 (7 arms x 3 runs); cell map identical across runs: {cell_keys is not None and not any('CELL MAP' in i for i in integrity)}")
P(f"   headers byte-identical across all runs outside the # n= knob line: {header_ok}")
P(f"   header batch=/work_mul=/ndiv= == run's (B,WM,NDIV) and n == (1,000,003*WM)//NDIV; every SAMPLE batch=/work_mul=/ndiv= == (B,WM,NDIV): {knob_field_ok}")
P(f"   every CELL spv= name is an archived .emitted.spv (no .iter -- the corpus is byte-identical this session): {spv_identity_ok}")
P(f"   SAMPLE lines: 450 per run (18 ok cells x 25 rounds) in 21/21 runs: {sample_counts_ok}")
P(f"   VERIFY mismatch total over all runs: {verify_mismatch_total} (per-arm: "
  + ", ".join(f"{t}={verify_mismatch_by_arm[t]}" for t in TAGS)
  + ") -- bit-exact correctness re-check inside every run; frozen INVALIDATION criterion (protocol section 4): >0 in any run makes that run DEFECTIVE and the arm INVALID")
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
P("   arm  B  WM  NDIV     n        total-nominal  (sum,128,16)   run-median band    min..max over 18 cells   host_ns")
for tag in TAGS:
    b, wm, dd = ARMB[tag], ARMW[tag], ARMD[tag]
    n = (N_BASE * wm) // dd
    vals = [pooled(tag, k) for k in ok_cells]
    v16 = pooled(tag, sum128)
    rms = run_medians(tag, sum128)
    hn = pooled_host(tag, sum128)
    tot = b * n / N_BASE
    P(f"   {tag}  {b}  {wm}  {dd:<5} {n:>8}  {tot:>12.6f}  {v16:>10.0f}     {min(rms):>8.0f}..{max(rms):<8.0f}  {min(vals):>8.0f}..{max(vals):<8.0f}  {hn:>9.0f}")
P("")

# ---- classification (protocol.txt section 4 thresholds) ----
def classify(tag):
    vals = [pooled(tag, k) for k in ok_cells]
    if all(v <= 100 for v in vals):
        return "FLOOR"
    if all(v >= 1000 for v in vals):
        return "CAPTURED"
    return "INTERMEDIATE/MIXED"

CLASS = {tag: classify(tag) for tag in TAGS}

P("3. PRE-REGISTERED LETTERS (thresholds frozen in protocol.txt section 4:")
P("   FLOOR <= 100 ticks at all 18 cells; CAPTURED >= 1000 ticks at all 18;")
P("   anything else INTERMEDIATE/MIXED):")
P("")
for tag in TAGS:
    b, wm, dd = ARMB[tag], ARMW[tag], ARMD[tag]
    n = (N_BASE * wm) // dd
    P(f"   class {tag} (B={b}, WM={wm}, NDIV={dd}, n={n}, {b*n/N_BASE:.6f} nominal units): {CLASS[tag]}")
P("")

arms_invalid = sorted(t for t in TAGS if verify_mismatch_by_arm[t] > 0)
if arms_invalid:
    P("   INVALIDATION CRITERION FIRED (frozen): VERIFY mismatch > 0 in arm(s)")
    P(f"   {arms_invalid} -- the knob arithmetic is WRONG at those arms")
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
P("   value at the control's OWN (B,WORK_MUL,NDIV) -- the a-set runs the")
P("   ARCHIVED spv bytes through the byte-identical session-25 instrument,")
P("   so this pins the environment as well):")
for s in c1_parts:
    P(f"     {s}")
if c1_ok:
    P("     VERDICT: branch (a) both controls satisfy their criteria --")
    P("     the W letters are evaluated against the row question.")
else:
    P("     VERDICT: branch (b) replication discrepancy (bearing on the")
    P("     environment pin); W letters interpretation is FLAGGED; cause UNMEASURED.")
P("")

# C2 the double bracket-anchor replication (lo == z3 knob, hi == session-24 mid knob)
vlo = pooled("lo", sum128)
vhi = pooled("hi", sum128)
lo_num_ok = abs(vlo - Z3_REF) <= 0.05 * Z3_REF
hi_num_ok = abs(vhi - S24_MID_REF) <= 0.05 * S24_MID_REF
lo_ok = lo_num_ok and CLASS["lo"] == Z3_CLASS
hi_ok = hi_num_ok and CLASS["hi"] == S24_MID_CLASS
c2_ok = lo_ok and hi_ok
P("   C2 BRACKET ANCHOR REPLICATION (lo is the committed z3 knob pair")
P("   BATCH=3,NDIV=4 -- rebuilt binary BYTE-IDENTICAL to session 19's")
P("   anv-n4-z3 (efc6f4ee...); hi is session 24's mid knob pair")
P("   BATCH=3,WORK_MUL=1213,NDIV=4753 -- rebuilt binary BYTE-IDENTICAL to")
P("   session 24's anv-bb-mid (123e8f73...) -- build-census-s25.txt;")
P("   hi is ALSO the FIRST cross-session replication of that knob pair:")
P(f"     lo (sum,128,16) pooled median {vlo:.0f} within +/-5% of committed z3 {Z3_REF} ({Z3_SRC}): {lo_num_ok}")
P(f"     lo class {CLASS['lo']} (committed z3 class {Z3_CLASS}): {CLASS['lo'] == Z3_CLASS}")
P(f"     lo context (quote-only): session 21's in-session replication {S21_Z3_REPL}; session 22's {S22_Z3_REPL}; session 23's {S23_Z3_REPL}; session 24's {S24_Z3_REPL}")
P(f"     hi (sum,128,16) pooled median {vhi:.0f} within +/-5% of session-24's {S24_MID_REF} ({S24_MID_SRC}): {hi_num_ok}")
P(f"     hi class {CLASS['hi']} (session-24 class {S24_MID_CLASS}): {CLASS['hi'] == S24_MID_CLASS}")
P(f"     NAMED, NOT HIDDEN: hi's expected class CAPTURED carries session")
P(f"     24's C3 (b) flagged risk (its 18-cell min sat exactly at {S24_MID_MIN});")
P(f"     if hi classifies INTERMEDIATE/MIXED here, C2 fires (b) and W1 is")
P(f"     FLAGGED at its frozen letter.")
if c2_ok:
    P("     VERDICT: branch (a) -- both bracket ends replicate IN-SESSION")
    P("     (at a byte-identical rebuilt binary each) and W1's bracket")
    P("     narrowing is valid at its letter.")
else:
    P("     VERDICT: branch (b) -- one or both bracket ends did not")
    P("     replicate in-session; W1 is FLAGGED; the measured classes")
    P("     stand as content; cause UNMEASURED.")
P("")

# C3 the pair-representation check (eq3 (194,768) vs mid (97,384) at identical n and B)
veq3 = pooled("eq3", sum128)
vmid = pooled("mid", sum128)
c3_num_ok = abs(veq3 - vmid) <= 0.05 * vmid
c3_ok = CLASS["eq3"] == CLASS["mid"] and c3_num_ok
P("   C3 PAIR-REPRESENTATION CHECK (eq3 is the (194,768) pair at")
P("   n = 252,604 == mid's grid and B=3 -- the same ratio 97/384 in a")
P("   different (WORK_MUL,NDIV) representation; NEW knob pairs, protocol L8;")
P("   NAMED, NOT HIDDEN: the double sits INSIDE the WM<=2,048 search box")
P("   this cut (13 of 41 in-box pairs have in-box doubles); session 24's")
P("   C3 fired (b) at its grid (same-ratio twin class-split at the frozen")
P("   1000-tick boundary) and whether that recurs here is MEASURED HERE):")
P(f"     eq3 class {CLASS['eq3']} == mid class {CLASS['mid']}: {CLASS['eq3'] == CLASS['mid']}")
P(f"     eq3 (sum,128,16) pooled median {veq3:.0f} within +/-5% of mid {vmid:.0f}: {c3_num_ok}")
if c3_ok:
    P("     VERDICT: branch (a) -- at the bisect grid the same-ratio")
    P("     representation (194,768) is behaviourally equivalent to")
    P("     (97,384) (MEASURED at this one grid point and B only; nothing")
    P("     is assumed for any other pair beyond the source reading that")
    P("     N_ELEMENTS is the only knob-derived quantity -- protocol L8).")
else:
    P("     VERDICT: branch (b) -- the same-ratio representation matters at")
    P("     this grid; the contradiction stands as measured content, is NOT")
    P("     resolved here, and mid/b2m carry the flagged risk.")
P("")

# W1 the row question: the fifth bisect cut
vb2m = pooled("b2m", sum128)
P("   W1 THE ROW QUESTION (the bisect: class(mid) at B=3, n=252,604 =")
P("   the EXACT floor midpoint of (250,000, 255,208] -- reachable at the")
P("   knob, derivation-census-s25.txt; the bracket ends are this")
P("   session's lo/hi -- C2 governs their validity):")
P(f"     class(mid) = {CLASS['mid']} (mid (sum,128,16) pooled median {vmid:.0f},")
P(f"     18-cell min..max {min(pooled('mid', k) for k in ok_cells):.0f}..{max(pooled('mid', k) for k in ok_cells):.0f})")
if not c2_ok:
    w1 = "(d)"
    P("     VERDICT: branch (d) FLAGGED -- C2 fired (b) (bracket ends did")
    P("     not replicate in-session); the measured classes stand as content")
    P("     and no bracket narrowing is claimed. ONE session; L2 binds;")
    P("     NO causal mechanism is claimed or measured.")
elif CLASS["mid"] == "CAPTURED":
    w1 = "(a)"
    P("     VERDICT: branch (a) MID-CAPTURED -- the B=3 class flip sits in")
    P("     (250,000, 252,604] n-units = (1/4, 252,604/1,000,003] work-units")
    P("     among measured grid points -- the bracket's LOWER half; the flip")
    P("     threshold in per-dispatch work sits in (0.2499993, 0.2526032].")
    P("     ONE session; L2 co-variation binds at fixed B=3; nothing between")
    P("     grid points is interpolated (L5); NO causal mechanism is claimed")
    P("     or measured.")
elif CLASS["mid"] == "INTERMEDIATE/MIXED":
    w1 = "(b)"
    P("     VERDICT: branch (b) MID-INTERMEDIATE -- the B=3 class flip sits")
    P("     in (252,604, 255,208] n-units = (252,604/1,000,003,")
    P("     255,208/1,000,003] work-units among measured grid points -- the")
    P("     bracket's UPPER half; the flip threshold in per-dispatch work")
    P("     sits in (0.2526032, 0.2552072]. ONE session; L2 binds; L5 no")
    P("     interpolation; NO causal mechanism is claimed or measured.")
elif CLASS["mid"] == "FLOOR":
    w1 = "(c)"
    P("     VERDICT: branch (c) MID-FLOOR NON-MONOTONE CONTRADICTION")
    P("     (named in advance, protocol section 5): mid FLOOR at n=252,604")
    P("     while the smaller n=250,000 point (lo) is INTERMEDIATE/MIXED")
    P("     and the larger n=255,208 point (hi) CAPTURED -- the committed")
    P("     monotone B=3 picture is contradicted at this session; the")
    P("     contradiction stands as measured content and is NOT resolved")
    P("     here (L5: nothing between grid points is interpolated). ONE")
    P("     session; NO causal mechanism is claimed or measured.")
else:
    w1 = "(d)"
    P("     VERDICT: branch (d) FLAGGED (no other letter applies).")
P(f"     b2m (B=2 control at the bisect n) class {CLASS['b2m']} (b2m (sum,128,16)")
P(f"     pooled median {vb2m:.0f}): " +
  ("'B=2 never captures' extends to n=252,604 at total work 0.5052065."
   if CLASS["b2m"] == "FLOOR" else
   "CONTRADICTION named in advance -- 'B=2 never captures' does NOT hold at n=252,604; not resolved here."))
P("")

# W2 the B=3 class-vs-per-dispatch-work row (descriptive)
P("   W2 (pre-registered, descriptive) THE B=3 CLASS-VS-PER-DISPATCH-")
P("   WORK ROW: this session's three B=3 points placed on the committed")
P("   row as TEN grid points (the committed points QUOTE-ONLY L7;")
P("   NO interpolation (L5); class granularity only):")
P("")
P("     n          work-unit     ticks  class                source")
for lbl, n, ticks, cls, src in B3ROW:
    P(f"     {n:<10} {lbl:<13} {ticks:>5}  {cls:<20} {src} (quote-only)")
P(f"     250000     1/4 (lo)      {pooled('lo', sum128):>5.0f}  {CLASS['lo']:<20} this session (== committed z3 knob)")
P(f"     252604     0.2526032     {pooled('mid', sum128):>5.0f}  {CLASS['mid']:<20} THIS SESSION (the bisect point)")
P(f"     255208     0.2552072     {pooled('hi', sum128):>5.0f}  {CLASS['hi']:<20} this session (== session-24 mid knob)")
P("")

# W3 the paired equal-grid comparisons (descriptive)
P("   W3 (pre-registered, descriptive) THE PAIRED EQUAL-GRID COMPARISONS:")
P(f"     (i) mid vs eq3 (identical n=252,604 and B=3; differ only in the")
P(f"         (WORK_MUL,NDIV) representation (97,384) vs (194,768)): {vmid:.0f} vs"
  f" {veq3:.0f} at (sum,128,16); classes {CLASS['mid']} vs {CLASS['eq3']}")
P(f"     (ii) mid vs b2m (identical n=252,604 and pair (97,384); differ only")
P(f"         in B 3 vs 2): {vmid:.0f} vs {vb2m:.0f}; classes {CLASS['mid']} vs {CLASS['b2m']}")
P(f"     (iii) lo vs mid vs hi (identical B=3; differ only in n/pair):"
  f" {vlo:.0f} / {vmid:.0f} / {vhi:.0f}; classes {CLASS['lo']} / {CLASS['mid']} / {CLASS['hi']}")
P("")

# X1 host_ns (descriptive)
P("   X1 (descriptive, host_ns at (sum,128,S=16)):")
hn = {t: pooled_host(t, sum128) for t in TAGS}
P("     " + ", ".join(f"{t} {hn[t]:.0f}" for t in TAGS))
P(f"     hi {hn['hi']:.0f} = {hn['hi']/309938:.3f}x session-24's same-knob mid"
  f" (309,938 -- the (1213,4753) pair's FIRST cross-session host_ns")
P(f"     comparison); its GPU bracket replicates per C2. lo {hn['lo']:.0f} = {hn['lo']/305931:.3f}x"
  f" session 24's (305,931; session-23's 305,159 = "
  f"{hn['lo']/305159:.3f}x; session-22's 302,655 = "
  f"{hn['lo']/302655:.3f}x; session-19 z3 305,240 = "
  f"{hn['lo']/305240:.3f}x); c2 {hn['c2']:.0f} = {hn['c2']/680860:.3f}x session 24's"
  f" (680,860); c8 {hn['c8']:.0f} = {hn['c8']/2393875:.3f}x session 24's"
  f" (2,393,875).")
P(f"     mid {hn['mid']:.0f}, eq3 {hn['eq3']:.0f}, b2m {hn['b2m']:.0f} first")
P(f"     measured here (their knob pairs are new). host_ns is the HOST-side")
P(f"     proxy (L3), not a C criterion; any excursion is NAMED, NOT HIDDEN")
P(f"     and its cause is UNMEASURED.")
P("")

P("4. VERDICT SUMMARY: C1 (a)={0}; C2 (a)={1}; C3 (a)={2}; W1 {3}.".format(
    c1_ok, c2_ok, c3_ok, w1))
P("   The named-hypothesis discrimination of the row question is as W1")
P("   states; WHY is UNMEASURED and NO causal mechanism is claimed.")

with open(os.path.join(HERE, "publication-s25.txt"), "w") as f:
    f.write("\n".join(out) + "\n")
print("\n".join(out))
