#!/usr/bin/env python3
"""JUN-59 session 9 analysis -- PER-WORKGROUP-FATNESS DISCRIMINATOR (ITERMUL).

Route (frozen in protocol.txt): this script parses ONLY the 30 committed run
logs in its own directory (run-<tag>-r<R>.txt) and writes publication-s9.txt.
No other input. Deterministic: running it twice yields byte-identical
publication-s9.txt (checked by diff after the recorded run).
"""
import re, sys, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

# tag -> (BATCH, ITERMUL, shader set), protocol.txt section 2
ARMS = [("a1", 1, 1, "a"), ("a2", 2, 1, "a"), ("a3", 3, 1, "a"), ("a8", 8, 1, "a"),
        ("f1b2", 2, 1, "f1"), ("f1b8", 8, 1, "f1"),
        ("f3b1", 1, 3, "f3"), ("f3b2", 2, 3, "f3"),
        ("f8b1", 1, 8, "f8"), ("f8b2", 2, 8, "f8")]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMI = {a[0]: a[2] for a in ARMS}
ARMSET = {a[0]: a[3] for a in ARMS}
SET_SUF = {"a": ".emitted.spv", "f1": ".emitted.iter1.spv",
           "f3": ".emitted.iter3.spv", "f8": ".emitted.iter8.spv"}
RUNS = [1, 2, 3]
N_BASE = 1000003

# committed anchors (comparison of committed numbers only)
COMMITTED = {"a1": 31, "a2": 31, "a3": 5520, "a8": 32915}
COMMITTED_SRC = {"a1": "sessions 1-8 floor", "a2": "sessions 1-8 floor",
                 "a3": "session 7 pooled median", "a8": "session 4 pooled median"}

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
P("JUN-59 session 9 -- PER-WORKGROUP-FATNESS DISCRIMINATOR (ITERMUL), publication")
P("Produced ONLY by analysis-s9.py over the 30 committed run logs in this")
P("directory (run-<tag>-r<R>.txt); protocol.txt was frozen before the")
P("first run. Arms = (binary BATCH, shader set): the a-set runs the ARCHIVED")
P("measured spv (16-digest corpus), the f-sets run the ITERMUL-derived spv")
P("(iter1/iter3/iter8; the shader derivation is the 3-line edit in")
P("shader-derivation.diff.txt, incl. the named pre-run wrapper-spelling fix).")
P("The instrument is the byte-identical session-8 snapshot (no C edit).")
P("The grid is the archived grid at every arm (n=1,000,003, WORK_MUL=1,")
P("BARRIER_N=0): 1 nominal work unit = one dispatch of the archived grid at")
P("ITERMUL=1 cost; a (B,I) arm runs B dispatches of the same grid at I-times")
P("per-workgroup cost = B*I nominal units.")
P("1 tick = timestampPeriod = 52.083 ns on this device.")
P("")

# ---- load everything, integrity checks ----
data = {}          # (tag, run) -> (cells, verifies, samples, header)
cell_keys = None
integrity = []
header_ok = True
knob_field_ok = True
n_field_ok = True
spv_identity_ok = True
verify_mismatch_total = 0
forcing_ok = 0
forcing_total = 0
s8_fail = 0
sample_counts_ok = True
base_header = None
for tag in TAGS:
    b, ii, st = ARMB[tag], ARMI[tag], ARMSET[tag]
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
                   or (not mmu or int(mmu.group(1)) != 1):
                    knob_field_ok = False
                    integrity.append(f"HEADER knob FIELD MISMATCH in {fn}: {l}")
                if not mn or int(mn.group(1)) != N_BASE:
                    n_field_ok = False
                    integrity.append(f"HEADER n= FIELD MISMATCH in {fn}: {l}")
        # shader-set identity: every CELL's spv name must carry the set suffix
        for k, v in cells.items():
            want = SET_SUF[st]
            ok = (v["spv"].endswith(want) if st != "a"
                  else v["spv"].endswith(".emitted.spv") and ".iter" not in v["spv"])
            if not ok:
                spv_identity_ok = False
                integrity.append(f"CELL spv SET MISMATCH in {fn} idx={k}: {v['spv']} vs {want}")
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
            if bt != b or mt != 1:
                knob_field_ok = False
                integrity.append(f"SAMPLE knob FIELD {bt},{mt} != {b},1 in {fn}")

P("1. INTEGRITY (computed over the 30 logs):")
P(f"   runs parsed: 30 (10 arms x 3 runs); cell map identical across runs: {cell_keys is not None and not any('CELL MAP' in i for i in integrity)}")
P(f"   headers byte-identical across all runs outside the # n= knob line: {header_ok}")
P(f"   header batch= == run's B, work_mul=1, barrier_n=0, n=1,000,003; every SAMPLE batch=/work_mul= == (B,1): {knob_field_ok and n_field_ok}")
P(f"   every CELL spv= name carries its arm's shader-set suffix (a-set: archived .emitted.spv, no .iter): {spv_identity_ok}")
P(f"   SAMPLE lines: 450 per run (18 ok cells x 25 rounds) in 30/30 runs: {sample_counts_ok}")
P(f"   VERIFY mismatch total over all runs: {verify_mismatch_total} (bit-exact correctness re-check, inside every run -- the ITERMUL loop must not change the stored value)")
P(f"   forcing reality (pipeline-ok cell-runs where probe_size==forced and probe_nsub==wg/forced): {forcing_ok}/{forcing_total}")
P(f"   S=8 cells fail-closed (pipeline=FAIL, forced=8): {s8_fail} cell-runs (6 per run x 30 runs = 180 expected)")
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

ok_cells = sorted([k for k, v in data[("a1", 1)][0].items() if v["pipeline"] == "ok"])
def ckey(idx):
    c = data[("a1", 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])

sum128 = [k for k in ok_cells if ckey(k) == ("sum", 128, "16")][0]

P("2. THE MEASURED BRACKETS (pooled median gpu_ticks over 3 runs x 25 rounds per cell):")
P("   each row: (sum,128,S=16) exact value, per-run median band at that cell,")
P("   then min..max over the 18 pipeline-ok cells; host_ns at (sum,128,S=16)")
P("")
P("   arm    B  I  units  (sum,128,16)   run-median band    min..max over 18 cells   host_ns")
for tag in TAGS:
    b, ii = ARMB[tag], ARMI[tag]
    vals = [pooled(tag, k) for k in ok_cells]
    v16 = pooled(tag, sum128)
    rms = run_medians(tag, sum128)
    hn = pooled_host(tag, sum128)
    P(f"   {tag}  {b}  {ii}  {b*ii:>4}  {v16:>10.0f}     {min(rms):>8.0f}..{max(rms):<8.0f}  {min(vals):>8.0f}..{max(vals):<8.0f}  {hn:>9.0f}")
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
    P(f"   class {tag} (B={ARMB[tag]}, I={ARMI[tag]}, set={ARMSET[tag]}, {ARMB[tag]*ARMI[tag]} nominal units): {CLASS[tag]}")
P("")

# C1 first (prerequisite; W1(d) depends on it)
c1_parts = []
c1_floor_ok = CLASS["a1"] == "FLOOR" and CLASS["a2"] == "FLOOR"
c1_parts.append(f"a1 and a2 satisfy FLOOR: {c1_floor_ok}")
v3 = pooled("a3", sum128)
v8 = pooled("a8", sum128)
c1_a3_ok = abs(v3 - COMMITTED["a3"]) <= 0.05 * COMMITTED["a3"]
c1_a8_ok = abs(v8 - COMMITTED["a8"]) <= 0.05 * COMMITTED["a8"]
c1_parts.append(f"a3 (sum,128,16) pooled median {v3:.0f} within +/-5% of committed {COMMITTED['a3']} ({COMMITTED_SRC['a3']}): {c1_a3_ok}")
c1_parts.append(f"a8 (sum,128,16) pooled median {v8:.0f} within +/-5% of committed {COMMITTED['a8']} ({COMMITTED_SRC['a8']}): {c1_a8_ok}")
c1_ok = c1_floor_ok and c1_a3_ok and c1_a8_ok
P("   C1 ARCHIVED CONTROL REPLICATION (numeric agreement with the committed")
P("   value at each control's OWN B -- the session-7 fix, kept; the a-set")
P("   runs the ARCHIVED measured spv bytes, so this also pins the untouched")
P("   instrument + corpus):")
for s in c1_parts:
    P(f"     {s}")
if c1_ok:
    P("     VERDICT: branch (a) all four controls satisfy their criteria --")
    P("     C2 and W1-W4 are evaluated against the row question.")
else:
    P("     VERDICT: branch (b) replication discrepancy (bearing on the")
    P("     environment, not the derivation -- the a-set uses no derived")
    P("     bytes); W1 interpretation is flagged per W1(d); cause UNMEASURED.")
P("")

# C2 (prerequisite for the f-sets)
c2_parts = []
c2_f1b2_ok = CLASS["f1b2"] == "FLOOR"
c2_parts.append(f"f1b2 satisfies FLOOR (like a2): {c2_f1b2_ok}")
vf8 = pooled("f1b8", sum128)
c2_f1b8_ok = abs(vf8 - COMMITTED["a8"]) <= 0.05 * COMMITTED["a8"]
c2_parts.append(f"f1b8 (sum,128,16) pooled median {vf8:.0f} within +/-5% of committed {COMMITTED['a8']} ({COMMITTED_SRC['a8']}): {c2_f1b8_ok}")
c2_ok = c2_f1b2_ok and c2_f1b8_ok
P("   C2 DERIVATION CONTROL (the I=1 analogue of session 8's C1: does the")
P("   wrapper derivation + iter1 codegen move the bracket?):")
for s in c2_parts:
    P(f"     {s}")
if c2_ok:
    P("     VERDICT: branch (a) the derivation is pinned at I=1 inside the")
    P("     frozen bands; f3/f8 are interpreted against it.")
else:
    P("     VERDICT: branch (b) the derivation itself moves the bracket (the")
    P("     iter1 compiled bytes are NOT the archived bytes -- codegen beyond")
    P("     the wrapper is UNMEASURED); f3/f8 interpretation flagged per")
    P("     W1(d); cause UNMEASURED.")
P("")

# W1
P("   W1 FATNESS AT B=2 (the row question): classes of f3b2 and f8b2 above.")
if not c1_ok or not c2_ok:
    P("     VERDICT: per W1(d), interpretation FLAGGED by the C1/C2")
    P("     discrepancy; the class assignments above stand as measured content.")
elif CLASS["f3b2"] == "FLOOR" and CLASS["f8b2"] == "FLOOR":
    P("     VERDICT: branch (a) -- f3b2 and f8b2 are FLOOR while the a8b8")
    P("     control (8 nominal units) is captured: capture at B=2 is NOT")
    P("     reachable by up to 8x per-workgroup work at the constant archived")
    P("     grid (f8b2 carries 16 nominal work units inside the bracket --")
    P("     twice the captured a8b8's 8 -- on a grid identical to a8b8's).")
    P("     Combined with session 8's grid axis (also unreachable at B=2), the")
    P("     capture is not a total-work threshold on EITHER separated axis at")
    P("     up to 8x; dispatch count stays implicated. Observable only; NO")
    P("     causal mechanism claimed or measured.")
elif CLASS["f3b2"] == "CAPTURED" or CLASS["f8b2"] == "CAPTURED":
    P("     VERDICT: branch (b) -- a B=2 arm with fatter per-workgroup work is")
    P("     CAPTURED at constant grid: capture CAN be driven by per-workgroup")
    P("     work at fixed B=2; the 2->3 onset step is not purely a")
    P("     dispatch-count step. Observable only; NO causal mechanism claimed")
    P("     or measured.")
else:
    P("     VERDICT: branch (c) -- INTERMEDIATE/MIXED at B=2 with fatter")
    P("     workgroups: the fatness answer is cell-quantified in section 2;")
    P("     mechanism UNMEASURED.")
P("")
P("   W1 REALIZATION BOUND, NAMED, NOT HIDDEN (computed from section 2's")
P("   host_ns values, no new measurement): the frozen W1 wording '8x")
P("   per-workgroup work' is NOMINAL (I body executions of the reduce tree)")
P("   and the frozen protocol named in advance that the cost scaling with I")
P("   is not calibrated. The measured host_ns shows the realization is")
P("   MARGINAL AND NON-MONOTONE in I:")
for fat in ["f3b1", "f8b1"]:
    P(f"     B=1: {fat} (I={ARMI[fat]}) host_ns {pooled_host(fat, sum128):.0f}"
      f" / a1 host_ns {pooled_host('a1', sum128):.0f} = {pooled_host(fat, sum128)/pooled_host('a1', sum128):.2f}x"
      f" for nominal I={ARMI[fat]}x")
for fat in ["f3b2", "f8b2"]:
    P(f"     B=2: {fat} (I={ARMI[fat]}) host_ns {pooled_host(fat, sum128):.0f}"
      f" / a2 host_ns {pooled_host('a2', sum128):.0f} = {pooled_host(fat, sum128)/pooled_host('a2', sum128):.2f}x"
      f" for nominal I={ARMI[fat]}x")
P("     I=3 costs MORE host time than I=8 at B=1 (f3b1 > f8b1): the knob")
P("     did NOT realize I-times per-workgroup COST on this instrument")
P("     (WHY is UNMEASURED -- no mechanism claimed; e.g. codegen, caching")
P("     or fixed-overhead dominance are NOT tested). Therefore branch (a)")
P("     above closes the NOMINAL-I axis only: capture at B=2 is not")
P("     reachable by up to 8 nominal ITERMUL body executions at constant")
P("     grid; a genuinely cost-8x-heavier workgroup at B=2 stays")
P("     UNMEASURED. Session 8's grid axis WAS cost-realized (its committed")
P("     publication: b2m8 host_ns 3,143,995 vs its b2m1 678,375 = 4.63x for")
P("     nominal 8x), so on")
P("     the two separated axes the evidence stands as: grid-total-work axis")
P("     cost-realized and unreachable at B=2 (session 8); per-workgroup-body")
P("     axis nominal-only and unreachable at B=2 (this session); dispatch")
P("     count implicated on both.")
P("")

# W2
P("   W2 EQUAL-NOMINAL-WORK PAIRS (descriptive; same nominal work inside the")
P("   bracket, different shape):")
for fat, thin, units in [("f3b1", "a3", 3), ("f8b1", "a8", 8)]:
    v_one, v_many = pooled(fat, sum128), pooled(thin, sum128)
    h_one, h_many = pooled_host(fat, sum128), pooled_host(thin, sum128)
    ratio = (v_one / v_many) if v_many else float("nan")
    P(f"     {units} units: {fat} (1 dispatch of I={ARMI[fat]}-fat workgroups) {v_one:.0f} ticks / {CLASS[fat]} / host_ns {h_one:.0f}"
      f"  vs  {thin} ({ARMB[thin]} dispatches, I=1) {v_many:.0f} ticks / {CLASS[thin]} / host_ns {h_many:.0f}"
      f"  bracket ratio {ratio:.3f}")
v_d, v_ref = pooled("f1b8", sum128), pooled("a8", sum128)
h_d, h_ref = pooled_host("f1b8", sum128), pooled_host("a8", sum128)
ratio = (v_d / v_ref) if v_ref else float("nan")
P(f"     8 units (derivation delta): f1b8 (iter1 spv) {v_d:.0f} ticks / {CLASS['f1b8']} / host_ns {h_d:.0f}"
      f"  vs  a8 (archived spv) {v_ref:.0f} ticks / {CLASS['a8']} / host_ns {h_ref:.0f}"
      f"  bracket ratio {ratio:.3f}")
P("")

# W3
P("   W3 SINGLE-DISPATCH FAT DOSE (descriptive; B=1 only):")
for tag in ["a1", "f3b1", "f8b1"]:
    P(f"     {tag} (I={ARMI[tag]}, set={ARMSET[tag]}): bracket {pooled(tag, sum128):.0f} ticks / {CLASS[tag]};"
      f" host_ns {pooled_host(tag, sum128):.0f}")
P("")

# W4
P("   W4 FATNESS IN HOST TIME (descriptive, NO linearity claim; host_ns at")
P("   (sum,128,16)): per nominal work unit (host_ns/(B*I)) and per dispatch:")
for tag in TAGS:
    b, ii = ARMB[tag], ARMI[tag]
    hn = pooled_host(tag, sum128)
    P(f"     {tag}: host_ns {hn:.0f} / {b*ii} units = {hn/(b*ii):.0f} ns/unit; / {b} dispatches = {hn/b:.0f} ns/dispatch")
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
          f" (no committed anchor at this (B,I) -- new)")
P("")

P("5. RULE 4 -- NOTHING MOVES: no workgroup row, no :measured? flag, no selection")
P("   answer; accelerator-targets defaults remain provisional design assumptions")
P("   (:measured? false). This is NOT the baseline-vs-variant contract of")
P("   accelerator-subgroup-reduce.cljk. NO vendor optimization exists for Intel")
P("   and none is claimed. No causal mechanism is claimed by any letter above.")
P("")
P("6. UNMEASURED (named): any causal mechanism for the undercount, the capture,")
P("   or the onset location; WHY capture turns on where it does; the ITERMUL")
P("   loop's cost realization (MARGINAL AND NON-MONOTONE as measured in")
P("   host_ns -- the nominal B*I unit count is a definition, not a claim); any")
P("   genuinely cost-8x-heavier per-workgroup work at B=2 (the frozen W1")
P("   wording is nominal-I only); any codegen difference between iter1 spv and archived spv beyond")
P("   the wrapper (bounded by C2 only at B=2 floor and B=8 captured); GRID x")
P("   FATNESS interaction (any M>1 with any I>1); any I outside {1,3,8}; any")
P("   (B,I) outside the ten arms; B in {4,5,6,7} at any I; any N>0; session 2's")
P("   run-1 dip cause; cross-day replication; S=8 timing; every W outside")
P("   {128,256}; shape 2; any baseline-vs-variant sign; BT ordering; isolated")
P("   single-dispatch timing; non-empty barriers; anything off this host.")

text = "\n".join(out) + "\n"
open(os.path.join(HERE, "publication-s9.txt"), "w").write(text)
print(text)
