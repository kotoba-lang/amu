#!/usr/bin/env python3
"""JUN-59 session 29 analysis -- THE WITHIN-SESSION BLOCK-VARIABILITY READ
OF THE (1024,4033) ANCHOR (four 3-run blocks of the (1024,4033) knob pair at
n=253,906, B=3 within ONE session, plus the archived controls c2/c8).

Route (frozen in protocol.txt section 6): this script parses ONLY the 18
committed run logs in its own directory (run-<tag>-r<R>.txt) and writes
publication-s29.txt. No other input. Deterministic: running it twice
yields byte-identical publication-s29.txt (checked by diff after the
recorded run).

Cross-session reference values are frozen in protocol.txt section 3 and
embedded below as named constants (committed controls and the
(1024,4033) pair's three cross-session readings session-26 mid /
session-27 hi / session-28 hi); they are comparison values only and never
this session's measurements.
"""
import re, sys, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

# tag -> (BATCH, WORK_MUL, NDIV, [runs]), protocol.txt section 0 arm table
ARMS = [("c2", 2, 1, 1, [1, 2, 3]),
        ("hi", 3, 1024, 4033, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]),
        ("c8", 8, 1, 1, [1, 2, 3])]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMW = {a[0]: a[2] for a in ARMS}
ARMD = {a[0]: a[3] for a in ARMS}
ARMR = {a[0]: a[4] for a in ARMS}
# blocks (frozen): a BLOCK is 3 fresh processes = the cross-session estimator unit
BLOCKS = [("A", [1, 2, 3]), ("B", [4, 5, 6]), ("C", [7, 8, 9]), ("D", [10, 11, 12])]
N_BASE = 1000003

# committed control anchors (comparison of committed values only)
COMMITTED = {"c2": 31, "c8": 32915}
COMMITTED_SRC = {"c2": "sessions 1-28 floor band 31..32",
                 "c8": "session 4 pooled median"}
# the (1024,4033) pair's THREE prior cross-session readings (protocol sec 3, quote-only L7)
HI_PRIOR = [(1129, "CAPTURED", 1001, "session 26 mid"),
            (1132, "INTERMEDIATE/MIXED", 976, "session 27 hi"),
            (1131, "INTERMEDIATE/MIXED", 991, "session 28 hi")]
# prior host_ns at (sum,128,S=16) (quote-only)
HOSTNS = {"c2": (680499, 672684, 678546), "hi": (309848, 310008, 309647),
          "c8": (2380500, 2397482, 3053605)}
HOSTNS_SRC = {"c2": "session-26 / session-27 / session-28",
              "hi": "session-26 mid / session-27 hi / session-28 hi",
              "c8": "session-26 / session-27 / session-28"}

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
P("JUN-59 session 29 -- THE WITHIN-SESSION BLOCK-VARIABILITY READ OF THE")
P("(1024,4033) ANCHOR (four 3-run blocks of the (1024,4033) knob pair at")
P("n=253,906 = (1,000,003*1024)//4033, B=3, ONE session, ONE binary --")
P("blocks A/B/C/D = hi r1-3 / r4-6 / r7-9 / r10-12 -- plus the archived")
P("controls c2/c8 bracketing the hi window), publication")
P("Produced ONLY by analysis-s29.py over the 18 committed run logs in this")
P("directory (run-<tag>-r<R>.txt); protocol.txt was frozen before the")
P("first run (freeze stamp 2026-10-27T23:09:19Z). Arms = binary")
P("compile-time (BATCH, WORK_MUL, NDIV); n = (1,000,003*WORK_MUL)/NDIV")
P("(integer floor). A BLOCK is 3 fresh processes pooled over 25 rounds")
P("per cell -- the same estimator unit every cross-session reading used.")
P("The (1024,4033) pair's three cross-session readings are session 26's")
P("mid (1,129 CAPTURED, 18-cell min 1,001), session 27's hi (1,132")
P("INTERMEDIATE/MIXED, min 976) and session 28's hi (1,131")
P("INTERMEDIATE/MIXED, min 991) at byte-identical rebuilt binaries -- the")
P("named cross-session class flip at the frozen 1000-tick boundary at a")
P("0.27% median span. The row question (protocol section 0): AT FIXED")
P("n=253,906 AND B=3 AND A BYTE-IDENTICAL BINARY, DO FOUR 3-RUN BLOCKS")
P("MEASURED WITHIN ONE SESSION AGREE ON THE FROZEN CLASS, OR DOES THE")
P("CLASS FLIP WITHIN THE SESSION? ZERO derivation this session: the")
P("instrument is session 28's committed NDIV-derived source byte-identical")
P("(digest a5e539f0... -- derivation-census-s29.txt); the a-set manifest")
P("runs the ARCHIVED measured spv (16-digest corpus). 1 tick =")
P("timestampPeriod = 52.083 ns.")
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
    for r in ARMR[tag]:
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

P("1. INTEGRITY (computed over the 18 logs):")
P(f"   runs parsed: 18 (c2 3 + hi 12 + c8 3); cell map identical across runs: {cell_keys is not None and not any('CELL MAP' in i for i in integrity)}")
P(f"   headers byte-identical across all runs outside the # n= knob line: {header_ok}")
P(f"   header batch=/work_mul=/ndiv= == run's (B,WM,NDIV) and n == (1,000,003*WM)//NDIV; every SAMPLE batch=/work_mul=/ndiv= == (B,WM,NDIV): {knob_field_ok}")
P(f"   every CELL spv= name is an archived .emitted.spv (no .iter -- the corpus is byte-identical this session): {spv_identity_ok}")
P(f"   SAMPLE lines: 450 per run (18 ok cells x 25 rounds) in 18/18 runs: {sample_counts_ok}")
P(f"   VERIFY mismatch total over all runs: {verify_mismatch_total} (per-arm: "
  + ", ".join(f"{t}={verify_mismatch_by_arm[t]}" for t in TAGS)
  + ") -- bit-exact correctness re-check inside every run; frozen INVALIDATION criterion (protocol section 4): >0 in any run makes that run DEFECTIVE and the arm INVALID")
P(f"   forcing reality (pipeline-ok cell-runs where probe_size==forced and probe_nsub==wg/forced): {forcing_ok}/{forcing_total}")
P(f"   S=8 cells fail-closed (pipeline=FAIL, forced=8): {s8_fail} cell-runs (6 per run x 18 runs = 108 expected)")
if integrity:
    for i in integrity:
        P(f"   !! {i}")
P("")

ok_cells = sorted([k for k, v in data[("c2", 1)][0].items() if v["pipeline"] == "ok"])

def ckey(idx):
    c = data[("c2", 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])

sum128 = [k for k in ok_cells if ckey(k) == ("sum", 128, "16")][0]

# ---- pooling helpers over an explicit run list ----
def pooled_runs(tag, idx, runs):
    xs = []
    for r in runs:
        cells, verifies, samples, header = data[(tag, r)]
        xs += [s[5] for s in samples if s[1] == idx]
    return med(xs)

def pooled_host_runs(tag, idx, runs):
    xs = []
    for r in runs:
        cells, verifies, samples, header = data[(tag, r)]
        xs += [s[8] for s in samples if s[1] == idx]
    return med(xs)

def block_class(tag, runs):
    vals = [pooled_runs(tag, k, runs) for k in ok_cells]
    if all(v <= 100 for v in vals):
        return "FLOOR", vals
    if all(v >= 1000 for v in vals):
        return "CAPTURED", vals
    return "INTERMEDIATE/MIXED", vals

def block_min(tag, runs):
    return min(pooled_runs(tag, k, runs) for k in ok_cells)

P("2. THE MEASURED BRACKETS (pooled median gpu_ticks; a BLOCK = 3 runs x")
P("   25 rounds per cell; hi-all pools all 12 runs and is a NAMED")
P("   DIFFERENT ESTIMATOR (12 runs, not the frozen 3-run unit)):")
P("   each row: (sum,128,S=16) exact value, then min..max over the 18")
P("   pipeline-ok cells; host_ns at (sum,128,S=16)")
P("")
P("   unit      B  WM   NDIV    n        total-nominal  (sum,128,16)  min..max over 18 cells   host_ns")
for tag in TAGS:
    b, wm, dd = ARMB[tag], ARMW[tag], ARMD[tag]
    n = (N_BASE * wm) // dd
    if tag == "hi":
        units = [(f"blk-{g}", rs) for g, rs in BLOCKS] + [("hi-all", ARMR["hi"])]
    else:
        units = [(f"{tag}", ARMR[tag])]
    for lbl, rs in units:
        vals = [pooled_runs(tag, k, rs) for k in ok_cells]
        v16 = pooled_runs(tag, sum128, rs)
        hn = pooled_host_runs(tag, sum128, rs)
        tot = b * n / N_BASE
        P(f"   {lbl:<9} {b}  {wm:<5} {dd:<6} {n:>8}  {tot:>12.6f}  {v16:>10.0f}  {min(vals):>8.0f}..{max(vals):<8.0f}  {hn:>9.0f}")
P("")

# ---- classification (protocol.txt section 4 thresholds) ----
CLASS = {}
BLOCKINFO = {}
for tag in TAGS:
    if tag == "hi":
        for g, rs in BLOCKS:
            cls, vals = block_class(tag, rs)
            BLOCKINFO[g] = dict(runs=rs, cls=cls, m=pooled_runs(tag, sum128, rs),
                                mn=min(vals), mx=max(vals),
                                hn=pooled_host_runs(tag, sum128, rs))
        cls, vals = block_class(tag, ARMR["hi"])
        CLASS["hi-all"] = cls
    else:
        cls, vals = block_class(tag, ARMR[tag])
        CLASS[tag] = cls
m_all = pooled_runs("hi", sum128, ARMR["hi"])

P("3. PRE-REGISTERED LETTERS (thresholds frozen in protocol.txt section 4:")
P("   FLOOR <= 100 ticks at all 18 cells; CAPTURED >= 1000 ticks at all 18;")
P("   anything else INTERMEDIATE/MIXED; a BLOCK = 3 fresh processes):")
P("")
for tag in TAGS:
    b, wm, dd = ARMB[tag], ARMW[tag], ARMD[tag]
    n = (N_BASE * wm) // dd
    if tag == "hi":
        for g, _ in BLOCKS:
            bi = BLOCKINFO[g]
            P(f"   class blk-{g} (runs {bi['runs']}, B=3, WM=1024, NDIV=4033, n={n}): {bi['cls']}  (sum,128,16) {bi['m']:.0f}  18-cell {bi['mn']:.0f}..{bi['mx']:.0f}")
        P(f"   class hi-all (12 runs pooled -- NAMED DIFFERENT ESTIMATOR, not the frozen unit): {CLASS['hi-all']}  (sum,128,16) {m_all:.0f}")
    else:
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
v8 = pooled_runs("c8", sum128, ARMR["c8"])
c1_c8_ok = abs(v8 - COMMITTED["c8"]) <= 0.05 * COMMITTED["c8"]
c1_parts.append(f"c8 (sum,128,16) pooled median {v8:.0f} within +/-5% of committed {COMMITTED['c8']} ({COMMITTED_SRC['c8']}): {c1_c8_ok}")
c1_ok = c1_c2_ok and c1_c8_ok
P("   C1 ARCHIVED CONTROL REPLICATION (numeric agreement with the committed")
P("   value at the control's OWN (B,WORK_MUL,NDIV) -- the a-set runs the")
P("   ARCHIVED spv bytes through the byte-identical session-29 instrument,")
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

# C2 within-session block-class stability
def in_band(m):
    conds = [abs(m - m_all) <= 0.05 * m_all]
    for p, _, _, _ in HI_PRIOR:
        conds.append(abs(m - p) <= 0.05 * p)
    return all(conds)

P("   C2 WITHIN-SESSION BLOCK-CLASS STABILITY (the four hi blocks of the")
P("   (1024,4033) pair at n=253,906, B=3 -- one binary (rebuilt")
P("   BYTE-IDENTICAL to session 26's anv-bb-mid / sessions 27/28's")
P("   anv-bb-hi, a6c31b6c... -- build-census-s29.txt), 12 fresh")
P("   processes; IN-BAND(m) := m within +/-5% of the 12-run pooled")
P("   median AND within +/-5% of each prior reading 1,129 / 1,132 / 1,131):")
bands = {}
for g, _ in BLOCKS:
    bi = BLOCKINFO[g]
    bands[g] = in_band(bi["m"])
    P(f"     blk-{g}: {bi['cls']:<20} (sum,128,16) {bi['m']:.0f}  18-cell min {bi['mn']:.0f}  IN-BAND {bands[g]}")
cls_set = sorted(set(BLOCKINFO[g]["cls"] for g, _ in BLOCKS))
all_inband = all(bands.values())
any_floor = any(BLOCKINFO[g]["cls"] == "FLOOR" for g, _ in BLOCKS)
c2_letter = None
if len(cls_set) == 1 and not any_floor and all_inband:
    c2_letter = "(a)"
    P("     VERDICT: branch (a) -- all four blocks classify the SAME (none")
    P("     FLOOR) and every block median is IN-BAND: the frozen class is")
    P("     STABLE within a session at block granularity, while the three")
    P("     cross-session readings flip at the frozen 1000-tick boundary.")
elif any_floor or not all_inband:
    c2_letter = "(c)"
    P("     VERDICT: branch (c) -- pre-named contradiction / out-of-band")
    P(f"     reading (any block FLOOR: {any_floor}; all medians in band: {all_inband});")
    P("     measured content, NOT resolved here.")
else:
    c2_letter = "(b)"
    P("     VERDICT: branch (b) -- the four blocks' classes are NOT all")
    P(f"     identical ({cls_set}; no FLOOR) at IN-BAND medians: the frozen")
    P("     class FLIPS WITHIN ONE SESSION at a byte-identical binary and")
    P("     identical knob triple at overlapping medians.")
P("     NAMED, NOT HIDDEN: four blocks give FOUR readings -- the")
P("     within-session block-variability of the class is measured HERE; no")
P("     flip rate is claimed (four blocks do not close a rate) and no")
P("     causal mechanism (thermal, scheduling, driver) is measured.")
P("")

# W1 the anchor-class question
P("   W1 THE ANCHOR-CLASS QUESTION (what the four blocks mean for")
P("   sessions 26-28's cross-session flip picture and for the frozen flip")
P("   bracket (252,604, 253,906] -- C1/C2 govern):")
P(f"     cross-session readings (quote-only L7): {HI_PRIOR[0][0]} {HI_PRIOR[0][1]} (min {HI_PRIOR[0][2]}, {HI_PRIOR[0][3]}) /")
P(f"       {HI_PRIOR[1][0]} {HI_PRIOR[1][1]} (min {HI_PRIOR[1][2]}, {HI_PRIOR[1][3]}) /")
P(f"       {HI_PRIOR[2][0]} {HI_PRIOR[2][1]} (min {HI_PRIOR[2][2]}, {HI_PRIOR[2][3]})")
P(f"     this session's four within-session block readings (MEASURED HERE): "
  + " / ".join(f"{BLOCKINFO[g]['m']:.0f} {BLOCKINFO[g]['cls']} (min {BLOCKINFO[g]['mn']:.0f})" for g, _ in BLOCKS))
w1 = None
if not c1_ok or c2_letter == "(c)":
    w1 = "(d)"
    P("     VERDICT: branch (d) FLAGGED -- C1 fired (b) or C2 fired (c);")
    P("     no block-variability reading is evaluable from this session.")
elif c2_letter == "(a)":
    w1 = "(a)"
    P("     VERDICT: branch (a) -- the anchor's class is STABLE within a")
    P("     session at block granularity while the three cross-session")
    P("     readings flip; the flip is NOT within-session block-level noise")
    P("     at this granularity; the anchor-class settling bar (a")
    P("     cross-session bar -- session 28's W1 residual) is NOT met by")
    P("     same-UTC-day data and NO bracket narrowing is claimed -- the")
    P("     flip location stays inside (252,604, 253,906]. ONE session; L2")
    P("     binds; L5 no interpolation; NO causal mechanism is claimed or")
    P("     measured.")
elif c2_letter == "(b)":
    w1 = "(b)"
    P("     VERDICT: branch (b) -- the class flips WITHIN ONE SESSION at a")
    P("     byte-identical binary and identical knob triple: the")
    P("     cross-session flip readings are confounded with within-session")
    P("     block-level variability at the frozen 1000-tick threshold")
    P("     (measured content) and the DESIGN of the anchor-class settling")
    P("     bar becomes the named next row (a bar that reads classes at this")
    P("     threshold must first name its block-variability floor). NO")
    P("     bracket narrowing is claimed. ONE session; L2 binds; L5 no")
    P("     interpolation; NO causal mechanism is claimed or measured.")
P("")

# W2 the B=3 class-vs-per-dispatch-work row (descriptive)
P("   W2 (pre-registered, descriptive) THE B=3 CLASS-VS-PER-DISPATCH-")
P("   WORK ROW: this session adds NO new grid point -- it re-reads")
P("   253,906 with FOUR within-session block readings placed at that grid")
P("   alongside the three prior cross-session readings (committed points")
P("   QUOTE-ONLY L7; NO interpolation (L5); class granularity only;")
P("   * = the session-26 reading carries its C3 (b) caveat; hi-all below")
P("   is a NAMED DIFFERENT ESTIMATOR (12 runs pooled) and replaces no")
P("   reading):")
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
        P(f"     253906     0.2539052     {HI_PRIOR[0][0]:>5}  {'CAPTURED*':<20} session 26 (quote-only)")
        P(f"     253906     0.2539052     {HI_PRIOR[1][0]:>5}  {HI_PRIOR[1][1]:<20} session 27 (quote-only)")
        P(f"     253906     0.2539052     {HI_PRIOR[2][0]:>5}  {HI_PRIOR[2][1]:<20} session 28 (quote-only)")
        for g, _ in BLOCKS:
            bi = BLOCKINFO[g]
            P(f"     253906     0.2539052     {bi['m']:>5.0f}  {bi['cls']:<20} THIS SESSION blk-{g}")
        P(f"     253906     0.2539052     {m_all:>5.0f}  {CLASS['hi-all']:<20} THIS SESSION hi-all (12-run estimator)")
        _inserted = True
    P(f"     {n:<10} {lbl:<13} {ticks:>5}  {cls:<20} {src} (quote-only)")
P("")

# W3 the block comparisons (descriptive)
P("   W3 (pre-registered, descriptive) THE BLOCK COMPARISONS:")
P(f"     (i) the four blocks side by side (identical knob triple, one")
P(f"         byte-identical binary, one session; differ only in time")
P(f"         order -- L9):")
for g, _ in BLOCKS:
    bi = BLOCKINFO[g]
    P(f"         blk-{g} (runs {bi['runs']}): {bi['m']:.0f} {bi['cls']}  18-cell {bi['mn']:.0f}..{bi['mx']:.0f}  host_ns {bi['hn']:.0f}")
P(f"     (ii) the four block 18-cell minima against the three")
P(f"         cross-session minima (all three within 25 ticks of the frozen")
P(f"         1,000 boundary -- quote-only L7): block minima "
  + "/".join(f"{BLOCKINFO[g]['mn']:.0f}" for g, _ in BLOCKS)
  + f"; cross-session {HI_PRIOR[0][2]} / {HI_PRIOR[1][2]} / {HI_PRIOR[2][2]}")
P(f"     (iii) the 12 per-run (sum,128,16) medians and the 12 per-run")
P(f"          18-cell minima (DESCRIPTIVE -- the per-run unit is 25 rounds")
P(f"          per cell, NOT the frozen 3-run unit -- L10):")
run_rows = []
for r in ARMR["hi"]:
    v16 = pooled_runs("hi", sum128, [r])
    mnr = min(pooled_runs("hi", k, [r]) for k in ok_cells)
    run_rows.append((r, v16, mnr))
P("          run  (sum,128,16)  18-cell min")
for r, v16, mnr in run_rows:
    P(f"          r{r:<3} {v16:>10.0f}  {mnr:>10.0f}")
P("")

# X1 host_ns (descriptive)
P("   X1 (descriptive, host_ns at (sum,128,S=16)):")
hn = {t: pooled_host_runs(t, sum128, ARMR[t]) for t in TAGS}
P("     " + ", ".join(f"{t} {hn[t]:.0f}" for t in TAGS)
  + f"; hi blocks " + ", ".join(f"blk-{g} {BLOCKINFO[g]['hn']:.0f}" for g, _ in BLOCKS))
for t in TAGS:
    prior = HOSTNS[t]
    comps = []
    for i, v in enumerate(prior):
        if v is not None:
            comps.append(f"{hn[t]/v:.3f}x session-{26+i}'s ({v:,})")
    P(f"     {t} {hn[t]:.0f} = " + "; ".join(comps) + f" -- {HOSTNS_SRC[t]} same-knob")
P("     host_ns is the HOST-side proxy (L3), not a C criterion; any")
P("     excursion is NAMED, NOT HIDDEN and its cause is UNMEASURED.")
P("")

P("4. VERDICT SUMMARY: C1 (a)={0}; C2 {1}; W1 {2}.".format(c1_ok, c2_letter, w1))
P("   The named-hypothesis discrimination of the row question is as W1")
P("   states; WHY is UNMEASURED and NO causal mechanism is claimed.")

with open(os.path.join(HERE, "publication-s29.txt"), "w") as f:
    f.write("\n".join(out) + "\n")
