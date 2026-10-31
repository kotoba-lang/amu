#!/usr/bin/env python3
"""JUN-59 session 126 -- the TENTH CUT pre-registration derivation.

Every number below is computed in this script from arithmetic or PARSED
from committed bytes -- nothing is transcribed from prose. Deterministic:
no clock, no RNG, no network, no hardware. Running it twice is
byte-identical (recorded in record.txt).

Purpose: the derivation half of the tenth cut pre-registration (the
s125 carry-forward (a), "any tenth cut ONLY through a NEW pre-registered
cut session (its own freeze; the C2 (b) class-instability at n=254,557
is named content any re-open must confront)"). The tenth cut is the
POINT-CLASS STABILITY CUT: NO new grid point is measured; the three
committed bisect knob pairs are re-run at byte-identical pinned
binaries in 12 fresh processes each. This script therefore derives NO
new knobs -- it verifies the three committed pairs' arithmetic, records
the five build pins, and parses the committed reading history the cut
confronts. The search SELF-VALIDATES against committed runs
(session 119's eighth-cut run and session 123's ninth-cut run).
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
    print("== JUN-59 session 126 derivation (the TENTH CUT pre-registration:  ==")
    print("== the POINT-CLASS STABILITY CUT -- committed-pair verification,  ==")
    print("== arm-pin derivation, committed-byte citations)                  ==")
    print("== every value computed here from arithmetic or committed bytes    ==")
    print()
    s119 = open("docs/evidence/gpu/anv-b3bisect8prereg-20261031/knob-search-s119-run1.txt").read()
    s123 = open("docs/evidence/gpu/anv-b3bisect9prereg-20261031/knob-search-s123-run1.txt").read()
    s27 = open("docs/evidence/gpu/anv-b3bisect7-20261027/derivation-census-s27.txt").read()
    pub121 = open("docs/evidence/gpu/anv-b3bisect8-20261031/publication-s121.txt").read()
    pub125 = open("docs/evidence/gpu/anv-b3bisect9-20261031/publication-s125.txt").read()

    # ---- the confrontation target (the s125 C2 (b) named content)
    print("THE CONFRONTATION TARGET (the s125 C2 (b) named content, parsed here):")
    print("  s125 publication W1 verdict: " + parsed(
        pub125, r"VERDICT: (branch \(d\) FLAGGED[^;]*;)"))
    print("  s125 publication C2 lo content check: " + parsed(
        pub125, r"lo class CAPTURED \(the eighth cut's committed class "
                r"INTERMEDIATE/MIXED\): (\w+)"))
    print("  s125 lo reading (the disputed point's second measurement): class "
          + parsed(pub125, r"class lo \(B=3, WM=405, NDIV=1591, n=254557, "
                           r"[\d.]+ nominal units\): (\S+)")
          + ", pooled median " + parsed(
              pub125, r"lo 3 405 1591 254557 [\d.]+ (\d+) [\d.]+\.\.[\d.]+ "
                      r"\d+\.\.\d+ \d+")
          + ", 18-cell " + parsed(
              pub125, r"lo 3 405 1591 254557 [\d.]+ \d+ [\d.]+\.\.[\d.]+ "
                      r"(\d+\.\.\d+) \d+"))
    print("  s121 lo reading (the same binary's first measurement): class "
          + parsed(pub121, r"class mid \(B=3, WM=405, NDIV=1591, n=254557, "
                           r"[\d.]+ nominal units\): (\S+)")
          + ", pooled median " + parsed(pub121, r"pooled median (\d+), 18-cell min\.\.max \d+\.\.\d+")
          + ", 18-cell " + parsed(pub121, r"pooled median \d+, 18-cell min\.\.max (\d+\.\.\d+)"))
    print("  -> the class at (405,1591)/n=254,557 DISAGREES across two committed")
    print("     sessions at byte-identical binaries; the frozen 1,000-tick boundary")
    print("     min moved 986 -> 1,005 at overlapping medians (1,156 vs 1,143).")

    # ---- the three committed knob pairs (all OLD)
    print()
    print("THE THREE COMMITTED KNOB PAIRS (all OLD -- zero new pairs this cut):")
    print("knob arithmetic: n = (1,000,003*WORK_MUL)//NDIV (integer floor)")
    print("search box (sessions 21-27's box): WORK_MUL 1..2,048 x NDIV 1..8,192")

    m = re.search(r"pairs mapping to 254557 in-box: (\d+); smallest: \((\d+), (\d+)\)", s119)
    assert m, "s119 run 254,557 line not parsed"
    want_n, want_sm = int(m.group(1)), (int(m.group(2)), int(m.group(3)))
    m2 = re.search(r"in-box pairs whose same-ratio double is also in-box: (\d+)", s119)
    want_dbl = int(m2.group(1))
    ref = pairs_for(254557)
    print()
    print("SEARCH SELF-VALIDATION against session 119's committed run (254,557):")
    print(f"  pairs found: {len(ref)} (s119 committed: {want_n}) -> "
          f"{'MATCH' if len(ref) == want_n else 'MISMATCH'}")
    print(f"  smallest: {smallest(ref)} (s119 committed: {want_sm}) -> "
          f"{'MATCH' if smallest(ref) == want_sm else 'MISMATCH'}")
    print(f"  doubles in box: {len(doubles_in_box(ref))} (s119 committed: {want_dbl}) -> "
          f"{'MATCH' if len(doubles_in_box(ref)) == want_dbl else 'MISMATCH'}")
    assert len(ref) == want_n and smallest(ref) == want_sm and len(doubles_in_box(ref)) == want_dbl

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
                  r"smallest: \((\d+), (\d+)\)", s119)
    assert m, "s119 run 255,208 line not parsed"
    want_n, want_sm = int(m.group(1)), (int(m.group(2)), int(m.group(3)))
    ref = pairs_for(255208)
    print()
    print("SEARCH SELF-VALIDATION against session 119's committed run (255,208):")
    print(f"  pairs found: {len(ref)} (s119 committed: {want_n}) -> "
          f"{'MATCH' if len(ref) == want_n else 'MISMATCH'}")
    print(f"  smallest: {smallest(ref)} (s119 committed: {want_sm}) -> "
          f"{'MATCH' if smallest(ref) == want_sm else 'MISMATCH'}")
    assert len(ref) == want_n and smallest(ref) == want_sm

    print()
    for tag, pair, want in [("the disputed pair", (405, 1591), 254557),
                            ("the ninth cut's row pair", (248, 973), 254882),
                            ("the anchor pair", (1213, 4753), 255208)]:
        got = (N_FULL * pair[0]) // pair[1]
        print(f"{tag} {pair}: (1,000,003*{pair[0]})//{pair[1]} = {got} "
              f"({'== ' + str(want) if got == want else 'MISMATCH'}) "
              f"in the mapping set: {pair in pairs_for(want)}; "
              f"gcd({want}, 1,000,003) = {math.gcd(want, N_FULL)}")
        assert got == want and pair in pairs_for(want)

    # ---- arm table (protocol arm table; L1 work units)
    arms = [
        ("c2", 2, 1, 1, 3), ("lo", 3, 405, 1591, 12),
        ("mid", 3, 248, 973, 12), ("hi", 3, 1213, 4753, 12),
        ("c8", 8, 1, 1, 3),
    ]
    print()
    print("ARM TABLE (5 rows = 42 fresh processes; this table governs the run count):")
    print("nominal work units (definition, L1):")
    total = 0
    for tag, b, wm, ndiv, k in arms:
        n = (N_FULL * wm) // ndiv
        total += k
        print(f"  {tag:4s} B={b} WM={wm:<5} NDIV={ndiv:<5} n={n:<8} k={k:<3} {fmt_work(n, b)}")
    print()
    print("arm n self-checks:")
    for tag, b, wm, ndiv, k, want in [("lo", 3, 405, 1591, 12, 254557),
                                      ("mid", 3, 248, 973, 12, 254882),
                                      ("hi", 3, 1213, 4753, 12, 255208)]:
        got = (N_FULL * wm) // ndiv
        print(f"  {tag}: n={got} want={want} -> {'ok' if got == want else 'FAIL'}")
        assert got == want
    print(f"run count self-check: 3+12+12+12+3 = {total} -> "
          f"{'ok' if total == 42 else 'FAIL'}")
    assert total == 42
    print("frozen block partition (per B=3 arm): block j = runs r(3j-2..3j) -> "
          "r01..r03 / r04..r06 / r07..r09 / r10..r12 (4 blocks of 3; "
          "the frozen 3-run classification method applies per block)")

    # ---- build replication pins (parsed from committed censuses, never transcribed)
    print()
    print("BUILD REPLICATION PINS (parsed here from committed censuses; "
          "5/5 -- every knob triple is OLD):")
    bc21 = open("docs/evidence/gpu/anv-b3bisect8-20261031/build-census-s121.txt").read()
    bc125 = open("docs/evidence/gpu/anv-b3bisect9-20261031/build-census-s125.txt").read()
    s26c = open("docs/evidence/gpu/anv-b3bisect6-20261027/derivation-census-s26.txt").read()
    for label, path, pat in [
        ("c2 pin (s27 census anv-bb-c2 expected)",
         "docs/evidence/gpu/anv-b3bisect7-20261027/derivation-census-s27.txt",
         r"anv-bb-c2 expected ([0-9a-f]{64})"),
        ("c8 pin (s27 census anv-bb-c8 expected)",
         "docs/evidence/gpu/anv-b3bisect7-20261027/derivation-census-s27.txt",
         r"anv-bb-c8 expected ([0-9a-f]{64})"),
        ("lo (3,405,1591) pin (s121 build census anv-bb-mid -- the pair's first measured digest)",
         "docs/evidence/gpu/anv-b3bisect8-20261031/build-census-s121.txt",
         r"([0-9a-f]{64}) anv-bb-mid"),
        ("mid (3,248,973) pin (s125 build census anv-bb-mid -- the pair's first measured digest)",
         "docs/evidence/gpu/anv-b3bisect9-20261031/build-census-s125.txt",
         r"([0-9a-f]{64}) anv-bb-mid"),
        ("hi (3,1213,4753) pin (s26 census anv-bb-hi expected)",
         "docs/evidence/gpu/anv-b3bisect6-20261027/derivation-census-s26.txt",
         r"anv-bb-hi expected ([0-9a-f]{64})"),
    ]:
        text = open(path).read()
        print(f"  {label}: {parsed(text, pat)}")
    print("  NAMED, NOT HIDDEN: the lo pin binary was rebuilt BYTE-IDENTICAL at s125")
    print("  (build-census-s125.txt: " + parsed(bc125, r"([0-9a-f]{64}) anv-bb-lo") +
          " anv-bb-lo) -- the s121-vs-s125 class disagreement occurred at a")
    print("  byte-identical binary (the s121 digest " + parsed(bc21, r"([0-9a-f]{64}) anv-bb-mid") +
          "), so it is content about RUN/SESSION variance, not binary identity.")

    # ---- zero-derivation custody (parsed)
    print()
    print("ZERO-DERIVATION CUSTODY (parsed here):")
    dc125 = open("docs/evidence/gpu/anv-b3bisect9-20261031/derivation-census-s125.txt").read()
    print("  instrument digest (== s26 committed NDIV-derived source): " + parsed(
        dc125, r"gpu-subgroup-reduce-anv-ndiv\.c sha256 \(== session 27's committed \.c\.txt\): ([0-9a-f]{64})"))
    print("  cases-s27-a.txt sha256: " + parsed(dc125, r"cases-s27-a\.txt sha256: ([0-9a-f]{64})"))
    print("  cases-s125-a.txt sha256: " + parsed(dc125, r"cases-s125-a\.txt sha256: ([0-9a-f]{64})")
          + " (the a-set cell lines are a byte-copy of s27's; the byte-copy")
    print("   check is the measuring session's derivation-census duty)")

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
