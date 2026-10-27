#!/usr/bin/env python3
"""JUN-59 session 5 analysis -- timestamp-stage discriminator (TS-STAGE).

Route (frozen in protocol.txt): this script parses ONLY the 36 committed run
logs in its own directory (run-<arm>-b<B>-r<R>.txt) and writes
publication-s5.txt. No other input. Deterministic: running it twice yields
byte-identical publication-s5.txt (checked by diff after the recorded run).
"""
import re, sys, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

ARMS = ["tb", "tt", "bb"]
BS = [1, 2, 4, 64]
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
P("JUN-59 session 5 -- TIMESTAMP-STAGE DISCRIMINATOR (TS-STAGE), publication")
P("Produced ONLY by analysis-s5.py over the 36 committed run logs in this")
P("directory (run-<arm>-b<B>-r<R>.txt); protocol.txt was frozen before the")
P("first run. Arms: tb=(TOP,BOTTOM) control, tt=(TOP,TOP), bb=(BOTTOM,BOTTOM)")
P("of the two vkCmdWriteTimestamp endpoints around the BATCH dispatches.")
P("1 tick = timestampPeriod = 52.083 ns on this device.")
P("")

# ---- load everything, integrity checks ----
data = {}          # (arm, b, run) -> (cells, verifies, samples, header)
cell_keys = None
integrity = []
header_by_b = {}
header_ok = True
batch_field_ok = True
verify_mismatch_total = 0
forcing_ok = 0
forcing_total = 0
s8_fail = 0
sample_counts_ok = True
for arm in ARMS:
    for b in BS:
        for r in RUNS:
            fn = f"run-{arm}-b{b}-r{r}.txt"
            cells, verifies, samples, header = load(os.path.join(HERE, fn))
            data[(arm, b, r)] = (cells, verifies, samples, header)
            keys = tuple(sorted((k, v["op"], v["wg"], v["forced"], v["pipeline"]) for k, v in cells.items()))
            if cell_keys is None:
                cell_keys = keys
            elif keys != cell_keys:
                integrity.append(f"CELL MAP MISMATCH in {fn}")
            # header identity: identical across everything except batch=<B>
            hb = tuple(l for l in header if not l.startswith("# n="))
            if b in header_by_b:
                if header_by_b[b] != hb:
                    header_ok = False
                    integrity.append(f"HEADER MISMATCH at B={b} in {fn}")
            else:
                header_by_b[b] = hb
            for l in header:
                if l.startswith("# n="):
                    m = re.search(r"batch=(\d+)", l)
                    if not m or int(m.group(1)) != b:
                        batch_field_ok = False
                        integrity.append(f"HEADER batch= FIELD MISMATCH in {fn}: {l}")
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
                    batch_field_ok = False
                    integrity.append(f"SAMPLE batch= FIELD {bt} != {b} in {fn}")

# header identity ACROSS arms at the same B (arm is not printed in the header)
P("1. INTEGRITY (computed over the 36 logs):")
P(f"   runs parsed: 36 (3 arms x 4 B x 3 runs); cell map identical across runs: {cell_keys is not None and not any('CELL MAP' in i for i in integrity)}")
P(f"   headers byte-identical within each B and across arms (arm not printed): {header_ok}")
P(f"   header batch= field == run's B everywhere; every SAMPLE batch= field == run's B: {batch_field_ok}")
P(f"   SAMPLE lines: 450 per run (18 ok cells x 25 rounds) in 36/36 runs: {sample_counts_ok}")
P(f"   VERIFY mismatch total over all runs: {verify_mismatch_total} (bit-exact correctness re-check)")
P(f"   forcing reality (pipeline-ok cell-runs where probe_size==forced and probe_nsub==wg/forced): {forcing_ok}/{forcing_total}")
P(f"   S=8 cells fail-closed (pipeline=FAIL, forced=8): {s8_fail} cell-runs (6 per run x 36 runs = 216)")
if integrity:
    for i in integrity:
        P(f"   !! {i}")
P("")

# ---- per-cell pooled medians per (arm, b) ----
def pooled(arm, b, idx):
    xs = []
    for r in RUNS:
        cells, verifies, samples, header = data[(arm, b, r)]
        xs += [s[3] for s in samples if s[1] == idx]
    return med(xs)

def pooled_host(arm, b, idx):
    xs = []
    for r in RUNS:
        cells, verifies, samples, header = data[(arm, b, r)]
        xs += [s[6] for s in samples if s[1] == idx]
    return med(xs)

ok_cells = sorted([k for k, v in data[("tb", 1, 1)][0].items() if v["pipeline"] == "ok"])
def ckey(idx):
    c = data[("tb", 1, 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])

sum128 = [k for k in ok_cells if ckey(k) == ("sum", 128, "16")][0]

P("2. THE MEASURED BRACKETS (pooled median gpu_ticks over 3 runs x 25 rounds per cell):")
P("   each row: (sum,128,S=16) exact value, then min..max over the 18 pipeline-ok cells")
P("   host_ns = pooled median host submit->completion at (sum,128,S=16)")
P("")
P("   arm  B    (sum,128,16)   min..max over 18 cells    host_ns(sum,128,16)")
for arm in ARMS:
    for b in BS:
        vals = [pooled(arm, b, k) for k in ok_cells]
        v16 = pooled(arm, b, sum128)
        hn = pooled_host(arm, b, sum128)
        P(f"   {arm}  B={b:<3} {v16:>10.0f}     {min(vals):>8.0f}..{max(vals):<8.0f}    {hn:>9.0f}")
P("")

# ---- letters ----
P("3. PRE-REGISTERED LETTERS (thresholds frozen in protocol.txt):")
P("")
# L1
l1_floor = all(pooled("tb", 1, k) <= 100 for k in ok_cells)
l1_band = all(pooled("tb", 64, k) >= 100000 for k in ok_cells)
P("   L1 CONTROL REPLICATION (arm tb vs session 4's shape):")
P(f"     B=1: all 18 cells pooled median <= 100 ticks (the 31-tick floor): {l1_floor}")
P(f"     B=64: all 18 cells pooled median >= 100000 ticks (captured band): {l1_band}")
if l1_floor and l1_band:
    P("     VERDICT: branch (a) REPRODUCED -- L2-L4 are evaluated against the row question.")
else:
    P("     VERDICT: branch (b) NOT REPRODUCED -- L2-L4 reported but NOT EVALUABLE against the session-4 row; cause UNMEASURED.")
P("")
# L2
ratios = {}
for k in ok_cells:
    ratios[k] = pooled("tb", 64, k) / pooled("tt", 64, k) if pooled("tt", 64, k) else float("inf")
ge5 = sum(1 for v in ratios.values() if v >= 5)
le2 = sum(1 for v in ratios.values() if v <= 2)
P("   L2 TS2-STAGE DEPENDENCE OF THE LARGE-B CAPTURE (B=64, ratio tb/tt per cell):")
P(f"     cells with ratio >= 5 (tt collapses): {ge5}/18")
P(f"     cells with ratio <= 2 (tt tracks tb): {le2}/18")
for k in ok_cells:
    P(f"     {ckey(k)}: tb/tt = {ratios[k]:.2f}")
if ge5 >= 15:
    P("     VERDICT: branch (a) -- the captured large-B bracket DEPENDS on ts2's BOTTOM_OF_PIPE placement")
    P("     (observable dependence only; no causal mechanism claimed or measured).")
elif le2 >= 15:
    P("     VERDICT: branch (b) -- the capture does NOT depend on ts2's stage placement among {TOP,BOTTOM}.")
else:
    P("     VERDICT: INCONCLUSIVE, quantified cell-by-cell above.")
P("")
# L3
lift = {}
for arm in ["tt", "bb"]:
    lift[arm] = all(pooled(arm, 1, k) > 1000 for k in ok_cells)
allfloor = all(pooled(arm, 1, k) <= 100 for arm in ARMS for k in ok_cells)
P("   L3 FLOOR REMOVABILITY AT B=1 (pooled median bracket per arm):")
for arm in ARMS:
    vals = [pooled(arm, 1, k) for k in ok_cells]
    P(f"     arm {arm}: min..max over 18 cells = {min(vals):.0f}..{max(vals):.0f} ticks")
P(f"     tt lifts the floor (all cells > 1000): {lift['tt']}")
P(f"     bb lifts the floor (all cells > 1000): {lift['bb']}")
if lift["tt"] or lift["bb"]:
    which = [a for a in ["tt", "bb"] if lift[a]]
    P(f"     VERDICT: branch (a) -- the small-B undercount IS removable by the stage placement of arm(s) {which}")
    P("     (name-only; no causal mechanism claimed or measured).")
elif allfloor:
    P("     VERDICT: branch (b) -- the small-B undercount is NOT removable by the stage placements")
    P("     tested here ((TOP,BOTTOM),(TOP,TOP),(BOTTOM,BOTTOM)); the row question is narrowed,")
    P("     the mechanism stays UNMEASURED.")
else:
    P("     VERDICT: quantified above, not classified.")
P("")
# L4
P("   L4 TS1-SIDE (descriptive only): B=64 ratio bb/tb per cell:")
for k in ok_cells:
    tbv = pooled("tb", 64, k)
    bbv = pooled("bb", 64, k)
    P(f"     {ckey(k)}: bb/tb = {bbv/tbv:.2f}  (tb={tbv:.0f}, bb={bbv:.0f})")
P("")

# derived per-dispatch at B=64 for context
P("4. DERIVED (arithmetic over section 2, no new measurement):")
for arm in ARMS:
    v = pooled(arm, 64, sum128)
    P(f"   arm {arm} B=64 (sum,128,16): bracket {v:.0f} ticks = {v*52.083/1000:.1f} us per 64-dispatch bracket; per-dispatch {v/64:.1f} ticks")
b1 = pooled("tb", 1, sum128)
P(f"   arm tb B=1 (sum,128,16): bracket {b1:.0f} ticks = {b1*52.083/1000:.2f} us; host_ns median {pooled_host('tb',1,sum128):.0f} ns (the undercount scale)")
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
P("   isolated single-dispatch timing; anything off this host.")

text = "\n".join(out) + "\n"
open(os.path.join(HERE, "publication-s5.txt"), "w").write(text)
print(text)
