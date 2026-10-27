#!/usr/bin/env python3
"""JUN-59 session 8 analysis -- WORK-DOSE DISCRIMINATOR (WORKMUL).

Route (frozen in protocol.txt): this script parses ONLY the 24 committed run
logs in its own directory (run-<tag>-r<R>.txt) and writes
publication-s8.txt. No other input. Deterministic: running it twice yields
byte-identical publication-s8.txt (checked by diff after the recorded run).
"""
import re, sys, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

# tag -> (BATCH, WORK_MUL), protocol.txt section 2
ARMS = [("b1m1", 1, 1), ("b2m1", 2, 1), ("b3m1", 3, 1), ("b8m1", 8, 1),
        ("b1m3", 1, 3), ("b1m8", 1, 8), ("b2m3", 2, 3), ("b2m8", 2, 8)]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMM = {a[0]: a[2] for a in ARMS}
RUNS = [1, 2, 3]
N_BASE = 1000003

# committed anchors (comparison of committed numbers only)
COMMITTED = {"b1m1": 31, "b2m1": 31, "b3m1": 5520, "b8m1": 32915}
COMMITTED_SRC = {"b1m1": "sessions 1-7 floor", "b2m1": "sessions 1-7 floor",
                 "b3m1": "session 7 pooled median", "b8m1": "session 4 pooled median"}

cell_re = re.compile(
    r"^CELL idx=(\d+) spv=(\S+) op=(\S+) wg=(\d+) forced=(\S+) probe_size=(-?\d+) "
    r"probe_nsub=(-?\d+) probe_wg=(-?\d+) pipeline=(\S+) void=(\d)")
verify_re = re.compile(r"^VERIFY idx=(\d+) checked=(\d+) mismatch=(\d+) ok=(\d)")
sample_re = re.compile(
    r"^SAMPLE round=(\d+) idx=(\d+) batch=(\d+) work_mul=(\d+) gpu_ticks=(\d+) "
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
                            int(m.group(5)), float(m.group(6)), float(m.group(7)), int(m.group(8))))
        elif line.startswith("# done"):
            header.append(line)
    return cells, verifies, samples, header

def med(xs):
    return statistics.median(xs)

out = []
P = out.append
P("JUN-59 session 8 -- WORK-DOSE DISCRIMINATOR (WORKMUL), publication")
P("Produced ONLY by analysis-s8.py over the 24 committed run logs in this")
P("directory (run-<tag>-r<R>.txt); protocol.txt was frozen before the")
P("first run. Arms = the (BATCH, WORK_MUL) compile-time pair (BARRIER_N=0")
P("everywhere; the instrument is the archived session-7 snapshot with the")
P("single WORK_MUL knob derivation, 4 hunks, instrument-derivation.diff.txt).")
P("1 work unit = one dispatch of the archived grid (n=1,000,003); an (B,M)")
P("arm runs B dispatches of an M-times grid = B*M work units.")
P("1 tick = timestampPeriod = 52.083 ns on this device.")
P("")

# ---- load everything, integrity checks ----
data = {}          # (tag, run) -> (cells, verifies, samples, header)
cell_keys = None
integrity = []
header_ok = True
knob_field_ok = True
n_field_ok = True
verify_mismatch_total = 0
forcing_ok = 0
forcing_total = 0
s8_fail = 0
sample_counts_ok = True
base_header = None
for tag in TAGS:
    b, mm = ARMB[tag], ARMM[tag]
    for r in RUNS:
        fn = f"run-{tag}-r{r}.txt"
        cells, verifies, samples, header = load(os.path.join(HERE, fn))
        data[(tag, r)] = (cells, verifies, samples, header)
        keys = tuple(sorted((k, v["op"], v["wg"], v["forced"], v["pipeline"]) for k, v in cells.items()))
        if cell_keys is None:
            cell_keys = keys
        elif keys != cell_keys:
            integrity.append(f"CELL MAP MISMATCH in {fn}")
        # header identity: identical across everything except the "# n=" line
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
                if (not mb or int(mb.group(1)) != b) or (not mbar or int(mbar.group(1)) != 0) \
                   or (not mmu or int(mmu.group(1)) != mm):
                    knob_field_ok = False
                    integrity.append(f"HEADER knob FIELD MISMATCH in {fn}: {l}")
                if not mn or int(mn.group(1)) != N_BASE * mm:
                    n_field_ok = False
                    integrity.append(f"HEADER n= FIELD MISMATCH in {fn}: {l}")
        for (idx, ch, mis, ok) in verifies:
            verify_mismatch_total += mis
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
        for (rnd, idx, bt, mt, gt, gn, pdn, hn) in samples:
            if bt != b or mt != mm:
                knob_field_ok = False
                integrity.append(f"SAMPLE knob FIELD {bt},{mt} != {b},{mm} in {fn}")

P("1. INTEGRITY (computed over the 24 logs):")
P(f"   runs parsed: 24 (8 arms x 3 runs); cell map identical across runs: {cell_keys is not None and not any('CELL MAP' in i for i in integrity)}")
P(f"   headers byte-identical across all runs outside the # n= knob line: {header_ok}")
P(f"   header batch=/work_mul= fields == run's (B,M), barrier_n=0, n=1,000,003*M; every SAMPLE batch=/work_mul= == run's (B,M): {knob_field_ok and n_field_ok}")
P(f"   SAMPLE lines: 450 per run (18 ok cells x 25 rounds) in 24/24 runs: {sample_counts_ok}")
P(f"   VERIFY mismatch total over all runs: {verify_mismatch_total} (bit-exact correctness re-check, inside every run)")
P(f"   forcing reality (pipeline-ok cell-runs where probe_size==forced and probe_nsub==wg/forced): {forcing_ok}/{forcing_total}")
P(f"   S=8 cells fail-closed (pipeline=FAIL, forced=8): {s8_fail} cell-runs (6 per run x 24 runs = 144 expected)")
if integrity:
    for i in integrity:
        P(f"   !! {i}")
P("")

# ---- per-cell pooled medians per arm ----
def pooled(tag, idx):
    xs = []
    for r in RUNS:
        cells, verifies, samples, header = data[(tag, r)]
        xs += [s[4] for s in samples if s[1] == idx]
    return med(xs)

def pooled_host(tag, idx):
    xs = []
    for r in RUNS:
        cells, verifies, samples, header = data[(tag, r)]
        xs += [s[7] for s in samples if s[1] == idx]
    return med(xs)

def run_medians(tag, idx):
    ms = []
    for r in RUNS:
        cells, verifies, samples, header = data[(tag, r)]
        ms.append(med([s[4] for s in samples if s[1] == idx]))
    return ms

ok_cells = sorted([k for k, v in data[("b1m1", 1)][0].items() if v["pipeline"] == "ok"])
def ckey(idx):
    c = data[("b1m1", 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])

sum128 = [k for k in ok_cells if ckey(k) == ("sum", 128, "16")][0]

P("2. THE MEASURED BRACKETS (pooled median gpu_ticks over 3 runs x 25 rounds per cell):")
P("   each row: (sum,128,S=16) exact value, per-run median band at that cell,")
P("   then min..max over the 18 pipeline-ok cells; host_ns at (sum,128,S=16)")
P("")
P("   arm    B  M  units  (sum,128,16)   run-median band    min..max over 18 cells   host_ns")
for tag in TAGS:
    b, mm = ARMB[tag], ARMM[tag]
    vals = [pooled(tag, k) for k in ok_cells]
    v16 = pooled(tag, sum128)
    rms = run_medians(tag, sum128)
    hn = pooled_host(tag, sum128)
    P(f"   {tag}  {b}  {mm}  {b*mm:>4}  {v16:>10.0f}     {min(rms):>8.0f}..{max(rms):<8.0f}  {min(vals):>8.0f}..{max(vals):<8.0f}  {hn:>9.0f}")
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

# ---- letters ----
P("3. PRE-REGISTERED LETTERS (thresholds frozen in protocol.txt section 4:")
P("   FLOOR <= 100 ticks at all 18 cells; CAPTURED >= 1000 ticks at all 18;")
P("   anything else INTERMEDIATE/MIXED):")
P("")
for tag in TAGS:
    P(f"   class {tag} (B={ARMB[tag]}, M={ARMM[tag]}, {ARMB[tag]*ARMM[tag]} units): {CLASS[tag]}")
P("")

# C1 first (prerequisite; W1(d) depends on it)
c1_parts = []
c1_floor_ok = CLASS["b1m1"] == "FLOOR" and CLASS["b2m1"] == "FLOOR"
c1_parts.append(f"b1m1 and b2m1 satisfy FLOOR: {c1_floor_ok}")
v3 = pooled("b3m1", sum128)
v8 = pooled("b8m1", sum128)
c1_b3_ok = abs(v3 - COMMITTED["b3m1"]) <= 0.05 * COMMITTED["b3m1"]
c1_b8_ok = abs(v8 - COMMITTED["b8m1"]) <= 0.05 * COMMITTED["b8m1"]
c1_parts.append(f"b3m1 (sum,128,16) pooled median {v3:.0f} within +/-5% of committed {COMMITTED['b3m1']} ({COMMITTED_SRC['b3m1']}): {c1_b3_ok}")
c1_parts.append(f"b8m1 (sum,128,16) pooled median {v8:.0f} within +/-5% of committed {COMMITTED['b8m1']} ({COMMITTED_SRC['b8m1']}): {c1_b8_ok}")
c1_ok = c1_floor_ok and c1_b3_ok and c1_b8_ok
P("   C1 CONTROL REPLICATION (numeric agreement with the committed value at")
P("   each control's OWN (B,M) -- the session-7 fix, kept; b3m1/b8m1 at")
P("   WORK_MUL=1 also pin the derivation edit to the archived behaviour):")
for s in c1_parts:
    P(f"     {s}")
if c1_ok:
    P("     VERDICT: branch (a) all four controls satisfy their criteria --")
    P("     W1-W4 are evaluated against the row question.")
else:
    P("     VERDICT: branch (b) replication discrepancy -- W1 interpretation is")
    P("     flagged per W1(d); the discrepancy's cause stays UNMEASURED.")
P("")

# W1
P("   W1 WORK-DOSE AT B=2 (the row question): classes of b2m3 and b2m8 above.")
if not c1_ok:
    P("     VERDICT: per W1(d), interpretation FLAGGED by the C1 discrepancy;")
    P("     the class assignments above stand as measured content.")
elif CLASS["b2m3"] == "FLOOR" and CLASS["b2m8"] == "FLOOR":
    P("     VERDICT: branch (a) -- b2m3 and b2m8 are FLOOR while the b8m1")
    P("     control (8 work units) is captured: capture at B=2 is NOT reachable")
    P("     by up to 8x per-dispatch work (b2m8 carries 16 work units inside")
    P("     the bracket -- twice b8m1's 8 units). The capture is not a")
    P("     total-work threshold on this axis; dispatch count stays implicated.")
    P("     Observable only; NO causal mechanism claimed or measured.")
elif CLASS["b2m3"] == "CAPTURED" or CLASS["b2m8"] == "CAPTURED":
    P("     VERDICT: branch (b) -- a B=2 arm with more per-dispatch work is")
    P("     CAPTURED: capture CAN be driven by per-dispatch work at fixed B=2;")
    P("     the 2->3 onset step is not purely a dispatch-count step. Observable")
    P("     only; NO causal mechanism claimed or measured.")
else:
    P("     VERDICT: branch (c) -- INTERMEDIATE/MIXED at B=2 with more work:")
    P("     the work-dose answer is cell-quantified in section 2; mechanism")
    P("     UNMEASURED.")
P("")

# W2
P("   W2 EQUAL-TOTAL-WORK PAIRS (descriptive; same total work inside the")
P("   bracket, different dispatch count):")
for one, many, units in [("b1m3", "b3m1", 3), ("b1m8", "b8m1", 8)]:
    v_one, v_many = pooled(one, sum128), pooled(many, sum128)
    h_one, h_many = pooled_host(one, sum128), pooled_host(many, sum128)
    ratio = (v_one / v_many) if v_many else float("nan")
    P(f"     {units} units: {one} (1 dispatch) {v_one:.0f} ticks / {CLASS[one]} / host_ns {h_one:.0f}"
      f"  vs  {many} ({ARMB[many]} dispatches) {v_many:.0f} ticks / {CLASS[many]} / host_ns {h_many:.0f}"
      f"  bracket ratio {ratio:.3f}")
P("")

# W3
P("   W3 SINGLE-DISPATCH WORK-DOSE (descriptive; B=1 only):")
for tag in ["b1m1", "b1m3", "b1m8"]:
    P(f"     {tag} (M={ARMM[tag]}): bracket {pooled(tag, sum128):.0f} ticks / {CLASS[tag]};"
      f" host_ns {pooled_host(tag, sum128):.0f}")
P("")

# W4
P("   W4 HOST TIME PER WORK UNIT (descriptive; host_ns / (B*M) at (sum,128,16)):")
for tag in TAGS:
    b, mm = ARMB[tag], ARMM[tag]
    P(f"     {tag}: host_ns {pooled_host(tag, sum128):.0f} / {b*mm} units = {pooled_host(tag, sum128)/(b*mm):.0f} ns/unit")
P("")

P("4. DERIVED (arithmetic over section 2, no new measurement):")
for tag in TAGS:
    v = pooled(tag, sum128)
    if tag in COMMITTED:
        d = (v - COMMITTED[tag]) / COMMITTED[tag] * 100
        P(f"   {tag}: bracket {v:.0f} ticks = {v*52.083/1000:.2f} us;"
          f" vs committed {COMMITTED[tag]} ({COMMITTED_SRC[tag]}): {d:+.2f}%")
    else:
        P(f"   {tag}: bracket {v:.0f} ticks = {v*52.083/1000:.2f} us;"
          f" (no committed anchor at this (B,M) -- new)")
P("")

P("5. RULE 4 -- NOTHING MOVES: no workgroup row, no :measured? flag, no selection")
P("   answer; accelerator-targets defaults remain provisional design assumptions")
P("   (:measured? false). This is NOT the baseline-vs-variant contract of")
P("   accelerator-subgroup-reduce.cljk. NO vendor optimization exists for Intel")
P("   and none is claimed. No causal mechanism is claimed by any letter above.")
P("")
P("6. UNMEASURED (named): any causal mechanism for the undercount, the capture,")
P("   or the onset location; WHY capture turns on where it does; 'more work' vs")
P("   'bigger grid' (the frozen named limitation -- WORK_MUL scales both); any M")
P("   outside {1,3,8}; any (B,M) outside the eight arms; B=7; any N>0; session")
P("   2's run-1 dip cause; cross-day replication; S=8 timing; every W outside")
P("   {128,256}; shape 2; any baseline-vs-variant sign; BT ordering; isolated")
P("   single-dispatch timing; non-empty barriers; anything off this host.")

text = "\n".join(out) + "\n"
open(os.path.join(HERE, "publication-s8.txt"), "w").write(text)
print(text)
