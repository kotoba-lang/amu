#!/usr/bin/env python3
"""JUN-59 session 133 -- the TWELFTH CUT pre-registration derivation.

Every number below is computed in this script from arithmetic or PARSED
from committed bytes -- nothing is transcribed from prose. Deterministic:
no clock, no RNG, no network, no hardware. Running it twice is
byte-identical (recorded in record.txt).

Purpose: the derivation half of the twelfth cut pre-registration (the
s133 carry-forward (a), "a twelfth cut at mid ONLY through a NEW
pre-registered cut session -- the narrowing channel re-opens at mid (W1
(b), C2 (a) PASSES) and stays CLOSED at hi"). The twelfth cut is the
first cut through the narrowing channel the eleventh cut's W1 (b)
re-opened at mid: it pre-registers the MID-ONLY NARROWING CLAIM (the
B=3 class flip lies above n=254,882 -- the ninth cut's W1 (b) branch
content the s125 FLAGGED could not claim) and derives the NEW bisect
point -- the exact floor midpoint of the mid-anchored interval
(254,882, 255,208]. This script therefore derives ONE new knob pair
(the bis triple's (WORK_MUL,NDIV), L8 named), verifies the two
committed pairs' arithmetic, SELF-VALIDATES its search against
committed runs (session 123's ninth-cut run and session 131's
eleventh-cut derivation run), and parses every cited value from
committed bytes (publication-s132.txt's C1/C2/C3/W1 letters, block
rows, W2 trajectories with COMPUTED boundary-crossing counts, the
bracket, the committed row's 255,045 absence; the build pins with the
mid 3-way cross-check s125/s129/s132; the ledger rows and the frozen
evaluator pin verdict).

Named provenance: this file is named session 133's by the state-s133.txt
NOT DONE list (the design session); it is written and run by the
completing session 134.
"""
import math
import re
import sys

N_FULL = 1_000_003
BOX_WM = range(1, 2049)
BOX_NDIV = range(1, 8193)


def pairs_for(target):
    out = []
    for wm in BOX_WM:
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


def fmt_work(n, b):
    return f"per-dispatch {n / N_FULL:.7f} total {b * n / N_FULL:.7f}"


def parsed(text, pattern, flags=0):
    flat = re.sub(r"\s+", " ", text)
    mm = re.search(pattern, flat, flags)
    val = "NOT PARSED"
    if mm is not None:
        val = mm.group(1).strip()
    return val


def scope(flat, start, end):
    mm = re.search(re.escape(start) + r".*?(?=" + re.escape(end) + ")", flat)
    assert mm, f"scope not parsed: {start} .. {end}"
    return mm.group(0)


def main():
    print("== JUN-59 session 133 derivation (the TWELFTH CUT pre-        ==")
    print("== registration: THE MID-ONLY NARROWING CUT -- the first cut  ==")
    print("== through the channel the eleventh cut's W1 (b) re-opened at ==")
    print("== mid; ONE new knob pair (bis), committed-pair verification, ==")
    print("== committed-byte citations)                                  ==")
    print("== every value computed here from arithmetic or committed bytes ==")
    print()
    s123 = open("docs/evidence/gpu/anv-b3bisect9prereg-20261031/knob-search-s123-run1.txt").read()
    s131 = open("docs/evidence/gpu/anv-b3bisect11prereg-20261031/knob-search-s131-run1.txt").read()
    s27 = open("docs/evidence/gpu/anv-b3bisect7-20261027/derivation-census-s27.txt").read()
    pub121 = open("docs/evidence/gpu/anv-b3bisect8-20261031/publication-s121.txt").read()
    pub125 = open("docs/evidence/gpu/anv-b3bisect9-20261031/publication-s125.txt").read()
    pub132 = open("docs/evidence/gpu/anv-b3bisect11-20261031/publication-s132.txt").read()
    flat = re.sub(r"\s+", " ", pub132)

    # ---- the channel's content: the eleventh cut's W1 (b) re-open at mid
    print("THE MID-ONLY NARROWING CLAIM (the channel's content; parsed here")
    print("from publication-s132.txt -- the eleventh cut's measurement half):")
    scope_c2 = scope(flat, "C2 MULTI-BLOCK STABILITY AT THE NINTH CUT'S ROW POINT",
                     "C3 MULTI-BLOCK STABILITY AT THE BRACKET'S UPPER ANCHOR")
    scope_c3 = scope(flat, "C3 MULTI-BLOCK STABILITY AT THE BRACKET'S UPPER ANCHOR",
                     "W1 THE ROW QUESTION")
    scope_w1 = scope(flat, "W1 THE ROW QUESTION", "W2 (pre-registered")
    mm = re.search(r"\(([a-d])\) block classes: "
                   r"\[([^\]]*)\]; pooled-24 class: (\S+) \(sum,128,S=16\): blocks "
                   r"([\d /]+?) ; pooled-24 (\d+)", scope_c2)
    assert mm, "eleventh cut C2 block rows not parsed"
    c2_letter, c2_classes, c2_pooled_cls, c2_blocks, c2_pooled = mm.groups()
    print(f"  eleventh cut C2 mid letter ({c2_letter}) block classes: [{c2_classes}]")
    print(f"    pooled-24 class: {c2_pooled_cls}; blocks {c2_blocks}; "
          f"pooled-24 {c2_pooled}")
    mm = re.search(r"\(([a-d])\) block classes: "
                   r"\[([^\]]*)\]; pooled-24 class: (\S+) \(sum,128,S=16\): blocks "
                   r"([\d /]+?) ; pooled-24 (\d+)", scope_c3)
    assert mm, "eleventh cut C3 block rows not parsed"
    c3_letter, c3_classes, c3_pooled_cls, c3_blocks, c3_pooled = mm.groups()
    print(f"  eleventh cut C3 hi letter ({c3_letter}) block classes: [{c3_classes}]")
    print(f"    pooled-24 class: {c3_pooled_cls}; blocks {c3_blocks}; "
          f"pooled-24 {c3_pooled}")
    mm = re.search(r"W1 \(([a-d])\)", scope_w1)
    assert mm, "eleventh cut W1 letter not parsed"
    w1_letter = mm.group(1)
    print(f"  eleventh cut W1 letter ({w1_letter}) -- the per-point CUT VERDICT")
    print("    " + parsed(
        pub132, r"CUT VERDICT \(pre-named composition, section 0's RESUMABILITY "
                r"RULE, per-point form\): (exactly one L9-bound point PASSES; "
                r"the narrowing channel re-opens at that point only\.)"))
    print("    " + parsed(
        pub132, r"(\(b\) EXACTLY ONE PASSES \(the named point: mid \(n=254,882\) "
                r"passes; the other FAILS\) -- the narrowing channel re-opens at "
                r"that point only\.)"))
    print("    " + parsed(
        pub132, r"(L9 CONTINUES to bind at hi: the class label at this point is "
                r"BLOCK-RUN-UNSTABLE at the finer granularity too\.)"))
    assert c2_letter == "a" and c3_letter == "c" and w1_letter == "b"
    assert c2_pooled_cls == "INTERMEDIATE/MIXED" and c3_pooled_cls == "CAPTURED"

    # ---- the committed bracket (parsed) and the new bisect point (derived)
    print()
    print("THE NEW BISECT POINT (derived here; the eighth cut's exact-floor-")
    print("midpoint shape):")
    br = parsed(pub132, r"the committed bracket stays exactly \(([\d, ]+)\]")
    print(f"  the committed bracket (parsed): ({br}]")
    lo_n, hi_n = 254882, 255208
    assert br == "254,557, 255,208"
    num = lo_n + hi_n
    assert num % 2 == 0, "the mid-anchored interval midpoint is not an exact integer"
    bis_n = num // 2
    print(f"  the mid-anchored interval ({lo_n:,}, {hi_n:,}] floor midpoint: "
          f"({lo_n} + {hi_n})/2 = {num / 2:.1f} -> exact integer {bis_n}")
    assert bis_n == 255045
    # the committed row (255,045 absence), parsed from publication-s132.txt's
    # W2 table rows (n column)
    row_n = []
    for line in pub132.splitlines():
        m = re.match(r"\s+(\d+) +(\S+) +(\d+) +(\S+) +(session|sessions|THIS)", line)
        if m is not None:
            row_n.append(int(m.group(1)))
    print(f"  the committed row's n values (parsed from publication-s132.txt's "
          f"W2 table, {len(row_n)} rows): {' '.join(str(v) for v in row_n)}")
    assert len(row_n) == 17
    print(f"  {bis_n} in the committed row: {bis_n in row_n} -> the new point is "
          f"{'NOT ' if bis_n not in row_n else ''}a committed grid point")
    assert bis_n not in row_n

    # ---- the NEW knob pair derivation (target 255,045)
    print()
    print("THE TARGET 255,045 DERIVATION (fresh -- NAMED, NOT HIDDEN: no")
    print("committed prior run exists at n=255,045, so no self-validation")
    print("against a committed run is possible for this target by")
    print("construction; the search itself is self-validated below against")
    print("the two committed targets 254,882 / 255,208):")
    print("knob arithmetic: n = (1,000,003*WORK_MUL)//NDIV (integer floor)")
    print("search box (sessions 21-27's box): WORK_MUL 1..2,048 x NDIV 1..8,192")
    ref_bis = pairs_for(255045)
    sm_bis = smallest(ref_bis)
    dbl_bis = doubles_in_box(ref_bis)
    print(f"pairs mapping to 255045 in-box: {len(ref_bis)}; smallest: "
          f"({sm_bis[0]}, {sm_bis[1]})")
    print(f"in-box pairs whose same-ratio double is also in-box: {len(dbl_bis)}")
    got = (N_FULL * sm_bis[0]) // sm_bis[1]
    print(f"smallest-pair arithmetic: (1,000,003*{sm_bis[0]})//{sm_bis[1]} = {got} "
          f"({'== 255045' if got == 255045 else 'MISMATCH'}) in the mapping set: "
          f"{sm_bis in ref_bis}; gcd(255045, 1,000,003) = {math.gcd(255045, N_FULL)}")
    assert got == 255045 and sm_bis in ref_bis and math.gcd(255045, N_FULL) == 1
    assert len(ref_bis) > 0

    # ---- the two committed knob pairs (both OLD)
    print()
    print("THE TWO COMMITTED KNOB PAIRS (both OLD):")
    for tag, pair, want in [("the ninth cut's row pair", (248, 973), 254882),
                            ("the anchor pair", (1213, 4753), 255208)]:
        got = (N_FULL * pair[0]) // pair[1]
        print(f"{tag} {pair}: (1,000,003*{pair[0]})//{pair[1]} = {got} "
              f"({'== ' + str(want) if got == want else 'MISMATCH'}) "
              f"in the mapping set: {pair in pairs_for(want)}; "
              f"gcd({want}, 1,000,003) = {math.gcd(want, N_FULL)}")
        assert got == want and pair in pairs_for(want)

    # ---- SEARCH SELF-VALIDATION against TWO committed runs per target
    ref_mid = pairs_for(254882)
    ref_hi = pairs_for(255208)
    m = re.search(r"pairs mapping to 254882 in-box: (\d+); smallest: \((\d+), (\d+)\)",
                  s123)
    assert m, "s123 run 254,882 line not parsed"
    want_n, want_sm = int(m.group(1)), (int(m.group(2)), int(m.group(3)))
    m2 = re.search(r"in-box pairs whose same-ratio double is also in-box: (\d+)", s123)
    assert m2, "s123 run doubles line not parsed"
    want_dbl = int(m2.group(1))
    print()
    print("SEARCH SELF-VALIDATION against session 123's committed run (254,882):")
    print(f"  pairs found: {len(ref_mid)} (s123 committed: {want_n}) -> "
          f"{'MATCH' if len(ref_mid) == want_n else 'MISMATCH'}")
    print(f"  smallest: {smallest(ref_mid)} (s123 committed: {want_sm}) -> "
          f"{'MATCH' if smallest(ref_mid) == want_sm else 'MISMATCH'}")
    print(f"  doubles in box: {len(doubles_in_box(ref_mid))} (s123 committed: {want_dbl}) -> "
          f"{'MATCH' if len(doubles_in_box(ref_mid)) == want_dbl else 'MISMATCH'}")
    assert len(ref_mid) == want_n and smallest(ref_mid) == want_sm \
        and len(doubles_in_box(ref_mid)) == want_dbl

    m = re.search(r"UPPER ANCHOR CITATION: pairs mapping to 255208 in-box: (\d+); "
                  r"smallest: \((\d+), (\d+)\)", s123)
    assert m, "s123 run 255,208 line not parsed"
    want_n, want_sm = int(m.group(1)), (int(m.group(2)), int(m.group(3)))
    print()
    print("SEARCH SELF-VALIDATION against session 123's committed run (255,208):")
    print(f"  pairs found: {len(ref_hi)} (s123 committed: {want_n}) -> "
          f"{'MATCH' if len(ref_hi) == want_n else 'MISMATCH'}")
    print(f"  smallest: {smallest(ref_hi)} (s123 committed: {want_sm}) -> "
          f"{'MATCH' if smallest(ref_hi) == want_sm else 'MISMATCH'}")
    assert len(ref_hi) == want_n and smallest(ref_hi) == want_sm

    flat131 = re.sub(r"\s+", " ", s131)
    m = re.search(r"against session 123's committed run \(254,882\): "
                  r"pairs found: (\d+) \(s123 committed: (\d+)\) -> MATCH "
                  r"smallest: \((\d+), (\d+)\) \(s123 committed: \((\d+), (\d+)\)\) "
                  r"-> MATCH doubles in box: (\d+) \(s123 committed: (\d+)\) -> MATCH",
                  flat131)
    assert m, "s131 run (254,882) self-validation block not parsed"
    want = (int(m.group(1)), (int(m.group(3)), int(m.group(4))), int(m.group(7)))
    print()
    print("SEARCH SELF-VALIDATION against session 131's committed run (254,882):")
    print(f"  pairs found: {len(ref_mid)} (s131 committed: {want[0]}) -> "
          f"{'MATCH' if len(ref_mid) == want[0] else 'MISMATCH'}")
    print(f"  smallest: {smallest(ref_mid)} (s131 committed: {want[1]}) -> "
          f"{'MATCH' if smallest(ref_mid) == want[1] else 'MISMATCH'}")
    print(f"  doubles in box: {len(doubles_in_box(ref_mid))} (s131 committed: {want[2]}) -> "
          f"{'MATCH' if len(doubles_in_box(ref_mid)) == want[2] else 'MISMATCH'}")
    assert len(ref_mid) == want[0] and smallest(ref_mid) == want[1] \
        and len(doubles_in_box(ref_mid)) == want[2]

    m = re.search(r"against session 123's committed run \(255,208\): "
                  r"pairs found: (\d+) \(s123 committed: (\d+)\) -> MATCH "
                  r"smallest: \((\d+), (\d+)\) \(s123 committed: \((\d+), (\d+)\)\) "
                  r"-> MATCH", flat131)
    assert m, "s131 run (255,208) self-validation block not parsed"
    want = (int(m.group(1)), (int(m.group(3)), int(m.group(4))))
    print()
    print("SEARCH SELF-VALIDATION against session 131's committed run (255,208):")
    print(f"  pairs found: {len(ref_hi)} (s131 committed: {want[0]}) -> "
          f"{'MATCH' if len(ref_hi) == want[0] else 'MISMATCH'}")
    print(f"  smallest: {smallest(ref_hi)} (s131 committed: {want[1]}) -> "
          f"{'MATCH' if smallest(ref_hi) == want[1] else 'MISMATCH'}")
    assert len(ref_hi) == want[0] and smallest(ref_hi) == want[1]

    # ---- the eleventh cut's letters and section-3 block rows (parsed)
    print()
    print("ELEVENTH CUT LETTERS AND BLOCK ROWS (parsed here from")
    print("publication-s132.txt):")
    scope_c1 = scope(flat, "C1 ARCHIVED CONTROL REPLICATION",
                     "C2 MULTI-BLOCK STABILITY AT THE NINTH CUT'S ROW POINT")
    mm = re.search(r"c2 \(sum,128,S=16\) pooled median (\d+), class (\S+) "
                   r"\(committed floor band (\d+)\.\.(\d+) at B=2\): (\S+)", scope_c1)
    assert mm, "eleventh cut C1 c2 line not parsed"
    print(f"  C1 c2: pooled median {mm.group(1)}, class {mm.group(2)}, committed "
          f"floor band {mm.group(3)}..{mm.group(4)} at B=2: {mm.group(5)}")
    mm = re.search(r"c8 \(sum,128,S=16\) pooled median (\d+) within \+/-5% of "
                   r"committed (\d+) \(session 4 pooled median\): (\S+)", scope_c1)
    assert mm, "eleventh cut C1 c8 line not parsed"
    print(f"  C1 c8: pooled median {mm.group(1)} within +/-5% of committed "
          f"{mm.group(2)} (session 4 pooled median): {mm.group(3)}")
    for tag, wm, ndiv, n, end in (
            ("mid", 248, 973, 254882, "hi (B=3, WM=1213"),
            ("hi", 1213, 4753, 255208, "c8 (B=8")):
        mm = re.search(
            rf"{tag} \(B=3, WM={wm}, NDIV={ndiv}, n={n}, [\d.]+ nominal total "
            rf"units\):.*?(?={re.escape(end)})", flat)
        assert mm, f"eleventh cut {tag} section-3 scope not parsed"
        sec = mm.group(0)
        blocks = re.findall(
            r"block(\d) runs [^ ]+ \(sum,128,16\) (\d+) 18-cell (\d+)\.\.(\d+) (\S+)",
            sec)
        assert len(blocks) == 8, f"eleventh cut {tag} block rows not parsed"
        pooled = re.search(
            r"pooled-24 runs [^ ]+ \(sum,128,16\) (\d+) 18-cell (\d+)\.\.(\d+) (\S+)",
            sec)
        assert pooled, f"eleventh cut {tag} pooled-24 row not parsed"
        print(f"  eleventh cut {tag} section-3 block rows (parsed): "
              + "; ".join(f"block{b} median {m} 18-cell {lo}..{hi} {cls}"
                          for b, m, lo, hi, cls in blocks))
        print(f"    pooled-24 median {pooled.group(1)} 18-cell "
              f"{pooled.group(2)}..{pooled.group(3)} {pooled.group(4)}")

    # ---- the eleventh cut's W2 trajectories and the COMPUTED counts
    print()
    print("  eleventh cut W2 per-run 18-cell min trajectories (parsed; the")
    print("  boundary-crossing counts COMPUTED here, descriptive only):")
    for tag, want_cross in (("mid", 2), ("hi", 5)):
        mm = re.search(
            rf"{tag} per-run 18-cell min: ([\d ]+?) {tag}: runs with 18-cell min "
            rf">= 1,000 \(COMPUTED here, descriptive\): (\d+/\d+)", flat)
        assert mm, f"eleventh cut {tag} W2 trajectory not parsed"
        vals = [int(x) for x in mm.group(1).split()]
        assert len(vals) == 24
        cross = sum(1 for v in vals if v >= 1000)
        print(f"    {tag}: {' '.join(str(v) for v in vals)}")
        print(f"    {tag}: runs with 18-cell min >= 1,000 (COMPUTED here, "
              f"descriptive): {cross}/{len(vals)} (published: {mm.group(2)})")
        assert cross == want_cross and mm.group(2) == f"{want_cross}/24"
    print("    " + parsed(
        pub132, r"(the tenth cut's computed counts at 12 runs: mid [\d/]+, "
                r"hi [\d/]+) -- parsed from publication-s129.txt"))

    # ---- arm table (protocol arm table; L1 work units)
    print()
    arms = [
        ("c2", 2, 1, 1, 3), ("mid", 3, 248, 973, 24),
        ("bis", 3, sm_bis[0], sm_bis[1], 24), ("c8", 8, 1, 1, 3),
    ]
    print("ARM TABLE (4 rows = 54 fresh processes; this table governs the run count):")
    print("nominal work units (definition, L1):")
    total = 0
    for tag, b, wm, ndiv, k in arms:
        n = (N_FULL * wm) // ndiv
        total += k
        print(f"  {tag:4s} B={b} WM={wm:<5} NDIV={ndiv:<5} n={n:<8} k={k:<3} {fmt_work(n, b)}")
    print()
    print("arm n self-checks:")
    for tag, b, wm, ndiv, k, want in [("mid", 3, 248, 973, 24, 254882),
                                      ("bis", 3, sm_bis[0], sm_bis[1], 24, 255045)]:
        got = (N_FULL * wm) // ndiv
        print(f"  {tag}: n={got} want={want} -> {'ok' if got == want else 'FAIL'}")
        assert got == want
    print(f"run count self-check: 3+24+24+3 = {total} -> "
          f"{'ok' if total == 54 else 'FAIL'}")
    assert total == 54
    print("frozen run order: c2-r01..r03, then interleaved mid/bis pairs "
          "k=01..24 (mid-r<k>, bis-r<k>), then c8-r01..r03 (controls bookend)")
    print("frozen block partition (per B=3 arm): block j = runs r(3j-2..3j) -> "
          "r01..r03 / r04..r06 / r07..r09 / r10..r12 / r13..r15 / r16..r18 / "
          "r19..r21 / r22..r24 (8 blocks of 3; the frozen 3-run classification "
          "method applies per block)")

    # ---- build replication pins (parsed from committed censuses; the mid
    # ---- pin is cross-checked 3-way s125/s129/s132; the bis triple is NEW)
    print()
    print("BUILD REPLICATION PINS (parsed here from committed censuses; 3/3")
    print("pinned OLD triples + the bis triple is NEW with NO pin (L8 named)):")
    bc125 = open("docs/evidence/gpu/anv-b3bisect9-20261031/build-census-s125.txt").read()
    bc129 = open("docs/evidence/gpu/anv-b3bisect10-20261031/build-census-s129.txt").read()
    bc132 = open("docs/evidence/gpu/anv-b3bisect11-20261031/build-census-s132.txt").read()
    pin_c2 = parsed(s27, r"anv-bb-c2 expected ([0-9a-f]{64})")
    pin_c8 = parsed(s27, r"anv-bb-c8 expected ([0-9a-f]{64})")
    pin_mid_125 = parsed(bc125, r"([0-9a-f]{64}) anv-bb-mid")
    pin_mid_129 = parsed(bc129, r"([0-9a-f]{64}) anv-bb-mid")
    pin_mid_132 = parsed(bc132, r"([0-9a-f]{64}) anv-bb-mid")
    print(f"  c2 pin (s27 census anv-bb-c2 expected): {pin_c2}")
    print(f"  c8 pin (s27 census anv-bb-c8 expected): {pin_c8}")
    print(f"  mid (3,248,973) pin (s125 build census anv-bb-mid -- the pair's "
          f"first measured digest): {pin_mid_125}")
    print(f"  mid cross-check (s129 build census anv-bb-mid -- the tenth cut's "
          f"byte-identical rebuild): {pin_mid_129} -> "
          f"{'MATCH' if pin_mid_125 == pin_mid_129 else 'MISMATCH'}")
    print(f"  mid cross-check (s132 build census anv-bb-mid -- the eleventh "
          f"cut's byte-identical rebuild): {pin_mid_132} -> "
          f"{'MATCH' if pin_mid_125 == pin_mid_132 else 'MISMATCH'}")
    assert pin_mid_125 == pin_mid_129 == pin_mid_132
    print(f"  bis (3,{sm_bis[0]},{sm_bis[1]}) pin: NONE -- NEW knob triple, "
          f"NO committed prior binary (L8 named); the measuring session builds "
          f"it fresh and records its digest in its build census")
    print("  NAMED, NOT HIDDEN: the mid pin binary was rebuilt BYTE-")
    print("  IDENTICAL at s129 AND s132 (build-census-s129.txt and")
    print("  build-census-s132.txt), so mid's committed readings (s125,")
    print("  s129, s132) all occurred at byte-identical binaries -- the")
    print("  in-window replication this cut pre-registers is content about")
    print("  RUN variance at fixed binary identity.")

    # ---- zero-derivation custody (parsed)
    print()
    print("ZERO-DERIVATION CUSTODY (parsed here):")
    dc125 = open("docs/evidence/gpu/anv-b3bisect9-20261031/derivation-census-s125.txt").read()
    dc129 = open("docs/evidence/gpu/anv-b3bisect10-20261031/derivation-census-s129.txt").read()
    print("  instrument digest (== s26 committed NDIV-derived source): " + parsed(
        dc125, r"gpu-subgroup-reduce-anv-ndiv\.c sha256 \(== session 27's committed \.c\.txt\): ([0-9a-f]{64})"))
    print("  cases-s27-a.txt sha256: " + parsed(dc125, r"cases-s27-a\.txt sha256: ([0-9a-f]{64})"))
    print("  expected-corpus.sha256 (byte-copy of s27's, s129 derivation census): "
          + parsed(dc129, r"expected-corpus\.sha256 byte-copy of session 27's: local sha256 ([0-9a-f]{64})"))
    print("  the a-set cell lines are a byte-copy of s27's; the byte-copy")
    print("  check is the measuring session's derivation-census duty")

    # ---- committed-byte citations (parsed, never transcribed)
    print()
    print("COMMITTED-BYTE CITATIONS (parsed here):")
    print("  s27 census (1213,4753) triple readings: " + parsed(
        s27, r"the \(1213,4753\) pair \(session 24 mid / session 25 hi / "
             r"session 26 hi\): ([\d,/\\s]+?) CAPTURED"))
    print("  s27 census committed controls: " + parsed(
        s27, r"committed controls: (c2 [\d]+ \(floor band [\d.]+\); c8 [\d,]+ \(session 4 pooled median\))"))
    print("  s121 publication hi reading: class "
          + parsed(pub121, r"class hi \(B=3, WM=1213, NDIV=4753, n=255208, [\d.]+ nominal units\): (\S+)")
          + ", pooled median " + parsed(pub121, r"hi \(sum,128,S=16\) pooled median (\d+) within"))
    print("  s125 publication mid reading: class "
          + parsed(pub125, r"class mid \(B=3, WM=248, NDIV=973, n=254882, [\d.]+ nominal units\): (\S+)")
          + ", pooled median " + parsed(
              pub125, r"mid 3 248 973 254882 [\d.]+ (\d+) [\d.]+\.\.[\d.]+ \d+\.\.\d+ \d+")
          + ", 18-cell " + parsed(
              pub125, r"mid 3 248 973 254882 [\d.]+ \d+ [\d.]+\.\.[\d.]+ (\d+\.\.\d+) \d+"))
    print("  s125 publication hi reading: class "
          + parsed(pub125, r"class hi \(B=3, WM=1213, NDIV=4753, n=255208, [\d.]+ nominal units\): (\S+)")
          + ", pooled median " + parsed(
              pub125, r"hi 3 1213 4753 255208 [\d.]+ (\d+) [\d.]+\.\.[\d.]+ \d+\.\.\d+ \d+")
          + ", 18-cell " + parsed(
              pub125, r"hi 3 1213 4753 255208 [\d.]+ \d+ [\d.]+\.\.[\d.]+ (\d+\.\.\d+) \d+"))

    ledger = open("docs/evidence/gpu/settle-bar-ledger.txt").read()
    counted, seen = [], set()
    for line in ledger.splitlines():
        if line.startswith("day="):
            d = re.match(r"day=(\S+) session=(\S+) class=(\S+) median=(\d+) min=(\d+)", line)
            if d is not None and d.group(1) not in seen:
                seen.add(d.group(1))
                counted.append(d.groups())
    print(f"  settle-bar-ledger.txt counted rows (first qualifying per UTC day): "
          f"{len(counted)}")
    for row in counted:
        print(f"    day={row[0]} session={row[1]} class={row[2]} median={row[3]} min={row[4]}")
    pin = open("docs/evidence/gpu/anv-b3w7ledgerappend-20261031/bar-s117-eval-post-run1.txt").read()
    print("  frozen evaluator committed pin (bar-s117-eval-post-run1.txt) VERDICT: "
          + parsed(pin, r"VERDICT: (.+)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
