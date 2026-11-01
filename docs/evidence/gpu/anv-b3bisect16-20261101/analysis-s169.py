#!/usr/bin/env python3
"""JUN-59 session 169 analysis -- THE B=3 PER-DISPATCH-WORK THRESHOLD
BISECT, SIXTEENTH CUT -- THE CLEAN-BISECTION CUT AT THE FLOOR MIDPOINT
(345,1354) n=254,801 (the interior floor midpoint of the committed
bracket (254,557, 255,045]; mid (248,973) n=254,882 is NOT re-measured
-- the per-point rule: no mid letter from this cut). ONE NEW KNOB
TRIPLE (fm (3,345,1,354) -- new-to-history, L8 APPLIES).
ANALYSIS half over the 54 committed run logs of the s169/s170/s171
measurement half (this directory -- the committed gzip -n form
run-<tag>-r<NN>.txt.gz; this script READS THROUGH GZIP, the s157
capture-form deviation executed at s171), under the frozen
anv-b3bisect16prereg-20261101/protocol.txt (freeze stamp
2026-11-01T08:05:17Z BEFORE any run log of this cut existed).

Route (the s160 NOT DONE (c) input rule, carried): this script parses
ONLY the 54 committed run logs in its own directory (read through
gzip) and the NAMED COMMITTED WANT SOURCES (the s27 controls census;
the publication-s147.txt arm-(a) FIRST content; the
publication-s139.txt W2 row table + pooled-window quotes (arm (d));
the publication-s158.txt 15th-cut landed outcome + bis content at
52fb68b6...; the knob-search-s164-run1.txt virgin-point quote +
bracket + in-box census; the build-census-s169.txt first-measured
binary pins -- all parsed here from committed bytes, never
transcribed) and writes publication-s169.txt. No other input.
Deterministic: running it twice yields byte-identical
publication-s169.txt (checked by cmp after the recorded run). Every
want source is parsed with fail-closed regexes; a want that does not
parse aborts (assert).

The frozen letters (protocol): C1 (control replication, unchanged
from the standing cut protocol: c2 FLOOR in the committed floor band
31..32; c8 within +/-5% of the committed 32,915; C1 (b) -> W1 (d)) /
C2 (fm class stability at 16-block granularity under THE
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
(a) C2 (b) -> the bracket narrows to (254,557, 254,801] and the
MID-ONLY NARROWING CLAIM is REFUTED BY IMPLICATION; (b) C2 (a) ->
the bracket narrows to (254,801, 255,045]; (c) C2 (c)/(d) -> NOTHING
MOVES, bracket stays EXACTLY (254,557, 255,045]; (d) INVALID -- also
fires on C1 (b)) / W2 (descriptive: per-run 18-cell min trajectory,
crossings at 1,000 AND in-band counts 981..1,015) / W3 (descriptive
cross-binary/cross-point letter -- the point is VIRGIN, so every
comparison is against the bracketing committed content and is
cross-binary AND cross-point; NAMED CROSS-BINARY HAZARD: this cut's
binaries are NEW, first-measured digests) / X1 (host_ns spread,
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

# frozen protocol constants (anv-b3bisect16prereg-20261101/protocol.txt)
R = 6400                 # rounds per cell per run (arm (c)(i))
WARMUP = 3
N_BASE = 1000003
H_CONST = 3.6420         # frozen CI constant (1.96 * 1.2533 * 1.4826)
CAP_MIN = 1000.0         # frozen 1,000-tick threshold
FLOOR_MAX = 100.0
TICK_NS = 52.083         # timestampPeriod (asserted against the logs)

# tag -> (BATCH, WORK_MUL, NDIV, k), frozen protocol ARM TABLE
# (3 rows = 54 fresh processes; self-check 3+48+3 = 54)
ARMS = [("c2", 2, 1, 1, 3), ("fm", 3, 345, 1354, 48), ("c8", 8, 1, 1, 3)]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMW = {a[0]: a[2] for a in ARMS}
ARMD = {a[0]: a[3] for a in ARMS}
ARMK = {a[0]: a[4] for a in ARMS}
BLOCKS = {"fm": [tuple(range(3 * j - 2, 3 * j + 1)) for j in range(1, 17)]}
UNIT48 = tuple(range(1, 49))
FM_N = (N_BASE * 345) // 1354          # 254,801 -- asserted below
BRACKET_LO, BRACKET_HI = 254557, 255045  # parsed two ways below


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
pub139 = open(os.path.join(GPU, "anv-b3bisect13-20261031",
                           "publication-s139.txt")).read()
pub147 = open(os.path.join(GPU, "anv-b3bisect14-20261031",
                           "publication-s147.txt")).read()
pub158 = open(os.path.join(GPU, "anv-b3bisect15-20261101",
                           "publication-s158.txt")).read()
ks164 = open(os.path.join(GPU, "anv-b3bisect16prereg-20261101",
                          "knob-search-s164-run1.txt")).read()
bc169 = open(os.path.join(HERE, "build-census-s169.txt")).read()

# committed controls (s27 census): "committed controls: c2 31 (floor
# band 31..32); c8 32,915 (session 4 pooled median)"
ctl = parse1(s27c, r"(committed controls: c2 \d+ \(floor band [\d.]+\.[\d.]+\); "
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


S139_MID_BLOCKS, S139_MID_POOLED = pub_arm_rows(pub139, "mid", 16, "pooled-48")
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
S147_TOL_ALL_IBU = (all(r[5] == "IN-BAND-UNDECIDED" for r in S147_MID_BLOCKS)
                    and S147_MID_POOLED[5] == "IN-BAND-UNDECIDED")
S147_TOL_VERDICT = parse1(
    pub147, r"\(c\) TOLERANCE-UNRESOLVED: any in-band minimum or mixed classes "
            r"-- FAILS; L9 binds at mid at 16 blocks under the tolerance rule too\.",
    "pub147 tolerance verdict")

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

# ---- knob-search-s164-run1.txt (the s165 reconnaissance; the
# ---- protocol's arm (a)/(d) re-citation source) ----
m = re.search(r"committed bracket \(publication-s158\.txt, parsed\): "
              r"\((\d+), (\d+)\] n-units", ks164)
assert m is not None, "WANT SOURCE NOT PARSED: ks164 bracket"
KS_BRACKET = (int(m.group(1)), int(m.group(2)))
m = re.search(r"bisect grid n = \((\d+)\+(\d+)\)//2 = (\d+)", ks164)
assert m is not None, "WANT SOURCE NOT PARSED: ks164 floor midpoint"
KS_MIDPOINT = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
VIRGIN_QUOTE = None
for l in ks164.splitlines():
    if l.strip().startswith("committed content at n=254801:"):
        VIRGIN_QUOTE = l.strip()
        break
assert VIRGIN_QUOTE is not None and VIRGIN_QUOTE.startswith(
    "committed content at n=254801: NONE"), "WANT SOURCE NOT PARSED: virgin quote"
ks_floor = ks164.split("FLOOR MIDPOINT CANDIDATE n=254801:")[1].split(
    "MID CANDIDATE n=254882:")[0]
m = re.search(r"pairs mapping to 254801 in-box: (\d+); smallest: \((\d+), (\d+)\)",
              ks_floor)
assert m is not None, "WANT SOURCE NOT PARSED: ks164 in-box census"
KS_INBOX = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
m = re.search(r"in-box pairs whose same-ratio double is also in-box: (\d+)",
              ks_floor)
assert m is not None, "WANT SOURCE NOT PARSED: ks164 doubles"
KS_DOUBLES = int(m.group(1))
assert "gcd(254801, 1,000,003) = 1" in ks_floor, "WANT SOURCE NOT PARSED: ks164 gcd"
KS_DUAL_MID = None
KS_DUAL_LO = None
KS_TOL_VERDICT = None
for l in ks164.splitlines():
    s = l.strip()
    if s.startswith("dual-class at mid on the committed record:"):
        KS_DUAL_MID = s
    elif s.startswith("dual-class at lo on the committed record:"):
        KS_DUAL_LO = s
    elif s.startswith("verdict line (parsed): (c) TOLERANCE-UNRESOLVED"):
        KS_TOL_VERDICT = s[len("verdict line (parsed): "):]
assert KS_DUAL_MID is not None, "WANT SOURCE NOT PARSED: ks164 dual mid"
assert KS_DUAL_LO is not None, "WANT SOURCE NOT PARSED: ks164 dual lo"
assert KS_TOL_VERDICT is not None, "WANT SOURCE NOT PARSED: ks164 tol verdict"

# ---- publication-s158.txt (the 15th cut's landed outcome; the
# ---- protocol's W3 named content at bis 52fb68b6...) ----
m = re.search(r"VERDICT SUMMARY: C1 \((\w)\); C2 \((\w)\) at bis \(255,045\); "
              r"W1 \((\w)\)\.", flat(pub158))
assert m is not None, "WANT SOURCE NOT PARSED: pub158 verdict summary"
S158_C1, S158_C2, S158_W1 = m.group(1), m.group(2), m.group(3)
m = re.search(r"Bracket state: NARROWED -- \((\d+), (\d+)\]", flat(pub158))
assert m is not None, "WANT SOURCE NOT PARSED: pub158 bracket state"
S158_BRACKET = (int(m.group(1)), int(m.group(2)))
assert S158_BRACKET == KS_BRACKET, (
    f"bracket parse disagreement pub158 {S158_BRACKET} vs ks164 {KS_BRACKET}")
assert KS_MIDPOINT == (BRACKET_LO, BRACKET_HI, FM_N), (
    f"floor midpoint derivation {KS_MIDPOINT}")
m = re.search(r"block classes: \[([^\]]*)\]; pooled-48 class: (\S+)", pub158)
assert m is not None, "WANT SOURCE NOT PARSED: pub158 block classes"
S158_BIS_CLASSES = re.findall(r"'(\S+?)'", m.group(1))
assert len(S158_BIS_CLASSES) == 16, f"pub158 classes {len(S158_BIS_CLASSES)}"
S158_BIS_POOLED_CLS = m.group(2)
S158_BIS_BIND = [float(x) for x in
                 parse1(pub158, r"block binding min\(m-h\): ([\d. /]+)",
                        "pub158 block bindings").split("/")]
assert len(S158_BIS_BIND) == 16, f"pub158 bindings {len(S158_BIS_BIND)}"
S158_BIS_POOLED_BIND = float(parse1(
    pub158, r"pooled-48 binding min\(m-h\): ([\d.]+)", "pub158 pooled binding"))
PINS158 = {}
for mm in re.finditer(r"anv-bb-(c2|bis|c8) ([0-9a-f]{64})", pub158):
    assert mm.group(1) not in PINS158, f"pub158 duplicate pin {mm.group(1)}"
    PINS158[mm.group(1)] = mm.group(2)
assert set(PINS158) == {"c2", "bis", "c8"}, f"pub158 pins {sorted(PINS158)}"


def traj(pub, tag, want):
    m = re.search(rf"{tag} per-run 18-cell min: ([\d. ]+)", flat(pub))
    assert m is not None, f"WANT SOURCE NOT PARSED: {tag} trajectory"
    vals = [float(x) for x in m.group(1).split()]
    assert len(vals) == want, f"{tag} trajectory length {len(vals)} != {want}"
    return vals


def x1_rows(pub, tags):
    idx = pub.rfind("X1 (descriptive")
    assert idx != -1, "WANT SOURCE NOT PARSED: X1 section"
    tail = pub[idx:]
    out = {}
    for t in tags:
        m = re.search(rf"{t}: per-run host_ns median min\.\.max "
                      rf"(\d+(?:\.\d+)?)\.\.(\d+(?:\.\d+)?) "
                      rf"\(spread (\d+(?:\.\d+)?) = ([\d.]+)% of min; k=(\d+)\)",
                      tail)
        assert m is not None, f"WANT SOURCE NOT PARSED: X1 {t}"
        out[t] = (m.group(1), m.group(2), m.group(3), m.group(4),
                  int(m.group(5)))
    return out


TRAJ147 = {"mid": traj(pub147, "mid", 48)}
TRAJ158 = {"bis": traj(pub158, "bis", 48)}
X1_147 = x1_rows(pub147, ("c2", "mid", "c8"))
X1_158 = x1_rows(pub158, ("c2", "bis", "c8"))

# this cut's first-measured binary pins (committed build-census-s169.txt)
PINS = {}
for mm in re.finditer(r"([0-9a-f]{64})  anv-bb-(c2|fm|c8)\n", bc169):
    assert mm.group(2) not in PINS, f"duplicate pin line {mm.group(2)}"
    PINS[mm.group(2)] = mm.group(1)
assert set(PINS) == {"c2", "fm", "c8"}, f"pin set {sorted(PINS)}"

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
            float(f[8][16:])
            assert (int(f[3][6:]) == b and int(f[4][9:]) == wm
                    and int(f[5][5:]) == dd), line
            ticks.setdefault(idx, []).append(gt)
            hosts.setdefault(idx, []).append(hn)
            counts[idx] = counts.get(idx, 0) + 1
    return cells, verifies, header, ticks, hosts, counts


def load_run(path, b, wm, dd):
    cells, verifies, header, ticks, hosts, counts = load(path, b, wm, dd)
    s128 = [k for k, v in cells.items()
            if (v["op"], v["wg"], v["forced"]) == ("sum", 128, "16")]
    assert len(s128) == 1, f"sum128 cells {s128}"
    host128 = hosts.pop(s128[0])  # keep only the (sum,128,S=16) host list
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
    return cells, verifies, header, ticks, ok_cells, ok, integrity, host128

out = []
P = out.append
P("JUN-59 session 169 analysis -- THE B=3 PER-DISPATCH-WORK THRESHOLD")
P("BISECT, SIXTEENTH CUT -- THE CLEAN-BISECTION CUT AT THE FLOOR")
P("MIDPOINT (345,1354) n=254,801 (the interior floor midpoint of the")
P("committed bracket (254,557, 255,045]; mid (248,973) n=254,882 is")
P("NOT re-measured -- the per-point rule: no mid letter from this")
P("cut). ONE NEW KNOB TRIPLE (fm (3,345,1,354) -- new-to-history, L8")
P("APPLIES).")
P("publication -- the ANALYSIS half over the 54 committed run logs of")
P("the s169/s170/s171 measurement half (this directory -- the")
P("committed gzip -n form run-<tag>-r<NN>.txt.gz; this script READS")
P("THROUGH GZIP, the s157 capture-form deviation executed at s171),")
P("under the frozen anv-b3bisect16prereg-20261101/protocol.txt (freeze")
P("stamp 2026-11-01T08:05:17Z BEFORE any run log of this cut")
P("existed).")
P("Produced ONLY by analysis-s169.py over the 54 committed run logs in")
P("this directory and the NAMED COMMITTED WANT SOURCES parsed below")
P("(the s27 controls census; the publication-s147.txt arm-(a) FIRST")
P("content; the publication-s139.txt W2 row table + pooled-window")
P("quotes (arm (d)); the publication-s158.txt 15th-cut landed outcome")
P("+ bis content at 52fb68b6...; the knob-search-s164-run1.txt")
P("virgin-point quote + bracket + in-box census; the")
P("build-census-s169.txt first-measured binary pins; all parsed from")
P("committed bytes, never transcribed). Arms = binary compile-time")
P("(BATCH, WORK_MUL, NDIV);")
P(f"n = (1,000,003*WORK_MUL)/NDIV (integer floor). The row question")
P("(protocol): AT FIXED B=3, IS THE CLASS AT THE FLOOR MIDPOINT")
P("n=254,801 (KNOB PAIR (345, 1,354)) SINGLE-CLASS STABLE AT 16-BLOCK")
P("GRANULARITY (16 blocks of 3 runs + pooled-48) UNDER THE")
P("PRE-REGISTERED DEEP-POOLING CI CLASS STATISTIC (R = 6,400), AT ITS")
P(f"NEW FIRST-MEASURED BINARY (THE ROUNDS6400 INSTRUMENT VARIANT; this")
P(f"window's build pins parsed below: c2 {PINS['c2'][:8]}... fm "
  f"{PINS['fm'][:8]}... c8 {PINS['c8'][:8]}...)?")
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
P(f"       class parse as IN-BAND-UNDECIDED ({S147_TOL_ALL_IBU})")
P(f"       tolerance verdict (parsed): {S147_TOL_VERDICT}")
P(f"     W1 ({S147_W1}) NOTHING MOVES; the MID-ONLY NARROWING CLAIM")
P("     stays SUSPENDED (named, not claimed); the committed bracket")
P("     stayed EXACTLY (254,557, 255,208] on that cut.")
P("     FROZEN STATEMENT (protocol, carried here verbatim): NO letter")
P("     of this cut supersedes any of that content -- this cut does not")
P("     measure mid; the 14th cut's tolerance-rule verdict at mid")
P("     stands as committed content under ALL outcomes of this cut.")
P("   this cut's point's committed content at (345,1354) n=254,801,")
P("   quoted from committed knob-search-s164-run1.txt bytes:")
P(f"     {VIRGIN_QUOTE}")
P("     STATED, NOT SILENT: the point is VIRGIN -- this cut's own")
P("     48-run content, if it runs, is the FIRST content at the point")
P("     (vacuous-at-point; arm (a) 'supersedes which committed")
P("     reading' is answered: NONE AT THE POINT (stated), and at")
P("     mid/lo NONE (the statement above)).")
P("   ARM (d) CLAIM-FORM CONFRONTATION CONTENT (protocol arm (d)):")
P("     the W2 row-table dual-class content (parsed from committed")
P("     publication-s139.txt W2 table bytes; fail-closed counts 2 rows")
P("     at 254,557 and 3 rows at 254,882):")
for n in ("254557", "254882"):
    for ticks_, cls, sess, src in W2CLAIM[n]:
        P(f"       n={n}: {ticks_} {cls} (session {sess})")
P("     the named pooled-window content at the same points (parsed):")
P(f"       lo pooled-12 {LO_POOLED12[0]} {LO_POOLED12[1]}; mid pooled-48 "
  f"{S139_MID_POOLED[0]} {S139_MID_POOLED[2]} (18-cell "
  f"{S139_MID_POOLED[1]}); s147 pooled-48 {S147_MID_POOLED[1]} "
  f"{S147_MID_POOLED[4]} frozen-rule {S147_MID_POOLED[4]} tolerance "
  f"{S147_MID_POOLED[5]}")
P("     the named cross-window disagreement at cabff942... (mid, named")
P("     content -- NO letter of this cut touches lo or mid), the")
P("     knob-search-s164-run1.txt re-citations (parsed):")
P(f"       {KS_DUAL_MID}")
P(f"       {KS_DUAL_LO}")
P("     15th cut (sessions 157-163) landed outcome (parsed from")
P("     committed publication-s158.txt bytes -- the bracket this cut")
P("     starts from):")
P(f"       VERDICT SUMMARY: C1 ({S158_C1}); C2 ({S158_C2}) at bis")
P(f"       (255,045); W1 ({S158_W1}).")
P(f"       Bracket state: NARROWED -- ({fmt(S158_BRACKET[0])}, "
  f"{fmt(S158_BRACKET[1])}]; knob-search-s164-run1.txt bracket parse "
  f"({KS_BRACKET[0]}, {KS_BRACKET[1]}] -> MATCH "
  f"{S158_BRACKET == KS_BRACKET})")
P("   this cut's first-measured binary pins (parsed from committed")
P("   build-census-s169.txt bytes; NEW binaries -- NO committed pin to")
P("   match, the s136 precedent; c2/c8 reproduce the s158 digests")
P("   byte-identically on the same source+knob bytes -- a capture")
P("   observation, not a claim; fm is new-to-history):")
for t in ("c2", "fm", "c8"):
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
        cells, verifies, header, ticks, ok_cells_r, ok_r, integ, host128 = load_run(
            os.path.join(HERE, fn), b, wm, dd)
        if not ok_r:
            load_ok = False
            for i in integ:
                integrity.append(f"{fn}: {i}")
        data[(tag, r)] = (cells, verifies, header, ticks, host128)
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

sample_counts_ok = not any("SAMPLE COUNT" in i for i in integrity)
spv_identity_ok = not any("CELL spv SET MISMATCH" in i for i in integrity)

assert dev_line is not None, "device line not parsed"
m = re.search(r"timestampPeriod=([\d.]+)", tp_line)
assert m is not None, "timestampPeriod not parsed"
assert abs(float(m.group(1)) - TICK_NS) < 1e-9, f"timestampPeriod {m.group(1)}"

P("1. INTEGRITY (computed over the 54 logs, READ THROUGH GZIP -- the")
P("   committed form is run-<tag>-r<NN>.txt.gz gzip -n, the s157")
P("   capture-form deviation executed at s171; the raw logs are NOT")
P("   kept, named):")
P(f"   device (parsed from the logs): {dev_line}")
P(f"   {tp_line}")
P("   runs parsed: 54 (c2 x3, fm x48, c8 x3 -- the frozen ARM TABLE's")
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
P(f"   knob arithmetic (record): (1,000,003*345)//1354 = "
  f"{(N_BASE * 345) // 1354} == the header n=254801: "
  f"{(N_BASE * 345) // 1354 == 254801 == FM_N}; gcd(345,1354) = "
  f"{math.gcd(345, 1354)}")
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


def run_host(tag, r):
    """Per-run host_ns median at (sum,128,S=16) -- the X1/L3 descriptive
    helper over the host_ns list load_run kept (one value per round)."""
    return statistics.median(data[(tag, r)][4])


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

# C2 (fm class stability at 16-block granularity under the deep-pooling
# statistic)
fm_classes = [unit_rows[("fm", f"block{j}")][1] for j in range(1, 17)]
fm_pooled_cls = unit_rows[("fm", "pooled-48")][1]
fm_bad = verify_mismatch_by_arm["fm"] > 0
if fm_bad:
    c2_letter = "(d)"
elif all(c == "INTERMEDIATE/MIXED" for c in fm_classes + [fm_pooled_cls]):
    c2_letter = "(a)"
elif all(c == "CAPTURED" for c in fm_classes + [fm_pooled_cls]):
    c2_letter = "(b)"
else:
    c2_letter = "(c)"
P("   C2 FM CLASS STABILITY AT 16-BLOCK GRANULARITY -- fm")
P("   (BATCH=3,WORK_MUL=345,NDIV=1354) at n=254,801 (knob pair (345,")
P("   1,354), the FLOOR MIDPOINT of the bracket (254,557, 255,045]; the")
P("   point is VIRGIN -- this cut's content is the FIRST content at it)")
P("   (16 blocks of 3 runs + pooled-48) under THE PRE-REGISTERED")
P(f"   DEEP-POOLING CI CLASS STATISTIC (R = {R:,}; protocol arm (c)): "
  f"{c2_letter}")
P(f"     block classes: {fm_classes}; pooled-48 class: {fm_pooled_cls}")
P("     block binding min(m-h): "
  + " / ".join(f4(min(m_ - h_ for m_, h_ in unit_rows[('fm', f'block{j}')][0]))
              for j in range(1, 17)))
P(f"     pooled-48 binding min(m-h): "
  f"{f4(min(m_ - h_ for m_, h_ in unit_rows[('fm', 'pooled-48')][0]))}")
P("     (sum,128,S=16) m: blocks "
  + " / ".join(fmt(unit_rows[("fm", f"block{j}")][0][ok_cells.index(sum128)][0])
              for j in range(1, 17))
  + f" ; pooled-48 {fmt(unit_rows[('fm', 'pooled-48')][0][ok_cells.index(sum128)][0])}")
if c2_letter == "(a)":
    P("     (a) STABLE-INTERMEDIATE: all 16 blocks AND the pooled-48 arm")
    P("     class INTERMEDIATE/MIXED -- PASSES the 16-block class-")
    P("     stability requirement at fm under the deep-pooling")
    P("     statistic.")
elif c2_letter == "(b)":
    P("     (b) STABLE-CAPTURED: all 16 blocks AND the pooled-48 arm")
    P("     class CAPTURED -- PASSES the 16-block class-stability")
    P("     requirement at fm under the deep-pooling statistic.")
elif c2_letter == "(c)":
    P("     (c) CLASS-UNRESOLVED: mixed block classes, or any")
    P("     IN-BAND-UNDECIDED unit, or the pooled arm differs -- FAILS;")
    P("     L9 binds at 254,801 under the deep-pooling statistic; any")
    P("     future narrowing claim at n=254,801 must confront this")
    P("     cut's content first (named here, not specified here).")
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
# EXACTLY under (b)/(c)/(d)... (c)/(d) in every reading).
if c2_letter == "(d)" or not c1_ok:
    w1_letter = "(d)"
elif c2_letter == "(c)":
    w1_letter = "(c)"
elif c2_letter == "(b)":
    w1_letter = "(a)"
else:
    w1_letter = "(b)"
P("   W1 CUT VERDICT (the floor-midpoint bisection at fm (345,1,354)")
P("   n=254,801; both stable-class outcomes narrow by bisection at the")
P("   interior point -- the D1 symmetric-narrowing criterion")
P("   (state-s166.txt D1; unlike mid, where a CAPTURED outcome cannot")
P("   narrow)):")
P(f"     C1 (control replication): {'(a)' if c1_ok else '(b)'}")
P(f"     C2 (fm class stability): {c2_letter}")
P(f"     W1 {w1_letter}")
P("     NAMED, NOT HIDDEN (label reading): the protocol's W1 (c) text")
P("     reads \"C2 (c)/(d) -> NOTHING MOVES\" while record.txt maps W1")
P("     (d) to the frozen INVALIDATION criterion and the protocol")
P("     header says W1 (d) also fires on C1 (b); this script reports")
P("     C2 (d)/C1 (b) as W1 (d) INVALID (record.txt's explicit")
P("     mapping), which also satisfies \"NOTHING MOVES\" -- the bracket")
P("     outcome is identical under every reading.")
if w1_letter == "(a)":
    P("     (a) C2 (b) -> THE BRACKET NARROWS TO (254,557, 254,801]")
    P("     (\"THE B=3 CLASS FLIP LIES AT OR BELOW n=254,801\"); the")
    P("     MID-ONLY NARROWING CLAIM is REFUTED BY IMPLICATION")
    P("     (F <= 254,801 < 254,882 -- the claim can never be claimed")
    P("     after that outcome; first status movement of the claim")
    P("     since suspension, by implication only, no mid content")
    P("     measured).")
elif w1_letter == "(b)":
    P("     (b) C2 (a) -> THE BRACKET NARROWS TO (254,801, 255,045]")
    P("     (\"THE B=3 CLASS FLIP LIES ABOVE n=254,801\"); the MID-ONLY")
    P("     NARROWING CLAIM stays SUSPENDED (named, not claimed).")
elif w1_letter == "(c)":
    P("     (c) C2 (c)/(d) -> NOTHING MOVES; the bracket stays EXACTLY")
    P("     (254,557, 255,045]; the MID-ONLY NARROWING CLAIM stays")
    P("     SUSPENDED (named, not claimed).")
else:
    P("     (d) INVALID (C1 (b) or the frozen INVALIDATION criterion")
    P("     leaves W1 unevaluable).")
if w1_letter == "(a)":
    P("     Bracket state: NARROWED -- (254,557, 254,801] (the upper")
    P("     endpoint moved 255,045 -> 254,801 on this cut's content;")
    P("     the lower endpoint is carried unchanged on lo's content")
    P("     (254,557).")
elif w1_letter == "(b)":
    P("     Bracket state: NARROWED -- (254,801, 255,045] (the lower")
    P("     endpoint moved 254,557 -> 254,801 on this cut's content;")
    P("     the upper endpoint is carried unchanged on hi's content")
    P("     (255,045).")
else:
    P("     Under (c)/(d) the committed bracket stays EXACTLY")
    P("     (254,557, 255,045].")
P("     NAMED, NOT HIDDEN (the protocol's frozen D1 note, verbatim):")
P("     \"Under W1 (a)/(b) both stable-class outcomes narrow the")
P("     bracket by bisection at the interior point -- the D1")
P("     symmetric-narrowing criterion (state-s166.txt D1; unlike mid,")
P("     where a CAPTURED outcome cannot narrow). NAMED, NOT HIDDEN:")
P("     both narrowing outcomes carry lo (254,557) -- dual-class on")
P("     the record -- as their lower anchor (the same anchor the 15th")
P("     cut's W1 (a) accepted when it landed (254,557, 255,045]); arm")
P("     (d)'s disputed record stands under all outcomes and no claim")
P("     at lo is ever made. Under ALL outcomes no claim at hi/lo and")
P("     no boundary between grid points is ever claimed (L5).\"")
P("     Under ALL outcomes: NO claim at hi, NO claim at lo; no boundary")
P("     between grid points is ever claimed (L5).")
P("")

# W2 (descriptive)
P("   W2 (pre-registered, descriptive) per-run 18-cell min trajectory")
P("   across the 48 fm runs in frozen order (per-run per-cell median")
P(f"   gpu_ticks over the run's {R:,} rounds, min over the 18")
P("   pipeline-ok cells; per-run quantities are DESCRIPTIVE ONLY and")
P(f"   never classify (L10)), the boundary-crossing count (runs with")
P("   18-cell min >= 1,000) AND the in-band count (runs with 18-cell")
P("   min in 981..1,015):")
traj169 = []
cross169 = 0
inband169 = 0
for r in range(1, 49):
    vals = [run_med("fm", r, kk) for kk in ok_cells]
    mn = min(vals)
    traj169.append(fmt(mn))
    if mn >= 1000:
        cross169 += 1
    if 981 <= mn <= 1015:
        inband169 += 1
P("     fm per-run 18-cell min: " + " ".join(traj169))
P(f"     fm: runs with 18-cell min >= 1,000 (COMPUTED here, "
  f"descriptive): {cross169}/48")
P(f"     fm: runs with 18-cell min in 981..1,015 (COMPUTED here, "
  f"descriptive): {inband169}/48")
P("     (prior windows' computed counts at both thresholds, parsed,")
P("     quote-only):")
for win, tdict, k in (("s147", TRAJ147, 48), ("s158", TRAJ158, 48)):
    for t in sorted(tdict):
        vals = tdict[t]
        P(f"       {win} {t} (k={k}): "
          f"{sum(1 for v in vals if v >= 1000)}/{k} at min >= 1,000, "
          f"{sum(1 for v in vals if 981 <= v <= 1015)}/{k} in 981..1,015")
P("   NO point is placed or moved on the committed row by W2 itself")
P("   (descriptive letter); bracket movement rides W1 only.")
P("")

# W3 (cross-window / cross-point letter; the point is VIRGIN)
fm_bind = [min(m_ - h_ for m_, h_ in unit_rows[("fm", f"block{j}")][0])
           for j in range(1, 17)]
fm_pooled_bind = min(m_ - h_ for m_, h_ in unit_rows[("fm", "pooled-48")][0])
P("   W3 (pre-registered, descriptive) CROSS-BINARY / CROSS-POINT")
P("   confrontation -- the point n=254,801 is VIRGIN (arm (a): NO")
P("   same-point committed window exists -- there is nothing at the")
P("   point for this window to disagree with); this window's fm")
P(f"   classes at the NEW first-measured binary (the ROUNDS6400")
P(f"   variant; fm pin {PINS['fm'][:8]}...) are reported against the")
P("   bracketing committed content (parsed, quote-only):")
P(f"     this cut's fm block classes: {fm_classes}; pooled-48 "
  f"{fm_pooled_cls}")
P("     this cut's fm block min(m-h): "
  + " / ".join(f4(v) for v in fm_bind)
  + f" ; pooled-48 {f4(fm_pooled_bind)}")
P("     lo n=254,557 dual-class rows (parsed; quote-only):")
for ticks_, cls, sess, src in W2CLAIM["254557"]:
    P(f"       n=254557: {ticks_} {cls} (session {sess})")
P(f"       lo pooled-12 {LO_POOLED12[0]} {LO_POOLED12[1]}")
P("     mid n=254,882 dual-class + TOLERANCE-UNRESOLVED record")
P("     (parsed; quote-only -- NO letter of this cut touches lo or")
P("     mid):")
for ticks_, cls, sess, src in W2CLAIM["254882"]:
    P(f"       n=254882: {ticks_} {cls} (session {sess})")
P(f"       mid pooled-48 {S139_MID_POOLED[0]} {S139_MID_POOLED[2]} "
  f"(s139); s147 pooled-48 {S147_MID_POOLED[1]} "
  f"{S147_MID_POOLED[5]} (16x IN-BAND-UNDECIDED + pooled "
  f"IN-BAND-UNDECIDED: {S147_TOL_ALL_IBU}; the 14th cut's tolerance "
  f"verdict TOLERANCE-UNRESOLVED, arm (a) content above)")
P("     the 15th cut's bis content at its NEW binary "
  f"{PINS158['bis'][:8]}... (parsed from publication-s158.txt:")
P(f"       16x block classes {S158_BIS_CLASSES}; pooled-48 "
  f"{S158_BIS_POOLED_CLS}")
P("       block binding min(m-h): "
  + " / ".join(f4(v) for v in S158_BIS_BIND)
  + f" ; pooled-48 {f4(S158_BIS_POOLED_BIND)}")
P(f"       block binding min(m-h) min..max {f4(min(S158_BIS_BIND))}.."
  f"{f4(max(S158_BIS_BIND))}")
P("     NAMED, NOT HIDDEN: the protocol's frozen W3 prose reads")
P("     \"binding min(m-h) 1,006.8..1,008.8 / pooled 1,009.7\" -- the")
P("     parsed committed publication-s158.txt bytes give block")
P(f"     min(m-h) min..max {f4(min(S158_BIS_BIND))}.."
  f"{f4(max(S158_BIS_BIND))} / pooled {f4(S158_BIS_POOLED_BIND)}; the")
P("     prose lower bound 1,006.8 matches NO committed byte (the")
P("     parsed bytes govern); W3 is descriptive and the deviation")
P("     reaches no class and no letter decision.")
P("     NAMED CROSS-BINARY HAZARD: this cut's binaries are NEW (the")
P("     ROUNDS6400 variant, first-measured digests -- NO committed pin")
P("     to match); any class comparison with the committed windows")
P("     may be BINARY-driven, cause UNMEASURED (L2 binds). Every")
P("     comparison here is cross-binary AND cross-point (the point is")
P("     VIRGIN).")
P("     L8 APPLIES (named): fm (345, 1,354) is a NEW knob pair of the")
P("     session-21 L8 combination risk class (WORK_MUL != 1 and")
P(f"     NDIV != 1), never measured at any binary before this cut; the")
P(f"     s165 enumeration gives {KS_DOUBLES} in-box same-ratio doubles")
P("     of n=254,801 and NONE is measured this cut (no same-ratio")
P("     twin arm) -- nothing is assumed about representation beyond")
P("     this cut's own measurements.")
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
for win, xd in (("s147", X1_147), ("s158", X1_158)):
    for t in sorted(xd):
        lo_, hi_, sp, pct, k = xd[t]
        P(f"       {win} {t}: per-run host_ns median min..max {lo_}..{hi_} "
          f"(spread {sp} = {pct}% of min; k={k})")
P("     host_ns is the HOST-side proxy (L3), not a C criterion; any")
P("     excursion is NAMED, NOT HIDDEN and its cause is UNMEASURED.")
P("")

P(f"5. VERDICT SUMMARY: C1 {'(a)' if c1_ok else '(b)'}; C2 {c2_letter} at "
  f"fm (254,801); W1 {w1_letter}.")
if w1_letter == "(a)":
    P("   CUT VERDICT: THE BRACKET NARROWS TO (254,557, 254,801]")
    P("   (\"THE B=3 CLASS FLIP LIES AT OR BELOW n=254,801\"); the")
    P("   MID-ONLY NARROWING CLAIM is REFUTED BY IMPLICATION (named,")
    P("   not claimed).")
elif w1_letter == "(b)":
    P("   CUT VERDICT: THE BRACKET NARROWS TO (254,801, 255,045]")
    P("   (\"THE B=3 CLASS FLIP LIES ABOVE n=254,801\"); the MID-ONLY")
    P("   NARROWING CLAIM stays SUSPENDED (named, not claimed).")
elif w1_letter == "(c)":
    P("   CUT VERDICT: NOTHING MOVES; the MID-ONLY NARROWING CLAIM stays")
    P("   SUSPENDED (named, not claimed) and is NOT made by this cut.")
else:
    P("   CUT VERDICT: INVALID; NOTHING MOVES.")
if w1_letter == "(a)":
    P("   Bracket state: NARROWED -- (254,557, 254,801].")
elif w1_letter == "(b)":
    P("   Bracket state: NARROWED -- (254,801, 255,045].")
else:
    P("   The committed bracket stays EXACTLY (254,557, 255,045].")
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

with open(os.path.join(HERE, "publication-s169.txt"), "w") as f:
    f.write("\n".join(out) + "\n")
