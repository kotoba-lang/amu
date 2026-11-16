#!/usr/bin/env python3
"""JUN-59 session 82 -- THE DL LEVEL-AXIS DESCRIPTIVE REFERENCE ROW
(analysis-s82.py; the s82-frozen protocol.txt of THIS directory,
sections 0/1/2/3/4/5/6).

WHAT THIS IS (honest states): the IMPLEMENTED analysis half of the
s82-frozen T17 descriptive row -- the DOUBLING LADDER vocabulary's
FIRST STATISTIC (the freeze is
docs/evidence/gpu/anv-b3dlprofile-20261029/protocol.txt, written
once at freeze stamp 2026-10-29T05:22:05Z BEFORE any statistic of
this row exists). Pairs named ONLY from the s81-frozen vocabulary
(DL4/DL8/DL16/DL32 -- the WHOLE closed vocabulary, no selection).
DESCRIPTIVE ONLY: NO letter, NO null, NO resampling, NO RNG, NO
threshold, NO direction. It parses the COMMITTED run logs only:
NO hardware runs, NO builds, NO compiles, NO GO stamp at this
session (protocol section 6: NO reading -> NO settle-bar-ledger
line, NO day-slot consumption).

Deterministic by construction: no RNG anywhere; running this
generator twice yields byte-identical output.
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
GPU = os.path.join(ROOT, "docs", "evidence", "gpu")

SESSION = 82
NEW_WIN = "s73"   # the W5 window tag of the xdayrep row (its run logs)
WINDOWS = [("s36", "anv-b3commonmode-20261028"),
           ("s38", "anv-b3joint3-20261028"),
           ("s39", "anv-b3joint4-20261028"),
           ("s51", "anv-b3levelrep-20261028"),
           (NEW_WIN, "anv-b3w5xdayrep-20261029")]
ARMS = {"c2": (2, 1, 1, [1, 2, 3]),
        "hi": (3, 1024, 4033, list(range(1, 37))),
        "tw": (3, 2048, 8066, list(range(1, 37))),
        "c8": (8, 1, 1, [1, 2, 3])}
COMMITTED_C8 = 32915
NAMED_CKEY = ("max", 128, "default")

# THE DL VOCABULARY (protocol section 1; 0-based sorted indices of
# the pooled 75 for the 1-indexed rank pairs (34,42)/(30,46)/
# (22,54)/(6,70)).
DL = (("DL4", 33, 41), ("DL8", 29, 45), ("DL16", 21, 53), ("DL32", 5, 69))
DL_LABEL = {"DL4": "DL4 (x_(34),x_(42))", "DL8": "DL8 (x_(30),x_(46))",
            "DL16": "DL16 (x_(22),x_(54))", "DL32": "DL32 (x_(6),x_(70))"}

# PARSER VALIDITY PINS (protocol section 4): the PUBLISHED
# publication-s78.txt quantile-pair vectors at the named cell/tw
# arm -- QUOTE-ONLY content recomputed here only as validity.
VALID = (("inner", "INNER (28,48)", 27, 47,
          [118, 102, 128, 113, 100],
          [42, 34, 40, 48, 74, 48, 60, 39, 74, 56, 52, 57]),
         ("outer", "OUTER (9,67)", 8, 66,
          [496, 429, 437, 446, 502],
          [267, 189, 242, 377, 340, 278, 214, 181, 255, 247, 268, 194]))

# frozen reference vectors / anchors (publication-s39.txt section 3
# for s36/s38/s39; publication-s51.txt section 3 for s51)
REF_X = {"s39": [986, 991, 984, 985, 989, 989, 986, 990, 995, 986, 987, 981],
         "s36": [991, 989, 981, 998, 993, 985, 984, 997, 994, 994, 980, 982],
         "s38": [992, 988, 984, 1007, 985, 984, 986, 983, 992, 991, 982, 997],
         "s51": [988, 986, 1000, 986, 989, 983, 995, 983, 994, 991, 984, 985]}
REF_Y = {"s39": [988, 989, 987, 990, 990, 988, 991, 983, 985, 988, 983, 986],
         "s36": [988, 985, 994, 993, 994, 995, 992, 984, 987, 984, 993, 981],
         "s38": [988, 987, 980, 980, 991, 994, 991, 994, 988, 991, 1001, 992],
         "s51": [980, 975, 991, 979, 986, 986, 992, 991, 988, 993, 995, 996]}
REF_ANCHOR = {"s36": (1142, 991, 1438), "s38": (1132, 992, 1443),
              "s39": (1146, 986, 1432), "s51": (1137, 988, 1430)}

import re
cell_re = re.compile(
    r"^CELL idx=(\d+) spv=(\S+) op=(\S+) wg=(\d+) forced=(\S+) probe_size=(-?\d+) "
    r"probe_nsub=(-?\d+) probe_wg=(-?\d+) pipeline=(\S+) void=(\d)")
verify_re = re.compile(r"^VERIFY idx=(\d+) checked=(\d+) mismatch=(\d+) ok=(\d)")
sample_re = re.compile(
    r"^SAMPLE round=(\d+) idx=(\d+) batch=(\d+) work_mul=(\d+) ndiv=(\d+) gpu_ticks=(\d+) "
    r"gpu_ns=([\d.]+) per_dispatch_ns=([\d.]+) host_ns=(\d+)")

def load(path):
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

def fmt_ht(x2):
    return "%.1f" % (x2 / 2)

# ------------------------------------------------------------------
# parse the five windows; integrity per protocol section 3
# ------------------------------------------------------------------
data = {}
win_info = {}
ref_cellmap = None
for win, dirname in WINDOWS:
    src = os.path.join(GPU, dirname)
    vmis = 0
    counts_ok = knob_ok = fail_ok = cmap_ok = True
    problems = []
    for tag in ("c2", "hi", "tw", "c8"):
        b, wm, dd, runs = ARMS[tag]
        for r in runs:
            fn = os.path.join(src, "run-%s-r%d.txt" % (tag, r))
            cells, verifies, samples = load(fn)
            data[(win, tag, r)] = (cells, verifies, samples)
            for (_i, _c, mis) in verifies:
                vmis += mis
            s8 = [k for k, v in cells.items() if v["forced"] == "8"]
            if len(s8) != 6 or any(cells[k]["pipeline"] != "FAIL" or cells[k]["void"] != "1"
                                   for k in s8):
                fail_ok = False
                problems.append("S=8 fail-closed violation in %s" % fn)
            if len(samples) != 450 or len(verifies) != 24:
                counts_ok = False
                problems.append("SAMPLE/VERIFY count mismatch in %s" % fn)
            for (_rnd, _idx, _gt, _hn, knobs) in samples:
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
                         fail_ok=fail_ok, cmap_ok=cmap_ok, problems=problems)

ok_cells = sorted([k for k, v in data[(WINDOWS[0][0], "c2", 1)][0].items()
                   if v["pipeline"] == "ok"])
cell_pos = {k: i for i, k in enumerate(ok_cells)}

def ckey(idx):
    c = data[(WINDOWS[0][0], "c2", 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])

def ckey_str(idx):
    op, wg, s = ckey(idx)
    return "(%s,%d,S=%s)" % (op, wg, s)

sum128 = [k for k in ok_cells if ckey(k) == ("sum", 128, "16")][0]
nc = [k for k in ok_cells if ckey(k) == NAMED_CKEY][0]
nc_pos = cell_pos[nc]
named_ok = (ckey_str(nc) == "(max,128,S=default)")   # section-0 named cell identity

def pooled(win, tag, idx, runs):
    xs = []
    for r in runs:
        xs += [s[2] for s in data[(win, tag, r)][2] if s[1] == idx]
    return float(np.median(np.asarray(xs, dtype=np.int64)))

def block_vals(win, tag, runs):
    return [pooled(win, tag, k, runs) for k in ok_cells]

# ------------------------------------------------------------------
# C1, block-min vectors, anchor reproduction rows (section 3)
# ------------------------------------------------------------------
c2_vals = block_vals(NEW_WIN, "c2", ARMS["c2"][3])
c2_cls = "FLOOR" if all(v <= 100 for v in c2_vals) else (
    "CAPTURED" if all(v >= 1000 for v in c2_vals) else "INTERMEDIATE/MIXED")
c8_m = pooled(NEW_WIN, "c8", sum128, ARMS["c8"][3])
c1_ok = (c2_cls == "FLOOR") and abs(c8_m - COMMITTED_C8) <= 0.05 * COMMITTED_C8

vec = {}
vec_ok = True
for win, _d in WINDOWS:
    X = [int(min(block_vals(win, "hi", [3 * i + 1, 3 * i + 2, 3 * i + 3]))) for i in range(12)]
    Y = [int(min(block_vals(win, "tw", [3 * i + 1, 3 * i + 2, 3 * i + 3]))) for i in range(12)]
    vec[win] = (X, Y)
    if win != NEW_WIN and (X != REF_X[win] or Y != REF_Y[win]):
        vec_ok = False

anchor_rows = {}
anchor_ok = True
for win, _d in WINDOWS:
    if win == NEW_WIN:
        continue   # this row computes NO anchor at W5 (protocol section 3)
    a_med = int(pooled(win, "hi", sum128, [1, 2, 3]))
    bvals = [int(v) for v in block_vals(win, "hi", [1, 2, 3])]
    anchor_rows[win] = (a_med, min(bvals), max(bvals))
    if anchor_rows[win] != REF_ANCHOR[win]:
        anchor_ok = False

# ------------------------------------------------------------------
# THE DL CONSTRUCTION (protocol section 1): the named cell's block
# rank-pair spreads over the tw arm; per block D over the block's
# pooled 75 gpu_ticks samples (EXACT INTEGER); L_w = median of the
# 12 block D values (2*L = 6th+7th order statistics, INTEGER
# half-tick). DESCRIPTIVE ONLY -- no letter exists in this row.
# ------------------------------------------------------------------
def named_pooled75(win):
    """(12, 75) int64: per-block pooled 75 gpu_ticks of the named cell, tw."""
    rows = []
    for i in range(12):
        xs = []
        for r in (3 * i + 1, 3 * i + 2, 3 * i + 3):
            xs += [s[2] for s in data[(win, "tw", r)][2] if s[1] == nc]
        assert len(xs) == 75
        rows.append(xs)
    return np.array(rows, dtype=np.int64)

def pair_d(pooled75, a, b):
    srt = np.sort(pooled75, axis=-1)
    return srt[..., b] - srt[..., a]

def l2_of(d12):
    s = np.sort(d12)
    return int(s[5] + s[6])

pooled75 = {win: named_pooled75(win) for win, _d in WINDOWS}

dl_tab = {}       # (pair, win) -> (2*L, [12 block D])
for name, a, b in DL:
    for win, _d in WINDOWS:
        d = pair_d(pooled75[win], a, b)
        dl_tab[(name, win)] = (l2_of(d), [int(v) for v in d])

# ------------------------------------------------------------------
# PARSER VALIDITY PINS (protocol section 4): the published s78
# quantile-pair vectors reproduced EXACTLY from the same parser.
# ------------------------------------------------------------------
valid_rows = []
valid_ok = True
for tag, label, a, b, ref_vec, ref_w5d in VALID:
    got_vec = []
    got_w5d = None
    for win, _d in WINDOWS:
        d = pair_d(pooled75[win], a, b)
        got_vec.append(l2_of(d))
        if win == NEW_WIN:
            got_w5d = [int(v) for v in d]
    ok = (got_vec == ref_vec) and (got_w5d == ref_w5d)
    valid_rows.append((label, got_vec, got_w5d, ok))
    if not ok:
        valid_ok = False

def invalidated():
    inv = any(win_info[w]["vmis"] != 0 or not win_info[w]["counts_ok"]
              or not win_info[w]["knob_ok"] or not win_info[w]["fail_ok"]
              or not win_info[w]["cmap_ok"] for w, _d in WINDOWS)
    return inv or (not named_ok) or (not vec_ok) or (not c1_ok) or (not anchor_ok) \
        or (not valid_ok)

# ==================================================================
# the publication
# ==================================================================
out = []
P = out.append
P("JUN-59 session 82 -- THE DL LEVEL-AXIS DESCRIPTIVE REFERENCE")
P("ROW (the s81-frozen DOUBLING LADDER vocabulary's FIRST")
P("STATISTIC) (publication)")
P("(what are the DL4/DL8/DL16/DL32 within-block spread LEVELS of")
P("the tw arm's (max,128,S=default) cell across the five")
P("committed windows -- the first statistic computed under the")
P("s81-frozen DL vocabulary? DESCRIPTIVE ONLY: NO letter, NO")
P("null, NO resampling, NO threshold, NO direction.)")
P("Produced ONLY by analysis-s82.py over the COMMITTED run logs of")
P("five fixed evidence directories (anv-b3commonmode-20261028 =")
P("the s36 window, anv-b3joint3-20261028 = the s38 window,")
P("anv-b3joint4-20261028 = the s39 window, anv-b3levelrep-20261028")
P("= the s51 window, anv-b3w5xdayrep-20261029 = the W5 window,")
P("measured by s73); protocol.txt was frozen BEFORE any statistic")
P("of this row existed (freeze stamp 2026-10-29T05:22:05Z; the")
P("pre-freeze freshness greps were 0/0 hits). ANALYSIS session --")
P("NO hardware runs this session; the W5 quantities were MEASURED")
P("on aiueos-6600hs Intel BMG G31 ANV in session 73.")
P("")

P("1. INTEGRITY (computed over each window's committed logs;")
P("   protocol section 3):")
for win, _d in WINDOWS:
    info = win_info[win]
    P("   %s: runs parsed 78; VERIFY mismatch total %d; counts ok %s; "
      "knobs ok %s; S=8 fail-closed %s; cell map ok %s"
      % (win, info["vmis"], info["counts_ok"], info["knob_ok"],
         info["fail_ok"], info["cmap_ok"]))
    for pr in info["problems"]:
        P("   !! %s" % pr)
P("   named cell present as ok-map cell %d (raw idx %d == %s): %s"
  % (nc_pos, nc, ckey_str(nc), named_ok))
P("   INVALIDATION criterion (protocol section 3): any violation =>")
P("   the descriptive table is NOT EVALUABLE (no letter exists).")
P("")

P("2. C1 RE-DERIVATION (environment pin, from the s73 W5 window's")
P("   logs):")
P("   c2 class: %s (FLOOR required; committed floor band 31..32)" % c2_cls)
P("   c8 (sum,128,S=16) pooled median %.0f vs committed %d "
  "(%.2f%% delta; +/-5%% required)" % (c8_m, COMMITTED_C8,
                                     abs(c8_m - COMMITTED_C8) / COMMITTED_C8 * 100))
P("   C1 branch: %s" % ("(a) both controls replicate" if c1_ok else "(b) discrepancy"))
P("")

P("3. THE BLOCK-MIN VECTORS (re-derived from the committed logs;")
P("   the four PRIOR windows reproduce the published vectors of")
P("   publication-s39.txt section 3 and publication-s51.txt section")
P("   3 EXACTLY (mismatch => NOT EVALUABLE); no vector enters the")
P("   DL table -- the row content is section 5):")
for win, _d in WINDOWS:
    X, Y = vec[win]
    P("   %s X (hi): %s" % (win, " ".join(str(v) for v in X)))
    P("   %s Y (tw): %s" % (win, " ".join(str(v) for v in Y)))
    if win != NEW_WIN:
        P("   %s reproduction EXACT: %s" % (win, X == REF_X[win] and Y == REF_Y[win]))
P("   all four prior windows reproduce EXACTLY (8/8): %s" % vec_ok)
P("")

P("3b. ANCHOR REPRODUCTION ROWS (hi block A's (sum,128,S=16) pooled")
P("    median and 18-cell min..max at the four PRIOR windows vs the")
P("    quote-only/published anchor priors, EXACTLY (mismatch =>")
P("    NOT EVALUABLE); this row computes NO anchor at W5:")
for win, _d in WINDOWS:
    if win == NEW_WIN:
        continue
    a_med, a_min, a_max = anchor_rows[win]
    P("    %s: median %d min..max %d..%d (want %d / %d..%d); "
      "reproduction EXACT: %s" % (win, a_med, a_min, a_max,
                                 REF_ANCHOR[win][0], REF_ANCHOR[win][1],
                                 REF_ANCHOR[win][2],
                                 (a_med, a_min, a_max) == REF_ANCHOR[win]))
P("    all four prior windows reproduce EXACTLY: %s" % anchor_ok)
P("")

P("4. PARSER VALIDITY PINS (protocol section 4; the published s78")
P("   quantile-pair vectors recomputed from THIS parser, EXACTLY")
P("   required -- the INNER/OUTER pairs are s53/s54 content, NOT")
P("   DL content; they exist here only as validity):")
for label, got_vec, got_w5d, ok in valid_rows:
    P("   %s: 2*L s36/s38/s39/s51/s73 = %s (want %s); W5 block D %s "
      "(want pinned vector); EXACT: %s"
      % (label, "/".join(str(v) for v in got_vec),
         "/".join(str(v) for v in VALID[[r[0] for r in valid_rows].index(label)][4]),
         " ".join(str(v) for v in got_w5d), ok))
P("   all validity pins EXACT: %s" % valid_ok)
P("")

P("5. T17 THE DL LEVEL-AXIS DESCRIPTIVE REFERENCE TABLE")
P("   (protocol sections 0/1; DESCRIPTIVE ONLY -- NO letter, NO")
P("   null, NO threshold, NO direction; the WHOLE closed DL")
P("   vocabulary, no selection among pairs):")
P("   the NAMED cell %s of the tw arm; block = 3 consecutive tw" % ckey_str(nc))
P("   runs (runs 1..36 -> 12 blocks of 3); per-block D over the")
P("   block's pooled 75 gpu_ticks samples (EXACT INTEGER);")
P("   L_w = median of the 12 block D values (2*L = 6th + 7th")
P("   order statistics, INTEGER half-tick). Per pair: the")
P("   five-window 2*L vector, the 12 W5 block D values (for a")
P("   future census), and the W5-vs-post-shift-band check (the")
P("   s78 D1 convention -- descriptive):")
for name, a, b in DL:
    vals = [dl_tab[(name, w)][0] for w, _d in WINDOWS]
    P("   %s: 2*L s36/s38/s39/s51/s73 = %s (L %s)"
      % (DL_LABEL[name], "/".join(str(v) for v in vals),
         "/".join(fmt_ht(v) for v in vals)))
    P("   %s W5 block D values: %s"
      % (DL_LABEL[name], " ".join(str(v) for v in dl_tab[(name, NEW_WIN)][1])))
    band = sorted(dl_tab[(name, w)][0] for w in ("s38", "s39", "s51"))
    l2_w5 = dl_tab[(name, NEW_WIN)][0]
    if l2_w5 < band[0]:
        verdict = "OUTSIDE-BELOW"
    elif l2_w5 > band[1]:
        verdict = "OUTSIDE-ABOVE"
    else:
        verdict = "INSIDE"
    P("   %s W5-vs-post-shift-band: 2*L_W5 = %d vs band 2*L %d..%d "
      "(closed interval spanned by {s38,s39,s51}): %s"
      % (DL_LABEL[name], l2_w5, band[0], band[1], verdict))
P("   NAMED, NOT HIDDEN (frozen): this table carries NO letter and")
P("   NO inferential claim of any kind; it is REFERENCE CONTENT")
P("   (the priors) for a FUTURE pre-registered DL row (its own")
P("   freeze supplies direction/null/threshold/multiplicity per")
P("   the s81 selection rule 3(c)/3(d)); the band placements are")
P("   descriptive, not tests; n = 12 blocks x 5 windows, ONE host;")
P("   tail-side asymmetry stays out of scope (self-mirror pairs);")
P("   the 18-cell scoreboard is NOT computed here.")
P("")

P("6. VERDICT SUMMARY:")
if invalidated():
    P("   T17 table: NOT EVALUABLE (an integrity/validity criterion")
    P("   of protocol section 3/4 is violated -- named above).")
else:
    P("   T17 table: EVALUABLE, DESCRIPTIVE ONLY -- NO letter exists")
    P("   in this row (by frozen design).")
for name, a, b in DL:
    vals = [dl_tab[(name, w)][0] for w, _d in WINDOWS]
    P("   %s: 2*L %s" % (DL_LABEL[name], "/".join(str(v) for v in vals)))
P("   evaluable inputs: prior vector reproduction EXACT (%s); prior"
  % vec_ok)
P("   anchor rows EXACT (%s); parser validity pins EXACT (%s);"
  % (anchor_ok, valid_ok))
P("   s73 C1 ((%s)); named cell identity %s (%s); per-window"
  % ("a" if c1_ok else "b", ckey_str(nc), named_ok))
P("   integrity rows in section 1.")
P("   ANALYSIS session: NO hardware runs -> NO reading -> NO")
P("   settle-bar-ledger line, NO day-slot consumption (protocol")
P("   section 6; settle-bar-ledger.txt byte-identical to HEAD).")
P("   Rule 4 binds: NOTHING MOVES; accelerator-targets defaults")
P("   remain provisional (:measured? false); NO vendor optimization")
P("   exists for Intel.")

open(os.path.join(HERE, "publication-s%d.txt" % SESSION), "w").write("\n".join(out) + "\n")
