#!/usr/bin/env python3
"""JUN-59 session 56 derivation census -- INDEPENDENT second parser
for publication-s56.txt (the second named rank-pair set
compression-profile read).

Independence contract (protocol.txt section 6):
- NO regex, NO re module: all run-log parsing is split()-based
  k=v tokenising; all publication parsing is find/split-based.
- NO numpy: every order statistic is a pure-Python sorted() index
  over the SAME pooled 75 (block outer2 spread = sorted(pooled75)
  [70] - sorted(pooled75)[4]; block inner2 spread =
  sorted(pooled75)[42] - sorted(pooled75)[32]; 2*L = sorted(ds)
  [5] + sorted(ds)[6]).
- The resampling is an independent pure-Python shuffle loop that
  re-implements the frozen RNG call contract exactly (one
  random.Random(2026102806); per contrast 20,000 fresh
  list(range(72)) shuffles in the frozen probe order (s36,s38),
  (s36,s39), (s36,s51); pseudo-windows = first/last 36 draws,
  12 blocks of 3 consecutive draws; BOTH axes computed on the
  SAME pseudo-blocks; ONE-SIDED count P2* >= P2_obs).

This script re-derives every published integer, count, p value and
letter of publication-s56.txt from the committed run logs, checks
the gate pins, bar pins and evidence hygiene, and prints a row
table. Deterministic: running it twice yields byte-identical
output.
"""
import os, random, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
PUB = os.path.join(HERE, "publication-s56.txt")
WINDOWS = [("s36", "anv-b3commonmode-20261028"),
           ("s38", "anv-b3joint3-20261028"),
           ("s39", "anv-b3joint4-20261028"),
           ("s51", "anv-b3levelrep-20261028")]
ARMS = {"c2": (2, 1, 1, [1, 2, 3]),
        "hi": (3, 1024, 4033, list(range(1, 37))),
        "tw": (3, 2048, 8066, list(range(1, 37))),
        "c8": (8, 1, 1, [1, 2, 3])}
TRIALS = 20000
SEED = 2026102806
COMMITTED_C8 = 32915
NAMED_CKEY = ("max", 128, "default")
PAIRS = [("s36", "s38"), ("s36", "s39"), ("s36", "s51")]
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

# ------------------------------------------------------------------
# independent split-based run-log parser (no regex)
# ------------------------------------------------------------------
def kv(tokens):
    d = {}
    for t in tokens:
        if "=" in t:
            k, v = t.split("=", 1)
            d[k] = v
    return d

def load(path):
    cells, verifies, samples = {}, [], []
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("CELL "):
            d = kv(line.split())
            cells[int(d["idx"])] = dict(op=d["op"], wg=int(d["wg"]),
                                        forced=d["forced"],
                                        pipeline=d["pipeline"], void=d["void"])
        elif line.startswith("VERIFY "):
            d = kv(line.split())
            verifies.append((int(d["idx"]), int(d["checked"]), int(d["mismatch"])))
        elif line.startswith("SAMPLE "):
            d = kv(line.split())
            samples.append((int(d["round"]), int(d["idx"]), int(d["gpu_ticks"]),
                            (int(d["batch"]), int(d["work_mul"]), int(d["ndiv"]))))
    return cells, verifies, samples

data = {}
win_info = {}
ref_cellmap = None
for win, dirname in WINDOWS:
    src = os.path.join(ROOT, "docs", "evidence", "gpu", dirname)
    vmis = 0
    counts_ok = knob_ok = fail_ok = cmap_ok = True
    for tag in ("c2", "hi", "tw", "c8"):
        b, wm, dd, runs = ARMS[tag]
        for r in runs:
            fn = os.path.join(src, f"run-{tag}-r{r}.txt")
            cells, verifies, samples = load(fn)
            data[(win, tag, r)] = (cells, verifies, samples)
            for (_i, _c, mis) in verifies:
                vmis += mis
            okc = [k for k, v in cells.items() if v["pipeline"] == "ok"]
            s8 = [k for k, v in cells.items() if v["forced"] == "8"]
            if len(s8) != 6 or any(cells[k]["pipeline"] != "FAIL" or cells[k]["void"] != "1"
                                   for k in s8):
                fail_ok = False
            if len(samples) != len(okc) * 25 or len(verifies) != 24:
                counts_ok = False
            for (_rnd, _idx, _gt, knobs) in samples:
                if knobs != (b, wm, dd):
                    knob_ok = False
            cmap = tuple(sorted((k, v["op"], v["wg"], v["forced"], v["pipeline"], v["void"])
                                for k, v in cells.items()))
            if ref_cellmap is None:
                ref_cellmap = cmap
            elif cmap != ref_cellmap:
                cmap_ok = False
    win_info[win] = (vmis, counts_ok, knob_ok, fail_ok, cmap_ok)

ok_cells = sorted([k for k, v in data[("s51", "c2", 1)][0].items() if v["pipeline"] == "ok"])
cell_pos = {k: i for i, k in enumerate(ok_cells)}

def ckey(idx):
    c = data[("s51", "c2", 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])

def ckey_str(idx):
    op, wg, s = ckey(idx)
    return f"({op},{wg},S={s})"

sum128 = [k for k in ok_cells if ckey(k) == ("sum", 128, "16")][0]
nc = [k for k in ok_cells if ckey(k) == NAMED_CKEY][0]

def pooled(win, tag, idx, runs):
    xs = []
    for r in runs:
        xs += [s[2] for s in data[(win, tag, r)][2] if s[1] == idx]
    return statistics.median(xs)

def block_vals(win, tag, runs):
    return [pooled(win, tag, k, runs) for k in ok_cells]

# independent pure-Python order statistics (no numpy; ONE shared
# sort per pooled 75 yields BOTH axes)
def block_pair(vals75):
    s = sorted(vals75)
    return s[70] - s[4], s[42] - s[32]

def l2_of(ds12):
    s = sorted(ds12)
    return s[5] + s[6]

def named_runs(win):
    """the 36 runs of the named cell: list of 36 lists of 25."""
    out = []
    for r in range(1, 37):
        out.append([s[2] for s in data[(win, "tw", r)][2] if s[1] == nc])
    return out

# ------------------------------------------------------------------
# independent publication reader (find/split, no regex)
# ------------------------------------------------------------------
pub_text = open(PUB).read()
pub_lines = pub_text.split("\n")
rows = []

def rec(label, pub, recomputed):
    rows.append((label, str(pub), str(recomputed), str(pub) == str(recomputed)))

def find_line(prefix, occurrence=0):
    hits = [l for l in pub_lines if l.startswith(prefix)]
    assert len(hits) > occurrence, (prefix, occurrence)
    return hits[occurrence]

# ---- section 1: integrity ----
for win, _d in WINDOWS:
    l = find_line(f"   {win}: runs parsed ")
    parts = l.split("; ")
    vmis_pub = int(parts[1].split("total ")[1])
    rec(f"sec1 {win} VERIFY mismatch total", vmis_pub, win_info[win][0])
    flags_pub = [p.split(" ")[-1] for p in parts[2:]]
    flags_rec = [str(win_info[win][1]), str(win_info[win][2]),
                 str(win_info[win][3]), str(win_info[win][4])]
    rec(f"sec1 {win} four integrity flags", " ".join(flags_pub), " ".join(flags_rec))

# ---- section 2: C1 ----
c1_rec = {}
for win, _d in WINDOWS:
    l = find_line(f"   {win}: c2 class ")
    cls_pub = l.split("c2 class ")[1].split(" ")[0]
    med_pub = int(l.split("pooled median ")[1].split(" ")[0])
    delta_pub = float(l.split("% delta")[0].split("(")[-1])
    c2_vals = block_vals(win, "c2", ARMS["c2"][3])
    cls_rec = "FLOOR" if all(v <= 100 for v in c2_vals) else (
        "CAPTURED" if all(v >= 1000 for v in c2_vals) else "INTERMEDIATE/MIXED")
    c8_m = pooled(win, "c8", sum128, ARMS["c8"][3])
    delta_rec = abs(c8_m - COMMITTED_C8) / COMMITTED_C8 * 100
    rec(f"sec2 {win} c2 class", cls_pub, cls_rec)
    rec(f"sec2 {win} c8 median", med_pub, int(c8_m))
    rec(f"sec2 {win} c8 delta pct", f"{delta_pub:.2f}", f"{delta_rec:.2f}")
    c1_rec[win] = (cls_rec == "FLOOR") and abs(c8_m - COMMITTED_C8) <= 0.05 * COMMITTED_C8

# ---- sections 3/3b: vectors and anchor rows ----
vec_ok = True
anchor_ok = True
for win, _d in WINDOWS:
    X = [int(min(block_vals(win, "hi", [3 * i + 1, 3 * i + 2, 3 * i + 3]))) for i in range(12)]
    Y = [int(min(block_vals(win, "tw", [3 * i + 1, 3 * i + 2, 3 * i + 3]))) for i in range(12)]
    lx = find_line(f"   {win} X (hi): ").split(": ")[1].split(" ")
    ly = find_line(f"   {win} Y (tw): ").split(": ")[1].split(" ")
    rec(f"sec3 {win} X vector", " ".join(lx), " ".join(str(v) for v in X))
    rec(f"sec3 {win} Y vector", " ".join(ly), " ".join(str(v) for v in Y))
    rec(f"sec3 {win} reproduction flag",
        find_line(f"   {win} reproduction EXACT: ").split(": ")[1],
        str(X == REF_X[win] and Y == REF_Y[win]))
    if X != REF_X[win] or Y != REF_Y[win]:
        vec_ok = False
    a_med = pooled(win, "hi", sum128, [1, 2, 3])
    bvals = [int(v) for v in block_vals(win, "hi", [1, 2, 3])]
    a_min, a_max = min(bvals), max(bvals)
    l = find_line(f"    {win}: median ")
    med_pub = int(l.split("median ")[1].split(" ")[0])
    rng_pub = l.split("min..max ")[1].split(" ")[0]
    flag_pub = l.split("reproduction EXACT: ")[1]
    rec(f"sec3b {win} anchor median", med_pub, int(a_med))
    rec(f"sec3b {win} anchor min..max", rng_pub, f"{a_min}..{a_max}")
    rec(f"sec3b {win} reproduction flag", flag_pub,
        str((a_med, a_min, a_max) == REF_ANCHOR[win]))
    if (a_med, a_min, a_max) != REF_ANCHOR[win]:
        anchor_ok = False

# ---- section 4: the three second-pair profile contrasts ----
# ---- (independent resampling) ----
runs_by_win = {w: named_runs(w) for w, _d in WINDOWS}

def obs_contrast(wa, wb):
    ds_o, ds_i = [], []
    for w in (wa, wb):
        blk_o, blk_i = [], []
        for i in range(12):
            vals = []
            for r in range(3 * i, 3 * i + 3):
                vals += runs_by_win[w][r]
            do, di = block_pair(vals)
            blk_o.append(do)
            blk_i.append(di)
        ds_o.append(blk_o)
        ds_i.append(blk_i)
    lo_a, lo_b = l2_of(ds_o[0]), l2_of(ds_o[1])
    li_a, li_b = l2_of(ds_i[0]), l2_of(ds_i[1])
    c_out = lo_a - lo_b
    c_in = li_a - li_b
    return lo_a, lo_b, li_a, li_b, c_out, c_in, c_out - c_in

rng = random.Random(SEED)
joint_letters = []
for wa, wb in PAIRS:
    lo_a, lo_b, li_a, li_b, c_out, c_in, p_obs = obs_contrast(wa, wb)
    flat = runs_by_win[wa] + runs_by_win[wb]
    cnt = 0
    for _t in range(TRIALS):
        perm = list(range(72))
        rng.shuffle(perm)
        po_a, po_b, pi_a, pi_b = [], [], [], []
        for i in range(12):
            va, vb = [], []
            for j in range(3):
                va += flat[perm[3 * i + j]]
                vb += flat[perm[36 + 3 * i + j]]
            do_a, di_a = block_pair(va)
            do_b, di_b = block_pair(vb)
            po_a.append(do_a)
            po_b.append(do_b)
            pi_a.append(di_a)
            pi_b.append(di_b)
        p = ((l2_of(po_a) - l2_of(po_b)) - (l2_of(pi_a) - l2_of(pi_b)))
        if p >= p_obs:
            cnt += 1
    pval = (1 + cnt) / (1 + TRIALS)
    letter = ("(a) SECONDPAIR-OUTER-WEIGHTED-DIFFERENT" if (p_obs > 0 and pval <= 0.05)
              else "(b) NOT-DIFFERENT [EXACTLY-ZERO]" if p_obs == 0
              else "(b) NOT-DIFFERENT [OPPOSITE-DIRECTION]" if p_obs < 0
              else "(b) NOT-DIFFERENT [NONZERO-NOT-SIGNIFICANT]")
    joint_letters.append(letter)
    l = find_line(f"   {wa}-vs-{wb}: ", 0)
    pa = l.split("2*L_" + wa + " = ")   # [1] = OUT2 occurrence, [2] = IN2 occurrence
    pb = l.split("2*L_" + wb + " = ")
    rec(f"sec4 {wa}-vs-{wb} OUT2 2*L_{wa}", int(pa[1].split(" ")[0]), lo_a)
    rec(f"sec4 {wa}-vs-{wb} OUT2 2*L_{wb}", int(pb[1].split(" ")[0]), lo_b)
    rec(f"sec4 {wa}-vs-{wb} 2*C_out2", int(l.split("2*C_out2 = ")[1].split(";")[0]), c_out)
    rec(f"sec4 {wa}-vs-{wb} IN2 2*L_{wa}", int(pa[2].split(" ")[0]), li_a)
    rec(f"sec4 {wa}-vs-{wb} IN2 2*L_{wb}", int(pb[2].split(" ")[0]), li_b)
    rec(f"sec4 {wa}-vs-{wb} 2*C_in2", int(l.split("2*C_in2 = ")[1].split(";")[0]), c_in)
    rec(f"sec4 {wa}-vs-{wb} 2*P2_obs", int(l.split("2*P2_obs = ")[1].split(" ")[0]), p_obs)
    rec(f"sec4 {wa}-vs-{wb} count", int(l.split("count ")[1].split(" ")[0]), cnt)
    rec(f"sec4 {wa}-vs-{wb} p", l.split("p = ")[1].split(";")[0], f"{pval:.6f}")
    rec(f"sec4 {wa}-vs-{wb} letter", l.split("contrast letter ")[1], letter)

# joint letter re-derivation
if not (all(win_info[w][0] == 0 and win_info[w][1] and win_info[w][2]
            and win_info[w][3] and win_info[w][4] for w, _d in WINDOWS)
        and vec_ok and anchor_ok and all(c1_rec.values())):
    t6_rec = "(c) NOT EVALUABLE"
elif not all(l.startswith("(a)") for l in joint_letters):
    t6_rec = "(b) NOT-SECONDPAIR-PROFILE-OUTER-WEIGHTED-CONSISTENT"
else:
    t6_rec = "(a) SECONDPAIR-PROFILE-OUTER-WEIGHTED-CONSISTENT"
for occ, sec in ((0, "sec4"), (1, "sec7")):
    l = find_line("   T6 = ", occ)
    phrase = l.split("T6 = ")[1].split(" (named")[0].strip()
    rec(f"{sec} joint T6", phrase, t6_rec)

# ---- section 6 D1: per-window per-axis second-pair block D ----
# ---- values + 2*L + profile2 level ----
for win, _d in WINDOWS:
    blk_o, blk_i = [], []
    for i in range(12):
        vals = []
        for r in range(3 * i, 3 * i + 3):
            vals += runs_by_win[win][r]
        do, di = block_pair(vals)
        blk_o.append(do)
        blk_i.append(di)
    lo, li = l2_of(blk_o), l2_of(blk_i)
    l = find_line(f"      {win} OUT2: ")
    rec(f"D1 {win} OUT2 2*L", int(l.split("2*L = ")[1].split(" ")[0]), lo)
    rec(f"D1 {win} OUT2 block D values", l.split("block D values: ")[1],
        " ".join(str(v) for v in blk_o))
    l = find_line(f"      {win} IN2: ")
    rec(f"D1 {win} IN2 2*L", int(l.split("2*L = ")[1].split(" ")[0]), li)
    rec(f"D1 {win} IN2 block D values", l.split("block D values: ")[1],
        " ".join(str(v) for v in blk_i))
    l = find_line(f"      {win} PROFILE2: ")
    rec(f"D1 {win} PROFILE2 level", int(l.split("= ")[1].split(" ")[0]), lo - li)

# ---- section 6 D3: 18-cell s36-vs-s51 second-pair profile table ----
d3 = {}
for win in ("s36", "s51"):
    col_o = [[] for _ in ok_cells]
    col_i = [[] for _ in ok_cells]
    for i in range(12):
        per = [[] for _ in ok_cells]
        for r in range(3 * i, 3 * i + 3):
            for s in data[(win, "tw", r + 1)][2]:
                per[cell_pos[s[1]]].append(s[2])
        for ci in range(len(ok_cells)):
            do, di = block_pair(per[ci])
            col_o[ci].append(do)
            col_i[ci].append(di)
    d3[win] = ([l2_of(c) for c in col_o], [l2_of(c) for c in col_i])
for ci, k in enumerate(ok_cells):
    l = find_line(f"      tw cell {ckey_str(k)}: ")
    pub_o = l.split("OUT2 2*L ")[1].split(" ")[0]
    pub_i = l.split("IN2 2*L ")[1].split(" ")[0]
    pub_p = l.split("P2 (C_out2 ")[1]
    o36, o51 = d3["s36"][0][ci], d3["s51"][0][ci]
    i36, i51 = d3["s36"][1][ci], d3["s51"][1][ci]
    rec(f"D3 {ckey_str(k)} OUT2 2*L pair", pub_o, f"{o36}/{o51}")
    rec(f"D3 {ckey_str(k)} IN2 2*L pair", pub_i, f"{i36}/{i51}")
    rec(f"D3 {ckey_str(k)} P2 tuple", pub_p,
        f"{(o36 - o51) / 2:.1f}, C_in2 {(i36 - i51) / 2:.1f}, "
        f"P2 {((o36 - o51) - (i36 - i51)) / 2:.1f})")

# ------------------------------------------------------------------
# gate pins, bar pins, evidence hygiene
# ------------------------------------------------------------------
gp = os.path.join(ROOT, "docs", "evidence", "gpu", "anv-b3pair2profile-20261028")
def read(fn):
    return open(os.path.join(gp, fn)).read()

cls_last = [l for l in read("classify-selftest.txt").split("\n") if l.strip()][-1]
rec("gate classify self-test last line", cls_last,
    "TOTAL: 2649 assertions passed, 0 failed")
for fn in ("gate-run1.txt", "gate-run2.txt"):
    t = read(fn)
    rec(f"gate {fn} green line", "Ran 123 tests containing 12162 assertions." in t
        and "0 failures, 0 errors." in t, True)
rec("gate full run-tests named red", "Could not find namespace: kotoba.form"
    in read("gate-full-run-tests.txt"), True)
bar_t = read("bar-eval-s56.txt")
rec("bar verdict pinned", "VERDICT: PENDING 1/4" in bar_t, True)
rec("bar self-test pinned", "TOTAL: 38 assertions passed, 0 failed" in bar_t, True)
ledger_lines = open(os.path.join(ROOT, "docs", "evidence", "gpu",
                                 "settle-bar-ledger.txt")).read().splitlines()
reading_lines = [l for l in ledger_lines if l.startswith("day=")]
rec("ledger reading-line count", 8, len(reading_lines))
rec("ledger has no s56 line", any("session=s56" in l for l in reading_lines), False)
sh_found = []
for dirpath, _dirs, files in os.walk(os.path.join(ROOT, "docs", "evidence", "gpu")):
    for f in files:
        if f.endswith(".sh"):
            sh_found.append(f)
rec("evidence .sh count", len(sh_found), 0)

# ------------------------------------------------------------------
# report
# ------------------------------------------------------------------
out = []
out.append("JUN-59 session 56 derivation census -- independent second")
out.append("parser for publication-s56.txt (split-based parsing, no")
out.append("re module, no numpy; pure-Python sorted() order statistics")
out.append("from ONE shared sort per pooled 75 (D_out2 =")
out.append("sorted(pooled75)[70] - sorted(pooled75)[4]; D_in2 =")
out.append("sorted(pooled75)[42] - sorted(pooled75)[32]); independent")
out.append("pure-Python shuffle loop re-implementing the frozen RNG")
out.append("contract random.Random(2026102806) consumed in the frozen")
out.append("probe order (s36,s38), (s36,s39), (s36,s51), BOTH axes")
out.append("computed on the SAME pseudo-blocks.")
out.append("")
mismatched = 0
for label, pub, recomputed, match in rows:
    if not match:
        mismatched += 1
    out.append(f"{label}: published {pub} | recomputed {recomputed} | match {match}")
out.append("")
out.append(f"TOTAL: {len(rows)} rows, {mismatched} mismatched")
open(os.path.join(HERE, "derivation-census-s56.txt"), "w").write("\n".join(out) + "\n")
print(f"TOTAL: {len(rows)} rows, {mismatched} mismatched")
