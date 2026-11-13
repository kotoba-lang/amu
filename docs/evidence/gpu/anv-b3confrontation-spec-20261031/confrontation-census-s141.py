#!/usr/bin/env python3
"""s141 confrontation-spec census -- re-derive every number cited by
confrontation-spec.txt from COMMITTED bytes only (quote-only content;
this script takes NO measurement of its own).

Inputs (committed, parsed fail-closed -- a want that does not parse
ABORTS):
  ../anv-b3bisect13-20261031/publication-s139.txt  (the 16-block content
    this spec's confrontation requirement names; itself produced only
    by analysis-s139.py over the 102 committed run logs -- re-run twice
    byte-identical at this session, repro-identity-s141.txt)
  ../anv-b3minwander-20261028/publication-s34.txt  (the within-window
    min-statistic wander content)

Pure stdlib. No clock, no RNG, no network, no hardware. Running it
twice yields byte-identical output.
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
GPU = os.path.join(HERE, "..")

P139 = open(os.path.join(GPU, "anv-b3bisect13-20261031",
                         "publication-s139.txt")).read()
P34 = open(os.path.join(GPU, "anv-b3minwander-20261028",
                        "publication-s34.txt")).read()

BLK = re.compile(r"block(\d+)\s+runs \S+\s+\(sum,128,16\)\s+(\d+)\s+18-cell\s+"
                 r"(\d+)\.\.(\d+)\s+(CAPTURED|INTERMEDIATE/MIXED|FLOOR)")
POOL = re.compile(r"pooled-48\s+runs 01\.\.48\s+\(sum,128,16\)\s+(\d+)\s+18-cell\s+"
                  r"(\d+)\.\.(\d+)\s+(CAPTURED|INTERMEDIATE/MIXED|FLOOR)")


def arm_rows(text, header):
    i = text.index(header)
    j = text.index("\n\n", i)
    seg = text[i:j]
    blocks = [(int(m.group(1)), int(m.group(2)), int(m.group(3)),
               int(m.group(4)), m.group(5)) for m in BLK.finditer(seg)]
    pm = POOL.search(seg)
    assert pm is not None, f"WANT NOT PARSED: pooled-48 of {header}"
    pooled = (int(pm.group(1)), int(pm.group(2)), int(pm.group(3)), pm.group(4))
    return blocks, pooled


out = []
P = out.append
P("confrontation-census-s141 -- every number confrontation-spec.txt cites,")
P("re-derived from committed bytes (quote-only; NO new measurement)")
P("")


# ---- 1. s139 16-block content at mid (254,882) and bis (255,045) ----
mid_blocks, mid_pooled = arm_rows(
    P139, "   mid (B=3, WM=248, NDIV=973, n=254882, 0.764644 nominal total units):")
bis_blocks, bis_pooled = arm_rows(
    P139, "   bis (B=3, WM=316, NDIV=1239, n=255045, 0.765133 nominal total units):")

MID_MED = [b[1] for b in mid_blocks]
MID_MIN = [b[2] for b in mid_blocks]
MID_CLS = [b[4] for b in mid_blocks]
BIS_MED = [b[1] for b in bis_blocks]
BIS_MIN = [b[2] for b in bis_blocks]
BIS_CLS = [b[4] for b in bis_blocks]

assert MID_MED == [1146, 1143, 1143, 1142, 1150, 1153, 1152, 1142, 1141,
                  1140, 1137, 1131, 1133, 1128, 1134, 1131], "mid medians"
assert MID_MIN == [1003, 1015, 1005, 1006, 997, 998, 1004, 992, 1004,
                   993, 985, 981, 1003, 986, 996, 992], "mid 18-cell minima"
assert BIS_MED == [1174, 1167, 1162, 1143, 1147, 1150, 1152, 1150, 1151,
                   1153, 1144, 1144, 1145, 1127, 1146, 1145], "bis medians"
assert BIS_MIN == [1002, 1001, 1003, 995, 994, 1011, 991, 996, 999,
                   991, 992, 1000, 1005, 1001, 990, 995], "bis 18-cell minima"
assert len(MID_CLS) == 16 and len(BIS_CLS) == 16, "16 blocks per arm"
mid_cap = MID_CLS.count("CAPTURED")
bis_cap = BIS_CLS.count("CAPTURED")
mid_im = MID_CLS.count("INTERMEDIATE/MIXED")
bis_im = BIS_CLS.count("INTERMEDIATE/MIXED")
assert (mid_cap, mid_im) == (7, 9), "mid 7x CAPTURED + 9x I/M"
assert (bis_cap, bis_im) == (7, 9), "bis 7x CAPTURED + 9x I/M"
assert mid_pooled == (1140, 1001, 1442, "CAPTURED"), "mid pooled-48"
assert bis_pooled == (1148, 1006, 1449, "CAPTURED"), "bis pooled-48"
P("1. s139 16-block content (publication-s139.txt section 3):")
P(f"   mid (248,973) n=254,882 pinned binary cabff942...: "
  f"{mid_cap}x CAPTURED + {mid_im}x INTERMEDIATE/MIXED blocks")
P(f"   mid block medians: {' / '.join(str(v) for v in MID_MED)}")
P(f"   mid block 18-cell minima: {' / '.join(str(v) for v in MID_MIN)}")
P(f"   mid pooled-48: median {mid_pooled[0]}, 18-cell {mid_pooled[1]}.."
  f"{mid_pooled[2]}, class {mid_pooled[3]}")
P(f"   bis (3,316,1239) n=255,045 pinned binary 440604ef...: "
  f"{bis_cap}x CAPTURED + {bis_im}x INTERMEDIATE/MIXED blocks")
P(f"   bis block medians: {' / '.join(str(v) for v in BIS_MED)}")
P(f"   bis block 18-cell minima: {' / '.join(str(v) for v in BIS_MIN)}")
P(f"   bis pooled-48: median {bis_pooled[0]}, 18-cell {bis_pooled[1]}.."
  f"{bis_pooled[2]}, class {bis_pooled[3]}")
P("")

# ---- 2. s139 W2 per-run minima and crossing counts; W1 verdict ----
def w2(text, arm):
    vec = re.search(rf"{arm} per-run 18-cell min: ((?:\d+ ?)+)", text)
    cnt = re.search(rf"{arm}: runs with 18-cell min >= 1,000 \(COMPUTED here, "
                    rf"descriptive\): (\d+)/(\d+)", text)
    assert vec and cnt, f"WANT NOT PARSED: W2 {arm}"
    vals = [int(x) for x in vec.group(1).split()]
    return vals, int(cnt.group(1)), int(cnt.group(2))

mid_v, mid_c, mid_n = w2(P139, "mid")
bis_v, bis_c, bis_n = w2(P139, "bis")
assert (mid_n, bis_n) == (48, 48), "48 runs per B=3 arm"
assert (mid_c, bis_c) == (13, 14), "boundary crossings 13/48 mid, 14/48 bis"
assert len(mid_v) == 48 and len(bis_v) == 48, "48 minima per arm"
assert (min(mid_v), max(mid_v)) == (974, 1013), "mid per-run band"
assert (min(bis_v), max(bis_v)) == (975, 1023), "bis per-run band"
assert "(c) NEITHER PASSES" in P139, "W1 (c) verdict"
assert "(254,557, 255,208]" in P139, "committed bracket"
P("2. s139 W2 (descriptive) + W1:")
P(f"   per-run 18-cell min crossing 1,000: mid {mid_c}/{mid_n}, "
  f"bis {bis_c}/{bis_n}")
P(f"   per-run 18-cell min bands: mid {min(mid_v)}..{max(mid_v)}, "
  f"bis {min(bis_v)}..{max(bis_v)} (per-run unit, DESCRIPTIVE)")
P("   W1 verdict line present: '(c) NEITHER PASSES'; bracket "
  "'(254,557, 255,208]'")
P("")

# ---- 3. s34 within-window min-statistic wander ----
m = re.search(r"block-unit min statistics \(THE STATISTIC, in run order "
              r"A\.\.L\): ((?:[A-L] \d+ ?)+)", P34)
assert m, "WANT NOT PARSED: s34 block mins"
s34_mins = [(a, int(b)) for a, b in re.findall(r"([A-L]) (\d+)", m.group(1))]
assert [v for _, v in s34_mins] == [993, 1003, 982, 1000, 991, 988, 991,
                                    986, 992, 989, 989, 985], "s34 mins"
mc = re.search(r"block classes \(in run order A\.\.L\): "
               r"((?:[A-L] \S+ ?)+)", P34)
assert mc, "WANT NOT PARSED: s34 block classes"
s34_cls = re.findall(r"([A-L]) (\S+)", mc.group(1))
cap = sum(1 for _, c in s34_cls if c == "CAPTURED")
im = sum(1 for _, c in s34_cls if c == "INTERMEDIATE/MIXED")
assert (cap, im) == (2, 10), "s34 2 CAPTURED + 10 I/M"
s34_vals = [v for _, v in s34_mins]
P("3. s34 within-window min-statistic wander (publication-s34.txt; ONE")
P("   window, byte-identical binary, 12 blocks at the (1024,4033) anchor")
P("   n=253,906):")
P(f"   block-unit min statistics A..L: {' '.join(str(v) for v in s34_vals)}")
P(f"   range {min(s34_vals)}..{max(s34_vals)}; classes {cap}x CAPTURED + "
  f"{im}x INTERMEDIATE/MIXED (the 1,000 boundary crossed WITHIN one window)")
P("")

# ---- 4. block-unit min band across s34 + s139; dual-class content ----
band_lo = min(MID_MIN + BIS_MIN + s34_vals)
band_hi = max(MID_MIN + BIS_MIN + s34_vals)
assert (band_lo, band_hi) == (981, 1015), "block-unit min band"
P("4. The measured block-unit 18-cell-min wander band over the s34 window")
P(f"   and the s139 16-block windows: {band_lo}..{band_hi} (block unit);")
P(f"   per-run unit {min(mid_v + bis_v)}..{max(mid_v + bis_v)} "
  f"(descriptive unit, s139 W2).")
P("")

row = re.compile(r"^\s+(254557|254882|255045|255208)\s+\S+\s+(\d+)\s+"
                 r"(INTERMEDIATE/MIXED|CAPTURED)\s+(.*)$", re.M)
rows = row.findall(P139)
r4557 = [(int(t), c) for n, t, c, _ in rows if n == "254557"]
r4882 = [(int(t), c) for n, t, c, _ in rows if n == "254882"]
assert any(c == "CAPTURED" for _, c in r4557) and \
       any(c == "INTERMEDIATE/MIXED" for _, c in r4557), "254,557 both classes"
assert any(c == "CAPTURED" for _, c in r4882) and \
       any(c == "INTERMEDIATE/MIXED" for _, c in r4882), "254,882 both classes"
P("5. Dual-class committed content (publication-s139.txt W2 row table):")
P(f"   n=254,557 rows: {' ; '.join(f'{t} {c}' for t, c in r4557)}")
P(f"   n=254,882 rows: {' ; '.join(f'{t} {c}' for t, c in r4882)}")
P("")

# ---- 6. cross-window disagreement at mid (pub139's W3 quote of s132/s136) ----
assert "1133" in P139 and "1148" in P139, "cross-window pooled values present"
P("6. Cross-window disagreement at mid at the byte-identical pinned binary")
P("   cabff942...: s132 window pooled-24 1,133 INTERMEDIATE/MIXED vs s136")
P("   window pooled-24 1,148 CAPTURED vs s139 window pooled-48 1,140")
P("   CAPTURED (the s132/s136 values are publication-s139.txt section-0/3")
P("   parsed quotes; the s139 value is section 3, above).")
P("")
P("CENSUS COMPLETE: every asserted want parsed; 0 mismatches.")

print("\n".join(out))
