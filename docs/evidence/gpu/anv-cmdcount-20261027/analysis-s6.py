#!/usr/bin/env python3
"""JUN-59 session 6 analysis -- command-count discriminator (CMD-COUNT).

Route (frozen in protocol.txt): this script parses ONLY the 21 committed run
logs in its own directory (run-<tag>-r<R>.txt) and writes
publication-s6.txt. No other input. Deterministic: running it twice yields
byte-identical publication-s6.txt (checked by diff after the recorded run).
"""
import re, sys, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

# tag -> (BATCH, BARRIER_N), protocol.txt section 2
ARMS = [("b1n0", 1, 0), ("b1n1", 1, 1), ("b1n2", 1, 2), ("b1n3", 1, 3),
        ("b2n2", 2, 2), ("b4n0", 4, 0), ("b1n7", 1, 7)]
TAGS = [a[0] for a in ARMS]
ARMN = {a[0]: (a[1], a[2]) for a in ARMS}
RUNS = [1, 2, 3]

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
P("JUN-59 session 6 -- COMMAND-COUNT DISCRIMINATOR (CMD-COUNT), publication")
P("Produced ONLY by analysis-s6.py over the 21 committed run logs in this")
P("directory (run-<tag>-r<R>.txt); protocol.txt was frozen before the")
P("first run. Arms = the (BATCH, BARRIER_N) compile-time pair; BARRIER_N")
P("empty global execution barriers sit between ts1 and the BATCH dispatches.")
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
    b, n = ARMN[tag]
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
                if (not m or int(m.group(1)) != b) or (not m2 or int(m2.group(1)) != n):
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
P(f"   header batch=/barrier_n= fields == run's arm everywhere; every SAMPLE batch= field == run's B: {knob_field_ok}")
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

ok_cells = sorted([k for k, v in data[("b1n0", 1)][0].items() if v["pipeline"] == "ok"])
def ckey(idx):
    c = data[("b1n0", 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])

sum128 = [k for k in ok_cells if ckey(k) == ("sum", 128, "16")][0]

P("2. THE MEASURED BRACKETS (pooled median gpu_ticks over 3 runs x 25 rounds per cell):")
P("   each row: (sum,128,S=16) exact value, then min..max over the 18 pipeline-ok cells")
P("   host_ns = pooled median host submit->completion at (sum,128,S=16)")
P("")
P("   arm    B  N  (sum,128,16)   min..max over 18 cells    host_ns(sum,128,16)")
for tag in TAGS:
    b, n = ARMN[tag]
    vals = [pooled(tag, k) for k in ok_cells]
    v16 = pooled(tag, sum128)
    hn = pooled_host(tag, sum128)
    P(f"   {tag}  {b}  {n}  {v16:>10.0f}     {min(vals):>8.0f}..{max(vals):<8.0f}    {hn:>9.0f}")
P("")

# ---- letters ----
P("3. PRE-REGISTERED LETTERS (thresholds frozen in protocol.txt):")
P("")
# C1
c1_floor = all(pooled("b1n0", k) <= 100 for k in ok_cells)
c1_band = all(pooled("b4n0", k) >= 100000 for k in ok_cells)
P("   C1 CONTROL REPLICATION (b1n0 floor / b4n0 capture vs sessions 4-5):")
P(f"     b1n0: all 18 cells pooled median <= 100 ticks (the floor): {c1_floor}")
P(f"     b4n0: all 18 cells pooled median >= 100000 ticks (captured band): {c1_band}")
if c1_floor and c1_band:
    P("     VERDICT: branch (a) REPRODUCED -- C2-C4 are evaluated against the row question.")
else:
    P("     VERDICT: branch (b) NOT REPRODUCED -- C2-C4 reported but NOT EVALUABLE against")
    P("     the sessions-4-5 row; the divergence is named, its cause stays UNMEASURED.")
P("")
# C2
P("   C2 BARRIER REMOVABILITY AT B=1 (pooled median bracket per arm):")
lift = {}
for tag in ["b1n1", "b1n2", "b1n3", "b1n7"]:
    lift[tag] = all(pooled(tag, k) > 1000 for k in ok_cells)
allfloor = all(pooled(tag, k) <= 100 for tag in ["b1n0", "b1n1", "b1n2", "b1n3", "b1n7"] for k in ok_cells)
for tag in ["b1n0", "b1n1", "b1n2", "b1n3", "b1n7"]:
    vals = [pooled(tag, k) for k in ok_cells]
    P(f"     arm {tag}: min..max over 18 cells = {min(vals):.0f}..{max(vals):.0f} ticks; lifts (>1000 at all 18): {lift.get(tag, 'control')}")
lifting = [t for t in lift if lift[t]]
if lifting:
    P(f"     VERDICT: branch (a) -- the small-B undercount IS removable by bracketed empty-barrier")
    P(f"     command count at arm(s) {lifting} (name-only; observable dependence only; no causal")
    P(f"     mechanism claimed or measured).")
elif allfloor:
    P("     VERDICT: branch (b) -- the small-B undercount is NOT removable by up to 7 empty global")
    P("     barriers between ts1 and the dispatches; whatever removes it is not empty bracketed")
    P("     commands; the row question is narrowed, the mechanism stays UNMEASURED.")
else:
    P("     VERDICT: INCONCLUSIVE, quantified cell-by-cell above.")
P("")
# C3
P("   C3 EQUAL-COUNT COMPOSITION (bracket holds 6 commands in all three arms:")
P("     b1n3 = 1 dispatch + 3 barriers, b2n2 = 2 dispatches + 2 barriers,")
P("     b4n0 = 4 dispatches + 0 barriers; ratios of pooled medians per cell):")
r13, r22 = {}, {}
for k in ok_cells:
    base = pooled("b4n0", k)
    r13[k] = pooled("b1n3", k) / base if base else float("inf")
    r22[k] = pooled("b2n2", k) / base if base else float("inf")
    P(f"     {ckey(k)}: b1n3/b4n0 = {r13[k]:.2f}, b2n2/b4n0 = {r22[k]:.2f}")
inband13 = sum(1 for v in r13.values() if 0.5 <= v <= 2.0)
inband22 = sum(1 for v in r22.values() if 0.5 <= v <= 2.0)
floor13 = all(pooled("b1n3", k) <= 100 for k in ok_cells)
floor22 = all(pooled("b2n2", k) <= 100 for k in ok_cells)
cap40 = all(pooled("b4n0", k) >= 100000 for k in ok_cells)
P(f"     cells with b1n3/b4n0 in [0.5,2.0]: {inband13}/18; cells with b2n2/b4n0 in [0.5,2.0]: {inband22}/18")
P(f"     b1n3 floors (<=100 at all 18): {floor13}; b2n2 floors: {floor22}; b4n0 captures (>=100000 at all 18): {cap40}")
if inband13 >= 15 and inband22 >= 15:
    P("     VERDICT: branch (a) -- composition-irrelevant at equal bracketed command count:")
    P("     both mixed arms track the 4-dispatch arm (observable only; no mechanism claimed).")
elif floor13 and floor22 and cap40:
    P("     VERDICT: branch (b) -- empty bracketed commands do NOT substitute for dispatch")
    P("     commands: both mixed arms floor while the 4-dispatch arm captures; the capture needs")
    P("     real work commands (observable only; no mechanism claimed).")
else:
    P("     VERDICT: INCONCLUSIVE, quantified cell-by-cell above.")
P("")
# C4
P("   C4 DOSE (descriptive only): B=1 arms, pooled median bracket at (sum,128,16):")
for tag in ["b1n0", "b1n1", "b1n2", "b1n3", "b1n7"]:
    P(f"     {tag}: {pooled(tag, sum128):.0f} ticks (host_ns {pooled_host(tag, sum128):.0f})")
P("")

P("4. DERIVED (arithmetic over section 2, no new measurement):")
for tag in TAGS:
    b, n = ARMN[tag]
    v = pooled(tag, sum128)
    P(f"   {tag}: bracket {v:.0f} ticks = {v*52.083/1000:.2f} us; per-dispatch {v/b:.1f} ticks")
P("")

P("5. RULE 4 -- NOTHING MOVES: no workgroup row, no :measured? flag, no selection")
P("   answer; accelerator-targets defaults remain provisional design assumptions")
P("   (:measured? false). This is NOT the baseline-vs-variant contract of")
P("   accelerator-subgroup-reduce.cljk. NO vendor optimization exists for Intel")
P("   and none is claimed. No causal mechanism is claimed by any letter above.")
P("")
P("6. UNMEASURED (named): any causal mechanism for the undercount or the capture;")
P("   session 2's run-1 dip cause; cross-day replication; S=8 timing; every W")
P("   outside {128,256}; shape 2; any baseline-vs-variant sign; BT ordering;")
P("   isolated single-dispatch timing; any B outside the arms above; any N outside")
P("   {0,1,2,3,7}; anything about non-empty barriers; anything off this host.")

text = "\n".join(out) + "\n"
open(os.path.join(HERE, "publication-s6.txt"), "w").write(text)
print(text)
