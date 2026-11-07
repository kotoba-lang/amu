#!/usr/bin/env python3
"""JUN-59 session 166 -- the SIXTEENTH CUT pre-registration FREEZE
verification (the s165 carry-forward (b): design decisions + protocol
freeze + freeze-record).

Every number below is COMPUTED here from arithmetic or PARSED from
committed bytes -- nothing is transcribed from prose. Deterministic: no
clock, no RNG, no network, no hardware. Running it twice is
byte-identical (the run captures + cmp in this directory).

Purpose: verify, fail-closed, every NEW quantity the sixteenth-cut
protocol freezes -- the floor-midpoint cut point n=254,801 and its
knob pair (345, 1,354) (arithmetic + in-box enumeration re-derived
here INDEPENDENTLY of knob-search-s164.py's run captures, which are
cross-checked against their committed byte pin), the adopted R=6,400
derivation quotes (ADOPTION is a design decision -- this script
verifies the quoted committed evidence, it does NOT re-derive R), the
instrument variant source pin, the 14th cut's TOLERANCE-UNRESOLVED mid
content (arm (a) FIRST confrontation), and the 15th cut's landed
outcome (C2 (b) at bis, bracket (254,557, 255,045]).

QUOTE-ONLY / ARITHMETIC-ONLY: this script takes NO measurement of its
own; no cut is frozen or queued by it (the freeze is the protocol.txt
write, recorded in freeze-record-s166.txt); no bracket moves; no
class/verdict/claim is produced.
"""
import hashlib
import math
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
GPU = os.path.join(HERE, "..")

N_FULL = 1_000_003
BOX_WM = range(1, 2049)
BOX_NDIV = range(1, 8193)

# Frozen wants (pin-like): every parse must match or abort fail-closed.
WANT_BRACKET = (254557, 255045)
WANT_FLOOR_MID = 254801
WANT_FM_PAIR = (345, 1354)
WANT_FM = (31, (345, 1354), 7)          # pairs / smallest / in-box doubles
WANT_S27 = (35, (214, 845), 9)          # s27 census anchor (253,255)
WANT_MID = (35, (248, 973), 10)         # mid n=254,882
WANT_MID_KNOB = (248, 973, 254882)
WANT_KNOBSEARCH_SHA = ("49892344f6f8a1d4ac9a471a6984ee8bfcc4e28dc38bc6bfdb"
                       "5296990c53ebec")
WANT_VARIANT_SHA = ("c2704aaad6bfeeae1f4f9cfa916d0160efb03926892237554c7dff"
                    "c8386e84e0")
WANT_S147_MINS = [992, 1006, 996, 1000, 1002, 993, 1002, 991,
                  1006, 996, 997, 996, 1002, 999, 995, 991]
WANT_S147_POOL_MIN = 1005
WANT_S147_VERDICT = ("(c) TOLERANCE-UNRESOLVED: any in-band minimum or "
                     "mixed classes -- FAILS; L9 binds at mid at 16 blocks "
                     "under the tolerance rule too.")


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


def flat(text):
    return re.sub(r"\s+", " ", text)


def parsed(text, pattern, label):
    mm = re.search(pattern, flat(text))
    assert mm is not None, f"WANT NOT PARSED: {label}"
    return mm


def want(cond, label):
    assert cond, f"MISMATCH: {label}"
    print(f"  ok: {label}")


def main():
    print("== JUN-59 session 166 freeze verification (the SIXTEENTH CUT ==")
    print("== pre-registration: design decisions + protocol freeze --     ==")
    print("== every value computed here from arithmetic or committed     ==")
    print("== bytes; QUOTE-ONLY; NO measurement, NO queue, NO claim      ==")
    print()

    # ---- 0. the committed bracket + floor midpoint (arithmetic) ----
    P158 = open(os.path.join(GPU, "anv-b3bisect15-20261101",
                             "publication-s158.txt")).read()
    m = parsed(P158, r"Bracket state: NARROWED -- \(([\d,]+), ([\d,]+)\]",
               "publication-s158.txt bracket")
    lo_end = int(m.group(1).replace(",", ""))
    hi_end = int(m.group(2).replace(",", ""))
    want((lo_end, hi_end) == WANT_BRACKET,
         f"committed bracket ({lo_end}, {hi_end}] == want")
    floor_mid = (lo_end + hi_end) // 2
    exact = (lo_end + hi_end) / 2
    want(floor_mid == WANT_FLOOR_MID and float(exact).is_integer(),
         f"floor midpoint ({lo_end}+{hi_end})//2 = {floor_mid} exact "
         f"{float(exact)}")
    want(lo_end < floor_mid <= hi_end, f"{lo_end} < {floor_mid} <= {hi_end}")

    # ---- 1. the fm knob pair (NEW arithmetic this freeze) ----
    wm, ndiv = WANT_FM_PAIR
    n_pair = (N_FULL * wm) // ndiv
    want(n_pair == WANT_FLOOR_MID,
         f"(1,000,003*{wm})//{ndiv} = {n_pair} == {WANT_FLOOR_MID}")
    want(math.gcd(wm, ndiv) == 1, f"gcd({wm},{ndiv}) = 1")
    want(1 <= wm <= 2048 and 1 <= ndiv <= 8192,
         f"({wm},{ndiv}) in frozen box WM 1..2,048 x NDIV 1..8,192")

    # ---- 2. independent re-enumeration (the s27 self-validation
    #         anchor first, then fm and mid) ----
    p27 = pairs_for(253255)
    got27 = (len(p27), smallest(p27), len(doubles_in_box(p27)))
    want(got27 == WANT_S27, f"anchor (253,255): {got27} == s27 census")
    pfm = pairs_for(WANT_FLOOR_MID)
    gotfm = (len(pfm), smallest(pfm), len(doubles_in_box(pfm)))
    want(gotfm == WANT_FM,
         f"fm {WANT_FLOOR_MID}: {gotfm[0]} pairs / smallest "
         f"{gotfm[1]} / {gotfm[2]} in-box doubles")
    want(WANT_FM_PAIR in pfm, "fm measured-pair candidate in mapping set")
    pmid = pairs_for(254882)
    gotmid = (len(pmid), smallest(pmid), len(doubles_in_box(pmid)))
    want(gotmid == WANT_MID,
         f"mid 254,882: {gotmid[0]} pairs / smallest {gotmid[1]} / "
         f"{gotmid[2]} in-box doubles")
    want((N_FULL * 248) // 973 == 254882, "(1,000,003*248)//973 = 254,882")

    # ---- 3. knob-search-s164 captures: byte pin + run1 == run2 ----
    k1p = os.path.join(HERE, "knob-search-s164-run1.txt")
    k2p = os.path.join(HERE, "knob-search-s164-run2.txt")
    k1 = open(k1p, "rb").read()
    k2 = open(k2p, "rb").read()
    sha1 = hashlib.sha256(k1).hexdigest()
    want(k1 == k2, "knob-search run1 == run2 byte-identical")
    want(sha1 == WANT_KNOBSEARCH_SHA,
         f"knob-search sha256 {sha1[:16]}... == committed pin")
    k1t = k1.decode()
    m = parsed(k1t, r"pairs mapping to 254801 in-box: (\d+); smallest: "
                    r"\((\d+), (\d+)\)", "knob-search fm enumeration")
    want((int(m.group(1)), (int(m.group(2)), int(m.group(3))))
         == (WANT_FM[0], WANT_FM[1]), "knob-search fm count/smallest == want")
    m = parsed(k1t, r"same-ratio double is also in-box: (\d+) gcd\(254801",
               "knob-search fm doubles")
    want(int(m.group(1)) == WANT_FM[2], "knob-search fm doubles == want")
    want("committed content at n=254801: NONE" in flat(k1t),
         "knob-search: committed content at n=254,801 is NONE")

    # ---- 4. the 15th cut's landed outcome (arm (d)/W3 quotes) ----
    m = parsed(P158, r"block classes: \[('CAPTURED', ){15}'CAPTURED'\]; "
                     r"pooled-48 class: CAPTURED",
               "publication-s158.txt 16x CAPTURED bis classes")
    want(True, "15th cut bis: 16x CAPTURED blocks + pooled-48 CAPTURED")
    want("W1 (a)" in flat(P158), "15th cut W1 (a) landed (bracket NARROWED)")

    # ---- 5. the adopted R=6,400 derivation quotes (ADOPTION is a
    #         design decision; the quoted committed evidence is
    #         verified here) ----
    P154 = open(os.path.join(GPU, "anv-b3bisect15prereg-20261031",
                             "protocol.txt")).read()
    want("R=3,200 h_max 2.6949 > 2.0 FAILS" in flat(P154),
         "s153 derivation quote: R=3,200 h_max 2.6949 FAILS")
    want("R=6,400 h_max 1.9056 <= 2.0 PASSES" in flat(P154),
         "s153 derivation quote: R=6,400 h_max 1.9056 PASSES")

    # ---- 6. the instrument variant source pin ----
    vp = os.path.join(GPU, "anv-b3bisect15prereg-20261031",
                      "gpu-subgroup-reduce-anv-ndiv-rounds6400.c.txt")
    vsha = hashlib.sha256(open(vp, "rb").read()).hexdigest()
    want(vsha == WANT_VARIANT_SHA,
         f"ROUNDS6400 variant sha256 {vsha[:16]}... == frozen pin")

    # ---- 7. the 14th cut's TOLERANCE-UNRESOLVED mid content (arm
    #         (a) FIRST confrontation; parsed fail-closed) ----
    P147 = open(os.path.join(GPU, "anv-b3bisect14-20261031",
                             "publication-s147.txt")).read()
    m = parsed(P147, r"mid \(BATCH=3,WORK_MUL=(\d+),NDIV=(\d+)\) at "
                     r"n=([\d,]+)", "publication-s147.txt mid knob")
    want((int(m.group(1)), int(m.group(2)),
          int(m.group(3).replace(",", ""))) == WANT_MID_KNOB,
         "14th cut mid knob == (248, 973) n=254,882")
    m = parsed(P147, r"block 18-cell minima \(exact pooled medians\): "
                     r"([\d /]+?) pooled-48", "s147 block minima")
    mins = [int(x) for x in m.group(1).split("/") if x.strip()]
    want(mins == WANT_S147_MINS, f"14th cut 16 block minima {mins}")
    m = parsed(P147, r"pooled-48 18-cell min: (\d+)", "s147 pooled min")
    want(int(m.group(1)) == WANT_S147_POOL_MIN,
         f"14th cut pooled-48 min {m.group(1)}")
    want(WANT_S147_VERDICT in flat(P147),
         "14th cut verdict line (c) TOLERANCE-UNRESOLVED parsed verbatim")

    print()
    print("FREEZE WANTS OK: every sixteenth-cut freeze quantity verified")
    print("from arithmetic or committed bytes; NO measurement taken here;")
    print("NO cut frozen/queued/run by this script; the bracket stays")
    print("EXACTLY (254,557, 255,045]; the MID-ONLY NARROWING CLAIM stays")
    print("SUSPENDED; RULE 4 unchanged (NO vendor optimization for any")
    print("vendor).")


if __name__ == "__main__":
    main()
