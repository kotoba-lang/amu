#!/usr/bin/env python3
"""JUN-59 session 86 -- THE TAIL-SIDE HALF-PAIRS (TS-L/TS-R): the
SEPARATE tail-side/asymmetric named rank-pair vocabulary the s81 DL
freeze named as necessary (limitation 4(b): "probing which tail moves
needs a SEPARATE future vocabulary (asymmetric pairs)"), queued as
carry-forward (e) at s85.

Deterministic enumerator + self-test for the frozen vocabulary of
vocabulary.txt in this directory. Pure Python (stdlib only), no
third-party imports, no randomness, no clock reads: the output is a
pure function of the frozen constants below.

THIS SCRIPT COMPUTES NO STATISTIC OF ANY RUN LOG. It names rank
pairs of the pooled-75 order statistics x_(1) <= ... <= x_(75) (the
frozen estimator unit F3 of settle-bar.txt) and checks the frozen
properties of those names. Every rank-pair quantity printed here is
a RANK (an integer position), never a measurement. The one algebraic
closure identity is checked on a synthetic strictly increasing
sequence built in-script (a pure function), never on run data.

Usage:
  python3 tailpair-vocab-s86.py            # the enumeration
  python3 tailpair-vocab-s86.py --self-test
"""

import sys

# ---- frozen constants (vocabulary.txt, freeze stamp in that file) ----

N_POOLED = 75
CENTER = 38                       # deviation-center rank of the pooled 75
K_MAX = 37                        # 38 + k <= 75 requires k <= 37
# The family's k set is the DL vocabulary's k set, named ONLY from the
# s81 freeze (docs/evidence/gpu/anv-b3dladder-20261029/vocabulary.txt
# section 1): no new k selection happens in this vocabulary.
K_FAMILY = [4, 8, 16, 32]
NARROW_SPAN_BAND = (2, 10)        # the halving ladder's inner cluster
                                  # span band (s81 section 4(c), adopted)

# The complete inventory of pooled-75 rank pairs NAMED by committed
# records before this freeze, with citations: the 16 pairs of the s81
# inventory (its section 2) plus the 4 DL pairs s81 itself named.
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
    ((34, 42), 4, "DL4 k=4 (s81; the DOUBLING LADDER)"),
    ((30, 46), 8, "DL8 k=8 (s81)"),
    ((22, 54), 16, "DL16 k=16 (s81)"),
    ((6, 70), 32, "DL32 k=32 (s81)"),
]


def mirror(r):
    """The pooled-75 mirror map the whole campaign uses (r <-> 76-r)."""
    return (N_POOLED + 1) - r


def pair_left(k):
    """TS-Lk: the LEFT half-pair (x_(38-k), x_(38)); span k."""
    return (CENTER - k, CENTER)


def pair_right(k):
    """TS-Rk: the RIGHT half-pair (x_(38), x_(38+k)); span k."""
    return (CENTER, CENTER + k)


def name_left(k):
    return "TS-L%d" % k


def name_right(k):
    return "TS-R%d" % k


def pair_mirror(p):
    a, b = mirror(p[1]), mirror(p[0])
    return (a, b) if a < b else (b, a)


def enumerate_family(out):
    P = out
    P("JUN-59 session 86 -- tailpair-vocab-s86 -- the TAIL-SIDE")
    P("HALF-PAIRS (TS-L/TS-R) named rank-pair vocabulary over the")
    P("pooled-75 order statistics x_(1)..x_(75) (center rank %d)."
      % CENTER)
    P("NO statistic of any run log is computed here: every quantity")
    P("below is a RANK (or a rank arithmetic identity).")
    P("")
    P("name   ranks        k  span  midpoint  self-mirror  mirror-twin"
      "  prior-overlap")
    for k in K_FAMILY:
        for p, nm in ((pair_left(k), name_left(k)),
                      (pair_right(k), name_right(k))):
            a, b = p
            overlap = "none"
            for (pa, pb), _, _ in PRIOR_NAMED:
                if (pa, pb) == (a, b):
                    overlap = "OVERLAP"
            P("%-6s (%2d, %2d)  %2d  %4d  %8d  %-11s  %-10s  %s"
              % (nm, a, b, k, b - a, (a + b) // 2,
                 "yes" if pair_mirror(p) == p else "no",
                 (name_right(k) if p == pair_left(k) else name_left(k))
                 if pair_mirror(p) != p else "-",
                 overlap))
    P("")
    P("frozen rule: the k set {%s} is the DL vocabulary's k set"
      % ", ".join(str(k) for k in K_FAMILY))
    P("(s81 freeze, section 1) verbatim -- this vocabulary introduces")
    P("NO new k selection. Per k: TS-Lk = (x_(38-k), x_(38)) and")
    P("TS-Rk = (x_(38), x_(38+k)) -- the two HALF-PAIRS of DLk's pair")
    P("(x_(38-k), x_(38+k)), sharing the deviation-center x_(38).")
    P("")
    P("family properties (script-checked):")
    P("  span control: span(TS-Lk) = span(TS-Rk) = k -- a left/right")
    P("    contrast within a family holds the span FIXED (this answers")
    P("    the s81 section-4(a) tail-identity/span conflation objection")
    P("    by construction)")
    P("  mirror closure: mirror(TS-Lk) = TS-Rk under r <-> 76-r; no")
    P("    member is self-mirror; the set is closed under the mirror")
    P("  DL decomposition: TS-Lk U TS-Rk = DLk's pair ranks plus the")
    P("    shared center; HL_k + HR_k = D_k EXACTLY (algebraic identity")
    P("    on any increasing sequence)")
    P("  disjoint from all %d previously named pooled-75 rank pairs"
      % len(PRIOR_NAMED))
    P("  narrow-span band %d..%d (s81 section 4(c) adopted): k in"
      % NARROW_SPAN_BAND)
    P("    {4,8} sits IN the band -> uninformative about tail identity;")
    P("    informative families are k in {16,32}")
    P("")
    P("prior named-pair inventory (%d pairs: the s81 section-2"
      % len(PRIOR_NAMED))
    P("inventory's 16 + the 4 DL pairs s81 named):")
    for (a, b), k, cite in PRIOR_NAMED:
        P("  (%2d, %2d) %s" % (a, b, cite))
    P("")
    P("estimators: NOT frozen here. The vocabulary names rank pairs")
    P("only; each future row freezes its own estimator, null and")
    P("thresholds in its own pre-registration (the s81 rule 3(c),")
    P("adopted).")


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
    check(K_FAMILY == [4, 8, 16, 32])
    check(len(K_FAMILY) == 4)
    check(len(set(K_FAMILY)) == 4)
    check(NARROW_SPAN_BAND == (2, 10))

    # the k set is exactly the DL vocabulary's k set (s81 section 1)
    K_DL = [4, 8, 16, 32]
    check(K_FAMILY == K_DL)

    check(len(PRIOR_NAMED) == 20)
    prior_pairs = [(a, b) for (a, b), _, _ in PRIOR_NAMED]
    check(len(set(prior_pairs)) == 20)     # no duplicated prior pair
    check((34, 42) in prior_pairs and (30, 46) in prior_pairs)
    check((22, 54) in prior_pairs and (6, 70) in prior_pairs)

    # the synthetic strictly increasing sequence for the closure
    # identity: s[i] = 100 * i (pure function; no run data)
    seq = [100 * i for i in range(N_POOLED + 1)]  # 1-indexed use

    names = []
    for k in K_FAMILY:
        a, b = pair_left(k)
        check(k > 0)
        check(k <= K_MAX)
        check(1 <= a < b <= N_POOLED)
        check(b == CENTER)
        check(a == CENTER - k)
        check(b - a == k)                          # span control (left)
        check(pair_mirror(pair_left(k)) == pair_right(k))  # mirror twin
        check(pair_mirror(pair_left(k)) != pair_left(k))   # not self
        for (pa, pb), _, _ in PRIOR_NAMED:
            check((a, b) != (pa, pb))              # disjoint (left)
        names.append(name_left(k))

        a, b = pair_right(k)
        check(1 <= a < b <= N_POOLED)
        check(a == CENTER)
        check(b == CENTER + k)
        check(b - a == k)                          # span control (right)
        check(pair_mirror(pair_right(k)) == pair_left(k))  # mirror twin
        check(pair_mirror(pair_right(k)) != pair_right(k))  # not self
        for (pa, pb), _, _ in PRIOR_NAMED:
            check((a, b) != (pa, pb))              # disjoint (right)
        names.append(name_right(k))

        # mirror closure as a set, per family
        check(pair_mirror(pair_left(k)) in (pair_left(k), pair_right(k)))
        check(pair_mirror(pair_right(k)) in (pair_left(k), pair_right(k)))

        # DL decomposition + algebraic closure on the synthetic seq
        dl = (CENTER - k, CENTER + k)
        hl = seq[CENTER] - seq[CENTER - k]
        hr = seq[CENTER + k] - seq[CENTER]
        d = seq[CENTER + k] - seq[CENTER - k]
        check(hl + hr == d)                        # HL_k + HR_k = D_k
        check(hl > 0 and hr > 0 and d == hl + hr)
        check(dl in prior_pairs)                   # DLk is a prior pair
        check(pair_left(k)[1] == pair_right(k)[0] == CENTER)

        # the narrow-span band flags
        in_band = NARROW_SPAN_BAND[0] <= k <= NARROW_SPAN_BAND[1]
        check(in_band == (k in (4, 8)))

    check(len(set(names)) == 8)
    check(len(names) == 8)
    spans = [pair_left(k)[1] - pair_left(k)[0] for k in K_FAMILY]
    check(spans == [4, 8, 16, 32])
    check([pair_right(k)[1] - pair_right(k)[0] for k in K_FAMILY]
          == spans)                                # both sides same span
    check(K_FAMILY[1] == 2 * K_FAMILY[0])
    check(K_FAMILY[2] == 2 * K_FAMILY[1])
    check(K_FAMILY[3] == 2 * K_FAMILY[2])
    check(2 * K_FAMILY[-1] > K_MAX)                # the DL ladder tops
    # out (2*32 = 64 > 37) -- the reason K_FAMILY is exactly 4 k's
    # no k=1/2 half-pairs (their full pairs are the retired halving
    # ladder's inner cluster) and no k=64 (2*64 > 37)
    check(1 not in K_FAMILY and 2 not in K_FAMILY)
    check(64 not in K_FAMILY)
    for k in K_FAMILY:
        check(k in [kk for _, kk, _ in PRIOR_NAMED if kk is not None])

    out("TOTAL: %d assertions passed, 0 failed" % n[0])


def main(argv):
    if argv and argv[0] == "--self-test":
        self_test(lambda s: print(s))
    else:
        enumerate_family(lambda s: print(s))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
