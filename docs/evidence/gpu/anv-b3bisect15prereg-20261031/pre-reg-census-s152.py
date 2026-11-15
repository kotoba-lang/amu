#!/usr/bin/env python3
"""s152 fifteenth-cut pre-registration census (run at s153, the s152
NOT DONE (a)) -- re-derive every number the fifteenth-cut
pre-registration cites from COMMITTED bytes only (quote-only content;
this script takes NO measurement of its own), run the D3 round-level
dispersion derivation that fixes the deep-pooling constant R, and
write the instrument variant source (the one-line '#define ROUNDS'
diff of the committed a5e539f0... copy) with its SHA-256 pin.

INPUT RULE (committed bytes only -- a want that does not parse
ABORTS; nothing else is read):
  ../anv-b3bisect13-20261031/run-mid-r01..48.txt   (s139 mid window)
  ../anv-b3bisect13-20261031/run-bis-r01..48.txt   (s139 bis window)
  ../anv-b3bisect14-20261031/run-mid-r01..48.txt   (s147 mid window)
  ../anv-b3bisect13-20261031/gpu-subgroup-reduce-anv-ndiv.c.txt
      (the committed instrument copy, sha256 a5e539f0...)
  ../anv-b3bisect13-20261031/publication-s139.txt  (quote sources)
  ../anv-b3bisect14-20261031/publication-s147.txt  (quote sources)

Pure stdlib. No clock, no RNG, no network, no hardware. Running it
twice yields byte-identical output (the instrument variant it writes
is byte-identical across runs).
"""
import hashlib
import math
import os
import re
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
GPU = os.path.join(HERE, "..")
B13 = os.path.join(GPU, "anv-b3bisect13-20261031")
B14 = os.path.join(GPU, "anv-b3bisect14-20261031")

P139 = open(os.path.join(B13, "publication-s139.txt")).read()
P147 = open(os.path.join(B14, "publication-s147.txt")).read()
INSTR = open(os.path.join(B13, "gpu-subgroup-reduce-anv-ndiv.c.txt")).read()
INSTR_PIN = ("a5e539f0ad1c5d732cda1eaa1cd2abb1aa4d1a66795c09c4ecb35ed2"
             "c3520556")

CELL_RE = re.compile(
    r"^CELL idx=(\d+) spv=(\S+) op=(\S+) wg=(\d+) forced=(\S+) "
    r"probe_size=(-?\d+) probe_nsub=(-?\d+) probe_wg=(-?\d+) "
    r"pipeline=(\S+)")
SAMP_RE = re.compile(
    r"^SAMPLE round=(\d+) idx=(\d+) batch=(\d+) work_mul=(\d+) "
    r"ndiv=(\d+) gpu_ticks=(\d+) ")


def sha256_file(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def parse_run(path):
    cells = {}
    samples = {}
    ncell = nsamp = nver = 0
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("CELL "):
            m = CELL_RE.match(line)
            assert m, f"WANT NOT PARSED: CELL line in {path}"
            idx = int(m.group(1))
            cells[idx] = (m.group(2), m.group(3), int(m.group(4)),
                          m.group(5), int(m.group(6)), int(m.group(7)),
                          int(m.group(8)), m.group(9))
            ncell += 1
        elif line.startswith("SAMPLE "):
            m = SAMP_RE.match(line)
            assert m, f"WANT NOT PARSED: SAMPLE line in {path}"
            samples[(int(m.group(2)), int(m.group(1)))] = (
                int(m.group(6)), int(m.group(3)), int(m.group(4)),
                int(m.group(5)))
            nsamp += 1
        elif line.startswith("VERIFY "):
            nver += 1
    ok = tuple(sorted(i for i, c in cells.items() if c[7] == "ok"))
    assert ncell == 24, f"CELL COUNT {ncell} != 24 in {path}"
    assert nsamp == 450, f"SAMPLE COUNT {nsamp} != 450 in {path}"
    assert nver == 24, f"VERIFY COUNT {nver} != 24 in {path}"
    return cells, samples, ok


def load_arm(d, prefix, k):
    runs = []
    for i in range(1, k + 1):
        runs.append(parse_run(os.path.join(d, f"{prefix}-r{i:02d}.txt")))
    return runs


def pooled_median(runs, idx):
    xs = [t for _, s, _ in runs for (i, r), (t, _, _, _) in sorted(s.items())
          if i == idx]
    return statistics.median(xs)


def per_cell_medians(runs, ok):
    return {i: pooled_median(runs, i) for i in ok}


def cell_samples(runs, idx):
    xs = [t for _, s, _ in runs for (i, r), (t, _, _, _) in sorted(s.items())
          if i == idx]
    return xs


out = []
P = out.append
P("pre-reg-census-s152 (run at s153) -- every number the fifteenth-cut")
P("pre-registration cites, re-derived from committed bytes (quote-only;")
P("NO new measurement) + the D3 round-level dispersion derivation that")
P("fixes the deep-pooling constant R + the written instrument variant")
P("source and its SHA-256 pin")
P("INPUT RULE: committed bytes only -- 48 s139 mid + 48 s139 bis + 48")
P("s147 mid run logs, the committed instrument copy (a5e539f0...),")
P("publication-s139.txt, publication-s147.txt. Nothing else is read.")
P("")

# ---- load the three committed 48-run windows ----
mid13 = load_arm(B13, "run-mid", 48)
bis13 = load_arm(B13, "run-bis", 48)
mid14 = load_arm(B14, "run-mid", 48)
ok = mid13[0][2]
assert ok == mid14[0][2] == bis13[0][2], "ok-cell sets identical"
assert ok == (1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15, 17, 18, 19, 21,
              22, 23), "18 pipeline-ok cells"
for cells, _, _ in mid13 + bis13 + mid14:
    assert tuple(sorted(cells)) == tuple(range(24)), "24 CELL lines"
for _, s, _ in mid13 + mid14:
    for (i, r), (t, b, wm, dd) in s.items():
        assert (b, wm, dd) == (3, 248, 973), f"mid knob {b},{wm},{dd}"
for _, s, _ in bis13:
    for (i, r), (t, b, wm, dd) in s.items():
        assert (b, wm, dd) == (3, 316, 1239), f"bis knob {b},{wm},{dd}"
for _, s, _ in mid13 + bis13 + mid14:
    per_cell = {}
    for (i, r), _ in s.items():
        per_cell.setdefault(i, set()).add(r)
    assert len(per_cell) == 18, "18 sampled cells per run"
    for i, rs in per_cell.items():
        assert rs == set(range(25)), f"25 rounds at cell {i}"
P("RUN-LOG INTEGRITY: 144 runs parsed (s139 mid 48 + s139 bis 48 +")
P("   s147 mid 48); 24 CELL / 450 SAMPLE / 24 VERIFY per run; 18")
P("   pipeline-ok cells x 25 rounds = 450 SAMPLE; mid SAMPLE knobs")
P("   (3,248,973), bis SAMPLE knobs (3,316,1239) in every sample.")
P("")


def block_stats(runs, ok):
    """16 blocks of 3 runs: per-cell pooled median over 75 samples;
    returns (minima, argmins, cell13 walk) per block."""
    mins, argmins, c13 = [], [], []
    for j in range(16):
        blk = runs[3 * j:3 * j + 3]
        pm = per_cell_medians(blk, ok)
        mins.append(min(pm.values()))
        argmins.append(min(pm, key=lambda i: (pm[i], i)))
        c13.append(pm[13])
    return mins, argmins, c13


# ---- 1. s150 (1): parse reproduction against committed values ----
m14_min, m14_arg, m14_c13 = block_stats(mid14, ok)
m13_min, m13_arg, m13_c13 = block_stats(mid13, ok)
pm14 = per_cell_medians(mid14, ok)
pm13 = per_cell_medians(mid13, ok)
pbis = per_cell_medians(bis13, ok)
assert m14_min == [992, 1006, 996, 1000, 1002, 993, 1002, 991, 1006,
                   996, 997, 996, 1002, 999, 995, 991], "s147 minima"
assert m13_min == [1003, 1015, 1005, 1006, 997, 998, 1004, 992, 1004,
                   993, 985, 981, 1003, 986, 996, 992], "s139 minima"
assert min(pm14.values()) == 1005, "s147 pooled-48 min"
assert min(pm13.values()) == 1001, "s139 pooled-48 min"
assert min(pbis.values()) == 1005.5, "s139 bis pooled-48 min exact"


def fnum(v):
    return str(int(v)) if float(v).is_integer() else f"{v:.1f}"


def own_rows(text, header):
    i = text.index(header)
    j = text.index("\n\n", i)
    seg = text[i:j]
    blocks = {int(a): (int(b), int(c), int(d)) for a, b, c, d in
              re.findall(r"block(\d+)\s+runs [0-9,]+\s+\(sum,128,16\)\s+"
                         r"(\d+)\s+18-cell\s+(\d+)\.\.(\d+)", seg)}
    pm = re.search(r"pooled-48\s+runs 01\.\.48\s+\(sum,128,16\)\s+"
                   r"(\d+)\s+18-cell\s+(\d+)\.\.(\d+)", seg)
    assert pm, f"WANT NOT PARSED: pooled-48 of {header}"
    return blocks, (int(pm.group(1)), int(pm.group(2)), int(pm.group(3)))


MID147_HDR = ("   mid (B=3, WM=248, NDIV=973, n=254882, 0.764644 nominal "
              "total units):")
MID139_HDR = MID147_HDR
BIS139_HDR = ("   bis (B=3, WM=316, NDIV=1239, n=255045, 0.765133 nominal "
              "total units):")
b147, p147 = own_rows(P147, MID147_HDR)
b139, p139 = own_rows(P139, MID139_HDR)
bbis, pbis_pub = own_rows(P139, BIS139_HDR)
assert len(b147) == len(b139) == len(bbis) == 16, "16 block rows each"
assert pbis_pub[1] == 1006 and round(min(pbis.values())) == 1006, \
    "published 1,006 is the presentation of exact 1,005.5"
assert [b147[k][1] for k in sorted(b147)] == m14_min, \
    "s147 raw == publication-s147.txt block minima"
assert [b139[k][1] for k in sorted(b139)] == m13_min, \
    "s139 raw == publication-s139.txt block minima"
assert (p147[1], p139[1], pbis_pub[1]) == (1005, 1001, 1006), \
    "published pooled-48 minima"
P("1. s150 (1) PARSE REPRODUCTION (committed run-log bytes vs the")
P("   committed publications -- match True on every row):")
P(f"   s147 mid block 18-cell minima: {' '.join(str(v) for v in m14_min)}")
P(f"   match publication-s147.txt section 3: "
  f"{[b147[k][1] for k in sorted(b147)] == m14_min}")
P(f"   s139 mid block 18-cell minima: {' '.join(str(v) for v in m13_min)}")
P(f"   match publication-s139.txt section 3: "
  f"{[b139[k][1] for k in sorted(b139)] == m13_min}")
P(f"   pooled-48 18-cell minima: s147 {int(min(pm14.values()))} (published "
  f"{p147[1]}), s139 {int(min(pm13.values()))} (published {p139[1]}), "
  f"s139 bis {fnum(min(pbis.values()))} exact (published {pbis_pub[1]} -- "
  f"the integer presentation of the exact half-integer, named)")
P("")

# ---- 2. s150 (2): the slow family (corrected label) ----
c13 = mid14[0][0][13]
assert c13 == ("subgroup-reduce-w256-sum.emitted.spv", "sum", 256, "16",
               16, 16, 256, "ok"), "idx 13 label"
for idx in (17, 21):
    assert mid14[0][0][idx][2:7] == (256, "16", 16, 16, 256), \
        f"idx {idx} label"
for idx in (14, 18, 22):
    assert mid14[0][0][idx][2:7] == (256, "32", 32, 8, 256), \
        f"idx {idx} forced=32 label"
assert m14_arg == [21, 13, 17, 21, 13, 13, 13, 13, 21, 21, 17, 17, 13,
                   17, 17, 17], "s147 argmin rotation"
assert min(pm14, key=lambda i: (pm14[i], i)) == 13, "s147 pooled argmin"
assert min(pm13, key=lambda i: (pm13[i], i)) == 13, "s139 pooled argmin"
slow = (13, 17, 21)


def next_band(pm):
    """The middle family: cluster the 18 pooled-48 medians where
    successive gaps exceed 100 ticks (the slow / next / fast families
    separate by >= 117 ticks); return the cluster just above slow."""
    order = sorted(pm, key=lambda i: (pm[i], i))
    clusters = [[order[0]]]
    for i in order[1:]:
        if pm[i] - pm[clusters[-1][-1]] > 100:
            clusters.append([])
        clusters[-1].append(i)
    assert len(clusters) == 3, "three families per window"
    assert tuple(sorted(clusters[0])) == slow, "slow family is the low cluster"
    return [pm[i] for i in clusters[1]]


mid_band13 = next_band(pm13)
mid_band14 = next_band(pm14)
assert (min(mid_band13), max(mid_band13)) == (1124, 1140), "s139 band"
assert (min(mid_band14), max(mid_band14)) == (1134, 1148), "s147 band"
assert (min(mid_band13 + mid_band14),
        max(mid_band13 + mid_band14)) == (1124, 1148), "next band"
assert max(pm13[i] for i in slow) < min(mid_band13 + mid_band14), \
    "no overlap slow vs next band"
P("2. s150 (2) THE SLOW FAMILY (label CORRECTED against committed")
P("   CELL lines -- s150's 'forced=32' prose is a naming slip, s152")
P("   recon (1) corrected it, re-verified here): idx 13/17/21 are")
P("   wg=256 forced=16 probe_size=16 probe_nsub=16 probe_wg=256")
P("   pipeline=ok (the w256 FORCED=16 cells; the forced=32 w256 cells")
P("   are idx 14/18/22).")
P(f"   slow-family pooled-48 medians idx 13/17/21: s147 "
  f"{'/'.join(str(int(pm14[i])) for i in slow)}, s139 "
  f"{'/'.join(str(int(pm13[i])) for i in slow)}")
P(f"   next band (the 9 middle-family cells) pooled-48 medians: s139 "
  f"{int(min(mid_band13))}..{int(max(mid_band13))}, s147 "
  f"{int(min(mid_band14))}..{int(max(mid_band14))} -- combined "
  f"1,124..1,148 (state-s150 (2)'s range), no overlap with the slow")
P("   family (max 1,008).")
P(f"   s147 per-block argmin among 18 cells (rotation): "
  f"{' '.join(str(v) for v in m14_arg)}")
P(f"   s139 per-block argmin among 18 cells (rotation): "
  f"{' '.join(str(v) for v in m13_arg)}")
P("   pooled-48 argmin: idx 13 in BOTH windows (identity stable).")
P("")

# ---- 3. s150 (3): walk vs margin ----
assert (min(m14_c13), max(m14_c13)) == (991, 1028), "s147 cell13 walk"
assert (min(m13_c13), max(m13_c13)) == (981, 1015), "s139 cell13 walk"
assert (min(m14_min), max(m14_min)) == (991, 1006), "s147 min18 walk"
assert (min(m13_min), max(m13_min)) == (981, 1015), "s139 min18 walk"
assert (min(m13_c13 + m14_c13 + m13_min + m14_min),
        max(m13_c13 + m14_c13 + m13_min + m14_min)) == (981, 1028), \
    "combined block-unit walk"
assert min(pm13.values()) - 1000 == 1 and min(pm14.values()) - 1000 == 5, \
    "pooled margins 1 and 5"
P("3. s150 (3) WALK VS MARGIN:")
P(f"   fixed-cell-13 block walk: s147 {int(min(m14_c13))}.."
  f"{int(max(m14_c13))}, s139 {int(min(m13_c13))}..{int(max(m13_c13))}")
P(f"   min-over-18 block walk: s147 {int(min(m14_min))}.."
  f"{int(max(m14_min))}, s139 {int(min(m13_min))}..{int(max(m13_min))}")
P(f"   combined block-unit walk across both windows: 981..1,028 "
  f"(straddles the frozen 1,000 threshold)")
P(f"   pooled-48 slow-family minima sit just ABOVE threshold: s139 "
  f"{int(min(pm13.values()))} (margin {int(min(pm13.values())) - 1000}), "
  f"s147 {int(min(pm14.values()))} (margin {int(min(pm14.values())) - 1000})")
P("")

# ---- 4. s151 (1): pooled-arm minima across the bracket ----
# (the section-0 quote arms are NOT blank-line delimited -- each arm's
# pooled row is reached by a unique anchor + non-greedy scan to the
# first pooled row after it; anchor occurrences are fail-closed)
def quote_pooled(anchor, label):
    assert P139.count(anchor) == 1, f"anchor not unique: {label}"
    i = P139.index(anchor)
    m = re.compile(r"pooled-(\d+) median (\d+) 18-cell (\d+)\.\.(\d+) "
                   r"(CAPTURED|INTERMEDIATE/MIXED|FLOOR)").search(P139, i)
    assert m, f"WANT NOT PARSED: {label}"
    return int(m.group(1)), int(m.group(3))


lo_k, lo_min = quote_pooled("lo (405,1591) at n=254,557", "lo pooled-12")
bisk, bis24_min = quote_pooled("bis (3,316,1239) at n=255,045",
                               "bis pooled-24 (s136 quote)")
hi_k, hi_min = quote_pooled("hi (1213,4753) at n=255,208", "hi pooled-24")
assert (lo_k, lo_min) == (12, 998), "lo pooled-12 998"
assert (bisk, bis24_min) == (24, 1012), "bis pooled-24 1,012 (s136)"
assert (hi_k, hi_min) == (24, 1004), "hi pooled-24 1,004 (s132)"
arm = [lo_min, p139[1], p147[1], pbis_pub[1], bis24_min, hi_min]
assert (min(arm), max(arm)) == (998, 1012), "bracket-wide band 998..1,012"
P("4. s151 (1) POOLED-ARM 18-CELL MINIMA ACROSS THE ENTIRE BRACKET")
P("   (quote sources parsed from publication-s139.txt section 0 +")
P("   raw re-derivation for the s139/s147 pooled-48 arms):")
P(f"   lo n=254,557 pooled-12: {lo_min} (tenth-cut quote)")
P(f"   mid n=254,882 pooled-48: {int(min(pm13.values()))} (s139) / "
  f"{int(min(pm14.values()))} (s147)")
P(f"   bis n=255,045 pooled-24: {bis24_min} (s136 quote) / pooled-48: "
  f"{pbis_pub[1]} published ({fnum(min(pbis.values()))} exact) (s139)")
P(f"   hi n=255,208 pooled-24: {hi_min} (s132 quote)")
P(f"   band {min(arm)}..{max(arm)} (14-tick total spread) while the")
P("   block-unit walk is 981..1,028 -- every in-bracket point's margin")
P("   is inside the measured wander.")
P("")

# ---- 5. s151 (2): estimator shape ----
assert sha256_file(os.path.join(
    B13, "gpu-subgroup-reduce-anv-ndiv.c.txt")) == INSTR_PIN, \
    "committed instrument copy pin"
lines = INSTR.split("\n")
r_lines = [k for k, l in enumerate(lines) if l == "#define ROUNDS 25"]
w_lines = [k for k, l in enumerate(lines) if l == "#define WARMUP 3"]
assert len(r_lines) == 1 and len(w_lines) == 1, "one ROUNDS / one WARMUP"
assert w_lines[0] + 1 == r_lines[0], "WARMUP 3 directly above ROUNDS 25"
P("5. s151 (2) ESTIMATOR SHAPE (committed instrument copy")
P(f"   gpu-subgroup-reduce-anv-ndiv.c.txt, sha256 {INSTR_PIN[:16]}...):")
P(f"   '#define WARMUP 3' line {w_lines[0] + 1}, '#define ROUNDS 25' "
  f"line {r_lines[0] + 1} -- the estimator is a COMPILE-TIME constant;")
P("   450 SAMPLE/run = 18 pipeline-ok cells x 25 rounds (verified per")
P("   run in section 0). Deepening per-cell pooling is an INSTRUMENT")
P("   VARIANT (one-line diff + new pins), not a knob-triple change.")
P("")

# ---- 6. D3: round-level dispersion -> R ----
def mads(runs, ok):
    tab = {}
    for i in ok:
        xs = cell_samples(runs, i)
        assert len(xs) == 48 * 25, f"{len(xs)} samples at cell {i}"
        m = statistics.median(xs)
        mad = statistics.median([abs(x - m) for x in xs])
        tab[i] = (m, mad)
    return tab


TAB = mads(bis13, ok)
assert TAB == {
    1: (1148.0, 32.0), 2: (1444.0, 53.0), 3: (1447.0, 51.0),
    5: (1147.0, 31.0), 6: (1448.0, 50.0), 7: (1443.0, 52.5),
    9: (1147.0, 31.0), 10: (1439.5, 54.5), 11: (1449.0, 50.0),
    13: (1006.0, 43.0), 14: (1127.5, 66.5), 15: (1133.0, 69.0),
    17: (1005.5, 43.0), 18: (1135.0, 69.0), 19: (1139.0, 68.5),
    21: (1006.0, 43.0), 22: (1128.5, 72.5), 23: (1134.0, 71.0)}, \
    "bis s139 per-cell (m, MAD) table"
K = 3.6420
assert round(1.96 * 1.2533 * 1.4826, 4) == K, "CI constant 3.6420"
LADDER = [25, 50, 100, 200, 400, 800, 1600, 3200, 6400]


def max_h(tab, R):
    return max(K * mad / math.sqrt(3 * R) for _, (m, mad) in tab.items())


def r_star(tab):
    for R in LADDER:
        if max_h(tab, R) <= 2.0:
            return R
    return None


R = r_star(TAB)
assert R == 6400, f"R* {R} != 6400"
assert max_h(TAB, 3200) > 2.0 and max_h(TAB, 6400) <= 2.0, \
    "6400 is the SMALLEST ladder value meeting the target"
bind = max(ok, key=lambda i: (TAB[i][1], i))
assert bind == 22 and TAB[22][1] == 72.5, "binding cell idx 22 MAD 72.5"
TABX = mads(mid14, ok)
Rx = r_star(TABX)
assert Rx == 6400, f"cross-check R* {Rx}"
bindx = max(ok, key=lambda i: (TABX[i][1], i))
P("6. D3 ROUND-LEVEL DISPERSION DERIVATION (the pre-registered rule:")
P("   R = the smallest ladder value {25..6400} with max over the 18")
P("   pipeline-ok cells of 3.6420 * MAD_c / sqrt(3R) <= 2.0 ticks;")
P("   MADs over the COMMITTED bis round-level samples -- s139 48 bis")
P("   runs x 25 rounds = 1,200 samples/cell; the s147 mid window as")
P("   cross-check; 3.6420 = 1.96 * 1.2533 * 1.4826, frozen formula):")
P(f"   {'idx':>3} {'m':>8} {'MAD':>6}")
for i in ok:
    m, mad = TAB[i]
    P(f"   {i:>3} {m:>8.1f} {mad:>6.1f}")
P(f"   ladder (R : max 18-cell h over bis s139):")
for RL in LADDER:
    P(f"     R={RL:>4}: h_max = {max_h(TAB, RL):.4f}")
P(f"   R* = {R} (the ladder's LARGEST value -- the 2.0-tick target is")
P(f"   first met only at the ladder top; binding cell idx {bind},")
P(f"   MAD {TAB[bind][1]}). Named, not hidden: had the ladder top")
P("   failed, the rule would have fixed NO R; it passes at 6400.")
P(f"   CROSS-CHECK (s147 mid window 48 x 25): R* = {Rx} (binding cell")
P(f"   idx {bindx}, MAD {TABX[bindx][1]}) -- the derivation rule")
P("   reproduces the same constant on the cross-check window.")
P("")

# ---- 7. instrument variant source + pin ----
new_lines = list(lines)
new_lines[r_lines[0]] = f"#define ROUNDS {R}"
diff = [k for k in range(len(lines)) if lines[k] != new_lines[k]]
assert diff == r_lines, "exactly ONE line differs (the ROUNDS define)"
variant = "\n".join(new_lines)
vpath = os.path.join(HERE, f"gpu-subgroup-reduce-anv-ndiv-rounds{R}.c.txt")
open(vpath, "w").write(variant)
vpin = hashlib.sha256(variant.encode()).hexdigest()
assert vpin == sha256_file(vpath), "written file == computed pin"
P("7. INSTRUMENT VARIANT SOURCE (the D2 one-line diff of the committed")
P(f"   a5e539f0... copy) WRITTEN: gpu-subgroup-reduce-anv-ndiv-rounds"
  f"{R}.c.txt")
P(f"   changed line {r_lines[0] + 1} only: '#define ROUNDS 25' -> "
  f"'#define ROUNDS {R}'")
P(f"   SHA-256 instrument pin (NEW -- first-measured source pin, the")
P(f"   s136 440604ef... precedent): {vpin}")
P("   all other bytes byte-identical to the committed copy; the shader")
P("   corpus is unchanged (BYTE-IDENTICAL -- no corpus file is touched)")
P("   . Build-digest pins remain UNMEASURED (the measurement half is")
P("   NOT queued).")
P("")

# ---- 8. arm table + knob arithmetic ----
assert 3 + 48 + 3 == 54, "arm table 3+48+3"
assert (1000003 * 316) // 1239 == 255045, "bis knob arithmetic"
assert math.gcd(316, 1239) == 1, "bis gcd 1"
assert (1000003 * 248) // 973 == 254882, "mid knob arithmetic"
assert math.gcd(248, 973) == 1, "mid gcd 1"
P("8. ARM TABLE + KNOB ARITHMETIC (D4):")
P("   c2 (B=2, WM=1, NDIV=1) k=3 / bis (B=3, WM=316, NDIV=1239)")
P("   n=255,045 k=48 / c8 (B=8, WM=1, NDIV=1) k=3 = 54 fresh")
P("   processes (3+48+3 self-check); ZERO NEW KNOB TRIPLES.")
P("   (1,000,003*316)//1239 = 255,045, gcd(316,1239) = 1;")
P("   (1,000,003*248)//973 = 254,882, gcd(248,973) = 1.")
P("")

P("CENSUS COMPLETE: every asserted want parsed; 0 mismatches.")
print("\n".join(out))
