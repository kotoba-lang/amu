#!/usr/bin/env python3
"""JUN-59 session 178 -- the SEVENTEENTH CUT pre-registration derivation,
cut-point confrontation census (the s177 carry-forward (a)).

Every number below is computed in this script from arithmetic or PARSED
from committed bytes -- nothing is transcribed from prose. Deterministic:
no clock, no RNG, no network, no hardware. Running it twice is
byte-identical (the run captures + cmp in the evidence directory).

Purpose: confront the cut point of the sixteenth cut against the
disputed record, over the remaining bracket (254,557, 255,045]:
  1. the s165 knob enumeration RE-DERIVED and CONFRONTED against the
     s165 capture pins (fm 31/(345,1,354)/7, mid 35/(248,973)/10);
  2. the 16th-cut content PARSED from publication-s169.txt (C1 (b),
     C2 (c), W1 (d), the verdict + bracket pins);
  3. the disputed record citations (lo/mid dual-class rows + the 14th
     cut's TOLERANCE-UNRESOLVED mid content) parsed from their primary
     committed sources AND cross-checked against the 16th cut's own W3
     reading of them;
  4. candidate cut points enumerated -- the floor midpoint re-derivation
     254,801 and the quarter-grid candidates -- with a committed-content
     census at each candidate across the parsed sources.

QUOTE-ONLY content: this script takes NO measurement of its own; no cut
is frozen or queued here, no bracket moves, no class/verdict/claim is
produced. The confrontation-spec arms (a)-(d) and the measured wander
band are parsed only as DESIGN INPUT pins for the design decisions
that the next slice drafts.
"""
import math
import os
import re
from collections import Counter
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
GPU = os.path.join(HERE, "..")

N_FULL = 1_000_003
BOX_WM = range(1, 2049)
BOX_NDIV = range(1, 8193)

# Frozen citation wants (pin-like): the PARSE must match these committed
# values or the script aborts fail-closed.
WANT_BRACKET = (254557, 255045)
WANT_FLOOR_MID = 254801
WANT_KS_FM = (254801, 31, (345, 1354), 7)      # s165 capture pin (fm)
WANT_KS_MID = (254882, 35, (248, 973), 10)     # s165 capture pin (mid)
WANT_C1_C2LINE = ("30", "31", "32", "False")
WANT_C1_C8LINE = ("32820", "32915", "True", "-0.29")
WANT_C1_VERDICT = ("b", "d")
WANT_C2_KNOB = ("345", "1354", "254801")
WANT_C2_CLASSES = ({"CAPTURED": 10, "INTERMEDIATE/MIXED": 3,
                    "IN-BAND-UNDECIDED": 3}, "CAPTURED")
WANT_C2_BIND = ("997.0538", "1006.7909", "1002.7437")   # min, max, pooled
WANT_C2_M = (16, "1145", "1134", "1138")                # n, first, last, pooled
WANT_SUMMARY = ("b", "c", "254801", "d")
WANT_SPEC_BAND = ("981", "1015", "974", "1023")
WANT_W3_ROWS = [("254557", "1156", "INTERMEDIATE/MIXED", "121"),
                ("254557", "1143", "CAPTURED", "125"),
                ("254882", "1129", "INTERMEDIATE/MIXED", "125"),
                ("254882", "1133", "INTERMEDIATE/MIXED", "132"),
                ("254882", "1148", "CAPTURED", "136")]
WANT_W3_LO_POOL12 = ("1141", "INTERMEDIATE/MIXED")
WANT_W3_POOLS = ("1140", "CAPTURED", "1148", "IN-BAND-UNDECIDED")
# Disputed-record pins (the s165 census wants, re-used verbatim):
WANT_R4557 = [(1156, "INTERMEDIATE/MIXED", "121"),
              (1143, "CAPTURED", "125")]
WANT_R4882 = [(1129, "INTERMEDIATE/MIXED", "125"),
              (1133, "INTERMEDIATE/MIXED", "132"),
              (1148, "CAPTURED", "136")]
WANT_LO_POOL12 = (1141, 998, 1452, "INTERMEDIATE/MIXED")   # s129 tenth cut
WANT_MID_POOL48 = (1140, 1001, 1442, "CAPTURED")           # s139 pooled-48
WANT_S147_MINS = [992, 1006, 996, 1000, 1002, 993, 1002, 991,
                  1006, 996, 997, 996, 1002, 999, 995, 991]
WANT_S147_POOL_MIN = 1005
WANT_S147_POOL_MED = 1148
WANT_S147_VERDICT = ("(c) TOLERANCE-UNRESOLVED: any in-band minimum or "
                     "mixed classes -- FAILS; L9 binds at mid at 16 blocks "
                     "under the tolerance rule too.")
# Quarter-grid candidate pins (re-derived at run time; these CHECK the
# derivation, never replace it):
WANT_QUARTER = {1: (254679, 31, (313, 1229), 8),
                2: (254801, 31, (345, 1354), 7),
                3: (254923, 34, (246, 965), 10)}


def pairs_for(target):
    out = []
    for wm in BOX_WM:
        # (N_FULL*wm)//ndiv == target <=> ndiv in (N_FULL*wm/(target+1),
        # N_FULL*wm/target]
        lo = (N_FULL * wm) // (target + 1) + 1
        hi = (N_FULL * wm) // target
        for ndiv in range(max(1, lo), min(8192, hi) + 1):
            if (N_FULL * wm) // ndiv == target:
                out.append((wm, ndiv))
    return out


def smallest(pairs):
    return min(pairs, key=lambda p: (p[0], p[1]))


def doubles_in_box(pairs):
    return [p for p in pairs if 2 * p[0] <= 2048 and 2 * p[1] <= 8192]


def flat(text):
    return re.sub(r"\s+", " ", text)


def parsed(text, pattern, label):
    mm = re.search(pattern, flat(text))
    assert mm is not None, f"WANT NOT PARSED: {label}"
    return mm


def ncomma(s):
    return s.replace(",", "")


def main():
    print("== JUN-59 session 178 derivation (the SEVENTEENTH CUT          ==")
    print("== pre-registration: cut-point confrontation census over the   ==")
    print("== remaining bracket (254,557, 255,045] and the disputed       ==")
    print("== record -- s165 enumeration re-derived and confronted, the   ==")
    print("== 16th-cut content parsed, disputed-record citations cross-   ==")
    print("== checked, candidate cut points enumerated)                   ==")
    print("== every value computed here from arithmetic or committed      ==")
    print("== bytes; QUOTE-ONLY; NO measurement, NO freeze, NO queue      ==")
    print()

    P158 = open(os.path.join(GPU, "anv-b3bisect15-20261101",
                             "publication-s158.txt")).read()
    P169 = open(os.path.join(GPU, "anv-b3bisect16-20261101",
                             "publication-s169.txt")).read()
    P139 = open(os.path.join(GPU, "anv-b3bisect13-20261031",
                             "publication-s139.txt")).read()
    P147 = open(os.path.join(GPU, "anv-b3bisect14-20261031",
                             "publication-s147.txt")).read()
    KS164 = open(os.path.join(GPU, "anv-b3bisect16prereg-20261101",
                              "knob-search-s164-run1.txt")).read()
    SPEC = open(os.path.join(GPU, "anv-b3confrontation-spec-20261031",
                             "confrontation-spec.txt")).read()

    # ---- 0. the committed bracket, re-derived from committed bytes ----
    m = parsed(P158, r"Bracket state: NARROWED -- \(([\d,]+), ([\d,]+)\]",
               "publication-s158.txt bracket")
    lo_end = int(ncomma(m.group(1)))
    hi_end = int(ncomma(m.group(2)))
    assert (lo_end, hi_end) == WANT_BRACKET, "committed bracket endpoints"
    width = hi_end - lo_end
    floor_mid = (lo_end + hi_end) // 2
    print("committed bracket (publication-s158.txt, parsed): "
          f"({lo_end}, {hi_end}] n-units, width {width}")
    print("knob arithmetic: n = (1,000,003*WORK_MUL)//NDIV (integer floor)")
    print("search box (sessions 21-27's box): WORK_MUL 1..2,048 x "
          "NDIV 1..8,192")

    # ---- 1. the s165 enumeration RE-DERIVED and CONFRONTED ----
    print()
    print("SECTION 1 -- S165 ENUMERATION RE-DERIVED AND CONFRONTED:")
    ks = flat(KS164)
    fm = parsed(ks, r"FLOOR MIDPOINT CANDIDATE n=(\d+): pairs mapping to "
                    r"\d+ in-box: (\d+); smallest: \((\d+), (\d+)\) in-box "
                    r"pairs whose same-ratio double is also in-box: (\d+)",
                "s165 capture fm pin")
    ks_fm = (int(fm.group(1)), int(fm.group(2)),
             (int(fm.group(3)), int(fm.group(4))), int(fm.group(5)))
    assert ks_fm == WANT_KS_FM, f"s165 fm pin: {ks_fm}"
    mid = parsed(ks, r"MID CANDIDATE n=(\d+): pairs mapping to \d+ in-box: "
                     r"(\d+); smallest: \((\d+), (\d+)\) in-box pairs whose "
                     r"same-ratio double is also in-box: (\d+)",
                 "s165 capture mid pin")
    ks_mid = (int(mid.group(1)), int(mid.group(2)),
              (int(mid.group(3)), int(mid.group(4))), int(mid.group(5)))
    assert ks_mid == WANT_KS_MID, f"s165 mid pin: {ks_mid}"
    got = {}
    for label, target in (("fm", WANT_FLOOR_MID), ("mid", 254882)):
        ps = pairs_for(target)
        got[label] = (target, len(ps), smallest(ps), len(doubles_in_box(ps)))
    assert got["fm"] == WANT_KS_FM, f"fm re-derivation: {got['fm']}"
    assert got["mid"] == WANT_KS_MID, f"mid re-derivation: {got['mid']}"
    for label in ("fm", "mid"):
        t, n, sm, dbl = got[label]
        print(f"  {label} n={t}: pairs {n}; smallest {sm}; in-box "
              f"same-ratio doubles {dbl} -- s165 capture "
              f"({ks_fm if label == 'fm' else ks_mid}) -> MATCH")

    # ---- 2. the 16th-cut content PARSED from publication-s169.txt ----
    print()
    print("SECTION 2 -- 16TH-CUT CONTENT PARSED (publication-s169.txt):")
    f169 = flat(P169)
    i = f169.index("C1 ARCHIVED CONTROL REPLICATION")
    c1 = f169[i:f169.index("C2 FM CLASS STABILITY")]
    cm = parsed(c1, r"c2 \(sum,128,S=16\) pooled median m (\d+), "
                    r"deep-pooling class FLOOR \(committed floor band "
                    r"(\d+)\.\.(\d+) at B=2\): (True|False)", "C1 c2 line")
    c1_c2 = cm.groups()
    assert c1_c2 == WANT_C1_C2LINE, f"C1 c2 pin: {c1_c2}"
    cm = parsed(c1, r"c8 \(sum,128,S=16\) pooled median m (\d+) within "
                    r"\+/-5% of committed (\d+) \(session 4 pooled median\): "
                    r"(True|False) \(([-\d.]+)%\)", "C1 c8 line")
    c1_c8 = cm.groups()
    assert c1_c8 == WANT_C1_C8LINE, f"C1 c8 pin: {c1_c8}"
    assert "control arms free of VERIFY mismatches (frozen INVALIDATION " \
           "criterion): True" in c1, "C1 control-arms line"
    vm = parsed(c1, r"VERDICT: branch \((\w)\) replication discrepancy "
                    r"\(W1 \((\w)\) INVALID fires\); cause UNMEASURED\.",
                "C1 verdict")
    c1_verdict = vm.groups()
    assert c1_verdict == WANT_C1_VERDICT, f"C1 verdict pin: {c1_verdict}"
    print(f"  C1: c2 pooled median m {c1_c2[0]}, deep-pooling class FLOOR "
          f"(committed floor band {c1_c2[1]}..{c1_c2[2]} at B=2): "
          f"{c1_c2[3]}")
    print(f"  C1: c8 pooled median m {c1_c8[0]} within +/-5% of committed "
          f"{c1_c8[1]} (session 4 pooled median): {c1_c8[2]} "
          f"({c1_c8[3]}%)")
    print("  C1: control arms free of VERIFY mismatches (frozen "
          "INVALIDATION criterion): True")
    print(f"  C1 VERDICT: branch ({c1_verdict[0]}) replication discrepancy "
          f"(W1 ({c1_verdict[1]}) INVALID fires); cause UNMEASURED.")

    i = f169.index("C2 FM CLASS STABILITY AT 16-BLOCK GRANULARITY")
    c2 = f169[i:f169.index("W1 CUT VERDICT")]
    hm = parsed(c2, r"fm \(BATCH=3,WORK_MUL=(\d+),NDIV=(\d+)\) at "
                    r"n=([\d,]+)", "C2 fm knob header")
    c2_knob = (hm.group(1), hm.group(2), ncomma(hm.group(3)))
    assert c2_knob == WANT_C2_KNOB, f"C2 knob pin: {c2_knob}"
    assert (N_FULL * int(c2_knob[0])) // int(c2_knob[1]) == int(c2_knob[2]), \
        "C2 knob arithmetic"
    assert (int(c2_knob[0]), int(c2_knob[1])) == WANT_KS_FM[2], \
        "C2 knob pair != s165 fm smallest pair"
    bm = parsed(c2, r"the FLOOR MIDPOINT of the bracket \(([\d,]+), "
                    r"([\d,]+)\]", "C2 bracket quote")
    assert (int(ncomma(bm.group(1))), int(ncomma(bm.group(2)))) == \
        WANT_BRACKET, "C2 bracket quote != committed bracket"
    assert "the point is VIRGIN -- this cut's content is the FIRST " \
           "content at it" in c2, "C2 virgin quote"
    clm = parsed(c2, r"block classes: \[([^\]]+)\]; pooled-48 class: (\S+)",
                 "C2 block classes")
    toks = re.findall(r"'([^']+)'", clm.group(1))
    counts = dict(Counter(toks))
    pooled_cls = clm.group(2)
    assert (len(toks) == 16 and counts == WANT_C2_CLASSES[0]
            and pooled_cls == WANT_C2_CLASSES[1]), \
        f"C2 class re-count: {len(toks)} {counts} {pooled_cls}"
    bdm = parsed(c2, r"block binding min\(m-h\): ([\d. /]+?)\s+pooled-48 "
                     r"binding min\(m-h\): ([\d.]+)", "C2 binding")
    bvals = [x for x in re.split(r"[\s/]+", bdm.group(1).strip()) if x]
    assert len(bvals) == 16, f"C2 binding count: {len(bvals)}"
    bmin = min(bvals, key=Decimal)
    bmax = max(bvals, key=Decimal)
    bpooled = bdm.group(2)
    assert (bmin, bmax, bpooled) == WANT_C2_BIND, \
        f"C2 binding pin: {(bmin, bmax, bpooled)}"
    mm = parsed(c2, r"\(sum,128,S=16\) m: blocks ([\d /]+?) ; pooled-48 "
                    r"(\d+)", "C2 block m")
    mvals = [x for x in re.split(r"[\s/]+", mm.group(1).strip()) if x]
    assert (len(mvals), mvals[0], mvals[-1], mm.group(2)) == WANT_C2_M, \
        f"C2 m pin: {(len(mvals), mvals[0], mvals[-1], mm.group(2))}"
    assert "(c) CLASS-UNRESOLVED: mixed block classes, or any " \
           "IN-BAND-UNDECIDED unit, or the pooled arm differs -- FAILS; " \
           "L9 binds at 254,801 under the deep-pooling statistic" in c2, \
        "C2 verdict line"
    print(f"  C2: fm (BATCH=3,WORK_MUL={c2_knob[0]},NDIV={c2_knob[1]}) at "
          f"n={c2_knob[2]} -- knob arithmetic (1,000,003*{c2_knob[0]})//"
          f"{c2_knob[1]} = {(N_FULL * int(c2_knob[0])) // int(c2_knob[1])}; "
          f"pair == the s165 fm smallest pair {WANT_KS_FM[2]}: True; the "
          "point quote 'the point is VIRGIN -- this cut's content is the "
          "FIRST content at it' PARSED")
    print(f"  C2 block classes (re-count COMPUTED here): "
          f"{counts['CAPTURED']}x CAPTURED + "
          f"{counts['INTERMEDIATE/MIXED']}x INTERMEDIATE/MIXED + "
          f"{counts['IN-BAND-UNDECIDED']}x IN-BAND-UNDECIDED; "
          f"pooled-48 class {pooled_cls}")
    print(f"  C2 block binding min(m-h): {bmin}..{bmax} (16 values), "
          f"pooled-48 {bpooled}")
    print(f"  C2 (sum,128,S=16) m: blocks {mvals[0]}..{mvals[-1]} "
          f"(16 values), pooled-48 {mm.group(2)}")
    print("  C2 VERDICT: (c) CLASS-UNRESOLVED (mixed block classes / any "
          "IN-BAND-UNDECIDED unit / pooled arm differs -- FAILS); L9 binds "
          "at 254,801.")

    i = f169.index("W1 CUT VERDICT")
    w1 = f169[i:f169.index("W2 (pre-registered")]
    for letter_line, want in (("C1 (control replication): (b)", "b"),
                              ("C2 (fm class stability): (c)", "c")):
        assert letter_line in w1, f"W1 letter line missing: {letter_line}"
    assert "W1 (d)" in w1, "W1 letter (d) missing"
    assert "(d) INVALID (C1 (b) or the frozen INVALIDATION criterion " \
           "leaves W1 unevaluable)." in w1, "W1 (d) INVALID text"
    print("  W1 letters (parsed): C1 (control replication): (b); "
          "C2 (fm class stability): (c); W1 (d).")

    i = f169.index("5. VERDICT SUMMARY")
    s5 = f169[i:f169.index("BAR NON-INTERFERENCE", i)]
    sm = parsed(s5, r"VERDICT SUMMARY: C1 \((\w)\); C2 \((\w)\) at "
                    r"fm \(([\d,]+)\); W1 \((\w)\)\.", "verdict summary")
    summary = (sm.group(1), sm.group(2), ncomma(sm.group(3)), sm.group(4))
    assert summary == WANT_SUMMARY, f"summary pin: {summary}"
    assert "CUT VERDICT: INVALID; NOTHING MOVES." in s5, "cut verdict line"
    bbm = parsed(s5, r"The committed bracket stays EXACTLY \(([\d,]+), "
                     r"([\d,]+)\]", "summary bracket")
    assert (int(ncomma(bbm.group(1))), int(ncomma(bbm.group(2)))) == \
        WANT_BRACKET, "summary bracket != committed bracket"
    print(f"  VERDICT SUMMARY (parsed): C1 ({summary[0]}); C2 "
          f"({summary[1]}) at fm ({summary[2]}); W1 ({summary[3]}). "
          "CUT VERDICT: INVALID; NOTHING MOVES. The committed bracket "
          f"stays EXACTLY ({lo_end}, {hi_end}].")

    # ---- 3. disputed-record citations + the 16th cut's W3 reading ----
    print()
    print("SECTION 3 -- DISPUTED-RECORD CITATIONS (primary sources) AND "
          "THE 16TH CUT'S W3 READING OF THEM:")
    row = re.compile(r"^\s+(254557|254882|255045|255208)\s+\S+\s+(\d+)\s+"
                     r"(INTERMEDIATE/MIXED|CAPTURED)\s+(.*)$", re.M)
    rows = row.findall(P139)

    def keyed(n):
        out = []
        for nn, med, cls, rest in rows:
            if nn == str(n):
                sess = re.search(r"session (\d+)", rest)
                assert sess is not None, f"row session ref: {rest}"
                out.append((int(med), cls, sess.group(1)))
        return out

    r4557, r4882 = keyed(254557), keyed(254882)
    assert r4557 == WANT_R4557, f"lo dual-class rows pin: {r4557}"
    assert r4882 == WANT_R4882, f"mid dual-class rows pin: {r4882}"
    t139 = flat(P139)
    i = t139.index("lo (405,1591) at n=254,557")
    seg = t139[i:t139.index("hi (1213,4753)", i)]
    pm = re.search(r"pooled-12 median (\d+) 18-cell (\d+)\.\.(\d+) "
                   r"(CAPTURED|INTERMEDIATE/MIXED)", seg)
    assert pm is not None, "WANT NOT PARSED: lo pooled-12"
    pool12 = (int(pm.group(1)), int(pm.group(2)), int(pm.group(3)),
              pm.group(4))
    assert pool12 == WANT_LO_POOL12, f"lo pooled-12 pin: {pool12}"
    i = P139.index("mid (B=3, WM=248, NDIV=973, n=254882, 0.764644")
    seg = flat(P139[i:P139.index("\n\n", i)])
    pm = re.search(r"pooled-48 runs 01\.\.48 \(sum,128,16\) (\d+) "
                   r"18-cell (\d+)\.\.(\d+) "
                   r"(CAPTURED|INTERMEDIATE/MIXED|FLOOR)", seg)
    assert pm is not None, "WANT NOT PARSED: s139 mid pooled-48"
    pool48 = (int(pm.group(1)), int(pm.group(2)), int(pm.group(3)),
              pm.group(4))
    assert pool48 == WANT_MID_POOL48, f"mid pooled-48 pin: {pool48}"
    sm147 = parsed(P147, r"mid \(BATCH=3,WORK_MUL=(\d+),NDIV=(\d+)\) at "
                         r"n=([\d,]+)", "publication-s147.txt mid knob")
    assert (int(sm147.group(1)), int(sm147.group(2)),
            int(ncomma(sm147.group(3)))) == \
        WANT_KS_MID[2] + (WANT_KS_MID[0],), "s147 mid knob triple"
    m = parsed(P147, r"block 18-cell minima \(exact pooled medians\): "
                     r"([\d /]+?) pooled-48", "s147 block minima")
    s147_mins = [int(x) for x in m.group(1).split() if x != "/"]
    assert s147_mins == WANT_S147_MINS, f"s147 minima pin: {s147_mins}"
    m = parsed(P147, r"pooled-48 18-cell min: (\d+)", "s147 pooled min")
    assert int(m.group(1)) == WANT_S147_POOL_MIN, "s147 pooled min pin"
    m = parsed(P147, r"tolerance classes: \[([^\]]+)\]; pooled-48 "
                     r"tolerance class: (\S+)", "s147 tolerance classes")
    s147_cls = re.findall(r"'([^']+)'", m.group(1))
    assert len(s147_cls) == 16 and set(s147_cls) == {"IN-BAND-UNDECIDED"} \
        and m.group(2) == "IN-BAND-UNDECIDED", "s147 class pins"
    m = parsed(P147, r"\(sum,128,S=16\): blocks ([\d /]+?) ; pooled-48 "
                     r"(\d+)", "s147 medians")
    assert int(m.group(2)) == WANT_S147_POOL_MED, "s147 pooled median pin"
    parsed(P147, re.escape(WANT_S147_VERDICT), "s147 verdict")
    print("  PRIMARY (publication-s139.txt): lo n=254,557 dual-class "
          f"rows {r4557}; lo tenth-cut pooled-12 median {pool12[0]}, "
          f"18-cell {pool12[1]}..{pool12[2]}, class {pool12[3]}")
    print("  PRIMARY (publication-s139.txt): mid n=254,882 dual-class "
          f"rows {r4882}; mid pooled-48 median {pool48[0]}, 18-cell "
          f"{pool48[1]}..{pool48[2]}, class {pool48[3]}")
    print("  PRIMARY (publication-s147.txt): 14th cut mid content -- "
          "16x IN-BAND-UNDECIDED + pooled-48 IN-BAND-UNDECIDED; block "
          f"18-cell minima {' / '.join(str(v) for v in s147_mins)}; "
          f"pooled-48 min {WANT_S147_POOL_MIN}, pooled-48 median "
          f"{WANT_S147_POOL_MED}; verdict (parsed): {WANT_S147_VERDICT}")
    w3i = f169.index("lo n=254,557 dual-class rows")
    w3 = f169[w3i:f169.index("the 15th cut's bis content", w3i)]
    w3rows = [(a, b, c, d) for a, b, c, d in
              re.findall(r"n=(\d+): (\d+) (INTERMEDIATE/MIXED|CAPTURED) "
                         r"\(session (\d+)\)", w3)]
    assert w3rows == WANT_W3_ROWS, f"W3 row quote pin: {w3rows}"
    lp = re.search(r"lo pooled-12 (\d+) (INTERMEDIATE/MIXED|CAPTURED)", w3)
    assert lp is not None and lp.groups() == WANT_W3_LO_POOL12, \
        f"W3 lo pooled quote: {lp.groups() if lp else None}"
    mp = re.search(r"mid pooled-48 (\d+) (CAPTURED|INTERMEDIATE/MIXED) "
                   r"\(s139\); s147 pooled-48 (\d+) (IN-BAND-UNDECIDED)",
                   w3)
    assert mp is not None and mp.groups() == WANT_W3_POOLS, \
        f"W3 pooled quotes: {mp.groups() if mp else None}"
    assert "16x IN-BAND-UNDECIDED + pooled IN-BAND-UNDECIDED: True" in w3, \
        "W3 s147 in-band quote"
    confront = ([("254557", str(a), b, c) for a, b, c in r4557] +
                [("254882", str(a), b, c) for a, b, c in r4882])
    assert sorted(confront) == sorted(WANT_W3_ROWS), \
        "W3 reading != primary rows"
    assert (str(pool12[0]), pool12[3]) == WANT_W3_LO_POOL12, \
        "W3 lo pooled-12 != primary"
    assert (str(pool48[0]), pool48[3],
            str(WANT_S147_POOL_MED), "IN-BAND-UNDECIDED") == WANT_W3_POOLS, \
        "W3 pooled quotes != primary"
    print("  W3 CROSS-CHECK: the 16th cut's W3 reading of the disputed "
          "record (5 row quotes + lo pooled-12 + mid pooled-48 + s147 "
          "pooled-48) MATCHES the primary-source parse at every value -- "
          "the disputed record is UNCONTESTED between the sources.")

    # ---- 4. confrontation-spec pins (design inputs for the next slice) --
    print()
    print("SECTION 4 -- CONFRONTATION-SPEC PINS (accepted design only; "
          "design inputs, no letter):")
    fsp = flat(SPEC)
    band = parsed(SPEC, r"Combined block-unit min band over that window "
                        r"and the s139 windows: (\d+)\.\.([\d,]+) "
                        r"\(census\); per-run unit \(descriptive, s139 "
                        r"W2\): (\d+)\.\.([\d,]+)\.", "spec wander band")
    bandv = tuple(ncomma(g) for g in band.groups())
    assert bandv == WANT_SPEC_BAND, f"spec band pin: {bandv}"
    for arm in ("(a) CONTENT CONFRONTATION",
                "(b) BLOCK-GRANULARITY FLOOR",
                "(c) STATISTIC CONFRONTATION",
                "(d) CLAIM-FORM CONFRONTATION"):
        assert arm in SPEC, f"spec arm missing: {arm}"
    assert "More blocks of the same mixed shape do not confront anything; " \
           "they re-read it" in fsp, "spec arm-(b) re-read hazard quote"
    for q in ("(i) a different class statistic",
              "(ii) a tolerance rule that confronts the MEASURED wander "
              "band",
              "(iii) points whose block minima are measured single-class "
              "stable OUTSIDE the band"):
        assert q in fsp, f"spec arm-(c) option missing: {q}"
    assert "The MID-ONLY NARROWING CLAIM stays SUSPENDED" in fsp, \
        "spec arm-(d) suspension quote"
    print(f"  measured wander band (spec, parsed): block-unit "
          f"{bandv[0]}..{bandv[1]}; per-run unit {bandv[2]}..{bandv[3]} "
          "(descriptive unit)")
    print("  arms (a)-(d) headings PARSED; arm-(b) re-read hazard quote "
          "'More blocks of the same mixed shape do not confront anything; "
          "they re-read it' PARSED; arm-(c) options (i)/(ii)/(iii) and "
          "arm-(d) 'The MID-ONLY NARROWING CLAIM stays SUSPENDED' PARSED.")
    inband = sum(1 for v in bvals
                 if Decimal(bandv[0]) <= Decimal(v) <= Decimal(bandv[1]))
    assert inband == 16, f"fm binding in-band count: {inband}"
    print(f"  COMPUTED here (descriptive; arithmetic on parsed values): "
          f"{inband}/16 of this cut's fm block binding min(m-h) values "
          f"land inside the block-unit wander band {bandv[0]}..{bandv[1]} "
          "-- every one; this is an arm-(c) design input, NO class and "
          "NO letter.")

    # ---- 5. candidate cut points enumerated ----
    print()
    print("SECTION 5 -- CANDIDATE CUT POINTS (quarter grid of the "
          f"bracket ({lo_end}, {hi_end}], width {width}; enumeration "
          "only):")
    assert floor_mid == WANT_FLOOR_MID, f"floor midpoint: {floor_mid}"
    print(f"  floor midpoint re-derivation: ({lo_end}+{hi_end})//2 = "
          f"{floor_mid} (RE-DERIVED here; == the 16th cut's fm point "
          f"n={c2_knob[2]}: True)")
    srcs = {"publication-s139.txt": P139, "publication-s147.txt": P147,
            "publication-s158.txt": P158, "publication-s169.txt": P169,
            "knob-search-s164-run1.txt": KS164}
    for q in (1, 2, 3):
        cand = lo_end + (width * q) // 4
        want = WANT_QUARTER[q]
        ps = pairs_for(cand)
        gotq = (cand, len(ps), smallest(ps) if ps else None,
                len(doubles_in_box(ps)))
        assert gotq == want, f"quarter q={q} derivation: {gotq}"
        occ = {name: txt.replace(",", "").count(str(cand))
               for name, txt in srcs.items()}
        q4 = "floor midpoint (q=2)" if q == 2 else f"quarter q={q}"
        print(f"  {q4} n={cand}: pairs {gotq[1]}; smallest {gotq[2]}; "
              f"in-box same-ratio doubles {gotq[3]}; committed-source "
              f"occurrences {occ}")
        if q == 2:
            assert occ["publication-s139.txt"] == 0 and \
                occ["publication-s147.txt"] == 0 and \
                occ["publication-s158.txt"] == 0, \
                "fm point had pre-16th-cut content"
            assert occ["publication-s169.txt"] > 0, \
                "fm point content missing from publication-s169.txt"
            assert occ["knob-search-s164-run1.txt"] > 0, \
                "fm point missing from the s165 capture"
            print("    content confrontation: at s165 this candidate was "
                  "recorded as 'committed content at n=254801: NONE' "
                  "(virgin); the 16th cut then made it its cut point -- "
                  "publication-s169.txt now carries the FIRST content at "
                  "it, while publication-s139/147/158.txt carry none "
                  "(occurrences 0/0/0). The s165 virgin quote and the "
                  "16th cut's 'the point is VIRGIN -- this cut's content "
                  "is the FIRST content at it' are CONSISTENT.")
        else:
            assert all(v == 0 for v in occ.values()), \
                f"q={q} candidate has committed content: {occ}"
            print(f"    content confrontation: n={cand} has NEVER been "
                  "measured -- 0 occurrences in every parsed committed "
                  "source (virgin; enumeration only).")
    print(f"  interior committed point mid (248, 973) n=254882 is NOT on "
          f"the quarter grid (it sits at q-fraction "
          f"({254882} - {lo_end})/{width} = "
          f"{(254882 - lo_end) / width:.6f}); it carries the disputed "
          "record content parsed in section 3.")

    print()
    print("SCOPE (three-state discipline): QUOTE-ONLY confrontation "
          "census -- every citation above is committed content parsed "
          "here or arithmetic on parsed values, NOT this session's "
          "measurement. NO cut is frozen, queued or run by this script; "
          "NO protocol.txt exists yet for the seventeenth cut; the "
          "MID-ONLY NARROWING CLAIM stays SUSPENDED; the committed "
          f"bracket stays EXACTLY ({lo_end}, {hi_end}]; RULE 4 unchanged "
          "(NO vendor optimization for any vendor). The confrontation "
          "spec is ACCEPTED DESIGN ONLY; the design decisions this "
          "census feeds are NOT drafted by this script.")
    print()
    print("CENSUS COMPLETE: every asserted want parsed and matched; "
          "0 mismatches.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
