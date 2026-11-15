#!/usr/bin/env python3
# design-verify-s179.py -- JUN-59 session 181: the s179 design-verify
# (the s180 carry-forward, fail-closed quote + arithmetic re-derivation
# vs the committed bytes pinned in state-s180.txt).
#
# FAIL-CLOSED: every want is a (file, line number, substring) triple
# checked against the exact committed line, plus file-level size/sha256
# pins, the knob-search-s177 run1==run2 byte-identity, and the pure
# arithmetic re-derivations asserted by the s179 draft. ANY missing
# line, mismatched byte, or wrong arithmetic is a hard failure (exit 1).
#
# QUOTE-ONLY / ARITHMETIC-ONLY: this script verifies the s179 draft's
# quotations and arithmetic against committed bytes. It computes NO
# seventeenth-cut quantity -- NO run log, NO class, NO verdict, NO
# claim. Every 17th-cut quantity stays UNMEASURED. RULE 4 unchanged:
# NOTHING MOVES; bracket stays EXACTLY (254,557, 255,045].
import hashlib
import os
import sys
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
GPU = os.path.dirname(HERE)

FILES = {
    "pub169": os.path.join(GPU, "anv-b3bisect16-20261101", "publication-s169.txt"),
    "pub158": os.path.join(GPU, "anv-b3bisect15-20261101", "publication-s158.txt"),
    "ks177": os.path.join(HERE, "knob-search-s177-run1.txt"),
    "ks177r2": os.path.join(HERE, "knob-search-s177-run2.txt"),
    "spec": os.path.join(GPU, "anv-b3confrontation-spec-20261031", "confrontation-spec.txt"),
    "s176": os.path.join(HERE, "state-s176.txt"),
}

SHORT = {
    "pub169": "publication-s169.txt",
    "pub158": "publication-s158.txt",
    "ks177": "knob-search-s177-run1.txt",
    "ks177r2": "knob-search-s177-run2.txt",
    "spec": "confrontation-spec.txt",
    "s176": "state-s176.txt",
}

# (id, file key, 1-based line number, exact substring expected on that line)
LINE_WANTS = [
    # -- publication-s169.txt (the 16th cut's publication) --
    ("Q-169-608", "pub169", 608, "class FLOOR (committed floor band 31..32 at B=2): False"),
    ("Q-169-611", "pub169", 611, "VERDICT: branch (b) replication discrepancy (W1 (d) INVALID"),
    ("Q-169-616", "pub169", 616, "the FLOOR MIDPOINT of the bracket (254,557, 255,045]; the"),
    ("Q-169-617", "pub169", 617, "point is VIRGIN -- this cut's content is the FIRST content at it"),
    ("Q-169-645", "pub169", 645, "NOTHING MOVES"),
    ("Q-169-707", "pub169", 707, "binding min(m-h) 1,006.8..1,008.8 / pooled 1,009.7"),
    ("Q-169-710", "pub169", 710, "prose lower bound 1,006.8 matches NO committed byte"),
    ("Q-169-742", "pub169", 742, "5. VERDICT SUMMARY: C1 (b); C2 (c) at fm (254,801); W1 (d)."),
    ("Q-169-743", "pub169", 743, "CUT VERDICT: INVALID; NOTHING MOVES."),
    ("Q-169-744", "pub169", 744, "The committed bracket stays EXACTLY (254,557, 255,045]."),
    # -- publication-s158.txt (the 15th cut's publication) --
    ("Q-158-135", "pub158", 135, "anv-bb-bis 52fb68b66b550f0029c50b8695e13ecdcfcd736831e42cc3bccdb9b6f5bf14a8"),
    ("Q-158-287", "pub158", 287, "min(m-h)=1005.8172@17"),
    ("Q-158-407", "pub158", 407, "min(m-h)=1008.7909@13"),
    ("Q-158-467", "pub158", 467, "min(m-h)=1008.7909@13"),
    ("Q-158-587", "pub158", 587, "min(m-h)=1009.6912@13"),
    ("Q-158-668", "pub158", 668, "(254,557, 255,045]"),
    ("Q-158-672", "pub158", 672, "Bracket state: NARROWED -- (254,557, 255,045]"),
    ("Q-158-705a", "pub158", 705, "s139 (16 blocks + pooled-48 at 440604ef...)"),
    ("Q-158-705b", "pub158", 705, "1174/1167/1162/1143/1147/1150/1152/1150/1151/1153/1144/1144/1145/1127/1146/1145, pooled-48 1148 CAPTURED"),
    ("Q-158-712", "pub158", 712, "n=254557: 1156 INTERMEDIATE/MIXED (session 121)"),
    ("Q-158-713", "pub158", 713, "n=254557: 1143 CAPTURED (session 125)"),
    ("Q-158-714", "pub158", 714, "n=254882: 1129 INTERMEDIATE/MIXED (session 125)"),
    ("Q-158-715", "pub158", 715, "n=254882: 1133 INTERMEDIATE/MIXED (session 132)"),
    ("Q-158-716", "pub158", 716, "n=254882: 1148 CAPTURED (session 136)"),
    ("Q-158-717", "pub158", 717, "lo pooled-12 1141 INTERMEDIATE/MIXED; mid pooled-48 1140 CAPTURED"),
    ("Q-158-718", "pub158", 718, "the named cross-window disagreement at cabff942"),
    ("Q-158-719", "pub158", 719, "pooled-24 1133 INTERMEDIATE/MIXED vs s136"),
    ("Q-158-720", "pub158", 720, "pooled-24 1148 CAPTURED vs s139"),
    ("Q-158-721", "pub158", 721, "pooled-48 1140 CAPTURED vs s147"),
    ("Q-158-722", "pub158", 722, "pooled-48 1148 CAPTURED"),
    ("Q-158-743", "pub158", 743, "(254,557, 255,045]"),
    ("Q-158-746", "pub158", 746, "Bracket state: NARROWED -- (254,557, 255,045]."),
    # -- knob-search-s177-run1.txt (the s178 census) --
    ("Q-KS-10", "ks177", 10, "(254557, 255045] n-units, width 488"),
    ("Q-KS-24", "ks177", 24, "10x CAPTURED + 3x INTERMEDIATE/MIXED + 3x IN-BAND-UNDECIDED; pooled-48 class CAPTURED"),
    ("Q-KS-25", "ks177", 25, "997.0538..1006.7909 (16 values), pooled-48 1002.7437"),
    ("Q-KS-26", "ks177", 26, "blocks 1145..1134 (16 values), pooled-48 1138"),
    ("Q-KS-27a", "ks177", 27, "C2 VERDICT: (c) CLASS-UNRESOLVED"),
    ("Q-KS-27b", "ks177", 27, "L9 binds at 254,801."),
    ("Q-KS-34a", "ks177", 34, "16x IN-BAND-UNDECIDED + pooled-48 IN-BAND-UNDECIDED"),
    ("Q-KS-34b", "ks177", 34, "TOLERANCE-UNRESOLVED"),
    ("Q-KS-40", "ks177", 40, "16/16 of this cut's fm block binding min(m-h) values land inside the block-unit wander band 981..1015"),
    ("Q-KS-43", "ks177", 43, "(254557+255045)//2 = 254801"),
    ("Q-KS-44", "ks177", 44, "quarter q=1 n=254679: pairs 31; smallest (313, 1229); in-box same-ratio doubles 8"),
    ("Q-KS-45", "ks177", 45, "n=254679 has NEVER been measured -- 0 occurrences in every parsed committed source (virgin; enumeration only)"),
    ("Q-KS-48", "ks177", 48, "quarter q=3 n=254923: pairs 34; smallest (246, 965); in-box same-ratio doubles 10"),
    # -- confrontation-spec.txt (accepted design only) --
    ("Q-SP-59", "spec", 59, "981..1,015 (census); per-run unit (descriptive, s139 W2): 974..1,023."),
    ("Q-SP-100", "spec", 100, "More blocks of the same mixed shape do"),
    ("Q-SP-101", "spec", 101, "not confront anything; they re-read it."),
    ("Q-SP-116", "spec", 116, "block-unit 981..1,015; per-run unit 974..1,023"),
    ("Q-SP-123", "spec", 123, "A statistic chosen after the runs are read is never a confrontation."),
    ("Q-SP-128", "spec", 128, "The MID-ONLY NARROWING CLAIM stays SUSPENDED until a"),
    ("Q-SP-129", "spec", 129, "claim passes (a)-(c) at mid and confronts (d)"),
    # -- state-s176.txt (the s176 named design input) --
    ("Q-S176-34", "s176", 34, "the 16th cut's c2/c8 binaries reproduced the"),
    ("Q-S176-35", "s176", 35, "s158 digests BYTE-IDENTICALLY, so the discrepancy is NOT"),
    ("Q-S176-36", "s176", 36, "binary-driven -- named here as a design input, not a"),
]

# (id, file key, expected size in bytes, expected sha256 hex)
FILE_PINS = [
    ("F-PUB169", "pub169", 56352,
     "c9aab750fd20120b3abe8db6e9cac554b6c8ea0fbb1b37d9169d1539e4ff7687"),
    ("F-KS177", "ks177", 6823,
     "b3fdb1f27cecbf18f1249948364e061b8d24c1773f730a00a808cb8ce24d627e"),
]

# (id, description, computed string, expected string)
ARITH_WANTS = [
    ("A-KNOB-Q1", "knob arithmetic (1,000,003*313)//1,229",
     str((1000003 * 313) // 1229), "254679"),
    ("A-GCD-Q1", "gcd(313, 1229)",
     str(__import__("math").gcd(313, 1229)), "1"),
    ("A-FMID", "floor midpoint (254557+255045)//2",
     str((254557 + 255045) // 2), "254801"),
    ("A-WIDTH", "bracket width 255045-254557",
     str(255045 - 254557), "488"),
    ("A-Q1-GRID", "quarter grid q=1: 254557 + 488//4",
     str(254557 + 488 // 4), "254679"),
    ("A-Q3-GRID", "quarter grid q=3: 254557 + 3*(488//4)",
     str(254557 + 3 * (488 // 4)), "254923"),
    ("A-ARM-TABLE", "arm table self-check 3+48+3",
     str(3 + 48 + 3), "54"),
    ("A-BIS-SPREAD", "bis binding spread 1008.7909-1005.8172",
     str(Decimal("1008.7909") - Decimal("1005.8172")), "2.9737"),
    ("A-FM-SPREAD", "fm binding spread 1006.7909-997.0538",
     str(Decimal("1006.7909") - Decimal("997.0538")), "9.7371"),
    ("A-BAND-WIDTH", "wander band width 1015-981",
     str(1015 - 981), "34"),
    ("A-D1-DISTANCE", "254,801 - 254,679 (the 122 n-units below)",
     str(254801 - 254679), "122"),
    ("A-Q3-CLIP", "255,045 - 254,923 (q=3 clips only the top 122)",
     str(255045 - 254923), "122"),
]


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

    print("== DESIGN-VERIFY S179 (session 181) ==")
    print("== fail-closed quote + arithmetic re-derivation vs committed bytes ==")
    print("== QUOTE-ONLY / ARITHMETIC-ONLY: NO 17th-cut quantity is computed ==")
    print()

    # 1. file-level pins (size + sha256)
    for want_id, key, size, sha in FILE_PINS:
        got = texts[key]
        got_sha = hashlib.sha256(got).hexdigest()
        detail = "%s size %d sha256 %s" % (SHORT[key], len(got), got_sha)
        record(want_id, detail, len(got) == size and got_sha == sha)

    # 2. knob-search-s177 run1 == run2 byte-identity
    same = texts["ks177"] == texts["ks177r2"]
    record("F-KS177-PAIR",
           "knob-search-s177-run1.txt == knob-search-s177-run2.txt byte-identity",
           same)

    # 3. line-pinned quote wants
    for want_id, key, lineno, substr in LINE_WANTS:
        lines = texts[key].split(b"\n")
        good = lineno <= len(lines) and substr.encode("utf-8") in lines[lineno - 1]
        detail = "%s:%d contains %r" % (SHORT[key], lineno, substr)
        record(want_id, detail, good)

    # 4. arithmetic re-derivations
    for want_id, desc, computed, expected in ARITH_WANTS:
        detail = "%s -> %s (expected %s)" % (desc, computed, expected)
        record(want_id, detail, computed == expected)

    print()
    print("DESIGN-VERIFY S179 SUMMARY: %d ok / %d failed" % (ok, failed))
    if failed == 0:
        print("DESIGN-VERIFY S179 COMPLETE (fail-closed: 0 failed)")
        return 0
    print("DESIGN-VERIFY S179 FAILED (fail-closed)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
