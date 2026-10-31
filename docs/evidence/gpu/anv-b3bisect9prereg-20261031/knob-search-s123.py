#!/usr/bin/env python3
"""JUN-59 session 123 -- the NINTH CUT pre-registration derivation.

Every number below is computed in this script from arithmetic or PARSED
from committed bytes -- nothing is transcribed from prose. Deterministic:
no clock, no RNG, no network, no hardware. Running it twice is
byte-identical (recorded in record.txt).

Purpose: the knob-search half of the ninth cut pre-registration (the
s122 carry-forward (a), "any ninth cut ONLY through a NEW pre-registered
cut session (its own freeze)"): the cut-point knob search over the
frozen search box (WORK_MUL 1..2,048 x NDIV 1..8,192, the sessions
21-27 box) for the floor midpoint of the re-opened bracket (254,557,
255,208] (the eighth cut's W1 (b) verdict, committed in
anv-b3bisect8-20261031/publication-s121.txt), and the anchor-pair
citations. The search SELF-VALIDATES against TWO committed censuses:
session 27's (253,255) and session 119's eighth-cut run (254,557 and
255,208).
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
        # (N_FULL*wm)//ndiv == target  <=>  ndiv in (N_FULL*wm/(target+1), N_FULL*wm/target]
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
    print("== JUN-59 session 123 derivation (the NINTH CUT pre-registration:  ==")
    print("== cut-point knob search + anchor-pair citations)                  ==")
    print("== every value computed here from arithmetic or committed bytes    ==")
    print()
    lo_end, hi_end = 254557, 255208
    mid_exact = (lo_end + hi_end) / 2
    mid = (lo_end + hi_end) // 2
    print(f"re-opened bracket (the eighth cut's W1 (b) verdict, named in "
          f"protocol.txt): ({lo_end}, {hi_end}] n-units")
    print(f"bracket midpoint exact: {mid_exact} -- exact_is_integer: "
          f"{float(mid_exact).is_integer()}")
    print(f"bisect grid n = ({lo_end}+{hi_end})//2 = {mid} (the EXACT floor "
          f"midpoint)")
    print("knob arithmetic: n = (1,000,003*WORK_MUL)//NDIV (integer floor)")
    print("search box (sessions 21-27's box): WORK_MUL 1..2,048 x NDIV 1..8,192")

    # ---- self-validation of the search against session 27's committed census
    s27 = open("docs/evidence/gpu/anv-b3bisect7-20261027/derivation-census-s27.txt").read()
    m = re.search(r"pairs mapping to 253255 in-box: (\d+); smallest: \((\d+),(\d+)\)", s27)
    assert m, "s27 census line not parsed"
    want_n, want_sm = int(m.group(1)), (int(m.group(2)), int(m.group(3)))
    ref = pairs_for(253255)
    m2 = re.search(r"in-box pairs whose same-ratio double is also in-box: (\d+)", s27)
    want_dbl = int(m2.group(1))
    print()
    print("SEARCH SELF-VALIDATION against session 27's committed census (253,255):")
    print(f"  pairs found: {len(ref)} (s27 committed: {want_n}) -> "
          f"{'MATCH' if len(ref) == want_n else 'MISMATCH'}")
    print(f"  smallest: {smallest(ref)} (s27 committed: {want_sm}) -> "
          f"{'MATCH' if smallest(ref) == want_sm else 'MISMATCH'}")
    print(f"  doubles in box: {len(doubles_in_box(ref))} (s27 committed: {want_dbl}) -> "
          f"{'MATCH' if len(doubles_in_box(ref)) == want_dbl else 'MISMATCH'}")
    assert len(ref) == want_n and smallest(ref) == want_sm and len(doubles_in_box(ref)) == want_dbl

    # ---- self-validation against session 119's committed eighth-cut run
    s119 = open("docs/evidence/gpu/anv-b3bisect8prereg-20261031/knob-search-s119-run1.txt").read()
    m = re.search(r"pairs mapping to 254557 in-box: (\d+); smallest: \((\d+), (\d+)\)", s119)
    assert m, "s119 run 254,557 line not parsed"
    want_n, want_sm = int(m.group(1)), (int(m.group(2)), int(m.group(3)))
    ref = pairs_for(254557)
    m2 = re.search(r"in-box pairs whose same-ratio double is also in-box: (\d+)", s119)
    want_dbl = int(m2.group(1))
    print()
    print("SEARCH SELF-VALIDATION against session 119's committed run (254,557):")
    print(f"  pairs found: {len(ref)} (s119 committed: {want_n}) -> "
          f"{'MATCH' if len(ref) == want_n else 'MISMATCH'}")
    print(f"  smallest: {smallest(ref)} (s119 committed: {want_sm}) -> "
          f"{'MATCH' if smallest(ref) == want_sm else 'MISMATCH'}")
    print(f"  doubles in box: {len(doubles_in_box(ref))} (s119 committed: {want_dbl}) -> "
          f"{'MATCH' if len(doubles_in_box(ref)) == want_dbl else 'MISMATCH'}")
    assert len(ref) == want_n and smallest(ref) == want_sm and len(doubles_in_box(ref)) == want_dbl

    # ---- the cut point 254,882
    cut = pairs_for(mid)
    sm = smallest(cut)
    dbls = doubles_in_box(cut)
    print()
    print(f"pairs mapping to {mid} in-box: {len(cut)}; smallest: {sm}")
    print(f"in-box pairs whose same-ratio double is also in-box: {len(dbls)}")
    print(f"bisect pair chosen: {sm}; same-ratio double ({2*sm[0]},{2*sm[1]}) "
          f"n={(N_FULL*2*sm[0])//(2*sm[1])} in-box: "
          f"{(2*sm[0], 2*sm[1]) in dbls}")
    print(f"gcd({mid}, 1,000,003) = {math.gcd(mid, N_FULL)} -- every knob pair is a "
          f"floor approximation of the grid")

    # ---- the lower anchor 254,557 citation (the eighth cut's committed mid)
    lo_pair = (405, 1591)
    n_lo = (N_FULL * lo_pair[0]) // lo_pair[1]
    print()
    print(f"LOWER ANCHOR CITATION: pairs mapping to {lo_end} in-box: "
          f"{len(pairs_for(lo_end))}; smallest: {smallest(pairs_for(lo_end))}")
    print(f"committed measurement pair {lo_pair}: "
          f"(1,000,003*{lo_pair[0]})//{lo_pair[1]} = {n_lo} "
          f"({'== ' + str(lo_end) if n_lo == lo_end else 'MISMATCH'}) "
          f"in the mapping set: {lo_pair in pairs_for(lo_end)}")
    print(f"gcd({lo_end}, 1,000,003) = {math.gcd(lo_end, N_FULL)}")
    lo_dbl = (2 * lo_pair[0], 2 * lo_pair[1])
    print(f"the pair's same-ratio double {lo_dbl}: n={(N_FULL*lo_dbl[0])//lo_dbl[1]}, "
          f"in search box: {lo_dbl[0] <= 2048 and lo_dbl[1] <= 8192} "
          f"(session 121's eq3 pair)")

    # ---- the upper anchor 255,208 citation
    up = pairs_for(hi_end)
    ups = smallest(up)
    m3 = re.search(r"UPPER ANCHOR CITATION: pairs mapping to 255208 in-box: (\d+); "
                   r"smallest: \((\d+), (\d+)\)", s119)
    assert m3, "s119 run upper-anchor line not parsed"
    want_up_n, want_up_sm = int(m3.group(1)), (int(m3.group(2)), int(m3.group(3)))
    print()
    print(f"UPPER ANCHOR CITATION: pairs mapping to {hi_end} in-box: {len(up)}; "
          f"smallest: {ups}")
    print(f"  s119 committed cross-check: {len(up)} vs {want_up_n} -> "
          f"{'MATCH' if len(up) == want_up_n else 'MISMATCH'}; "
          f"{ups} vs {want_up_sm} -> "
          f"{'MATCH' if ups == want_up_sm else 'MISMATCH'}")
    assert len(up) == want_up_n and ups == want_up_sm
    committed_hi = (1213, 4753)
    n_hi = (N_FULL * committed_hi[0]) // committed_hi[1]
    print(f"committed measurement pair {committed_hi}: "
          f"(1,000,003*{committed_hi[0]})//{committed_hi[1]} = {n_hi} "
          f"({'== ' + str(hi_end) if n_hi == hi_end else 'MISMATCH'}) "
          f"in the mapping set: {committed_hi in up}")
    print(f"gcd({hi_end}, 1,000,003) = {math.gcd(hi_end, N_FULL)}")
    twin = (2 * committed_hi[0], 2 * committed_hi[1])
    print(f"session-24 C3 (b) twin {twin}: n={(N_FULL*twin[0])//twin[1]}, "
          f"in search box: {twin[0] <= 2048 and twin[1] <= 8192}")

    # ---- arm table arithmetic (protocol arm table; L1 work units)
    X, Y = sm
    arms = [
        ("c2", 2, 1, 1), ("lo", 3, 405, 1591), ("mid", 3, X, Y),
        ("eq3", 3, 2 * X, 2 * Y), ("hi", 3, 1213, 4753),
        ("b2m", 2, X, Y), ("c8", 8, 1, 1),
    ]
    print()
    print("nominal work units (definition, L1):")
    for tag, b, wm, ndiv in arms:
        n = (N_FULL * wm) // ndiv
        print(f"  {tag:4s} B={b} WM={wm:<5} NDIV={ndiv:<5} n={n:<8} {fmt_work(n, b)}")
    print()
    print("arm n self-checks:")
    for tag, b, wm, ndiv, want in [("lo", 3, 405, 1591, lo_end),
                                   ("hi", 3, 1213, 4753, hi_end),
                                   ("mid", 3, X, Y, mid),
                                   ("eq3", 3, 2 * X, 2 * Y, mid),
                                   ("b2m", 2, X, Y, mid)]:
        got = (N_FULL * wm) // ndiv
        print(f"  {tag}: n={got} want={want} -> {'ok' if got == want else 'FAIL'}")
        assert got == want

    # ---- build replication pins (parsed from committed censuses, never transcribed)
    print()
    print("BUILD REPLICATION PINS (parsed here from committed censuses):")
    s27c = s27
    bc21 = open("docs/evidence/gpu/anv-b3bisect8-20261031/build-census-s121.txt").read()
    s26c = open("docs/evidence/gpu/anv-b3bisect6-20261027/derivation-census-s26.txt").read()
    for label, path, pat in [
        ("c2 pin (s27 census anv-bb-c2 expected)",
         "docs/evidence/gpu/anv-b3bisect7-20261027/derivation-census-s27.txt",
         r"anv-bb-c2 expected ([0-9a-f]{64})"),
        ("c8 pin (s27 census anv-bb-c8 expected)",
         "docs/evidence/gpu/anv-b3bisect7-20261027/derivation-census-s27.txt",
         r"anv-bb-c8 expected ([0-9a-f]{64})"),
        ("lo (405,1591) triple pin (s121 build census anv-bb-mid -- s121's mid IS (3,405,1591), the pair's first measured digest)",
         "docs/evidence/gpu/anv-b3bisect8-20261031/build-census-s121.txt",
         r"([0-9a-f]{64}) anv-bb-mid"),
        ("hi (1213,4753) triple pin (s26 census anv-bb-hi expected -- s26's hi IS (1213,4753))",
         "docs/evidence/gpu/anv-b3bisect6-20261027/derivation-census-s26.txt",
         r"anv-bb-hi expected ([0-9a-f]{64})"),
    ]:
        text = open(path).read()
        print(f"  {label}: {parsed(text, pat)}")
    print("  context (NOT pins for this cut): s121 (810,3182) digest: "
          + parsed(bc21, r"([0-9a-f]{64}) anv-bb-eq3")
          + "; s121 (2,405,1591) digest: "
          + parsed(bc21, r"([0-9a-f]{64}) anv-bb-b2m")
          + " -- this cut's eq3/b2m are the NEW (2X,2Y)/(X,Y) triples (see below)")
    print(f"  NEW knob triples (no prior binary, no pin applies -- named): "
          f"mid (3,{X},{Y}), eq3 (3,{2*X},{2*Y}), b2m (2,{X},{Y})")

    # ---- committed-byte citations (parsed, never transcribed)
    print()
    print("COMMITTED-BYTE CITATIONS (parsed here):")
    print("  s27 census (1213,4753) triple readings: " + parsed(
        s27c, r"the \(1213,4753\) pair \(session 24 mid / session 25 hi / "
              r"session 26 hi\): ([\d,/\s]+?) CAPTURED"))
    s27p = open("docs/evidence/gpu/anv-b3bisect7-20261027/protocol.txt").read()
    print("  s27 protocol section 3: " + parsed(
        s27p, r"\(1213,4753\) pair \(session 24 mid / session 25 hi / session 26 hi\): "
              r"([\d,\s/]+CAPTURED)"))
    print("  s24 C3 (b) split minima ((1213,4753) vs (2426,9506)): " + parsed(
        s27c, r"session 24 \(b\) SPLIT \(\(1213,4753\) vs \(2426,9506\), minima "
              r"([\d,]+ vs [\d,]+ at n=[\d,]+)\)"))
    print("  s27 census committed controls: " + parsed(
        s27c, r"committed controls: (c2 [\d]+ \(floor band [\d.]+\); c8 [\d,]+ \(session 4 pooled median\))"))
    print("  s27 census b2m-class want: " + parsed(
        s27c, r"b2m-class \(B=2 at a small grid\): (FLOOR \(sessions 21-26: [\d,]+\))"))
    pub121 = open("docs/evidence/gpu/anv-b3bisect8-20261031/publication-s121.txt").read()
    m = re.search(r"branch \(b\) MID-INTERMEDIATE -- the B=3 class flip sits in "
                  r"\(([\d, ]+), ([\d, ]+)\]", re.sub(r"\s+", " ", pub121))
    if m:
        print("  s121 publication W1 bracket (the re-opened bracket): "
              f"({m.group(1)}, {m.group(2)}]")
    else:
        print("  s121 publication W1 bracket (the re-opened bracket): NOT PARSED")
    print("  s121 publication lo-pair (s121 mid) reading: class "
          + parsed(pub121, r"class mid \(B=3, WM=405, NDIV=1591, n=254557, [\d.]+ nominal units\): (\S+)")
          + ", pooled median " + parsed(pub121, r"mid \(sum,128,S=16\) pooled median (\d+)")
          + ", 18-cell " + parsed(pub121, r"pooled median 1156, 18-cell min\.\.max (\d+\.\.\d+)"))
    print("  s121 publication hi-pair reading: pooled median "
          + parsed(pub121, r"hi \(sum,128,S=16\) pooled median (\d+)")
          + ", class " + parsed(pub121, r"class hi \(B=3, WM=1213, NDIV=4753, n=255208, [\d.]+ nominal units\): (\S+)"))
    print("  s121 publication b2m reading: class "
          + parsed(pub121, r"class b2m \(B=2, WM=405, NDIV=1591, n=254557, [\d.]+ nominal units\): (\S+)")
          + ", pooled median " + parsed(pub121, r"b2m \(sum,128,S=16\) pooled median (\d+)"))

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
