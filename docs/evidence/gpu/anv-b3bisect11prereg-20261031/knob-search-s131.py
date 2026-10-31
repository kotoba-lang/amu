#!/usr/bin/env python3
"""JUN-59 session 131 -- the ELEVENTH CUT pre-registration derivation.

Every number below is computed in this script from arithmetic or PARSED
from committed bytes -- nothing is transcribed from prose. Deterministic:
no clock, no RNG, no network, no hardware. Running it twice is
byte-identical (recorded in record.txt).

Purpose: the derivation half of the eleventh cut pre-registration (the
s130 carry-forward (a), "any eleventh cut ONLY through a NEW
pre-registered cut session confronting the L9 block-run-instability
content"). The eleventh cut is the MULTI-BLOCK STABILITY REQUIREMENT
CUT: NO new grid point is measured; the two points where the tenth cut
fired L9 (mid n=254,882 and hi n=255,208) are re-run at byte-identical
pinned binaries in 24 fresh processes each (8 blocks of 3 -- double the
tenth cut's block count, confronting L10's named coarseness). This
script therefore derives NO new knobs -- it verifies the two committed
pairs' arithmetic, records the four build pins (each cross-checked
against the tenth cut's byte-identical rebuild), and parses the
committed reading history the cut confronts. The search SELF-VALIDATES
against committed runs (session 123's ninth-cut run and session 126's
tenth-cut derivation run).
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


def main():
    print("== JUN-59 session 131 derivation (the ELEVENTH CUT pre-       ==")
    print("== registration: the MULTI-BLOCK STABILITY REQUIREMENT CUT --  ==")
    print("== committed-pair verification, arm-pin derivation,            ==")
    print("== committed-byte citations)                                  ==")
    print("== every value computed here from arithmetic or committed bytes ==")
    print()
    s119 = open("docs/evidence/gpu/anv-b3bisect8prereg-20261031/knob-search-s119-run1.txt").read()
    s123 = open("docs/evidence/gpu/anv-b3bisect9prereg-20261031/knob-search-s123-run1.txt").read()
    s126 = open("docs/evidence/gpu/anv-b3bisect10prereg-20261031/knob-search-s126-run1.txt").read()
    s27 = open("docs/evidence/gpu/anv-b3bisect7-20261027/derivation-census-s27.txt").read()
    pub121 = open("docs/evidence/gpu/anv-b3bisect8-20261031/publication-s121.txt").read()
    pub125 = open("docs/evidence/gpu/anv-b3bisect9-20261031/publication-s125.txt").read()
    pub129 = open("docs/evidence/gpu/anv-b3bisect10-20261031/publication-s129.txt").read()

    # ---- the confrontation target (the tenth cut's L9 block-run-instability
    # ---- content at mid AND hi -- the s130 carry-forward (a) named content)
    print("THE CONFRONTATION TARGET (the tenth cut's L9 block-run-instability")
    print("content at mid AND hi, parsed here from publication-s129.txt):")
    print("  tenth cut CUT VERDICT: " + parsed(
        pub129, r"CUT VERDICT \(pre-named composition, section 0's RESUMABILITY "
                r"RULE\): (the stability precondition .*?False\))"))
    print("  tenth cut C2 lo letter (a) block classes: " + parsed(
        pub129, r"lo \(BATCH=3,WORK_MUL=405,NDIV=1591\) at n=254,557[^:]*: "
                r"\(a\) block classes: \[([^\]]*)\]")
          + "; pooled-12 class: " + parsed(
        pub129, r"lo \(BATCH=3,WORK_MUL=405,NDIV=1591\) at n=254,557[^:]*: "
                r"\(a\) block classes: \[[^\]]*\]; pooled-12 class: (\S+)")
          + "; blocks " + parsed(
        pub129, r"lo \(BATCH=3,WORK_MUL=405,NDIV=1591\) at n=254,557[^:]*: "
                r"\(a\) block classes[^;]*; pooled-12 class: \S+ "
                r"\(sum,128,S=16\): blocks ([\d /]+?) ;"))
    print("  tenth cut C3 mid letter (c) block classes: " + parsed(
        pub129, r"mid \(BATCH=3,WORK_MUL=248,NDIV=973\) at n=254,882[^:]*: "
                r"\(c\) block classes: \[([^\]]*)\]")
          + "; pooled-12 class: " + parsed(
        pub129, r"mid \(BATCH=3,WORK_MUL=248,NDIV=973\) at n=254,882[^:]*: "
                r"\(c\) block classes: \[[^\]]*\]; pooled-12 class: (\S+)")
          + "; blocks " + parsed(
        pub129, r"mid \(BATCH=3,WORK_MUL=248,NDIV=973\) at n=254,882[^:]*: "
                r"\(c\) block classes[^;]*; pooled-12 class: \S+ "
                r"\(sum,128,S=16\): blocks ([\d /]+?) ;"))
    print("  tenth cut W1 hi letter (c) block classes: " + parsed(
        pub129, r"hi \(BATCH=3,WORK_MUL=1213,NDIV=4753\) at n=255,208[^:]*: "
                r"\(c\) block classes: \[([^\]]*)\]")
          + "; pooled-12 class: " + parsed(
        pub129, r"hi \(BATCH=3,WORK_MUL=1213,NDIV=4753\) at n=255,208[^:]*: "
                r"\(c\) block classes: \[[^\]]*\]; pooled-12 class: (\S+)")
          + "; blocks " + parsed(
        pub129, r"hi \(BATCH=3,WORK_MUL=1213,NDIV=4753\) at n=255,208[^:]*: "
                r"\(c\) block classes[^;]*; pooled-12 class: \S+ "
                r"\(sum,128,S=16\): blocks ([\d /]+?) ;"))

    # ---- the tenth cut's per-run 18-cell min trajectories (W2) and the
    # ---- boundary-crossing counts COMPUTED from the parsed strings
    flat = re.sub(r"\s+", " ", pub129)
    traj = re.search(
        r"lo per-run 18-cell min: ([\d ]+?) mid per-run 18-cell min: "
        r"([\d ]+?) hi per-run 18-cell min: ([\d ]+?) the three", flat)
    assert traj, "tenth cut W2 trajectories not parsed"
    lo_min, mid_min, hi_min = traj.groups()
    print("  tenth cut W2 per-run 18-cell min trajectories (parsed):")
    for tag, s in (("lo", lo_min), ("mid", mid_min), ("hi", hi_min)):
        vals = [int(x) for x in s.split()]
        cross = sum(1 for v in vals if v >= 1000)
        print(f"    {tag}: {' '.join(str(v) for v in vals)}")
        print(f"    {tag}: runs with 18-cell min >= 1,000 (COMPUTED here, "
              f"descriptive): {cross}/{len(vals)}")
    assert len(lo_min.split()) == 12 and len(mid_min.split()) == 12 \
        and len(hi_min.split()) == 12

    # ---- the tenth cut's section-3 block minima (the fine content the
    # ---- eleventh cut confronts at 8 blocks)
    for tag, wm, ndiv, n in (("mid", 248, 973, 254882), ("hi", 1213, 4753, 255208)):
        sec = parsed(pub129,
                     rf"{tag} \(B=3, WM={wm}, NDIV={ndiv}, n={n}, [\d.]+ "
                     r"nominal total units\): (.*?) pooled-12 runs", re.S)
        blocks = re.findall(
            r"block(\d) runs [^ ]+ \(sum,128,16\) (\d+) 18-cell (\d+)\.\.(\d+) (\S+)",
            sec)
        assert len(blocks) == 4, f"tenth cut {tag} block rows not parsed"
        print(f"  tenth cut {tag} section-3 block rows (parsed): "
              + "; ".join(f"block{b} median {m} 18-cell {lo}..{hi} {cls}"
                          for b, m, lo, hi, cls in blocks))

    # ---- the two committed knob pairs (both OLD)
    print()
    print("THE TWO COMMITTED KNOB PAIRS (both OLD -- zero new pairs this cut):")
    print("knob arithmetic: n = (1,000,003*WORK_MUL)//NDIV (integer floor)")
    print("search box (sessions 21-27's box): WORK_MUL 1..2,048 x NDIV 1..8,192")

    m = re.search(r"pairs mapping to 254882 in-box: (\d+); smallest: \((\d+), (\d+)\)", s123)
    assert m, "s123 run 254,882 line not parsed"
    want_n, want_sm = int(m.group(1)), (int(m.group(2)), int(m.group(3)))
    m2 = re.search(r"in-box pairs whose same-ratio double is also in-box: (\d+)", s123)
    want_dbl = int(m2.group(1))
    ref = pairs_for(254882)
    print()
    print("SEARCH SELF-VALIDATION against session 123's committed run (254,882):")
    print(f"  pairs found: {len(ref)} (s123 committed: {want_n}) -> "
          f"{'MATCH' if len(ref) == want_n else 'MISMATCH'}")
    print(f"  smallest: {smallest(ref)} (s123 committed: {want_sm}) -> "
          f"{'MATCH' if smallest(ref) == want_sm else 'MISMATCH'}")
    print(f"  doubles in box: {len(doubles_in_box(ref))} (s123 committed: {want_dbl}) -> "
          f"{'MATCH' if len(doubles_in_box(ref)) == want_dbl else 'MISMATCH'}")
    assert len(ref) == want_n and smallest(ref) == want_sm and len(doubles_in_box(ref)) == want_dbl

    m = re.search(r"UPPER ANCHOR CITATION: pairs mapping to 255208 in-box: (\d+); "
                  r"smallest: \((\d+), (\d+)\)", s123)
    assert m, "s123 run 255,208 line not parsed"
    want_n, want_sm = int(m.group(1)), (int(m.group(2)), int(m.group(3)))
    ref_hi = pairs_for(255208)
    print()
    print("SEARCH SELF-VALIDATION against session 123's committed run (255,208):")
    print(f"  pairs found: {len(ref_hi)} (s123 committed: {want_n}) -> "
          f"{'MATCH' if len(ref_hi) == want_n else 'MISMATCH'}")
    print(f"  smallest: {smallest(ref_hi)} (s123 committed: {want_sm}) -> "
          f"{'MATCH' if smallest(ref_hi) == want_sm else 'MISMATCH'}")
    assert len(ref_hi) == want_n and smallest(ref_hi) == want_sm

    flat126 = re.sub(r"\s+", " ", s126)
    m = re.search(r"against session 123's committed run \(254,882\): "
                  r"pairs found: (\d+) \(s123 committed: (\d+)\) -> MATCH "
                  r"smallest: \((\d+), (\d+)\) \(s123 committed: \((\d+), (\d+)\)\) "
                  r"-> MATCH doubles in box: (\d+) \(s123 committed: (\d+)\) -> MATCH", flat126)
    assert m, "s126 run (254,882) self-validation block not parsed"
    want = (int(m.group(1)), (int(m.group(3)), int(m.group(4))), int(m.group(7)))
    print()
    print("SEARCH SELF-VALIDATION against session 126's committed run (254,882):")
    print(f"  pairs found: {len(ref)} (s126 committed: {want[0]}) -> "
          f"{'MATCH' if len(ref) == want[0] else 'MISMATCH'}")
    print(f"  smallest: {smallest(ref)} (s126 committed: {want[1]}) -> "
          f"{'MATCH' if smallest(ref) == want[1] else 'MISMATCH'}")
    print(f"  doubles in box: {len(doubles_in_box(ref))} (s126 committed: {want[2]}) -> "
          f"{'MATCH' if len(doubles_in_box(ref)) == want[2] else 'MISMATCH'}")
    assert len(ref) == want[0] and smallest(ref) == want[1] and len(doubles_in_box(ref)) == want[2]

    m = re.search(r"against session 119's committed run \(255,208\): "
                  r"pairs found: (\d+) \(s119 committed: (\d+)\) -> MATCH "
                  r"smallest: \((\d+), (\d+)\) \(s119 committed: \((\d+), (\d+)\)\) -> MATCH", flat126)
    assert m, "s126 run (255,208) self-validation block not parsed"
    want = (int(m.group(1)), (int(m.group(3)), int(m.group(4))))
    print()
    print("SEARCH SELF-VALIDATION against session 126's committed run (255,208):")
    print(f"  pairs found: {len(ref_hi)} (s126 committed: {want[0]}) -> "
          f"{'MATCH' if len(ref_hi) == want[0] else 'MISMATCH'}")
    print(f"  smallest: {smallest(ref_hi)} (s126 committed: {want[1]}) -> "
          f"{'MATCH' if smallest(ref_hi) == want[1] else 'MISMATCH'}")
    assert len(ref_hi) == want[0] and smallest(ref_hi) == want[1]

    print()
    for tag, pair, want in [("the ninth cut's row pair", (248, 973), 254882),
                            ("the anchor pair", (1213, 4753), 255208)]:
        got = (N_FULL * pair[0]) // pair[1]
        print(f"{tag} {pair}: (1,000,003*{pair[0]})//{pair[1]} = {got} "
              f"({'== ' + str(want) if got == want else 'MISMATCH'}) "
              f"in the mapping set: {pair in pairs_for(want)}; "
              f"gcd({want}, 1,000,003) = {math.gcd(want, N_FULL)}")
        assert got == want and pair in pairs_for(want)

    # ---- arm table (protocol arm table; L1 work units)
    arms = [
        ("c2", 2, 1, 1, 3), ("mid", 3, 248, 973, 24),
        ("hi", 3, 1213, 4753, 24), ("c8", 8, 1, 1, 3),
    ]
    print()
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
                                      ("hi", 3, 1213, 4753, 24, 255208)]:
        got = (N_FULL * wm) // ndiv
        print(f"  {tag}: n={got} want={want} -> {'ok' if got == want else 'FAIL'}")
        assert got == want
    print(f"run count self-check: 3+24+24+3 = {total} -> "
          f"{'ok' if total == 54 else 'FAIL'}")
    assert total == 54
    print("frozen block partition (per B=3 arm): block j = runs r(3j-2..3j) -> "
          "r01..r03 / r04..r06 / r07..r09 / r10..r12 / r13..r15 / r16..r18 / "
          "r19..r21 / r22..r24 (8 blocks of 3; the frozen 3-run classification "
          "method applies per block)")

    # ---- build replication pins (parsed from committed censuses, never
    # ---- transcribed; each B=3 pin cross-checked against the tenth cut's
    # ---- byte-identical rebuild census)
    print()
    print("BUILD REPLICATION PINS (parsed here from committed censuses; "
          "4/4 -- every knob triple is OLD):")
    bc125 = open("docs/evidence/gpu/anv-b3bisect9-20261031/build-census-s125.txt").read()
    bc129 = open("docs/evidence/gpu/anv-b3bisect10-20261031/build-census-s129.txt").read()
    s26c = open("docs/evidence/gpu/anv-b3bisect6-20261027/derivation-census-s26.txt").read()
    pin_c2 = parsed(s27, r"anv-bb-c2 expected ([0-9a-f]{64})")
    pin_c8 = parsed(s27, r"anv-bb-c8 expected ([0-9a-f]{64})")
    pin_mid = parsed(bc125, r"([0-9a-f]{64}) anv-bb-mid")
    pin_mid_129 = parsed(bc129, r"([0-9a-f]{64}) anv-bb-mid")
    pin_hi = parsed(s26c, r"anv-bb-hi expected ([0-9a-f]{64})")
    pin_hi_129 = parsed(bc129, r"([0-9a-f]{64}) anv-bb-hi")
    print(f"  c2 pin (s27 census anv-bb-c2 expected): {pin_c2}")
    print(f"  c8 pin (s27 census anv-bb-c8 expected): {pin_c8}")
    print(f"  mid (3,248,973) pin (s125 build census anv-bb-mid -- the pair's "
          f"first measured digest): {pin_mid}")
    print(f"  mid cross-check (s129 build census anv-bb-mid -- the tenth cut's "
          f"byte-identical rebuild): {pin_mid_129} -> "
          f"{'MATCH' if pin_mid == pin_mid_129 else 'MISMATCH'}")
    print(f"  hi (3,1213,4753) pin (s26 census anv-bb-hi expected): {pin_hi}")
    print(f"  hi cross-check (s129 build census anv-bb-hi -- the tenth cut's "
          f"byte-identical rebuild): {pin_hi_129} -> "
          f"{'MATCH' if pin_hi == pin_hi_129 else 'MISMATCH'}")
    assert pin_mid == pin_mid_129 and pin_hi == pin_hi_129
    print("  NAMED, NOT HIDDEN: both B=3 pin binaries were rebuilt BYTE-")
    print("  IDENTICAL at s129 (build-census-s129.txt 5/5), so the tenth")
    print("  cut's block-run instability occurred at byte-identical")
    print("  binaries -- it is content about RUN variance, not binary")
    print("  identity, and it is exactly what this cut confronts at 8")
    print("  blocks.")

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
             r"session 26 hi\): ([\d,/\s]+?) CAPTURED"))
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
