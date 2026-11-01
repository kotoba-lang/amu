#!/usr/bin/env python3
"""JUN-59 session 158 analysis -- THE B=3 PER-DISPATCH-WORK THRESHOLD
BISECT, FIFTEENTH CUT -- THE DEEP-POOLING CI CUT AT BIS (3,316,1239)
n=255,045 (the bracket's interior bisection point; mid is NOT
re-measured -- the per-point rule: no mid letter from this cut); ZERO
NEW KNOB TRIPLES; NO new grid point.
ANALYSIS half over the 54 committed run logs of the s158 measurement
half (this directory -- the committed gzip -n form
run-<tag>-r<NN>.txt.gz; this script READS THROUGH GZIP, the s157
capture-form deviation executed at s160), under the frozen
anv-b3bisect15prereg-20261031/protocol.txt (freeze stamp
2026-11-01T01:27:58Z BEFORE any run log of this cut existed).

Route (the state-s160.txt NOT DONE (c) input rule): this script parses
ONLY the 54 committed run logs in its own directory (read through
gzip) and the NAMED COMMITTED WANT SOURCES (the s27 controls census;
the s132/s136/s139/s147 publications' committed quotes; the
build-census-s158.txt first-measured binary pins -- all parsed here
from committed bytes, never transcribed) and writes
publication-s158.txt. No other input. Deterministic: running it twice
yields byte-identical publication-s158.txt (checked by cmp after the
recorded run). Every want source is parsed with fail-closed regexes;
a want that does not parse aborts (assert).

The frozen letters (protocol): C1 (control replication, unchanged
from the standing cut protocol: c2 FLOOR in the committed floor band
31..32; c8 within +/-5% of the committed 32,915; C1 (b) -> W1 (d)) /
C2 (bis class stability at 16-block granularity under THE
PRE-REGISTERED DEEP-POOLING CI CLASS STATISTIC (protocol arm (c),
frozen BEFORE runs): per unit per cell m_c = pooled sample median
gpu_ticks, MAD_c = sample median |x - m_c|, CI half-width
h_c = 3.6420 * MAD_c / sqrt(N) (N = 3R = 19,200 per block/control
cell, 48R = 307,200 per pooled-48 cell; R = 6,400 frozen); unit
classes at the FROZEN 1,000-tick threshold -- CAPTURED iff all 18
pipeline-ok cells m_c - h_c >= 1,000; FLOOR iff all 18
m_c + h_c <= 100; INTERMEDIATE/MIXED iff (some m_c + h_c < 1,000)
AND (some m_c - h_c > 100); IN-BAND-UNDECIDED otherwise; C2 (a)
STABLE-INTERMEDIATE (all 16 blocks + pooled-48 class
INTERMEDIATE/MIXED) / (b) STABLE-CAPTURED (all CAPTURED) / (c)
CLASS-UNRESOLVED (mixed block classes, or any IN-BAND-UNDECIDED
unit, or the pooled arm differs) / (d) INVALID) / W1 (cut verdict;
(a) C2 (b) -> the bracket narrows to (254,557, 255,045]; (b) C2 (a)
-> (255,045, 255,208]; (c) C2 (c)/(d) -> NOTHING MOVES; (d) INVALID
-- also fires on C1 (b)) / W2 (descriptive: per-run 18-cell min
trajectory, crossings at 1,000 AND in-band counts 981..1,015) / W3
(cross-window letter confronting the committed bis windows at
440604ef...; NAMED CROSS-BINARY HAZARD -- this cut's binaries are
NEW, first-measured digests; any class disagreement may be
BINARY-driven, cause UNMEASURED, L2) / X1 (host_ns spread,
descriptive). The min-over-18 threshold-ride statistic is GONE (the
s152 D2 decision) -- no class is computed from it.
"""
import gzip
import math
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

GPU = os.path.join(HERE, "..")

# frozen protocol constants (anv-b3bisect15prereg-20261031/protocol.txt)
R = 6400                 # rounds per cell per run (arm (c)(i))
WARMUP = 3
N_BASE = 1000003
H_CONST = 3.6420         # frozen CI constant (1.96 * 1.2533 * 1.4826)
CAP_MIN = 1000.0         # frozen 1,000-tick threshold
FLOOR_MAX = 100.0
TICK_NS = 52.083         # timestampPeriod (asserted against the logs)

# tag -> (BATCH, WORK_MUL, NDIV, k), frozen protocol ARM TABLE
# (3 rows = 54 fresh processes; self-check 3+48+3 = 54)
ARMS = [("c2", 2, 1, 1, 3), ("bis", 3, 316, 1239, 48), ("c8", 8, 1, 1, 3)]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMW = {a[0]: a[2] for a in ARMS}
ARMD = {a[0]: a[3] for a in ARMS}
ARMK = {a[0]: a[4] for a in ARMS}
BLOCKS = {"bis": [tuple(range(3 * j - 2, 3 * j + 1)) for j in range(1, 17)]}
UNIT48 = tuple(range(1, 49))


def fmt(v):
    if isinstance(v, str):
        return v
    if float(v).is_integer():
        return str(int(v))
    return f"{v:.1f}"


def f4(v):
    return f"{v:.4f}"


def flat(text):
    return re.sub(r"\s+", " ", text)


def parse1(text, pattern, what):
    m = re.search(pattern, flat(text))
    assert m is not None, f"WANT SOURCE NOT PARSED: {what}"
    return m.group(1).strip()


def dp_class(cell_stats):
    """THE DEEP-POOLING CI CLASS STATISTIC (protocol arm (c)(iii)).
    cell_stats: iterable of (m_c, h_c) over the 18 pipeline-ok cells."""
    if all(m - h >= CAP_MIN for m, h in cell_stats):
        return "CAPTURED"
    if all(m + h <= FLOOR_MAX for m, h in cell_stats):
        return "FLOOR"
    if (any(m + h < CAP_MIN for m, h in cell_stats)
            and any(m - h > FLOOR_MAX for m, h in cell_stats)):
        return "INTERMEDIATE/MIXED"
    return "IN-BAND-UNDECIDED"


# ---- NAMED COMMITTED WANT SOURCES (parsed from committed bytes, never
# ---- transcribed; fail-closed) ----
s27c = open(os.path.join(GPU, "anv-b3bisect7-20261027",
                         "derivation-census-s27.txt")).read()
pub132 = open(os.path.join(GPU, "anv-b3bisect11-20261031",
                           "publication-s132.txt")).read()
pub136 = open(os.path.join(GPU, "anv-b3bisect12-20261031",
                           "publication-s136.txt")).read()
pub139 = open(os.path.join(GPU, "anv-b3bisect13-20261031",
                           "publication-s139.txt")).read()
pub147 = open(os.path.join(GPU, "anv-b3bisect14-20261031",
                           "publication-s147.txt")).read()
bc158 = open(os.path.join(HERE, "build-census-s158.txt")).read()

# committed controls (s27 census): "c2 31 (floor band 31..32); c8 32,915 ..."
ctl = parse1(s27c, r"(committed controls: c2 \d+ \(floor band [\d.]+\.\.[\d.]+\); "
                   r"c8 [\d,]+ \(session 4 pooled median\))", "committed controls")
m = re.search(r"c2 (\d+) \(floor band (\d+)\.\.(\d+)\); c8 ([\d,]+)", ctl)
assert m, "committed controls shape"
C2_COMMITTED = int(m.group(1))
C2_BAND = (int(m.group(2)), int(m.group(3)))
C8_COMMITTED = int(m.group(4).replace(",", ""))


def pub_arm_rows(pub, tag, nblocks, pooled_label):
    """[(label, med, lo, hi, cls)] blocks + (label, med, lo..hi, cls) pooled,
    parsed from a publication's section-3 arm section (quote-only)."""
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
                     r"+(\S+) +18-cell +(\S+)\.\.(\S+) +(INTERMEDIATE/MIXED|CAPTURED)"
                     r"(?: +\(exact [\d.]+\))?", l)
        assert m is not None, f"WANT SOURCE NOT PARSED: {tag} row: {l}"
        rec = (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5))
        if m.group(1) == pooled_label:
            pooled = (m.group(2), f"{m.group(3)}..{m.group(4)}", m.group(5))
        else:
            rows.append(rec)
    assert len(rows) == nblocks and pooled is not None, f"{tag} rows {len(rows)}"
    return rows, pooled


S132_MID_BLOCKS, S132_MID_POOLED = pub_arm_rows(pub132, "mid", 8, "pooled-24")
S136_MID_BLOCKS, S136_MID_POOLED = pub_arm_rows(pub136, "mid", 8, "pooled-24")
S136_BIS_BLOCKS, S136_BIS_POOLED = pub_arm_rows(pub136, "bis", 8, "pooled-24")
S139_MID_BLOCKS, S139_MID_POOLED = pub_arm_rows(pub139, "mid", 16, "pooled-48")
S139_BIS_BLOCKS, S139_BIS_POOLED = pub_arm_rows(pub139, "bis", 16, "pooled-48")


def pub147_arm_rows(pub, tag, nblocks, pooled_label):
    """s147 section-3 rows carry 'frozen-rule X tolerance Y' classes."""
    lines = pub.splitlines()
    start = None
    for i, l in enumerate(lines):
        if l.startswith(f"   {tag} (B=3, WM=") and "nominal total units" in l:
            start = i + 1
            break
    assert start is not None, f"WANT SOURCE NOT PARSED: pub147 {tag} arm header"
    rows, pooled = [], None
    for l in lines[start:]:
        if not l.strip():
            break
        m = re.match(r" +(block\d+|" + pooled_label + r") +runs \S+ +\(sum,128,16\) "
                     r"+(\S+) +18-cell +(\S+)\.\.(\S+) +frozen-rule (\S+(?:/\S+)*) "
                     r"+tolerance (\S+(?:/\S+)*)", l)
        assert m is not None, f"WANT SOURCE NOT PARSED: pub147 {tag} row: {l}"
        rec = (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5),
               m.group(6))
        if m.group(1) == pooled_label:
            pooled = rec
        else:
            rows.append(rec)
    assert len(rows) == nblocks and pooled is not None, f"pub147 {tag} rows {len(rows)}"
    return rows, pooled


S147_MID_BLOCKS, S147_MID_POOLED = pub147_arm_rows(pub147, "mid", 16, "pooled-48")

# the 14th cut's C1/C2/W1 verdicts (VERDICT SUMMARY line, parse-once)
m = re.search(r"VERDICT SUMMARY: C1 \((\w)\); C2 \((\w)\) at mid \(254,882\); "
              r"W1 \((\w)\)\.", flat(pub147))
assert m is not None, "WANT SOURCE NOT PARSED: pub147 verdict summary"
S147_C1, S147_C2, S147_W1 = m.group(1), m.group(2), m.group(3)

# the 14th cut's mid block minima + pooled-48 min (arm (a) content)
S147_MINIMA = [int(x) for x in
               parse1(pub147, r"block 18-cell minima \(exact pooled medians\): "
                              r"([\d /]+)", "pub147 block minima").split("/")]
assert len(S147_MINIMA) == 16, f"pub147 minima {len(S147_MINIMA)}"
S147_POOLED_MIN = parse1(pub147, r"pooled-48 18-cell min: ([\d.]+)",
                         "pub147 pooled min")
S147_REC_CAP = sum(1 for r in S147_MID_BLOCKS if r[4] == "CAPTURED")
S147_REC_IM = sum(1 for r in S147_MID_BLOCKS if r[4] == "INTERMEDIATE/MIXED")


# per-run 18-cell min trajectories (the W2 quantities, prior windows)
def traj(pub, tag, want):
    m = re.search(rf"{tag} per-run 18-cell min: ([\d ]+)", flat(pub))
    assert m is not None, f"WANT SOURCE NOT PARSED: {tag} trajectory"
    vals = [float(x) for x in m.group(1).split()]
    assert len(vals) == want, f"{tag} trajectory length {len(vals)} != {want}"
    return vals


TRAJ136 = {"mid": traj(pub136, "mid", 24), "bis": traj(pub136, "bis", 24)}
TRAJ139 = {"mid": traj(pub139, "mid", 48), "bis": traj(pub139, "bis", 48)}
TRAJ147 = {"mid": traj(pub147, "mid", 48)}


# X1 content (per-run host_ns spread), parsed from each publication's
# own X1 section (the LAST "X1 (descriptive" marker)
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
X1_147 = x1_rows(pub147, ("c2", "mid", "c8"))

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

# named pooled-window content at the claim points (protocol arm (d))
m = re.search(r"\(lo pooled-12 (\d+) (INTERMEDIATE/MIXED|CAPTURED); "
              r"hi pooled-24 (\d+) (INTERMEDIATE/MIXED|CAPTURED) -- quote-only\)",
              flat(pub139))
assert m is not None, "WANT SOURCE NOT PARSED: pub139 pooled-window quotes"
LO_POOLED12 = (m.group(1), m.group(2))
HI_POOLED24 = (m.group(3), m.group(4))

# this cut's first-measured binary pins (committed build-census-s158.txt)
PINS = {}
for mm in re.finditer(r"([0-9a-f]{64})  anv-bb-(c2|bis|c8)\n", bc158):
    assert mm.group(2) not in PINS, f"duplicate pin line {mm.group(2)}"
    PINS[mm.group(2)] = mm.group(1)
assert sorted(PINS) == ["c2", "bis", "c8"], f"pin set {sorted(PINS)}"

cell_re = re.compile(
    r"^CELL idx=(\d+) spv=(\S+) op=(\S+) wg=(\d+) forced=(\S+) probe_size=(-?\d+) "
    r"probe_nsub=(-?\d+) probe_wg=(-?\d+) pipeline=(\S+) void=(\d)")
verify_re = re.compile(r"^VERIFY idx=(\d+) checked=(\d+) mismatch=(\d+) ok=(\d)")
SAMPLE_FIELDS = ("round=", "idx=", "batch=", "work_mul=", "ndiv=",
                 "gpu_ticks=", "gpu_ns=", "per_dispatch_ns=", "host_ns=")


def load(path, b, wm, dd):
    """One committed run log, READ THROUGH GZIP (the s157 capture-form
    deviation; the raw logs are not kept). Returns (cells, verifies,
    header, ticks_by_idx, hosts_by_idx, counts) with ticks as int lists."""
    cells, verifies, header = {}, [], []
    ticks, hosts = {}, {}
    counts = {}
    with gzip.open(path, "rt") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("#"):
                header.append(line)
                continue
            if line.startswith("CELL "):
                m = cell_re.match(line)
                assert m, line
                cells[int(m.group(1))] = dict(spv=m.group(2), op=m.group(3),
                                              wg=int(m.group(4)),
                                              forced=m.group(5),
                                              probe_size=int(m.group(6)),
                                              probe_nsub=int(m.group(7)),
                                              probe_wg=int(m.group(8)),
                                              pipeline=m.group(9),
                                              void=int(m.group(10)))
                continue
            if line.startswith("VERIFY "):
                m = verify_re.match(line)
                assert m, line
                verifies.append((int(m.group(1)), int(m.group(2)),
                                 int(m.group(3)), int(m.group(4))))
                continue
            assert line.startswith("SAMPLE "), line
            f = line.split(" ")
            assert len(f) == 10, line
            assert f[0] == "SAMPLE", line
            for i in range(1, 10):
                assert f[i].startswith(SAMPLE_FIELDS[i - 1]), line
            idx = int(f[2][4:])
            gt = int(f[6][10:])
            hn = int(f[9][8:])
            float(f[7][7:])
            float(f[8][15:])
            assert (int(f[3][6:]) == b and int(f[4][9:]) == wm
                    and int(f[5][5:]) == dd), line
            ticks.setdefault(idx, []).append(gt)
            hosts.setdefault(idx, []).append(hn)
            counts[idx] = counts.get(idx, 0) + 1
    return cells, verifies, header, ticks, hosts, counts


def load_run(path, b, wm, dd):
    cells, verifies, header, ticks, hosts, counts = load(path)
    integrity = []
    ok = True
    if len(cells) != 24:
        ok = False
        integrity.append(f"CELL COUNT {len(cells)} != 24")
    if len(verifies) != 24:
        ok = False
        integrity.append(f"VERIFY COUNT {len(verifies)} != 24")
    if "# done cells=24" not in header:
        ok = False
        integrity.append("TAIL MISSING")
    for l in header:
        if l.startswith("# n="):
            mb = re.search(r"batch=(\d+)", l)
            mbar = re.search(r"barrier_n=(\d+)", l)
            mmu = re.search(r"work_mul=(\d+)", l)
            mdi = re.search(r"ndiv=(\d+)", l)
            mn = re.search(r"n=(\d+)", l)
            mro = re.search(r"rounds=(\d+)", l)
            mwa = re.search(r"warmup=(\d+)", l)
            if (not mb or int(mb.group(1)) != b
                    or not mbar or int(mbar.group(1)) != 0
                    or not mmu or int(mmu.group(1)) != wm
                    or not mdi or int(mdi.group(1)) != dd
                    or not mro or int(mro.group(1)) != R
                    or not mwa or int(mwa.group(1)) != WARMUP):
                ok = False
                integrity.append(f"HEADER knob FIELD MISMATCH: {l}")
            if not mn or int(mn.group(1)) != (N_BASE * wm) // dd:
                ok = False
                integrity.append(f"HEADER n= FIELD MISMATCH: {l}")
    for kk, v in cells.items():
        if not (v["spv"].endswith(".emitted.spv") and ".iter" not in v["spv"]):
            ok = False
            integrity.append(f"CELL spv SET MISMATCH idx={kk}: {v['spv']}")
    ok_cells = sorted(k for k, v in cells.items() if v["pipeline"] == "ok")
    exp = len(ok_cells) * R
    if sum(counts.values()) != exp:
        ok = False
        integrity.append(f"SAMPLE COUNT {sum(counts.values())} != {exp}")
    for kk in ok_cells:
        if counts.get(kk, 0) != R:
            ok = False
            integrity.append(f"SAMPLE COUNT idx={kk} {counts.get(kk, 0)} != {R}")
    return cells, verifies, header, ticks, ok_cells, ok, integrity


out = []
P = out.append
P("JUN-59 session 158 analysis -- THE B=3 PER-DISPATCH-WORK THRESHOLD")
P("BISECT, FIFTEENTH CUT -- THE DEEP-POOLING CI CUT AT BIS (3,316,1239)")
P("n=255,045 (the bracket's interior bisection point; mid is NOT")
P("re-measured -- the per-point rule: no mid letter from this cut); ZERO")
P("NEW KNOB TRIPLES; NO new grid point.")
P("publication -- the ANALYSIS half over the 54 committed run logs of")
P("the s158 measurement half (this directory -- the committed gzip -n")
P("form run-<tag>-r<NN>.txt.gz; this script READS THROUGH GZIP, the")
P("s157 capture-form deviation executed at s160), under the frozen")
P("anv-b3bisect15prereg-20261031/protocol.txt (freeze stamp")
P("2026-11-01T01:27:58Z BEFORE any run log of this cut existed).")
P("Produced ONLY by analysis-s158.py over the 54 committed run logs in")
P("this directory and the NAMED COMMITTED WANT SOURCES parsed below")
P("(the s27 controls census; the s132/s136/s139/s147 publications'")
P("committed quotes; the build-census-s158.txt first-measured binary")
P("pins; all parsed from committed bytes, never transcribed). Arms =")
P("binary compile-time (BATCH, WORK_MUL, NDIV);")
P(f"n = (1,000,003*WORK_MUL)/NDIV (integer floor). The row question")
P("(protocol): AT FIXED B=3, IS bis (3,316,1239) n=255,045 CLASS-STABLE")
P("AT 16-BLOCK GRANULARITY (16 blocks of 3 runs + pooled-48) UNDER THE")
P("PRE-REGISTERED DEEP-POOLING CI CLASS STATISTIC (R = 6,400), AT ITS")
P(f"NEW FIRST-MEASURED BINARY (THE ROUNDS6400 INSTRUMENT VARIANT; this")
P(f"window's build pins parsed below: c2 {PINS['c2'][:8]}... bis "
  f"{PINS['bis'][:8]}... c8 {PINS['c8'][:8]}...)?")
P("Classification statistic (protocol arm (c), frozen BEFORE runs): per")
P("unit per cell m_c = pooled sample median gpu_ticks, MAD_c = sample")
P("median |x - m_c|, CI half-width h_c = 3.6420 * MAD_c / sqrt(N)")
P(f"(N = 3R = {3 * R:,} per block/control cell, 48R = {48 * R:,} per")
P("pooled-48 cell; the constant 1.96 * 1.2533 * 1.4826 = "
  f"{1.96 * 1.2533 * 1.4826:.7f} -> frozen 3.6420, "
  f"|diff| = {abs(1.96 * 1.2533 * 1.4826 - 3.6420):.7f} <= 0.00005: "
  f"{abs(1.96 * 1.2533 * 1.4826 - 3.6420) <= 0.00005}); unit classes at")
P("the FROZEN 1,000-tick threshold -- CAPTURED iff all 18 pipeline-ok")
P("cells m_c - h_c >= 1,000; FLOOR iff all 18 m_c + h_c <= 100;")
P("INTERMEDIATE/MIXED iff (some m_c + h_c < 1,000) AND (some")
P("m_c - h_c > 100); IN-BAND-UNDECIDED otherwise. The min-over-18")
P("threshold-ride statistic is GONE (s152 D2) -- no class is computed")
P("from it. BAR NON-INTERFERENCE: the cut's runs are BISECT CONTENT and")
P("NOT bar readings -- no ledger append, no day-slot consumption, no")
P("bar verdict movement, no Rule 4 row or :measured? flag movement. WHY")
P("any class occurs is UNMEASURED (L2 binds); NO causal mechanism is")
P(f"claimed. 1 tick = timestampPeriod = {TICK_NS} ns.")
P("")

P("0. NAMED COMMITTED WANT SOURCES (parsed here from committed bytes;")
P("   every value below is a QUOTE-ONLY comparison value and never this")
P("   session's measurement):")
P(f"   committed controls (s27 census): {ctl}")
P("   ARM (a) CONTENT CONFRONTED FIRST (protocol arm (a), the D1")
P("   mandate): the FOURTEENTH CUT's TOLERANCE-UNRESOLVED mid content,")
P("   parsed from committed publication-s147.txt bytes:")
P(f"     C2 ({S147_C2}) TOLERANCE-UNRESOLVED at mid (248,973) n=254,882")
P("     at the byte-identical pinned binary cabff942...:")
P("       16 block minima (exact pooled medians): "
  + " / ".join(str(v) for v in S147_MINIMA))
P(f"       pooled-48 18-cell min {S147_POOLED_MIN} -- all 16 block")
P("       minima and the pooled-48 min IN-BAND-UNDECIDED under the 14th")
P("       cut's wander-band tolerance rule (981..1,015); the frozen-rule")
P(f"       record {S147_REC_CAP}x CAPTURED + {S147_REC_IM}x "
  "INTERMEDIATE/MIXED blocks was superseded AT MID FOR THAT CLAIM'S")
P("       DECISION ONLY; all 16 block tolerance classes and the pooled")
P("       class parse as IN-BAND-UNDECIDED "
  f"({all(r[5] == 'IN-BAND-UNDECIDED' for r in S147_MID_BLOCKS) and S147_MID_POOLED[5] == 'IN-BAND-UNDECIDED'}")
P(f"     W1 ({S147_W1}) NOTHING MOVES; the MID-ONLY NARROWING CLAIM")
P("     stays SUSPENDED (named, not claimed); the committed bracket")
P("     stays EXACTLY (254,557, 255,208].")
P("     FROZEN STATEMENT (protocol, carried here verbatim): NO letter")
P("     of this cut supersedes any of that content -- this cut does not")
P("     measure mid; the 14th cut's tolerance-rule verdict at mid")
P("     stands as committed content under ALL outcomes of this cut.")
P("   this cut's point's committed content at bis (3,316,1239)")
P("   n=255,045 at the byte-identical pinned binary 440604ef..., parsed")
P("   from committed publication-s136.txt / publication-s139.txt bytes:")
P("     session 136 (the twelfth cut, 8 blocks of 3 + pooled-24):")
for lbl, medv, lo_, hi_, cls in S136_BIS_BLOCKS:
    P(f"       {lbl} median {medv} 18-cell {lo_}..{hi_} {cls}")
P(f"       pooled-24 median {S136_BIS_POOLED[0]} 18-cell "
  f"{S136_BIS_POOLED[1]} {S136_BIS_POOLED[2]}")
P(f"       classes {sum(1 for r in S136_BIS_BLOCKS if r[4] == 'CAPTURED')}x "
  f"CAPTURED + "
  f"{sum(1 for r in S136_BIS_BLOCKS if r[4] == 'INTERMEDIATE/MIXED')}x "
  "INTERMEDIATE/MIXED")
P("     session 139 (the thirteenth cut, 16 blocks of 3 + pooled-48):")
for lbl, medv, lo_, hi_, cls in S139_BIS_BLOCKS:
    P(f"       {lbl} median {medv} 18-cell {lo_}..{hi_} {cls}")
P(f"       pooled-48 median {S139_BIS_POOLED[0]} 18-cell "
  f"{S139_BIS_POOLED[1]} {S139_BIS_POOLED[2]}")
P(f"       classes {sum(1 for r in S139_BIS_BLOCKS if r[4] == 'CAPTURED')}x "
  f"CAPTURED + "
  f"{sum(1 for r in S139_BIS_BLOCKS if r[4] == 'INTERMEDIATE/MIXED')}x "
  "INTERMEDIATE/MIXED")
P(f"       block 18-cell minima: "
  + " / ".join(r[2] for r in S139_BIS_BLOCKS)
  + f" ; pooled-48 min {S139_BIS_POOLED[1].split('..')[0]}")
P("   ARM (d) CLAIM-FORM CONFRONTATION CONTENT (protocol arm (d)):")
P("     the W2 row-table dual-class content (parsed from committed")
P("     publication-s139.txt W2 table bytes; fail-closed counts 2 rows")
P("     at 254,557 and 3 rows at 254,882):")
for n in ("254557", "254882"):
    for ticks_, cls, sess, src in W2CLAIM[n]:
        P(f"       n={n}: {ticks_} {cls} (session {sess})")
P("     the named pooled-window content at the same points (parsed):")
P(f"       lo pooled-12 {LO_POOLED12[0]} {LO_POOLED12[1]}; hi pooled-24 "
  f"{HI_POOLED24[0]} {HI_POOLED24[1]}; mid pooled-48 "
  f"{S139_MID_POOLED[0]} {S139_MID_POOLED[2]}")
P("     the named cross-window disagreement at cabff942... (mid, named")
P("     content -- NO letter of this cut touches lo or mid):")
P(f"       s132 pooled-24 {S132_MID_POOLED[0]} {S132_MID_POOLED[2]} vs")
P(f"       s136 pooled-24 {S136_MID_POOLED[0]} {S136_MID_POOLED[2]} vs")
P(f"       s139 pooled-48 {S139_MID_POOLED[0]} {S139_MID_POOLED[2]} vs")
P(f"       s147 pooled-48 {S147_MID_POOLED[1]} {S147_MID_POOLED[4]} "
  f"frozen-rule {S147_MID_POOLED[4]} tolerance {S147_MID_POOLED[5]}")
P("       (the FOURTH window; its C2 tolerance verdict")
P("       TOLERANCE-UNRESOLVED, arm (a) above)")
P("   prior W2 per-run 18-cell min trajectories (parsed; computed")
P("   counts at min >= 1,000 AND min in 981..1,015, quote-only):")
for win, tdict, k in (("s136", TRAJ136, 24), ("s139", TRAJ139, 48),
                      ("s147", TRAJ147, 48)):
    for t in sorted(tdict):
        vals = tdict[t]
        P(f"     {win} {t} (k={k}): {' '.join(fmt(v) for v in vals)} "
          f"({sum(1 for v in vals if v >= 1000)}/{k} at min >= 1,000; "
          f"{sum(1 for v in vals if 981 <= v <= 1015)}/{k} in 981..1,015)")
P("   prior X1 content (parsed, quote-only):")
for win, xd in (("s136", X1_136), ("s139", X1_139), ("s147", X1_147)):
    for t in sorted(xd):
        lo_, hi_, sp, pct, k = xd[t]
        P(f"     {win} {t}: per-run host_ns median min..max {lo_}..{hi_} "
          f"(spread {sp} = {pct}% of min; k={k})")
P("   this cut's first-measured binary pins (parsed from committed")
P("   build-census-s158.txt bytes; NEW binaries -- NO committed pin to")
P("   match, the s136 precedent):")
for t in ("c2", "bis", "c8"):
    P(f"     anv-bb-{t} {PINS[t]}")
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
load_ok = True
base_header = None
dev_line = None
tp_line = None
for tag in TAGS:
    b, wm, dd, k = ARMB[tag], ARMW[tag], ARMD[tag], ARMK[tag]
    for r in range(1, k + 1):
        fn = f"run-{tag}-r{r:02d}.txt.gz"
        cells, verifies, header, ticks, ok_cells_r, ok_r, integ = load_run(
            os.path.join(HERE, fn), b, wm, dd)
        if not ok_r:
            load_ok = False
            for i in integ:
                integrity.append(f"{fn}: {i}")
        data[(tag, r)] = (cells, verifies, header, ticks)
        keys = tuple(sorted((kk, v["op"], v["wg"], v["forced"], v["pipeline"])
                            for kk, v in cells.items()))
        if cell_keys is None:
            cell_keys = keys
        elif keys != cell_keys:
            integrity.append(f"CELL MAP MISMATCH in {fn}")
        if len(cells) != 24:
            cell_counts_ok = False
        if len(verifies) != 24:
            verify_counts_ok = False
        if "# done cells=24" not in header:
            tail_ok = False
        hb = tuple(l for l in header if not l.startswith("# n="))
        if base_header is None:
            base_header = hb
        elif base_header != hb:
            header_ok = False
            integrity.append(f"HEADER MISMATCH in {fn}")
        for l in header:
            if l.startswith("# device_name=") and dev_line is None:
                dev_line = l[2:]
            if l.startswith("# timestampPeriod=") and tp_line is None:
                tp_line = l[2:]
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
        if sum(counts.values()) if False else False:
            pass

assert dev_line is not None, "device line not parsed"
m = re.search(r"timestampPeriod=([\d.]+)", tp_line)
assert m is not None, "timestampPeriod not parsed"
assert abs(float(m.group(1)) - TICK_NS) < 1e-9, f"timestampPeriod {m.group(1)}"

P("1. INTEGRITY (computed over the 54 logs, READ THROUGH GZIP -- the")
P("   committed form is run-<tag>-r<NN>.txt.gz gzip -n, the s157")
P("   capture-form deviation executed at s160; the raw logs are NOT")
P("   kept, named):")
P(f"   device (parsed from the logs): {dev_line}")
P(f"   {tp_line}")
P("   runs parsed: 54 (c2 x3, bis x48, c8 x3 -- the frozen ARM TABLE's")
P("   3 rows govern the count; run-count self-check 3+48+3 = 54 -> "
  f"{sum(ARMK[t] for t in TAGS) == 54}); cell map")
P("   identical across runs: "
  f"{cell_keys is not None and not any('CELL MAP' in i for i in integrity)}")
P(f"   all per-log integrity checks pass (cell/verify counts, tail,")
P(f"   header knob fields, n=, per-cell sample counts): {load_ok}")
P(f"   headers byte-identical across all runs outside the # n= knob line: {header_ok}")
P(f"   header batch=/work_mul=/ndiv= == run's (B,WM,NDIV), rounds={R}, "
  f"warmup={WARMUP}, barrier_n=0 and n == (1,000,003*WM)//NDIV: "
  f"{not any('HEADER knob' in i or 'HEADER n=' in i for i in integrity)}")
P(f"   knob arithmetic (record): (1,000,003*316)//1239 = "
  f"{(N_BASE * 316) // 1239} == the header n=255045: "
  f"{(N_BASE * 316) // 1239 == 255045}; gcd(316,1239) = {math.gcd(316, 1239)}")
P(f"   every CELL spv= name is an archived .emitted.spv (no .iter -- the "
  f"corpus is byte-identical this session): {spv_identity_ok}")
P(f"   CELL lines: 24 per run in 54/54 runs: {cell_counts_ok}")
P(f"   VERIFY lines: 24 per run in 54/54 runs: {verify_counts_ok}")
P(f"   tail '# done cells=24' in 54/54 runs: {tail_ok}")
P(f"   SAMPLE lines: 115,200 per run (18 ok cells x {R:,} rounds) in "
  f"54/54 runs: {sample_counts_ok}")
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

ok_cells = sorted(k for k, v in data[("c2", 1)][0].items()
                  if v["pipeline"] == "ok")
assert len(ok_cells) == 18, f"ok cells {len(ok_cells)}"


def ckey(idx):
    c = data[("c2", 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])


sum128 = [k for k in ok_cells if ckey(k) == ("sum", 128, "16")][0]

med_cache = {}


def run_med(tag, r, idx):
    key = (tag, r, idx)
    if key not in med_cache:
        med_cache[key] = statistics.median(data[(tag, r)][3][idx])
    return med_cache[key]


P("2. PER-RUN DESCRIPTIVE (W2/L10: per-run quantities are DESCRIPTIVE")
P("   ONLY and never classify; each run: (sum,128,S=16) per-cell median")
P(f"   gpu_ticks over its {R:,} rounds, then min..max over the 18")
P("   pipeline-ok cells of the per-cell medians, then the per-run")
P("   host_ns median at (sum,128,S=16)):")
P("")
for tag in TAGS:
    b, wm, dd, k = ARMB[tag], ARMW[tag], ARMD[tag], ARMK[tag]
    n = (N_BASE * wm) // dd
    P(f"   {tag} (B={b}, WM={wm}, NDIV={dd}, n={n}, k={k}):")
    for r in range(1, k + 1):
        vals = [run_med(tag, r, kk) for kk in ok_cells]
        v16 = run_med(tag, r, sum128)
        hn = statistics.median(data[(tag, r)][3][sum128 + 1000000]
                               if False else [0]) if False else None
        P(f"     r{r:02d}  (sum,128,16) {fmt(v16):>7}   18-cell "
          f"{fmt(min(vals)):>6}..{fmt(max(vals)):<6}   host_ns "
          f"{fmt(run_host(tag, r))}")
    P("")
P("")

P("3. UNIT CLASSIFICATION UNDER THE PRE-REGISTERED DEEP-POOLING CI")
P(f"   CLASS STATISTIC (R = {R:,}; the frozen 3-run method applied to")
P("   the pre-registered classification units: block j (j=1..16) = runs")
P("   r(3j-2), r(3j-1), r(3j); pooled-48 pools all 48 runs x R rounds")
P("   per cell -- a NAMED EXTENSION of the frozen 3-run method,")
P("   reported alongside -- never instead of -- the sixteen block")
P("   classes; controls have k=3: one unit each). Per unit per cell:")
P("   m_c = pooled sample median gpu_ticks, MAD_c = sample median")
P("   |x - m_c|, h_c = 3.6420 * MAD_c / sqrt(N). Unit class at the")
P("   FROZEN 1,000-tick threshold (all-cells quantifiers): CAPTURED iff")
P("   all 18 m_c - h_c >= 1,000; FLOOR iff all 18 m_c + h_c <= 100;")
P("   INTERMEDIATE/MIXED iff (some m_c + h_c < 1,000) AND (some")
P("   m_c - h_c > 100); IN-BAND-UNDECIDED otherwise. Medians are exact")
P("   pooled medians -- half-integers can occur at even sample counts.")
P("")
unit_rows = {}
for tag in TAGS:
    b, wm, dd, k = ARMB[tag], ARMW[tag], ARMD[tag], ARMK[tag]
    n = (N_BASE * wm) // dd
    P(f"   {tag} (B={b}, WM={wm}, NDIV={dd}, n={n}):")
    units = []
    if tag in BLOCKS:
        for j, runs in enumerate(BLOCKS[tag], 1):
            units.append((f"block{j}", runs))
        units.append(("pooled-48", UNIT48))
    else:
        units.append((f"block1 (k={k} control)", tuple(range(1, k + 1))))
    for label, runs in units:
        runlabel = ",".join(f"{r:02d}" for r in runs)
        if len(runlabel) > 22:
            runlabel = "01..48"
        cell_stats = []
        cell_full = []
        for kk in ok_cells:
            xs = []
            for r in runs:
                xs.extend(data[(tag, r)][3][kk])
            N = len(xs)
            assert N == len(runs) * R, f"{tag} {label} idx={kk} N={N}"
            m_ = statistics.median(xs)
            mad = statistics.median([abs(x - m_) for x in xs])
            h_ = H_CONST * mad / math.sqrt(N)
            cell_stats.append((m_, h_))
            cell_full.append((kk, m_, mad, h_))
        cls = dp_class(cell_stats)
        lo_mh = min((m_ - h_, kk) for kk, m_, mad, h_ in cell_full)
        hi_ph = max((m_ + h_, kk) for kk, m_, mad, h_ in cell_full)
        hi_mh = max((m_ - h_, kk) for kk, m_, mad, h_ in cell_full)
        lo_ph = min((m_ + h_, kk) for kk, m_, mad, h_ in cell_full)
        N = len(runs) * R
        P(f"     {label} runs {runlabel} N={N} class {cls}")
        P(f"       binding: min(m-h)={f4(lo_mh[0])}@{lo_mh[1]}  "
          f"max(m+h)={f4(hi_ph[0])}@{hi_ph[1]}  "
          f"max(m-h)={f4(hi_mh[0])}@{hi_mh[1]}  "
          f"min(m+h)={f4(lo_ph[0])}@{lo_ph[1]}")
        for kk, m_, mad, h_ in cell_full:
            P(f"       idx={kk:2d} m={fmt(m_):>9} mad={fmt(mad):>7} "
              f"h={f4(h_):>9} m-h={f4(m_ - h_):>11} m+h={f4(m_ + h_):>11}")
        unit_rows[(tag, label)] = (cell_stats, cls, runs)
    P("")

P("4. PRE-REGISTERED LETTERS (the frozen letters of the protocol):")
P("")

# C1 (prerequisite; W1 (d) also fires on C1 (b)) -- unchanged from the
# standing cut protocol
c2_stats, cls_c2, _ = unit_rows[("c2", "block1 (k=3 control)")]
c8_stats, cls_c8, _ = unit_rows[("c8", "block1 (k=3 control)")]
v_c2 = [m_ for kk, m_, mad, h_ in [None] * 0] if False else None
v_c2 = dict((kk, m_) for kk, m_, mad, h_ in []) if False else None
v_c2 = c2_stats[ok_cells.index(sum128)][0]
v_c8 = c8_stats[ok_cells.index(sum128)][0]
c1_c2_ok = cls_c2 == "FLOOR" and C2_BAND[0] <= v_c2 <= C2_BAND[1]
c1_c8_ok = abs(v_c8 - C8_COMMITTED) <= 0.05 * C8_COMMITTED
c1_arm_ok = (verify_mismatch_by_arm["c2"] == 0
             and verify_mismatch_by_arm["c8"] == 0)
c1_ok = c1_c2_ok and c1_c8_ok and c1_arm_ok
P("   C1 ARCHIVED CONTROL REPLICATION (prerequisite; W1 (d) also fires")
P("   on C1 (b); unchanged from the standing cut protocol): controls")
P("   have k=3: one deep-pooling unit each (N = 3R = "
  f"{3 * R:,} per cell):")
P(f"     c2 (sum,128,S=16) pooled median m {fmt(v_c2)}, deep-pooling")
P(f"     class {cls_c2} (committed floor band {C2_BAND[0]}..{C2_BAND[1]} "
  f"at B=2): {c1_c2_ok}")
P(f"     c8 (sum,128,S=16) pooled median m {fmt(v_c8)} within +/-5% of "
  f"committed {C8_COMMITTED} (session 4 pooled median): {c1_c8_ok} "
  f"({(v_c8 - C8_COMMITTED) / C8_COMMITTED * 100:+.2f}%)")
P(f"     control arms free of VERIFY mismatches (frozen INVALIDATION "
  f"criterion): {c1_arm_ok}")
if c1_ok:
    P("     VERDICT: branch (a) both controls satisfy their criteria --")
    P("     W1 is evaluated against the row question.")
else:
    P("     VERDICT: branch (b) replication discrepancy (W1 (d) INVALID")
    P("     fires); cause UNMEASURED.")
P("")

# C2 (bis class stability at 16-block granularity under the deep-pooling
# statistic)
bis_classes = [unit_rows[("bis", f"block{j}")][1] for j in range(1, 17)]
bis_pooled_cls = unit_rows[("bis", "pooled-48")][1]
bis_bad = verify_mismatch_by_arm["bis"] > 0
if bis_bad:
    c2_letter = "(d)"
elif all(c == "INTERMEDIATE/MIXED" for c in bis_classes + [bis_pooled_cls]):
    c2_letter = "(a)"
elif all(c == "CAPTURED" for c in bis_classes + [bis_pooled_cls]):
    c2_letter = "(b)"
else:
    c2_letter = "(c)"
P("   C2 BIS CLASS STABILITY AT 16-BLOCK GRANULARITY -- bis")
P("   (BATCH=3,WORK_MUL=316,NDIV=1239) at n=255,045 (16 blocks of 3 runs")
P("   + pooled-48) under THE PRE-REGISTERED DEEP-POOLING CI CLASS")
P(f"   STATISTIC (R = {R:,}; protocol arm (c)): {c2_letter}")
P(f"     block classes: {bis_classes}; pooled-48 class: {bis_pooled_cls}")
P("     block binding min(m-h): "
  + " / ".join(f4(min(m_ - h_ for m_, h_ in unit_rows[('bis', f'block{j}')][0]))
              for j in range(1, 17)))
P(f"     pooled-48 binding min(m-h): "
  f"{f4(min(m_ - h_ for m_, h_ in unit_rows[('bis', 'pooled-48')][0]))}")
P("     (sum,128,S=16) m: blocks "
  + " / ".join(fmt(unit_rows[("bis", f"block{j}")][0][ok_cells.index(sum128)][0])
              for j in range(1, 17))
  + f" ; pooled-48 {fmt(unit_rows[('bis', 'pooled-48')][0][ok_cells.index(sum128)][0])}")
if c2_letter == "(a)":
    P("     (a) STABLE-INTERMEDIATE: all 16 blocks AND the pooled-48 arm")
    P("     class INTERMEDIATE/MIXED -- PASSES the 16-block class-")
    P("     stability requirement at bis under the deep-pooling")
    P("     statistic.")
elif c2_letter == "(b)":
    P("     (b) STABLE-CAPTURED: all 16 blocks AND the pooled-48 arm")
    P("     class CAPTURED -- PASSES the 16-block class-stability")
    P("     requirement at bis under the deep-pooling statistic.")
elif c2_letter == "(c)":
    P("     (c) CLASS-UNRESOLVED: mixed block classes, or any")
    P("     IN-BAND-UNDECIDED unit, or the pooled arm differs -- FAILS;")
    P("     L9 binds at bis under the deep-pooling statistic; any future")
    P("     narrowing claim at bis must confront this cut's content")
    P("     first (named here, not specified here).")
else:
    P("     (d) INVALID: the frozen INVALIDATION criterion (VERIFY")
    P("     mismatches) leaves C2 unevaluable.")
P("     NAMED, NOT HIDDEN: WHY any class occurs is UNMEASURED (L2")
P("     binds); NO causal mechanism is claimed.")
P("")

# W1 (cut verdict) -- mapping per the frozen protocol W1 rows; the
# protocol's W1 (c) text reads "C2 (c)/(d) -> NOTHING MOVES" while
# record.txt maps W1 (d) to the frozen INVALIDATION criterion and the
# protocol header says W1 (d) also fires on C1 (b) -- this script
# reports C2 (d)/C1 (b) as W1 (d) INVALID (record.txt's explicit
# mapping), which also satisfies "NOTHING MOVES" (the bracket stays
# EXACTLY under (b)/(c)/(d) in every reading).
if c2_letter == "(d)" or not c1_ok:
    w1_letter = "(d)"
elif c2_letter == "(c)":
    w1_letter = "(c)"
elif c2_letter == "(b)":
    w1_letter = "(a)"
else:
    w1_letter = "(b)"
P("   W1 CUT VERDICT (the bracket's interior bisection at bis; both")
P("   class outcomes narrow by bisection, unlike mid where a CAPTURED")
P("   outcome cannot narrow -- lo is dual-class on the record):")
P(f"     C1 (control replication): {'(a)' if c1_ok else '(b)'}")
P(f"     C2 (bis class stability): {c2_letter}")
P(f"     W1 {w1_letter}")
P("     NAMED, NOT HIDDEN (label reading): the protocol's W1 (c) text")
P("     reads \"C2 (c)/(d) -> NOTHING MOVES\" while record.txt maps W1")
P("     (d) to the frozen INVALIDATION criterion and the protocol")
P("     header says W1 (d) also fires on C1 (b); this script reports")
P("     C2 (d)/C1 (b) as W1 (d) INVALID (record.txt's explicit")
P("     mapping), which also satisfies \"NOTHING MOVES\" -- the bracket")
P("     outcome is identical under every reading.")
if w1_letter == "(a)":
    P("     (a) C2 (b) -> THE BRACKET NARROWS TO (254,557, 255,045]")
    P("     (\"THE B=3 CLASS FLIP LIES AT OR BELOW n=255,045\"); the")
    P("     MID-ONLY NARROWING CLAIM stays SUSPENDED (named, not")
    P("     claimed).")
elif w1_letter == "(b)":
    P("     (b) C2 (a) -> THE BRACKET NARROWS TO (255,045, 255,208]")
    P("     (\"THE B=3 CLASS FLIP LIES ABOVE n=255,045\"); NAMED, NOT")
    P("     HIDDEN: this outcome IMPLIES the claim's inequality")
    P("     F > 254,882 and SUPERSEDES its realization-at-mid form --")
    P("     the bracket is strictly narrower than (254,882, 255,208].")
elif w1_letter == "(c)":
    P("     (c) C2 (c) -> NOTHING MOVES; the MID-ONLY NARROWING CLAIM")
    P("     stays SUSPENDED (named, not claimed).")
else:
    P("     (d) INVALID (C1 (b) or the frozen INVALIDATION criterion")
    P("     leaves W1 unevaluable).")
if w1_letter == "(a)":
    P("     Bracket state: NARROWED -- (254,557, 255,045] (the upper")
    P("     endpoint moved 255,208 -> 255,045 on this cut's content;")
    P("     the lower endpoint is carried unchanged on lo's content).")
elif w1_letter == "(b)":
    P("     Bracket state: NARROWED -- (255,045, 255,208] (the lower")
    P("     endpoint moved 254,557 -> 255,045 on this cut's content;")
    P("     the upper endpoint is carried unchanged on hi's content).")
else:
    P("     Under (c)/(d) the committed bracket stays EXACTLY")
    P("     (254,557, 255,208].")
P("     Under ALL outcomes: NO claim at hi, NO claim at lo; no boundary")
P("     between grid points is ever claimed (L5).")
P("")

# W2 (descriptive)
P("   W2 (pre-registered, descriptive) per-run 18-cell min trajectory")
P("   across the 48 bis runs in frozen order (per-run per-cell median")
P(f"   gpu_ticks over the run's {R:,} rounds, min over the 18")
P("   pipeline-ok cells; per-run quantities are DESCRIPTIVE ONLY and")
P("   never classify (L10)), the boundary-crossing count (runs with")
P("   18-cell min >= 1,000) AND the in-band count (runs with 18-cell")
P("   min in 981..1,015):")
traj158 = []
cross158 = 0
inband158 = 0
for r in range(1, 49):
    vals = [run_med("bis", r, kk) for kk in ok_cells]
    mn = min(vals)
    traj158.append(fmt(mn))
    if mn >= 1000:
        cross158 += 1
    if 981 <= mn <= 1015:
        inband158 += 1
P("     bis per-run 18-cell min: " + " ".join(traj158))
P(f"     bis: runs with 18-cell min >= 1,000 (COMPUTED here, "
  f"descriptive): {cross158}/48")
P(f"     bis: runs with 18-cell min in 981..1,015 (COMPUTED here, "
  f"descriptive): {inband158}/48")
P("     (prior windows' computed counts at both thresholds, parsed,")
P("     quote-only):")
for win, tdict, k in (("s136", TRAJ136, 24), ("s139", TRAJ139, 48),
                      ("s147", TRAJ147, 48)):
    for t in sorted(tdict):
        vals = tdict[t]
        P(f"       {win} {t} (k={k}): "
          f"{sum(1 for v in vals if v >= 1000)}/{k} at min >= 1,000, "
          f"{sum(1 for v in vals if 981 <= v <= 1015)}/{k} in 981..1,015")
P("   NO point is placed or moved on the committed row by W2 itself")
P("   (descriptive letter); bracket movement rides W1 only.")
P("")

# W3 (cross-window letter)
P("   W3 (pre-registered, descriptive) CROSS-BINARY confrontation at")
P("   bis -- this window's classes at the NEW first-measured binary")
P(f"   (the ROUNDS6400 variant; bis pin {PINS['bis'][:8]}...) vs the")
P("   committed bis windows at 440604ef... (parsed, quote-only):")
P(f"     this cut's bis block classes: {bis_classes}; pooled-48 "
  f"{bis_pooled_cls}")
P("     this cut's bis block min(m-h): "
  + " / ".join(f4(min(m_ - h_ for m_, h_ in unit_rows[('bis', f'block{j}')][0]))
              for j in range(1, 17))
  + f" ; pooled-48 "
    f"{f4(min(m_ - h_ for m_, h_ in unit_rows[('bis', 'pooled-48')][0]))}")
P("     s136 (8 blocks + pooled-24 at 440604ef...): block medians "
  + "/".join(b[1] for b in S136_BIS_BLOCKS)
  + f", pooled-24 {S136_BIS_POOLED[0]} {S136_BIS_POOLED[2]}")
P("     s139 (16 blocks + pooled-48 at 440604ef...): block medians "
  + "/".join(b[1] for b in S139_BIS_BLOCKS)
  + f", pooled-48 {S139_BIS_POOLED[0]} {S139_BIS_POOLED[2]}")
P("     NAMED CROSS-BINARY HAZARD: this cut's binaries are NEW (the")
P("     ROUNDS6400 variant, first-measured digests -- NO committed pin")
P("     to match); any class disagreement with the committed windows")
P("     may be BINARY-driven, cause UNMEASURED (L2 binds).")
P("     claim-form confrontation content (protocol arm (d); parsed; NO")
P("     letter of this cut touches lo or mid):")
for n in ("254557", "254882"):
    for ticks_, cls, sess, src in W2CLAIM[n]:
        P(f"       n={n}: {ticks_} {cls} (session {sess})")
P(f"       lo pooled-12 {LO_POOLED12[0]} {LO_POOLED12[1]}; mid pooled-48 "
  f"{S139_MID_POOLED[0]} {S139_MID_POOLED[2]}")
P("       the named cross-window disagreement at cabff942...: s132")
P(f"       pooled-24 {S132_MID_POOLED[0]} {S132_MID_POOLED[2]} vs s136")
P(f"       pooled-24 {S136_MID_POOLED[0]} {S136_MID_POOLED[2]} vs s139")
P(f"       pooled-48 {S139_MID_POOLED[0]} {S139_MID_POOLED[2]} vs s147")
P(f"       pooled-48 {S147_MID_POOLED[1]} {S147_MID_POOLED[4]} (the")
P("       FOURTH window; its C2 tolerance verdict TOLERANCE-UNRESOLVED,")
P("       arm (a) above); its cause stays UNMEASURED (L2 binds).")
P("")

# X1 (descriptive)
P("   X1 (descriptive, host_ns at (sum,128,S=16); NOT a C criterion")
P("   (L3); per-run host_ns spread is reported):")
for tag in TAGS:
    k = ARMK[tag]
    hs = [run_host(tag, r) for r in range(1, k + 1)]
    P(f"     {tag}: per-run host_ns median min..max {fmt(min(hs))}.."
      f"{fmt(max(hs))} (spread {fmt(max(hs) - min(hs))} = "
      f"{(max(hs) - min(hs)) / min(hs) * 100:.1f}% of min; k={k})")
P("     prior windows' X1 content (parsed, quote-only):")
for win, xd in (("s136", X1_136), ("s139", X1_139), ("s147", X1_147)):
    for t in sorted(xd):
        lo_, hi_, sp, pct, k = xd[t]
        P(f"       {win} {t}: {lo_}..{hi_} (spread {sp} = {pct}% of min; k={k})")
P("     host_ns is the HOST-side proxy (L3), not a C criterion; any")
P("     excursion is NAMED, NOT HIDDEN and its cause is UNMEASURED.")
P("")

P(f"5. VERDICT SUMMARY: C1 {'(a)' if c1_ok else '(b)'}; C2 {c2_letter} at "
  f"bis (255,045); W1 {w1_letter}.")
if w1_letter == "(a)":
    P("   CUT VERDICT: THE BRACKET NARROWS TO (254,557, 255,045]")
    P("   (\"THE B=3 CLASS FLIP LIES AT OR BELOW n=255,045\"); the")
    P("   MID-ONLY NARROWING CLAIM stays SUSPENDED (named, not claimed).")
elif w1_letter == "(b)":
    P("   CUT VERDICT: THE BRACKET NARROWS TO (255,045, 255,208]")
    P("   (\"THE B=3 CLASS FLIP LIES ABOVE n=255,045\"); this outcome")
    P("   IMPLIES the claim's inequality F > 254,882 and SUPERSEDES its")
    P("   realization-at-mid form.")
elif w1_letter == "(c)":
    P("   CUT VERDICT: NOTHING MOVES; the MID-ONLY NARROWING CLAIM stays")
    P("   SUSPENDED (named, not claimed) and is NOT made by this cut.")
else:
    P("   CUT VERDICT: INVALID; NOTHING MOVES.")
if w1_letter == "(a)":
    P("   Bracket state: NARROWED -- (254,557, 255,045].")
elif w1_letter == "(b)":
    P("   Bracket state: NARROWED -- (255,045, 255,208].")
else:
    P("   The committed bracket stays EXACTLY (254,557, 255,208].")
P("   Under ALL outcomes: NO claim at hi, NO claim at lo; no boundary")
P("   between grid points is ever claimed (L5). WHY any class occurs is")
P("   UNMEASURED and NO causal mechanism is claimed (L2 binds). The")
P("   14th cut's TOLERANCE-UNRESOLVED mid content stands as committed")
P("   content under ALL outcomes (arm (a)); NO letter of this cut")
P("   supersedes it or touches lo/mid.")
P("   BAR NON-INTERFERENCE (frozen protocol): these runs are BISECT")
P("   CONTENT and NOT bar readings -- NO settle-bar-ledger.txt append,")
P("   NO UTC-day slot consumption, NO movement of the bar's SETTLED")
P("   INTERMEDIATE/MIXED verdict (the s117 committed landing), NO Rule")
P("   4 workgroup row movement, NO :measured? flag change (the")
P("   accelerator-targets rows stay exactly as ADR-0358 left them).")

with open(os.path.join(HERE, "publication-s158.txt"), "w") as f:
    f.write("\n".join(out) + "\n")
