#!/usr/bin/env python3
"""JUN-59 session 81 -- the DOUBLING LADDER (DL): the NEW named
rank-pair vocabulary / selection rule (the s63-retired rank-pair
program's only route back; the s80 carry-forward item (c)).

Deterministic enumerator + self-test for the frozen vocabulary of
vocabulary.txt in this directory. Pure Python (stdlib only), no
third-party imports, no randomness, no clock reads: the output is a
pure function of the frozen constants below.

THIS SCRIPT COMPUTES NO STATISTIC OF ANY RUN LOG. It names rank
pairs of the pooled-75 order statistics x_(1) <= ... <= x_(75) (the
frozen estimator unit F3 of settle-bar.txt) and checks the frozen
properties of those names. Every rank-pair quantity printed here is
a RANK (an integer position), never a measurement.

Usage:
  python3 rankpair-vocab-s81.py            # the enumeration
  python3 rankpair-vocab-s81.py --self-test
"""

import sys

# ---- frozen constants (vocabulary.txt, freeze stamp in that file) ----

N_POOLED = 75
CENTER = 38                       # deviation-center rank of the pooled 75
K_DOUBLING = [4, 8, 16, 32]       # the vocabulary's half-distances k
K_MAX = 37                        # 38 + k <= 75 requires k <= 37

# The complete inventory of pooled-75 rank pairs NAMED by committed
# records before this freeze, with citations.  Symmetric pairs carry
# their k (half-distance from CENTER); the four-rank-vocabulary pairs
# (s62/s63) are asymmetric and carry no k.
PRIOR_NAMED = [
    ((38, 38), 0, "center anchor k=0 (s58 freeze; degenerate)"),
    ((37, 39), 1, "INNER5 k=1 (s60/s61; halving ladder, RETIRED)"),
    ((36, 40), 2, "INNER4 k=2 (s59; s58 alt-k2 candidate; s61 re-read)"),
    ((35, 41), 3, "INNER3 k=3 (s58; halving ladder, RETIRED)"),
    ((33, 43), 5, "INNER2 k=5 (s56; halving ladder, RETIRED)"),
    ((28, 48), 10, "INNER k=10 (s53)"),
    ((19, 57), 19, "IQR k=19 (s47)"),
    ((9, 67), 29, "OUTER k=29 (s53)"),
    ((5, 71), 33, "OUTER2 k=33 (s56; halving ladder, RETIRED)"),
    ((3, 73), 35, "OUTER3 k=35 (s58; halving ladder, RETIRED)"),
    ((2, 74), 36, "OUTER4 k=36 (s59; halving ladder, RETIRED)"),
    ((1, 75), 37, "OUTER5 k=37 / outer5 (s60/s61; degenerate range)"),
    ((1, 57), None, "HX-L (s62; four-rank vocabulary, RETIRED)"),
    ((19, 75), None, "HX-R (s62; four-rank vocabulary, RETIRED)"),
    ((1, 19), None, "HS-SET-L (s63; four-rank vocabulary, RETIRED)"),
    ((57, 75), None, "HS-SET-R (s63; four-rank vocabulary, RETIRED)"),
]

NAMED_KS = sorted(k for _, k, _ in PRIOR_NAMED if k is not None)
POWERS_OF_TWO = [k for k in [1, 2, 4, 8, 16, 32, 64] if k <= K_MAX]
FREE_POWERS_OF_TWO = [k for k in POWERS_OF_TWO if k not in NAMED_KS]

# The spacing-repair property: each vocabulary k sits strictly
# between a consecutive named-k pair (frozen check targets).
GAP_TARGETS = {4: (3, 5), 8: (5, 10), 16: (10, 19), 32: (29, 33)}


def pair_for(k):
    return (CENTER - k, CENTER + k)


def pair_name(k):
    return "DL%d" % k


def enumerate_family(out):
    P = out
    P("JUN-59 session 81 -- rankpair-vocab-s81 -- the DOUBLING LADDER")
    P("(DL) named rank-pair vocabulary over the pooled-75 order")
    P("statistics x_(1)..x_(75) (center rank %d). NO statistic of any" % CENTER)
    P("run log is computed here: every quantity below is a RANK.")
    P("")
    P("name  ranks        k  span  midpoint  self-mirror  prior-overlap")
    for k in K_DOUBLING:
        a, b = pair_for(k)
        overlap = "none"
        for (pa, pb), _, _ in PRIOR_NAMED:
            if (pa, pb) == (a, b):
                overlap = "OVERLAP"
        P("%-5s (%2d, %2d)  %2d  %4d  %8d  %-11s  %s"
          % (pair_name(k), a, b, k, b - a, (a + b) // 2,
             "yes" if (2 * CENTER - b, 2 * CENTER - a) == (a, b) else "NO",
             overlap))
    P("")
    P("frozen rule: k in {%s} -- the powers of two <= %d whose k is"
      % (", ".join(str(k) for k in K_DOUBLING), K_MAX))
    P("unnamed in the prior inventory (powers of two <= %d: %s;"
      % (K_MAX, ", ".join(str(k) for k in POWERS_OF_TWO)))
    P("named: %s -> free: %s)."
      % (", ".join(str(k) for k in POWERS_OF_TWO if k in NAMED_KS),
         ", ".join(str(k) for k in FREE_POWERS_OF_TWO)))
    P("")
    P("prior named-k inventory (%d symmetric pairs + 4 asymmetric):"
      % len(NAMED_KS))
    P("  k = {%s}" % ", ".join(str(k) for k in NAMED_KS))
    P("spacing repair (each DL k strictly between consecutive named k):")
    for k in K_DOUBLING:
        lo, hi = GAP_TARGETS[k]
        P("  %s: %d < %d < %d -> %s"
          % (pair_name(k), lo, k, hi,
             "holds" if lo < k < hi else "BROKEN"))
    P("")
    P("estimators: NOT frozen here. The vocabulary names rank pairs")
    P("only; each future row freezes its own estimator, null and")
    P("thresholds in its own pre-registration (campaign convention).")


def self_test(out):
    n = [0]

    def check(cond):
        n[0] += 1
        if not cond:
            raise AssertionError("assertion %d failed" % n[0])

    check(N_POOLED == 75)
    check(CENTER == 38)
    check(K_MAX == 37)
    check(CENTER + K_MAX == N_POOLED)
    check(K_DOUBLING == [4, 8, 16, 32])
    check(len(K_DOUBLING) == 4)
    check(len(set(K_DOUBLING)) == 4)
    for k in K_DOUBLING:
        check(k > 0)
        check(k <= K_MAX)
        check(k & (k - 1) == 0)          # power of two
        check(k in FREE_POWERS_OF_TWO)   # free in the prior inventory
    check(POWERS_OF_TWO == [1, 2, 4, 8, 16, 32])
    check(FREE_POWERS_OF_TWO == [4, 8, 16, 32])
    check(FREE_POWERS_OF_TWO == K_DOUBLING)

    check(len(PRIOR_NAMED) == 16)
    check(len(NAMED_KS) == 12)
    check(NAMED_KS == [0, 1, 2, 3, 5, 10, 19, 29, 33, 35, 36, 37])
    for (a, b), k, _ in PRIOR_NAMED:
        check(1 <= a <= N_POOLED)
        check(1 <= b <= N_POOLED)
        if k is not None:
            check((a, b) == (CENTER - k, CENTER + k))
            check(a + b == 2 * CENTER)

    spans = []
    names = []
    for k in K_DOUBLING:
        a, b = pair_for(k)
        names.append(pair_name(k))
        spans.append(b - a)
        check(a == CENTER - k)
        check(b == CENTER + k)
        check(1 <= a < b <= N_POOLED)
        check(a + b == 2 * CENTER)                    # midpoint = center
        check((2 * CENTER - b, 2 * CENTER - a) == (a, b))  # self-mirror
        for (pa, pb), _, _ in PRIOR_NAMED:
            check((a, b) != (pa, pb))                # disjoint, per prior pair
        lo, hi = GAP_TARGETS[k]
        check(lo < k < hi)                           # spacing repair
    check(len(set(names)) == len(names))
    check(spans == [8, 16, 32, 64])
    check(K_DOUBLING[1] == 2 * K_DOUBLING[0])
    check(K_DOUBLING[2] == 2 * K_DOUBLING[1])
    check(K_DOUBLING[3] == 2 * K_DOUBLING[2])
    check(2 * K_DOUBLING[-1] > K_MAX)                # the ladder tops out

    out("TOTAL: %d assertions passed, 0 failed" % n[0])


def main(argv):
    if argv and argv[0] == "--self-test":
        self_test(lambda s: print(s))
    else:
        enumerate_family(lambda s: print(s))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
