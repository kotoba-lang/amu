#!/usr/bin/env python3
# JUN-59 session 184 -- POST-HOC RECORD VERIFICATION for the
# SEVENTEENTH CUT PRE-REGISTRATION record (record.txt, sessions
# 176-183): the row-decision + reconnaissance + census + design +
# design-verify + protocol freeze + standing gates + landing of
# the clean-bisection cut at the virgin quarter point (313, 1229)
# n=254,679, PRE-REGISTERED AND FROZEN -- NOT MEASURED.
#
# Pure stdlib. No clock, no RNG, no network, no hardware, no
# subprocess. Every value computed here from arithmetic or
# committed bytes; QUOTE-ONLY. Verifies, fail-closed, every
# byte-level and arithmetic claim record.txt makes over the
# committed captures of sessions 176-183 (the s168/s175
# record-verify precedent: run TWICE, byte-identical). This is
# NOT a measurement: NO hardware, NO builds, NO compiles, NO
# queue, NO claim. NO seventeenth-cut quantity is computed here
# -- every 17th-cut quantity stays UNMEASURED (the measurement
# half is NOT queued).

import hashlib
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))   # .../anv-b3bisect17prereg-20261101
GP = os.path.dirname(BASE)                          # .../docs/evidence/gpu
ROOT = os.path.normpath(os.path.join(BASE, "..", "..", "..", ".."))  # chain root
P16 = os.path.join(GP, "anv-b3bisect16-20261101")
PIN88 = os.path.join(GP, "anv-b3w6tailrep-20261030")
PIN117 = os.path.join(GP, "anv-b3w7ledgerappend-20261031")
ADR = os.path.normpath(os.path.join(GP, "..", "..", "adr",
                                    "0355-gpu-vendor-target-dispatch.md"))

# pins tool-verified at s184 from committed bytes / session identities
KNOB_PY_SHA = "786b37460b216c1d1c0f940abc9cadc69f659d08871449ed3ca43c62041d5ba7"
KNOB_RUN_SHA = "b3fdb1f27cecbf18f1249948364e061b8d24c1773f730a00a808cb8ce24d627e"
DV_PY_SHA = "e40fdb0c8001b21262a11d254b47c9195ade2e96355c705611b4c155084ec80b"
DV_RUN_SHA = "bd469b93a3c4cee411e60164c9ff242e20cd2d7cd601c9cc1d2870a90c50b9c5"
PROTO_SHA = "ad8ace961cf6eca9f1e68752b9fba89861806a8161fbaec5448c7654a74cf6fb"
PUB169_SHA = "c9aab750fd20120b3abe8db6e9cac554b6c8ea0fbb1b37d9169d1539e4ff7687"
INSTR_SHA = "c2704aaad6bfeeae1f4f9cfa916d0160efb03926892237554c7dffc8386e84e0"
RECORD_SHA = "2e5f18eda9d628678c389f4e7de583ac9d90137e3979942d68cff6268c4ce9cf"

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


def norm(b):
    return re.sub(r"\s+", " ", b.decode("utf-8", "replace"))


def main():
    # ---- 0. the record's own pin + structure ------------------------
    rec = rd(sub("record.txt"))
    want(len(rec) == 11924 and sha(rec) == RECORD_SHA,
         "record.txt 11,924 bytes sha256 2e5f18ed... (the s183 landing pin)")
    rn = norm(rec)
    for q, lbl in [
        ("== THE CLEAN-BISECTION CUT AT THE VIRGIN QUARTER POINT "
         "(313, 1229) n=254,679, PRE-REGISTERED AND FROZEN -- NOT MEASURED ==",
         "record header: the cut at the virgin quarter point, FROZEN -- NOT MEASURED"),
        ("1. THE CENSUS (sessions 177-178", "record section 1 heading (census)"),
        ("2. THE DESIGN DECISIONS AND THE FREEZE (sessions 179-182)",
         "record section 2 heading (design + freeze)"),
        ("3. STANDING GATES (a)-(f) run LIVE at s183",
         "record section 3 heading (standing gates)"),
        ("4. THE ENVIRONMENT INCIDENT AT s183 (NAMED, NOT HIDDEN)",
         "record section 4 heading (environment incident)"),
        ("5. NAMED, NOT HIDDEN", "record section 5 heading"),
        ("6. THREE-STATE / RULE 4 / BAR", "record section 6 heading"),
        ("7. Carry-forward to s184", "record section 7 heading (carry-forward)"),
        ("(JUN-55, JUN-59; Linear tracking JUN-499)", "record footer cites JUN-55/JUN-59/JUN-499"),
    ]:
        want(q in rn, lbl)
    want("1. THE CENSUS (sessions 177-178" in rn,
         "record section 1 heading (census sessions 177-178) -- exact")

    # ---- 1. the census pair (s178) + the named draft defect ---------
    want(sha(rd(sub("knob-search-s177.py"))) == KNOB_PY_SHA,
         "knob-search-s177.py sha256 786b3746... == the s178 identity pin")
    k1 = rd(sub("knob-search-s177-run1.txt"))
    k2 = rd(sub("knob-search-s177-run2.txt"))
    want(k1 == k2 and len(k1) == 6823 and sha(k1) == KNOB_RUN_SHA,
         "knob-search-s177 run1 == run2 (6,823 bytes, sha256 b3fdb1f2...) both")
    want(len(rd(sub("knob-search-s177-run1.err"))) == 0
         and len(rd(sub("knob-search-s177-run2.err"))) == 0,
         "knob-search-s177 .err 0 bytes both runs")
    ident = rd(sub("knob-search-s177-identity.txt")).decode("utf-8", "replace")
    want(KNOB_RUN_SHA in ident and KNOB_PY_SHA in ident,
         "knob-search-s177-identity.txt quotes both pins (b3fdb1f2... / 786b3746...)")
    want("CENSUS COMPLETE: every asserted want parsed and matched; 0 mismatches."
         in rd(sub("knob-search-s177-run1.txt")).decode("utf-8", "replace"),
         "census completion line in run1.txt (record section 1 quote)")
    d1 = rd(sub("knob-search-s177-draft1-run1.txt"))
    d2 = rd(sub("knob-search-s177-draft1-run2.txt"))
    want(d1 == d2 and sha(d1).startswith("f52b6f92") and len(d1) == 3390,
         "named draft-1 pair stdout byte-identical (3,390 bytes, sha256 f52b6f92...)")
    e1 = rd(sub("knob-search-s177-draft1-run1.err"))
    e2 = rd(sub("knob-search-s177-draft1-run2.err"))
    want(e1 == e2 and len(e1) == 556 and sha(e1).startswith("3df11a96"),
         "named draft-1 pair .err byte-identical (556 bytes, sha256 3df11a96...)")
    want("not enough values to unpack (expected 4, got 3)" in e1.decode("utf-8", "replace"),
         "draft-1 defect named in its .err (4-tuple over 3-tuple, fail-closed)")

    # ---- 2. the census values (record section 1 quotes) -------------
    kt = k1.decode("utf-8", "replace")
    for q, lbl in [
        ("committed bracket (publication-s158.txt, parsed): (254557, 255045] "
         "n-units, width 488", "census: committed bracket (254,557, 255,045], width 488"),
        ("fm n=254801: pairs 31; smallest (345, 1354); in-box same-ratio "
         "doubles 7 -- s165 capture ((254801, 31, (345, 1354), 7)) -> MATCH",
         "census s165 re-derivation: fm 31 / (345, 1354) / 7 -> MATCH"),
        ("mid n=254882: pairs 35; smallest (248, 973); in-box same-ratio "
         "doubles 10 -- s165 capture ((254882, 35, (248, 973), 10)) -> MATCH",
         "census s165 re-derivation: mid 35 / (248, 973) / 10 -> MATCH"),
        ("C1: c2 pooled median m 30, deep-pooling class FLOOR "
         "(committed floor band 31..32 at B=2): False",
         "C1 (b) quote: c2 m 30 vs floor band 31..32 -> False"),
        ("c8 pooled median m 32820 within +/-5% of committed 32915 "
         "(session 4 pooled median): True (-0.29%)",
         "C1 (b) quote: c8 32,820 vs 32,915 -> True (-0.29%)"),
        ("C1 VERDICT: branch (b) replication discrepancy (W1 (d) INVALID "
         "fires); cause UNMEASURED.",
         "C1 VERDICT: branch (b) replication discrepancy, cause UNMEASURED"),
        ("C2 block classes (re-count COMPUTED here): 10x CAPTURED + 3x "
         "INTERMEDIATE/MIXED + 3x IN-BAND-UNDECIDED; pooled-48 class CAPTURED",
         "C2 block classes 10/3/3 re-count + pooled-48 CAPTURED"),
        ("C2 block binding min(m-h): 997.0538..1006.7909 (16 values), "
         "pooled-48 1002.7437",
         "C2 block binding min(m-h) 997.0538..1006.7909, pooled 1,002.7437"),
        ("C2 VERDICT: (c) CLASS-UNRESOLVED (mixed block classes / any "
         "IN-BAND-UNDECIDED unit / pooled arm differs -- FAILS); L9 binds at "
         "254,801.",
         "C2 VERDICT (c) CLASS-UNRESOLVED; L9 binds at 254,801"),
        ("CUT VERDICT: INVALID; NOTHING MOVES. The committed bracket stays "
         "EXACTLY (254557, 255045].",
         "cut verdict: INVALID; NOTHING MOVES; bracket stays EXACTLY"),
        ("W3 CROSS-CHECK: the 16th cut's W3 reading of the disputed record "
         "(5 row quotes + lo pooled-12 + mid pooled-48 + s147 pooled-48) "
         "MATCHES the primary-source parse at every value -- the disputed "
         "record is UNCONTESTED between the sources.",
         "disputed record UNCONTESTED between its sources"),
        ("measured wander band (spec, parsed): block-unit 981..1015; "
         "per-run unit 974..1023 (descriptive unit)",
         "confrontation-spec wander band 981..1015 / 974..1023 parsed"),
        ("16/16 of this cut's fm block binding min(m-h) values land inside "
         "the block-unit wander band 981..1015",
         "16/16 fm block binding min(m-h) inside the wander band (descriptive)"),
        ("floor midpoint re-derivation: (254557+255045)//2 = 254801 "
         "(RE-DERIVED here; == the 16th cut's fm point n=254801: True)",
         "floor midpoint re-derivation == the 16th cut's fm point"),
        ("quarter q=1 n=254679: pairs 31; smallest (313, 1229); in-box "
         "same-ratio doubles 8; committed-source occurrences "
         "{'publication-s139.txt': 0, 'publication-s147.txt': 0, "
         "'publication-s158.txt': 0, 'publication-s169.txt': 0, "
         "'knob-search-s164-run1.txt': 0}",
         "q1 n=254,679 (31 / (313, 1229) / 8), 0 occurrences everywhere"),
        ("quarter q=3 n=254923: pairs 34; smallest (246, 965); in-box "
         "same-ratio doubles 10",
         "q3 n=254,923 (34 / (246, 965) / 10)"),
        ("q-fraction (254882 - 254557)/488 = 0.665984",
         "mid NOT on the quarter grid (q-fraction 0.665984)"),
    ]:
        want(q in kt, lbl)
    want("'the point is VIRGIN -- this cut's content is the FIRST content at it' PARSED"
         in kt, "the VIRGIN/FIRST-content point quote parsed from publication-s169")

    # ---- 3. the design-verify pair (s181) ---------------------------
    want(sha(rd(sub("design-verify-s179.py"))) == DV_PY_SHA,
         "design-verify-s179.py sha256 e40fdb0c... == the s181 identity pin")
    v1 = rd(sub("design-verify-s179-run1.txt"))
    v2 = rd(sub("design-verify-s179-run2.txt"))
    want(v1 == v2 and len(v1) == 7070 and sha(v1) == DV_RUN_SHA,
         "design-verify-s179 run1 == run2 (7,070 bytes, sha256 bd469b93...) both")
    want(len(rd(sub("design-verify-s179-run1.err"))) == 0
         and len(rd(sub("design-verify-s179-run2.err"))) == 0,
         "design-verify-s179 .err 0 bytes both runs")
    want("DESIGN-VERIFY S179 SUMMARY: 70 ok / 0 failed" in v1.decode("utf-8", "replace"),
         "design-verify verdict: 70 ok / 0 failed")
    vident = rd(sub("design-verify-s179-identity.txt")).decode("utf-8", "replace")
    want(DV_RUN_SHA in vident and DV_PY_SHA in vident,
         "design-verify-s179-identity.txt quotes both pins (bd469b93... / e40fdb0c...)")
    want("CHECK SET (70 wants, every one matched):" in vident
         and "Arithmetic re-derivations (12):" in vident,
         "identity records the 70-want check set + 12 arithmetic re-derivations")
    want("55 line-pinned quotes MATCH at their exact committed lines, 12 "
         "arithmetic re-derivations MATCH" in rn,
         "record section 2 quotes the 55 line-pinned + 12 arithmetic MATCH claims")

    # ---- 4. the freeze (s182) ---------------------------------------
    proto = rd(sub("protocol.txt"))
    want(len(proto) == 19974 and sha(proto) == PROTO_SHA,
         "protocol.txt 19,974 bytes sha256 ad8ace96... == the s182 freeze pin")
    fr = norm(rd(sub("freeze-record-s179.txt")))
    for q, lbl in [
        ("protocol.txt pin: 19,974 bytes, sha256 "
         "ad8ace961cf6eca9f1e68752b9fba89861806a8161fbaec5448c7654a74cf6fb",
         "freeze-record quotes the full protocol pin"),
        ("freeze stamp 2026-11-01T16:20:57Z", "freeze-record quotes the freeze stamp"),
        ("run-log count in this directory at freeze 0",
         "freeze-record: no run log of this cut existed at freeze"),
        ("(i) binds literally at 254,801", "freeze-record names the arm-(b) "
         "re-read hazard edge (i) at 254,801"),
        ("h_c = 3.6420 * MAD_c / sqrt(N)", "frozen statistic formula quoted"),
        ("R = 6,400 ADOPTED UNCHANGED, NOT re-derived",
         "R = 6,400 adopted unchanged"),
        ("ARM TABLE c2/q1/c8 = 54 processes (3+48+3 self-check ok)",
         "arm table 54 processes (3+48+3)"),
    ]:
        want(q in fr, lbl)
    want(sha(rd(os.path.join(P16, "gpu-subgroup-reduce-anv-ndiv-rounds6400.c.txt")))
         == INSTR_SHA,
         "ROUNDS6400 instrument re-hash c2704aaa... == the adopted source pin")

    # ---- 5. the s183 standing gates vs the s88/s117 pins ------------
    c = rd(sub("gate-s183-classify.txt"))
    want(c == rd(pin88("gate-s88-classify.txt")) and len(c) == 17925,
         "gate-s183-classify.txt 17,925 bytes == the s88 pin")
    want(len(rd(sub("gate-s183-classify.err"))) == 0, "gate-s183-classify.err 0 bytes")
    r1 = rd(sub("gate-s183-run1.txt"))
    r2 = rd(sub("gate-s183-run2.txt"))
    want(r1 == r2 == rd(pin88("gate-s88-run1.txt")) == rd(pin88("gate-s88-run2.txt"))
         and len(r1) == 919,
         "gate-s183-run1 == run2 == both s88 pins (919 bytes)")
    want("Ran 123 tests containing 12162 assertions. 0 failures, 0 errors."
         in norm(r1),
         "scoped GPU gate GREEN 123 tests / 12162 assertions / 0 failures / 0 errors")
    want(len(rd(sub("gate-s183-run1.err"))) == 0 and len(rd(sub("gate-s183-run2.err"))) == 0,
         "gate-s183-run .err 0 bytes both runs")
    fo = rd(sub("gate-s183-full.out"))
    fe = rd(sub("gate-s183-full.err"))
    want(fo == rd(pin88("gate-s88-full.out")) and len(fo) == 0,
         "gate-s183-full.out 0 bytes == pin")
    want(fe == rd(pin88("gate-s88-full.err")) and len(fe) == 879,
         "gate-s183-full.err 879 bytes == pin")
    want(b"Could not find namespace: kotoba.form" in fe,
         "full suite RED AT BASE kotoba.form (ADR-0362) -- NO green full suite claimed")
    bt = rd(sub("bar-s183-selftest.txt"))
    want(bt == rd(pin88("bar-s88-selftest.txt")) and len(bt) == 3590,
         "bar-s183-selftest.txt 3,590 bytes == the s88 pin")
    want(len(rd(sub("bar-s183-selftest.err"))) == 0, "bar-s183-selftest.err 0 bytes")
    b1 = rd(sub("bar-s183-eval-run1.txt"))
    b2 = rd(sub("bar-s183-eval-run2.txt"))
    want(b1 == b2 == rd(pin117("bar-s117-eval-post-run1.txt")) and len(b1) == 1006,
         "bar-s183-eval run1 == run2 == the s117 post-append pin (1,006 bytes)")
    want(len(rd(sub("bar-s183-eval-run1.err"))) == 0
         and len(rd(sub("bar-s183-eval-run2.err"))) == 0,
         "bar-s183-eval .err 0 bytes both runs")
    want(b"SETTLED INTERMEDIATE/MIXED" in b1,
         "bar verdict SETTLED INTERMEDIATE/MIXED (unchanged)")

    # ---- 6. the environment incident captures (record section 4) ----
    g1 = rd(sub("gate-s183-envfail-run1.err"))
    g2 = rd(sub("gate-s183-envfail-run2.err"))
    want(g1 == g2 and len(g1) == 877,
         "envfail pair .err byte-identical (877 bytes each)")
    want(b"Could not find namespace: kotoba.hir" in g1,
         "envfail .err names the failure (kotoba.hir not found)")
    want(len(rd(sub("gate-s183-envfail-run1.txt"))) == 0
         and len(rd(sub("gate-s183-envfail-run2.txt"))) == 0,
         "envfail .txt 0 bytes both (no test ran before the failure)")

    # ---- 7. arithmetic re-derivations (the record's + design-verify's
    #        12, recomputed here) -------------------------------------
    want((1000003 * 313) // 1229 == 254679,
         "re-derived: (1,000,003*313)//1,229 = 254,679")
    a, b = 313, 1229
    while b:
        a, b = b, a % b
    want(a == 1, "re-derived: gcd(313, 1,229) = 1")
    want((254557 + 255045) // 2 == 254801,
         "re-derived: (254,557+255,045)//2 = 254,801")
    want(255045 - 254557 == 488, "re-derived: bracket width 488")
    want(254557 + 488 // 4 == 254679, "re-derived: q=1 grid 254,557+488//4 = 254,679")
    want(254557 + 3 * (488 // 4) == 254923,
         "re-derived: q=3 grid 254,557+3*(488//4) = 254,923")
    want(3 + 48 + 3 == 54, "re-derived: arm table 3+48+3 = 54 processes")
    want(10087909 - 10058172 == 29737,
         "re-derived: bis binding spread 1008.7909-1005.8172 = 2.9737")
    want(10067909 - 9970538 == 97371,
         "re-derived: fm binding spread 1006.7909-997.0538 = 9.7371")
    want(1015 - 981 == 34, "re-derived: wander band width 1,015-981 = 34")
    want(254801 - 254679 == 122, "re-derived: 254,801-254,679 = 122")
    want(255045 - 254923 == 122, "re-derived: 255,045-254,923 = 122")

    # ---- 8. record.txt narrative quotes (whitespace-normalized) -----
    for q, lbl in [
        ("No record-verify script is run at this landing (the s168/s175 "
         "record-verify precedent is NOT repeated this tick)",
         "record section 5: record-verify NOT run at the s183 landing"),
        ("A post-hoc record-verify over the committed captures remains "
         "available to a later session; it is standing, not queued.",
         "record section 5: the post-hoc record-verify row (this tick's row)"),
        ("every seventeenth-cut quantity -- every unit class, C2, W1, W2, "
         "W3, X1 -- is UNMEASURED",
         "record section 6: every 17th-cut quantity UNMEASURED"),
        ("workgroup rows stay exactly as ADR-0358 left them",
         "record section 6: workgroup rows as ADR-0358 left them"),
        ("RULE 4 unchanged: NOTHING MOVES", "record section 6: RULE 4 NOTHING MOVES"),
        ("54 fresh processes c2/q1/c8 = 3/48/3",
         "record section 7: the measurement half 3/48/3 = 54 processes"),
        ("NO queued row remains; s184 takes a row only per the recorded "
         "carry-forward precedent, else stands down.",
         "record section 7: s184 takes a row only per the carry-forward precedent"),
    ]:
        want(q in rn, lbl)

    # ---- 9. the ADR-0355 dated note ---------------------------------
    adr = norm(rd(ADR))
    want("2026-11-02 (sessions 176-183, JUN-59 -- THE SEVENTEENTH CUT" in adr,
         "ADR-0355 carries the sessions 176-183 dated note marker")
    want("docs/evidence/gpu/anv-b3bisect17prereg-20261101/." in adr,
         "ADR-0355 dated note cites this evidence directory")

    # ---- 10. evidence hygiene + deleted scratch runner ---------------
    shs = []
    for root, dirs, files in os.walk(GP):
        dirs.sort()
        for name in sorted(files):
            if name.endswith(".sh"):
                shs.append(os.path.join(root, name))
    want(len(shs) == 0, "find docs/evidence/gpu -name '*.sh' -> 0 files")
    want(not os.path.exists(os.path.join(ROOT, "scratch", "scoped-gpu-gate.cljk")),
         "scratch/scoped-gpu-gate.cljk deleted (created/run/DELETED at s183, never committed)")

    # ---- 11. the pre-push blocker-first capture ---------------------
    pl = rd(sub("prlist-s183-prepush.json")).decode("utf-8", "replace")
    prs = json.loads(pl)
    want(isinstance(prs, list) and len(prs) == 15,
         "prlist-s183-prepush.json: 15 open kotoba-lang/amu PRs")
    if isinstance(prs, list):
        hermes = [p for p in prs if str(p.get("headRefName", "")).startswith("hermes/")]
        chain = [p for p in prs if str(p.get("headRefName", "")).startswith("bot/amu-gpu-chain")]
        want(len(hermes) == 0,
             "BLOCKER-FIRST: 0 open kotoba-lang/amu PRs with a hermes/ head")
        want(len(chain) == 1
             and chain[0].get("headRefName") == "bot/amu-gpu-chain-20261028-4"
             and chain[0].get("number") == 1665,
             "exactly ONE chain PR head (bot/amu-gpu-chain-20261028-4, #1665)")

    # ---- summary ---------------------------------------------------
    print(f"RECORD-VERIFY S184 SUMMARY: {len(oks)} ok / {len(fails)} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
