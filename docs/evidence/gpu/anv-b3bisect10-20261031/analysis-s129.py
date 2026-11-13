#!/usr/bin/env python3
"""JUN-59 session 129 analysis -- THE B=3 PER-DISPATCH-WORK THRESHOLD
BISECT, TENTH CUT -- THE POINT-CLASS STABILITY CUT (the C2 (b)
confrontation; NO new grid point is measured; the committed bracket
stays exactly (254,557, 255,208]).
The MEASUREMENT half of the s126 pre-registration
(anv-b3bisect10prereg-20261031/protocol.txt, frozen 2026-10-31T07:35:39Z
BEFORE any run log of this cut existed).

Route (frozen in protocol.txt section 7): this script parses ONLY the 42
committed run logs in its own directory (run-<tag>-r<NN>.txt) and NAMED
COMMITTED WANT SOURCES (the quote-only values of protocol section 3,
parsed here from committed bytes -- never transcribed) and writes
publication-s129.txt. No other input. Deterministic: running it twice
yields byte-identical publication-s129.txt (checked by diff after the
recorded run). Every want source is parsed with fail-closed regexes; a
want that does not parse aborts (assert).

Frozen classification (protocol section 4): over the 18 pipeline-ok
cells, pooled median gpu_ticks over the unit's runs x 25 rounds per
cell; FLOOR = <= 100 at ALL 18 cells; CAPTURED = >= 1000 at ALL 18
cells; anything else INTERMEDIATE/MIXED. The pre-registered
classification UNIT is the BLOCK (4 disjoint blocks of 3 runs per
B=3 arm: r01..r03 / r04..r06 / r07..r09 / r10..r12) plus the pooled-12
(a named extension, reported alongside -- never instead of -- the
block classes). Controls have k=3: one block each.
"""
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

GPU = os.path.join(HERE, "..")

# tag -> (BATCH, WORK_MUL, NDIV, k), frozen protocol section 0 arm table
# (5 rows = 42 fresh processes)
ARMS = [("c2", 2, 1, 1, 3), ("lo", 3, 405, 1591, 12), ("mid", 3, 248, 973, 12),
        ("hi", 3, 1213, 4753, 12), ("c8", 8, 1, 1, 3)]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMW = {a[0]: a[2] for a in ARMS}
ARMD = {a[0]: a[3] for a in ARMS}
ARMK = {a[0]: a[4] for a in ARMS}
N_BASE = 1000003
BLOCKS = {t: [tuple(range(3 * j - 2, 3 * j + 1)) for j in range(1, 5)]
          for t in ("lo", "mid", "hi")}
UNIT12 = tuple(range(1, 13))


def flat(text):
    return re.sub(r"\s+", " ", text)


def parse1(text, pattern, what):
    m = re.search(pattern, flat(text))
    assert m is not None, f"WANT SOURCE NOT PARSED: {what}"
    return m.group(1).strip()


# ---- NAMED COMMITTED WANT SOURCES (protocol section 3; parsed from
# ---- committed bytes, never transcribed; fail-closed) ----
s27c = open(os.path.join(GPU, "anv-b3bisect7-20261027",
                         "derivation-census-s27.txt")).read()
pub121 = open(os.path.join(GPU, "anv-b3bisect8-20261031",
                           "publication-s121.txt")).read()
pub125 = open(os.path.join(GPU, "anv-b3bisect9-20261031",
                           "publication-s125.txt")).read()

# committed controls (s27 census): "c2 31 (floor band 31..32); c8 32,915 ..."
ctl = parse1(s27c, r"(committed controls: c2 \d+ \(floor band [\d.]+\.\.[\d.]+\); "
                   r"c8 [\d,]+ \(session 4 pooled median\))", "committed controls")
m = re.search(r"c2 (\d+) \(floor band (\d+)\.\.(\d+)\); c8 ([\d,]+)", ctl)
assert m, "committed controls shape"
C2_COMMITTED = int(m.group(1))
C2_BAND = (int(m.group(2)), int(m.group(3)))
C8_COMMITTED = int(m.group(4).replace(",", ""))

# lo history at the (405,1591) pair (n=254,557) -- BOTH committed readings
m = re.search(r"mid 3 405 1591 254557 \S+ (\d+) \d+\.\.\d+ "
              r"(\d+\.\.\d+) \d+", flat(pub121))
assert m is not None, "WANT SOURCE NOT PARSED: lo s121 row"
LO121_MED, LO121_18 = int(m.group(1)), m.group(2)
LO121_CLASS = parse1(pub121, r"class mid \(B=3, WM=405, NDIV=1591, n=254557, "
                             r"\S+ nominal units\): (\S+(?:/\S+)*)", "lo s121 class")
m = re.search(r"lo 3 405 1591 254557 \S+ (\d+) \d+\.\.\d+ "
              r"(\d+\.\.\d+) \d+", flat(pub125))
assert m is not None, "WANT SOURCE NOT PARSED: lo s125 row"
LO125_MED, LO125_18 = int(m.group(1)), m.group(2)
LO125_CLASS = parse1(pub125, r"class lo \(B=3, WM=405, NDIV=1591, n=254557, "
                             r"\S+ nominal units\): (\S+(?:/\S+)*)", "lo s125 class")

# mid row at (248,973) (n=254,882) -- the ninth cut's committed reading
m = re.search(r"mid 3 248 973 254882 \S+ (\d+) \d+\.\.\d+ "
              r"(\d+\.\.\d+) \d+", flat(pub125))
assert m is not None, "WANT SOURCE NOT PARSED: mid s125 row"
MID125_MED, MID125_18 = int(m.group(1)), m.group(2)
MID125_CLASS = parse1(pub125, r"class mid \(B=3, WM=248, NDIV=973, n=254882, "
                              r"\S+ nominal units\): (\S+(?:/\S+)*)", "mid s125 class")

# hi history at the (1213,4753) pair (n=255,208)
trio_txt = parse1(s27c, r"the \(1213,4753\) pair \(session 24 mid / session 25 hi "
                        r"/ session 26 hi\): ([\d,/]+)", "hi trio")
HI_TRIO = tuple(int(x.replace(",", "")) for x in trio_txt.split("/"))
m = re.search(r"hi 3 1213 4753 255208 \S+ (\d+) \d+\.\.\d+ "
              r"\d+\.\.\d+ \d+", flat(pub121))
assert m is not None, "WANT SOURCE NOT PARSED: hi s121 row"
HI121_MED = int(m.group(1))
HI121_CLASS = parse1(pub121, r"class hi \(B=3, WM=1213, NDIV=4753, n=255208, "
                             r"\S+ nominal units\): (\S+(?:/\S+)*)", "hi s121 class")
m = re.search(r"hi 3 1213 4753 255208 \S+ (\d+) \d+\.\.\d+ "
              r"(\d+\.\.\d+) \d+", flat(pub125))
assert m is not None, "WANT SOURCE NOT PARSED: hi s125 row"
HI125_MED, HI125_18 = int(m.group(1)), m.group(2)
HI125_CLASS = parse1(pub125, r"class hi \(B=3, WM=1213, NDIV=4753, n=255208, "
                             r"\S+ nominal units\): (\S+(?:/\S+)*)", "hi s125 class")

# the committed B=3 class-vs-per-dispatch-work row (QUOTE-ONLY): the
# s125 W2 table's committed rows (parsed from publication-s125.txt's
# committed bytes -- the 12 "(quote-only)" rows plus the ninth cut's
# own three measured rows, which are committed content of session 125)
B3ROW = []
for line in pub125.splitlines():
    m = re.match(r"\s+(\d+)\s+(\S+)\s+(\d+)\s+(\S+)\s+(.+?) \(quote-only\)$", line)
    if m:
        B3ROW.append((m.group(2), int(m.group(1)), int(m.group(3)),
                      m.group(4).rstrip("*"), m.group(5), ""))
    m = re.match(r"\s+(\d+)\s+(\S+)\s+(\d+)\s+(\S+)\s+(?:this|THIS) "
                 r"(?:session|SESSION) \((lo|mid|hi), (.+?)\)$", line)
    if m:
        B3ROW.append((m.group(2), int(m.group(1)), int(m.group(3)),
                      m.group(4).rstrip("*"),
                      f"session 125 (the ninth cut, {m.group(5)})",
                      m.group(6)))
assert len(B3ROW) == 15, f"B3ROW committed parsed {len(B3ROW)} want 15"
B3ROW.sort(key=lambda r: r[1])

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
            cells[int(m.group(1))] = dict(spv=m.group(2), op=m.group(3),
                                          wg=int(m.group(4)), forced=m.group(5),
                                          probe_size=int(m.group(6)),
                                          probe_nsub=int(m.group(7)),
                                          probe_wg=int(m.group(8)),
                                          pipeline=m.group(9), void=int(m.group(10)))
        elif line.startswith("VERIFY "):
            m = verify_re.match(line)
            assert m, line
            verifies.append((int(m.group(1)), int(m.group(2)), int(m.group(3)),
                             int(m.group(4))))
        elif line.startswith("SAMPLE "):
            m = sample_re.match(line)
            assert m, line
            samples.append((int(m.group(1)), int(m.group(2)), int(m.group(3)),
                            int(m.group(4)), int(m.group(5)), int(m.group(6)),
                            float(m.group(7)), float(m.group(8)), int(m.group(9))))
        elif line.startswith("# done"):
            header.append(line)
    return cells, verifies, samples, header


def med(xs):
    return statistics.median(xs)


out = []
P = out.append
P("JUN-59 session 129 -- THE B=3 PER-DISPATCH-WORK THRESHOLD BISECT,")
P("TENTH CUT -- THE POINT-CLASS STABILITY CUT (the C2 (b) confrontation;")
P("NO new grid point is measured -- the first cut in the chain that")
P("measures none; the committed bracket stays exactly (254,557,")
P("255,208] n-units). publication -- the MEASUREMENT half of the s126")
P("pre-registration (anv-b3bisect10prereg-20261031/protocol.txt, frozen")
P("2026-10-31T07:35:39Z BEFORE any run log of this cut existed).")
P("Produced ONLY by analysis-s129.py over the 42 committed run logs in")
P("this directory (run-<tag>-r<NN>.txt) and the NAMED COMMITTED WANT")
P("SOURCES parsed below (protocol section 3 quote-only values, parsed")
P("from committed bytes, never transcribed). Arms = binary compile-time")
P("(BATCH, WORK_MUL, NDIV); n = (1,000,003*WORK_MUL)/NDIV (integer")
P("floor). The row question (protocol section 0): AT FIXED B=3 AND")
P("BYTE-IDENTICAL PINNED BINARIES, IS THE CLASS LABEL OF A COMMITTED")
P("BISECT POINT STABLE ACROSS FRESH PROCESSES? -- each of the three")
P("committed points is measured in 12 fresh processes at its pinned")
P("byte-identical binary and classified in 4 disjoint frozen-method")
P("blocks of 3 runs plus the pooled 12: lo (405,1591) n=254,557 (THE")
P("DISPUTED POINT); mid (248,973) n=254,882 (the ninth cut's row")
P("point); hi (1213,4753) n=255,208 (the bracket's upper anchor).")
P("RESUMABILITY RULE (frozen, protocol section 0): the stability")
P("precondition HOLDS iff C2 in {(a),(b)} AND C3 in {(a),(b)} AND")
P("W1 == (a); only then may the bisect narrowing channel re-open in a")
P("NEW pre-registered cut (NOT queued here). If any of C2 (c) / C3 (c)")
P("/ W1 (c) fires, L9 binds at that point. Under ALL outcomes: NO")
P("bracket movement, NO narrowing, no boundary between grid points is")
P("ever claimed (L5). BAR NON-INTERFERENCE: the cut's runs are BISECT")
P("CONTENT and NOT bar readings -- no ledger append, no day-slot")
P("consumption, no bar verdict movement, no Rule 4 row or :measured?")
P("flag movement. WHY any class label occurs or flips is UNMEASURED")
P("(L2 binds; L9 names the flip content); NO causal mechanism is")
P("claimed. 1 tick = timestampPeriod = 52.083 ns.")
P("")

P("0. NAMED COMMITTED WANT SOURCES (parsed here from committed bytes;")
P("   every value below is a QUOTE-ONLY comparison value and never this")
P("   session's measurement):")
P(f"   committed controls (s27 census): {ctl}")
P(f"   lo = the (405,1591) pair at n=254,557 -- BOTH committed readings:")
P(f"   session 121 (the eighth cut, mid arm): {LO121_MED}, 18-cell "
  f"{LO121_18},")
P(f"   class {LO121_CLASS}")
P(f"   session 125 (the ninth cut, lo arm): {LO125_MED}, 18-cell "
  f"{LO125_18},")
P(f"   class {LO125_CLASS}")
P(f"   mid = the (248,973) pair at n=254,882 -- session 125 (the ninth")
P(f"   cut's row point): {MID125_MED}, 18-cell {MID125_18}, class "
  f"{MID125_CLASS}")
P(f"   hi = the (1213,4753) pair at n=255,208 -- committed trio (s27")
P(f"   census): {trio_txt}; session 121: {HI121_MED} {HI121_CLASS};")
P(f"   session 125: {HI125_MED}, 18-cell {HI125_18}, class "
  f"{HI125_CLASS}")
P(f"   committed B=3 row (publication-s125.txt W2 table, committed")
P(f"   bytes): {len(B3ROW)} grid points parsed")
P("")

# ---- load everything, integrity checks ----
data = {}
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
    b, wm, dd, k = ARMB[tag], ARMW[tag], ARMD[tag], ARMK[tag]
    for r in range(1, k + 1):
        fn = f"run-{tag}-r{r:02d}.txt"
        cells, verifies, samples, header = load(os.path.join(HERE, fn))
        data[(tag, r)] = (cells, verifies, samples, header)
        keys = tuple(sorted((kk, v["op"], v["wg"], v["forced"], v["pipeline"])
                            for kk, v in cells.items()))
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
                if (not mb or int(mb.group(1)) != b) \
                   or (not mbar or int(mbar.group(1)) != 0) \
                   or (not mmu or int(mmu.group(1)) != wm) \
                   or (not mdi or int(mdi.group(1)) != dd):
                    knob_field_ok = False
                    integrity.append(f"HEADER knob FIELD MISMATCH in {fn}: {l}")
                if not mn or int(mn.group(1)) != (N_BASE * wm) // dd:
                    knob_field_ok = False
                    integrity.append(f"HEADER n= FIELD MISMATCH in {fn}: {l}")
        for kk, v in cells.items():
            ok = v["spv"].endswith(".emitted.spv") and ".iter" not in v["spv"]
            if not ok:
                spv_identity_ok = False
                integrity.append(f"CELL spv SET MISMATCH in {fn} idx={kk}: {v['spv']}")
        for (idx, ch, mis, okv) in verifies:
            verify_mismatch_total += mis
            verify_mismatch_by_arm[tag] += mis
            c = cells[idx]
            if c["pipeline"] == "ok":
                forcing_total += 1
                exp_s = 32 if c["forced"] == "default" else int(c["forced"])
                if (c["probe_size"] == exp_s
                        and c["probe_nsub"] == (c["wg"] // exp_s)):
                    forcing_ok += 1
            else:
                if c["forced"] == "8":
                    s8_fail += 1
        ok_cells = [kk for kk, v in cells.items() if v["pipeline"] == "ok"]
        exp = len(ok_cells) * 25
        if len(samples) != exp:
            sample_counts_ok = False
            integrity.append(f"SAMPLE COUNT {len(samples)} != {exp} in {fn}")
        for (rnd, idx, bt, mt, dt, gt, gn, pdn, hn_) in samples:
            if bt != b or mt != wm or dt != dd:
                knob_field_ok = False
                integrity.append(f"SAMPLE knob FIELD {bt},{mt},{dt} != {b},{wm},{dd} in {fn}")

P("1. INTEGRITY (computed over the 42 logs):")
P(f"   runs parsed: 42 (c2 x3, lo x12, mid x12, hi x12, c8 x3 -- the")
P(f"   frozen section 0 arm table's 5 rows govern the count); cell map")
P(f"   identical across runs: "
  f"{cell_keys is not None and not any('CELL MAP' in i for i in integrity)}")
P(f"   headers byte-identical across all runs outside the # n= knob line: {header_ok}")
P(f"   header batch=/work_mul=/ndiv= == run's (B,WM,NDIV) and n == "
  f"(1,000,003*WM)//NDIV; every SAMPLE batch=/work_mul=/ndiv= == (B,WM,NDIV): "
  f"{knob_field_ok}")
P(f"   every CELL spv= name is an archived .emitted.spv (no .iter -- the "
  f"corpus is byte-identical this session): {spv_identity_ok}")
P(f"   SAMPLE lines: 450 per run (18 ok cells x 25 rounds) in 42/42 runs: "
  f"{sample_counts_ok}")
P(f"   VERIFY mismatch total over all runs: {verify_mismatch_total} (per-arm: "
  + ", ".join(f"{t}={verify_mismatch_by_arm[t]}" for t in TAGS)
  + ") -- bit-exact correctness re-check inside every run; frozen "
    "INVALIDATION criterion (protocol section 4): >0 in any run makes that "
    "run DEFECTIVE and the arm INVALID (its block classes not evaluable)")
P(f"   forcing reality (pipeline-ok cell-runs where probe_size==forced and "
  f"probe_nsub==wg/forced): {forcing_ok}/{forcing_total}")
P(f"   S=8 cells fail-closed (pipeline=FAIL, forced=8): {s8_fail} cell-runs "
  f"(6 per run x 42 runs = 252 expected)")
if integrity:
    for i in integrity:
        P(f"   !! {i}")
P("")


def cell_median(tag, runs, idx, field=5):
    xs = []
    for r in runs:
        cells, verifies, samples, header = data[(tag, r)]
        xs += [s[field] for s in samples if s[1] == idx]
    return med(xs)


ok_cells = sorted([k for k, v in data[("c2", 1)][0].items()
                   if v["pipeline"] == "ok"])


def ckey(idx):
    c = data[("c2", 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])


sum128 = [k for k in ok_cells if ckey(k) == ("sum", 128, "16")][0]


def unit_class(tag, runs):
    vals = [cell_median(tag, runs, k) for k in ok_cells]
    if all(v <= 100 for v in vals):
        return "FLOOR"
    if all(v >= 1000 for v in vals):
        return "CAPTURED"
    return "INTERMEDIATE/MIXED"


def unit_summary(tag, runs):
    vals = [cell_median(tag, runs, k) for k in ok_cells]
    v16 = cell_median(tag, runs, sum128)
    return v16, min(vals), max(vals), unit_class(tag, runs)


P("2. PER-RUN DESCRIPTIVE (W2/L10: per-run quantities are DESCRIPTIVE")
P("   ONLY and never classify; each run: (sum,128,S=16) per-cell median")
P("   gpu_ticks over its 25 rounds, then min..max over the 18 pipeline-ok")
P("   cells of the per-cell medians, then the per-run host_ns median at")
P("   (sum,128,S=16)):")
P("")
for tag in TAGS:
    b, wm, dd, k = ARMB[tag], ARMW[tag], ARMD[tag], ARMK[tag]
    n = (N_BASE * wm) // dd
    P(f"   {tag} (B={b}, WM={wm}, NDIV={dd}, n={n}, k={k}):")
    for r in range(1, k + 1):
        runs = (r,)
        vals = [cell_median(tag, runs, kk) for kk in ok_cells]
        v16 = cell_median(tag, runs, sum128)
        hn = cell_median(tag, runs, sum128, field=8)
        P(f"     r{r:02d}  (sum,128,16) {v16:>7.0f}   18-cell "
          f"{min(vals):>6.0f}..{max(vals):<6.0f}   host_ns {hn:.0f}")
    P("")
P("")

P("3. BLOCK + POOLED-12 CLASSIFICATION (the frozen method of protocol")
P("   section 4 applied to the pre-registered classification units:")
P("   block j (j=1..4) = runs r(3j-2), r(3j-1), r(3j); pooled-12 pools")
P("   all 12 runs x 25 rounds per cell (a NAMED EXTENSION of the frozen")
P("   3-run method, reported alongside -- never instead of -- the four")
P("   block classes, protocol section 0). Controls have k=3: one block")
P("   each. Each unit row: pooled median gpu_ticks at (sum,128,S=16),")
P("   18-cell min..max of per-cell pooled medians, class.")
P("")
unit_rows = {}
for tag in TAGS:
    b, wm, dd, k = ARMB[tag], ARMW[tag], ARMD[tag], ARMK[tag]
    n = (N_BASE * wm) // dd
    P(f"   {tag} (B={b}, WM={wm}, NDIV={dd}, n={n}, "
      f"{b * n / N_BASE:.6f} nominal total units):")
    units = []
    if tag in BLOCKS:
        for j, runs in enumerate(BLOCKS[tag], 1):
            units.append((f"block{j}", runs))
        units.append(("pooled-12", UNIT12))
    else:
        units.append(("block1 (k=3 control)", tuple(range(1, k + 1))))
    for label, runs in units:
        v16, lo_, hi_, cls = unit_summary(tag, runs)
        runlabel = ",".join(f"{r:02d}" for r in runs)
        P(f"     {label:<20} runs {runlabel:<22} (sum,128,16) {v16:>7.0f}   "
          f"18-cell {lo_:>6.0f}..{hi_:<6.0f}   {cls}")
        unit_rows[(tag, label)] = (v16, lo_, hi_, cls, runs)
    P("")


def letter_stability(tag, want):
    """C2/C3 style letter: (a) all-blocks+pooled12 == want; (b) all ==
    the other stable class; (c) BLOCK-UNSTABLE; (d) INVALID."""
    if verify_mismatch_by_arm[tag] > 0:
        return "(d)", None
    labels = [f"block{j}" for j in range(1, 5)]
    classes = [unit_rows[(tag, l)][3] for l in labels]
    pooled_cls = unit_rows[(tag, "pooled-12")][3]
    other = "CAPTURED" if want == "INTERMEDIATE/MIXED" else "INTERMEDIATE/MIXED"
    if all(c == want for c in classes) and pooled_cls == want:
        return "(a)", classes
    if all(c == other for c in classes) and pooled_cls == other:
        return "(b)", classes
    return "(c)", classes


P("4. PRE-REGISTERED LETTERS (thresholds frozen in protocol section 4:")
P("   FLOOR <= 100 ticks at all 18 cells; CAPTURED >= 1000 ticks at all")
P("   18; anything else INTERMEDIATE/MIXED; the re-defined C2/C3/W1 of")
P("   protocol section 5 -- the ninth cut's meanings do NOT carry):")
P("")

# C1 (prerequisite; W letters depend on it)
v_c2 = unit_rows[("c2", "block1 (k=3 control)")][0]
v_c8 = unit_rows[("c8", "block1 (k=3 control)")][0]
cls_c2 = unit_rows[("c2", "block1 (k=3 control)")][3]
cls_c8 = unit_rows[("c8", "block1 (k=3 control)")][3]
c1_c2_ok = cls_c2 == "FLOOR" and C2_BAND[0] <= v_c2 <= C2_BAND[1]
c1_c8_ok = abs(v_c8 - C8_COMMITTED) <= 0.05 * C8_COMMITTED
c1_ok = c1_c2_ok and c1_c8_ok
P("   C1 ARCHIVED CONTROL REPLICATION (prerequisite; W letters depend on")
P("   it): controls have k=3: one block each, the frozen method exactly:")
P(f"     c2 (sum,128,S=16) pooled median {v_c2:.0f}, class {cls_c2} "
  f"(committed floor band {C2_BAND[0]}..{C2_BAND[1]} at B=2): {c1_c2_ok}")
P(f"     c8 (sum,128,S=16) pooled median {v_c8:.0f} within +/-5% of "
  f"committed {C8_COMMITTED} (session 4 pooled median): {c1_c8_ok}")
if c1_ok:
    P("     VERDICT: branch (a) both controls satisfy their criteria --")
    P("     the W letters are evaluated against the row question.")
else:
    P("     VERDICT: branch (b) replication discrepancy (W interpretation")
    P("     FLAGGED); cause UNMEASURED.")
P("")

# C2 (lo, the disputed point)
c2_letter, c2_classes = letter_stability("lo", "INTERMEDIATE/MIXED")
P("   C2 POINT-CLASS STABILITY AT THE DISPUTED POINT -- lo")
P("   (BATCH=3,WORK_MUL=405,NDIV=1591) at n=254,557 (the s125 C2 (b)")
P(f"   named content; 4 blocks + pooled-12): {c2_letter}")
P(f"     block classes: {c2_classes}; pooled-12 class: "
  f"{unit_rows[('lo', 'pooled-12')][3]}")
P(f"     (sum,128,S=16): blocks "
  + " / ".join(f"{unit_rows[('lo', f'block{j}')][0]:.0f}" for j in range(1, 5))
  + f" ; pooled-12 {unit_rows[('lo', 'pooled-12')][0]:.0f}")
if c2_letter == "(a)":
    P("     (a) STABLE-INTERMEDIATE: all 4 block classes AND the pooled-12")
    P("     class are INTERMEDIATE/MIXED (the s125 CAPTURED reading is")
    P("     named tail content of the point's committed history).")
elif c2_letter == "(b)":
    P("     (b) STABLE-CAPTURED: all 4 block classes AND the pooled-12")
    P("     class are CAPTURED (the s121 INTERMEDIATE/MIXED reading is")
    P("     named tail content).")
elif c2_letter == "(c)":
    P("     (c) BLOCK-UNSTABLE: the 4 block classes are not all equal, or")
    P("     the pooled-12 class differs from a unanimous block class (the")
    P("     class at this point is BLOCK-RUN-UNSTABLE at the frozen")
    P("     threshold -- the instability is CONFIRMED at this point and")
    P("     quantified in W2).")
else:
    P("     (d) INVALID: the frozen INVALIDATION criterion leaves C2")
    P("     unevaluable.")
P("     NAMED, NOT HIDDEN: branches (a) and (b) do NOT adjudicate which")
P("     committed reading was 'right' -- both stay committed content;")
P("     they name one reading as tail content of a stable distribution.")
P("     WHY any branch occurs is UNMEASURED.")
P("")

# C3 (mid, the ninth cut's row point)
c3_letter, c3_classes = letter_stability("mid", "INTERMEDIATE/MIXED")
P("   C3 POINT-CLASS STABILITY AT THE NINTH CUT'S ROW POINT -- mid")
P("   (BATCH=3,WORK_MUL=248,NDIV=973) at n=254,882 (4 blocks +")
P(f"   pooled-12): {c3_letter}")
P(f"     block classes: {c3_classes}; pooled-12 class: "
  f"{unit_rows[('mid', 'pooled-12')][3]}")
P(f"     (sum,128,S=16): blocks "
  + " / ".join(f"{unit_rows[('mid', f'block{j}')][0]:.0f}" for j in range(1, 5))
  + f" ; pooled-12 {unit_rows[('mid', 'pooled-12')][0]:.0f}")
P(f"     as C2's letters ((a) STABLE-INTERMEDIATE / (b) STABLE-CAPTURED /")
P(f"     (c) BLOCK-UNSTABLE / (d) INVALID). NAMED, NOT HIDDEN: this")
P(f"     cut's C3 is NOT the pair-representation check of cuts 2-9 (no")
P(f"     same-ratio pair is measured this cut); the committed C3")
P(f"     scoreboard (s24 (b)/s25 (a)/s26 (b)/s27 (a)/s121 (a)/s125 (a))")
P(f"     is untouched content.")
P("")

# W1 (hi, the upper anchor) + the cut verdict
w1_letter, w1_classes = letter_stability("hi", "CAPTURED")
P("   W1 THE ROW QUESTION -- POINT-CLASS STABILITY AT THE BRACKET'S")
P("   UPPER ANCHOR -- hi (BATCH=3,WORK_MUL=1213,NDIV=4753) at")
P(f"   n=255,208 (4 blocks + pooled-12): {w1_letter}")
P(f"     block classes: {w1_classes}; pooled-12 class: "
  f"{unit_rows[('hi', 'pooled-12')][3]}")
P(f"     (sum,128,S=16): blocks "
  + " / ".join(f"{unit_rows[('hi', f'block{j}')][0]:.0f}" for j in range(1, 5))
  + f" ; pooled-12 {unit_rows[('hi', 'pooled-12')][0]:.0f}")
if w1_letter == "(a)":
    P("     (a) STABLE-CAPTURED: all 4 block classes AND the pooled-12")
    P("     class are CAPTURED (the committed CAPTURED content -- trio +")
    P("     s121 + s125 -- replicates as stable).")
elif w1_letter == "(b)":
    P("     (b) STABLE-INTERMEDIATE: all 4 block classes AND the pooled-12")
    P("     class are INTERMEDIATE/MIXED (pre-named contradiction of the")
    P("     committed CAPTURED content at the anchor).")
elif w1_letter == "(c)":
    P("     (c) BLOCK-UNSTABLE (the upper anchor's class is itself")
    P("     run-unstable -- the flip bracket's upper end rests on nothing")
    P("     stable).")
else:
    P("     (d) INVALID.")
holds = (c2_letter in ("(a)", "(b)") and c3_letter in ("(a)", "(b)")
         and w1_letter == "(a)")
P(f"     CUT VERDICT (pre-named composition, section 0's RESUMABILITY")
P(f"     RULE): the stability precondition "
  f"{'HOLDS' if holds else 'DOES NOT HOLD'}"
  f" (C2 {c2_letter} in {{(a),(b)}}: {c2_letter in ('(a)', '(b)')}; C3 "
  f"{c3_letter} in {{(a),(b)}}: {c3_letter in ('(a)', '(b)')}; W1 == (a): "
  f"{w1_letter == '(a)'}).")
if holds:
    P("     only now may the bisect narrowing channel re-open in a NEW")
    P("     pre-registered cut (NOT queued here) confronting the stable")
    P("     class content.")
else:
    P("     no narrowing channel re-opens; any future narrowing claim at")
    P("     the affected point(s) must pre-register its own multi-block")
    P("     stability requirement first (L9 named here, not specified")
    P("     here).")
for tg, lt in (("lo", c2_letter), ("mid", c3_letter), ("hi", w1_letter)):
    if lt == "(c)":
        P(f"     L9 BINDS at {tg}: the class label at this point is")
        P(f"     BLOCK-RUN-UNSTABLE at the frozen threshold.")
P("     Under ALL outcomes: NO bracket movement, NO narrowing, nothing")
P("     moves on the class-vs-work row (L5).")
P("")

# W2 dispersion (descriptive)
P("   W2 (pre-registered, descriptive) DISPERSION QUANTIFICATION:")
P("   the per-run 18-cell min trajectory across the 12 runs in frozen")
P("   order (the quantity observed moving across the frozen 1,000")
P("   boundary between s121 and s125 -- L9's named content):")
for tag in ("lo", "mid", "hi"):
    traj = []
    for r in range(1, 13):
        vals = [cell_median(tag, (r,), kk) for kk in ok_cells]
        traj.append(f"{min(vals):.0f}")
    P(f"     {tag} per-run 18-cell min: " + " ".join(traj))
P("   the three points placed on the committed row as grid points")
P("   (committed points QUOTE-ONLY, parsed from publication-s125.txt's")
P("   committed W2 table; NO interpolation (L5); class granularity")
P("   only; * = the session-26 point carries its C3 (b) caveat / was")
P("   SETTLED OVER to INTERMEDIATE/MIXED by the bar):")
P("")
P("     n          work-unit     ticks  class                source")
for lbl, n, ticks, cls, src, note in B3ROW:
    mark = "*" if n == 253906 else ""
    suffix = f" [{note}]" if note else ""
    P(f"     {n:<10} {lbl:<13} {ticks:>5}  {cls + mark:<20} {src}{suffix} "
      f"(quote-only)")
for tag in ("lo", "mid", "hi"):
    b, wm, dd = ARMB[tag], ARMW[tag], ARMD[tag]
    n = (N_BASE * wm) // dd
    v16, lo_, hi_, cls, runs = unit_rows[(tag, "pooled-12")]
    lbl = {254557: "0.2545562", 254882: "0.2548812", 255208: "0.2552072"}[n]
    role = {"lo": "THE DISPUTED POINT (405,1591)", "mid": "the ninth cut's "
            "row point (248,973)", "hi": "the upper anchor (1213,4753)"}[tag]
    P(f"     {n:<10} {lbl:<13} {v16:>5.0f}  {cls:<20} THIS SESSION "
      f"(pooled-12, {role})")
P("")

# W3 history comparisons (descriptive)
P("   W3 (pre-registered, descriptive) THE HISTORY COMPARISONS:")
P(f"     (i) lo blocks vs the same binary's two committed readings:")
P(f"         s121: {LO121_MED} {LO121_CLASS} 18-cell {LO121_18}; s125: "
  f"{LO125_MED} {LO125_CLASS} 18-cell {LO125_18};")
P(f"         this cut's lo blocks (sum,128,16): "
  + " / ".join(f"{unit_rows[('lo', f'block{j}')][0]:.0f}" for j in range(1, 5))
  + f"; pooled-12 {unit_rows[('lo', 'pooled-12')][0]:.0f} "
    f"{unit_rows[('lo', 'pooled-12')][3]}")
P(f"     (ii) mid blocks vs the s125 committed reading ({MID125_MED} "
  f"{MID125_CLASS}, 18-cell {MID125_18}):")
P(f"         this cut's mid blocks (sum,128,16): "
  + " / ".join(f"{unit_rows[('mid', f'block{j}')][0]:.0f}" for j in range(1, 5))
  + f"; pooled-12 {unit_rows[('mid', 'pooled-12')][0]:.0f} "
    f"{unit_rows[('mid', 'pooled-12')][3]}")
P(f"     (iii) hi blocks vs the committed CAPTURED content (trio "
  f"{trio_txt}; s121 {HI121_MED}; s125 {HI125_MED}, 18-cell "
  f"{HI125_18}):")
P(f"         this cut's hi blocks (sum,128,16): "
  + " / ".join(f"{unit_rows[('hi', f'block{j}')][0]:.0f}" for j in range(1, 5))
  + f"; pooled-12 {unit_rows[('hi', 'pooled-12')][0]:.0f} "
    f"{unit_rows[('hi', 'pooled-12')][3]}")
P("")

# X1 host_ns dispersion (descriptive)
P("   X1 (descriptive, host_ns at (sum,128,S=16); the first cut in the")
P("   chain to report host_ns dispersion -- dispersion is the cut's")
P("   subject; NOT a C criterion (L3)):")
for tag in TAGS:
    k = ARMK[tag]
    hs = [cell_median(tag, (r,), sum128, field=8) for r in range(1, k + 1)]
    P(f"     {tag}: per-run host_ns median min..max {min(hs):.0f}.."
      f"{max(hs):.0f} (spread {max(hs) - min(hs):.0f} = "
      f"{(max(hs) - min(hs)) / min(hs) * 100:.1f}% of min; k={k})")
P("     host_ns is the HOST-side proxy (L3), not a C criterion; any")
P("     excursion is NAMED, NOT HIDDEN and its cause is UNMEASURED.")
P("")

P("5. VERDICT SUMMARY: C1 (a)={0}; C2 {1}; C3 {2}; W1 {3}; stability "
  .format(c1_ok and "(a)" or "(b)", c2_letter, c3_letter, w1_letter)
  + f"precondition {'HOLDS' if holds else 'DOES NOT HOLD'}.")
P("   The point-class stability of the three committed B=3 points is as")
P("   the letters state; WHY is UNMEASURED and NO causal mechanism is")
P("   claimed. The committed bracket stays exactly (254,557, 255,208]")
P("   under ALL outcomes (L5 named N/A in its narrowing form). BAR")
P("   NON-INTERFERENCE (frozen protocol section 6): these runs are BISECT")
P("   CONTENT and NOT bar readings -- NO settle-bar-ledger.txt append, NO")
P("   UTC-day slot consumption, NO movement of the bar's SETTLED")
P("   INTERMEDIATE/MIXED verdict (the s117 committed landing), NO Rule 4")
P("   workgroup row movement, NO :measured? flag change (the")
P("   accelerator-targets rows stay exactly as ADR-0358 left them).")

with open(os.path.join(HERE, "publication-s129.txt"), "w") as f:
    f.write("\n".join(out) + "\n")
