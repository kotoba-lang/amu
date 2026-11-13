#!/usr/bin/env python3
"""JUN-59 session 147 analysis -- THE B=3 PER-DISPATCH-WORK THRESHOLD
BISECT, FOURTEENTH CUT -- THE WANDER-BAND TOLERANCE CUT AT MID (the
MID-ONLY NARROWING CLAIM's realization attempt; bis is NOT measured --
the per-point rule: no claim at 255,045 from this cut).
ANALYSIS half over the 54 committed run logs of the s147 measurement
half (this directory), under the frozen
anv-b3bisect14prereg-20261031/protocol.txt (freeze stamp
2026-10-31T19:54:33Z BEFORE any run log of this cut existed).

Route (the state-s147.txt NOT DONE (a) input rule): this script parses
ONLY the 54 committed run logs in its own directory
(run-<tag>-r<NN>.txt) and the NAMED COMMITTED WANT SOURCES (the s27
controls census; the s125/s129/s132/s136/s139 publications' committed
quotes -- all parsed here from committed bytes, never transcribed) and
writes publication-s147.txt. No other input. Deterministic: running it
twice yields byte-identical publication-s147.txt (checked by cmp after
the recorded run). Every want source is parsed with fail-closed
regexes; a want that does not parse aborts (assert).

The frozen letters (protocol): C1 (control replication, unchanged from
the s139 cut protocol) / C2 (mid tolerance stability at 16-block
granularity under THE WANDER-BAND TOLERANCE RULE -- RE-DEFINED for
this cut: a block's (and the pooled-48 arm's) 18-cell min classifies
TOLERANT-INTERMEDIATE/MIXED iff <= 980, TOLERANT-CAPTURED iff >= 1,016,
IN-BAND-UNDECIDED iff strictly between (the measured wander band
981..1,015 at integer granularity); C2 (a) STABLE-TOLERANT-
INTERMEDIATE (all 16 blocks + pooled-48 min <= 980) / (b) STABLE-
TOLERANT-CAPTURED (all >= 1,016) / (c) TOLERANCE-UNRESOLVED (any
in-band min or mixed classes) / (d) INVALID) / W1 (cut verdict) / W2
(descriptive: per-run 18-cell min trajectory with crossings at 1,000
AND in-band counts 981..1,015) / W3 (cross-window letter) / X1
(host_ns spread, descriptive). The frozen-rule class labels (the 18-
cell MIN at the 1,000-tick threshold: FLOOR <= 100 at all 18 cells;
CAPTURED >= 1000 at all 18; anything else INTERMEDIATE/MIXED) are
reported alongside as THE RECORD; per the pre-registered supersession
(protocol arm (a)) this cut's C2 tolerant classes supersede the
committed frozen-rule class labels AT MID FOR THIS CLAIM'S DECISION
ONLY.
"""
import math
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

GPU = os.path.join(HERE, "..")

# tag -> (BATCH, WORK_MUL, NDIV, k), frozen protocol ARM TABLE
# (3 rows = 54 fresh processes; self-check 3+48+3 = 54)
ARMS = [("c2", 2, 1, 1, 3), ("mid", 3, 248, 973, 48), ("c8", 8, 1, 1, 3)]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMW = {a[0]: a[2] for a in ARMS}
ARMD = {a[0]: a[3] for a in ARMS}
ARMK = {a[0]: a[4] for a in ARMS}
N_BASE = 1000003
BLOCKS = {"mid": [tuple(range(3 * j - 2, 3 * j + 1)) for j in range(1, 17)]}
UNIT48 = tuple(range(1, 49))

# THE WANDER-BAND TOLERANCE RULE (frozen thresholds, protocol arm (c)):
# 18-cell min <= 980 -> TOLERANT-INTERMEDIATE/MIXED; >= 1,016 ->
# TOLERANT-CAPTURED; strictly between -> IN-BAND-UNDECIDED (the
# measured wander band 981..1,015 at integer granularity; exact pooled
# medians can be half-integers at even sample counts -- a value in
# (980, 1016) is IN-BAND-UNDECIDED under any reading).
TOL_IM_MAX = 980
TOL_CAP_MIN = 1016


def tol_class(v):
    if v <= TOL_IM_MAX:
        return "TOLERANT-INTERMEDIATE/MIXED"
    if v >= TOL_CAP_MIN:
        return "TOLERANT-CAPTURED"
    return "IN-BAND-UNDECIDED"


def fmt(v):
    if isinstance(v, str):
        return v
    if float(v).is_integer():
        return str(int(v))
    return f"{v:.1f}"


def flat(text):
    return re.sub(r"\s+", " ", text)


def parse1(text, pattern, what):
    m = re.search(pattern, flat(text))
    assert m is not None, f"WANT SOURCE NOT PARSED: {what}"
    return m.group(1).strip()


# ---- NAMED COMMITTED WANT SOURCES (parsed from committed bytes, never
# ---- transcribed; fail-closed) ----
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
pub139 = open(os.path.join(GPU, "anv-b3bisect13-20261031",
                           "publication-s139.txt")).read()

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
MID125_MED, MID125_18 = m.group(1), m.group(2)
MID125_CLASS = parse1(pub125, r"class mid \(B=3, WM=248, NDIV=973, n=254882, "
                              r"\S+ nominal units\): (\S+(?:/\S+)*)",
                      "mid s125 class")


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
    pooled = (m.group(2), f"{m.group(3)}..{m.group(4)}", m.group(5))
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


def pub_arm_rows(pub, tag, nblocks, pooled_label):
    """(block rows [(label, med, lo, hi, cls)], pooled (med, 'lo..hi', cls))
    parsed from a publication's section-3 arm section (quote-only
    strings -- printed committed bytes are the record)."""
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
        m = re.match(r" +(block\d+|" + pooled_label + r") +runs \S+ +\(sum,128,16\) "
                     r"+(\S+) +18-cell +(\S+)\.\.(\S+) +(\S+)", l)
        assert m is not None, f"WANT SOURCE NOT PARSED: {tag} row: {l}"
        if m.group(1) == pooled_label:
            pooled = (m.group(2), f"{m.group(3)}..{m.group(4)}", m.group(5))
        else:
            rows.append((m.group(1), m.group(2), m.group(3), m.group(4),
                         m.group(5)))
    assert len(rows) == nblocks and pooled is not None, f"{tag} rows {len(rows)}"
    return rows, pooled


S132_MID_BLOCKS, S132_MID_POOLED = pub_arm_rows(pub132, "mid", 8, "pooled-24")
S132_HI_BLOCKS, S132_HI_POOLED = pub_arm_rows(pub132, "hi", 8, "pooled-24")
S136_MID_BLOCKS, S136_MID_POOLED = pub_arm_rows(pub136, "mid", 8, "pooled-24")
S136_BIS_BLOCKS, S136_BIS_POOLED = pub_arm_rows(pub136, "bis", 8, "pooled-24")
S139_MID_BLOCKS, S139_MID_POOLED = pub_arm_rows(pub139, "mid", 16, "pooled-48")
S139_BIS_BLOCKS, S139_BIS_POOLED = pub_arm_rows(pub139, "bis", 16, "pooled-48")

# per-run 18-cell min trajectories (the W2 quantities, prior windows)
def traj(pub, tag, want):
    m = re.search(rf"{tag} per-run 18-cell min: ([\d ]+)", flat(pub))
    assert m is not None, f"WANT SOURCE NOT PARSED: {tag} trajectory"
    vals = [int(x) for x in m.group(1).split()]
    assert len(vals) == want, f"{tag} trajectory length {len(vals)} != {want}"
    return vals


TRAJ132 = {"mid": traj(pub132, "mid", 24), "hi": traj(pub132, "hi", 24)}
TRAJ136 = {"mid": traj(pub136, "mid", 24), "bis": traj(pub136, "bis", 24)}
TRAJ139 = {"mid": traj(pub139, "mid", 48), "bis": traj(pub139, "bis", 48)}


# X1 content (per-run host_ns spread), parsed from each publication's
# own X1 section (the LAST "X1 (descriptive" marker -- section-0 quotes
# of earlier windows carry the same phrase and are NOT this window's)
def x1_rows(pub, tags):
    idx = pub.rfind("X1 (descriptive")
    assert idx != -1, "WANT SOURCE NOT PARSED: X1 section"
    tail = pub[idx:]
    out = {}
    for t in tags:
        m = re.search(rf"{t}: per-run host_ns median min\.\.max (\d+)\.\.(\d+) "
                      rf"\(spread (\d+) = ([\d.]+)% of min; k=(\d+)\)", tail)
        assert m is not None, f"WANT SOURCE NOT PARSED: X1 {t}"
        out[t] = (int(m.group(1)), int(m.group(2)), int(m.group(3)),
                  m.group(4), int(m.group(5)))
    return out


X1_136 = x1_rows(pub136, ("mid", "bis"))
X1_139 = x1_rows(pub139, ("mid", "bis"))

# the named pooled-window content at the claim points (protocol arm
# (d)): lo pooled-12 / hi pooled-24 quoted in publication-s136.txt's
# W3; mid pooled-48 from publication-s139.txt section 3 (parsed above)
m = re.search(r"\(lo pooled-12 (\d+) (INTERMEDIATE/MIXED|CAPTURED); "
              r"hi pooled-24 (\d+) (INTERMEDIATE/MIXED|CAPTURED) -- quote-only",
              flat(pub136))
assert m is not None, "WANT SOURCE NOT PARSED: pub136 pooled-window quotes"
LO_POOLED12 = (m.group(1), m.group(2))
HI_POOLED24 = (m.group(3), m.group(4))

# the W2 row-table dual-class content at the claim points (protocol arm
# (d)): the committed publication-s139.txt W2 table rows at n=254,557
# (2 rows) and n=254,882 (3 rows), fail-closed counts
W2CLAIM = {"254557": [], "254882": []}
for l in pub139.splitlines():
    m = re.match(r" +(254557|254882) +(\S+) +(\d+) +(INTERMEDIATE/MIXED|CAPTURED)"
                 r"\*? +(session (\d+).*)", l)
    if m:
        W2CLAIM[m.group(1)].append((int(m.group(3)), m.group(4), m.group(6),
                                    m.group(5)))
assert len(W2CLAIM["254557"]) == 2, f"254557 claim rows {len(W2CLAIM['254557'])}"
assert len(W2CLAIM["254882"]) == 3, f"254882 claim rows {len(W2CLAIM['254882'])}"

# THE SUPERSESSION CONTENT (protocol arm (a)) -- COMPUTED here from the
# parsed s139 block/pooled 18-cell minima (printed committed values are
# the record): the tolerance-rule classification of every committed
# block/pooled arm at mid AND bis
COMMITTED_MINIMA = ([int(r[2]) for r in S139_MID_BLOCKS]
                    + [int(r[2]) for r in S139_BIS_BLOCKS]
                    + [int(S139_MID_POOLED[1].split("..")[0]),
                       int(S139_BIS_POOLED[1].split("..")[0])])
assert len(COMMITTED_MINIMA) == 34, f"committed minima {len(COMMITTED_MINIMA)}"
COMMITTED_TOL = [tol_class(v) for v in COMMITTED_MINIMA]
COMMITTED_ALL_INBAND = all(c == "IN-BAND-UNDECIDED" for c in COMMITTED_TOL)

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
    return cells, verifies, samples, header


def med(xs):
    return statistics.median(xs)


out = []
P = out.append
P("JUN-59 session 147 analysis -- THE B=3 PER-DISPATCH-WORK THRESHOLD")
P("BISECT, FOURTEENTH CUT -- THE WANDER-BAND TOLERANCE CUT AT MID (the")
P("MID-ONLY NARROWING CLAIM's realization attempt; bis is NOT measured")
P("-- the per-point rule: no claim at 255,045 from this cut); ZERO NEW")
P("KNOB TRIPLES; NO new grid point.")
P("publication -- the ANALYSIS half over the 54 committed run logs of")
P("the s147 measurement half (this directory), under the frozen")
P("anv-b3bisect14prereg-20261031/protocol.txt (freeze stamp")
P("2026-10-31T19:54:33Z BEFORE any run log of this cut existed).")
P("Produced ONLY by analysis-s147.py over the 54 committed run logs in")
P("this directory (run-<tag>-r<NN>.txt) and the NAMED COMMITTED WANT")
P("SOURCES parsed below (the s27 controls census; the s125/s129/s132/")
P("s136/s139 publications' committed quotes, parsed from committed")
P("bytes, never transcribed). Arms = binary compile-time (BATCH,")
P("WORK_MUL, NDIV); n = (1,000,003*WORK_MUL)/NDIV (integer floor). The")
P("row question (protocol): AT FIXED B=3, IS mid (248,973) n=254,882")
P("TOLERANCE-STABLE AT 16-BLOCK GRANULARITY (16 blocks of 3 runs +")
P("pooled-48) UNDER THE PRE-REGISTERED WANDER-BAND TOLERANCE RULE, AT")
P("ITS BYTE-IDENTICAL PINNED BINARY cabff942...? Classification")
P("statistic for C2 (protocol arm (c), frozen BEFORE runs): a unit's")
P("18-cell min (the minimum over the 18 pipeline-ok cells of the")
P("per-cell pooled median gpu_ticks) -- <= 980 TOLERANT-INTERMEDIATE/")
P("MIXED, >= 1,016 TOLERANT-CAPTURED, strictly between IN-BAND-")
P("UNDECIDED (the measured wander band 981..1,015 at integer")
P("granularity). The frozen-rule class labels (FLOOR <= 100 at all 18")
P("cells; CAPTURED >= 1000 at all 18; anything else INTERMEDIATE/")
P("MIXED -- the 18-cell MIN at the 1,000-tick threshold) are reported")
P("alongside as THE RECORD; per the pre-registered supersession")
P("(protocol arm (a)) this cut's C2 tolerant classes SUPERSEDE the")
P("committed frozen-rule class labels AT MID FOR THIS CLAIM'S DECISION")
P("ONLY. BAR NON-INTERFERENCE: the cut's runs are BISECT CONTENT and")
P("NOT bar readings -- no ledger append, no day-slot consumption, no")
P("bar verdict movement, no Rule 4 row or :measured? flag movement. WHY")
P("any class occurs is UNMEASURED (L2 binds); NO causal mechanism is")
P("claimed. 1 tick = timestampPeriod = 52.083 ns.")
P("")

P("0. NAMED COMMITTED WANT SOURCES (parsed here from committed bytes;")
P("   every value below is a QUOTE-ONLY comparison value and never this")
P("   session's measurement):")
P(f"   committed controls (s27 census): {ctl}")
P("   mid = the (248,973) pair at n=254,882 -- the claimed anchor's")
P("   committed history (all readings at byte-identical binaries):")
P(f"   session 125 (the ninth cut, mid arm): {MID125_MED}, "
  f"18-cell {MID125_18},")
P(f"   class {MID125_CLASS}")
P("   session 129 (the tenth cut): block rows (parsed):")
for lbl, medv, lo_, hi_, cls in S129_MID_BLOCKS:
    P(f"     {lbl} median {medv} 18-cell {lo_}..{hi_} {cls}")
P(f"     pooled-12 median {S129_MID_POOLED[0]} 18-cell "
  f"{S129_MID_POOLED[1]} {S129_MID_POOLED[2]}")
P("   session 132 (the eleventh cut): block rows (parsed):")
for lbl, medv, lo_, hi_, cls in S132_MID_BLOCKS:
    P(f"     {lbl} median {medv} 18-cell {lo_}..{hi_} {cls}")
P(f"     pooled-24 median {S132_MID_POOLED[0]} 18-cell "
  f"{S132_MID_POOLED[1]} {S132_MID_POOLED[2]}")
P("   session 136 (the twelfth cut): block rows (parsed):")
for lbl, medv, lo_, hi_, cls in S136_MID_BLOCKS:
    P(f"     {lbl} median {medv} 18-cell {lo_}..{hi_} {cls}")
P(f"     pooled-24 median {S136_MID_POOLED[0]} 18-cell "
  f"{S136_MID_POOLED[1]} {S136_MID_POOLED[2]}")
P("   session 139 (the thirteenth cut): block rows (parsed; the named")
P("   content this cut confronts, protocol arm (a)):")
for lbl, medv, lo_, hi_, cls in S139_MID_BLOCKS:
    P(f"     {lbl} median {medv} 18-cell {lo_}..{hi_} {cls}")
P(f"     pooled-48 median {S139_MID_POOLED[0]} 18-cell "
  f"{S139_MID_POOLED[1]} {S139_MID_POOLED[2]}")
P("   bis (3,316,1239) at n=255,045 -- NOT measured this cut (the")
P("   per-point rule: no claim at 255,045 from this cut); the s139")
P("   16-block committed content (parsed) enters the supersession")
P("   census below:")
for lbl, medv, lo_, hi_, cls in S139_BIS_BLOCKS:
    P(f"     {lbl} median {medv} 18-cell {lo_}..{hi_} {cls}")
P(f"     pooled-48 median {S139_BIS_POOLED[0]} 18-cell "
  f"{S139_BIS_POOLED[1]} {S139_BIS_POOLED[2]}")
P("   THE SUPERSESSION CONTENT (COMPUTED here from the parsed s139")
P("   block/pooled 18-cell minima -- printed committed values are the")
P("   record; the tolerance-rule classification of every committed")
P("   block/pooled arm at mid AND bis, protocol arm (a)):")
P("     mid 16 block minima: "
  + "/".join(str(int(r[2])) for r in S139_MID_BLOCKS))
P("     bis 16 block minima: "
  + "/".join(str(int(r[2])) for r in S139_BIS_BLOCKS))
P(f"     pooled minima: mid {S139_MID_POOLED[1].split('..')[0]}, "
  f"bis {S139_BIS_POOLED[1].split('..')[0]}")
P(f"     all 34 committed minima in 981..1,015 (IN-BAND-UNDECIDED): "
  f"{COMMITTED_ALL_INBAND} "
  f"({sum(1 for c in COMMITTED_TOL if c == 'IN-BAND-UNDECIDED')}/34 "
  f"IN-BAND-UNDECIDED, "
  f"{sum(1 for c in COMMITTED_TOL if c == 'TOLERANT-INTERMEDIATE/MIXED')}/34 "
  f"TOLERANT-INTERMEDIATE/MIXED, "
  f"{sum(1 for c in COMMITTED_TOL if c == 'TOLERANT-CAPTURED')}/34 "
  f"TOLERANT-CAPTURED)")
P("     -> every committed block/pooled arm at mid (and bis) is")
P("     IN-BAND-UNDECIDED under the tolerance rule; NO committed block")
P("     resolves to a tolerant class; this cut's own runs are what")
P("     would. The committed readings stand as the frozen rule's")
P("     record (rows above).")
P("   lo (405,1591) at n=254,557 -- NOT measured this cut (W1 (b)'s")
P("   'lo is dual-class on the record' content); the tenth cut's")
P("   committed block rows (parsed):")
for lbl, medv, lo_, hi_, cls in S129_LO_BLOCKS:
    P(f"     {lbl} median {medv} 18-cell {lo_}..{hi_} {cls}")
P(f"     pooled-12 median {S129_LO_POOLED[0]} 18-cell "
  f"{S129_LO_POOLED[1]} {S129_LO_POOLED[2]}")
P("   the W2 row-table dual-class content (parsed from committed")
P("   publication-s139.txt W2 table bytes; claim-form confrontation,")
P("   protocol arm (d); fail-closed counts 2 rows at 254,557 and 3 rows")
P("   at 254,882):")
for n in ("254557", "254882"):
    for ticks, cls, sess, src in W2CLAIM[n]:
        P(f"     n={n}: {ticks} {cls} (session {sess}) [{src}]")
P("   the named pooled-window content at the same points (parsed;")
P("   protocol arm (d)):")
P(f"     lo pooled-12 {LO_POOLED12[0]} {LO_POOLED12[1]} "
  f"(publication-s136.txt quote-only)")
P(f"     hi pooled-24 {HI_POOLED24[0]} {HI_POOLED24[1]} "
  f"(publication-s136.txt quote-only)")
P(f"     mid pooled-48 {S139_MID_POOLED[0]} {S139_MID_POOLED[2]} "
  f"(publication-s139.txt section 3)")
P("   the named cross-window disagreement at cabff942... (W3 content):")
P(f"     s132 pooled-24 {S132_MID_POOLED[0]} {S132_MID_POOLED[2]} vs")
P(f"     s136 pooled-24 {S136_MID_POOLED[0]} {S136_MID_POOLED[2]} vs")
P(f"     s139 pooled-48 {S139_MID_POOLED[0]} {S139_MID_POOLED[2]}")
P("   prior W2 per-run 18-cell min trajectories (parsed; computed")
P("   counts at min >= 1,000 AND min in 981..1,015, quote-only:")
for win, tdict, k in (("s129", S129_TRAJ, 12), ("s132", TRAJ132, 24),
                      ("s136", TRAJ136, 24), ("s139", TRAJ139, 48)):
    for t in sorted(tdict):
        vals = tdict[t]
        P(f"     {win} {t} (k={k}): {' '.join(str(v) for v in vals)} "
          f"({sum(1 for v in vals if v >= 1000)}/{k} at min >= 1,000; "
          f"{sum(1 for v in vals if 981 <= v <= 1015)}/{k} in 981..1,015)")
P("   the twelfth/thirteenth cut X1 content (parsed, quote-only):")
for win, xd in (("s136", X1_136), ("s139", X1_139)):
    for t in ("mid", "bis"):
        lo_, hi_, sp, pct, k = xd[t]
        P(f"     {win} {t}: per-run host_ns median min..max {lo_}..{hi_} "
          f"(spread {sp} = {pct}% of min; k={k})")
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
verify_counts_ok = True
cell_counts_ok = True
tail_ok = True
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
        if len(cells) != 24:
            cell_counts_ok = False
            integrity.append(f"CELL COUNT {len(cells)} != 24 in {fn}")
        if len(verifies) != 24:
            verify_counts_ok = False
            integrity.append(f"VERIFY COUNT {len(verifies)} != 24 in {fn}")
        if "# done cells=24" not in header:
            tail_ok = False
            integrity.append(f"TAIL MISSING in {fn}")
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
        ok_cells_n = [kk for kk, v in cells.items() if v["pipeline"] == "ok"]
        exp = len(ok_cells_n) * 25
        if len(samples) != exp:
            sample_counts_ok = False
            integrity.append(f"SAMPLE COUNT {len(samples)} != {exp} in {fn}")
        for (rnd, idx, bt, mt, dt, gt, gn, pdn, hn_) in samples:
            if bt != b or mt != wm or dt != dd:
                knob_field_ok = False
                integrity.append(f"SAMPLE knob FIELD {bt},{mt},{dt} != {b},{wm},{dd} in {fn}")

P("1. INTEGRITY (computed over the 54 logs):")
P("   runs parsed: 54 (c2 x3, mid x48, c8 x3 -- the frozen ARM TABLE's")
P("   3 rows govern the count; run-count self-check 3+48+3 = 54 -> "
  f"{sum(ARMK[t] for t in TAGS) == 54}); cell map")
P("   identical across runs: "
  f"{cell_keys is not None and not any('CELL MAP' in i for i in integrity)}")
P(f"   headers byte-identical across all runs outside the # n= knob line: {header_ok}")
P(f"   header batch=/work_mul=/ndiv= == run's (B,WM,NDIV) and n == "
  f"(1,000,003*WM)//NDIV; every SAMPLE batch=/work_mul=/ndiv= == (B,WM,NDIV): "
  f"{knob_field_ok}")
P(f"   knob arithmetic (record): (1,000,003*248)//973 = "
  f"{(N_BASE * 248) // 973} == the header n=254882: "
  f"{(N_BASE * 248) // 973 == 254882}; gcd(248,973) = {math.gcd(248, 973)}")
P(f"   every CELL spv= name is an archived .emitted.spv (no .iter -- the "
  f"corpus is byte-identical this session): {spv_identity_ok}")
P(f"   CELL lines: 24 per run in 54/54 runs: {cell_counts_ok}")
P(f"   VERIFY lines: 24 per run in 54/54 runs: {verify_counts_ok}")
P(f"   tail '# done cells=24' in 54/54 runs: {tail_ok}")
P(f"   SAMPLE lines: 450 per run (18 ok cells x 25 rounds) in 54/54 runs: "
  f"{sample_counts_ok}")
P(f"   VERIFY mismatch total over all runs: {verify_mismatch_total} (per-arm: "
  + ", ".join(f"{t}={verify_mismatch_by_arm[t]}" for t in TAGS)
  + ") -- bit-exact correctness re-check inside every run; frozen "
    "INVALIDATION criterion (protocol): >0 in any run makes that run "
    "DEFECTIVE and the arm INVALID (its letters not evaluable)")
P(f"   forcing reality (pipeline-ok cell-runs where probe_size==forced and "
  f"probe_nsub==wg/forced): {forcing_ok}/{forcing_total}")
P(f"   S=8 cells fail-closed (pipeline=FAIL, forced=8): {s8_fail} cell-runs "
  f"(6 per run x 54 runs = 324 expected -- fail-closed, never read as data)")
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


def unit_stats(tag, runs):
    """(v16 median at (sum,128,S=16), 18-cell min, 18-cell max,
    frozen-rule record class, tolerance class)."""
    vals = [cell_median(tag, runs, k) for k in ok_cells]
    v16 = cell_median(tag, runs, sum128)
    lo_, hi_ = min(vals), max(vals)
    if all(v <= 100 for v in vals):
        frozen = "FLOOR"
    elif all(v >= 1000 for v in vals):
        frozen = "CAPTURED"
    else:
        frozen = "INTERMEDIATE/MIXED"
    return v16, lo_, hi_, frozen, tol_class(lo_)


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
        P(f"     r{r:02d}  (sum,128,16) {fmt(v16):>7}   18-cell "
          f"{fmt(min(vals)):>6}..{fmt(max(vals)):<6}   host_ns {fmt(hn)}")
    P("")
P("")

P("3. BLOCK + POOLED-48 CLASSIFICATION (the frozen method applied to")
P("   the pre-registered classification units: block j (j=1..16) = runs")
P("   r(3j-2), r(3j-1), r(3j); pooled-48 pools all 48 runs x 25 rounds")
P("   per cell (a NAMED EXTENSION of the frozen 3-run method, reported")
P("   alongside -- never instead of -- the sixteen block classes).")
P("   Controls have k=3: one block each. Each unit row: pooled median")
P("   gpu_ticks at (sum,128,S=16), 18-cell min..max of per-cell pooled")
P("   medians, the frozen-rule record class AND the tolerance class")
P("   (the C2 decision statistic; controls carry no tolerance class).")
P("   Medians are exact pooled medians -- half-integers can occur only")
P("   at the pooled arms (even sample counts); the tolerance thresholds")
P("   are applied to the exact value (<= 980 / >= 1,016; strictly")
P("   between IN-BAND-UNDECIDED).")
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
        v16, lo_, hi_, frozen, tolc = unit_stats(tag, runs)
        runlabel = ",".join(f"{r:02d}" for r in runs)
        if len(runlabel) > 22:
            runlabel = "01..48"
        if tag in BLOCKS:
            tols = f"tolerance {tolc}"
        else:
            tols = "tolerance n/a (control)"
        P(f"     {label:<20} runs {runlabel:<22} (sum,128,16) {fmt(v16):>7}   "
          f"18-cell {fmt(lo_):>6}..{fmt(hi_):<6}   frozen-rule {frozen:<20} {tols}")
        unit_rows[(tag, label)] = (v16, lo_, hi_, frozen, tolc, runs)
    P("")

P("4. PRE-REGISTERED LETTERS (the frozen letters of the protocol; C2 is")
P("   RE-DEFINED for this cut -- the s139 cut's C2/C3/W1 meanings do")
P("   NOT carry):")
P("")

# C1 (prerequisite; W1 depends on it) -- unchanged from the s139 cut
v_c2 = unit_rows[("c2", "block1 (k=3 control)")][0]
v_c8 = unit_rows[("c8", "block1 (k=3 control)")][0]
cls_c2 = unit_rows[("c2", "block1 (k=3 control)")][3]
cls_c8 = unit_rows[("c8", "block1 (k=3 control)")][3]
c1_c2_ok = cls_c2 == "FLOOR" and C2_BAND[0] <= v_c2 <= C2_BAND[1]
c1_c8_ok = abs(v_c8 - C8_COMMITTED) <= 0.05 * C8_COMMITTED
c1_ok = c1_c2_ok and c1_c8_ok
P("   C1 ARCHIVED CONTROL REPLICATION (prerequisite; W1 depends on it;")
P("   unchanged from the s139 cut protocol): controls have k=3: one")
P("   block each, the frozen method exactly:")
P(f"     c2 (sum,128,S=16) pooled median {fmt(v_c2)}, class {cls_c2} "
  f"(committed floor band {C2_BAND[0]}..{C2_BAND[1]} at B=2): {c1_c2_ok}")
P(f"     c8 (sum,128,S=16) pooled median {fmt(v_c8)} within +/-5% of "
  f"committed {C8_COMMITTED} (session 4 pooled median): {c1_c8_ok} "
  f"({(v_c8 - C8_COMMITTED) / C8_COMMITTED * 100:+.2f}%)")
if c1_ok:
    P("     VERDICT: branch (a) both controls satisfy their criteria --")
    P("     W1 is evaluated against the row question.")
else:
    P("     VERDICT: branch (b) replication discrepancy (W1 interpretation")
    P("     FLAGGED); cause UNMEASURED.")
P("")

# C2 (mid tolerance stability at 16-block granularity)
mid_minima = [unit_rows[("mid", f"block{j}")][1] for j in range(1, 17)]
mid_pooled_min = unit_rows[("mid", "pooled-48")][1]
mid_tol_classes = [unit_rows[("mid", f"block{j}")][4] for j in range(1, 17)]
mid_pooled_tol = unit_rows[("mid", "pooled-48")][4]
if verify_mismatch_by_arm["mid"] > 0:
    c2_letter = "(d)"
elif all(v <= TOL_IM_MAX for v in mid_minima + [mid_pooled_min]):
    c2_letter = "(a)"
elif all(v >= TOL_CAP_MIN for v in mid_minima + [mid_pooled_min]):
    c2_letter = "(b)"
else:
    c2_letter = "(c)"
P("   C2 MID TOLERANCE STABILITY AT 16-BLOCK GRANULARITY -- mid")
P("   (BATCH=3,WORK_MUL=248,NDIV=973) at n=254,882 (16 blocks of 3 runs")
P("   + pooled-48) under THE WANDER-BAND TOLERANCE RULE (protocol arm")
P("   (c); thresholds frozen BEFORE runs: 18-cell min <= 980 TOLERANT-")
P("   INTERMEDIATE/MIXED; >= 1,016 TOLERANT-CAPTURED; strictly between")
P(f"   IN-BAND-UNDECIDED): {c2_letter}")
P("     block 18-cell minima (exact pooled medians): "
  + " / ".join(fmt(v) for v in mid_minima))
P(f"     pooled-48 18-cell min: {fmt(mid_pooled_min)}")
P(f"     tolerance classes: {mid_tol_classes}; pooled-48 tolerance "
  f"class: {mid_pooled_tol}")
P("     (sum,128,S=16): blocks "
  + " / ".join(fmt(unit_rows[("mid", f"block{j}")][0]) for j in range(1, 17))
  + f" ; pooled-48 {fmt(unit_rows[('mid', 'pooled-48')][0])}")
if c2_letter == "(a)":
    P("     (a) STABLE-TOLERANT-INTERMEDIATE: all 16 block minima AND")
    P("     the pooled-48 minimum are <= 980 -- PASSES the 16-block")
    P("     tolerance-stability requirement at mid.")
elif c2_letter == "(b)":
    P("     (b) STABLE-TOLERANT-CAPTURED: all 16 block minima AND the")
    P("     pooled-48 minimum are >= 1,016 -- PASSES the 16-block")
    P("     tolerance-stability requirement at mid (directionally: the")
    P("     tolerant content is CAPTURED, not INTERMEDIATE/MIXED).")
elif c2_letter == "(c)":
    P("     (c) TOLERANCE-UNRESOLVED: any in-band minimum or mixed")
    P("     classes -- FAILS; L9 binds at mid at 16 blocks under the")
    P("     tolerance rule too.")
else:
    P("     (d) INVALID: the frozen INVALIDATION criterion leaves C2")
    P("     unevaluable.")
P("     NAMED, NOT HIDDEN: this cut's C2 tolerant classes SUPERSEDE the")
P("     committed frozen-rule class labels AT MID FOR THIS CLAIM'S")
P("     DECISION ONLY (protocol arm (a)); the committed readings stand")
P("     as the frozen rule's record (section 0) and every committed")
P(f"     block/pooled arm is IN-BAND-UNDECIDED under the tolerance rule "
  f"({COMMITTED_ALL_INBAND}, computed above). The superseded statistic")
P("     is the 18-cell MIN at the frozen 1,000-tick threshold, pre-")
P("     registered within-window unstable near the boundary. WHY any")
P("     class occurs is UNMEASURED (L2 binds).")
P("")

# W1 (cut verdict)
if c2_letter == "(d)" or not c1_ok:
    w1_letter = "(d)"
else:
    w1_letter = c2_letter
P("   W1 CUT VERDICT (the MID-ONLY NARROWING CLAIM's realization")
P("   attempt; W1 (d) also fires on C1 (b)):")
P(f"     C2 (mid tolerance stability): {c2_letter}")
P(f"     W1 {w1_letter}")
if w1_letter == "(a)":
    P("     (a) C2 (a) -> THE MID-ONLY NARROWING CLAIM IS REALIZED (\"THE")
    P("     B=3 CLASS FLIP LIES ABOVE n=254,882\"); the bracket narrows")
    P("     AT MID to (254,882, 255,208] (lower endpoint 254,557 ->")
    P("     254,882 only; upper endpoint carried unchanged on hi's")
    P("     content; NO claim at hi/lo/bis).")
elif w1_letter == "(b)":
    P("     (b) C2 (b) -> direction CONTRADICTED at this window; NO")
    P("     bracket movement (the reverse narrowing is not claimable:")
    P("     lo is dual-class on the record -- section 0); the MID-ONLY")
    P("     NARROWING CLAIM stays SUSPENDED (named, not claimed).")
elif w1_letter == "(c)":
    P("     (c) C2 (c) -> NOTHING MOVES; the MID-ONLY NARROWING CLAIM")
    P("     stays SUSPENDED (named, not claimed).")
else:
    P("     (d) INVALID (C1 (b) or the frozen INVALIDATION criterion")
    P("     leaves W1 unevaluable).")
if w1_letter == "(a)":
    P("     Bracket state: NARROWED AT MID -- (254,882, 255,208]")
    P("     (the lower endpoint moved 254,557 -> 254,882 on this cut's")
    P("     content; the upper endpoint is carried unchanged on hi's")
    P("     content).")
else:
    P("     Under (b)/(c)/(d) the committed bracket stays EXACTLY")
    P("     (254,557, 255,208].")
P("     Under ALL outcomes: NO claim at 255,045 (bis is NOT measured")
P("     this cut), NO claim at hi, NO claim at lo; no boundary between")
P("     grid points is ever claimed (L5).")
P("")

# W2 (descriptive)
P("   W2 (pre-registered, descriptive) per-run 18-cell min trajectory")
P("   across the 48 mid runs in frozen order (the quantity observed")
P("   moving across the frozen 1,000 boundary -- L9's named content),")
P("   the boundary-crossing count (runs with 18-cell min >= 1,000) AND")
P("   the in-band count (runs with 18-cell min in 981..1,015):")
traj147 = []
cross147 = 0
inband147 = 0
for r in range(1, 49):
    vals = [cell_median("mid", (r,), kk) for kk in ok_cells]
    mn = min(vals)
    traj147.append(f"{fmt(mn)}")
    if mn >= 1000:
        cross147 += 1
    if 981 <= mn <= 1015:
        inband147 += 1
P("     mid per-run 18-cell min: " + " ".join(traj147))
P(f"     mid: runs with 18-cell min >= 1,000 (COMPUTED here, "
  f"descriptive): {cross147}/48")
P(f"     mid: runs with 18-cell min in 981..1,015 (COMPUTED here, "
  f"descriptive): {inband147}/48")
P("     (prior windows' computed counts at both thresholds, parsed,")
P("     quote-only):")
for win, tdict, k in (("s129", S129_TRAJ, 12), ("s132", TRAJ132, 24),
                      ("s136", TRAJ136, 24), ("s139", TRAJ139, 48)):
    for t in sorted(tdict):
        vals = tdict[t]
        P(f"       {win} {t} (k={k}): "
          f"{sum(1 for v in vals if v >= 1000)}/{k} at min >= 1,000, "
          f"{sum(1 for v in vals if 981 <= v <= 1015)}/{k} in 981..1,015")
P("   NO point is placed or moved on the committed row by W2 itself")
P("   (descriptive letter); bracket movement rides W1 only.")
P("")

# W3 (cross-window letter)
P("   W3 (pre-registered, descriptive) CROSS-WORD at cabff942... --")
P("   this window is the FOURTH window at the pinned binary (the")
P("   protocol's pre-registered count over the named cross-window")
P("   disagreement series: s132 / s136 / s139 / this window):")
P(f"     this cut's mid blocks (sum,128,16): "
  + " / ".join(fmt(unit_rows[("mid", f"block{j}")][0]) for j in range(1, 17)))
P(f"     ; pooled-48 {fmt(unit_rows[('mid', 'pooled-48')][0])} "
  f"frozen-rule {unit_rows[('mid', 'pooled-48')][3]} "
  f"tolerance {unit_rows[('mid', 'pooled-48')][4]}")
P(f"     block 18-cell minima: "
  + " / ".join(fmt(v) for v in mid_minima)
  + f" ; pooled-48 min {fmt(mid_pooled_min)}")
P("     vs the same binary's committed windows (parsed, quote-only):")
P(f"       s125 {MID125_MED} {MID125_CLASS}, 18-cell {MID125_18}")
P(f"       s129 block medians {'/'.join(b[1] for b in S129_MID_BLOCKS)}, "
  f"pooled-12 {S129_MID_POOLED[0]} {S129_MID_POOLED[2]}")
P(f"       s132 block medians {'/'.join(b[1] for b in S132_MID_BLOCKS)}, "
  f"pooled-24 {S132_MID_POOLED[0]} {S132_MID_POOLED[2]}")
P(f"       s136 block medians {'/'.join(b[1] for b in S136_MID_BLOCKS)}, "
  f"pooled-24 {S136_MID_POOLED[0]} {S136_MID_POOLED[2]}")
P(f"       s139 block medians {'/'.join(b[1] for b in S139_MID_BLOCKS)}, "
  f"pooled-48 {S139_MID_POOLED[0]} {S139_MID_POOLED[2]}")
P("     the named cross-window disagreement (L9 content): s132")
P(f"     pooled-24 {S132_MID_POOLED[0]} {S132_MID_POOLED[2]} vs s136")
P(f"     pooled-24 {S136_MID_POOLED[0]} {S136_MID_POOLED[2]} vs s139")
P(f"     pooled-48 {S139_MID_POOLED[0]} {S139_MID_POOLED[2]}")
P("     claim-form confrontation content (protocol arm (d); parsed):")
for n in ("254557", "254882"):
    for ticks, cls, sess, src in W2CLAIM[n]:
        P(f"       n={n}: {ticks} {cls} (session {sess})")
P(f"       lo pooled-12 {LO_POOLED12[0]} {LO_POOLED12[1]}; hi pooled-24 "
  f"{HI_POOLED24[0]} {HI_POOLED24[1]}; mid pooled-48 "
  f"{S139_MID_POOLED[0]} {S139_MID_POOLED[2]}")
if w1_letter == "(a)":
    P("     Under W1 (a): the claim rides THIS window's tolerant-stable")
    P("     content with the named supersession (this cut's C2 tolerant")
    P("     classes supersede the committed frozen-rule labels AT MID")
    P("     FOR THIS CLAIM'S DECISION ONLY); prior windows' labels ride")
    P("     the pre-registered-unstable statistic (the 18-cell MIN at")
    P("     the 1,000-tick threshold); s139's pooled minimum "
      f"{fmt(int(S139_MID_POOLED[1].split('..')[0]))} is in-band -> "
      "IN-BAND-UNDECIDED under the tolerance rule. The cross-window")
    P("     disagreement's cause stays UNMEASURED (L2 binds).")
else:
    P("     Under W1 (b)/(c)/(d): the MID-ONLY NARROWING CLAIM stays")
    P("     SUSPENDED (named, not claimed); the cross-window")
    P("     disagreement's cause stays UNMEASURED (L2 binds).")
P("")

# X1 (descriptive)
P("   X1 (descriptive, host_ns at (sum,128,S=16); NOT a C criterion")
P("   (L3); per-run host_ns spread is reported):")
for tag in TAGS:
    k = ARMK[tag]
    hs = [cell_median(tag, (r,), sum128, field=8) for r in range(1, k + 1)]
    P(f"     {tag}: per-run host_ns median min..max {fmt(min(hs))}.."
      f"{fmt(max(hs))} (spread {fmt(max(hs) - min(hs))} = "
      f"{(max(hs) - min(hs)) / min(hs) * 100:.1f}% of min; k={k})")
P("     prior windows' X1 content (parsed, quote-only):")
for win, xd in (("s136", X1_136), ("s139", X1_139)):
    for t in ("mid", "bis"):
        lo_, hi_, sp, pct, k = xd[t]
        P(f"       {win} {t}: {lo_}..{hi_} (spread {sp} = {pct}% of min; k={k})")
P("     host_ns is the HOST-side proxy (L3), not a C criterion; any")
P("     excursion is NAMED, NOT HIDDEN and its cause is UNMEASURED.")
P("")

P(f"5. VERDICT SUMMARY: C1 {'(a)' if c1_ok else '(b)'}; C2 {c2_letter} at "
  f"mid (254,882); W1 {w1_letter}.")
if w1_letter == "(a)":
    P("   CUT VERDICT: THE MID-ONLY NARROWING CLAIM IS REALIZED (\"THE B=3")
    P("   CLASS FLIP LIES ABOVE n=254,882\"); the bracket narrows AT MID")
    P("   to (254,882, 255,208] (lower endpoint 254,557 -> 254,882 only;")
    P("   upper endpoint carried unchanged on hi's content).")
elif w1_letter == "(b)":
    P("   CUT VERDICT: direction CONTRADICTED at this window; NO bracket")
    P("   movement (the reverse narrowing is not claimable: lo is")
    P("   dual-class on the record); the MID-ONLY NARROWING CLAIM stays")
    P("   SUSPENDED (named, not claimed).")
elif w1_letter == "(c)":
    P("   CUT VERDICT: NOTHING MOVES; the MID-ONLY NARROWING CLAIM stays")
    P("   SUSPENDED (named, not claimed) and is NOT made by this cut.")
else:
    P("   CUT VERDICT: INVALID.")
if w1_letter == "(a)":
    P("   Bracket state: NARROWED AT MID -- (254,882, 255,208].")
else:
    P("   The committed bracket stays EXACTLY (254,557, 255,208].")
P("   Under ALL outcomes: NO claim at 255,045 (bis is NOT measured this")
P("   cut), NO claim at hi, NO claim at lo; no boundary between grid")
P("   points is ever claimed (L5). WHY any class occurs is UNMEASURED")
P("   and NO causal mechanism is claimed (L2 binds).")
P("   BAR NON-INTERFERENCE (frozen protocol): these runs are BISECT")
P("   CONTENT and NOT bar readings -- NO settle-bar-ledger.txt append,")
P("   NO UTC-day slot consumption, NO movement of the bar's SETTLED")
P("   INTERMEDIATE/MIXED verdict (the s117 committed landing), NO Rule")
P("   4 workgroup row movement, NO :measured? flag change (the")
P("   accelerator-targets rows stay exactly as ADR-0358 left them).")

with open(os.path.join(HERE, "publication-s147.txt"), "w") as f:
    f.write("\n".join(out) + "\n")
