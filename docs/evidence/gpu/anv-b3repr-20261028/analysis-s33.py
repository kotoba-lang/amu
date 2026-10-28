#!/usr/bin/env python3
"""JUN-59 session 33 analysis -- THE REPRESENTATION-SIDE RE-READ (the
(1024,4033)-vs-(2048,8066) PAIR-TWIN CLASS RELATION at the anchor grid
n=253,906, B=3 -- one 3-run block per arm at byte-identical rebuilt
binaries, plus the archived controls c2/c8), ON UTC DAY 2026-10-28.

Route (frozen in protocol.txt section 6): this script parses ONLY the
12 committed run logs in its own directory (run-<tag>-r<R>.txt) and
writes publication-s33.txt. No other input. Deterministic: running it
twice yields byte-identical publication-s33.txt (checked by diff after
the recorded run).

Cross-session reference values are frozen in protocol.txt section 3 and
embedded below as named constants (committed controls, the
(1024,4033) pair's prior readings sessions 26-32, the (2048,8066)
pair's prior readings sessions 26/28, and the settling bar's frozen
in-band references 1,129 / 1,132 / 1,131); they are comparison values
only and never this session's measurements.
"""
import re, sys, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

# tag -> (BATCH, WORK_MUL, NDIV, [runs]), protocol.txt section 1 arm table
ARMS = [("c2", 2, 1, 1, [1, 2, 3]),
        ("hi", 3, 1024, 4033, [1, 2, 3]),
        ("tw", 3, 2048, 8066, [1, 2, 3]),
        ("c8", 8, 1, 1, [1, 2, 3])]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMW = {a[0]: a[2] for a in ARMS}
ARMD = {a[0]: a[3] for a in ARMS}
ARMR = {a[0]: a[4] for a in ARMS}
N_BASE = 1000003

# committed control anchors (comparison of committed values only)
COMMITTED = {"c2": 31, "c8": 32915}
COMMITTED_SRC = {"c2": "sessions 1-32 floor band 31..32",
                 "c8": "session 4 pooled median"}
# the (1024,4033) pair's prior readings (protocol sec 3, quote-only L7)
HI_PRIOR = [(1129, "CAPTURED", 1001, "session 26 mid"),
            (1132, "INTERMEDIATE/MIXED", 976, "session 27 hi"),
            (1131, "INTERMEDIATE/MIXED", 991, "session 28 hi"),
            (1130, "INTERMEDIATE/MIXED", 993, "session 29 blk-A"),
            (1144, "INTERMEDIATE/MIXED", 979, "session 29 blk-B"),
            (1143, "INTERMEDIATE/MIXED", 985, "session 29 blk-C"),
            (1151, "INTERMEDIATE/MIXED", 993, "session 29 blk-D"),
            (1142, "INTERMEDIATE/MIXED", 985, "session 31 (day 28, COUNTED)"),
            (1128, "INTERMEDIATE/MIXED", 982, "session 32 (day 28, descriptive)")]
# the (2048,8066) pair's prior readings (quote-only L7)
TW_PRIOR = [(1145, "INTERMEDIATE/MIXED", 985, "session 26 eq3"),
            (1141, "INTERMEDIATE/MIXED", 983, "session 28 tw")]
# the settling bar's frozen in-band references (settle-bar.txt D3)
BAR_REFS = (1129, 1132, 1131)
# prior host_ns at (sum,128,S=16) (quote-only)
HOSTNS = {"c2": (680499, 672684, 678546, 673456, 679908, 672374),
          "hi": (309848, 310008, 309647, 308129, 875403, 304999),
          "tw": (310509, 309467),
          "c8": (2380500, 2397482, 3053605, 2397240, 2381642, 2400076)}
HOSTNS_SRC = {"c2": "sessions 26/27/28/29/31/32",
              "hi": "sessions 26 mid / 27 hi / 28 hi / 29 pooled / 31 / 32",
              "tw": "session 26 eq3 / session 28 tw",
              "c8": "sessions 26/27/28/29/31/32"}
# the C3 scoreboard before this session (quote-only)
SCOREBOARD = "s24 (b) SPLIT / s25 (a) AGREE / s26 (b) SPLIT / s27 (a) AGREE / s28 (a) AGREE"

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
P("JUN-59 session 33 -- THE REPRESENTATION-SIDE RE-READ (THE")
P("(1024,4033)-vs-(2048,8066) PAIR-TWIN CLASS RELATION AT THE ANCHOR")
P("GRID: one 3-run block of (3,1024,4033) and one of (3,2048,8066),")
P("both at n=253,906 = (1,000,003*1024)//4033, B=3, byte-identical")
P("rebuilt binaries, ON UTC DAY 2026-10-28 -- the settling bar's day")
P("slot is session 31's (COUNTED 1/4) and the bar never judges the")
P("twin -- plus the archived controls c2/c8 bracketing), publication")
P("Produced ONLY by analysis-s33.py over the 12 committed run logs in this")
P("directory (run-<tag>-r<R>.txt); protocol.txt was frozen before the")
P("first run (freeze stamp 2026-10-28T01:08:56Z). Arms = binary")
P("compile-time (BATCH, WORK_MUL, NDIV); n = (1,000,003*WORK_MUL)/NDIV")
P("(integer floor). THE PAIR BLOCK = hi r1-3 and THE TWIN BLOCK = tw")
P("r1-3, each pooled over 25 rounds per cell (the frozen estimator")
P("unit). The row question (protocol section 0): AT THE IDENTICAL GRID")
P("AND B=3, DO THE (1024,4033) PAIR AND ITS SAME-RATIO TWIN (2048,8066)")
P("CLASSIFY THE SAME OR DIFFERENT AT THE FROZEN SECTION-4 THRESHOLD AT")
P("BYTE-IDENTICAL BINARIES (T1)? ZERO derivation this session: the")
P("instrument is session 28's committed NDIV-derived source")
P("byte-identical (digest a5e539f0... -- derivation-census-s33.txt); the")
P("a-set manifest runs the ARCHIVED measured spv (16-digest corpus).")
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

P("1. INTEGRITY (computed over the 12 logs):")
P(f"   runs parsed: 12 (c2 3 + hi 3 + tw 3 + c8 3); cell map identical across runs: {cell_keys is not None and not any('CELL MAP' in i for i in integrity)}")
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

P("2. THE MEASURED BRACKETS (pooled median gpu_ticks; each BLOCK =")
P("   one arm's r1-3 = one 3-run block x 25 rounds per cell):")
P("   each row: (sum,128,S=16) exact value, then min..max over the 18")
P("   pipeline-ok cells; host_ns at (sum,128,S=16)")
P("")
P("   unit      B  WM   NDIV    n        total-nominal  (sum,128,16)  min..max over 18 cells   host_ns")
for tag in TAGS:
    b, wm, dd = ARMB[tag], ARMW[tag], ARMD[tag]
    n = (N_BASE * wm) // dd
    vals = [pooled_runs(tag, k, ARMR[tag]) for k in ok_cells]
    v16 = pooled_runs(tag, sum128, ARMR[tag])
    hn = pooled_host_runs(tag, sum128, ARMR[tag])
    tot = b * n / N_BASE
    P(f"   {tag:<9} {b}  {wm:<5} {dd:<6} {n:>8}  {tot:>12.6f}  {v16:>10.0f}  {min(vals):>8.0f}..{max(vals):<8.0f}  {hn:>9.0f}")
P("")

# ---- classification (protocol.txt section 4 thresholds) ----
CLASS = {}
INFO = {}
for tag in TAGS:
    cls, vals = block_class(tag, ARMR[tag])
    CLASS[tag] = cls
    INFO[tag] = dict(cls=cls, m=pooled_runs(tag, sum128, ARMR[tag]),
                     mn=min(vals), mx=max(vals),
                     hn=pooled_host_runs(tag, sum128, ARMR[tag]))

P("3. PRE-REGISTERED LETTERS (thresholds frozen in protocol.txt section 4:")
P("   FLOOR <= 100 ticks at all 18 cells; CAPTURED >= 1000 ticks at all 18;")
P("   anything else INTERMEDIATE/MIXED; each BLOCK = 3 fresh processes):")
P("")
for tag in TAGS:
    b, wm, dd = ARMB[tag], ARMW[tag], ARMD[tag]
    n = (N_BASE * wm) // dd
    if tag == "hi":
        P(f"   class THE PAIR BLOCK (hi r1-3, B=3, WM=1024, NDIV=4033, n={n}, UTC day 2026-10-28, THIRD same-day reading): {INFO['hi']['cls']}  (sum,128,16) {INFO['hi']['m']:.0f}  18-cell {INFO['hi']['mn']:.0f}..{INFO['hi']['mx']:.0f}")
    elif tag == "tw":
        P(f"   class THE TWIN BLOCK (tw r1-3, B=3, WM=2048, NDIV=8066, n={n}, UTC day 2026-10-28, the (2048,8066) pair's THIRD measurement): {INFO['tw']['cls']}  (sum,128,16) {INFO['tw']['m']:.0f}  18-cell {INFO['tw']['mn']:.0f}..{INFO['tw']['mx']:.0f}")
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

# C1 first (prerequisite; the environment pin)
c1_c2_ok = CLASS["c2"] == "FLOOR"
c1_parts = [f"c2 satisfies FLOOR (committed floor band 31..32 at B=2): {c1_c2_ok}"]
v8 = pooled_runs("c8", sum128, ARMR["c8"])
c1_c8_ok = abs(v8 - COMMITTED["c8"]) <= 0.05 * COMMITTED["c8"]
c1_parts.append(f"c8 (sum,128,16) pooled median {v8:.0f} within +/-5% of committed {COMMITTED['c8']} ({COMMITTED_SRC['c8']}): {c1_c8_ok}")
c1_ok = c1_c2_ok and c1_c8_ok
P("   C1 ARCHIVED CONTROL REPLICATION (numeric agreement with the committed")
P("   value at the control's OWN (B,WORK_MUL,NDIV) -- the a-set runs the")
P("   ARCHIVED spv bytes through the byte-identical session-33 instrument,")
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

# T1 -- THE ROW QUESTION (the pair-twin class relation at the identical grid)
P("   T1 THE ROW QUESTION (frozen letters, protocol section 0): AT THE")
P("   IDENTICAL GRID n=253,906 AND B=3, DO THE (1024,4033) PAIR AND ITS")
P("   SAME-RATIO TWIN (2048,8066) CLASSIFY THE SAME OR DIFFERENT AT")
P("   BYTE-IDENTICAL BINARIES?")
same_class = CLASS["tw"] == CLASS["hi"]
med_close = abs(INFO["tw"]["m"] - INFO["hi"]["m"]) <= 0.05 * INFO["hi"]["m"]
P(f"     class(hi) = {INFO['hi']['cls']} ({INFO['hi']['m']:.0f}, 18-cell min {INFO['hi']['mn']:.0f})")
P(f"     class(tw) = {INFO['tw']['cls']} ({INFO['tw']['m']:.0f}, 18-cell min {INFO['tw']['mn']:.0f})")
P(f"     same class: {same_class}; medians within +/-5% ({INFO['tw']['m']:.0f} vs {INFO['hi']['m']:.0f}, {abs(INFO['tw']['m']-INFO['hi']['m'])/INFO['hi']['m']*100:.2f}% apart): {med_close}")
verify0 = verify_mismatch_total == 0
if not (c1_ok and verify0):
    t1 = "(c) NOT EVALUABLE (session FLAGGED)"
    P(f"     T1 LETTER: {t1} -- the environment pin is broken (C1/VERIFY).")
elif same_class and med_close:
    t1 = "(a) AGREE"
    P(f"     T1 LETTER: {t1} -- the s28 anchor-grid C3 (a) REPEATS: the")
    P("     representation does not split the class at this grid in this")
    P("     window. NAMED, NOT HIDDEN: an AGREE does not resolve")
    P("     threshold-artifact-vs-representation -- the min-statistic")
    P("     wander (F2: per-run minima 971..1,001; block minima 976..1,001)")
    P("     may mask a representation effect (L2: observational only).")
else:
    t1 = "(b) SPLIT"
    P(f"     T1 LETTER: {t1} -- the sessions 24/26 C3 (b) RECURS at this grid")
    P("     in this window. NAMED, NOT HIDDEN: a SPLIT does not resolve")
    P("     threshold-artifact-vs-representation -- s26's split was itself")
    P("     min 1,001 vs 985 at overlapping medians, i.e. inside the F2")
    P("     wander band, and may be that wander wearing the pair-twin")
    P("     relation (L2: observational only).")
P(f"     The C3 scoreboard becomes: {SCOREBOARD} / s33 {'(a) AGREE' if t1 == '(a) AGREE' else ('(b) SPLIT' if t1 == '(b) SPLIT' else t1)}.")
P("")

# D1 the twin's cross-session class (descriptive)
P("   D1 (pre-registered, descriptive) THE TWIN'S CROSS-SESSION CLASS")
P("   (the (2048,8066) pair's readings at byte-identical binaries;")
P("   quote-only L7 priors; ONE new reading -- no rate is claimed):")
P(f"     priors: " + " / ".join(f"{m} {c} (min {mn}, {src})" for m, c, mn, src in TW_PRIOR))
P(f"     THIS BLOCK (MEASURED HERE): {INFO['tw']['m']:.0f} {INFO['tw']['cls']} (18-cell min {INFO['tw']['mn']:.0f}, max {INFO['tw']['mx']:.0f})")
tw_prior_classes = [c for _, c, _, _ in TW_PRIOR]
if INFO["tw"]["cls"] in tw_prior_classes:
    P(f"     the twin's class is UNCHANGED across its three readings ({', '.join(tw_prior_classes)} -> {INFO['tw']['cls']})")
    P("     -- NAMED, NOT HIDDEN: the (1024,4033) pair flipped class across")
    P("     sessions (1,129 CAPTURED s26 -> 1,132 MIXED s27 -> ...) while the")
    P("     twin has not in its three readings; three twin readings vs nine")
    P("     pair readings do NOT establish different flip rates and none is")
    P("     claimed.")
else:
    P(f"     the twin's class MOVED ({', '.join(tw_prior_classes)} -> {INFO['tw']['cls']}) -- the twin")
    P("     ALSO moves across sessions at byte-identical binaries. NAMED,")
    P("     NOT HIDDEN: three readings; no rate is claimed.")
P("")

# B1 the ledger status (the bar's day slot is session 31's; the twin is not bar content)
P("   B1 THE LEDGER STATUS (settle-bar.txt section 2): the UTC-day")
P("   2026-10-28 slot is CONSUMED by session 31 (COUNTED 1/4). The hi")
P("   block is a LATER same-UTC-day anchor reading: NAMED DESCRIPTIVE")
P("   CONTENT; it can NOT advance the bar. The tw block produces NO")
P("   ledger line (the bar never judges the (2048,8066) twin -- L11).")
qualifies = c1_ok and verify0
if qualifies:
    P("     The hi reading QUALIFIES on the run-log criteria (C1 (a), VERIFY")
    P("     mismatch 0) and, with the custody facts (build pins, GO before")
    P("     builds/runs), is appended to the ledger with flag=none as")
    P("     descriptive content; the frozen evaluator excludes it from")
    P("     COUNTED (same-day-duplicate fixture).")
else:
    P("     branch (b) FLAGGED -- the line enters the ledger with its flag")
    P("     token and adds no reading.")
P("     The expected evaluator verdict after the append is UNCHANGED:")
P("     PENDING 1/4 with session 31 counted. The frozen evaluator")
P("     settle-bar-eval.py over the ledger (bar-eval-s33.txt) is the ONLY")
P("     verdict writer -- never hand-written here.")
P("")

# D2 the hi block vs the flip picture (descriptive)
P("   D2 (pre-registered, descriptive) THE PAIR BLOCK AGAINST THE FLIP")
P("   PICTURE (quote-only L7 priors; NO bracket narrowing -- L5):")
P(f"     THIS BLOCK (UTC day 2026-10-28, THIRD same-day, MEASURED HERE): "
  f"{INFO['hi']['m']:.0f} {INFO['hi']['cls']} (18-cell min {INFO['hi']['mn']:.0f}, max {INFO['hi']['mx']:.0f})")
inband = all(abs(INFO['hi']['m'] - ref) <= 0.05 * ref for ref in BAR_REFS)
P(f"     in-band vs the bar's frozen refs {BAR_REFS[0]} / {BAR_REFS[1]} / {BAR_REFS[2]} (within +/-5% of EACH): {inband}")
P(f"     the pair's nine prior readings: " +
  " / ".join(f"{m} {c} (min {mn}, {src})" for m, c, mn, src in HI_PRIOR))
P("     Same-day multiplicity does not advance the bar (V4 PENDING 1/4);")
P("     no causal mechanism is claimed or measured.")
P("")

# D3 the per-run comparison (descriptive)
P("   D3 (pre-registered, descriptive) THE PER-RUN VIEW (DESCRIPTIVE --")
P("   the per-run unit is 25 rounds per cell, NOT the frozen 3-run unit --")
P("   L10):")
P("          unit  run  (sum,128,16)  18-cell min   host_ns")
for tag in ("hi", "tw"):
    for r in ARMR[tag]:
        v16 = pooled_runs(tag, sum128, [r])
        mnr = min(pooled_runs(tag, k, [r]) for k in ok_cells)
        hnr = pooled_host_runs(tag, sum128, [r])
        P(f"          {tag:<4}  r{r:<3} {v16:>10.0f}  {mnr:>10.0f}  {hnr:>10.0f}")
P("")

# X1 host_ns (descriptive)
P("   X1 (descriptive, host_ns at (sum,128,S=16)):")
hn = {t: pooled_host_runs(t, sum128, ARMR[t]) for t in TAGS}
P("     " + ", ".join(f"{t} {hn[t]:.0f}" for t in TAGS))
for t in TAGS:
    prior = HOSTNS[t]
    comps = []
    lbls = ["s26", "s27", "s28", "s29", "s31", "s32"]
    tlbls = ["s26", "s28"]
    for i, v in enumerate(prior):
        comps.append(f"{hn[t]/v:.3f}x {(tlbls if t=='tw' else lbls)[i]}'s ({v:,})")
    P(f"     {t} {hn[t]:.0f} = " + "; ".join(comps) + f" -- {HOSTNS_SRC[t]} same-knob")
P("     host_ns is the HOST-side proxy (L3), not a C criterion; any")
P("     excursion is NAMED, NOT HIDDEN and its cause is UNMEASURED.")
P("")

P("4. VERDICT SUMMARY: C1 (a)={0}; T1 LETTER {1}; PAIR BLOCK {2}")
out[-1] = out[-1].format(c1_ok, t1, INFO["hi"]["cls"])
P("   ({0:.0f}, min {1:.0f}) vs TWIN BLOCK {2} ({3:.0f}, min {4:.0f}) on UTC"
  .format(INFO["hi"]["m"], INFO["hi"]["mn"], INFO["tw"]["cls"], INFO["tw"]["m"], INFO["tw"]["mn"]))
P("   day 2026-10-28 at byte-identical binaries (4/4 pins). The hi block is")
P("   the THIRD same-day anchor reading (the bar stays PENDING 1/4 with")
P("   session 31 counted -- the frozen evaluator's verdict in")
P("   bar-eval-s33.txt); the twin is not bar content. WHY any class flips")
P("   across sessions/days is UNMEASURED and NO causal mechanism is")
P("   claimed.")

with open(os.path.join(HERE, "publication-s33.txt"), "w") as f:
    f.write("\n".join(out) + "\n")
