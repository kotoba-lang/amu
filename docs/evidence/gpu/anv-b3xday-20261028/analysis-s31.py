#!/usr/bin/env python3
"""JUN-59 session 31 analysis -- THE FIRST BAR-EXECUTING SESSION: THE
FIRST CROSS-UTC-DAY READING OF THE (1024,4033) ANCHOR (one 3-run block
of the (1024,4033) knob pair at n=253,906, B=3 ON UTC DAY 2026-10-28,
plus the archived controls c2/c8).

Route (frozen in protocol.txt section 6): this script parses ONLY the 9
committed run logs in its own directory (run-<tag>-r<R>.txt) and writes
publication-s31.txt. No other input. Deterministic: running it twice
yields byte-identical publication-s31.txt (checked by diff after the
recorded run).

Cross-session reference values are frozen in protocol.txt section 3 and
embedded below as named constants (committed controls, the
(1024,4033) pair's prior readings sessions 26-29, and the settling
bar's frozen in-band references 1,129 / 1,132 / 1,131); they are
comparison values only and never this session's measurements.
"""
import re, sys, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

# tag -> (BATCH, WORK_MUL, NDIV, [runs]), protocol.txt section 0 arm table
ARMS = [("c2", 2, 1, 1, [1, 2, 3]),
        ("hi", 3, 1024, 4033, [1, 2, 3]),
        ("c8", 8, 1, 1, [1, 2, 3])]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMW = {a[0]: a[2] for a in ARMS}
ARMD = {a[0]: a[3] for a in ARMS}
ARMR = {a[0]: a[4] for a in ARMS}
# THE READING (frozen): hi r1-3 = one 3-run block = the bar's estimator unit
READING = ("hi", [1, 2, 3])
N_BASE = 1000003

# committed control anchors (comparison of committed values only)
COMMITTED = {"c2": 31, "c8": 32915}
COMMITTED_SRC = {"c2": "sessions 1-29 floor band 31..32",
                 "c8": "session 4 pooled median"}
# the (1024,4033) pair's prior readings (protocol sec 3, quote-only L7)
HI_PRIOR = [(1129, "CAPTURED", 1001, "session 26 mid"),
            (1132, "INTERMEDIATE/MIXED", 976, "session 27 hi"),
            (1131, "INTERMEDIATE/MIXED", 991, "session 28 hi"),
            (1130, "INTERMEDIATE/MIXED", 993, "session 29 blk-A"),
            (1144, "INTERMEDIATE/MIXED", 979, "session 29 blk-B"),
            (1143, "INTERMEDIATE/MIXED", 985, "session 29 blk-C"),
            (1151, "INTERMEDIATE/MIXED", 993, "session 29 blk-D")]
# the settling bar's frozen in-band references (settle-bar.txt D3)
BAR_REFS = (1129, 1132, 1131)
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
P("JUN-59 session 31 -- THE FIRST BAR-EXECUTING SESSION: THE FIRST")
P("CROSS-UTC-DAY READING OF THE (1024,4033) ANCHOR (one 3-run block of")
P("the (1024,4033) knob pair at n=253,906 = (1,000,003*1024)//4033,")
P("B=3, ON UTC DAY 2026-10-28 -- the settling bar's L4 axis, never")
P("spanned before -- plus the archived controls c2/c8 bracketing the hi")
P("window), publication")
P("Produced ONLY by analysis-s31.py over the 9 committed run logs in this")
P("directory (run-<tag>-r<R>.txt); protocol.txt was frozen before the")
P("first run (freeze stamp 2026-10-28T00:04:50Z). Arms = binary")
P("compile-time (BATCH, WORK_MUL, NDIV); n = (1,000,003*WORK_MUL)/NDIV")
P("(integer floor). THE READING is one 3-run block (hi r1-3) pooled over")
P("25 rounds per cell -- the frozen estimator unit of the settling bar")
P("(settle-bar.txt section 2). The (1024,4033) pair's prior readings are")
P("session 26's mid (1,129 CAPTURED, 18-cell min 1,001), session 27's hi")
P("(1,132 INTERMEDIATE/MIXED, min 976), session 28's hi (1,131")
P("INTERMEDIATE/MIXED, min 991) and session 29's four within-session")
P("blocks (1,130/1,144/1,143/1,151, minima 993/979/985/993) -- all on")
P("UTC day 2026-10-27, all quote-only. The row question (protocol")
P("section 0): DOES A QUALIFYING READING EXIST FOR UTC DAY 2026-10-28 AT")
P("THE (1024,4033) ANCHOR, AND WHAT CLASS DOES IT READ AT THE FROZEN")
P("SECTION-4 THRESHOLD? ZERO derivation this session: the instrument is")
P("session 28's committed NDIV-derived source byte-identical (digest")
P("a5e539f0... -- derivation-census-s31.txt); the a-set manifest runs the")
P("ARCHIVED measured spv (16-digest corpus). 1 tick = timestampPeriod =")
P("52.083 ns.")
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

P("1. INTEGRITY (computed over the 9 logs):")
P(f"   runs parsed: 9 (c2 3 + hi 3 + c8 3); cell map identical across runs: {cell_keys is not None and not any('CELL MAP' in i for i in integrity)}")
P(f"   headers byte-identical across all runs outside the # n= knob line: {header_ok}")
P(f"   header batch=/work_mul=/ndiv= == run's (B,WM,NDIV) and n == (1,000,003*WM)//NDIV; every SAMPLE batch=/work_mul=/ndiv= == (B,WM,NDIV): {knob_field_ok}")
P(f"   every CELL spv= name is an archived .emitted.spv (no .iter -- the corpus is byte-identical this session): {spv_identity_ok}")
P(f"   SAMPLE lines: 450 per run (18 ok cells x 25 rounds) in 9/9 runs: {sample_counts_ok}")
P(f"   VERIFY mismatch total over all runs: {verify_mismatch_total} (per-arm: "
  + ", ".join(f"{t}={verify_mismatch_by_arm[t]}" for t in TAGS)
  + ") -- bit-exact correctness re-check inside every run; frozen INVALIDATION criterion (protocol section 4): >0 in any run makes that run DEFECTIVE and the arm INVALID")
P(f"   forcing reality (pipeline-ok cell-runs where probe_size==forced and probe_nsub==wg/forced): {forcing_ok}/{forcing_total}")
P(f"   S=8 cells fail-closed (pipeline=FAIL, forced=8): {s8_fail} cell-runs (6 per run x 9 runs = 54 expected)")
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

P("2. THE MEASURED BRACKETS (pooled median gpu_ticks; THE READING = hi")
P("   r1-3 = one 3-run block x 25 rounds per cell):")
P("   each row: (sum,128,S=16) exact value, then min..max over the 18")
P("   pipeline-ok cells; host_ns at (sum,128,S=16)")
P("")
P("   unit      B  WM   NDIV    n        total-nominal  (sum,128,16)  min..max over 18 cells   host_ns")
for tag in TAGS:
    b, wm, dd = ARMB[tag], ARMW[tag], ARMD[tag]
    n = (N_BASE * wm) // dd
    for lbl, rs in [(f"{tag}", ARMR[tag])]:
        vals = [pooled_runs(tag, k, rs) for k in ok_cells]
        v16 = pooled_runs(tag, sum128, rs)
        hn = pooled_host_runs(tag, sum128, rs)
        tot = b * n / N_BASE
        P(f"   {lbl:<9} {b}  {wm:<5} {dd:<6} {n:>8}  {tot:>12.6f}  {v16:>10.0f}  {min(vals):>8.0f}..{max(vals):<8.0f}  {hn:>9.0f}")
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
P("   anything else INTERMEDIATE/MIXED; THE READING = 3 fresh processes):")
P("")
for tag in TAGS:
    b, wm, dd = ARMB[tag], ARMW[tag], ARMD[tag]
    n = (N_BASE * wm) // dd
    if tag == "hi":
        P(f"   class THE READING (runs [1, 2, 3], B=3, WM=1024, NDIV=4033, n={n}, UTC day 2026-10-28): {INFO['hi']['cls']}  (sum,128,16) {INFO['hi']['m']:.0f}  18-cell {INFO['hi']['mn']:.0f}..{INFO['hi']['mx']:.0f}")
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

# C1 first (prerequisite; the bar's qualification depends on it)
c1_c2_ok = CLASS["c2"] == "FLOOR"
c1_parts = [f"c2 satisfies FLOOR (committed floor band 31..32 at B=2): {c1_c2_ok}"]
v8 = pooled_runs("c8", sum128, ARMR["c8"])
c1_c8_ok = abs(v8 - COMMITTED["c8"]) <= 0.05 * COMMITTED["c8"]
c1_parts.append(f"c8 (sum,128,16) pooled median {v8:.0f} within +/-5% of committed {COMMITTED['c8']} ({COMMITTED_SRC['c8']}): {c1_c8_ok}")
c1_ok = c1_c2_ok and c1_c8_ok
P("   C1 ARCHIVED CONTROL REPLICATION (numeric agreement with the committed")
P("   value at the control's OWN (B,WORK_MUL,NDIV) -- the a-set runs the")
P("   ARCHIVED spv bytes through the byte-identical session-31 instrument,")
P("   so this pins the environment as well):")
for s in c1_parts:
    P(f"     {s}")
if c1_ok:
    P("     VERDICT: branch (a) both controls satisfy their criteria --")
    P("     the bar qualification (B1) is evaluated against the row question.")
else:
    P("     VERDICT: branch (b) replication discrepancy (bearing on the")
    P("     environment pin); the bar qualification is FLAGGED; cause UNMEASURED.")
P("")

# B1 the bar qualification (the row question)
P("   B1 THE BAR QUALIFICATION (the row question; settle-bar.txt section 2")
P("   READING criteria: C1 (a), VERIFY mismatch 0 everywhere, byte-identical")
P("   build pins, custody GO before builds and runs):")
verify0 = verify_mismatch_total == 0
P(f"     C1 (a): {c1_ok}; VERIFY mismatch 0 everywhere: {verify0}")
P("     build pins byte-identical and custody GO before builds/runs: see")
P("     build-census-s31.txt / host-verify-s31.txt (custody facts, outside")
P("     the run logs this route parses).")
qualifies = c1_ok and verify0
if qualifies:
    P("     (run-log parts of the criterion hold; combined with the custody")
    P("     facts the record fixes B1:) branch (a) QUALIFYING -- the reading")
    P("     is COUNTED 1/4 (the FIRST qualifying reading of UTC day")
    P("     2026-10-28), enters the settle-bar ledger with flag=none, and")
    P("     the frozen evaluator's verdict is the bar letter (B2).")
else:
    P("     branch (b) FLAGGED -- no class is counted; the session consumes")
    P("     no day slot.")
P("")

# B2 shape (the actual verdict comes from settle-bar-eval.py over the ledger)
P("   B2 THE BAR LETTER: the frozen evaluator settle-bar-eval.py run over")
P("   the ledger after this session's append (bar-eval-s31.txt); the")
P("   verdict string there is the letter -- never hand-written here.")
P("")

# W1 the cross-UTC-day reading against the flip picture (descriptive)
P("   W1 (pre-registered, descriptive) THE CROSS-UTC-DAY READING AGAINST")
P("   THE FLIP PICTURE (quote-only L7 priors; NO bracket narrowing -- L5):")
P(f"     prior readings (all UTC day 2026-10-27): " +
  " / ".join(f"{m} {c} (min {mn}, {src})" for m, c, mn, src in HI_PRIOR))
P(f"     THIS READING (UTC day 2026-10-28, MEASURED HERE): "
  f"{INFO['hi']['m']:.0f} {INFO['hi']['cls']} (18-cell min {INFO['hi']['mn']:.0f}, max {INFO['hi']['mx']:.0f})")
inband = all(abs(INFO['hi']['m'] - ref) <= 0.05 * ref for ref in BAR_REFS)
P(f"     in-band vs the bar's frozen refs {BAR_REFS[0]} / {BAR_REFS[1]} / {BAR_REFS[2]} (within +/-5% of EACH): {inband}")
P("     ONE cross-UTC-day reading does not settle the bar (V4 PENDING);")
P("     no causal mechanism is claimed or measured.")
P("")

# W2 the B=3 class-vs-per-dispatch-work row (descriptive)
P("   W2 (pre-registered, descriptive) THE B=3 CLASS-VS-PER-DISPATCH-")
P("   WORK ROW: this session adds NO new grid point -- it re-reads")
P("   253,906 with ONE cross-UTC-day reading placed at that grid (committed")
P("   points QUOTE-ONLY L7; NO interpolation (L5); class granularity only;")
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
        P(f"     253906     0.2539052     {HI_PRIOR[0][0]:>5}  {'CAPTURED*':<20} session 26 (quote-only)")
        P(f"     253906     0.2539052     {HI_PRIOR[1][0]:>5}  {HI_PRIOR[1][1]:<20} session 27 (quote-only)")
        P(f"     253906     0.2539052     {HI_PRIOR[2][0]:>5}  {HI_PRIOR[2][1]:<20} session 28 (quote-only)")
        for m, c, mn, s in HI_PRIOR[3:]:
            P(f"     253906     0.2539052     {m:>5}  {c:<20} {s} (quote-only)")
        P(f"     253906     0.2539052     {INFO['hi']['m']:>5.0f}  {INFO['hi']['cls']:<20} THIS SESSION (day 2026-10-28)")
        _inserted = True
    P(f"     {n:<10} {lbl:<13} {ticks:>5}  {cls:<20} {src} (quote-only)")
P("")

# W3 the per-run comparison (descriptive)
P("   W3 (pre-registered, descriptive) THE PER-RUN VIEW (DESCRIPTIVE --")
P("   the per-run unit is 25 rounds per cell, NOT the frozen 3-run unit --")
P("   L10):")
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
P("     " + ", ".join(f"{t} {hn[t]:.0f}" for t in TAGS))
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

P("4. VERDICT SUMMARY: C1 (a)={0}; THE READING {1} (sum,128,16) {2:.0f}")
out[-1] = out[-1].format(c1_ok, INFO["hi"]["cls"], INFO["hi"]["m"])
P("   (18-cell min {0:.0f}) on UTC day 2026-10-28; B1 (run-log parts) {1};"
  .format(INFO["hi"]["mn"], "(a) qualifying" if qualifies else "(b) FLAGGED"))
P("   the bar letter is settle-bar-eval.py's verdict over the ledger")
P("   (bar-eval-s31.txt). WHY any class flips across sessions/days is")
P("   UNMEASURED and NO causal mechanism is claimed.")

with open(os.path.join(HERE, "publication-s31.txt"), "w") as f:
    f.write("\n".join(out) + "\n")
