#!/usr/bin/env python3
"""JUN-59 session 7 analysis -- B-onset localization (BONSET).

Route (frozen in protocol.txt): this script parses ONLY the 21 committed run
logs in its own directory (run-<tag>-r<R>.txt) and writes
publication-s7.txt. No other input. Deterministic: running it twice yields
byte-identical publication-s7.txt (checked by diff after the recorded run).
"""
import re, sys, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

# tag -> (BATCH, BARRIER_N), protocol.txt section 2
ARMS = [("b1n0", 1), ("b2n0", 2), ("b3n0", 3), ("b4n0", 4),
        ("b5n0", 5), ("b6n0", 6), ("b8n0", 8)]
TAGS = [a[0] for a in ARMS]
ARMN = {a[0]: a[1] for a in ARMS}
RUNS = [1, 2, 3]

# committed anchors (comparison of committed numbers only; sessions 4-6)
COMMITTED = {1: 31, 2: 31, 4: 11674, 8: 32915}   # session 4 pooled medians at (sum,128,S=16)
COMMITTED_PD_FLAT = (3455.69, 4369.81)           # session 4, per-dispatch flat band, B>=16
COMMITTED_PD_B4 = 2918                           # session 4, B=4 per-dispatch

cell_re = re.compile(
    r"^CELL idx=(\d+) spv=(\S+) op=(\S+) wg=(\d+) forced=(\S+) probe_size=(-?\d+) "
    r"probe_nsub=(-?\d+) probe_wg=(-?\d+) pipeline=(\S+) void=(\d)")
verify_re = re.compile(r"^VERIFY idx=(\d+) checked=(\d+) mismatch=(\d+) ok=(\d)")
sample_re = re.compile(
    r"^SAMPLE round=(\d+) idx=(\d+) batch=(\d+) gpu_ticks=(\d+) gpu_ns=([\d.]+) "
    r"per_dispatch_ns=([\d.]+) host_ns=(\d+)")

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
            samples.append((int(m.group(1)), int(m.group(2)), int(m.group(3)),
                            int(m.group(4)), float(m.group(5)), float(m.group(6)), int(m.group(7))))
        elif line.startswith("# done"):
            header.append(line)
    return cells, verifies, samples, header

def med(xs):
    return statistics.median(xs)

out = []
P = out.append
P("JUN-59 session 7 -- B-ONSET LOCALIZATION (BONSET), publication")
P("Produced ONLY by analysis-s7.py over the 21 committed run logs in this")
P("directory (run-<tag>-r<R>.txt); protocol.txt was frozen before the")
P("first run. Arms = the BATCH compile-time value alone (BARRIER_N=0")
P("everywhere; the instrument is the byte-identical session-6 snapshot).")
P("1 tick = timestampPeriod = 52.083 ns on this device.")
P("")

# ---- load everything, integrity checks ----
data = {}          # (tag, run) -> (cells, verifies, samples, header)
cell_keys = None
integrity = []
header_ok = True
knob_field_ok = True
verify_mismatch_total = 0
forcing_ok = 0
forcing_total = 0
s8_fail = 0
sample_counts_ok = True
base_header = None
for tag in TAGS:
    b = ARMN[tag]
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
                m = re.search(r"batch=(\d+)", l)
                m2 = re.search(r"barrier_n=(\d+)", l)
                if (not m or int(m.group(1)) != b) or (not m2 or int(m2.group(1)) != 0):
                    knob_field_ok = False
                    integrity.append(f"HEADER knob FIELD MISMATCH in {fn}: {l}")
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
        for (rnd, idx, bt, gt, gn, pdn, hn) in samples:
            if bt != b:
                knob_field_ok = False
                integrity.append(f"SAMPLE batch= FIELD {bt} != {b} in {fn}")

P("1. INTEGRITY (computed over the 21 logs):")
P(f"   runs parsed: 21 (7 arms x 3 runs); cell map identical across runs: {cell_keys is not None and not any('CELL MAP' in i for i in integrity)}")
P(f"   headers byte-identical across all runs outside the # n= knob line: {header_ok}")
P(f"   header batch= field == run's B and barrier_n=0 everywhere; every SAMPLE batch= field == run's B: {knob_field_ok}")
P(f"   SAMPLE lines: 450 per run (18 ok cells x 25 rounds) in 21/21 runs: {sample_counts_ok}")
P(f"   VERIFY mismatch total over all runs: {verify_mismatch_total} (bit-exact correctness re-check)")
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
        xs += [s[3] for s in samples if s[1] == idx]
    return med(xs)

def pooled_host(tag, idx):
    xs = []
    for r in RUNS:
        cells, verifies, samples, header = data[(tag, r)]
        xs += [s[6] for s in samples if s[1] == idx]
    return med(xs)

def run_medians(tag, idx):
    ms = []
    for r in RUNS:
        cells, verifies, samples, header = data[(tag, r)]
        ms.append(med([s[3] for s in samples if s[1] == idx]))
    return ms

ok_cells = sorted([k for k, v in data[("b1n0", 1)][0].items() if v["pipeline"] == "ok"])
def ckey(idx):
    c = data[("b1n0", 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])

sum128 = [k for k in ok_cells if ckey(k) == ("sum", 128, "16")][0]

P("2. THE MEASURED BRACKETS (pooled median gpu_ticks over 3 runs x 25 rounds per cell):")
P("   each row: (sum,128,S=16) exact value, per-run median band at that cell,")
P("   then min..max over the 18 pipeline-ok cells; host_ns at (sum,128,S=16)")
P("")
P("   arm    B  (sum,128,16)   run-median band    min..max over 18 cells   host_ns")
for tag in TAGS:
    b = ARMN[tag]
    vals = [pooled(tag, k) for k in ok_cells]
    v16 = pooled(tag, sum128)
    rms = run_medians(tag, sum128)
    hn = pooled_host(tag, sum128)
    P(f"   {tag}  {b}  {v16:>10.0f}     {min(rms):>8.0f}..{max(rms):<8.0f}  {min(vals):>8.0f}..{max(vals):<8.0f}  {hn:>9.0f}")
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
    P(f"   class {tag} (B={ARMN[tag]}): {CLASS[tag]}")
P("")

# O3 first (prerequisite; O1(d) depends on it)
o3_parts = []
o3_floor_ok = CLASS["b1n0"] == "FLOOR" and CLASS["b2n0"] == "FLOOR"
o3_parts.append(f"b1n0 and b2n0 satisfy FLOOR: {o3_floor_ok}")
v4 = pooled("b4n0", sum128)
v8 = pooled("b8n0", sum128)
o3_b4_ok = abs(v4 - COMMITTED[4]) <= 0.05 * COMMITTED[4]
o3_b8_ok = abs(v8 - COMMITTED[8]) <= 0.05 * COMMITTED[8]
o3_parts.append(f"b4n0 (sum,128,16) pooled median {v4:.0f} within +/-5% of committed {COMMITTED[4]} (session 4): {o3_b4_ok}")
o3_parts.append(f"b8n0 (sum,128,16) pooled median {v8:.0f} within +/-5% of committed {COMMITTED[8]} (session 4): {o3_b8_ok}")
o3_ok = o3_floor_ok and o3_b4_ok and o3_b8_ok
P("   O3 CONTROL REPLICATION (numeric agreement with the committed value at")
P("   each control's OWN B -- the named fix for session 6's C1 threshold defect):")
for s in o3_parts:
    P(f"     {s}")
if o3_ok:
    P("     VERDICT: branch (a) all four controls satisfy their criteria --")
    P("     O1-O2 are evaluated against the row question.")
else:
    P("     VERDICT: branch (b) replication discrepancy -- O1 interpretation is")
    P("     flagged per O1(d); the discrepancy's cause stays UNMEASURED.")
P("")

# O1
P("   O1 ONSET LOCALIZATION (the row question): classes above.")
if not o3_ok:
    P("     VERDICT: per O1(d), interpretation FLAGGED by the O3 discrepancy;")
    P("     the class assignments above stand as measured content.")
elif CLASS["b3n0"] == "CAPTURED" and CLASS["b2n0"] == "FLOOR":
    P("     VERDICT: branch (a) -- b3n0 CAPTURED while b2n0 FLOOR: capture turns")
    P("     on strictly between B=2 and B=3 (the committed 'between 2 and 4' band")
    P("     is narrowed on the low side). Observable only; NO causal mechanism")
    P("     claimed or measured.")
elif CLASS["b3n0"] == "FLOOR" and CLASS["b4n0"] == "CAPTURED":
    P("     VERDICT: branch (b) -- b3n0 FLOOR while b4n0 CAPTURED: capture turns")
    P("     on strictly between B=3 and B=4 (the committed band is narrowed on the")
    P("     high side). Observable only; NO causal mechanism claimed or measured.")
else:
    P("     VERDICT: branch (c) -- b3n0 is INTERMEDIATE/MIXED: an intermediate")
    P("     state exists at B=3 (or the classes are cell-mixed); the onset is a")
    P("     band, not a point; per-dispatch figures below; mechanism UNMEASURED.")
P("")

# O2
P("   O2 POST-ONSET GROWTH (descriptive; per-dispatch = pooled median bracket / B")
P(f"   at (sum,128,16); committed anchors: B=4 {COMMITTED_PD_B4} ticks/dispatch,")
P(f"   flat band {COMMITTED_PD_FLAT[0]}..{COMMITTED_PD_FLAT[1]} ticks/dispatch for B>=16 (session 4)):")
for tag in TAGS:
    b = ARMN[tag]
    v = pooled(tag, sum128)
    pd = v / b
    where = ""
    if pd < COMMITTED_PD_FLAT[0]:
        where = "below the committed flat band"
    elif pd > COMMITTED_PD_FLAT[1]:
        where = "above the committed flat band"
    else:
        where = "inside the committed flat band"
    P(f"     {tag}: bracket {v:.0f} ticks -> per-dispatch {pd:.1f} ({where})")
P("")

# O4
P("   O4 B-DOSE (descriptive only): this session's own B-curve at (sum,128,16)")
for tag in TAGS:
    b = ARMN[tag]
    P(f"     B={b}: bracket {pooled(tag, sum128):.0f} ticks = {pooled(tag, sum128)*52.083/1000:.2f} us;"
      f" host_ns {pooled_host(tag, sum128):.0f}")
P("")

P("4. DERIVED (arithmetic over section 2, no new measurement):")
for tag in TAGS:
    b = ARMN[tag]
    v = pooled(tag, sum128)
    if b in COMMITTED and b != 1 and b != 2:
        d = (v - COMMITTED[b]) / COMMITTED[b] * 100
        P(f"   {tag}: bracket {v:.0f} ticks = {v*52.083/1000:.2f} us; per-dispatch {v/b:.1f} ticks;"
          f" vs committed {COMMITTED[b]}: {d:+.2f}%")
    elif b in COMMITTED:
        P(f"   {tag}: bracket {v:.0f} ticks = {v*52.083/1000:.2f} us; per-dispatch {v/b:.1f} ticks;"
          f" vs committed floor {COMMITTED[b]}")
    else:
        P(f"   {tag}: bracket {v:.0f} ticks = {v*52.083/1000:.2f} us; per-dispatch {v/b:.1f} ticks;"
          f" (no committed anchor at this B -- new)")
P("")

P("5. RULE 4 -- NOTHING MOVES: no workgroup row, no :measured? flag, no selection")
P("   answer; accelerator-targets defaults remain provisional design assumptions")
P("   (:measured? false). This is NOT the baseline-vs-variant contract of")
P("   accelerator-subgroup-reduce.cljk. NO vendor optimization exists for Intel")
P("   and none is claimed. No causal mechanism is claimed by any letter above.")
P("")
P("6. UNMEASURED (named): any causal mechanism for the undercount, the capture,")
P("   or the onset location; WHY capture turns on where it does; B=7; any B")
P("   outside {1,2,3,4,5,6,8}; any N>0 at these B; session 2's run-1 dip cause;")
P("   cross-day replication; S=8 timing; every W outside {128,256}; shape 2; any")
P("   baseline-vs-variant sign; BT ordering; isolated single-dispatch timing;")
P("   anything about non-empty barriers; anything off this host.")

text = "\n".join(out) + "\n"
open(os.path.join(HERE, "publication-s7.txt"), "w").write(text)
print(text)
