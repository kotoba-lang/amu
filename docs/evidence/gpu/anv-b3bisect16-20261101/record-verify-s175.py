#!/usr/bin/env python3
# JUN-59 session 175 -- RECORD VERIFICATION for the SIXTEENTH CUT
# record (record.txt, sessions 169-174): the MEASUREMENT + ANALYSIS
# + LANDING halves of the clean-bisection cut at the floor midpoint
# (345, 1354) n=254,801 under the frozen
# anv-b3bisect16prereg-20261101/protocol.txt.
#
# Pure stdlib. No clock, no RNG, no network, no hardware, no subprocess.
# Every value computed here from arithmetic or committed bytes; QUOTE-ONLY.
# Verifies, fail-closed, every byte-level claim record.txt quotes from the
# committed captures of sessions 169-174 (the s168 record-verify precedent:
# run TWICE, byte-identical). This is NOT a measurement: NO hardware, NO
# builds, NO compiles, NO queue, NO claim. The sixteenth-cut letters this
# record quotes are MEASURED QUANTITIES computed at s173 from the s169-s171
# hardware runs; this script only re-reads their committed bytes.

import gzip
import hashlib
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))   # .../anv-b3bisect16-20261101
GP = os.path.dirname(BASE)                          # .../docs/evidence/gpu
PRE = os.path.join(GP, "anv-b3bisect16prereg-20261101")
P158 = os.path.join(GP, "anv-b3bisect15-20261101", "publication-s158.txt")
CASES157 = os.path.join(GP, "anv-b3bisect15-20261101", "cases-s157-a.txt")
PIN88 = os.path.join(GP, "anv-b3w6tailrep-20261030")
PIN117 = os.path.join(GP, "anv-b3w7ledgerappend-20261031")
ADR = os.path.normpath(os.path.join(GP, "..", "..", "adr",
                                    "0355-gpu-vendor-target-dispatch.md"))

PUB_SHA = "c9aab750fd20120b3abe8db6e9cac554b6c8ea0fbb1b37d9169d1539e4ff7687"
PY_SHA = "525f55a87294479314e78e654edc66659d4b1e40ff0c965bbebd56fb0e3da987"
AGG = "f8c08e16dabd4c1d6256bf8779c616d0f2067126e568bdf1155bf0239f32e52c"

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
    # ---- 1. publication-s169.txt pin + the frozen letters -----------
    pub = rd(sub("publication-s169.txt"))
    want(len(pub) == 56352 and sha(pub) == PUB_SHA,
         "publication-s169.txt 56,352 bytes sha256 c9aab750... (s173 pin)")
    ptxt = pub.decode("utf-8", "replace")
    want("5. VERDICT SUMMARY: C1 (b); C2 (c) at fm (254,801); W1 (d)." in ptxt,
         "publication VERDICT SUMMARY line C1 (b); C2 (c) at fm (254,801); W1 (d)")
    want("CUT VERDICT: INVALID; NOTHING MOVES." in ptxt,
         "publication CUT VERDICT: INVALID; NOTHING MOVES")
    want("The committed bracket stays EXACTLY (254,557, 255,045]." in ptxt,
         "publication: the committed bracket stays EXACTLY (254,557, 255,045]")
    want("committed floor band 31..32 at B=2): False" in ptxt,
         "C1: c2 pooled median vs the committed floor band 31..32 -> False")
    want("committed 32915 (session 4 pooled median): True (-0.29%)" in ptxt,
         "C1: c8 within +/-5% of committed 32,915 -> True (-0.29%)")
    want("VERDICT: branch (b) replication discrepancy" in ptxt,
         "C1 VERDICT: branch (b) replication discrepancy (W1 (d) fires)")
    want("control arms free of VERIFY mismatches (frozen INVALIDATION criterion): True"
         in ptxt,
         "C1: control arms free of VERIFY mismatches -> True")
    want("(c) CLASS-UNRESOLVED" in ptxt, "C2 (c) CLASS-UNRESOLVED quote present")
    want("pooled-48 class: CAPTURED" in ptxt, "C2: pooled-48 class CAPTURED")
    want("pooled-48 binding min(m-h): 1002.7437" in ptxt,
         "C2: pooled-48 binding min(m-h) 1,002.7437")
    m = parsed(ptxt, r"block classes: \[([^\]]*)\]",
               "C2 block-classes list (16 blocks)")
    if m:
        cls = re.findall(r"'([A-Z/-]+)'", m.group(1))
        want(len(cls) == 16 and cls.count("CAPTURED") == 10
             and cls.count("INTERMEDIATE/MIXED") == 3
             and cls.count("IN-BAND-UNDECIDED") == 3,
             "C2 block classes 10x CAPTURED + 3x INTERMEDIATE/MIXED + 3x IN-BAND-UNDECIDED")
    want("1004.8961 / 1006.7909" in ptxt and "997.0538 / 997.0538" in ptxt,
         "C2 block binding min(m-h) span 997.0538..1006.7909 quoted")
    want("(d) INVALID (C1 (b) or the frozen INVALIDATION criterion" in ptxt,
         "W1 (d) INVALID quote present")
    want("fm: runs with 18-cell min >= 1,000 (COMPUTED here, descriptive): 34/48"
         in ptxt, "W2: fm 34/48 runs at per-run 18-cell min >= 1,000")
    want("fm: runs with 18-cell min in 981..1,015 (COMPUTED here, descriptive): 48/48"
         in ptxt, "W2: fm 48/48 runs in the 981..1,015 band")
    want("1005.8172..1008.7909" in ptxt,
         "W3: parsed publication-s158.txt block min(m-h) 1005.8172..1008.7909")
    want("matches NO committed byte" in ptxt,
         "W3: the frozen prose lower bound matches NO committed byte (named)")
    want("spread 194948.5 = 62.9% of min; k=48" in ptxt,
         "X1: fm host_ns per-run median spread 62.9% of min (k=48)")
    want("VERIFY mismatch total over all runs: 0" in ptxt,
         "integrity: VERIFY mismatch total over all runs: 0")

    # ---- 2. the analysis byte-identity + the named draft defects ----
    ident = rd(sub("analysis-s169-identity.txt")).decode("utf-8", "replace")
    want(PUB_SHA in ident and "56,352 bytes both runs" in ident,
         "analysis-s169-identity.txt: publication pin + 56,352 bytes both runs")
    want(PY_SHA in ident, "analysis-s169-identity.txt: analysis-s169.py pin")
    want(sha(rd(sub("analysis-s169.py"))) == PY_SHA,
         "analysis-s169.py sha256 525f55a8... == the identity pin")
    want("MID-ONLY NARROWING CLAIM: W1 (a) did NOT fire" in ident,
         "identity: W1 (a) did NOT fire -> MID-ONLY NARROWING CLAIM stays SUSPENDED")
    want(len(rd(sub("analysis-s169-run1.txt"))) == 0
         and len(rd(sub("analysis-s169-run2.txt"))) == 0
         and len(rd(sub("analysis-s169-run1.err"))) == 0
         and len(rd(sub("analysis-s169-run2.err"))) == 0,
         "analysis runs 1/2 stdout+stderr all 0 bytes")
    d1e = rd(sub("analysis-s169-draft1-run1.err")).decode("utf-8", "replace")
    d2e = rd(sub("analysis-s169-draft2-run1.err")).decode("utf-8", "replace")
    want("IndexError: no such group" in d1e,
         "analysis draft-1 defect named in its .err (no capture group, fail-closed)")
    want("WANT SOURCE NOT PARSED: pub158 bracket state" in d2e,
         "analysis draft-2 defect named in its .err (comma-free bracket regex)")
    want(len(rd(sub("analysis-s169-draft1-run1.txt"))) == 0
         and len(rd(sub("analysis-s169-draft2-run1.txt"))) == 0,
         "analysis draft .txt 0 bytes (no publication written by either draft)")

    # ---- 3. the run-log custody chain (s169-s171 captures) ----------
    hd = rd(sub("host-digests-s169.txt")).decode("utf-8", "replace")
    want(AGG in hd, "host-digests: canonical aggregate f8c08e16... quoted")
    want("host == local -> MATCH (108/108 logs byte-identical)" in hd,
         "host-digests: host == local MATCH 108/108")
    want("checked=54 mismatch=0" in hd, "host-digests: gzip fidelity checked=54 mismatch=0")
    want("776748956 total" in hd and "raw stdout bytes 776,748,956 (54 logs); 54 stderr logs 0 bytes (all)"
         in hd, "host-digests: raw byte census 776,748,956 / 0 (54+54 logs)")
    want("missing=0" in hd, "host-digests: host-side name-existence check missing=0")
    for kat, lbl in [
        ("8c8ef86446f8f11280c4ac020d2ff7aa1cb25c76af307777e90178c9e156b69c",
         "KAT-1 s147 plain aggregate 8c8ef864... EXACTLY"),
        ("7c52eb638a995cb5a92db0e17ac95607dc800aa93768fa4c473dea2d54df33af",
         "negative control 7c52eb63... (sha256sum-line, equals no aggregate)"),
        ("97bd3d33db2f49346a370bfd5269d8fd17da8d223d3915fc32fc7e9025116c8e",
         "KAT-2 s158 committed-form aggregate 97bd3d33... EXACTLY"),
    ]:
        want(kat in hd, f"host-digests: {lbl}")
    hr = rd(sub("host-runs-s169.txt")).decode("utf-8", "replace")
    want(len(re.findall(r"run_rc=0", hr)) == 54,
         "host-runs: 54 per-run lines run_rc=0 (the full frozen-order window)")
    want(AGG in hr and "missing=0" in hr,
         "host-runs: driver aggregate tail f8c08e16... + missing=0")
    raw = rd(sub("raw-digests-s169.txt")).decode("utf-8", "replace")
    rows = re.findall(
        r"^([0-9a-f]{64})  (run-\S+\.txt)  bytes=(\d+)$", raw, re.M)
    want(len(rows) == 54, "raw-digests: 54 pre-compression digest rows")
    # spot-check the committed gzip -n form against its raw-digest row
    spot = [r for r in rows if r[1] in ("run-c2-r01.txt", "run-fm-r48.txt")]
    want(len(spot) == 2, "raw-digests: both spot-check rows present")
    for digest, name, nbytes in spot:
        with gzip.open(sub(name + ".gz"), "rb") as f:
            data = f.read()
        want(sha(data) == digest and len(data) == int(nbytes),
             f"committed form {name}.gz decompresses to its raw digest + bytes={nbytes}")
    want(len([f for f in os.listdir(BASE) if re.fullmatch(r"run-.*\.txt\.gz", f)]) == 54
         and len([f for f in os.listdir(BASE) if re.fullmatch(r"run-.*\.stderr\.txt", f)]) == 54,
         "committed form: 54 run .txt.gz + 54 plain 0-byte .stderr.txt")

    # ---- 4. derivation + build census -------------------------------
    dc = rd(sub("derivation-census-s169.txt")).decode("utf-8", "replace")
    want("3+48+3 = 54 -> ok" in dc, "derivation: run-count self-check 3+48+3 = 54")
    want("(1,000,003*345)//1354 = 254,801 == n" in dc
         and "gcd(345,1354) = 1 -> ok" in dc,
         "derivation: knob arithmetic (1,000,003*345)//1354 = 254,801, gcd = 1")
    want((1000003 * 345) // 1354 == 254801, "re-derived: (1,000,003*345)//1354 = 254,801")
    a, b = 345, 1354
    while b:
        a, b = b, a % b
    want(a == 1, "re-derived: gcd(345,1354) = 1")
    for digest, fname, lbl in [
        ("c2704aaad6bfeeae1f4f9cfa916d0160efb03926892237554c7dffc8386e84e0",
         "gpu-subgroup-reduce-anv-ndiv-rounds6400.c.txt", "instrument c2704aaa..."),
        ("eefba52e7be052d66eb7baae700b3f7583db7306f1a7d6b5a2201b862ac595a4",
         "expected-corpus.sha256", "expected-corpus eefba52e..."),
        ("abd09ab174fa97e95201cf0296b7ab6a4613534964e97e857513886c84074981",
         "cases-s169-a.txt", "manifest cases-s169-a.txt abd09ab1..."),
    ]:
        want(sha(rd(sub(fname))) == digest, f"local re-derived {lbl}")
        want(digest in dc, f"derivation-census quotes {lbl}")
    want("873025d650afae2329ab2c05c2048931a5263976b9bfb585d3665b7018c32200" in dc,
         "derivation-census quotes the cell-block pin 873025d6...")
    cells169 = b"".join(l + b"\n" for l in rd(sub("cases-s169-a.txt")).split(b"\n")
                        if l and not l.startswith(b"#"))
    want(sha(cells169) == "873025d650afae2329ab2c05c2048931a5263976b9bfb585d3665b7018c32200",
         "re-derived: the 24 cell lines' block sha256 == 873025d6... (s25/s27 pin)")
    want(cells169 == b"".join(l + b"\n" for l in rd(CASES157).split(b"\n")
                              if l and not l.startswith(b"#")),
         "the s169 cell lines are byte-equal to the s157 a-set cell block")
    bc = rd(sub("build-census-s169.txt")).decode("utf-8", "replace")
    for digest, lbl in [
        ("b791b71a73671f2ed0882d1376d13294ece40b64320db828c94985959e734c48",
         "binary pin anv-bb-c2 b791b71a..."),
        ("8c568de523418f0042b30023eb01d6a083c9e1819f0c1dfa7f7edde15479c1a8",
         "binary pin anv-bb-fm 8c568de5... (the ONE NEW KNOB TRIPLE)"),
        ("2f25d678d6958b6fbbe0125492eab1b0e8fb67412d1cb379d7c6401c35617831",
         "binary pin anv-bb-c8 2f25d678..."),
    ]:
        want(digest in bc and digest in rd(sub("host-digests-s169.txt")).decode("utf-8", "replace"),
             f"build census + host re-census quote {lbl}")
    want("build_rcs=['0', '0', '0'] (3/3 rc 0)" in bc, "build census: 3/3 builds rc 0")

    # ---- 5. the s174 standing-gate captures vs the pins -------------
    c = rd(sub("gate-s174-classify.txt"))
    want(c == rd(pin88("gate-s88-classify.txt")) and len(c) == 17925,
         "gate-s174-classify.txt 17,925 bytes == the s88 pin")
    want(len(rd(sub("gate-s174-classify.err"))) == 0, "gate-s174-classify.err 0 bytes")
    r1 = rd(sub("gate-s174-run1.txt"))
    r2 = rd(sub("gate-s174-run2.txt"))
    want(r1 == r2 == rd(pin88("gate-s88-run1.txt")) == rd(pin88("gate-s88-run2.txt"))
         and len(r1) == 919,
         "gate-s174-run1 == run2 == both s88 pins (919 bytes)")
    want(len(rd(sub("gate-s174-run1.err"))) == 0 and len(rd(sub("gate-s174-run2.err"))) == 0,
         "gate-s174-run .err 0 bytes both runs")
    fo = rd(sub("gate-s174-full.out"))
    fe = rd(sub("gate-s174-full.err"))
    want(fo == rd(pin88("gate-s88-full.out")) and len(fo) == 0,
         "gate-s174-full.out 0 bytes == pin")
    want(fe == rd(pin88("gate-s88-full.err")) and len(fe) == 879,
         "gate-s174-full.err 879 bytes == pin")
    want(b"Could not find namespace: kotoba.form" in fe,
         "full suite RED AT BASE kotoba.form (ADR-0362) -- NO green full suite claimed")
    bt = rd(sub("bar-s174-selftest.txt"))
    want(bt == rd(pin88("bar-s88-selftest.txt")) and len(bt) == 3590,
         "bar-s174-selftest.txt 3,590 bytes == the s88 pin")
    want(len(rd(sub("bar-s174-selftest.err"))) == 0, "bar-s174-selftest.err 0 bytes")
    b1 = rd(sub("bar-s174-eval-run1.txt"))
    b2 = rd(sub("bar-s174-eval-run2.txt"))
    want(b1 == b2 == rd(pin117("bar-s117-eval-post-run1.txt")) and len(b1) == 1006,
         "bar-s174-eval run1 == run2 == the s117 post-append pin (1,006 bytes)")
    want(len(rd(sub("bar-s174-eval-run1.err"))) == 0 and len(rd(sub("bar-s174-eval-run2.err"))) == 0,
         "bar-s174-eval .err 0 bytes both runs")
    want(len(rd(sub("gate-s174-nosh.txt"))) == 0 and len(rd(sub("gate-s174-nosh.err"))) == 0,
         "gate-s174-nosh captures 0 bytes (find '*.sh' -> 0)")
    want(len(rd(sub("gate-s174-ledger-head.out"))) == 0
         and len(rd(sub("gate-s174-ledger-head.err"))) == 0,
         "gate-s174-ledger-head captures 0 bytes (ledger == HEAD, no append)")

    # ---- 6. the committed bracket + the cut-point arithmetic --------
    pub158 = rd(P158)
    p158txt = pub158.decode("utf-8", "replace")
    m = parsed(p158txt, r"Bracket state: NARROWED -- \(([\d,]+), ([\d,]+)\]",
               "publication-s158.txt bracket (comma-tolerant)")
    if m:
        lo, hi = int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
        want((lo, hi) == (254557, 255045), "committed bracket EXACTLY (254,557, 255,045]")
        want((lo + hi) // 2 == 254801,
             "floor midpoint (254,557+255,045)//2 = 254,801 == the cut point")

    # ---- 7. the ADR-0355 dated note (sessions 169-174) --------------
    adr = rd(ADR).decode("utf-8", "replace")
    want("2026-11-01 (sessions 169-174, JUN-59 -- THE SIXTEENTH CUT" in adr,
         "ADR-0355 carries the sessions 169-174 dated note marker")
    want("docs/evidence/gpu/anv-b3bisect16-20261101/." in adr,
         "ADR-0355 dated note cites this evidence directory")

    # ---- 8. evidence hygiene: no POSIX .sh under docs/evidence/gpu --
    shs = []
    for root, _dirs, files in os.walk(GP):
        for name in files:
            if name.endswith(".sh"):
                shs.append(os.path.join(root, name))
    want(len(shs) == 0, "find docs/evidence/gpu -name '*.sh' -> 0 files")

    # ---- 9. the pre-push blocker-first capture ----------------------
    pl = rd(sub("prlist-s175-prepush.json")).decode("utf-8", "replace")
    prs = json.loads(pl)
    want(isinstance(prs, list), "prlist-s175-prepush.json parses as a PR list")
    if isinstance(prs, list):
        hermes = [p for p in prs if str(p.get("headRefName", "")).startswith("hermes/")]
        chain = [p for p in prs if str(p.get("headRefName", "")).startswith("bot/amu-gpu-chain")]
        want(len(hermes) == 0, "BLOCKER-FIRST: 0 open kotoba-lang/amu PRs with a hermes/ head")
        want(len(chain) == 1 and chain[0].get("headRefName") == "bot/amu-gpu-chain-20261028-4",
             "exactly ONE chain PR head (bot/amu-gpu-chain-20261028-4)")

    # ---- summary ---------------------------------------------------
    print(f"SUMMARY: {len(oks)} ok / {len(fails)} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
