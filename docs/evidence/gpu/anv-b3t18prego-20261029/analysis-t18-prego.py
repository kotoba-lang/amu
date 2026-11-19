#!/usr/bin/env python3
"""JUN-59 session 92 -- THE T18 ANALYSIS PRE-BUILD (analysis-t18-prego.py)

(the T18 row's ANALYSIS machinery pre-build -- NO hardware runs, NO
builds, NO compiles, NO GO stamp, NO host writes, NO day-slot
consumption, NO ledger line. Row: the s91 carry-forward's item (b)
(the T18 ANALYSIS half, the s84 freeze), taken to its PREPARATION
half -- the s69/s90 pre-build precedent applied to the s84-frozen
analysis path (docs/evidence/gpu/anv-b3w6dlrep-20261030/protocol.txt
sections 1/3/4/5/6/7). The analysis half itself REMAINS day-slot-
gated behind the W6 measurement half (STARTED, NOT FINISHED): it
runs only after the W6 measurement half (the first measurement
session at/after 2026-10-30T00:00:00Z) commits the W6 run logs.)

WHAT THIS IS (honest states): an IMPLEMENTATION pre-build of the
complete frozen T18 row -- the construction (section 1: named cell
(max,128,S=default), tw arm, 12 blocks of 3, per-block pooled-75
EXACT-INTEGER D at the closed DL vocabulary), the frozen null
(section 4: the s78 two-window run-exchangeability machinery,
ONE random.Random(2026102918), probe order DL4/DL8/DL16/DL32,
20,000 trials per probe, ONE rng.shuffle of a fresh
list(range(72)) per trial), the letters and the IUT joint
(section 5), the invalidation machinery (section 6) and the
D-family (section 7 -- D1/D2/D3, the D3 band under the s83/s89
CORRECTED [MIN,MAX] convention, NAMED). It is NOT the T18
session's script yet: the analysis session adopts this file as
analysis-s<NN>.py (the filename IS the mode switch -- full mode is
UNREACHABLE under this pre-build name) and owns its record.

MODES:
  (default under this pre-build name) --compat: the s84 section-6
    PARSER VALIDITY PINS recomputed over the five committed windows
    and two-way-checked against the COMMITTED publication bytes
    (want values PARSED from publication-s78.txt /
    publication-s82.txt, never transcribed): the publication-s78
    INNER (28,48) / OUTER (9,67) five-window 2*L vectors and W5
    block D vectors, the publication-s82 DL five-window 2*L
    vectors and W5 block D vectors -- plus the integrity/C1 parser
    rows -- plus the s78 NULL REPRODUCTION (the SAME frozen engine
    at the T15 row's seed 2026102815, probe order INNER then
    OUTER, window pair (s36, W5): reproducing publication-s78.txt's
    PUBLISHED T15 counts and p EXACTLY -- a validity recomputation
    of published frozen content, NOT a T18 statistic; T18 exists
    only at the (s36, W6) pair and only after W6 commits).
  --self-test: the fixture suite -- hand-computable degenerate null
    at the full 20,000 trials, an INDEPENDENT pure-Python twin of
    the null engine (NO numpy, explicit sorted() order statistics)
    cross-checked in-loop on synthetic data, the RNG stream
    determinism pins (generated ONCE at pre-build and committed;
    they certify stream stability across runs, NOT RNG
    correctness -- the engine itself is externally validated in
    --compat by the publication-s78 reproduction), the
    letter/joint tables, and a MOCK end-to-end run of the
    full-row glue on a deterministic synthetic 78-log window --
    MOCK numbers are FIXTURES, never measurements).
  analysis-s<NN>.py (the adopted frozen filename): the real T18
    row over the six windows; fail-closed (exit non-zero) if the
    W6 run logs are absent (the freeze: the analysis half runs
    only after the W6 measurement half commits them).

NO T18 quantity is computed in this pre-build: no (s36, W6)
contrast, no T18 p-value, no T18 letter on any real window pair.
Deterministic apart from the frozen null's seeded stream: the
claim is "run twice, byte-identical (cmp exit 0)".
"""
import hashlib
import os
import random
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
GPU = os.path.join(ROOT, "docs", "evidence", "gpu")
SCRATCH = os.path.join(ROOT, "scratch")

_name = os.path.basename(__file__)
_adopted = re.match(r"analysis-s(\d+)\.py$", _name)
SELFTST = "--self-test" in sys.argv[1:]
if _adopted:
    MODE = "full"
    SESSION = int(_adopted.group(1))
elif SELFTST:
    MODE = "selftest"
else:
    MODE = "compat"

WIN5 = [("s36", "anv-b3commonmode-20261028"),
        ("s38", "anv-b3joint3-20261028"),
        ("s39", "anv-b3joint4-20261028"),
        ("s51", "anv-b3levelrep-20261028"),
        ("s73", "anv-b3w5xdayrep-20261029")]
W6_DIR = "anv-b3w6daybar-20261030"
ARMS = {"c2": (2, 1, 1, [1, 2, 3]),
        "hi": (3, 1024, 4033, list(range(1, 37))),
        "tw": (3, 2048, 8066, list(range(1, 37))),
        "c8": (8, 1, 1, [1, 2, 3])}
COMMITTED_C8 = 32915
FLOOR_BAND = (31, 32)          # "committed floor band 31..32" (s78 section 2)
NAMED_CKEY = ("max", 128, "default")
CELLKEY_SUM128 = ("sum", 128, "16")

# The pair tables (0-based indices of the sorted pooled 75 for the
# 1-indexed rank pairs). QP pairs = the publication-s78 axes (their
# reproduction is a section-6 validity pin); DL pairs = the s81
# closed doubling-ladder vocabulary (the T18 construction).
QP_PAIRS = (("INNER (28,48)", 27, 47), ("OUTER (9,67)", 8, 66))
DL_PAIRS = (("DL4 (x_(34),x_(42))", 33, 41), ("DL8 (x_(30),x_(46))", 29, 45),
            ("DL16 (x_(22),x_(54))", 21, 53), ("DL32 (x_(6),x_(70))", 5, 69))
DL_ORDER = [p[0] for p in DL_PAIRS]     # frozen probe order (section 4)
DL_TBL = {p[0]: (p[1], p[2]) for p in DL_PAIRS}
QP_TBL = {p[0]: (p[1], p[2]) for p in QP_PAIRS}
INFORMATIVE = [DL_ORDER[1], DL_ORDER[2], DL_ORDER[3]]   # DL8/DL16/DL32
UNINFORMATIVE_TAG = "UNINFORMATIVE-BY-S81-CAVEAT"
TRIALS_T18 = 20000
SEED_T18 = 2026102918
TRIALS_S78 = 20000
SEED_S78 = 2026102815
S78_ORDER = ["INNER (28,48)", "OUTER (9,67)"]
BATCH = 50                      # memory detail, NOT part of the frozen contract

# RNG stream determinism pins (see docstring: determinism, not correctness).
PIN_SHUFFLE_HEAD = (40, 67, 21, 3, 36, 27, 15, 28)
PIN_SHUFFLE_TAIL = (7, 11, 2, 35, 23, 60, 53, 32)
PIN_4SHUFFLE_SHA256 = "ced9969194148bc5743fbae64781050e37b50f41d996e54098d7da22dd5b53a7"

# frozen prior-window reference vectors (publication-s39.txt section 3
# for s36/s38/s39; publication-s51.txt section 3 for s51 -- the
# analysis-s78/s82 constants verbatim; s73's block-min vector is the
# one publication-s82.txt section 3 prints for W5 -- all five pairs
# are cross-checked against the committed publication bytes in
# --compat, section F)
REF_X = {"s39": [986, 991, 984, 985, 989, 989, 986, 990, 995, 986, 987, 981],
         "s36": [991, 989, 981, 998, 993, 985, 984, 997, 994, 994, 980, 982],
         "s38": [992, 988, 984, 1007, 985, 984, 986, 983, 992, 991, 982, 997],
         "s51": [988, 986, 1000, 986, 989, 983, 995, 983, 994, 991, 984, 985],
         "s73": [998, 978, 985, 983, 982, 980, 981, 982, 974, 988, 977, 988]}
REF_Y = {"s39": [988, 989, 987, 990, 990, 988, 991, 983, 985, 988, 983, 986],
         "s36": [988, 985, 994, 993, 994, 995, 992, 984, 987, 984, 993, 981],
         "s38": [988, 987, 980, 980, 991, 994, 991, 994, 988, 991, 1001, 992],
         "s51": [980, 975, 991, 979, 986, 986, 992, 991, 988, 993, 995, 996],
         "s73": [992, 984, 982, 985, 993, 972, 979, 990, 978, 982, 987, 987]}
REF_ANCHOR = {"s36": (1142, 991, 1438), "s38": (1132, 992, 1443),
              "s39": (1146, 986, 1432), "s51": (1137, 988, 1430)}
ANCHOR_WINS = ["s36", "s38", "s39", "s51"]   # the four prior anchor rows
                                             # (s84 section 6)

cell_re = re.compile(
    r"^CELL idx=(\d+) spv=(\S+) op=(\S+) wg=(\d+) forced=(\S+) probe_size=(-?\d+) "
    r"probe_nsub=(-?\d+) probe_wg=(-?\d+) pipeline=(\S+) void=(\d)")
verify_re = re.compile(r"^VERIFY idx=(\d+) checked=(\d+) mismatch=(\d+) ok=(\d)")
sample_re = re.compile(
    r"^SAMPLE round=(\d+) idx=(\d+) batch=(\d+) work_mul=(\d+) ndiv=(\d+) gpu_ticks=(\d+) "
    r"gpu_ns=([\d.]+) per_dispatch_ns=([\d.]+) host_ns=(\d+)")


def fmt_ht(x2):
    return "%.1f" % (x2 / 2)


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
                            int(m.group(9)), (int(m.group(3)), int(m.group(4)), int(m.group(5)))))
    return cells, verifies, samples


class Corpus(object):
    """The parsed run logs of one or more windows + the s78 integrity set."""

    def __init__(self, windows):
        self.data = {}
        self.win_info = {}
        self.ref_cellmap = None
        for win, dirname in windows:
            src = os.path.join(GPU, dirname)
            vmis = 0
            counts_ok = knob_ok = fail_ok = cmap_ok = True
            problems = []
            runs_parsed = 0
            for tag in ("c2", "hi", "tw", "c8"):
                b, wm, dd, runs = ARMS[tag]
                for r in runs:
                    fn = os.path.join(src, "run-%s-r%d.txt" % (tag, r))
                    cells, verifies, samples = load(fn)
                    self.data[(win, tag, r)] = (cells, verifies, samples)
                    runs_parsed += 1
                    for (_i, _c, mis) in verifies:
                        vmis += mis
                    s8 = [k for k, v in cells.items() if v["forced"] == "8"]
                    if len(s8) != 6 or any(cells[k]["pipeline"] != "FAIL"
                                           or cells[k]["void"] != "1" for k in s8):
                        fail_ok = False
                        problems.append("S=8 fail-closed violation in %s" % fn)
                    if len(samples) != 450 or len(verifies) != 24:
                        counts_ok = False
                        problems.append("SAMPLE/VERIFY count mismatch in %s" % fn)
                    for (_rnd, _idx, _gt, _hn, knobs) in samples:
                        if knobs != (b, wm, dd):
                            knob_ok = False
                            problems.append("knob mismatch in %s" % fn)
                    cmap = tuple(sorted((k, v["op"], v["wg"], v["forced"],
                                         v["pipeline"], v["void"])
                                        for k, v in cells.items()))
                    if self.ref_cellmap is None:
                        self.ref_cellmap = cmap
                    elif cmap != self.ref_cellmap:
                        cmap_ok = False
                        problems.append("cell map mismatch in %s" % fn)
            self.win_info[win] = dict(runs=runs_parsed, vmis=vmis,
                                      counts_ok=counts_ok, knob_ok=knob_ok,
                                      fail_ok=fail_ok, cmap_ok=cmap_ok,
                                      problems=problems)
        c0 = self.data[(windows[0][0], "c2", 1)][0]
        self.ok_cells = sorted(k for k, v in c0.items() if v["pipeline"] == "ok")
        self.cell_pos = {k: i for i, k in enumerate(self.ok_cells)}
        self.nc = [k for k in self.ok_cells if self.ckey(k) == NAMED_CKEY][0]
        self.nc_pos = self.cell_pos[self.nc]
        self.sum128 = [k for k in self.ok_cells
                       if self.ckey(k) == CELLKEY_SUM128][0]
        self.named_ok = (self.ckey_str(self.nc) == "(max,128,S=default)")

    def ckey(self, idx):
        c = self.data[(WIN5[0][0], "c2", 1)][0][idx]
        return (c["op"], c["wg"], c["forced"])

    def ckey_str(self, idx):
        op, wg, s = self.ckey(idx)
        return "(%s,%d,S=%s)" % (op, wg, s)

    def pooled(self, win, tag, idx, runs):
        xs = []
        for r in runs:
            xs += [s[2] for s in self.data[(win, tag, r)][2] if s[1] == idx]
        return float(np.median(np.asarray(xs, dtype=np.int64)))

    def block_vals(self, win, tag, runs):
        return [self.pooled(win, tag, k, runs) for k in self.ok_cells]

    def run_arr(self, win, tag):
        arr = np.zeros((36, len(self.ok_cells), 25), dtype=np.int64)
        for ri in range(36):
            tbl = {k: [] for k in self.ok_cells}
            for (_rnd, idx, gt, _hn, _kn) in self.data[(win, tag, ri + 1)][2]:
                tbl[idx].append(gt)
            for k in self.ok_cells:
                assert len(tbl[k]) == 25
                arr[ri, self.cell_pos[k], :] = tbl[k]
        return arr

    def named_flat(self, win_a, win_b):
        """(72, 25) named-cell tw samples: window A runs 1..36 then B."""
        return np.vstack([self.run_arr(win_a, "tw")[:, self.nc_pos, :],
                          self.run_arr(win_b, "tw")[:, self.nc_pos, :]])

    def named_blocks(self, win):
        """12 block pooled-75 arrays (12, 75) at the named cell, tw arm."""
        rows = []
        for i in range(12):
            xs = []
            for r in (3 * i + 1, 3 * i + 2, 3 * i + 3):
                xs += [s[2] for s in self.data[(win, "tw", r)][2]
                       if s[1] == self.nc]
            assert len(xs) == 75
            rows.append(xs)
        return rows

    def integrity_line(self, win):
        info = self.win_info[win]
        return ("   %s: runs parsed %d; VERIFY mismatch total %d; counts ok %s; "
                "knobs ok %s; S=8 fail-closed %s; cell map ok %s"
                % (win, info["runs"], info["vmis"], info["counts_ok"],
                   info["knob_ok"], info["fail_ok"], info["cmap_ok"]))

    def named_cell_line(self):
        return ("   named cell present as ok-map cell %d (raw idx %d == %s): %s"
                % (self.nc_pos, self.nc, self.ckey_str(self.nc), self.named_ok))


# ------------------------------------------------------------------
# the frozen estimator machinery (s84 section 1)
# ------------------------------------------------------------------
def d_pair(arr, i, j):
    """(...,75) int64 -> exact INTEGER pair spread x_(j+1) - x_(i+1)."""
    srt = np.sort(arr, axis=-1)
    return srt[..., j] - srt[..., i]


def l2_of(block_d):
    """12 block D values -> 2*L = 6th+7th order statistics (INTEGER)."""
    s = np.sort(np.asarray(block_d, dtype=np.int64))
    return int(s[5] + s[6])


def named_vectors(corpus, pairs, windows):
    """per pair: {win: 2*L} over the named cell's 12 tw blocks + block D."""
    out = {}
    for (label, i, j) in pairs:
        vec, blk = {}, {}
        for win, _d in windows:
            blocks = corpus.named_blocks(win)
            bd = [int(d_pair(np.asarray(b, dtype=np.int64).reshape(1, 75),
                             i, j)[0]) for b in blocks]
            vec[win] = l2_of(bd)
            blk[win] = bd
        out[label] = (vec, blk)
    return out


# ------------------------------------------------------------------
# the frozen null engine (s84 section 4 = the s78 machinery verbatim)
# ------------------------------------------------------------------
def run_null(flat72, pair_tbl, seed, trials, order):
    """Two-window run-exchangeability null.

    pair_tbl: {label: (i, j)}; ONE random.Random(seed) consumed in
    `order`; per trial ONE rng.shuffle of a fresh list(range(72)),
    split into pseudo-windows A then B of 36 in draw order, each
    into 12 blocks of 3 in draw order; 2*L* per pseudo-window =
    6th+7th order statistics of the 12 block D values; 2*C* =
    2*L*_A - 2*L*_B; p = (1 + count(C* >= C_obs)) / (1 + trials),
    ONE-SIDED in the pre-registered direction C_obs > 0.
    """
    rng = random.Random(seed)
    res = {}
    for label in order:
        i, j = pair_tbl[label]
        obs = np.arange(72, dtype=np.int64).reshape(1, 2, 12, 3)
        sub = flat72[obs].reshape(1, 2, 12, 75)
        d_obs = d_pair(sub, i, j)[0]                    # (2, 12)
        ds = np.sort(d_obs, axis=1)
        l2_obs = (ds[:, 5] + ds[:, 6]).astype(np.int64)  # (2,)
        c2_obs = int(l2_obs[0] - l2_obs[1])
        perms = np.empty((trials, 72), dtype=np.int64)
        for t in range(trials):
            perm = list(range(72))
            rng.shuffle(perm)
            perms[t] = perm
        cnt = 0
        for k in range(0, trials, BATCH):
            batch = perms[k:k + BATCH].reshape(-1, 2, 12, 3)
            sub = flat72[batch].reshape(-1, 2, 12, 75)
            d = d_pair(sub, i, j)                       # (b, 2, 12)
            ds = np.sort(d, axis=2)
            l2p = ds[:, :, 5] + ds[:, :, 6]             # (b, 2)
            c2 = l2p[:, 0] - l2p[:, 1]
            cnt += int((c2 >= c2_obs).sum())
        p = (1 + cnt) / (1 + trials)
        res[label] = dict(l2A=int(l2_obs[0]), l2B=int(l2_obs[1]),
                          c2_obs=c2_obs, count=cnt, p=p)
    return res


def py_null(flat_list, pair_tbl, seed, trials, order):
    """INDEPENDENT pure-Python twin of run_null (self-test cross-check).

    NO numpy: explicit sorted() order statistics, explicit loops; the
    ONLY shared contract is the frozen RNG call order (one
    rng.shuffle of a fresh list(range(72)) per trial).
    """
    rng = random.Random(seed)
    res = {}
    for label in order:
        i, j = pair_tbl[label]

        def blockd(perm):
            out = []
            for w in range(2):
                bd = []
                for b in range(12):
                    pooled = []
                    for k in range(3):
                        pooled.extend(flat_list[perm[w * 36 + b * 3 + k]])
                    pooled.sort()
                    bd.append(pooled[j] - pooled[i])
                out.append(bd)
            return out

        obs_a, obs_b = blockd(list(range(72)))
        l2a = sorted(obs_a)[5] + sorted(obs_a)[6]
        l2b = sorted(obs_b)[5] + sorted(obs_b)[6]
        c2_obs = l2a - l2b
        cnt = 0
        for _t in range(trials):
            perm = list(range(72))
            rng.shuffle(perm)
            ba, bb = blockd(perm)
            c2 = ((sorted(ba)[5] + sorted(ba)[6])
                  - (sorted(bb)[5] + sorted(bb)[6]))
            if c2 >= c2_obs:
                cnt += 1
        res[label] = dict(l2A=l2a, l2B=l2b, c2_obs=c2_obs, count=cnt,
                          p=(1 + cnt) / (1 + trials))
    return res


# ------------------------------------------------------------------
# the frozen letters / joint (s84 section 5)
# ------------------------------------------------------------------
def pair_letter(c2_obs, p, invalidated):
    if invalidated:
        return "(c) NOT EVALUABLE"
    if c2_obs > 0 and p <= 0.05:
        return "(a) LEVEL-NARROWING-REPLICATED-CONTINUED"
    if c2_obs <= 0:
        return "(b) NOT-REPLICATED [DIRECTION-REVERSED]"
    return "(b) NOT-REPLICATED [DIRECTION-CONSISTENT-NOT-SIGNIFICANT]"


def joint_letter(letters, invalidated):
    if invalidated:
        return "(c) NOT EVALUABLE"
    fails = [l for l in INFORMATIVE if not letters[l].startswith("(a)")]
    if not fails:
        return ("(a) DL-LADDER-CROSS-DAY-NARROWING-REPLICATED-ON-"
                "INFORMATIVE-STEPS")
    named = "|".join("%s %s" % (l, letters[l]) for l in fails)
    return "(b) NOT-REPLICATED (named failing: %s)" % named


# ==================================================================
# MODE: compat -- the section-6 parser validity pins + the s78 null
# reproduction, two-way against the committed publication bytes.
# ==================================================================
def mode_compat():
    pub78 = open(os.path.join(
        GPU, "anv-b3w5qpairevel-20261029", "publication-s78.txt")).read()
    pub82 = open(os.path.join(
        GPU, "anv-b3dlprofile-20261029", "publication-s82.txt")).read()

    rows = []   # (name, got, want) -- two-way; want PARSED, never transcribed
    corpus = Corpus(WIN5)

    # -- A. integrity rows (5) + named cell row, want = publication-s78
    #       section-1 lines
    want_int = {}
    for m in re.finditer(
            r"^   (s\d+): runs parsed \d+; VERIFY mismatch total \d+; "
            r"counts ok \S+; knobs ok \S+; S=8 fail-closed \S+; "
            r"cell map ok \S+$", pub78, re.M):
        want_int[m.group(1)] = m.group(0)
    for win, _d in WIN5:
        rows.append(("sec1 integrity %s" % win,
                     corpus.integrity_line(win), want_int[win]))
    m = re.search(
        r"^   named cell present as ok-map cell (\d+) \(raw idx (\d+) == "
        r"(\S+)\): (\S+)$", pub78, re.M)
    want_named = ("   named cell present as ok-map cell %s (raw idx %s == %s): %s"
                  % (m.group(1), m.group(2), m.group(3), m.group(4)))
    rows.append(("sec1 named cell", corpus.named_cell_line(), want_named))

    # -- B. C1 rows (3), computed at the W5 window (the s78 rows'
    #       environment pin), want = publication-s78 section-2 lines
    c2_vals = corpus.block_vals("s73", "c2", ARMS["c2"][3])
    c2_cls = "FLOOR" if all(v <= 100 for v in c2_vals) else (
        "CAPTURED" if all(v >= 1000 for v in c2_vals) else "INTERMEDIATE/MIXED")
    c2_line = "   c2 class: %s (FLOOR required; committed floor band 31..32)" % c2_cls
    c8_m = corpus.pooled("s73", "c8", corpus.sum128, ARMS["c8"][3])
    c8_line = ("   c8 (sum,128,S=16) pooled median %.0f vs committed %d "
               "(%.2f%% delta; +/-5%% required)"
               % (c8_m, COMMITTED_C8,
                  abs(c8_m - COMMITTED_C8) / COMMITTED_C8 * 100))
    c1_ok = (c2_cls == "FLOOR") and abs(c8_m - COMMITTED_C8) <= 0.05 * COMMITTED_C8
    c1_line = "   C1 branch: %s" % ("(a) both controls replicate" if c1_ok
                                    else "(b) discrepancy")
    for nm, got in (("sec2 c2 class", c2_line), ("sec2 c8 pooled median", c8_line),
                    ("sec2 C1 branch", c1_line)):
        w = [ln for ln in pub78.splitlines() if ln == got] or [
            ln for ln in pub78.splitlines()
            if ln.split(" (")[0] == got.split(" (")[0]] or ["<no published line>"]
        rows.append((nm, got, w[0]))

    # -- C. s78 NULL REPRODUCTION (the frozen engine, externally
    #       validated against publication-s78.txt's PUBLISHED T15
    #       counts/p -- NOT a T18 statistic)
    flat = corpus.named_flat("s36", "s73")
    s78 = run_null(flat, QP_TBL, SEED_S78, TRIALS_S78, S78_ORDER)
    want_null = {}
    for m in re.finditer(
            r"^   (INNER \(28,48\)|OUTER \(9,67\)): 2\*L_s36 = (\d+) "
            r"\([\d.]+\); 2\*L_s73 = (\d+) \([\d.]+\); 2\*C_obs = (-?\d+) "
            r"\(C_obs = -?[\d.]+\); count (\d+) / (\d+); p = ([\d.]+); "
            r"axis letter .+$", pub78, re.M):
        want_null[m.group(1)] = (int(m.group(2)), int(m.group(3)),
                                 int(m.group(4)), int(m.group(5)),
                                 m.group(7))
    for label in S78_ORDER:
        r = s78[label]
        got = (r["l2A"], r["l2B"], r["c2_obs"], r["count"], "%.6f" % r["p"])
        rows.append(("s78 null reproduction %s (2L_A/2L_B/2C/count/p)"
                     % label, got, want_null[label]))

    # -- D. QP validity vectors (five-window 2*L + W5 block D),
    #       want = publication-s78 section-5 D1 lines
    qp_vecs = named_vectors(corpus, QP_PAIRS, WIN5)
    for label in [p[0] for p in QP_PAIRS]:
        vec, blk = qp_vecs[label]
        got_v = tuple(vec[w] for w, _d in WIN5)
        m = re.search(r"^      %s: 2\*L s36/s38/s39/s51/s73 = ([\d/]+) \("
                      % re.escape(label), pub78, re.M)
        want_v = tuple(int(x) for x in m.group(1).split("/"))
        rows.append(("%s five-window 2*L" % label, got_v, want_v))
        got_b = tuple(blk["s73"])
        m = re.search(r"^      %s W5 block D values: ([\d ]+)$"
                      % re.escape(label), pub78, re.M)
        want_b = tuple(int(x) for x in m.group(1).split())
        rows.append(("%s W5 block D" % label, got_b, want_b))

    # -- E. DL validity vectors (five-window 2*L + W5 block D),
    #       want = publication-s82 section D1/D2 lines
    dl_vecs = named_vectors(corpus, DL_PAIRS, WIN5)
    for label in DL_ORDER:
        vec, blk = dl_vecs[label]
        got_v = tuple(vec[w] for w, _d in WIN5)
        m = re.search(r"^   %s: 2\*L s36/s38/s39/s51/s73 = ([\d/]+) \("
                      % re.escape(label), pub82, re.M)
        want_v = tuple(int(x) for x in m.group(1).split("/"))
        rows.append(("%s five-window 2*L" % label, got_v, want_v))
        got_b = tuple(blk["s73"])
        m = re.search(r"^   %s W5 block D values: ([\d ]+)$"
                      % re.escape(label), pub82, re.M)
        want_b = tuple(int(x) for x in m.group(1).split())
        rows.append(("%s W5 block D" % label, got_b, want_b))

    # -- F. reference-constant cross-check (the REF_X/REF_Y block-min
    #       constants vs publication-s82.txt section 3 bytes and the
    #       REF_ANCHOR constants vs its section-3b bytes -- want
    #       PARSED from the committed publication, never transcribed)
    for win, _d in WIN5:
        m = re.search(r"^   %s X \(hi\): ([\d ]+)$" % win, pub82, re.M)
        rows.append(("ref X constant %s" % win,
                     tuple(REF_X[win]),
                     tuple(int(x) for x in m.group(1).split())))
        m = re.search(r"^   %s Y \(tw\): ([\d ]+)$" % win, pub82, re.M)
        rows.append(("ref Y constant %s" % win,
                     tuple(REF_Y[win]),
                     tuple(int(x) for x in m.group(1).split())))
    for win in ANCHOR_WINS:
        m = re.search(r"^    %s: median (\d+) min\.\.max (\d+)\.\.(\d+) \("
                      % win, pub82, re.M)
        rows.append(("ref anchor constant %s" % win, REF_ANCHOR[win],
                     (int(m.group(1)), int(m.group(2)), int(m.group(3)))))

    # ------------------------------------------------------------------
    out = []
    P = out.append
    P("JUN-59 session 92 -- T18 ANALYSIS PRE-BUILD, --compat VALIDATION")
    P("(the s84-frozen T18 analysis machinery recomputed over the FIVE")
    P("committed windows and two-way-checked against the committed")
    P("publication bytes; want values PARSED from publication-s78.txt /")
    P("publication-s82.txt, never transcribed). NO W6 quantity exists or")
    P("is computed (the W6 run logs do not exist); NO T18 quantity")
    P("exists (T18 is frozen ONLY at the (s36, W6) pair and its null")
    P("runs only after the W6 measurement half commits the logs). What")
    P("runs here: the s84 section-6 PARSER VALIDITY PINS, the")
    P("integrity/C1 parser rows, and the s78 NULL REPRODUCTION (the")
    P("same frozen engine at the T15 row's seed 2026102815, probe order")
    P("INNER then OUTER, pair (s36, W5) -- reproducing publication-")
    P("s78.txt's PUBLISHED T15 counts/p exactly; a validity")
    P("recomputation of published frozen content, not a T18 statistic).")
    P("")
    for (nm, got, want) in rows:
        P("row %s: got %s | want %s | EXACT: %s" % (nm, got, want, got == want))
    bad = [nm for (nm, got, want) in rows if got != want]
    P("")
    P("c2 pooled-medians min..max at W5: %d..%d (floor band %d..%d; "
      "within: %s)" % (int(min(c2_vals)), int(max(c2_vals)),
                       FLOOR_BAND[0], FLOOR_BAND[1],
                       min(c2_vals) >= FLOOR_BAND[0]
                       and max(c2_vals) <= FLOOR_BAND[1]))
    P("")
    P("TOTAL: %d rows, %d mismatched" % (len(rows), len(bad)))
    if bad:
        P("FAILED rows: %s" % ", ".join(bad))
    print("\n".join(out))
    return 0 if not bad else 1


# ==================================================================
# MODE: full -- the real T18 row (adopted name analysis-s<NN>.py).
# Also driven by the self-test's MOCK end-to-end fixture run.
# ==================================================================
def t18_row(session, w6_dirname, out_path, w6_tag=None):
    w6_runwin = os.path.join(GPU, w6_dirname, "run-window.txt")
    if w6_tag is None:
        if not os.path.isdir(os.path.join(GPU, w6_dirname)):
            print("FAIL-CLOSED: the W6 run logs are absent (%s): the T18 "
                  "analysis half runs only after the W6 measurement half "
                  "commits them (s84 section 8)." % w6_dirname)
            return None
        first = open(w6_runwin).readline()
        m = re.search(r"session (\d+)", first)
        assert m, first
        w6_tag = "s%s" % m.group(1)
    windows = WIN5 + [(w6_tag, w6_dirname)]
    corpus = Corpus(windows)

    # -- section 6: the invalidation machinery
    inv_notes = []
    integrity_ok = True
    for win, _d in windows:
        info = corpus.win_info[win]
        if (info["runs"] != 78 or info["vmis"] != 0 or not info["counts_ok"]
                or not info["knob_ok"] or not info["fail_ok"]
                or not info["cmap_ok"]):
            integrity_ok = False
            inv_notes.append("integrity violation at %s" % win)
    named_ok = corpus.named_ok
    if not named_ok:
        inv_notes.append("named cell identity violation")

    c2_vals = corpus.block_vals(w6_tag, "c2", ARMS["c2"][3])
    c2_cls = "FLOOR" if all(v <= 100 for v in c2_vals) else (
        "CAPTURED" if all(v >= 1000 for v in c2_vals) else "INTERMEDIATE/MIXED")
    c8_m = corpus.pooled(w6_tag, "c8", corpus.sum128, ARMS["c8"][3])
    c2_band_ok = (min(c2_vals) >= FLOOR_BAND[0]
                  and max(c2_vals) <= FLOOR_BAND[1])
    c1_ok = (c2_cls == "FLOOR" and c2_band_ok
             and abs(c8_m - COMMITTED_C8) <= 0.05 * COMMITTED_C8)
    if not c1_ok:
        inv_notes.append("C1 at W6 not branch (a)")

    # five prior windows' block-min vectors EXACT + four anchors EXACT
    vec_ok = True
    vec = {}
    for win, _d in WIN5:
        X = [int(min(corpus.block_vals(win, "hi", [3 * i + 1, 3 * i + 2, 3 * i + 3])))
             for i in range(12)]
        Y = [int(min(corpus.block_vals(win, "tw", [3 * i + 1, 3 * i + 2, 3 * i + 3])))
             for i in range(12)]
        vec[win] = (X, Y)
        if X != REF_X[win] or Y != REF_Y[win]:
            vec_ok = False
            inv_notes.append("block-min vector mismatch at %s" % win)
    anchor_ok = True
    anchor_rows = {}
    for win in ANCHOR_WINS:
        a_med = int(corpus.pooled(win, "hi", corpus.sum128, [1, 2, 3]))
        bvals = [int(v) for v in corpus.block_vals(win, "hi", [1, 2, 3])]
        anchor_rows[win] = (a_med, min(bvals), max(bvals))
        if anchor_rows[win] != REF_ANCHOR[win]:
            anchor_ok = False
            inv_notes.append("anchor row mismatch at %s" % win)

    # parser validity pins (the s84 section-6 honesty anchor)
    qp_vecs = named_vectors(corpus, QP_PAIRS, WIN5)
    dl_vecs = named_vectors(corpus, DL_PAIRS, WIN5)
    pins_ok = True
    pin_rows = []
    want_qp = {"INNER (28,48)": ([118, 102, 128, 113, 100],
                                [42, 34, 40, 48, 74, 48, 60, 39, 74, 56, 52, 57]),
               "OUTER (9,67)": ([496, 429, 437, 446, 502],
                                [267, 189, 242, 377, 340, 278, 214, 181, 255, 247, 268, 194])}
    want_dl = {"DL4 (x_(34),x_(42))": ([46, 47, 48, 38, 40],
                                       [20, 17, 18, 21, 33, 17, 20, 15, 36, 20, 16, 23]),
               "DL8 (x_(30),x_(46))": ([97, 84, 99, 79, 83],
                                       [35, 27, 34, 44, 61, 38, 48, 25, 57, 42, 41, 45]),
               "DL16 (x_(22),x_(54))": ([238, 187, 201, 188, 178],
                                        [74, 63, 70, 87, 116, 91, 96, 70, 113, 103, 92, 81]),
               "DL32 (x_(6),x_(70))": ([655, 537, 572, 564, 658],
                                       [360, 261, 287, 429, 430, 399, 277, 279, 323, 335, 368, 297])}
    for tbl, label in [(qp_vecs, l) for l in want_qp] + [(dl_vecs, l) for l in want_dl]:
        vec_w, blk_w = tbl[label]
        if label in want_qp:
            want_v, want_b = want_qp[label]
        else:
            want_v, want_b = want_dl[label]
        got_v = [vec_w[w] for w, _d in WIN5]
        got_b = blk_w["s73"]
        ok = (got_v == want_v and got_b == want_b)
        if not ok:
            pins_ok = False
            inv_notes.append("parser validity pin mismatch at %s" % label)
        pin_rows.append((label, got_v, got_b, ok))

    invalidated = (not integrity_ok) or (not named_ok) or (not c1_ok) \
        or (not vec_ok) or (not anchor_ok) or (not pins_ok)

    # -- sections 1/7: the T18 construction + the frozen null
    dl_vecs6 = named_vectors(corpus, DL_PAIRS,
                             WIN5 + [(w6_tag, w6_dirname)])
    flat = corpus.named_flat("s36", w6_tag)
    prim = run_null(flat, DL_TBL, SEED_T18, TRIALS_T18, DL_ORDER)
    letters = {label: pair_letter(prim[label]["c2_obs"], prim[label]["p"],
                                  invalidated)
               for label in DL_ORDER}
    joint = joint_letter(letters, invalidated)

    # -- D-family (section 7; descriptive only)
    d3 = {}
    for label in DL_ORDER:
        vec6, _blk = dl_vecs6[label]
        band = sorted(vec6[w] for w in ("s38", "s39", "s51"))
        lo, hi = band[0], band[2]      # [MIN, MAX] -- the s83/s89 convention
        v6 = vec6[w6_tag]
        d3[label] = (lo, hi,
                     "INSIDE" if lo <= v6 <= hi else
                     ("OUTSIDE-BELOW" if v6 < lo else "OUTSIDE-ABOVE"))

    # -- the publication
    out = []
    P = out.append
    P("JUN-59 session %d -- THE DL LADDER CROSS-DAY LEVEL REPLICATION AT"
      % session)
    P("W6 (T18, the s84-frozen inferential row; publication-s%d.txt,"
      % session)
    P("produced ONLY by analysis-s%d.py over the COMMITTED run logs of" % session)
    P("the six evidence directories: the five prior windows of")
    P("publication-s82.txt section 0 plus %s = the W6 window (window" % w6_dirname)
    P("tag %s), measured by the W6 measurement half under the s80" % w6_tag)
    P("freeze. protocol.txt freeze stamp 2026-10-29T06:14:31Z preceded")
    P("any W6 quantity. ANALYSIS session -- NO hardware runs this")
    P("session.")
    P("")
    P("1. INTEGRITY (protocol section 6):")
    for win, _d in windows:
        P(corpus.integrity_line(win))
    P(corpus.named_cell_line())
    P("   invalidation: %s" % ("CLEAN" if not invalidated
                               else "; ".join(inv_notes)))
    P("")
    P("2. C1 RE-DERIVATION at %s:" % w6_tag)
    P("   c2 class: %s (FLOOR required; committed floor band 31..32)"
      % c2_cls)
    P("   c2 pooled medians min..max %d..%d (within band %d..%d: %s)"
      % (int(min(c2_vals)), int(max(c2_vals)), FLOOR_BAND[0], FLOOR_BAND[1],
         c2_band_ok))
    P("   c8 (sum,128,S=16) pooled median %.0f vs committed %d "
      "(%.2f%% delta; +/-5%% required)"
      % (c8_m, COMMITTED_C8, abs(c8_m - COMMITTED_C8) / COMMITTED_C8 * 100))
    P("   C1 branch: %s" % ("(a) both controls replicate" if c1_ok
                            else "(b) discrepancy"))
    P("")
    P("3. PRIOR-WINDOW REPRODUCTION + PARSER VALIDITY PINS (section 6):")
    for win, _d in WIN5:
        X, Y = vec[win]
        P("   %s block-min X (hi): %s EXACT: %s" % (win, " ".join(map(str, X)),
                                                    X == REF_X[win]))
        P("   %s block-min Y (tw): %s EXACT: %s" % (win, " ".join(map(str, Y)),
                                                    Y == REF_Y[win]))
    for win in ANCHOR_WINS:
        a_med, a_min, a_max = anchor_rows[win]
        P("   %s anchor: median %d min..max %d..%d EXACT: %s"
          % (win, a_med, a_min, a_max,
             anchor_rows[win] == REF_ANCHOR[win]))
    P("   block-min vectors EXACT (10/10 over five windows): %s; "
      "anchors EXACT (4/4): %s" % (vec_ok, anchor_ok))
    for (label, got_v, got_b, ok) in pin_rows:
        P("   PIN %s: five-window 2*L %s; %s W5 block D %s; EXACT: %s"
          % (label, "/".join(map(str, got_v)), w6_tag and "W5",
             " ".join(map(str, got_b)), ok))
    P("   pins EXACT (6/6 vectors + 4/4 block D): %s" % pins_ok)
    P("")
    P("4. T18 THE ROW QUESTION (frozen letters, protocol sections 3/4/5):")
    P("   the NAMED cell %s of the tw arm; per-block D over the block's"
      % corpus.ckey_str(corpus.nc))
    P("   pooled 75 gpu_ticks (EXACT INTEGER) at the closed DL")
    P("   vocabulary; 2*L = 6th+7th order statistics of the 12 block D")
    P("   values; 2*C_obs = 2*L_s36 - 2*L_%s at the named pair (s36, %s);"
      % (w6_tag, w6_tag))
    P("   the null: 72 tw runs exchangeable, %d trials per probe, ONE" % TRIALS_T18)
    P("   random.Random(%d), probe order %s; p = (1 + count(C* >=" % (SEED_T18, "/".join(DL_ORDER)))
    P("   C_obs)) / (1 + 20,000), ONE-SIDED:")
    for label in DL_ORDER:
        r = prim[label]
        P("   %s: 2*L_s36 = %d (%s); 2*L_%s = %d (%s); 2*C_obs = %d "
          "(C_obs = %s); count %d / %d; p = %.6f; pair letter %s%s"
          % (label, r["l2A"], fmt_ht(r["l2A"]), w6_tag, r["l2B"],
             fmt_ht(r["l2B"]), r["c2_obs"], fmt_ht(r["c2_obs"]),
             r["count"], TRIALS_T18 + 1, r["p"], letters[label],
             ("" if label in INFORMATIVE else " [" + UNINFORMATIVE_TAG + "]")))
    P("   JOINT T18 = %s" % joint)
    P("   (DL4's letter carries the standing %s tag and never enters" % UNINFORMATIVE_TAG)
    P("   the joint; IUT convention, NO multiplicity correction.)")
    P("")
    P("5. D-FAMILY (descriptive only, NO letter):")
    P("   D1 six-window 2*L vectors (s36/s38/s39/s51/W5/%s):" % w6_tag)
    for label in DL_ORDER:
        vec6, _b = dl_vecs6[label]
        P("   %s: 2*L %s (L %s)"
          % (label, "/".join(str(vec6[w]) for w, _d in WIN5 + [(w6_tag, w6_dirname)]),
             "/".join(fmt_ht(vec6[w]) for w, _d in WIN5 + [(w6_tag, w6_dirname)])))
    P("   D2 the 12 %s block D values per pair (for a future census):" % w6_tag)
    _vec6, blk6 = None, None
    for label in DL_ORDER:
        _v, b = named_vectors(corpus, [x for x in DL_PAIRS if x[0] == label],
                              [(w6_tag, w6_dirname)])[label]
        P("   %s %s block D values: %s"
          % (label, w6_tag, " ".join(str(x) for x in b[w6_tag])))
    P("   D3 %s-vs-post-shift-band (the CLOSED INTERVAL [MIN, MAX] of" % w6_tag)
    P("   {2*L_s38, 2*L_s39, 2*L_s51} -- the s83/s89 convention, NOT")
    P("   min..median; descriptive, never a test):")
    for label in DL_ORDER:
        lo, hi, verdict = d3[label]
        P("   %s: 2*L_%s = %d vs band 2*L %d..%d: %s"
          % (label, w6_tag, dl_vecs6[label][0][w6_tag], lo, hi, verdict))
    P("")
    P("6. VERDICT SUMMARY:")
    P("   T18 = %s" % joint)
    for label in DL_ORDER:
        r = prim[label]
        P("   %s: 2*L_s36 %d -> 2*L_%s %d (2*C_obs %d); count %d/%d; "
          "p %.6f; letter %s"
          % (label, r["l2A"], w6_tag, r["l2B"], r["c2_obs"], r["count"],
             TRIALS_T18 + 1, r["p"], letters[label]))
    P("   ANALYSIS session: NO hardware runs -> NO reading -> NO")
    P("   settle-bar-ledger line, NO day-slot consumption.")
    P("   Rule 4 binds: NOTHING MOVES; accelerator-targets defaults")
    P("   remain provisional (:measured? false); NO vendor optimization")
    P("   exists for Intel (or for any vendor).")
    text = "\n".join(out) + "\n"
    open(out_path, "w").write(text)
    return dict(text=text, letters=letters, joint=joint, prim=prim,
                d3=d3, invalidated=invalidated, w6_tag=w6_tag,
                pin_rows=pin_rows, c1_ok=c1_ok)


# ==================================================================
# MODE: self-test -- the fixture suite
# ==================================================================
class Tally(object):
    def __init__(self):
        self.n = 0
        self.failed = 0

    def check(self, name, got, want):
        self.n += 1
        ok = got == want
        if not ok:
            self.failed += 1
        print("  check %s: got %s want %s -> %s"
              % (name, got, want, "ok" if ok else "FAILED"))


def make_mock_window(dstdir):
    """Deterministic synthetic W6 logs -- MOCK FIXTURE, NOT A MEASUREMENT.

    CELL lines are copied verbatim from a committed s36 log (the cell
    map is byte-identical across every committed log; copying it keeps
    the mock's map equal to the reference map); SAMPLE/VERIFY lines are
    synthetic deterministic formulas (NO RNG, no clock).
    """
    src = os.path.join(GPU, WIN5[0][1], "run-c2-r1.txt")
    cell_lines = [ln.rstrip("\n") for ln in open(src)
                  if ln.startswith("CELL ")]
    assert len(cell_lines) == 24
    if not os.path.isdir(dstdir):
        os.makedirs(dstdir)
    with open(os.path.join(dstdir, "run-window.txt"), "w") as f:
        f.write("JUN-59 session 999 run window (MOCK FIXTURE -- NOT A "
                "MEASUREMENT; synthetic logs for the s92 pre-build "
                "self-test).\n")
    for tag in ("c2", "hi", "tw", "c8"):
        b, wm, dd, runs = ARMS[tag]
        for r in runs:
            lines = ["# mock fixture (s92 self-test) arm=%s run=%d" % (tag, r)]
            lines += cell_lines
            for idx in range(24):
                if idx % 4 == 0:
                    lines.append("VERIFY idx=%d checked=0 mismatch=0 ok=0 "
                                 "note=pipeline-failed" % idx)
                else:
                    lines.append("VERIFY idx=%d checked=7813 mismatch=0 ok=1"
                                 % idx)
            for k in range(25):
                for idx in range(24):
                    if idx % 4 == 0:
                        continue
                    if tag == "c2":
                        gt = 31 + ((r + idx + k) % 2)
                    elif tag == "c8":
                        gt = 32915 if idx == 1 else 32000 + ((r * 7 + idx * 13 + k) % 900)
                    else:
                        gt = 1000 + ((r * 131 + idx * 17 + k * 7
                                      + (r * k) % 23) % 400)
                    lines.append("SAMPLE round=%d idx=%d batch=%d work_mul=%d "
                                 "ndiv=%d gpu_ticks=%d gpu_ns=%d.0 "
                                 "per_dispatch_ns=%d.0 host_ns=%d"
                                 % (k, idx, b, wm, dd, gt, gt * 51,
                                    gt * 51 // max(b, 1), gt * 1000))
            lines.append("# done cells=24")
            with open(os.path.join(dstdir, "run-%s-r%d.txt" % (tag, r)),
                      "w") as f:
                f.write("\n".join(lines) + "\n")


def mode_selftest():
    t = Tally()
    print("JUN-59 session 92 -- T18 ANALYSIS PRE-BUILD --self-test "
          "(fixture suite; every quantity here is a FIXTURE, never a "
          "measurement; no real window pair is tested inferentially).")
    print("")

    # ST1: pair-D identity on deterministic pooled-75 permutations of 0..74
    for (label, i, j) in QP_PAIRS + DL_PAIRS:
        for name, arr in (("asc", np.arange(75, dtype=np.int64)),
                          ("desc", np.arange(74, -1, -1, dtype=np.int64)),
                          ("perm", (np.arange(75, dtype=np.int64) * 7) % 75)):
            got = int(d_pair(arr.reshape(1, 75), i, j)[0])
            srt = sorted(int(x) for x in arr)
            t.check("D %s %s" % (label, name), got, srt[j] - srt[i])

    # ST2: 2*L identity (hand-computable)
    t.check("2*L [1..12]", l2_of(list(range(1, 13))), 13)
    t.check("2*L [12..1]", l2_of(list(range(12, 0, -1))), 13)
    t.check("2*L all-5", l2_of([5] * 12), 10)
    t.check("2*L hand", l2_of([3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8]), 9)

    # ST3: degenerate null at the FULL frozen trial count (hand-computable:
    # every block D = 0 -> every 2*L* = 0 -> every C* = 0 -> count = all)
    flat_deg = [(777,) * 25 for _ in range(72)]
    res = py_null(flat_deg, DL_TBL, SEED_T18, 200,
                  DL_ORDER)  # quick twin sanity first (see ST4)
    for label in DL_ORDER:
        t.check("degenerate-twin %s count" % label, res[label]["count"], 200)
    res = run_null(np.asarray(flat_deg, dtype=np.int64).reshape(72, 25),
                   DL_TBL, SEED_T18, TRIALS_T18, DL_ORDER)
    for label in DL_ORDER:
        t.check("degenerate %s 2*C_obs" % label, res[label]["c2_obs"], 0)
        t.check("degenerate %s count" % label, res[label]["count"], TRIALS_T18)
        t.check("degenerate %s p" % label, res[label]["p"], 1.0)
        t.check("degenerate %s letter" % label,
                pair_letter(res[label]["c2_obs"], res[label]["p"], False),
                "(b) NOT-REPLICATED [DIRECTION-REVERSED]")

    # ST4: INDEPENDENT twin cross-check on deterministic synthetic data
    flat_syn = [(1000 + ((r * 131 + s * 17 + (r * s) % 23) % 400)
                 for s in range(25)) for r in range(72)]
    flat_syn = [tuple(v) for v in flat_syn]
    trials = 2000
    res_np = run_null(np.asarray(flat_syn, dtype=np.int64).reshape(72, 25),
                      DL_TBL, SEED_T18, trials, DL_ORDER)
    res_py = py_null(flat_syn, DL_TBL, SEED_T18, trials, DL_ORDER)
    for label in DL_ORDER:
        for field in ("l2A", "l2B", "c2_obs", "count", "p"):
            t.check("twin %s %s" % (label, field),
                    res_np[label][field], res_py[label][field])

    # ST5: RNG stream determinism pins (determinism, NOT correctness)
    rng = random.Random(SEED_T18)
    perm = list(range(72))
    rng.shuffle(perm)
    t.check("stream head", tuple(perm[:8]), PIN_SHUFFLE_HEAD)
    t.check("stream tail", tuple(perm[64:]), PIN_SHUFFLE_TAIL)
    rng2 = random.Random(SEED_T18)
    acc = hashlib.sha256()
    for _t in range(4):
        p2 = list(range(72))
        rng2.shuffle(p2)
        acc.update(bytes(p2))
    t.check("stream 4-shuffle sha256", acc.hexdigest(), PIN_4SHUFFLE_SHA256)

    # ST6: letter table (hand cases, s84 section 5)
    t.check("letter a", pair_letter(18, 0.04, False),
            "(a) LEVEL-NARROWING-REPLICATED-CONTINUED")
    t.check("letter b ns", pair_letter(18, 0.073896, False),
            "(b) NOT-REPLICATED [DIRECTION-CONSISTENT-NOT-SIGNIFICANT]")
    t.check("letter b zero", pair_letter(0, 0.5, False),
            "(b) NOT-REPLICATED [DIRECTION-REVERSED]")
    t.check("letter b rev", pair_letter(-6, 0.577921, False),
            "(b) NOT-REPLICATED [DIRECTION-REVERSED]")
    t.check("letter c", pair_letter(18, 0.04, True), "(c) NOT EVALUABLE")
    t.check("letter boundary p", pair_letter(1, 0.05, False),
            "(a) LEVEL-NARROWING-REPLICATED-CONTINUED")

    # ST7: joint table (hand cases)
    la = "(a) LEVEL-NARROWING-REPLICATED-CONTINUED"
    lb = "(b) NOT-REPLICATED [DIRECTION-REVERSED]"
    t.check("joint DL4-(b)-excluded-from-joint",
            joint_letter({DL_ORDER[0]: lb, DL_ORDER[1]: la,
                          DL_ORDER[2]: la, DL_ORDER[3]: la}, False),
            "(a) DL-LADDER-CROSS-DAY-NARROWING-REPLICATED-ON-INFORMATIVE-STEPS")
    j = joint_letter({DL_ORDER[0]: la, DL_ORDER[1]: la,
                      DL_ORDER[2]: la, DL_ORDER[3]: lb}, False)
    t.check("joint DL32-failing-named", j,
            "(b) NOT-REPLICATED (named failing: %s %s)" % (DL_ORDER[3], lb))
    j = joint_letter({DL_ORDER[0]: la, DL_ORDER[1]: la,
                      DL_ORDER[2]: lb, DL_ORDER[3]: la}, False)
    t.check("joint one-failing",
            j,
            "(b) NOT-REPLICATED (named failing: %s %s)"
            % (DL_ORDER[2], lb))
    t.check("joint invalidated",
            joint_letter({l: la for l in DL_ORDER}, True),
            "(c) NOT EVALUABLE")

    # ST8: p-formula identity
    for cnt, trials in ((0, 20000), (20000, 20000), (1477, 20000)):
        t.check("p-formula %d/%d" % (cnt, trials),
                (1 + cnt) / (1 + trials), (1 + cnt) / (1 + trials + 0))
    t.check("p-min resolution", 1 / (1 + 20000), 1 / 20001)

    # ST9: MOCK end-to-end run of the full-row glue (fixtures only)
    mock_dir = os.path.join(SCRATCH, "mck-w6-s92")
    make_mock_window(mock_dir)
    mock_rel = os.path.relpath(mock_dir, GPU)
    out_path = os.path.join(SCRATCH, "mck-t18-publication.txt")
    row = t18_row(998, mock_rel, out_path, w6_tag="s999")
    t.check("mock row computed", row is not None, True)
    t.check("mock not invalidated", row["invalidated"], False)
    t.check("mock w6 tag", row["w6_tag"], "s999")
    t.check("mock joint is a/b token",
            row["joint"].startswith("(a)") or row["joint"].startswith("(b)"),
            True)
    for label in DL_ORDER:
        t.check("mock letter token %s" % label,
                row["letters"][label].startswith("(a)")
                or row["letters"][label].startswith("(b)"), True)
        lo, hi, verdict = row["d3"][label]
        v6 = row["prim"][label]["l2B"]
        t.check("mock D3 band %s ordered" % label, lo <= hi, True)
        t.check("mock D3 verdict %s" % label, verdict,
                "INSIDE" if lo <= v6 <= hi else
                ("OUTSIDE-BELOW" if v6 < lo else "OUTSIDE-ABOVE"))
    text = row["text"]
    t.check("mock publication has s999", "s999" in text, True)
    t.check("mock publication has joint line",
            "JOINT T18 = " in text, True)
    m = re.search(r"PIN DL32 \(x_\(6\),x_\(70\)\): five-window 2\*L "
                  r"655/537/572/564/658", text)
    t.check("mock publication pin DL32 exact", m is not None, True)
    t.check("mock C1 branch (a)", row["c1_ok"], True)

    print("")
    print("TOTAL: %d assertions passed, %d failed" % (t.n, t.failed))
    return 0 if t.failed == 0 else 1


if MODE == "compat":
    sys.exit(mode_compat())
elif MODE == "selftest":
    sys.exit(mode_selftest())
else:
    out_path = os.path.join(HERE, "publication-s%d.txt" % SESSION)
    row = t18_row(SESSION, W6_DIR, out_path)
    sys.exit(0 if row is not None else 1)
