#!/usr/bin/env python3
"""JUN-59 session 165 -- the SIXTEENTH CUT pre-registration derivation,
cut-point reconnaissance (the s164 carry-forward (a)).

Every number below is computed in this script from arithmetic or PARSED
from committed bytes -- nothing is transcribed from prose. Deterministic:
no clock, no RNG, no network, no hardware. Running it twice is
byte-identical (the run captures + cmp in the evidence directory).

Purpose: enumerate the in-box knob pairs (frozen search box WORK_MUL
1..2,048 x NDIV 1..8,192, the sessions 21-27 box) hitting the interior
candidates of the committed bracket (254,557, 255,045] -- the floor
midpoint (254,557+255,045)//2 (re-derived here; the s164 state's prose
candidate is CHECKED against this derivation, never assumed) and the
interior committed point mid (248,973) n=254,882 -- plus the
committed-bytes citations at each candidate (mid's dual-class rows +
the 14th cut's TOLERANCE-UNRESOLVED mid content; lo's dual-class rows
at (254,557)). QUOTE-ONLY content: this script takes NO measurement of
its own; no cut is frozen or queued here, no bracket moves, no class/
verdict/claim is produced.
"""
import math
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
GPU = os.path.join(HERE, "..")

N_FULL = 1_000_003
BOX_WM = range(1, 2049)
BOX_NDIV = range(1, 8193)

# Frozen citation wants (pin-like): the PARSE must match these committed
# values or the script aborts fail-closed.
WANT_BRACKET = (254557, 255045)
WANT_PROSE_MIDPOINT = 254801          # state-s164.txt prose candidate
WANT_S27 = (35, (214, 845), 9)        # s27 census anchor (253,255)
WANT_MID_KNOB = (248, 973, 254882)    # publication-s139.txt mid header
WANT_BIS_KNOB = (316, 1239, 255045)   # publication-s139.txt bis header
WANT_LO_KNOB = (405, 1591, 254557)    # publication-s139.txt lo section
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
WANT_S147_MEDS = [1144, 1170, 1138, 1161, 1134, 1146, 1141, 1146,
                  1160, 1148, 1145, 1147, 1149, 1164, 1161, 1145]
WANT_S147_POOL_MED = 1148
WANT_S147_VERDICT = ("(c) TOLERANCE-UNRESOLVED: any in-band minimum or "
                     "mixed classes -- FAILS; L9 binds at mid at 16 blocks "
                     "under the tolerance rule too.")


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


def main():
    print("== JUN-59 session 165 derivation (the SIXTEENTH CUT          ==")
    print("== pre-registration: cut-point reconnaissance -- enumeration ==")
    print("== of in-box knob pairs at the interior candidates of the    ==")
    print("== committed bracket + committed-bytes citations)            ==")
    print("== every value computed here from arithmetic or committed    ==")
    print("== bytes; QUOTE-ONLY; NO measurement, NO freeze, NO queue    ==")
    print()

    # ---- 0. the committed bracket, re-derived from committed bytes ----
    P158 = open(os.path.join(GPU, "anv-b3bisect15-20261101",
                             "publication-s158.txt")).read()
    m = parsed(P158, r"Bracket state: NARROWED -- \(([\d,]+), ([\d,]+)\]",
               "publication-s158.txt bracket")
    lo_end = int(m.group(1).replace(",", ""))
    hi_end = int(m.group(2).replace(",", ""))
    assert (lo_end, hi_end) == WANT_BRACKET, "committed bracket endpoints"
    print("committed bracket (publication-s158.txt, parsed): "
          f"({lo_end}, {hi_end}] n-units")
    print("knob arithmetic: n = (1,000,003*WORK_MUL)//NDIV (integer floor)")
    print("search box (sessions 21-27's box): WORK_MUL 1..2,048 x "
          "NDIV 1..8,192")

    # ---- 1. the floor midpoint, re-derived; s164's prose candidate
    #         checked against the derivation ----
    mid_exact = (lo_end + hi_end) / 2
    floor_mid = (lo_end + hi_end) // 2
    S164 = open(os.path.join(HERE, "state-s164.txt")).read()
    m = parsed(S164, r"\(254,557\+255,045\)//2 = ([\d,]+)",
               "state-s164.txt prose midpoint candidate")
    prose = int(m.group(1).replace(",", ""))
    assert prose == WANT_PROSE_MIDPOINT, "s164 prose candidate pin"
    assert floor_mid == prose, "script re-derivation != s164 prose candidate"
    print()
    print(f"bracket floor midpoint exact: {mid_exact} -- exact_is_integer: "
          f"{float(mid_exact).is_integer()}")
    print(f"bisect grid n = ({lo_end}+{hi_end})//2 = {floor_mid} "
          f"(RE-DERIVED here; state-s164.txt prose candidate {prose} "
          "-> MATCH)")

    # ---- 2. the interior committed point mid (248,973) n=254,882 ----
    P139 = open(os.path.join(GPU, "anv-b3bisect13-20261031",
                             "publication-s139.txt")).read()
    m = parsed(P139, r"mid \(B=3, WM=(\d+), NDIV=(\d+), n=(\d+),",
               "publication-s139.txt mid knob header")
    mid_knob = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    assert mid_knob == WANT_MID_KNOB, "mid knob triple pin"
    assert (N_FULL * mid_knob[0]) // mid_knob[1] == mid_knob[2], \
        "mid knob arithmetic"
    n_mid = mid_knob[2]
    print(f"interior committed point mid {mid_knob[:2]} n={n_mid} "
          "(publication-s139.txt header, parsed)")
    assert lo_end < floor_mid <= hi_end, "floor midpoint interior"
    assert lo_end < n_mid <= hi_end, "mid interior"
    print(f"interior check: {lo_end} < {floor_mid} <= {hi_end} and "
          f"{lo_end} < {n_mid} <= {hi_end} -> both interior")

    # ---- 3. SEARCH SELF-VALIDATION against session 27's committed
    #         census anchor (253,255) and state-s164's quote of it ----
    S27 = open(os.path.join(GPU, "anv-b3bisect7-20261027",
                            "derivation-census-s27.txt")).read()
    m = parsed(S27, r"pairs mapping to 253255 in-box: (\d+); "
                    r"smallest: \((\d+),(\d+)\)", "s27 census anchor")
    s27_n, s27_sm = int(m.group(1)), (int(m.group(2)), int(m.group(3)))
    m = parsed(S27, r"in-box pairs whose same-ratio double is also "
                    r"in-box: (\d+)", "s27 census doubles")
    s27_dbl = int(m.group(1))
    m = parsed(S164, r"253,255: (\d+) pairs / smallest \((\d+),(\d+)\) / "
                     r"(\d+) in-box doubles", "state-s164 anchor quote")
    st_n, st_sm, st_dbl = (int(m.group(1)),
                           (int(m.group(2)), int(m.group(3))),
                           int(m.group(4)))
    assert (s27_n, s27_sm, s27_dbl) == WANT_S27, "s27 anchor pin"
    assert (st_n, st_sm, st_dbl) == WANT_S27, "state-s164 quote == s27"
    ref = pairs_for(253255)
    got = (len(ref), smallest(ref), len(doubles_in_box(ref)))
    print()
    print("SEARCH SELF-VALIDATION against session 27's committed census "
          "(253,255):")
    print(f"  pairs found: {got[0]} (s27 committed: {s27_n}; "
          f"state-s164: {st_n}) -> "
          f"{'MATCH' if got[0] == s27_n == st_n else 'MISMATCH'}")
    print(f"  smallest: {got[1]} (s27 committed: {s27_sm}; "
          f"state-s164: {st_sm}) -> "
          f"{'MATCH' if got[1] == s27_sm == st_sm else 'MISMATCH'}")
    print(f"  doubles in box: {got[2]} (s27 committed: {s27_dbl}; "
          f"state-s164: {st_dbl}) -> "
          f"{'MATCH' if got[2] == s27_dbl == st_dbl else 'MISMATCH'}")
    assert got == (s27_n, s27_sm, s27_dbl), "self-validation MISMATCH"

    # ---- 4. in-box knob enumeration at the interior candidates ----
    for label, target in (("FLOOR MIDPOINT CANDIDATE", floor_mid),
                          ("MID CANDIDATE", n_mid)):
        ps = pairs_for(target)
        sm = smallest(ps) if ps else None
        dbls = doubles_in_box(ps)
        print()
        print(f"{label} n={target}:")
        print(f"  pairs mapping to {target} in-box: {len(ps)}; "
              f"smallest: {sm}")
        print(f"  in-box pairs whose same-ratio double is also in-box: "
              f"{len(dbls)}")
        print(f"  gcd({target}, 1,000,003) = {math.gcd(target, N_FULL)} "
              "-- every knob pair is a floor approximation of the grid")
        if target == n_mid:
            assert mid_knob[:2] in ps, "committed mid pair not in mapping"
            print(f"  committed measurement pair {mid_knob[:2]}: "
                  f"(1,000,003*{mid_knob[0]})//{mid_knob[1]} = "
                  f"{(N_FULL * mid_knob[0]) // mid_knob[1]} in the mapping "
                  f"set: True")
        else:
            print(f"  committed content at n={target}: NONE -- this "
                  "candidate has never been measured (enumeration only; "
                  "no reading exists at it in any committed bytes)")

    # ---- 5. bracket-endpoint knob citations (anchors) ----
    m = parsed(P139, r"bis \(B=3, WM=(\d+), NDIV=(\d+), n=(\d+),",
               "publication-s139.txt bis knob header")
    bis_knob = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    assert bis_knob == WANT_BIS_KNOB, "bis knob triple pin"
    assert (N_FULL * bis_knob[0]) // bis_knob[1] == bis_knob[2], \
        "bis knob arithmetic"
    m = parsed(P139, r"lo \((\d+),(\d+)\) at n=([\d,]+)",
               "publication-s139.txt lo knob")
    lo_knob = (int(m.group(1)), int(m.group(2)),
               int(m.group(3).replace(",", "")))
    assert lo_knob == WANT_LO_KNOB, "lo knob triple pin"
    assert (N_FULL * lo_knob[0]) // lo_knob[1] == lo_knob[2], \
        "lo knob arithmetic"
    print()
    print("BRACKET-ENDPOINT KNOB CITATIONS (parsed from "
          "publication-s139.txt):")
    print(f"  lo (n={lo_end}): pair {lo_knob[:2]} -> "
          f"n={(N_FULL * lo_knob[0]) // lo_knob[1]}; in mapping set "
          f"pairs_for({lo_end}): {lo_knob[:2] in pairs_for(lo_end)}")
    print(f"  hi/bis (n={hi_end}): pair {bis_knob[:2]} -> "
          f"n={(N_FULL * bis_knob[0]) // bis_knob[1]}; in mapping set "
          f"pairs_for({hi_end}): {bis_knob[:2] in pairs_for(hi_end)}")

    # ---- 6. committed-bytes citations at mid (254,882): the dual-class
    #         rows + the 14th cut's TOLERANCE-UNRESOLVED content ----
    print()
    print("COMMITTED-BYTE CITATIONS AT MID n=254,882 (parsed; "
          "quote-only):")
    row = re.compile(r"^\s+(254557|254882|255045|255208)\s+\S+\s+(\d+)\s+"
                     r"(INTERMEDIATE/MIXED|CAPTURED)\s+(.*)$", re.M)
    rows = row.findall(P139)

    def keyed(n):
        out = []
        for nn, med, cls, rest in rows:
            if nn == str(n):
                sm = re.search(r"session (\d+)", rest)
                assert sm is not None, f"row session ref not parsed: {rest}"
                out.append((int(med), cls, sm.group(1)))
        return out

    r4557, r4882 = keyed(254557), keyed(254882)
    assert r4557 == WANT_R4557, f"lo dual-class rows pin: {r4557}"
    assert r4882 == WANT_R4882, f"mid dual-class rows pin: {r4882}"
    for med, cls, sess in r4882:
        print(f"  W2 row table: {med} {cls} (session {sess})")
    i = P139.index("mid (B=3, WM=248, NDIV=973, n=254882, 0.764644")
    seg = flat(P139[i:P139.index("\n\n", i)])
    pm = re.search(r"pooled-48 runs 01\.\.48 \(sum,128,16\) (\d+) "
                   r"18-cell (\d+)\.\.(\d+) "
                   r"(CAPTURED|INTERMEDIATE/MIXED|FLOOR)", seg)
    assert pm is not None, "WANT NOT PARSED: s139 mid pooled-48"
    pool48 = (int(pm.group(1)), int(pm.group(2)), int(pm.group(3)),
              pm.group(4))
    assert pool48 == WANT_MID_POOL48, f"mid pooled-48 pin: {pool48}"
    print(f"  s139 window pooled-48: median {pool48[0]}, 18-cell "
          f"{pool48[1]}..{pool48[2]}, class {pool48[3]} (session 139)")
    print("  dual-class at mid on the committed record: "
          "1,129/1,133 INTERMEDIATE/MIXED (s125/s132) vs 1,148 CAPTURED "
          "(s136 pooled-24) vs 1,140 CAPTURED (s139 pooled-48)")

    P147 = open(os.path.join(GPU, "anv-b3bisect14-20261031",
                             "publication-s147.txt")).read()
    m = parsed(P147, r"mid \(BATCH=3,WORK_MUL=(\d+),NDIV=(\d+)\) at "
                     r"n=([\d,]+)", "publication-s147.txt mid knob")
    s147_knob = (int(m.group(1)), int(m.group(2)),
                 int(m.group(3).replace(",", "")))
    assert s147_knob == WANT_MID_KNOB, "s147 mid knob == s139 mid knob"
    m = parsed(P147, r"block 18-cell minima \(exact pooled medians\): "
                     r"([\d /]+?) pooled-48", "s147 block minima")
    s147_mins = [int(x) for x in m.group(1).split() if x != "/"]
    assert s147_mins == WANT_S147_MINS, f"s147 minima pin: {s147_mins}"
    m = parsed(P147, r"pooled-48 18-cell min: (\d+)", "s147 pooled min")
    s147_pool_min = int(m.group(1))
    assert s147_pool_min == WANT_S147_POOL_MIN, "s147 pooled min pin"
    m = parsed(P147, r"tolerance classes: \[([^\]]+)\]; pooled-48 "
                     r"tolerance class: (\S+)", "s147 tolerance classes")
    s147_cls = re.findall(r"'([^']+)'", m.group(1))
    s147_pool_cls = m.group(2)
    assert len(s147_cls) == 16 and set(s147_cls) == {"IN-BAND-UNDECIDED"}, \
        f"s147 block tolerance classes pin: {s147_cls}"
    assert s147_pool_cls == "IN-BAND-UNDECIDED", "s147 pooled class pin"
    m = parsed(P147, r"\(sum,128,S=16\): blocks ([\d /]+?) ; pooled-48 "
                     r"(\d+)", "s147 medians")
    s147_meds = [int(x) for x in m.group(1).split() if x != "/"]
    s147_pool_med = int(m.group(2))
    assert s147_meds == WANT_S147_MEDS, f"s147 medians pin: {s147_meds}"
    assert s147_pool_med == WANT_S147_POOL_MED, "s147 pooled median pin"
    m = parsed(P147, re.escape(WANT_S147_VERDICT), "s147 verdict")
    in_band = all(980 < v < 1016 for v in s147_mins) and \
        980 < s147_pool_min < 1016
    print()
    print("  14th cut (publication-s147.txt) mid content at "
          f"{s147_knob[:2]} n={s147_knob[2]} (its own window):")
    print(f"    16 blocks + pooled-48 tolerance classes: 16x "
          f"{s147_cls[0]} + pooled-48 {s147_pool_cls}")
    print(f"    block 18-cell minima: "
          f"{' / '.join(str(v) for v in s147_mins)}")
    print(f"    pooled-48 18-cell min: {s147_pool_min}; block medians "
          f"{min(s147_meds)}..{max(s147_meds)}; pooled-48 median "
          f"{s147_pool_med}")
    print(f"    every min strictly inside (980, 1,016) (the IN-BAND "
          f"condition, COMPUTED here): {in_band}")
    assert in_band, "s147 IN-BAND arithmetic"
    print(f"    verdict line (parsed): {m.group(0)}")
    print("    -> the 14th cut's mid content is TOLERANCE-UNRESOLVED "
          "(16x IN-BAND-UNDECIDED + pooled IN-BAND-UNDECIDED); it "
          "STANDS as arm (a) content to confront.")

    # ---- 7. committed-bytes citations at lo (254,557): the dual-class
    #         rows ----
    print()
    print("COMMITTED-BYTE CITATIONS AT LO n=254,557 (parsed; "
          "quote-only):")
    for med, cls, sess in r4557:
        print(f"  W2 row table: {med} {cls} (session {sess})")
    t = flat(P139)
    i = t.index("lo (405,1591) at n=254,557")
    seg = t[i:t.index("hi (1213,4753)", i)]
    assert "the tenth cut's committed reading" in seg, \
        "lo section tenth-cut attribution not parsed"
    tm = re.search(r"session (\d+) \(the tenth cut\)", t)
    assert tm is not None, "tenth-cut session ref not parsed"
    assert tm.group(1) == "129", "tenth cut == session 129"
    pm = re.search(r"pooled-12 median (\d+) 18-cell (\d+)\.\.(\d+) "
                   r"(CAPTURED|INTERMEDIATE/MIXED)", seg)
    assert pm is not None, "WANT NOT PARSED: lo pooled-12"
    pool12 = (int(pm.group(1)), int(pm.group(2)), int(pm.group(3)),
              pm.group(4))
    assert pool12 == WANT_LO_POOL12, f"lo pooled-12 pin: {pool12}"
    print(f"  tenth cut (session {tm.group(1)}) lo pooled-12: median "
          f"{pool12[0]}, 18-cell {pool12[1]}..{pool12[2]}, class "
          f"{pool12[3]}")
    print("  dual-class at lo on the committed record: 1,156 "
          "INTERMEDIATE/MIXED (s121), 1,143 CAPTURED (s125), 1,141 "
          "INTERMEDIATE/MIXED (s129 pooled-12) -- spec section 1 (iv)")

    print()
    print("SCOPE (three-state discipline): QUOTE-ONLY reconnaissance -- "
          "every citation above is committed content parsed here, NOT "
          "this session's measurement. NO cut is frozen, queued or run "
          "by this script; NO protocol.txt exists yet; the MID-ONLY "
          "NARROWING CLAIM stays SUSPENDED; the committed bracket stays "
          "EXACTLY (254,557, 255,045]; RULE 4 unchanged (NO vendor "
          "optimization for any vendor).")
    print()
    print("CENSUS COMPLETE: every asserted want parsed and matched; "
          "0 mismatches.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
