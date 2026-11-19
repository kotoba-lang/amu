#!/usr/bin/env python3
"""host-shape-s239.py -- THE HOST_NS CHANNEL'S PER-SAMPLE SHAPE
CONFRONTATION AT THE READING CELL (amu-gpu session 239; the s238
carry-forward's QUEUED row "the host_ns channel's per-sample shape
confrontation at the reading cell under its own criterion frozen
before the numbers (this row reports the host channel descriptively
only)" TAKEN AS ITS ROW).

THE ROW: the s234 confrontation decided the gpu_ticks (a)/(b)
sample-shape dichotomy at the reading cell (sum,128,S=16) and the
s238 row constrained its locus to whole-stream states.  The host_ns
channel (CLOCK_MONOTONIC submit->completion -- a DIFFERENT
instrument channel from the gpu_ticks timestamp channel) was
reported there DESCRITIVELY ONLY, without a criterion.  Whether the
(a)/(b) letter groups carry distinct per-sample shapes on the host
channel too is UNCHECKED from committed bytes -- and it CONSTRAINS
the cause dichotomy again: the two surviving candidates (an
execution-time state of the whole dispatch stream vs an
instrument/timestamp-quantization state of the whole recording)
make different predictions for a second, host-side instrument
channel.

THE HOST CRITERION (frozen HERE, before any host sample of this
confrontation is read -- the s238 named row "the host_ns channel
carries NO criterion here (its sample shape confrontation needs its
own frozen criterion)" is exactly what this script supplies): the
host_ns channel is ns-resolution and high-dimensional (the s238
raw-support D_groups_host row already showed this), so the s234
gpu_ticks criterion is NOT transplanted to raw support unchanged.
THE FROZEN FORM for this channel: quantize every reading-cell
host_ns sample to a bin index b = host_ns // BIN with BIN = 1000 ns
(1 us -- a fixed physical scale chosen before the numbers, NOT
derived from any sample of this confrontation); per-window share
vectors s_w over the union support of occupied bin indices
(percent); W_in = max L1 over same-letter window pairs, W_out =
min L1 over opposite-letter window pairs; SHAPES SEPARATE iff
W_out > W_in -- the s234 rule shape, on the channel's own frozen
quantization.  The LETTERS are the gpu_ticks letters (re-derived
from m vs the committed floor band and BOUND to the committed s234
rows below) -- the host channel does not get its own letters.
PATTERN-LEVEL ONLY (s218 2(e)): NO p-value, NO test statistic, NO
probability claim.

ROBUSTNESS FAMILY (also frozen here, REPORT only -- every width is
reported whatever direction it points, and a verdict that flips
across the family is NAMED as width-robustness, never hidden):
the same arithmetic at BIN in (100, 250, 500, 2000, 5000, 10000)
ns.  RAW-SUPPORT SUPPLEMENTARY (REPORT only): the same W_in/W_out
arithmetic on the raw host_ns support (the s238 D_groups_host
machinery extended from pooled groups to window pairs).

PRIOR EXPOSURE, NAMED: the committed s238 report already carries
descriptive host_ns rows at the reading cell (per-window pooled
medians and the raw-support D_groups_host) which this script
re-derives and BINDS fail-closed below; no criterion was chosen
against any host per-sample shape number -- none of that shape had
been computed before this script's criterion text above.

UNIVERSE (fixed here, before the numbers): the nine deep-pooling-
era own readings whose raw run logs are COMMITTED -- the s234/s238
universe unchanged (cuts s158/s169/s185/s197/s209 + the s225 act's
four readings; 27 run logs, 9 windows x k=3), at the READING CELL
ONLY (sum,128,S=16).  The s237 kernel-variant arms and the s235
supplementary arms are OUTSIDE (named, not hidden).

Reads ONLY committed bytes (fail-closed; any parse anomaly is an
immediate abort = failed run):
  - docs/evidence/gpu/anv-b3bisect{15..19}-*/run-c2-r0{1..3}.txt.gz
    and docs/evidence/gpu/anv-b3control3state-20261102/run-
    rd{1..4}-c2-r0{1..3}.txt.gz (the nine windows' c2 logs, through
    gzip).
  - docs/evidence/gpu/anv-b3control3state-20261102/identity-
    shape-s234-run1.txt (the committed s234 report rows -- BINDS:
    the gpu_ticks reading-cell re-derivation below must EQUAL the
    committed bytes).
  - docs/evidence/gpu/anv-b3control3state-20261102/crosscell-
    extent-s238-run1.txt (the committed s238 report rows -- BINDS:
    the host_ns descriptive reading-cell rows below must EQUAL the
    committed bytes).
  - docs/evidence/gpu/anv-b3bisect7-20261027/derivation-census-
    s27.txt (the committed floor band and c8 reference).

Writes NOTHING.  Prints the report to stdout, nothing to stderr on
success.  Exit 0 iff every CHECK is ok.

CHECKS vs REPORTS (the honesty split): PARSE anomalies and BIND
mismatches (missing file, header/cell-map divergence, run-integrity
problems, any reading-cell row disagreeing with the committed
s234/s238 bytes) are CHECKS and fail the run; the host_ns
confrontation itself, the robustness family, the raw-support rows
and the interpretation rows are REPORTS and never fail the run.

THREE-STATE: every sample value below is a named run's landed
MEASURED QUANTITY (its own hardware runs on aiueos-6600hs, Intel
BMG G31, under the named instrument), RE-PARSED here from committed
run-log bytes -- this script measures NOTHING new on hardware (no
runs, no builds, NO GO stamp) and no value here is a measurement of
this tick; the share/distance arithmetic is DERIVED (labelled).
The CAUSE of the sample-shape difference stays UNMEASURED and
UNDECIDED (this row CONSTRAINS which candidates stay consistent
with a second instrument channel only); the underlying-instrument-
state COUNT stays outside (s220 1(b) binds).  RULE 4 unchanged:
NOTHING MOVES; the committed bracket stays EXACTLY (254,923,
255,045]; the accelerator-targets workgroup rows stay exactly as
ADR-0358 left them (:measured? false rows remain provisional --
NOT optimization evidence); NO vendor optimization exists for
Intel (or for any vendor) and none follows from this confrontation.
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

# THE FROZEN HOST CRITERION (see the docstring; fixed BEFORE the
# numbers): primary quantization width and the pre-frozen
# robustness family (REPORT only).
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

S234_REPORT = HERE / "identity-shape-s234-run1.txt"
S238_REPORT = HERE / "crosscell-extent-s238-run1.txt"
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
# -- committed s238 report row forms (BINDS; the host descriptive
#    rows at the reading cell) --
S238_HOSTTAB_ANCHOR = ("   idx  (op,wg,forced)      host_m_a  "
                       "host_m_b   D_groups_host")
S238_HOSTMED_ANCHOR = "   per-window pooled host_ns medians at every cell:"
RE_S238_HOSTTAB_ROW = re.compile(
    r"^ +(\d+)  \((\w+),(\d+),(\w+)\) +([0-9]+\.[0-9]) +([0-9]+\.[0-9]) "
    r"+([0-9]+\.[0-9]{4})$")
RE_S238_HOSTMED_ROW = re.compile(r"^ +(\d+) ((?:[0-9.]+ +){8}[0-9.]+)$")

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


def share_rows(sh):
    return "  ".join(f"{k}:{v:.4f}" for k, v in sorted(sh.items()) if v > 0)


def top3(counter, n):
    top = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    return "  ".join(f"{k}:{100.0 * v / n:.4f}%" for k, v in top)


# ------------------------------------------------------------------ report
P("host-shape-s239.py -- THE HOST_NS CHANNEL'S PER-SAMPLE SHAPE")
P("CONFRONTATION AT THE READING CELL (amu-gpu s239; the s238")
P("carry-forward's QUEUED row -- the host channel's own frozen")
P("criterion -- taken as its row).")
P()
P("1. THE HOST CRITERION (frozen in the script BEFORE any host")
P("   sample of this confrontation was read): bin index")
P(f"   b = host_ns // {BIN} ns (1 us, fixed physical scale, NOT")
P("   derived from any sample); per-window share vectors over the")
P("   union support of occupied bin indices (percent); W_in = max")
P("   L1 over same-letter window pairs, W_out = min L1 over")
P("   opposite-letter window pairs; SHAPES SEPARATE iff W_out >")
P("   W_in -- the s234 rule shape on the channel's own frozen")
P("   quantization.  Letters are the gpu_ticks letters (re-derived")
P("   and BOUND to the committed s234 rows in section 3).")
P(f"   ROBUSTNESS FAMILY (frozen here too; REPORT only, every")
P(f"   width reported whatever it shows): BIN in "
  f"{(BIN,) + ROBUST_BINS} ns.")
P("   RAW-SUPPORT SUPPLEMENTARY (REPORT only): the same W_in/W_out")
P("   arithmetic on raw host_ns support.")
P("   PATTERN-LEVEL ONLY (s218 2(e)): NO p-value, NO test")
P("   statistic, NO probability claim.")
P("   PRIOR EXPOSURE, NAMED: the committed s238 report already")
P("   carries descriptive host rows at the reading cell (medians +")
P("   raw-support D_groups_host), re-derived and BOUND in section")
P("   4; no criterion was chosen against any host per-sample shape")
P("   number.")
P("UNIVERSE: the s234/s238 nine-window universe unchanged (27")
P("committed c2 run logs), at the READING CELL ONLY (sum,128,S=16).")
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
check("S239.A1 s27 census parse == pins (c2 31, band 31..32, c8 32915)",
      (c2pin, band, c8ref) == (C2_PIN, FLOOR_BAND, C8_REF),
      f"got {(c2pin, band, c8ref)}")

# ---- the 27 committed run logs ----
P()
P("2. THE RUN-LOG CENSUS (every sample RE-PARSED from committed")
P("   run-log bytes; m = pooled sample median gpu_ticks over k=3")
P("   runs x R rounds at the reading cell; host_m = pooled sample")
P("   median host_ns at the reading cell):")
runs = {}
for label, sess, kind, d, pat in WINDOWS:
    for nn in (1, 2, 3):
        name = pat.format(nn)
        path = GPU / d / name
        assert path.exists(), f"RUN LOG MISSING: {path}"
        runs[(label, nn)] = load_run(path)
check("S239.A2 header identity across all 27 runs",
      len({r["header"] for r in runs.values()}) == 1)
check("S239.A3 cell-map identity across all 27 runs",
      len({r["cell_map"] for r in runs.values()}) == 1)
for (label, nn), r in sorted(runs.items()):
    check(f"S239.B{label}-r{nn:02d} run integrity clean",
          not r["problems"], "; ".join(r["problems"]))
sidx = runs[(WINDOWS[0][0], 1)]["s128"]
check("S239.A4 ok/fail cell sets uniform (18 ok incl. the reading "
      "cell idx=1 (sum,128,S=16), 6 FAIL forced=8)",
      len({r["ok_cells"] for r in runs.values()}) == 1
      and len({r["fail_cells"] for r in runs.values()}) == 1
      and len(runs[(WINDOWS[0][0], 1)]["ok_cells"]) == 18
      and len(runs[(WINDOWS[0][0], 1)]["fail_cells"]) == 6
      and sidx == 1 and sidx in runs[(WINDOWS[0][0], 1)]["ok_cells"])
P()
P("   the header block (8 lines, identical across all 27 runs --")
P("   the RECORDED instrument/timestamp metadata, byte-compared):")
for l in runs[(WINDOWS[0][0], 1)]["header"]:
    P(f"     {l}")

# ---- per-window pooled statistics at the reading cell ----
order = [w[0] for w in WINDOWS]
win = {}
for label, sess, kind, d, pat in WINDOWS:
    xs, hs = [], []
    for nn in (1, 2, 3):
        xs.extend(runs[(label, nn)]["ticks"][sidx])
        hs.extend(runs[(label, nn)]["host"][sidx])
    m_ = statistics.median(xs)
    hm_ = statistics.median(hs)
    win[label] = dict(
        N=len(xs), m=m_,
        mad=statistics.median([abs(x - m_) for x in xs]),
        cnt=Counter(xs), host=hs, host_med=hm_,
        host_mad=statistics.median([abs(x - hm_) for x in hs]),
        host_cnt=Counter(hs))
for label in order:
    check(f"S239.E1.{label} host sample count at the reading cell == 3R",
          len(win[label]["host"]) == 3 * R,
          f"got {len(win[label]['host'])}")

# ---- gpu_ticks reading-cell binds to the committed s234 report ----
P()
P("3. READING-CELL gpu_ticks BINDS (every s234 row below is")
P("   RE-DERIVED here from the run logs and must EQUAL the")
P("   committed report bytes identity-shape-s234-run1.txt --")
P("   fail-closed; this binds the letters and the machinery to the")
P("   committed record):")
s234_bytes = S234_REPORT.read_bytes()
P(f"   s234 report pin: {len(s234_bytes)} bytes sha256 "
  f"{hashlib.sha256(s234_bytes).hexdigest()}")
s234 = s234_bytes.decode()
s234_lines = s234.splitlines()
support128 = sorted({v for label in order for v in win[label]["cnt"]})
msup = [RE_S234_SUPPORT.match(l) for l in s234_lines]
msup = [m for m in msup if m]
check("S239.C1 s234 union-support row present exactly once",
      len(msup) == 1, f"found {len(msup)}")
if len(msup) == 1:
    sup_pub = [int(x) for x in msup[0].group(1).split(",")]
    check("S239.C2 re-derived reading-cell union support == s234 row",
          sup_pub == support128, f"{sup_pub} != {support128}")

pub_census, pub_shares = {}, {}
for l in s234_lines:
    mc = RE_S234_CENSUS.match(l)
    if mc:
        pub_census[mc.group(1)] = mc
        continue
    msh = RE_S234_SHAREROW.match(l)
    if msh and msh.group(1) in {w[0] for w in WINDOWS}:
        pub_shares[msh.group(1)] = msh.group(2).split()
check("S239.C3 s234 per-window census rows present 9/9",
      set(pub_census) == {w[0] for w in WINDOWS}, f"{sorted(pub_census)}")
check("S239.C4 s234 per-window share rows present 9/9",
      set(pub_shares) == {w[0] for w in WINDOWS}, f"{sorted(pub_shares)}")

groups = {"a": [], "b": []}
for label in order:
    w = win[label]
    letter = "a" if band[0] <= w["m"] <= band[1] else "b"
    groups[letter].append(label)
    top = sorted(w["cnt"].items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    top_s = "  ".join(f"{k}:{100.0 * v / w['N']:.4f}%" for k, v in top)
    mc = pub_census.get(label)
    if mc is not None:
        check(f"S239.C5.{label} re-derived N/m/mad/top3 == s234 census row",
              (int(mc.group(3)), float(mc.group(4)), float(mc.group(5)),
               mc.group(6)) == (w["N"], w["m"], w["mad"], top_s),
              f"got N={w['N']} m={w['m']} mad={w['mad']} top3={top_s!r} "
              f"pub=({mc.group(3)}, {mc.group(4)}, {mc.group(5)}, "
              f"{mc.group(6)!r})")
    if label in pub_shares:
        mine = share_rows(shares(w["cnt"], support128)).split()
        check(f"S239.C6.{label} re-derived reading-cell share row == "
              f"s234 share row",
              mine == pub_shares[label],
              f"got {mine} pub {pub_shares[label]}")

for letter in ("a", "b"):
    mrows = [RE_S234_GROUP.match(l) for l in s234_lines]
    mrows = [m for m in mrows if m and m.group(1) == letter]
    check(f"S239.C7.{letter} s234 group row present exactly once",
          len(mrows) == 1, f"found {len(mrows)}")
    if len(mrows) == 1:
        pub_list = [x.strip().strip("'") for x in mrows[0].group(2).split(",")]
        check(f"S239.C8.{letter} re-derived letter group == s234 group row",
              pub_list == groups[letter],
              f"got {groups[letter]} pub {pub_list}")
mpool = [RE_S234_POOLED.match(l) for l in s234_lines]
mpool = [m for m in mpool if m]
check("S239.C9 s234 pooled rows present 2/2",
      {m.group(1) for m in mpool} == {"a", "b"}, f"{[m.group(1) for m in mpool]}")

gp128 = {}
for letter in ("a", "b"):
    c = Counter()
    for label in groups[letter]:
        c.update(win[label]["cnt"])
    gp128[letter] = shares(c, support128)
    for m in mpool:
        if m.group(1) == letter:
            mine = share_rows(gp128[letter]).split()
            check(f"S239.C10.{letter} re-derived pooled reading-cell share "
                  f"row == s234 pooled row",
                  mine == m.group(2).split(),
                  f"got {mine} pub {m.group(2).split()}")

ws128 = {label: shares(win[label]["cnt"], support128) for label in order}
pairs = [(x, y) for i, x in enumerate(order) for y in order[i + 1:]]
within = [(l1(ws128[x], ws128[y]), x, y) for x, y in pairs
          if (x in groups["a"]) == (y in groups["a"])]
between = [(l1(ws128[x], ws128[y]), x, y) for x, y in pairs
           if (x in groups["a"]) != (y in groups["a"])]
win_a = [p for p in within if p[1] in groups["a"]]
win_b = [p for p in within if p[1] in groups["b"]]
mpc = [RE_S234_PAIRCENSUS.match(l) for l in s234_lines]
mpc = [m for m in mpc if m]
check("S239.C11 s234 pair-census row present exactly once", len(mpc) == 1)
if len(mpc) == 1:
    check("S239.C12 re-derived pair counts == s234 pair census row",
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
check("S239.C13 s234 W_in/W_out rows present 2/2",
      len(mwi) == 1 and len(mwo) == 1, f"{len(mwi)}/{len(mwo)}")
if len(mwi) == 1:
    check("S239.C14 re-derived W_in (value + pair) == s234 W_in row",
          (f"{w_in_v:.4f}", w_in_p[1], w_in_p[2])
          == (mwi[0].group(1), mwi[0].group(2), mwi[0].group(3)),
          f"got {w_in_v:.4f} ({w_in_p[1]} vs {w_in_p[2]}) "
          f"pub {mwi[0].group(1)} ({mwi[0].group(2)} vs {mwi[0].group(3)})")
if len(mwo) == 1:
    check("S239.C15 re-derived W_out (value + pair) == s234 W_out row",
          (f"{w_out_v:.4f}", w_out_p[1], w_out_p[2])
          == (mwo[0].group(1), mwo[0].group(2), mwo[0].group(3)),
          f"got {w_out_v:.4f} ({w_out_p[1]} vs {w_out_p[2]}) "
          f"pub {mwo[0].group(1)} ({mwo[0].group(2)} vs {mwo[0].group(3)})")
mvv = [RE_S234_VERDICT.match(l) for l in s234_lines]
mvv = [m for m in mvv if m]
check("S239.C16 s234 SHAPES SEPARATE verdict row present", len(mvv) == 1)
if len(mvv) == 1:
    check("S239.C17 re-derived verdict arithmetic == s234 verdict row",
          (f"{w_out_v:.4f}", f"{w_in_v:.4f}")
          == (mvv[0].group(1), mvv[0].group(2)),
          f"got ({w_out_v:.4f}, {w_in_v:.4f})")
check("S239.C18 reading-cell letters re-derived (m vs band) == the "
      "committed s234 group split",
      (groups["a"], groups["b"]) == (["s158", "s185", "s197"],
                                     ["s169", "s209", "act-rd1",
                                      "act-rd2", "act-rd3", "act-rd4"]))
P(f"   letters re-derived and bound: (a) {groups['a']} / "
  f"(b) {groups['b']}")

# ---- host_ns binds to the committed s238 report ----
P()
P("4. READING-CELL host_ns BINDS (the committed s238 descriptive")
P("   rows below are RE-DERIVED here from the run logs and must")
P("   EQUAL the committed report bytes crosscell-extent-s238-")
P("   run1.txt -- fail-closed):")
s238_bytes = S238_REPORT.read_bytes()
P(f"   s238 report pin: {len(s238_bytes)} bytes sha256 "
  f"{hashlib.sha256(s238_bytes).hexdigest()}")
s238 = s238_bytes.decode()
s238_lines = s238.splitlines()
anchors_t = [i for i, l in enumerate(s238_lines)
             if l == S238_HOSTTAB_ANCHOR]
anchors_m = [i for i, l in enumerate(s238_lines)
             if l == S238_HOSTMED_ANCHOR]
check("S239.D1 s238 host-table anchor present exactly once",
      len(anchors_t) == 1, f"found {len(anchors_t)}")
check("S239.D2 s238 host-median table anchor present exactly once",
      len(anchors_m) == 1, f"found {len(anchors_m)}")
tab_rows, med_rows = {}, {}
if len(anchors_t) == 1:
    i = anchors_t[0] + 1
    for _ in range(3):            # skip any header line (s235 form walk)
        if RE_S238_HOSTTAB_ROW.match(s238_lines[i]):
            break
        i += 1
    while i < len(s238_lines):
        mm = RE_S238_HOSTTAB_ROW.match(s238_lines[i])
        if not mm:
            break
        tab_rows[int(mm.group(1))] = mm
        i += 1
    check("S239.D3 s238 host-table rows parse (18 pipeline-ok cells)",
          len(tab_rows) == 18, f"got {len(tab_rows)}")
if len(anchors_m) == 1:
    i = anchors_m[0] + 1
    for _ in range(3):            # skip the column-header line
        if RE_S238_HOSTMED_ROW.match(s238_lines[i]):
            break
        i += 1
    while i < len(s238_lines):
        mm = RE_S238_HOSTMED_ROW.match(s238_lines[i])
        if not mm:
            break
        med_rows[int(mm.group(1))] = mm
        i += 1
    check("S239.D4 s238 host-median table rows parse (18 pipeline-ok "
          "cells)",
          len(med_rows) == 18, f"got {len(med_rows)}")

if sidx in med_rows:
    pub_meds = [float(x) for x in med_rows[sidx].group(2).split()]
    mine_meds = [win[label]["host_med"] for label in order]
    check("S239.D5 re-derived per-window host_ns medians at the reading "
          "cell == s238 row (9 values)",
          [f"{v:.1f}" for v in mine_meds] == [f"{v:.1f}" for v in pub_meds],
          f"got {[f'{v:.1f}' for v in mine_meds]} "
          f"pub {[f'{v:.1f}' for v in pub_meds]}")
else:
    check("S239.D5 re-derived per-window host_ns medians at the reading "
          "cell == s238 row (9 values)", False, "reading-cell row missing")

support_raw = sorted({v for label in order for v in win[label]["host_cnt"]})
gph = {}
for letter in ("a", "b"):
    c = Counter()
    for label in groups[letter]:
        c.update(win[label]["host_cnt"])
    gph[letter] = shares(c, support_raw)
host_m_a = statistics.median([win[l]["host_med"] for l in groups["a"]])
host_m_b = statistics.median([win[l]["host_med"] for l in groups["b"]])
d_groups_host_raw = l1(gph["a"], gph["b"])
if sidx in tab_rows:
    trow = tab_rows[sidx]
    check("S239.D6 re-derived host_m_a/host_m_b/D_groups_host "
          "(raw-support, the s238 machinery) == s238 host-table row",
          (f"{host_m_a:.1f}", f"{host_m_b:.1f}", f"{d_groups_host_raw:.4f}")
          == (trow.group(5), trow.group(6), trow.group(7)),
          f"got ({host_m_a:.1f}, {host_m_b:.1f}, {d_groups_host_raw:.4f}) "
          f"pub ({trow.group(5)}, {trow.group(6)}, {trow.group(7)})")
else:
    check("S239.D6 re-derived host_m_a/host_m_b/D_groups_host == s238 "
          "host-table row", False, "reading-cell row missing")
P(f"   reading-cell host rows bound: host_m_a {host_m_a:.1f} "
  f"host_m_b {host_m_b:.1f} D_groups_host(raw) {d_groups_host_raw:.4f}")

# ---- the host_ns confrontation (the row's answer; REPORT) ----
def shape_at(binw):
    """The frozen criterion arithmetic at quantization width binw
    (REPORT machinery; the primary width's verdict is the row's
    answer)."""
    wb = {label: Counter(v // binw for v in win[label]["host"])
          for label in order}
    support = sorted({b for label in order for b in wb[label]})
    ws = {label: shares(wb[label], support) for label in order}
    gp = {}
    for letter in ("a", "b"):
        c = Counter()
        for label in groups[letter]:
            c.update(wb[label])
        gp[letter] = shares(c, support)
    within_c = [(l1(ws[x], ws[y]), x, y) for x, y in pairs
                if (x in groups["a"]) == (y in groups["a"])]
    between_c = [(l1(ws[x], ws[y]), x, y) for x, y in pairs
                 if (x in groups["a"]) != (y in groups["a"])]
    w_in_c = max(within_c, key=lambda t: t[0])
    w_out_c = min(between_c, key=lambda t: t[0])
    return dict(wb=wb, support=support, ws=ws, gp=gp,
                d_groups=l1(gp["a"], gp["b"]),
                w_in=w_in_c, w_out=w_out_c,
                sep=w_out_c[0] > w_in_c[0],
                within=within_c, between=between_c)


primary = shape_at(BIN)

P()
P("5. THE HOST_NS PER-SAMPLE SHAPE CONFRONTATION AT THE READING")
P("   CELL (the row's answer; REPORT; PATTERN-LEVEL ONLY -- the")
P(f"   frozen criterion, BIN = {BIN} ns):")
P()
P("   per-window host census at the reading cell (N, median ns,")
P("   MAD ns, occupied bins, top1 bin share):")
for label in order:
    w = win[label]
    occ = len(w["host_cnt"] and primary["wb"][label])
    top1 = max(primary["wb"][label].items(), key=lambda kv: kv[1])
    P(f"     {label:8s} N={w['N']} host_m={w['host_med']:.1f} "
      f"host_mad={w['host_mad']:.1f} bins={occ} "
      f"top1 {top1[0] * BIN}:{100.0 * top1[1] / w['N']:.4f}%")
P()
P(f"   union support of host_ns bins at the cell ({BIN} ns bins):")
P(f"     {len(primary['support'])} occupied bins "
  f"(ns range {primary['support'][0] * BIN}.."
  f"{primary['support'][-1] * BIN + BIN - 1})")
P()
P("   per-window share rows (bin ns-start:share):")
for label in order:
    rows = "  ".join(
        f"{b * BIN}:{v:.4f}" for b, v in sorted(primary["ws"][label].items())
        if v > 0)
    P(f"     {label:8s} {rows}")
P()
for letter in ("a", "b"):
    tops = sorted(primary["gp"][letter].items(),
                  key=lambda kv: (-kv[1], kv[0]))[:6]
    rows = "  ".join(f"{b * BIN}:{v:.4f}" for b, v in tops)
    P(f"     group ({letter}) pooled top6: {rows}")
P()
P(f"   pair census: within-a {len([p for p in primary['within'] if p[1] in groups['a']])}, "
  f"within-b {len([p for p in primary['within'] if p[1] in groups['b']])}, "
  f"between {len(primary['between'])}")
P(f"   W_in  = max within-group L1 = {primary['w_in'][0]:.4f} "
  f"({primary['w_in'][1]} vs {primary['w_in'][2]})")
P(f"   W_out = min between-group L1 = {primary['w_out'][0]:.4f} "
  f"({primary['w_out'][1]} vs {primary['w_out'][2]})")
P(f"   D_groups = L1 between pooled group shares = "
  f"{primary['d_groups']:.4f}")
if primary["sep"]:
    P(f"   SHAPES SEPARATE (W_out {primary['w_out'][0]:.4f} > "
      f"W_in {primary['w_in'][0]:.4f}).")
else:
    P(f"   SHAPES DO NOT SEPARATE (W_out {primary['w_out'][0]:.4f} "
      f"<= W_in {primary['w_in'][0]:.4f}).")

P()
P("6. ROBUSTNESS FAMILY + RAW SUPPORT (REPORT only -- every width")
P("   reported whatever it shows; frozen before the numbers):")
P("   BIN ns  bins  W_in     W_out    D_groups  verdict")
for binw in (BIN,) + ROBUST_BINS:
    s = primary if binw == BIN else shape_at(binw)
    P(f"   {binw:6d}  {len(s['support']):4d}  {s['w_in'][0]:7.4f}  "
      f"{s['w_out'][0]:7.4f}  {s['d_groups']:8.4f}  "
      f"{'SEPARATE' if s['sep'] else 'no'}"
      + ("   (PRIMARY)" if binw == BIN else ""))
verdicts = [(binw, (primary if binw == BIN else shape_at(binw))["sep"])
            for binw in (BIN,) + ROBUST_BINS]
width_robust = len({v for _, v in verdicts}) == 1
P(f"   width-robustness: the verdict is "
  f"{'IDENTICAL at all 7 frozen widths' if width_robust else 'NOT identical across the frozen widths (width-dependent; NAMED)'}")
P()
P("   RAW-SUPPORT SUPPLEMENTARY (the s238 machinery extended to")
P(f"   window pairs; {len(support_raw)} distinct raw host_ns values):")
ws_raw = {label: shares(win[label]["host_cnt"], support_raw)
          for label in order}
within_r = [(l1(ws_raw[x], ws_raw[y]), x, y) for x, y in pairs
            if (x in groups["a"]) == (y in groups["a"])]
between_r = [(l1(ws_raw[x], ws_raw[y]), x, y) for x, y in pairs
             if (x in groups["a"]) != (y in groups["a"])]
w_in_r = max(within_r, key=lambda t: t[0])
w_out_r = min(between_r, key=lambda t: t[0])
P(f"   W_in(raw)  = {w_in_r[0]:.4f} ({w_in_r[1]} vs {w_in_r[2]})")
P(f"   W_out(raw) = {w_out_r[0]:.4f} ({w_out_r[1]} vs {w_out_r[2]})")
P(f"   D_groups(raw) = {d_groups_host_raw:.4f} (bound in section 4)")
P(f"   raw verdict: "
  f"{'SEPARATE' if w_out_r[0] > w_in_r[0] else 'no'} "
  f"(high-dimensional support; contextual only)")

# ---- interpretation constraints ----
P()
P("7. INTERPRETATION CONSTRAINTS (what this row does and does NOT")
P("   decide): the host_ns channel is CLOCK_MONOTONIC submit->")
P("   completion -- an instrument channel independent of the GPU")
P("   timestamp channel, but SPANNING GPU execution.  The pure")
P("   GPU-timestamp-record quantization account does not by itself")
P("   predict a host-channel letter-group shape split; an")
P("   execution-time state imprints both channels.  The observed")
P(f"   primary verdict is "
  f"{'SEPARATE' if primary['sep'] else 'NOT SEPARATE'} at the reading cell")
if primary["sep"]:
    P("   -- the (a)/(b) shape difference REPLICATES on the second")
    P("   instrument channel (consistency row: a state confined to")
    P("   the GPU timestamp values alone is ruled out as the whole")
    P("   account; both surviving whole-stream candidates that")
    P("   co-vary with host-observed duration stay consistent).")
else:
    P("   -- NO letter-group shape split is detectable on the host")
    P("   channel at the reading cell under the frozen criterion")
    P("   (consistency row: the difference is confined to the GPU")
    P("   timestamp channel here; the recording-state candidate")
    P("   stays consistent, and an execution-time state too small")
    P("   for the host channel is equally live).")
P("   EITHER WAY: the cause dichotomy (execution-time state vs")
P("   instrument/timestamp-quantization state) is NOT DECIDED and")
P("   the CAUSE stays UNMEASURED -- this row adds a second-")
P("   instrument-channel constraint only; the underlying-")
P("   instrument-state COUNT stays outside (s220 1(b)).")

P()
P("8. THREE-STATE / RULE 4 / BAR (unchanged): every sample value")
P("   above is a named run's landed MEASURED QUANTITY on")
P("   aiueos-6600hs (Intel BMG G31) under the named instrument,")
P("   RE-PARSED from committed run-log bytes -- this slice measures")
P("   NOTHING new on hardware (no runs, no builds, NO GO stamp); the")
P("   share/distance arithmetic is DERIVED; the accelerator-targets")
P("   workgroup rows stay exactly as ADR-0358 left them (:measured?")
P("   false rows remain provisional -- NOT optimization evidence);")
P("   NO vendor optimization exists for Intel (or for any vendor)")
P("   and none follows from this confrontation.  RULE 4 unchanged:")
P("   NOTHING MOVES; the committed bracket stays EXACTLY (254,923,")
P("   255,045]; L9 binds at n=254,984 (C2 (c), D3 (v)); the MID-ONLY")
P("   NARROWING CLAIM stays SUSPENDED.  BAR NON-INTERFERENCE: NO")
P("   settle-bar-ledger line, NO day-slot consumption; the bar's")
P("   SETTLED INTERMEDIATE/MIXED verdict unmoved.")

P()
P("9. NAMED, NOT HIDDEN:")
P("   (a) the host criterion's bin width (and the robustness")
P("   family) is a frozen CHOICE made before any host per-sample")
P("   number existed -- the verdict is reported at every frozen")
P("   width whatever it shows, and width dependence is NAMED above.")
P("   (b) the letters come from the gpu_ticks channel (bound to")
P("   the committed s234 rows) -- the host channel does not define")
P("   its own groups.")
P("   (c) the committed s238 descriptive host rows (medians +")
P("   raw-support D_groups_host) are re-derived and bound here;")
P("   the s238 report's 'high-dimensional host noise' note is why")
P("   this row freezes a quantization instead of transplanting the")
P("   s234 raw-support criterion unchanged.")
P("   (d) OUTSIDE this universe (named, not hidden): the s237")
P("   kernel-variant arms and the s235 supplementary arms; every")
P("   cell except the reading cell (the queue names the reading")
P("   cell only).")

P()
P("10. NOT DONE (s240 carries exactly this list): the s216 identity")
P("    hazard's remaining residuals (standing, not queued): the")
P("    CAUSE of the sample-shape difference stays UNMEASURED and")
P("    UNDECIDED (this row added a second-instrument-channel")
P("    constraint; a cause-resolution act needs new hardware runs,")
P("    each with its own freeze -- standing, not queued); the")
P("    underlying-instrument-state COUNT stays outside (s220 1(b));")
P("    at N=75 the s235/s237 classifications carry NO noise model")
P("    and near-neither prevalence needs higher-N readings -- new")
P("    hardware runs, each with its own freeze (standing, not")
P("    queued); standing, not queued: any further counted-day slot")
P("    (each needs its own freeze) and the cross-day tail-movement")
P("    row.")
if width_robust:
    P("    QUEUED for s240: the host_ns channel's cross-cell shape")
    P("    extent under the same frozen quantization (this row's")
    P("    reading-cell confrontation extended over the 18 pipeline-")
    P("    ok cells, supplementary REPORT).")
else:
    P("    QUEUED for s240: a width-free host-channel shape")
    P("    confrontation at the reading cell (its criterion frozen")
    P("    before its own numbers) -- the primary verdict is width-")
    P("    dependent here and that dependence is the open row.")
P("    (JUN-55, JUN-59; Linear tracking JUN-499)")

P()
P(f"# host-shape s239 (host-shape-s239.py): "
  f"{CHECKS['ok']} ok / {CHECKS['failed']} failed")
print("\n".join(OUT))
sys.exit(0 if CHECKS["failed"] == 0 else 1)
