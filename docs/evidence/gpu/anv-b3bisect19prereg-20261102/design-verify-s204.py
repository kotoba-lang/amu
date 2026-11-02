#!/usr/bin/env python3
# design-verify-s204.py -- JUN-59 session 205: the s204 design-verify
# (the s205 carry-forward, fail-closed quote + arithmetic re-derivation
# vs the committed bytes the state-s204 draft cites).
#
# FAIL-CLOSED: every want is a (file, line number, substring) triple
# checked against the exact committed line, plus file-level size/sha256
# pins, the knob-search-s203 run1==run2 byte-identity, the pure
# arithmetic re-derivations asserted by the state-s204 draft (its
# VERIFIED THIS TICK paragraph), derived re-computations FROM COMMITTED
# BYTES, and the W1 (a)/(b) per-outcome bracket-width geometry (D1 (2))
# re-derived from the committed W1 letter shapes. ANY missing line,
# mismatched byte, wrong arithmetic or incoherent letter assignment is
# a hard failure (exit 1).
#
# QUOTE-ONLY / ARITHMETIC-ONLY: this script verifies the s204 draft's
# quotations and arithmetic against committed bytes. It computes NO
# nineteenth-cut quantity -- NO run log, NO class, NO verdict, NO claim.
# Every 19th-cut quantity stays UNMEASURED. RULE 4 unchanged: NOTHING
# MOVES; bracket stays EXACTLY (254,923, 255,045].
import hashlib
import os
import re
import sys
from decimal import Decimal
import math

HERE = os.path.dirname(os.path.abspath(__file__))
GPU = os.path.dirname(HERE)

FILES = {
    "ks203": os.path.join(HERE, "knob-search-s203-run1.txt"),
    "ks203r2": os.path.join(HERE, "knob-search-s203-run2.txt"),
    "pub197": os.path.join(GPU, "anv-b3bisect18-20261101", "publication-s197.txt"),
    "pub158": os.path.join(GPU, "anv-b3bisect15-20261101", "publication-s158.txt"),
    "pub139": os.path.join(GPU, "anv-b3bisect13-20261031", "publication-s139.txt"),
    "pub147": os.path.join(GPU, "anv-b3bisect14-20261031", "publication-s147.txt"),
    "pub185": os.path.join(GPU, "anv-b3bisect17-20261101", "publication-s185.txt"),
    "pub169": os.path.join(GPU, "anv-b3bisect16-20261101", "publication-s169.txt"),
    "spec": os.path.join(GPU, "anv-b3confrontation-spec-20261031", "confrontation-spec.txt"),
    "pr18": os.path.join(GPU, "anv-b3bisect18prereg-20261101", "protocol.txt"),
    "s179": os.path.join(GPU, "anv-b3bisect17prereg-20261101", "state-s179.txt"),
    "s193": os.path.join(GPU, "anv-b3bisect18prereg-20261101", "state-s193.txt"),
    "s203": os.path.join(HERE, "state-s203.txt"),
    "s204": os.path.join(HERE, "state-s204.txt"),
}

SHORT = {
    "ks203": "knob-search-s203-run1.txt",
    "ks203r2": "knob-search-s203-run2.txt",
    "pub197": "publication-s197.txt",
    "pub158": "publication-s158.txt",
    "pub139": "publication-s139.txt",
    "pub147": "publication-s147.txt",
    "pub185": "publication-s185.txt",
    "pub169": "publication-s169.txt",
    "spec": "confrontation-spec.txt",
    "pr18": "anv-b3bisect18prereg-20261101/protocol.txt",
    "s179": "state-s179.txt",
    "s193": "state-s193.txt",
    "s203": "state-s203.txt",
    "s204": "state-s204.txt",
}

# (id, file key, 1-based line number, exact substring expected on that line)
LINE_WANTS = [
    # -- knob-search-s203-run1.txt (the s203 census, == run2 byte-identically) --
    ("Q-KS-12", "ks203", 12, "(254923, 255045] n-units, width 122"),
    ("Q-KS-17", "ks203", 17, "fm n=254801: pairs 31; smallest (345, 1354); in-box same-ratio doubles 7"),
    ("Q-KS-21", "ks203", 21, "q3 n=254923: pairs 34; smallest (246, 965); in-box same-ratio doubles 10"),
    ("Q-KS-24", "ks203", 24, "lo n=254923 (the NEW lower endpoint; the 18th cut's cut point): pairs 34; smallest (246, 965); in-box same-ratio doubles 10"),
    ("Q-KS-25a", "ks203", 25, "hi n=255045 (the NEW upper endpoint; bis (3, 316, 1,239)): pairs 33; smallest (316, 1239); in-box same-ratio doubles 8"),
    ("Q-KS-25b", "ks203", 25, "the 8 in-box same-ratio doubles are FRESH"),
    ("Q-KS-28", "ks203", 28, "C1: c2 pooled median m 31, deep-pooling class FLOOR (committed floor band 31..32 at B=2): True"),
    ("Q-KS-29", "ks203", 29, "C1: c8 pooled median m 32778 within +/-5% of committed 32915 (session 4 pooled median): True (-0.42%)"),
    ("Q-KS-30", "ks203", 30, "C1: control arms free of VERIFY mismatches (frozen INVALIDATION criterion): True"),
    ("Q-KS-32", "ks203", 32, "the current control state (the 17th cut's C1 (a)) REPLICATES at back-to-back cuts -- no supersession needed"),
    ("Q-KS-33", "ks203", 33, "C2: q3 (BATCH=3,WORK_MUL=246,NDIV=965) at n=254923 -- knob arithmetic (1,000,003*246)//965 = 254923"),
    ("Q-KS-34", "ks203", 34, "C2 block classes (re-count COMPUTED here): 16x INTERMEDIATE/MIXED; pooled-48 class INTERMEDIATE/MIXED"),
    ("Q-KS-35", "ks203", 35, "C2 block binding min(m-h): 995.1326..998.0538 (16 values), pooled-48 997.7700"),
    ("Q-KS-36", "ks203", 36, "C2 (sum,128,S=16) m: blocks 1131..1132 (16 values, min..max), pooled-48 1132"),
    ("Q-KS-37", "ks203", 37, "C2 VERDICT: (a) STABLE-INTERMEDIATE: all 16 blocks AND the pooled-48 arm class INTERMEDIATE/MIXED -- PASSES the 16-block class-stability requirement at q3 under the deep-pooling statistic"),
    ("Q-KS-38", "ks203", 38, "WHY any class occurs is UNMEASURED (L2 binds)"),
    ("Q-KS-39", "ks203", 39, "W1 letters (parsed): C1 (control replication): (a); C2 (q3 class stability): (a); W1 (b)."),
    ("Q-KS-40", "ks203", 40, "W1 (b) text PARSED: (b) C2 (a) -> THE BRACKET NARROWS TO (254,923, 255,045]"),
    ("Q-KS-41", "ks203", 41, "the lower endpoint moved 254,557 -> 254,923"),
    ("Q-KS-42", "ks203", 42, "the top clip 255,045-254,923 = 122; the low clip 254,923-254,557 = 366"),
    ("Q-KS-43", "ks203", 43, "W3: NAMED CROSS-BINARY HAZARD quote PARSED (the q3 binary is NEW first-measured ROUNDS6400 variant"),
    ("Q-KS-44", "ks203", 44, "the s192 enumeration gives 10 in-box same-ratio doubles of n=254,923 and NONE is measured this cut"),
    ("Q-KS-45", "ks203", 45, "q3 per-run host_ns median min..max 309798..503223.5 (spread 193425.5 = 62.4% of min; k=48)"),
    ("Q-KS-46", "ks203", 46, "VERDICT SUMMARY (parsed): C1 (a); C2 (a) at q3 (254923); W1 (b). CUT VERDICT: THE BRACKET NARROWS TO (254,923, 255,045]"),
    ("Q-KS-49", "ks203", 49, "PRIMARY (publication-s139.txt): lo n=254,557 dual-class rows [(1156, 'INTERMEDIATE/MIXED', '121'), (1143, 'CAPTURED', '125')]; lo tenth-cut pooled-12 median 1141, 18-cell 998..1452, class INTERMEDIATE/MIXED"),
    ("Q-KS-50", "ks203", 50, "mid n=254,882 dual-class rows [(1129, 'INTERMEDIATE/MIXED', '125'), (1133, 'INTERMEDIATE/MIXED', '132'), (1148, 'CAPTURED', '136')]; mid pooled-48 median 1140, 18-cell 1001..1442, class CAPTURED"),
    ("Q-KS-51a", "ks203", 51, "PRIMARY (publication-s147.txt): 14th cut mid content -- 16x IN-BAND-UNDECIDED + pooled-48 IN-BAND-UNDECIDED"),
    ("Q-KS-51b", "ks203", 51, "(c) TOLERANCE-UNRESOLVED: any in-band minimum or mixed classes -- FAILS"),
    ("Q-KS-52", "ks203", 52, "the disputed record is UNCONTESTED between the sources"),
    ("Q-KS-55", "ks203", 55, "measured wander band (spec, parsed): block-unit 981..1015; per-run unit 974..1023"),
    ("Q-KS-56", "ks203", 56, "spec section 1 (i) bis content pin PARSED: bis (3,316,1239) n=255,045 at binary 440604ef... -- 7x CAPTURED + 9x INTERMEDIATE/MIXED blocks, pooled-48 CAPTURED 1,148"),
    ("Q-KS-57", "ks203", 57, "arm-(b) re-read hazard quote 'More blocks of the same mixed shape do not confront anything; they re-read it' PARSED"),
    ("Q-KS-58a", "ks203", 58, "16/16 of the 18th cut's q3 block binding min(m-h) values land inside the block-unit wander band 981..1015"),
    ("Q-KS-58b", "ks203", 58, "0/16 >= the frozen 1,000-tick threshold"),
    ("Q-KS-61", "ks203", 61, "floor midpoint re-derivation: (254923+255045)//2 = 254984"),
    ("Q-KS-62", "ks203", 62, "quarter q=1 n=254953: pairs 31; smallest (296, 1161); in-box same-ratio doubles 8"),
    ("Q-KS-63", "ks203", 63, "n=254953 is VIRGIN after the eighteenth cut"),
    ("Q-KS-64", "ks203", 64, "floor midpoint (q=2) n=254984: pairs 29; smallest (307, 1204); in-box same-ratio doubles 6"),
    ("Q-KS-65", "ks203", 65, "n=254984 is VIRGIN after the eighteenth cut -- RE-DERIVED here: 0 occurrences in every parsed publication source (including publication-s197.txt) AND in both knob-search captures"),
    ("Q-KS-66", "ks203", 66, "quarter q=3 n=255014: pairs 25; smallest (674, 2643); in-box same-ratio doubles 4"),
    ("Q-KS-67", "ks203", 67, "n=255014 is VIRGIN after the eighteenth cut"),
    ("Q-KS-68", "ks203", 68, "'publication-s185.txt': 0, 'publication-s197.txt': 26}"),
    ("Q-KS-69", "ks203", 69, "NAMED, NOT HIDDEN: what binds at 254,923 for a future same-shape re-run is a DESIGN QUESTION (the frozen 'mixed at q3' second-edge shape did NOT fire on (a) content)"),
    ("Q-KS-70a", "ks203", 70, "upper endpoint hi n=255045 (the NEW upper endpoint; bis (3, 316, 1,239))"),
    ("Q-KS-70b", "ks203", 70, "{'publication-s139.txt': 10, 'publication-s147.txt': 5, 'publication-s158.txt': 16, 'publication-s169.txt': 8, 'publication-s185.txt': 10, 'publication-s197.txt': 13}"),
    ("Q-KS-71a", "ks203", 71, "the 13th cut's content stands at this point (publication-s139.txt VERDICT SUMMARY 'C1 (a); C2 (c) at bis (255,045); C3 (c) at mid; W1 (c)'"),
    ("Q-KS-71b", "ks203", 71, "AND the 15th cut's re-measure at its NEW binary 52fb68b6... (publication-s158.txt: 16x CAPTURED blocks, pooled-48 class CAPTURED, pooled binding 1009.6912, (b) STABLE-CAPTURED"),
    ("Q-KS-71c", "ks203", 71, "publication-s139.txt carries NO 'C2 (b)' at all"),
    ("Q-KS-72", "ks203", 72, "interior committed point mid (248, 973) n=254882 is NOT on the new quarter grid"),
    ("Q-KS-78", "ks203", 78, "CENSUS COMPLETE: every asserted want parsed and matched; 0 mismatches."),
    # -- publication-s197.txt (the 18th cut's publication) --
    ("Q-197-33", "pub197", 33, "c2 b791b71a... q3 c7ba9c86... c8 2f25d678..."),
    ("Q-197-85", "pub197", 85, "cut does not measure 254,679; that content stands as committed"),
    ("Q-197-130", "pub197", 130, "anv-bb-q3 c7ba9c864a356de95fff67ce7a997c30af99cd7b7626da4894b8c0077c65d76b"),
    ("Q-197-637", "pub197", 637, "the current control state (the 17th cut's C1 (a)) REPLICATES"),
    ("Q-197-638", "pub197", 638, "at back-to-back cuts -- no supersession needed (the 17th"),
    ("Q-197-642", "pub197", 642, "(BATCH=3,WORK_MUL=246,NDIV=965) at n=254,923 (knob pair (246,"),
    ("Q-197-643", "pub197", 643, "965), the Q=3 QUARTER POINT of the bracket (254,557, 255,045];"),
    ("Q-197-647", "pub197", 647, "pooled-48 class: INTERMEDIATE/MIXED"),
    ("Q-197-648", "pub197", 648, "block binding min(m-h): 997.1063 / 997.0801 / 996.0801"),
    ("Q-197-649", "pub197", 649, "pooled-48 binding min(m-h): 997.7700"),
    ("Q-197-650", "pub197", 650, "(sum,128,S=16) m: blocks 1132 / 1132 / 1132 / 1132 / 1132 / 1132 / 1132 / 1131"),
    ("Q-197-651", "pub197", 651, "(a) STABLE-INTERMEDIATE: all 16 blocks AND the pooled-48 arm"),
    ("Q-197-673", "pub197", 673, "(\"THE B=3 CLASS FLIP LIES ABOVE n=254,923\"); the MID-ONLY"),
    ("Q-197-688", "pub197", 688, "n-units: the top clip 255,045-254,923 = 122; the low clip"),
    ("Q-197-730", "pub197", 730, "block binding min(m-h) min..max 999.0012..1002.9224"),
    ("Q-197-753", "pub197", 753, "block binding min(m-h) min..max 1005.8172..1008.7909"),
    ("Q-197-764", "pub197", 764, "s192 enumeration gives 10 in-box same-ratio doubles"),
    ("Q-197-772", "pub197", 772, "q3: per-run host_ns median min..max 309798..503223.5 (spread 193425.5 = 62.4% of min; k=48)"),
    ("Q-197-790", "pub197", 790, "5. VERDICT SUMMARY: C1 (a); C2 (a) at q3 (254,923); W1 (b)."),
    ("Q-197-791", "pub197", 791, "CUT VERDICT: THE BRACKET NARROWS TO (254,923, 255,045]"),
    ("Q-197-792", "pub197", 792, "(\"THE B=3 CLASS FLIP LIES ABOVE n=254,923\"); the MID-ONLY"),
    # -- publication-s158.txt (the 15th cut's publication) --
    ("Q-158-135", "pub158", 135, "anv-bb-bis 52fb68b66b550f0029c50b8695e13ecdcfcd736831e42cc3bccdb9b6f5bf14a8"),
    ("Q-158-647", "pub158", 647, "pooled-48 binding min(m-h): 1009.6912"),
    ("Q-158-649", "pub158", 649, "(b) STABLE-CAPTURED: all 16 blocks AND the pooled-48 arm"),
    ("Q-158-703", "pub158", 703, "this cut's bis block min(m-h): 1006.8172 / 1005.8172 / 1006.7909 / 1005.8435"),
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
    ("Q-158-742", "pub158", 742, "5. VERDICT SUMMARY: C1 (a); C2 (b) at bis (255,045); W1 (a)."),
    # -- publication-s139.txt / publication-s147.txt (the disputed record's primary sources) --
    ("Q-139-86", "pub139", 86, "pooled-12 median 1141 18-cell 998..1452 INTERMEDIATE/MIXED"),
    ("Q-139-270", "pub139", 270, "1140   18-cell   1001..1442     CAPTURED"),
    ("Q-139-380", "pub139", 380, "1156  INTERMEDIATE/MIXED   session 121 (the eighth cut)"),
    ("Q-139-381", "pub139", 381, "1143  CAPTURED             session 125 (the ninth cut, lo)"),
    ("Q-139-382", "pub139", 382, "1129  INTERMEDIATE/MIXED   session 125 (the ninth cut, mid)"),
    ("Q-139-391", "pub139", 391, "1133  INTERMEDIATE/MIXED   session 132 (the eleventh cut"),
    ("Q-139-393", "pub139", 393, "1148  CAPTURED             session 136 (the twelfth cut"),
    ("Q-139-421", "pub139", 421, "5. VERDICT SUMMARY: C1 (a); C2 (c) at bis (255,045); C3 (c) at mid; W1 (c)."),
    ("Q-147-284", "pub147", 284, "1148   18-cell   1005..1428     frozen-rule CAPTURED             tolerance IN-BAND-UNDECIDED"),
    ("Q-147-310a", "pub147", 310, "(sum,128,S=16): blocks 1144 / 1170 / 1138"),
    ("Q-147-310b", "pub147", 310, "pooled-48 1148"),
    ("Q-147-311", "pub147", 311, "(c) TOLERANCE-UNRESOLVED: any in-band minimum or mixed"),
    ("Q-147-363a", "pub147", 363, "block 18-cell minima: 992 / 1006 / 996 / 1000 / 1002 / 993 / 1002 / 991"),
    ("Q-147-363b", "pub147", 363, "pooled-48 min 1005"),
    # -- publication-s185.txt / publication-s169.txt (the 17th/16th cut content the D4 rationale cites) --
    ("Q-185-81", "pub185", 81, "cut does not measure 254,801; that content stands as committed"),
    ("Q-185-642", "pub185", 642, "block binding min(m-h): 1001.9486 / 1000.9749 / 1000.0012"),
    ("Q-185-643", "pub185", 643, "pooled-48 binding min(m-h): 1001.7437"),
    ("Q-169-615", "pub169", 615, "(BATCH=3,WORK_MUL=345,NDIV=1354) at n=254,801 (knob pair (345,"),
    ("Q-169-621", "pub169", 621, "block binding min(m-h): 1004.8961 / 1006.7909 / 1005.8172"),
    # -- confrontation-spec.txt (accepted design only) --
    ("Q-SP-39", "spec", 39, "(18-cell 1,001..1,442). bis (3,316,1239) n=255,045 at binary"),
    ("Q-SP-40", "spec", 40, "440604ef... -- 7x CAPTURED + 9x INTERMEDIATE/MIXED blocks, block"),
    ("Q-SP-59", "spec", 59, "981..1,015 (census); per-run unit (descriptive, s139 W2): 974..1,023."),
    ("Q-SP-100", "spec", 100, "at this granularity or finer. More blocks of the same mixed shape do"),
    ("Q-SP-101", "spec", 101, "not confront anything; they re-read it."),
    ("Q-SP-116", "spec", 116, "(block-unit 981..1,015; per-run unit 974..1,023 -- descriptive"),
    ("Q-SP-123", "spec", 123, "A statistic chosen after the runs are read is never a confrontation."),
    ("Q-SP-128", "spec", 128, "do with them. The MID-ONLY NARROWING CLAIM stays SUSPENDED until a"),
    ("Q-SP-129", "spec", 129, "claim passes (a)-(c) at mid and confronts (d); a claim that rests on"),
    # -- anv-b3bisect18prereg-20261101/protocol.txt (the 18th cut's FROZEN protocol; the adopted source pin) --
    ("Q-PR18-55", "pr18", 55, "this cut does not measure 254,679; that content stands"),
    ("Q-PR18-98", "pr18", 98, "(the ROUNDS6400 instrument variant; the measuring session"),
    ("Q-PR18-150", "pr18", 150, "c2704aaad6bfeeae1f4f9cfa916d0160efb03926892237554c7dffc8"),
    ("Q-PR18-151", "pr18", 151, "386e84e0 (adopted UNCHANGED from the s166 freeze; re-"),
    ("Q-PR18-157", "pr18", 157, "|x - m_c|; CI half-width h_c = 3.6420 * MAD_c / sqrt(N)"),
    ("Q-PR18-165", "pr18", 165, "changes): CAPTURED iff all 18 pipeline-ok cells m_c - h_c"),
    ("Q-PR18-166", "pr18", 166, ">= 1,000; FLOOR iff all 18 m_c + h_c <= 100;"),
    ("Q-PR18-167", "pr18", 167, "INTERMEDIATE/MIXED iff (some m_c + h_c < 1,000) AND (some"),
    ("Q-PR18-168", "pr18", 168, "m_c - h_c > 100); IN-BAND-UNDECIDED otherwise."),
    ("Q-PR18-169", "pr18", 169, "THE CONSTANT R = 6,400 is ADOPTED UNCHANGED, NOT re-derived at"),
    ("Q-PR18-240", "pr18", 240, "(d) INVALID -- the frozen INVALIDATION criterion (the standing"),
    ("Q-PR18-241", "pr18", 241, "cut protocol): > 0 VERIFY mismatches in any run makes that"),
    ("Q-PR18-279", "pr18", 279, "(16 blocks of 3 runs + pooled-48) UNDER THE PRE-REGISTERED DEEP-"),
    ("Q-PR18-280", "pr18", 280, "POOLING CI CLASS STATISTIC (R = 6,400), AT ITS NEW FIRST-MEASURED"),
    ("Q-PR18-404", "pr18", 404, "(block = 3 runs x 6,400 rounds per cell, frozen estimator unit --"),
    # -- state-s179.txt (the D3 (ii) second-edge form) / state-s193.txt (the D1 (1) shape-change form) --
    ("Q-S179-132", "s179", 132, "is named: if this cut's own content at 254,679 comes"),
    ("Q-S179-133", "s179", 133, "out mixed (C2 (c)), it is NOT rescued by later"),
    ("Q-S179-136", "s179", 136, "must confront this cut's content first -- named here,"),
    ("Q-S179-138", "s179", 138, "would re-read, not confront."),
    ("Q-S193-44", "s193", 44, "first). NAMED: a SHAPE-CHANGE confrontation at"),
    ("Q-S193-48", "s193", 48, "row with its own pre-registration -- NOT this cut;"),
    # -- state-s203.txt (the census-half state) --
    ("Q-S203-46", "s203", 46, "0/16 >= 1,000 (range + pooled entirely below 1,000) while all"),
    ("Q-S203-53", "s203", 53, "THREE VIRGIN (0 occurrences in every parsed publication source"),
    # -- state-s204.txt (the design record itself: the D-shape, the arm table, the VERIFIED paragraph, the D1 (2) sentences) --
    ("Q-S204-38", "s204", 38, "derived this session): at q=1 the W1 (a) outcome leaves"),
    ("Q-S204-39", "s204", 39, "width 92 of 122 and W1 (b) leaves 30 (worst case 92);"),
    ("Q-S204-41", "s204", 41, "61); at q=3 W1 (a) leaves 91 and W1 (b) leaves 31"),
    ("Q-S204-43", "s204", 43, "worst-case remaining bracket width (61 < 91 < 92) and"),
    ("Q-S204-97", "s204", 97, "does not measure 254,923 and NO letter of this cut"),
    ("Q-S204-200", "s204", 200, "this cut does not measure 254,923; that content stands"),
    ("Q-S204-391", "s204", 391, "(a) C2 (b) -> the bracket narrows to (254,923, 254,984]"),
    ("Q-S204-401", "s204", 401, "(b) C2 (a) -> the bracket narrows to (254,984, 255,045]"),
    ("Q-S204-418", "s204", 418, "c2  (B=2, WM=1, NDIV=1)       control, k=3"),
    ("Q-S204-419", "s204", 419, "q2  (B=3, WM=307, NDIV=1204)  n=254,984 (knob"),
    ("Q-S204-422", "s204", 422, "c8  (B=8, WM=1, NDIV=1)       control, k=3"),
    ("Q-S204-493", "s204", 493, "gcd(307,1204) = gcd(674,2643) = 1; clip widths q=1 92/30,"),
]

# (id, file key, expected size in bytes, expected sha256 hex)
FILE_PINS = [
    ("F-KS203", "ks203", 14169,
     "39de9bc274154b7cdd1f891454d548adfef931a034b7a5f7651fd328c63083a2"),
    ("F-PUB197", "pub197", 62811,
     "f3d7465ad60a7de2be20d4edfcbb4743f73849d7b0a93e7ff6f2eccbd1ff5e53"),
    ("F-PUB158", "pub158", 56588,
     "45538ad757bfa28821de2728000581897aaef8cc75f32ed656914509f400cd25"),
    ("F-PUB139", "pub139", 33345,
     "b6eb79cb397ae6b9ee6f502fee3b3e70c7d9cbbbe1e3b21c00ae126a3ac3092c"),
    ("F-PUB147", "pub147", 29876,
     "d41df35aff0a0ff674549a9f4390752be27f28f71cce90dfdf54bb1b08d407aa"),
    ("F-PUB185", "pub185", 59777,
     "c62c01e17a045933782cc3fb8c67e452ae0f35a513ad1f396a9dea08834d6d34"),
    ("F-PUB169", "pub169", 56352,
     "c9aab750fd20120b3abe8db6e9cac554b6c8ea0fbb1b37d9169d1539e4ff7687"),
    ("F-SPEC", "spec", 9660,
     "c0eff7fb0a5997658c94c7be36f776229d29aabe99f4f96be6ebb48c821d5ec7"),
    ("F-PR18", "pr18", 24242,
     "97364eb10f233d342aff2a9d7d5310cfe879479e29e0b2dc42df2998c236bb77"),
    ("F-S179", "s179", 19949,
     "a165e8c38649c8d2585674c5c60aa99e340191071c01e5011e0441f8389c7a69"),
    ("F-S193", "s193", 29283,
     "222916e21abe224b7b2046bea0e669118ba6653c3b24aaf81fbd25b5b3ac2784"),
    ("F-S203", "s203", 6801,
     "35656eac8f6add1bd34edcff8d2a0d45170a96a76964a356a5f69de0045dde49"),
    ("F-S204", "s204", 32324,
     "0619aef27022f9a406dfc3047b25595b6da0ef9347906380ed9531126261a5f3"),
]

# (id, description, computed string, expected string) -- the state-s204
# VERIFIED THIS TICK paragraph arithmetic, re-derived here.
ARITH_WANTS = [
    ("A-WIDTH", "bracket width 255045-254923",
     str(255045 - 254923), "122"),
    ("A-QG1", "quarter grid q=1: 254923 + 122//4",
     str(254923 + 122 // 4), "254953"),
    ("A-QG2", "quarter grid q=2: 254923 + (2*122)//4",
     str(254923 + (2 * 122) // 4), "254984"),
    ("A-QG3", "quarter grid q=3: 254923 + (3*122)//4",
     str(254923 + (3 * 122) // 4), "255014"),
    ("A-FMID", "floor midpoint (254923+255045)//2",
     str((254923 + 255045) // 2), "254984"),
    ("A-FMID-EQ", "254923+(2*122)//4 == (254923+255045)//2",
     str(254923 + (2 * 122) // 4 == (254923 + 255045) // 2), "True"),
    ("A-KNOB-Q1", "knob arithmetic (1,000,003*296)//1161",
     str((1000003 * 296) // 1161), "254953"),
    ("A-KNOB-Q2", "knob arithmetic (1,000,003*307)//1204",
     str((1000003 * 307) // 1204), "254984"),
    ("A-KNOB-Q3", "knob arithmetic (1,000,003*674)//2643",
     str((1000003 * 674) // 2643), "255014"),
    ("A-KNOB-HI", "knob arithmetic (1,000,003*316)//1239",
     str((1000003 * 316) // 1239), "255045"),
    ("A-GCD-Q1", "gcd(296, 1161)",
     str(math.gcd(296, 1161)), "1"),
    ("A-GCD-Q2", "gcd(307, 1204)",
     str(math.gcd(307, 1204)), "1"),
    ("A-GCD-Q3", "gcd(674, 2643)",
     str(math.gcd(674, 2643)), "1"),
    ("A-GCD-HI", "gcd(316, 1239)",
     str(math.gcd(316, 1239)), "1"),
    ("A-CLIP-Q1-TOP", "q=1 top piece 255045-254953",
     str(255045 - 254953), "92"),
    ("A-CLIP-Q1-LOW", "q=1 low piece 254953-254923",
     str(254953 - 254923), "30"),
    ("A-CLIP-Q2-LOW", "q=2 low piece 254984-254923",
     str(254984 - 254923), "61"),
    ("A-CLIP-Q2-TOP", "q=2 top piece 255045-254984",
     str(255045 - 254984), "61"),
    ("A-CLIP-Q3-TOP", "q=3 top piece 255045-255014",
     str(255045 - 255014), "31"),
    ("A-CLIP-Q3-LOW", "q=3 low piece 255014-254923",
     str(255014 - 254923), "91"),
    ("A-WORST-Q1", "worst-case remaining width at q=1 max(92,30)",
     str(max(255045 - 254953, 254953 - 254923)), "92"),
    ("A-WORST-Q2", "worst-case remaining width at q=2 max(61,61)",
     str(max(255045 - 254984, 254984 - 254923)), "61"),
    ("A-WORST-Q3", "worst-case remaining width at q=3 max(31,91)",
     str(max(255045 - 255014, 255014 - 254923)), "91"),
    ("A-MINIMAX", "argmin worst-case over q=1/q=2/q=3",
     min({"q=1": 255045 - 254953, "q=2": 255045 - 254984,
          "q=3": 255045 - 255014}.items(), key=lambda kv: kv[1])[0],
     "q=2"),
    ("A-ARM-TABLE", "arm table self-check 3+48+3",
     str(3 + 48 + 3), "54"),
    ("A-OLDWIDTH", "old bracket width 255045-254557",
     str(255045 - 254557), "488"),
    ("A-FM16", "16th-cut floor midpoint (254557+255045)//2",
     str((254557 + 255045) // 2), "254801"),
    ("A-IMPL", "F > 254,984 > 254,882 (both inequalities)",
     str(254984 > 254882 and 254923 < 254984), "True"),
    ("A-BAND-WIDTH", "wander band width 1015-981",
     str(1015 - 981), "34"),
    ("A-LO-SPREAD", "lo (18th cut) binding spread 998.0538-995.1326",
     str(Decimal("998.0538") - Decimal("995.1326")), "2.9212"),
    ("A-BIS-SPREAD", "bis (15th cut) binding spread 1008.7909-1005.8172",
     str(Decimal("1008.7909") - Decimal("1005.8172")), "2.9737"),
    ("A-FM-SPREAD", "fm (16th cut) binding spread 1006.7909-997.0538",
     str(Decimal("1006.7909") - Decimal("997.0538")), "9.7371"),
    ("A-Q1-SPREAD", "q1 (17th cut) binding spread 1002.9224-999.0012",
     str(Decimal("1002.9224") - Decimal("999.0012")), "3.9212"),
]


def line_of(texts, key, lineno):
    return texts[key].split(b"\n")[lineno - 1].decode("utf-8")


def parse_binding_list(line, marker):
    after = line.split(marker, 1)[1]
    if "; pooled-48" in after:
        after = after.split("; pooled-48", 1)[0]
    return [Decimal(v.strip()) for v in after.split("/")]


def parse_pooled(line, marker):
    return Decimal(line.split(marker, 1)[1].strip())


def parse_class_list(line):
    body = line.split("block classes:", 1)[1].split("; pooled-48 class:")[0]
    return re.findall(r"'([A-Z/-]+)'", body)


def parse_m_list(line):
    body = line.split("m: blocks", 1)[1].split(";")[0]
    return [int(v.strip()) for v in body.split("/")]


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

    print("== DESIGN-VERIFY S204 (session 205) ==")
    print("== fail-closed quote + arithmetic re-derivation vs committed bytes ==")
    print("== QUOTE-ONLY / ARITHMETIC-ONLY: NO 19th-cut quantity is computed ==")
    print()

    # 1. file-level pins (size + sha256)
    for want_id, key, size, sha in FILE_PINS:
        got = texts[key]
        got_sha = hashlib.sha256(got).hexdigest()
        detail = "%s size %d sha256 %s" % (SHORT[key], len(got), got_sha)
        record(want_id, detail, len(got) == size and got_sha == sha)

    # 2. knob-search-s203 run1 == run2 byte-identity
    same = texts["ks203"] == texts["ks203r2"]
    record("F-KS203-PAIR",
           "knob-search-s203-run1.txt == knob-search-s203-run2.txt byte-identity",
           same)

    # 3. line-pinned quote wants
    for want_id, key, lineno, substr in LINE_WANTS:
        lines = texts[key].split(b"\n")
        good = lineno <= len(lines) and substr.encode("utf-8") in lines[lineno - 1]
        detail = "%s:%d contains %r" % (SHORT[key], lineno, substr)
        record(want_id, detail, good)

    # 4. arithmetic re-derivations (state-s204 VERIFIED THIS TICK paragraph)
    for want_id, desc, computed, expected in ARITH_WANTS:
        detail = "%s -> %s (expected %s)" % (desc, computed, expected)
        record(want_id, detail, computed == expected)

    # 5. derived re-computations FROM COMMITTED BYTES
    lo_bind = parse_binding_list(line_of(texts, "pub197", 648), "block binding min(m-h):")
    lo_pooled = parse_pooled(line_of(texts, "pub197", 649), "pooled-48 binding min(m-h):")
    lo_m = parse_m_list(line_of(texts, "pub197", 650))
    lo_m_pooled = int(line_of(texts, "pub197", 650).split("pooled-48", 1)[1].strip())
    lo_classes = parse_class_list(line_of(texts, "pub197", 647))
    lo_pooled_class = line_of(texts, "pub197", 647).split("pooled-48 class:", 1)[1].strip()
    bis_bind = parse_binding_list(line_of(texts, "pub158", 703), "block min(m-h):")
    bis_pooled = parse_pooled(line_of(texts, "pub158", 703), "; pooled-48 ")
    q1_bind = parse_binding_list(line_of(texts, "pub185", 642), "block binding min(m-h):")
    q1_pooled = parse_pooled(line_of(texts, "pub185", 643), "pooled-48 binding min(m-h):")
    fm_bind = parse_binding_list(line_of(texts, "pub169", 621), "block binding min(m-h):")

    record("D-LO-BIND",
           "pub197:648 16 values min %s max %s spread %s (want 995.1326/998.0538/2.9212)"
           % (min(lo_bind), max(lo_bind), max(lo_bind) - min(lo_bind)),
           len(lo_bind) == 16
           and min(lo_bind) == Decimal("995.1326")
           and max(lo_bind) == Decimal("998.0538")
           and max(lo_bind) - min(lo_bind) == Decimal("2.9212"))
    record("D-LO-UNDER-1000",
           "pub197:648 16/16 min(m-h) < 1,000: %s" % (all(b < 1000 for b in lo_bind)),
           all(b < 1000 for b in lo_bind) and len(lo_bind) == 16)
    record("D-LO-POOLED",
           "pub197:649 pooled-48 binding %s (want 997.7700)" % lo_pooled,
           lo_pooled == Decimal("997.7700"))
    record("D-LO-CLASSES",
           "pub197:647 classes re-counted: %d total, %d INTERMEDIATE/MIXED, pooled-48 %s (want 16/16/INTERMEDIATE/MIXED)"
           % (len(lo_classes),
              sum(1 for c in lo_classes if c == "INTERMEDIATE/MIXED"),
              lo_pooled_class),
           len(lo_classes) == 16
           and all(c == "INTERMEDIATE/MIXED" for c in lo_classes)
           and lo_pooled_class == "INTERMEDIATE/MIXED")
    record("D-LO-M",
           "pub197:650 block m min %d max %d pooled %d (want 1131/1132/1132)"
           % (min(lo_m), max(lo_m), lo_m_pooled),
           len(lo_m) == 16 and min(lo_m) == 1131
           and max(lo_m) == 1132 and lo_m_pooled == 1132)
    record("D-BIS-BIND",
           "pub158:703 16 values min %s max %s spread %s (want 1005.8172/1008.7909/2.9737)"
           % (min(bis_bind), max(bis_bind), max(bis_bind) - min(bis_bind)),
           len(bis_bind) == 16
           and min(bis_bind) == Decimal("1005.8172")
           and max(bis_bind) == Decimal("1008.7909")
           and max(bis_bind) - min(bis_bind) == Decimal("2.9737"))
    record("D-BIS-OVER-1000",
           "pub158:703 16/16 min(m-h) > 1,000: %s" % (all(b > 1000 for b in bis_bind)),
           all(b > 1000 for b in bis_bind) and len(bis_bind) == 16)
    record("D-BIS-POOLED",
           "pub158:703 pooled-48 binding %s (want 1009.6912)" % bis_pooled,
           bis_pooled == Decimal("1009.6912"))
    record("D-Q1-BIND",
           "pub185:642 min %s max %s spread %s (want 999.0012/1002.9224/3.9212)"
           % (min(q1_bind), max(q1_bind), max(q1_bind) - min(q1_bind)),
           len(q1_bind) == 16
           and min(q1_bind) == Decimal("999.0012")
           and max(q1_bind) == Decimal("1002.9224")
           and max(q1_bind) - min(q1_bind) == Decimal("3.9212"))
    record("D-Q1-STRADDLE",
           "pub185:642 range STRADDLES 1,000: %s" % (min(q1_bind) < 1000 < max(q1_bind)),
           min(q1_bind) < 1000 < max(q1_bind))
    record("D-Q1-POOLED",
           "pub185:643 pooled-48 binding %s (want 1001.7437)" % q1_pooled,
           q1_pooled == Decimal("1001.7437"))
    record("D-FM-BIND",
           "pub169:621 min %s max %s spread %s (want 997.0538/1006.7909/9.7371)"
           % (min(fm_bind), max(fm_bind), max(fm_bind) - min(fm_bind)),
           len(fm_bind) == 16
           and min(fm_bind) == Decimal("997.0538")
           and max(fm_bind) == Decimal("1006.7909")
           and max(fm_bind) - min(fm_bind) == Decimal("9.7371"))
    allfour = lo_bind + bis_bind + q1_bind + fm_bind
    record("D-BAND-4SETS",
           "all 64 committed block minima in 981..1,015 (D4 (2) claim): %s"
           % all(Decimal("981") <= b <= Decimal("1015") for b in allfour),
           len(allfour) == 64
           and all(Decimal("981") <= b <= Decimal("1015") for b in allfour))

    # 6. THE W1 (a)/(b) PER-OUTCOME BRACKET-WIDTH GEOMETRY (D1 (2)),
    #    re-derived from the committed W1 letter shapes: W1 (a) keeps
    #    (254,923, p] (state-s204 L391, the18th cut's W1 (b) narrowed
    #    upward at its point), W1 (b) keeps (p, 255,045] (state-s204
    #    L401 == publication-s197 L791 at p=254,923).
    lo_n, hi_n = 254923, 255045
    pts = {"q=1": 254953, "q=2": 254984, "q=3": 255014}
    derived = {k: (p - lo_n, hi_n - p) for k, p in pts.items()}
    s204 = texts["s204"].decode("utf-8")
    q1_claim_text = (line_of(texts, "s204", 38) + " " + line_of(texts, "s204", 39))
    m_q1 = re.search(r"at q=1 the W1 \(a\) outcome leaves width (\d+) of 122 and W1 \(b\) leaves (\d+)", q1_claim_text)
    m_q3 = re.search(r"at q=3 W1 \(a\) leaves (\d+) and W1 \(b\) leaves (\d+)",
                     line_of(texts, "s204", 41))
    claimed_q1 = (int(m_q1.group(1)), int(m_q1.group(2))) if m_q1 else None
    claimed_q3 = (int(m_q3.group(1)), int(m_q3.group(2))) if m_q3 else None
    record("D-W1-Q1-LETTERS",
           "state-s204 D1 (2) q=1 per-letter remaining widths (W1 (a), W1 (b)) "
           "claimed %s vs re-derived %s from the committed W1 shapes"
           % (claimed_q1, derived["q=1"]),
           claimed_q1 == derived["q=1"])
    record("D-W1-Q2-LETTERS",
           "state-s204 D1 (2) q=2 per-letter remaining widths claimed (61, 61) vs re-derived %s"
           % (derived["q=2"],),
           derived["q=2"] == (61, 61))
    record("D-W1-Q3-LETTERS",
           "state-s204 D1 (2) q=3 per-letter remaining widths claimed %s vs re-derived %s"
           % (claimed_q3, derived["q=3"]),
           claimed_q3 == derived["q=3"])
    record("D-W1-GEOM",
           "re-derived W1 (a)/(b) widths at q=1 %s / q=2 %s / q=3 %s "
           "(W1 (a) = p-254,923 keeps the low piece; W1 (b) = 255,045-p keeps the top piece)"
           % (derived["q=1"], derived["q=2"], derived["q=3"]),
           derived["q=1"] == (30, 92) and derived["q=2"] == (61, 61)
           and derived["q=3"] == (91, 31))

    print()
    print("DESIGN-VERIFY S204 SUMMARY: %d ok / %d failed" % (ok, failed))
    if failed == 0:
        print("DESIGN-VERIFY S204 COMPLETE (fail-closed: 0 failed)")
        return 0
    print("DESIGN-VERIFY S204 FAILED (fail-closed)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
