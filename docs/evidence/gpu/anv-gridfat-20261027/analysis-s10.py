#!/usr/bin/env python3
"""JUN-59 session 10 analysis -- GRID x FATNESS INTERACTION (the joint knob
at B=2).

Route (frozen in protocol.txt section 6): this script parses ONLY the 15
committed run logs in its own directory (run-<tag>-r<R>.txt) and writes
publication-s10.txt. No other input. Deterministic: running it twice yields
byte-identical publication-s10.txt (checked by diff after the recorded run).
"""
import re, sys, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

# tag -> (BATCH, WORK_MUL, shader set), protocol.txt section 2
ARMS = [("c2", 2, 1, "a"), ("c8", 8, 1, "a"), ("g8", 2, 8, "a"),
        ("f8", 2, 1, "i8"), ("gf", 2, 8, "i8")]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMM = {a[0]: a[2] for a in ARMS}
ARMSET = {a[0]: a[3] for a in ARMS}
SET_SUF = {"a": ".emitted.spv", "i8": ".emitted.iter8.spv"}
RUNS = [1, 2, 3]
N_BASE = 1000003

# committed anchors (comparison of committed numbers only)
COMMITTED = {"c2": 31, "c8": 32915}
COMMITTED_SRC = {"c2": "sessions 1-9 floor", "c8": "session 4 pooled median"}
KNOB_CTRL_SRC = {"g8": "session 8 committed b2m8: FLOOR (31..32 band)",
                 "f8": "session 9 committed f8b2: FLOOR (31..32 band)"}

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
P("JUN-59 session 10 -- GRID x FATNESS INTERACTION (the joint knob at B=2), publication")
P("Produced ONLY by analysis-s10.py over the 15 committed run logs in this")
P("directory (run-<tag>-r<R>.txt); protocol.txt was frozen before the")
P("first run. Arms = (binary compile-time BATCH x WORK_MUL, shader set):")
P("the a-set runs the ARCHIVED measured spv (16-digest corpus), the i8-set")
P("runs the ITERMUL=8 derived spv (session 9's committed 3-line derivation,")
P("byte-reused and re-verified this session -- shader-reuse-census.txt; the")
P("rebuilt spv are byte-identical to session 9's build). The instrument is")
P("the byte-identical session-8 snapshot (no C edit; all 3 binaries byte-")
P("identical to session 8's same-flag binaries).")
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
P(f"   every CELL spv= name carries its arm's shader-set suffix (a-set: archived .emitted.spv, no .iter; i8-set: .emitted.iter8.spv): {spv_identity_ok}")
P(f"   SAMPLE lines: 450 per run (18 ok cells x 25 rounds) in 15/15 runs: {sample_counts_ok}")
P(f"   VERIFY mismatch total over all runs: {verify_mismatch_total} (bit-exact correctness re-check, inside every run -- the ITERMUL loop must not change the stored value, at any WORK_MUL)")
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
    ii = 8 if ARMSET[tag] == "i8" else 1
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
    ii = 8 if ARMSET[tag] == "i8" else 1
    P(f"   class {tag} (B={b}, M={mm_}, I={ii}, set={ARMSET[tag]}, {b*mm_*ii} nominal units): {CLASS[tag]}")
P("")

# C1 first (prerequisite; X1 depends on it)
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
    P("     C2 and X1-X2 are evaluated against the row question.")
else:
    P("     VERDICT: branch (b) replication discrepancy (bearing on the")
    P("     environment, not the derivation -- the a-set uses no derived")
    P("     bytes); X1 interpretation is flagged; cause UNMEASURED.")
P("")

# C2 (prerequisite: the two knobs at their own committed readings)
c2_parts = []
c2_g8_ok = CLASS["g8"] == "FLOOR"
c2_parts.append(f"g8 satisfies FLOOR ({KNOB_CTRL_SRC['g8']}): {c2_g8_ok}")
c2_f8_ok = CLASS["f8"] == "FLOOR"
c2_parts.append(f"f8 satisfies FLOOR ({KNOB_CTRL_SRC['f8']}): {c2_f8_ok}")
c2_ok = c2_g8_ok and c2_f8_ok
P("   C2 KNOB CONTROL REPLICATION (the two knobs at their single-knob")
P("   committed readings, re-run together in this session's environment):")
for s in c2_parts:
    P(f"     {s}")
if c2_ok:
    P("     VERDICT: branch (a) both knobs are pinned at their single-knob")
    P("     readings; gf is interpreted against them.")
else:
    P("     VERDICT: branch (b) a knob control moved (cause UNMEASURED;")
    P("     X1 interpretation flagged).")
P("")

# X1 (the row question)
P("   X1 JOINT DOSE AT B=2 (the row question): the class of gf above")
P("   (B=2, M=8 grid x I=8 fat workgroups = 128 nominal work units inside")
P("   one 2-dispatch bracket).")
if not c1_ok or not c2_ok:
    P("     VERDICT: interpretation FLAGGED by the C1/C2 discrepancy; the")
    P("     class assignments above stand as measured content.")
elif CLASS["gf"] == "FLOOR":
    P("     VERDICT: branch (a) -- gf is FLOOR while the c8 control (8")
    P("     nominal units, 8 dispatches) is CAPTURED: the capture at B=2 is")
    P("     NOT reachable even by the JOINT grid x fatness dose (128 nominal")
    P("     units, 16x the joint dose either single knob reached at B=2 in")
    P("     sessions 8/9 and 64x the captured control's nominal 8). With")
    P("     session 8 (grid axis alone, cost-realized, unreachable) and")
    P("     session 9 (fatness axis alone, nominal, unreachable), the capture")
    P("     is not a total-work threshold on any knob combination tested to")
    P("     date; dispatch count stays implicated. Observable only; NO")
    P("     causal mechanism claimed or measured.")
elif CLASS["gf"] == "CAPTURED":
    P("     VERDICT: branch (b) -- the joint dose at B=2 is CAPTURED: the")
    P("     capture CAN be driven by combined grid + per-workgroup work at")
    P("     fixed B=2 where neither knob alone reached it at up to 8x; the")
    P("     2->3 onset step is a work-dose threshold on the joint knob.")
    P("     Observable only; NO causal mechanism claimed or measured.")
else:
    P("     VERDICT: branch (c) -- INTERMEDIATE/MIXED at B=2 under the joint")
    P("     dose: the joint-dose answer is cell-quantified in section 2;")
    P("     mechanism UNMEASURED.")
P("")

# X2 realization
P("   X2 REALIZATION (descriptive, computed from section 2's host_ns values,")
P("   NO new measurement and NO linearity claim): the NOMINAL unit count is")
P("   a definition, not a cost claim. Realized host-time factors at")
P("   (sum,128,S=16), this session's own runs:")
h_c2 = pooled_host("c2", sum128)
for tag, what in [("g8", "grid knob M=8 (nominal 8x per dispatch)"),
                  ("f8", "fatness knob I=8 (nominal 8x per workgroup)"),
                  ("gf", "JOINT M=8 x I=8 (nominal 64x per dispatch)")]:
    h = pooled_host(tag, sum128)
    P(f"     {tag}: host_ns {h:.0f} / c2 host_ns {h_c2:.0f} = {h/h_c2:.2f}x  [{what}]")
P(f"     joint-vs-single: gf/g8 = {pooled_host('gf', sum128)/pooled_host('g8', sum128):.2f}x,"
  f" gf/f8 = {pooled_host('gf', sum128)/pooled_host('f8', sum128):.2f}x")
P("     (comparison of committed numbers, not a new measurement: session 8")
P("     measured its M knob at 4.63x host growth for nominal 8x; session 9")
P("     measured its I knob at 1.14x..1.57x for nominal 3x/8x, marginal and")
P("     non-monotone.) Whatever the joint realization measures above, X1's")
P("     reading is NOMINAL and a genuinely cost-calibrated joint dose stays")
P("     UNMEASURED and named in section 6.")
P("")

P("4. DERIVED (arithmetic over section 2, no new measurement):")
for tag in TAGS:
    b, mm_ = ARMB[tag], ARMM[tag]
    ii = 8 if ARMSET[tag] == "i8" else 1
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
P("   or the onset location; WHY capture turns on where it does; the joint")
P("   knob's COST realization beyond the host_ns factors reported in X2 (the")
P("   nominal B*M*I unit count is a definition, not a claim); any genuinely")
P("   COST-CALIBRATED joint dose at B=2 (this session's gf is nominal-64x --")
P("   realized cost is whatever X2 reports); any codegen difference between")
P("   iter1/iter8 spv and the archived spv beyond the wrapper; any (M,I)")
P("   outside {(1,1),(8,1),(1,8),(8,8)}; M or I in {2..7,9+}; any B outside")
P("   {2,8}; B in {4,5,6,7} at any (M,I); any N>0; session 2's run-1 dip")
P("   cause; cross-day replication; S=8 timing; every W outside {128,256};")
P("   shape 2; BT ordering; any baseline-vs-variant sign; isolated")
P("   single-dispatch timing; non-empty barriers; anything off this host.")

text = "\n".join(out) + "\n"
open(os.path.join(HERE, "publication-s10.txt"), "w").write(text)
print(text)
