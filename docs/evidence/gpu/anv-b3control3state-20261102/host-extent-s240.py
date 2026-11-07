#!/usr/bin/env python3
"""host-extent-s240.py -- THE HOST_NS CHANNEL'S CROSS-CELL SHAPE
EXTENT UNDER THE SAME FROZEN QUANTIZATION (amu-gpu session 240;
the s239 carry-forward's QUEUED row "the host_ns channel's cross-
cell shape extent under the same frozen quantization (this row's
reading-cell confrontation extended over the 18 pipeline-ok cells,
supplementary REPORT)" TAKEN AS ITS ROW).

THE ROW: the s239 confrontation decided the host_ns per-sample
shape question at ONE cell -- the c2 reading cell (sum,128,S=16) --
under the host channel's own criterion frozen before its numbers:
SHAPES DO NOT SEPARATE there (W_out 10.1667 <= W_in 39.7917),
width-robust at all 7 frozen widths.  Whether the host channel
carries a letter-group shape split at any OTHER recorded cell is
UNCHECKED from committed bytes -- and it completes the second-
instrument-channel constraint of the s216 cause dichotomy at
stream scope (the s238 row already fixed the gpu_ticks extent:
SEPARATE at 18 of 18 pipeline-ok cells).

THE EXTENT CRITERION (the s239 frozen host criterion applied per
cell, UNCHANGED -- no new frozen choice; the queue prescribes the
extension): at each pipeline-ok cell c, quantize every window's
host_ns samples at c to bin indices b = host_ns // 1000 ns (the
s239 primary quantization); per-window share vectors s_w,c over
the union support of occupied bin indices at c (percent);
W_in(c) = max L1 over same-letter window pairs, W_out(c) = min L1
over opposite-letter window pairs; the cell SEPARATES iff
W_out(c) > W_in(c).  The LETTERS are the gpu_ticks letters (the
fixed split, re-derived at the reading cell and BOUND to the
committed s234 rows) -- the host channel does not get its own
letters, at any cell.  ROBUSTNESS FAMILY (the s239 pre-frozen
family, unchanged; REPORT only -- every width reported at every
cell whatever it shows): BIN in (100, 250, 500, 2000, 5000,
10000) ns.  RAW-SUPPORT SUPPLEMENTARY (REPORT only): the same
W_in/W_out arithmetic on raw host_ns support at each cell (the
s238 D_groups_host machinery extended to window pairs).
EXTENT ROWS (reported): NO-CELL (no host-channel letter-group
shape split at any pipeline-ok cell -- the (a)/(b) shape
difference is confined to the gpu_ticks channel stream-wide under
the frozen quantization) / SOME-CELL (the named separating set)
/ ALL-CELLS (the (a)/(b) shape difference replicates on the host
channel stream-wide).  PATTERN-LEVEL ONLY (s218 2(e)): NO p-value,
NO test statistic, NO probability claim.

BINDS (fail-closed; the per-cell confrontation itself is
SUPPLEMENTARY REPORT and never fails the run):
  - the reading-cell rows re-derived here must EQUAL the committed
    s239 report rows (host-shape-s239-run1.txt): the 9 per-window
    host census rows, the union-support row, the pair census, the
    W_in/W_out/D_groups/verdict rows, the 7 robustness rows and
    the raw-support rows;
  - the per-cell host descriptive rows re-derived here must EQUAL
    the committed s238 report rows (crosscell-extent-s238-run1.txt)
    at ALL 18 pipeline-ok cells: the 18 host-table rows
    (host_m_a / host_m_b / D_groups_host) and the 18 rows of the
    per-window host-median table (9 values each);
  - the letter split re-derived here (reading-cell gpu_ticks m vs
    the committed floor band) must EQUAL the committed s234 group
    rows;
  - the gpu_ticks extent count re-derived here must EQUAL the
    committed s238 extent row (SEPARATE at 18 of 18).

UNIVERSE (the s234/s238/s239 universe unchanged): the nine deep-
pooling-era own readings whose raw run logs are COMMITTED (cuts
s158/s169/s185/s197/s209 + the s225 act's four readings; 27 run
logs, 9 windows x k=3), at EVERY pipeline-ok cell of the c2
dispatch stream (18 cells; the 6 forced=8 cells are pipeline=FAIL
with no samples, named and excluded).  OUTSIDE (named, not
hidden): the s237 kernel-variant arms (iter1/iter3/iter8/itervc8
spvs) and the s235 supplementary arms (anv-tsstage bb-b2/tt-b2).

Reads ONLY committed bytes (fail-closed; any parse anomaly is an
immediate abort = failed run):
  - docs/evidence/gpu/anv-b3bisect{15..19}-*/run-c2-r0{1..3}.txt.gz
    and docs/evidence/gpu/anv-b3control3state-20261102/run-
    rd{1..4}-c2-r0{1..3}.txt.gz (through gzip).
  - identity-shape-s234-run1.txt (the letter-group rows).
  - crosscell-extent-s238-run1.txt (the per-cell host descriptive
    rows + the gpu_ticks extent row).
  - host-shape-s239-run1.txt (the reading-cell host confrontation
    rows).
  - anv-b3bisect7-20261027/derivation-census-s27.txt (the floor
    band pin).

Writes NOTHING.  Prints the report to stdout, nothing to stderr on
success.  Exit 0 iff every CHECK is ok.

CHECKS vs REPORTS (the honesty split): PARSE anomalies and BIND
mismatches (missing file, header/cell-map divergence, run-
integrity problems, any bound row disagreeing with the committed
s234/s238/s239 bytes) are CHECKS and fail the run; the cross-cell
confrontation tables, the per-cell robustness family, the raw-
support rows, the extent verdict and the interpretation rows are
REPORTS and never fail the run.

THREE-STATE: every sample value below is a named run's landed
MEASURED QUANTITY (its own hardware runs on aiueos-6600hs, Intel
BMG G31, under the named instrument), RE-PARSED here from
committed run-log bytes -- this script measures NOTHING new on
hardware (no runs, no builds, NO GO stamp) and no value here is a
measurement of this tick; the share/distance arithmetic is DERIVED
(labelled).  The CAUSE of the sample-shape difference stays
UNMEASURED and UNDECIDED (this row completes the second-
instrument-channel extent constraint only); the underlying-
instrument-state COUNT stays outside (s220 1(b) binds).  RULE 4
unchanged: NOTHING MOVES; the committed bracket stays EXACTLY
(254,923, 255,045]; the accelerator-targets workgroup rows stay
exactly as ADR-0358 left them (:measured? false rows remain
provisional -- NOT optimization evidence); NO vendor optimization
exists for Intel (or for any vendor) and none follows from this
extent row.
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

# THE FROZEN HOST CRITERION (the s239 choice, UNCHANGED here):
# primary quantization width and the pre-frozen robustness family
# (REPORT only).
BIN = 1000
ROBUST_BINS = (100, 250, 500, 2000, 5000, 10000)

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
ORDER = [w[0] for w in WINDOWS]

# The gpu_ticks letter split (the s234 group rows; RE-DERIVED from
# m vs the committed floor band and BOUND below).
GROUPS_PIN = (["s158", "s185", "s197"],
              ["s169", "s209", "act-rd1", "act-rd2", "act-rd3",
               "act-rd4"])

S234_REPORT = HERE / "identity-shape-s234-run1.txt"
S238_REPORT = HERE / "crosscell-extent-s238-run1.txt"
S239_REPORT = HERE / "host-shape-s239-run1.txt"
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
# -- committed s234 report row forms (the letter-group BINDS) --
RE_S234_GROUP = re.compile(r"^     \(([ab])\): \[('.*')\]$")
# -- committed s238 report row forms (the per-cell host BINDS and
#    the gpu_ticks extent row) --
S238_HOSTTAB_ANCHOR = ("   idx  (op,wg,forced)      host_m_a  "
                       "host_m_b   D_groups_host")
S238_HOSTMED_ANCHOR = "   per-window pooled host_ns medians at every cell:"
RE_S238_HOSTTAB_ROW = re.compile(
    r"^ +(\d+)  \((\w+),(\d+),(\w+)\) +([0-9]+\.[0-9]) +([0-9]+\.[0-9]) "
    r"+([0-9]+\.[0-9]{4})$")
RE_S238_HOSTMED_ROW = re.compile(r"^ +(\d+) ((?:[0-9.]+ +){8}[0-9.]+)$")
RE_S238_EXTENT = re.compile(
    r"^   SEPARATE at (\d+) of (\d+) pipeline-ok cells "
    r"under the s234 rule$")
# -- committed s239 report row forms (the reading-cell BINDS) --
RE_S239_CENSUS = re.compile(
    r"^ {5}(\S+)\s+N=(\d+) host_m=([\d.]+) host_mad=([\d.]+) "
    r"bins=(\d+) top1 (\d+):([\d.]+)%$")
RE_S239_SUPPORT = re.compile(
    r"^ {5}(\d+) occupied bins \(ns range (\d+)\.\.(\d+)\)$")
RE_S239_PAIRCENSUS = re.compile(
    r"^   pair census: within-a (\d+), within-b (\d+), between (\d+)$")
RE_S239_WIN = re.compile(
    r"^   W_in  = max within-group L1 = ([\d.]+) \((\S+) vs (\S+)\)$")
RE_S239_WOUT = re.compile(
    r"^   W_out = min between-group L1 = ([\d.]+) \((\S+) vs (\S+)\)$")
RE_S239_DGROUPS = re.compile(
    r"^   D_groups = L1 between pooled group shares = ([\d.]+)$")
RE_S239_VERDICT = re.compile(
    r"^   SHAPES (DO NOT SEPARATE|SEPARATE) "
    r"\(W_out ([\d.]+) (<=|>) W_in ([\d.]+)\)\.$")
S239_ROBUST_ANCHOR = "   BIN ns  bins  W_in     W_out    D_groups  verdict"
RE_S239_ROBUST = re.compile(
    r"^\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+"
    r"(SEPARATE|no)(?:\s+\(PRIMARY\))?\s*$")
RE_S239_RAW_WIN = re.compile(
    r"^   W_in\(raw\)  = ([\d.]+) \((\S+) vs (\S+)\)$")
RE_S239_RAW_WOUT = re.compile(
    r"^   W_out\(raw\) = ([\d.]+) \((\S+) vs (\S+)\)$")
RE_S239_RAW_DG = re.compile(
    r"^   D_groups\(raw\) = ([\d.]+) \(bound in section 4\)$")

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


def top6_rows(sh):
    tops = sorted(sh.items(), key=lambda kv: (-kv[1], kv[0]))[:6]
    return "  ".join(f"{k}:{v:.4f}" for k, v in tops)


# ------------------------------------------------------------------ report
P("host-extent-s240.py -- THE HOST_NS CHANNEL'S CROSS-CELL SHAPE")
P("EXTENT UNDER THE SAME FROZEN QUANTIZATION (amu-gpu s240; the")
P("s239 carry-forward's QUEUED row -- the reading-cell host")
P("confrontation extended over the 18 pipeline-ok cells -- taken")
P("as its row).")
P()
P("1. THE EXTENT CRITERION (the s239 frozen host criterion")
P("   applied per cell, UNCHANGED -- no new frozen choice): at")
P("   each pipeline-ok cell c, bin index b = host_ns // "
  f"{BIN} ns")
P(f"   (the s239 primary quantization, {BIN} ns); per-window")
P("   share vectors over the union support of occupied bin")
P("   indices at c (percent); W_in(c) = max L1 over same-letter")
P("   window pairs, W_out(c) = min L1 over opposite-letter")
P("   window pairs; the cell SEPARATES iff W_out(c) > W_in(c).")
P("   Letters are the gpu_ticks letters (the fixed split,")
P("   re-derived at the reading cell and BOUND to the committed")
P("   s234 rows) -- the host channel does not get its own")
P("   letters, at any cell.  ROBUSTNESS FAMILY (the s239 pre-")
P("   frozen family, unchanged; REPORT only, every width")
P(f"   reported at every cell whatever it shows): BIN in "
  f"{(BIN,) + ROBUST_BINS} ns.")
P("   RAW-SUPPORT SUPPLEMENTARY (REPORT only): the same")
P("   W_in/W_out arithmetic on raw host_ns support at each cell.")
P("   EXTENT ROWS: NO-CELL (no host-channel letter-group shape")
P("   split at any pipeline-ok cell -- the (a)/(b) shape")
P("   difference confined to the gpu_ticks channel stream-wide")
P("   under the frozen quantization) / SOME-CELL (the named")
P("   separating set) / ALL-CELLS (the (a)/(b) shape difference")
P("   replicates on the host channel stream-wide).")
P("   PATTERN-LEVEL ONLY (s218 2(e)): NO p-value, NO test")
P("   statistic, NO probability claim.")
P("UNIVERSE: the s234/s238/s239 nine-window universe unchanged")
P("(27 committed c2 run logs), at EVERY pipeline-ok cell (18;")
P("the 6 forced=8 cells are pipeline=FAIL, named and excluded).")
P("OUTSIDE (named, not hidden): the s237 kernel-variant arms")
P("(iter1/iter3/iter8/itervc8 spvs) and the s235 supplementary")
P("arms (anv-tsstage bb-b2/tt-b2).")
P()

# ---- band / reference pins from the committed s27 census ----
s27 = S27.read_text()
m27 = RE_S27.search(s27)
assert m27, "s27 census row"
band = (int(m27.group(2)), int(m27.group(3)))
c2pin, c8ref = int(m27.group(1)), int(m27.group(4).replace(",", ""))
check("S240.A1 s27 census parse == pins (c2 31, band 31..32, c8 32915)",
      (c2pin, band, c8ref) == (C2_PIN, FLOOR_BAND, C8_REF),
      f"got {(c2pin, band, c8ref)}")

# ---- the 27 committed run logs ----
P()
P("2. THE RUN-LOG CENSUS (every sample RE-PARSED from committed")
P("   run-log bytes; m = pooled sample median gpu_ticks over k=3")
P("   runs x R rounds at the cell; host_m = pooled sample median")
P("   host_ns at the cell):")
runs = {}
for label, sess, kind, d, pat in WINDOWS:
    for nn in (1, 2, 3):
        name = pat.format(nn)
        path = GPU / d / name
        assert path.exists(), f"RUN LOG MISSING: {path}"
        runs[(label, nn)] = load_run(path)
check("S240.A2 header identity across all 27 runs",
      len({r["header"] for r in runs.values()}) == 1)
check("S240.A3 cell-map identity across all 27 runs",
      len({r["cell_map"] for r in runs.values()}) == 1)
for (label, nn), r in sorted(runs.items()):
    check(f"S240.B{label}-r{nn:02d} run integrity clean",
          not r["problems"], "; ".join(r["problems"]))
ok_cells = runs[(WINDOWS[0][0], 1)]["ok_cells"]
fail_cells = runs[(WINDOWS[0][0], 1)]["fail_cells"]
sidx = runs[(WINDOWS[0][0], 1)]["s128"]
check("S240.A4 ok/fail cell sets uniform (18 ok incl. the reading "
      "cell idx=1 (sum,128,S=16), 6 FAIL forced=8)",
      all(r["ok_cells"] == ok_cells and r["fail_cells"] == fail_cells
          for r in runs.values())
      and len(ok_cells) == 18 and len(fail_cells) == 6
      and sidx == 1 and sidx in ok_cells)
P()
P("   the header block (8 lines, identical across all 27 runs --")
P("   the RECORDED instrument/timestamp metadata, byte-compared):")
for l in runs[(WINDOWS[0][0], 1)]["header"]:
    P(f"     {l}")
P()
P("   the 6 pipeline-FAIL cells (no samples in any window; named")
P("   and EXCLUDED from the extent tables below):")
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
        hm_ = statistics.median(hs)
        per[idx] = dict(
            N=len(xs), m=m_,
            mad=statistics.median([abs(x - m_) for x in xs]),
            cnt=Counter(xs), host=hs, host_med=hm_,
            host_mad=statistics.median([abs(x - hm_) for x in hs]),
            host_cnt=Counter(hs))
    win[label] = per

P()
P("   per-cell sample counts and letter-uniformity (CHECKS):")
for idx in ok_cells:
    nbad = [l for l in ORDER if win[l][idx]["N"] != 3 * R]
    check(f"S240.E1.{idx:02d} host/gpu sample counts == 3R at all 9 "
          f"windows", not nbad, f"{nbad}")
mis = []
for idx in ok_cells:
    for label in ORDER:
        inb = band[0] <= win[label][idx]["m"] <= band[1]
        if inb != (label in GROUPS_PIN[0]):
            mis.append((idx, label, win[label][idx]["m"]))
check("S240.E2 letter split uniform at every cell (every (a) window "
      "pools m in the floor band, every (b) window pools m outside "
      "it, at all 18 cells)",
      not mis, f"{mis}")

# ---- letters: s234 group rows BIND ----
P()
P("3. LETTER BINDS (the gpu_ticks letters re-derived from reading-")
P("   cell m vs the committed floor band must EQUAL the committed")
P("   s234 group rows -- fail-closed; the host confrontation at")
P("   every cell below runs on this fixed split):")
groups = {"a": [], "b": []}
for label in ORDER:
    letter = "a" if band[0] <= win[label][sidx]["m"] <= band[1] else "b"
    groups[letter].append(label)
s234_bytes = S234_REPORT.read_bytes()
P(f"   s234 report pin: {len(s234_bytes)} bytes sha256 "
  f"{hashlib.sha256(s234_bytes).hexdigest()}")
s234_lines = s234_bytes.decode().splitlines()
grp_rows = {}
for l in s234_lines:
    mg = RE_S234_GROUP.match(l)
    if mg:
        grp_rows[mg.group(1)] = [x.strip().strip("'")
                                 for x in mg.group(2).split(",")]
check("S240.C1 s234 letter-group rows present 2/2",
      set(grp_rows) == {"a", "b"}, f"{sorted(grp_rows)}")
check("S240.C2 re-derived letters (reading-cell m vs band) == s234 "
      "group rows == the fixed pin",
      grp_rows.get("a") == groups["a"] == GROUPS_PIN[0]
      and grp_rows.get("b") == groups["b"] == GROUPS_PIN[1],
      f"derived {groups} s234 {grp_rows}")
P(f"   letters (fixed at every cell): (a) {groups['a']} / "
  f"(b) {groups['b']}")

# ---- reading-cell confrontation BINDS to the committed s239 report ----
P()
P("4. READING-CELL host_ns BINDS (the committed s239 confrontation")
P("   rows below are RE-DERIVED here from the run logs and must")
P("   EQUAL the committed report bytes host-shape-s239-run1.txt --")
P("   fail-closed; this binds the per-cell machinery at the reading")
P("   cell to the committed record):")
s239_bytes = S239_REPORT.read_bytes()
P(f"   s239 report pin: {len(s239_bytes)} bytes sha256 "
  f"{hashlib.sha256(s239_bytes).hexdigest()}")
s239_lines = s239_bytes.decode().splitlines()


def shape_at(idx, binw):
    """The frozen criterion arithmetic at cell idx and quantization
    width binw (the s239 shape_at machinery, per cell)."""
    wb = {label: Counter(v // binw for v in win[label][idx]["host"])
          for label in ORDER}
    support = sorted({b for label in ORDER for b in wb[label]})
    ws = {label: shares(wb[label], support) for label in ORDER}
    gp = {}
    for letter in ("a", "b"):
        c = Counter()
        for label in groups[letter]:
            c.update(wb[label])
        gp[letter] = shares(c, support)
    within_c = [(l1(ws[x], ws[y]), x, y)
                for i, x in enumerate(ORDER) for y in ORDER[i + 1:]
                if (x in groups["a"]) == (y in groups["a"])]
    between_c = [(l1(ws[x], ws[y]), x, y)
                 for i, x in enumerate(ORDER) for y in ORDER[i + 1:]
                 if (x in groups["a"]) != (y in groups["a"])]
    w_in_c = max(within_c, key=lambda t: t[0])
    w_out_c = min(between_c, key=lambda t: t[0])
    return dict(wb=wb, support=support, ws=ws, gp=gp,
                d_groups=l1(gp["a"], gp["b"]),
                w_in=w_in_c, w_out=w_out_c,
                sep=w_out_c[0] > w_in_c[0],
                within=within_c, between=between_c)


def raw_at(idx):
    """The raw-support supplementary arithmetic at cell idx (the
    s239 section-6 machinery, per cell)."""
    support_raw = sorted({v for label in ORDER
                          for v in win[label][idx]["host_cnt"]})
    ws_raw = {label: shares(win[label][idx]["host_cnt"], support_raw)
              for label in ORDER}
    within_r = [(l1(ws_raw[x], ws_raw[y]), x, y)
                for i, x in enumerate(ORDER) for y in ORDER[i + 1:]
                if (x in groups["a"]) == (y in groups["a"])]
    between_r = [(l1(ws_raw[x], ws_raw[y]), x, y)
                 for i, x in enumerate(ORDER) for y in ORDER[i + 1:]
                 if (x in groups["a"]) != (y in groups["a"])]
    gp = {}
    for letter in ("a", "b"):
        c = Counter()
        for label in groups[letter]:
            c.update(win[label][idx]["host_cnt"])
        gp[letter] = shares(c, support_raw)
    return dict(support=support_raw,
                w_in=max(within_r, key=lambda t: t[0]),
                w_out=min(between_r, key=lambda t: t[0]),
                d_groups=l1(gp["a"], gp["b"]))


primary = {idx: shape_at(idx, BIN) for idx in ok_cells}
raws = {idx: raw_at(idx) for idx in ok_cells}
robust = {idx: {binw: (primary[idx] if binw == BIN
                       else shape_at(idx, binw))
                for binw in (BIN,) + ROBUST_BINS}
          for idx in ok_cells}

# -- s239 census rows (9) --
pub_census = {}
for l in s239_lines:
    mc = RE_S239_CENSUS.match(l)
    if mc:
        pub_census[mc.group(1)] = mc
check("S240.C3 s239 per-window host census rows present 9/9",
      set(pub_census) == set(ORDER), f"{sorted(pub_census)}")
for label in ORDER:
    mc = pub_census.get(label)
    pr = primary[sidx]
    top1 = max(pr["wb"][label].items(), key=lambda kv: kv[1])
    mine = (str(win[label][sidx]["N"]),
            f"{win[label][sidx]['host_med']:.1f}",
            f"{win[label][sidx]['host_mad']:.1f}",
            str(len(pr["wb"][label])),
            str(top1[0] * BIN), f"{100.0 * top1[1] / win[label][sidx]['N']:.4f}")
    check(f"S240.C4.{label} re-derived reading-cell host census row == "
          f"s239 census row",
          mc is not None and mine == tuple(mc.group(i) for i in range(2, 8)),
          f"got {mine} pub "
          f"{tuple(mc.group(i) for i in range(2, 8)) if mc else None}")
# -- union-support row --
msup = [RE_S239_SUPPORT.match(l) for l in s239_lines]
msup = [m for m in msup if m]
check("S240.C5 s239 occupied-bins row present exactly once",
      len(msup) == 1, f"found {len(msup)}")
if len(msup) == 1:
    sup = primary[sidx]["support"]
    check("S240.C6 re-derived reading-cell occupied bins + ns range == "
          "s239 row",
          (str(len(sup)), str(sup[0] * BIN),
           str(sup[-1] * BIN + BIN - 1))
          == (msup[0].group(1), msup[0].group(2), msup[0].group(3)),
          f"got {(len(sup), sup[0] * BIN, sup[-1] * BIN + BIN - 1)} "
          f"pub {msup[0].groups()}")
# -- pair census --
mpc = [RE_S239_PAIRCENSUS.match(l) for l in s239_lines]
mpc = [m for m in mpc if m]
check("S240.C7 s239 pair-census row present exactly once",
      len(mpc) == 1, f"found {len(mpc)}")
if len(mpc) == 1:
    pr = primary[sidx]
    counts3 = (len([p for p in pr["within"] if p[1] in groups["a"]]),
               len([p for p in pr["within"] if p[1] in groups["b"]]),
               len(pr["between"]))
    check("S240.C8 re-derived pair counts == s239 pair census row",
          tuple(str(c) for c in counts3)
          == tuple(mpc[0].group(i) for i in (1, 2, 3)),
          f"got {counts3} pub {tuple(mpc[0].group(i) for i in (1, 2, 3))}")
# -- W_in / W_out / D_groups / verdict --
pr = primary[sidx]
mwi = [m for m in (RE_S239_WIN.match(l) for l in s239_lines) if m]
mwo = [m for m in (RE_S239_WOUT.match(l) for l in s239_lines) if m]
mdg = [m for m in (RE_S239_DGROUPS.match(l) for l in s239_lines) if m]
mvv = [m for m in (RE_S239_VERDICT.match(l) for l in s239_lines) if m]
check("S240.C9 s239 W_in/W_out/D_groups/verdict rows present 4/4",
      len(mwi) == 1 and len(mwo) == 1 and len(mdg) == 1 and len(mvv) == 1,
      f"{len(mwi)}/{len(mwo)}/{len(mdg)}/{len(mvv)}")
if len(mwi) == 1:
    check("S240.C10 re-derived reading-cell W_in (value + pair) == s239 row",
          (f"{pr['w_in'][0]:.4f}", pr["w_in"][1], pr["w_in"][2])
          == (mwi[0].group(1), mwi[0].group(2), mwi[0].group(3)),
          f"got {pr['w_in']} pub {mwi[0].groups()}")
if len(mwo) == 1:
    check("S240.C11 re-derived reading-cell W_out (value + pair) == s239 row",
          (f"{pr['w_out'][0]:.4f}", pr["w_out"][1], pr["w_out"][2])
          == (mwo[0].group(1), mwo[0].group(2), mwo[0].group(3)),
          f"got {pr['w_out']} pub {mwo[0].groups()}")
if len(mdg) == 1:
    check("S240.C12 re-derived reading-cell D_groups == s239 row",
          f"{pr['d_groups']:.4f}" == mdg[0].group(1),
          f"got {pr['d_groups']:.4f} pub {mdg[0].group(1)}")
if len(mvv) == 1:
    word = "SEPARATE" if pr["sep"] else "DO NOT SEPARATE"
    rel = ">" if pr["sep"] else "<="
    check("S240.C13 re-derived reading-cell verdict (wording + "
          "arithmetic) == s239 row",
          (word, f"{pr['w_out'][0]:.4f}", rel, f"{pr['w_in'][0]:.4f}")
          == (mvv[0].group(1), mvv[0].group(2), mvv[0].group(3),
              mvv[0].group(4)),
          f"got {(word, pr['w_out'][0], rel, pr['w_in'][0])} "
          f"pub {mvv[0].groups()}")
# -- robustness family (7 rows) --
rob_rows = {}
anchor = [i for i, l in enumerate(s239_lines)
          if l == S239_ROBUST_ANCHOR]
check("S240.C14 s239 robustness anchor present exactly once",
      len(anchor) == 1, f"found {len(anchor)}")
if len(anchor) == 1:
    i = anchor[0] + 1
    while i < len(s239_lines):
        mm = RE_S239_ROBUST.match(s239_lines[i])
        if not mm:
            break
        rob_rows[int(mm.group(1))] = mm
        i += 1
check("S240.C15 s239 robustness rows present 7/7",
      set(rob_rows) == set((BIN,) + ROBUST_BINS),
      f"{sorted(rob_rows)}")
for binw in (BIN,) + ROBUST_BINS:
    mm = rob_rows.get(binw)
    s = robust[sidx][binw]
    mine = (str(binw), str(len(s["support"])), f"{s['w_in'][0]:.4f}",
            f"{s['w_out'][0]:.4f}", f"{s['d_groups']:.4f}",
            "SEPARATE" if s["sep"] else "no")
    check(f"S240.C16.{binw} re-derived reading-cell robustness row == "
          f"s239 row",
          mm is not None and mine == tuple(mm.group(i) for i in range(1, 7)),
          f"got {mine} pub "
          f"{tuple(mm.group(i) for i in range(1, 7)) if mm else None}")
# -- raw-support rows --
rrw = [m for m in (RE_S239_RAW_WIN.match(l) for l in s239_lines) if m]
rro = [m for m in (RE_S239_RAW_WOUT.match(l) for l in s239_lines) if m]
rrd = [m for m in (RE_S239_RAW_DG.match(l) for l in s239_lines) if m]
check("S240.C17 s239 raw-support rows present 3/3",
      len(rrw) == 1 and len(rro) == 1 and len(rrd) == 1,
      f"{len(rrw)}/{len(rro)}/{len(rrd)}")
rw = raws[sidx]
if len(rrw) == 1:
    check("S240.C18 re-derived reading-cell W_in(raw) (value + pair) == "
          "s239 row",
          (f"{rw['w_in'][0]:.4f}", rw["w_in"][1], rw["w_in"][2])
          == (rrw[0].group(1), rrw[0].group(2), rrw[0].group(3)),
          f"got {rw['w_in']} pub {rrw[0].groups()}")
if len(rro) == 1:
    check("S240.C19 re-derived reading-cell W_out(raw) (value + pair) == "
          "s239 row",
          (f"{rw['w_out'][0]:.4f}", rw["w_out"][1], rw["w_out"][2])
          == (rro[0].group(1), rro[0].group(2), rro[0].group(3)),
          f"got {rw['w_out']} pub {rro[0].groups()}")
if len(rrd) == 1:
    check("S240.C20 re-derived reading-cell D_groups(raw) == s239 row",
          f"{rw['d_groups']:.4f}" == rrd[0].group(1),
          f"got {rw['d_groups']:.4f} pub {rrd[0].group(1)}")
P(f"   reading-cell rows bound: W_in {pr['w_in'][0]:.4f} "
  f"({pr['w_in'][1]} vs {pr['w_in'][2]}), W_out {pr['w_out'][0]:.4f} "
  f"({pr['w_out'][1]} vs {pr['w_out'][2]}), "
  f"{'SEPARATE' if pr['sep'] else 'DO NOT SEPARATE'}")

# ---- per-cell host descriptive rows BIND to the committed s238 report ----
P()
P("5. CROSS-CELL host_ns BINDS (the committed s238 descriptive")
P("   rows below are RE-DERIVED here from the run logs and must")
P("   EQUAL the committed report bytes crosscell-extent-s238-")
P("   run1.txt at ALL 18 pipeline-ok cells -- fail-closed; this")
P("   extends the s239 reading-cell bind to every cell):")
s238_bytes = S238_REPORT.read_bytes()
P(f"   s238 report pin: {len(s238_bytes)} bytes sha256 "
  f"{hashlib.sha256(s238_bytes).hexdigest()}")
s238_lines = s238_bytes.decode().splitlines()
anchors_t = [i for i, l in enumerate(s238_lines)
             if l == S238_HOSTTAB_ANCHOR]
anchors_m = [i for i, l in enumerate(s238_lines)
             if l == S238_HOSTMED_ANCHOR]
check("S240.D1 s238 host-table anchor present exactly once",
      len(anchors_t) == 1, f"found {len(anchors_t)}")
check("S240.D2 s238 host-median table anchor present exactly once",
      len(anchors_m) == 1, f"found {len(anchors_m)}")
tab_rows, med_rows = {}, {}
if len(anchors_t) == 1:
    i = anchors_t[0] + 1
    for _ in range(3):
        if RE_S238_HOSTTAB_ROW.match(s238_lines[i]):
            break
        i += 1
    while i < len(s238_lines):
        mm = RE_S238_HOSTTAB_ROW.match(s238_lines[i])
        if not mm:
            break
        tab_rows[int(mm.group(1))] = mm
        i += 1
    check("S240.D3 s238 host-table rows parse (18 pipeline-ok cells)",
          set(tab_rows) == set(ok_cells), f"{sorted(tab_rows)}")
if len(anchors_m) == 1:
    i = anchors_m[0] + 1
    for _ in range(3):
        if RE_S238_HOSTMED_ROW.match(s238_lines[i]):
            break
        i += 1
    while i < len(s238_lines):
        mm = RE_S238_HOSTMED_ROW.match(s238_lines[i])
        if not mm:
            break
        med_rows[int(mm.group(1))] = mm
        i += 1
    check("S240.D4 s238 host-median table rows parse (18 pipeline-ok "
          "cells)", set(med_rows) == set(ok_cells), f"{sorted(med_rows)}")

P()
P("   per-window pooled host_ns medians at every cell (RE-DERIVED;")
P("   must equal the committed s238 table rows above):")
P("   cell " + " ".join(f"{label:>8s}" for label in ORDER))
for idx in ok_cells:
    P(f"   {idx:4d} " + " ".join(f"{win[label][idx]['host_med']:8.1f}"
                                 for label in ORDER))
for idx in ok_cells:
    mm = med_rows.get(idx)
    mine = [f"{win[label][idx]['host_med']:.1f}" for label in ORDER]
    pub = mm.group(2).split() if mm else None
    check(f"S240.D5.{idx:02d} re-derived per-window host_ns medians == "
          f"s238 row (9 values)", mine == pub,
          f"got {mine} pub {pub}")
    tm = tab_rows.get(idx)
    host_m_a = statistics.median([win[l][idx]["host_med"]
                                  for l in groups["a"]])
    host_m_b = statistics.median([win[l][idx]["host_med"]
                                  for l in groups["b"]])
    desc = f"({cell_map[idx][2]},{cell_map[idx][3]},{cell_map[idx][4]})"
    mine_t = (f"{host_m_a:.1f}", f"{host_m_b:.1f}",
              f"{raws[idx]['d_groups']:.4f}", desc)
    pub_t = ((tm.group(5), tm.group(6), tm.group(7),
              f"({tm.group(2)},{tm.group(3)},{tm.group(4)})")
             if tm else None)
    check(f"S240.D6.{idx:02d} re-derived host_m_a/host_m_b/D_groups_host "
          f"(raw) + cell desc == s238 host-table row",
          mine_t == pub_t, f"got {mine_t} pub {pub_t}")
# -- the s238 gpu_ticks extent row --
mext = [m for m in (RE_S238_EXTENT.match(l) for l in s238_lines) if m]
check("S240.D7 s238 gpu_ticks extent row present exactly once",
      len(mext) == 1, f"found {len(mext)}")
gpu_sep = []
for idx in ok_cells:
    support_t = sorted({v for label in ORDER for v in win[label][idx]["cnt"]})
    ws_t = {label: shares(win[label][idx]["cnt"], support_t)
            for label in ORDER}
    within_t = [(l1(ws_t[x], ws_t[y]), x, y)
                for i, x in enumerate(ORDER) for y in ORDER[i + 1:]
                if (x in groups["a"]) == (y in groups["a"])]
    between_t = [(l1(ws_t[x], ws_t[y]), x, y)
                 for i, x in enumerate(ORDER) for y in ORDER[i + 1:]
                 if (x in groups["a"]) != (y in groups["a"])]
    if min(between_t, key=lambda t: t[0])[0] > max(within_t,
                                                   key=lambda t: t[0])[0]:
        gpu_sep.append(idx)
if len(mext) == 1:
    check("S240.D8 re-derived gpu_ticks separating-cell count == s238 "
          "extent row",
          (str(len(gpu_sep)), str(len(ok_cells)))
          == (mext[0].group(1), mext[0].group(2)),
          f"got {len(gpu_sep)} of {len(ok_cells)} "
          f"pub {mext[0].groups()}")

# ---- the cross-cell host extent (the row's answer; REPORT) ----
P()
P("6. THE HOST_NS CROSS-CELL SHAPE EXTENT (the row's answer;")
P(f"   REPORT; PATTERN-LEVEL ONLY -- the frozen criterion, "
  f"BIN = {BIN} ns at every cell):")
P()
P("   idx  (op,wg,forced)         bins  W_in     W_out    D_groups"
  "   SEP   W_in pair / W_out pair")
for idx in ok_cells:
    s = primary[idx]
    desc = f"({cell_map[idx][2]},{cell_map[idx][3]},{cell_map[idx][4]})"
    P(f"   {idx:3d}  {desc:20s} {len(s['support']):5d}"
      f"  {s['w_in'][0]:7.4f}  {s['w_out'][0]:7.4f}  {s['d_groups']:8.4f}"
      f"   {'YES' if s['sep'] else 'no ':3s}"
      f"  {s['w_in'][1]} vs {s['w_in'][2]} / "
      f"{s['w_out'][1]} vs {s['w_out'][2]}")
P()
P("   per-window host census at every cell (N, host_m ns, host_mad")
P(f"   ns, occupied bins at {BIN} ns, top1 bin):")
P("   idx label      N     host_m     host_mad  bins  top1")
for idx in ok_cells:
    s = primary[idx]
    for label in ORDER:
        w = win[label][idx]
        top1 = max(s["wb"][label].items(), key=lambda kv: kv[1])
        P(f"   {idx:3d} {label:8s} {w['N']:5d} {w['host_med']:11.1f}"
          f" {w['host_mad']:10.1f} {len(s['wb'][label]):5d}"
          f"  {top1[0] * BIN}:{100.0 * top1[1] / w['N']:.4f}%")
P()
P("   per-cell group pooled top6 bin rows (bin ns-start:share):")
for idx in ok_cells:
    s = primary[idx]
    for letter in ("a", "b"):
        P(f"   idx={idx:2d} ({letter}) pooled top6: "
          f"{top6_rows(s['gp'][letter])}")
P()
P("   RAW-SUPPORT SUPPLEMENTARY per cell (REPORT only; high-")
P("   dimensional support):")
P("   idx  W_in(raw)  W_out(raw)  D_groups(raw)  raw SEP"
  "   W_in pair / W_out pair")
for idx in ok_cells:
    rw_ = raws[idx]
    P(f"   {idx:3d}  {rw_['w_in'][0]:9.4f}  {rw_['w_out'][0]:9.4f}"
      f"  {rw_['d_groups']:12.4f}"
      f"   {'YES' if rw_['w_out'][0] > rw_['w_in'][0] else 'no '}"
      f"      {rw_['w_in'][1]} vs {rw_['w_in'][2]} / "
      f"{rw_['w_out'][1]} vs {rw_['w_out'][2]}")

# ---- the per-cell robustness family (REPORT) ----
P()
P("7. ROBUSTNESS FAMILY PER CELL (REPORT only -- every width")
P("   reported at every cell whatever it shows; the s239 pre-")
P("   frozen family, unchanged):")
P("   idx BIN ns  bins  W_in     W_out    D_groups  verdict")
for idx in ok_cells:
    for binw in (BIN,) + ROBUST_BINS:
        s = robust[idx][binw]
        P(f"   {idx:3d} {binw:6d} {len(s['support']):5d}"
          f"  {s['w_in'][0]:7.4f}  {s['w_out'][0]:7.4f}"
          f"  {s['d_groups']:8.4f}  "
          f"{'SEPARATE' if s['sep'] else 'no'}"
          + ("   (PRIMARY)" if binw == BIN else ""))
P()
P("   width-robustness per cell (the verdict identical at all 7")
P("   frozen widths?):")
width_robust_cells = []
for idx in ok_cells:
    vs = {robust[idx][binw]["sep"] for binw in (BIN,) + ROBUST_BINS}
    wr = len(vs) == 1
    if wr:
        width_robust_cells.append(idx)
    P(f"   idx={idx:2d} verdict at 7 widths "
      f"{sorted('SEPARATE' if robust[idx][binw]['sep'] else 'no' for binw in (BIN,) + ROBUST_BINS)}"
      f" -> {'IDENTICAL' if wr else 'WIDTH-DEPENDENT (NAMED)'}")
P()
P("   per-width separating-cell counts (of 18):")
sep_by_width = {}
for binw in (BIN,) + ROBUST_BINS:
    sep_by_width[binw] = [idx for idx in ok_cells if robust[idx][binw]["sep"]]
    P(f"   BIN {binw:6d} -> SEPARATE at {len(sep_by_width[binw]):2d} of "
      f"{len(ok_cells)} cells"
      + (f"  {sorted(sep_by_width[binw])}" if sep_by_width[binw] else ""))

# ---- the extent verdict ----
sep_cells = sep_by_width[BIN]
P()
P("8. THE EXTENT VERDICT (the row's answer; PATTERN-LEVEL):")
P(f"   SEPARATE at {len(sep_cells)} of {len(ok_cells)} pipeline-ok")
P(f"   cells on the host_ns channel under the frozen criterion")
P(f"   (BIN = {BIN} ns primary; the reading cell idx={sidx} "
  f"{'is' if sidx in sep_cells else 'is NOT'} one of them).")
if len(sep_cells) == 0:
    P("   EXTENT ROW: NO-CELL -- no host-channel letter-group shape")
    P("   split is detectable at any recorded cell under the frozen")
    P("   quantization; the (a)/(b) sample-shape difference is")
    P("   CONFINED to the gpu_ticks channel stream-wide.")
elif len(sep_cells) == len(ok_cells):
    P("   EXTENT ROW: ALL-CELLS -- the (a)/(b) sample-shape")
    P("   difference REPLICATES on the host_ns channel at every")
    P("   recorded cell (18/18); the difference imprints BOTH")
    P("   instrument channels stream-wide.")
else:
    P("   EXTENT ROW: SOME-CELL -- the host-channel separating set")
    P(f"   is the named set {sorted(sep_cells)}; neither pure NO-")
    P("   CELL nor pure ALL-CELLS; the split is cell-dependent on")
    P("   the host channel.")
P(f"   CONTRAST (bound in section 5): the gpu_ticks extent row")
P(f"   (committed s238) is SEPARATE at {len(gpu_sep)} of "
  f"{len(ok_cells)} cells -- re-derived here and bound above.")
P(f"   WIDTH: the host extent row is "
  f"{'IDENTICAL at all 7 frozen widths' if all(len(sep_by_width[w]) == len(sep_cells) and sep_by_width[w] == sep_cells for w in (BIN,) + ROBUST_BINS) else 'WIDTH-DEPENDENT (the per-width sets above)'}")

# ---- interpretation constraints ----
P()
P("9. INTERPRETATION CONSTRAINTS (what this row does and does NOT")
P("   decide): the host_ns channel (CLOCK_MONOTONIC submit->")
P("   completion) is independent of the GPU timestamp channel but")
P("   SPANS GPU execution.  The pure GPU-timestamp-record")
P("   quantization account does not by itself predict a host-")
P("   channel letter-group shape split at any cell; an execution-")
P("   time state imprints both channels (subject to magnitude).")
if len(sep_cells) == 0:
    P("   OBSERVED: NO host-channel letter-group shape split at any")
    P("   cell under the frozen quantization -- the s239 reading-")
    P("   cell result EXTENDS to the whole recorded stream: the")
    P("   (a)/(b) sample-shape difference is confined to the")
    P("   gpu_ticks channel at BOTH extents (s238 gpu_ticks 18/18")
    P("   SEPARATE bound above; host 0/18).  CONSISTENCY ROW: the")
    P("   recording-state candidate stays consistent, and an")
    P("   execution-time state too small for the host channel at")
    P("   every cell is equally live.")
elif len(sep_cells) == len(ok_cells):
    P("   OBSERVED: the host-channel letter-group shape split")
    P("   replicates at every cell -- the s239 reading-cell null")
    P("   does NOT extend; a state confined to the GPU timestamp")
    P("   values alone is ruled out as the whole account; both")
    P("   surviving whole-stream candidates that co-vary with")
    P("   host-observed duration stay consistent.")
else:
    P("   OBSERVED: the host-channel split holds at the named set")
    P("   only -- the s239 reading-cell null holds at most cells;")
    P("   both surviving candidates stay consistent with a")
    P("   cell-modulated imprint; no candidate is ruled out.")
P("   EITHER WAY: the cause dichotomy (execution-time state vs")
P("   instrument/timestamp-quantization state) is NOT DECIDED and")
P("   the CAUSE stays UNMEASURED -- this row completes the second-")
P("   instrument-channel EXTENT constraint only; the underlying-")
P("   instrument-state COUNT stays outside (s220 1(b)).")

P()
P("10. THREE-STATE / RULE 4 / BAR (unchanged): every sample value")
P("    above is a named run's landed MEASURED QUANTITY on")
P("    aiueos-6600hs (Intel BMG G31) under the named instrument,")
P("    RE-PARSED from committed run-log bytes -- this slice")
P("    measures NOTHING new on hardware (no runs, no builds, NO GO")
P("    stamp); the share/distance arithmetic is DERIVED; the")
P("    accelerator-targets workgroup rows stay exactly as ADR-0358")
P("    left them (:measured? false rows remain provisional -- NOT")
P("    optimization evidence); NO vendor optimization exists for")
P("    Intel (or for any vendor) and none follows from this")
P("    extent row.  RULE 4 unchanged: NOTHING MOVES; the committed")
P("    bracket stays EXACTLY (254,923, 255,045]; L9 binds at")
P("    n=254,984 (C2 (c), D3 (v)); the MID-ONLY NARROWING CLAIM")
P("    stays SUSPENDED.  BAR NON-INTERFERENCE: NO settle-bar-")
P("    ledger line, NO day-slot consumption; the bar's SETTLED")
P("    INTERMEDIATE/MIXED verdict unmoved.")

P()
P("11. NAMED, NOT HIDDEN:")
P("    (a) the per-cell rule application is SUPPLEMENTARY REPORT --")
P("    only the committed rows (sections 3-5) bind; the per-cell")
P("    confrontation never fails the run.")
P("    (b) the letters come from the gpu_ticks channel (bound to")
P("    the committed s234 rows) -- the host channel does not")
P("    define its own groups, at any cell.")
P("    (c) the criterion's quantization and robustness family are")
P("    the s239 frozen choices, applied per cell UNCHANGED -- no")
P("    width or form was chosen against any cross-cell host shape")
P("    number.")
P("    (d) OUTSIDE this universe (named, not hidden): the s237")
P("    kernel-variant arms (iter1/iter3/iter8/itervc8 spvs) and")
P("    the s235 supplementary arms (anv-tsstage bb-b2/tt-b2); the")
P("    6 pipeline-FAIL cells (no samples in any window).")

P()
P("12. NOT DONE (s241 carries exactly this list): the s216")
P("    identity hazard's remaining residuals (standing, not")
P("    queued): the CAUSE of the sample-shape difference stays")
P("    UNMEASURED and UNDECIDED (this row completed the second-")
P("    instrument-channel extent constraint; a cause-resolution")
P("    act needs new hardware runs, each with its own freeze --")
P("    standing, not queued); the underlying-instrument-state")
P("    COUNT stays outside (s220 1(b)); at N=75 the s235/s237")
P("    classifications carry NO noise model and near-neither")
P("    prevalence needs higher-N readings -- new hardware runs,")
P("    each with its own freeze (standing, not queued); standing,")
P("    not queued: any further counted-day slot (each needs its")
P("    own freeze) and the cross-day tail-movement row.")
if len(width_robust_cells) == len(ok_cells):
    P("    NOTHING is QUEUED at s241 from this row -- the queued")
    P("    row is answered here and the host_ns channel's")
    P("    committed-bytes confrontation is complete at this scope")
    P("    (reading cell + cross-cell extent, width-robust at every")
    P("    cell); the residuals remaining all need new hardware")
    P("    runs (standing, not queued).")
else:
    P("    QUEUED for s241: a width-free host-channel cross-cell")
    P("    shape extent (its criterion frozen before its own")
    P("    numbers) -- the verdict is width-dependent at the named")
    P(f"    cells {sorted(set(ok_cells) - set(width_robust_cells))}")
    P("    and that dependence is the open row.")
P("    (JUN-55, JUN-59; Linear tracking JUN-499)")

P()
P(f"# host-extent s240 (host-extent-s240.py): "
  f"{CHECKS['ok']} ok / {CHECKS['failed']} failed")
print("\n".join(OUT))
sys.exit(0 if CHECKS["failed"] == 0 else 1)
