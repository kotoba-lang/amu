#!/usr/bin/env python3
"""JUN-59 session 34 analysis -- THE WITHIN-WINDOW MIN-STATISTIC WANDER
PROBE (the THRESHOLD-ARTIFACT side of threshold-artifact-vs-
representation -- TWELVE independent 3-run blocks A..L of the
(1024,4033) anchor at n=253,906, B=3 in ONE session window at a
byte-identical rebuilt binary, plus the archived controls c2/c8), ON
UTC DAY 2026-10-28.

Route (frozen in protocol.txt section 6): this script parses ONLY the
42 committed run logs in its own directory (run-<tag>-r<R>.txt) and
writes publication-s34.txt. No other input. Deterministic: running it
twice yields byte-identical publication-s34.txt (checked by diff after
the recorded run).

Cross-session reference values are frozen in protocol.txt section 3 and
embedded below as named constants (committed controls, the
(1024,4033) pair's ten prior block readings sessions 26-33, the
per-run minima band, and the settling bar's frozen in-band references
1,129 / 1,132 / 1,131); they are comparison values only and never this
session's measurements.
"""
import re, sys, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

# tag -> (BATCH, WORK_MUL, NDIV, [runs]), protocol.txt section 1 arm table
BLOCK_LETTERS = "ABCDEFGHIJKL"
ARMS = [("c2", 2, 1, 1, [1, 2, 3]),
        ("hi", 3, 1024, 4033, list(range(1, 37))),
        ("c8", 8, 1, 1, [1, 2, 3])]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMW = {a[0]: a[2] for a in ARMS}
ARMD = {a[0]: a[3] for a in ARMS}
ARMR = {a[0]: a[4] for a in ARMS}
N_BASE = 1000003
# block letter -> the 3 hi run numbers that form that frozen 3-run block
BLOCKS = {BLOCK_LETTERS[i]: [3 * i + 1, 3 * i + 2, 3 * i + 3] for i in range(12)}

# committed control anchors (comparison of committed values only)
COMMITTED = {"c2": 31, "c8": 32915}
COMMITTED_SRC = {"c2": "sessions 1-33 floor band 31..32",
                 "c8": "session 4 pooled median"}
# the (1024,4033) pair's TEN prior block readings (protocol sec 3, quote-only L7)
HI_PRIOR = [(1129, "CAPTURED", 1001, "session 26 mid"),
            (1132, "INTERMEDIATE/MIXED", 976, "session 27 hi"),
            (1131, "INTERMEDIATE/MIXED", 991, "session 28 hi"),
            (1130, "INTERMEDIATE/MIXED", 993, "session 29 blk-A"),
            (1144, "INTERMEDIATE/MIXED", 979, "session 29 blk-B"),
            (1143, "INTERMEDIATE/MIXED", 985, "session 29 blk-C"),
            (1151, "INTERMEDIATE/MIXED", 993, "session 29 blk-D"),
            (1142, "INTERMEDIATE/MIXED", 985, "session 31 (day 28, COUNTED)"),
            (1128, "INTERMEDIATE/MIXED", 982, "session 32 (day 28, descriptive)"),
            (1124, "INTERMEDIATE/MIXED", 987, "session 33 (day 28, descriptive)")]
PRIOR_BLOCK_MIN_BAND = (976, 1001)   # quote-only: the ten pair block-unit minima
PRIOR_PERRUN_MIN_BAND = (971, 1001)  # quote-only
# the settling bar's frozen in-band references (settle-bar.txt D3)
BAR_REFS = (1129, 1132, 1131)
# prior host_ns at (sum,128,S=16) (quote-only)
HOSTNS = {"c2": (680499, 672684, 678546, 673456, 679908, 672374, 678726),
          "hi": (309848, 310008, 309647, 308129, 875403, 304999, 308946),
          "c8": (2380500, 2397482, 3053605, 2397240, 2381642, 2400076, 2394025)}
HOSTNS_SRC = {"c2": "sessions 26/27/28/29/31/32/33",
              "hi": "sessions 26 mid / 27 / 28 / 29 pooled / 31 / 32 / 33",
              "c8": "sessions 26/27/28/29/31/32/33"}
HOSTNS_LBL = ("s26", "s27", "s28", "s29", "s31", "s32", "s33")

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
P("JUN-59 session 34 -- THE WITHIN-WINDOW MIN-STATISTIC WANDER PROBE")
P("(THE THRESHOLD-ARTIFACT SIDE OF threshold-artifact-vs-representation:")
P("TWELVE independent 3-run blocks A..L of the (1024,4033) anchor at")
P("n=253,906 = (1,000,003*1024)//4033, B=3, in ONE session window at a")
P("byte-identical rebuilt binary, ON UTC DAY 2026-10-28 -- the settling")
P("bar's day slot is session 31's (COUNTED 1/4) and block A is the only")
P("bar-candidate block (protocol L12) -- plus the archived controls")
P("c2/c8 bracketing the whole hi window), publication")
P("Produced ONLY by analysis-s34.py over the 42 committed run logs in this")
P("directory (run-<tag>-r<R>.txt); protocol.txt was frozen before the")
P("first run (freeze stamp 2026-10-28T01:39:28Z). Arms = binary")
P("compile-time (BATCH, WORK_MUL, NDIV); n = (1,000,003*WORK_MUL)/NDIV")
P("(integer floor). EACH BLOCK = 3 fresh processes x 25 rounds per cell")
P("(the frozen estimator unit). The row question (protocol section 0):")
P("DO THE 12 IN-WINDOW BLOCK-UNIT MIN STATISTICS (min over the 18")
P("pipeline-ok cells of the pooled median gpu_ticks -- the quantity that")
P("decides CAPTURED-vs-not at the frozen 1,000-tick threshold) STRADDLE")
P("1,000 (T1)? ZERO derivation this session: the instrument is session")
P("28's committed NDIV-derived source byte-identical (digest")
P("a5e539f0... -- derivation-census-s34.txt); the a-set manifest runs the")
P("ARCHIVED measured spv (16-digest corpus).")
P("1 tick = timestampPeriod = 52.083 ns.")
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

P("1. INTEGRITY (computed over the 42 logs):")
P(f"   runs parsed: 42 (c2 3 + hi 36 + c8 3); cell map identical across runs: {cell_keys is not None and not any('CELL MAP' in i for i in integrity)}")
P(f"   headers byte-identical across all runs outside the # n= knob line: {header_ok}")
P(f"   header batch=/work_mul=/ndiv= == run's (B,WM,NDIV) and n == (1,000,003*WM)//NDIV; every SAMPLE batch=/work_mul=/ndiv= == (B,WM,NDIV): {knob_field_ok}")
P(f"   every CELL spv= name is an archived .emitted.spv (no .iter -- the corpus is byte-identical this session): {spv_identity_ok}")
P(f"   SAMPLE lines: 450 per run (18 ok cells x 25 rounds) in 42/42 runs: {sample_counts_ok}")
P(f"   VERIFY mismatch total over all runs: {verify_mismatch_total} (per-arm: "
  + ", ".join(f"{t}={verify_mismatch_by_arm[t]}" for t in TAGS)
  + ") -- bit-exact correctness re-check inside every run; frozen INVALIDATION criterion (protocol section 4): >0 in any run makes that run DEFECTIVE and the arm INVALID")
P(f"   forcing reality (pipeline-ok cell-runs where probe_size==forced and probe_nsub==wg/forced): {forcing_ok}/{forcing_total}")
P(f"   S=8 cells fail-closed (pipeline=FAIL, forced=8): {s8_fail} cell-runs (6 per run x 42 runs = 252 expected)")
if integrity:
    for i in integrity:
        P(f"   !! {i}")
P("")

ok_cells = sorted([k for k, v in data[("c2", 1)][0].items() if v["pipeline"] == "ok"])

def ckey(idx):
    c = data[("c2", 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])

sum128 = [k for k in ok_cells if ckey(k) == ("sum", 128, "16")][0]

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

# ---- per-block stats for the 12 hi blocks ----
BLK = {}   # letter -> dict(m, mn, mx, cls, hn)
for L in BLOCK_LETTERS:
    runs = BLOCKS[L]
    vals = [pooled_runs("hi", k, runs) for k in ok_cells]
    cls, _ = block_class("hi", runs)
    BLK[L] = dict(runs=runs, m=pooled_runs("hi", sum128, runs), mn=min(vals), mx=max(vals),
                  cls=cls, hn=pooled_host_runs("hi", sum128, runs))

CTRL = {}
for tag in ("c2", "c8"):
    cls, vals = block_class(tag, ARMR[tag])
    CTRL[tag] = dict(m=pooled_runs(tag, sum128, ARMR[tag]), mn=min(vals), mx=max(vals),
                     cls=cls, hn=pooled_host_runs(tag, sum128, ARMR[tag]))

P("2. THE MEASURED BRACKETS (pooled median gpu_ticks; each BLOCK =")
P("   3 fresh processes x 25 rounds per cell -- the frozen estimator")
P("   unit): each row: (sum,128,S=16) exact value, then min..max over")
P("   the 18 pipeline-ok cells; host_ns at (sum,128,S=16)")
P("")
P("   unit      B  WM   NDIV    n        total-nominal  (sum,128,16)  min..max over 18 cells   host_ns")
for L in BLOCK_LETTERS:
    d = BLK[L]
    P(f"   hi blk {L:<2} 3  1024 4033   253906      0.750000  {d['m']:>10.0f}  {d['mn']:>8.0f}..{d['mx']:<8.0f}  {d['hn']:>9.0f}")
for tag in ("c2", "c8"):
    b, wm, dd = ARMB[tag], ARMW[tag], ARMD[tag]
    n = (N_BASE * wm) // dd
    d = CTRL[tag]
    P(f"   {tag:<9} {b}  {wm:<5} {dd:<6} {n:>8}  {b*n/N_BASE:>12.6f}  {d['m']:>10.0f}  {d['mn']:>8.0f}..{d['mx']:<8.0f}  {d['hn']:>9.0f}")
P("")

P("3. PRE-REGISTERED LETTERS (thresholds frozen in protocol.txt section 4:")
P("   FLOOR <= 100 ticks at all 18 cells; CAPTURED >= 1000 ticks at all 18;")
P("   anything else INTERMEDIATE/MIXED; each BLOCK = 3 fresh processes):")
P("")
P("   block-unit min statistics (THE STATISTIC, in run order A..L): "
  + " ".join(f"{L} {BLK[L]['mn']:.0f}" for L in BLOCK_LETTERS))
P("   block classes (in run order A..L): "
  + " ".join(f"{L} {BLK[L]['cls']}" for L in BLOCK_LETTERS))
for L in BLOCK_LETTERS:
    P(f"   class block {L} (hi r{BLOCKS[L][0]}-r{BLOCKS[L][2]}, B=3, WM=1024, NDIV=4033, n=253906): {BLK[L]['cls']}  (sum,128,16) {BLK[L]['m']:.0f}  18-cell {BLK[L]['mn']:.0f}..{BLK[L]['mx']:.0f}")
for tag in ("c2", "c8"):
    P(f"   class {tag} (B={ARMB[tag]}, WM={ARMW[tag]}, NDIV={ARMD[tag]}, n={(N_BASE*ARMW[tag])//ARMD[tag]}, {ARMB[tag]*((N_BASE*ARMW[tag])//ARMD[tag])/N_BASE:.6f} nominal units): {CTRL[tag]['cls']}")
P("")

arms_invalid = sorted(t for t in TAGS if verify_mismatch_by_arm[t] > 0)
if arms_invalid:
    P("   INVALIDATION CRITERION FIRED (frozen): VERIFY mismatch > 0 in arm(s)")
    P(f"   {arms_invalid} -- the knob arithmetic is WRONG at those arms")
    P("   (a stored value changed: buffer sizing / PARTS_CAP / CPU reference)")
    P("   and no letter below is evaluable from those arms.")
    P("")

# C1 first (prerequisite; the environment pin)
c1_c2_ok = CTRL["c2"]["cls"] == "FLOOR"
c1_parts = [f"c2 satisfies FLOOR (committed floor band 31..32 at B=2): {c1_c2_ok}"]
v8 = CTRL["c8"]["m"]
c1_c8_ok = abs(v8 - COMMITTED["c8"]) <= 0.05 * COMMITTED["c8"]
c1_parts.append(f"c8 (sum,128,16) pooled median {v8:.0f} within +/-5% of committed {COMMITTED['c8']} ({COMMITTED_SRC['c8']}): {c1_c8_ok}")
c1_ok = c1_c2_ok and c1_c8_ok
P("   C1 ARCHIVED CONTROL REPLICATION (numeric agreement with the committed")
P("   value at the control's OWN (B,WORK_MUL,NDIV) -- the a-set runs the")
P("   ARCHIVED spv bytes through the byte-identical session-34 instrument,")
P("   so this pins the environment as well):")
for s in c1_parts:
    P(f"     {s}")
if c1_ok:
    P("     VERDICT: branch (a) both controls satisfy their criteria --")
    P("     the environment pin holds and the T1 letter is evaluable.")
else:
    P("     VERDICT: branch (b) replication discrepancy (bearing on the")
    P("     environment pin); the T1 letter is NOT EVALUABLE; cause UNMEASURED.")
P("")

# T1 -- THE ROW QUESTION (the within-window straddle of the class boundary)
P("   T1 THE ROW QUESTION (frozen letters, protocol section 0): DO THE 12")
P("   IN-WINDOW BLOCK-UNIT MIN STATISTICS STRADDLE THE FROZEN 1,000-TICK")
P("   CLASS BOUNDARY AT THE BYTE-IDENTICAL ANCHOR BINARY?")
mn_min = min(BLK[L]["mn"] for L in BLOCK_LETTERS)
mn_max = max(BLK[L]["mn"] for L in BLOCK_LETTERS)
ge = [L for L in BLOCK_LETTERS if BLK[L]["mn"] >= 1000]
lt = [L for L in BLOCK_LETTERS if BLK[L]["mn"] < 1000]
P(f"     in-window block-min range: {mn_min:.0f}..{mn_max:.0f} (12 blocks)")
P(f"     blocks with min >= 1,000: {len(ge)} ({' '.join(ge) if ge else 'none'}); blocks with min < 1,000: {len(lt)} ({' '.join(lt) if lt else 'none'})")
verify0 = verify_mismatch_total == 0
if not (c1_ok and verify0):
    t1 = "(c) NOT EVALUABLE (session FLAGGED)"
    P(f"     T1 LETTER: {t1} -- the environment pin is broken (C1/VERIFY).")
elif ge and lt:
    t1 = "(a) STRADDLE"
    P(f"     T1 LETTER: {t1} -- the frozen class boundary is crossed by")
    P("     WITHIN-WINDOW variation alone at byte-identical binaries:")
    P(f"     blocks {' '.join(ge)} >= 1,000 and blocks {' '.join(lt)} < 1,000 in ONE window.")
    P("     The cross-session class flip (s26 1,129 CAPTURED min 1,001 ->")
    P("     s27 1,132 MIXED min 976) needs no session-level effect to occur.")
    P("     NAMED, NOT HIDDEN: this does NOT prove threshold artifact -- the")
    P("     wander may itself be driven by an uncontrolled physical variable")
    P("     (thermal, scheduling, memory state); L2 observational only, NO")
    P("     causal mechanism claimed, and threshold-artifact-vs-")
    P("     representation is NOT resolved.")
else:
    t1 = "(b) ONE-SIDE"
    side = ">= 1,000" if ge else "< 1,000"
    P(f"     T1 LETTER: {t1} -- all 12 in-window block mins fall strictly {side}")
    P("     of 1,000; the boundary was NOT crossed inside this window.")
    P("     NAMED, NOT HIDDEN: one window bounds nothing about other")
    P("     windows -- estimator wander at other windows/days is untouched")
    P("     (L2 observational only), and threshold-artifact-vs-")
    P("     representation is NOT resolved either way.")
P("")

# D1 the in-window sequence vs the cross-session bands (descriptive)
P("   D1 (pre-registered, descriptive) THE IN-WINDOW BLOCK-MIN SEQUENCE")
P("   vs THE QUOTE-ONLY CROSS-SESSION BANDS (L7 -- no variance, rate or")
P("   distribution claim is made or measurable from K=12 in one window):")
P(f"     this window's 12 block mins (run order): "
  + " ".join(f"{BLK[L]['mn']:.0f}" for L in BLOCK_LETTERS))
P(f"     this window's range {mn_min:.0f}..{mn_max:.0f} vs the pair's ten prior block-unit")
P(f"     minima {PRIOR_BLOCK_MIN_BAND[0]}..{PRIOR_BLOCK_MIN_BAND[1]} (the 1,000 class boundary sits inside BOTH)")
P(f"     this window's per-run minima (36 values, DESCRIPTIVE per-run unit -- L10): "
  + " ".join(f"{min(pooled_runs('hi', k, [r]) for k in ok_cells):.0f}" for L in BLOCK_LETTERS for r in BLOCKS[L]))
perrun_min = min(min(pooled_runs("hi", k, [r]) for k in ok_cells) for L in BLOCK_LETTERS for r in BLOCKS[L])
perrun_max = max(min(pooled_runs("hi", k, [r]) for k in ok_cells) for L in BLOCK_LETTERS for r in BLOCKS[L])
P(f"     per-run minima range {perrun_min:.0f}..{perrun_max:.0f} vs the quote-only per-run band {PRIOR_PERRUN_MIN_BAND[0]}..{PRIOR_PERRUN_MIN_BAND[1]}")
P("     NAMED, NOT HIDDEN: 12 blocks in ONE window at ONE binary do NOT")
P("     estimate a per-block noise distribution (L13: the blocks share")
P("     host state) and no independence assumption is made.")
P("")

# B1 the ledger status (the bar's day slot is session 31's)
P("   B1 THE LEDGER STATUS (settle-bar.txt section 2 + this session's")
P("   frozen L12): the UTC-day 2026-10-28 slot is CONSUMED by session 31")
P("   (COUNTED 1/4). Block A (the run-order-first hi block) is the")
P("   session's ONLY bar candidate: a LATER same-UTC-day anchor reading,")
P("   NAMED DESCRIPTIVE CONTENT; it can NOT advance the bar. Blocks B..L")
P("   produce NO ledger line (L12, frozen before the runs).")
qualifies = c1_ok and verify0
if qualifies:
    P("     The block A reading QUALIFIES on the run-log criteria (C1 (a),")
    P("     VERIFY mismatch 0) and, with the custody facts (build pins, GO")
    P("     before builds/runs), is appended to the ledger with flag=none as")
    P("     descriptive content; the frozen evaluator excludes it from")
    P("     COUNTED (same-day-duplicate fixture).")
else:
    P("     branch (b) FLAGGED -- the line enters the ledger with its flag")
    P("     token and adds no reading.")
P("     The expected evaluator verdict after the append is UNCHANGED:")
P("     PENDING 1/4 with session 31 counted. The frozen evaluator")
P("     settle-bar-eval.py over the ledger (bar-eval-s34.txt) is the ONLY")
P("     verdict writer -- never hand-written here.")
P("")

# D2 block A vs the flip picture (descriptive)
P("   D2 (pre-registered, descriptive) BLOCK A (THE BAR CANDIDATE) AGAINST")
P("   THE FLIP PICTURE (quote-only L7 priors; NO bracket narrowing -- L5):")
P(f"     BLOCK A (UTC day 2026-10-28, FOURTH same-day, MEASURED HERE): "
  f"{BLK['A']['m']:.0f} {BLK['A']['cls']} (18-cell min {BLK['A']['mn']:.0f}, max {BLK['A']['mx']:.0f})")
inband = all(abs(BLK["A"]["m"] - ref) <= 0.05 * ref for ref in BAR_REFS)
P(f"     in-band vs the bar's frozen refs {BAR_REFS[0]} / {BAR_REFS[1]} / {BAR_REFS[2]} (within +/-5% of EACH): {inband}")
P("     the pair's ten prior block readings: " +
  " / ".join(f"{m} {c} (min {mn}, {src})" for m, c, mn, src in HI_PRIOR))
P("     Same-day multiplicity does not advance the bar (V4 PENDING 1/4);")
P("     no causal mechanism is claimed or measured.")
P("")

# D3 the per-run view (descriptive)
P("   D3 (pre-registered, descriptive) THE PER-RUN VIEW (DESCRIPTIVE --")
P("   the per-run unit is 25 rounds per cell, NOT the frozen 3-run unit --")
P("   L10):")
P("          unit  run  (sum,128,16)  18-cell min   host_ns")
for L in BLOCK_LETTERS:
    for r in BLOCKS[L]:
        v16 = pooled_runs("hi", sum128, [r])
        mnr = min(pooled_runs("hi", k, [r]) for k in ok_cells)
        hnr = pooled_host_runs("hi", sum128, [r])
        P(f"          hi-{L:<2} r{r:<3} {v16:>10.0f}  {mnr:>10.0f}  {hnr:>10.0f}")
for tag in ("c2", "c8"):
    for r in ARMR[tag]:
        v16 = pooled_runs(tag, sum128, [r])
        mnr = min(pooled_runs(tag, k, [r]) for k in ok_cells)
        hnr = pooled_host_runs(tag, sum128, [r])
        P(f"          {tag:<4}  r{r:<3} {v16:>10.0f}  {mnr:>10.0f}  {hnr:>10.0f}")
P("")

# X1 host_ns (descriptive)
P("   X1 (descriptive, host_ns at (sum,128,S=16)):")
P("     per-block hi host_ns (run order A..L): "
  + " ".join(f"{L} {BLK[L]['hn']:.0f}" for L in BLOCK_LETTERS))
for t in ("c2", "c8"):
    hn = CTRL[t]["hn"]
    comps = [f"{hn/v:.3f}x {HOSTNS_LBL[i]}'s ({v:,})" for i, v in enumerate(HOSTNS[t])]
    P(f"     {t} {hn:.0f} = " + "; ".join(comps) + f" -- {HOSTNS_SRC[t]} same-knob")
hn_hi_all = [BLK[L]["hn"] for L in BLOCK_LETTERS]
hi_lo, hi_hi = min(hn_hi_all), max(hn_hi_all)
comps = [f"{hi_lo/875403:.3f}x..{hi_hi/875403:.3f}x s31's excursion (875,403)"] + \
        [f"{hi_lo/v:.3f}x..{hi_hi/v:.3f}x {HOSTNS_LBL[i]}'s ({v:,})" for i, v in enumerate(HOSTNS["hi"]) if v != 875403]
P(f"     hi block range {hi_lo:.0f}..{hi_hi:.0f} = " + "; ".join(comps))
P("     host_ns is the HOST-side proxy (L3), not a C criterion; any")
P("     excursion is NAMED, NOT HIDDEN and its cause is UNMEASURED.")
P("")

P("4. VERDICT SUMMARY: C1 (a)={0}; T1 LETTER {1}".format(c1_ok, t1))
P("   In-window block-min range {0:.0f}..{1:.0f} over 12 blocks of the anchor at".format(mn_min, mn_max))
P("   n=253,906, B=3 on UTC day 2026-10-28 at a byte-identical binary (3/3")
P("   pins); blocks >= 1,000: {0} ({1}), blocks < 1,000: {2} ({3}).".format(len(ge), " ".join(ge) if ge else "none", len(lt), " ".join(lt) if lt else "none"))
P("   Block A is the FOURTH same-day anchor reading (the bar stays PENDING")
P("   1/4 with session 31 counted -- the frozen evaluator's verdict in")
P("   bar-eval-s34.txt). WHY any class flips across sessions/days is")
P("   UNMEASURED and NO causal mechanism is claimed; the")
P("   threshold-artifact-vs-representation question is NOT resolved by")
P("   this session.")

with open(os.path.join(HERE, "publication-s34.txt"), "w") as f:
    f.write("\n".join(out) + "\n")
