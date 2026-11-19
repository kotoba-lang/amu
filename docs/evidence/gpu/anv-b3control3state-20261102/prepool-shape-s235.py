#!/usr/bin/env python3
"""prepool-shape-s235.py -- THE S216 IDENTITY HAZARD'S RESIDUAL-C
SAMPLE-SHAPE CENSUS OVER EVERY COMMITTED c2-RUNG RAW RUN LOG
(amu-gpu session 235; the s234 carry-forward's first named residual
"whether pre-deep-pooling windows share either sample shape is
UNCHECKED from committed bytes (no committed raw logs)" -- taken as
this tick's ONE row).

THE ROW AND THE PREMISE CORRECTION (named up front): the s234 scope
statement "Pre-deep-pooling windows (sessions 5..147) carry NO
committed raw run logs (publication-level only)" is CONTRADICTED by
the committed tree.  Committed raw run logs at the c2 control rung
(n=1,000,003, B=2, WM=1, NDIV=1 -- the rung whose readings the
record carries) with PER-SAMPLE reading-cell rows exist for far more
windows than the nine the s234 universe admitted; this script
enumerates them fail-closed and answers the residual's question
wherever the committed bytes allow.  The s234 nine-window sample-
shape conclusion itself is untouched: its references are RE-DERIVED
here from the same committed bytes and cross-checked against the
committed s234 report; every OTHER committed c2-rung window is then
classified against those references.

THE DECISION CRITERION (fixed here, before the numbers):
  Reference shapes: R_a = the pooled per-sample share vector of the
  committed (a) windows {s158, s185, s197}; R_b = that of the
  committed (b) windows {s169, s209, act-rd1..4} (each window's
  samples re-derived from its committed run logs; the letters
  re-derived from the pooled median m against the committed floor
  band 31..32 at B=2 and bound to the committed record letters).
  For every OTHER committed c2-rung window w (its reading-cell
  samples pooled over its own committed runs):
    D_a(w) = L1(share_w, R_a), D_b(w) = L1(share_w, R_b)
    (percentage points over the union support of ALL windows).
  RULE (fixed here, before the numbers): w SHARES THE (a) SHAPE iff
  D_a < D_b; SHARES THE (b) SHAPE iff D_b < D_a; EXACT TIE ->
  UNDECIDED.  The margins are reported for every window.  FLAG
  (reported, never a class): NEAR-NEITHER iff min(D_a,D_b) exceeds
  W_in (the re-derived s234 max within-group L1).  PATTERN-LEVEL
  ONLY (s218 2(e)): NO p-value, NO test statistic, NO probability
  claim.  The non-reference windows' pools are SMALLER than the nine
  windows' (pre-deep-pooling pooling: k=3 runs x 25 rounds = 75
  samples per reading vs N=19,200): the classification is reported
  as-is with N named per row and NO noise model is claimed.

UNIVERSE (fixed here, before the numbers): every committed raw run
log under docs/evidence/gpu (file name run-*, .stderr.txt siblings
excluded) whose parsed header identifies the v2 instrument
(anv-subgroupsize-batch v2-batch64) and the c2 control-rung knob set
n=1,000,003, batch=2, warmup=3, seed=20261027 with barrier_n=0-or-
absent, work_mul=1-or-absent, ndiv=1-or-absent (older committed
header forms omit those fields; absent = the instrument default --
NAMED, not hidden).  Runs at other knob sets, other instruments and
non-run-log files are COUNTED and NAMED in the census and excluded
from the shape scope.  Reading cell = the (sum,128,S=16) cell
(spv=subgroup-reduce-w128-sum.emitted.spv, wg=128, forced=16) of
each run's committed cell map.  BYTES-FORCED SCOPE CORRECTION (named
here, before any classification number; found by this slice's first
dev run against the committed tree): some committed arms' cell maps
carry the (sum,128,S=16) key ONLY under a kernel-variant spv (e.g.
subgroup-reduce-w128-sum.emitted.iter1.spv, the f1b2/f3b2/f8b2/f8
family arms) -- such runs are NAMED in the census and EXCLUDED from
the shape scope (their samples never enter any pool; a run with no
(sum,128,16) key at all remains a check failure, and exact/variant
status must be uniform within a window -- a check).

CHECKS vs REPORTS (the honesty split): PARSE anomalies (missing
file, header/knob mismatch, cell-map divergence at the reading
cell, sample-count or round-set mismatch, a publication row
disagreeing with the re-derivation, a potential publication binding
that no committed form parses) are CHECKS and fail the run; CENSUS
OUTCOMES and SHAPE OUTCOMES (classifications, distances, margins,
flags, the premise-correction counts) are REPORTS and never fail the
run.

Reads ONLY committed bytes (fail-closed; any parse anomaly is an
immediate recorded failure).  Writes NOTHING to the evidence tree;
prints the report to stdout, nothing to stderr on success.  Exit 0
iff every check is ok.

THREE-STATE: every sample value below is a named run's landed
MEASURED QUANTITY (its own hardware runs on aiueos-6600hs, Intel
BMG G31, under the named instrument), RE-PARSED here from committed
run-log bytes -- this script measures NOTHING new on hardware and no
value here is a measurement of this tick; the share/distance/class
arithmetic is DERIVED (labelled).  The verdict is scoped EXACTLY as
the criterion above: sample-shape classification at the c2 reading
cell over the committed c2-rung windows; the CAUSE of the shape
difference (a genuine execution-time state vs an instrument/timestamp-
quantization state) stays UNMEASURED; the underlying-instrument-
state COUNT stays outside (s220 1(b) binds).  RULE 4 unchanged:
NOTHING MOVES; the committed bracket stays EXACTLY (254,923,
255,045]; the accelerator-targets workgroup rows stay exactly as
ADR-0358 left them (:measured? false rows remain provisional -- NOT
optimization evidence); NO vendor optimization exists for Intel (or
for any vendor) and none follows from this census.
"""

import gzip
import hashlib
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

GPU = Path(__file__).resolve().parent.parent  # docs/evidence/gpu

# ----------------------------------------------------------------
# instrument contract (the committed v2 header/sample forms)
# ----------------------------------------------------------------
V2_INSTR = ("# instrument=anv-subgroupsize-batch v2-batch64 "
            "(JUN-59 subgroup 16-vs-32 floor-lifting rerun, 2026-10-27)")
V1_INSTR_PREFIX = "# instrument=anv-subgroupsize v1"
DEVICE_PREFIX = "# device_name=Intel(R) Graphics (BMG G31)"

TICK_NS_NUM, TICK_NS_DEN = 625, 12  # timestampPeriod 52.0833... ns

CELL_RE = re.compile(
    r"^CELL idx=(\d+) spv=(\S+) op=(\S+) wg=(\d+) forced=(\S+) "
    r"probe_size=(-?\d+) probe_nsub=(-?\d+) probe_wg=(-?\d+) "
    r"pipeline=(\S+) void=(\d)")
SAMPLE_RE = re.compile(
    r"^SAMPLE round=(\d+) idx=(\d+) batch=(\d+)"
    r"(?: work_mul=(\d+))?(?: ndiv=(\d+))?"
    r" gpu_ticks=(\d+) gpu_ns=([\d.]+) per_dispatch_ns=([\d.]+)"
    r" host_ns=(\d+)$")
VERIFY_RE = re.compile(
    r"^VERIFY idx=(\d+) checked=(\d+) mismatch=(\d+) ok=(\d)"
    r"(?: note=(\S+))?$")
HEADER_RE = re.compile(r"^# n=(\d+) rounds=(\d+) warmup=(\d+) batch=(\d+)(.*)$")

CELL_KEY = ("sum", "128", "16")  # the reading cell (op, wg, forced)

# the nine committed reference windows (the s234 universe) and the
# committed record letters (cross-checked against the re-derivation)
REF_WINDOWS = [
    ("s158",    "anv-b3bisect15-20261101",      "c2",    "a"),
    ("s169",    "anv-b3bisect16-20261101",      "c2",    "b"),
    ("s185",    "anv-b3bisect17-20261101",      "c2",    "a"),
    ("s197",    "anv-b3bisect18-20261101",      "c2",    "a"),
    ("s209",    "anv-b3bisect19-20261102",      "c2",    "b"),
    ("act-rd1", "anv-b3control3state-20261102", "rd1-c2", "b"),
    ("act-rd2", "anv-b3control3state-20261102", "rd2-c2", "b"),
    ("act-rd3", "anv-b3control3state-20261102", "rd3-c2", "b"),
    ("act-rd4", "anv-b3control3state-20261102", "rd4-c2", "b"),
]

# committed cross-check pins parsed from committed bytes below
S27 = GPU / "anv-b3bisect7-20261027" / "derivation-census-s27.txt"
S234_REPORT = (GPU / "anv-b3control3state-20261102" /
               "identity-shape-s234-run1.txt")
S234_SCRIPT = (GPU / "anv-b3control3state-20261102" /
               "identity-shape-s234.py")
C2_PIN, C8_PIN = 31, 32915  # s27 line-43 pins (cross-checked below)

# the two committed publication-row forms bound here (fixed before
# numbers); any OTHER committed form is NAMED in the report as
# unparsed-form (not silently skipped, not checked)
F1_RE = re.compile(
    r"(?m)^\s*(\S+(?:\s+\S+)*?)\s+\(sum,128,S=16\) pooled median (\d+)")
F1_POTENTIAL_RE = re.compile(r"\(sum,128,S=16\) pooled median \d")
F2_RE = re.compile(r"\(sum,W=128,S=16\)[^\n]*?B2:(\d+)\(PIN\)")
F2_POTENTIAL_RE = re.compile(r"\(sum,W=128,S=16\)[^\n]*?B2:\d+\(PIN\)")

problems = []
n_checks = [0]


def check(ok, label):
    n_checks[0] += 1
    if ok:
        print(f"  ok    {label}")
    else:
        print(f"  FAIL  {label}")
        problems.append(label)


def P(s=""):
    print(s)


def read_lines(path):
    if path.name.endswith(".gz"):
        with gzip.open(path, "rt", errors="strict") as fh:
            return fh.read().splitlines()
    with open(path, "r", errors="strict") as fh:
        return fh.read().splitlines()


def sha256_file(path):
    h = hashlib.sha256()
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def median2(pool):
    """independent even-N median (sort + middle), never statistics"""
    s = sorted(pool)
    n = len(s)
    if n % 2:
        return float(s[n // 2])
    return (s[n // 2 - 1] + s[n // 2]) / 2.0


def read_bytes(path):
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rb") as fh:
        return fh.read()


# ================================================================
P("prepool-shape-s235.py -- THE S216 IDENTITY HAZARD'S RESIDUAL-C")
P("SAMPLE-SHAPE CENSUS OVER EVERY COMMITTED c2-RUNG RAW RUN LOG")
P()
P("THE ROW (the s234 carry-forward's first named residual):")
P("'whether pre-deep-pooling windows share either sample shape is")
P("UNCHECKED from committed bytes (no committed raw logs)' -- taken")
P("as this tick's ONE row.  The criterion is frozen in this file's")
P("docstring BEFORE any number below is computed.")
P()

# ----------------------------------------------------------------
# 0. the raw-log census over the whole evidence tree
# ----------------------------------------------------------------
P("0. RAW-LOG CENSUS (every committed run-* raw log under")
P("   docs/evidence/gpu, .stderr.txt siblings excluded):")

all_run_files = sorted(p for p in GPU.rglob("run-*")
                       if p.is_file() and not p.name.endswith(".stderr.txt"))
v2_files, v1_files, other_files = [], [], []
other_first = Counter()
for p in all_run_files:
    if p.name.endswith(".gz"):
        with gzip.open(p, "rt", errors="replace") as fh:
            first = fh.readline().rstrip("\n")
    else:
        with open(p, "r", errors="replace") as fh:
            first = fh.readline().rstrip("\n")
    if first == V2_INSTR:
        v2_files.append(p)
    elif first.startswith(V1_INSTR_PREFIX):
        v1_files.append(p)
    else:
        other_files.append(p)
        other_first[first[:48]] += 1

P(f"   run-* raw logs found: {len(all_run_files)}")
P(f"   v2 instrument ({V2_INSTR[:40]}...): {len(v2_files)}")
P(f"   v1 instrument (older family): {len(v1_files)}")
P(f"   other/non-run-log first lines: {len(other_files)}")
for first, cnt in sorted(other_first.items(), key=lambda kv: (-kv[1], kv[0])):
    P(f"     {cnt:4d}  {first!r}")

# ----------------------------------------------------------------
# 1. the c2-rung universe: header scan + fail-closed full parse
# ----------------------------------------------------------------
P()
P("1. THE c2-RUNG UNIVERSE (v2 runs whose committed header carries")
P("   the c2 control-rung knob set n=1,000,003 batch=2 warmup=3")
P("   seed=20261027, barrier_n/work_mul/ndiv at 0-or-absent /")
P("   1-or-absent / 1-or-absent; older header forms omit fields --")
P("   absent = instrument default, NAMED here):")

universe = []          # (path, family, knobs, rounds)
other_knob = []        # (path, knobs-summary)
for p in v2_files:
    with (gzip.open(p, "rt", errors="replace")
          if p.name.endswith(".gz") else open(p, "r", errors="replace")) as fh:
        head = [fh.readline().rstrip("\n") for _ in range(10)]
    hdr = next((l for l in head if l.startswith("# n=")), None)
    if hdr is None:
        check(False, f"v2 run without '# n=' header line: {p.relative_to(GPU)}")
        continue
    m = HEADER_RE.match(hdr)
    if not m:
        check(False, f"header line parse: {p.relative_to(GPU)}")
        continue
    n, rounds, warmup, batch = (int(m.group(1)), int(m.group(2)),
                                int(m.group(3)), int(m.group(4)))
    rest = m.group(5)
    kv = dict(re.findall(r"(\w+)=(\S+)", rest))
    knobs = dict(n=n, rounds=rounds, warmup=warmup, batch=batch,
                 barrier_n=kv.get("barrier_n"),
                 work_mul=kv.get("work_mul"), ndiv=kv.get("ndiv"),
                 seed=kv.get("seed"))
    is_c2 = (n == 1000003 and batch == 2 and warmup == 3
             and knobs["barrier_n"] in (None, "0")
             and knobs["work_mul"] in (None, "1")
             and knobs["ndiv"] in (None, "1"))
    if is_c2:
        fam = re.sub(r"-r\d+\.txt(\.gz)?$", "", p.name[len("run-"):])
        universe.append((p, fam, knobs, rounds))
    else:
        other_knob.append((p, f"n={n} batch={batch} wm={knobs['work_mul']} "
                              f"ndiv={knobs['ndiv']} bn={knobs['barrier_n']}"))

P(f"   v2 runs at other knob sets (named, excluded from shape scope):"
  f" {len(other_knob)}")
okc = Counter(k for _, k in other_knob)
for k, cnt in sorted(okc.items(), key=lambda kv: (-kv[1], kv[0])):
    P(f"     {cnt:4d}  {k}")
P(f"   c2-RUNG UNIVERSE RUNS: {len(universe)}")
groups = {}
for p, fam, knobs, rounds in universe:
    groups.setdefault((str(p.parent.relative_to(GPU)), fam), []).append(p)
P(f"   c2-rung windows (dir x arm family): {len(groups)}")
check(len(v2_files) + len(v1_files) + len(other_files) == len(all_run_files),
      "raw-log census reconciles: v2 + v1 + other == every run-* file")
check(len(universe) + len(other_knob) == len(v2_files),
      "v2 census reconciles: c2-rung + other-knob == every v2 run")

# full fail-closed parse of every universe run
P()
P("   fail-closed parse of every universe run (header, cell map,")
P("   samples at the reading cell, VERIFY rows, tail, bytes/sha256):")

group_pools = {}   # (dir, fam) -> list of gpu_ticks at the reading cell
group_rounds = {}  # (dir, fam) -> rounds
excluded_windows = []  # (dir, fam, status) -- named, never classified
map_digests = Counter()
total_samples = 0
verify_mismatch_total = 0
for key in sorted(groups):
    d, fam = key
    pool = []
    rounds_seen = set()
    status_seen = set()
    for p in sorted(groups[key]):
        rel = p.relative_to(GPU)
        lines = read_lines(p)
        head = lines[:10]
        # header
        hdr = next(l for l in head if l.startswith("# n="))
        m = HEADER_RE.match(hdr)
        check(m is not None, f"{rel} header parses")
        if not m:
            continue
        n, rounds, warmup, batch = (int(m.group(1)), int(m.group(2)),
                                    int(m.group(3)), int(m.group(4)))
        kv = dict(re.findall(r"(\w+)=(\S+)", m.group(5)))
        rounds_seen.add(rounds)
        check(rounds in (25, 6400), f"{rel} rounds {rounds} in (25, 6400)")
        check(kv.get("seed") == "20261027", f"{rel} seed=20261027")
        check(head[0] == V2_INSTR, f"{rel} instrument line exact")
        check(head[1].startswith(DEVICE_PREFIX), f"{rel} device line prefix")
        check(any(l.startswith("# timestampPeriod=52.083")
                  for l in head), f"{rel} timestampPeriod=52.083 pinned")
        # cell map
        cells = []
        sample_n = verify_n = done_n = 0
        read_idx = None
        variant_idx = {}
        file_pool = []
        per_idx = Counter()
        for line in lines:
            if line.startswith("CELL "):
                cm = CELL_RE.match(line)
                check(cm is not None, f"{rel} CELL row parse"
                      ) if cm is None else None
                if cm is None:
                    continue
                cells.append(cm.groups())
                if (cm.group(3), cm.group(4), cm.group(5)) == \
                        ("sum", "128", "16"):
                    if cm.group(2) == \
                            "subgroup-reduce-w128-sum.emitted.spv":
                        check(cm.group(9) == "ok",
                              f"{rel} reading cell pipeline=ok")
                        check(read_idx is None,
                              f"{rel} reading cell unique")
                        read_idx = int(cm.group(1))
                    else:
                        variant_idx[cm.group(2)] = int(cm.group(1))
            elif line.startswith("SAMPLE "):
                sm = SAMPLE_RE.match(line)
                if sm is None:
                    check(False, f"{rel} SAMPLE row parse: {line[:60]!r}")
                    continue
                sample_n += 1
                idx = int(sm.group(2))
                per_idx[idx] += 1
                check_b = (int(sm.group(3)) == batch
                           and (sm.group(4) in (None, kv.get("work_mul")))
                           and (sm.group(5) in (None, kv.get("ndiv"))))
                if not check_b:
                    check(False, f"{rel} SAMPLE knob fields match header")
                ticks = int(sm.group(6))
                gpu_ns = float(sm.group(7))
                pd_ns = float(sm.group(8))
                if abs(gpu_ns - ticks * TICK_NS_NUM / TICK_NS_DEN) > 0.06:
                    check(False, f"{rel} gpu_ns == ticks*625/12 ({ticks})")
                if abs(pd_ns - ticks * TICK_NS_NUM / TICK_NS_DEN / batch) \
                        > 0.006:
                    check(False, f"{rel} per_dispatch_ns == gpu_ns/batch")
                if idx == read_idx:
                    file_pool.append(ticks)
            elif line.startswith("VERIFY "):
                vm = VERIFY_RE.match(line)
                check(vm is not None, f"{rel} VERIFY row parse"
                      ) if vm is None else None
                if vm is None:
                    continue
                verify_n += 1
                verify_mismatch_total += int(vm.group(3))
            elif line == "# done cells=24":
                done_n += 1
        if read_idx is not None:
            check(not variant_idx,
                  f"{rel} no (sum,128,16) spv-variant duplicate")
        else:
            check(bool(variant_idx),
                  f"{rel} (sum,128,16) key present (exact or named variant)")
        check(len(cells) == 24, f"{rel} 24 CELL rows (got {len(cells)})")
        ok_cells = [c for c in cells if c[8] == "ok"]
        check(len(ok_cells) == 18, f"{rel} 18 pipeline-ok cells")
        check(sample_n == 18 * rounds,
              f"{rel} SAMPLE count {sample_n} == 18*rounds")
        for c in ok_cells:
            check(per_idx.get(int(c[0]), 0) == rounds,
                  f"{rel} idx={c[0]} samples == rounds")
        for c in cells:
            if c[8] != "ok":
                check(per_idx.get(int(c[0]), 0) == 0,
                      f"{rel} FAIL cell idx={c[0]} has no samples")
        check(verify_n == 24, f"{rel} 24 VERIFY rows")
        check(done_n == 1, f"{rel} tail '# done cells=24'")
        if read_idx is not None:
            check(len(file_pool) == rounds,
                  f"{rel} reading-cell samples {len(file_pool)} == rounds")
            pool.extend(file_pool)
            status_seen.add("exact")
        else:
            P(f"     NAMED EXCLUSION {rel}: the (sum,128,16) key exists"
              f" only under spv variant {sorted(variant_idx)} -- the"
              f" bytes-forced scope correction: no exact reading cell,"
              f" its samples never enter any pool (shape scope)")
            status_seen.add(("variant", tuple(sorted(variant_idx))))
        map_digests[hashlib.sha256(
            "|".join(",".join(c[:7]) for c in cells).encode()).hexdigest()[:16]] \
            += 1
        total_samples += len(file_pool)
        P(f"     pin {rel} bytes={len(read_bytes(p))} sha256={sha256_file(p)}")
    check(len(status_seen) == 1,
          f"{d}/{fam} reading-cell status uniform across its runs")
    check(len(rounds_seen) == 1,
          f"{d}/{fam} rounds uniform across its runs")
    if pool:
        group_pools[key] = pool
        group_rounds[key] = next(iter(rounds_seen))
    else:
        excluded_windows.append((d, fam, sorted(status_seen, key=str)[0]))
P(f"   universe runs parsed: {len(universe)}; reading-cell samples"
  f" pooled: {total_samples}")
P(f"   cell-map digests across the universe: {len(map_digests)} distinct")
for dig, cnt in sorted(map_digests.items()):
    P(f"     {cnt:4d}  {dig}")
P(f"   VERIFY mismatch total over every universe run:"
  f" {verify_mismatch_total}")
check(verify_mismatch_total == 0,
      "VERIFY mismatches zero over every universe run")


# ----------------------------------------------------------------
# 2. the nine reference windows: re-derivation + committed binds
# ----------------------------------------------------------------
P()
P("2. THE NINE REFERENCE WINDOWS (the s234 universe) RE-DERIVED")
P("   here from the committed run logs (m = pooled sample median")
P("   gpu_ticks at the reading cell; letters = f(m vs the committed")
P("   floor band 31..32 at B=2); cross-checked against the")
P("   committed s234 report rows:")

# s27 band parse (fail-closed)
s27_text = S27.read_text()
sm = re.search(r"committed controls: c2 (\d+) \(floor band (\d+)\.\.(\d+)\);"
               r" c8 ([\d,]+) \(session 4 pooled median\)", s27_text)
check(sm is not None, "s27 committed-controls row parses")
band = (int(sm.group(2)), int(sm.group(3))) if sm else (31, 32)
check(int(sm.group(1)) == C2_PIN, f"s27 c2 pin {sm.group(1)} == {C2_PIN}")
check(band == (31, 32), f"s27 floor band {band} == (31, 32)")
check(int(sm.group(4).replace(",", "")) == C8_PIN,
      f"s27 c8 pin {sm.group(4)} == {C8_PIN}")

s234_text = S234_REPORT.read_text()
s234_script_text = S234_SCRIPT.read_text()
check("carry NO committed raw run logs" in s234_script_text,
      "the s234 premise quote binds to the committed s234 script bytes")

ref_pools, ref_m, ref_letter = {}, {}, {}
for label, d, fam, letter in REF_WINDOWS:
    key = (d, fam)
    check(key in group_pools,
          f"{label} group pooled exact reading-cell samples present")
    if key not in group_pools:
        continue
    pool = group_pools[key]
    ref_pools[label] = pool
    m = statistics.median(pool)
    m2 = median2(pool)
    check(m == m2, f"{label} independent median re-derivation agrees")
    ref_m[label] = m
    der = "a" if band[0] <= m <= band[1] else "b"
    check(der == letter,
          f"{label} derived letter ({der}) == committed record ({letter})")
    ref_letter[label] = der
    check(len(pool) == 19200, f"{label} N=3R=19,200 pooled")

# s234 report share-row cross-check (per-window + pooled + W_in/out)
s234_share_rows = {}
for line in s234_text.splitlines():
    mm = re.match(r"^\s+(\S+)\s+((?:\d+:[\d.]+\s*)+)$", line)
    if mm and mm.group(1) in ref_pools:
        s234_share_rows[mm.group(1)] = {
            int(t): float(s) for t, s in
            re.findall(r"(\d+):([\d.]+)", mm.group(2))}

U9 = sorted({t for label in ref_pools for t in ref_pools[label]})


def shares(pool, support):
    cnt = Counter(pool)
    n = len(pool)
    return {t: cnt.get(t, 0) * 100.0 / n for t in support}


def l1(a, b, support):
    return sum(abs(a.get(t, 0.0) - b.get(t, 0.0)) for t in support)


ref_shares = {label: shares(ref_pools[label], U9) for label in ref_pools}
for label in ref_pools:
    s234_row = s234_share_rows.get(label)
    check(s234_row is not None, f"{label} s234 report share row present")
    if s234_row:
        agree = all(round(ref_shares[label].get(t, 0.0), 4) == s
                    for t, s in s234_row.items()) and \
                all(round(v, 4) == s234_row.get(t, 0.0)
                    for t, v in ref_shares[label].items() if v != 0.0)
        check(agree, f"{label} re-derived shares == s234 report row")

group_a = [l for l in ref_pools if ref_letter[l] == "a"]
group_b = [l for l in ref_pools if ref_letter[l] == "b"]
check(sorted(group_a) == ["s158", "s185", "s197"],
      f"group (a) == the committed (a) windows {sorted(group_a)}")
check(sorted(group_b) == ["act-rd1", "act-rd2", "act-rd3", "act-rd4",
                          "s169", "s209"],
      f"group (b) == the committed (b) windows {sorted(group_b)}")

R_a = shares([t for l in group_a for t in ref_pools[l]], U9)
R_b = shares([t for l in group_b for t in ref_pools[l]], U9)
for tag, R, names in (("(a)", R_a, group_a), ("(b)", R_b, group_b)):
    P(f"   group {tag} pooled reference ({'+'.join(sorted(names))};"
      f" N={sum(len(ref_pools[l]) for l in names)}):")
    P("     " + "  ".join(f"{t}:{R[t]:.4f}" for t in U9 if R[t] != 0.0))
    mm = re.search(r"group \Q{tag}\E pooled: ((?:\d+:[\d.]+\s*)+)"
                   .replace("\\Q{tag}\\E", re.escape(tag)), s234_text)
    if mm:
        s234_pooled = {int(t): float(s) for t, s in
                       re.findall(r"(\d+):([\d.]+)", mm.group(1))}
        agree = all(round(R.get(t, 0.0), 4) == s
                    for t, s in s234_pooled.items())
        check(agree, f"group {tag} pooled reference == s234 report row")

# W_in / W_out on U9 (context constants; cross-checked to s234)
within = []
between = []
labels = list(ref_pools)
for i, x in enumerate(labels):
    for y in labels[i + 1:]:
        d = l1(ref_shares[x], ref_shares[y], U9)
        if ref_letter[x] == ref_letter[y]:
            within.append((d, x, y))
        else:
            between.append((d, x, y))
W_in = max(within)
W_out = min(between)
P(f"   W_in  = max within-group L1 = {W_in[0]:.4f} ({W_in[1]} vs"
  f" {W_in[2]})")
P(f"   W_out = min between-group L1 = {W_out[0]:.4f} ({W_out[1]} vs"
  f" {W_out[2]})")
wm = re.search(r"W_in  = max within-group L1 = ([\d.]+) \((\S+) vs (\S+)\)",
               s234_text)
wo = re.search(r"W_out = min between-group L1 = ([\d.]+) \((\S+) vs (\S+)\)",
               s234_text)
check(wm is not None and wo is not None, "s234 W_in/W_out rows parse")
check(wm and round(W_in[0], 4) == float(wm.group(1))
      and {W_in[1], W_in[2]} == {wm.group(2), wm.group(3)},
      "re-derived W_in == s234 report row")
check(wo and round(W_out[0], 4) == float(wo.group(1))
      and {W_out[1], W_out[2]} == {wo.group(2), wo.group(3)},
      "re-derived W_out == s234 report row")

# ----------------------------------------------------------------
# 3. every other c2-rung window: the classification
# ----------------------------------------------------------------
P()
P("3. EVERY c2-RUNG WINDOW'S READING-CELL SAMPLE SHAPE (the")
P("   classification under the criterion frozen before the numbers;")
P("   DERIVED arithmetic; pattern-level only):")

U_all = sorted({t for key in group_pools for t in group_pools[key]})
P(f"   union support of gpu_ticks over all {len(group_pools)} windows:"
  f" {U_all}")
R_a_all = {t: R_a.get(t, 0.0) for t in U_all}
R_b_all = {t: R_b.get(t, 0.0) for t in U_all}

rows = []
for key in sorted(group_pools):
    d, fam = key
    pool = group_pools[key]
    if any(key == (dd, ff) for _, dd, ff, _ in REF_WINDOWS):
        continue
    sw = shares(pool, U_all)
    D_a = l1(sw, R_a_all, U_all)
    D_b = l1(sw, R_b_all, U_all)
    cls = ("(a)" if D_a < D_b else "(b)" if D_b < D_a else "UNDECIDED")
    flag = " NEAR-NEITHER" if min(D_a, D_b) > W_in[0] else ""
    m = statistics.median(pool)
    rows.append((d, fam, len(groups[key]), group_rounds[key], len(pool),
                 m, D_a, D_b, cls, flag))

P(f"   {'dir':<32} {'arm':<8} {'runs':>4} {'rnd':>5} {'N':>6} {'m':>6}"
  f" {'D_a':>9} {'D_b':>9}  class  flag")
for (d, fam, nr, rnd, n, m, D_a, D_b, cls, flag) in rows:
    P(f"   {d:<32} {fam:<8} {nr:>4} {rnd:>5} {n:>6} {m:>6.1f}"
      f" {D_a:>9.4f} {D_b:>9.4f}  {cls}{flag}")

cls_counts = Counter(r[8] for r in rows)
flagged = [r for r in rows if r[9]]
c2fam = [r for r in rows if r[1] == "c2"]
othfam = [r for r in rows if r[1] != "c2"]
P(f"   classification census over {len(rows)} non-reference windows:"
  f" (a) {cls_counts.get('(a)', 0)}, (b) {cls_counts.get('(b)', 0)},"
  f" UNDECIDED {cls_counts.get('UNDECIDED', 0)}")
P(f"   family split (the frozen knob-set universe admits arms other")
P(f"   than the record's c2 reading arm; family names are the rows'")
P(f"   own, never re-labelled): family c2 {len(c2fam)} windows,"
  f" other arms {len(othfam)}"
  f" ({','.join(sorted({r[1] for r in othfam}))})")
for tag, sub in (("family c2", c2fam), ("other arms", othfam)):
    cc = Counter(r[8] for r in sub)
    P(f"     {tag}: (a) {cc.get('(a)', 0)}, (b) {cc.get('(b)', 0)},"
      f" UNDECIDED {cc.get('UNDECIDED', 0)} over {len(sub)} windows")
P(f"   NEAR-NEITHER flags (min(D_a,D_b) > W_in {W_in[0]:.4f}):"
  f" {len(flagged)}")
for r in flagged:
    P(f"     {r[0]} {r[1]} N={r[4]} D_a={r[6]:.4f} D_b={r[7]:.4f}")
P(f"   named exclusions (no exact reading-cell samples pooled; NEVER")
P(f"   classified): {len(excluded_windows)} windows")
for (d, fam, st) in excluded_windows:
    P(f"     {d}/{fam}: {st}")

# publication binding census (cross-check only; two committed forms)
P()
P("   publication binding census (forms F1 '<arm> (sum,128,S=16)")
P("   pooled median <N>' and F2 '(sum,W=128,S=16) ... B2:<N>(PIN)';")
P("   other committed forms are NAMED unparsed-form, not checked):")
dirs = sorted({k[0] for k in group_pools})
for d in dirs:
    pubs = sorted((GPU / d).glob("publication-*.txt"))
    fams = sorted(f for dd, f in group_pools if dd == d)
    if not pubs:
        P(f"     {d:<32} arms={','.join(fams):<24} NO publication-*.txt")
        continue
    text = "\n".join(p.read_text() for p in pubs)
    f1 = [(mm.group(1).split()[-1], int(mm.group(2)))
          for mm in F1_RE.finditer(text)]
    f2 = [(("b2"), int(mm.group(1)))
          for mm in F2_RE.finditer(text)]
    pot1 = len(F1_POTENTIAL_RE.findall(text))
    pot2 = len(F2_POTENTIAL_RE.findall(text))
    check(pot1 == len(f1) and pot2 == len(f2),
          f"{d} potential publication bindings all parse under F1/F2")
    bound = f1 + f2
    status = []
    for arm, val in bound:
        if arm in fams:
            pool = group_pools[(d, arm)]
            m = statistics.median(pool)
            if float(m).is_integer():
                check(int(m) == val,
                      f"{d}/{arm} re-derived m {int(m)} == published {val}")
                status.append(f"{arm} BOUND m={int(m)}")
            else:
                status.append(f"{arm} NAMED-UNCOMPARABLE m={m} pub={val}")
        else:
            status.append(f"{arm} OTHER-ARM pub={val}")
    for f in fams:
        if not any(arm == f for arm, _ in bound):
            status.append(f"{f} NOT-CARRIED")
    P(f"     {d:<32} arms={','.join(fams):<24} {'; '.join(status)}")

# ----------------------------------------------------------------
# 4. the verdict for residual C
# ----------------------------------------------------------------
P()
P("4. THE VERDICT FOR RESIDUAL C (the s216 identity hazard's")
P("   'whether pre-deep-pooling windows share either sample shape';")
P("   pattern-level only, scoped to the committed bytes):")
pre = [r for r in rows if r[3] == 25]
deep = [r for r in rows if r[3] == 6400]
P(f"   non-reference c2-rung windows with committed raw run logs:")
P(f"     pre-deep-pooling pooling (rounds=25, N=75 per reading):"
  f" {len(pre)} windows")
P(f"     deep pooling (rounds=6400): {len(deep)} windows")
for (d, fam, nr, rnd, n, m, D_a, D_b, cls, flag) in rows:
    P(f"     {d}/{fam}: rounds={rnd} N={n} m={m:.1f} class {cls}"
      f" (D_a={D_a:.4f} D_b={D_b:.4f}){flag}")
P()
P(f"   ANSWER (scoped): over the {len(pre)} pre-deep-pooling B=2-knob")
P(f"   windows whose raw run logs ARE committed (family c2 -- the")
P(f"   record's reading arm -- in {len([r for r in pre if r[1] == 'c2'])};")
P(f"   other arms at the same knob set in"
  f" {len([r for r in pre if r[1] != 'c2'])}, named above), the")
P(f"   reading-cell sample shape SHARES the (a) reference shape in")
P(f"   {cls_counts.get('(a)', 0)} windows, the (b) reference shape in")
P(f"   {cls_counts.get('(b)', 0)}, and is UNDECIDED (exact D tie) in")
P(f"   {cls_counts.get('UNDECIDED', 0)} -- under the criterion frozen")
P(f"   before the numbers (nearest reference by L1 over the union")
P(f"   support; W_in={W_in[0]:.4f} reported as the near-neither gate).")
P(f"   SCOPED FURTHER to the record's c2 reading arm alone (the")
P(f"   residual's windows proper):"
  f" (a) {Counter(r[8] for r in pre if r[1] == 'c2').get('(a)', 0)},"
  f" (b) {Counter(r[8] for r in pre if r[1] == 'c2').get('(b)', 0)},"
  f" UNDECIDED"
  f" {Counter(r[8] for r in pre if r[1] == 'c2').get('UNDECIDED', 0)}"
  f" over {len([r for r in pre if r[1] == 'c2'])} windows; the other-")
P(f"   arm rows are SUPPLEMENTARY (same knob set, different arm --")
P(f"   their shape is reported, not part of the record's reading")
P(f"   scope).")
P(f"   The s234 premise 'no committed raw run logs' for these")
P(f"   windows is CORRECTED by the census counts above; the s234")
P(f"   nine-window separation (W_out {W_out[0]:.4f} > W_in"
  f" {W_in[0]:.4f}) is re-derived here UNCHANGED.")
P("   The CAUSE of any shape difference (execution-time state vs")
P("   instrument/timestamp-quantization state) stays UNMEASURED; the")
P("   underlying-instrument-state COUNT stays outside (s220 1(b)).")

# ----------------------------------------------------------------
# 5. three-state / scope / carry-forward
# ----------------------------------------------------------------
P()
P("5. THREE-STATE / SCOPE / RULE 4 / BAR: every sample re-parsed")
P("   here is a named run's landed MEASURED QUANTITY on aiueos-6600hs")
P("   (Intel BMG G31) under the named instrument -- this tick")
P("   measures NOTHING new on hardware (NO runs, NO builds, NO GO")
P("   stamp); the shares/distances/classes are DERIVED arithmetic;")
P("   the accelerator-targets workgroup rows stay exactly as")
P("   ADR-0358 left them (:measured? false rows remain provisional")
P("   -- NOT optimization evidence); NO vendor optimization exists")
P("   for Intel (or for any vendor) and none follows from this")
P("   census.  RULE 4 unchanged: NOTHING MOVES; the committed")
P("   bracket stays EXACTLY (254,923, 255,045]; L9 binds at")
P("   n=254,984 (C2 (c), D3 (v)); the MID-ONLY NARROWING CLAIM stays")
P("   SUSPENDED.  BAR NON-INTERFERENCE: NO settle-bar-ledger line,")
P("   NO day-slot consumption; the bar's SETTLED INTERMEDIATE/MIXED")
P("   verdict unmoved.")
P()
P("   NAMED, NOT HIDDEN: this census admits pre-deep-pooling runs")
P("   whose committed header omits barrier_n/work_mul/ndiv fields")
P("   (the s4-era header form) as the c2 rung under the instrument")
P("   defaults BARRIER_N=0/WM=1/NDIV=1 -- an assumption NAMED here")
P("   and cross-checked by the publication binding wherever the")
P("   committed publication rows parse; windows whose publications")
P("   carry other committed row forms are named unparsed-form and")
P("   are NOT checked against their re-derived medians.")
P()
P("   NOT DONE (s236 carries exactly this list): the s216 identity")
P("   hazard's remaining residuals (standing, not queued): the CAUSE")
P("   of the sample-shape difference (execution-time state vs")
P("   instrument/timestamp-quantization state) stays UNMEASURED;")
P("   the underlying-instrument-state COUNT stays outside (s220")
P("   1(b)); whether the windows whose c2-rung raw logs are NOT")
P("   committed (if any remain after this census) share either")
P("   sample shape stays UNCHECKED from committed bytes; standing,")
P("   not queued: any further counted-day slot (each needs its own")
P("   freeze) and the cross-day tail-movement row.")
P()
P(f"checks: {n_checks[0]} run; failures: {len(problems)}")
P(f"# prepool-shape s235 (prepool-shape-s235.py):"
  f" {n_checks[0] - len(problems)} ok / {len(problems)} failed")
sys.exit(1 if problems else 0)
