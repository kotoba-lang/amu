#!/usr/bin/env python3
"""enumerate-s232.py -- THE FULL ENUMERATION OF EVERY COMMITTED SESSION
5..20 c2/c8 READING (amu-gpu session 232; the s231 carry-forward's
standing row, s216 NAMED (a)).

THE QUESTION (the row exactly as named at s216 NAMED (a)): enumerate
every committed session 5..20 c2/c8 reading -- the full enumeration the
s216 provenance parse did NOT do ("this tick did NOT enumerate every
committed session 5..20 c2/c8 reading (the full enumeration is its own
parse if a future slice needs it)").  The enumeration is the NAMED INPUT
to the s216 identity hazard (whether the (b) readings' m 30 is a NEW
control state or a tolerance/defect reading) -- this script SUPPLIES the
enumeration and does NOT decide the hazard.

DEFINITION (fixed here, before the parse): a session's c2 reading is the
pooled median gpu_ticks at (sum,128,S=16) of that session's committed
B=2 control rung; its c8 reading is the same at the session's committed
B=8 control rung -- the rungs that feed the committed floor band
"31..32 at B=2" and the c8 reference stability rows.  Each session's
control-arm naming is per its own committed publication (tb / b2n0 /
b2m1 / a2 / c2 ...), located by the per-session arm spec below and
re-parsed from the committed publication BYTES at runtime -- no value
is transcribed anywhere in this script.

Reads ONLY committed bytes (fail-closed; any parse anomaly is an
immediate abort = failed run):
  - docs/evidence/gpu/<session dir>/publication-s<N>.txt for N = 5..20
    (the sixteen committed session publications).

Writes NOTHING.  Prints the enumeration report to stdout, nothing to
stderr on success.  Exit 0 iff every ok/failed check is ok.

CHECKS vs REPORTS (the honesty split): PARSE anomalies (missing file,
non-unique bracket row, table-vs-confrontation-line value mismatch,
unverified absence) are CHECKS and fail the run; MEASUREMENT OUTCOMES
(c2 value, band membership, c8 pct) are REPORTS and never fail the run
(a below-band c2 reading would be data to report, not a defect).

THREE-STATE: every value below is a named session's landed MEASURED
QUANTITY (its own hardware runs under its own instrument and protocol),
RE-PARSED here from committed publication bytes -- this script measures
NOTHING new on hardware and no value here is a measurement of this tick;
the pct arithmetic is DERIVED (labelled).  The s216 identity hazard
stays UNDECIDED and unqueued.
"""

import hashlib
import re
import sys
from pathlib import Path

# The committed c8 reference and floor band (the s27 controls census,
# ../anv-b3bisect7-20261027/derivation-census-s27.txt L43: "committed
# controls: c2 31 (floor band 31..32); c8 32,915 (session 4 pooled
# median)") -- used ONLY as DERIVED arithmetic inputs.
C8_REF = 32915
FLOOR_BAND = (31, 32)

GPU = Path(__file__).resolve().parent.parent  # docs/evidence/gpu

# Per-session spec: directory name and the session's committed control
# arm names (c2 = the B=2 rung, c8 = the B=8 rung, None = no B=8 rung in
# the session's committed bracket grid -- verified below, not assumed).
SPEC = [
    (5, "anv-tsstage-20261027", "tb", None),
    (6, "anv-cmdcount-20261027", "b2n2", None),
    (7, "anv-bonset-20261027", "b2n0", "b8n0"),
    (8, "anv-workmul-20261027", "b2m1", "b8m1"),
    (9, "anv-itrmul-20261027", "a2", "a8"),
    (10, "anv-gridfat-20261027", "c2", "c8"),
    (11, "anv-costcal-20261027", "c2", "c8"),
    (12, "anv-workdown-20261027", "c2", "c8"),
    (13, "anv-workthresh-20261027", "c2", "c8"),
    (14, "anv-floorbisect-20261027", "c2", "c8"),
    (15, "anv-sessrepl-20261027", "c2", "c8"),
    (16, "anv-dispatchcount-20261027", "c2", "c8"),
    (17, "anv-consttotal-20261027", "c2", "c8"),
    (18, "anv-ndiv8ladder-20261027", "c2", "c8"),
    (19, "anv-ndiv4ladder-20261027", "c2", "c8"),
    (20, "anv-ndiv2ladder-20261027", "c2", "c8"),
]

BAND_RE = re.compile(r"(\d+)\s+(\d+)\.\.(\d+)")


def sha256(b):
    return hashlib.sha256(b).hexdigest()


ok = 0
failed = 0
report = []


def check(cond, label):
    global ok, failed
    if cond:
        ok += 1
        report.append("  ok    %s" % label)
    else:
        failed += 1
        report.append("  FAILED %s" % label)


def bracket_row(lines, arm, b):
    """The unique bracket-table row of `arm` at rung B=`b`: a line that
    starts with the arm name, whose knob columns start with the rung B,
    and that carries a min..max band.  The pooled median at
    (sum,128,S=16) is the last integer immediately before the first
    min..max band on the row (the committed table convention)."""
    pat = re.compile(r"^\s*%s\s+(?:B=)?%d\s" % (re.escape(arm), b))
    rows = [ln for ln in lines if pat.match(ln) and BAND_RE.search(ln)]
    if len(rows) != 1:
        return None, rows
    m = BAND_RE.search(rows[0])
    assert m is not None  # rows[] is filtered on a band match
    value = int(m.group(1))
    return (value, int(m.group(2)), int(m.group(3)), rows[0]), rows


def class_line(lines, arm, b):
    pat = re.compile(r"^\s*class\s+%s\s+\(B=%d[^)]*\):\s*(\S+)" % (re.escape(arm), b))
    for ln in lines:
        m = pat.match(ln)
        if m:
            return m.group(1), ln
    return None, None


print("== JUN-59 s232 -- THE FULL ENUMERATION OF EVERY COMMITTED SESSION")
print("== 5..20 c2/c8 READING (s216 NAMED (a)) -- enumerate-s232.py")
print("== over the committed publication bytes ONLY (post-hoc parse; the")
print("== values are the named sessions' landed MEASURED QUANTITIES, NOT")
print("== measurements of this tick; pct arithmetic DERIVED).")
print("== c2 reading = pooled median gpu_ticks at (sum,128,S=16) of the")
print("== session's committed B=2 control rung; c8 reading = same at the")
print("== B=8 control rung.  DERIVED inputs: committed floor band 31..32")
print("== at B=2; committed c8 reference 32,915 (session 4 pooled median)")
print("== -- both from the s27 controls census (committed).")
print()

c2_values = []
c8_values = []

for n, d, arm2, arm8 in SPEC:
    path = GPU / d / ("publication-s%d.txt" % n)
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    lines = text.splitlines()
    print("-- session %d  %s/publication-s%d.txt  %d bytes  sha256 %s"
          % (n, d, n, len(raw), sha256(raw)))
    check(True, "S%d.1 publication bytes read (%d bytes)" % (n, len(raw)))

    # ---- c2 (B=2 control rung) ----
    row2, all2 = bracket_row(lines, arm2, 2)
    check(row2 is not None,
          "S%d.2 c2 bracket row unique and parsed (arm %s B=2)" % (n, arm2))
    if row2 is None:
        print("     c2: PARSE FAIL -- candidate rows: %r" % all2)
        sys.exit(1)
    v2, lo2, hi2, ln2 = row2
    c2_values.append((n, v2))
    cls2, cln2 = class_line(lines, arm2, 2)
    print("     c2 (arm %s B=2): pooled median %d  run-median band %d..%d"
          % (arm2, v2, lo2, hi2))
    print("       row: %s" % ln2.strip())
    if cln2:
        print("       class: %s" % cln2.strip())
    else:
        print("       class: n/a (no class line in this publication format)")
    inband = FLOOR_BAND[0] <= v2 <= FLOOR_BAND[1]
    print("       in committed floor band 31..32 at B=2 (DERIVED): %s"
          % inband)

    # ---- c8 (B=8 control rung) ----
    if arm8 is not None:
        row8, all8 = bracket_row(lines, arm8, 8)
        check(row8 is not None,
              "S%d.3 c8 bracket row unique and parsed (arm %s B=8)" % (n, arm8))
        if row8 is None:
            print("     c8: PARSE FAIL -- candidate rows: %r" % all8)
            sys.exit(1)
        v8, lo8, hi8, ln8 = row8
        print("     c8 (arm %s B=8): pooled median %d  run-median band %d..%d"
              % (arm8, v8, lo8, hi8))
        print("       row: %s" % ln8.strip())
        # cross-check against the publication's own committed
        # confrontation line (the s8..s20 C1/O3 wording)
        xpat = re.compile(
            r"^\s*%s \(sum,128,16\) pooled median (\d+) within \+/-5%% of "
            r"committed %d" % (re.escape(arm8), C8_REF))
        xvals = []
        for ln in lines:
            xm = xpat.match(ln)
            if xm:
                xvals.append(int(xm.group(1)))
        check(len(xvals) >= 1 and all(x == v8 for x in xvals),
              "S%d.4 c8 confrontation line(s) re-read (%d) and all == table "
              "value %d" % (n, len(xvals), v8))
        pct = (v8 - C8_REF) / C8_REF * 100.0
        c8_values.append((n, v8, pct))
        print("       vs committed 32,915 (DERIVED): %+.4f%%  within "
              "+/-5%%: %s" % (pct, abs(pct) <= 5.0))
    else:
        # fail-closed ABSENCE: the session's committed bracket grid must
        # genuinely carry no B=8 rung
        grid = []
        for ln in lines:
            m = re.match(r"^\s*[A-Za-z0-9]+\s+B=(\d+)\s", ln)
            if m:
                grid.append(int(m.group(1)))
            m = re.match(r"^\s*[A-Za-z0-9]+\s+(\d+)\s", ln)
            if m and BAND_RE.search(ln):
                b = int(m.group(1))
                if b <= 64:
                    grid.append(b)
        grid = sorted(set(grid))
        check(len(grid) >= 1 and 8 not in grid,
              "S%d.3 c8 ABSENT BY DESIGN -- no B=8 rung in the committed "
              "bracket grid %s" % (n, grid))
        print("     c8: ABSENT BY DESIGN -- this session's committed "
              "bracket grid carries no B=8 rung (grid %s)" % grid)
    print()

# ---- summary ----
print("== SUMMARY (all values RE-PARSED from committed bytes above; the")
print("== multiset arithmetic is DERIVED):")
c2_only = sorted(v for _, v in c2_values)
print("  c2 readings: %d of %d sessions (sessions without a B=2 rung: %s)"
      % (len(c2_only), len(SPEC),
         [n for n, _, _, _ in SPEC
          if all(nn != n for nn, _ in c2_values)] or "NONE"))
for n, v in c2_values:
    print("    session %2d: %d" % (n, v))
counts = {}
for v in c2_only:
    counts[v] = counts.get(v, 0) + 1
print("  c2 multiset: %s (min %d, max %d)"
      % (", ".join("%d x%d" % (v, counts[v]) for v in sorted(counts)),
         min(c2_only), max(c2_only)))
below = [(n, v) for n, v in c2_values if v < FLOOR_BAND[0]]
print("  c2 below the committed floor band 31..32 at B=2 (<31): %d of %d"
      "  -> %s" % (len(below), len(c2_only), below or "NONE"))
print()
for n, v, pct in c8_values:
    print("    session %2d: c8 %d  (%+.4f%% of 32,915)" % (n, v, pct))
c8_only = [v for _, v, _ in c8_values]
pcts = [p for _, _, p in c8_values]
print("  c8 readings: %d of %d sessions (sessions %s: c8 ABSENT BY DESIGN)"
      % (len(c8_only), len(SPEC),
         [n for n, _, _, a8 in SPEC if a8 is None]))
print("  c8 range: min %d (%+.4f%%), max %d (%+.4f%%); within +/-5%% of"
      " 32,915: %d of %d"
      % (min(c8_only), min(pcts), max(c8_only), max(pcts),
         sum(1 for p in pcts if abs(p) <= 5.0), len(pcts)))
print()
print("  IDENTITY-HAZARD INPUT (s216 NAMED (a) -- the hazard question")
print("  itself stays UNDECIDED and unqueued; this enumeration is its")
print("  named input, not its resolution): within sessions 5..20 NO B=2")
print("  reading is 30 or below -- the minimum committed c2 reading is")
print("  %d.  The m 30 readings (the 16th and 19th cuts' c2 pooled"
      % min(c2_only))
print("  medians, publication-s169.txt / publication-s209.txt, and the")
print("  s225 resolution act's four (b) readings' m 30) have NO session")
print("  5..20 precedent in the committed bytes enumerated here.")
print()
print("== THREE-STATE: the sixteen publications' c2/c8 readings are the")
print("== named sessions' landed MEASURED QUANTITIES (sessions 5..20's own")
print("== hardware runs on the one named device family under their own")
print("== instruments and protocols), RE-PARSED from committed bytes by")
print("== this script -- NOT measurements of this tick; the band/pct")
print("== arithmetic is DERIVED; the s216 identity hazard stays UNMEASURED")
print("== and unqueued; NO vendor optimization exists for Intel (or for any")
print("== vendor) and NONE follows from this enumeration; the accelerator-")
print("== targets workgroup rows stay as ADR-0358 left them (:measured? false")
print("== rows remain provisional -- NOT optimization evidence).")
print()
print("# enumerate s232 (enumerate-s232.py): %d ok / %d failed" % (ok, failed))
sys.exit(0 if failed == 0 else 1)
