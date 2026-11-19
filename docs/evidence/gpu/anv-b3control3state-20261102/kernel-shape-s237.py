#!/usr/bin/env python3
"""kernel-shape-s237.py -- THE EXCLUDED KERNEL-VARIANT ARMS'
(sum,128,16) SAMPLE-SHAPE CHECK (amu-gpu session 237; the s236
carry-forward's QUEUED row (iii) -- "the excluded kernel-variant
arms' (sum,128,16) shapes (iter1/iter3/iter8 spvs) stay UNCHECKED
(out of scope by the s235 bytes-forced correction) -- QUEUED for
s237" -- taken as this tick's ONE row).

THE ROW AND THE NAMED SPELLING OMISSION (named up front): the
queue parenthetical enumerates three variant spellings
(iter1/iter3/iter8); the committed s235 named-exclusion block --
the row's own source -- carries FOUR (it adds
subgroup-reduce-w128-sum.emitted.itervc8.spv at
anv-costcal-20261027/f8vc).  This slice takes the WHOLE committed
excluded set (8 windows / 24 runs) as the row universe and names
the parenthetical's omission rather than silently dropping the
fourth spelling.

THE QUESTION the committed bytes can answer: at the same
instrument cell (op=sum, wg=128, forced=16 -- the (sum,128,S=16)
reading cell) and the same c2 control-rung knob set
(n=1,000,003, B=2, warmup=3, seed=20261027, barrier_n/work_mul/
ndiv at 0-or-absent/1-or-absent/1-or-absent), do the kernel-variant
arms' cell samples -- taken under the ITERATED kernel variant spv
(iter1/iter3/iter8/itervc8) that carries the (sum,128,16) key in
those runs -- SHARE the (a) or the (b) reference sample shape of
the record's deep-pooling reading cell, or NEITHER?

THE DECISION CRITERION (the s235 criterion applied unchanged; its
reference construction re-derived here from the committed run logs
and BOUND to the committed s234/s235 report rows; frozen here
before the numbers):
  Reference shapes: R_a = the pooled per-sample share vector of
  the committed (a) windows {s158, s185, s197}; R_b = that of the
  committed (b) windows {s169, s209, act-rd1..4} (each window's
  samples re-derived from its committed run logs; the letters
  re-derived from the pooled median m against the committed floor
  band 31..32 at B=2 and bound to the committed record letters).
  Support U = the union of gpu_ticks values over the nine
  reference pools AND the eight variant pools (fixed here).
  For every kernel-variant window w (its (sum,128,16)-cell samples
  under its named variant spv, pooled over its committed runs):
    D_a(w) = L1(share_w, R_a), D_b(w) = L1(share_w, R_b)
    (percentage points over U).
  RULE (the s235 rule verbatim): w SHARES THE (a) SHAPE iff
  D_a < D_b; SHARES THE (b) SHAPE iff D_b < D_a; EXACT TIE ->
  UNDECIDED.  The margins are reported for every window.  FLAG
  (reported, never a class): NEAR-NEITHER iff min(D_a,D_b) exceeds
  W_in (the re-derived s234/s235 max within-group L1).  PATTERN-
  LEVEL ONLY (s218 2(e)): NO p-value, NO test statistic, NO
  probability claim.  The variant windows' pools are the pre-
  deep-pooling pooling (k=3 runs x 25 rounds = N=75 per window):
  the classification is reported as-is with N named per row and NO
  noise model is claimed (the s235 (i) caveat binds verbatim).

SCOPE -- SUPPLEMENTARY, CROSS-KERNEL (named here, before the
numbers): the variant cell EXECUTES DIFFERENT KERNEL BYTES (the
iterated subgroup-reduce variants) than the record's reading cell
(the archived .emitted.spv) -- same instrument, same knob set, same
(op,wg,forced) cell, different SPIR-V.  The comparison is
descriptive: it does NOT extend the s234 (a)/(b) state-IDENTITY
claim to these arms, it does NOT make these arms part of the
record's reading scope, and it moves NO record row.

BINDING (CHECKS, fail-closed):
  (B1) the row quote binds to the committed s236 report bytes
  (map-sessions-s236-run1.txt: 'excluded kernel-variant arms' +
  'QUEUED for s237');
  (B2) the committed s235 named-exclusion block parses: 8 window
  rows (dir/fam/variant-spv) + 24 NAMED-EXCLUSION run lines
  (rel/spv) -- and this slice's fail-closed re-derivation of the
  variant set from the committed run bytes EQUALS it both ways;
  (B3) the raw-log census rows re-derived here BIND to the
  committed s235 report rows (2477/1869/6/602 raw-log counts,
  1680 other-knob runs, 189 universe runs, 63 windows, 176250
  exact-cell samples pooled, the 5 cell-map digest rows, VERIFY
  mismatch total 0);
  (B4) the nine references re-derived here BIND to the committed
  s234 report rows (9 per-window share rows, 2 pooled rows,
  W_in/W_out) and to the committed s235 report rows (2 pooled
  rows, W_in/W_out);
  (B5) per-window publication binding under THIS slice's frozen
  table-row form T1 (fixed here before the numbers): in the
  window's dir publication-*.txt every line starting with the arm
  name followed by a digit must parse under T1
  ('<arm> <cols...> <value> <lo>..<hi> <lo>..<hi> <host_ns>'; the
  published section-2 header defines <value> = pooled median
  gpu_ticks over 3 runs x 25 rounds at the cell and <lo>..<hi> =
  the run-median band at that cell); the re-derived pooled median
  (N=75) == <value> and the re-derived per-run median band ==
  <lo>..<hi>.  A window whose dir publication carries NO such line
  is REPORTED NOT-CARRIED (named, not hidden, never a check).
  (B6) run-log parse integrity of every pooled run (header/knob/
  instrument/device/timestampPeriod/seed pins; 24 CELL rows; 18
  pipeline-ok; SAMPLE counts == 18*rounds; per-idx counts; FAIL
  cells carry no samples; 24 VERIFY rows; tail '# done cells=24';
  gpu_ns/per_dispatch_ns arithmetic; VERIFY mismatch total 0;
  exactly one (sum,128,16) key per run and it is the window's
  named variant spv; variant spv uniform within a window; rounds
  uniform within a window; the ok-cell idx set uniform within a
  window; the reference windows as in s235).

REPORTS (never checks): the shape classes, distances, margins,
NEAR-NEITHER flags, share vectors, medians, per-run medians, the
NOT-CARRIED rows, and the DERIVED semantic probe of the published
'min..max over the 18 pipeline-ok cells' column (the re-derived
per-cell pooled-median range is compared to the published column
and REPORTED -- the column's exact derivation semantics are NOT
frozen here and the probe NEVER fails the run).

Reads ONLY committed bytes (fail-closed; any parse anomaly is an
immediate recorded failure).  Writes NOTHING to the evidence tree;
prints the report to stdout, nothing to stderr on success.  Exit 0
iff every check is ok.

THREE-STATE: every sample value below is a named run's landed
MEASURED QUANTITY (its own hardware runs on aiueos-6600hs, Intel
BMG G31, under the named instrument), RE-PARSED here from committed
run-log bytes -- this script measures NOTHING new on hardware and
no value here is a measurement of this tick; the share/distance/
class arithmetic is DERIVED (labelled).  The verdict is scoped
EXACTLY as the criterion above.  The CAUSE of any shape difference
(execution-time state vs instrument/timestamp-quantization state)
stays UNMEASURED; the underlying-instrument-state COUNT stays
outside (s220 1(b) binds).  RULE 4 unchanged: NOTHING MOVES; the
committed bracket stays EXACTLY (254,923, 255,045]; the
accelerator-targets workgroup rows stay exactly as ADR-0358 left
them (:measured? false rows remain provisional -- NOT optimization
evidence); NO vendor optimization exists for Intel (or for any
vendor) and none follows from this check.
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

EXACT_SPV = "subgroup-reduce-w128-sum.emitted.spv"
CELL_KEY = ("sum", "128", "16")  # the reading cell (op, wg, forced)

# the nine committed reference windows (the s234 universe; copied
# verbatim from prepool-shape-s235.py, bound 9/9 to the s234 tuples)
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
REF_KEYS = {(d, fam) for _, d, fam, _ in REF_WINDOWS}

# committed cross-check pins / report files parsed below
S27 = GPU / "anv-b3bisect7-20261027" / "derivation-census-s27.txt"
S234_REPORT = HERE / "identity-shape-s234-run1.txt"
S234_SCRIPT = HERE / "identity-shape-s234.py"
S235_REPORT = HERE / "prepool-shape-s235-run1.txt"
S236_REPORT = HERE / "map-sessions-s236-run1.txt"
C2_PIN, C8_PIN = 31, 32915  # s27 line-43 pins (cross-checked below)

problems = []
n_checks = [0]

def check(ok, label, quiet=False):
    n_checks[0] += 1
    if ok:
        if not quiet:
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

def read_bytes(path):
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rb") as fh:
        return fh.read()

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

def shares(pool, support):
    cnt = Counter(pool)
    n = len(pool)
    return {t: cnt.get(t, 0) * 100.0 / n for t in support}

def l1(a, b, support):
    return sum(abs(a.get(t, 0.0) - b.get(t, 0.0)) for t in support)

# ================================================================
P("kernel-shape-s237.py -- THE EXCLUDED KERNEL-VARIANT ARMS'")
P("(sum,128,16) SAMPLE-SHAPE CHECK")
P()
P("THE ROW (the s236 carry-forward's QUEUED row (iii)):")
P("'the excluded kernel-variant arms' (sum,128,16) shapes")
P("(iter1/iter3/iter8 spvs) stay UNCHECKED (out of scope by the")
P("s235 bytes-forced correction) -- QUEUED for s237' -- taken as")
P("this tick's ONE row.  The criterion is frozen in this file's")
P("docstring BEFORE any number below is computed.")
P()

# ----------------------------------------------------------------
# 0. the row quote binds to the committed s236 report bytes (B1)
# ----------------------------------------------------------------
P("0. THE ROW'S COMMITTED SOURCE (B1):")
s236_text = S236_REPORT.read_text()
check("excluded kernel-variant arms" in s236_text,
      "s236 report carries the 'excluded kernel-variant arms' row")
check("QUEUED for s237" in s236_text,
      "s236 report carries the 'QUEUED for s237' queue mark")

# ----------------------------------------------------------------
# 1. the committed s235 named-exclusion block (B2, parse side)
# ----------------------------------------------------------------
P()
P("1. THE COMMITTED s235 NAMED-EXCLUSION BLOCK (the row's own")
P("   source) PARSED from prepool-shape-s235-run1.txt bytes:")

s235_text = S235_REPORT.read_text()
excl_block = {}
for mm in re.finditer(
        r"^     (\S+)/(\S+): \('variant', \('([^']+)',\)\)$",
        s235_text, re.M):
    excl_block[(mm.group(1), mm.group(2))] = mm.group(3)
excl_runs = {}
for mm in re.finditer(
        r"^     NAMED EXCLUSION (\S+): the \(sum,128,16\) key exists"
        r" only under spv variant \['([^']+)'\]",
        s235_text, re.M):
    excl_runs[mm.group(1)] = mm.group(2)
check(len(excl_block) == 8,
      f"s235 named-exclusion block carries 8 window rows (got {len(excl_block)})")
check(len(excl_runs) == 24,
      f"s235 NAMED-EXCLUSION run lines carry 24 rows (got {len(excl_runs)})")
for (d, fam), spv in sorted(excl_block.items()):
    P(f"     committed window row: {d}/{fam} -> {spv}")
P(f"   NAMED SPELLING OMISSION in the queue parenthetical: the")
P(f"   s236 NOT-DONE line enumerates (iter1/iter3/iter8 spvs); the")
P(f"   committed block above carries FOUR spellings --")
P(f"   {', '.join(sorted({s.split('.emitted.')[1] for s in excl_block.values()}))}"
  f" -- this slice takes the whole committed excluded set.")

# ----------------------------------------------------------------
# 2. raw-log census + c2-rung universe (B3, re-derived)
# ----------------------------------------------------------------
P()
P("2. RAW-LOG CENSUS + c2-RUNG UNIVERSE (the s235 census rule")
P("   re-derived here from committed bytes; the s235 script NOT")
P("   re-run):")

all_run_files = sorted(p for p in GPU.rglob("run-*")
                       if p.is_file() and not p.name.endswith(".stderr.txt"))
v2_files, v1_files, other_files = [], [], []
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
P(f"   run-* raw logs found: {len(all_run_files)}")
P(f"   v2 instrument: {len(v2_files)}")
P(f"   v1 instrument (older family): {len(v1_files)}")
P(f"   other/non-run-log first lines: {len(other_files)}")

# census-row binding to the committed s235 report (B3)
for label, pat, val in (
        ("raw-log total", r"run-\* raw logs found: (\d+)", len(all_run_files)),
        ("v2 count", r"v2 instrument \([^)]*\.\.\.\): (\d+)", len(v2_files)),
        ("v1 count", r"v1 instrument \(older family\): (\d+)", len(v1_files)),
        ("other count", r"other/non-run-log first lines: (\d+)",
         len(other_files))):
    mm = re.search(pat, s235_text)
    check(mm is not None, f"s235 census row parses: {label}")
    if mm:
        check(int(mm.group(1)) == val,
              f"{label} {val} == s235 report row {mm.group(1)}")

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
P(f"   v2 runs at other knob sets (named, excluded): {len(other_knob)}")
P(f"   c2-RUNG UNIVERSE RUNS: {len(universe)}")
groups = {}
for p, fam, knobs, rounds in universe:
    groups.setdefault((str(p.parent.relative_to(GPU)), fam), []).append(p)
P(f"   c2-rung windows (dir x arm family): {len(groups)}")
check(len(v2_files) + len(v1_files) + len(other_files) == len(all_run_files),
      "raw-log census reconciles: v2 + v1 + other == every run-* file")
check(len(universe) + len(other_knob) == len(v2_files),
      "v2 census reconciles: c2-rung + other-knob == every v2 run")
for label, pat, val in (
        ("other-knob runs", r"v2 runs at other knob sets [^:]*: (\d+)",
         len(other_knob)),
        ("universe runs", r"c2-RUNG UNIVERSE RUNS: (\d+)", len(universe)),
        ("universe windows", r"c2-rung windows \(dir x arm family\): (\d+)",
         len(groups))):
    mm = re.search(pat, s235_text)
    check(mm is not None, f"s235 census row parses: {label}")
    if mm:
        check(int(mm.group(1)) == val,
              f"{label} {val} == s235 report row {mm.group(1)}")

# ----------------------------------------------------------------
# 3. fail-closed parse of every universe run (B6); verbose only for
#    the reference windows and the committed variant windows
# ----------------------------------------------------------------
P()
P("3. FAIL-CLOSED PARSE OF EVERY UNIVERSE RUN (verbose rows for")
P("   the 9 reference + 8 variant windows; other windows quiet --")
P("   their checks count, FAILs always print):")

variant_pools = {}     # (dir, fam) -> pooled gpu_ticks at the variant cell
variant_runmed = {}    # (dir, fam) -> per-run medians at the variant cell
variant_spv = {}       # (dir, fam) -> variant spv name
variant_cellpools = {} # (dir, fam) -> {idx: pooled gpu_ticks over ok cells}
ref_pools = {}         # label -> pooled gpu_ticks at the exact cell
group_rounds = {}
map_digests = Counter()
total_samples = 0
verify_mismatch_total = 0
derived_excl_block = {}
derived_excl_runs = {}
quiet_windows = 0
quiet_checks = 0

for key in sorted(groups):
    d, fam = key
    verbose = key in REF_KEYS or key in excl_block
    if not verbose:
        quiet_windows += 1
    pool = []            # exact reading-cell samples (s235 semantics)
    vpool = []           # variant-cell samples (this slice's scope)
    vrunmed = []         # per-run medians at the variant cell
    cellpools = {}       # idx -> pooled samples over the window's runs
    rounds_seen = set()
    status_seen = set()
    spv_seen = set()
    okidx_seen = set()
    read_idx = None
    for p in sorted(groups[key]):
        rel = str(p.relative_to(GPU))
        lines = read_lines(p)
        head = lines[:10]
        hdr = next(l for l in head if l.startswith("# n="))
        m = HEADER_RE.match(hdr)
        check(m is not None, f"{rel} header parses", quiet=not verbose)
        if not m:
            continue
        n, rounds, warmup, batch = (int(m.group(1)), int(m.group(2)),
                                    int(m.group(3)), int(m.group(4)))
        kv = dict(re.findall(r"(\w+)=(\S+)", m.group(5)))
        rounds_seen.add(rounds)
        check(rounds in (25, 6400), f"{rel} rounds {rounds} in (25, 6400)",
              quiet=not verbose)
        check(kv.get("seed") == "20261027", f"{rel} seed=20261027",
              quiet=not verbose)
        check(head[0] == V2_INSTR, f"{rel} instrument line exact",
              quiet=not verbose)
        check(head[1].startswith(DEVICE_PREFIX), f"{rel} device line prefix",
              quiet=not verbose)
        check(any(l.startswith("# timestampPeriod=52.083") for l in head),
              f"{rel} timestampPeriod=52.083 pinned", quiet=not verbose)
        cells = []
        sample_n = verify_n = done_n = 0
        read_idx = None
        variant_idx = {}
        file_pool = []
        vfile_pool = []
        per_idx = Counter()
        for line in lines:
            if line.startswith("CELL "):
                cm = CELL_RE.match(line)
                if cm is None:
                    check(False, f"{rel} CELL row parse")
                    continue
                cells.append(cm.groups())
                if (cm.group(3), cm.group(4), cm.group(5)) == CELL_KEY:
                    if cm.group(2) == EXACT_SPV:
                        check(cm.group(9) == "ok",
                              f"{rel} reading cell pipeline=ok",
                              quiet=not verbose)
                        check(read_idx is None, f"{rel} reading cell unique",
                              quiet=not verbose)
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
                if idx in variant_idx.values():
                    vfile_pool.append((idx, ticks))
            elif line.startswith("VERIFY "):
                vm = VERIFY_RE.match(line)
                if vm is None:
                    check(False, f"{rel} VERIFY row parse")
                    continue
                verify_n += 1
                verify_mismatch_total += int(vm.group(3))
            elif line == "# done cells=24":
                done_n += 1
        if read_idx is not None:
            check(not variant_idx,
                  f"{rel} no (sum,128,16) spv-variant duplicate",
                  quiet=not verbose)
        else:
            check(bool(variant_idx),
                  f"{rel} (sum,128,16) key present (exact or named variant)",
                  quiet=not verbose)
        check(len(cells) == 24, f"{rel} 24 CELL rows (got {len(cells)})",
              quiet=not verbose)
        ok_cells = [c for c in cells if c[8] == "ok"]
        check(len(ok_cells) == 18, f"{rel} 18 pipeline-ok cells",
              quiet=not verbose)
        check(sample_n == 18 * rounds,
              f"{rel} SAMPLE count {sample_n} == 18*rounds", quiet=not verbose)
        for c in ok_cells:
            check(per_idx.get(int(c[0]), 0) == rounds,
                  f"{rel} idx={c[0]} samples == rounds", quiet=not verbose)
        for c in cells:
            if c[8] != "ok":
                check(per_idx.get(int(c[0]), 0) == 0,
                      f"{rel} FAIL cell idx={c[0]} has no samples",
                      quiet=not verbose)
        check(verify_n == 24, f"{rel} 24 VERIFY rows", quiet=not verbose)
        check(done_n == 1, f"{rel} tail '# done cells=24'", quiet=not verbose)
        okidx = tuple(sorted(int(c[0]) for c in ok_cells))
        okidx_seen.add(okidx)
        if read_idx is not None:
            check(len(file_pool) == rounds,
                  f"{rel} reading-cell samples {len(file_pool)} == rounds",
                  quiet=not verbose)
            pool.extend(file_pool)
            status_seen.add("exact")
        else:
            check(bool(variant_idx),
                  f"{rel} variant run carries a (sum,128,16) key",
                  quiet=not verbose)
            check(len(variant_idx) == 1,
                  f"{rel} exactly one (sum,128,16) variant key "
                  f"(got {sorted(variant_idx)})", quiet=not verbose)
            if variant_idx:
                vidx = next(iter(variant_idx.values()))
                vspv = next(iter(variant_idx))
                spv_seen.add(vspv)
                derived_excl_runs[rel] = vspv
                check(len(vfile_pool) == rounds,
                      f"{rel} variant-cell samples {len(vfile_pool)} == rounds",
                      quiet=not verbose)
                vrunmed.append(median2([t for _, t in vfile_pool]))
                for idx, t in vfile_pool:
                    vpool.append(t)
                for c in ok_cells:
                    idx = int(c[0])
                    cellpools.setdefault(idx, [])
            status_seen.add(("variant", tuple(sorted(variant_idx))))
        # per-cell pooling over ALL ok cells (variant windows only;
        # the derived semantic probe of the published minmax column)
        if read_idx is None and variant_idx:
            for line in lines:
                if line.startswith("SAMPLE "):
                    sm = SAMPLE_RE.match(line)
                    if sm is None:
                        continue
                    idx = int(sm.group(2))
                    if idx in cellpools:
                        cellpools[idx].append(int(sm.group(6)))
        map_digests[hashlib.sha256(
            "|".join(",".join(c[:7]) for c in cells).encode()).hexdigest()[:16]] \
            += 1
        total_samples += len(file_pool)
        if verbose:
            P(f"     pin {rel} bytes={len(read_bytes(p))} "
              f"sha256={sha256_file(p)}")
    if not verbose:
        quiet_checks += 0
        P(f"     quiet window {d}/{fam}: {len(groups[key])} runs parsed")
    check(len(status_seen) == 1,
          f"{d}/{fam} reading-cell status uniform across its runs",
          quiet=not verbose)
    check(len(rounds_seen) == 1,
          f"{d}/{fam} rounds uniform across its runs", quiet=not verbose)
    check(len(okidx_seen) == 1,
          f"{d}/{fam} ok-cell idx set uniform across its runs",
          quiet=not verbose)
    if read_idx is None and "variant" in {s[0] if isinstance(s, tuple) else s
                                          for s in status_seen}:
        check(len(spv_seen) == 1,
              f"{d}/{fam} variant spv uniform across its runs",
              quiet=not verbose)
        derived_excl_block[(d, fam)] = next(iter(spv_seen))
    if pool:
        # exact-cell windows (the s235 universe proper); no pooling here
        group_rounds[key] = next(iter(rounds_seen))
    if vpool:
        variant_pools[key] = vpool
        variant_runmed[key] = vrunmed
        variant_spv[key] = next(iter(spv_seen))
        variant_cellpools[key] = cellpools
        group_rounds[key] = next(iter(rounds_seen))
        check(len(vpool) == 75,
              f"{d}/{fam} variant-cell pool N={len(vpool)} == 75")
    if key in REF_KEYS:
        label = next(l for l, dd, ff, _ in REF_WINDOWS
                     if (dd, ff) == key)
        ref_pools[label] = pool
        group_rounds[key] = next(iter(rounds_seen))

P(f"   universe runs parsed: {len(universe)}; exact reading-cell")
P(f"   samples pooled (s235 semantics): {total_samples}")
P(f"   cell-map digests across the universe: {len(map_digests)} distinct")
for dig, cnt in sorted(map_digests.items()):
    P(f"     {cnt:4d}  {dig}")
P(f"   VERIFY mismatch total over every universe run: {verify_mismatch_total}")
check(verify_mismatch_total == 0,
      "VERIFY mismatches zero over every universe run")

# B3 census bindings (counts + digests + pooled total)
mm = re.search(r"universe runs parsed: (\d+); reading-cell samples"
               r" pooled: (\d+)", s235_text)
check(mm is not None, "s235 universe-parsed row parses")
if mm:
    check(int(mm.group(1)) == len(universe),
          f"universe runs parsed {len(universe)} == s235 row")
    check(int(mm.group(2)) == total_samples,
          f"exact-cell samples pooled {total_samples} == s235 row 176250")
mm = re.search(r"cell-map digests across the universe: (\d+) distinct",
               s235_text)
check(mm is not None and int(mm.group(1)) == len(map_digests),
      f"cell-map digest count {len(map_digests)} == s235 row")
mm = re.search(r"cell-map digests across the universe: \d+ distinct\n"
               r"((?:\s+\d+\s+[0-9a-f]{16}\s*\n)+)", s235_text)
check(mm is not None, "s235 cell-map digest block parses")
dig_rows = re.findall(r"^\s+(\d+)\s+([0-9a-f]{16})\s*$",
                      mm.group(1) if mm else "", re.M)
s235_digests = Counter()
for cnt, dig in dig_rows:
    s235_digests[dig] += int(cnt)
check(s235_digests == map_digests,
      "re-derived (count,digest) rows == s235 report rows")
mm = re.search(r"VERIFY mismatch total over every universe run: (\d+)",
               s235_text)
check(mm is not None and int(mm.group(1)) == verify_mismatch_total,
      f"VERIFY mismatch total {verify_mismatch_total} == s235 row")

# B2: the re-derived variant set == the committed s235 block (both ways)
P()
P("   B2: the re-derived variant set vs the committed s235")
P("   named-exclusion block:")
check(derived_excl_block == excl_block,
      f"re-derived variant window set == committed 8 rows "
      f"({len(derived_excl_block)} vs {len(excl_block)})")
check(derived_excl_runs == excl_runs,
      f"re-derived variant run set == committed 24 rows "
      f"({len(derived_excl_runs)} vs {len(excl_runs)})")
check(set(derived_excl_block) == set(variant_pools),
      "every re-derived variant window pooled (N=75 each)")
for (d, fam), spv in sorted(derived_excl_block.items()):
    P(f"     {d}/{fam}: variant {spv}, runs "
      f"{len(groups[(d, fam)])}, N={len(variant_pools.get((d, fam), []))}")

# ----------------------------------------------------------------
# 4. the nine references re-derived + B4 bindings
# ----------------------------------------------------------------
P()
P("4. THE NINE REFERENCE WINDOWS RE-DERIVED from the committed")
P("   run logs (m = pooled sample median gpu_ticks at the reading")
P("   cell; letters = f(m vs the committed floor band 31..32 at")
P("   B=2)); B4 bindings to the committed s234/s235 report rows:")

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

ref_m, ref_letter = {}, {}
for label, d, fam, letter in REF_WINDOWS:
    key = (d, fam)
    check(key in {(dd, ff) for _, dd, ff, _ in REF_WINDOWS},
          f"{label} key well-formed")
    if label not in ref_pools:
        check(False, f"{label} pooled exact reading-cell samples present")
        continue
    pool = ref_pools[label]
    check(len(pool) > 0, f"{label} pooled exact reading-cell samples present")
    m = statistics.median(pool)
    m2 = median2(pool)
    check(m == m2, f"{label} independent median re-derivation agrees")
    ref_m[label] = m
    der = "a" if band[0] <= m <= band[1] else "b"
    ref_letter[label] = der
    check(der == letter,
          f"{label} derived letter ({der}) == committed record ({letter})")
    check(len(pool) == 19200, f"{label} N=3R=19,200 pooled")

U9 = sorted({t for label in ref_pools for t in ref_pools[label]})
ref_shares = {label: shares(ref_pools[label], U9) for label in ref_pools}

# s234 per-window share-row binding (the s235 binding, repeated)
s234_share_rows = {}
for line in s234_text.splitlines():
    mm = re.match(r"^\s+(\S+)\s+((?:\d+:[\d.]+\s*)+)$", line)
    if mm and mm.group(1) in ref_pools:
        s234_share_rows[mm.group(1)] = {
            int(t): float(s) for t, s in
            re.findall(r"(\d+):([\d.]+)", mm.group(2))}
for label in ref_pools:
    s234_row = s234_share_rows.get(label)
    check(s234_row is not None, f"{label} s234 report share row present")
    if s234_row:
        agree = all(round(ref_shares[label].get(t, 0.0), 4) == s
                    for t, s in s234_row.items()) and \
                all(round(v, 4) == s234_row.get(t, 0.0)
                    for t, v in ref_shares[label].items() if v != 0.0)
        check(agree, f"{label} re-derived shares == s234 report row")

group_a = [l for l in ref_pools if ref_letter.get(l) == "a"]
group_b = [l for l in ref_pools if ref_letter.get(l) == "b"]
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
    # B4: bind to the committed s234 (single-line) AND s235
    # (header + next-line share row) pooled rows
    mm = re.search(rf"group {re.escape(tag)} pooled: "
                   r"((?:\d+:[\d.]+\s*)+)", s234_text)
    check(mm is not None, f"group {tag} pooled row parses in s234 report")
    if mm:
        pooled = {int(t): float(s) for t, s in
                  re.findall(r"(\d+):([\d.]+)", mm.group(1))}
        agree = all(round(R.get(t, 0.0), 4) == s for t, s in pooled.items())
        check(agree, f"group {tag} pooled reference == s234 report row")
    mm = re.search(rf"group {re.escape(tag)} pooled reference[^\n]*:\n"
                   r"\s+((?:\d+:[\d.]+\s*)+)", s235_text)
    check(mm is not None, f"group {tag} pooled row parses in s235 report")
    if mm:
        pooled = {int(t): float(s) for t, s in
                  re.findall(r"(\d+):([\d.]+)", mm.group(1))}
        agree = all(round(R.get(t, 0.0), 4) == s for t, s in pooled.items())
        check(agree, f"group {tag} pooled reference == s235 report row")

within = []
between = []
labels = list(ref_pools)
for i, x in enumerate(labels):
    for y in labels[i + 1:]:
        dd = l1(ref_shares[x], ref_shares[y], U9)
        if ref_letter[x] == ref_letter[y]:
            within.append((dd, x, y))
        else:
            between.append((dd, x, y))
W_in = max(within)
W_out = min(between)
P(f"   W_in  = max within-group L1 = {W_in[0]:.4f} ({W_in[1]} vs"
  f" {W_in[2]})")
P(f"   W_out = min between-group L1 = {W_out[0]:.4f} ({W_out[1]} vs"
  f" {W_out[2]})")
for src, src_text in (("s235", s235_text), ("s234", s234_text)):
    wm = re.search(r"W_in  = max within-group L1 = ([\d.]+) \((\S+) vs (\S+)\)",
                   src_text)
    wo = re.search(r"W_out = min between-group L1 = ([\d.]+) \((\S+) vs (\S+)\)",
                   src_text)
    check(wm is not None and wo is not None, f"{src} W_in/W_out rows parse")
    check(wm and round(W_in[0], 4) == float(wm.group(1))
          and {W_in[1], W_in[2]} == {wm.group(2), wm.group(3)},
          f"re-derived W_in == {src} report row")
    check(wo and round(W_out[0], 4) == float(wo.group(1))
          and {W_out[1], W_out[2]} == {wo.group(2), wo.group(3)},
          f"re-derived W_out == {src} report row")

# ----------------------------------------------------------------
# 5. the eight kernel-variant windows' shapes (the row proper)
# ----------------------------------------------------------------
P()
P("5. THE EIGHT KERNEL-VARIANT WINDOWS' (sum,128,16) SAMPLE")
P("   SHAPES (the criterion frozen before the numbers; DERIVED")
P("   arithmetic; pattern-level only; SUPPLEMENTARY -- the variant")
P("   cell executes the iterated kernel spv, NOT the record's")
P("   reading-cell kernel):")

U_all = sorted({t for key in variant_pools for t in variant_pools[key]}
               | set(U9))
P(f"   union support U of gpu_ticks over the 9 reference + 8")
P(f"   variant pools: {U_all}")
P(f"   (reference support U9: {U9})")
check(set(U9) <= set(U_all), "U9 subset of U")
R_a_all = {t: R_a.get(t, 0.0) for t in U_all}
R_b_all = {t: R_b.get(t, 0.0) for t in U_all}

rows = []
for key in sorted(variant_pools):
    d, fam = key
    pool = variant_pools[key]
    sw = shares(pool, U_all)
    D_a = l1(sw, R_a_all, U_all)
    D_b = l1(sw, R_b_all, U_all)
    cls = ("(a)" if D_a < D_b else "(b)" if D_b < D_a else "UNDECIDED")
    flag = " NEAR-NEITHER" if min(D_a, D_b) > W_in[0] else ""
    m = statistics.median(pool)
    m2 = median2(pool)
    check(m == m2, f"{d}/{fam} independent median re-derivation agrees")
    rows.append((d, fam, variant_spv[key], len(groups[key]),
                 group_rounds[key], len(pool), m, D_a, D_b, cls, flag, sw))
    P(f"   window {d}/{fam} (spv {variant_spv[key]}):")
    P(f"     runs={len(groups[key])} rounds={group_rounds[key]} "
      f"N={len(pool)} m={m:.1f} "
      f"per-run medians={[f'{x:.1f}' for x in variant_runmed[key]]}")
    P("     shares: " + "  ".join(f"{t}:{sw[t]:.4f}"
                                  for t in U_all if sw[t] != 0.0))

P()
P(f"   {'dir':<32} {'arm':<6} {'spv':>7} {'runs':>4} {'rnd':>5} {'N':>4}"
  f" {'m':>5} {'D_a':>9} {'D_b':>9}  class  flag")
for (d, fam, spv, nr, rnd, n, m, D_a, D_b, cls, flag, sw) in rows:
    suffix = spv.split(".emitted.")[1].replace(".spv", "")
    P(f"   {d:<32} {fam:<6} {suffix:>7} {nr:>4} {rnd:>5} {n:>4}"
      f" {m:>5.1f} {D_a:>9.4f} {D_b:>9.4f}  {cls}{flag}")

cls_counts = Counter(r[9] for r in rows)
flagged = [r for r in rows if r[10]]
P(f"   classification census over {len(rows)} kernel-variant windows:"
  f" (a) {cls_counts.get('(a)', 0)}, (b) {cls_counts.get('(b)', 0)},"
  f" UNDECIDED {cls_counts.get('UNDECIDED', 0)}")
P(f"   NEAR-NEITHER flags (min(D_a,D_b) > W_in {W_in[0]:.4f}):"
  f" {len(flagged)}")
for r in flagged:
    P(f"     {r[0]} {r[1]} N={r[5]} D_a={r[7]:.4f} D_b={r[8]:.4f}")
P(f"   variant-spv split: "
  f"{dict(sorted(Counter(r[2] for r in rows).items()))}")

# DERIVED cross-dir identity REPORT (never a check): are any of the
# 24 variant run logs byte-identical copies across dirs?
P()
P("   DERIVED CROSS-DIR IDENTITY REPORT (never a check; the raw-")
P("   log sha256s are the section-3 pins):")
sha_class = {}
for rel in sorted(derived_excl_runs):
    p = GPU / rel
    sha_class.setdefault(sha256_file(p), []).append(rel)
P(f"   the 24 variant run logs form {len(sha_class)} distinct byte")
P(f"   classes (sha256 of the raw log):")
for sha, rels in sorted(sha_class.items(), key=lambda kv: kv[1][0]):
    if len(rels) > 1:
        P(f"     DUPLICATE CLASS {sha[:16]}: {rels}")
dup_classes = [rels for rels in sha_class.values() if len(rels) > 1]
n_dup_rows = sum(len(rels) for rels in dup_classes)
P(f"   NAMED, NOT HIDDEN: {n_dup_rows} of the 24 variant run logs")
P(f"   sit in {len(dup_classes)} byte-duplicate cross-dir classes --")
P(f"   the classification census above counts committed ROWS (8")
P(f"   windows); the byte classes show how many DISTINCT sample")
P(f"   pools those rows carry (reported, never a check).")

# ----------------------------------------------------------------
# 6. publication binding under frozen form T1 (B5) + the derived
#    semantic probe of the published minmax column (REPORT)
# ----------------------------------------------------------------
P()
P("6. PUBLICATION BINDING under the frozen table-row form T1")
P("   ('<arm> <cols...> <value> <lo>..<hi> <lo>..<hi> <host_ns>';")
P("   every line starting with the arm name followed by a digit")
P("   must parse; re-derived pooled median == <value>; re-derived")
P("   per-run median band == <lo>..<hi>); NOT-CARRIED rows are")
P("   REPORTS (named, never checks):")

for (d, fam, spv, nr, rnd, n, m, D_a, D_b, cls, flag, sw) in rows:
    pubs = sorted((GPU / d).glob("publication-*.txt"))
    text = "\n".join(p.read_text() for p in pubs)
    pot = re.findall(rf"(?m)^[ \t]*{re.escape(fam)}[ \t]+\d[^\n]*", text)
    row_re = re.compile(
        rf"(?m)^[ \t]*{re.escape(fam)}[ \t]+(?:\S+[ \t]+)*?"
        rf"(\d+)[ \t]+(\d+)\.\.(\d+)[ \t]+(\d+)\.\.(\d+)[ \t]+(\d+)[ \t]*$")
    parsed = row_re.findall(text)
    check(len(parsed) == len(pot),
          f"{d}/{fam} potential T1 bindings all parse under T1 "
          f"({len(parsed)} rows / {len(pot)} potentials)")
    if not pot:
        P(f"     {d}/{fam}: NOT-CARRIED (no '<arm> <digit>...' row in "
          f"{','.join(p.name for p in pubs) or 'no publication-*.txt'})")
        continue
    for (val, b1, b2, m1, m2, host) in parsed:
        val, b1, b2 = int(val), int(b1), int(b2)
        m1, m2, host = int(m1), int(m2), int(host)
        if float(m).is_integer():
            check(int(m) == val,
                  f"{d}/{fam} re-derived pooled median {int(m)} == "
                  f"published {val}")
        else:
            P(f"     {d}/{fam} NAMED-UNCOMPARABLE m={m} pub={val}")
        rmed = variant_runmed[(d, fam)]
        check(min(rmed) == float(b1) and max(rmed) == float(b2),
              f"{d}/{fam} re-derived run-median band "
              f"{min(rmed):.1f}..{max(rmed):.1f} == published {b1}..{b2}")
        # DERIVED semantic probe (REPORT, never a check): the
        # published 'min..max over the 18 pipeline-ok cells' column
        # vs the re-derived per-cell pooled-median range over the
        # window's ok cells.
        cell_meds = [median2(cp) for cp in
                     variant_cellpools[(d, fam)].values()]
        probe = ((min(cell_meds), max(cell_meds)) == (m1, m2))
        P(f"     {d}/{fam} DERIVED semantic probe (REPORT, not bound):"
          f" published minmax {m1}..{m2}; re-derived per-cell pooled-"
          f"median range over {len(cell_meds)} ok cells "
          f"{min(cell_meds):.1f}..{max(cell_meds):.1f}"
          f" ({'MATCHES' if probe else 'DIFFERS'})")

# ----------------------------------------------------------------
# 7. the answer for the row
# ----------------------------------------------------------------
P()
P("7. THE ANSWER FOR THE ROW (the s236 carry-forward's QUEUED")
P("   row (iii): 'the excluded kernel-variant arms' (sum,128,16)")
P("   shapes (iter1/iter3/iter8 spvs) stay UNCHECKED'; pattern-")
P("   level only, scoped to the committed bytes):")
P(f"   over the {len(rows)} kernel-variant windows / "
  f"{sum(len(groups[k]) for k in variant_pools)} runs the s235")
P(f"   bytes-forced correction excluded from the shape scope --")
P(f"   every (sum,128,16) sample RE-PARSED here from the committed")
P(f"   run logs under the window's own named variant spv")
P(f"   (iter1/iter3/iter8/itervc8), N=75 per window (3 runs x 25")
P(f"   rounds) -- the reading-cell sample shape SHARES the (a)")
P(f"   reference shape in {cls_counts.get('(a)', 0)} windows, the")
P(f"   (b) reference shape in {cls_counts.get('(b)', 0)}, and is")
P(f"   UNDECIDED (exact D tie) in {cls_counts.get('UNDECIDED', 0)}")
P(f"   -- under the s235 criterion applied unchanged (nearest")
P(f"   reference by L1 of per-sample share vectors over the union")
P(f"   support U; W_in={W_in[0]:.4f} reported as the near-neither")
P(f"   gate; {len(flagged)} of {len(rows)} windows flagged")
P(f"   NEAR-NEITHER).  At N=75 the classification carries NO noise")
P(f"   model (the s235 (i) caveat binds verbatim) and is reported")
P(f"   as-is.  PATTERN-LEVEL ONLY (s218 2(e)): NO p-value, NO test")
P(f"   statistic, NO probability claim.")
P(f"   NAMED: the 8 classification rows form")
win_class = {}
for (d, fam) in sorted(variant_pools):
    shas = tuple(sorted(sha256_file(p) for p in groups[(d, fam)]))
    win_class.setdefault(shas, []).append(f"{d}/{fam}")
P(f"   {len(win_class)} distinct pool byte-classes (a row is a")
P(f"   duplicate iff its run sha256s match another row's):")
for shas, wins in sorted(win_class.items(), key=lambda kv: kv[1][0]):
    if len(wins) > 1:
        P(f"     DUPLICATE ROWS {wins} (identical run logs)")
P(f"   -- the census counts committed rows; the byte classes show")
P(f"   how many DISTINCT sample pools those rows carry (reported,")
P(f"   never a check).")
P(f"   SUPPLEMENTARY, CROSS-KERNEL: the variant cell executes the")
P(f"   iterated kernel spv (its own bytes) where the record's")
P(f"   reading cell executes the archived .emitted.spv -- these")
P(f"   rows do NOT extend the s234 (a)/(b) state-IDENTITY claim to")
P(f"   these arms, do NOT put them in the record's reading scope,")
P(f"   and move NO record row.  The s234 separation (W_out")
P(f"   {W_out[0]:.4f} > W_in {W_in[0]:.4f}) is re-derived here")
P(f"   UNCHANGED.")
P(f"   The CAUSE of any shape difference (execution-time state vs")
P(f"   instrument/timestamp-quantization state) stays UNMEASURED;")
P(f"   the underlying-instrument-state COUNT stays outside (s220")
P(f"   1(b)).")

# ----------------------------------------------------------------
# 8. three-state / scope / carry-forward
# ----------------------------------------------------------------
P()
P("8. THREE-STATE / SCOPE / RULE 4 / BAR: every sample re-parsed")
P("   here is a named run's landed MEASURED QUANTITY on aiueos-6600hs")
P("   (Intel BMG G31) under the named instrument -- this tick")
P("   measures NOTHING new on hardware (NO runs, NO builds, NO GO")
P("   stamp); the shares/distances/classes are DERIVED arithmetic;")
P("   the accelerator-targets workgroup rows stay exactly as")
P("   ADR-0358 left them (:measured? false rows remain provisional")
P("   -- NOT optimization evidence); NO vendor optimization exists")
P("   for Intel (or for any vendor) and none follows from this")
P("   check.  RULE 4 unchanged: NOTHING MOVES; the committed")
P("   bracket stays EXACTLY (254,923, 255,045]; L9 binds at")
P("   n=254,984 (C2 (c), D3 (v)); the MID-ONLY NARROWING CLAIM stays")
P("   SUSPENDED.  BAR NON-INTERFERENCE: NO settle-bar-ledger line,")
P("   NO day-slot consumption; the bar's SETTLED INTERMEDIATE/MIXED")
P("   verdict unmoved.")
P()
P("   NAMED, NOT HIDDEN: (a) the queue parenthetical enumerates")
P("   (iter1/iter3/iter8 spvs) while the committed exclusion set")
P("   carries a fourth spelling (itervc8 at anv-costcal-20261027/")
P("   f8vc) -- the whole committed excluded set is this row's")
P("   universe and the omission is named, not silently dropped;")
P("   (b) the published 'min..max over the 18 pipeline-ok cells'")
P("   column's exact derivation semantics are NOT frozen here --")
P("   the derived per-cell pooled-median range probe above is a")
P("   REPORT and never a check;")
P("   (c) the reference construction here is the s235/s234 one")
P("   re-derived and bound at both report layers; the s235 script")
P("   itself is NOT re-run;")
P("   (d) 3 of the 8 classification rows (anv-b3bisect-20261027")
P("   f1b2/f3b2/f8b2) are byte-identical cross-dir re-captures of")
P("   the anv-itrmul-20261027 rows -- 8 committed rows, 5 distinct")
P("   sample pools (the section-5/section-7 byte-class reports).")
P()
P("   NOT DONE (s238 carries exactly this list): the s216 identity")
P("   hazard's remaining residuals (standing, not queued): the")
P("   CAUSE of the sample-shape difference (execution-time state vs")
P("   instrument/timestamp-quantization state) stays UNMEASURED;")
P("   the underlying-instrument-state COUNT stays outside (s220")
P("   1(b)); at N=75 the classifications carry NO noise model and")
P("   near-neither prevalence needs higher-N readings -- new")
P("   hardware runs, each with its own freeze (standing, not")
P("   queued); standing, not queued: any further counted-day slot")
P("   (each needs its own freeze) and the cross-day tail-movement")
P("   row.  NOTHING is QUEUED at s238 from this row: the queued")
P("   row (iii) is answered here.")
P()
P(f"checks: {n_checks[0]} run; failures: {len(problems)}")
P(f"# kernel-shape s237 (kernel-shape-s237.py):"
  f" {n_checks[0] - len(problems)} ok / {len(problems)} failed")
sys.exit(1 if problems else 0)
