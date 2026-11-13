#!/usr/bin/env python3
"""JUN-59 session 185 analysis -- THE B=3 PER-DISPATCH-WORK THRESHOLD
BISECT, SEVENTEENTH CUT -- THE QUARTER-POINT CUT AT q1 (313,1229)
n=254,679 (the q=1 quarter point of the width-488 bracket (254,557,
255,045]; q=2/floor-midpoint 254,801 is NOT re-cut and mid is NOT
re-measured -- the per-point rule: no mid letter from this cut). ONE
NEW KNOB TRIPLE (q1 (3,313,1,229) -- new-to-history, L8 APPLIES).
ANALYSIS half over the 54 committed run logs of the s185/s186/s187/
s188 measurement half (this directory -- the committed gzip -n form
run-<tag>-r<NN>.txt.gz; this script READS THROUGH GZIP, the s157
capture-form deviation), under the frozen
anv-b3bisect17prereg-20261101/protocol.txt (freeze stamp
2026-11-01T16:20:57Z BEFORE any run log of this cut existed).

Route (the s160 NOT DONE (c) input rule, carried): this script parses
ONLY the 54 committed run logs in its own directory (read through
gzip) and the NAMED COMMITTED WANT SOURCES (the s27 controls census;
the publication-s169.txt 16th-cut content -- the arm-(a) FIRST
content + the C1 (b) discrepancy; the knob-search-s177-run1.txt
section-2/section-3/section-5 quotes -- the s178 census, the
publication-s139.txt W2 row table + pooled-window quotes (arm (d));
the publication-s147.txt mid TOLERANCE-UNRESOLVED record (arm (d));
the publication-s158.txt 15th-cut landed outcome + bis content at
52fb68b6... (W3); the build-census-s185.txt first-measured binary
pins -- all parsed here from committed bytes, never transcribed) and
writes publication-s185.txt. No other input. Deterministic: running
it twice yields byte-identical publication-s185.txt (checked by cmp
after the recorded run). Every want source is parsed with fail-closed
regexes; a want that does not parse aborts (assert).

The frozen letters (protocol): C1 (control replication, unchanged
from the standing cut protocol: c2 FLOOR in the committed floor band
31..32; c8 within +/-5% of the committed 32,915; C1 (b) -> W1 (d);
+ the D2 supersession/limitation, arm (a): if THIS cut's own c2
control lands FLOOR inside the committed floor band 31..32 (C1 (a)),
this cut's C1 (a) reading SUPERSEDES the 16th cut's C1 (b) reading AS
THE CURRENT CONTROL STATE; if C1 (b) again, NOTHING is superseded,
the discrepancy REPLICATES (twice on record), W1 (d) fires, and the
committed floor band 31..32 vs the observed value becomes a named
open control question carried forward) / C2 (q1 class stability at
16-block granularity under THE PRE-REGISTERED DEEP-POOLING CI CLASS
STATISTIC (protocol arm (c), frozen BEFORE runs): per unit per cell
m_c = pooled sample median gpu_ticks, MAD_c = sample median
|x - m_c|, CI half-width h_c = 3.6420 * MAD_c / sqrt(N) (N = 3R =
19,200 per block/control cell, 48R = 307,200 per pooled-48 cell;
R = 6,400 frozen); unit classes at the FROZEN 1,000-tick threshold --
CAPTURED iff all 18 pipeline-ok cells m_c - h_c >= 1,000; FLOOR iff
all 18 m_c + h_c <= 100; INTERMEDIATE/MIXED iff (some m_c + h_c <
1,000) AND (some m_c - h_c > 100); IN-BAND-UNDECIDED otherwise; C2
(a) STABLE-INTERMEDIATE (all 16 blocks + pooled-48 class
INTERMEDIATE/MIXED) / (b) STABLE-CAPTURED (all CAPTURED) / (c)
CLASS-UNRESOLVED (mixed block classes, or any IN-BAND-UNDECIDED
unit, or the pooled arm differs) / (d) INVALID) / W1 (cut verdict;
(a) C2 (b) -> the bracket narrows to (254,557, 254,679] and the
MID-ONLY NARROWING CLAIM is REFUTED BY IMPLICATION (F <= 254,679 <
254,882); (b) C2 (a) -> the bracket narrows to (254,679, 255,045];
(c) C2 (c)/(d) -> NOTHING MOVES, bracket stays EXACTLY (254,557,
255,045]; (d) INVALID -- also fires on C1 (b)) / W2 (descriptive:
per-run 18-cell min trajectory, crossings at 1,000 AND in-band counts
981..1,015) / W3 (descriptive cross-binary/cross-point letter -- the
point is VIRGIN, so every comparison is against the bracketing
committed content and is cross-binary AND cross-point; NAMED
CROSS-BINARY HAZARD: this cut's binaries are NEW, first-measured
digests) / X1 (host_ns spread, descriptive). The min-over-18
threshold-ride statistic is GONE (the s152 D2 decision) -- no class
is computed from it.
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

# frozen protocol constants (anv-b3bisect17prereg-20261101/protocol.txt)
R = 6400                 # rounds per cell per run (arm (c)(i))
WARMUP = 3
N_BASE = 1000003
H_CONST = 3.6420         # frozen CI constant (1.96 * 1.2533 * 1.4826)
CAP_MIN = 1000.0         # frozen 1,000-tick threshold
FLOOR_MAX = 100.0
TICK_NS = 52.083         # timestampPeriod (asserted against the logs)

# tag -> (BATCH, WORK_MUL, NDIV, k), frozen protocol ARM TABLE
# (3 rows = 54 fresh processes; run-count self-check 3+48+3 = 54)
ARMS = [("c2", 2, 1, 1, 3), ("q1", 3, 313, 1229, 48), ("c8", 8, 1, 1, 3)]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMW = {a[0]: a[2] for a in ARMS}
ARMD = {a[0]: a[3] for a in ARMS}
ARMK = {a[0]: a[4] for a in ARMS}
BLOCKS = {"q1": [tuple(range(3 * j - 2, 3 * j + 1)) for j in range(1, 17)]}
UNIT48 = tuple(range(1, 49))
Q1_N = (N_BASE * 313) // 1229         # 254,679 -- asserted below
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
pub169 = open(os.path.join(GPU, "anv-b3bisect16-20261101",
                           "publication-s169.txt")).read()
ks177 = open(os.path.join(GPU, "anv-b3bisect17prereg-20261101",
                          "knob-search-s177-run1.txt")).read()
bc185 = open(os.path.join(HERE, "build-census-s185.txt")).read()

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
    pub147, r"(\(c\) TOLERANCE-UNRESOLVED: any in-band minimum or mixed classes "
            r"-- FAILS; L9 binds at mid at 16 blocks under the tolerance rule too\.)",
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

# ---- knob-search-s177-run1.txt (the s178 cut-point confrontation
# ---- census; the protocol's arm (a)/(d)/(W3) re-citation source) ----
m = re.search(r"committed bracket \(publication-s158\.txt, parsed\): "
              r"\((\d+), (\d+)\] n-units, width (\d+)", flat(ks177))
assert m is not None, "WANT SOURCE NOT PARSED: ks177 bracket"
KS_BRACKET = (int(m.group(1)), int(m.group(2)))
KS_WIDTH = int(m.group(3))
m = re.search(r"quarter q=1 n=(\d+): pairs (\d+); smallest \((\d+), (\d+)\); "
              r"in-box same-ratio doubles (\d+); committed-source occurrences "
              r"\{([^}]*)\}", flat(ks177))
assert m is not None, "WANT SOURCE NOT PARSED: ks177 q1 quarter line"
KS_Q1 = (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)),
         int(m.group(5)), m.group(6))
VIRGIN_QUOTE = parse1(
    ks177, r"(content confrontation: n=254679 has NEVER been measured -- "
           r"0 occurrences in every parsed committed source "
           r"\(virgin; enumeration only\)\.)", "ks177 virgin quote")

# ks177 section 2 -- the 16th cut's content parsed at s178 (the arm (a)
# FIRST content quote; cross-checked below against the publication-
# s169.txt parse -- the protocol's "knob-search-s177-run1.txt == run2.txt
# section 2, == the publication-s169.txt parse")
KS169_C1C2 = parse1(ks177, r"(C1: c2 pooled median m [\d.]+, deep-pooling class "
                           r"FLOOR \(committed floor band \d+\.\.\d+ at B=2\): "
                           r"(?:True|False))", "ks177 C1 c2 line")
m = re.search(r"C1: c2 pooled median m ([\d.]+), deep-pooling class FLOOR "
              r"\(committed floor band (\d+)\.\.(\d+) at B=2\): (True|False)",
              flat(ks177))
assert m is not None, "WANT SOURCE NOT PARSED: ks177 C1 c2 fields"
KS169_C1C2_FIELDS = (m.group(1), int(m.group(2)), int(m.group(3)), m.group(4))
KS169_C1C8 = parse1(ks177, r"(C1: c8 pooled median m [\d.]+ within \+/-5% of "
                           r"committed [\d,]+ \(session 4 pooled median\): "
                           r"(?:True|False) \([-+][\d.]+%\))", "ks177 C1 c8 line")
KS169_C1_VERDICT = parse1(
    ks177, r"(C1 VERDICT: branch \(\w\) replication discrepancy \(W1 \(d\) "
           r"INVALID fires\); cause UNMEASURED\.)", "ks177 C1 verdict")
m = re.search(r"C2 block classes \(re-count COMPUTED here\): (\d+)x CAPTURED "
              r"\+ (\d+)x INTERMEDIATE/MIXED \+ (\d+)x IN-BAND-UNDECIDED; "
              r"pooled-48 class (\S+)", flat(ks177))
assert m is not None, "WANT SOURCE NOT PARSED: ks177 class re-count"
KS169_RECOUNT = (int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4))
KS169_RECOUNT_QUOTE = parse1(
    ks177, r"(C2 block classes \(re-count COMPUTED here\): \d+x CAPTURED "
           r"\+ \d+x INTERMEDIATE/MIXED \+ \d+x IN-BAND-UNDECIDED; "
           r"pooled-48 class \S+)", "ks177 class re-count quote")
m = re.search(r"C2 block binding min\(m-h\): ([\d.]+)\.\.([\d.]+) "
              r"\((\d+) values\), pooled-48 ([\d.]+)", flat(ks177))
assert m is not None, "WANT SOURCE NOT PARSED: ks177 binding range"
KS169_BIND_RANGE = (float(m.group(1)), float(m.group(2)), int(m.group(3)),
                    float(m.group(4)))
m = re.search(r"C2 \(sum,128,S=16\) m: blocks (\d+)\.\.(\d+) \((\d+) values\), "
              r"pooled-48 (\d+)", flat(ks177))
assert m is not None, "WANT SOURCE NOT PARSED: ks177 m range"
KS169_M_RANGE = (int(m.group(1)), int(m.group(2)), int(m.group(3)),
                 int(m.group(4)))
m = re.search(r"(VERDICT SUMMARY \(parsed\): C1 \((\w)\); C2 \((\w)\) at fm "
              r"\(254801\); W1 \((\w)\)\. CUT VERDICT: INVALID; NOTHING MOVES\. "
              r"The committed bracket stays EXACTLY \(254557, 255045\]\.)",
              flat(ks177))
assert m is not None, "WANT SOURCE NOT PARSED: ks177 verdict summary"
KS169_VERDICT_QUOTE = m.group(1)
KS169_LETTERS = (m.group(2), m.group(3), m.group(4))

# ks177 section 3 -- the disputed-record PRIMARY quotes (arm (d)),
# cross-checked below against the pub139/pub147 parses
KS177_LO = parse1(ks177, r"(PRIMARY \(publication-s139\.txt\): lo n=254,557 "
                         r"dual-class rows \[[^\]]*\]; lo tenth-cut pooled-12 "
                         r"median \d+, 18-cell \d+\.\.\d+, class \S+)",
                  "ks177 primary lo")
KS177_MID = parse1(ks177, r"(PRIMARY \(publication-s139\.txt\): mid n=254,882 "
                          r"dual-class rows \[[^\]]*\]; mid pooled-48 median "
                          r"\d+, 18-cell \d+\.\.\d+, class \S+)",
                   "ks177 primary mid")
KS177_PUB147 = parse1(ks177, r"(PRIMARY \(publication-s147\.txt\): 14th cut mid "
                             r"content -- .*?under the tolerance rule too\.)",
                      "ks177 primary pub147")
KS177_W3_XCHECK = parse1(ks177, r"(W3 CROSS-CHECK: .*?UNCONTESTED between the "
                                r"sources\.)", "ks177 w3 cross-check")

# cross-check the ks177 disputed-record quotes against the pub139/pub147
# parses (the s178 "UNCONTESTED between the sources" claim, re-derived)
ks177_lo_rows = [(int(a), b, c) for a, b, c in
                 re.findall(r"\((\d+), '((?:INTERMEDIATE/MIXED|CAPTURED))', "
                            r"'(\d+)'\)", KS177_LO)]
assert ks177_lo_rows == [(t, c, s) for t, c, s, _ in W2CLAIM["254557"]], (
    f"ks177 lo rows {ks177_lo_rows} vs pub139 {W2CLAIM['254557']}")
m = re.search(r"lo tenth-cut pooled-12 median (\d+), 18-cell (\d+)\.\.(\d+), "
              r"class (\S+)", KS177_LO)
assert m is not None, "WANT SOURCE NOT PARSED: ks177 lo pooled"
assert (m.group(1), m.group(4)) == LO_POOLED12, (
    f"ks177 lo pooled {(m.group(1), m.group(4))} vs pub139 {LO_POOLED12}")
ks177_mid_rows = [(int(a), b, c) for a, b, c in
                  re.findall(r"\((\d+), '((?:INTERMEDIATE/MIXED|CAPTURED))', "
                             r"'(\d+)'\)", KS177_MID)]
assert ks177_mid_rows == [(t, c, s) for t, c, s, _ in W2CLAIM["254882"]], (
    f"ks177 mid rows {ks177_mid_rows} vs pub139 {W2CLAIM['254882']}")
m = re.search(r"mid pooled-48 median (\d+), 18-cell (\d+)\.\.(\d+), "
              r"class (\S+)", KS177_MID)
assert m is not None, "WANT SOURCE NOT PARSED: ks177 mid pooled"
assert (m.group(1), m.group(4)) == (S139_MID_POOLED[0], S139_MID_POOLED[2]), (
    f"ks177 mid pooled vs pub139 {S139_MID_POOLED}")
m = re.search(r"block 18-cell minima ([\d /]+); pooled-48 min (\d+), "
              r"pooled-48 median (\d+)", KS177_PUB147)
assert m is not None, "WANT SOURCE NOT PARSED: ks177 pub147 minima"
assert [int(x) for x in m.group(1).split("/")] == S147_MINIMA, (
    "ks177 pub147 minima vs pub147 parse")
assert m.group(2) == S147_POOLED_MIN, "ks177 pub147 pooled min vs pub147 parse"

# ---- publication-s169.txt (the SIXTEENTH CUT's landed content: the
# ---- protocol's arm-(a) FIRST content at fm (345,1354) n=254,801, the
# ---- C1 (b) discrepancy, and W3 comparison content) ----
m = re.search(r"c2 \(sum,128,S=16\) pooled median m ([\d.]+), deep-pooling "
              r"class FLOOR \(committed floor band (\d+)\.\.(\d+) at B=2\): "
              r"(True|False)", flat(pub169))
assert m is not None, "WANT SOURCE NOT PARSED: pub169 C1 c2"
S169_C1C2 = (float(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4))
S169_C1C2_QUOTE = parse1(pub169, r"(c2 \(sum,128,S=16\) pooled median m [\d.]+, "
                                 r"deep-pooling class FLOOR \(committed floor "
                                 r"band \d+\.\.\d+ at B=2\): (?:True|False))",
                         "pub169 C1 c2 quote")
m = re.search(r"c8 \(sum,128,S=16\) pooled median m ([\d.]+) within \+/-5% of "
              r"committed ([\d,]+) \(session 4 pooled median\): (True|False) "
              r"\(([-+][\d.]+)%\)", flat(pub169))
assert m is not None, "WANT SOURCE NOT PARSED: pub169 C1 c8"
S169_C1C8 = (float(m.group(1)), m.group(2), m.group(3), m.group(4))
S169_C1_ARM_OK = parse1(pub169, r"control arms free of VERIFY mismatches "
                                r"\(frozen INVALIDATION criterion\): "
                                r"(True|False)", "pub169 control arms")
S169_C1_VERDICT = parse1(pub169, r"(VERDICT: branch \(\w\) replication "
                                 r"discrepancy \(W1 \(d\) INVALID fires\); "
                                 r"cause UNMEASURED\.)", "pub169 C1 verdict")
m = re.search(r"block classes: \[([^\]]*)\]; pooled-48 class: (\S+)", pub169)
assert m is not None, "WANT SOURCE NOT PARSED: pub169 block classes"
S169_FM_CLASSES = re.findall(r"'(\S+?)'", m.group(1))
assert len(S169_FM_CLASSES) == 16, f"pub169 classes {len(S169_FM_CLASSES)}"
S169_FM_POOLED_CLS = m.group(2)
S169_FM_BIND = [float(x) for x in
                parse1(pub169, r"block binding min\(m-h\): ([\d. /]+)",
                       "pub169 block bindings").split("/")]
assert len(S169_FM_BIND) == 16, f"pub169 bindings {len(S169_FM_BIND)}"
S169_FM_POOLED_BIND = float(parse1(pub169, r"pooled-48 binding min\(m-h\): "
                                           r"([\d.]+)", "pub169 pooled binding"))
m = re.search(r"\(sum,128,S=16\) m: blocks ([\d. /]+) ; pooled-48 ([\d.]+)",
              flat(pub169))
assert m is not None, "WANT SOURCE NOT PARSED: pub169 m line"
S169_FM_M = [float(x) for x in m.group(1).split("/")]
assert len(S169_FM_M) == 16, f"pub169 m {len(S169_FM_M)}"
S169_FM_POOLED_M = float(m.group(2))
m = re.search(r"VERDICT SUMMARY: C1 \((\w)\); C2 \((\w)\) at fm \(254,?801\); "
              r"W1 \((\w)\)\.", flat(pub169))
assert m is not None, "WANT SOURCE NOT PARSED: pub169 verdict summary"
S169_LETTERS = (m.group(1), m.group(2), m.group(3))
S169_CUT_VERDICT = parse1(pub169, r"(CUT VERDICT: INVALID; NOTHING MOVES\.)",
                          "pub169 cut verdict")
m = re.search(r"Bracket state: NARROWED -- \(([\d,]+), ([\d,]+)\]", flat(pub158))
assert m is not None, "WANT SOURCE NOT PARSED: pub158 bracket state"
S158_BRACKET = (int(m.group(1).replace(",", "")),
                int(m.group(2).replace(",", "")))
assert S158_BRACKET == KS_BRACKET, (
    f"bracket parse disagreement pub158 {S158_BRACKET} vs ks177 {KS_BRACKET}")
assert KS_BRACKET == (BRACKET_LO, BRACKET_HI), f"bracket {KS_BRACKET}"
assert KS_WIDTH == 488, f"bracket width {KS_WIDTH}"
assert (BRACKET_LO + KS_WIDTH // 4) == Q1_N == KS_Q1[0] == 254679, (
    f"quarter derivation {BRACKET_LO + KS_WIDTH // 4} vs {Q1_N} vs {KS_Q1[0]}")
assert KS_Q1[2:5] == (313, 1229, 8), f"ks177 q1 fields {KS_Q1}"
assert math.gcd(313, 1229) == 1, "q1 knob gcd"
assert KS169_LETTERS == S169_LETTERS, (
    f"ks177 vs pub169 letters {KS169_LETTERS} vs {S169_LETTERS}")

# cross-check the ks177 section-2 re-count/ranges against the pub169 parse
assert KS169_RECOUNT == (
    S169_FM_CLASSES.count("CAPTURED"),
    S169_FM_CLASSES.count("INTERMEDIATE/MIXED"),
    S169_FM_CLASSES.count("IN-BAND-UNDECIDED"), S169_FM_POOLED_CLS), (
    f"ks177 recount {KS169_RECOUNT} vs pub169 classes {S169_FM_CLASSES}")
assert (abs(KS169_BIND_RANGE[0] - min(S169_FM_BIND)) < 0.00005
        and abs(KS169_BIND_RANGE[1] - max(S169_FM_BIND)) < 0.00005
        and KS169_BIND_RANGE[2] == 16
        and abs(KS169_BIND_RANGE[3] - S169_FM_POOLED_BIND) < 0.00005), (
    f"ks177 bind range {KS169_BIND_RANGE} vs pub169 "
    f"{min(S169_FM_BIND)}..{max(S169_FM_BIND)} {S169_FM_POOLED_BIND}")
# NAMED, NOT HIDDEN: the ks177 m range reads FIRST..LAST (block1..block16),
# not min..max -- asserted against the parsed pub169 m list on that reading
assert (KS169_M_RANGE[0] == S169_FM_M[0] and KS169_M_RANGE[1] == S169_FM_M[-1]
        and KS169_M_RANGE[2] == 16
        and KS169_M_RANGE[3] == S169_FM_POOLED_M), (
    f"ks177 m range {KS169_M_RANGE} vs pub169 first/last "
    f"{S169_FM_M[0]}..{S169_FM_M[-1]} {S169_FM_POOLED_M}")
assert KS169_C1C2_FIELDS == (fmt(S169_C1C2[0]), S169_C1C2[1], S169_C1C2[2],
                             S169_C1C2[3]), (
    f"ks177 C1 c2 fields {KS169_C1C2_FIELDS} vs pub169 {S169_C1C2}")

# the 15th cut's landed outcome + bis content (W3 comparison content)
m = re.search(r"VERDICT SUMMARY: C1 \((\w)\); C2 \((\w)\) at bis \(255,045\); "
              r"W1 \((\w)\)\.", flat(pub158))
assert m is not None, "WANT SOURCE NOT PARSED: pub158 verdict summary"
S158_C1, S158_C2, S158_W1 = m.group(1), m.group(2), m.group(3)
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
TRAJ169 = {"fm": traj(pub169, "fm", 48)}
X1_147 = x1_rows(pub147, ("c2", "mid", "c8"))
X1_158 = x1_rows(pub158, ("c2", "bis", "c8"))
X1_169 = x1_rows(pub169, ("c2", "fm", "c8"))

# the s169 W2 computed counts (cross-checked against the trajectory)
m = re.search(r"fm: runs with 18-cell min >= 1,000 \(COMPUTED here, "
              r"descriptive\): (\d+)/(\d+)", flat(pub169))
assert m is not None, "WANT SOURCE NOT PARSED: pub169 W2 cross count"
S169_W2_CROSS = (int(m.group(1)), int(m.group(2)))
m = re.search(r"fm: runs with 18-cell min in 981\.\.1,015 \(COMPUTED here, "
              r"descriptive\): (\d+)/(\d+)", flat(pub169))
assert m is not None, "WANT SOURCE NOT PARSED: pub169 W2 inband count"
S169_W2_INBAND = (int(m.group(1)), int(m.group(2)))
assert S169_W2_CROSS == (sum(1 for v in TRAJ169["fm"] if v >= 1000), 48), (
    f"pub169 W2 cross {S169_W2_CROSS} vs trajectory recompute")
assert S169_W2_INBAND == (sum(1 for v in TRAJ169["fm"]
                              if 981 <= v <= 1015), 48), (
    f"pub169 W2 inband {S169_W2_INBAND} vs trajectory recompute")

# this cut's first-measured binary pins (committed build-census-s185.txt)
PINS = {}
for mm in re.finditer(r"anv-bb-(c2|q1|c8)  ([0-9a-f]{64})", bc185):
    assert mm.group(1) not in PINS, f"duplicate pin line {mm.group(1)}"
    PINS[mm.group(1)] = mm.group(2)
assert set(PINS) == {"c2", "q1", "c8"}, f"pin set {sorted(PINS)}"

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
        integrity.append(f"SUM COUNT {sum(counts.values())} != {exp}")
    for kk in ok_cells:
        if counts.get(kk, 0) != R:
            ok = False
            integrity.append(f"SUM COUNT idx={kk} {counts.get(kk, 0)} != {R}")
    return cells, verifies, header, ticks, ok_cells, ok, integrity, host128


out = []
P = out.append
P("JUN-59 session 185 analysis -- THE B=3 PER-DISPATCH-WORK THRESHOLD")
P("BISECT, SEVENTEENTH CUT -- THE QUARTER-POINT CUT AT q1 (313,1229)")
P("n=254,679 (the q=1 quarter point of the width-488 bracket (254,557,")
P("255,045]; q=2/floor-midpoint 254,801 is NOT re-cut and mid is NOT")
P("re-measured -- the per-point rule: no mid letter from this cut).")
P("ONE NEW KNOB TRIPLE (q1 (3,313,1,229) -- new-to-history, L8")
P("APPLIES).")
P("publication -- the ANALYSIS half over the 54 committed run logs of")
P("the s185/s186/s187/s188 measurement half (this directory -- the")
P("committed gzip -n form run-<tag>-r<NN>.txt.gz; this script READS")
P("THROUGH GZIP, the s157 capture-form deviation), under the frozen")
P("anv-b3bisect17prereg-20261101/protocol.txt (freeze stamp")
P("2026-11-01T16:20:57Z BEFORE any run log of this cut existed).")
P("Produced ONLY by analysis-s185.py over the 54 committed run logs in")
P("this directory and the NAMED COMMITTED WANT SOURCES parsed below")
P("(the s27 controls census; the publication-s169.txt 16th-cut")
P("content -- the arm-(a) FIRST content + the C1 (b) discrepancy; the")
P("knob-search-s177-run1.txt section-2/3/5 quotes (the s178 census);")
P("the publication-s139.txt W2 row table + pooled-window quotes (arm")
P("(d)); the publication-s147.txt mid TOLERANCE-UNRESOLVED record (arm")
P("(d)); the publication-s158.txt 15th-cut landed outcome + bis")
P("content at 52fb68b6... (W3); the build-census-s185.txt")
P("first-measured binary pins; all parsed from committed bytes, never")
P("transcribed). Arms = binary compile-time (BATCH, WORK_MUL, NDIV);")
P(f"n = (1,000,003*WORK_MUL)/NDIV (integer floor). The row question")
P("(protocol): AT FIXED B=3, IS THE CLASS AT (313, 1229) n=254,679")
P("SINGLE-CLASS STABLE AT 16-BLOCK GRANULARITY (16 blocks of 3 runs +")
P("pooled-48) UNDER THE PRE-REGISTERED DEEP-POOLING CI CLASS STATISTIC")
P(f"(R = 6,400), AT ITS NEW FIRST-MEASURED BINARY (THE ROUNDS6400")
P(f"INSTRUMENT VARIANT; this window's build pins parsed below: c2 "
  f"{PINS['c2'][:8]}... q1 {PINS['q1'][:8]}... c8 {PINS['c8'][:8]}...)?")
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
P("   ARM (a) CONTENT CONFRONTED FIRST (protocol arm (a), the D2")
P("   mandate): the SIXTEENTH CUT's content at fm (345, 1354)")
P("   n=254,801, quoted from committed bytes (knob-search-s177-run1.txt")
P("   section 2 == the publication-s169.txt parse; both parsed here and")
P("   cross-checked against each other):")
P(f"     {KS169_VERDICT_QUOTE}")
P(f"     C1: {KS169_C1C2}")
P(f"     C1: {KS169_C1C8}")
P(f"     {KS169_C1_VERDICT}")
P(f"     {KS169_RECOUNT_QUOTE}")
P(f"     C2 block binding min(m-h): {f4(KS169_BIND_RANGE[0])}.."
  f"{f4(KS169_BIND_RANGE[1])} ({KS169_BIND_RANGE[2]} values), pooled-48 "
  f"{fmt(KS169_BIND_RANGE[3])}")
P(f"     C2 (sum,128,S=16) m: blocks {KS169_M_RANGE[0]}.."
  f"{KS169_M_RANGE[1]} ({KS169_M_RANGE[2]} values), pooled-48 "
  f"{KS169_M_RANGE[3]}")
P("     NAMED, NOT HIDDEN: the ks177 m range reads FIRST..LAST")
P("     (block1..block16: 1,145..1,134), NOT min..max (the parsed")
P("     pub169 bytes give min..max 1,133..1,147) -- the ks177 range is")
P("     asserted against the pub169 first/last values on that reading;")
P("     the binding range 997.0538..1006.7909 reads min..max and is")
P("     asserted as such.")
P("     CROSS-CHECK ks177 section 2 == publication-s169.txt parse:")
P(f"       letters {KS169_LETTERS} == {S169_LETTERS}: "
  f"{KS169_LETTERS == S169_LETTERS}")
P(f"       class recount {KS169_RECOUNT} == pub169 class list counts: "
  f"{KS169_RECOUNT == (S169_FM_CLASSES.count('CAPTURED'), S169_FM_CLASSES.count('INTERMEDIATE/MIXED'), S169_FM_CLASSES.count('IN-BAND-UNDECIDED'), S169_FM_POOLED_CLS)}")
P(f"       pooled-48 class {S169_FM_POOLED_CLS}; pooled-48 binding "
  f"min(m-h) {f4(S169_FM_POOLED_BIND)}; pooled-48 (sum,128,S=16) m "
  f"{fmt(S169_FM_POOLED_M)}")
P("     THE C1 (b) DISCREPANCY (protocol arm (a); the 16th cut's")
P("     control replication discrepancy -- confronted by this cut's C1")
P("     letter below; its cause is UNMEASURED, L2 binds):")
P(f"       {S169_C1C2_QUOTE}")
P(f"       {S169_C1_VERDICT}")
P("     FROZEN SUPERSESSION STATEMENT (protocol, carried here")
P("     verbatim): NO letter of this cut supersedes the 16th cut's")
P("     point content at 254,801 or its C2 (c)/W1 (d)/CUT VERDICT: this")
P("     cut does not measure 254,801; that content stands as committed")
P("     content under ALL outcomes of this cut (the s166 'no letter")
P("     supersedes' precedent). The L9 clause at 254,801 stands (any")
P("     future narrowing claim at n=254,801 must confront the 16th")
P("     cut's content first). THIS CUT's POINT is vacuous-at-point")
P("     (VIRGIN; ks177 section 5 quote below) -- no committed reading")
P("     exists at n=254,679 to supersede; this cut's own content, if it")
P("     runs, is the FIRST content at the point. The ONLY supersession")
P("     this cut can perform is on the control reading: the C1 (b)")
P("     confrontation below.")
P("   this cut's point's committed content at (313, 1229) n=254,679,")
P("   quoted from committed knob-search-s177-run1.txt bytes:")
P(f"     quarter q=1 n={KS_Q1[0]}: pairs {KS_Q1[1]}; smallest "
  f"({KS_Q1[2]}, {KS_Q1[3]}); in-box same-ratio doubles {KS_Q1[4]}; "
  f"committed-source occurrences {{{KS_Q1[5]}}}")
P(f"     {VIRGIN_QUOTE}")
P("     STATED, NOT SILENT: the point is VIRGIN -- this cut's own")
P("     48-run content, if it runs, is the FIRST content at the point")
P("     (vacuous-at-point; arm (a) 'supersedes which committed reading'")
P("     is answered: NONE AT THE POINT (stated), and at fm NONE (the")
P("     statement above)).")
P("   ARM (d) CLAIM-FORM CONFRONTATION CONTENT (protocol arm (d); the")
P("   disputed record, quoted from committed knob-search-s177-run1.txt")
P("   section 3 PRIMARY lines == the publication-s139/147.txt parses --")
P("   both parsed here and cross-checked against each other):")
P(f"     {KS177_LO}")
P(f"     {KS177_MID}")
P(f"     {KS177_PUB147}")
P(f"     {KS177_W3_XCHECK}")
P("   the letters' treatment, frozen here: NO letter of this cut")
P("   touches lo or mid; the dual-class and cross-window disputed")
P("   record stands as committed content under ALL outcomes; its cause")
P("   is UNMEASURED (L2 binds).")
P("   15th cut (sessions 157-163) landed outcome (parsed from")
P("   committed publication-s158.txt bytes -- the bracket this cut")
P("   starts from):")
P(f"     VERDICT SUMMARY: C1 ({S158_C1}); C2 ({S158_C2}) at bis")
P(f"     (255,045); W1 ({S158_W1}).")
P(f"     Bracket state: NARROWED -- ({fmt(S158_BRACKET[0])}, "
  f"{fmt(S158_BRACKET[1])}]; knob-search-s177-run1.txt bracket parse "
  f"({KS_BRACKET[0]}, {KS_BRACKET[1]}] -> MATCH "
  f"{S158_BRACKET == KS_BRACKET})")
P("   this cut's first-measured binary pins (parsed from committed")
P("   build-census-s185.txt bytes; NEW binaries -- NO committed pin to")
P("   match, the s136 precedent; c2/c8 reproduce the s169 digests")
P("   byte-identically on the same source+knob bytes -- a capture")
P("   observation, not a claim; q1 is new-to-history):")
for t in ("c2", "q1", "c8"):
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
P("   capture-form deviation; the raw logs are NOT kept, named):")
P(f"   device (parsed from the logs): {dev_line}")
P(f"   {tp_line}")
P("   runs parsed: 54 (c2 x3, q1 x48, c8 x3 -- the frozen ARM TABLE's")
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
P(f"   knob arithmetic (record): (1,000,003*313)//1229 = "
  f"{(N_BASE * 313) // 1229} == the header n=254679: "
  f"{(N_BASE * 313) // 1229 == 254679 == Q1_N}; gcd(313,1229) = "
  f"{math.gcd(313, 1229)}")
P(f"   quarter-grid derivation (record): width {KS_WIDTH}, q=1 = "
  f"{BRACKET_LO} + {KS_WIDTH}//4 = {BRACKET_LO + KS_WIDTH // 4} == Q1_N; "
  f"floor midpoint q=2 = ({BRACKET_LO}+{BRACKET_HI})//2 = "
  f"{(BRACKET_LO + BRACKET_HI) // 2} (NOT re-cut this cut)")
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
assert len(ok_cells) == 18, f"ok cells {ok_cells}"


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
# standing cut protocol + the D2 supersession/limitation (arm (a))
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
P("   on C1 (b); unchanged from the standing cut protocol + the D2")
P("   supersession/limitation, arm (a)): controls have k=3: one")
P(f"   deep-pooling unit each (N = 3R = {3 * R:,} per cell):")
P(f"     c2 (sum,128,S=16) pooled median m {fmt(v_c2)}, deep-pooling")
P(f"     class FLOOR (committed floor band {C2_BAND[0]}..{C2_BAND[1]} "
  f"at B=2): {c1_c2_ok}")
P(f"     c8 (sum,128,S=16) pooled median m {fmt(v_c8)} within +/-5% of "
  f"committed {C8_COMMITTED} (session 4 pooled median): {c1_c8_ok} "
  f"({(v_c8 - C8_COMMITTED) / C8_COMMITTED * 100:+.2f}%)")
P(f"     control arms free of VERIFY mismatches (frozen INVALIDATION "
  f"criterion): {c1_arm_ok}")
if c1_ok:
    P("     VERDICT: branch (a) both controls satisfy their criteria --")
    P("     W1 is evaluated against the row question.")
    P("     D2 SUPERSESSION (arm (a), the frozen rule): this cut's C1")
    P("     (a) reading SUPERSEDES the 16th cut's C1 (b) reading AS THE")
    P("     CURRENT CONTROL STATE (the 16th's (b) remains committed")
    P("     history; the discrepancy cause stays UNMEASURED, L2 binds).")
else:
    P("     VERDICT: branch (b) replication discrepancy (W1 (d) INVALID")
    P("     fires); cause UNMEASURED.")
    P("     D2 REPLICATION (arm (a), the frozen rule): NOTHING is")
    P("     superseded; the discrepancy REPLICATES (twice on record --")
    P("     the 16th cut's C1 (b) and this cut); W1 (d) fires; the")
    P("     committed floor band "
      f"{C2_BAND[0]}..{C2_BAND[1]} vs the observed {fmt(v_c2)} becomes a")
    P("     named open control question carried forward (named here,")
    P("     not resolved here).")
P("")

# C2 (q1 class stability at 16-block granularity under the deep-pooling
# statistic)
q1_classes = [unit_rows[("q1", f"block{j}")][1] for j in range(1, 17)]
q1_pooled_cls = unit_rows[("q1", "pooled-48")][1]
q1_bad = verify_mismatch_by_arm["q1"] > 0
if q1_bad:
    c2_letter = "(d)"
elif all(c == "INTERMEDIATE/MIXED" for c in q1_classes + [q1_pooled_cls]):
    c2_letter = "(a)"
elif all(c == "CAPTURED" for c in q1_classes + [q1_pooled_cls]):
    c2_letter = "(b)"
else:
    c2_letter = "(c)"
P("   C2 Q1 CLASS STABILITY AT 16-BLOCK GRANULARITY -- q1")
P("   (BATCH=3,WORK_MUL=313,NDIV=1229) at n=254,679 (knob pair (313,")
P("   1,229), the Q=1 QUARTER POINT of the bracket (254,557, 255,045];")
P("   the point is VIRGIN -- this cut's content is the FIRST content at")
P("   it) (16 blocks of 3 runs + pooled-48) under THE PRE-REGISTERED")
P(f"   DEEP-POOLING CI CLASS STATISTIC (R = {R:,}; protocol arm (c)): "
  f"{c2_letter}")
P(f"     block classes: {q1_classes}; pooled-48 class: {q1_pooled_cls}")
P("     block binding min(m-h): "
  + " / ".join(f4(min(m_ - h_ for m_, h_ in unit_rows[('q1', f'block{j}')][0]))
              for j in range(1, 17)))
P(f"     pooled-48 binding min(m-h): "
  f"{f4(min(m_ - h_ for m_, h_ in unit_rows[('q1', 'pooled-48')][0]))}")
P("     (sum,128,S=16) m: blocks "
  + " / ".join(fmt(unit_rows[("q1", f"block{j}")][0][ok_cells.index(sum128)][0])
              for j in range(1, 17))
  + f" ; pooled-48 {fmt(unit_rows[('q1', 'pooled-48')][0][ok_cells.index(sum128)][0])}")
if c2_letter == "(a)":
    P("     (a) STABLE-INTERMEDIATE: all 16 blocks AND the pooled-48 arm")
    P("     class INTERMEDIATE/MIXED -- PASSES the 16-block class-")
    P("     stability requirement at q1 under the deep-pooling")
    P("     statistic.")
elif c2_letter == "(b)":
    P("     (b) STABLE-CAPTURED: all 16 blocks AND the pooled-48 arm")
    P("     class CAPTURED -- PASSES the 16-block class-stability")
    P("     requirement at q1 under the deep-pooling statistic.")
elif c2_letter == "(c)":
    P("     (c) CLASS-UNRESOLVED: mixed block classes, or any")
    P("     IN-BAND-UNDECIDED unit, or the pooled arm differs -- FAILS;")
    P("     L9 binds at n=254,679 under the deep-pooling statistic (the")
    P("     D3 (ii) clause); any future narrowing claim at n=254,679")
    P("     must confront this cut's content first (named here, not")
    P("     specified here). NAMED (the arm-(b) re-read hazard's second")
    P("     edge, D3 (ii), verbatim): if this cut's own content at")
    P("     254,679 comes out mixed (C2 (c)), it is NOT rescued by later")
    P("     more-blocks-of-the-same-shape runs; a same-shape re-run")
    P("     there would re-read, not confront.")
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
P("   W1 CUT VERDICT (the quarter-point bisection at q1 (313,1,229)")
P("   n=254,679; both stable-class outcomes narrow by bisection at the")
P("   interior point -- the D1 symmetric-narrowing criterion holds at")
P("   q=1):")
P(f"     C1 (control replication): {'(a)' if c1_ok else '(b)'}")
P(f"     C2 (q1 class stability): {c2_letter}")
P(f"     W1 {w1_letter}")
P("     NAMED, NOT HIDDEN (label reading): the protocol's W1 (c) text")
P("     reads \"C2 (c)/(d) -> NOTHING MOVES\" while record.txt maps W1")
P("     (d) to the frozen INVALIDATION criterion and the protocol")
P("     header says W1 (d) also fires on C1 (b); this script reports")
P("     C2 (d)/C1 (b) as W1 (d) INVALID (record.txt's explicit")
P("     mapping), which also satisfies \"NOTHING MOVES\" -- the bracket")
P("     outcome is identical under every reading.")
if w1_letter == "(a)":
    P("     (a) C2 (b) -> THE BRACKET NARROWS TO (254,557, 254,679]")
    P("     (\"THE B=3 CLASS FLIP LIES AT OR BELOW n=254,679\"); the")
    P("     MID-ONLY NARROWING CLAIM is REFUTED BY IMPLICATION")
    P("     (F <= 254,679 < 254,882 -- first status movement since")
    P("     suspension, by implication only, no mid content measured;")
    P("     the s166 W1 (a) precedent shape).")
elif w1_letter == "(b)":
    P("     (b) C2 (a) -> THE BRACKET NARROWS TO (254,679, 255,045]")
    P("     (\"THE B=3 CLASS FLIP LIES ABOVE n=254,679\"); the MID-ONLY")
    P("     NARROWING CLAIM stays SUSPENDED (named, not claimed).")
elif w1_letter == "(c)":
    P("     (c) C2 (c)/(d) -> NOTHING MOVES; the bracket stays EXACTLY")
    P("     (254,557, 255,045]; the MID-ONLY NARROWING CLAIM stays")
    P("     SUSPENDED (named, not claimed).")
else:
    P("     (d) INVALID (C1 (b) or the frozen INVALIDATION criterion")
    P("     leaves W1 unevaluable).")
if w1_letter == "(a)":
    P("     Bracket state: NARROWED -- (254,557, 254,679] (the upper")
    P("     endpoint moved 255,045 -> 254,679 on this cut's content;")
    P("     the lower endpoint is carried unchanged on lo's content")
    P("     (254,557). NAMED: lo (254,557, dual-class on the record)")
    P("     remains the lower anchor -- the structural caveat the")
    P("     15th/16th cuts' W1 (a) accepted.")
elif w1_letter == "(b)":
    P("     Bracket state: NARROWED -- (254,679, 255,045] (the lower")
    P("     endpoint moved 254,557 -> 254,679 on this cut's content;")
    P("     the upper endpoint is carried unchanged on hi's content")
    P("     (255,045). NAMED: lo leaves the bracket (its rows stand as")
    P("     committed content outside it; no claim at lo is ever made)")
    P("     and mid's disputed record stays inside (arm (d) binds")
    P("     literally at mid for any future claim there).")
else:
    P("     Under (c)/(d) the committed bracket stays EXACTLY")
    P("     (254,557, 255,045].")
P("     NAMED, NOT HIDDEN (the protocol's frozen D1 note, verbatim):")
P("     \"Both (a)/(b) narrow -- the s166 D1 symmetric-narrowing")
P("     criterion holds at q=1. Under ALL outcomes no claim at hi/lo")
P("     and no boundary between grid points is ever claimed (L5).\"")
P("     Under ALL outcomes: NO claim at hi, NO claim at lo; no boundary")
P("     between grid points is ever claimed (L5).")
P("")

# W2 (descriptive)
P("   W2 (pre-registered, descriptive) per-run 18-cell min trajectory")
P("   across the 48 q1 runs in frozen order (per-run per-cell median")
P(f"   gpu_ticks over the run's {R:,} rounds, min over the 18")
P("   pipeline-ok cells; per-run quantities are DESCRIPTIVE ONLY and")
P(f"   never classify (L10)), the boundary-crossing count (runs with")
P("   18-cell min >= 1,000) AND the in-band count (runs with 18-cell")
P("   min in 981..1,015):")
traj185 = []
cross185 = 0
inband185 = 0
for r in range(1, 49):
    vals = [run_med("q1", r, kk) for kk in ok_cells]
    mn = min(vals)
    traj185.append(fmt(mn))
    if mn >= 1000:
        cross185 += 1
    if 981 <= mn <= 1015:
        inband185 += 1
P("     q1 per-run 18-cell min: " + " ".join(traj185))
P(f"     q1: runs with 18-cell min >= 1,000 (COMPUTED here, "
  f"descriptive): {cross185}/48")
P(f"     q1: runs with 18-cell min in 981..1,015 (COMPUTED here, "
  f"descriptive): {inband185}/48")
P("     (prior windows' computed counts at both thresholds, parsed,")
P("     quote-only):")
for win, tdict, k in (("s147", TRAJ147, 48), ("s158", TRAJ158, 48),
                      ("s169", TRAJ169, 48)):
    for t in sorted(tdict):
        vals = tdict[t]
        P(f"       {win} {t} (k={k}): "
          f"{sum(1 for v in vals if v >= 1000)}/{k} at min >= 1,000, "
          f"{sum(1 for v in vals if 981 <= v <= 1015)}/{k} in 981..1,015")
P("   NO point is placed or moved on the committed row by W2 itself")
P("   (descriptive letter); bracket movement rides W1 only.")
P("")

# W3 (cross-window / cross-point letter; the point is VIRGIN)
q1_bind = [min(m_ - h_ for m_, h_ in unit_rows[("q1", f"block{j}")][0])
           for j in range(1, 17)]
q1_pooled_bind = min(m_ - h_ for m_, h_ in unit_rows[("q1", "pooled-48")][0])
P("   W3 (pre-registered, descriptive) CROSS-BINARY / CROSS-POINT")
P("   confrontation -- the point n=254,679 is VIRGIN (arm (a): NO")
P("   same-point committed window exists -- there is nothing at the")
P("   point for this window to disagree with); this window's q1")
P(f"   classes at the NEW first-measured binary (the ROUNDS6400")
P(f"   variant; q1 pin {PINS['q1'][:8]}...) are reported against the")
P("   bracketing committed content (parsed, quote-only):")
P(f"     this cut's q1 block classes: {q1_classes}; pooled-48 "
  f"{q1_pooled_cls}")
P("     this cut's q1 block min(m-h): "
  + " / ".join(f4(v) for v in q1_bind)
  + f" ; pooled-48 {f4(q1_pooled_bind)}")
P("     lo n=254,557 dual-class rows (parsed; quote-only):")
for ticks_, cls, sess, src in W2CLAIM["254557"]:
    P(f"       n=254557: {ticks_} {cls} (session {sess})")
P(f"       lo pooled-12 {LO_POOLED12[0]} {LO_POOLED12[1]}")
P("     the 16th cut's fm content at 254,801 (parsed; quote-only -- NO")
P("     letter of this cut supersedes it; it stands as committed")
P("     content under ALL outcomes of this cut):")
P(f"       16x block classes {S169_FM_CLASSES}; pooled-48 "
  f"{S169_FM_POOLED_CLS}")
P("       block binding min(m-h): "
  + " / ".join(f4(v) for v in S169_FM_BIND)
  + f" ; pooled-48 {f4(S169_FM_POOLED_BIND)}")
P(f"       block binding min(m-h) min..max {f4(min(S169_FM_BIND))}.."
  f"{f4(max(S169_FM_BIND))}")
P(f"       its letters: C1 ({S169_LETTERS[0]}); C2 ({S169_LETTERS[1]}) at "
  f"fm (254,801); W1 ({S169_LETTERS[2]}); {S169_CUT_VERDICT}")
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
P("     NAMED CROSS-BINARY HAZARD: this cut's binaries are NEW (the")
P("     ROUNDS6400 variant, first-measured digests -- NO committed pin")
P("     to match; c2/c8 reproduce the s169 digests byte-identically --")
P("     a capture observation, not a class claim); any class")
P("     comparison with the committed windows may be BINARY-driven,")
P("     cause UNMEASURED (L2 binds). Every comparison here is")
P("     cross-binary AND cross-point (the point is VIRGIN).")
P("     L8 APPLIES (named): q1 (313, 1,229) is a NEW knob pair of the")
P("     session-21 L8 combination risk class (WORK_MUL != 1 and")
P(f"     NDIV != 1), never measured at any binary before this cut; the")
P(f"     s178 enumeration gives {KS_Q1[4]} in-box same-ratio doubles")
P("     of n=254,679 and NONE is measured this cut (no same-ratio")
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
for win, xd in (("s147", X1_147), ("s158", X1_158), ("s169", X1_169)):
    for t in sorted(xd):
        lo_, hi_, sp, pct, k = xd[t]
        P(f"       {win} {t}: per-run host_ns median min..max {lo_}..{hi_} "
          f"(spread {sp} = {pct}% of min; k={k})")
P("     host_ns is the HOST-side proxy (L3), not a C criterion; any")
P("     excursion is NAMED, NOT HIDDEN and its cause is UNMEASURED.")
P("")

P(f"5. VERDICT SUMMARY: C1 {'(a)' if c1_ok else '(b)'}; C2 {c2_letter} at "
  f"q1 (254,679); W1 {w1_letter}.")
if w1_letter == "(a)":
    P("   CUT VERDICT: THE BRACKET NARROWS TO (254,557, 254,679]")
    P("   (\"THE B=3 CLASS FLIP LIES AT OR BELOW n=254,679\"); the")
    P("   MID-ONLY NARROWING CLAIM is REFUTED BY IMPLICATION (named,")
    P("   not claimed).")
elif w1_letter == "(b)":
    P("   CUT VERDICT: THE BRACKET NARROWS TO (254,679, 255,045]")
    P("   (\"THE B=3 CLASS FLIP LIES ABOVE n=254,679\"); the MID-ONLY")
    P("   NARROWING CLAIM stays SUSPENDED (named, not claimed).")
elif w1_letter == "(c)":
    P("   CUT VERDICT: NOTHING MOVES; the MID-ONLY NARROWING CLAIM stays")
    P("   SUSPENDED (named, not claimed) and is NOT made by this cut.")
else:
    P("   CUT VERDICT: INVALID; NOTHING MOVES.")
if w1_letter == "(a)":
    P("   Bracket state: NARROWED -- (254,557, 254,679].")
elif w1_letter == "(b)":
    P("   Bracket state: NARROWED -- (254,679, 255,045].")
else:
    P("   The committed bracket stays EXACTLY (254,557, 255,045].")
P("   Under ALL outcomes: NO claim at hi, NO claim at lo; no boundary")
P("   between grid points is ever claimed (L5). WHY any class occurs is")
P("   UNMEASURED and NO causal mechanism is claimed (L2 binds). The")
P("   16th cut's fm content at 254,801 and the 14th cut's")
P("   TOLERANCE-UNRESOLVED mid content stand as committed content")
P("   under ALL outcomes (arm (a)); NO letter of this cut supersedes")
P("   them or touches lo/mid/fm.")
P("   BAR NON-INTERFERENCE (frozen protocol): these runs are BISECT")
P("   CONTENT and NOT bar readings -- NO settle-bar-ledger.txt append,")
P("   NO UTC-day slot consumption, NO movement of the bar's SETTLED")
P("   INTERMEDIATE/MIXED verdict (the s117 committed landing), NO Rule")
P("   4 workgroup row movement, NO :measured? flag change (the")
P("   accelerator-targets rows stay exactly as ADR-0358 left them).")

with open(os.path.join(HERE, "publication-s185.txt"), "w") as f:
    f.write("\n".join(out) + "\n")
