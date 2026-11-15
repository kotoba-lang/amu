#!/usr/bin/env python3
"""JUN-59 session 132 analysis -- THE B=3 PER-DISPATCH-WORK THRESHOLD
BISECT, ELEVENTH CUT -- THE MULTI-BLOCK STABILITY REQUIREMENT CUT (the
L9 block-run-instability confrontation at mid AND hi; NO new grid point
is measured; the committed bracket stays exactly (254,557, 255,208]).
The MEASUREMENT half of the s131 pre-registration
(anv-b3bisect11prereg-20261031/protocol.txt, frozen 2026-10-31T13:50:45Z
BEFORE any run log of this cut existed).

Route (frozen in protocol.txt section 7): this script parses ONLY the 54
committed run logs in its own directory (run-<tag>-r<NN>.txt) and NAMED
COMMITTED WANT SOURCES (the quote-only values of protocol section 3,
parsed here from committed bytes -- never transcribed) and writes
publication-s132.txt. No other input. Deterministic: running it twice
yields byte-identical publication-s132.txt (checked by diff after the
recorded run). Every want source is parsed with fail-closed regexes; a
want that does not parse aborts (assert).

Frozen classification (protocol section 4): over the 18 pipeline-ok
cells, pooled median gpu_ticks over the unit's runs x 25 rounds per
cell; FLOOR = <= 100 at ALL 18 cells; CAPTURED = >= 1000 at ALL 18
cells; anything else INTERMEDIATE/MIXED. The pre-registered
classification UNIT is the BLOCK (8 disjoint blocks of 3 runs per
B=3 arm: r01..r03 / r04..r06 / r07..r09 / r10..r12 / r13..r15 /
r16..r18 / r19..r21 / r22..r24) plus the pooled-24 (a named extension,
reported alongside -- never instead of -- the eight block classes).
Controls have k=3: one block each.
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
# (4 rows = 54 fresh processes)
ARMS = [("c2", 2, 1, 1, 3), ("mid", 3, 248, 973, 24),
        ("hi", 3, 1213, 4753, 24), ("c8", 8, 1, 1, 3)]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMW = {a[0]: a[2] for a in ARMS}
ARMD = {a[0]: a[3] for a in ARMS}
ARMK = {a[0]: a[4] for a in ARMS}
N_BASE = 1000003
BLOCKS = {t: [tuple(range(3 * j - 2, 3 * j + 1)) for j in range(1, 9)]
          for t in ("mid", "hi")}
UNIT24 = tuple(range(1, 25))


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
pub129 = open(os.path.join(GPU, "anv-b3bisect10-20261031",
                           "publication-s129.txt")).read()

# committed controls (s27 census): "c2 31 (floor band 31..32); c8 32,915 ..."
ctl = parse1(s27c, r"(committed controls: c2 \d+ \(floor band [\d.]+\.\.[\d.]+\); "
                   r"c8 [\d,]+ \(session 4 pooled median\))", "committed controls")
m = re.search(r"c2 (\d+) \(floor band (\d+)\.\.(\d+)\); c8 ([\d,]+)", ctl)
assert m, "committed controls shape"
C2_COMMITTED = int(m.group(1))
C2_BAND = (int(m.group(2)), int(m.group(3)))
C8_COMMITTED = int(m.group(4).replace(",", ""))

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

# the tenth cut's committed rows (publication-s129.txt) -- the W3
# history comparisons and the W2 boundary-crossing counts
def pub129_arm(tag, wm, dd, n):
    f9 = flat(pub129)
    m = re.search(
        rf"{tag} \(B=3, WM={wm}, NDIV={dd}, n={n}, [\d.]+ nominal total units\): "
        rf"(.*?) pooled-12 runs [^ ]+ \(sum,128,16\) (\d+) 18-cell (\d+)\.\.(\d+) (\S+)",
        f9)
    assert m is not None, f"WANT SOURCE NOT PARSED: {tag} s129 arm section"
    blocks = re.findall(
        r"(block\d) runs [^ ]+ \(sum,128,16\) (\d+) 18-cell (\d+)\.\.(\d+) (\S+)",
        m.group(1))
    assert len(blocks) == 4, f"s129 {tag} block rows not parsed ({len(blocks)})"
    pooled = (int(m.group(2)), f"{m.group(3)}..{m.group(4)}", m.group(5))
    return blocks, pooled


S129_MID_BLOCKS, S129_MID_POOLED = pub129_arm("mid", 248, 973, 254882)
S129_HI_BLOCKS, S129_HI_POOLED = pub129_arm("hi", 1213, 4753, 255208)
S129_LO_BLOCKS, S129_LO_POOLED = pub129_arm("lo", 405, 1591, 254557)

f9 = flat(pub129)
traj9 = re.search(
    r"lo per-run 18-cell min: ([\d ]+?) mid per-run 18-cell min: "
    r"([\d ]+?) hi per-run 18-cell min: ([\d ]+?) the three", f9)
assert traj9, "tenth cut W2 trajectories not parsed"
S129_TRAJ = {"lo": [int(x) for x in traj9.group(1).split()],
             "mid": [int(x) for x in traj9.group(2).split()],
             "hi": [int(x) for x in traj9.group(3).split()]}
for t in S129_TRAJ:
    assert len(S129_TRAJ[t]) == 12, f"s129 {t} trajectory length"

# the committed B=3 class-vs-per-dispatch-work row (QUOTE-ONLY): the
# s125 W2 table's committed rows (parsed from publication-s125.txt's
# committed bytes)
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
P("JUN-59 session 132 -- THE B=3 PER-DISPATCH-WORK THRESHOLD BISECT,")
P("ELEVENTH CUT -- THE MULTI-BLOCK STABILITY REQUIREMENT CUT (the L9")
P("block-run-instability confrontation at mid AND hi; NO new grid point")
P("is measured -- the second cut in the chain that measures none; the")
P("committed bracket stays exactly (254,557, 255,208] n-units).")
P("publication -- the MEASUREMENT half of the s131 pre-registration")
P("(anv-b3bisect11prereg-20261031/protocol.txt, frozen")
P("2026-10-31T13:50:45Z BEFORE any run log of this cut existed).")
P("Produced ONLY by analysis-s132.py over the 54 committed run logs in")
P("this directory (run-<tag>-r<NN>.txt) and the NAMED COMMITTED WANT")
P("SOURCES parsed below (protocol section 3 quote-only values, parsed")
P("from committed bytes, never transcribed). Arms = binary compile-time")
P("(BATCH, WORK_MUL, NDIV); n = (1,000,003*WORK_MUL)/NDIV (integer")
P("floor). The row question (protocol section 0): AT FIXED B=3 AND")
P("BYTE-IDENTICAL PINNED BINARIES, DO THE TWO BLOCK-RUN-UNSTABLE")
P("COMMITTED POINTS SATISFY THE MULTI-BLOCK STABILITY REQUIREMENT AT 8")
P("BLOCKS OF 3 (24 fresh processes each)? -- mid (248,973) n=254,882")
P("and hi (1213,4753) n=255,208, each classified in 8 disjoint")
P("frozen-method blocks of 3 runs plus the pooled 24. THE MULTI-BLOCK")
P("STABILITY REQUIREMENT (frozen): a point PASSES (8-block form) iff")
P("all 8 block classes AND the pooled-24 class are EQUAL under the")
P("frozen method of section 4. RESUMABILITY RULE (frozen, per-point")
P("form): the narrowing channel re-opens at a point P ONLY via a NEW")
P("pre-registered cut (NOT queued here) and ONLY if P PASSED the")
P("multi-block stability requirement here (C at P in {(a),(b)}). If C")
P("at P is (c), L9 CONTINUES to bind at P at the finer granularity.")
P("Under ALL outcomes: NO bracket movement, NO narrowing, no boundary")
P("between grid points is ever claimed (L5). BAR NON-INTERFERENCE: the")
P("cut's runs are BISECT CONTENT and NOT bar readings -- no ledger")
P("append, no day-slot consumption, no bar verdict movement, no Rule 4")
P("row or :measured? flag movement. WHY any class label occurs is")
P("UNMEASURED (L2 binds); NO causal mechanism is claimed. 1 tick =")
P("timestampPeriod = 52.083 ns.")
P("")

P("0. NAMED COMMITTED WANT SOURCES (parsed here from committed bytes;")
P("   every value below is a QUOTE-ONLY comparison value and never this")
P("   session's measurement):")
P(f"   committed controls (s27 census): {ctl}")
P(f"   mid = the (248,973) pair at n=254,882 -- the L9-bound point's two")
P(f"   committed readings: session 125 (the ninth cut, mid arm): "
  f"{MID125_MED}, 18-cell {MID125_18},")
P(f"   class {MID125_CLASS}")
P(f"   session 129 (the tenth cut): C3 (c) BLOCK-UNSTABLE -- block rows "
  f"(parsed):")
for lbl, medv, lo_, hi_, cls in S129_MID_BLOCKS:
    P(f"     {lbl} median {medv} 18-cell {lo_}..{hi_} {cls}")
P(f"     pooled-12 median {S129_MID_POOLED[0]} 18-cell "
  f"{S129_MID_POOLED[1]} {S129_MID_POOLED[2]}")
P(f"   hi = the (1213,4753) pair at n=255,208 -- the bracket's upper")
P(f"   anchor and the second L9-bound point: committed trio (s27")
P(f"   census): {trio_txt}; session 121: {HI121_MED} {HI121_CLASS};")
P(f"   session 125: {HI125_MED}, 18-cell {HI125_18}, class {HI125_CLASS}")
P(f"   session 129 (the tenth cut): W1 (c) BLOCK-UNSTABLE -- block rows "
  f"(parsed):")
for lbl, medv, lo_, hi_, cls in S129_HI_BLOCKS:
    P(f"     {lbl} median {medv} 18-cell {lo_}..{hi_} {cls}")
P(f"     pooled-12 median {S129_HI_POOLED[0]} 18-cell "
  f"{S129_HI_POOLED[1]} {S129_HI_POOLED[2]}")
P(f"   lo (405,1591) at n=254,557 -- NOT measured this cut; the tenth")
P(f"   cut's committed reading stands as content (block rows parsed):")
for lbl, medv, lo_, hi_, cls in S129_LO_BLOCKS:
    P(f"     {lbl} median {medv} 18-cell {lo_}..{hi_} {cls}")
P(f"     pooled-12 median {S129_LO_POOLED[0]} 18-cell "
  f"{S129_LO_POOLED[1]} {S129_LO_POOLED[2]}")
P(f"   the tenth cut's W2 per-run 18-cell min trajectories (parsed; the")
P(f"   boundary-crossing counts COMPUTED here, descriptive only):")
for t in ("lo", "mid", "hi"):
    cross = sum(1 for v in S129_TRAJ[t] if v >= 1000)
    P(f"     {t}: {' '.join(str(v) for v in S129_TRAJ[t])} "
      f"({cross}/12 at min >= 1,000)")
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

P("1. INTEGRITY (computed over the 54 logs):")
P(f"   runs parsed: 54 (c2 x3, mid x24, hi x24, c8 x3 -- the")
P(f"   frozen section 0 arm table's 4 rows govern the count); cell map")
P(f"   identical across runs: "
  f"{cell_keys is not None and not any('CELL MAP' in i for i in integrity)}")
P(f"   headers byte-identical across all runs outside the # n= knob line: {header_ok}")
P(f"   header batch=/work_mul=/ndiv= == run's (B,WM,NDIV) and n == "
  f"(1,000,003*WM)//NDIV; every SAMPLE batch=/work_mul=/ndiv= == (B,WM,NDIV): "
  f"{knob_field_ok}")
P(f"   every CELL spv= name is an archived .emitted.spv (no .iter -- the "
  f"corpus is byte-identical this session): {spv_identity_ok}")
P(f"   SAMPLE lines: 450 per run (18 ok cells x 25 rounds) in 54/54 runs: "
  f"{sample_counts_ok}")
P(f"   VERIFY mismatch total over all runs: {verify_mismatch_total} (per-arm: "
  + ", ".join(f"{t}={verify_mismatch_by_arm[t]}" for t in TAGS)
  + ") -- bit-exact correctness re-check inside every run; frozen "
    "INVALIDATION criterion (protocol section 4): >0 in any run makes that "
    "run DEFECTIVE and the arm INVALID (its block classes not evaluable)")
P(f"   forcing reality (pipeline-ok cell-runs where probe_size==forced and "
  f"probe_nsub==wg/forced): {forcing_ok}/{forcing_total}")
P(f"   S=8 cells fail-closed (pipeline=FAIL, forced=8): {s8_fail} cell-runs "
  f"(6 per run x 54 runs = 324 expected)")
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

P("3. BLOCK + POOLED-24 CLASSIFICATION (the frozen method of protocol")
P("   section 4 applied to the pre-registered classification units:")
P("   block j (j=1..8) = runs r(3j-2), r(3j-1), r(3j); pooled-24 pools")
P("   all 24 runs x 25 rounds per cell (a NAMED EXTENSION of the frozen")
P("   3-run method, reported alongside -- never instead of -- the eight")
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
        units.append(("pooled-24", UNIT24))
    else:
        units.append(("block1 (k=3 control)", tuple(range(1, k + 1))))
    for label, runs in units:
        v16, lo_, hi_, cls = unit_summary(tag, runs)
        runlabel = ",".join(f"{r:02d}" for r in runs)
        if len(runlabel) > 22:
            runlabel = "01..24"
        P(f"     {label:<20} runs {runlabel:<22} (sum,128,16) {v16:>7.0f}   "
          f"18-cell {lo_:>6.0f}..{hi_:<6.0f}   {cls}")
        unit_rows[(tag, label)] = (v16, lo_, hi_, cls, runs)
    P("")


def letter_stability(tag, want):
    """C2/C3 multi-block letter: (a) all-blocks+pooled24 == want; (b) all ==
    the other stable class; (c) BLOCK-UNSTABLE; (d) INVALID."""
    if verify_mismatch_by_arm[tag] > 0:
        return "(d)", None
    labels = [f"block{j}" for j in range(1, 9)]
    classes = [unit_rows[(tag, l)][3] for l in labels]
    pooled_cls = unit_rows[(tag, "pooled-24")][3]
    other = "CAPTURED" if want == "INTERMEDIATE/MIXED" else "INTERMEDIATE/MIXED"
    if all(c == want for c in classes) and pooled_cls == want:
        return "(a)", classes
    if all(c == other for c in classes) and pooled_cls == other:
        return "(b)", classes
    return "(c)", classes


P("4. PRE-REGISTERED LETTERS (thresholds frozen in protocol section 4:")
P("   FLOOR <= 100 ticks at all 18 cells; CAPTURED >= 1000 ticks at all")
P("   18; anything else INTERMEDIATE/MIXED; the re-defined C2/C3/W1 of")
P("   protocol section 5 -- the tenth cut's meanings do NOT carry):")
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

# C2 (mid, the ninth cut's row point -- the first L9-bound point)
c2_letter, c2_classes = letter_stability("mid", "INTERMEDIATE/MIXED")
P("   C2 MULTI-BLOCK STABILITY AT THE NINTH CUT'S ROW POINT -- mid")
P("   (BATCH=3,WORK_MUL=248,NDIV=973) at n=254,882 (8 blocks +")
P(f"   pooled-24): {c2_letter}")
P(f"     block classes: {c2_classes}; pooled-24 class: "
  f"{unit_rows[('mid', 'pooled-24')][3]}")
P(f"     (sum,128,S=16): blocks "
  + " / ".join(f"{unit_rows[('mid', f'block{j}')][0]:.0f}" for j in range(1, 9))
  + f" ; pooled-24 {unit_rows[('mid', 'pooled-24')][0]:.0f}")
if c2_letter == "(a)":
    P("     (a) STABLE-INTERMEDIATE: all 8 block classes AND the pooled-24")
    P("     class are INTERMEDIATE/MIXED -- PASSES the multi-block")
    P("     stability requirement (the tenth cut's block4 CAPTURED is")
    P("     named tail content).")
elif c2_letter == "(b)":
    P("     (b) STABLE-CAPTURED: all 8 block classes AND the pooled-24")
    P("     class are CAPTURED -- PASSES the requirement.")
elif c2_letter == "(c)":
    P("     (c) BLOCK-UNSTABLE: the 8 block classes are not all equal, or")
    P("     the pooled-24 class differs from a unanimous block class --")
    P("     FAILS the requirement (the class at this point is")
    P("     BLOCK-RUN-UNSTABLE at the finer granularity too; the")
    P("     instability is CONFIRMED at 8 blocks and quantified in W2).")
else:
    P("     (d) INVALID: the frozen INVALIDATION criterion leaves C2")
    P("     unevaluable.")
P("     NAMED, NOT HIDDEN: branches (a) and (b) do NOT adjudicate which")
P("     committed reading was 'right' -- all stay committed content;")
P("     they name one reading as tail content of a stable distribution.")
P("     WHY any branch occurs is UNMEASURED.")
P("")

# C3 (hi, the bracket's upper anchor -- the second L9-bound point)
c3_letter, c3_classes = letter_stability("hi", "CAPTURED")
P("   C3 MULTI-BLOCK STABILITY AT THE BRACKET'S UPPER ANCHOR -- hi")
P("   (BATCH=3,WORK_MUL=1213,NDIV=4753) at n=255,208 (8 blocks +")
P(f"   pooled-24): {c3_letter}")
P(f"     block classes: {c3_classes}; pooled-24 class: "
  f"{unit_rows[('hi', 'pooled-24')][3]}")
P(f"     (sum,128,S=16): blocks "
  + " / ".join(f"{unit_rows[('hi', f'block{j}')][0]:.0f}" for j in range(1, 9))
  + f" ; pooled-24 {unit_rows[('hi', 'pooled-24')][0]:.0f}")
if c3_letter == "(a)":
    P("     (a) STABLE-CAPTURED: all 8 block classes AND the pooled-24")
    P("     class are CAPTURED -- PASSES (the committed CAPTURED content")
    P("     -- trio + s121 + s125 -- replicates as stable at the finer")
    P("     granularity).")
elif c3_letter == "(b)":
    P("     (b) STABLE-INTERMEDIATE: all 8 block classes AND the pooled-24")
    P("     class are INTERMEDIATE/MIXED -- PASSES (pre-named")
    P("     contradiction of the committed CAPTURED content at the")
    P("     anchor).")
elif c3_letter == "(c)":
    P("     (c) BLOCK-UNSTABLE -- FAILS (the upper anchor's class is")
    P("     run-unstable at the finer granularity too).")
else:
    P("     (d) INVALID.")
P("     NAMED, NOT HIDDEN: this cut's C3 is again NOT the pair-")
P("     representation check of cuts 2-9 (no same-ratio pair is measured")
P("     this cut); the committed C3 scoreboard (s24 (b)/s25 (a)/s26")
P("     (b)/s27 (a)/s121 (a)/s125 (a)) is untouched content.")
P("")

# W1 -- THE CUT VERDICT (per-point composition)
c2_pass = c2_letter in ("(a)", "(b)")
c3_pass = c3_letter in ("(a)", "(b)")
if "(d)" in (c2_letter, c3_letter):
    w1_letter = "(d)"
elif c2_pass and c3_pass:
    w1_letter = "(a)"
elif c2_pass or c3_pass:
    w1_letter = "(b)"
else:
    w1_letter = "(c)"
P("   W1 THE ROW QUESTION -- THE CUT VERDICT (pre-named composition,")
P("   section 0's RESUMABILITY RULE, per-point form):")
P(f"     mid (n=254,882): C2 {c2_letter} -> "
  f"{'PASSES' if c2_pass else 'FAILS'} the multi-block stability "
  "requirement")
P(f"     hi (n=255,208): C3 {c3_letter} -> "
  f"{'PASSES' if c3_pass else 'FAILS'} the multi-block stability "
  "requirement")
P(f"     W1 {w1_letter}")
if w1_letter == "(a)":
    P("     (a) BOTH PASS: the multi-block stability requirement HOLDS at")
    P("     both L9-bound points; the narrowing channel re-opens at BOTH")
    P("     points in a NEW pre-registered cut (NOT queued here).")
elif w1_letter == "(b)":
    names = []
    if c2_pass:
        names.append("mid (n=254,882)")
    if c3_pass:
        names.append("hi (n=255,208)")
    P(f"     (b) EXACTLY ONE PASSES (the named point: {' and '.join(names)} "
      "passes;")
    P("     the other FAILS) -- the narrowing channel re-opens at that")
    P("     point only.")
elif w1_letter == "(c)":
    P("     (c) NEITHER PASSES -- the narrowing channel remains closed at")
    P("     both points; the flip bracket's endpoints rest on finer-")
    P("     granularity-confirmed unstable content and any future")
    P("     narrowing claim at either point must confront this cut's")
    P("     8-block instability content first (named here, not specified")
    P("     here).")
else:
    P("     (d) INVALID (C2 (d) or C3 (d)).")
for tg, lt, ps in (("mid", c2_letter, c2_pass), ("hi", c3_letter, c3_pass)):
    if lt == "(c)":
        P(f"     L9 CONTINUES to bind at {tg}: the class label at this")
        P(f"     point is BLOCK-RUN-UNSTABLE at the finer granularity too.")
P("     Under ALL outcomes: NO bracket movement, NO narrowing, no")
P("     boundary between grid points is ever claimed (L5).")
P("")

# W2 dispersion (descriptive)
P("   W2 (pre-registered, descriptive) DISPERSION QUANTIFICATION: per")
P("   arm, per run (descriptive, never classifying -- L10): the per-run")
P("   18-cell min trajectory across the 24 runs in frozen order (the")
P("   quantity observed moving across the frozen 1,000 boundary -- L9's")
P("   named content) and the boundary-crossing count (runs with 18-cell")
P("   min >= 1,000):")
for tag in ("mid", "hi"):
    traj = []
    cross = 0
    for r in range(1, 25):
        vals = [cell_median(tag, (r,), kk) for kk in ok_cells]
        mn = min(vals)
        traj.append(f"{mn:.0f}")
        if mn >= 1000:
            cross += 1
    P(f"     {tag} per-run 18-cell min: " + " ".join(traj))
    P(f"     {tag}: runs with 18-cell min >= 1,000 (COMPUTED here, "
      f"descriptive): {cross}/24")
P("     (the tenth cut's computed counts at 12 runs: mid "
  f"{sum(1 for v in S129_TRAJ['mid'] if v >= 1000)}/12, hi "
  f"{sum(1 for v in S129_TRAJ['hi'] if v >= 1000)}/12 -- parsed from "
  "publication-s129.txt, quote-only)")
P("   the two points placed on the committed row as grid points")
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
for tag in ("mid", "hi"):
    b, wm, dd = ARMB[tag], ARMW[tag], ARMD[tag]
    n = (N_BASE * wm) // dd
    v16, lo_, hi_, cls, runs = unit_rows[(tag, "pooled-24")]
    lbl = {254882: "0.2548812", 255208: "0.2552072"}[n]
    role = {"mid": "the ninth cut's row point (248,973)",
            "hi": "the upper anchor (1213,4753)"}[tag]
    P(f"     {n:<10} {lbl:<13} {v16:>5.0f}  {cls:<20} THIS SESSION "
      f"(pooled-24, {role})")
P("")

# W3 history comparisons (descriptive)
P("   W3 (pre-registered, descriptive) THE HISTORY COMPARISONS:")
P(f"     (i) mid blocks vs the same binary's two committed readings (s125")
P(f"         {MID125_MED} {MID125_CLASS}, 18-cell {MID125_18}; s129 block")
P(f"         medians "
  + "/".join(b[1] for b in S129_MID_BLOCKS)
  + ", block4 CAPTURED min 1,023, pooled-12 "
  + f"{S129_MID_POOLED[0]} {S129_MID_POOLED[2]}):")
P(f"         this cut's mid blocks (sum,128,16): "
  + " / ".join(f"{unit_rows[('mid', f'block{j}')][0]:.0f}" for j in range(1, 9))
  + f"; pooled-24 {unit_rows[('mid', 'pooled-24')][0]:.0f} "
    f"{unit_rows[('mid', 'pooled-24')][3]}")
P(f"     (ii) hi blocks vs the committed CAPTURED content (trio "
  f"{trio_txt}; s121 {HI121_MED}; s125 {HI125_MED}, 18-cell {HI125_18};")
P(f"         s129 block medians "
  + "/".join(b[1] for b in S129_HI_BLOCKS)
  + ", block1 INTERMEDIATE/MIXED min 988, pooled-12 "
  + f"{S129_HI_POOLED[0]} {S129_HI_POOLED[2]}):")
P(f"         this cut's hi blocks (sum,128,16): "
  + " / ".join(f"{unit_rows[('hi', f'block{j}')][0]:.0f}" for j in range(1, 9))
  + f"; pooled-24 {unit_rows[('hi', 'pooled-24')][0]:.0f} "
    f"{unit_rows[('hi', 'pooled-24')][3]}")
P("")

# X1 host_ns dispersion (descriptive)
P("   X1 (descriptive, host_ns at (sum,128,S=16); NOT a C criterion")
P("   (L3); per-run host_ns spread is reported):")
for tag in TAGS:
    k = ARMK[tag]
    hs = [cell_median(tag, (r,), sum128, field=8) for r in range(1, k + 1)]
    P(f"     {tag}: per-run host_ns median min..max {min(hs):.0f}.."
      f"{max(hs):.0f} (spread {max(hs) - min(hs):.0f} = "
      f"{(max(hs) - min(hs)) / min(hs) * 100:.1f}% of min; k={k})")
P("     host_ns is the HOST-side proxy (L3), not a C criterion; any")
P("     excursion is NAMED, NOT HIDDEN and its cause is UNMEASURED.")
P("")

P("5. VERDICT SUMMARY: C1 {0}; C2 {1} at mid; C3 {2} at hi; W1 {3}."
  .format("(a)" if c1_ok else "(b)", c2_letter, c3_letter, w1_letter))
P(f"   THE MULTI-BLOCK STABILITY REQUIREMENT (8-block form): mid "
  f"{'PASSES' if c2_pass else 'FAILS'} (C2 {c2_letter}), hi "
  f"{'PASSES' if c3_pass else 'FAILS'} (C3 {c3_letter}).")
if w1_letter == "(a)":
    P("   CUT VERDICT (pre-named composition, section 0's RESUMABILITY")
    P("   RULE, per-point form): the multi-block stability requirement")
    P("   HOLDS at BOTH L9-bound points; the narrowing channel re-opens")
    P("   at both points ONLY via a NEW pre-registered cut (NOT queued).")
elif w1_letter == "(b)":
    P("   CUT VERDICT (pre-named composition, section 0's RESUMABILITY")
    P("   RULE, per-point form): exactly one L9-bound point PASSES; the")
    P("   narrowing channel re-opens at that point only.")
elif w1_letter == "(c)":
    P("   CUT VERDICT (pre-named composition, section 0's RESUMABILITY")
    P("   RULE, per-point form): NEITHER L9-bound point passes the")
    P("   multi-block stability requirement; the narrowing channel")
    P("   remains closed at both points and the flip bracket's endpoints")
    P("   rest on finer-granularity-confirmed unstable content.")
else:
    P("   CUT VERDICT: INVALID (frozen INVALIDATION criterion).")
P("   The multi-block stability of the two committed B=3 points is as")
P("   the letters state; WHY is UNMEASURED and NO causal mechanism is")
P("   claimed. The committed bracket stays exactly (254,557, 255,208]")
P("   under ALL outcomes (L5 named N/A in its narrowing form). BAR")
P("   NON-INTERFERENCE (frozen protocol section 6): these runs are BISECT")
P("   CONTENT and NOT bar readings -- NO settle-bar-ledger.txt append, NO")
P("   UTC-day slot consumption, NO movement of the bar's SETTLED")
P("   INTERMEDIATE/MIXED verdict (the s117 committed landing), NO Rule 4")
P("   workgroup row movement, NO :measured? flag change (the")
P("   accelerator-targets rows stay exactly as ADR-0358 left them).")

with open(os.path.join(HERE, "publication-s132.txt"), "w") as f:
    f.write("\n".join(out) + "\n")
