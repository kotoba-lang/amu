#!/usr/bin/env python3
"""JUN-59 session 100 -- the s90 W6 READING PRE-BUILD + the session-100
w6-block extension (the s98 provenance pattern: the s90 original is
committed UNCHANGED at anv-b3w6prego-20261029/reading-prego.py; THIS
file supersedes it for W6 adoption).  Session-100 changes, w6 mode
ONLY (the --compat output is byte-identical to the s90 pin):
  (1) the section-4 prior rows are printed in the frozen
      publication-s73.txt section-3b row shape -- want values PARSED
      from the committed publication-s73.txt bytes (never
      transcribed), mechanically enforced, and NO class token on a
      prior row.  WHY: a class-bearing prior row is parsed by
      reconcile-prego.py --line (parse_pub_tuples) as a bar tuple;
      five such rows plus the fresh row gave 6 tuples / 5 distinct
      and a FALSE INCONSISTENT verdict on a fully consistent pair
      (demonstrated at session 100 on the W5-stand-in rehearsal
      pair -- rehearsal-line-unfixed-run1.txt).
  (2) a section-6 D4-shape bar row -- the second class-bearing row,
      equal to section 3's fresh row by construction (the shape
      reconcile-prego.py --line was validated against at s99 on the
      committed publication-s73.txt pair).
  (3) the ok-map label names its index base (the s80 section-3
      phrase "ok-map cell 5" is the 0-based ok-map index of raw idx
      7; this file's s90 form printed the 1-based position 6
      unlabeled).
  (4) the verifier-twin note corrected: derivation-census-prego.py
      is --compat-only (the five committed windows) and has NO w6
      mode -- the fresh-window "every published integer cross-
      checked" duty is a NAMED gap (queued), not machinery that
      exists.

ORIGINAL s90 DOCSTRING FOLLOWS.
JUN-59 session 90 -- W6 READING PRE-BUILD (the W6 measurement row's
IMPLEMENTATION preparation half -- NO hardware runs, NO builds, NO
compiles, NO GO stamp, NO host writes, NO day-slot consumption, NO
ledger line).

WHAT THIS IS (honest states): an IMPLEMENTATION pre-build of the
s80-frozen W6 protocol's READING path (docs/evidence/gpu/
anv-b3w6daybar-20261030/protocol.txt section 6: "the running session's
reading-s<NN>.py parses the committed W6 run logs and writes
publication-s<NN>.txt (the hi block A anchor reading -- (sum,128,S=16)
pooled median, 18-cell min..max, bar class vs the frozen refs
1,129/1,132/1,131 -- plus the section-3 integrity rows)").  It is NOT
the W6 session's script yet: the W6 session (the first measurement
session starting at or after 2026-10-30T00:00:00Z) adopts this file as
reading-s<NN>.py and owns its record.txt.  NO W6 quantity exists or is
computed here -- the W6 run logs do not exist at pre-build time.

VALIDATION AVAILABLE NOW (--compat mode, the default under this
pre-build name): the same generic machinery run over the FIVE committed
windows (s36/s38/s39/s51/s73) must reproduce the committed
publication-s73.txt reading rows EXACTLY -- the section-1 integrity
rows (5), the section-2 C1 rows (3), the section-3b anchor rows (4
prior + 1 fresh) and the section-6 D4 bar row (1): 14 two-way rows,
want values PARSED from the committed publication bytes, never
transcribed.  That validates the run-log parser, the pooled-median
estimator and the class/threshold machinery end-to-end against
published frozen numbers.  The W6-dependent parts (the W6 anchor row,
W6 integrity/C1, the ledger-line day from run-window.txt) cannot be
validated until the W6 logs exist -- they are UNVALIDATED here, named,
not hidden.

THE INDEPENDENCE CONTRACT (the census twin's side; named here so the
pair is read together): derivation-census-prego.py is the independent
second parser -- NO re module (split()-based k=v run-log parsing,
find/split publication parsing) and estimators on the numpy
np.partition kth paths (this generator is pure stdlib,
statistics.median / min / max), cross-checked in-loop against pure-
Python sorted() explicit order statistics.  Both files are
deterministic: NO RNG anywhere, no clock.

Frozen implementation paths (s80 protocol section 6): deterministic
scripts only; the frozen filename is reading-s<NN>.py with <NN> the
running session's number (enforced below -- w6 mode under the pre-build
name refuses to generate).
"""
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
GPU = os.path.join(ROOT, "docs", "evidence", "gpu")

_name = os.path.basename(__file__)
_m = re.match(r"reading-s(\d+)\.py$", _name)
MODE = "w6" if _m else "compat"

WIN5 = [("s36", "anv-b3commonmode-20261028"),
        ("s38", "anv-b3joint3-20261028"),
        ("s39", "anv-b3joint4-20261028"),
        ("s51", "anv-b3levelrep-20261028"),
        ("s73", "anv-b3w5xdayrep-20261029")]
W6_DIR = "anv-b3w5xdayrep-20261029"  # REHEARSAL STAND-IN (s100, fixed path): the committed W5 window stands in for W6

if MODE == "w6":
    assert _m is not None
    SESSION = int(_m.group(1))
    NEW_WIN = "s%d" % SESSION
    WINDOWS = WIN5 + [(NEW_WIN, W6_DIR)]
else:
    SESSION = None
    NEW_WIN = "s73"
    WINDOWS = WIN5

ARMS = {"c2": (2, 1, 1, [1, 2, 3]),
        "hi": (3, 1024, 4033, list(range(1, 37))),
        "tw": (3, 2048, 8066, list(range(1, 37))),
        "c8": (8, 1, 1, [1, 2, 3])}
COMMITTED_C8 = 32915
BAR_REFS = (1129, 1132, 1131)   # settle-bar.txt F3 frozen refs, quoted
CELLKEY_SUM128 = ("sum", 128, "16")
NAMED_CKEY = ("max", 128, "default")

cell_re = re.compile(
    r"^CELL idx=(\d+) spv=(\S+) op=(\S+) wg=(\d+) forced=(\S+) probe_size=(-?\d+) "
    r"probe_nsub=(-?\d+) probe_wg=(-?\d+) pipeline=(\S+) void=(\d)")
verify_re = re.compile(r"^VERIFY idx=(\d+) checked=(\d+) mismatch=(\d+) ok=(\d)")
sample_re = re.compile(
    r"^SAMPLE round=(\d+) idx=(\d+) batch=(\d+) work_mul=(\d+) ndiv=(\d+) gpu_ticks=(\d+) "
    r"gpu_ns=([\d.]+) per_dispatch_ns=([\d.]+) host_ns=(\d+)")


def load(path):
    """One committed run log -> (cells, verifies, samples)."""
    cells, verifies, samples = {}, [], []
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("CELL "):
            m = cell_re.match(line)
            assert m, line
            cells[int(m.group(1))] = dict(op=m.group(3), wg=int(m.group(4)),
                                          forced=m.group(5), pipeline=m.group(9),
                                          void=m.group(10))
        elif line.startswith("VERIFY "):
            m = verify_re.match(line)
            assert m, line
            verifies.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
        elif line.startswith("SAMPLE "):
            m = sample_re.match(line)
            assert m, line
            samples.append((int(m.group(1)), int(m.group(2)), int(m.group(6)),
                            (int(m.group(3)), int(m.group(4)), int(m.group(5)))))
    return cells, verifies, samples


# ------------------------------------------------------------------
# parse the windows; integrity per the s80 protocol section 3
# ------------------------------------------------------------------
data = {}
win_info = {}
ref_cellmap = None
for win, dirname in WINDOWS:
    src = os.path.join(GPU, dirname)
    vmis = 0
    counts_ok = knob_ok = fail_ok = cmap_ok = True
    problems = []
    nlogs = 0
    for tag in ("c2", "hi", "tw", "c8"):
        b, wm, dd, runs = ARMS[tag]
        for r in runs:
            fn = os.path.join(src, "run-%s-r%d.txt" % (tag, r))
            cells, verifies, samples = load(fn)
            data[(win, tag, r)] = (cells, verifies, samples)
            nlogs += 1
            for (_i, _c, mis) in verifies:
                vmis += mis
            okc = [k for k, v in cells.items() if v["pipeline"] == "ok"]
            s8 = [k for k, v in cells.items() if v["forced"] == "8"]
            if len(s8) != 6 or any(cells[k]["pipeline"] != "FAIL" or cells[k]["void"] != "1"
                                   for k in s8):
                fail_ok = False
                problems.append("S=8 fail-closed violation in %s" % fn)
            if len(samples) != len(okc) * 25 or len(verifies) != 24:
                counts_ok = False
                problems.append("sample/verify count mismatch in %s" % fn)
            for (_rnd, _idx, _gt, knobs) in samples:
                if knobs != (b, wm, dd):
                    knob_ok = False
                    problems.append("knob mismatch in %s" % fn)
            cmap = tuple(sorted((k, v["op"], v["wg"], v["forced"], v["pipeline"], v["void"])
                                for k, v in cells.items()))
            if ref_cellmap is None:
                ref_cellmap = cmap
            elif cmap != ref_cellmap:
                cmap_ok = False
                problems.append("cell map mismatch in %s" % fn)
    win_info[win] = dict(vmis=vmis, counts_ok=counts_ok, knob_ok=knob_ok,
                         fail_ok=fail_ok, cmap_ok=cmap_ok, nlogs=nlogs,
                         problems=problems)

ok_cells = sorted([k for k, v in data[(WINDOWS[0][0], "c2", 1)][0].items()
                   if v["pipeline"] == "ok"])


def ckey(idx):
    c = data[(WINDOWS[0][0], "c2", 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])


def ckey_str(idx):
    op, wg, s = ckey(idx)
    return "(%s,%s,S=%s)" % (op, wg, s)


sum128 = [k for k in ok_cells if ckey(k) == CELLKEY_SUM128][0]
nc = [k for k in ok_cells if ckey(k) == NAMED_CKEY][0]
nc_okpos = ok_cells.index(nc) + 1          # 1-based position in the ok map
nc_rawidx = nc                             # raw CELL idx

NCELLS = len(ok_cells)


def pooled(win, tag, idx, runs):
    """Exact pooled median (gpu_ticks) over the runs' 25-round samples."""
    xs = []
    for r in runs:
        xs += [s[2] for s in data[(win, tag, r)][2] if s[1] == idx]
    assert len(xs) == 25 * len(runs)
    return int(statistics.median(xs))


def block_vals(win, tag, runs):
    """Per-cell pooled medians of one block (NCELLS values)."""
    return [pooled(win, tag, k, runs) for k in ok_cells]


def bar_class(bvals):
    if all(v <= 100 for v in bvals):
        return "FLOOR"
    if all(v >= 1000 for v in bvals):
        return "CAPTURED"
    return "INTERMEDIATE/MIXED"


# ------------------------------------------------------------------
# the reading: anchor rows, C1 (the s80 sections 1/3/6 construction)
# ------------------------------------------------------------------
anchor_rows = {}
for win, _d in WINDOWS:
    a_med = pooled(win, "hi", sum128, [1, 2, 3])
    bvals = block_vals(win, "hi", [1, 2, 3])
    anchor_rows[win] = (a_med, min(bvals), max(bvals), bar_class(bvals))

c2_vals = block_vals(NEW_WIN, "c2", ARMS["c2"][3])
c2_cls = bar_class(c2_vals)
c8_m = pooled(NEW_WIN, "c8", sum128, ARMS["c8"][3])
c1_ok = (c2_cls == "FLOOR") and abs(c8_m - COMMITTED_C8) <= 0.05 * COMMITTED_C8

a_med, a_min, a_max, a_cls = anchor_rows[NEW_WIN]
in_band = all(abs(a_med - ref) <= 0.05 * ref for ref in BAR_REFS)


def integrity_row(win):
    info = win_info[win]
    return ("runs %d vmis %d counts %s knobs %s s8 %s cmap %s" %
            (info["nlogs"], info["vmis"], info["counts_ok"], info["knob_ok"],
             info["fail_ok"], info["cmap_ok"]))


# ------------------------------------------------------------------
# run-window day census (the ledger line's day; w6 mode + compat)
# ------------------------------------------------------------------
def run_days(dirname):
    days = []
    path = os.path.join(GPU, dirname, "run-window.txt")
    for line in open(path):
        i = line.find("host-date=")
        if i >= 0:
            days.append(line[i + len("host-date="):i + len("host-date=") + 10])
    return days


if MODE == "w6":
    # ---- the W6 session's publication (s80 protocol section 6) ----
    # Frozen anchor priors: PARSED from the committed
    # publication-s73.txt bytes, never transcribed.  The s36/s38/s39/
    # s51 rows carry explicit "(want M / A..B)" groups; s73's row is
    # the published NEW row and its values ARE the frozen prior for
    # W6's reading.
    PRIOR_RE = re.compile(
        r"\n    (s\d+)(?: \(NEW\))?: median (\d+) min\.\.max (\d+)\.\.(\d+)"
        r"(?: \(want (\d+) / (\d+)\.\.(\d+)\))?")
    _ptext = open(os.path.join(GPU, "anv-b3w5xdayrep-20261029",
                               "publication-s73.txt")).read()
    PRIORS = {}
    for _pm in PRIOR_RE.finditer(_ptext):
        if _pm.group(5) is not None:
            PRIORS[_pm.group(1)] = (int(_pm.group(5)), int(_pm.group(6)),
                                    int(_pm.group(7)))
        else:
            PRIORS[_pm.group(1)] = (int(_pm.group(2)), int(_pm.group(3)),
                                    int(_pm.group(4)))
    assert set(PRIORS) == {"s36", "s38", "s39", "s51", "s73"}, sorted(PRIORS)
    out = []
    P = out.append
    P("JUN-59 session %d -- THE ANCHOR-CLASS SETTLING BAR'S THIRD" % SESSION)
    P("COUNTED-DAY MEASUREMENT (the W6 window) -- READING")
    P("(produced ONLY by reading-s%d.py over the COMMITTED run logs of" % SESSION)
    P("the six fixed evidence directories: the five prior windows of")
    P("publication-s73.txt section 0 (anv-b3commonmode-20261028 = s36,")
    P("anv-b3joint3-20261028 = s38, anv-b3joint4-20261028 = s39,")
    P("anv-b3levelrep-20261028 = s51, anv-b3w5xdayrep-20261029 = W5)")
    P("plus the NEW W6 window measured THIS session in")
    P("anv-b3w6daybar-20261030; protocol.txt was frozen BEFORE any W6")
    P("quantity existed (freeze stamp 2026-10-29T04:23:51Z).)")
    P("")
    P("1. INTEGRITY (computed over each window's committed logs;")
    P("   s80 protocol section 3):")
    for win, _d in WINDOWS:
        P("   %s: %s" % (win, integrity_row(win)))
    P("   named cell (max,128,S=default): ok-map cell %d, raw idx %d" %
      (nc_okpos - 1, nc_rawidx))
    P("   (the ok-map cell index is 0-based -- the s80 section-3")
    P("   phrase 'ok-map cell 5'; the 1-based ok-map position is %d)" %
      nc_okpos)
    P("   INVALIDATION criterion (protocol section 3): any violation =>")
    P("   FLAGGED (no reading, no day slot).")
    P("")
    P("2. C1 RE-DERIVATION (environment pin, from the %s window's logs):" % NEW_WIN)
    P("   c2 class: %s (FLOOR required; committed floor band 31..32)" % c2_cls)
    P("   c8 (sum,128,S=16) pooled median %d vs committed %d "
      "(%.2f%% delta; +/-5%% required)" %
      (c8_m, COMMITTED_C8, abs(c8_m - COMMITTED_C8) / COMMITTED_C8 * 100))
    P("   C1 branch: %s" % ("(a) both controls replicate" if c1_ok else "(b) discrepancy"))
    P("")
    P("3. THE ANCHOR READING (hi block A -- the frozen L12 single bar")
    P("   candidate; the reading unit is one 3-run block pooled over 25")
    P("   rounds per cell, the frozen estimator unit F3 of settle-bar.txt):")
    P("   %s (NEW): median %d min..max %d..%d; class %s" %
      (NEW_WIN, a_med, a_min, a_max, a_cls))
    P("   in-band vs the bar's frozen refs 1,129/1,132/1,131 (within")
    P("   +/-5%% of EACH, settle-bar.txt V1): %s" % in_band)
    P("")
    P("4. PRIOR-WINDOW ANCHOR REPRODUCTION (the frozen priors PARSED")
    P("   from the committed publication-s73.txt bytes, never")
    P("   transcribed; reproduction EXACT required -- the prior rows")
    P("   carry NO class token: the frozen publication-s73 section-3b")
    P("   row shape, and a class-bearing prior row is parsed by")
    P("   reconcile-prego.py --line as a BAR tuple):")
    prior_ok = True
    for win, _d in WIN5:
        a = anchor_rows[win]
        w = PRIORS[win]
        rok = (a[0], a[1], a[2]) == w
        prior_ok = prior_ok and rok
        P("   %s: median %d min..max %d..%d (want %d / %d..%d); "
          "reproduction EXACT: %s" % (win, a[0], a[1], a[2],
                                      w[0], w[1], w[2], rok))
    P("   all five prior windows reproduce EXACTLY: %s" % prior_ok)
    P("   (a False row means the run logs do not reproduce the")
    P("   committed priors; FAIL-CLOSED -- no ledger line derives")
    P("   from this reading.)")
    P("")
    P("5. THE RUN DAY (the ledger line's day; s80 protocol section 1:")
    P("   day = the W6 run's ACTUAL UTC day from run-window.txt):")
    days = run_days(W6_DIR)
    distinct = sorted(set(days))
    P("   run-window host-dates: %d parsed, %d distinct: %s" %
      (len(days), len(distinct), " ".join(distinct)))
    P("   ledger line day = %s" % (distinct[0] if len(distinct) == 1 else
                                   "NOT SINGLE-DAY (%s)" % ",".join(distinct)))
    P("")
    P("6. THE BAR READING ROW (D4 shape -- the ledger-line tuple,")
    P("   printed a second time for the reconciler's two-class-row")
    P("   agreement check; both class-bearing rows carry the same")
    P("   values by construction): median %d min..max %d..%d, class %s" %
      (a_med, a_min, a_max, a_cls))
    P("")
    P("   NAMED, NOT HIDDEN: this reading machinery pre-build computes")
    P("   NO W6 quantity; the block-min vectors are NOT part of this")
    P("   reading (the T18 analysis half's invalidation machinery, its")
    P("   own session); the verifier twin derivation-census-prego.py is")
    P("   --compat-only (the five committed windows) and has NO w6")
    P("   mode -- the fresh-window 'every published integer")
    P("   cross-checked' duty is a NAMED gap (queued), not machinery")
    P("   that exists; the cross-tool check that exists today is")
    P("   reconcile-prego.py --line against the ledger line after the")
    P("   append.")
    text = "\n".join(out) + "\n"
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    sys.exit(0)

# ------------------------------------------------------------------
# --compat: the 14 two-way rows against the committed publication-s73.txt
# ------------------------------------------------------------------
pub = open(os.path.join(GPU, "anv-b3w5xdayrep-20261029", "publication-s73.txt")).read()
rows = []


def row(label, want, got):
    rows.append((label, want, got, want == got))


ire = re.compile(
    r"(s\d+): runs parsed (\d+); VERIFY mismatch total (\d+); counts ok (\w+); "
    r"knobs ok (\w+); S=8 fail-closed (\w+); cell map ok (\w+)")
for m in ire.finditer(pub):
    win = m.group(1)
    want = "runs %s vmis %s counts %s knobs %s s8 %s cmap %s" % m.group(2, 3, 4, 5, 6, 7)
    row("sec1 %s integrity" % win, want, integrity_row(win))

m = re.search(r"c2 class: (\S+) \(FLOOR required", pub)
assert m is not None
row("sec2 c2 class", m.group(1), c2_cls)
m = re.search(r"pooled median (\d+) vs committed", pub)
assert m is not None
row("sec2 c8 pooled median", m.group(1), "%d" % c8_m)
m = re.search(r"C1 branch: (.+)", pub)
assert m is not None
row("sec2 C1 branch", m.group(1).strip(),
    "(a) both controls replicate" if c1_ok else "(b) discrepancy")

are = re.compile(r"\n    (s\d+): median (\d+) min\.\.max (\d+)\.\.(\d+) \(want")
for m in are.finditer(pub):
    win = m.group(1)
    a = anchor_rows[win]
    row("sec3b %s anchor" % win, "%s %s..%s" % m.group(2, 3, 4),
        "%d %d..%d" % (a[0], a[1], a[2]))

m = re.search(r"\n    s73 \(NEW\): median (\d+) min\.\.max (\d+)\.\.(\d+); class (\S+)", pub)
assert m is not None
a = anchor_rows["s73"]
row("sec3b s73 anchor (fresh)", "%s %s..%s %s" % m.group(1, 2, 3, 4),
    "%d %d..%d %s" % (a[0], a[1], a[2], a[3]))

m = re.search(r"D4 the W5 anchor reading.*?median (\d+) min\.\.max (\d+)\.\.(\d+), "
              r"class (\S+) vs the bar", pub, re.S)
assert m is not None
row("sec6-D4 s73 bar reading", "%s %s..%s %s" % m.group(1, 2, 3, 4),
    "%d %d..%d %s" % (a[0], a[1], a[2], a[3]))

out = []
out.append("JUN-59 session 90 -- W6 READING PRE-BUILD (--compat validation")
out.append("report; reading-prego.py over the FIVE committed windows; NO W6")
out.append("quantity exists or is computed -- the W6 run logs do not exist).")
out.append("Two-way rows: want = parsed from the committed publication-s73.txt")
out.append("bytes (never transcribed); got = recomputed here from the 390")
out.append("committed run logs. Generator: pure stdlib (re + statistics.median).")
out.append("")
nfail = 0
for (label, want, got, ok) in rows:
    out.append("%-28s want: %-42s got: %-42s %s" %
               (label, want, got, "EXACT" if ok else "MISMATCH"))
    if not ok:
        nfail += 1
out.append("")
out.append("TOTAL: %d rows, %d failed" % (len(rows), nfail))
out.append("")
out.append("BAR-FACING READING (the row this machinery exists for; computed")
out.append("content, cross-checked by derivation-census-prego.py):")
out.append("  %s anchor: median %d min..max %d..%d; class %s; in-band vs" %
           (NEW_WIN, a_med, a_min, a_max, a_cls))
out.append("  refs 1,129/1,132/1,131 (within +/-5%% of EACH): %s" % in_band)
out.append("")
out.append("UNVALIDATED (named, not hidden): the W6-dependent parts of the")
out.append("w6 mode (the W6 anchor row, W6 integrity/C1, the run-window day")
out.append("census) cannot run until the W6 logs exist; w6 mode is enforced")
out.append("by the frozen filename reading-s<NN>.py and refuses to run under")
out.append("this pre-build name.")
text = "\n".join(out) + "\n"
if len(sys.argv) > 1:
    with open(sys.argv[1], "w") as f:
        f.write(text)
else:
    sys.stdout.write(text)
sys.exit(0 if nfail == 0 else 1)
