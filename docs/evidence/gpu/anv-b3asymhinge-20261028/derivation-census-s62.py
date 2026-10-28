#!/usr/bin/env python3
"""JUN-59 session 62 derivation census -- INDEPENDENT second parser
for publication-s62.txt (the non-ladder asymmetric HX rank-pair
spread-compression probe).

Independence contract (protocol.txt section 6):
- NO regex, NO re module: all run-log parsing is split()-based
  k=v tokenising; all publication parsing is find/split-based.
- NO numpy: every order statistic is a pure-Python sorted() index
  over the SAME pooled 75 (block HXL spread = sorted(pooled75)
  [56] - sorted(pooled75)[0]; block HXR spread =
  sorted(pooled75)[74] - sorted(pooled75)[18]; 2*L = sorted(ds)
  [5] + sorted(ds)[6]).
- The resampling is an independent pure-Python shuffle loop that
  re-implements the frozen RNG call contract exactly (one
  random.Random(2026102812); per contrast 20,000 fresh
  list(range(72)) shuffles in the frozen probe order (s36,s38),
  (s36,s39), (s36,s51); pseudo-windows = first/last 36 draws,
  12 blocks of 3 consecutive draws; BOTH axes computed on the
  SAME pseudo-blocks; ONE-SIDED count C* >= C_obs per axis).

This script re-derives every published integer, count, p value and
letter of publication-s62.txt from the committed run logs, checks
the gate pins, bar pins and evidence hygiene, and prints a row
table. Deterministic: running it twice yields byte-identical
output.
"""
import os, random, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
PUB = os.path.join(HERE, "publication-s62.txt")
WINDOWS = [("s36", "anv-b3commonmode-20261028"),
           ("s38", "anv-b3joint3-20261028"),
           ("s39", "anv-b3joint4-20261028"),
           ("s51", "anv-b3levelrep-20261028")]
ARMS = {"c2": (2, 1, 1, [1, 2, 3]),
        "hi": (3, 1024, 4033, list(range(1, 37))),
        "tw": (3, 2048, 8066, list(range(1, 37))),
        "c8": (8, 1, 1, [1, 2, 3])}
TRIALS = 20000
SEED = 2026102812
COMMITTED_C8 = 32915
NAMED_CKEY = ("max", 128, "default")
PAIRS = [("s36", "s38"), ("s36", "s39"), ("s36", "s51")]
AXES = ["HXL", "HXR"]
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
    return s[56] - s[0], s[74] - s[18]

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

# ---- section 4: the six HX spread-compression contrasts ----
# ---- (independent resampling) ----
runs_by_win = {w: named_runs(w) for w, _d in WINDOWS}

def obs_contrast(wa, wb):
    ds_l, ds_r = [], []
    for w in (wa, wb):
        blk_l, blk_r = [], []
        for i in range(12):
            vals = []
            for r in range(3 * i, 3 * i + 3):
                vals += runs_by_win[w][r]
            dl, dr = block_pair(vals)
            blk_l.append(dl)
            blk_r.append(dr)
        ds_l.append(blk_l)
        ds_r.append(blk_r)
    ll_a, ll_b = l2_of(ds_l[0]), l2_of(ds_l[1])
    lr_a, lr_b = l2_of(ds_r[0]), l2_of(ds_r[1])
    return {"HXL": (ll_a, ll_b, ll_a - ll_b),
            "HXR": (lr_a, lr_b, lr_a - lr_b)}

rng = random.Random(SEED)
joint_letters = []
for wa, wb in PAIRS:
    obs = obs_contrast(wa, wb)
    flat = runs_by_win[wa] + runs_by_win[wb]
    cnt = {"HXL": 0, "HXR": 0}
    for _t in range(TRIALS):
        perm = list(range(72))
        rng.shuffle(perm)
        pl_a, pl_b, pr_a, pr_b = [], [], [], []
        for i in range(12):
            va, vb = [], []
            for j in range(3):
                va += flat[perm[3 * i + j]]
                vb += flat[perm[36 + 3 * i + j]]
            dl_a, dr_a = block_pair(va)
            dl_b, dr_b = block_pair(vb)
            pl_a.append(dl_a)
            pl_b.append(dl_b)
            pr_a.append(dr_a)
            pr_b.append(dr_b)
        c_l_star = l2_of(pl_a) - l2_of(pl_b)
        c_r_star = l2_of(pr_a) - l2_of(pr_b)
        if c_l_star >= obs["HXL"][2]:
            cnt["HXL"] += 1
        if c_r_star >= obs["HXR"][2]:
            cnt["HXR"] += 1
    for ax in AXES:
        la, lb, c_obs = obs[ax]
        pval = (1 + cnt[ax]) / (1 + TRIALS)
        letter = ("(a) HXPAIR-ASYMMETRIC-SPREAD-COMPRESSION-DIFFERENT"
                  if (c_obs > 0 and pval <= 0.05)
                  else "(b) NOT-DIFFERENT [EXACTLY-ZERO]" if c_obs == 0
                  else "(b) NOT-DIFFERENT [OPPOSITE-DIRECTION]" if c_obs < 0
                  else "(b) NOT-DIFFERENT [NONZERO-NOT-SIGNIFICANT]")
        joint_letters.append(letter)
        l = find_line(f"   {wa}-vs-{wb} {ax}: ")
        rec(f"sec4 {wa}-vs-{wb} {ax} 2*L_{wa}", int(l.split("2*L_" + wa + " = ")[1].split(" ")[0]), la)
        rec(f"sec4 {wa}-vs-{wb} {ax} 2*L_{wb}", int(l.split("2*L_" + wb + " = ")[1].split(" ")[0]), lb)
        rec(f"sec4 {wa}-vs-{wb} {ax} 2*C_obs", int(l.split("2*C_obs = ")[1].split(" ")[0]), c_obs)
        rec(f"sec4 {wa}-vs-{wb} {ax} count", int(l.split("count ")[1].split(" ")[0]), cnt[ax])
        rec(f"sec4 {wa}-vs-{wb} {ax} p", l.split("p = ")[1].split(";")[0], f"{pval:.6f}")
        rec(f"sec4 {wa}-vs-{wb} {ax} letter", l.split("contrast letter ")[1], letter)

# joint letter re-derivation (no D1 prior check -- fresh prediction)
if not (all(win_info[w][0] == 0 and win_info[w][1] and win_info[w][2]
            and win_info[w][3] and win_info[w][4] for w, _d in WINDOWS)
        and vec_ok and anchor_ok and all(c1_rec.values())):
    t_rec = "(c) NOT EVALUABLE"
elif not all(l.startswith("(a)") for l in joint_letters):
    t_rec = "(b) NOT-HXPAIR-ASYMMETRIC-SPREAD-COMPRESSION-CONSISTENT"
else:
    t_rec = "(a) HXPAIR-ASYMMETRIC-SPREAD-COMPRESSION-CONSISTENT"
for occ, sec in ((0, "sec4"), (1, "sec7")):
    l = find_line("   T12 = ", occ)
    phrase = l.split("T12 = ")[1].split(" (named")[0].strip()
    rec(f"{sec} joint T12", phrase, t_rec)

# ---- section 6 D1: per-window per-axis HX block D values + 2*L ----
d1_rec = {}
for win, _d in WINDOWS:
    blk_l, blk_r = [], []
    for i in range(12):
        vals = []
        for r in range(3 * i, 3 * i + 3):
            vals += runs_by_win[win][r]
        dl, dr = block_pair(vals)
        blk_l.append(dl)
        blk_r.append(dr)
    ll, lr = l2_of(blk_l), l2_of(blk_r)
    d1_rec[win] = (blk_l, blk_r, ll, lr)
    for ax, blk, l2 in (("HXL", blk_l, ll), ("HXR", blk_r, lr)):
        l = find_line(f"      {win} {ax}: ")
        rec(f"D1 {win} {ax} 2*L", int(l.split("2*L = ")[1].split(" ")[0]), l2)
        rec(f"D1 {win} {ax} block D values", l.split("block D values: ")[1],
            " ".join(str(v) for v in blk))

# ---- section 6 D3: 18-cell s36-vs-s51 HX level table ----
d3 = {}
for win in ("s36", "s51"):
    col_l = [[] for _ in ok_cells]
    col_r = [[] for _ in ok_cells]
    for i in range(12):
        per = [[] for _ in ok_cells]
        for r in range(3 * i, 3 * i + 3):
            for s in data[(win, "tw", r + 1)][2]:
                per[cell_pos[s[1]]].append(s[2])
        for ci in range(len(ok_cells)):
            dl, dr = block_pair(per[ci])
            col_l[ci].append(dl)
            col_r[ci].append(dr)
    d3[win] = ([l2_of(c) for c in col_l], [l2_of(c) for c in col_r])
for ci, k in enumerate(ok_cells):
    l = find_line(f"      tw cell {ckey_str(k)}: ")
    pub_l = l.split("HXL 2*L ")[1].split(" ")[0]
    pub_r = l.split("HXR 2*L ")[1].split(" ")[0]
    pub_c = l.split("(C_HXL ")[1]
    l36, l51 = d3["s36"][0][ci], d3["s51"][0][ci]
    r36, r51 = d3["s36"][1][ci], d3["s51"][1][ci]
    rec(f"D3 {ckey_str(k)} HXL 2*L pair", pub_l, f"{l36}/{l51}")
    rec(f"D3 {ckey_str(k)} HXR 2*L pair", pub_r, f"{r36}/{r51}")
    rec(f"D3 {ckey_str(k)} C tuple", pub_c,
        f"{(l36 - l51) / 2:.1f}, C_HXR {(r36 - r51) / 2:.1f})")

# ------------------------------------------------------------------
# gate pins, bar pins, evidence hygiene
# ------------------------------------------------------------------
gp = os.path.join(ROOT, "docs", "evidence", "gpu", "anv-b3asymhinge-20261028")
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
bar_t = read("bar-eval-s62.txt")
rec("bar verdict pinned", "VERDICT: PENDING 1/4" in bar_t, True)
rec("bar self-test pinned", "TOTAL: 38 assertions passed, 0 failed" in bar_t, True)
ledger_lines = open(os.path.join(ROOT, "docs", "evidence", "gpu",
                                 "settle-bar-ledger.txt")).read().splitlines()
reading_lines = [l for l in ledger_lines if l.startswith("day=")]
rec("ledger reading-line count", 8, len(reading_lines))
rec("ledger has no s62 line", any("session=s62" in l for l in reading_lines), False)
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
out.append("JUN-59 session 62 derivation census -- independent second")
out.append("parser for publication-s62.txt (the non-ladder asymmetric")
out.append("HX rank-pair spread-compression probe; split-based parsing,")
out.append("no re module, no numpy; pure-Python sorted() order")
out.append("statistics from ONE shared sort per pooled 75 (D_L =")
out.append("sorted(pooled75)[56] - sorted(pooled75)[0]; D_R =")
out.append("sorted(pooled75)[74] - sorted(pooled75)[18]); independent")
out.append("pure-Python shuffle loop re-implementing the frozen RNG")
out.append("contract random.Random(2026102812) consumed in the frozen")
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
open(os.path.join(HERE, "derivation-census-s62.txt"), "w").write("\n".join(out) + "\n")
print(f"TOTAL: {len(rows)} rows, {mismatched} mismatched")
