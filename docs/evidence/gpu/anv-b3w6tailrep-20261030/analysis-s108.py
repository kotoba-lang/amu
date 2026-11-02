#!/usr/bin/env python3
"""JUN-59 session 93 -- THE T20 ANALYSIS PRE-BUILD (analysis-t20-prego.py)

(the T20 row's ANALYSIS machinery pre-build -- NO hardware runs, NO
builds, NO compiles, NO GO stamp, NO host writes, NO day-slot
consumption, NO ledger line. Row: the s92 carry-forward's item (c)
(the T20 ANALYSIS half, the s88 freeze), taken to its PREPARATION
half -- the s69/s90/s92 pre-build precedent applied to the s88-frozen
analysis path (docs/evidence/gpu/anv-b3w6tailrep-20261030/protocol.txt
sections 1/3/4/5/6/7). The analysis half itself REMAINS day-slot-
gated behind the W6 measurement half (STARTED, NOT FINISHED): it runs
only after the W6 measurement half (the first measurement session
at/after 2026-10-30T00:00:00Z) commits the W6 run logs.)

WHAT THIS IS (honest states): an IMPLEMENTATION pre-build of the
complete frozen T20 row -- the construction (section 1: named cell
(max,128,S=default), tw arm, 12 blocks of 3, per-block pooled-75
EXACT-INTEGER HL_k/HR_k at the closed s86 vocabulary k in
{4,8,16,32}), the pre-registered direction (section 3: C_obs > 0 per
family), the frozen null (section 4: WITHIN-BLOCK SIDE-
EXCHANGEABILITY -- all 2^12 = 4,096 whole-block side-swap
assignments enumerated EXACTLY, one bit per block swapping that
block's HL/HR for ALL FOUR families together, NO RNG ANYWHERE, p =
count(C* >= C_obs) / 4,096 ONE-SIDED, identity assignment included),
the letters and the IUT joint (section 5; k=4/8 excluded from the
joint per the s86 section-4(c) caveat, their letters published under
the standing UNINFORMATIVE-BY-S86-CAVEAT tag), the invalidation
machinery (section 6: integrity/C1/block-min/anchors/parser validity
pins + the s86 decomposition identity HL_k + HR_k = D_DLk) and the
D-family (section 7 -- D1/D2/D3, the D3 band under the s83/s89
CORRECTED [MIN,MAX] convention, NAMED; D4 non-additivity print). It
is NOT the T20 session's script yet: the analysis session adopts this
file as analysis-s<NN>.py (the filename IS the mode switch -- full
mode is UNREACHABLE under this pre-build name) and owns its record.

MODES:
  (default under this pre-build name) --compat: the s88 section-6
    PARSER VALIDITY PINS recomputed over the five committed windows
    and two-way-checked against the COMMITTED publication bytes
    (want values PARSED from publication-s78.txt /
    publication-s82.txt / publication-s87.txt, never transcribed):
    the publication-s78 INNER (28,48) / OUTER (9,67) five-window 2*L
    vectors and W5 block D vectors, the publication-s82 DL
    five-window 2*L vectors and W5 block D vectors, the
    publication-s87 TS five-window 2*L vectors and W5 TS block
    values -- plus the integrity/C1 parser rows, the s86
    decomposition identity's 240 prior checks, and the REF-CONSTANT
    cross-check. NAMED, NOT HIDDEN: the exact-enumeration null has
    NO published reproduction target (no prior row used this null --
    T19 is descriptive-only by frozen design), so --compat validates
    the CONSTRUCTION against published bytes and the NULL ENGINE is
    validated in --self-test by hand-computable exact cases plus an
    INDEPENDENT pure-Python twin.
  --self-test: the fixture suite -- the half-spread/decomposition
    identities on deterministic pooled-75 permutations, hand-
    computable exact-enumeration cases at the FULL 4,096 assignments
    (the identical-block case has count = sum_{m=0..5} C(12,m) =
    1586), an INDEPENDENT pure-Python twin of the null engine (NO
    numpy) cross-checked in-loop on synthetic data, the letter/joint
    tables, and a MOCK end-to-end run of the full-row glue on a
    deterministic synthetic 78-log window -- MOCK numbers are
    FIXTURES, never measurements.
  analysis-s<NN>.py (the adopted frozen filename): the real T20 row
    over the six windows; fail-closed (exit non-zero) if the W6 run
    logs are absent (the freeze: the analysis half runs only after
    the W6 measurement half commits them).

NO T20 quantity is computed in this pre-build: no W6 contrast, no
T20 p-value, no T20 letter on any real window. Deterministic apart
from NOTHING (the exact enumeration carries no RNG stream): the
claim is "run twice, byte-identical (cmp exit 0)".
"""
import os
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
# 1-indexed rank pairs). QP pairs = the publication-s78 axes and DL
# pairs = the s81 closed doubling-ladder vocabulary: their
# reproduction is a section-6 validity pin (and DLk is the
# decomposition partner D_DLk of HL_k/HR_k). TS pairs = the s86
# tail-side half-pair vocabulary (the T20 construction): TS-Lk =
# (x_(38-k), x_(38)) HL_k, TS-Rk = (x_(38), x_(38+k)) HR_k.
QP_PAIRS = (("INNER (28,48)", 27, 47), ("OUTER (9,67)", 8, 66))
DL_PAIRS = (("DL4 (x_(34),x_(42))", 33, 41), ("DL8 (x_(30),x_(46))", 29, 45),
            ("DL16 (x_(22),x_(54))", 21, 53), ("DL32 (x_(6),x_(70))", 5, 69))
DL_ORDER = [p[0] for p in DL_PAIRS]
DL_TBL = {p[0]: (p[1], p[2]) for p in DL_PAIRS}
QP_TBL = {p[0]: (p[1], p[2]) for p in QP_PAIRS}

CENTER = 37                    # 0-based index of the x_(38) deviation center
FAMS = (4, 8, 16, 32)          # the s86 closed k vocabulary (section 1)
TS_PAIRS = (("TS-L4 (x_(34),x_(38))", 4, "L"), ("TS-R4 (x_(38),x_(42))", 4, "R"),
            ("TS-L8 (x_(30),x_(38))", 8, "L"), ("TS-R8 (x_(38),x_(46))", 8, "R"),
            ("TS-L16 (x_(22),x_(38))", 16, "L"),
            ("TS-R16 (x_(38),x_(54))", 16, "R"),
            ("TS-L32 (x_(6),x_(38))", 32, "L"),
            ("TS-R32 (x_(38),x_(70))", 32, "R"))
TS_ORDER = [p[0] for p in TS_PAIRS]
TS_TBL = {p[0]: (p[1], p[2]) for p in TS_PAIRS}
TS_SIDE = {(k, s): label for (label, k, s) in TS_PAIRS}
INFORMATIVE_FAMS = (16, 32)    # s86 section 4(c): k=4/8 in the noise band
UNINFORMATIVE_TAG = "UNINFORMATIVE-BY-S86-CAVEAT"
ASSIGN = 4096                  # 2^12 exact whole-block side-swap assignments
DL_IDX = {4: (33, 41), 8: (29, 45), 16: (21, 53), 32: (5, 69)}

# frozen prior-window reference vectors (the analysis-s78/s82
# constants verbatim; cross-checked against the committed publication
# bytes in --compat, section G)
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
                                             # (s88 section 6: NO anchor
                                             # is computed at W6)

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

    def named_half(self, win):
        """12 blocks -> {k: (hl_list, hr_list)} at the named cell, tw arm."""
        out = {k: ([], []) for k in FAMS}
        for blk in self.named_blocks(win):
            hp = half_of(blk)
            for k in FAMS:
                out[k][0].append(hp[k][0])
                out[k][1].append(hp[k][1])
        return out

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
# the frozen estimator machinery (s88 section 1)
# ------------------------------------------------------------------
def d_pair(arr, i, j):
    """(...,75) int64 -> exact INTEGER pair spread x_(j+1) - x_(i+1)."""
    srt = np.sort(arr, axis=-1)
    return srt[..., j] - srt[..., i]


def l2_of(block_d):
    """12 block values -> 2*L = 6th+7th order statistics (INTEGER)."""
    s = np.sort(np.asarray(block_d, dtype=np.int64))
    return int(s[5] + s[6])


def half_of(block):
    """one pooled-75 block -> {k: (HL_k, HR_k)} EXACT INTEGER (s86 pairs)."""
    srt = sorted(int(x) for x in block)
    c = srt[CENTER]
    return {k: (c - srt[CENTER - k], srt[CENTER + k] - c) for k in FAMS}


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


def ts_vectors(corpus, windows):
    """per TS pair: {win: 2*L} over the 12 block HL_k/HR_k values + blocks."""
    out = {}
    for label in TS_ORDER:
        k, side = TS_TBL[label]
        vec, blk = {}, {}
        for win, _d in windows:
            hp = corpus.named_half(win)
            vals = hp[k][0] if side == "L" else hp[k][1]
            vec[win] = l2_of(vals)
            blk[win] = list(vals)
        out[label] = (vec, blk)
    return out


def decomp_check(corpus, windows):
    """HL_k + HR_k == D_DLk per block (the s86 decomposition identity).

    Returns (n_checks, bad) where bad names each violation.
    """
    n = 0
    bad = []
    for win, _d in windows:
        for blk in corpus.named_blocks(win):
            srt = sorted(int(x) for x in blk)
            hp = half_of(blk)
            for k in FAMS:
                i, j = DL_IDX[k]
                n += 1
                want = srt[j] - srt[i]
                if hp[k][0] + hp[k][1] != want:
                    bad.append((win, k, hp[k][0] + hp[k][1], want))
    return n, bad


# ------------------------------------------------------------------
# the frozen null engine (s88 section 4 -- exact enumeration, NO RNG)
# ------------------------------------------------------------------
_MASKS = None


def side_masks():
    """(4096, 12) bool: bit b of assignment a = block b swapped."""
    a = np.arange(ASSIGN, dtype=np.int64)[:, None]
    b = np.arange(12, dtype=np.int64)[None, :]
    return ((a >> b) & 1).astype(bool)


def exact_null(hlhr):
    """Exact within-block side-exchangeability null (frozen section 4).

    hlhr: {k: (hl_12, hr_12)}. All 2^12 = 4,096 whole-block side-swap
    assignments enumerated (one bit per block; bit=1 swaps that block's
    HL/HR for ALL FOUR families together -- the shared mask IS the
    frozen coupling); per assignment 2*L_HL*, 2*L_HR* per family and
    C* = 2*L_HL* - 2*L_HR*; p = count(C* >= C_obs) / 4,096 ONE-SIDED
    in the pre-registered direction. The identity (all-zero)
    assignment is assignment 0, so C*(0) = C_obs and p >= 1/4,096.
    NO RNG ANYWHERE.
    """
    global _MASKS
    if _MASKS is None:
        _MASKS = side_masks()
    res = {}
    for k in FAMS:
        hl = np.asarray(hlhr[k][0], dtype=np.int64)
        hr = np.asarray(hlhr[k][1], dtype=np.int64)
        L = np.where(_MASKS, hr[None, :], hl[None, :])
        R = np.where(_MASKS, hl[None, :], hr[None, :])
        L.sort(axis=1)
        R.sort(axis=1)
        l2L = L[:, 5] + L[:, 6]
        l2R = R[:, 5] + R[:, 6]
        cs = l2L - l2R
        c_obs = int(cs[0])                 # identity assignment
        cnt = int((cs >= c_obs).sum())
        res[k] = dict(l2L=int(l2L[0]), l2R=int(l2R[0]), c_obs=c_obs,
                      count=cnt, p=cnt / ASSIGN)
    return res


def py_exact_null(hlhr):
    """INDEPENDENT pure-Python twin of exact_null (self-test cross-check).

    NO numpy: explicit sorted() order statistics, explicit bit loops in
    a different enumeration shape; the ONLY shared contract is the
    frozen definition (all 2^12 assignments, swap = one block bit for
    all families, p = count/4,096).
    """
    res = {}
    for k in FAMS:
        hl = [int(x) for x in hlhr[k][0]]
        hr = [int(x) for x in hlhr[k][1]]
        c_obs = None
        cnt = 0
        l2L0 = l2R0 = None
        for bits in range(ASSIGN):
            L, R = [], []
            for b in range(12):
                if (bits >> b) & 1:
                    L.append(hr[b])
                    R.append(hl[b])
                else:
                    L.append(hl[b])
                    R.append(hr[b])
            L.sort()
            R.sort()
            c = (L[5] + L[6]) - (R[5] + R[6])
            if c_obs is None:
                c_obs = c
                l2L0 = L[5] + L[6]
                l2R0 = R[5] + R[6]
            if c >= c_obs:
                cnt += 1
        res[k] = dict(l2L=l2L0, l2R=l2R0, c_obs=c_obs,
                      count=cnt, p=cnt / ASSIGN)
    return res


# ------------------------------------------------------------------
# the frozen letters / joint (s88 section 5)
# ------------------------------------------------------------------
def family_letter(c_obs, p, invalidated):
    if invalidated:
        return "(c) NOT EVALUABLE"
    if c_obs > 0 and p <= 0.05:
        return "(a) ASYMMETRY-LEFT-GREATER-REPLICATED"
    if c_obs <= 0:
        return "(b) NOT-REPLICATED [DIRECTION-REVERSED]"
    return "(b) NOT-REPLICATED [DIRECTION-CONSISTENT-NOT-SIGNIFICANT]"


def joint_letter(letters, invalidated):
    if invalidated:
        return "(c) NOT EVALUABLE"
    fails = [k for k in INFORMATIVE_FAMS if not letters[k].startswith("(a)")]
    if not fails:
        return ("(a) TAIL-SIDE-ASYMMETRY-REPLICATED-ON-INFORMATIVE-FAMILIES")
    named = "|".join("k=%d %s" % (k, letters[k]) for k in fails)
    return "(b) NOT-REPLICATED (named failing: %s)" % named


# ------------------------------------------------------------------
# the published want values (PARSED from the committed publication
# bytes -- never transcribed; shared by --compat and full mode)
# ------------------------------------------------------------------
PUB78_DIR = "anv-b3w5qpairevel-20261029"
PUB82_DIR = "anv-b3dlprofile-20261029"
PUB87_DIR = "anv-b3tailprofile-20261029"


def vec_blk_want(pub, label, indent, blkword):
    m = re.search(r"^%s%s: 2\*L s36/s38/s39/s51/s73 = ([\d/]+) \("
                  % (indent, re.escape(label)), pub, re.M)
    assert m, label
    want_v = tuple(int(x) for x in m.group(1).split("/"))
    m = re.search(r"^%s%s W5 block %s: ([\d ]+)$"
                  % (indent, re.escape(label), blkword), pub, re.M)
    assert m, label
    want_b = tuple(int(x) for x in m.group(1).split())
    return want_v, want_b


def parse_wants():
    pub78 = open(os.path.join(GPU, PUB78_DIR, "publication-s78.txt")).read()
    pub82 = open(os.path.join(GPU, PUB82_DIR, "publication-s82.txt")).read()
    pub87 = open(os.path.join(GPU, PUB87_DIR, "publication-s87.txt")).read()
    want = {}
    for label in [p[0] for p in QP_PAIRS]:
        want[label] = vec_blk_want(pub78, label, "      ", "D values")
    for label in DL_ORDER:
        want[label] = vec_blk_want(pub82, label, "   ", "D values")
    for label in TS_ORDER:
        want[label] = vec_blk_want(pub87, label, "   ", "values")
    m = re.search(r"240 checks\): (\S+ \S+)", pub87)
    decomp_want = m.group(1)
    return pub78, pub82, pub87, want, decomp_want


# ==================================================================
# MODE: compat -- the section-6 parser validity pins two-way against
# the committed publication bytes.
# ==================================================================
def mode_compat():
    pub78, pub82, pub87, want, decomp_want = parse_wants()

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

    # -- B. C1 rows (3), computed at the W5 window (the rows'
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

    # -- C. QP validity vectors (five-window 2*L + W5 block D),
    #       want = publication-s78 section-5 D1 lines
    qp_vecs = named_vectors(corpus, QP_PAIRS, WIN5)
    for label in [p[0] for p in QP_PAIRS]:
        vec, blk = qp_vecs[label]
        got_v = tuple(vec[w] for w, _d in WIN5)
        rows.append(("%s five-window 2*L" % label, got_v, want[label][0]))
        rows.append(("%s W5 block D" % label, tuple(blk["s73"]), want[label][1]))

    # -- D. DL validity vectors (five-window 2*L + W5 block D),
    #       want = publication-s82 D1/D2 lines
    dl_vecs = named_vectors(corpus, DL_PAIRS, WIN5)
    for label in DL_ORDER:
        vec, blk = dl_vecs[label]
        got_v = tuple(vec[w] for w, _d in WIN5)
        rows.append(("%s five-window 2*L" % label, got_v, want[label][0]))
        rows.append(("%s W5 block D" % label, tuple(blk["s73"]), want[label][1]))

    # -- E. TS validity vectors (five-window 2*L + W5 block values),
    #       want = publication-s87 section-4 lines (the T20
    #       construction itself, validated against the published T19
    #       reference vectors)
    ts_vecs = ts_vectors(corpus, WIN5)
    for label in TS_ORDER:
        vec, blk = ts_vecs[label]
        got_v = tuple(vec[w] for w, _d in WIN5)
        rows.append(("%s five-window 2*L" % label, got_v, want[label][0]))
        rows.append(("%s W5 block values" % label, tuple(blk["s73"]),
                     want[label][1]))

    # -- F. the s86 decomposition identity (HL_k + HR_k = D_DLk per
    #       block; the 240 prior checks of publication-s87 section 1),
    #       want = publication-s87's own "EXACT everywhere" line
    n_dec, bad_dec = decomp_check(corpus, WIN5)
    got_dec = "EXACT everywhere" if not bad_dec else (
        "EXACT %d/%d (%s)" % (n_dec - len(bad_dec), n_dec, bad_dec[:3]))
    rows.append(("sec6 decomposition identity %d checks" % n_dec,
                 got_dec, decomp_want))

    # -- G. reference-constant cross-check (the REF_X/REF_Y block-min
    #       constants vs publication-s82.txt section 3 bytes and the
    #       REF_ANCHOR constants vs its section-3b bytes)
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
    P("JUN-59 session 93 -- T20 ANALYSIS PRE-BUILD, --compat VALIDATION")
    P("(the s88-frozen T20 analysis machinery recomputed over the FIVE")
    P("committed windows and two-way-checked against the committed")
    P("publication bytes; want values PARSED from publication-s78.txt /")
    P("publication-s82.txt / publication-s87.txt, never transcribed).")
    P("NO W6 quantity exists or is computed (the W6 run logs do not")
    P("exist); NO T20 quantity exists (T20 is frozen ONLY at the W6")
    P("window and its null runs only after the W6 measurement half")
    P("commits the logs). What runs here: the s88 section-6 PARSER")
    P("VALIDITY PINS, the integrity/C1 parser rows, the s86")
    P("decomposition identity's 240 prior checks, and the REF-CONSTANT")
    P("cross-check. NAMED, NOT HIDDEN: the exact-enumeration null has")
    P("NO published reproduction target (no prior row used this null --")
    P("T19 is descriptive-only by frozen design), so the null engine is")
    P("validated in --self-test (hand-computable exact cases + an")
    P("independent pure-Python twin), NOT here.")
    P("")
    for (nm, got, want_v) in rows:
        P("row %s: got %s | want %s | EXACT: %s" % (nm, got, want_v, got == want_v))
    bad = [nm for (nm, got, want_v) in rows if got != want_v]
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
# MODE: full -- the real T20 row (adopted name analysis-s<NN>.py).
# Also driven by the self-test's MOCK end-to-end fixture run.
# ==================================================================
def t20_row(session, w6_dirname, out_path, w6_tag=None):
    w6_runwin = os.path.join(GPU, w6_dirname, "run-window.txt")
    if w6_tag is None:
        if not os.path.isdir(os.path.join(GPU, w6_dirname)):
            print("FAIL-CLOSED: the W6 run logs are absent (%s): the T20 "
                  "analysis half runs only after the W6 measurement half "
                  "commits them (s88 section 8)." % w6_dirname)
            return None
        first = open(w6_runwin).readline()
        m = re.search(r"session (\d+)", first)
        assert m, first
        w6_tag = "s%s" % m.group(1)
    windows = WIN5 + [(w6_tag, w6_dirname)]
    corpus = Corpus(windows)
    _pub78, _pub82, _pub87, want, decomp_want = parse_wants()

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

    # parser validity pins (the s88 section-6 honesty anchor) --
    # wants PARSED from the committed publication bytes
    qp_vecs = named_vectors(corpus, QP_PAIRS, WIN5)
    dl_vecs = named_vectors(corpus, DL_PAIRS, WIN5)
    ts_vecs = ts_vectors(corpus, WIN5)
    pins_ok = True
    pin_rows = []
    for tbl in (qp_vecs, dl_vecs, ts_vecs):
        for label in [l for l in want if l in tbl]:
            vec_w, blk_w = tbl[label]
            want_v, want_b = want[label]
            got_v = [vec_w[w] for w, _d in WIN5]
            got_b = blk_w["s73"]
            ok = (got_v == list(want_v) and got_b == list(want_b))
            if not ok:
                pins_ok = False
                inv_notes.append("parser validity pin mismatch at %s" % label)
            pin_rows.append((label, got_v, got_b, ok))

    n_dec, bad_dec = decomp_check(corpus, windows)
    decomp_ok = (not bad_dec) and n_dec == 4 * len(windows) * 12
    if not decomp_ok:
        inv_notes.append("decomposition identity violation (%d checks, %d bad)"
                         % (n_dec, len(bad_dec)))

    invalidated = (not integrity_ok) or (not named_ok) or (not c1_ok) \
        or (not vec_ok) or (not anchor_ok) or (not pins_ok) or (not decomp_ok)

    # -- sections 1/3/4: the T20 construction + the frozen exact null
    hp6 = corpus.named_half(w6_tag)
    prim = exact_null(hp6)
    letters = {k: family_letter(prim[k]["c_obs"], prim[k]["p"], invalidated)
               for k in FAMS}
    joint = joint_letter(letters, invalidated)

    # -- section 7: D-family (descriptive only)
    ts6 = ts_vectors(corpus, windows)
    dl6 = named_vectors(corpus, DL_PAIRS, windows)
    d3 = {}
    for label in TS_ORDER:
        vec6, _blk = ts6[label]
        band = sorted(vec6[w] for w in ("s38", "s39", "s51"))
        lo, hi = band[0], band[2]      # [MIN, MAX] -- the s83/s89 convention
        v6 = vec6[w6_tag]
        d3[label] = (lo, hi,
                     "INSIDE" if lo <= v6 <= hi else
                     ("OUTSIDE-BELOW" if v6 < lo else "OUTSIDE-ABOVE"))

    # -- the publication
    out = []
    P = out.append
    P("JUN-59 session %d -- THE TAIL-SIDE ASYMMETRY REPLICATION AT W6"
      % session)
    P("(T20, the s88-frozen inferential row; publication-s%d.txt,"
      % session)
    P("produced ONLY by analysis-s%d.py over the COMMITTED run logs of" % session)
    P("the six evidence directories: the five prior windows of")
    P("publication-s82.txt section 0 plus %s = the W6 window (window" % w6_dirname)
    P("tag %s), measured by the W6 measurement half under the s80" % w6_tag)
    P("freeze. protocol.txt freeze stamp 2026-10-29T08:16:54Z preceded")
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
        P("   PIN %s: five-window 2*L %s; W5 block values %s; EXACT: %s"
          % (label, "/".join(map(str, got_v)),
             " ".join(map(str, got_b)), ok))
    P("   pins EXACT (14/14 vectors + 14/14 block vectors): %s" % pins_ok)
    P("   decomposition identity HL_k+HR_k = D_DLk (%d checks = 4 fams x "
      "%d windows x 12 blocks): %s (want %s)"
      % (n_dec, len(windows),
         "EXACT everywhere" if not bad_dec else "VIOLATIONS %s" % bad_dec[:3],
         decomp_want))
    P("")
    P("4. T20 THE ROW QUESTION (frozen letters, protocol sections 3/4/5):")
    P("   the NAMED cell %s of the tw arm; per-block HL_k/HR_k over"
      % corpus.ckey_str(corpus.nc))
    P("   the block's pooled 75 gpu_ticks (EXACT INTEGER) at the closed")
    P("   s86 vocabulary; 2*L = 6th+7th order statistics of the 12 block")
    P("   values; C_obs = 2*L({HL_k}) - 2*L({HR_k}) per family; the")
    P("   null: WITHIN-BLOCK SIDE-EXCHANGEABILITY -- all 2^12 = 4,096")
    P("   whole-block side-swap assignments enumerated EXACTLY (one bit")
    P("   per block, that block's HL/HR swapped for ALL FOUR families")
    P("   together; NO RNG); p = count(C* >= C_obs) / 4,096, ONE-SIDED")
    P("   in the pre-registered direction C_obs > 0:")
    for k in FAMS:
        r = prim[k]
        P("   k=%d %s/%s: 2*L_HL = %d (%s); 2*L_HR = %d (%s); C_obs = %d "
          "(%s); count %d / 4,096; p = %.10f; family letter %s%s"
          % (k, TS_SIDE[(k, "L")], TS_SIDE[(k, "R")],
             r["l2L"], fmt_ht(r["l2L"]), r["l2R"], fmt_ht(r["l2R"]),
             r["c_obs"], fmt_ht(r["c_obs"]), r["count"], r["p"],
             letters[k],
             ("" if k in INFORMATIVE_FAMS else " [" + UNINFORMATIVE_TAG + "]")))
    P("   JOINT T20 = %s" % joint)
    P("   (the k=4/8 letters carry the standing %s tag and never" % UNINFORMATIVE_TAG)
    P("   enter the joint; IUT convention, NO multiplicity correction.)")
    P("")
    P("5. D-FAMILY (descriptive only, NO letter):")
    P("   D1 six-window 2*L vectors (s36/s38/s39/s51/W5/%s) + R-L level" % w6_tag)
    P("   difference vectors (the T19 convention):")
    for k in FAMS:
        lv, _lb = ts6[TS_SIDE[(k, "L")]]
        rv, _rb = ts6[TS_SIDE[(k, "R")]]
        ws = [w for w, _d in windows]
        P("   k=%d %s 2*L %s; %s 2*L %s; R-L %s"
          % (k, TS_SIDE[(k, "L")],
             "/".join(str(lv[w]) for w in ws),
             TS_SIDE[(k, "R")],
             "/".join(str(rv[w]) for w in ws),
             "/".join(str(rv[w] - lv[w]) for w in ws)))
    P("   D2 the 12 %s block values per pair (for a future census):" % w6_tag)
    for label in TS_ORDER:
        _v, b = ts6[label]
        P("   %s %s block values: %s"
          % (label, w6_tag, " ".join(str(x) for x in b[w6_tag])))
    P("   D3 %s-vs-post-shift-band (the CLOSED INTERVAL [MIN, MAX] of" % w6_tag)
    P("   {2*L_s38, 2*L_s39, 2*L_s51} -- the s83/s89 convention, NOT")
    P("   min..median; descriptive, never a test):")
    for label in TS_ORDER:
        lo, hi, verdict = d3[label]
        P("   %s: 2*L_%s = %d vs band 2*L %d..%d: %s"
          % (label, w6_tag, ts6[label][0][w6_tag], lo, hi, verdict))
    P("   D4 sum-of-levels vs 2*L(D_k) (the publication-s87 section-5b")
    P("   convention -- the 2*L LEVELS do NOT add; printed to NAME the")
    P("   non-additivity, never to test it):")
    ws = [w for w, _d in windows]
    for k in FAMS:
        lv, _lb = ts6[TS_SIDE[(k, "L")]]
        rv, _rb = ts6[TS_SIDE[(k, "R")]]
        dv, _db = dl6[DL_ORDER[FAMS.index(k)]]
        P("   k=%d: sum-of-levels vs 2*L(D_k) %s -- levels do NOT add"
          % (k, " ".join("%d/%d" % (lv[w] + rv[w], dv[w]) for w in ws)))
    P("")
    P("6. VERDICT SUMMARY:")
    P("   T20 = %s" % joint)
    for k in FAMS:
        r = prim[k]
        P("   k=%d: 2*L_HL %d vs 2*L_HR %d (C_obs %d); count %d/4,096; "
          "p %.10f; letter %s"
          % (k, r["l2L"], r["l2R"], r["c_obs"], r["count"], r["p"],
             letters[k]))
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
                "MEASUREMENT; synthetic logs for the s93 pre-build "
                "self-test).\n")
    for tag in ("c2", "hi", "tw", "c8"):
        b, wm, dd, runs = ARMS[tag]
        for r in runs:
            lines = ["# mock fixture (s93 self-test) arm=%s run=%d" % (tag, r)]
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
    print("JUN-59 session 93 -- T20 ANALYSIS PRE-BUILD --self-test "
          "(fixture suite; every quantity here is a FIXTURE, never a "
          "measurement; no real window is tested inferentially).")
    print("")

    # ST1: half-spread + decomposition identity on deterministic
    #      pooled-75 permutations of 0..74
    for name, arr in (("asc", list(range(75))),
                      ("desc", list(range(74, -1, -1))),
                      ("perm", [(i * 7) % 75 for i in range(75)])):
        srt = sorted(arr)
        hp = half_of(arr)
        for k in FAMS:
            t.check("half %s k%d hl" % (name, k), hp[k][0], srt[37] - srt[37 - k])
            t.check("half %s k%d hr" % (name, k), hp[k][1], srt[37 + k] - srt[37])
            t.check("decomp %s k%d" % (name, k), hp[k][0] + hp[k][1],
                    srt[37 + k] - srt[37 - k])

    # ST2: 2*L identity (hand-computable)
    t.check("2*L [1..12]", l2_of(list(range(1, 13))), 13)
    t.check("2*L [12..1]", l2_of(list(range(12, 0, -1))), 13)
    t.check("2*L all-5", l2_of([5] * 12), 10)
    t.check("2*L hand", l2_of([3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8]), 9)

    # ST3: degenerate null at the FULL 4,096 assignments (hand-
    #      computable: HL = HR = 0 -> every C* = 0 -> count = all)
    deg = {k: ([0] * 12, [0] * 12) for k in FAMS}
    res_np = exact_null(deg)
    res_py = py_exact_null(deg)
    for k in FAMS:
        t.check("degenerate k%d 2*L_HL" % k, res_np[k]["l2L"], 0)
        t.check("degenerate k%d 2*L_HR" % k, res_np[k]["l2R"], 0)
        t.check("degenerate k%d C_obs" % k, res_np[k]["c_obs"], 0)
        t.check("degenerate k%d count" % k, res_np[k]["count"], ASSIGN)
        t.check("degenerate k%d p" % k, res_np[k]["p"], 1.0)
        t.check("degenerate-twin k%d count" % k, res_py[k]["count"], ASSIGN)
        t.check("degenerate k%d letter" % k,
                family_letter(res_np[k]["c_obs"], res_np[k]["p"], False),
                "(b) NOT-REPLICATED [DIRECTION-REVERSED]")

    # ST4: hand-computable exact cases at the full assignment space.
    #      identical blocks (HL,HR) = (4,2): C*(m) = 4 for m<=5, 0 at
    #      m=6, -4 for m>=7 -> C_obs = 4, count = sum_{m=0..5} C(12,m)
    #      = 1586, p = 1586/4096 (one-sided, identity included).
    #      mirrored (2,4): C_obs = -4, every C* >= -4 -> count = 4096.
    hand = {k: ([4] * 12, [2] * 12) for k in FAMS}
    res_np = exact_null(hand)
    res_py = py_exact_null(hand)
    for k in FAMS:
        t.check("hand(4,2) k%d C_obs" % k, res_np[k]["c_obs"], 4)
        t.check("hand(4,2) k%d count" % k, res_np[k]["count"], 1586)
        t.check("hand(4,2) k%d p" % k, res_np[k]["p"], 1586 / 4096)
        t.check("hand(4,2)-twin k%d count" % k, res_py[k]["count"], 1586)
        t.check("hand(4,2)-twin k%d p" % k, res_py[k]["p"], 1586 / 4096)
        t.check("hand(4,2) k%d letter" % k,
                family_letter(res_np[k]["c_obs"], res_np[k]["p"], False),
                "(b) NOT-REPLICATED [DIRECTION-CONSISTENT-NOT-SIGNIFICANT]")
    hand = {k: ([2] * 12, [4] * 12) for k in FAMS}
    res_np = exact_null(hand)
    res_py = py_exact_null(hand)
    for k in FAMS:
        t.check("hand(2,4) k%d C_obs" % k, res_np[k]["c_obs"], -4)
        t.check("hand(2,4) k%d count" % k, res_np[k]["count"], ASSIGN)
        t.check("hand(2,4) k%d p" % k, res_np[k]["p"], 1.0)
        t.check("hand(2,4)-twin k%d count" % k, res_py[k]["count"], ASSIGN)
        t.check("hand(2,4) k%d letter" % k,
                family_letter(res_np[k]["c_obs"], res_np[k]["p"], False),
                "(b) NOT-REPLICATED [DIRECTION-REVERSED]")

    # ST5: INDEPENDENT twin cross-check on deterministic synthetic
    #      data (non-degenerate) + identity-included properties
    syn = {}
    for k in FAMS:
        hl = [10 * k + 3 * (b % 7) + (b % 5) for b in range(12)]
        hr = [7 * k + 2 * (b % 4) + (b % 3) for b in range(12)]
        syn[k] = (hl, hr)
    res_np = exact_null(syn)
    res_py = py_exact_null(syn)
    for k in FAMS:
        for field in ("l2L", "l2R", "c_obs", "count", "p"):
            t.check("twin k%d %s" % (k, field),
                    res_np[k][field], res_py[k][field])
        t.check("identity-included k%d" % k, res_np[k]["count"] >= 1, True)
        t.check("p-resolution k%d" % k,
                res_np[k]["p"], res_np[k]["count"] / 4096)
        t.check("p-floor k%d" % k, res_np[k]["p"] >= 1 / 4096, True)

    # ST6: letter table (hand cases, s88 section 5)
    t.check("letter a", family_letter(18, 0.04, False),
            "(a) ASYMMETRY-LEFT-GREATER-REPLICATED")
    t.check("letter boundary p", family_letter(18, 0.05, False),
            "(a) ASYMMETRY-LEFT-GREATER-REPLICATED")
    t.check("letter b ns", family_letter(18, 0.073896, False),
            "(b) NOT-REPLICATED [DIRECTION-CONSISTENT-NOT-SIGNIFICANT]")
    t.check("letter b zero", family_letter(0, 0.5, False),
            "(b) NOT-REPLICATED [DIRECTION-REVERSED]")
    t.check("letter b rev", family_letter(-6, 0.577921, False),
            "(b) NOT-REPLICATED [DIRECTION-REVERSED]")
    t.check("letter c", family_letter(18, 0.04, True), "(c) NOT EVALUABLE")

    # ST7: joint table (hand cases; k=4/8 excluded per s86 4(c))
    la = "(a) ASYMMETRY-LEFT-GREATER-REPLICATED"
    lb = "(b) NOT-REPLICATED [DIRECTION-REVERSED]"
    t.check("joint uninformative-excluded",
            joint_letter({4: lb, 8: lb, 16: la, 32: la}, False),
            "(a) TAIL-SIDE-ASYMMETRY-REPLICATED-ON-INFORMATIVE-FAMILIES")
    j = joint_letter({4: la, 8: la, 16: la, 32: lb}, False)
    t.check("joint k32-failing-named", j,
            "(b) NOT-REPLICATED (named failing: k=32 %s)" % lb)
    j = joint_letter({4: la, 8: la, 16: lb, 32: la}, False)
    t.check("joint k16-failing-named", j,
            "(b) NOT-REPLICATED (named failing: k=16 %s)" % lb)
    j = joint_letter({4: la, 8: la, 16: lb, 32: lb}, False)
    t.check("joint both-failing-named", j,
            "(b) NOT-REPLICATED (named failing: k=16 %s|k=32 %s)" % (lb, lb))
    t.check("joint invalidated",
            joint_letter({k: la for k in FAMS}, True),
            "(c) NOT EVALUABLE")

    # ST8: the exact-enumeration p has NO published reproduction
    #      target (named; checked here as a printed marker so the
    #      claim cannot silently change)
    t.check("no-published-null-target marker",
            "NO published reproduction target", "NO published reproduction target")

    # ST9: MOCK end-to-end run of the full-row glue (fixtures only)
    mock_dir = os.path.join(SCRATCH, "mck-w6-s93")
    make_mock_window(mock_dir)
    mock_rel = os.path.relpath(mock_dir, GPU)
    out_path = os.path.join(SCRATCH, "mck-t20-publication.txt")
    row = t20_row(998, mock_rel, out_path, w6_tag="s999")
    t.check("mock row computed", row is not None, True)
    t.check("mock not invalidated", row["invalidated"], False)
    t.check("mock w6 tag", row["w6_tag"], "s999")
    t.check("mock joint is a/b token",
            row["joint"].startswith("(a)") or row["joint"].startswith("(b)"),
            True)
    for k in FAMS:
        t.check("mock letter token k%d" % k,
                row["letters"][k].startswith("(a)")
                or row["letters"][k].startswith("(b)"), True)
        for label in (TS_SIDE[(k, "L")], TS_SIDE[(k, "R")]):
            lo, hi, verdict = row["d3"][label]
            v6 = row["prim"][k]["l2L"] if TS_TBL[label][1] == "L" \
                else row["prim"][k]["l2R"]
            t.check("mock D3 band %s ordered" % label, lo <= hi, True)
            t.check("mock D3 verdict %s" % label, verdict,
                    "INSIDE" if lo <= v6 <= hi else
                    ("OUTSIDE-BELOW" if v6 < lo else "OUTSIDE-ABOVE"))
    text = row["text"]
    t.check("mock publication has s999", "s999" in text, True)
    t.check("mock publication has joint line", "JOINT T20 = " in text, True)
    m = re.search(r"PIN TS-R32 \(x_\(38\),x_\(70\)\): five-window 2\*L "
                  r"213/186/183/204/214", text)
    t.check("mock publication pin TS-R32 exact", m is not None, True)
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
    row = t20_row(SESSION, W6_DIR, out_path)
    sys.exit(0 if row is not None else 1)
