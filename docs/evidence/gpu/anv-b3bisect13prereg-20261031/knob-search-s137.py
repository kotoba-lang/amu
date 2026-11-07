#!/usr/bin/env python3
"""JUN-59 session 137 -- the THIRTEENTH CUT pre-registration derivation.

Every number below is computed in this script from arithmetic or PARSED
from committed bytes -- nothing is transcribed from prose. Deterministic:
no clock, no RNG, no network, no hardware. Running it twice is
byte-identical (recorded in record.txt).

Purpose: the derivation half of the thirteenth cut pre-registration (the
s136 carry-forward (a): "any thirteenth cut ONLY through a NEW
pre-registered cut session (its own freeze; this cut's 8-block
BLOCK-UNSTABLE content at mid AND 255,045 must be confronted first)").
The thirteenth cut is THE 16-BLOCK STABILITY CONFRONTATION CUT -- the
direct extension of the eleventh cut's confrontation shape (which
confronted the tenth cut's 4-block block-run-instability by doubling the
block count to 8 at the same points at byte-identical pinned binaries,
ZERO NEW KNOB TRIPLES): this cut confronts the twelfth cut's 8-block
BLOCK-UNSTABLE content at mid (248,973) n=254,882 AND bis (3,316,1239)
n=255,045 by doubling the block count to 16 (16 blocks of 3 per B=3 arm,
k=48 per point) at the same two points at their byte-identical pinned
binaries, ZERO NEW KNOB TRIPLES (4/4 pinned: the bis pin is s136's first
measured digest, now declared). NO narrowing claim is pre-registered by
this cut (the MID-ONLY NARROWING CLAIM stays SUSPENDED (named, not
claimed), the 12th cut's W1 (c) content).

This script verifies the two measured pairs' arithmetic, SELF-VALIDATES
its pair search against committed runs (sessions 123/131/133), parses
every cited value from committed bytes (publication-s136.txt's
C1/C2/C3/W1 letters and section-3 block rows -- the named content being
confronted; its W2 trajectories with COMPUTED boundary-crossing counts;
its X1 spreads; the pre-named cross-window disagreement content quoted
in its section 0; the bracket; the s136 build census pins with the mid
4-way cross-check s125/s129/s132/s136 and the bis first-measured-digest
pin; the ledger rows and the frozen evaluator pin verdict).
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
    print("== JUN-59 session 137 derivation (the THIRTEENTH CUT pre-       ==")
    print("== registration: THE 16-BLOCK STABILITY CONFRONTATION CUT --     ==")
    print("== confronting the twelfth cut's 8-block BLOCK-UNSTABLE content  ==")
    print("== at mid AND 255,045 at byte-identical pinned binaries, ZERO    ==")
    print("== NEW KNOB TRIPLES, 102 fresh processes)                        ==")
    print("== every value computed here from arithmetic or committed bytes ==")
    print()
    s123 = open("docs/evidence/gpu/anv-b3bisect9prereg-20261031/knob-search-s123-run1.txt").read()
    s131 = open("docs/evidence/gpu/anv-b3bisect11prereg-20261031/knob-search-s131-run1.txt").read()
    s133 = open("docs/evidence/gpu/anv-b3bisect12prereg-20261031/knob-search-s133-run1.txt").read()
    s27 = open("docs/evidence/gpu/anv-b3bisect7-20261027/derivation-census-s27.txt").read()
    pub125 = open("docs/evidence/gpu/anv-b3bisect9-20261031/publication-s125.txt").read()
    pub132 = open("docs/evidence/gpu/anv-b3bisect11-20261031/publication-s132.txt").read()
    pub136 = open("docs/evidence/gpu/anv-b3bisect12-20261031/publication-s136.txt").read()
    state136 = open("docs/evidence/gpu/anv-b3bisect12-20261031/state-s136.txt").read()
    flat = re.sub(r"\s+", " ", pub136)

    # ---- the named content being confronted: the twelfth cut's letters
    print("THE NAMED CONTENT BEING CONFRONTED (parsed here from")
    print("publication-s136.txt -- the twelfth cut's measurement half):")
    scope_c2 = scope(flat, "C2 MULTI-BLOCK STABILITY AT THE NEW GRID POINT",
                     "C3 IN-WINDOW REPLICATION AT THE CLAIMED ANCHOR")
    scope_c3 = scope(flat, "C3 IN-WINDOW REPLICATION AT THE CLAIMED ANCHOR",
                     "W1 THE MID-ONLY NARROWING")
    scope_w1 = scope(flat, "W1 THE MID-ONLY NARROWING", "W2 (pre-registered")
    mm = re.search(r"\(([a-d])\) block classes: "
                   r"\[([^\]]*)\]; pooled-24 class: (\S+) \(sum,128,S=16\): blocks "
                   r"([\d /]+?) ; pooled-24 (\d+)", scope_c2)
    assert mm, "twelfth cut C2 block rows not parsed"
    c2_letter, c2_classes, c2_pooled_cls, c2_blocks, c2_pooled = mm.groups()
    print(f"  twelfth cut C2 bis letter ({c2_letter}) block classes: [{c2_classes}]")
    print(f"    pooled-24 class: {c2_pooled_cls}; blocks {c2_blocks}; "
          f"pooled-24 {c2_pooled}")
    mm = re.search(r"\(([a-d])\) block classes: "
                   r"\[([^\]]*)\]; pooled-24 class: (\S+) \(sum,128,S=16\): blocks "
                   r"([\d /]+?) ; pooled-24 (\d+)", scope_c3)
    assert mm, "twelfth cut C3 block rows not parsed"
    c3_letter, c3_classes, c3_pooled_cls, c3_blocks, c3_pooled = mm.groups()
    print(f"  twelfth cut C3 mid letter ({c3_letter}) block classes: [{c3_classes}]")
    print(f"    pooled-24 class: {c3_pooled_cls}; blocks {c3_blocks}; "
          f"pooled-24 {c3_pooled}")
    mm = re.findall(r"W1 \(([a-d])\)", scope_w1)
    assert mm, "twelfth cut W1 letter not parsed"
    w1_letter = mm[-1]  # the VERDICT line; the header quotes "W1 (d)" first
    print(f"  twelfth cut W1 letter ({w1_letter}) -- the CUT VERDICT")
    print("    " + parsed(
        pub136, r"(\(c\) SUSPENDED \(named, not claimed\), no movement -- mid is "
                r"BLOCK-RUN-UNSTABLE at the finer granularity too\.)"))
    assert c2_letter == "c" and c3_letter == "c" and w1_letter == "c"
    assert c2_pooled_cls == "CAPTURED" and c3_pooled_cls == "CAPTURED"
    print("  the twelfth cut's C2 (c) AND C3 (c) are the 8-block BLOCK-UNSTABLE")
    print("  content at bis (255,045) AND mid (254,882) this cut confronts.")

    # ---- the committed bracket (parsed) -- this cut narrows NOTHING
    print()
    print("THE COMMITTED BRACKET (parsed; this cut narrows NOTHING by")
    print("construction -- it is a stability cut):")
    br = parsed(pub136, r"the committed bracket stays \(([\d, ]+)\]")
    print(f"  the committed bracket (parsed from publication-s136.txt): ({br}]")
    assert br == "254,557, 255,208"

    # ---- the pre-named cross-window disagreement at mid (real content)
    print()
    print("THE PRE-NAMED CROSS-WINDOW DISAGREEMENT AT MID (real content;")
    print("parsed here -- s132's quoted block rows in publication-s136.txt")
    print("section 0 vs this cut's own section-3 rows):")
    scope_132 = scope(flat,
                      "session 132 (the eleventh cut): C2 (a) STABLE-INTERMEDIATE",
                      "bis (3,316,1239) at n=255,045 -- the new grid point")
    rows132 = re.findall(r"block\d median (\d+) 18-cell (\d+)\.\.(\d+) (\S+)",
                         scope_132)
    assert len(rows132) == 8, "s132 quoted mid block rows not parsed"
    pooled132 = re.search(
        r"pooled-24 median (\d+) 18-cell (\d+)\.\.(\d+) (\S+)", scope_132)
    assert pooled132, "s132 quoted mid pooled-24 row not parsed"
    print("  session 132 window (the eleventh cut, C2 (a) STABLE-INTERMEDIATE):")
    print("    block medians " + "/".join(r[0] for r in rows132)
          + " classes " + "/".join(r[3] for r in rows132))
    print(f"    pooled-24 median {pooled132.group(1)} 18-cell "
          f"{pooled132.group(2)}..{pooled132.group(3)} {pooled132.group(4)}")
    scope_mid136 = scope(flat,
                         "mid (B=3, WM=248, NDIV=973, n=254882, 0.764644 nominal total units):",
                         "bis (B=3, WM=316, NDIV=1239, n=255045,")
    blocks136 = re.findall(
        r"block\d runs [^ ]+ \(sum,128,16\) (\d+) 18-cell (\d+)\.\.(\d+) (\S+)",
        scope_mid136)
    assert len(blocks136) == 8, "twelfth cut mid block rows not parsed"
    pooled136 = re.search(
        r"pooled-24 runs [^ ]+ \(sum,128,16\) (\d+) 18-cell (\d+)\.\.(\d+) (\S+)",
        scope_mid136)
    assert pooled136, "twelfth cut mid pooled-24 row not parsed"
    print("  session 136 window (the twelfth cut, C3 (c) BLOCK-UNSTABLE):")
    print("    block medians " + "/".join(r[0] for r in blocks136)
          + " classes " + "/".join(r[3] for r in blocks136))
    print(f"    pooled-24 median {pooled136.group(1)} 18-cell "
          f"{pooled136.group(2)}..{pooled136.group(3)} {pooled136.group(4)}")
    print("    at the SAME byte-identical pinned binary (cabff942..., section 2)")
    assert pooled132.group(4) == "INTERMEDIATE/MIXED" \
        and pooled136.group(4) == "CAPTURED"

    # ---- the two measured knob pairs (both OLD)
    print()
    print("THE TWO MEASURED KNOB PAIRS (both OLD -- ZERO NEW KNOB TRIPLES):")
    for tag, pair, want in [("the confrontation point pair", (248, 973), 254882),
                            ("the new grid point pair", (316, 1239), 255045)]:
        got = (N_FULL * pair[0]) // pair[1]
        print(f"{tag} {pair}: (1,000,003*{pair[0]})//{pair[1]} = {got} "
              f"({'== ' + str(want) if got == want else 'MISMATCH'}) "
              f"in the mapping set: {pair in pairs_for(want)}; "
              f"gcd({want}, 1,000,003) = {math.gcd(want, N_FULL)}")
        assert got == want and pair in pairs_for(want)
        assert math.gcd(want, N_FULL) == 1

    # ---- SEARCH SELF-VALIDATION against committed runs
    ref_mid = pairs_for(254882)
    ref_bis = pairs_for(255045)
    ref_hi = pairs_for(255208)
    m = re.search(r"pairs mapping to 254882 in-box: (\d+); smallest: \((\d+), (\d+)\)",
                  s123)
    assert m, "s123 run 254,882 line not parsed"
    want_n, want_sm = int(m.group(1)), (int(m.group(2)), int(m.group(3)))
    m2 = re.search(r"in-box pairs whose same-ratio double is also in-box: (\d+)",
                   s123)
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

    flat133 = re.sub(r"\s+", " ", s133)
    m = re.search(r"pairs mapping to 255045 in-box: (\d+); smallest: \((\d+), (\d+)\)",
                  flat133)
    assert m, "s133 run 255,045 line not parsed"
    want_n, want_sm = int(m.group(1)), (int(m.group(2)), int(m.group(3)))
    m2 = re.search(r"in-box pairs whose same-ratio double is also in-box: (\d+)",
                   flat133)
    assert m2, "s133 run 255,045 doubles line not parsed"
    want_dbl = int(m2.group(1))
    print()
    print("SEARCH SELF-VALIDATION against session 133's committed run (255,045)")
    print("  (the twelfth cut's derivation; the pair is now also a COMMITTED")
    print("  MEASURED pair -- session 136's bis arm):")
    print(f"  pairs found: {len(ref_bis)} (s133 committed: {want_n}) -> "
          f"{'MATCH' if len(ref_bis) == want_n else 'MISMATCH'}")
    print(f"  smallest: {smallest(ref_bis)} (s133 committed: {want_sm}) -> "
          f"{'MATCH' if smallest(ref_bis) == want_sm else 'MISMATCH'}")
    print(f"  doubles in box: {len(doubles_in_box(ref_bis))} (s133 committed: {want_dbl}) -> "
          f"{'MATCH' if len(doubles_in_box(ref_bis)) == want_dbl else 'MISMATCH'}")
    assert len(ref_bis) == want_n and smallest(ref_bis) == want_sm \
        and len(doubles_in_box(ref_bis)) == want_dbl
    print("  session 136's committed bis arm (publication-s136.txt, parsed): "
          + parsed(flat, r"(bis \(B=3, WM=316, NDIV=1239, n=255045, k=24\))")
          + " -> the smallest in-box pair IS the measured pair")

    # ---- the twelfth cut's letters (C1) and section-3 block rows (parsed)
    print()
    print("TWELFTH CUT C1 AND SECTION-3 ROWS (parsed here from")
    print("publication-s136.txt -- the content this cut confronts at the")
    print("same binaries):")
    scope_c1 = scope(flat, "C1 ARCHIVED CONTROL REPLICATION",
                     "C2 MULTI-BLOCK STABILITY AT THE NEW GRID POINT")
    mm = re.search(r"c2 \(sum,128,S=16\) pooled median (\d+), class (\S+) "
                   r"\(committed floor band (\d+)\.\.(\d+) at B=2\): (\S+)", scope_c1)
    assert mm, "twelfth cut C1 c2 line not parsed"
    print(f"  C1 c2: pooled median {mm.group(1)}, class {mm.group(2)}, committed "
          f"floor band {mm.group(3)}..{mm.group(4)} at B=2: {mm.group(5)}")
    mm = re.search(r"c8 \(sum,128,S=16\) pooled median (\d+) within \+/-5% of "
                   r"committed (\d+) \(session 4 pooled median\): (\S+)", scope_c1)
    assert mm, "twelfth cut C1 c8 line not parsed"
    print(f"  C1 c8: pooled median {mm.group(1)} within +/-5% of committed "
          f"{mm.group(2)} (session 4 pooled median): {mm.group(3)}")
    scope_bis136 = scope(flat,
                         "bis (B=3, WM=316, NDIV=1239, n=255045, 0.765133 nominal total units):",
                         "c8 (B=8, WM=1, NDIV=1, n=1000003,")
    blocks_bis136 = re.findall(
        r"block\d runs [^ ]+ \(sum,128,16\) (\d+) 18-cell (\d+)\.\.(\d+) (\S+)",
        scope_bis136)
    assert len(blocks_bis136) == 8, "twelfth cut bis block rows not parsed"
    pooled_bis136 = re.search(
        r"pooled-24 runs [^ ]+ \(sum,128,16\) (\d+) 18-cell (\d+)\.\.(\d+) (\S+)",
        scope_bis136)
    assert pooled_bis136, "twelfth cut bis pooled-24 row not parsed"
    print("  twelfth cut bis section-3 block rows (parsed): "
          + "; ".join(f"block{i + 1} median {m} 18-cell {lo}..{hi} {cls}"
                      for i, (m, lo, hi, cls) in enumerate(blocks_bis136)))
    print(f"    pooled-24 median {pooled_bis136.group(1)} 18-cell "
          f"{pooled_bis136.group(2)}..{pooled_bis136.group(3)} {pooled_bis136.group(4)}")
    print("  twelfth cut mid section-3 block rows (parsed): "
          + "; ".join(f"block{i + 1} median {m} 18-cell {lo}..{hi} {cls}"
                      for i, (m, lo, hi, cls) in enumerate(blocks136)))
    print(f"    pooled-24 median {pooled136.group(1)} 18-cell "
          f"{pooled136.group(2)}..{pooled136.group(3)} {pooled136.group(4)}")
    print(f"  mid block classes: {sum(1 for r in blocks136 if r[3] == 'CAPTURED')}x "
          f"CAPTURED + {sum(1 for r in blocks136 if r[3] != 'CAPTURED')}x "
          f"INTERMEDIATE/MIXED")
    print(f"  bis block classes: {sum(1 for r in blocks_bis136 if r[3] == 'CAPTURED')}x "
          f"CAPTURED + {sum(1 for r in blocks_bis136 if r[3] != 'CAPTURED')}x "
          f"INTERMEDIATE/MIXED")

    # ---- the twelfth cut's W2 trajectories and the COMPUTED counts
    print()
    print("  twelfth cut W2 per-run 18-cell min trajectories (parsed; the")
    print("  boundary-crossing counts COMPUTED here, descriptive only):")
    for tag, want_cross in (("mid", 9), ("bis", 10)):
        mm = re.search(
            rf"{tag} per-run 18-cell min: ([\d ]+?) {tag}: runs with 18-cell min "
            rf">= 1,000 \(COMPUTED here, descriptive\): (\d+/\d+)", flat)
        assert mm, f"twelfth cut {tag} W2 trajectory not parsed"
        vals = [int(x) for x in mm.group(1).split()]
        assert len(vals) == 24
        cross = sum(1 for v in vals if v >= 1000)
        print(f"    {tag}: {' '.join(str(v) for v in vals)}")
        print(f"    {tag}: runs with 18-cell min >= 1,000 (COMPUTED here, "
              f"descriptive): {cross}/{len(vals)} (published: {mm.group(2)})")
        assert cross == want_cross and mm.group(2) == f"{want_cross}/24"
    print("    " + parsed(
        flat, r"(the eleventh cut's computed counts at 24 runs: mid [\d/]+, "
              r"hi [\d/]+; the tenth cut's at 12 runs: mid [\d/]+, "
              r"lo [\d/]+ -- all parsed, quote-only)"))

    # ---- X1 spreads (parsed)
    print()
    print("  twelfth cut X1 host_ns spreads (parsed, descriptive only):")
    for tag, want_pct in (("mid", "856.0"), ("bis", "273.6")):
        mm = re.search(
            rf"{tag}: per-run host_ns median min\.\.max (\d+)\.\.(\d+) "
            rf"\(spread (\d+) = ([\d.]+)% of min; k=(\d+)\)", flat)
        assert mm, f"twelfth cut X1 {tag} line not parsed"
        print(f"    {tag}: min..max {mm.group(1)}..{mm.group(2)} spread "
              f"{mm.group(3)} = {mm.group(4)}% of min; k={mm.group(5)}")
        assert mm.group(4) == want_pct

    # ---- arm table (protocol arm table; L1 work units)
    print()
    arms = [
        ("c2", 2, 1, 1, 3), ("mid", 3, 248, 973, 48),
        ("bis", 3, 316, 1239, 48), ("c8", 8, 1, 1, 3),
    ]
    print("ARM TABLE (4 rows = 102 fresh processes; this table governs the run count):")
    print("nominal work units (definition, L1):")
    total = 0
    for tag, b, wm, ndiv, k in arms:
        n = (N_FULL * wm) // ndiv
        total += k
        print(f"  {tag:4s} B={b} WM={wm:<5} NDIV={ndiv:<5} n={n:<8} k={k:<3} {fmt_work(n, b)}")
    print()
    print("arm n self-checks:")
    for tag, b, wm, ndiv, k, want in [("mid", 3, 248, 973, 48, 254882),
                                      ("bis", 3, 316, 1239, 48, 255045)]:
        got = (N_FULL * wm) // ndiv
        print(f"  {tag}: n={got} want={want} -> {'ok' if got == want else 'FAIL'}")
        assert got == want
    print(f"run count self-check: 3+48+48+3 = {total} -> "
          f"{'ok' if total == 102 else 'FAIL'}")
    assert total == 102
    print("frozen run order: c2-r01..r03, then interleaved mid/bis pairs "
          "k=01..48 (mid-r<k>, bis-r<k>), then c8-r01..r03 (controls bookend)")
    print("frozen block partition (per B=3 arm): block j = runs r(3j-2..3j) "
          "for j=1..16 (16 blocks of 3; the frozen 3-run classification "
          "method applies per block); pooled-48 alongside (named extension)")

    # ---- build replication pins (parsed from committed censuses; the mid
    # ---- pin is cross-checked 4-way s125/s129/s132/s136; the bis pin is
    # ---- s136's first measured digest, now declared)
    print()
    print("BUILD REPLICATION PINS (parsed here from committed censuses; 4/4")
    print("pinned OLD triples -- ZERO NEW KNOB TRIPLES):")
    bc125 = open("docs/evidence/gpu/anv-b3bisect9-20261031/build-census-s125.txt").read()
    bc129 = open("docs/evidence/gpu/anv-b3bisect10-20261031/build-census-s129.txt").read()
    bc132 = open("docs/evidence/gpu/anv-b3bisect11-20261031/build-census-s132.txt").read()
    bc136 = open("docs/evidence/gpu/anv-b3bisect12-20261031/build-census-s136.txt").read()
    pin_c2 = parsed(s27, r"anv-bb-c2 expected ([0-9a-f]{64})")
    pin_c8 = parsed(s27, r"anv-bb-c8 expected ([0-9a-f]{64})")
    pin_mid_125 = parsed(bc125, r"([0-9a-f]{64}) anv-bb-mid")
    pin_mid_129 = parsed(bc129, r"([0-9a-f]{64}) anv-bb-mid")
    pin_mid_132 = parsed(bc132, r"([0-9a-f]{64}) anv-bb-mid")
    pin_mid_136 = parsed(bc136, r"([0-9a-f]{64}) anv-bb-mid")
    pin_bis = parsed(bc136, r"([0-9a-f]{64}) anv-bb-bis")
    pin_bis_state = parsed(state136, r"NEW triple ([0-9a-f]{64})")
    print(f"  c2 pin (s27 census anv-bb-c2 expected): {pin_c2}")
    print(f"  c8 pin (s27 census anv-bb-c8 expected): {pin_c8}")
    print(f"  mid (3,248,973) pin (s125 build census anv-bb-mid -- the pair's "
          f"first measured digest): {pin_mid_125}")
    print(f"  mid cross-check (s129): {pin_mid_129} -> "
          f"{'MATCH' if pin_mid_125 == pin_mid_129 else 'MISMATCH'}")
    print(f"  mid cross-check (s132): {pin_mid_132} -> "
          f"{'MATCH' if pin_mid_125 == pin_mid_132 else 'MISMATCH'}")
    print(f"  mid cross-check (s136): {pin_mid_136} -> "
          f"{'MATCH' if pin_mid_125 == pin_mid_136 else 'MISMATCH'}")
    assert pin_mid_125 == pin_mid_129 == pin_mid_132 == pin_mid_136
    print(f"  bis (3,316,1239) pin (s136 build census anv-bb-bis -- the pair's "
          f"first measured digest, now DECLARED as the pin): {pin_bis}")
    print(f"  bis pin cross-check (state-s136.txt recorded digest): "
          f"{pin_bis_state} -> "
          f"{'MATCH' if pin_bis == pin_bis_state else 'MISMATCH'}")
    assert pin_bis == pin_bis_state
    assert re.fullmatch(r"[0-9a-f]{64}", pin_c2) and re.fullmatch(r"[0-9a-f]{64}", pin_c8)
    assert re.fullmatch(r"[0-9a-f]{64}", pin_mid_125) and re.fullmatch(r"[0-9a-f]{64}", pin_bis)
    print("  NAMED, NOT HIDDEN: mid's FOUR committed readings (s125, s129,")
    print("  s132, s136) all occurred at this byte-identical binary; bis's")
    print("  ONE committed reading (s136) occurred at ITS byte-identical")
    print("  binary. The instability this cut confronts occurred at exactly")
    print("  these binaries.")

    # ---- zero-derivation custody (parsed)
    print()
    print("ZERO-DERIVATION CUSTODY (parsed here from derivation-census-s136.txt):")
    dc136 = open("docs/evidence/gpu/anv-b3bisect12-20261031/derivation-census-s136.txt").read()
    print("  instrument digest (== s26 committed NDIV-derived source): " + parsed(
        dc136, r"instrument gpu-subgroup-reduce-anv-ndiv\.c\.txt sha256: ([0-9a-f]{64})"))
    print("  expected-corpus.sha256 (byte-copy of s27's): " + parsed(
        dc136, r"expected-corpus\.sha256 sha256: ([0-9a-f]{64})"))
    print("  a-set cell lines' block sha256 (== s27 == s132 == s136): " + parsed(
        dc136, r"the 24 cell lines' block sha256: ([0-9a-f]{64})"))
    print("  the a-set cell lines are a byte-copy of s27's; the byte-copy")
    print("  check is the measuring session's derivation-census duty")

    # ---- committed-byte citations (parsed, never transcribed)
    print()
    print("COMMITTED-BYTE CITATIONS (parsed here):")
    print("  s125 publication mid reading: class "
          + parsed(pub125, r"class mid \(B=3, WM=248, NDIV=973, n=254882, [\d.]+ nominal units\): (\S+)")
          + ", pooled median " + parsed(
              pub125, r"mid 3 248 973 254882 [\d.]+ (\d+) [\d.]+\.\.[\d.]+ \d+\.\.\d+ \d+")
          + ", 18-cell " + parsed(
              pub125, r"mid 3 248 973 254882 [\d.]+ \d+ [\d.]+\.\.[\d.]+ (\d+\.\.\d+) \d+"))
    print("  s132 publication mid letter and pooled-24 (quoted in")
    print("    publication-s136.txt section 0, parsed): "
          + parsed(flat, r"session 132 \(the eleventh cut\): C2 \(([a-d])\) STABLE-INTERMEDIATE")
          + ", pooled-24 " + parsed(
              flat, r"session 132 \(the eleventh cut\): C2 \(a\) STABLE-INTERMEDIATE.*?pooled-24 median (\d+)")
          + " INTERMEDIATE/MIXED")
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
