#!/usr/bin/env python3
"""JUN-59 session 28 analysis -- THE (1024,4033) ANCHOR-CLASS RECURRENCE
READ (the (1024,4033) knob pair's THIRD reading at n=253,906, B=3, plus
its same-ratio twin (2048,8066)'s SECOND reading).

Route (frozen in protocol.txt section 6): this script parses ONLY the 12
committed run logs in its own directory (run-<tag>-r<R>.txt) and writes
publication-s28.txt. No other input. Deterministic: running it twice
yields byte-identical publication-s28.txt (checked by diff after the
recorded run).

Cross-session reference values are frozen in protocol.txt section 3 and
embedded below as named constants (committed controls, the (1024,4033)
pair's two prior readings session-26 mid / session-27 hi, the
(2048,8066) pair's one prior reading session-26 eq3); they are
comparison values only and never this session's measurements.
"""
import re, sys, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

# tag -> (BATCH, WORK_MUL, NDIV), protocol.txt section 0 arm table (4 rows = 12 logs)
ARMS = [("c2", 2, 1, 1), ("hi", 3, 1024, 4033), ("tw", 3, 2048, 8066), ("c8", 8, 1, 1)]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMW = {a[0]: a[2] for a in ARMS}
ARMD = {a[0]: a[3] for a in ARMS}
RUNS = [1, 2, 3]
N_BASE = 1000003

# committed control anchors (comparison of committed values only)
COMMITTED = {"c2": 31, "c8": 32915}
COMMITTED_SRC = {"c2": "sessions 1-27 floor band 31..32",
                 "c8": "session 4 pooled median"}
# the (1024,4033) pair's TWO prior readings (protocol section 3, quote-only L7)
HI_S26 = 1129       # session 26 mid, class CAPTURED, 18-cell min 1,001
HI_S26_CLASS = "CAPTURED"
HI_S26_MIN = 1001
HI_S27 = 1132       # session 27 hi, class INTERMEDIATE/MIXED, 18-cell min 976
HI_S27_CLASS = "INTERMEDIATE/MIXED"
HI_S27_MIN = 976
# the (2048,8066) pair's ONE prior reading
TW_S26 = 1145       # session 26 eq3, class INTERMEDIATE/MIXED, 18-cell min 985
TW_S26_CLASS = "INTERMEDIATE/MIXED"
TW_S26_MIN = 985
# session-26/27 host_ns at (sum,128,S=16) (quote-only)
HOSTNS = {"c2": (680499, 672684), "hi": (309848, 310008), "tw": (310509, None), "c8": (2380500, 2397482)}
HOSTNS_SRC = {"c2": "session-26 / session-27", "hi": "session-26 mid / session-27 hi",
              "tw": "session-26 eq3", "c8": "session-26 / session-27"}

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
P("JUN-59 session 28 -- THE (1024,4033) ANCHOR-CLASS RECURRENCE READ")
P("(the (1024,4033) knob pair's THIRD reading at n=253,906 =")
P("(1,000,003*1024)//4033, B=3 -- and its same-ratio twin (2048,8066)'s")
P("SECOND reading), publication")
P("Produced ONLY by analysis-s28.py over the 12 committed run logs in this")
P("directory (run-<tag>-r<R>.txt); protocol.txt was frozen before the")
P("first run (freeze stamp 2026-10-27T22:41:14Z). Arms = binary")
P("compile-time (BATCH, WORK_MUL, NDIV); n = (1,000,003*WORK_MUL)/NDIV")
P("(integer floor). hi re-runs the (1024,4033) knob pair whose two prior")
P("cross-session readings are session 26's mid (1,129 CAPTURED, 18-cell")
P("min 1,001) and session 27's hi (1,132 INTERMEDIATE/MIXED, min 976) at")
P("a byte-identical rebuilt binary -- the named cross-session class flip")
P("at the frozen 1000-tick boundary; tw re-runs the same-ratio pair")
P("(2048,8066) (session 26's eq3, 1,145 INTERMEDIATE/MIXED, min 985).")
P("c2/c8 are the archived environment controls. ZERO derivation this")
P("session: the instrument is session 27's committed NDIV-derived source")
P("byte-identical (digest a5e539f0... -- derivation-census-s28.txt); the")
P("a-set manifest runs the ARCHIVED measured spv (16-digest corpus).")
P("The row question (protocol section 0): AT FIXED n=253,906 AND B=3,")
P("DOES THE (1024,4033) PAIR'S CLASS FLIP (CAPTURED -> INTERMEDIATE/MIXED")
P("AT THE FROZEN 1000-TICK BOUNDARY) RECUR IN A THIRD SESSION? -- hi")
P("CAPTURED -> the session-27 flip did NOT recur (reading sequence")
P("CAPTURED / MIXED / CAPTURED); hi INTERMEDIATE/MIXED -> the flip RECURS")
P("(two MIXED readings running after one CAPTURED); hi FLOOR is a")
P("pre-named non-monotone contradiction and is not resolved here. NO")
P("BRACKET NARROWING IS CLAIMED IN ANY BRANCH (L5): this session's axis")
P("is the anchor class, not the cut. 1 tick = timestampPeriod = 52.083 ns.")
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

P("1. INTEGRITY (computed over the 12 logs):")
P(f"   runs parsed: 12 (4 arms x 3 runs); cell map identical across runs: {cell_keys is not None and not any('CELL MAP' in i for i in integrity)}")
P(f"   headers byte-identical across all runs outside the # n= knob line: {header_ok}")
P(f"   header batch=/work_mul=/ndiv= == run's (B,WM,NDIV) and n == (1,000,003*WM)//NDIV; every SAMPLE batch=/work_mul=/ndiv= == (B,WM,NDIV): {knob_field_ok}")
P(f"   every CELL spv= name is an archived .emitted.spv (no .iter -- the corpus is byte-identical this session): {spv_identity_ok}")
P(f"   SAMPLE lines: 450 per run (18 ok cells x 25 rounds) in 12/12 runs: {sample_counts_ok}")
P(f"   VERIFY mismatch total over all runs: {verify_mismatch_total} (per-arm: "
  + ", ".join(f"{t}={verify_mismatch_by_arm[t]}" for t in TAGS)
  + ") -- bit-exact correctness re-check inside every run; frozen INVALIDATION criterion (protocol section 4): >0 in any run makes that run DEFECTIVE and the arm INVALID")
P(f"   forcing reality (pipeline-ok cell-runs where probe_size==forced and probe_nsub==wg/forced): {forcing_ok}/{forcing_total}")
P(f"   S=8 cells fail-closed (pipeline=FAIL, forced=8): {s8_fail} cell-runs (6 per run x 12 runs = 72 expected)")
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
P("   arm  B  WM   NDIV    n        total-nominal  (sum,128,16)   run-median band    min..max over 18 cells   host_ns")
for tag in TAGS:
    b, wm, dd = ARMB[tag], ARMW[tag], ARMD[tag]
    n = (N_BASE * wm) // dd
    vals = [pooled(tag, k) for k in ok_cells]
    v16 = pooled(tag, sum128)
    rms = run_medians(tag, sum128)
    hn = pooled_host(tag, sum128)
    tot = b * n / N_BASE
    P(f"   {tag}  {b}  {wm:<5} {dd:<6} {n:>8}  {tot:>12.6f}  {v16:>10.0f}     {min(rms):>8.0f}..{max(rms):<8.0f}  {min(vals):>8.0f}..{max(vals):<8.0f}  {hn:>9.0f}")
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
P("   ARCHIVED spv bytes through the byte-identical session-28 instrument,")
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

# C2 the anchor-class recurrence read (the (1024,4033) pair's third reading)
vhi = pooled("hi", sum128)
hi_min = min(pooled("hi", k) for k in ok_cells)
hi_num_s26 = abs(vhi - HI_S26) <= 0.05 * HI_S26
hi_num_s27 = abs(vhi - HI_S27) <= 0.05 * HI_S27
hi_num_ok = hi_num_s26 and hi_num_s27
c2_letter = None
P("   C2 ANCHOR-CLASS RECURRENCE (hi is the (1024,4033) knob pair's THIRD")
P("   reading at n=253,906, B=3 -- rebuilt binary BYTE-IDENTICAL to session")
P("   26's anv-bb-mid / session 27's anv-bb-hi (a6c31b6c...)")
P("   -- build-census-s28.txt; the pair's SECOND cross-session rebuild):")
P(f"     hi (sum,128,16) pooled median {vhi:.0f} within +/-5% of BOTH session-26's {HI_S26} and session-27's {HI_S27}: {hi_num_ok} (vs s26: {hi_num_s26}; vs s27: {hi_num_s27})")
P(f"     hi class {CLASS['hi']} (session-26 class {HI_S26_CLASS} min {HI_S26_MIN}; session-27 class {HI_S27_CLASS} min {HI_S27_MIN})")
P(f"     hi 18-cell min..max {hi_min:.0f}..{max(pooled('hi', k) for k in ok_cells):.0f}")
P(f"     NAMED, NOT HIDDEN: ONE session adds ONE reading -- the recurrence RATE is a")
P(f"     multi-session quantity and one more point does not close it; this session names")
P(f"     what its reading IS and does not extrapolate.")
if CLASS["hi"] == "CAPTURED" and hi_num_ok:
    c2_letter = "(a)"
    P("     VERDICT: branch (a) HI-CAPTURED -- the session-27 flip did NOT")
    P("     recur this session; the reading sequence at byte-identical")
    P("     binaries is CAPTURED / INTERMEDIATE/MIXED / CAPTURED.")
elif CLASS["hi"] == "INTERMEDIATE/MIXED" and hi_num_ok:
    c2_letter = "(b)"
    P("     VERDICT: branch (b) HI-INTERMEDIATE -- the flip RECURS: the")
    P("     reading sequence at byte-identical binaries is CAPTURED /")
    P("     INTERMEDIATE/MIXED / INTERMEDIATE/MIXED.")
elif CLASS["hi"] == "FLOOR" or not hi_num_ok:
    c2_letter = "(c)"
    P("     VERDICT: branch (c) -- pre-named contradiction / out-of-band")
    P("     reading (hi class FLOOR, or the pooled median outside +/-5% of")
    P("     both prior readings); measured content, NOT resolved here.")
P("")

# C3 the pair-representation check (tw (2048,8066) vs hi (1024,4033) at identical n and B)
vtw = pooled("tw", sum128)
tw_min = min(pooled("tw", k) for k in ok_cells)
c3_num_ok = abs(vtw - vhi) <= 0.05 * vhi
c3_ok = CLASS["tw"] == CLASS["hi"] and c3_num_ok
P("   C3 PAIR-REPRESENTATION CHECK (tw is the (2048,8066) pair at")
P("   n = 253,906 == hi's grid and B=3 -- the same ratio 1024/4033 in a")
P("   different (WORK_MUL,NDIV) representation; both knob pairs OLD,")
P("   protocol L8; NAMED, NOT HIDDEN: this is the SAME grid and SAME")
P("   pair-pair that session 26's C3 fired (b) on (min 1,001 vs 985 at")
P("   overlapping medians); the scoreboard after this session reads:")
P("   s24 (b) SPLIT, s25 (a) AGREE, s26 (b) SPLIT, s27 (a) AGREE, s28")
P("   (measured here); threshold-artifact-vs-representation UNRESOLVED:")
P(f"     tw class {CLASS['tw']} == hi class {CLASS['hi']}: {CLASS['tw'] == CLASS['hi']}")
P(f"     tw (sum,128,16) pooled median {vtw:.0f} within +/-5% of hi {vhi:.0f}: {c3_num_ok}")
P(f"     tw 18-cell min..max {tw_min:.0f}..{max(pooled('tw', k) for k in ok_cells):.0f}")
if c3_ok:
    P("     VERDICT: branch (a) -- at this grid the same-ratio")
    P("     representation (2048,8066) is class-identical to (1024,4033)")
    P("     (MEASURED at this one grid point and B only; nothing is")
    P("     assumed for any other pair beyond the source reading that")
    P("     N_ELEMENTS is the only knob-derived quantity -- protocol L8).")
else:
    P("     VERDICT: branch (b) -- the same-ratio representation matters at")
    P("     this grid; the contradiction stands as measured content, is NOT")
    P("     resolved here.")
P("")

# W1 the recurrence question
P("   W1 THE RECURRENCE QUESTION (the (1024,4033) pair's three")
P("   cross-session readings at byte-identical binaries and what this")
P("   session's reading means for the frozen flip bracket (252,604,")
P("   253,906] -- C1/C2 govern):")
P(f"     reading 1 (session 26 mid):  {HI_S26} {HI_S26_CLASS} (18-cell min {HI_S26_MIN}) [quote-only L7]")
P(f"     reading 2 (session 27 hi):   {HI_S27} {HI_S27_CLASS} (18-cell min {HI_S27_MIN}) [quote-only L7]")
P(f"     reading 3 (THIS session hi): {vhi:.0f} {CLASS['hi']} (18-cell min {hi_min:.0f}) [MEASURED HERE]")
w1 = None
if not c1_ok or c2_letter == "(c)":
    w1 = "(d)"
    P("     VERDICT: branch (d) FLAGGED -- C1 fired (b) or C2 fired (c);")
    P("     no recurrence reading is evaluable from this session.")
elif c2_letter == "(a)":
    w1 = "(a)"
    P("     VERDICT: branch (a) HI-CAPTURED -- the reading sequence is")
    P("     CAPTURED / MIXED / CAPTURED; the session-27 flip did NOT recur;")
    P("     the anchor-class question is NOT settled (the readings disagree")
    P("     across sessions) and NO bracket narrowing is claimed -- the flip")
    P("     location stays inside (252,604, 253,906]. ONE session; L2 binds;")
    P("     L5 no interpolation; NO causal mechanism is claimed or measured.")
elif c2_letter == "(b)":
    w1 = "(b)"
    P("     VERDICT: branch (b) HI-INTERMEDIATE -- the flip RECURS: the")
    P("     reading sequence is CAPTURED / MIXED / MIXED at byte-identical")
    P("     binaries; the anchor's class is UNSTABLE across sessions at the")
    P("     frozen 1000-tick boundary (two flips observed in three readings)")
    P("     and NO bracket narrowing is claimed. ONE session; L2 binds; L5")
    P("     no interpolation; NO causal mechanism is claimed or measured.")
P("")

# W2 the B=3 class-vs-per-dispatch-work row (descriptive)
P("   W2 (pre-registered, descriptive) THE B=3 CLASS-VS-PER-DISPATCH-")
P("   WORK ROW: this session adds NO new grid point -- it re-reads")
P("   253,906, which now carries THREE readings (the committed points")
P("   QUOTE-ONLY L7; NO interpolation (L5); class granularity only;")
P("   * = the session-26 reading carries its C3 (b) caveat):")
P("")
B3ROW = [("1/8", 125000, 599, "INTERMEDIATE/MIXED", "session 18"),
         ("1/4", 250000, 1140, "INTERMEDIATE/MIXED", "session 19"),
         ("0.2526032", 252604, 1153, "INTERMEDIATE/MIXED", "session 25"),
         ("0.2532542", 253255, 1136, "INTERMEDIATE/MIXED", "session 27"),
         ("0.2552072", 255208, 1166, "CAPTURED", "session 24"),
         ("0.2604162", 260417, 1186, "CAPTURED", "session 23"),
         ("0.2708332", 270834, 1224, "CAPTURED", "session 22"),
         ("0.2916657", 291667, 1330, "CAPTURED", "session 21"),
         ("1/3", 333334, 1578, "CAPTURED", "session 17"),
         ("1/2", 500001, 2739, "CAPTURED", "session 20"),
         ("1.0", 1000003, 5520, "CAPTURED", "sessions 7/16")]
P("     n          work-unit     ticks  class                source")
_inserted = False
for lbl, n, ticks, cls, src in B3ROW:
    if n > 253255 and not _inserted:
        P(f"     253906     0.2539052     {HI_S26:>5}  {'CAPTURED*':<20} session 26 (quote-only)")
        P(f"     253906     0.2539052     {HI_S27:>5}  {HI_S27_CLASS:<20} session 27 (quote-only)")
        P(f"     253906     0.2539052     {vhi:>5.0f}  {CLASS['hi']:<20} THIS SESSION (the recurrence read)")
        _inserted = True
    P(f"     {n:<10} {lbl:<13} {ticks:>5}  {cls:<20} {src} (quote-only)")
P("")

# W3 the paired equal-grid comparisons (descriptive)
P("   W3 (pre-registered, descriptive) THE PAIRED EQUAL-GRID COMPARISONS:")
P(f"     (i) hi vs tw (identical n=253,906 and B=3; differ only in the")
P(f"         (WORK_MUL,NDIV) representation (1024,4033) vs (2048,8066)):")
P(f"         {vhi:.0f} vs {vtw:.0f} at (sum,128,16); classes {CLASS['hi']} vs {CLASS['tw']};")
P(f"         18-cell minima {hi_min:.0f} vs {tw_min:.0f}")
P(f"     (ii) the (1024,4033) pair's three readings against each other")
P(f"         (identical knob triple and byte-identical binaries; differ")
P(f"         only in session): {HI_S26} (s26, min {HI_S26_MIN}) / {HI_S27} (s27, min {HI_S27_MIN}) /"
  f" {vhi:.0f} (s28, min {hi_min:.0f});")
P(f"         classes {HI_S26_CLASS} / {HI_S27_CLASS} / {CLASS['hi']}")
P("")

# X1 host_ns (descriptive)
P("   X1 (descriptive, host_ns at (sum,128,S=16)):")
hn = {t: pooled_host(t, sum128) for t in TAGS}
P("     " + ", ".join(f"{t} {hn[t]:.0f}" for t in TAGS))
for t in TAGS:
    prior = HOSTNS[t]
    comps = []
    if prior[0] is not None:
        comps.append(f"{hn[t]/prior[0]:.3f}x session-26's ({prior[0]:,})")
    if prior[1] is not None:
        comps.append(f"{hn[t]/prior[1]:.3f}x session-27's ({prior[1]:,})")
    P(f"     {t} {hn[t]:.0f} = " + "; ".join(comps) + f" -- {HOSTNS_SRC[t]} same-knob")
P("     host_ns is the HOST-side proxy (L3), not a C criterion; any")
P("     excursion is NAMED, NOT HIDDEN and its cause is UNMEASURED.")
P("")

P("4. VERDICT SUMMARY: C1 (a)={0}; C2 {1}; C3 (a)={2}; W1 {3}.".format(
    c1_ok, c2_letter, c3_ok, w1))
P("   The named-hypothesis discrimination of the row question is as W1")
P("   states; WHY is UNMEASURED and NO causal mechanism is claimed.")

with open(os.path.join(HERE, "publication-s28.txt"), "w") as f:
    f.write("\n".join(out) + "\n")
