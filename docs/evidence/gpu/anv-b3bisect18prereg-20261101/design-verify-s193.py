#!/usr/bin/env python3
# design-verify-s193.py -- JUN-59 session 194: the s193 design-verify
# (the s193 carry-forward, fail-closed quote + arithmetic re-derivation
# vs the committed bytes the state-s193 draft cites).
#
# FAIL-CLOSED: every want is a (file, line number, substring) triple
# checked against the exact committed line, plus file-level size/sha256
# pins, the knob-search-s192 run1==run2 byte-identity, and the pure
# arithmetic re-derivations asserted by the s193 draft (state-s193.txt
# VERIFIED THIS TICK paragraph). ANY missing line, mismatched byte, or
# wrong arithmetic is a hard failure (exit 1).
#
# QUOTE-ONLY / ARITHMETIC-ONLY: this script verifies the s193 draft's
# quotations and arithmetic against committed bytes. It computes NO
# eighteenth-cut quantity -- NO run log, NO class, NO verdict, NO claim.
# Every 18th-cut quantity stays UNMEASURED. RULE 4 unchanged: NOTHING
# MOVES; bracket stays EXACTLY (254,557, 255,045].
import hashlib
import os
import re
import sys
from decimal import Decimal
import math

HERE = os.path.dirname(os.path.abspath(__file__))
GPU = os.path.dirname(HERE)

FILES = {
    "pub185": os.path.join(GPU, "anv-b3bisect17-20261101", "publication-s185.txt"),
    "pub169": os.path.join(GPU, "anv-b3bisect16-20261101", "publication-s169.txt"),
    "pub158": os.path.join(GPU, "anv-b3bisect15-20261101", "publication-s158.txt"),
    "pub139": os.path.join(GPU, "anv-b3bisect13-20261031", "publication-s139.txt"),
    "pub147": os.path.join(GPU, "anv-b3bisect14-20261031", "publication-s147.txt"),
    "spec": os.path.join(GPU, "anv-b3confrontation-spec-20261031", "confrontation-spec.txt"),
    "protocol": os.path.join(GPU, "anv-b3bisect17prereg-20261101", "protocol.txt"),
    "s179": os.path.join(GPU, "anv-b3bisect17prereg-20261101", "state-s179.txt"),
    "ks192": os.path.join(HERE, "knob-search-s192-run1.txt"),
    "ks192r2": os.path.join(HERE, "knob-search-s192-run2.txt"),
}

SHORT = {
    "pub185": "publication-s185.txt",
    "pub169": "publication-s169.txt",
    "pub158": "publication-s158.txt",
    "pub139": "publication-s139.txt",
    "pub147": "publication-s147.txt",
    "spec": "confrontation-spec.txt",
    "protocol": "protocol.txt",
    "s179": "state-s179.txt",
    "ks192": "knob-search-s192-run1.txt",
    "ks192r2": "knob-search-s192-run2.txt",
}

# (id, file key, 1-based line number, exact substring expected on that line)
LINE_WANTS = [
    # -- knob-search-s192-run1.txt (the s192 census, == run2 byte-identically) --
    ("Q-KS-12", "ks192", 12, "(254557, 255045] n-units, width 488"),
    ("Q-KS-21", "ks192", 21, "q3 n=254923: pairs 34; smallest (246, 965); in-box same-ratio doubles 10"),
    ("Q-KS-24", "ks192", 24, "c2 pooled median m 31, deep-pooling class FLOOR (committed floor band 31..32 at B=2): True"),
    ("Q-KS-25", "ks192", 25, "c8 pooled median m 32775 within +/-5% of committed 32915 (session 4 pooled median): True (-0.43%)"),
    ("Q-KS-28", "ks192", 28, "SUPERSEDES the 16th cut's C1 (b) reading AS THE CURRENT CONTROL STATE"),
    ("Q-KS-28b", "ks192", 28, "the discrepancy cause stays UNMEASURED, L2 binds"),
    ("Q-KS-30", "ks192", 30, "12x CAPTURED + 4x IN-BAND-UNDECIDED; pooled-48 class CAPTURED"),
    ("Q-KS-31", "ks192", 31, "999.0012..1002.9224 (16 values), pooled-48 1001.7437"),
    ("Q-KS-32", "ks192", 32, "blocks 1132..1135 (16 values, min..max), pooled-48 1133"),
    ("Q-KS-33a", "ks192", 33, "C2 VERDICT: (c) CLASS-UNRESOLVED"),
    ("Q-KS-33b", "ks192", 33, "L9 binds at 254,679 under the deep-pooling statistic (the D3 (ii) clause)."),
    ("Q-KS-34a", "ks192", 34, "RE-READ HAZARD SECOND EDGE (D3 (ii), verbatim quote PARSED)"),
    ("Q-KS-34b", "ks192", 34, "would re-read, not confront"),
    ("Q-KS-34c", "ks192", 34, "the hazard binds at n=254,679 exactly as frozen"),
    ("Q-KS-36", "ks192", 36, "VERDICT SUMMARY (parsed): C1 (a); C2 (c) at q1 (254679); W1 (c). CUT VERDICT: NOTHING MOVES."),
    ("Q-KS-39", "ks192", 39, "lo n=254,557 dual-class rows [(1156, 'INTERMEDIATE/MIXED', '121'), (1143, 'CAPTURED', '125')]"),
    ("Q-KS-39b", "ks192", 39, "lo tenth-cut pooled-12 median 1141, 18-cell 998..1452, class INTERMEDIATE/MIXED"),
    ("Q-KS-40", "ks192", 40, "mid n=254,882 dual-class rows [(1129, 'INTERMEDIATE/MIXED', '125'), (1133, 'INTERMEDIATE/MIXED', '132'), (1148, 'CAPTURED', '136')]"),
    ("Q-KS-40b", "ks192", 40, "mid pooled-48 median 1140, 18-cell 1001..1442, class CAPTURED"),
    ("Q-KS-41a", "ks192", 41, "16x IN-BAND-UNDECIDED + pooled-48 IN-BAND-UNDECIDED"),
    ("Q-KS-41b", "ks192", 41, "pooled-48 min 1005, pooled-48 median 1148"),
    ("Q-KS-41c", "ks192", 41, "(c) TOLERANCE-UNRESOLVED"),
    ("Q-KS-42", "ks192", 42, "the disputed record is UNCONTESTED between the sources"),
    ("Q-KS-45", "ks192", 45, "block-unit 981..1015; per-run unit 974..1023"),
    ("Q-KS-46", "ks192", 46, "More blocks of the same mixed shape do not confront anything; they re-read it"),
    ("Q-KS-47a", "ks192", 47, "16/16 of the 17th cut's q1 block binding min(m-h) values land inside the block-unit wander band 981..1015"),
    ("Q-KS-47b", "ks192", 47, "the class label equals (binding >= 1,000) at 16/16 blocks"),
    ("Q-KS-47c", "ks192", 47, "999.0012..1002.9224 STRADDLES the 1,000 threshold"),
    ("Q-KS-50", "ks192", 50, "(254557+255045)//2 = 254801"),
    ("Q-KS-53a", "ks192", 53, "floor midpoint (q=2) n=254801: pairs 31; smallest (345, 1354); in-box same-ratio doubles 7"),
    ("Q-KS-53b", "ks192", 53, "'publication-s169.txt': 15, 'publication-s185.txt': 11"),
    ("Q-KS-54a", "ks192", 54, "10x CAPTURED + 3x INTERMEDIATE/MIXED + 3x IN-BAND-UNDECIDED, pooled-48 CAPTURED"),
    ("Q-KS-54b", "ks192", 54, "'this cut does not measure 254,801'"),
    ("Q-KS-55", "ks192", 55, "quarter q=3 n=254923: pairs 34; smallest (246, 965); in-box same-ratio doubles 10; committed-source occurrences {'publication-s139.txt': 0, 'publication-s147.txt': 0, 'publication-s158.txt': 0, 'publication-s169.txt': 0, 'publication-s185.txt': 0}"),
    ("Q-KS-56", "ks192", 56, "RE-DERIVED here: 0 occurrences in every parsed publication source (including publication-s185.txt; the s178 'VIRGIN at s178' state SURVIVES the 17th cut)"),
    ("Q-KS-57", "ks192", 57, "q-fraction (254882 - 254557)/488 = 0.665984"),
    ("Q-KS-61", "ks192", 61, "CENSUS COMPLETE: every asserted want parsed and matched; 0 mismatches."),
    # -- publication-s185.txt (the 17th cut's publication) --
    ("Q-185-81", "pub185", 81, "cut does not measure 254,801; that content stands as committed"),
    ("Q-185-624", "pub185", 624, "c2 (sum,128,S=16) pooled median m 31, deep-pooling"),
    ("Q-185-625", "pub185", 625, "class FLOOR (committed floor band 31..32 at B=2): True"),
    ("Q-185-626", "pub185", 626, "c8 (sum,128,S=16) pooled median m 32775 within +/-5% of committed 32915 (session 4 pooled median): True (-0.43%)"),
    ("Q-185-627", "pub185", 627, "control arms free of VERIFY mismatches (frozen INVALIDATION criterion): True"),
    ("Q-185-631", "pub185", 631, "(a) reading SUPERSEDES the 16th cut's C1 (b) reading AS THE"),
    ("Q-185-632", "pub185", 632, "CURRENT CONTROL STATE (the 16th's (b) remains committed"),
    ("Q-185-633", "pub185", 633, "history; the discrepancy cause stays UNMEASURED, L2 binds)."),
    ("Q-185-636", "pub185", 636, "(BATCH=3,WORK_MUL=313,NDIV=1229) at n=254,679 (knob pair (313,"),
    ("Q-185-637", "pub185", 637, "1,229), the Q=1 QUARTER POINT of the bracket (254,557, 255,045];"),
    ("Q-185-638", "pub185", 638, "the point is VIRGIN -- this cut's content is the FIRST content at"),
    ("Q-185-641a", "pub185", 641, "block classes: ['CAPTURED'"),
    ("Q-185-641b", "pub185", 641, "pooled-48 class: CAPTURED"),
    ("Q-185-642", "pub185", 642, "block binding min(m-h): 1001.9486 / 1000.9749 / 1000.0012"),
    ("Q-185-643", "pub185", 643, "pooled-48 binding min(m-h): 1001.7437"),
    ("Q-185-644a", "pub185", 644, "(sum,128,S=16) m: blocks 1134 / 1135 / 1135 / 1134"),
    ("Q-185-644b", "pub185", 644, "pooled-48 1133"),
    ("Q-185-645", "pub185", 645, "(c) CLASS-UNRESOLVED: mixed block classes, or any"),
    ("Q-185-647", "pub185", 647, "L9 binds at n=254,679 under the deep-pooling statistic (the"),
    ("Q-185-651", "pub185", 651, "edge, D3 (ii), verbatim): if this cut's own content at"),
    ("Q-185-652", "pub185", 652, "254,679 comes out mixed (C2 (c)), it is NOT rescued by later"),
    ("Q-185-653", "pub185", 653, "more-blocks-of-the-same-shape runs; a same-shape re-run"),
    ("Q-185-654", "pub185", 654, "there would re-read, not confront."),
    ("Q-185-672", "pub185", 672, "(c) C2 (c)/(d) -> NOTHING MOVES; the bracket stays EXACTLY"),
    ("Q-185-673", "pub185", 673, "(254,557, 255,045]; the MID-ONLY NARROWING CLAIM stays"),
    ("Q-185-674", "pub185", 674, "SUSPENDED (named, not claimed)."),
    # -- publication-s169.txt (the 16th cut's publication) --
    ("Q-169-615", "pub169", 615, "(BATCH=3,WORK_MUL=345,NDIV=1354) at n=254,801 (knob pair (345,"),
    ("Q-169-620a", "pub169", 620, "block classes: ['CAPTURED'"),
    ("Q-169-620b", "pub169", 620, "pooled-48 class: CAPTURED"),
    ("Q-169-621", "pub169", 621, "block binding min(m-h): 1004.8961 / 1006.7909 / 1005.8172"),
    ("Q-169-624", "pub169", 624, "(c) CLASS-UNRESOLVED: mixed block classes, or any"),
    ("Q-169-626", "pub169", 626, "L9 binds at 254,801 under the deep-pooling statistic; any"),
    # -- publication-s158.txt (the 15th cut's publication) --
    ("Q-158-135", "pub158", 135, "anv-bb-bis 52fb68b66b550f0029c50b8695e13ecdcfcd736831e42cc3bccdb9b6f5bf14a8"),
    ("Q-158-646", "pub158", 646, "block binding min(m-h): 1006.8172 / 1005.8172 / 1006.7909 / 1005.8435"),
    ("Q-158-647", "pub158", 647, "pooled-48 binding min(m-h): 1009.6912"),
    ("Q-158-649", "pub158", 649, "(b) STABLE-CAPTURED: all 16 blocks AND the pooled-48 arm"),
    ("Q-158-712", "pub158", 712, "n=254557: 1156 INTERMEDIATE/MIXED (session 121)"),
    ("Q-158-713", "pub158", 713, "n=254557: 1143 CAPTURED (session 125)"),
    ("Q-158-714", "pub158", 714, "n=254882: 1129 INTERMEDIATE/MIXED (session 125)"),
    ("Q-158-715", "pub158", 715, "n=254882: 1133 INTERMEDIATE/MIXED (session 132)"),
    ("Q-158-716", "pub158", 716, "n=254882: 1148 CAPTURED (session 136)"),
    ("Q-158-717", "pub158", 717, "lo pooled-12 1141 INTERMEDIATE/MIXED; mid pooled-48 1140 CAPTURED"),
    ("Q-158-718", "pub158", 718, "the named cross-window disagreement at cabff942...: s132"),
    ("Q-158-719", "pub158", 719, "pooled-24 1133 INTERMEDIATE/MIXED vs s136"),
    ("Q-158-720", "pub158", 720, "pooled-24 1148 CAPTURED vs s139"),
    ("Q-158-721", "pub158", 721, "pooled-48 1140 CAPTURED vs s147"),
    ("Q-158-722", "pub158", 722, "pooled-48 1148 CAPTURED (the"),
    # -- publication-s139.txt / publication-s147.txt (the disputed record's primary sources) --
    ("Q-139-86", "pub139", 86, "pooled-12 median 1141 18-cell 998..1452 INTERMEDIATE/MIXED"),
    ("Q-139-270a", "pub139", 270, "1140   18-cell   1001..1442"),
    ("Q-139-270b", "pub139", 270, "CAPTURED"),
    ("Q-139-380a", "pub139", 380, "1156  INTERMEDIATE/MIXED"),
    ("Q-139-380b", "pub139", 380, "session 121 (the eighth cut)"),
    ("Q-139-381a", "pub139", 381, "1143  CAPTURED"),
    ("Q-139-381b", "pub139", 381, "session 125 (the ninth cut, lo)"),
    ("Q-139-382a", "pub139", 382, "1129  INTERMEDIATE/MIXED"),
    ("Q-139-382b", "pub139", 382, "session 125 (the ninth cut, mid)"),
    ("Q-139-391a", "pub139", 391, "1133  INTERMEDIATE/MIXED"),
    ("Q-139-391b", "pub139", 391, "session 132 (the eleventh cut, pooled-24"),
    ("Q-139-393a", "pub139", 393, "1148  CAPTURED"),
    ("Q-139-393b", "pub139", 393, "session 136 (the twelfth cut, pooled-24"),
    ("Q-147-284a", "pub147", 284, "1148   18-cell   1005..1428"),
    ("Q-147-284b", "pub147", 284, "frozen-rule CAPTURED"),
    ("Q-147-284c", "pub147", 284, "tolerance IN-BAND-UNDECIDED"),
    ("Q-147-310a", "pub147", 310, "(sum,128,S=16): blocks 1144 / 1170 / 1138"),
    ("Q-147-310b", "pub147", 310, "pooled-48 1148"),
    ("Q-147-311", "pub147", 311, "(c) TOLERANCE-UNRESOLVED: any in-band minimum or mixed"),
    ("Q-147-363a", "pub147", 363, "block 18-cell minima: 992 / 1006 / 996"),
    ("Q-147-363b", "pub147", 363, "pooled-48 min 1005"),
    # -- confrontation-spec.txt (accepted design only) --
    ("Q-SP-59", "spec", 59, "981..1,015 (census); per-run unit (descriptive, s139 W2): 974..1,023."),
    ("Q-SP-100", "spec", 100, "More blocks of the same mixed shape do"),
    ("Q-SP-101", "spec", 101, "not confront anything; they re-read it."),
    ("Q-SP-116", "spec", 116, "block-unit 981..1,015; per-run unit 974..1,023"),
    ("Q-SP-123", "spec", 123, "A statistic chosen after the runs are read is never a confrontation."),
    ("Q-SP-128", "spec", 128, "The MID-ONLY NARROWING CLAIM stays SUSPENDED until a"),
    ("Q-SP-129", "spec", 129, "claim passes (a)-(c) at mid and confronts (d)"),
    # -- protocol.txt (the 17th cut's FROZEN protocol; the adopted source pin) --
    ("Q-PR-88", "protocol", 88, "ROUNDS6400 instrument variant; the measuring session records"),
    ("Q-PR-124", "protocol", 124, "c2704aaad6bfeeae1f4f9cfa916d0160efb03926892237554c7dffc8"),
    ("Q-PR-125", "protocol", 125, "386e84e0 (adopted UNCHANGED from the s166 freeze; re-"),
    # -- state-s179.txt (the D3 (ii) conditional, named at the 17th cut's draft) --
    ("Q-S179-132", "s179", 132, "is named: if this cut's own content at 254,679 comes"),
    ("Q-S179-133", "s179", 133, "out mixed (C2 (c)), it is NOT rescued by later"),
    ("Q-S179-136", "s179", 136, "must confront this cut's content first -- named here,"),
    ("Q-S179-137", "s179", 137, "not specified here\") and a same-shape re-run there"),
    ("Q-S179-138", "s179", 138, "would re-read, not confront."),
]

# (id, file key, expected size in bytes, expected sha256 hex)
FILE_PINS = [
    ("F-PUB185", "pub185", 59777,
     "c62c01e17a045933782cc3fb8c67e452ae0f35a513ad1f396a9dea08834d6d34"),
    ("F-PUB169", "pub169", 56352,
     "c9aab750fd20120b3abe8db6e9cac554b6c8ea0fbb1b37d9169d1539e4ff7687"),
    ("F-PUB158", "pub158", 56588,
     "45538ad757bfa28821de2728000581897aaef8cc75f32ed656914509f400cd25"),
    ("F-PUB139", "pub139", 33345,
     "b6eb79cb397ae6b9ee6f502fee3b3e70c7d9cbbbe1e3b21c00ae126a3ac3092c"),
    ("F-PUB147", "pub147", 29876,
     "d41df35aff0a0ff674549a9f4390752be27f28f71cce90dfdf54bb1b08d407aa"),
    ("F-SPEC", "spec", 9660,
     "c0eff7fb0a5997658c94c7be36f776229d29aabe99f4f96be6ebb48c821d5ec7"),
    ("F-PROTOCOL", "protocol", 19974,
     "ad8ace961cf6eca9f1e68752b9fba89861806a8161fbaec5448c7654a74cf6fb"),
    ("F-S179", "s179", 19949,
     "a165e8c38649c8d2585674c5c60aa99e340191071c01e5011e0441f8389c7a69"),
    ("F-KS192", "ks192", 9477,
     "78fe5a96517ce7a7126b6534b03d702230a84bebad9c3e2772bc8fccd77b43f9"),
]

# (id, description, computed string, expected string) -- the state-s193
# VERIFIED THIS TICK paragraph arithmetic, re-derived here.
ARITH_WANTS = [
    ("A-KNOB-Q3", "knob arithmetic (1,000,003*246)//965",
     str((1000003 * 246) // 965), "254923"),
    ("A-GCD-Q3", "gcd(246, 965)",
     str(math.gcd(246, 965)), "1"),
    ("A-KNOB-Q1", "knob arithmetic (1,000,003*313)//1,229",
     str((1000003 * 313) // 1229), "254679"),
    ("A-FMID", "floor midpoint (254557+255045)//2",
     str((254557 + 255045) // 2), "254801"),
    ("A-WIDTH", "bracket width 255045-254557",
     str(255045 - 254557), "488"),
    ("A-Q1-GRID", "quarter grid q=1: 254557 + 488//4",
     str(254557 + 488 // 4), "254679"),
    ("A-Q3-GRID", "quarter grid q=3: 254557 + 3*(488//4)",
     str(254557 + 3 * (488 // 4)), "254923"),
    ("A-MID-QFRAC", "mid q-fraction (254882-254557)/488 to 6 dp",
     str((Decimal(254882 - 254557) / Decimal(488)).quantize(Decimal("0.000001"))),
     "0.665984"),
    ("A-ARM-TABLE", "arm table self-check 3+48+3",
     str(3 + 48 + 3), "54"),
    ("A-Q1-SPREAD", "q1 binding spread 1002.9224-999.0012",
     str(Decimal("1002.9224") - Decimal("999.0012")), "3.9212"),
    ("A-FM-SPREAD", "fm binding spread 1006.7909-997.0538",
     str(Decimal("1006.7909") - Decimal("997.0538")), "9.7371"),
    ("A-BIS-SPREAD", "bis binding spread 1008.7909-1005.8172",
     str(Decimal("1008.7909") - Decimal("1005.8172")), "2.9737"),
    ("A-BAND-WIDTH", "wander band width 1015-981",
     str(1015 - 981), "34"),
    ("A-TOP-CLIP", "255,045 - 254,923 (q=3 top clip)",
     str(255045 - 254923), "122"),
    ("A-LOW-CLIP", "254,923 - 254,557 (q=3 low clip)",
     str(254923 - 254557), "366"),
]


def line_of(texts, key, lineno):
    return texts[key].split(b"\n")[lineno - 1].decode("utf-8")


def parse_binding_list(line):
    after = line.split("block binding min(m-h):", 1)[1]
    return [Decimal(v.strip()) for v in after.split("/")]


def parse_class_list(line):
    body = line.split("block classes:", 1)[1].split("; pooled-48 class:")[0]
    return re.findall(r"'([A-Z/-]+)'", body)


def main():
    ok = 0
    failed = 0
    texts = {}
    for key, path in sorted(FILES.items()):
        with open(path, "rb") as f:
            texts[key] = f.read()

    def record(want_id, detail, good):
        nonlocal ok, failed
        if good:
            ok += 1
            print("ok   %s  %s" % (want_id, detail))
        else:
            failed += 1
            print("FAIL %s  %s" % (want_id, detail))

    print("== DESIGN-VERIFY S193 (session 194) ==")
    print("== fail-closed quote + arithmetic re-derivation vs committed bytes ==")
    print("== QUOTE-ONLY / ARITHMETIC-ONLY: NO 18th-cut quantity is computed ==")
    print()

    # 1. file-level pins (size + sha256)
    for want_id, key, size, sha in FILE_PINS:
        got = texts[key]
        got_sha = hashlib.sha256(got).hexdigest()
        detail = "%s size %d sha256 %s" % (SHORT[key], len(got), got_sha)
        record(want_id, detail, len(got) == size and got_sha == sha)

    # 2. knob-search-s192 run1 == run2 byte-identity
    same = texts["ks192"] == texts["ks192r2"]
    record("F-KS192-PAIR",
           "knob-search-s192-run1.txt == knob-search-s192-run2.txt byte-identity",
           same)

    # 3. line-pinned quote wants
    for want_id, key, lineno, substr in LINE_WANTS:
        lines = texts[key].split(b"\n")
        good = lineno <= len(lines) and substr.encode("utf-8") in lines[lineno - 1]
        detail = "%s:%d contains %r" % (SHORT[key], lineno, substr)
        record(want_id, detail, good)

    # 4. arithmetic re-derivations (state-s193 VERIFIED THIS TICK paragraph)
    for want_id, desc, computed, expected in ARITH_WANTS:
        detail = "%s -> %s (expected %s)" % (desc, computed, expected)
        record(want_id, detail, computed == expected)

    # 5. derived re-computation from committed bytes (the s193 draft's
    #    quoted values re-derived from the published row lines)
    q1_classes = parse_class_list(line_of(texts, "pub185", 641))
    q1_bind = parse_binding_list(line_of(texts, "pub185", 642))
    q1_pooled = Decimal(line_of(texts, "pub185", 643)
                        .split("pooled-48 binding min(m-h):", 1)[1].strip())
    fm_bind = parse_binding_list(line_of(texts, "pub169", 621))
    bis_bind = parse_binding_list(line_of(texts, "pub158", 646))
    bis_pooled = Decimal(line_of(texts, "pub158", 647)
                         .split("pooled-48 binding min(m-h):", 1)[1].strip())

    q1_cap = sum(1 for c in q1_classes if c == "CAPTURED")
    q1_inb = sum(1 for c in q1_classes if c == "IN-BAND-UNDECIDED")
    record("D-Q1-CLASSES",
           "pub185:641 classes re-counted: %d total, %d CAPTURED, %d IN-BAND-UNDECIDED (want 16/12/4)"
           % (len(q1_classes), q1_cap, q1_inb),
           len(q1_classes) == 16 and q1_cap == 12 and q1_inb == 4)

    ride = all((b >= 1000) == (c == "CAPTURED")
               for b, c in zip(q1_bind, q1_classes))
    record("D-Q1-CLASS-RIDE",
           "pub185:641/642 class == (binding >= 1000) at 16/16 blocks: %s" % ride,
           ride and len(q1_bind) == 16)

    record("D-Q1-SPREAD",
           "pub185:642 binding min %s max %s spread %s (want 999.0012/1002.9224/3.9212)"
           % (min(q1_bind), max(q1_bind), max(q1_bind) - min(q1_bind)),
           min(q1_bind) == Decimal("999.0012")
           and max(q1_bind) == Decimal("1002.9224")
           and max(q1_bind) - min(q1_bind) == Decimal("3.9212"))

    inband = all(Decimal("981") <= b <= Decimal("1015") for b in q1_bind)
    straddle = min(q1_bind) < 1000 < max(q1_bind)
    record("D-Q1-INBAND-STRADDLE",
           "pub185:642 16/16 in 981..1015: %s; range STRADDLES 1,000: %s"
           % (inband, straddle),
           inband and straddle and len(q1_bind) == 16)

    record("D-Q1-POOLED",
           "pub185:643 pooled-48 binding %s (want 1001.7437)" % q1_pooled,
           q1_pooled == Decimal("1001.7437"))

    record("D-FM-SPREAD",
           "pub169:621 binding min %s max %s spread %s (want 997.0538/1006.7909/9.7371)"
           % (min(fm_bind), max(fm_bind), max(fm_bind) - min(fm_bind)),
           min(fm_bind) == Decimal("997.0538")
           and max(fm_bind) == Decimal("1006.7909")
           and max(fm_bind) - min(fm_bind) == Decimal("9.7371"))

    record("D-BIS-SPREAD",
           "pub158:646 binding min %s max %s spread %s (want 1005.8172/1008.7909/2.9737)"
           % (min(bis_bind), max(bis_bind), max(bis_bind) - min(bis_bind)),
           min(bis_bind) == Decimal("1005.8172")
           and max(bis_bind) == Decimal("1008.7909")
           and max(bis_bind) - min(bis_bind) == Decimal("2.9737"))

    record("D-BIS-POOLED",
           "pub158:647 pooled-48 binding %s (want 1009.6912)" % bis_pooled,
           bis_pooled == Decimal("1009.6912"))

    m_line = line_of(texts, "pub185", 644)
    m_vals = [int(v.strip()) for v in
              m_line.split("m: blocks", 1)[1].split(";")[0].split("/")]
    m_pooled = int(m_line.split("pooled-48", 1)[1].strip())
    record("D-Q1-M",
           "pub185:644 block m min %d max %d pooled %d (want 1132/1135/1133)"
           % (min(m_vals), max(m_vals), m_pooled),
           len(m_vals) == 16 and min(m_vals) == 1132
           and max(m_vals) == 1135 and m_pooled == 1133)

    print()
    print("DESIGN-VERIFY S193 SUMMARY: %d ok / %d failed" % (ok, failed))
    if failed == 0:
        print("DESIGN-VERIFY S193 COMPLETE (fail-closed: 0 failed)")
        return 0
    print("DESIGN-VERIFY S193 FAILED (fail-closed)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
