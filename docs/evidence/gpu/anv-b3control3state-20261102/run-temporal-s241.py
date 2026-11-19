#!/usr/bin/env python3
"""run-temporal-s241.py -- THE S216 CAUSE RESIDUAL'S RUN-LEVEL AND
WITHIN-RUN TEMPORAL CONSTRAINT ON THE GPU_TICKS CHANNEL (amu-gpu
session 241; the s240 carry-forward's FIRST STANDING ROW -- "the
CAUSE of the sample-shape difference stays UNMEASURED and UNDECIDED
... a cause-resolution act needs new hardware runs, each with its own
freeze -- standing, not queued" -- TAKEN AS ITS ROW under the
recorded chain precedent (state-s225.txt: s118/s123/s125/s126/s129/
s143 all took carry-forward (a) despite the stand-down clause; the
s238 precedent itself: the s237 carry-forward's first standing row
taken as a CONSTRAINT row), as a CONSTRAINT row on the FIRST
instrument channel (gpu_ticks), whose committed-bytes confrontation
so far is pooled-window level (s234), whole-tree census level
(s235), kernel-variant arms (s237), cross-cell extent (s238) and
the second-instrument-channel rows (s239/s240) -- but NEVER at run
level or within-run level.  This row adds the TEMPORAL TIMESCALE
constraint: at what granularity inside a single run's 6,400-round
sample stream do the two letter-group shapes occur.

THE FROZEN DECOMPOSITION CRITERION (fixed here, BEFORE any number):
  UNIT: a RUN (one committed run log's 6,400 reading-cell samples,
  in round order 0..6399) or a BLOCK (a run's rounds split into K
  equal consecutive blocks; block j of K = rounds j*R/K .. (j+1)*
  R/K - 1, R = 6400).
  REFERENCES (fixed here): R_a = pooled per-sample share vector of
  the committed (a) windows, R_b = pooled of the committed (b)
  windows, over the union support of observed gpu_ticks at the
  reading cell (percent).  The letter groups and both reference rows
  are RE-DERIVED from the run logs and BOUND to the committed s234
  report rows before any temporal number is read.
  CLASSIFICATION (fixed here): for a unit u with share vector s over
  the union support: D_a = L1(s, R_a), D_b = L1(s, R_b); CLASS(u) =
  'a' iff D_a < D_b, 'b' iff D_b < D_a, UNDECIDED iff equal.  NEAR-
  NEITHER flag (REPORT-ONLY, the s235 flag shape) iff min(D_a, D_b)
  > W_in, with W_in re-derived and bound to the committed s234 row.
  TEMPORAL CUTS (fixed here): run-level (K=1) and the frozen
  within-run family K in {8, 16, 32, 64} (blocks of 800/400/200/100
  rounds); EVERY cut of the family is reported whatever it shows
  (the s239 width-robustness precedent shape).
  TRANSITION ROW (fixed here): for each run and K, the block-class
  sequence in round order and T = the number of adjacent block pairs
  whose classes differ (UNDECIDED differs from either neighbour
  class; two adjacent UNDECIDED blocks do not count).  A run is
  CLASS-UNIFORM at K iff T = 0 and no UNDECIDED block.
  CONSTRAINT SHAPE (fixed here): if every run is class-uniform at
  every cut of the family and every run's class equals its window's
  letter, the (a)/(b) difference's temporal locus is AT RUN
  GRANULARITY OR COARSER in this universe and the sub-run-switching
  variant of EITHER cause candidate is contradicted at 100-round
  granularity; any other outcome is reported with its counts and the
  finest cut at which transitions appear.  Either way the row is a
  CONSTRAINT row only (the s238 shape): the dichotomy (a genuine
  execution-time state vs an instrument/timestamp-quantization
  state) is NOT DECIDED here and the CAUSE stays UNMEASURED.
  PATTERN-LEVEL ONLY (s218 2(e)): NO p-value, NO test statistic,
  NO probability claim.

UNIVERSE (fixed here): the s234 nine-window universe exactly -- the
nine deep-pooling-era own readings with COMMITTED raw run logs (the
record cuts s158/s169/s185/s197/s209 + the s225 resolution act's
four readings), 27 committed c2 run logs at the reading cell
(sum,128,S=16).  Pre-deep-pooling windows (sessions 5..147) carry
no committed raw run logs and are OUTSIDE this scope; the s237
kernel-variant arms and the s235 supplementary arms are OUTSIDE.

Reads ONLY committed bytes (fail-closed; any parse anomaly is an
immediate abort = failed run):
  - the 27 run logs of the s234 WINDOWS list
  - docs/evidence/gpu/anv-b3bisect7-20261027/derivation-census-s27.txt
    (the committed floor band 31..32 pin)
  - docs/evidence/gpu/anv-b3control3state-20261102/identity-shape-
    s234-run1.txt (the committed s234 report rows -- the BIND
    target: the re-derived rows must EQUAL these rows)

Writes NOTHING.  Prints the report to stdout, nothing to stderr on
success.  Exit 0 iff every check is ok.

CHECKS vs REPORTS (the honesty split): PARSE anomalies and BIND
mismatches (missing file, header/knob divergence, sample/round
miscount, a re-derived row differing from the committed s234 row)
are CHECKS and fail the run; CLASSIFICATIONS, sequences, transition
counts and the timescale constraint are REPORTS and never fail the
run.

THREE-STATE: every sample value below is a named run's landed
MEASURED QUANTITY (its own hardware runs on aiueos-6600hs, Intel
BMG G31, under the named instrument), RE-PARSED here from committed
run-log bytes -- this script measures NOTHING new on hardware and no
value here is a measurement of this tick; the share/distance/
sequence arithmetic is DERIVED (labelled).  The underlying-
instrument-state COUNT is outside this slice (s220 1(b) binds).
RULE 4 unchanged: NOTHING MOVES; the committed bracket stays EXACTLY
(254,923, 255,045]; L9 binds at n=254,984 (C2 (c), D3 (v)); the
MID-ONLY NARROWING CLAIM stays SUSPENDED; the accelerator-targets
workgroup rows stay exactly as ADR-0358 left them (:measured? false
rows remain provisional -- NOT optimization evidence); NO vendor
optimization exists for Intel (or for any vendor) and none follows
from this constraint.
"""

import gzip
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

GPU = Path(__file__).resolve().parent.parent  # docs/evidence/gpu
HERE = Path(__file__).resolve().parent

# The committed floor band (the s27 controls census; parsed from the
# committed bytes below and cross-checked to this pin).
C2_PIN, FLOOR_BAND, C8_REF = 31, (31, 32), 32915

# The frozen reading cell and run knobs (the instrument contract).
CELL_KEY = ("sum", 128, "16")          # (op, wg, forced) at the cell
R, WARMUP, N_BASE, B = 6400, 3, 1000003, 2
KNOB_PIN = dict(n=N_BASE, rounds=R, warmup=WARMUP, batch=B,
                barrier_n=0, work_mul=1, ndiv=1, seed=20261027)
INSTRUMENT = ("# instrument=anv-subgroupsize-batch v2-batch64 "
              "(JUN-59 subgroup 16-vs-32 floor-lifting rerun, "
              "2026-10-27)")
DEVICE = ("# device_name=Intel(R) Graphics (BMG G31) vendor=8086 "
          "device=e223 api=1.4.318")

# The frozen within-run cut family (blocks of 800/400/200/100 rounds).
K_FAMILY = (8, 16, 32, 64)

# (label, session, kind, run dir, run name pattern, publication)
WINDOWS = [
    ("s158",   158, "cut", "anv-b3bisect15-20261101",
     "run-c2-r0{}.txt.gz", "publication-s158.txt"),
    ("s169",   169, "cut", "anv-b3bisect16-20261101",
     "run-c2-r0{}.txt.gz", "publication-s169.txt"),
    ("s185",   185, "cut", "anv-b3bisect17-20261101",
     "run-c2-r0{}.txt.gz", "publication-s185.txt"),
    ("s197",   197, "cut", "anv-b3bisect18-20261101",
     "run-c2-r0{}.txt.gz", "publication-s197.txt"),
    ("s209",   209, "cut", "anv-b3bisect19-20261102",
     "run-c2-r0{}.txt.gz", "publication-s209.txt"),
    ("act-rd1", 229, "act", "anv-b3control3state-20261102",
     "run-rd1-c2-r0{}.txt.gz", "publication-s229.txt"),
    ("act-rd2", 229, "act", "anv-b3control3state-20261102",
     "run-rd2-c2-r0{}.txt.gz", "publication-s229.txt"),
    ("act-rd3", 229, "act", "anv-b3control3state-20261102",
     "run-rd3-c2-r0{}.txt.gz", "publication-s229.txt"),
    ("act-rd4", 229, "act", "anv-b3control3state-20261102",
     "run-rd4-c2-r0{}.txt.gz", "publication-s229.txt"),
]

S27 = GPU / "anv-b3bisect7-20261027" / "derivation-census-s27.txt"
S234_REPORT = HERE / "identity-shape-s234-run1.txt"

cell_re = re.compile(
    r"^CELL idx=(\d+) spv=(\S+) op=(\S+) wg=(\d+) forced=(\S+) "
    r"probe_size=(-?\d+) probe_nsub=(-?\d+) probe_wg=(-?\d+) "
    r"pipeline=(\S+) void=(\d)")
verify_re = re.compile(r"^VERIFY idx=(\d+) checked=(\d+) mismatch=(\d+) ok=(\d)")
SAMPLE_FIELDS = ("round=", "idx=", "batch=", "work_mul=", "ndiv=",
                 "gpu_ticks=", "gpu_ns=", "per_dispatch_ns=", "host_ns=")
RE_S27 = re.compile(
    r"committed controls: c2 (\d+) \(floor band (\d+)\.\.(\d+)\); "
    r"c8 ([\d,]+) \(session 4 pooled median\)")
RE_KNOB = re.compile(
    r"n=(\d+) rounds=(\d+) warmup=(\d+) batch=(\d+) barrier_n=(\d+) "
    r"work_mul=(\d+) ndiv=(\d+) seed=(\d+)")

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
    fail-closed).  Returns (cells, verifies, header, ticks, counts,
    rounds_by_idx) -- ticks keep SAMPLE order (round order)."""
    cells, verifies, header = {}, [], []
    ticks, counts, rounds = {}, {}, {}
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
            int(f[9][8:])
            assert (int(f[3][6:]) == B and int(f[4][9:]) == 1
                    and int(f[5][5:]) == 1), line
            ticks.setdefault(idx, []).append((rnd, gt))
            counts[idx] = counts.get(idx, 0) + 1
            rounds.setdefault(idx, set()).add(rnd)
    return cells, verifies, header, ticks, counts, rounds


def load_run(path):
    cells, verifies, header, ticks, counts, rounds = load(path)
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
    seq = ticks.get(s128[0], []) if s128 else []
    round_order_ok = [r for r, _ in seq] == list(range(R))
    return dict(seq=seq,
                ticks=[t for _, t in seq],
                problems=problems, header=tuple(header),
                cell_map=cell_map, s128=s128[0] if s128 else None,
                round_order_ok=round_order_ok)


# ------------------------------------------------------------------ report
P("run-temporal-s241.py -- THE S216 CAUSE RESIDUAL'S RUN-LEVEL AND")
P("WITHIN-RUN TEMPORAL CONSTRAINT ON THE GPU_TICKS CHANNEL (amu-gpu")
P("s241; the s240 carry-forward's FIRST STANDING ROW -- the CAUSE of")
P("the sample-shape difference -- TAKEN AS ITS ROW under the s238")
P("precedent, as a CONSTRAINT row on the first instrument channel).")
P()
P("THE FROZEN DECOMPOSITION CRITERION (fixed in the script BEFORE")
P("  any number):")
P("  UNIT: a RUN (6,400 reading-cell samples in round order) or a")
P("  BLOCK (K equal consecutive round blocks).")
P("  REFERENCES: R_a / R_b = pooled share vectors of the committed")
P("  (a) / (b) windows over the union support; re-derived and bound")
P("  to the committed s234 report rows before any temporal number.")
P("  CLASS: nearest reference by L1 of share vectors (percent over")
P("  the union support); tie -> UNDECIDED; NEAR-NEITHER flag")
P("  (report-only) iff min(D_a,D_b) > W_in (bound to the committed")
P("  s234 row).")
P("  CUTS: run-level + the frozen family K=8,16,32,64 (blocks of")
P("  800/400/200/100 rounds), every cut reported whatever it shows.")
P("  TRANSITION ROW: block-class sequence per run per K; T =")
P("  adjacent pairs differing (UNDECIDED differs from either")
P("  neighbour; two UNDECIDED neighbours do not count); CLASS-")
P("  UNIFORM iff T=0 and no UNDECIDED block.")
P("  CONSTRAINT SHAPE: class-uniform at every cut with every run's")
P("  class == its window's letter -> temporal locus AT RUN")
P("  GRANULARITY OR COARSER and the sub-run-switching variant of")
P("  EITHER cause candidate contradicted at 100-round granularity;")
P("  any other outcome reported with its counts.  CONSTRAINT row")
P("  only: the dichotomy (execution-time state vs instrument/")
P("  timestamp-quantization state) NOT DECIDED, CAUSE UNMEASURED.")
P("  PATTERN-LEVEL ONLY (s218 2(e)): NO p-value, NO test statistic,")
P("  NO probability claim.")
P("UNIVERSE: the s234 nine-window universe exactly -- 27 committed")
P("  c2 run logs at the reading cell (sum,128,S=16); pre-deep-")
P("  pooling windows, kernel-variant arms and supplementary arms")
P("  are OUTSIDE this scope.")
P()

# ---- band pin from the committed s27 census ----
s27 = S27.read_text()
m27 = RE_S27.search(s27)
assert m27, "s27 census row"
band = (int(m27.group(2)), int(m27.group(3)))
c2pin, c8ref = int(m27.group(1)), int(m27.group(4).replace(",", ""))
check("S241.A1 s27 census parse == pins (c2 31, band 31..32, c8 32915)",
      (c2pin, band, c8ref) == (C2_PIN, FLOOR_BAND, C8_REF),
      f"got {(c2pin, band, c8ref)}")

# ---- the 27 committed run logs ----
P()
P("1. THE RUN-LOG CENSUS (every sample RE-PARSED from committed")
P("   run-log bytes in ROUND ORDER; m = pooled sample median")
P("   gpu_ticks, MAD = sample median |x - m| -- the frozen s217/s218")
P("   statistic; the rows below are the s234 forms, re-derived):")
runs = {}
for label, sess, kind, d, pat, pub in WINDOWS:
    for nn in (1, 2, 3):
        name = pat.format(nn)
        path = GPU / d / name
        assert path.exists(), f"RUN LOG MISSING: {path}"
        runs[(label, nn)] = load_run(path)
check("S241.A2 header identity across all 27 runs",
      len({r["header"] for r in runs.values()}) == 1)
check("S241.A3 cell-map identity across all 27 runs",
      len({r["cell_map"] for r in runs.values()}) == 1)
for (label, nn), r in sorted(runs.items()):
    check(f"S241.B{label}-r{nn:02d} run integrity clean + round order exact",
          not r["problems"] and r["round_order_ok"],
          "; ".join(r["problems"] + ([] if r["round_order_ok"]
                                    else ["ROUND ORDER NOT 0..R-1"])))

window = {}
runrow = {}
for label, sess, kind, d, pat, pub in WINDOWS:
    xs = []
    for nn in (1, 2, 3):
        xs.extend(runs[(label, nn)]["ticks"])
    N = len(xs)
    m_ = statistics.median(xs)
    mad = statistics.median([abs(x - m_) for x in xs])
    cnt = Counter(xs)
    window[label] = dict(sess=sess, kind=kind, N=N, m=m_, mad=mad,
                         cnt=cnt, pub=pub, d=d)
    top = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    shape = "  ".join(f"{k}:{100.0 * v / N:.4f}%" for k, v in top)
    P(f"   {label:8s} sess={sess} N={N} m={fmtm(m_)} mad={fmtm(mad)}"
      f"  top3 {shape}")
    for nn in (1, 2, 3):
        t = runs[(label, nn)]["ticks"]
        rc = Counter(t)
        rt = sorted(rc.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
        rshape = "  ".join(f"{k}:{100.0 * v / len(t):.4f}%" for k, v in rt)
        runrow[(label, nn)] = (len(t), statistics.median(t), rshape)
        P(f"      run{nn:02d} N={len(t)} m={fmtm(statistics.median(t))}"
          f"  top3 {rshape}")

# ---- the confrontation shapes (derived; the s234 forms) ----
labels = [w[0] for w in WINDOWS]
support = sorted(set().union(*[set(window[l]["cnt"]) for l in labels]))


def shares_of(cnt, n):
    return [100.0 * cnt.get(v, 0) / n for v in support]


def shares(l):
    return shares_of(window[l]["cnt"], window[l]["N"])


group = {"a": [l for l in labels if band[0] <= window[l]["m"] <= band[1]],
         "b": [l for l in labels if not (band[0] <= window[l]["m"] <= band[1])]}
pooled = {}
for g in ("a", "b"):
    pc = Counter()
    for l in group[g]:
        pc.update(window[l]["cnt"])
    pooled[g] = pc

pairs = {"within-a": [], "within-b": [], "between": []}
for i, x in enumerate(labels):
    for y in labels[i + 1:]:
        sx, sy = shares(x), shares(y)
        dd = sum(abs(a - b) for a, b in zip(sx, sy))
        lx = "a" if band[0] <= window[x]["m"] <= band[1] else "b"
        ly = "a" if band[0] <= window[y]["m"] <= band[1] else "b"
        key = "between" if lx != ly else ("within-a" if lx == "a" else "within-b")
        pairs[key].append((dd, x, y))
w_in = max(pairs["within-a"] + pairs["within-b"])
w_out = min(pairs["between"])

# ---- BIND: the re-derived rows must EQUAL the committed s234 rows ----
P()
P("2. BINDS TO THE COMMITTED S234 REPORT ROWS (identity-shape-")
P("   s234-run1.txt; every re-derived row must appear there BYTE-")
P("   FORMATTED -- any disagreement fails the run; the bind runs")
P("   BEFORE any temporal number is reported):")
s234_text = S234_REPORT.read_text()
check("S241.C0 committed identity-shape-s234-run1.txt present and "
      "carries its own tail",
      "# identity-shape s234 (identity-shape-s234.py): 76 ok / 0 failed"
      in s234_text)

# census rows (9) + per-run rows (27)
for label, sess, kind, d, pat, pub in WINDOWS:
    w = window[label]
    top = sorted(w["cnt"].items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    shape = "  ".join(f"{k}:{100.0 * v / w['N']:.4f}%" for k, v in top)
    row = (f"   {label:8s} sess={sess} N={w['N']} m={fmtm(w['m'])} "
           f"mad={fmtm(w['mad'])}  top3 {shape}")
    check(f"S241.E{label} census row == committed s234 row",
          row in s234_text, f"derived: {row!r}")
    for nn in (1, 2, 3):
        n_, m_, sh = runrow[(label, nn)]
        rrow = f"      run{nn:02d} N={n_} m={fmtm(m_)}  top3 {sh}"
        check(f"S241.F{label}-r{nn:02d} per-run row == committed s234 row",
              rrow in s234_text, f"derived: {rrow!r}")

# support / share rows (1 + 9) / letter groups (2 + header) / pooled (2)
suprow = f"   union support of gpu_ticks at the cell: {support}"
check("S241.G0 union-support row == committed s234 row",
      suprow in s234_text, f"derived: {suprow!r}")
for l in labels:
    srow = f"     {l:8s} " + "  ".join(
        f"{v}:{s:.4f}" for v, s in zip(support, shares(l)) if s > 0)
    check(f"S241.G{l} share row == committed s234 row",
          srow in s234_text, f"derived: {srow!r}")
grow_h = f"   letter groups (derived from re-derived m vs band {band}):"
check("S241.G10 letter-groups header row == committed s234 row",
      grow_h in s234_text, f"derived: {grow_h!r}")
for g in ("a", "b"):
    lrow = f"     ({g}): {group[g]}"
    check(f"S241.G11{g} letter-group ({g}) row == committed s234 row",
          lrow in s234_text, f"derived: {lrow!r}")
    tot = sum(pooled[g].values())
    prow = f"     group ({g}) pooled: " + "  ".join(
        f"{v}:{100.0 * c / tot:.4f}" for v, c in zip(support,
                                                    [pooled[g][v] for v in
                                                     support])
        if c > 0)
    check(f"S241.G12{g} pooled group ({g}) row == committed s234 row",
          prow in s234_text, f"derived: {prow!r}")

# pair census + rows (36) + W_in/W_out + verdict
check("S241.H1 pair census counts (within-a 3, within-b 15, between 18)",
      (len(pairs["within-a"]), len(pairs["within-b"]),
       len(pairs["between"])) == (3, 15, 18),
      f"got {({k: len(v) for k, v in pairs.items()})}")
for key in ("within-a", "within-b", "between"):
    for dd, x, y in pairs[key]:
        prow = f"     {x:8s} {y:8s} {dd:.4f}"
        check(f"S241.I{x}-{y} pair row == committed s234 row",
              prow in s234_text, f"derived: {prow!r}")
wrow = (f"   W_in  = max within-group L1 = {w_in[0]:.4f} "
        f"({w_in[1]} vs {w_in[2]})")
check("S241.J1 W_in row == committed s234 row", wrow in s234_text,
      f"derived: {wrow!r}")
wrow2 = (f"   W_out = min between-group L1 = {w_out[0]:.4f} "
         f"({w_out[1]} vs {w_out[2]})")
check("S241.J2 W_out row == committed s234 row", wrow2 in s234_text,
      f"derived: {wrow2!r}")
vrow = (f"   SHAPES SEPARATE (W_out {w_out[0]:.4f} > W_in {w_in[0]:.4f})."
        if w_out[0] > w_in[0] else
        f"   SHAPES DO NOT SEPARATE (W_out {w_out[0]:.4f} <= W_in "
        f"{w_in[0]:.4f}).")
check("S241.J3 verdict row == committed s234 row", vrow in s234_text,
      f"derived: {vrow!r}")

# ---- references (now bound) ----
R_ref = {}
for g in ("a", "b"):
    tot = sum(pooled[g].values())
    R_ref[g] = [100.0 * pooled[g][v] / tot for v in support]


def classify(vec):
    da = sum(abs(a - b) for a, b in zip(vec, R_ref["a"]))
    db = sum(abs(a - b) for a, b in zip(vec, R_ref["b"]))
    if da < db:
        cls = "a"
    elif db < da:
        cls = "b"
    else:
        cls = "?"
    near = min(da, db) > w_in[0]
    return da, db, cls, near


# ---- the run-level classification (REPORTS) ----
P()
P("3. THE RUN-LEVEL CLASSIFICATION (frozen nearest-reference rule;")
P("   R_a / R_b and W_in bound to the committed s234 rows above;")
P("   D_a/D_b in pct points over the union support; NEAR-NEITHER")
P("   (report-only) iff min(D_a,D_b) > W_in "
  f"{w_in[0]:.4f}):")
P(f"   R_a (bound) = " + "  ".join(
    f"{v}:{s:.4f}" for v, s in zip(support, R_ref["a"]) if s > 0))
P(f"   R_b (bound) = " + "  ".join(
    f"{v}:{s:.4f}" for v, s in zip(support, R_ref["b"]) if s > 0))
run_class = {}
run_agree = {}
for label, sess, kind, d, pat, pub in WINDOWS:
    wl = "a" if band[0] <= window[label]["m"] <= band[1] else "b"
    classes = []
    for nn in (1, 2, 3):
        t = runs[(label, nn)]["ticks"]
        vec = shares_of(Counter(t), len(t))
        da, db, cls, near = classify(vec)
        run_class[(label, nn)] = (cls, near)
        classes.append(cls)
        P(f"     {label:8s} run{nn:02d} N={len(t)} m={fmtm(statistics.median(t))}"
          f"  D_a={da:.4f} D_b={db:.4f} class={cls}"
          f" near-neither={near}")
    agree = all(c == wl for c in classes)
    run_agree[label] = agree
    P(f"     {label:8s} runs {classes} window letter ({wl}) "
      f"all-agree={agree}")
n_a = sum(1 for v in run_class.values() if v[0] == "a")
n_b = sum(1 for v in run_class.values() if v[0] == "b")
n_u = sum(1 for v in run_class.values() if v[0] == "?")
n_nn = sum(1 for v in run_class.values() if v[1])
P(f"   run-level summary: class a {n_a} / b {n_b} / UNDECIDED {n_u}; "
  f"NEAR-NEITHER flags {n_nn} of 27 (report-only)")
P(f"   windows whose 3 runs all carry their window letter: "
  f"{sum(1 for v in run_agree.values() if v)} of 9")

# ---- the within-run block decomposition (REPORTS) ----
P()
P("4. THE WITHIN-RUN BLOCK DECOMPOSITION (the frozen family; each")
P("   row: the block-class sequence in round order, T = adjacent")
P("   differing pairs, CLASS-UNIFORM iff T=0 and no UNDECIDED;")
P("   block N = R/K; NEAR-NEITHER block counts report-only):")
seqs = {}
for K in K_FAMILY:
    blk = R // K
    P(f"   K={K} (blocks of {blk} rounds):")
    uniform_runs = 0
    mixed_runs = 0
    total_T = 0
    undec_blocks = 0
    nn_blocks = 0
    for label, sess, kind, d, pat, pub in WINDOWS:
        for nn in (1, 2, 3):
            t = runs[(label, nn)]["ticks"]
            classes = []
            n_near = 0
            n_und = 0
            for j in range(K):
                chunk = t[j * blk:(j + 1) * blk]
                assert len(chunk) == blk, (label, nn, K, j)
                vec = shares_of(Counter(chunk), len(chunk))
                _, _, cls, near = classify(vec)
                classes.append(cls)
                if cls == "?":
                    n_und += 1
                if near:
                    n_near += 1
            seqs[(K, label, nn)] = classes
            T = 0
            for j in range(K - 1):
                c1, c2 = classes[j], classes[j + 1]
                if c1 == "?" or c2 == "?":
                    if not (c1 == "?" and c2 == "?"):
                        T += 1
                elif c1 != c2:
                    T += 1
            uniform = (T == 0 and n_und == 0)
            if uniform:
                uniform_runs += 1
            else:
                mixed_runs += 1
            total_T += T
            undec_blocks += n_und
            nn_blocks += n_near
            P(f"     {label:8s} run{nn:02d} {''.join(classes)}  T={T} "
              f"uniform={uniform} undecided-blocks={n_und} "
              f"near-neither-blocks={n_near}")
    P(f"   K={K} summary: class-uniform runs {uniform_runs}/27; runs "
      f"carrying >=1 transition or UNDECIDED {mixed_runs}/27; total "
      f"transitions {total_T}; UNDECIDED blocks {undec_blocks} of "
      f"{27 * K}; NEAR-NEITHER blocks {nn_blocks} of {27 * K} "
      f"(report-only)")

# ---- the timescale constraint (CONSTRAINT rows only) ----
P()
P("5. THE TIMESCALE CONSTRAINT (CONSTRAINT rows only -- the s238")
P("   shape; the dichotomy NOT DECIDED and the CAUSE stays")
P("   UNMEASURED):")
all_uniform = all(
    len(set(seqs[(K, l, nn)])) == 1 and "?" not in seqs[(K, l, nn)]
    for K in K_FAMILY for l, _, _, _, _, _ in WINDOWS for nn in (1, 2, 3))
all_agree = all(run_agree.values()) and n_u == 0
if all_uniform and all_agree:
    P("   THE TWO SHAPES DO NOT ALTERNATE WITHIN ANY RUN'S 6,400-")
    P("   ROUND STREAM at any cut of the frozen family (100-round")
    P("   granularity included): all 27 runs are class-uniform at")
    P("   every K in {8,16,32,64} and every run carries its window's")
    P("   letter class.  The (a)/(b) difference's temporal locus is")
    P("   AT RUN GRANULARITY OR COARSER in this universe -- the state")
    P("   persists across a whole run (6,400 rounds) wherever it is")
    P("   present, and the sub-run-switching variant of EITHER cause")
    P("   candidate is CONTRADICTED at 100-round granularity.")
else:
    P("   WITHIN-RUN STRUCTURE IS PRESENT (counts above): the finest")
    P("   frozen cut at which a class transition or an UNDECIDED")
    P("   block appears is reported per run in section 4; the")
    P("   (a)/(b) difference's temporal locus is FINER THAN RUN")
    P("   GRANULARITY somewhere in this universe at the cuts shown.")
P("   What the row does NOT do: it does not decide the dichotomy")
P("   (a genuine execution-time state vs an instrument/timestamp-")
P("   quantization state).  Both candidates survive in their run-")
P("   persistent variants (an execution-time state whose episodes")
P("   span whole runs and a recording state whose episodes span")
P("   whole runs are EQUALLY LIVE here); a cause-resolution act")
P("   still needs new hardware runs, each with its own freeze.")
P("   The underlying-instrument-state COUNT stays outside (s220")
P("   1(b)).  PATTERN-LEVEL ONLY (s218 2(e)): NO p-value, NO test")
P("   statistic, NO probability claim; at block N=100..800 the")
P("   classification carries NO noise model (the s235 honesty")
P("   shape) and the NEAR-NEITHER counts are reported as-is.")

P()
P("6. NAMED, NOT HIDDEN -- SCOPE:")
P("   - The 27 committed c2 run logs of the s234 nine-window")
P("     universe at the reading cell (sum,128,S=16) ONLY; pre-deep-")
P("     pooling windows carry no committed raw run logs (outside);")
P("     the s237 kernel-variant arms (iter1/iter3/iter8/itervc8")
P("     spvs) and the s235 supplementary arms (anv-tsstage bb-b2/")
P("     tt-b2) are OUTSIDE this universe.")
P("   - gpu_ticks ONLY: the host_ns channel's committed-bytes")
P("     confrontation is complete (s239/s240) and is not re-opened")
P("     here.")
P("   - The defective dev attempts, if any, are named in run-")
P("     temporal-s241-identity.txt; none of them is evidence.")
P()
P("7. THREE-STATE / RULE 4 / BAR: every sample is a named run's")
P("   landed MEASURED QUANTITY on aiueos-6600hs (Intel BMG G31)")
P("   RE-PARSED from committed bytes -- this tick measures NOTHING")
P("   new on hardware (no runs, no builds, no GO stamp); the share,")
P("   distance and sequence arithmetic is DERIVED.  NO vendor")
P("   optimization exists for Intel (or for any vendor) and none")
P("   follows from this constraint; the accelerator-targets")
P("   workgroup rows stay exactly as ADR-0358 left them (:measured?")
P("   false rows remain provisional -- NOT optimization evidence).")
P("   RULE 4 unchanged: NOTHING MOVES; the committed bracket stays")
P("   EXACTLY (254,923, 255,045]; L9 binds at n=254,984 (C2 (c),")
P("   D3 (v)); the MID-ONLY NARROWING CLAIM stays SUSPENDED.  BAR")
P("   NON-INTERFERENCE: NO settle-bar-ledger line, NO day-slot")
P("   consumption; the bar's SETTLED INTERMEDIATE/MIXED verdict")
P("   unmoved.")

P()
P(f"# run-temporal s241 (run-temporal-s241.py): "
  f"{CHECKS['ok']} ok / {CHECKS['failed']} failed")
print("\n".join(OUT))
sys.exit(0 if CHECKS["failed"] == 0 else 1)
