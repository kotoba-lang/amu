#!/usr/bin/env python3
"""JUN-59 session 139 analysis -- THE B=3 PER-DISPATCH-WORK THRESHOLD
BISECT, THIRTEENTH CUT -- THE 16-BLOCK STABILITY CONFRONTATION CUT (the
confrontation the twelfth cut's W1 (c) made mandatory; NO new grid
point; ZERO NEW KNOB TRIPLES; under ALL outcomes NO bracket movement
and the MID-ONLY NARROWING CLAIM stays SUSPENDED (named, not
claimed)).
The MEASUREMENT half of the s137 pre-registration
(anv-b3bisect13prereg-20261031/protocol.txt, frozen 2026-10-31T16:52:54Z
BEFORE any run log of this cut existed).

Route (frozen in protocol.txt section 7): this script parses ONLY the
102 committed run logs in its own directory (run-<tag>-r<NN>.txt) and
NAMED COMMITTED WANT SOURCES (the quote-only values of protocol section
3, parsed here from committed bytes -- never transcribed) and writes
publication-s139.txt. No other input. Deterministic: running it twice
yields byte-identical publication-s139.txt (checked by diff after the
recorded run). Every want source is parsed with fail-closed regexes; a
want that does not parse aborts (assert).

Frozen classification (protocol section 4): over the 18 pipeline-ok
cells, pooled median gpu_ticks over the unit's runs x 25 rounds per
cell; FLOOR = <= 100 at ALL 18 cells; CAPTURED = >= 1000 at ALL 18
cells; anything else INTERMEDIATE/MIXED. The pre-registered
classification UNIT is the BLOCK (16 disjoint blocks of 3 runs per
B=3 arm: r01..r03 / ... / r46..r48) plus the pooled-48 (a named
extension, reported alongside -- never instead of -- the sixteen block
classes). Controls have k=3: one block each.

The letters C2/C3/W1 are RE-DEFINED for this cut (protocol section 5) --
the twelfth cut's meanings do not carry. C2/C3 here are the 16-block
multi-block STABILITY at bis/mid; W1 is THE 16-BLOCK CONFRONTATION
verdict deciding both points' channels for LATER pre-registered cuts.
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
# (4 rows = 102 fresh processes)
ARMS = [("c2", 2, 1, 1, 3), ("mid", 3, 248, 973, 48),
        ("bis", 3, 316, 1239, 48), ("c8", 8, 1, 1, 3)]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMW = {a[0]: a[2] for a in ARMS}
ARMD = {a[0]: a[3] for a in ARMS}
ARMK = {a[0]: a[4] for a in ARMS}
N_BASE = 1000003
BLOCKS = {t: [tuple(range(3 * j - 2, 3 * j + 1)) for j in range(1, 17)]
          for t in ("mid", "bis")}
UNIT48 = tuple(range(1, 49))


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
pub125 = open(os.path.join(GPU, "anv-b3bisect9-20261031",
                           "publication-s125.txt")).read()
pub129 = open(os.path.join(GPU, "anv-b3bisect10-20261031",
                           "publication-s129.txt")).read()
pub132 = open(os.path.join(GPU, "anv-b3bisect11-20261031",
                           "publication-s132.txt")).read()
pub136 = open(os.path.join(GPU, "anv-b3bisect12-20261031",
                           "publication-s136.txt")).read()

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


# -- publication-s132.txt / publication-s136.txt: line-based structural
# -- parsers (fail-closed); the same shape both files --
def pub_arm_rows(pub, tag, pooled_label="pooled-24"):
    """(block rows [(label, medv, lo, hi, cls)] x8, pooled (medv, 'lo..hi', cls))
    parsed from a publication's section-3 arm section."""
    lines = pub.splitlines()
    start = None
    for i, l in enumerate(lines):
        if l.startswith(f"   {tag} (B=3, WM=") and "nominal total units" in l:
            start = i + 1
            break
    assert start is not None, f"WANT SOURCE NOT PARSED: {tag} arm header"
    rows, pooled = [], None
    for l in lines[start:]:
        if not l.strip():
            break
        m = re.match(r" +(block\d|" + pooled_label + r") +runs \S+ +\(sum,128,16\) +(\d+) "
                     r"+18-cell +(\d+)\.\.(\d+) +(\S+)", l)
        assert m is not None, f"WANT SOURCE NOT PARSED: {tag} row: {l}"
        if m.group(1) == pooled_label:
            pooled = (int(m.group(2)), f"{m.group(3)}..{m.group(4)}", m.group(5))
        else:
            rows.append((m.group(1), int(m.group(2)), m.group(3), m.group(4),
                         m.group(5)))
    assert len(rows) == 8 and pooled is not None, f"{tag} rows {len(rows)}"
    return rows, pooled


S132_MID_BLOCKS, S132_MID_POOLED = pub_arm_rows(pub132, "mid")
S132_HI_BLOCKS, S132_HI_POOLED = pub_arm_rows(pub132, "hi")
# the twelfth cut's windows (the named content this cut confronts)
S136_MID_BLOCKS, S136_MID_POOLED = pub_arm_rows(pub136, "mid")
S136_BIS_BLOCKS, S136_BIS_POOLED = pub_arm_rows(pub136, "bis")

# the eleventh cut's W2 per-run 18-cell min trajectories (24 each)
traj132 = {}
for tag in ("mid", "hi"):
    m = re.search(rf"{tag} per-run 18-cell min: ([\d ]+)", flat(pub132))
    assert m is not None, f"WANT SOURCE NOT PARSED: pub132 {tag} trajectory"
    traj132[tag] = [int(x) for x in m.group(1).split()]
    assert len(traj132[tag]) == 24, f"pub132 {tag} trajectory length"

# the twelfth cut's W2 per-run 18-cell min trajectories (24 each)
traj136 = {}
for tag in ("mid", "bis"):
    m = re.search(rf"{tag} per-run 18-cell min: ([\d ]+)", flat(pub136))
    assert m is not None, f"WANT SOURCE NOT PARSED: pub136 {tag} trajectory"
    traj136[tag] = [int(x) for x in m.group(1).split()]
    assert len(traj136[tag]) == 24, f"pub136 {tag} trajectory length"

# the twelfth cut's X1 content (quote-only)
x1_136 = {}
for tag in ("mid", "bis"):
    m = re.search(rf"{tag}: per-run host_ns median min\.\.max (\d+)\.\.(\d+) "
                  rf"\(spread (\d+) = ([\d.]+)% of min; k=(\d+)\)", flat(pub136))
    assert m is not None, f"WANT SOURCE NOT PARSED: pub136 X1 {tag}"
    x1_136[tag] = (int(m.group(1)), int(m.group(2)), int(m.group(3)),
                   float(m.group(4)), int(m.group(5)))

# the committed B=3 row: publication-s136.txt's W2 table (19 rows -- the
# s132 table's 17 plus the twelfth cut's two pooled-24 readings)
B3ROW = []
lines = pub136.splitlines()
tstart = None
for i, l in enumerate(lines):
    if re.match(r" +n +work-unit", l):
        tstart = i + 1
        break
assert tstart is not None, "WANT SOURCE NOT PARSED: pub136 W2 table header"
for l in lines[tstart:]:
    if not l.strip():
        break
    m = re.match(r" +(\d+) +(\S+) +(\d+) +(\S+?)\*? +(.+?)$", l)
    assert m is not None, f"WANT SOURCE NOT PARSED: pub136 W2 row: {l}"
    src = m.group(5)
    star = "*" if re.search(r"\S\* ", l + " ") or l.rstrip().endswith("*") else ""
    if src.startswith("THIS SESSION"):
        src = "session 136 (the twelfth cut, " + src[len("THIS SESSION ("):]
    B3ROW.append((m.group(2), int(m.group(1)), int(m.group(3)),
                  m.group(4) + star, src))
assert len(B3ROW) == 19, f"committed row parsed {len(B3ROW)} want 19"

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
P("JUN-59 session 139 -- THE B=3 PER-DISPATCH-WORK THRESHOLD BISECT,")
P("THIRTEENTH CUT -- THE 16-BLOCK STABILITY CONFRONTATION CUT (the")
P("confrontation the twelfth cut's W1 (c) made mandatory before any re-")
P("open or narrowing claim; NO new grid point; ZERO NEW KNOB TRIPLES;")
P("under ALL outcomes NO bracket movement and the MID-ONLY NARROWING")
P("CLAIM stays SUSPENDED (named, not claimed)).")
P("publication -- the MEASUREMENT half of the s137 pre-registration")
P("(anv-b3bisect13prereg-20261031/protocol.txt, frozen")
P("2026-10-31T16:52:54Z BEFORE any run log of this cut existed).")
P("Produced ONLY by analysis-s139.py over the 102 committed run logs in")
P("this directory (run-<tag>-r<NN>.txt) and the NAMED COMMITTED WANT")
P("SOURCES parsed below (protocol section 3 quote-only values, parsed")
P("from committed bytes, never transcribed). Arms = binary compile-time")
P("(BATCH, WORK_MUL, NDIV); n = (1,000,003*WORK_MUL)/NDIV (integer")
P("floor). The row question (protocol section 0): AT FIXED B=3, ARE mid")
P("(248,973) n=254,882 AND bis (3,316,1239) n=255,045 MULTI-BLOCK")
P("STABLE AT 16-BLOCK GRANULARITY (16 blocks of 3 runs + pooled-48) AT")
P("THEIR BYTE-IDENTICAL PINNED BINARIES (W1: do the channels re-open")
P("for LATER pre-registered cuts)? NO NARROWING CLAIM IS PRE-REGISTERED")
P("BY THIS CUT; it narrows NOTHING under any outcome. The pre-named")
P("cross-window disagreement at mid (s132 window pooled-24 1,133")
P("INTERMEDIATE/MIXED vs s136 window pooled-24 1,148 CAPTURED, same")
P("byte-identical binary) is named content confronted in W3 (this is")
P("the THIRD reading at mid, at a FINER granularity). BAR NON-")
P("INTERFERENCE: the cut's runs are BISECT CONTENT and NOT bar readings")
P("-- no ledger append, no day-slot consumption, no bar verdict")
P("movement, no Rule 4 row or :measured? flag movement. WHY any class")
P("label occurs is UNMEASURED (L2 binds); NO causal mechanism is")
P("claimed. 1 tick = timestampPeriod = 52.083 ns.")
P("")

P("0. NAMED COMMITTED WANT SOURCES (parsed here from committed bytes;")
P("   every value below is a QUOTE-ONLY comparison value and never this")
P("   session's measurement):")
P(f"   committed controls (s27 census): {ctl}")
P(f"   mid = the (248,973) pair at n=254,882 -- the claimed anchor's")
P(f"   committed history (all readings at byte-identical binaries):")
P(f"   session 125 (the ninth cut, mid arm): "
  f"{MID125_MED}, 18-cell {MID125_18},")
P(f"   class {MID125_CLASS}")
P(f"   session 129 (the tenth cut): block rows (parsed):")
for lbl, medv, lo_, hi_, cls in S129_MID_BLOCKS:
    P(f"     {lbl} median {medv} 18-cell {lo_}..{hi_} {cls}")
P(f"     pooled-12 median {S129_MID_POOLED[0]} 18-cell "
  f"{S129_MID_POOLED[1]} {S129_MID_POOLED[2]}")
P(f"   session 132 (the eleventh cut): C2 (a) STABLE-INTERMEDIATE --")
P(f"   block rows (parsed):")
for lbl, medv, lo_, hi_, cls in S132_MID_BLOCKS:
    P(f"     {lbl} median {medv} 18-cell {lo_}..{hi_} {cls}")
P(f"     pooled-24 median {S132_MID_POOLED[0]} 18-cell "
  f"{S132_MID_POOLED[1]} {S132_MID_POOLED[2]}")
P(f"   session 136 (the twelfth cut): C3 (c) BLOCK-UNSTABLE -- block")
P(f"   rows (parsed; the named content this cut confronts):")
for lbl, medv, lo_, hi_, cls in S136_MID_BLOCKS:
    P(f"     {lbl} median {medv} 18-cell {lo_}..{hi_} {cls}")
P(f"     pooled-24 median {S136_MID_POOLED[0]} 18-cell "
  f"{S136_MID_POOLED[1]} {S136_MID_POOLED[2]}")
P(f"   bis (3,316,1239) at n=255,045 -- committed history (ONE")
P(f"   reading):")
P(f"   session 136 (the twelfth cut): C2 (c) BLOCK-UNSTABLE -- block")
P(f"   rows (parsed; the named content this cut confronts):")
for lbl, medv, lo_, hi_, cls in S136_BIS_BLOCKS:
    P(f"     {lbl} median {medv} 18-cell {lo_}..{hi_} {cls}")
P(f"     pooled-24 median {S136_BIS_POOLED[0]} 18-cell "
  f"{S136_BIS_POOLED[1]} {S136_BIS_POOLED[2]}")
P(f"   lo (405,1591) at n=254,557 -- NOT measured this cut; the tenth")
P(f"   cut's committed reading stands as content (block rows parsed):")
for lbl, medv, lo_, hi_, cls in S129_LO_BLOCKS:
    P(f"     {lbl} median {medv} 18-cell {lo_}..{hi_} {cls}")
P(f"     pooled-12 median {S129_LO_POOLED[0]} 18-cell "
  f"{S129_LO_POOLED[1]} {S129_LO_POOLED[2]}")
P(f"   hi (1213,4753) at n=255,208 -- NOT measured this cut (channel")
P(f"   closed); its eleventh-cut committed content (parsed; L9 binds):")
for lbl, medv, lo_, hi_, cls in S132_HI_BLOCKS:
    P(f"     {lbl} median {medv} 18-cell {lo_}..{hi_} {cls}")
P(f"     pooled-24 median {S132_HI_POOLED[0]} 18-cell "
  f"{S132_HI_POOLED[1]} {S132_HI_POOLED[2]}")
P(f"   the twelfth cut's W2 per-run 18-cell min trajectories (parsed;")
P(f"   the boundary-crossing counts COMPUTED here, descriptive only):")
for t in ("mid", "bis"):
    cross = sum(1 for v in traj136[t] if v >= 1000)
    P(f"     {t}: {' '.join(str(v) for v in traj136[t])} "
      f"({cross}/24 at min >= 1,000)")
P(f"   the eleventh cut's computed counts at 24 runs (from its parsed")
P(f"   trajectories, quote-only): mid "
  f"{sum(1 for v in traj132['mid'] if v >= 1000)}/24, hi "
  f"{sum(1 for v in traj132['hi'] if v >= 1000)}/24")
P(f"   the tenth cut's computed counts at 12 runs (from its parsed")
P(f"   trajectories, quote-only): mid "
  f"{sum(1 for v in S129_TRAJ['mid'] if v >= 1000)}/12, lo "
  f"{sum(1 for v in S129_TRAJ['lo'] if v >= 1000)}/12")
P(f"   the twelfth cut's X1 content (parsed, quote-only):")
for t in ("mid", "bis"):
    lo_, hi_, sp, pct, k = x1_136[t]
    P(f"     {t}: per-run host_ns median min..max {lo_}..{hi_} "
      f"(spread {sp} = {pct}% of min; k={k})")
P(f"   committed B=3 row (publication-s136.txt W2 table, committed")
P(f"   bytes): {len(B3ROW)} grid rows parsed")
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

P("1. INTEGRITY (computed over the 102 logs):")
P(f"   runs parsed: 102 (c2 x3, mid x48, bis x48, c8 x3 -- the")
P(f"   frozen section 0 arm table's 4 rows govern the count); cell map")
P(f"   identical across runs: "
  f"{cell_keys is not None and not any('CELL MAP' in i for i in integrity)}")
P(f"   headers byte-identical across all runs outside the # n= knob line: {header_ok}")
P(f"   header batch=/work_mul=/ndiv= == run's (B,WM,NDIV) and n == "
  f"(1,000,003*WM)//NDIV; every SAMPLE batch=/work_mul=/ndiv= == (B,WM,NDIV): "
  f"{knob_field_ok}")
P(f"   every CELL spv= name is an archived .emitted.spv (no .iter -- the "
  f"corpus is byte-identical this session): {spv_identity_ok}")
P(f"   SAMPLE lines: 450 per run (18 ok cells x 25 rounds) in 102/102 runs: "
  f"{sample_counts_ok}")
P(f"   VERIFY mismatch total over all runs: {verify_mismatch_total} (per-arm: "
  + ", ".join(f"{t}={verify_mismatch_by_arm[t]}" for t in TAGS)
  + ") -- bit-exact correctness re-check inside every run; frozen "
    "INVALIDATION criterion (protocol section 4): >0 in any run makes that "
    "run DEFECTIVE and the arm INVALID (its block classes not evaluable)")
P(f"   forcing reality (pipeline-ok cell-runs where probe_size==forced and "
  f"probe_nsub==wg/forced): {forcing_ok}/{forcing_total}")
P(f"   S=8 cells fail-closed (pipeline=FAIL, forced=8): {s8_fail} cell-runs "
  f"(6 per run x 102 runs = 612 expected)")
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

P("3. BLOCK + POOLED-48 CLASSIFICATION (the frozen method of protocol")
P("   section 4 applied to the pre-registered classification units:")
P("   block j (j=1..16) = runs r(3j-2), r(3j-1), r(3j); pooled-48 pools")
P("   all 48 runs x 25 rounds per cell (a NAMED EXTENSION of the frozen")
P("   3-run method, reported alongside -- never instead of -- the sixteen")
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
        units.append(("pooled-48", UNIT48))
    else:
        units.append(("block1 (k=3 control)", tuple(range(1, k + 1))))
    for label, runs in units:
        v16, lo_, hi_, cls = unit_summary(tag, runs)
        runlabel = ",".join(f"{r:02d}" for r in runs)
        if len(runlabel) > 22:
            runlabel = "01..48"
        P(f"     {label:<20} runs {runlabel:<22} (sum,128,16) {v16:>7.0f}   "
          f"18-cell {lo_:>6.0f}..{hi_:<6.0f}   {cls}")
        unit_rows[(tag, label)] = (v16, lo_, hi_, cls, runs)
    P("")


def letter_stability(tag):
    """C2/C3 16-block multi-block stability letter (protocol section 5,
    this cut's meanings): (a) all 16 blocks AND pooled-48 INTERMEDIATE/
    MIXED; (b) all 16 AND pooled-48 CAPTURED; (c) the 16 block classes
    are not all equal, or the pooled-48 class differs from a unanimous
    block class; (d) INVALID. Fail-closed: an all-equal block class
    outside {(a),(b)} with matching pooled-48 is not a branch the
    frozen letters define -- assert."""
    if verify_mismatch_by_arm[tag] > 0:
        return "(d)", None
    labels = [f"block{j}" for j in range(1, 17)]
    classes = [unit_rows[(tag, l)][3] for l in labels]
    pooled_cls = unit_rows[(tag, "pooled-48")][3]
    if all(c == "INTERMEDIATE/MIXED" for c in classes) \
       and pooled_cls == "INTERMEDIATE/MIXED":
        return "(a)", classes
    if all(c == "CAPTURED" for c in classes) and pooled_cls == "CAPTURED":
        return "(b)", classes
    if len(set(classes)) > 1 or pooled_cls != classes[0]:
        return "(c)", classes
    assert False, f"frozen letters define no branch for {tag}: {classes} {pooled_cls}"


P("4. PRE-REGISTERED LETTERS (thresholds frozen in protocol section 4:")
P("   FLOOR <= 100 ticks at all 18 cells; CAPTURED >= 1000 ticks at all")
P("   18; anything else INTERMEDIATE/MIXED; the RE-DEFINED C2/C3/W1 of")
P("   protocol section 5 -- the twelfth cut's meanings do NOT carry):")
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

# C2 (bis -- 16-block stability at the twelfth cut's FIRST-reading point)
c2_letter, c2_classes = letter_stability("bis")
P("   C2 MULTI-BLOCK STABILITY AT THE TWELFTH CUT'S FIRST-READING POINT")
P("   -- bis (BATCH=3,WORK_MUL=316,NDIV=1239) at n=255,045 (16 blocks +")
P(f"   pooled-48): {c2_letter}")
P(f"     block classes: {c2_classes}; pooled-48 class: "
  f"{unit_rows[('bis', 'pooled-48')][3]}")
P(f"     (sum,128,S=16): blocks "
  + " / ".join(f"{unit_rows[('bis', f'block{j}')][0]:.0f}" for j in range(1, 17))
  + f" ; pooled-48 {unit_rows[('bis', 'pooled-48')][0]:.0f}")
if c2_letter == "(a)":
    P("     (a) STABLE-INTERMEDIATE: all 16 block classes AND the pooled-48")
    P("     class are INTERMEDIATE/MIXED -- PASSES the 16-block multi-block")
    P("     stability requirement and RE-OPENS the narrowing channel at")
    P("     255,045 for a LATER pre-registered cut (NOT queued).")
elif c2_letter == "(b)":
    P("     (b) STABLE-CAPTURED: all 16 block classes AND the pooled-48")
    P("     class are CAPTURED -- PASSES and re-opens the channel at")
    P("     255,045 likewise.")
elif c2_letter == "(c)":
    P("     (c) BLOCK-UNSTABLE: the 16 block classes are not all equal, or")
    P("     the pooled-48 class differs from a unanimous block class --")
    P("     FAILS (L9 binds at 255,045 at the finer granularity; any")
    P("     future narrowing claim at 255,045 must confront this cut's")
    P("     16-block content first (named here, not specified here)).")
else:
    P("     (d) INVALID: the frozen INVALIDATION criterion leaves C2")
    P("     unevaluable.")
P("     NAMED, NOT HIDDEN: NO narrowing claim at 255,045 may be")
P("     pre-registered here (the frozen per-point rule: its channel")
P("     status is decided here and used by a LATER cut). WHY any branch")
P("     occurs is UNMEASURED.")
P("")

# C3 (mid -- 16-block stability at the claimed anchor's point)
c3_letter, c3_classes = letter_stability("mid")
P("   C3 MULTI-BLOCK STABILITY AT THE CLAIMED ANCHOR'S POINT -- mid")
P("   (BATCH=3,WORK_MUL=248,NDIV=973) at n=254,882 (16 blocks +")
P(f"   pooled-48): {c3_letter}")
P(f"     block classes: {c3_classes}; pooled-48 class: "
  f"{unit_rows[('mid', 'pooled-48')][3]}")
P(f"     (sum,128,S=16): blocks "
  + " / ".join(f"{unit_rows[('mid', f'block{j}')][0]:.0f}" for j in range(1, 17))
  + f" ; pooled-48 {unit_rows[('mid', 'pooled-48')][0]:.0f}")
if c3_letter == "(a)":
    P("     (a) STABLE-INTERMEDIATE: all 16 block classes AND the pooled-48")
    P("     class are INTERMEDIATE/MIXED -- PASSES the 16-block multi-block")
    P("     stability requirement and RE-OPENS the narrowing channel at")
    P("     mid for a LATER pre-registered cut (NOT queued).")
elif c3_letter == "(b)":
    P("     (b) STABLE-CAPTURED: all 16 AND pooled-48 CAPTURED (pre-named")
    P("     contradiction of the committed INTERMEDIATE/MIXED content at")
    P("     this point -- the s125/s129/s132 windows); PASSES likewise.")
elif c3_letter == "(c)":
    P("     (c) BLOCK-UNSTABLE: the 16 block classes are not all equal, or")
    P("     the pooled-48 class differs from a unanimous block class --")
    P("     FAILS (L9 binds at mid at the finer granularity; any future")
    P("     narrowing claim at mid must confront this cut's 16-block")
    P("     content first (named here, not specified here)).")
else:
    P("     (d) INVALID.")
P("     NAMED, NOT HIDDEN: this cut's C3 is NOT the twelfth cut's")
P("     in-window replication form and NOT the pair-representation check")
P("     of cuts 2-9 (no same-ratio pair is measured this cut); the")
P("     committed C3 scoreboard is untouched content. The cross-window")
P("     disagreement (L9) is confronted in W3, not in C3's letter.")
P("")

# W1 -- THE 16-BLOCK CONFRONTATION (the cut verdict; both channels)
if c2_letter == "(d)" or c3_letter == "(d)" or not c1_ok:
    w1_letter = "(d)"
else:
    c2_pass = c2_letter in ("(a)", "(b)")
    c3_pass = c3_letter in ("(a)", "(b)")
    if c2_pass and c3_pass:
        w1_letter = "(a)"
    elif c2_pass != c3_pass:
        w1_letter = "(b)"
    else:
        w1_letter = "(c)"
P("   W1 THE 16-BLOCK CONFRONTATION -- THE CUT VERDICT (both points'")
P("   channels decided here; W1 (d) also fires on C1 (b)):")
P(f"     C2 (bis stability): {c2_letter}")
P(f"     C3 (mid stability): {c3_letter}")
P(f"     W1 {w1_letter}")
if w1_letter == "(a)":
    P("     (a) BOTH points PASS at 16 blocks; the narrowing channel re-")
    P("     opens at BOTH points for LATER pre-registered cuts (NOT")
    P("     queued).")
elif w1_letter == "(b)":
    which = "bis (255,045)" if c2_letter in ("(a)", "(b)") else "mid (254,882)"
    P(f"     (b) EXACTLY ONE PASSES: the channel re-opens at {which} only")
    P("     (NEW pre-registered cut required, NOT queued).")
elif w1_letter == "(c)":
    P("     (c) NEITHER PASSES -- L9 binds at BOTH points at 16-block")
    P("     granularity; any future narrowing claim at either point must")
    P("     confront this cut's 16-block content first (named here, not")
    P("     specified here).")
else:
    P("     (d) INVALID (C1 (b) or the frozen INVALIDATION criterion")
    P("     leaves W1 unevaluable).")
P("     Under ALL outcomes: NO bracket movement -- the committed bracket")
P("     stays EXACTLY (254,557, 255,208]; the MID-ONLY NARROWING CLAIM")
P("     stays SUSPENDED (named, not claimed); NO claim at hi, NO claim")
P("     at lo, NO claim at either measured point beyond channel status;")
P("     no boundary between grid points is ever claimed (L5).")
P("")

# W2 dispersion (descriptive)
P("   W2 (pre-registered, descriptive) DISPERSION QUANTIFICATION: per")
P("   arm, per run (descriptive, never classifying -- L10): the (sum,128,")
P("   S=16) per-cell median value and the 18-cell min..max of per-cell")
P("   medians (section 2); per block: pooled median (sum,128,S=16), 18-")
P("   cell min..max, class; pooled-48: same (section 3); the per-run 18-")
P("   cell min trajectory across the 48 runs in frozen order (the")
P("   quantity observed moving across the frozen 1,000 boundary -- L9's")
P("   named content) and the boundary-crossing count (runs with 18-cell")
P("   min >= 1,000):")
for tag in ("mid", "bis"):
    traj = []
    cross = 0
    for r in range(1, 49):
        vals = [cell_median(tag, (r,), kk) for kk in ok_cells]
        mn = min(vals)
        traj.append(f"{mn:.0f}")
        if mn >= 1000:
            cross += 1
    P(f"     {tag} per-run 18-cell min: " + " ".join(traj))
    P(f"     {tag}: runs with 18-cell min >= 1,000 (COMPUTED here, "
      f"descriptive): {cross}/48")
P("     (the twelfth cut's computed counts at 24 runs: mid "
  f"{sum(1 for v in traj136['mid'] if v >= 1000)}/24, bis "
  f"{sum(1 for v in traj136['bis'] if v >= 1000)}/24; the eleventh cut's")
P("     at 24 runs: mid "
  f"{sum(1 for v in traj132['mid'] if v >= 1000)}/24, hi "
  f"{sum(1 for v in traj132['hi'] if v >= 1000)}/24; the tenth cut's at")
P("     12 runs: mid "
  f"{sum(1 for v in S129_TRAJ['mid'] if v >= 1000)}/12, lo "
  f"{sum(1 for v in S129_TRAJ['lo'] if v >= 1000)}/12 -- all parsed, "
  "quote-only)")
P("   NO point is placed or moved on the committed row by this cut (it")
P("   measures no new grid point; frozen protocol section 5 W2); the")
P("   committed row is QUOTE-ONLY below (parsed from publication-")
P("   s136.txt's committed W2 table; NO interpolation (L5); class")
P("   granularity only; * = the session-26 point carries its C3 (b)")
P("   caveat):")
P("")
P("     n          work-unit     ticks  class                source")
for lbl, n, ticks, cls, src in B3ROW:
    P(f"     {n:<10} {lbl:<13} {ticks:>5}  {cls:<20} {src} "
      f"(publication-s136.txt committed bytes, quote-only)")
P("")

# W3 history comparisons (descriptive)
P("   W3 (pre-registered, descriptive) THE HISTORY COMPARISONS (the")
P("   cross-window confrontation, L9):")
P(f"     (i) mid's 16 blocks + pooled-48 vs the same binary's FOUR")
P(f"         committed windows (s125 {MID125_MED} {MID125_CLASS}, 18-cell")
P(f"         {MID125_18}; s129 block medians "
  + "/".join(b[1] for b in S129_MID_BLOCKS)
  + f", pooled-12 {S129_MID_POOLED[0]} {S129_MID_POOLED[2]}; s132 block")
P(f"         medians "
  + "/".join(str(b[1]) for b in S132_MID_BLOCKS)
  + f", pooled-24 {S132_MID_POOLED[0]} {S132_MID_POOLED[2]}; s136 block")
P(f"         medians "
  + "/".join(str(b[1]) for b in S136_MID_BLOCKS)
  + f", pooled-24 {S136_MID_POOLED[0]} {S136_MID_POOLED[2]}):")
P(f"         this cut's mid blocks (sum,128,16): "
  + " / ".join(f"{unit_rows[('mid', f'block{j}')][0]:.0f}" for j in range(1, 17))
  + f"; pooled-48 {unit_rows[('mid', 'pooled-48')][0]:.0f} "
    f"{unit_rows[('mid', 'pooled-48')][3]}")
P(f"     (ii) bis's 16 blocks + pooled-48 vs its ONE committed window")
P(f"         (s136 block medians "
  + "/".join(str(b[1]) for b in S136_BIS_BLOCKS)
  + f", pooled-24 {S136_BIS_POOLED[0]} {S136_BIS_POOLED[2]}) and the")
P(f"         bracket endpoints' committed content (lo pooled-12 "
  f"{S129_LO_POOLED[0]} {S129_LO_POOLED[2]}; hi pooled-24 "
  f"{S132_HI_POOLED[0]} {S132_HI_POOLED[2]} -- quote-only):")
P(f"         this cut's bis blocks (sum,128,16): "
  + " / ".join(f"{unit_rows[('bis', f'block{j}')][0]:.0f}" for j in range(1, 17))
  + f"; pooled-48 {unit_rows[('bis', 'pooled-48')][0]:.0f} "
    f"{unit_rows[('bis', 'pooled-48')][3]}")
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
P("     the twelfth cut's X1 content (parsed, quote-only):")
for t in ("mid", "bis"):
    lo_, hi_, sp, pct, k = x1_136[t]
    P(f"       {t}: {lo_}..{hi_} (spread {sp} = {pct}% of min; k={k})")
P("     host_ns is the HOST-side proxy (L3), not a C criterion; any")
P("     excursion is NAMED, NOT HIDDEN and its cause is UNMEASURED.")
P("")

P("5. VERDICT SUMMARY: C1 {0}; C2 {1} at bis (255,045); C3 {2} at mid; "
  "W1 {3}."
  .format("(a)" if c1_ok else "(b)", c2_letter, c3_letter, w1_letter))
if w1_letter == "(a)":
    P("   CUT VERDICT: BOTH points PASS at 16-block granularity; the")
    P("   narrowing channel re-opens at BOTH points for LATER pre-")
    P("   registered cuts (NOT queued).")
elif w1_letter == "(b)":
    which = "bis (255,045)" if c2_letter in ("(a)", "(b)") else "mid (254,882)"
    P(f"   CUT VERDICT: EXACTLY ONE PASSES -- the channel re-opens at")
    P(f"   {which} only (NEW pre-registered cut required, NOT queued).")
elif w1_letter == "(c)":
    P("   CUT VERDICT: NEITHER PASSES -- L9 binds at BOTH points at 16-")
    P("   block granularity; any future narrowing claim at either point")
    P("   must confront this cut's 16-block content first (named here,")
    P("   not specified here).")
else:
    P("   CUT VERDICT: INVALID.")
P("   Under ALL outcomes: NO bracket movement -- the committed bracket")
P("   stays EXACTLY (254,557, 255,208]; the MID-ONLY NARROWING CLAIM")
P("   stays SUSPENDED (named, not claimed) and is NOT made by this cut.")
P("   WHY any class occurs is UNMEASURED and NO causal mechanism is")
P("   claimed. Under ALL outcomes: NO claim at hi, NO claim at lo (L5).")
P("   BAR NON-INTERFERENCE (frozen protocol section 6): these runs are")
P("   BISECT CONTENT and NOT bar readings -- NO settle-bar-ledger.txt")
P("   append, NO UTC-day slot consumption, NO movement of the bar's")
P("   SETTLED INTERMEDIATE/MIXED verdict (the s117 committed landing),")
P("   NO Rule 4 workgroup row movement, NO :measured? flag change (the")
P("   accelerator-targets rows stay exactly as ADR-0358 left them).")

with open(os.path.join(HERE, "publication-s139.txt"), "w") as f:
    f.write("\n".join(out) + "\n")
