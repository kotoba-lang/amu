#!/usr/bin/env python3
"""JUN-59 session 203 -- the NINETEENTH CUT pre-registration derivation,
cut-point confrontation census (the s202 carry-forward (a); census half).

Every number below is computed in this script from arithmetic or PARSED
from committed bytes -- nothing is transcribed from prose. Deterministic:
no clock, no RNG, no network, no hardware. Running it twice is
byte-identical (the run captures + cmp in the evidence directory).

Purpose: confront the cut point of the nineteenth cut against the
eighteenth cut's landed content and the disputed record, over the
remaining bracket (254,923, 255,045]:
  1. the s192 quarter-grid enumeration RE-DERIVED and CONFRONTED
     against the s192 capture pins (knob-search-s192-run1.txt), and
     the NEW bracket's endpoints enumerated (the upper endpoint's
     in-box pair/doubles census is FRESH -- not enumerated in any
     committed source before this census);
  2. the 18th-cut content PARSED from publication-s197.txt (C1 (a),
     the D2 control-state confrontation, C2 (a) at q3 (246, 965)
     n=254,923, W1 (b) + the bracket narrowing + the frozen D1 clip
     note, the W3 cross-binary hazard + L8, X1, the verdict +
     bracket pins);
  3. the disputed record citations (lo/mid dual-class rows + the 14th
     cut's TOLERANCE-UNRESOLVED mid content) parsed from their primary
     committed sources AND cross-checked against the 18th cut's own W3
     reading of them;
  4. candidate cut points enumerated -- the NEW quarter-grid
     candidates of (254,923, 255,045] -- with a committed-content
     census at each candidate across the parsed sources, its
     occurrence state RE-DERIVED after the eighteenth cut, plus the
     bracket endpoints' content confrontation (the 13th/15th cuts at
     bis (255,045); the 18th cut at q3 (254,923)).

QUOTE-ONLY content: this script takes NO measurement of its own; no cut
is frozen or queued here, no bracket moves, no class/verdict/claim is
produced. The confrontation-spec arms (a)-(d) and the measured wander
band are parsed only as DESIGN INPUT pins for the design decisions
that the next slice drafts. One named correction: the s202
reconnaissance quote misattributed the summary 'C1 (a); C2 (b) at bis
(255,045); W1 (a)' to publication-s139.txt; this census confronts the
committed bytes (that summary is publication-s158.txt's -- the 15th
cut's -- and publication-s139.txt's own summary is 'C1 (a); C2 (c) at
bis (255,045); C3 (c) at mid; W1 (c)'), per the s191 rule that the
census is the authority for every derived number.
"""
import os
import re
from collections import Counter
from decimal import Decimal
from math import gcd

HERE = os.path.dirname(os.path.abspath(__file__))
GPU = os.path.join(HERE, "..")

N_FULL = 1_000_003
BOX_WM = range(1, 2049)
BOX_NDIV = range(1, 8193)

# Frozen citation wants (pin-like): the PARSE must match these committed
# values or the script aborts fail-closed.
WANT_NEW_BRACKET = (254923, 255045)
WANT_OLD_BRACKET = (254557, 255045)
WANT_BRACKET_STATES = {("254923", "255045"): 2, ("254557", "255045"): 1}
WANT_S192 = {"fm": (254801, 31, (345, 1354), 7),
             "mid": (254882, 35, (248, 973), 10),
             "q1": (254679, 31, (313, 1229), 8),
             "q2": (254801, 31, (345, 1354), 7),
             "q3": (254923, 34, (246, 965), 10)}
WANT_HI = (255045, 33, (316, 1239), 8)   # doubles 8 = FRESH (this census)
WANT_SPEC_BIS = ("316", "1239", "255045")
# 18th-cut content pins (publication-s197.txt):
WANT_C1_C2LINE = ("31", "31", "32", "True")
WANT_C1_C8LINE = ("32778", "32915", "True", "-0.42")
WANT_C1_VERDICT = ("a",)
WANT_C2_KNOB = ("246", "965", "254923")
WANT_C2_CLASSES = ({"INTERMEDIATE/MIXED": 16}, "INTERMEDIATE/MIXED")
WANT_C2_BIND = ("995.1326", "998.0538", "997.7700")   # min, max, pooled
WANT_C2_M = (16, "1131", "1132", "1132")               # n, min, max, pooled
WANT_SUMMARY = ("a", "a", "254923", "b")
WANT_X1_Q3 = ("309798", "503223.5", "193425.5", "62.4", "48")
WANT_SPEC_BAND = ("981", "1015", "974", "1023")
# Disputed-record pins (the s192 wants, re-used verbatim):
WANT_R4557 = [(1156, "INTERMEDIATE/MIXED", "121"),
              (1143, "CAPTURED", "125")]
WANT_R4882 = [(1129, "INTERMEDIATE/MIXED", "125"),
              (1133, "INTERMEDIATE/MIXED", "132"),
              (1148, "CAPTURED", "136")]
WANT_LO_POOL12 = (1141, 998, 1452, "INTERMEDIATE/MIXED")
WANT_MID_POOL48 = (1140, 1001, 1442, "CAPTURED")
WANT_S147_MINS = [992, 1006, 996, 1000, 1002, 993, 1002, 991,
                  1006, 996, 997, 996, 1002, 999, 995, 991]
WANT_S147_POOL_MIN = 1005
WANT_S147_POOL_MED = 1148
WANT_S147_VERDICT = ("(c) TOLERANCE-UNRESOLVED: any in-band minimum or "
                     "mixed classes -- FAILS; L9 binds at mid at 16 blocks "
                     "under the tolerance rule too.")
# The 18th cut's W3 reading of the disputed record:
WANT_W3_ROWS = [("254557", "1156", "INTERMEDIATE/MIXED", "121"),
                ("254557", "1143", "CAPTURED", "125"),
                ("254882", "1129", "INTERMEDIATE/MIXED", "125"),
                ("254882", "1133", "INTERMEDIATE/MIXED", "132"),
                ("254882", "1148", "CAPTURED", "136")]
WANT_W3_LO_POOL12 = ("1141", "INTERMEDIATE/MIXED")
WANT_W3_POOLS = ("1140", "CAPTURED", "1148", "IN-BAND-UNDECIDED")
# Hi-endpoint (bis 255,045) content pins:
WANT_P139_SUMMARY = ("VERDICT SUMMARY: C1 (a); C2 (c) at bis (255,045); "
                     "C3 (c) at mid; W1 (c).")
WANT_P158_SUMMARY = ("VERDICT SUMMARY: C1 (a); C2 (b) at bis (255,045); "
                     "W1 (a).")
WANT_P158_CLASSES = ({"CAPTURED": 16}, "CAPTURED")
WANT_P158_POOLED_BIND = "1009.6912"
WANT_SPEC_BIS_CONTENT = ("7x CAPTURED + 9x INTERMEDIATE/MIXED blocks",
                         "pooled-48 CAPTURED 1,148 (18-cell 1,006..1,449)")
# Candidate quarter grid of the NEW bracket (fresh; pinned from this
# session's development recon and re-derived by both captured runs):
WANT_QUARTER = {1: (254953, 31, (296, 1161), 8),
                2: (254984, 29, (307, 1204), 6),
                3: (255014, 25, (674, 2643), 4)}
WANT_FLOOR_MID = 254984
# Occurrence-census wants (comma-stripped substring counts over the
# frozen committed bytes; checked live here, asserted fail-closed):
WANT_OCC = {
    254953: {"publication-s139.txt": 0, "publication-s147.txt": 0,
             "publication-s158.txt": 0, "publication-s169.txt": 0,
             "publication-s185.txt": 0, "publication-s197.txt": 0},
    254984: {"publication-s139.txt": 0, "publication-s147.txt": 0,
             "publication-s158.txt": 0, "publication-s169.txt": 0,
             "publication-s185.txt": 0, "publication-s197.txt": 0},
    255014: {"publication-s139.txt": 0, "publication-s147.txt": 0,
             "publication-s158.txt": 0, "publication-s169.txt": 0,
             "publication-s185.txt": 0, "publication-s197.txt": 0},
    254923: {"publication-s139.txt": 0, "publication-s147.txt": 0,
             "publication-s158.txt": 0, "publication-s169.txt": 0,
             "publication-s185.txt": 0, "publication-s197.txt": 26},
    255045: {"publication-s139.txt": 10, "publication-s147.txt": 5,
             "publication-s158.txt": 16, "publication-s169.txt": 8,
             "publication-s185.txt": 10, "publication-s197.txt": 13},
    254679: {"publication-s139.txt": 0, "publication-s147.txt": 0,
             "publication-s158.txt": 0, "publication-s169.txt": 0,
             "publication-s185.txt": 19, "publication-s197.txt": 12},
    254801: {"publication-s139.txt": 0, "publication-s147.txt": 0,
             "publication-s158.txt": 0, "publication-s169.txt": 15,
             "publication-s185.txt": 11, "publication-s197.txt": 9},
    254882: {"publication-s139.txt": 8, "publication-s147.txt": 15,
             "publication-s158.txt": 8, "publication-s169.txt": 10,
             "publication-s185.txt": 5, "publication-s197.txt": 7},
}
WANT_E_OCC = {
    254953: {"knob-search-s177-run1.txt": 0, "knob-search-s192-run1.txt": 0},
    254984: {"knob-search-s177-run1.txt": 0, "knob-search-s192-run1.txt": 0},
    255014: {"knob-search-s177-run1.txt": 0, "knob-search-s192-run1.txt": 0},
    254923: {"knob-search-s177-run1.txt": 2, "knob-search-s192-run1.txt": 4},
    255045: {"knob-search-s177-run1.txt": 6, "knob-search-s192-run1.txt": 6},
    254679: {"knob-search-s177-run1.txt": 2, "knob-search-s192-run1.txt": 11},
    254801: {"knob-search-s177-run1.txt": 10, "knob-search-s192-run1.txt": 8},
    254882: {"knob-search-s177-run1.txt": 5, "knob-search-s192-run1.txt": 5},
}

W = 0


def want(cond, label):
    global W
    W += 1
    assert cond, f"WANT NOT MATCHED: {label}"


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
    want(mm is not None, f"WANT NOT PARSED: {label}")
    return mm


def ncomma(s):
    return s.replace(",", "")


def main():
    print("== JUN-59 session 203 derivation (the NINETEENTH CUT         ==")
    print("== pre-registration: cut-point confrontation census over the  ==")
    print("== remaining bracket (254,923, 255,045] and the disputed      ==")
    print("== record -- the s192 quarter-grid enumeration re-derived and ==")
    print("== confronted, the 18th-cut content parsed, disputed-record   ==")
    print("== citations cross-checked against the 18th cut's W3 reading, ==")
    print("== candidate cut points enumerated with their occurrence      ==")
    print("== state RE-DERIVED after the eighteenth cut)                 ==")
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
    P197 = open(os.path.join(GPU, "anv-b3bisect18-20261101",
                             "publication-s197.txt")).read()
    KS177 = open(os.path.join(GPU, "anv-b3bisect17prereg-20261101",
                              "knob-search-s177-run1.txt")).read()
    KS192 = open(os.path.join(GPU, "anv-b3bisect18prereg-20261101",
                              "knob-search-s192-run1.txt")).read()
    SPEC = open(os.path.join(GPU, "anv-b3confrontation-spec-20261031",
                             "confrontation-spec.txt")).read()

    # ---- 0. the committed bracket, re-derived from committed bytes ----
    f197 = flat(P197)
    states = re.findall(r"Bracket state: NARROWED -- \(([0-9,]+), ([0-9,]+)\]",
                        f197)
    scount = Counter((ncomma(a), ncomma(b)) for a, b in states)
    want(scount == Counter(WANT_BRACKET_STATES),
         f"bracket-state occurrence census: {scount}")
    new_states = [s for s in states if (ncomma(s[0]), ncomma(s[1])) ==
                  tuple(str(x) for x in WANT_NEW_BRACKET)]
    want(len(new_states) == 2, "new-bracket state count")
    lo_end, hi_end = WANT_NEW_BRACKET
    old_states = [s for s in states if (ncomma(s[0]), ncomma(s[1])) ==
                  tuple(str(x) for x in WANT_OLD_BRACKET)]
    want(len(old_states) == 1, "old-bracket quote count")
    width = hi_end - lo_end
    old_width = WANT_OLD_BRACKET[1] - WANT_OLD_BRACKET[0]
    want(width == 122 and old_width == 488, "bracket widths")
    floor_mid = (lo_end + hi_end) // 2
    want(floor_mid == WANT_FLOOR_MID, f"floor midpoint: {floor_mid}")
    want(hi_end - lo_end == 122 and lo_end - WANT_OLD_BRACKET[0] == 366,
         "clip arithmetic 122/366")
    print("committed bracket (publication-s197.txt, parsed): "
          f"({lo_end}, {hi_end}] n-units, width {width}; the old "
          f"bracket quote ({WANT_OLD_BRACKET[0]}, {WANT_OLD_BRACKET[1]}] "
          f"width {old_width} appears once as committed history "
          "(bracket-state occurrence census "
          f"{dict(scount)} == the pin: MATCH)")
    print("knob arithmetic: n = (1,000,003*WORK_MUL)//NDIV (integer floor)")
    print("search box (sessions 21-27's box): WORK_MUL 1..2,048 x "
          "NDIV 1..8,192")

    # ---- 1. the s192 enumeration RE-DERIVED and CONFRONTED ----
    print()
    print("SECTION 1 -- S192 QUARTER-GRID ENUMERATION RE-DERIVED AND "
          "CONFRONTED:")
    ks = flat(KS192)

    def ks_pin(label, pre):
        mm = parsed(ks, pre + r" n=(\d+): pairs (\d+); smallest \((\d+), "
                              r"(\d+)\); in-box same-ratio doubles (\d+)",
                    f"s192 {label} pin")
        return (int(mm.group(1)), int(mm.group(2)),
                (int(mm.group(3)), int(mm.group(4))), int(mm.group(5)))
    pins = {"fm": ks_pin("fm", "fm"),
            "mid": ks_pin("mid", "mid"),
            "q1": ks_pin("q1", "quarter q=1"),
            "q2": ks_pin("q2", "floor midpoint \\(q=2\\)"),
            "q3": ks_pin("q3", "quarter q=3")}
    for label in ("fm", "mid", "q1", "q2", "q3"):
        want(pins[label] == WANT_S192[label],
             f"s192 {label} pin: {pins[label]}")
    got = {}
    for label, target in (("fm", WANT_S192["fm"][0]), ("mid", 254882),
                          ("q1", 254679), ("q2", 254801), ("q3", 254923)):
        ps = pairs_for(target)
        got[label] = (target, len(ps), smallest(ps), len(doubles_in_box(ps)))
    for label in ("fm", "mid", "q1", "q2", "q3"):
        want(got[label] == WANT_S192[label],
             f"{label} re-derivation: {got[label]}")
        t, n, sm, dbl = got[label]
        print(f"  {label} n={t}: pairs {n}; smallest {sm}; in-box "
              f"same-ratio doubles {dbl} -- s192 capture ({pins[label]}) "
              "-> MATCH")
    want(got["q2"] == got["fm"], "q2 == fm")

    # ---- the NEW bracket's endpoints enumerated ----
    print()
    print("SECTION 1b -- THE NEW BRACKET'S ENDPOINTS ENUMERATED:")
    want(pins["q3"][0] == lo_end, "lo endpoint == s192 q3")
    ps_lo = pairs_for(lo_end)
    lo_enum = (lo_end, len(ps_lo), smallest(ps_lo), len(doubles_in_box(ps_lo)))
    want(lo_enum == WANT_S192["q3"], f"lo endpoint enum: {lo_enum}")
    print(f"  lo n={lo_end} (the NEW lower endpoint; the 18th cut's cut "
          f"point): pairs {lo_enum[1]}; smallest {lo_enum[2]}; in-box "
          f"same-ratio doubles {lo_enum[3]} -- == the s192 q3 capture "
          "-> MATCH")
    ps_hi = pairs_for(hi_end)
    hi_enum = (hi_end, len(ps_hi), smallest(ps_hi), len(doubles_in_box(ps_hi)))
    want(hi_enum == WANT_HI, f"hi endpoint enum: {hi_enum}")
    want((N_FULL * 316) // 1239 == hi_end, "bis knob arithmetic")
    want(gcd(316, 1239) == 1 and gcd(246, 965) == 1, "knob gcds")
    spec_knob = parsed(SPEC, r"bis \((\d+),(\d+),(\d+)\) n=([\d,]+)",
                       "spec bis knob")
    want((spec_knob.group(2), spec_knob.group(3),
          ncomma(spec_knob.group(4)))
         == WANT_SPEC_BIS, f"spec bis knob pin: {spec_knob.groups()}")
    want((int(spec_knob.group(2)), int(spec_knob.group(3))) == hi_enum[2],
         "spec bis pair == census smallest pair")
    print(f"  hi n={hi_end} (the NEW upper endpoint; bis (3, 316, 1,239)): "
          f"pairs {hi_enum[1]}; smallest {hi_enum[2]}; in-box same-ratio "
          f"doubles {hi_enum[3]} -- the smallest pair == the spec's bis "
          f"knob pair ({spec_knob.group(2)}, {spec_knob.group(3)}): MATCH "
          f"(knob arithmetic (1,000,003*{spec_knob.group(2)})//"
          f"{spec_knob.group(3)} = {(N_FULL * 316) // 1239}); the "
          f"{hi_enum[3]} in-box same-ratio doubles are FRESH -- this "
          "census is the FIRST enumeration of them (s202 reconnaissance: "
          "the hi pair/doubles census is NOT enumerated in any committed "
          "source -- named).")

    # ---- 2. the 18th-cut content PARSED from publication-s197.txt ----
    print()
    print("SECTION 2 -- 18TH-CUT CONTENT PARSED (publication-s197.txt):")
    i = f197.index("C1 ARCHIVED CONTROL REPLICATION")
    c1 = f197[i:f197.index("C2 Q3 CLASS STABILITY")]
    cm = parsed(c1, r"c2 \(sum,128,S=16\) pooled median m (\d+), "
                    r"deep-pooling class FLOOR \(committed floor band "
                    r"(\d+)\.\.(\d+) at B=2\): (True|False)", "C1 c2 line")
    c1_c2 = cm.groups()
    want(c1_c2 == WANT_C1_C2LINE, f"C1 c2 pin: {c1_c2}")
    cm = parsed(c1, r"c8 \(sum,128,S=16\) pooled median m (\d+) within "
                    r"\+/-5% of committed (\d+) \(session 4 pooled median\): "
                    r"(True|False) \(([-\d.]+)%\)", "C1 c8 line")
    c1_c8 = cm.groups()
    want(c1_c8 == WANT_C1_C8LINE, f"C1 c8 pin: {c1_c8}")
    want("control arms free of VERIFY mismatches (frozen INVALIDATION "
         "criterion): True" in c1, "C1 control-arms line")
    vm = parsed(c1, r"VERDICT: branch \((\w)\) both controls satisfy their "
                    r"criteria -- W1 is evaluated against the row question\.",
                "C1 verdict")
    want(vm.groups() == WANT_C1_VERDICT, f"C1 verdict pin: {vm.groups()}")
    want("D2 CONTROL-STATE CONFRONTATION (arm (a), the frozen rule): "
         "the current control state (the 17th cut's C1 (a)) REPLICATES "
         "at back-to-back cuts -- no supersession needed (the 17th "
         "cut's C1 (a) stands confirmed; named)." in c1, "D2 quote")
    print(f"  C1: c2 pooled median m {c1_c2[0]}, deep-pooling class FLOOR "
          f"(committed floor band {c1_c2[1]}..{c1_c2[2]} at B=2): "
          f"{c1_c2[3]}")
    print(f"  C1: c8 pooled median m {c1_c8[0]} within +/-5% of committed "
          f"{c1_c8[1]} (session 4 pooled median): {c1_c8[2]} "
          f"({c1_c8[3]}%)")
    print("  C1: control arms free of VERIFY mismatches (frozen "
          "INVALIDATION criterion): True")
    print(f"  C1 VERDICT: branch ({vm.group(1)}) both controls satisfy "
          "their criteria -- W1 is evaluated against the row question.")
    print("  D2 CONTROL-STATE CONFRONTATION quote PARSED (arm (a), the "
          "frozen rule): the current control state (the 17th cut's C1 "
          "(a)) REPLICATES at back-to-back cuts -- no supersession "
          "needed (the 17th cut's C1 (a) stands confirmed; named).")

    i = f197.index("C2 Q3 CLASS STABILITY")
    c2 = f197[i:f197.index("W1 CUT VERDICT", i)]
    hm = parsed(c2, r"q3 \(BATCH=3,WORK_MUL=(\d+),NDIV=(\d+)\) at "
                    r"n=([\d,]+)", "C2 q3 knob header")
    c2_knob = (hm.group(1), hm.group(2), ncomma(hm.group(3)))
    want(c2_knob == WANT_C2_KNOB, f"C2 knob pin: {c2_knob}")
    want((N_FULL * int(c2_knob[0])) // int(c2_knob[1]) == int(c2_knob[2]),
         "C2 knob arithmetic")
    want((int(c2_knob[0]), int(c2_knob[1])) == WANT_S192["q3"][2],
         "C2 knob pair != s192 q3 smallest pair")
    want("the Q=3 QUARTER POINT of the bracket (254,557, 255,045]" in c2,
         "C2 Q=3 quarter-point quote")
    want("the point is VIRGIN -- this cut's content is the FIRST content "
         "at it" in c2, "C2 virgin quote")
    clm = parsed(c2, r"block classes: \[([^\]]+)\]; pooled-48 class: (\S+)",
                 "C2 block classes")
    toks = re.findall(r"'([^']+)'", clm.group(1))
    counts = dict(Counter(toks))
    pooled_cls = clm.group(2)
    want(len(toks) == 16 and counts == WANT_C2_CLASSES[0]
         and pooled_cls == WANT_C2_CLASSES[1],
         f"C2 class re-count: {len(toks)} {counts} {pooled_cls}")
    bdm = parsed(c2, r"block binding min\(m-h\): ([\d. /]+?)\s+pooled-48 "
                     r"binding min\(m-h\): ([\d.]+)", "C2 binding")
    bvals = [x for x in re.split(r"[\s/]+", bdm.group(1).strip()) if x]
    want(len(bvals) == 16, f"C2 binding count: {len(bvals)}")
    bmin = min(bvals, key=Decimal)
    bmax = max(bvals, key=Decimal)
    bpooled = bdm.group(2)
    want((bmin, bmax, bpooled) == WANT_C2_BIND,
         f"C2 binding pin: {(bmin, bmax, bpooled)}")
    mm = parsed(c2, r"\(sum,128,S=16\) m: blocks ([\d /]+?) ; pooled-48 "
                    r"(\d+)", "C2 block m")
    mvals = [x for x in re.split(r"[\s/]+", mm.group(1).strip()) if x]
    mmin = min(mvals, key=Decimal)
    mmax = max(mvals, key=Decimal)
    want((len(mvals), mmin, mmax, mm.group(2)) == WANT_C2_M,
         f"C2 m pin: {(len(mvals), mmin, mmax, mm.group(2))}")
    want(re.search(r"\(a\) STABLE-INTERMEDIATE: all 16 blocks AND the "
                   r"pooled-48 arm class INTERMEDIATE/MIXED -- PASSES the "
                   r"16-block class- ?stability requirement at q3 under the "
                   r"deep-pooling statistic\.", f197) is not None,
         "C2 (a) STABLE-INTERMEDIATE verdict")
    want("WHY any class occurs is UNMEASURED (L2 binds); NO causal "
         "mechanism is claimed." in f197, "C2 unmeasured quote")
    print(f"  C2: q3 (BATCH=3,WORK_MUL={c2_knob[0]},NDIV={c2_knob[1]}) at "
          f"n={c2_knob[2]} -- knob arithmetic (1,000,003*{c2_knob[0]})//"
          f"{c2_knob[1]} = {(N_FULL * int(c2_knob[0])) // int(c2_knob[1])}; "
          f"pair == the s192 q3 smallest pair {WANT_S192['q3'][2]}: True; "
          "the Q=3 QUARTER POINT quote and the virgin quote PARSED")
    print(f"  C2 block classes (re-count COMPUTED here): "
          f"{counts['INTERMEDIATE/MIXED']}x INTERMEDIATE/MIXED; "
          f"pooled-48 class {pooled_cls}")
    print(f"  C2 block binding min(m-h): {bmin}..{bmax} (16 values), "
          f"pooled-48 {bpooled}")
    print(f"  C2 (sum,128,S=16) m: blocks {mmin}..{mmax} (16 values, "
          f"min..max), pooled-48 {mm.group(2)}")
    print("  C2 VERDICT: (a) STABLE-INTERMEDIATE: all 16 blocks AND the "
          "pooled-48 arm class INTERMEDIATE/MIXED -- PASSES the 16-block "
          "class-stability requirement at q3 under the deep-pooling "
          "statistic (quote PARSED).")
    print("  NAMED, NOT HIDDEN: WHY any class occurs is UNMEASURED (L2 "
          "binds); NO causal mechanism is claimed (quote PARSED).")

    w1 = f197[f197.index("W1 CUT VERDICT"):f197.index("W2 (pre-registered")]
    for letter_line in ("C1 (control replication): (a)",
                        "C2 (q3 class stability): (a)", "W1 (b)"):
        want(letter_line in w1, f"W1 letter line missing: {letter_line}")
    want("(b) C2 (a) -> THE BRACKET NARROWS TO (254,923, 255,045]" in w1,
         "W1 (b) text")
    want("F > 254,923 > 254,882" in w1, "W1 implication")
    want(lo_end > 254882, "implication arithmetic F > 254,923 > 254,882")
    want("the lower endpoint moved 254,557 -> 254,923 on this cut's "
         "content; the upper endpoint is carried unchanged on hi's "
         "content (255,045)" in w1, "W1 endpoint movement")
    want("NAMED: lo AND mid leave the bracket" in w1, "W1 lo/mid leave")
    want("the top clip 255,045-254,923 = 122; the low clip 254,923-254,557 "
         "= 366" in w1, "D1 clip note")
    print("  W1 letters (parsed): C1 (control replication): (a); "
          "C2 (q3 class stability): (a); W1 (b).")
    print("  W1 (b) text PARSED: (b) C2 (a) -> THE BRACKET NARROWS TO "
          "(254,923, 255,045]; the MID-ONLY NARROWING CLAIM's location "
          "statement CONFIRMED BY IMPLICATION (F > 254,923 > 254,882 -- by "
          "implication only, no mid content measured).")
    print("  W1 bracket movement PARSED: the lower endpoint moved "
          "254,557 -> 254,923 on this cut's content; the upper endpoint "
          "carried unchanged on hi's content (255,045); NAMED: lo AND mid "
          "leave the bracket.")
    print("  D1 note (verbatim quote PARSED): the top clip "
          "255,045-254,923 = 122; the low clip 254,923-254,557 = 366 -- "
          "arithmetic re-derived here: 122 / 366 (the clips are not equal "
          "widths).")

    w3i = f197.index("W3 (pre-registered, descriptive)")
    w3 = f197[w3i:f197.index("X1 (descriptive", w3i)]
    want("NAMED CROSS-BINARY HAZARD" in w3, "W3 cross-binary label")
    want("any class comparison with the committed windows may be "
         "BINARY-driven, cause UNMEASURED (L2 binds)" in w3,
         "W3 cross-binary quote")
    want("the s192 enumeration gives 10 in-box same-ratio doubles "
         "of n=254,923 and NONE is measured this cut" in w3, "W3 L8 quote")
    xm = parsed(f197, r"q3: per-run host_ns median min\.\.max "
                      r"([\d.]+)\.\.([\d.]+) \(spread ([\d.]+) = "
                      r"([\d.]+)% of min; k=(\d+)\)", "X1 q3 line")
    want(xm.groups() == WANT_X1_Q3, f"X1 q3 pin: {xm.groups()}")
    print("  W3: NAMED CROSS-BINARY HAZARD quote PARSED (the q3 binary is "
          "NEW first-measured ROUNDS6400 variant; any class comparison "
          "with the committed windows may be BINARY-driven, cause "
          "UNMEASURED, L2 binds).")
    print("  W3: L8 APPLIES quote PARSED: q3 (246, 965) is a NEW knob "
          "pair of the session-21 L8 combination risk class; the s192 "
          "enumeration gives 10 in-box same-ratio doubles of n=254,923 "
          "and NONE is measured this cut.")
    print(f"  X1 (descriptive, NOT a C criterion): q3 per-run host_ns "
          f"median min..max {xm.group(1)}..{xm.group(2)} (spread "
          f"{xm.group(3)} = {xm.group(4)}% of min; k={xm.group(5)}) "
          "(quote PARSED).")

    sm = parsed(f197, r"VERDICT SUMMARY: C1 \((\w)\); C2 \((\w)\) at "
                      r"q3 \(([\d,]+)\); W1 \((\w)\)", "verdict summary")
    summary = (sm.group(1), sm.group(2), ncomma(sm.group(3)), sm.group(4))
    want(summary == WANT_SUMMARY, f"summary pin: {summary}")
    want("CUT VERDICT: THE BRACKET NARROWS TO (254,923, 255,045]" in f197,
         "cut verdict line")
    want('("THE B=3 CLASS FLIP LIES ABOVE n=254,923")' in f197,
         "class-flip line")
    print(f"  VERDICT SUMMARY (parsed): C1 ({summary[0]}); C2 "
          f"({summary[1]}) at q3 ({summary[2]}); W1 ({summary[3]}). "
          "CUT VERDICT: THE BRACKET NARROWS TO (254,923, 255,045] "
          '("THE B=3 CLASS FLIP LIES ABOVE n=254,923").')

    # ---- 3. disputed-record citations + the 18th cut's W3 reading ----
    print()
    print("SECTION 3 -- DISPUTED-RECORD CITATIONS (primary sources) AND "
          "THE 18TH CUT'S W3 READING OF THEM:")
    row = re.compile(r"^\s+(254557|254882|255045|255208)\s+\S+\s+(\d+)\s+"
                     r"(INTERMEDIATE/MIXED|CAPTURED)\s+(.*)$", re.M)
    rows = row.findall(P139)

    def keyed(n):
        out = []
        for nn, med, cls, rest in rows:
            if nn == str(n):
                sess = re.search(r"session (\d+)", rest)
                want(sess is not None, f"row session ref: {rest}")
                out.append((int(med), cls, sess.group(1)))
        return out

    r4557, r4882 = keyed(254557), keyed(254882)
    want(r4557 == WANT_R4557, f"lo dual-class rows pin: {r4557}")
    want(r4882 == WANT_R4882, f"mid dual-class rows pin: {r4882}")
    t139 = flat(P139)
    i = t139.index("lo (405,1591) at n=254,557")
    seg = t139[i:t139.index("hi (1213,4753)", i)]
    pm = re.search(r"pooled-12 median (\d+) 18-cell (\d+)\.\.(\d+) "
                   r"(CAPTURED|INTERMEDIATE/MIXED)", seg)
    want(pm is not None, "WANT NOT PARSED: lo pooled-12")
    pool12 = (int(pm.group(1)), int(pm.group(2)), int(pm.group(3)),
              pm.group(4))
    want(pool12 == WANT_LO_POOL12, f"lo pooled-12 pin: {pool12}")
    i = P139.index("mid (B=3, WM=248, NDIV=973, n=254882, 0.764644")
    seg = flat(P139[i:P139.index("\n\n", i)])
    pm = re.search(r"pooled-48 runs 01\.\.48 \(sum,128,16\) (\d+) "
                   r"18-cell (\d+)\.\.(\d+) "
                   r"(CAPTURED|INTERMEDIATE/MIXED|FLOOR)", seg)
    want(pm is not None, "WANT NOT PARSED: s139 mid pooled-48")
    pool48 = (int(pm.group(1)), int(pm.group(2)), int(pm.group(3)),
              pm.group(4))
    want(pool48 == WANT_MID_POOL48, f"mid pooled-48 pin: {pool48}")
    sm147 = parsed(P147, r"mid \(BATCH=3,WORK_MUL=(\d+),NDIV=(\d+)\) at "
                         r"n=([\d,]+)", "publication-s147.txt mid knob")
    want((int(sm147.group(1)), int(sm147.group(2)),
          int(ncomma(sm147.group(3)))) ==
         WANT_S192["mid"][2] + (WANT_S192["mid"][0],),
         "s147 mid knob triple")
    m = parsed(P147, r"block 18-cell minima \(exact pooled medians\): "
                     r"([\d /]+?) pooled-48", "s147 block minima")
    s147_mins = [int(x) for x in m.group(1).split() if x != "/"]
    want(s147_mins == WANT_S147_MINS, f"s147 minima pin: {s147_mins}")
    m = parsed(P147, r"pooled-48 18-cell min: (\d+)", "s147 pooled min")
    want(int(m.group(1)) == WANT_S147_POOL_MIN, "s147 pooled min pin")
    m = parsed(P147, r"tolerance classes: \[([^\]]+)\]; pooled-48 "
                     r"tolerance class: (\S+)", "s147 tolerance classes")
    s147_cls = re.findall(r"'([^']+)'", m.group(1))
    want(len(s147_cls) == 16 and set(s147_cls) == {"IN-BAND-UNDECIDED"}
         and m.group(2) == "IN-BAND-UNDECIDED", "s147 class pins")
    m = parsed(P147, r"\(sum,128,S=16\): blocks ([\d /]+?) ; pooled-48 "
                     r"(\d+)", "s147 medians")
    want(int(m.group(2)) == WANT_S147_POOL_MED, "s147 pooled median pin")
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
    w3rows = [(a, b, c, d) for a, b, c, d in
              re.findall(r"n=(\d+): (\d+) (INTERMEDIATE/MIXED|CAPTURED) "
                         r"\(session (\d+)\)", w3)]
    want(w3rows == WANT_W3_ROWS, f"W3 row quote pin: {w3rows}")
    lp = re.search(r"lo pooled-12 (\d+) (INTERMEDIATE/MIXED|CAPTURED)", w3)
    want(lp is not None and lp.groups() == WANT_W3_LO_POOL12,
         f"W3 lo pooled quote: {lp.groups() if lp else None}")
    mp = re.search(r"mid pooled-48 (\d+) (CAPTURED|INTERMEDIATE/MIXED) "
                   r"\(s139\); s147 pooled-48 (\d+) (IN-BAND-UNDECIDED)",
                   w3)
    want(mp is not None and mp.groups() == WANT_W3_POOLS,
         f"W3 pooled quotes: {mp.groups() if mp else None}")
    want("16x IN-BAND-UNDECIDED + pooled IN-BAND-UNDECIDED: True" in w3,
         "W3 s147 in-band quote")
    confront = ([("254557", str(a), b, c) for a, b, c in r4557] +
                [("254882", str(a), b, c) for a, b, c in r4882])
    want(sorted(confront) == sorted(WANT_W3_ROWS),
         "W3 reading != primary rows")
    want((str(pool12[0]), pool12[3]) == WANT_W3_LO_POOL12,
         "W3 lo pooled-12 != primary")
    want((str(pool48[0]), pool48[3], str(WANT_S147_POOL_MED),
          "IN-BAND-UNDECIDED") == WANT_W3_POOLS, "W3 pooled quotes != primary")
    print("  W3 CROSS-CHECK: the 18th cut's W3 reading of the disputed "
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
    want(bandv == WANT_SPEC_BAND, f"spec band pin: {bandv}")
    for arm in ("(a) CONTENT CONFRONTATION",
                "(b) BLOCK-GRANULARITY FLOOR",
                "(c) STATISTIC CONFRONTATION",
                "(d) CLAIM-FORM CONFRONTATION"):
        want(arm in SPEC, f"spec arm missing: {arm}")
    want("More blocks of the same mixed shape do not confront anything; "
         "they re-read it" in fsp, "spec arm-(b) re-read hazard quote")
    for q in ("(i) a different class statistic",
              "(ii) a tolerance rule that confronts the MEASURED wander "
              "band",
              "(iii) points whose block minima are measured single-class "
              "stable OUTSIDE the band"):
        want(q in fsp, f"spec arm-(c) option missing: {q}")
    want("The MID-ONLY NARROWING CLAIM stays SUSPENDED" in fsp,
         "spec arm-(d) suspension quote")
    bi = fsp.index("bis (3,316,1239) n=255,045 at binary 440604ef")
    bis_seg = fsp[bi:bi + 400]
    want(WANT_SPEC_BIS_CONTENT[0] in bis_seg, "spec bis class split quote")
    want(WANT_SPEC_BIS_CONTENT[1] in bis_seg, "spec bis pooled quote")
    print(f"  measured wander band (spec, parsed): block-unit "
          f"{bandv[0]}..{bandv[1]}; per-run unit {bandv[2]}..{bandv[3]} "
          "(descriptive unit)")
    print("  spec section 1 (i) bis content pin PARSED: bis (3,316,1239) "
          "n=255,045 at binary 440604ef... -- 7x CAPTURED + 9x "
          "INTERMEDIATE/MIXED blocks, pooled-48 CAPTURED 1,148 (18-cell "
          "1,006..1,449) -- the 13th cut's content at the NEW bracket's "
          "upper endpoint (the spec is ACCEPTED DESIGN ONLY).")
    print("  arms (a)-(d) headings PARSED; arm-(b) re-read hazard quote "
          "'More blocks of the same mixed shape do not confront anything; "
          "they re-read it' PARSED; arm-(c) options (i)/(ii)/(iii) and "
          "arm-(d) 'The MID-ONLY NARROWING CLAIM stays SUSPENDED' PARSED.")
    inband = sum(1 for v in bvals
                 if Decimal(bandv[0]) <= Decimal(v) <= Decimal(bandv[1]))
    want(inband == 16, f"q3 binding in-band count: {inband}")
    above = sum(1 for v in bvals if Decimal(v) >= 1000)
    want(above == 0, f"q3 binding >= 1000 count: {above}")
    want(Decimal(bpooled) < 1000, "q3 pooled binding below threshold")
    print(f"  COMPUTED here (descriptive; arithmetic on parsed values): "
          f"{inband}/16 of the 18th cut's q3 block binding min(m-h) "
          f"values land inside the block-unit wander band {bandv[0]}.."
          f"{bandv[1]} -- every one; {above}/16 >= the frozen 1,000-tick "
          f"threshold (the binding range {bmin}..{bmax} and the pooled-48 "
          f"{bpooled} lie ENTIRELY BELOW 1,000, INSIDE the band) while "
          "all 16 block classes and the pooled-48 class are "
          "INTERMEDIATE/MIXED (section 2) -- an arm-(c) design input, NO "
          "class and NO letter; the binding min(m-h) within-window wander "
          "at a byte-identical binary remains UNMEASURED (the standing "
          "GAP, unchanged).")

    # ---- 5. candidate cut points enumerated ----
    print()
    print("SECTION 5 -- CANDIDATE CUT POINTS (quarter grid of the "
          f"bracket ({lo_end}, {hi_end}], width {width}; enumeration "
          "only):")
    print(f"  floor midpoint re-derivation: ({lo_end}+{hi_end})//2 = "
          f"{floor_mid} (RE-DERIVED here; == the q=2 candidate: True)")
    srcs = {"publication-s139.txt": P139, "publication-s147.txt": P147,
            "publication-s158.txt": P158, "publication-s169.txt": P169,
            "publication-s185.txt": P185, "publication-s197.txt": P197}
    esrcs = {"knob-search-s177-run1.txt": KS177,
             "knob-search-s192-run1.txt": KS192}

    def occ(target):
        o = {name: txt.replace(",", "").count(str(target))
             for name, txt in srcs.items()}
        e = {name: txt.replace(",", "").count(str(target))
             for name, txt in esrcs.items()}
        return o, e

    for q in (1, 2, 3):
        cand = lo_end + (width * q) // 4
        want(cand == WANT_QUARTER[q][0], f"quarter q={q} grid: {cand}")
        ps = pairs_for(cand)
        gotq = (cand, len(ps), smallest(ps) if ps else None,
                len(doubles_in_box(ps)))
        want(gotq == WANT_QUARTER[q], f"quarter q={q} derivation: {gotq}")
        o, e = occ(cand)
        want(o == WANT_OCC[cand], f"q={q} occurrence census: {o}")
        want(e == WANT_E_OCC[cand], f"q={q} enum occurrence census: {e}")
        want(all(v == 0 for v in o.values()) and all(v == 0 for v in e.values()),
             f"q={q} not virgin")
        q4 = "floor midpoint (q=2)" if q == 2 else f"quarter q={q}"
        print(f"  {q4} n={cand}: pairs {gotq[1]}; smallest {gotq[2]}; "
              f"in-box same-ratio doubles {gotq[3]}; committed-source "
              f"occurrences {o}; enumeration-source occurrences {e}")
        print(f"    content confrontation: n={cand} is VIRGIN after the "
              "eighteenth cut -- RE-DERIVED here: 0 occurrences in every "
              "parsed publication source (including "
              "publication-s197.txt) AND in both knob-search captures.")
    o, e = occ(lo_end)
    want(o == WANT_OCC[lo_end], f"lo occurrence census: {o}")
    want(e == WANT_E_OCC[lo_end], f"lo enum occurrence census: {e}")
    print(f"  lower endpoint lo n={lo_end} (the NEW lower endpoint; the "
          "18th cut's cut point): committed-source occurrences "
          f"{o}; enumeration-source occurrences {e}")
    print("    content confrontation: publication-s197.txt carries the "
          "FIRST content at it (C2 (a) STABLE-INTERMEDIATE, parsed in "
          "section 2; 26 occurrences) and the pre-18th-cut publication "
          "sources carry none (0/0/0/0/0); the knob-search captures "
          "carry enumeration quotes only. NAMED, NOT HIDDEN: what binds "
          "at 254,923 for a future same-shape re-run is a DESIGN "
          "QUESTION (the frozen 'mixed at q3' second-edge shape did NOT "
          "fire on (a) content) -- NOT decided by this census.")
    o, e = occ(hi_end)
    want(o == WANT_OCC[hi_end], f"hi occurrence census: {o}")
    want(e == WANT_E_OCC[hi_end], f"hi enum occurrence census: {e}")
    want(WANT_P139_SUMMARY in t139, "p139 summary pin")
    f158 = flat(P158)
    want(WANT_P158_SUMMARY in f158, "p158 summary pin")
    want("C2 (b)" not in t139, "p139 carries no C2 (b)")
    i = f158.index("bis (B=3, WM=316, NDIV=1239, n=255045)")
    seg158 = f158[i:]
    mc = parsed(seg158, r"block classes: \[([^\]]+)\]; pooled-48 class: "
                        r"(\S+)", "p158 bis block classes")
    mtoks = re.findall(r"'([^']+)'", mc.group(1))
    mcounts = dict(Counter(mtoks))
    want(len(mtoks) == 16 and mcounts == WANT_P158_CLASSES[0]
         and mc.group(2) == WANT_P158_CLASSES[1],
         f"p158 class re-count: {mcounts} {mc.group(2)}")
    want(f"pooled-48 binding min(m-h): {WANT_P158_POOLED_BIND}" in f158,
         "p158 pooled binding pin")
    want("(b) STABLE-CAPTURED: all 16 blocks AND the pooled-48 arm" in f158,
         "p158 (b) STABLE-CAPTURED verdict")
    print(f"  upper endpoint hi n={hi_end} (the NEW upper endpoint; bis "
          "(3, 316, 1,239)): committed-source occurrences "
          f"{o}; enumeration-source occurrences {e}")
    print("    content confrontation: the 13th cut's content stands at "
          "this point (publication-s139.txt VERDICT SUMMARY "
          "'C1 (a); C2 (c) at bis (255,045); C3 (c) at mid; W1 (c)'; the "
          "spec section 1 (i) census: 7x CAPTURED + 9x "
          "INTERMEDIATE/MIXED blocks, pooled-48 CAPTURED 1,148 at binary "
          "440604ef...) AND the 15th cut's re-measure at its NEW binary "
          "52fb68b6... (publication-s158.txt: 16x CAPTURED blocks, "
          "pooled-48 class CAPTURED, pooled binding 1009.6912, "
          "(b) STABLE-CAPTURED; VERDICT SUMMARY 'C1 (a); C2 (b) at bis "
          "(255,045); W1 (a)'). NAMED, NOT HIDDEN -- the s202 "
          "reconnaissance quote attributed the summary 'C1 (a); C2 (b) "
          "at bis (255,045); W1 (a)' to publication-s139.txt and called "
          "it 'the thirteenth cut's C2 (b) content'; the committed bytes "
          "disagree (asserted fail-closed here: publication-s139.txt "
          "carries NO 'C2 (b)' at all; that summary is publication-"
          "s158.txt's -- the FIFTEENTH cut's -- and the 13th cut's own "
          "letter at bis is (c)) -- this census confronts the committed "
          "bytes (the s191 rule: the census is the authority) and "
          "supersedes the s202 reconnaissance quote on this point.")
    o, e = occ(254882)
    want(o == WANT_OCC[254882], f"mid occurrence census: {o}")
    want(e == WANT_E_OCC[254882], f"mid enum occurrence census: {e}")
    frac = (254882 - WANT_OLD_BRACKET[0]) / old_width
    want(f"{frac:.6f}" == "0.665984", f"mid q-fraction: {frac:.6f}")
    print(f"  interior committed point mid (248, 973) n=254882 is NOT on "
          f"the new quarter grid (it sits at old-bracket q-fraction "
          f"(254882 - {WANT_OLD_BRACKET[0]})/{old_width} = "
          f"{frac:.6f}) and is now OUTSIDE the new bracket (below its "
          f"lower endpoint); it carries the disputed record content "
          f"parsed in section 3; committed-source occurrences {o}.")
    for label, target in (("q1 (17th cut)", 254679),
                          ("fm (16th cut)", 254801)):
        o, e = occ(target)
        want(o == WANT_OCC[target], f"{label} occurrence census: {o}")
        want(e == WANT_E_OCC[target], f"{label} enum occurrence census: {e}")
        print(f"  OLD grid point {label} n={target}: outside the new "
              f"bracket; committed-source occurrences {o}; "
              f"enumeration-source occurrences {e}; its rows stand as "
              "committed content outside the bracket (no claim at it is "
              "ever made).")

    print()
    print("SCOPE (three-state discipline): QUOTE-ONLY confrontation "
          "census -- every citation above is committed content parsed "
          "here or arithmetic on parsed values, NOT this session's "
          "measurement. NO cut is frozen, queued or run by this script; "
          "NO protocol.txt exists yet for the nineteenth cut; the "
          "MID-ONLY NARROWING CLAIM stays SUSPENDED; the committed "
          f"bracket is NARROWED to ({lo_end}, {hi_end}] by the eighteenth "
          "cut's landed content and NOTHING in this script moves it; "
          "RULE 4 unchanged (NO vendor optimization for any vendor). The "
          "confrontation spec is ACCEPTED DESIGN ONLY; the design "
          "decisions this census feeds are NOT drafted by this script.")
    print()
    print("CENSUS COMPLETE: every asserted want parsed and matched; "
          "0 mismatches.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
