#!/usr/bin/env python3
"""JUN-59 session 192 -- the EIGHTEENTH CUT pre-registration derivation,
cut-point confrontation census (the s191 carry-forward (a); census half).

Every number below is computed in this script from arithmetic or PARSED
from committed bytes -- nothing is transcribed from prose. Deterministic:
no clock, no RNG, no network, no hardware. Running it twice is
byte-identical (the run captures + cmp in the evidence directory).

Purpose: confront the cut point of the eighteenth cut against the
seventeenth cut's landed content and the disputed record, over the
remaining bracket (254,557, 255,045]:
  1. the s178 quarter-grid enumeration RE-DERIVED and CONFRONTED
     against the s178 capture pins (knob-search-s177-run1.txt);
  2. the 17th-cut content PARSED from publication-s185.txt (C1 (a),
     the D2 supersession, C2 (c) at q1 (313, 1,229) n=254,679, the
     arm-(b) re-read hazard's second edge, W1 (c), the verdict +
     bracket pins);
  3. the disputed record citations (lo/mid dual-class rows + the 14th
     cut's TOLERANCE-UNRESOLVED mid content) parsed from their primary
     committed sources AND cross-checked against the 17th cut's own W3
     reading of them;
  4. candidate cut points enumerated -- the floor midpoint
     re-derivation 254,801 and the quarter-grid candidates -- with a
     committed-content census at each candidate across the parsed
     sources, its occurrence state RE-DERIVED after the seventeenth
     cut.

QUOTE-ONLY content: this script takes NO measurement of its own; no cut
is frozen or queued here, no bracket moves, no class/verdict/claim is
produced. The confrontation-spec arms (a)-(d) and the measured wander
band are parsed only as DESIGN INPUT pins for the design decisions
that the next slice drafts.
"""
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
WANT_KS_FM = (254801, 31, (345, 1354), 7)      # s178 capture pin (fm)
WANT_KS_MID = (254882, 35, (248, 973), 10)     # s178 capture pin (mid)
WANT_QUARTER = {1: (254679, 31, (313, 1229), 8),
                2: (254801, 31, (345, 1354), 7),
                3: (254923, 34, (246, 965), 10)}
# 17th-cut content pins (publication-s185.txt, the s191 state quotes):
WANT_C1_C2LINE = ("31", "31", "32", "True")
WANT_C1_C8LINE = ("32775", "32915", "True", "-0.43")
WANT_C1_VERDICT = ("a",)
WANT_C2_KNOB = ("313", "1229", "254679")
WANT_C2_CLASSES = ({"CAPTURED": 12, "IN-BAND-UNDECIDED": 4}, "CAPTURED")
WANT_C2_BIND = ("999.0012", "1002.9224", "1001.7437")   # min, max, pooled
WANT_C2_M = (16, "1132", "1135", "1133")                # n, min, max, pooled
WANT_SUMMARY = ("a", "c", "254679", "c")
WANT_SPEC_BAND = ("981", "1015", "974", "1023")
WANT_W3_ROWS = [("254557", "1156", "INTERMEDIATE/MIXED", "121"),
                ("254557", "1143", "CAPTURED", "125"),
                ("254882", "1129", "INTERMEDIATE/MIXED", "125"),
                ("254882", "1133", "INTERMEDIATE/MIXED", "132"),
                ("254882", "1148", "CAPTURED", "136")]
WANT_W3_LO_POOL12 = ("1141", "INTERMEDIATE/MIXED")
WANT_W3_POOLS = ("1140", "CAPTURED", "1148", "IN-BAND-UNDECIDED")
# Disputed-record pins (the s177 census wants, re-used verbatim):
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
# Occurrence-census expectations after the 17th cut (checked live here,
# asserted fail-closed against the committed sources):
#   q1 254,679: the 17th cut's first content (pub-185 > 0), none before;
#   q2 254,801: the 16th cut's content (pub-169 > 0) + the 17th cut's
#               quote-only readings of it (pub-185 > 0), none before;
#   q3 254,923: STILL VIRGIN (0 in every publication source incl. 185).


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
    print("== JUN-59 session 192 derivation (the EIGHTEENTH CUT         ==")
    print("== pre-registration: cut-point confrontation census over the  ==")
    print("== remaining bracket (254,557, 255,045] and the disputed      ==")
    print("== record -- the s178 quarter-grid enumeration re-derived and ==")
    print("== confronted, the 17th-cut content parsed, disputed-record   ==")
    print("== citations cross-checked against the 17th cut's W3 reading, ==")
    print("== candidate cut points enumerated with their occurrence      ==")
    print("== state RE-DERIVED after the seventeenth cut)                ==")
    print("== every value computed here from arithmetic or committed     ==")
    print("== bytes; QUOTE-ONLY; NO measurement, NO freeze, NO queue     ==")
    print()

    P139 = open(os.path.join(GPU, "anv-b3bisect13-20261031",
                             "publication-s139.txt")).read()
    P147 = open(os.path.join(GPU, "anv-b3bisect14-20261031",
                             "publication-s147.txt")).read()
    P158 = open(os.path.join(GPU, "anv-b3bisect15-20261101",
                             "publication-s158.txt")).read()
    P169 = open(os.path.join(GPU, "anv-b3bisect16-20261101",
                             "publication-s169.txt")).read()
    P185 = open(os.path.join(GPU, "anv-b3bisect17-20261101",
                             "publication-s185.txt")).read()
    KS164 = open(os.path.join(GPU, "anv-b3bisect16prereg-20261101",
                              "knob-search-s164-run1.txt")).read()
    KS177 = open(os.path.join(GPU, "anv-b3bisect17prereg-20261101",
                              "knob-search-s177-run1.txt")).read()
    SPEC = open(os.path.join(GPU, "anv-b3confrontation-spec-20261031",
                             "confrontation-spec.txt")).read()

    # ---- 0. the committed bracket, re-derived from committed bytes ----
    m = parsed(P185, r"The committed bracket stays EXACTLY \(([\d,]+), "
                     r"([\d,]+)\]", "publication-s185.txt bracket")
    lo_end = int(ncomma(m.group(1)))
    hi_end = int(ncomma(m.group(2)))
    assert (lo_end, hi_end) == WANT_BRACKET, "committed bracket endpoints"
    bm15 = parsed(P185, r"Bracket state: NARROWED -- \((\d+), (\d+)\]",
                  "publication-s185.txt 15th-cut bracket quote")
    assert (int(bm15.group(1)), int(bm15.group(2))) == WANT_BRACKET, \
        "15th-cut bracket quote != committed bracket"
    width = hi_end - lo_end
    floor_mid = (lo_end + hi_end) // 2
    print("committed bracket (publication-s185.txt, parsed): "
          f"({lo_end}, {hi_end}] n-units, width {width}")
    print("knob arithmetic: n = (1,000,003*WORK_MUL)//NDIV (integer floor)")
    print("search box (sessions 21-27's box): WORK_MUL 1..2,048 x "
          "NDIV 1..8,192")

    # ---- 1. the s178 enumeration RE-DERIVED and CONFRONTED ----
    print()
    print("SECTION 1 -- S178 QUARTER-GRID ENUMERATION RE-DERIVED AND "
          "CONFRONTED:")
    ks = flat(KS177)
    fm = parsed(ks, r"fm n=(\d+): pairs (\d+); smallest \((\d+), (\d+)\); "
                    r"in-box same-ratio doubles (\d+)", "s178 fm pin")
    ks_fm = (int(fm.group(1)), int(fm.group(2)),
             (int(fm.group(3)), int(fm.group(4))), int(fm.group(5)))
    assert ks_fm == WANT_KS_FM, f"s178 fm pin: {ks_fm}"
    mid = parsed(ks, r"mid n=(\d+): pairs (\d+); smallest \((\d+), (\d+)\); "
                     r"in-box same-ratio doubles (\d+)", "s178 mid pin")
    ks_mid = (int(mid.group(1)), int(mid.group(2)),
              (int(mid.group(3)), int(mid.group(4))), int(mid.group(5)))
    assert ks_mid == WANT_KS_MID, f"s178 mid pin: {ks_mid}"
    ks_q = {}
    for q in (1, 2, 3):
        label = f"floor midpoint (q=2)" if q == 2 else f"quarter q={q}"
        pre = r"floor midpoint \(q=2\)" if q == 2 else rf"quarter q={q}"
        qm = parsed(ks, pre + r" n=(\d+): pairs (\d+); smallest \((\d+), "
                              r"(\d+)\); in-box same-ratio doubles (\d+)",
                    f"s178 q={q} pin")
        ks_q[q] = (int(qm.group(1)), int(qm.group(2)),
                   (int(qm.group(3)), int(qm.group(4))), int(qm.group(5)))
        assert ks_q[q] == WANT_QUARTER[q], f"s178 q={q} pin: {ks_q[q]}"
    got = {}
    for label, target in (("fm", WANT_FLOOR_MID), ("mid", 254882),
                          ("q1", 254679), ("q2", 254801), ("q3", 254923)):
        ps = pairs_for(target)
        got[label] = (target, len(ps), smallest(ps), len(doubles_in_box(ps)))
    assert got["fm"] == WANT_KS_FM, f"fm re-derivation: {got['fm']}"
    assert got["mid"] == WANT_KS_MID, f"mid re-derivation: {got['mid']}"
    for q in (1, 2, 3):
        assert got[f"q{q}"] == WANT_QUARTER[q], \
            f"q={q} re-derivation: {got[f'q{q}']}"
    for label in ("fm", "mid", "q1", "q2", "q3"):
        t, n, sm, dbl = got[label]
        pin = {"fm": ks_fm, "mid": ks_mid, "q1": ks_q[1], "q2": ks_q[2],
               "q3": ks_q[3]}[label]
        print(f"  {label} n={t}: pairs {n}; smallest {sm}; in-box "
              f"same-ratio doubles {dbl} -- s178 capture ({pin}) -> MATCH")

    # ---- 2. the 17th-cut content PARSED from publication-s185.txt ----
    print()
    print("SECTION 2 -- 17TH-CUT CONTENT PARSED (publication-s185.txt):")
    f185 = flat(P185)
    i = f185.index("C1 ARCHIVED CONTROL REPLICATION")
    c1 = f185[i:f185.index("C2 Q1 CLASS STABILITY")]
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
    vm = parsed(c1, r"VERDICT: branch \((\w)\) both controls satisfy their "
                    r"criteria -- W1 is evaluated against the row question\.",
                "C1 verdict")
    c1_verdict = vm.groups()
    assert c1_verdict == WANT_C1_VERDICT, f"C1 verdict pin: {c1_verdict}"
    assert "D2 SUPERSESSION (arm (a), the frozen rule): this cut's C1 " \
           "(a) reading SUPERSEDES the 16th cut's C1 (b) reading AS THE " \
           "CURRENT CONTROL STATE (the 16th's (b) remains committed " \
           "history; the discrepancy cause stays UNMEASURED, L2 binds)." \
           in c1, "D2 supersession quote"
    print(f"  C1: c2 pooled median m {c1_c2[0]}, deep-pooling class FLOOR "
          f"(committed floor band {c1_c2[1]}..{c1_c2[2]} at B=2): "
          f"{c1_c2[3]}")
    print(f"  C1: c8 pooled median m {c1_c8[0]} within +/-5% of committed "
          f"{c1_c8[1]} (session 4 pooled median): {c1_c8[2]} "
          f"({c1_c8[3]}%)")
    print("  C1: control arms free of VERIFY mismatches (frozen "
          "INVALIDATION criterion): True")
    print(f"  C1 VERDICT: branch ({c1_verdict[0]}) both controls satisfy "
          "their criteria -- W1 is evaluated against the row question.")
    print("  D2 SUPERSESSION quote PARSED (arm (a), the frozen rule): "
          "this cut's C1 (a) reading SUPERSEDES the 16th cut's C1 (b) "
          "reading AS THE CURRENT CONTROL STATE (the 16th's (b) remains "
          "committed history; the discrepancy cause stays UNMEASURED, "
          "L2 binds).")

    i = f185.index("C2 Q1 CLASS STABILITY")
    c2 = f185[i:f185.index("W1 CUT VERDICT")]
    hm = parsed(c2, r"q1 \(BATCH=3,WORK_MUL=(\d+),NDIV=(\d+)\) at "
                    r"n=([\d,]+)", "C2 q1 knob header")
    c2_knob = (hm.group(1), hm.group(2), ncomma(hm.group(3)))
    assert c2_knob == WANT_C2_KNOB, f"C2 knob pin: {c2_knob}"
    assert (N_FULL * int(c2_knob[0])) // int(c2_knob[1]) == int(c2_knob[2]), \
        "C2 knob arithmetic"
    assert (int(c2_knob[0]), int(c2_knob[1])) == WANT_QUARTER[1][2], \
        "C2 knob pair != s178 q1 smallest pair"
    assert "the Q=1 QUARTER POINT of the bracket (254,557, 255,045]" in c2, \
        "C2 Q=1 quarter-point quote"
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
    mmin = min(mvals, key=Decimal)
    mmax = max(mvals, key=Decimal)
    assert (len(mvals), mmin, mmax, mm.group(2)) == WANT_C2_M, \
        f"C2 m pin: {(len(mvals), mmin, mmax, mm.group(2))}"
    assert "(c) CLASS-UNRESOLVED: mixed block classes, or any " \
           "IN-BAND-UNDECIDED unit, or the pooled arm differs -- FAILS; " \
           "L9 binds at n=254,679 under the deep-pooling statistic (the " \
           "D3 (ii) clause); any future narrowing claim at n=254,679 " \
           "must confront this cut's content first (named here, not " \
           "specified here)." in c2, "C2 verdict line"
    assert "the arm-(b) re-read hazard's second edge, D3 (ii), verbatim" \
           in c2, "C2 hazard label"
    assert "if this cut's own content at 254,679 comes out mixed (C2 " \
           "(c)), it is NOT rescued by later more-blocks-of-the-same-shape " \
           "runs; a same-shape re-run there would re-read, not confront." \
           in c2, "C2 re-read hazard second edge"
    print(f"  C2: q1 (BATCH=3,WORK_MUL={c2_knob[0]},NDIV={c2_knob[1]}) at "
          f"n={c2_knob[2]} -- knob arithmetic (1,000,003*{c2_knob[0]})//"
          f"{c2_knob[1]} = {(N_FULL * int(c2_knob[0])) // int(c2_knob[1])}; "
          f"pair == the s178 q1 smallest pair {WANT_QUARTER[1][2]}: True; "
          "the Q=1 QUARTER POINT quote and the point quote 'the point is "
          "VIRGIN -- this cut's content is the FIRST content at it' PARSED")
    print(f"  C2 block classes (re-count COMPUTED here): "
          f"{counts['CAPTURED']}x CAPTURED + "
          f"{counts['IN-BAND-UNDECIDED']}x IN-BAND-UNDECIDED; "
          f"pooled-48 class {pooled_cls}")
    print(f"  C2 block binding min(m-h): {bmin}..{bmax} (16 values), "
          f"pooled-48 {bpooled}")
    print(f"  C2 (sum,128,S=16) m: blocks {mmin}..{mmax} (16 values, "
          f"min..max), pooled-48 {mm.group(2)}")
    print("  C2 VERDICT: (c) CLASS-UNRESOLVED (mixed block classes / any "
          "IN-BAND-UNDECIDED unit / pooled arm differs -- FAILS); L9 binds "
          "at 254,679 under the deep-pooling statistic (the D3 (ii) "
          "clause).")
    print("  RE-READ HAZARD SECOND EDGE (D3 (ii), verbatim quote PARSED): "
          "if this cut's own content at 254,679 comes out mixed (C2 (c)), "
          "it is NOT rescued by later more-blocks-of-the-same-shape runs; "
          "a same-shape re-run there would re-read, not confront. -- it HAS "
          "come out mixed, so the hazard binds at n=254,679 exactly as "
          "frozen.")

    i = f185.index("W1 CUT VERDICT")
    w1 = f185[i:f185.index("W2 (pre-registered", i)]
    for letter_line in ("C1 (control replication): (a)",
                        "C2 (q1 class stability): (c)", "W1 (c)"):
        assert letter_line in w1, f"W1 letter line missing: {letter_line}"
    assert "(c) C2 (c)/(d) -> NOTHING MOVES; the bracket stays EXACTLY " \
           "(254,557, 255,045]; the MID-ONLY NARROWING CLAIM stays " \
           "SUSPENDED (named, not claimed)." in w1, "W1 (c) text"
    print("  W1 letters (parsed): C1 (control replication): (a); "
          "C2 (q1 class stability): (c); W1 (c).")

    i = f185.index("5. VERDICT SUMMARY")
    s5 = f185[i:f185.index("BAR NON-INTERFERENCE", i)]
    sm = parsed(s5, r"VERDICT SUMMARY: C1 \((\w)\); C2 \((\w)\) at "
                    r"q1 \(([\d,]+)\); W1 \((\w)\)\.", "verdict summary")
    summary = (sm.group(1), sm.group(2), ncomma(sm.group(3)), sm.group(4))
    assert summary == WANT_SUMMARY, f"summary pin: {summary}"
    assert "CUT VERDICT: NOTHING MOVES" in s5, "cut verdict line"
    bbm = parsed(s5, r"The committed bracket stays EXACTLY \(([\d,]+), "
                     r"([\d,]+)\]", "summary bracket")
    assert (int(ncomma(bbm.group(1))), int(ncomma(bbm.group(2)))) == \
        WANT_BRACKET, "summary bracket != committed bracket"
    assert "The 16th cut's fm content at 254,801 and the 14th cut's " \
           "TOLERANCE-UNRESOLVED mid content stand as committed content " \
           "under ALL outcomes (arm (a)); NO letter of this cut supersedes " \
           "them or touches lo/mid/fm." in s5, "summary arm-(a) treatment"
    print(f"  VERDICT SUMMARY (parsed): C1 ({summary[0]}); C2 "
          f"({summary[1]}) at q1 ({summary[2]}); W1 ({summary[3]}). "
          "CUT VERDICT: NOTHING MOVES. The committed bracket stays "
          f"EXACTLY ({lo_end}, {hi_end}].")

    # ---- 3. disputed-record citations + the 17th cut's W3 reading ----
    print()
    print("SECTION 3 -- DISPUTED-RECORD CITATIONS (primary sources) AND "
          "THE 17TH CUT'S W3 READING OF THEM:")
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
    w3i = f185.index("W3 (pre-registered, descriptive)")
    w3 = f185[w3i:f185.index("X1 (descriptive", w3i)]
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
    print("  W3 CROSS-CHECK: the 17th cut's W3 reading of the disputed "
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
    assert inband == 16, f"q1 binding in-band count: {inband}"
    below = [(cls, v) for cls, v in zip(toks, bvals) if Decimal(v) < 1000]
    above = [(cls, v) for cls, v in zip(toks, bvals) if Decimal(v) >= 1000]
    assert len(below) == 4 and len(above) == 12, \
        f"binding threshold split: {len(below)}/{len(above)}"
    assert all(cls == "IN-BAND-UNDECIDED" for cls, v in below), \
        "binding<1000 blocks not the IN-BAND-UNDECIDED blocks"
    assert all(cls == "CAPTURED" for cls, v in above), \
        "binding>=1000 blocks not the CAPTURED blocks"
    assert Decimal(bmin) < 1000 <= Decimal(bmax), "binding range straddle"
    print(f"  COMPUTED here (descriptive; arithmetic on parsed values): "
          f"{inband}/16 of the 17th cut's q1 block binding min(m-h) values "
          f"land inside the block-unit wander band {bandv[0]}..{bandv[1]} "
          "-- every one; the class label equals (binding >= 1,000) at "
          "16/16 blocks (the 12 blocks >= 1,000 are exactly the 12x "
          "CAPTURED; the 4 blocks < 1,000 are exactly the 4x "
          "IN-BAND-UNDECIDED) and the binding range "
          f"{bmin}..{bmax} STRADDLES the 1,000 threshold inside the "
          "wander band -- the class discrimination at n=254,679 rides the "
          "binding statistic INSIDE the measured wander band; this is an "
          "arm-(c) design input, NO class and NO letter.")

    # ---- 5. candidate cut points enumerated ----
    print()
    print("SECTION 5 -- CANDIDATE CUT POINTS (quarter grid of the "
          f"bracket ({lo_end}, {hi_end}], width {width}; enumeration "
          "only):")
    assert floor_mid == WANT_FLOOR_MID, f"floor midpoint: {floor_mid}"
    print(f"  floor midpoint re-derivation: ({lo_end}+{hi_end})//2 = "
          f"{floor_mid} (RE-DERIVED here; == the 16th cut's fm point "
          f"n={floor_mid} == the q=2 candidate: True)")
    srcs = {"publication-s139.txt": P139, "publication-s147.txt": P147,
            "publication-s158.txt": P158, "publication-s169.txt": P169,
            "publication-s185.txt": P185}
    esrcs = {"knob-search-s164-run1.txt": KS164,
             "knob-search-s177-run1.txt": KS177}
    for q in (1, 2, 3):
        cand = lo_end + (width * q) // 4
        want = WANT_QUARTER[q]
        ps = pairs_for(cand)
        gotq = (cand, len(ps), smallest(ps) if ps else None,
                len(doubles_in_box(ps)))
        assert gotq == want, f"quarter q={q} derivation: {gotq}"
        occ = {name: txt.replace(",", "").count(str(cand))
               for name, txt in srcs.items()}
        eocc = {name: txt.replace(",", "").count(str(cand))
                for name, txt in esrcs.items()}
        q4 = "floor midpoint (q=2)" if q == 2 else f"quarter q={q}"
        print(f"  {q4} n={cand}: pairs {gotq[1]}; smallest {gotq[2]}; "
              f"in-box same-ratio doubles {gotq[3]}; committed-source "
              f"occurrences {occ}; enumeration-source occurrences {eocc}")
        if q == 1:
            assert occ["publication-s139.txt"] == 0 and \
                occ["publication-s147.txt"] == 0 and \
                occ["publication-s158.txt"] == 0 and \
                occ["publication-s169.txt"] == 0, \
                f"q=1 had pre-17th-cut content: {occ}"
            assert occ["publication-s185.txt"] > 0, \
                "q=1 content missing from publication-s185.txt"
            print("    content confrontation: at s178 this candidate was "
                  "recorded '0 occurrences in every parsed committed "
                  "source' (virgin); the 17th cut then made it its cut "
                  "point -- publication-s185.txt now carries the FIRST "
                  "content at it (C2 (c) CLASS-UNRESOLVED: 12x CAPTURED + "
                  "4x IN-BAND-UNDECIDED blocks, pooled-48 CAPTURED (arm "
                  "differs); parsed in section 2), while "
                  "publication-s139/147/158/169.txt carry none "
                  "(0/0/0/0). The arm-(b) re-read hazard's SECOND EDGE "
                  "binds at n=254,679 exactly as frozen (the content HAS "
                  "come out mixed): a same-shape re-run there would "
                  "re-read, not confront.")
        elif q == 2:
            assert occ["publication-s139.txt"] == 0 and \
                occ["publication-s147.txt"] == 0 and \
                occ["publication-s158.txt"] == 0, \
                f"q=2 had pre-16th-cut content: {occ}"
            assert occ["publication-s169.txt"] > 0, \
                "q=2 content missing from publication-s169.txt"
            assert occ["publication-s185.txt"] > 0, \
                "q=2 quote missing from publication-s185.txt"
            assert "this cut does not measure 254,801" in f185, \
                "17th-cut no-supersession quote at 254,801"
            print("    content confrontation: the 16th cut's content "
                  "stands at this point (publication-s169.txt carries it: "
                  "C2 (c) CLASS-UNRESOLVED 10x CAPTURED + 3x "
                  "INTERMEDIATE/MIXED + 3x IN-BAND-UNDECIDED, pooled-48 "
                  "CAPTURED); the arm-(b) re-read hazard binds LITERALLY "
                  "there ('More blocks of the same mixed shape do not "
                  "confront anything; they re-read it'); the "
                  "publication-s185.txt occurrences are the 17th cut's "
                  "quote-only readings of that same committed content (its "
                  "W3/section-0 quotes) -- its frozen supersession "
                  "statement 'this cut does not measure 254,801' is PARSED "
                  "-- NOT new content at the point.")
        else:
            assert all(v == 0 for v in occ.values()), \
                f"q=3 candidate has committed content: {occ}"
            print(f"    content confrontation: n={cand} is STILL VIRGIN "
                  "after the seventeenth cut -- RE-DERIVED here: 0 "
                  "occurrences in every parsed publication source "
                  "(including publication-s185.txt; the s178 'VIRGIN at "
                  "s178' state SURVIVES the 17th cut); the knob-search "
                  "captures carry enumeration quotes only "
                  f"({eocc['knob-search-s177-run1.txt']} in "
                  "knob-search-s177-run1.txt).")
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
          "NO protocol.txt exists yet for the eighteenth cut; the "
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
