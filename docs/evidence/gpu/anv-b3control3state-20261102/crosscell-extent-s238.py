#!/usr/bin/env python3
"""crosscell-extent-s238.py -- THE S216 IDENTITY HAZARD'S CAUSE
RESIDUAL'S CROSS-CELL EXTENT (amu-gpu session 238; the s237
carry-forward's first standing row "the CAUSE of the sample-shape
difference (execution-time state vs instrument/timestamp-quantization
state) stays UNMEASURED" TAKEN AS ITS ROW as a CONSTRAINT row -- the
s232 precedent shape: a named input to the cause question, NOT its
resolution).

THE ROW: the s234 sample-shape confrontation decided the (a)/(b)
dichotomy at ONE cell -- the c2 reading cell (sum,128,S=16) -- and
named the cause of the shape difference UNMEASURED.  The committed
c2 run logs of the same nine reference windows carry EVERY pipeline-
ok cell of the instrument's dispatch stream (18 cells: 2 workgroup
sizes x 3 ops x 3 non-failed forced widths).  Whether the (a)/(b)
sample-shape difference is confined to the reading cell or extends
over the whole recorded stream is UNCHECKED from committed bytes --
and it CONSTRAINS the cause dichotomy: a cell-/kernel-LOCAL cause
and a whole-stream cause make different extent predictions.

THE EXTENT CRITERION (fixed here, before the numbers; the s234
criterion applied per cell, unchanged): at each cell c, let s_w,c be
the per-sample share vector of window w over the union support of
observed gpu_ticks at cell c (percent); W_in(c) = max L1 over
same-letter window pairs at c, W_out(c) = min L1 over opposite-
letter window pairs at c.  The cell SEPARATES iff W_out(c) > W_in(c)
-- the s234 rule, frozen there for the reading cell, applied here to
every cell as a SUPPLEMENTARY REPORT (PATTERN-LEVEL ONLY (s218 2(e)):
NO p-value, NO test statistic, NO probability claim; the per-cell
application is REPORT, never a CHECK -- only the reading-cell rows
bind).  EXTENT ROWS (reported):
  - CELL-LOCAL: separation confined to the reading cell -> a whole-
    stream cause is ruled out as the locus.
  - WHOLE-STREAM: separation at every pipeline-ok cell -> any cell-/
    kernel-local cause is ruled out as the locus; the dichotomy
    (execution-time state vs instrument/timestamp-quantization
    state) itself is NOT decided -- both surviving candidates are
    whole-stream states, and the CAUSE stays UNMEASURED.
SHAPE-VS-SHIFT (reported, supplementary): at each cell, D = L1
between the letter groups' pooled share vectors and D_shift = L1
between group (a)'s pooled shares and group (b)'s pooled shares
translated +1 tick.  A pure additive-shift account predicts D_shift
at within-group order (<= W_in); reported per cell, never a check.

UNIVERSE (fixed here, before the numbers): the nine deep-pooling-era
own readings whose raw run logs are COMMITTED -- the s234 universe
unchanged (cuts s158/s169/s185/s197/s209 + the s225 act's four
readings; 27 run logs, 9 windows x k=3).  The s237 kernel-variant
arms and the s235 supplementary arms are OUTSIDE (named, not
hidden).  The letter groups are RE-DERIVED here (m against the
committed floor band) and must EQUAL the committed s234 rows.

Reads ONLY committed bytes (fail-closed; any parse anomaly is an
immediate abort = failed run):
  - docs/evidence/gpu/anv-b3bisect{15..19}-*/run-c2-r0{1..3}.txt.gz
    and docs/evidence/gpu/anv-b3control3state-20261102/run-
    rd{1..4}-c2-r0{1..3}.txt.gz (the nine windows' c2 logs, through
    gzip).
  - docs/evidence/gpu/anv-b3control3state-20261102/identity-
    shape-s234-run1.txt (the committed s234 report rows -- BINDS:
    every reading-cell row below re-derived from the run logs must
    EQUAL the committed bytes).
  - docs/evidence/gpu/anv-b3bisect7-20261027/derivation-census-
    s27.txt (the committed floor band and c8 reference).

Writes NOTHING.  Prints the report to stdout, nothing to stderr on
success.  Exit 0 iff every CHECK is ok.

CHECKS vs REPORTS (the honesty split): PARSE anomalies and BIND
mismatches (missing file, header/cell-map divergence, run-integrity
problems, any reading-cell row disagreeing with the committed s234
bytes) are CHECKS and fail the run; the cross-cell extent table, the
shape-vs-shift rows, the host_ns channel rows and the extent verdict
are REPORTS and never fail the run.

THREE-STATE: every sample value below is a named run's landed
MEASURED QUANTITY (its own hardware runs on aiueos-6600hs, Intel BMG
G31, under the named instrument), RE-PARSED here from committed
run-log bytes -- this script measures NOTHING new on hardware (no
runs, no builds, NO GO stamp) and no value here is a measurement of
this tick; the share/distance arithmetic is DERIVED (labelled).  The
CAUSE of the sample-shape difference stays UNMEASURED and UNDECIDED
(this row CONSTRAINS its locus only); the underlying-instrument-state
COUNT stays outside (s220 1(b) binds).  RULE 4 unchanged: NOTHING
MOVES; the committed bracket stays EXACTLY (254,923, 255,045]; the
accelerator-targets workgroup rows stay exactly as ADR-0358 left
them (:measured? false rows remain provisional -- NOT optimization
evidence); NO vendor optimization exists for Intel (or for any
vendor) and none follows from this constraint.
"""

import gzip
import hashlib
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

GPU = Path(__file__).resolve().parent.parent  # docs/evidence/gpu
HERE = Path(__file__).resolve().parent

# The committed floor band / c8 reference (the s27 controls census;
# parsed from the committed bytes below and cross-checked to these
# pins) -- DERIVED arithmetic inputs only.
C2_PIN, FLOOR_BAND, C8_REF = 31, (31, 32), 32915

# The frozen reading cell and run knobs (the instrument contract,
# uniform across all nine windows' committed c2 logs -- the s234
# pins, re-checked here).
CELL_KEY = ("sum", 128, "16")          # (op, wg, forced) at the cell
R, WARMUP, N_BASE, B = 6400, 3, 1000003, 2
KNOB_PIN = dict(n=N_BASE, rounds=R, warmup=WARMUP, batch=B,
                barrier_n=0, work_mul=1, ndiv=1, seed=20261027)
INSTRUMENT = ("# instrument=anv-subgroupsize-batch v2-batch64 "
              "(JUN-59 subgroup 16-vs-32 floor-lifting rerun, "
              "2026-10-27)")
DEVICE = ("# device_name=Intel(R) Graphics (BMG G31) vendor=8086 "
          "device=e223 api=1.4.318")

# (label, session, kind, run dir, run name pattern)
WINDOWS = [
    ("s158",   158, "cut", "anv-b3bisect15-20261101",
     "run-c2-r0{}.txt.gz"),
    ("s169",   169, "cut", "anv-b3bisect16-20261101",
     "run-c2-r0{}.txt.gz"),
    ("s185",   185, "cut", "anv-b3bisect17-20261101",
     "run-c2-r0{}.txt.gz"),
    ("s197",   197, "cut", "anv-b3bisect18-20261101",
     "run-c2-r0{}.txt.gz"),
    ("s209",   209, "cut", "anv-b3bisect19-20261102",
     "run-c2-r0{}.txt.gz"),
    ("act-rd1", 229, "act", "anv-b3control3state-20261102",
     "run-rd1-c2-r0{}.txt.gz"),
    ("act-rd2", 229, "act", "anv-b3control3state-20261102",
     "run-rd2-c2-r0{}.txt.gz"),
    ("act-rd3", 229, "act", "anv-b3control3state-20261102",
     "run-rd3-c2-r0{}.txt.gz"),
    ("act-rd4", 229, "act", "anv-b3control3state-20261102",
     "run-rd4-c2-r0{}.txt.gz"),
]

S234_REPORT = HERE / "identity-shape-s234-run1.txt"
S27 = GPU / "anv-b3bisect7-20261027" / "derivation-census-s27.txt"

cell_re = re.compile(
    r"^CELL idx=(\d+) spv=(\S+) op=(\S+) wg=(\d+) forced=(\S+) "
    r"probe_size=(-?\d+) probe_nsub=(-?\d+) probe_wg=(-?\d+) "
    r"pipeline=(\S+) void=(\d)")
verify_re = re.compile(r"^VERIFY idx=(\d+) checked=(\d+) mismatch=(\d+) ok=(\d)")
SAMPLE_FIELDS = ("round=", "idx=", "batch=", "work_mul=", "ndiv=",
                 "gpu_ticks=", "gpu_ns=", "per_dispatch_ns=", "host_ns=")
RE_KNOB = re.compile(
    r"n=(\d+) rounds=(\d+) warmup=(\d+) batch=(\d+) barrier_n=(\d+) "
    r"work_mul=(\d+) ndiv=(\d+) seed=(\d+)")
RE_S27 = re.compile(
    r"committed controls: c2 (\d+) \(floor band (\d+)\.\.(\d+)\); "
    r"c8 ([\d,]+) \(session 4 pooled median\)")
# -- committed s234 report row forms (BINDS) --
RE_S234_SUPPORT = re.compile(
    r"^   union support of gpu_ticks at the cell: \[([\d, ]+)\]$")
RE_S234_CENSUS = re.compile(
    r"^   (\S+)\s+sess=(\d+) N=(\d+) m=([\d.]+) mad=([\d.]+)\s+top3 (.+)$")
RE_S234_SHAREROW = re.compile(r"^     (\S+)\s+((?:\d+:[\d.]+\s*)+)$")
RE_S234_GROUP = re.compile(r"^     \(([ab])\): \[('.*')\]$")
RE_S234_POOLED = re.compile(
    r"^     group \(([ab])\) pooled: ((?:\d+:[\d.]+\s*)+)$")
RE_S234_PAIRCENSUS = re.compile(
    r"^  ok    S234\.D1 pair census complete "
    r"\(within-a (\d+), within-b (\d+), between (\d+)\)$")
RE_S234_WIN = re.compile(
    r"^   W_in  = max within-group L1 = ([\d.]+) \((\S+) vs (\S+)\)$")
RE_S234_WOUT = re.compile(
    r"^   W_out = min between-group L1 = ([\d.]+) \((\S+) vs (\S+)\)$")
RE_S234_VERDICT = re.compile(
    r"^   SHAPES SEPARATE \(W_out ([\d.]+) > W_in ([\d.]+)\)\.$")

CHECKS = {"ok": 0, "failed": 0}
OUT = []


def P(text=""):
    OUT.append(text)


def check(label, cond, detail=""):
    if cond:
        CHECKS["ok"] += 1
        P(f"  ok    {label}")
    else:
        CHECKS["failed"] += 1
        P(f"  FAIL  {label}" + (f" -- {detail}" if detail else ""))


def fmtm(m):
    return str(int(m)) if float(m).is_integer() else f"{m}"


# ---------------------------------------------------------------- run logs
def load(path):
    """One committed run log, READ THROUGH GZIP (structure asserted,
    fail-closed).  Returns (cells, verifies, header, ticks, host, counts,
    rounds)."""
    cells, verifies, header = {}, [], []
    ticks, host, counts, rounds = {}, {}, {}, {}
    with gzip.open(path, "rt") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("#"):
                header.append(line)
                continue
            if line.startswith("CELL "):
                mm = cell_re.match(line)
                assert mm, line
                idx = int(mm.group(1))
                assert idx not in cells, f"duplicate CELL idx {idx}"
                cells[idx] = dict(spv=mm.group(2), op=mm.group(3),
                                  wg=int(mm.group(4)), forced=mm.group(5),
                                  pipeline=mm.group(9), void=int(mm.group(10)))
                continue
            if line.startswith("VERIFY "):
                mm = verify_re.match(line)
                assert mm, line
                verifies.append((int(mm.group(1)), int(mm.group(2)),
                                 int(mm.group(3)), int(mm.group(4))))
                continue
            assert line.startswith("SAMPLE "), line
            f = line.split(" ")
            assert len(f) == 10, line
            assert f[0] == "SAMPLE", line
            for i in range(1, 10):
                assert f[i].startswith(SAMPLE_FIELDS[i - 1]), line
            rnd = int(f[1][6:])
            idx = int(f[2][4:])
            gt = int(f[6][10:])
            float(f[7][7:])
            float(f[8][16:])
            hn = int(f[9][8:])
            assert (int(f[3][6:]) == B and int(f[4][9:]) == 1
                    and int(f[5][5:]) == 1), line
            ticks.setdefault(idx, []).append(gt)
            host.setdefault(idx, []).append(hn)
            counts[idx] = counts.get(idx, 0) + 1
            rounds.setdefault(idx, set()).add(rnd)
    return cells, verifies, header, ticks, host, counts, rounds


def load_run(path):
    cells, verifies, header, ticks, host, counts, rounds = load(path)
    s128 = [k for k, v in cells.items()
            if (v["op"], v["wg"], v["forced"]) == CELL_KEY]
    problems = []
    if len(s128) != 1:
        problems.append(f"reading-cell count {s128}")
    if len(cells) != 24:
        problems.append(f"CELL COUNT {len(cells)} != 24")
    if len(verifies) != 24:
        problems.append(f"VERIFY COUNT {len(verifies)} != 24")
    if "# done cells=24" not in header:
        problems.append("TAIL MISSING")
    if INSTRUMENT not in header:
        problems.append("INSTRUMENT LINE MISMATCH")
    if DEVICE not in header:
        problems.append("DEVICE LINE MISMATCH")
    if not any("timestampPeriod=52.083" in l for l in header):
        problems.append("timestampPeriod PIN MISMATCH")
    knobs = None
    for l in header:
        if l.startswith("# n="):
            mk = RE_KNOB.search(l)
            assert mk, l
            knobs = tuple(int(mk.group(i)) for i in range(1, 9))
    if knobs != tuple(KNOB_PIN.values()):
        problems.append(f"HEADER KNOB MISMATCH {knobs}")
    for kk, v in cells.items():
        if not (v["spv"].endswith(".emitted.spv") and ".iter" not in v["spv"]):
            problems.append(f"CELL spv SET MISMATCH idx={kk}: {v['spv']}")
    ok_cells = sorted(k for k, v in cells.items() if v["pipeline"] == "ok")
    if len(ok_cells) != 18:
        problems.append(f"OK CELL COUNT {len(ok_cells)} != 18")
    if sum(counts.values()) != len(ok_cells) * R:
        problems.append(f"SAMPLE COUNT {sum(counts.values())} != "
                        f"{len(ok_cells) * R}")
    for kk in ok_cells:
        if counts.get(kk, 0) != R:
            problems.append(f"SAMPLE COUNT idx={kk} {counts.get(kk, 0)} != {R}")
        if rounds.get(kk, set()) != set(range(R)):
            problems.append(f"ROUND SET idx={kk} incomplete")
    fail_cells = sorted(k for k, v in cells.items() if v["pipeline"] == "FAIL")
    for kk in fail_cells:
        if kk in ticks:
            problems.append(f"FAIL CELL HAS SAMPLES idx={kk}")
    if len(verifies) == 24 and sum(t[2] for t in verifies) != 0:
        problems.append("VERIFY MISMATCH NONZERO")
    cell_map = tuple(sorted((kk, v["spv"], v["op"], v["wg"], v["forced"],
                             v["pipeline"], v["void"])
                            for kk, v in cells.items()))
    return dict(ticks=ticks, host=host, problems=problems,
                header=tuple(header), cell_map=cell_map,
                ok_cells=tuple(ok_cells), fail_cells=tuple(fail_cells),
                s128=s128[0] if s128 else None)


# ------------------------------------------------------- share / L1 (s234)
def shares(counter, support):
    n = sum(counter.values())
    return {v: 100.0 * counter.get(v, 0) / n for v in support}


def l1(s1, s2):
    return sum(abs(s1[v] - s2[v]) for v in s1)


def share_rows(sh):
    return "  ".join(f"{k}:{v:.4f}" for k, v in sorted(sh.items()) if v > 0)


def top3(counter, n):
    top = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    return "  ".join(f"{k}:{100.0 * v / n:.4f}%" for k, v in top)


# ------------------------------------------------------------------ report
P("crosscell-extent-s238.py -- THE S216 IDENTITY HAZARD'S CAUSE")
P("RESIDUAL'S CROSS-CELL EXTENT (amu-gpu s238; the s237 carry-")
P("forward's first standing row -- the CAUSE of the sample-shape")
P("difference (execution-time state vs instrument/timestamp-")
P("quantization state) -- taken as a CONSTRAINT row: the cause")
P("question's named input, NOT its resolution).")
P()
P("THE EXTENT CRITERION (the s234 criterion applied per cell,")
P("unchanged; supplementary REPORT at every cell but the reading")
P("cell): s_w,c = per-sample share vector of window w over the union")
P("support of observed gpu_ticks at cell c; W_in(c) = max L1 over")
P("same-letter window pairs, W_out(c) = min L1 over opposite-letter")
P("window pairs; the cell SEPARATES iff W_out(c) > W_in(c).")
P("  EXTENT ROWS: CELL-LOCAL (separation confined to the reading")
P("cell -> a whole-stream cause ruled out as the locus) vs WHOLE-")
P("STREAM (separation at every pipeline-ok cell -> any cell-/kernel-")
P("local cause ruled out as the locus; the dichotomy itself stays")
P("UNDECIDED -- both surviving candidates are whole-stream states).")
P("  SHAPE-VS-SHIFT: D = L1 between the groups' pooled shares;")
P("D_shift = L1 between (a)'s pooled shares and (b)'s pooled shares")
P("translated +1 tick; a pure additive-shift account predicts")
P("D_shift at within-group order (<= W_in).")
P("  PATTERN-LEVEL ONLY (s218 2(e)): NO p-value, NO test statistic,")
P("NO probability claim.")
P("UNIVERSE: the nine deep-pooling-era own readings with COMMITTED")
P("raw run logs (the s234 universe unchanged: cuts s158/s169/s185/")
P("s197/s209 + the act's four readings; 27 run logs).  OUTSIDE")
P("(named, not hidden): the s237 kernel-variant arms and the s235")
P("supplementary arms.")
P()

# ---- band / reference pins from the committed s27 census ----
s27 = S27.read_text()
m27 = RE_S27.search(s27)
assert m27, "s27 census row"
band = (int(m27.group(2)), int(m27.group(3)))
c2pin, c8ref = int(m27.group(1)), int(m27.group(4).replace(",", ""))
check("S238.A1 s27 census parse == pins (c2 31, band 31..32, c8 32915)",
      (c2pin, band, c8ref) == (C2_PIN, FLOOR_BAND, C8_REF),
      f"got {(c2pin, band, c8ref)}")

# ---- the 27 committed run logs ----
P()
P("1. THE RUN-LOG CENSUS (every sample RE-PARSED from committed")
P("   run-log bytes; m = pooled sample median gpu_ticks over k=3")
P("   runs x R rounds at the cell; MAD = sample median |x - m| --")
P("   the frozen s217/s218 statistic):")
runs = {}
for label, sess, kind, d, pat in WINDOWS:
    for nn in (1, 2, 3):
        name = pat.format(nn)
        path = GPU / d / name
        assert path.exists(), f"RUN LOG MISSING: {path}"
        runs[(label, nn)] = load_run(path)
check("S238.A2 header identity across all 27 runs",
      len({r["header"] for r in runs.values()}) == 1)
check("S238.A3 cell-map identity across all 27 runs",
      len({r["cell_map"] for r in runs.values()}) == 1)
for (label, nn), r in sorted(runs.items()):
    check(f"S238.B{label}-r{nn:02d} run integrity clean",
          not r["problems"], "; ".join(r["problems"]))
ok_cells = runs[(WINDOWS[0][0], 1)]["ok_cells"]
fail_cells = runs[(WINDOWS[0][0], 1)]["fail_cells"]
check("S238.A4 ok/fail cell sets uniform (18 ok incl. reading cell, "
      "6 FAIL forced=8)",
      all(r["ok_cells"] == ok_cells and r["fail_cells"] == fail_cells
          for r in runs.values())
      and len(ok_cells) == 18 and len(fail_cells) == 6
      and runs[(WINDOWS[0][0], 1)]["s128"] in ok_cells)

P()
P("   the header block (8 lines, identical across all 27 runs --")
P("   the RECORDED instrument/timestamp metadata, byte-compared):")
for l in runs[(WINDOWS[0][0], 1)]["header"]:
    P(f"     {l}")
P()
P("   the 6 pipeline-FAIL cells (no samples in any window; named")
P("   and EXCLUDED from the extent table below):")
cell_map = runs[(WINDOWS[0][0], 1)]["cell_map"]
for row in cell_map:
    if row[0] in fail_cells:
        P(f"     idx={row[0]:2d} spv={row[1]} op={row[2]} wg={row[3]} "
          f"forced={row[4]} pipeline={row[5]}")

# ---- per-window, per-cell pooled statistics ----
win = {}
for label, sess, kind, d, pat in WINDOWS:
    per = {}
    for idx in ok_cells:
        xs, hs = [], []
        for nn in (1, 2, 3):
            xs.extend(runs[(label, nn)]["ticks"][idx])
            hs.extend(runs[(label, nn)]["host"][idx])
        m_ = statistics.median(xs)
        per[idx] = dict(
            N=len(xs), m=m_,
            mad=statistics.median([abs(x - m_) for x in xs]),
            cnt=Counter(xs), host_med=statistics.median(hs),
            host_cnt=Counter(hs))
    win[label] = per

# ---- reading-cell re-derivation BINDS to the committed s234 report ----
P()
P("2. READING-CELL BINDS (every s234 row below is RE-DERIVED here")
P("   from the run logs and must EQUAL the committed report bytes")
P("   identity-shape-s234-run1.txt -- fail-closed; this binds the")
P("   cross-cell machinery to the committed record):")
s234_bytes = S234_REPORT.read_bytes()
P(f"   s234 report pin: {len(s234_bytes)} bytes sha256 "
  f"{hashlib.sha256(s234_bytes).hexdigest()}")
s234 = s234_bytes.decode()
s234_lines = s234.splitlines()
sidx = runs[(WINDOWS[0][0], 1)]["s128"]
support128 = sorted({v for label, *_ in WINDOWS
                     for v in win[label][sidx]["cnt"]})
msup = [RE_S234_SUPPORT.match(l) for l in s234_lines]
msup = [m for m in msup if m]
check("S238.C1 s234 union-support row present exactly once",
      len(msup) == 1, f"found {len(msup)}")
if len(msup) == 1:
    sup_pub = [int(x) for x in msup[0].group(1).split(",")]
    check("S238.C2 re-derived reading-cell union support == s234 row",
          sup_pub == support128, f"{sup_pub} != {support128}")

# per-window census + share rows
pub_census, pub_shares = {}, {}
for l in s234_lines:
    mc = RE_S234_CENSUS.match(l)
    if mc:
        pub_census[mc.group(1)] = mc
        continue
    msh = RE_S234_SHAREROW.match(l)
    if msh and msh.group(1) in {w[0] for w in WINDOWS}:
        pub_shares[msh.group(1)] = msh.group(2).split()
check("S238.C3 s234 per-window census rows present 9/9",
      set(pub_census) == {w[0] for w in WINDOWS}, f"{sorted(pub_census)}")
check("S238.C4 s234 per-window share rows present 9/9",
      set(pub_shares) == {w[0] for w in WINDOWS}, f"{sorted(pub_shares)}")

groups = {"a": [], "b": []}
for label, sess, kind, d, pat in WINDOWS:
    w = win[label][sidx]
    letter = "a" if band[0] <= w["m"] <= band[1] else "b"
    groups[letter].append(label)
    top = sorted(w["cnt"].items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    top_s = "  ".join(f"{k}:{100.0 * v / w['N']:.4f}%" for k, v in top)
    mc = pub_census.get(label)
    if mc is not None:
        check(f"S238.C5.{label} re-derived N/m/mad/top3 == s234 census row",
              (int(mc.group(3)), float(mc.group(4)), float(mc.group(5)),
               mc.group(6)) == (w["N"], w["m"], w["mad"], top_s),
              f"got N={w['N']} m={w['m']} mad={w['mad']} top3={top_s!r} "
              f"pub=({mc.group(3)}, {mc.group(4)}, {mc.group(5)}, "
              f"{mc.group(6)!r})")
    if label in pub_shares:
        mine = share_rows(shares(w["cnt"], support128)).split()
        check(f"S238.C6.{label} re-derived reading-cell share row == "
              f"s234 share row",
              mine == pub_shares[label],
              f"got {mine} pub {pub_shares[label]}")

# group rows + pooled rows
for letter in ("a", "b"):
    mrows = [RE_S234_GROUP.match(l) for l in s234_lines]
    mrows = [m for m in mrows if m and m.group(1) == letter]
    check(f"S238.C7.{letter} s234 group row present exactly once",
          len(mrows) == 1, f"found {len(mrows)}")
    if len(mrows) == 1:
        pub_list = [x.strip().strip("'") for x in mrows[0].group(2).split(",")]
        check(f"S238.C8.{letter} re-derived letter group == s234 group row",
              pub_list == groups[letter],
              f"got {groups[letter]} pub {pub_list}")
mpool = [RE_S234_POOLED.match(l) for l in s234_lines]
mpool = [m for m in mpool if m]
check("S238.C9 s234 pooled rows present 2/2",
      {m.group(1) for m in mpool} == {"a", "b"}, f"{[m.group(1) for m in mpool]}")

# pooled group shares + pair census + W_in/W_out at the reading cell
gp128 = {}
for letter in ("a", "b"):
    c = Counter()
    for label in groups[letter]:
        c.update(win[label][sidx]["cnt"])
    gp128[letter] = shares(c, support128)
    for m in mpool:
        if m.group(1) == letter:
            mine = share_rows(gp128[letter]).split()
            check(f"S238.C10.{letter} re-derived pooled reading-cell share "
                  f"row == s234 pooled row",
                  mine == m.group(2).split(),
                  f"got {mine} pub {m.group(2).split()}")

order = [w[0] for w in WINDOWS]
ws128 = {label: shares(win[label][sidx]["cnt"], support128)
         for label in order}
pairs = [(x, y) for i, x in enumerate(order) for y in order[i + 1:]]
within = [(l1(ws128[x], ws128[y]), x, y) for x, y in pairs
          if (x in groups["a"]) == (y in groups["a"])]
between = [(l1(ws128[x], ws128[y]), x, y) for x, y in pairs
           if (x in groups["a"]) != (y in groups["a"])]
win_a = [p for p in within if p[1] in groups["a"]]
win_b = [p for p in within if p[1] in groups["b"]]
mpc = [RE_S234_PAIRCENSUS.match(l) for l in s234_lines]
mpc = [m for m in mpc if m]
check("S238.C11 s234 pair-census row present exactly once", len(mpc) == 1)
if len(mpc) == 1:
    check("S238.C12 re-derived pair counts == s234 pair census row",
          (len(win_a), len(win_b), len(between))
          == tuple(int(mpc[0].group(i)) for i in (1, 2, 3)),
          f"got {(len(win_a), len(win_b), len(between))}")
w_in_p = max(within, key=lambda t: t[0])
w_in_v = w_in_p[0]
w_out_p = min(between, key=lambda t: t[0])
w_out_v = w_out_p[0]
mwi = [RE_S234_WIN.match(l) for l in s234_lines]
mwi = [m for m in mwi if m]
mwo = [RE_S234_WOUT.match(l) for l in s234_lines]
mwo = [m for m in mwo if m]
check("S238.C13 s234 W_in/W_out rows present 2/2",
      len(mwi) == 1 and len(mwo) == 1, f"{len(mwi)}/{len(mwo)}")
if len(mwi) == 1:
    check("S238.C14 re-derived W_in (value + pair) == s234 W_in row",
          (f"{w_in_v:.4f}", w_in_p[1], w_in_p[2])
          == (mwi[0].group(1), mwi[0].group(2), mwi[0].group(3)),
          f"got {w_in_v:.4f} ({w_in_p[1]} vs {w_in_p[2]}) "
          f"pub {mwi[0].group(1)} ({mwi[0].group(2)} vs {mwi[0].group(3)})")
if len(mwo) == 1:
    check("S238.C15 re-derived W_out (value + pair) == s234 W_out row",
          (f"{w_out_v:.4f}", w_out_p[1], w_out_p[2])
          == (mwo[0].group(1), mwo[0].group(2), mwo[0].group(3)),
          f"got {w_out_v:.4f} ({w_out_p[1]} vs {w_out_p[2]}) "
          f"pub {mwo[0].group(1)} ({mwo[0].group(2)} vs {mwo[0].group(3)})")
mvv = [RE_S234_VERDICT.match(l) for l in s234_lines]
mvv = [m for m in mvv if m]
check("S238.C16 s234 SHAPES SEPARATE verdict row present", len(mvv) == 1)
if len(mvv) == 1:
    check("S238.C17 re-derived verdict arithmetic == s234 verdict row",
          (f"{w_out_v:.4f}", f"{w_in_v:.4f}")
          == (mvv[0].group(1), mvv[0].group(2)),
          f"got ({w_out_v:.4f}, {w_in_v:.4f})")
check("S238.C18 reading-cell letters re-derived (m vs band) == the "
      "committed s234 group split",
      (groups["a"], groups["b"]) == (["s158", "s185", "s197"],
                                     ["s169", "s209", "act-rd1",
                                      "act-rd2", "act-rd3", "act-rd4"]))

# ---- the cross-cell extent (the row's own content; REPORT only) ----
P()
P("3. THE CROSS-CELL EXTENT (REPORT ONLY -- the s234 rule applied")
P("   per cell as a supplementary reading; PATTERN-LEVEL; the only")
P("   binding rows are section 2's):")
P("   idx  (op,wg,forced)       m_a  m_b   D_groups  W_in     W_out"
  "    SEP   D_shift1  top1_a  top1_b")
extent = {}
for idx in ok_cells:
    support = sorted({v for label, *_ in WINDOWS
                      for v in win[label][idx]["cnt"]})
    ws = {label: shares(win[label][idx]["cnt"], support)
          for label in order}
    gp = {}
    for letter in ("a", "b"):
        c = Counter()
        for label in groups[letter]:
            c.update(win[label][idx]["cnt"])
        gp[letter] = shares(c, support)
    d_groups = l1(gp["a"], gp["b"])
    within_c = [(l1(ws[x], ws[y]), x, y) for x, y in pairs
                if (x in groups["a"]) == (y in groups["a"])]
    between_c = [(l1(ws[x], ws[y]), x, y) for x, y in pairs
                 if (x in groups["a"]) != (y in groups["a"])]
    w_in_c = max(within_c)
    w_out_c = min(between_c)
    # shape-vs-shift: (b) pooled translated +1 tick
    c_a = Counter()
    for label in groups["a"]:
        c_a.update(win[label][idx]["cnt"])
    c_b_shift = Counter()
    for label in groups["b"]:
        for v, n in win[label][idx]["cnt"].items():
            c_b_shift[v + 1] += n
    support_s = sorted(set(support) | set(c_b_shift))
    d_shift = l1(shares(c_a, support_s), shares(c_b_shift, support_s))
    top1_a = max(gp["a"].values())
    top1_b = max(gp["b"].values())
    sep = w_out_c[0] > w_in_c[0]
    extent[idx] = dict(d_groups=d_groups, w_in=w_in_c, w_out=w_out_c,
                       sep=sep, d_shift=d_shift, gp=gp, support=support)
    desc = f"({cell_map[idx][2]},{cell_map[idx][3]},{cell_map[idx][4]})"
    P(f"   {idx:3d}  {desc:20s} {statistics.median([win[l][idx]['m'] for l in groups['a']]):3.0f}"
      f"  {statistics.median([win[l][idx]['m'] for l in groups['b']]):3.0f}"
      f"   {d_groups:8.4f}  {w_in_c[0]:7.4f}  {w_out_c[0]:7.4f}"
      f"   {'YES' if sep else 'no ':3s}  {d_shift:8.4f}"
      f"  {top1_a:6.2f}  {top1_b:6.2f}")

P()
P("   per-cell group pooled share rows (the extent's own shapes):")
for idx in ok_cells:
    desc = f"({cell_map[idx][2]},{cell_map[idx][3]},{cell_map[idx][4]})"
    for letter in ("a", "b"):
        P(f"   idx={idx:2d} {desc:20s} ({letter}) pooled: "
          f"{share_rows(extent[idx]['gp'][letter])}")
P()
P("   per-window pooled medians at every cell (gpu_ticks):")
P("   cell " + " ".join(f"{label:>8s}" for label in order))
for idx in ok_cells:
    P(f"   {idx:4d} " + " ".join(f"{win[label][idx]['m']:8.1f}"
                                 for label in order))
P()
P("   SHAPE-VS-SHIFT rows (REPORT; the pure additive-shift account")
P("   predicts D_shift1 <= W_in at each cell):")
for idx in ok_cells:
    e = extent[idx]
    account = ("consistent" if e["d_shift"] <= e["w_in"][0]
               else "REFUTED at this cell")
    P(f"   idx={idx:2d} D_groups={e['d_groups']:.4f} "
      f"D_shift1={e['d_shift']:.4f} W_in={e['w_in'][0]:.4f} -> "
      f"pure additive-shift account {account}")
shift_refuted = [idx for idx in ok_cells
                 if extent[idx]["d_shift"] > extent[idx]["w_in"][0]]

# ---- the host_ns channel (REPORT; no rule applied) ----
P()
P("4. THE host_ns CHANNEL (REPORT ONLY -- a different instrument")
P("   channel, CLOCK_MONOTONIC submit->completion; NO criterion")
P("   applied here -- descriptive rows only):")
P("   idx  (op,wg,forced)      host_m_a  host_m_b   D_groups_host")
for idx in ok_cells:
    support_h = sorted({v for label, *_ in WINDOWS
                        for v in win[label][idx]["host_cnt"]})
    gph = {}
    for letter in ("a", "b"):
        c = Counter()
        for label in groups[letter]:
            c.update(win[label][idx]["host_cnt"])
        gph[letter] = shares(c, support_h)
    desc = f"({cell_map[idx][2]},{cell_map[idx][3]},{cell_map[idx][4]})"
    P(f"   {idx:3d}  {desc:20s}"
      f" {statistics.median([win[l][idx]['host_med'] for l in groups['a']]):9.1f}"
      f" {statistics.median([win[l][idx]['host_med'] for l in groups['b']]):9.1f}"
      f"   {l1(gph['a'], gph['b']):8.4f}")
P()
P("   per-window pooled host_ns medians at every cell:")
P("   cell " + " ".join(f"{label:>8s}" for label in order))
for idx in ok_cells:
    P(f"   {idx:4d} " + " ".join(f"{win[label][idx]['host_med']:8.1f}"
                                 for label in order))

# ---- the constraint verdict ----
sep_cells = [idx for idx in ok_cells if extent[idx]["sep"]]
P()
P("5. THE EXTENT VERDICT (the row's answer; PATTERN-LEVEL):")
P(f"   SEPARATE at {len(sep_cells)} of {len(ok_cells)} pipeline-ok "
  f"cells under the s234 rule")
P(f"   (W_out > W_in at every separating cell; the reading cell idx="
  f"{sidx} is one of them).")
if len(sep_cells) == len(ok_cells):
    P("   EXTENT ROW: WHOLE-STREAM -- the (a)/(b) sample-shape")
    P("   difference is NOT confined to the reading cell; it acts on")
    P("   every recorded cell of the c2 dispatch stream (2 workgroup")
    P("   sizes x 3 ops x 3 non-failed forced widths, 18/18 cells).")
    P("   A cell-/kernel-LOCAL cause is ruled out as the locus.")
elif len(sep_cells) == 1 and sidx in sep_cells:
    P("   EXTENT ROW: CELL-LOCAL -- separation confined to the")
    P("   reading cell; a whole-stream cause is ruled out as the")
    P("   locus.")
else:
    P("   EXTENT ROW: MIXED -- the separating cells are the rows")
    P(f"   above ({sorted(sep_cells)}); the locus constraint is the")
    P("   named set, neither pure CELL-LOCAL nor pure WHOLE-STREAM.")
P(f"   SHAPE, NOT JUST SHIFT: the pure additive-shift account is")
P(f"   REFUTED at {len(shift_refuted)} of {len(ok_cells)} cells")
P(f"   (D_shift1 > W_in there); the (b) shape is sharper than the")
P(f"   (a) shape at the reading cell (top1 {gp128['b'][max(gp128['b'], key=gp128['b'].get)]:.4f}% vs "
  f"{gp128['a'][max(gp128['a'], key=gp128['a'].get)]:.4f}%).")
P("   CAUSE DICHOTOMY: NOT DECIDED -- both surviving candidates are")
P("   whole-stream states (an execution-time state of the whole")
P("   dispatch stream vs an instrument/timestamp-quantization state")
P("   of the whole recording).  The RECORDED instrument/timestamp")
P("   metadata is byte-identical across all 27 runs of both letter")
P("   groups (section 1: 8 header lines, timestampPeriod=52.083")
P("   included) -- so the dichotomy's instrument side, if true, is")
P("   an UNRECORDED state; an unrecorded execution-time state is")
P("   equally live.  The CAUSE of the sample-shape difference stays")
P("   UNMEASURED (this row constrains its LOCUS only); the")
P("   underlying-instrument-state COUNT stays outside (s220 1(b)).")

P()
P("6. THREE-STATE / RULE 4 / BAR (unchanged): every sample value")
P("   above is a named run's landed MEASURED QUANTITY on")
P("   aiueos-6600hs (Intel BMG G31) under the named instrument,")
P("   RE-PARSED from committed run-log bytes -- this slice measures")
P("   NOTHING new on hardware (no runs, no builds, NO GO stamp); the")
P("   share/distance arithmetic is DERIVED; the accelerator-targets")
P("   workgroup rows stay exactly as ADR-0358 left them (:measured?")
P("   false rows remain provisional -- NOT optimization evidence);")
P("   NO vendor optimization exists for Intel (or for any vendor)")
P("   and none follows from this constraint.  RULE 4 unchanged:")
P("   NOTHING MOVES; the committed bracket stays EXACTLY (254,923,")
P("   255,045]; L9 binds at n=254,984 (C2 (c), D3 (v)); the MID-ONLY")
P("   NARROWING CLAIM stays SUSPENDED.  BAR NON-INTERFERENCE: NO")
P("   settle-bar-ledger line, NO day-slot consumption; the bar's")
P("   SETTLED INTERMEDIATE/MIXED verdict unmoved.")

P()
P("7. NAMED, NOT HIDDEN:")
P("   (a) the s234 report's own prose counts 'the 24 committed run")
P("   logs'/'across all 24 runs' while its checks enumerate 27 runs")
P("   (9 windows x k=3; 27 'run integrity clean' rows in the")
P("   committed bytes) -- a prose-count artifact named here, no")
P("   value affected; this row's census says 27.")
P("   (b) the per-cell rule application is SUPPLEMENTARY REPORT --")
P("   the s234 criterion was frozen for the reading cell; only the")
P("   reading-cell rows (section 2) bind.")
P("   (c) the host_ns channel carries NO criterion here (its sample")
P("   shape confrontation needs its own frozen criterion).")
P("   (d) OUTSIDE this universe (named, not hidden): the s237 kernel-")
P("   variant arms (iter1/iter3/iter8/itervc8 spvs) and the s235")
P("   supplementary arms (anv-tsstage bb-b2/tt-b2) -- no extent row")
P("   covers them here.")

P()
P("8. NOT DONE (s239 carries exactly this list): the s216 identity")
P("   hazard's remaining residuals (standing, not queued): the CAUSE")
P("   of the sample-shape difference stays UNMEASURED and UNDECIDED")
P("   (this row CONSTRAINED its locus to whole-stream states; a")
P("   cause-resolution act needs new hardware runs, each with its own")
P("   freeze -- standing, not queued); the underlying-instrument-")
P("   state COUNT stays outside (s220 1(b)); at N=75 the s235/s237")
P("   classifications carry NO noise model and near-neither")
P("   prevalence needs higher-N readings -- new hardware runs, each")
P("   with its own freeze (standing, not queued); standing, not")
P("   queued: any further counted-day slot (each needs its own")
P("   freeze) and the cross-day tail-movement row.  QUEUED for")
P("   s239: the host_ns channel's per-sample shape confrontation at")
P("   the reading cell under its own criterion frozen before the")
P("   numbers (this row reports the host channel descriptively")
P("   only).  (JUN-55, JUN-59; Linear tracking JUN-499)")

P()
P(f"# crosscell-extent s238 (crosscell-extent-s238.py): "
  f"{CHECKS['ok']} ok / {CHECKS['failed']} failed")
print("\n".join(OUT))
sys.exit(0 if CHECKS["failed"] == 0 else 1)
