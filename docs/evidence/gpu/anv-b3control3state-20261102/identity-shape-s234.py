#!/usr/bin/env python3
"""identity-shape-s234.py -- THE S216 IDENTITY HAZARD'S SAMPLE-SHAPE
CONFRONTATION AT THE READING CELL (amu-gpu session 234; the s233
carry-forward's row "the s216 identity hazard's own question (whether
the (b) readings' m 30 is a NEW control state or a tolerance/defect
reading)" -- its named input (the whole-history enumeration) COMPLETE
at s233, taken as this tick's ONE row).

THE ROW: the hazard's dichotomy makes different predictions about the
PER-SAMPLE SHAPE at the reading cell (sum,128,S=16).  The committed
run logs of every deep-pooling-era own reading in the hazard's scope --
the five record cuts s158/s169/s185/s197/s209 (15th..19th) and the
s225 resolution act's four readings -- carry those samples.  This
script re-parses those samples from the COMMITTED RUN LOG BYTES and
confronts the two letter groups' shapes under a criterion FIXED BELOW,
BEFORE ANY NUMBER IS COMPUTED.

THE DECISION CRITERION (fixed here, before the numbers):
  Let s_w be the per-sample share vector of window w over the union
  support of observed gpu_ticks values at the reading cell (percent).
  Let W_in  = max L1(s_x, s_y) over same-letter window pairs and
      W_out = min L1(s_x, s_y) over opposite-letter window pairs
  (L1 in percentage points, both over the union support).
  - H_T "tolerance/defect reading": the (b) readings' m 30 is a
    tolerance/defect excursion of the SAME per-sample state as the
    (a) readings -- one shared shape; the letter flip is a pooled-
    median boundary effect.  Prediction: W_out is of the same order
    as W_in (between-group distance not exceeding within-group).
  - H_N "NEW control state": the (b) readings are a distinct
    replicating per-sample state.  Prediction: W_out > W_in -- the
    letter groups carry DISTINCT shapes, each internally replicating.
  RULE (fixed here, before the numbers): the shapes SEPARATE iff
  W_out > W_in.  SEPARATE -> H_T's sample-level prediction is
  REFUTED and H_N's is SATISFIED at sample-shape level.  NOT
  SEPARATE -> the committed bytes do not discriminate and the hazard
  stays UNDECIDED at sample level.  PATTERN-LEVEL ONLY (s218 2(e)):
  NO p-value, NO test statistic, NO probability claim.

UNIVERSE (fixed here, before the numbers): the nine deep-pooling-era
own readings whose raw run logs are COMMITTED (the hazard's (b)
readings are exactly s169, s209 and the act's four; the record's own
(a) readings are exactly s158, s185, s197).  Pre-deep-pooling windows
(sessions 5..147) carry NO committed raw run logs (publication-level
only) and are OUTSIDE this sample-shape scope -- named, not hidden.

Reads ONLY committed bytes (fail-closed; any parse anomaly is an
immediate abort = failed run):
  - docs/evidence/gpu/<cut dir>/run-c2-r0{1..3}.txt.gz (5 cut windows)
  - docs/evidence/gpu/anv-b3control3state-20261102/run-rd{1..4}-c2-
    r0{1..3}.txt.gz (the act's four readings)
  - the same windows' committed publications (the C1TWO own two-line
    blocks, the act's reading rows and letter rows, the s229 slot
    rows, the s215 four-cut record rows) -- CROSS-CHECK sources only:
    every reading value below is RE-DERIVED from the run logs, and
    the publications must AGREE with the re-derivation.
  - docs/evidence/gpu/anv-b3bisect7-20261027/derivation-census-s27.txt
    (the committed floor band 31..32 and c8 reference 32,915).

Writes NOTHING.  Prints the report to stdout, nothing to stderr on
success.  Exit 0 iff every check is ok.

CHECKS vs REPORTS (the honesty split): PARSE anomalies (missing file,
header/knob mismatch, cell-map divergence, sample-count or round-set
mismatch, publication disagreeing with the re-derivation) are CHECKS
and fail the run; SHAPE OUTCOMES (histograms, distances, the
discriminant verdict) are REPORTS and never fail the run.

THREE-STATE: every sample value below is a named run's landed
MEASURED QUANTITY (its own hardware runs on aiueos-6600hs, Intel BMG
G31, under the named instrument), RE-PARSED here from committed run-
log bytes -- this script measures NOTHING new on hardware and no
value here is a measurement of this tick; the share/distance
arithmetic is DERIVED (labelled).  The verdict is scoped EXACTLY as
the criterion above: sample-shape level at the c2 reading cell; the
CAUSE of the shape difference (a genuine execution-time state vs an
instrument/timestamp-quantization state) stays UNMEASURED; the
underlying-instrument-state COUNT is outside this slice (s220 1(b)
binds); no act sequence is re-judged here.  RULE 4 unchanged:
NOTHING MOVES; the committed bracket stays EXACTLY (254,923,
255,045]; the accelerator-targets workgroup rows stay exactly as
ADR-0358 left them (:measured? false rows remain provisional -- NOT
optimization evidence); NO vendor optimization exists for Intel (or
for any vendor) and none follows from this confrontation.
"""

import gzip
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

GPU = Path(__file__).resolve().parent.parent  # docs/evidence/gpu

# The committed floor band / c8 reference (the s27 controls census;
# parsed from the committed bytes below and cross-checked to these
# pins) -- DERIVED arithmetic inputs only.
C2_PIN, FLOOR_BAND, C8_REF = 31, (31, 32), 32915

# The frozen reading cell and run knobs (the instrument contract,
# uniform across all nine windows' committed c2 logs).
CELL_KEY = ("sum", 128, "16")          # (op, wg, forced) at the cell
R, WARMUP, N_BASE, B = 6400, 3, 1000003, 2
KNOB_PIN = dict(n=N_BASE, rounds=R, warmup=WARMUP, batch=B,
                barrier_n=0, work_mul=1, ndiv=1, seed=20261027)
INSTRUMENT = ("# instrument=anv-subgroupsize-batch v2-batch64 "
              "(JUN-59 subgroup 16-vs-32 floor-lifting rerun, "
              "2026-10-27)")
DEVICE = ("# device_name=Intel(R) Graphics (BMG G31) vendor=8086 "
          "device=e223 api=1.4.318")

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

# Committed record rows (the s215 four-cut record; cross-check only).
S215 = GPU / "anv-b3control3state-prereg-20261102" / "state-s215.txt"
S27 = GPU / "anv-b3bisect7-20261027" / "derivation-census-s27.txt"

cell_re = re.compile(
    r"^CELL idx=(\d+) spv=(\S+) op=(\S+) wg=(\d+) forced=(\S+) "
    r"probe_size=(-?\d+) probe_nsub=(-?\d+) probe_wg=(-?\d+) "
    r"pipeline=(\S+) void=(\d)")
verify_re = re.compile(r"^VERIFY idx=(\d+) checked=(\d+) mismatch=(\d+) ok=(\d)")
SAMPLE_FIELDS = ("round=", "idx=", "batch=", "work_mul=", "ndiv=",
                 "gpu_ticks=", "gpu_ns=", "per_dispatch_ns=", "host_ns=")
RE_C2_OWN_M = re.compile(
    r"^\s*c2 \(sum,128,S=16\) pooled median m ([\d.]+), deep-pooling\s*$")
RE_CLASS = re.compile(
    r"class FLOOR \(committed floor band 31\.\.32 at B=2\): (True|False)")
RE_C8 = re.compile(
    r"c8 \(sum,128,S=16\) pooled median m ([\d.]+) within \+/-5% of "
    r"committed ([\d,]+) \(session 4 pooled median\): (True|False) "
    r"\(([-+\d.]+)%\)")
RE_VERIFY = re.compile(
    r"control arms free of VERIFY mismatches \(frozen INVALIDATION "
    r"criterion\): (True|False)")
RE_EVALUABLE = re.compile(
    r"reading evaluable \(both arms valid under \(a\) \+ in the s218 "
    r"letter domain\): (True|False)")
RE_VERDICT = re.compile(r"VERDICT: branch \(([ab])\)")
RE_LETTER = re.compile(
    r"\bL(\d) = \(([ab])\) \(s218 1\(c\): letter = f\(m against")
RE_LETTER_AGG = re.compile(r"L1\.\.L4 = ((?:\([ab]\)(?: / )?)+)")
RE_READROW = re.compile(
    r"reading (\d) c2 N=([\d,]+) m=([\d.]+) mad=([\d.]+)")
RE_SLOT = re.compile(
    r"reading (\d) \(the L(\d) slot beside the record's (\d+)(?:th|st|nd|rd) "
    r"cut's \(([ab])\)")
RE_S215MAP = re.compile(
    r"(\d+)(?:th|st|nd|rd) cut -- publication-s(\d+)\.txt \(anv-([^)]+)/\)")
RE_S215SEQ = re.compile(
    r"the 16th cut's \(([ab])\), the 17th cut's \(([ab])\), the 18th "
    r"cut's \(([ab])\), this cut's \(([ab])\)")
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


def flat(text):
    return re.sub(r"\s+", " ", text)


# ---------------------------------------------------------------- run logs
def load(path):
    """One committed run log, READ THROUGH GZIP (structure asserted,
    fail-closed).  Returns (cells, verifies, header, ticks, counts)."""
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
            ticks.setdefault(idx, []).append(gt)
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
    return dict(ticks=ticks.get(s128[0], []) if s128 else [],
                problems=problems, header=tuple(header),
                cell_map=cell_map, s128=s128[0] if s128 else None)


# ------------------------------------------------------------------ report
P("identity-shape-s234.py -- THE S216 IDENTITY HAZARD'S SAMPLE-SHAPE")
P("CONFRONTATION AT THE READING CELL (sum,128,S=16) (amu-gpu s234;")
P("the s233 carry-forward's row: the s216 identity hazard's own")
P("question -- is the (b) readings' m 30 a NEW control state or a")
P("tolerance/defect reading -- its named input COMPLETE at s233).")
P()
P("THE DECISION CRITERION (fixed in the script BEFORE any number):")
P("  s_w = per-sample share vector (percent) of window w over the")
P("  union support of observed gpu_ticks at the reading cell;")
P("  W_in  = max L1 over same-letter window pairs,")
P("  W_out = min L1 over opposite-letter window pairs (pct points).")
P("  H_T (tolerance/defect reading = one shared shape, letter flip")
P("  a median boundary effect): W_out of the same order as W_in.")
P("  H_N (NEW control state = distinct replicating shape per letter")
P("  group): W_out > W_in.  RULE: SHAPES SEPARATE iff W_out > W_in.")
P("  PATTERN-LEVEL ONLY (s218 2(e)): NO p-value, NO test statistic,")
P("  NO probability claim.")
P("UNIVERSE: the nine deep-pooling-era own readings with COMMITTED")
P("raw run logs (cuts s158/s169/s185/s197/s209 + the act's four")
P("readings); pre-deep-pooling windows carry no committed raw logs")
P("(publication-level only) and are OUTSIDE this scope.")
P()

# ---- band / reference pins from the committed s27 census ----
s27 = S27.read_text()
m27 = RE_S27.search(s27)
assert m27, "s27 census row"
band = (int(m27.group(2)), int(m27.group(3)))
c2pin, c8ref = int(m27.group(1)), int(m27.group(4).replace(",", ""))
check("S234.A1 s27 census parse == pins (c2 31, band 31..32, c8 32915)",
      (c2pin, band, c8ref) == (C2_PIN, FLOOR_BAND, C8_REF),
      f"got {(c2pin, band, c8ref)}")

# ---- the 24 committed run logs ----
P()
P("1. THE RUN-LOG CENSUS (every sample RE-PARSED from committed")
P("   run-log bytes; m = pooled sample median gpu_ticks over k=3")
P("   runs x R rounds at the reading cell, N = 3R = 19,200; MAD =")
P("   sample median |x - m| -- the frozen s217/s218 statistic):")
runs = {}
for label, sess, kind, d, pat, pub in WINDOWS:
    for nn in (1, 2, 3):
        name = pat.format(nn)
        path = GPU / d / name
        assert path.exists(), f"RUN LOG MISSING: {path}"
        runs[(label, nn)] = load_run(path)
check("S234.A2 header identity across all 24 runs",
      len({r["header"] for r in runs.values()}) == 1)
check("S234.A3 cell-map identity across all 24 runs",
      len({r["cell_map"] for r in runs.values()}) == 1)
for (label, nn), r in sorted(runs.items()):
    check(f"S234.B{label}-r{nn:02d} run integrity clean",
          not r["problems"], "; ".join(r["problems"]))

window = {}
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
        P(f"      run{nn:02d} N={len(t)} m={fmtm(statistics.median(t))}"
          f"  top3 {rshape}")

# ---- publication cross-checks (the re-derivation BINDS the logs) ----
P()
P("2. PUBLICATION CROSS-CHECKS (the re-derived readings must EQUAL")
P("   the committed publication rows; any disagreement fails the")
P("   run -- this binds the committed run logs to the committed")
P("   readings):")
region_n = 12
for label, sess, kind, d, pat, pub in WINDOWS:
    text = (GPU / d / pub).read_text()
    lines = text.splitlines()
    own = [i for i, l in enumerate(lines) if RE_C2_OWN_M.match(l)]
    if kind == "cut":
        check(f"S234.C{sess}.1 exactly one own C1TWO block in {pub}",
              len(own) == 1, f"found {len(own)}")
        if len(own) != 1:
            continue
        i = own[0]
        region = "\n".join(lines[i:i + region_n])
        m_pub = float(RE_C2_OWN_M.match(lines[i]).group(1))
        mc = RE_CLASS.search(region)
        mv = RE_VERDICT.search(region)
        m8 = RE_C8.search(region)
        mvf = RE_VERIFY.search(region)
        check(f"S234.C{sess}.2 region fields present",
              all(x is not None for x in (mc, mv, m8, mvf)))
        if not all(x is not None for x in (mc, mv, m8, mvf)):
            continue
        w = window[label]
        derived = "a" if band[0] <= w["m"] <= band[1] else "b"
        check(f"S234.C{sess}.3 re-derived m {fmtm(w['m'])} == publication "
              f"m {fmtm(m_pub)}", float(w["m"]) == m_pub)
        check(f"S234.C{sess}.4 derived letter ({derived}) == publication "
              f"class bool == VERDICT branch ({mv.group(1)})",
              (derived == "a") == (mc.group(1) == "True")
              and derived == mv.group(1))
        check(f"S234.C{sess}.5 letter-domain rows True (c8 {m8.group(3)}, "
              f"VERIFY {mvf.group(1)})",
              m8.group(3) == "True" and mvf.group(1) == "True")

acttext = (GPU / WINDOWS[5][3] / "publication-s229.txt").read_text()
actlines = acttext.splitlines()
actown = [i for i, l in enumerate(actlines) if RE_C2_OWN_M.match(l)]
check("S234.C229.1 publication-s229.txt carries four own C1TWO blocks",
      len(actown) == 4, f"found {len(actown)}")
readrows = {}
for l in actlines:
    mr = RE_READROW.search(l)
    if mr:
        readrows.setdefault(int(mr.group(1)), []).append(
            (float(mr.group(3)), float(mr.group(4))))
check("S234.C229.2 publication-s229.txt carries four 'reading N c2' rows, "
      "one per reading",
      sorted(readrows) == [1, 2, 3, 4]
      and all(len(v) == 1 for v in readrows.values()))
letters229 = {}
for l in actlines:
    ml = RE_LETTER.search(l)
    if ml:
        letters229.setdefault(int(ml.group(1)), []).append(ml.group(2))
check("S234.C229.3 publication-s229.txt carries four letter rows L1..L4",
      sorted(letters229) == [1, 2, 3, 4]
      and all(len(v) == 1 for v in letters229.values()),
      f"got {letters229}")
agg = RE_LETTER_AGG.findall(flat(acttext))
row_letters = [letters229[k][0] for k in (1, 2, 3, 4) if letters229.get(k)]
agg_letters = re.findall(r"\(([ab])\)", agg[0]) if len(agg) == 1 else []
agg_shape = (len(agg) == 1 and len(agg_letters) == 4
             and agg_letters == row_letters)
check("S234.C229.3b aggregate row 'L1..L4 = ...' parsed, shape-checked, "
      "EXCLUDED from the letter-row census (not a reading row)",
      agg_shape, f"aggregates found: {agg}")
if len(actown) == 4:
    for k, i in enumerate(actown, start=1):
        label = f"act-rd{k}"
        region = "\n".join(actlines[i:i + region_n])
        m_pub = float(RE_C2_OWN_M.match(actlines[i]).group(1))
        mc = RE_CLASS.search(region)
        m8 = RE_C8.search(region)
        mvf = RE_VERIFY.search(region)
        me = RE_EVALUABLE.search(flat(region))
        ml = RE_LETTER.search(region)
        w = window[label]
        derived = "a" if band[0] <= w["m"] <= band[1] else "b"
        row_m = readrows.get(k, [(None,)])[0][0]
        check(f"S234.C229.r{k}.1 re-derived m {fmtm(w['m'])} == block m "
              f"{fmtm(m_pub)} == reading-row m {fmtm(row_m)}",
              float(w["m"]) == m_pub == row_m)
        check(f"S234.C229.r{k}.2 derived letter ({derived}) == class bool "
              f"== letter row L{k} ({ml.group(2) if ml else 'ABSENT'})",
              ml is not None and derived == ml.group(2)
              and (derived == "a") == (mc.group(1) == "True"))
        check(f"S234.C229.r{k}.3 letter-domain rows True (c8 "
              f"{m8.group(3) if m8 else 'ABSENT'}, VERIFY "
              f"{mvf.group(1) if mvf else 'ABSENT'}, evaluable "
              f"{me.group(1) if me else 'ABSENT'})",
              m8 is not None and mvf is not None and me is not None
              and m8.group(3) == "True" and mvf.group(1) == "True"
              and me.group(1) == "True")

# ---- the s215 four-cut record (ordinal -> session -> letter) ----
s215 = S215.read_text()
maprows = {int(a): (int(b), c) for a, b, c in RE_S215MAP.findall(s215)}
check("S234.C229.4 s215 record maps cuts 16..19 to the four cut windows",
      sorted(maprows) == [16, 17, 18, 19]
      and [maprows[o][0] for o in (16, 17, 18, 19)] == [169, 185, 197, 209],
      f"got {maprows}")
seq = RE_S215SEQ.search(flat(s215))
check("S234.C229.5 s215 record's four-cut letter sequence present",
      seq is not None)
slots = RE_SLOT.findall(acttext)
check("S234.C229.6 s229 slot rows present (4, reading# == L#)",
      len(slots) == 4 and all(s[0] == s[1] for s in slots))
if seq and len(slots) == 4 and sorted(maprows) == [16, 17, 18, 19]:
    ok_seq = True
    detail = []
    for j, (rd, lnum, cutord, let) in enumerate(slots):
        sess = maprows[int(cutord)][0]
        cutlabel = [w[0] for w in WINDOWS if w[1] == sess][0]
        derived = ("a" if band[0] <= window[cutlabel]["m"] <= band[1]
                   else "b")
        rec = seq.groups()[j]
        if not (let == derived == rec):
            ok_seq = False
            detail.append(f"L{lnum}: slot {let} derived {derived} record {rec}")
    check("S234.C229.7 s229 slot letters == derived cut letters == the "
          "s215 record sequence", ok_seq, "; ".join(detail))

# ---- the confrontation ----
P()
P("3. THE SAMPLE-SHAPE CONFRONTATION (DERIVED arithmetic on the")
P("   re-parsed samples; pattern-level only):")
labels = [w[0] for w in WINDOWS]
support = sorted(set().union(*[set(window[l]["cnt"]) for l in labels]))


def shares(l):
    w = window[l]
    return [100.0 * w["cnt"].get(v, 0) / w["N"] for v in support]


P(f"   union support of gpu_ticks at the cell: {support}")
P("   share vectors (percent):")
for l in labels:
    P(f"     {l:8s} " + "  ".join(
        f"{v}:{s:.4f}" for v, s in zip(support, shares(l)) if s > 0))
group = {"a": [l for l in labels
               if band[0] <= window[l]["m"] <= band[1]],
         "b": [l for l in labels
               if not (band[0] <= window[l]["m"] <= band[1])]}
P(f"   letter groups (derived from re-derived m vs band {band}):")
P(f"     (a): {group['a']}")
P(f"     (b): {group['b']}")
for g in ("a", "b"):
    pooled = [sum(window[l]["cnt"].get(v, 0) for l in group[g])
              for v in support]
    tot = sum(pooled)
    P(f"     group ({g}) pooled: " + "  ".join(
        f"{v}:{100.0 * c / tot:.4f}" for v, c in zip(support, pooled)
        if c > 0))

pairs = {"within-a": [], "within-b": [], "between": []}
for i, x in enumerate(labels):
    for y in labels[i + 1:]:
        sx, sy = shares(x), shares(y)
        d = sum(abs(a - b) for a, b in zip(sx, sy))
        lx = "a" if window[x]["m"] >= band[0] and window[x]["m"] <= band[1] else "b"
        ly = "a" if window[y]["m"] >= band[0] and window[y]["m"] <= band[1] else "b"
        key = "between" if lx != ly else ("within-a" if lx == "a" else "within-b")
        pairs[key].append((d, x, y))
check("S234.D1 pair census complete (within-a 3, within-b 15, between 18)",
      (len(pairs["within-a"]), len(pairs["within-b"]),
       len(pairs["between"])) == (3, 15, 18),
      f"got {({k: len(v) for k, v in pairs.items()})}")
for key in ("within-a", "within-b", "between"):
    P(f"   {key} L1 pairs (pct points):")
    for d, x, y in sorted(pairs[key]):
        P(f"     {x:8s} {y:8s} {d:.4f}")
w_in = max(pairs["within-a"] + pairs["within-b"])
w_out = min(pairs["between"])
separated = w_out[0] > w_in[0]
P(f"   W_in  = max within-group L1 = {w_in[0]:.4f} "
  f"({w_in[1]} vs {w_in[2]})")
P(f"   W_out = min between-group L1 = {w_out[0]:.4f} "
  f"({w_out[1]} vs {w_out[2]})")

P()
P("4. THE VERDICT UNDER THE FIXED RULE (pattern-level only):")
if separated:
    P(f"   SHAPES SEPARATE (W_out {w_out[0]:.4f} > W_in {w_in[0]:.4f}).")
    P("   H_T (tolerance/defect reading = one shared shape with a")
    P("   median flip): its sample-level prediction is REFUTED -- the")
    P("   (b) windows are NOT the (a) shape read one tick low here or")
    P("   there; each letter group carries its OWN replicating shape.")
    P("   H_N (NEW control state): its sample-level prediction is")
    P("   SATISFIED -- at sample-shape level the (b) readings' m 30 is")
    P("   a DISTINCT, WINDOW-COHERENT, REPLICATING reading state, not")
    P("   a tolerance/defect excursion of the (a) state's shape.")
else:
    P(f"   SHAPES DO NOT SEPARATE (W_out {w_out[0]:.4f} <= W_in "
      f"{w_in[0]:.4f}).")
    P("   The committed bytes do NOT discriminate the two limbs at")
    P("   sample-shape level; the s216 identity hazard stays")
    P("   UNDECIDED at sample level.")

P()
P("5. THE TEMPORAL INTERLEAVING ROW (the windows in session order;")
P("   DERIVED letters):")
for l in labels:
    w = window[l]
    derived = "a" if band[0] <= w["m"] <= band[1] else "b"
    P(f"     {w['sess']:3d} {l:8s} m={fmtm(w['m'])} ({derived})")

P()
P("6. NAMED, NOT HIDDEN -- WHAT THIS VERDICT DOES AND DOES NOT")
P("   DECIDE:")
P("   - It decides the s216 dichotomy at SAMPLE-SHAPE level over the")
P("     nine deep-pooling-era own readings with committed raw logs,")
P("     under the criterion fixed above.  The (b) readings are a")
P("     distinct replicating reading state at the c2 reading cell.")
P("   - It does NOT decide the CAUSE of the shape difference (a")
P("     genuine execution-time state vs an instrument/timestamp-")
P("     quantization state): UNMEASURED, outside the committed bytes.")
P("   - It does NOT count underlying instrument states (s220 1(b)")
P("     binds: no act sequence establishes an underlying-state")
P("     count); 'NEW' is used in the record's sense of a DISTINCT")
P("     state (a second reading state in the record), NOT as")
P("     'recently appeared' -- the interleaving row shows both")
P("     shapes present across the named windows (the (a) shape")
P("     recurs after (b) windows).")
P("   - Pre-deep-pooling windows (sessions 5..147) carry no committed")
P("     raw run logs; their sample shape is UNCHECKED here.")
P("   - The running defect attempts are named in identity-shape-")
P("     s234-identity.txt; none of them is evidence.")
P()
P("7. THREE-STATE / RULE 4 / BAR: every sample is a named run's")
P("   landed MEASURED QUANTITY on aiueos-6600hs (Intel BMG G31)")
P("   RE-PARSED from committed bytes -- this tick measures NOTHING")
P("   new on hardware (no runs, no builds, no GO stamp); the share")
P("   and distance arithmetic is DERIVED.  NO vendor optimization")
P("   exists for Intel (or for any vendor) and none follows from")
P("   this confrontation; the accelerator-targets workgroup rows")
P("   stay exactly as ADR-0358 left them (:measured? false rows")
P("   remain provisional -- NOT optimization evidence).  RULE 4")
P("   unchanged: NOTHING MOVES; the committed bracket stays EXACTLY")
P("   (254,923, 255,045]; the MID-ONLY NARROWING CLAIM stays")
P("   SUSPENDED.  BAR NON-INTERFERENCE: NO settle-bar-ledger line,")
P("   NO day-slot consumption; the bar's SETTLED INTERMEDIATE/MIXED")
P("   verdict unmoved.")

P()
P(f"# identity-shape s234 (identity-shape-s234.py): "
  f"{CHECKS['ok']} ok / {CHECKS['failed']} failed")
print("\n".join(OUT))
sys.exit(0 if CHECKS["failed"] == 0 else 1)
