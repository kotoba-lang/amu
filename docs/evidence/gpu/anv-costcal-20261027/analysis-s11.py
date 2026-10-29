#!/usr/bin/env python3
"""JUN-59 session 11 analysis -- COST-CALIBRATED JOINT DOSE (the vc-fatness
knob).

Route (frozen in protocol.txt section 6): this script parses ONLY the 15
committed run logs in its own directory (run-<tag>-r<R>.txt) and writes
publication-s11.txt. No other input. Deterministic: running it twice yields
byte-identical publication-s11.txt (checked by diff after the recorded run).
"""
import re, sys, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

# tag -> (BATCH, WORK_MUL, shader set), protocol.txt section 2
ARMS = [("c2", 2, 1, "a"), ("c8", 8, 1, "a"), ("g8", 2, 8, "a"),
        ("f8vc", 2, 1, "vc"), ("gfvc", 2, 8, "vc")]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMM = {a[0]: a[2] for a in ARMS}
ARMSET = {a[0]: a[3] for a in ARMS}
SET_SUF = {"a": ".emitted.spv", "vc": ".emitted.itervc8.spv"}
RUNS = [1, 2, 3]
N_BASE = 1000003

# committed anchors (comparison of committed numbers only)
COMMITTED = {"c2": 31, "c8": 32915}
COMMITTED_SRC = {"c2": "sessions 1-10 floor", "c8": "session 4 pooled median"}
KNOB_CTRL_SRC = {"g8": "sessions 8/10 committed b2m8: FLOOR (31..32 band)"}

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
P("JUN-59 session 11 -- COST-CALIBRATED JOINT DOSE (the vc-fatness knob), publication")
P("Produced ONLY by analysis-s11.py over the 15 committed run logs in this")
P("directory (run-<tag>-r<R>.txt); protocol.txt was frozen before the")
P("first run. Arms = (binary compile-time BATCH x WORK_MUL, shader set):")
P("the a-set runs the ARCHIVED measured spv (16-digest corpus), the vc-set")
P("runs the ITERMUL=8 + coherent-volatile derived spv (this session's")
P("derivation: session 9's committed iter8 sources + ONE memory-qualifier")
P("edit on the X buffer; two-level inverse check 6/6 -- derivation-census.txt.")
P("The instrument is the byte-identical session-8 snapshot (no C edit; all")
P("3 binaries byte-identical to session 8's same-flag binaries).")
P("1 nominal work unit = one dispatch of the archived grid at ITERMUL=1")
P("cost; an (M,I) arm at B runs B dispatches of an M-times grid (n =")
P("1,000,003*M) at I-times per-workgroup cost = B*M*I nominal units.")
P("1 tick = timestampPeriod = 52.083 ns on this device.")
P("")

# ---- load everything, integrity checks ----
data = {}          # (tag, run) -> (cells, verifies, samples, header)
cell_keys = None
integrity = []
header_ok = True
knob_field_ok = True
spv_identity_ok = True
verify_mismatch_total = 0
forcing_ok = 0
forcing_total = 0
s8_fail = 0
sample_counts_ok = True
base_header = None
for tag in TAGS:
    b, mm_, st = ARMB[tag], ARMM[tag], ARMSET[tag]
    for r in RUNS:
        fn = f"run-{tag}-r{r}.txt"
        cells, verifies, samples, header = load(os.path.join(HERE, fn))
        data[(tag, r)] = (cells, verifies, samples, header)
        keys = tuple(sorted((k, v["op"], v["wg"], v["forced"], v["pipeline"]) for k, v in cells.items()))
        if cell_keys is None:
            cell_keys = keys
        elif keys != cell_keys:
            integrity.append(f"CELL MAP MISMATCH in {fn}")
        # header identity: identical across everything except the "# n=" knob line
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
                   or (not mmu or int(mmu.group(1)) != mm_):
                    knob_field_ok = False
                    integrity.append(f"HEADER knob FIELD MISMATCH in {fn}: {l}")
                if not mn or int(mn.group(1)) != N_BASE * mm_:
                    knob_field_ok = False
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
            if bt != b or mt != mm_:
                knob_field_ok = False
                integrity.append(f"SAMPLE knob FIELD {bt},{mt} != {b},{mm_} in {fn}")

P("1. INTEGRITY (computed over the 15 logs):")
P(f"   runs parsed: 15 (5 arms x 3 runs); cell map identical across runs: {cell_keys is not None and not any('CELL MAP' in i for i in integrity)}")
P(f"   headers byte-identical across all runs outside the # n= knob line: {header_ok}")
P(f"   header batch=/work_mul= == run's (B,M), barrier_n=0, n=1,000,003*M; every SAMPLE batch=/work_mul= == (B,M): {knob_field_ok}")
P(f"   every CELL spv= name carries its arm's shader-set suffix (a-set: archived .emitted.spv, no .iter; vc-set: .emitted.itervc8.spv): {spv_identity_ok}")
P(f"   SAMPLE lines: 450 per run (18 ok cells x 25 rounds) in 15/15 runs: {sample_counts_ok}")
P(f"   VERIFY mismatch total over all runs: {verify_mismatch_total} (bit-exact correctness re-check, inside every run -- frozen INVALIDATION criterion: >0 in any run makes that arm's derivation DEFECTIVE and the arm INVALID)")
P(f"   forcing reality (pipeline-ok cell-runs where probe_size==forced and probe_nsub==wg/forced): {forcing_ok}/{forcing_total}")
P(f"   S=8 cells fail-closed (pipeline=FAIL, forced=8): {s8_fail} cell-runs (6 per run x 15 runs = 90 expected)")
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

ok_cells = sorted([k for k, v in data[("c2", 1)][0].items() if v["pipeline"] == "ok"])
def ckey(idx):
    c = data[("c2", 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])

sum128 = [k for k in ok_cells if ckey(k) == ("sum", 128, "16")][0]

P("2. THE MEASURED BRACKETS (pooled median gpu_ticks over 3 runs x 25 rounds per cell):")
P("   each row: (sum,128,S=16) exact value, per-run median band at that cell,")
P("   then min..max over the 18 pipeline-ok cells; host_ns at (sum,128,S=16)")
P("")
P("   arm    B  M  I  nominal  (sum,128,16)   run-median band    min..max over 18 cells   host_ns")
for tag in TAGS:
    b, mm_ = ARMB[tag], ARMM[tag]
    ii = 8 if ARMSET[tag] == "vc" else 1
    vals = [pooled(tag, k) for k in ok_cells]
    v16 = pooled(tag, sum128)
    rms = run_medians(tag, sum128)
    hn = pooled_host(tag, sum128)
    P(f"   {tag}  {b}  {mm_}  {ii}  {b*mm_*ii:>6}  {v16:>10.0f}     {min(rms):>8.0f}..{max(rms):<8.0f}  {min(vals):>8.0f}..{max(vals):<8.0f}  {hn:>9.0f}")
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
    b, mm_ = ARMB[tag], ARMM[tag]
    ii = 8 if ARMSET[tag] == "vc" else 1
    P(f"   class {tag} (B={b}, M={mm_}, I={ii}, set={ARMSET[tag]}, {b*mm_*ii} nominal units): {CLASS[tag]}")
P("")

# INVALIDATION check first (frozen): VERIFY mismatch makes affected arms INVALID
arms_invalid = verify_mismatch_total > 0
if arms_invalid:
    P("   INVALIDATION CRITERION FIRED (frozen): VERIFY mismatch > 0 -- the")
    P("   derivation is DEFECTIVE (a stored value changed); every vc-set arm")
    P("   is INVALID and no letter below is interpretable from it.")
    P("")

# C1 first (prerequisite; V1-K2 depend on it)
c1_parts = []
c1_c2_ok = CLASS["c2"] == "FLOOR"
c1_parts.append(f"c2 satisfies FLOOR: {c1_c2_ok}")
v8 = pooled("c8", sum128)
c1_c8_ok = abs(v8 - COMMITTED["c8"]) <= 0.05 * COMMITTED["c8"]
c1_parts.append(f"c8 (sum,128,16) pooled median {v8:.0f} within +/-5% of committed {COMMITTED['c8']} ({COMMITTED_SRC['c8']}): {c1_c8_ok}")
c1_ok = c1_c2_ok and c1_c8_ok
P("   C1 ARCHIVED CONTROL REPLICATION (numeric agreement with the committed")
P("   value at the control's OWN B -- the session-7 fix, kept; the a-set")
P("   runs the ARCHIVED measured spv bytes, so this also pins the untouched")
P("   instrument + corpus):")
for s in c1_parts:
    P(f"     {s}")
if c1_ok:
    P("     VERDICT: branch (a) both controls satisfy their criteria --")
    P("     C2 and V1-K2 are evaluated against the row question.")
else:
    P("     VERDICT: branch (b) replication discrepancy (bearing on the")
    P("     environment, not the derivation -- the a-set uses no derived")
    P("     bytes); V1-K2 interpretation is flagged; cause UNMEASURED.")
P("")

# C2 (prerequisite: the grid knob at its committed reading)
c2_parts = []
c2_g8_ok = CLASS["g8"] == "FLOOR"
c2_parts.append(f"g8 satisfies FLOOR ({KNOB_CTRL_SRC['g8']}): {c2_g8_ok}")
c2_ok = c2_g8_ok
P("   C2 GRID KNOB CONTROL REPLICATION (the M knob at its single-knob")
P("   committed reading, re-run in this session's environment):")
for s in c2_parts:
    P(f"     {s}")
if c2_ok:
    P("     VERDICT: branch (a) the grid knob is pinned at its committed")
    P("     reading; gfvc is interpreted against it.")
else:
    P("     VERDICT: branch (b) the knob control moved (cause UNMEASURED;")
    P("     interpretation flagged).")
P("")

# X2 realization values (needed by V1/K1 verdicts)
h_c2 = pooled_host("c2", sum128)
h_c8 = pooled_host("c8", sum128)
h_g8 = pooled_host("g8", sum128)
h_f8vc = pooled_host("f8vc", sum128)
h_gfvc = pooled_host("gfvc", sum128)
r_g8 = h_g8 / h_c2
r_f8vc = h_f8vc / h_c2
r_gfvc = h_gfvc / h_c2

# V1 (the derivation's design claim)
v1_ratio = r_f8vc
v1_ok = v1_ratio >= 3.0
P("   V1 VC-REALIZATION (the derivation's design claim; f8vc host_ns / c2")
P("   host_ns at (sum,128,S=16); criterion >= 3.0x frozen in advance --")
P("   session 9's non-vc I=8 realized 1.14x..1.57x and session 10's f8 1.18x,")
P("   so >= 3.0x separates a genuinely realized iterated-load cost from the")
P("   CSE'd/marginal band):")
P(f"     f8vc/c2 = {h_f8vc:.0f} / {h_c2:.0f} = {v1_ratio:.2f}x")
if arms_invalid:
    P("     VERDICT: NOT EVALUABLE (the INVALIDATION criterion fired).")
elif v1_ok:
    P("     VERDICT: branch (a) -- the vc-fatness knob is COST-REALIZING as")
    P("     designed; K1(ii) is evaluated and, with it, the cost-calibrated")
    P("     reading of K2.")
else:
    P("     VERDICT: branch (b) -- the vc derivation FAILED to realize cost")
    P("     (the measured factor is inside/near the CSE'd marginal band); the")
    P("     cost-calibrated joint dose stays UNMEASURED (named), the measured")
    P("     factors are reported, and K2 is read nominally only.")
P("")

# V2 (fatness-only class)
P("   V2 FATNESS-ONLY CLASS (the class of f8vc -- the qualifier alone at")
P("   B=2, M=1):")
if CLASS["f8vc"] == "FLOOR":
    P("     VERDICT: branch (a) -- f8vc is FLOOR: the qualifier alone at B=2")
    P("     does not reach the capture; consistent with the dispatch-count")
    P("     reading. Observable only; NO causal mechanism claimed.")
else:
    P(f"     VERDICT: branch (b) -- f8vc is {CLASS['f8vc']}: the qualifier")
    P("     alone moves the bracket class at B=2 (new observable; the classes")
    P("     stand as measured content; mechanism UNMEASURED).")
P("")

# K1 (cost calibration)
k1_i = v1_ok
k1_ii = h_gfvc >= 2 * h_c8
P("   K1 COST CALIBRATION (the joint dose's cost status, pre-registered:")
P("   gfvc is COST-CALIBRATED iff (i) V1 branch (a) AND (ii) gfvc host_ns")
P("   >= 2x the c8 control's host_ns in-session):")
P(f"     (i) V1 branch (a) fired: {k1_i}")
P(f"     (ii) gfvc host_ns {h_gfvc:.0f} >= 2 x c8 host_ns 2 x {h_c8:.0f} = {2*h_c8:.0f}: {k1_ii}")
k1_ok = k1_i and k1_ii and not arms_invalid
if arms_invalid:
    P("     VERDICT: NOT EVALUABLE (the INVALIDATION criterion fired).")
elif k1_ok:
    P("     VERDICT: branch (a) -- both hold: gfvc is read AT CALIBRATED COST")
    P("     in K2.")
else:
    P("     VERDICT: branch (b) -- the cost-calibrated dose stays UNMEASURED")
    P("     and named; K2 is read nominally only.")
P("")

# K2 (the row question)
P("   K2 THE ROW QUESTION (the class of gfvc: at fixed B=2, is the capture")
P("   reachable by the joint grid x fatness dose at COST-CALIBRATED")
P(f"   fatness; cost status per K1: {'CALIBRATED' if k1_ok else 'NOMINAL-ONLY'}):")
if not c1_ok or not c2_ok:
    P("     VERDICT: interpretation FLAGGED by the C1/C2 discrepancy; the")
    P("     class assignments above stand as measured content.")
elif arms_invalid:
    P("     VERDICT: NOT EVALUABLE (the INVALIDATION criterion fired).")
elif CLASS["gfvc"] == "FLOOR":
    P("     VERDICT: branch (a) -- gfvc is FLOOR while the c8 control (8")
    P("     nominal units, 8 dispatches) is CAPTURED: the capture at B=2 is")
    P("     NOT reachable even by the joint dose at cost-calibrated fatness.")
    if k1_ok:
        P(f"     On the realized-cost axis this closes the axis up to the")
        P(f"     measured gfvc/c2 factor ({r_gfvc:.2f}x c2 host_ns) at B=2.")
    P("     With sessions 8-10 the capture is not a total-work or total-cost")
    P("     threshold on any knob tested to date; dispatch count stays")
    P("     implicated. Observable only; NO causal mechanism claimed or")
    P("     measured.")
elif CLASS["gfvc"] == "CAPTURED":
    P("     VERDICT: branch (b) -- the joint dose at cost-calibrated fatness")
    P("     is CAPTURED at B=2: the capture IS reachable at calibrated cost;")
    P("     the 2->3 onset is a cost threshold that the nominal doses of")
    P("     sessions 8-10 never crossed. Observable only; NO causal")
    P("     mechanism claimed or measured.")
else:
    P("     VERDICT: branch (c) -- INTERMEDIATE/MIXED at B=2 under the")
    P("     cost-calibrated joint dose: cell-quantified in section 2;")
    P("     mechanism UNMEASURED.")
P("")

# X2 realization
P("   X2 REALIZATION (descriptive, computed from section 2's host_ns values,")
P("   NO new measurement and NO linearity claim): the NOMINAL unit count is")
P("   a definition, not a cost claim. Realized host-time factors at")
P("   (sum,128,S=16), this session's own runs:")
P(f"     g8: host_ns {h_g8:.0f} / c2 host_ns {h_c2:.0f} = {r_g8:.2f}x  [grid knob M=8 (nominal 8x per dispatch)]")
P(f"     f8vc: host_ns {h_f8vc:.0f} / c2 host_ns {h_c2:.0f} = {r_f8vc:.2f}x  [vc-fatness knob I=8 (nominal 8x per workgroup)]")
P(f"     gfvc: host_ns {h_gfvc:.0f} / c2 host_ns {h_c2:.0f} = {r_gfvc:.2f}x  [JOINT M=8 x I=8-vc (nominal 64x per dispatch)]")
P(f"     joint-vs-single: gfvc/g8 = {h_gfvc/h_g8:.2f}x, gfvc/f8vc = {h_gfvc/h_f8vc:.2f}x")
P("     (comparison of committed numbers, not a new measurement: session 8")
P("     measured its M knob at 4.63x host growth for nominal 8x; session 9")
P("     measured its NON-vc I knob at 1.14x..1.57x for nominal 3x/8x;")
P("     session 10 measured f8 1.18x, g8 5.55x, gf 5.92x. The named")
P("     limitation stands: host_ns is a HOST-side proxy; the GPU-side cost")
P("     inside a B=2 bracket is UNOBSERVABLE on this instrument.)")
P("")

P("4. DERIVED (arithmetic over section 2, no new measurement):")
for tag in TAGS:
    b, mm_ = ARMB[tag], ARMM[tag]
    ii = 8 if ARMSET[tag] == "vc" else 1
    v = pooled(tag, sum128)
    hn = pooled_host(tag, sum128)
    line = (f"   {tag}: bracket {v:.0f} ticks = {v*52.083/1000:.2f} us;"
            f" host_ns {hn:.0f}; {b*mm_*ii} nominal units")
    if tag in COMMITTED:
        d = (v - COMMITTED[tag]) / COMMITTED[tag] * 100
        line += f"; vs committed {COMMITTED[tag]} ({COMMITTED_SRC[tag]}): {d:+.2f}%"
    else:
        line += " (no committed anchor at this (M,I) -- new)"
    P(line)
P("")

P("5. RULE 4 -- NOTHING MOVES: no workgroup row, no :measured? flag, no selection")
P("   answer; accelerator-targets defaults remain provisional design assumptions")
P("   (:measured? false). This is NOT the baseline-vs-variant contract of")
P("   accelerator-subgroup-reduce.cljk. NO vendor optimization exists for Intel")
P("   and none is claimed. No causal mechanism is claimed by any letter above.")
P("")
P("6. UNMEASURED (named): any causal mechanism for the undercount, the capture,")
P("   or the onset location; WHY capture turns on where it does; the GPU-side")
P("   cost inside a B=2 bracket (unobservable on this instrument -- the named")
P("   limitation); why the vc qualifier realizes whatever V1 measures; any")
P("   genuinely cost-calibrated dose beyond the measured gfvc/c2 factor; any")
P("   codegen difference between the iter1/iter8/itervc8 spv and the archived")
P("   spv beyond the wrapper and qualifier; any (M,I,vc) outside the five")
P("   arms; M or I in {2..7,9+}; any B outside {2,8}; B in {4,5,6,7} at any")
P("   (M,I); any N>0; session 2's run-1 dip cause; cross-day replication;")
P("   S=8 timing; every W outside {128,256}; shape 2; BT ordering; any")
P("   baseline-vs-variant sign; isolated single-dispatch timing; non-empty")
P("   barriers; anything off this host.")

text = "\n".join(out) + "\n"
open(os.path.join(HERE, "publication-s11.txt"), "w").write(text)
print(text)
