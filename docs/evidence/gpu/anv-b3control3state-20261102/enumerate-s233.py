#!/usr/bin/env python3
"""enumerate-s233.py -- THE FULL ENUMERATION OF EVERY COMMITTED SESSION
c2/c8 READING, EXTENDED PAST SESSION 20 (amu-gpu session 233; the s232
carry-forward's row "the same enumeration extended past session 20
where the per-session censuses do not already carry it"; s216 NAMED
(a) input, the s232 enumeration's continuation).

THE ROW (exactly as carried at s232): the same enumeration, extended
past session 20.  This script re-runs the s232 enumeration (sessions
5..20, same parser convention, same definition) AND extends it over
every committed session publication past session 20 -- 64 further
publications -- so the hazard input is ONE report over the WHOLE
committed publication history.  The enumeration SUPPLIES the named
input to the s216 identity hazard (whether the (b) readings' m 30 is a
NEW control state or a tolerance/defect reading) and does NOT decide
the hazard.

DEFINITION (fixed here, before the parse; unchanged from s232): a
session's c2 reading is the pooled median gpu_ticks at (sum,128,S=16)
of that session's committed B=2 control rung; its c8 reading is the
same at the session's committed B=8 control rung.  The control rung is
the publication's own archived-environment-control arm (named per
session in the SPEC below: tb/b2n2/... in sessions 5..20, c2/c8 from
session 21 on).  Every value is RE-PARSED from the committed
publication BYTES at runtime -- no value is transcribed anywhere in
this script.

SOURCE FAMILIES (the per-session census forms the committed
publications actually carry; the family is fixed in the SPEC, the
parsing is fail-closed):

  BRACKET  -- the committed bracket-table convention (sessions 5..34,
              121, 125): the unique bracket row of the control arm at
              its rung B; the pooled median at (sum,128,S=16) is the
              last integer immediately before the first min..max band
              on the row (the committed table convention).  c8 absent
              = ABSENT BY DESIGN with a positive grid check (s5/s6).
  CLASSED  -- the C1 re-derivation form (sessions 35..51, 73..113):
              the publication carries 'c2 class: FLOOR (...)' (class
              ONLY, no reading value) and one c8 value line
              ('c8 (sum,128,S=16) pooled median N vs committed
              32915').  c2 READING NOT-CARRIED -- verified fail-closed
              (the class line is present, every single-value form is
              absent).  A 'c2 pooled medians min..max L..H (within
              band ...: bool)' AGGREGATE line (s107/s108) is NOT a
              reading at the named cell -- reported as an aggregate.

PROVENANCE (own reading vs anchor re-derivation; amended at s233
after the first full parse exposed the form -- the s232-era wording
called every CLASSED c8 line 'own', which the committed bytes
contradict): a CLASSED c8 line is an OWN READING only when the C1
re-derivation block sources THIS session's window (header bare /
'this window's logs' / 'from the s<n> ...' with n == the session,
and the preamble (text before section '1.') names no other session
-- 'session-N run logs' / 'measured in session N').  When the block
names ANOTHER session's window (the header 'at sN' / 'from the sN
...' with N != n -- s37/s40..s50/s77..s87/s107/s108 -- or the
preamble names N != n -- s35's 'the 84 committed session-34 run
logs ... every input quantity was measured in session 34'), the
line is an ANCHOR RE-DERIVATION: NOT a reading of that session (it
duplicates the anchor window's measured quantity), cross-checked
byte-equal to the anchor's own carried reading in pass 2 and
reported in its own census.  Provenance signals that contradict
each other fail the run.
  QUOTES   -- the multi-window quote form (sessions 52..63): the
              publication carries NO own control readings at all --
              every control line is a quote row of ANOTHER named
              session ('sNN: c2 class FLOOR (...); c8 ... pooled
              median M vs committed 32915').  Both readings
              NOT-CARRIED; each quote row is CROSS-CHECKED against the
              named session's own parsed reading.
  C1LINE   -- the one-line own C1 form (sessions 129..147):
              'c2 (sum,128,S=16) pooled median N, class FLOOR
              (...): True/False' plus the own c8 line.
  C1TWO    -- the deep-pooling two-line own C1 form (sessions
              158..229): 'c2 (sum,128,S=16) pooled median m N,
              deep-pooling' followed by 'class FLOOR (...):
              True/False', then the own c8 'm M' line.  A session may
              carry SEVERAL readings (the s225 resolution act carries
              four).  The one-line QUOTE form ('c2 ... m N,
              deep-pooling class FLOOR ...: True/False' on ONE line --
              a quoted earlier cut) is excluded by the two-line
              structure and REPORTED as a quote.

Reads ONLY committed bytes (fail-closed; any parse anomaly is an
immediate abort = failed run):
  - docs/evidence/gpu/<session dir>/publication-s<N>.txt for every
    committed session publication N >= 5 on disk (the SPEC's set must
    EQUAL the on-disk set -- a publication missing from the SPEC, or a
    SPEC entry missing on disk, fails the run).  publication-s4.txt
    (session 4, the c8 reference's source session) is below the
    universe floor N >= 5 and outside this named row; its pooled
    median stays the committed reference via the s27 controls census.

Writes NOTHING.  Prints the enumeration report to stdout, nothing to
stderr on success.  Exit 0 iff every ok/failed check is ok.

CHECKS vs REPORTS (the honesty split): PARSE anomalies (missing file,
SPEC/on-disk set mismatch, non-unique bracket row, table-vs-
confrontation-line value mismatch, value-form line present where the
family says NOT-CARRIED, quote row disagreeing with the named
session's own reading, unpaired C1TWO block) are CHECKS and fail the
run; MEASUREMENT OUTCOMES (c2 value, band membership, c8 pct, class
bool) are REPORTS and never fail the run (a below-band c2 reading
would be data to report, not a defect).

THREE-STATE: every value below is a named session's landed MEASURED
QUANTITY (its own hardware runs under its own instrument and
protocol), RE-PARSED here from committed publication bytes -- this
script measures NOTHING new on hardware and no value here is a
measurement of this tick; the pct arithmetic is DERIVED (labelled).
The s216 identity hazard stays UNDECIDED and unqueued.
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

# Per-session spec: (n, directory, family, c2 arm, c8 arm).  For
# BRACKET the arms are the bracket-table control rung names (c8 None =
# no B=8 rung in the session's committed bracket grid -- verified
# below, not assumed).  For the other families the arms are unused.
SPEC = [
    # -- the s232 enumeration (sessions 5..20), re-run here unchanged --
    (5, "anv-tsstage-20261027", "BRACKET", "tb", None),
    (6, "anv-cmdcount-20261027", "BRACKET", "b2n2", None),
    (7, "anv-bonset-20261027", "BRACKET", "b2n0", "b8n0"),
    (8, "anv-workmul-20261027", "BRACKET", "b2m1", "b8m1"),
    (9, "anv-itrmul-20261027", "BRACKET", "a2", "a8"),
    (10, "anv-gridfat-20261027", "BRACKET", "c2", "c8"),
    (11, "anv-costcal-20261027", "BRACKET", "c2", "c8"),
    (12, "anv-workdown-20261027", "BRACKET", "c2", "c8"),
    (13, "anv-workthresh-20261027", "BRACKET", "c2", "c8"),
    (14, "anv-floorbisect-20261027", "BRACKET", "c2", "c8"),
    (15, "anv-sessrepl-20261027", "BRACKET", "c2", "c8"),
    (16, "anv-dispatchcount-20261027", "BRACKET", "c2", "c8"),
    (17, "anv-consttotal-20261027", "BRACKET", "c2", "c8"),
    (18, "anv-ndiv8ladder-20261027", "BRACKET", "c2", "c8"),
    (19, "anv-ndiv4ladder-20261027", "BRACKET", "c2", "c8"),
    (20, "anv-ndiv2ladder-20261027", "BRACKET", "c2", "c8"),
    # -- the extension past session 20 --
    (21, "anv-b3bisect-20261027", "BRACKET", "c2", "c8"),
    (22, "anv-b3bisect2-20261027", "BRACKET", "c2", "c8"),
    (23, "anv-b3bisect3-20261027", "BRACKET", "c2", "c8"),
    (24, "anv-b3bisect4-20261027", "BRACKET", "c2", "c8"),
    (25, "anv-b3bisect5-20261027", "BRACKET", "c2", "c8"),
    (26, "anv-b3bisect6-20261027", "BRACKET", "c2", "c8"),
    (27, "anv-b3bisect7-20261027", "BRACKET", "c2", "c8"),
    (28, "anv-b3anchorrec-20261027", "BRACKET", "c2", "c8"),
    (29, "anv-b3blockvar-20261027", "BRACKET", "c2", "c8"),
    (31, "anv-b3xday-20261028", "BRACKET", "c2", "c8"),
    (32, "anv-b3x1rec-20261028", "BRACKET", "c2", "c8"),
    (33, "anv-b3repr-20261028", "BRACKET", "c2", "c8"),
    (34, "anv-b3minwander-20261028", "BRACKET", "c2", "c8"),
    (35, "anv-b3wandercov-20261028", "CLASSED", None, None),
    (36, "anv-b3commonmode-20261028", "CLASSED", None, None),
    (37, "anv-b3jointprobe-20261028", "CLASSED", None, None),
    (38, "anv-b3joint3-20261028", "CLASSED", None, None),
    (39, "anv-b3joint4-20261028", "CLASSED", None, None),
    (40, "anv-b3wandernoise-20261028", "CLASSED", None, None),
    (41, "anv-b3xwindt-20261028", "CLASSED", None, None),
    (42, "anv-b3levelshift-20261028", "CLASSED", None, None),
    (43, "anv-b3bodylevel-20261028", "CLASSED", None, None),
    (44, "anv-b3percellshift-20261028", "CLASSED", None, None),
    (45, "anv-b3percellwander-20261028", "CLASSED", None, None),
    (46, "anv-b3percellspread-20261028", "CLASSED", None, None),
    (47, "anv-b3percelliqr-20261028", "CLASSED", None, None),
    (48, "anv-b3percellmad-20261028", "CLASSED", None, None),
    (49, "anv-b3percellmadlevel-20261028", "CLASSED", None, None),
    (50, "anv-b3percelliqrlevel-20261028", "CLASSED", None, None),
    (51, "anv-b3levelrep-20261028", "CLASSED", None, None),
    (52, "anv-b3centerlevel-20261028", "QUOTES", None, None),
    (53, "anv-b3innerlevel-20261028", "QUOTES", None, None),
    (54, "anv-b3outerlevel-20261028", "QUOTES", None, None),
    (55, "anv-b3innerouterprofile-20261028", "QUOTES", None, None),
    (56, "anv-b3pair2profile-20261028", "QUOTES", None, None),
    (58, "anv-b3pair3profile-20261028", "QUOTES", None, None),
    (59, "anv-b3pair4profile-20261028", "QUOTES", None, None),
    (60, "anv-b3pair5profile-20261028", "QUOTES", None, None),
    (61, "anv-b3pair3k2reread-20261028", "QUOTES", None, None),
    (62, "anv-b3asymhinge-20261028", "QUOTES", None, None),
    (63, "anv-b3hingeside-20261028", "QUOTES", None, None),
    (73, "anv-b3w5xdayrep-20261029", "CLASSED", None, None),
    (77, "anv-b3w5hiwander-20261029", "CLASSED", None, None),
    (78, "anv-b3w5qpairevel-20261029", "CLASSED", None, None),
    (79, "anv-b3w5pair2profile-20261029", "CLASSED", None, None),
    (82, "anv-b3dlprofile-20261029", "CLASSED", None, None),
    (87, "anv-b3tailprofile-20261029", "CLASSED", None, None),
    (105, "anv-b3w6daybar-20261030", "CLASSED", None, None),
    (107, "anv-b3w6dlrep-20261030", "CLASSED", None, None),
    (108, "anv-b3w6tailrep-20261030", "CLASSED", None, None),
    (113, "anv-b3w7daybar-20261031", "CLASSED", None, None),
    (121, "anv-b3bisect8-20261031", "BRACKET", "c2", "c8"),
    (125, "anv-b3bisect9-20261031", "BRACKET", "c2", "c8"),
    (129, "anv-b3bisect10-20261031", "C1LINE", None, None),
    (132, "anv-b3bisect11-20261031", "C1LINE", None, None),
    (136, "anv-b3bisect12-20261031", "C1LINE", None, None),
    (139, "anv-b3bisect13-20261031", "C1LINE", None, None),
    (147, "anv-b3bisect14-20261031", "C1LINE", None, None),
    (158, "anv-b3bisect15-20261101", "C1TWO", None, None),
    (169, "anv-b3bisect16-20261101", "C1TWO", None, None),
    (185, "anv-b3bisect17-20261101", "C1TWO", None, None),
    (197, "anv-b3bisect18-20261101", "C1TWO", None, None),
    (209, "anv-b3bisect19-20261102", "C1TWO", None, None),
    (229, "anv-b3control3state-20261102", "C1TWO", None, None),
]

BAND_RE = re.compile(r"(\d+)\s+(\d+)\.\.(\d+)")

# -- own-value line forms (each family) --
RE_C2_QUOTE_M = re.compile(
    r"c2 \(sum,128,S=16\) pooled median m (\d+), deep-pooling class FLOOR")
RE_C2_OWN_M = re.compile(
    r"^\s*c2 \(sum,128,S=16\) pooled median m (\d+), deep-pooling\s*$")
RE_CLASS_LINE = re.compile(
    r"^\s*class FLOOR \(committed floor band 31\.\.32 at B=2\):"
    r" (True|False)\s*$", re.M)
RE_C8_M = re.compile(
    r"^\s*c8 \(sum,128,S=16\) pooled median m (\d+) within \+/-5% of"
    r" committed 32915 \(session 4 pooled median\): (True|False)")
RE_C2_ONELINE = re.compile(
    r"^\s*c2 \(sum,128,S=16\) pooled median (\d+), class FLOOR"
    r" \(committed floor band 31\.\.32 at B=2\): (True|False)\s*$")
RE_C8_ONELINE = re.compile(
    r"^\s*c8 \(sum,128,S=16\) pooled median (\d+) within \+/-5% of"
    r" committed 32915 \(session 4 pooled median\): (True|False)")
RE_C2_CLASS_ONLY = re.compile(
    r"^\s*c2 class: FLOOR \(FLOOR required; committed floor band"
    r" 31\.\.32\)\s*$", re.M)
RE_C8_VS = re.compile(
    r"^\s*c8 \(sum,128,S=16\) pooled median (\d+) vs committed 32915"
    r" \(([\d.]+)% delta; \+/-5% required\)\s*$")
RE_QUOTE_ROW = re.compile(
    r"^\s*s(\d+): c2 class FLOOR \(FLOOR required; committed floor band"
    r" 31\.\.32\); c8 \(sum,128,S=16\) pooled median (\d+) vs committed"
    r" 32915")
# -- absence probes (any hit where the family says NOT-CARRIED; the
# anchored ones carry re.M because they run over whole-file text) --
RE_ANY_C2_M = re.compile(r"c2 \(sum,128,S=16\) pooled median")
RE_ANY_C2_BARE = re.compile(r"c2 pooled median")
RE_ANY_C2_DEEP_M = re.compile(r"c2 \(sum,128,S=16\) pooled median m \d+")
RE_ANY_C8_OWN_VS = re.compile(
    r"^\s*c8 \(sum,128,S=16\) pooled median", re.M)
# -- the CLASSED aggregate form (NOT a reading) and provenance signals --
RE_AGG_MINMAX = re.compile(
    r"^\s*c2 pooled medians min\.\.max (\d+)\.\.(\d+) \(within band"
    r" (\d+)\.\.(\d+): (True|False)\)\s*$")
RE_HDR_SRC = re.compile(
    r"C1 RE-DERIVATION (?:at s(\d+)|\(environment pin, from the s(\d+))")
RE_PRE_SRC = re.compile(r"session-(\d+) run logs|measured in session (\d+)")


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
    print(report[-1])


def bracket_row(lines, arm, b):
    """The unique bracket-table row of `arm` at rung B=`b` (the s232
    convention): the pooled median at (sum,128,S=16) is the last
    integer immediately before the first min..max band on the row."""
    pat = re.compile(r"^\s*%s\s+(?:B=)?%d\s" % (re.escape(arm), b))
    rows = [ln for ln in lines if pat.match(ln) and BAND_RE.search(ln)]
    if len(rows) != 1:
        return None, rows
    m = BAND_RE.search(rows[0])
    assert m is not None  # rows[] is filtered on a band match
    value = int(m.group(1))
    return (value, int(m.group(2)), int(m.group(3)), rows[0]), rows


print("== JUN-59 s233 -- THE FULL ENUMERATION OF EVERY COMMITTED SESSION")
print("== c2/c8 READING, EXTENDED PAST SESSION 20 (the s232 row; s216")
print("== NAMED (a) input) -- enumerate-s233.py over the committed")
print("== publication bytes ONLY (post-hoc parse; the values are the")
print("== named sessions' landed MEASURED QUANTITIES, NOT measurements of")
print("== this tick; pct arithmetic DERIVED).  c2 reading = pooled median")
print("== gpu_ticks at (sum,128,S=16) of the session's committed B=2")
print("== control rung; c8 reading = same at the B=8 control rung.")
print("== DERIVED inputs: committed floor band 31..32 at B=2; committed")
print("== c8 reference 32,915 (session 4 pooled median) -- both from the")
print("== s27 controls census (committed).  The s216 identity hazard")
print("== stays UNDECIDED and unqueued.")
print()

# ---- completeness: SPEC set == on-disk set (fail-closed) ----
disk = {}
for p in GPU.glob("*/publication-s*.txt"):
    m = re.match(r"^publication-s(\d+)\.txt$", p.name)
    if m:
        n = int(m.group(1))
        if n >= 5:
            check(n not in disk, "C0.1 on-disk publication-s%d unique" % n)
            disk[n] = p
spec_ns = sorted(n for n, _, _, _, _ in SPEC)
disk_ns = sorted(disk)
check(spec_ns == disk_ns,
      "C0.2 SPEC set == on-disk set of publication-s<N>.txt (N >= 5):"
      " %d == %d" % (len(spec_ns), len(disk_ns)))
if spec_ns != disk_ns:
    print("     SPEC-only: %s" % sorted(set(spec_ns) - set(disk_ns)))
    print("     disk-only: %s" % sorted(set(disk_ns) - set(spec_ns)))
    sys.exit(1)

# ---- pass 1: parse every session ----
parsed = []  # (n, dir, family, c2_rows, c8_rows, extras)
for n, d, family, arm2, arm8 in SPEC:
    path = GPU / d / ("publication-s%d.txt" % n)
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    lines = text.splitlines()
    print("-- session %3d  %s/publication-s%d.txt  %d bytes  sha256 %s"
          % (n, d, n, len(raw), sha256(raw)))
    check(True, "S%d.1 publication bytes read (%d bytes)" % (n, len(raw)))

    c2_rows = []   # (label, value, extra)
    c8_rows = []
    extras = []

    if family == "BRACKET":
        row2, all2 = bracket_row(lines, arm2, 2)
        check(row2 is not None,
              "S%d.2 c2 bracket row unique and parsed (arm %s B=2)"
              % (n, arm2))
        if row2 is None:
            print("     c2: PARSE FAIL -- candidate rows: %r" % all2)
            sys.exit(1)
        v2, lo2, hi2, ln2 = row2
        c2_rows.append(("bracket", v2, (lo2, hi2)))
        print("     family BRACKET  c2 (arm %s B=2): pooled median %d"
              "  run-median band %d..%d" % (arm2, v2, lo2, hi2))
        print("       row: %s" % ln2.strip())
        inband = FLOOR_BAND[0] <= v2 <= FLOOR_BAND[1]
        print("       in committed floor band 31..32 at B=2 (DERIVED): %s"
              % inband)
        if arm8 is not None:
            row8, all8 = bracket_row(lines, arm8, 8)
            check(row8 is not None,
                  "S%d.3 c8 bracket row unique and parsed (arm %s B=8)"
                  % (n, arm8))
            if row8 is None:
                print("     c8: PARSE FAIL -- candidate rows: %r" % all8)
                sys.exit(1)
            v8, lo8, hi8, ln8 = row8
            c8_rows.append(("bracket", v8, (lo8, hi8)))
            print("     family BRACKET  c8 (arm %s B=8): pooled median %d"
                  "  run-median band %d..%d" % (arm8, v8, lo8, hi8))
            print("       row: %s" % ln8.strip())
            # table-vs-confrontation cross-check (the s232 S%.4 row)
            xpat = re.compile(
                r"^\s*%s \(sum,128,(?:S=)?16\) pooled median (\d+) within"
                r" \+/-5%% of committed %d"
                % (re.escape(arm8), C8_REF))
            xvals = []
            for ln in lines:
                xm = xpat.match(ln)
                if xm:
                    xvals.append(int(xm.group(1)))
            check(len(xvals) >= 1 and all(x == v8 for x in xvals),
                  "S%d.4 c8 confrontation line(s) re-read (%d) and all =="
                  " table value %d" % (n, len(xvals), v8))
            pct = (v8 - C8_REF) / C8_REF * 100.0
            print("       vs committed 32,915 (DERIVED): %+.4f%%  within"
                  " +/-5%%: %s" % (pct, abs(pct) <= 5.0))
        else:
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
                  "S%d.3 c8 ABSENT BY DESIGN -- no B=8 rung in the"
                  " committed bracket grid %s" % (n, grid))
            print("     family BRACKET  c8: ABSENT BY DESIGN (grid %s)"
                  % grid)

    elif family == "CLASSED":
        cls = [ln for ln in lines if RE_C2_CLASS_ONLY.match(ln)]
        check(len(cls) == 1,
              "S%d.2 exactly one own 'c2 class: FLOOR' line (%d)"
              % (n, len(cls)))
        # -- c2: class line only; aggregate lines reported, never readings --
        agg = [m for m in (RE_AGG_MINMAX.match(ln) for ln in lines) if m]
        for m in agg:
            check((int(m.group(1)), int(m.group(2)))
                  == (int(m.group(3)), int(m.group(4))),
                  "S%d.3b c2 AGGREGATE self-consistent (min..max %s..%s"
                  " == stated band %s..%s)"
                  % (n, m.group(1), m.group(2), m.group(3), m.group(4)))
        bare_lines = [ln for ln in lines if RE_ANY_C2_BARE.search(ln)]
        check(not RE_ANY_C2_M.search(text)
              and all(RE_AGG_MINMAX.match(ln) for ln in bare_lines),
              "S%d.3 c2 READING NOT-CARRIED -- zero single-value"
              " 'c2 ... pooled median' lines (min..max aggregate lines"
              " excluded and reported: %d)" % (n, len(agg)))
        b2 = [ln for ln in lines
              if re.match(r"^\s*c2\s+(?:B=)?2\s", ln) and BAND_RE.search(ln)]
        check(len(b2) == 0,
              "S%d.4 c2 READING NOT-CARRIED -- zero c2 bracket rows" % n)
        # -- provenance: which window does the C1 block source? --
        hdr = None
        for ln in lines:
            m = RE_HDR_SRC.search(ln)
            if m:
                hdr = int(m.group(1) or m.group(2))
                break
        pre_end = len(lines)
        for i, ln in enumerate(lines):
            if re.match(r"^\s*1\.\s", ln):
                pre_end = i
                break
        srcs = set()
        for m in RE_PRE_SRC.finditer("\n".join(lines[:pre_end])):
            srcs.add(int(m.group(1) or m.group(2)))
        signals = set(srcs)
        if hdr is not None:
            signals.add(hdr)
        ambiguous = bool(signals - {n}) and (n in signals
                                             or len(signals - {n}) > 1)
        check(not ambiguous,
              "S%d.4b provenance unambiguous (header %s, preamble %s)"
              % (n, "s%d" % hdr if hdr is not None else "none",
                 sorted(srcs) or "none"))
        if ambiguous:
            print("     provenance: PARSE FAIL (contradictory signals)")
            sys.exit(1)
        anchor = None
        if signals - {n}:
            anchor = next(iter(signals - {n}))
        # -- c8: exactly one value line; own reading vs anchor re-derivation --
        vs = [RE_C8_VS.match(ln) for ln in lines]
        vs = [m for m in vs if m]
        check(len(vs) == 1,
              "S%d.5 exactly one c8 value line (vs committed form)"
              " (%d)" % (n, len(vs)))
        if len(vs) != 1:
            print("     c8: PARSE FAIL")
            sys.exit(1)
        v8, stated = int(vs[0].group(1)), float(vs[0].group(2))
        pct = (v8 - C8_REF) / C8_REF * 100.0
        check(abs(abs(pct) - stated) < 0.005 + 1e-9,
              "S%d.6 stated delta %s%% == DERIVED |%+.4f%%| (rounding)"
              % (n, vs[0].group(2), pct))
        print("     family CLASSED  c2: READING NOT-CARRIED (class line"
              " carried: FLOOR)")
        for m in agg:
            print("       c2 AGGREGATE carried (NOT a reading): pooled"
                  " medians min..max %s..%s (within band %s..%s: %s)"
                  % (m.group(1), m.group(2), m.group(3), m.group(4),
                     m.group(5)))
            extras.append(("c2-aggregate",
                           (int(m.group(1)), int(m.group(2)), m.group(5))))
        if anchor is None:
            c8_rows.append(("c1-re-derivation-own", v8, stated))
            print("     family CLASSED  c8 (own C1 re-derivation line):"
                  " pooled median %d  vs committed 32,915 (DERIVED):"
                  " %+.4f%%" % (v8, pct))
        else:
            extras.append(("anchor-c8", (anchor, v8)))
            print("     family CLASSED  c8: ANCHOR re-derivation at s%d"
                  " (NOT this session's reading) -- pooled median %d"
                  "  vs committed 32,915 (DERIVED): %+.4f%%"
                  % (anchor, v8, pct))

    elif family == "QUOTES":
        check(not RE_C2_CLASS_ONLY.search(text)
              and not RE_ANY_C8_OWN_VS.search(text)
              and not RE_ANY_C2_M.search(text)
              and not RE_ANY_C2_BARE.search(text),
              "S%d.2 both readings NOT-CARRIED -- zero own-form control"
              " lines (class-only, c8 value, c2 value)" % n)
        b2 = [ln for ln in lines
              if re.match(r"^\s*c2\s+(?:B=)?2\s", ln) and BAND_RE.search(ln)]
        b8 = [ln for ln in lines
              if re.match(r"^\s*c8\s+(?:B=)?8\s", ln) and BAND_RE.search(ln)]
        check(not b2 and not b8,
              "S%d.3 both readings NOT-CARRIED -- zero c2/c8 bracket"
              " rows" % n)
        qrows = [RE_QUOTE_ROW.match(ln) for ln in lines]
        qrows = [(int(m.group(1)), int(m.group(2))) for m in qrows if m]
        nclass = sum(1 for ln in lines if "c2 class FLOOR" in ln)
        check(nclass == len(qrows),
              "S%d.4 every 'c2 class FLOOR' line is a quote row (%d == %d)"
              % (n, nclass, len(qrows)))
        check(len(qrows) >= 1,
              "S%d.5 quote rows present (%d)" % (n, len(qrows)))
        extras.append(("quote-rows", qrows))
        print("     family QUOTES   c2: NOT-CARRIED  c8: NOT-CARRIED"
              " (quote rows of named sessions only)")
        for qn, qv in qrows:
            print("       quote s%d: c8 %d" % (qn, qv))

    elif family == "C1LINE":
        c2 = [RE_C2_ONELINE.match(ln) for ln in lines]
        c2 = [m for m in c2 if m]
        check(len(c2) == 1,
              "S%d.2 exactly one own c2 one-line C1 form (%d)"
              % (n, len(c2)))
        if len(c2) != 1:
            print("     c2: PARSE FAIL")
            sys.exit(1)
        v2, bool2 = int(c2[0].group(1)), c2[0].group(2)
        c2_rows.append(("c1-one-line", v2, bool2))
        c8 = [RE_C8_ONELINE.match(ln) for ln in lines]
        c8 = [m for m in c8 if m]
        check(len(c8) == 1,
              "S%d.3 exactly one own c8 one-line C1 form (%d)"
              % (n, len(c8)))
        if len(c8) != 1:
            print("     c8: PARSE FAIL")
            sys.exit(1)
        v8, bool8 = int(c8[0].group(1)), c8[0].group(2)
        c8_rows.append(("c1-one-line", v8, bool8))
        check(not RE_ANY_C2_DEEP_M.search(text) and not RE_CLASS_LINE.search(text),
              "S%d.4 zero deep-pooling 'm' forms and zero standalone"
              " class lines (the one-line form carries its own class)"
              % n)
        b2 = [ln for ln in lines
              if re.match(r"^\s*c2\s+(?:B=)?2\s", ln) and BAND_RE.search(ln)]
        b8 = [ln for ln in lines
              if re.match(r"^\s*c8\s+(?:B=)?8\s", ln) and BAND_RE.search(ln)]
        check(not b2 and not b8,
              "S%d.5 zero c2/c8 bracket rows" % n)
        inband = FLOOR_BAND[0] <= v2 <= FLOOR_BAND[1]
        pct = (v8 - C8_REF) / C8_REF * 100.0
        print("     family C1LINE   c2 (sum,128,S=16) pooled median %d"
              "  class FLOOR in-band: %s" % (v2, bool2))
        print("       in committed floor band 31..32 at B=2 (DERIVED): %s"
              % inband)
        print("     family C1LINE   c8 (sum,128,S=16) pooled median %d"
              "  within +/-5%%: %s (DERIVED %+.4f%%)" % (v8, bool8, pct))

    elif family == "C1TWO":
        blocks = []
        for i, ln in enumerate(lines):
            m = RE_C2_OWN_M.match(ln)
            if m:
                blocks.append((i, int(m.group(1))))
        nclass = len([ln for ln in lines if RE_CLASS_LINE.match(ln)])
        nc8 = len([RE_C8_M.match(ln) for ln in lines if RE_C8_M.match(ln)])
        check(len(blocks) >= 1,
              "S%d.2 own two-line C1 blocks present (%d)" % (n, len(blocks)))
        check(nclass == len(blocks) and nc8 == len(blocks),
              "S%d.3 block pairing complete (c2 %d / class %d / c8 %d)"
              % (n, len(blocks), nclass, nc8))
        for i, v2 in blocks:
            cm = RE_CLASS_LINE.match(lines[i + 1]) if i + 1 < len(lines) \
                else None
            check(cm is not None,
                  "S%d.4 block at line %d: class line immediately follows"
                  " the c2 line" % (n, i + 1))
            pair = None
            for j in range(i + 2, min(i + 4, len(lines))):
                pm = RE_C8_M.match(lines[j])
                if pm:
                    pair = pm
                    break
            check(pair is not None,
                  "S%d.4 block at line %d: own c8 'm' line paired within"
                  " the block" % (n, i + 1))
            if cm is None or pair is None:
                print("     c2/c8: PARSE FAIL at line %d" % (i + 1))
                sys.exit(1)
            bool2 = cm.group(1)
            v8, bool8 = int(pair.group(1)), pair.group(2)
            c2_rows.append(("c1-deep-pooling", v2, bool2))
            c8_rows.append(("c1-deep-pooling", v8, bool8))
            inband = FLOOR_BAND[0] <= v2 <= FLOOR_BAND[1]
            pct = (v8 - C8_REF) / C8_REF * 100.0
            print("     family C1TWO    reading (line %d): c2 pooled median"
                  " m %d  class FLOOR in-band: %s (DERIVED band %s)"
                  % (i + 1, v2, bool2, inband))
            print("       c8 pooled median m %d  within +/-5%%: %s"
                  " (DERIVED %+.4f%%)" % (v8, bool8, pct))
        quotes = [RE_C2_QUOTE_M.search(ln) for ln in lines]
        quotes = [int(m.group(1)) for m in quotes if m]
        bare = len([ln for ln in lines if RE_ANY_C2_BARE.search(ln)])
        extras.append(("quote-1line", quotes))
        extras.append(("quote-bare", bare))
        print("       one-line quote forms excluded structurally: %d %s"
              " (unanchored 'c2 pooled median' lines also excluded:"
              " %d)" % (len(quotes), quotes, bare))

    else:
        print("     unknown family %r" % family)
        sys.exit(1)

    parsed.append((n, d, family, c2_rows, c8_rows, extras))
    print()

# ---- pass 2: cross-family checks ----
carried_c8 = {}
anchor_sessions = set()
for n, d, family, c2_rows, c8_rows, extras in parsed:
    vals = [v for _, v, _ in c8_rows]
    for tag, payload in extras:
        if tag == "anchor-c8":
            anchor_sessions.add(n)
            vals.append(payload[1])
    carried_c8[n] = vals
for n, d, family, c2_rows, c8_rows, extras in parsed:
    for tag, payload in extras:
        if tag == "anchor-c8":
            src, v = payload
            check(src in carried_c8 and v in carried_c8[src]
                  and src not in anchor_sessions,
                  "S%d.8 anchor s%d re-derivation %d == s%d's own carried"
                  " reading %s (s%d own-window provenance: %s)"
                  % (n, src, v, src, carried_c8.get(src), src,
                     src not in anchor_sessions))
for n, d, family, c2_rows, c8_rows, extras in parsed:
    if family != "QUOTES":
        continue
    qrows = [e for e in extras if e[0] == "quote-rows"]
    qrows = qrows[0][1] if qrows else []
    for qn, qv in qrows:
        check(qn in carried_c8 and qv in carried_c8[qn],
              "S%d.7 quote row s%d c8 %d == s%d's carried c8 line %s"
              % (n, qn, qv, qn, carried_c8.get(qn)))

# ---- summary ----
print("== SUMMARY (all values RE-PARSED from committed bytes above; the")
print("== multiset arithmetic is DERIVED):")
c2_vals = []
for n, d, family, c2_rows, c8_rows, extras in parsed:
    for label, v, extra in c2_rows:
        c2_vals.append((n, v, label, extra))
c2_only = sorted(v for _, v, _, _ in c2_vals)
counts = {}
for v in c2_only:
    counts[v] = counts.get(v, 0) + 1
print("  c2 readings carried: %d rows over %d sessions"
      % (len(c2_vals), len({n for n, _, _, _ in c2_vals})))
for n, v, label, extra in c2_vals:
    extra_s = ("  class in-band %s" % extra) if isinstance(extra, str) \
        else ""
    print("    session %3d: %d (%s)%s" % (n, v, label, extra_s))
print("  c2 multiset: %s (min %d, max %d)"
      % (", ".join("%d x%d" % (v, counts[v]) for v in sorted(counts)),
         min(c2_only), max(c2_only)))
below = [(n, v) for n, v, _, _ in c2_vals if v < FLOOR_BAND[0]]
print("  c2 below the committed floor band 31..32 at B=2 (<31): %d of %d"
      "  -> %s" % (len(below), len(c2_only), below or "NONE"))
nc2 = [(n, d) for n, d, family, c2_rows, c8_rows, extras in parsed
       if not c2_rows]
print("  c2 READING NOT-CARRIED (per-session census carries no c2"
      " reading at the cell): %d sessions -> %s"
      % (len(nc2), [n for n, _ in nc2]))
agg_rows = [(n, e[1]) for n, d, family, c2_rows, c8_rows, extras in parsed
            for e in extras if e[0] == "c2-aggregate"]
print("  c2 AGGREGATE lines carried (NOT readings; min..max over a"
      " window's pooled medians): %s"
      % [(n, "min..max %d..%d within-band %s" % (lo, hi, b))
         for n, (lo, hi, b) in agg_rows])
print()
c8_vals = []
for n, d, family, c2_rows, c8_rows, extras in parsed:
    for label, v, extra in c8_rows:
        c8_vals.append((n, v, label))
for n, v, label in c8_vals:
    pct = (v - C8_REF) / C8_REF * 100.0
    print("    session %3d: c8 %d  (%+.4f%% of 32,915)" % (n, v, pct))
c8_only = [v for _, v, _ in c8_vals]
pcts = [(v - C8_REF) / C8_REF * 100.0 for v in c8_only]
print("  c8 OWN readings carried: %d rows over %d sessions"
      % (len(c8_vals), len({n for n, _, _ in c8_vals})))
print("  c8 own-reading range: min %d (%+.4f%%), max %d (%+.4f%%);"
      " within +/-5%% of 32,915: %d of %d"
      % (min(c8_only), min(pcts), max(c8_only), max(pcts),
         sum(1 for p in pcts if abs(p) <= 5.0), len(pcts)))
anchor_rows = [(n, e[1][0], e[1][1])
               for n, d, family, c2_rows, c8_rows, extras in parsed
               for e in extras if e[0] == "anchor-c8"]
print("  c8 ANCHOR re-derivations (NOT session readings -- each"
      " duplicates its anchor window's measured quantity, pass-2"
      " cross-checked equal): %d rows" % len(anchor_rows))
for n, src, v in anchor_rows:
    print("    session %3d: c8 %d re-derived at s%d's window" % (n, v, src))
nc8 = [(n, d) for n, d, family, c2_rows, c8_rows, extras in parsed
       if not c8_rows]
print("  c8 own reading NOT-CARRIED: %d sessions -> %s"
      % (len(nc8), [n for n, _ in nc8]))
absent = [(n, d) for n, d, family, c2_rows, c8_rows, extras in parsed
          if family == "BRACKET" and not c8_rows]
print("  c8 ABSENT BY DESIGN (no B=8 rung): %s"
      % [n for n, _ in absent])
print()
print("  IDENTITY-HAZARD INPUT (s216 NAMED (a) -- the hazard question")
print("  itself stays UNDECIDED and unqueued; this enumeration is its")
print("  named input, not its resolution): over EVERY committed session")
print("  publication (sessions 5..229, %d publications: the s232 set of"
      % len(parsed))
print("  16 re-parsed here unchanged + %d extended here), the committed"
      % (len(parsed) - 16))
print("  B=2 control readings at or below 30 are EXACTLY: %s"
      % [(n, v) for n, v, _, _ in c2_vals if v <= 30])
print("  -- every other carried B=2 reading is 31 or 32 (the s232")
sub_counts = {}
for nn, v, _, _ in c2_vals:
    if nn <= 20:
        sub_counts[v] = sub_counts.get(v, 0) + 1
print("  sessions 5..20 multiset re-derives here unchanged: 31 x%d /"
      " 32 x%d; whole-history multiset: %s)."
      % (sub_counts.get(31, 0), sub_counts.get(32, 0),
         {v: counts[v] for v in sorted(counts)}))
print("  The six m 30 rows are the 16th cut's (s169), the 19th cut's")
print("  (s209) and the s225 resolution act's four readings (s229) --")
print("  all in the deep-pooling-era publications, all attached to a")
print("  False in-band verdict (the record's own (b) label).  Every")
print("  own reading the record labels (a) (s158/s185/s197) reads 31.")
print("  AGGREGATE ADJUNCT (named, NOT readings): the CLASSED min..max")
print("  aggregate lines carry no reading at the cell but state every")
print("  pooled median of their windows in band 31..32: %s"
      % [(n, "%d..%d within-band %s" % (lo, hi, b))
         for n, (lo, hi, b) in agg_rows])
print("  CROSS-ERA CAVEAT (named): the readings come from the sessions'")
print("  own instrument/protocol generations (the committed publications")
print("  name them -- e.g. the 25-round bracket grids vs the deep-")
print("  pooling N = 3R = 19,200 units); the enumeration compares them")
print("  observationally at the one named cell (sum,128,S=16) and is not")
print("  a cross-instrument calibration.")
print()
print("== THREE-STATE: the publications' c2/c8 readings are the named")
print("== sessions' landed MEASURED QUANTITIES (their own hardware runs")
print("== on the one named device family under their own instruments and")
print("== protocols), RE-PARSED from committed bytes by this script --")
print("== NOT measurements of this tick; the band/pct arithmetic is")
print("== DERIVED; the s216 identity hazard stays UNMEASURED and")
print("== unqueued; NO vendor optimization exists for Intel (or for any")
print("== vendor) and NONE follows from this enumeration; the accelerator-")
print("== targets workgroup rows stay as ADR-0358 left them (:measured?")
print("== false rows remain provisional -- NOT optimization evidence).")
print()
print("# enumerate s233 (enumerate-s233.py): %d ok / %d failed" % (ok, failed))
sys.exit(0 if failed == 0 else 1)
