#!/usr/bin/env python3
# JUN-59 session 168 -- RECORD VERIFICATION for the SIXTEENTH CUT
# PRE-REGISTRATION record (record.txt, sessions 164-168).
#
# Pure stdlib. No clock, no RNG, no network, no hardware, no subprocess.
# Every value computed here from arithmetic or committed bytes; QUOTE-ONLY.
# Verifies, fail-closed, every byte-level claim record.txt quotes from the
# committed captures of sessions 164-167 (the s166 freeze-verify precedent:
# run TWICE, byte-identical). This is NOT a measurement: NO hardware, NO
# builds, NO compiles, NO queue, NO claim -- every sixteenth-cut quantity
# stays UNMEASURED.

import hashlib
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))   # .../anv-b3bisect16prereg-20261101
GP = os.path.dirname(BASE)                          # .../docs/evidence/gpu
P158 = os.path.join(GP, "anv-b3bisect15-20261101", "publication-s158.txt")
PIN88 = os.path.join(GP, "anv-b3w6tailrep-20261030")
PIN117 = os.path.join(GP, "anv-b3w7ledgerappend-20261031")

oks = []
fails = []


def want(cond, label):
    if cond:
        oks.append(label)
        print(f"ok: {label}")
    else:
        fails.append(label)
        print(f"WANT NOT SATISFIED: {label}")


def parsed(text, pattern, label):
    m = re.search(pattern, text)
    if m is None:
        fails.append(label)
        print(f"WANT NOT PARSED: {label}")
        return None
    return m


def rd(path):
    with open(path, "rb") as f:
        return f.read()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def sub(path):
    return os.path.join(BASE, path)


def pin88(name):
    return os.path.join(PIN88, name)


def pin117(name):
    return os.path.join(PIN117, name)


def main():
    # ---- 1. the frozen protocol (s166) --------------------------------
    proto = rd(sub("protocol.txt"))
    want(len(proto) == 17002, "protocol.txt 17,002 bytes")
    want(sha(proto) == "a2da5d622e0ac0a0f4422d3c76704ad5ffd1911e82d5f14226fa6b17a8345c93",
         "protocol.txt sha256 a2da5d62... (s166 freeze pin)")
    want(b"2026-11-01T08:05:17Z" in proto, "protocol.txt carries the freeze stamp 2026-11-01T08:05:17Z")
    fr = rd(sub("freeze-record-s166.txt")).decode("utf-8", "replace")
    want("2026-11-01T08:05:17Z" in fr, "freeze-record-s166.txt carries the same freeze stamp")
    want("NO run log of this cut exists at freeze" in fr,
         "freeze-record-s166.txt states NO run log of the cut existed at freeze")

    # ---- 2. the s164/s165 reconnaissance + census ---------------------
    k1 = rd(sub("knob-search-s164-run1.txt"))
    k2 = rd(sub("knob-search-s164-run2.txt"))
    want(k1 == k2, "knob-search run1 == run2 (byte-identical)")
    want(sha(k1) == "49892344f6f8a1d4ac9a471a6984ee8bfcc4e28dc38bc6bfdb5296990c53ebec",
         "knob-search run sha256 49892344... (s165 committed pin)")
    want(len(rd(sub("knob-search-s164-run1.err"))) == 0 and len(rd(sub("knob-search-s164-run2.err"))) == 0,
         "knob-search .err 0 bytes both runs")
    ktxt = k1.decode("utf-8", "replace")
    want("committed content at n=254801: NONE" in ktxt,
         "knob-search census: the cut point n=254,801 is VIRGIN (committed content NONE)")
    fm_blk = re.search(r"FLOOR MIDPOINT CANDIDATE n=254801:(.*?)MID CANDIDATE", ktxt, re.S)
    want(fm_blk is not None and "pairs mapping to 254801 in-box: 31; smallest: (345, 1354)" in fm_blk.group(1)
         and "in-box pairs whose same-ratio double is also in-box: 7" in fm_blk.group(1),
         "knob-search census at 254,801: 31 in-box pairs / smallest (345, 1354) / 7 doubles")
    want("pairs mapping to 254882 in-box: 35; smallest: (248, 973)" in ktxt,
         "knob-search census at 254,882: 35 in-box pairs / smallest (248, 973)")
    want("pairs found: 35 (s27 committed: 35; state-s164: 35) -> MATCH" in ktxt,
         "knob-search self-validation vs the s27 census anchor -> MATCH")
    d1 = rd(sub("knob-search-s164-draft1-run1.txt"))
    d2 = rd(sub("knob-search-s164-draft1-run2.txt"))
    e1 = rd(sub("knob-search-s164-draft1-run1.err"))
    e2 = rd(sub("knob-search-s164-draft1-run2.err"))
    want(d1 == d2 and e1 == e2, "s165 draft-1 pair byte-identical to each other (runs AND .err)")
    want(b"WANT NOT PARSED: publication-s158.txt bracket" in e1,
         "s165 draft-1 defect named in its own .err (comma-free bracket regex, fail-closed)")

    # ---- 3. the s166 freeze verification ------------------------------
    f1 = rd(sub("freeze-verify-s166-run1.txt"))
    f2 = rd(sub("freeze-verify-s166-run2.txt"))
    want(f1 == f2, "freeze-verify run1 == run2 (byte-identical)")
    want(sha(f1) == "b34fd9d04cd51e8c7aaa3686504f22c28bc6f9dda3af71f5080868e2fb6185c3",
         "freeze-verify run sha256 b34fd9d0... (s166 committed pin)")
    want(len(rd(sub("freeze-verify-s166-run1.err"))) == 0 and len(rd(sub("freeze-verify-s166-run2.err"))) == 0,
         "freeze-verify .err 0 bytes both runs")
    ftxt = f1.decode("utf-8", "replace")
    want(len(re.findall(r"ok:", ftxt)) == 25, "freeze-verify 25 ok: wants")
    want(re.search(r"NOT PARSED|MISMATCH|Traceback", ftxt) is None,
         "freeze-verify carries no failure token")

    # ---- 4. the s167 standing-gate captures vs the pins ---------------
    c = rd(sub("gate-s167-classify.txt"))
    want(c == rd(pin88("gate-s88-classify.txt")) and len(c) == 17925,
         "gate-s167-classify.txt 17,925 bytes == the s88 pin")
    want(len(rd(sub("gate-s167-classify.err"))) == 0, "gate-s167-classify.err 0 bytes")
    r1 = rd(sub("gate-s167-run1.txt"))
    r2 = rd(sub("gate-s167-run2.txt"))
    want(r1 == r2 == rd(pin88("gate-s88-run1.txt")) == rd(pin88("gate-s88-run2.txt")) and len(r1) == 919,
         "gate-s167-run1 == run2 == both s88 pins (919 bytes)")
    want(len(rd(sub("gate-s167-run1.err"))) == 0 and len(rd(sub("gate-s167-run2.err"))) == 0,
         "gate-s167-run .err 0 bytes both runs")
    fo = rd(sub("gate-s167-full.out"))
    fe = rd(sub("gate-s167-full.err"))
    want(fo == rd(pin88("gate-s88-full.out")) and len(fo) == 0, "gate-s167-full.out 0 bytes == pin")
    want(fe == rd(pin88("gate-s88-full.err")) and len(fe) == 879, "gate-s167-full.err 879 bytes == pin")
    want(b"Could not find namespace: kotoba.form" in fe,
         "full suite RED AT BASE kotoba.form (ADR-0362) -- NO green full suite claimed")
    bt = rd(sub("bar-s167-selftest.txt"))
    want(bt == rd(pin88("bar-s88-selftest.txt")) and len(bt) == 3590,
         "bar-s167-selftest.txt 3,590 bytes == the s88 pin")
    want(len(rd(sub("bar-s167-selftest.err"))) == 0, "bar-s167-selftest.err 0 bytes")
    b1 = rd(sub("bar-s167-eval-run1.txt"))
    b2 = rd(sub("bar-s167-eval-run2.txt"))
    want(b1 == b2 == rd(pin117("bar-s117-eval-post-run1.txt")) and len(b1) == 1006,
         "bar-s167-eval run1 == run2 == the s117 post-append pin (1,006 bytes)")
    want(len(rd(sub("bar-s167-eval-run1.err"))) == 0 and len(rd(sub("bar-s167-eval-run2.err"))) == 0,
         "bar-s167-eval .err 0 bytes both runs")
    want(len(rd(sub("gate-s167-nosh.txt"))) == 0 and len(rd(sub("gate-s167-nosh.err"))) == 0,
         "gate-s167-nosh captures 0 bytes (find '*.sh' -> 0)")
    want(len(rd(sub("gate-s167-ledger-head.out"))) == 0 and len(rd(sub("gate-s167-ledger-head.err"))) == 0,
         "gate-s167-ledger-head captures 0 bytes (ledger == HEAD, no append)")

    # ---- 5. the committed bracket + the cut-point arithmetic ----------
    pub = rd(P158)
    want(len(pub) == 56588 and sha(pub) == "45538ad757bfa28821de2728000581897aaef8cc75f32ed656914509f400cd25",
         "publication-s158.txt 56,588 bytes sha256 45538ad7... (s162 committed pin)")
    ptxt = pub.decode("utf-8", "replace")
    # comma-tolerant endpoint parse: publication quotes endpoints with
    # thousands commas ("(254,557, 255,045]") -- the record-verify draft-1
    # repeated the s165 draft-1 comma-free defect here (named in record.txt).
    m = parsed(ptxt, r"Bracket state: NARROWED -- \(([\d,]+), ([\d,]+)\]",
               "publication-s158.txt bracket (comma-tolerant)")
    if m:
        lo, hi = int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
        want((lo, hi) == (254557, 255045), "committed bracket EXACTLY (254,557, 255,045]")
        want((lo + hi) // 2 == 254801, "floor midpoint (254,557+255,045)//2 = 254,801")
    want("THE BRACKET NARROWS TO (254,557, 255,045]" in ptxt, "publication W1 (a) verdict quote present")
    want((1000003 * 345) // 1354 == 254801, "fm knob arithmetic (1,000,003*345)//1354 = 254,801")
    g1, g2 = 254801, 1000003
    while g2:
        g1, g2 = g2, g1 % g2
    want(g1 == 1, "knob-search census quote re-derived: gcd(254,801, 1,000,003) = 1 -- floor approximation")
    a, b = 345, 1354
    while b:
        a, b = b, a % b
    want(a == 1, "fm knob gcd(345,1354) = 1")

    # ---- 6. evidence hygiene: no POSIX .sh under docs/evidence/gpu ----
    shs = []
    for root, _dirs, files in os.walk(GP):
        for name in files:
            if name.endswith(".sh"):
                shs.append(os.path.join(root, name))
    want(len(shs) == 0, "find docs/evidence/gpu -name '*.sh' -> 0 files")

    # ---- 7. the pre-push blocker-first capture ------------------------
    pl = rd(sub("prlist-s168-prepush.json")).decode("utf-8", "replace")
    import json
    prs = json.loads(pl)
    want(isinstance(prs, list), "prlist-s168-prepush.json parses as a PR list")
    if isinstance(prs, list):
        hermes = [p for p in prs if str(p.get("headRefName", "")).startswith("hermes/")]
        chain = [p for p in prs if str(p.get("headRefName", "")).startswith("bot/amu-gpu-chain")]
        want(len(hermes) == 0, "BLOCKER-FIRST: 0 open kotoba-lang/amu PRs with a hermes/ head")
        want(len(chain) == 1 and chain[0].get("headRefName") == "bot/amu-gpu-chain-20261028-4",
             "exactly ONE chain PR head (bot/amu-gpu-chain-20261028-4)")

    # ---- summary -----------------------------------------------------
    print(f"SUMMARY: {len(oks)} ok / {len(fails)} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
