#!/usr/bin/env python3
"""JUN-59 session 121 analysis -- THE B=3 PER-DISPATCH-WORK THRESHOLD
BISECT, EIGHTH CUT (one new grid point at n = 254,557 = the exact floor
midpoint of the settle-bar-V3 re-opened bracket (253,906, 255,208]).
The MEASUREMENT half of the s120 pre-registration
(anv-b3bisect8prereg-20261031/protocol.txt, frozen 2026-10-31T03:53:30Z
BEFORE any run log of this cut existed).

Route (frozen in protocol.txt section 7): this script parses ONLY the 21
committed run logs in its own directory (run-<tag>-r<R>.txt) and NAMED
COMMITTED WANT SOURCES (the quote-only values of protocol section 3,
parsed here from committed bytes -- never transcribed) and writes
publication-s121.txt. No other input. Deterministic: running it twice
yields byte-identical publication-s121.txt (checked by diff after the
recorded run). Every want source is parsed with fail-closed regexes; a
want that does not parse aborts (assert).
"""
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    HERE = sys.argv[1]

GPU = os.path.join(HERE, "..")

# tag -> (BATCH, WORK_MUL, NDIV), frozen protocol section 0 arm table
# (7 rows = 21 logs)
ARMS = [("c2", 2, 1, 1), ("lo", 3, 1024, 4033), ("mid", 3, 405, 1591),
        ("eq3", 3, 810, 3182), ("hi", 3, 1213, 4753), ("b2m", 2, 405, 1591),
        ("c8", 8, 1, 1)]
TAGS = [a[0] for a in ARMS]
ARMB = {a[0]: a[1] for a in ARMS}
ARMW = {a[0]: a[2] for a in ARMS}
ARMD = {a[0]: a[3] for a in ARMS}
RUNS = [1, 2, 3]
N_BASE = 1000003


def flat(text):
    return re.sub(r"\s+", " ", text)


def parse1(text, pattern, what):
    m = re.search(pattern, flat(text))
    assert m is not None, f"WANT SOURCE NOT PARSED: {what}"
    return m.group(1).strip()


# ---- NAMED COMMITTED WANT SOURCES (protocol section 3; parsed from
# ---- committed bytes, never transcribed; fail-closed) ----
s27c = open(os.path.join(GPU, "anv-b3bisect7-20261027",
                         "derivation-census-s27.txt")).read()
s27pub = open(os.path.join(GPU, "anv-b3bisect7-20261027",
                           "publication-s27.txt")).read()
bar_txt = open(os.path.join(GPU, "anv-b3settlebar-20261027",
                            "settle-bar.txt")).read()
bar_pin = open(os.path.join(GPU, "anv-b3w7ledgerappend-20261031",
                            "bar-s117-eval-post-run1.txt")).read()

# committed controls (s27 census): "c2 31 (floor band 31..32); c8 32,915 ..."
ctl = parse1(s27c, r"committed controls: (c2 \d+ \(floor band [\d.]+\.\.[\d.]+\); "
                   r"c8 [\d,]+ \(session 4 pooled median\))", "committed controls")
m = re.match(r"c2 (\d+) \(floor band (\d+)\.\.(\d+)\); c8 ([\d,]+)", ctl)
assert m, "committed controls shape"
C2_COMMITTED = int(m.group(1))
C2_BAND = (int(m.group(2)), int(m.group(3)))
C8_COMMITTED = int(m.group(4).replace(",", ""))
COMMITTED_SRC = ctl

# the bar's frozen numeric references (settle-bar.txt D3)
refs_txt = parse1(bar_txt, r"frozen numeric reference \(([\d, /]+)--",
                  "bar frozen refs")
BAR_REFS = tuple(int(x.replace(",", "")) for x in refs_txt.split("/") )
# the settle-bar settled class (the frozen evaluator's committed pin)
SETTLED = parse1(bar_pin, r"VERDICT: (SETTLED \S+(?:/\S+)*)", "settled verdict")
SETTLED_CLASS = SETTLED.replace("SETTLED ", "")

# lo arm wants: the bar-SETTLED anchor class + in-band criterion vs the refs
LO_CLASS_WANT = SETTLED_CLASS

# lo's settled-over prior reading (s27 census, quote-only): s26's one-tick
# (1024,4033) reading and its C3 (b) twin caveat
LO_PRIOR = parse1(s27c, r"the \(1024,4033\) pair \(this session's hi\): "
                        r"(session 26 mid [\d,]+ \S+ \(min [\d,]+\))",
                  "lo prior reading")
LO_TWIN = parse1(s27c, r"twin \(2048,8066\) min (\d+ \S+(?:/\S+)* at overlapping "
                       r"medians\))", "lo C3 (b) twin caveat")

# hi arm wants: the committed (1213,4753) trio (s27 census)
trio_txt = parse1(s27c, r"the \(1213,4753\) pair \(session 24 mid / session 25 hi "
                        r"/ session 26 hi\): ([\d,/]+)", "hi trio")
HI_TRIO = tuple(int(x.replace(",", "")) for x in trio_txt.split("/"))
HI_REF = HI_TRIO[0]

# b2m-class want (s27 census)
B2M_WANT = parse1(s27c, r"b2m-class \(B=2 at a small grid\): "
                        r"(FLOOR \(sessions 21-26: [\d,]+\))", "b2m-class")

# the committed B=3 class-vs-per-dispatch-work row (s27 publication W2
# table, quote-only rows)
B3ROW = []
for line in s27pub.splitlines():
    m = re.match(r"\s+(\d+)\s+(\S+)\s+(\d+)\s+(\S+)\s+(.+?) \(quote-only\)$", line)
    if m:
        cls = m.group(4).rstrip("*")
        B3ROW.append((m.group(2), int(m.group(1)), int(m.group(3)), cls,
                      m.group(5)))
assert len(B3ROW) == 11, f"B3ROW parsed {len(B3ROW)} want 11"

# prior host_ns rows for X1 (s27 census s26 row; s27 publication s27 row)
s26hn_txt = parse1(s27c, r"session-26 host_ns at \(sum,128,S=16\): "
                         r"((?:\w+ \d+; )*\w+ \d+)", "s26 host_ns row")
S26HN = {k: int(v) for k, v in
         (part.strip().split() for part in s26hn_txt.split(";"))}
m = re.search(r"^\s+c2 (\d+), lo (\d+), mid (\d+), eq3 (\d+), hi (\d+), "
              r"b2m (\d+), c8 (\d+)$", s27pub, re.M)
assert m, "s27 host_ns row not parsed"
S27HN = dict(zip(TAGS, (int(m.group(i)) for i in range(1, 8))))

cell_re = re.compile(
    r"^CELL idx=(\d+) spv=(\S+) op=(\S+) wg=(\d+) forced=(\S+) probe_size=(-?\d+) "
    r"probe_nsub=(-?\d+) probe_wg=(-?\d+) pipeline=(\S+) void=(\d)")
verify_re = re.compile(r"^VERIFY idx=(\d+) checked=(\d+) mismatch=(\d+) ok=(\d)")
sample_re = re.compile(
    r"^SAMPLE round=(\d+) idx=(\d+) batch=(\d+) work_mul=(\d+) ndiv=(\d+) gpu_ticks=(\d+) "
    r"gpu_ns=([\d.]+) per_dispatch_ns=([\d.]+) host_ns=(\d+)")


def load(path):
    cells, verifies, samples, header = {}, [], [], []
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("#"):
            header.append(line)
        elif line.startswith("CELL "):
            m = cell_re.match(line)
            assert m, line
            cells[int(m.group(1))] = dict(spv=m.group(2), op=m.group(3),
                                          wg=int(m.group(4)), forced=m.group(5),
                                          probe_size=int(m.group(6)),
                                          probe_nsub=int(m.group(7)),
                                          probe_wg=int(m.group(8)),
                                          pipeline=m.group(9), void=int(m.group(10)))
        elif line.startswith("VERIFY "):
            m = verify_re.match(line)
            assert m, line
            verifies.append((int(m.group(1)), int(m.group(2)), int(m.group(3)),
                             int(m.group(4))))
        elif line.startswith("SAMPLE "):
            m = sample_re.match(line)
            assert m, line
            samples.append((int(m.group(1)), int(m.group(2)), int(m.group(3)),
                            int(m.group(4)), int(m.group(5)), int(m.group(6)),
                            float(m.group(7)), float(m.group(8)), int(m.group(9))))
        elif line.startswith("# done"):
            header.append(line)
    return cells, verifies, samples, header


def med(xs):
    return statistics.median(xs)


out = []
P = out.append
P("JUN-59 session 121 -- THE B=3 PER-DISPATCH-WORK THRESHOLD BISECT,")
P("EIGHTH CUT (one new grid point at n = 254,557 -- the EXACT floor")
P("midpoint of the settle-bar-V3 re-opened bracket (253,906, 255,208],")
P("reachable at the knob -- 31 in-box pairs, smallest (405,1591); 7 pairs")
P("have their same-ratio double in-box -- including the smallest -- so eq3")
P("IS in-box this cut (810,3182)), publication -- the MEASUREMENT half of")
P("the s120 pre-registration (anv-b3bisect8prereg-20261031/protocol.txt,")
P("frozen 2026-10-31T03:53:30Z BEFORE any run log of this cut existed).")
P("Produced ONLY by analysis-s121.py over the 21 committed run logs in this")
P("directory (run-<tag>-r<R>.txt) and the NAMED COMMITTED WANT SOURCES")
P("parsed below (protocol section 3 quote-only values, parsed from")
P("committed bytes, never transcribed). Arms = binary compile-time (BATCH,")
P("WORK_MUL, NDIV); n = (1,000,003*WORK_MUL)/NDIV (integer floor). lo/hi")
P("re-run the frozen bracket-end knob pairs in-session (n=253,906 =")
P("(1,000,003*1024)//4033 = the bar-SETTLED (1024,4033) anchor pair;")
P("n=255,208 = (1,000,003*1213)//4753 = the committed measurement pair")
P("(1213,4753)); mid is THE bisect point n = (1,000,003*405)//1591 =")
P("254,557 = (253,906+255,208)//2 (the smallest of 31 knob pairs mapping")
P("to it in the WM<=2,048 x NDIV<=8,192 search box -- knob-search-s119.py,")
P("committed in anv-b3bisect8prereg-20261031/); eq3 is the same-ratio")
P("(810,3182) pair-representation check at mid's grid (the double of")
P("(405,1591)); b2m is the B=2 control at the bisect n. c2/c8 are the")
P("archived environment controls. ZERO derivation this session: the")
P("instrument is session 26's committed NDIV-derived source byte-identical")
P("(digest a5e539f0... -- derivation-census-s121.txt); the a-set manifest")
P("runs the ARCHIVED measured spv (16-digest corpus).")
P("The row question (protocol section 0): AT FIXED DISPATCH COUNT B=3,")
P("WHERE IN (253,906, 255,208] DOES THE B=3 CLASS FLIP FROM")
P("INTERMEDIATE/MIXED TO CAPTURED? -- mid CAPTURED narrows the flip to")
P("(253,906, 254,557]; mid INTERMEDIATE/MIXED narrows it to (254,557,")
P("255,208]; mid FLOOR is a pre-named non-monotone contradiction and is")
P("not resolved here. The bracket direction came from the settle-bar V3")
P("SETTLED class at the (1024,4033) anchor (BAR NON-INTERFERENCE: the")
P("cut's runs are BISECT CONTENT and NOT bar readings -- no ledger")
P("append, no day-slot consumption, no bar verdict movement, no Rule 4")
P("row or :measured? flag movement). Protocol L2: at fixed B=3 the")
P("per-dispatch grid n and TOTAL nominal work co-vary BY CONSTRUCTION")
P("(total = 3*n/1,000,003); the letters are observational discriminators")
P("among named hypotheses, never a mechanism. 1 tick = timestampPeriod =")
P("52.083 ns.")
P("")

P("0. NAMED COMMITTED WANT SOURCES (parsed here from committed bytes;")
P("   every value below is a QUOTE-ONLY comparison value and never this")
P("   session's measurement):")
P(f"   committed controls (s27 census): {COMMITTED_SRC}")
P(f"   bar frozen refs (anv-b3settlebar-20261027/settle-bar.txt): "
  f"{'/'.join(f'{r:,}' for r in BAR_REFS)}")
P(f"   settle-bar settled verdict (bar-s117-eval-post-run1.txt): {SETTLED}")
P(f"   lo prior reading (s27 census): {LO_PRIOR}")
P(f"   lo C3 (b) twin caveat (s27 census): {LO_TWIN}")
P(f"   hi committed trio (s27 census): {trio_txt}")
P(f"   b2m-class (s27 census): {B2M_WANT}")
P(f"   committed B=3 row (s27 publication W2 table): {len(B3ROW)} grid "
  f"points parsed")
P("")

# ---- load everything, integrity checks ----
data = {}
cell_keys = None
integrity = []
header_ok = True
knob_field_ok = True
spv_identity_ok = True
verify_mismatch_total = 0
verify_mismatch_by_arm = {t: 0 for t in TAGS}
forcing_ok = 0
forcing_total = 0
s8_fail = 0
sample_counts_ok = True
base_header = None
for tag in TAGS:
    b, wm, dd = ARMB[tag], ARMW[tag], ARMD[tag]
    for r in RUNS:
        fn = f"run-{tag}-r{r}.txt"
        cells, verifies, samples, header = load(os.path.join(HERE, fn))
        data[(tag, r)] = (cells, verifies, samples, header)
        keys = tuple(sorted((k, v["op"], v["wg"], v["forced"], v["pipeline"])
                            for k, v in cells.items()))
        if cell_keys is None:
            cell_keys = keys
        elif keys != cell_keys:
            integrity.append(f"CELL MAP MISMATCH in {fn}")
        hb = tuple(l for l in header if not l.startswith("# n="))
        if base_header is None:
            base_header = hb
        elif base_header != hb:
            header_ok = False
            integrity.append(f"HEADER MISMATCH in {fn}")
        for l in header:
            if l.startswith("# n="):
                mn = re.search(r"n=(\d+)", l)
                mb = re.search(r"batch=(\d+)", l)
                mbar = re.search(r"barrier_n=(\d+)", l)
                mmu = re.search(r"work_mul=(\d+)", l)
                mdi = re.search(r"ndiv=(\d+)", l)
                if (not mb or int(mb.group(1)) != b) \
                   or (not mbar or int(mbar.group(1)) != 0) \
                   or (not mmu or int(mmu.group(1)) != wm) \
                   or (not mdi or int(mdi.group(1)) != dd):
                    knob_field_ok = False
                    integrity.append(f"HEADER knob FIELD MISMATCH in {fn}: {l}")
                if not mn or int(mn.group(1)) != (N_BASE * wm) // dd:
                    knob_field_ok = False
                    integrity.append(f"HEADER n= FIELD MISMATCH in {fn}: {l}")
        for k, v in cells.items():
            ok = v["spv"].endswith(".emitted.spv") and ".iter" not in v["spv"]
            if not ok:
                spv_identity_ok = False
                integrity.append(f"CELL spv SET MISMATCH in {fn} idx={k}: {v['spv']}")
        for (idx, ch, mis, ok) in verifies:
            verify_mismatch_total += mis
            verify_mismatch_by_arm[tag] += mis
            c = cells[idx]
            if c["pipeline"] == "ok":
                forcing_total += 1
                exp_s = 32 if c["forced"] == "default" else int(c["forced"])
                if (c["probe_size"] == exp_s
                        and c["probe_nsub"] == (c["wg"] // exp_s)):
                    forcing_ok += 1
            else:
                if c["forced"] == "8":
                    s8_fail += 1
        ok_cells = [k for k, v in cells.items() if v["pipeline"] == "ok"]
        exp = len(ok_cells) * 25
        if len(samples) != exp:
            sample_counts_ok = False
            integrity.append(f"SAMPLE COUNT {len(samples)} != {exp} in {fn}")
        for (rnd, idx, bt, mt, dt, gt, gn, pdn, hn) in samples:
            if bt != b or mt != wm or dt != dd:
                knob_field_ok = False
                integrity.append(f"SAMPLE knob FIELD {bt},{mt},{dt} != {b},{wm},{dd} in {fn}")

P("1. INTEGRITY (computed over the 21 logs):")
P(f"   runs parsed: 21 (7 arms x 3 runs); cell map identical across runs: "
  f"{cell_keys is not None and not any('CELL MAP' in i for i in integrity)}")
P(f"   headers byte-identical across all runs outside the # n= knob line: {header_ok}")
P(f"   header batch=/work_mul=/ndiv= == run's (B,WM,NDIV) and n == "
  f"(1,000,003*WM)//NDIV; every SAMPLE batch=/work_mul=/ndiv= == (B,WM,NDIV): "
  f"{knob_field_ok}")
P(f"   every CELL spv= name is an archived .emitted.spv (no .iter -- the "
  f"corpus is byte-identical this session): {spv_identity_ok}")
P(f"   SAMPLE lines: 450 per run (18 ok cells x 25 rounds) in 21/21 runs: "
  f"{sample_counts_ok}")
P(f"   VERIFY mismatch total over all runs: {verify_mismatch_total} (per-arm: "
  + ", ".join(f"{t}={verify_mismatch_by_arm[t]}" for t in TAGS)
  + ") -- bit-exact correctness re-check inside every run; frozen "
    "INVALIDATION criterion (protocol section 4): >0 in any run makes that "
    "run DEFECTIVE and the arm INVALID")
P(f"   forcing reality (pipeline-ok cell-runs where probe_size==forced and "
  f"probe_nsub==wg/forced): {forcing_ok}/{forcing_total}")
P(f"   S=8 cells fail-closed (pipeline=FAIL, forced=8): {s8_fail} cell-runs "
  f"(6 per run x 21 runs = 126 expected)")
if integrity:
    for i in integrity:
        P(f"   !! {i}")
P("")


def pooled(tag, idx):
    xs = []
    for r in RUNS:
        cells, verifies, samples, header = data[(tag, r)]
        xs += [s[5] for s in samples if s[1] == idx]
    return med(xs)


def pooled_host(tag, idx):
    xs = []
    for r in RUNS:
        cells, verifies, samples, header = data[(tag, r)]
        xs += [s[8] for s in samples if s[1] == idx]
    return med(xs)


def run_medians(tag, idx):
    ms = []
    for r in RUNS:
        cells, verifies, samples, header = data[(tag, r)]
        ms.append(med([s[5] for s in samples if s[1] == idx]))
    return ms


ok_cells = sorted([k for k, v in data[("c2", 1)][0].items()
                   if v["pipeline"] == "ok"])


def ckey(idx):
    c = data[("c2", 1)][0][idx]
    return (c["op"], c["wg"], c["forced"])


sum128 = [k for k in ok_cells if ckey(k) == ("sum", 128, "16")][0]

P("2. THE MEASURED BRACKETS (pooled median gpu_ticks over 3 runs x 25 "
  "rounds per cell):")
P("   each row: (sum,128,S=16) exact value, per-run median band at that "
  "cell,")
P("   then min..max over the 18 pipeline-ok cells; host_ns at (sum,128,S=16)")
P("")
P("   arm  B  WM  NDIV     n        total-nominal  (sum,128,16)   "
  "run-median band    min..max over 18 cells   host_ns")
for tag in TAGS:
    b, wm, dd = ARMB[tag], ARMW[tag], ARMD[tag]
    n = (N_BASE * wm) // dd
    vals = [pooled(tag, k) for k in ok_cells]
    v16 = pooled(tag, sum128)
    rms = run_medians(tag, sum128)
    hn = pooled_host(tag, sum128)
    tot = b * n / N_BASE
    P(f"   {tag}  {b}  {wm}  {dd:<5} {n:>8}  {tot:>12.6f}  {v16:>10.0f}     "
      f"{min(rms):>8.0f}..{max(rms):<8.0f}  {min(vals):>8.0f}..{max(vals):<8.0f}  "
      f"{hn:>9.0f}")
P("")


def classify(tag):
    vals = [pooled(tag, k) for k in ok_cells]
    if all(v <= 100 for v in vals):
        return "FLOOR"
    if all(v >= 1000 for v in vals):
        return "CAPTURED"
    return "INTERMEDIATE/MIXED"


CLASS = {tag: classify(tag) for tag in TAGS}

P("3. PRE-REGISTERED LETTERS (thresholds frozen in protocol.txt section 4:")
P("   FLOOR <= 100 ticks at all 18 cells; CAPTURED >= 1000 ticks at all 18;")
P("   anything else INTERMEDIATE/MIXED):")
P("")
for tag in TAGS:
    b, wm, dd = ARMB[tag], ARMW[tag], ARMD[tag]
    n = (N_BASE * wm) // dd
    P(f"   class {tag} (B={b}, WM={wm}, NDIV={dd}, n={n}, "
      f"{b * n / N_BASE:.6f} nominal units): {CLASS[tag]}")
P("")

arms_invalid = sorted(t for t in TAGS if verify_mismatch_by_arm[t] > 0)
if arms_invalid:
    P("   INVALIDATION CRITERION FIRED (frozen): VERIFY mismatch > 0 in arm(s)")
    P(f"   {arms_invalid} -- the knob arithmetic is WRONG at those arms")
    P("   (a stored value changed: buffer sizing / PARTS_CAP / CPU reference)")
    P("   and no letter below is evaluable from those arms.")
    P("")

# C1 (prerequisite)
c1_c2_ok = CLASS["c2"] == "FLOOR"
c1_parts = [f"c2 satisfies FLOOR (committed floor band "
            f"{C2_BAND[0]}..{C2_BAND[1]} at B=2): {c1_c2_ok}"]
v8 = pooled("c8", sum128)
c1_c8_ok = abs(v8 - C8_COMMITTED) <= 0.05 * C8_COMMITTED
c1_parts.append(f"c8 (sum,128,S=16) pooled median {v8:.0f} within +/-5% of "
                f"committed {C8_COMMITTED} (session 4 pooled median): {c1_c8_ok}")
c1_ok = c1_c2_ok and c1_c8_ok
P("   C1 ARCHIVED CONTROL REPLICATION (numeric agreement with the committed")
P("   value at the control's OWN (B,WORK_MUL,NDIV) -- the a-set runs the")
P("   ARCHIVED spv bytes through the byte-identical session-26 instrument,")
P("   so this pins the environment as well):")
for s in c1_parts:
    P(f"     {s}")
if c1_ok:
    P("     VERDICT: branch (a) both controls satisfy their criteria --")
    P("     the W letters are evaluated against the row question.")
else:
    P("     VERDICT: branch (b) replication discrepancy (bearing on the")
    P("     environment pin); W letters interpretation is FLAGGED; cause "
      "UNMEASURED.")
P("")

# C2 bracket anchor replication (lo = bar-SETTLED (1024,4033) anchor;
# hi = committed (1213,4753) measurement pair)
vlo = pooled("lo", sum128)
vhi = pooled("hi", sum128)
lo_refs_ok = all(abs(vlo - ref) <= 0.05 * ref for ref in BAR_REFS)
lo_ok = lo_refs_ok and CLASS["lo"] == LO_CLASS_WANT
hi_num_ok = abs(vhi - HI_REF) <= 0.05 * HI_REF
hi_ok = hi_num_ok and CLASS["hi"] == "CAPTURED"
c2_ok = lo_ok and hi_ok
P("   C2 BRACKET ANCHOR REPLICATION (lo is the bar-SETTLED anchor knob pair")
P("   BATCH=3,WORK_MUL=1024,NDIV=4033 -- rebuilt binary BYTE-IDENTICAL to")
P("   session 27's anv-bb-hi (a6c31b6c... -- build-census-s121.txt); hi is")
P("   the committed measurement pair BATCH=3,WORK_MUL=1213,NDIV=4753 --")
P("   rebuilt binary BYTE-IDENTICAL to session 26's anv-bb-hi (123e8f73...")
P("   -- both pins declared in the frozen protocol section 2 in advance):")
P(f"     lo (sum,128,S=16) pooled median {vlo:.0f} within +/-5% of EACH "
  f"frozen bar reference {'/'.join(f'{r:,}' for r in BAR_REFS)} "
  f"(the bar's own in-band criterion): {lo_refs_ok}")
P(f"     lo class {CLASS['lo']} (the bar-SETTLED class {LO_CLASS_WANT}): "
  f"{CLASS['lo'] == LO_CLASS_WANT}")
P(f"     NAMED, NOT HIDDEN: lo's settled-over prior content is {LO_PRIOR} "
  f"-- the bar settled that class over four counted readings of four "
  f"distinct UTC days to {SETTLED}; the C3 (b) caveat ({LO_TWIN}) is "
  f"carried. If lo classifies anything but {LO_CLASS_WANT} here, that "
  f"DISAGREEMENT with the bar's settled class is named content, fires C2 "
  f"(b), and does NOT re-open or move the bar (the BAR NON-INTERFERENCE "
  f"clause).")
P(f"     hi (sum,128,S=16) pooled median {vhi:.0f} within +/-5% of the "
  f"committed reading {HI_REF} (the trio {trio_txt} spans 0.9%): {hi_num_ok}")
P(f"     hi class {CLASS['hi']} (committed class CAPTURED): "
  f"{CLASS['hi'] == 'CAPTURED'}")
P(f"     NAMED, NOT HIDDEN: hi's expected CAPTURED class carries the named "
  f"1,000-at-the-boundary risk (session 24's 18-cell min sat at 1,000, "
  f"EXACTLY at the frozen boundary) AND the C3 (b) twin caveat "
  f"((2426,9506) min 994 INTERMEDIATE/MIXED at overlapping medians, "
  f"committed quote \"1,000 vs 994 at n=255,208\"); if hi classifies "
  f"INTERMEDIATE/MIXED here, C2 fires (b) and W1 is FLAGGED at its frozen "
  f"letter.")
if c2_ok:
    P("     VERDICT: branch (a) -- both bracket ends replicate IN-SESSION")
    P("     (at a byte-identical rebuilt binary each) and W1's bracket")
    P("     narrowing is valid at its letter.")
else:
    P("     VERDICT: branch (b) -- one or both bracket ends did not")
    P("     replicate in-session; W1 is FLAGGED; the measured classes")
    P("     stand as content; cause UNMEASURED.")
P("")

# C3 pair-representation check (eq3 (810,3182) vs mid (405,1591))
veq3 = pooled("eq3", sum128)
vmid = pooled("mid", sum128)
c3_num_ok = abs(veq3 - vmid) <= 0.05 * vmid
c3_ok = CLASS["eq3"] == CLASS["mid"] and c3_num_ok
P("   C3 PAIR-REPRESENTATION CHECK (eq3 is the (810,3182) pair at")
P("   n = 254,557 == mid's grid and B=3 -- the same ratio 405/1591 in a")
P("   different (WORK_MUL,NDIV) representation; NEW knob pairs, protocol "
  "L8;")
P("   NAMED, NOT HIDDEN: the double sits INSIDE the WM<=2,048 search box")
P("   this cut (7 of 31 in-box pairs have their double in-box, including")
P("   the smallest); the carried scoreboard is session 24 (b) SPLIT,")
P("   session 25 (a) AGREE, session 26 (b) SPLIT, session 27 (a) AGREE --")
P("   two splitting grids and two agreeing grids,")
P("   threshold-artifact-vs-representation UNRESOLVED; whether a split")
P("   recurs here is MEASURED HERE):")
P(f"     eq3 class {CLASS['eq3']} == mid class {CLASS['mid']}: "
  f"{CLASS['eq3'] == CLASS['mid']}")
P(f"     eq3 (sum,128,S=16) pooled median {veq3:.0f} within +/-5% of mid "
  f"{vmid:.0f}: {c3_num_ok}")
if c3_ok:
    P("     VERDICT: branch (a) -- at the bisect grid the same-ratio")
    P("     representation (810,3182) is behaviourally equivalent to")
    P("     (405,1591) (MEASURED at this one grid point and B only; nothing")
    P("     is assumed for any other pair beyond the source reading that")
    P("     N_ELEMENTS is the only knob-derived quantity -- protocol L8).")
else:
    P("     VERDICT: branch (b) -- the same-ratio representation matters at")
    P("     this grid; the contradiction stands as measured content, is NOT")
    P("     resolved here, and mid/b2m carry the flagged risk.")
P("")

# W1 the row question
vb2m = pooled("b2m", sum128)
P("   W1 THE ROW QUESTION (the bisect: class(mid) at B=3, n=254,557 =")
P("   the EXACT floor midpoint of (253,906, 255,208] -- reachable at the")
P("   knob (31 in-box pairs, smallest (405,1591), knob-search-s119.py);")
P("   the bracket ends are this session's lo/hi -- C2 governs their")
P("   validity):")
P(f"     class(mid) = {CLASS['mid']} (mid (sum,128,S=16) pooled median "
  f"{vmid:.0f},")
P(f"     18-cell min..max {min(pooled('mid', k) for k in ok_cells):.0f}.."
  f"{max(pooled('mid', k) for k in ok_cells):.0f})")
if not c2_ok:
    w1 = "(d)"
    P("     VERDICT: branch (d) FLAGGED -- C2 fired (b) (bracket ends did")
    P("     not replicate in-session); the measured classes stand as content")
    P("     and no bracket narrowing is claimed. ONE session; L2 binds;")
    P("     NO causal mechanism is claimed or measured.")
elif CLASS["mid"] == "CAPTURED":
    w1 = "(a)"
    P("     VERDICT: branch (a) MID-CAPTURED -- the B=3 class flip sits in")
    P("     (253,906, 254,557] n-units = (0.2539052, 0.2545562] work-units")
    P("     among measured grid points -- the bracket's LOWER half; the flip")
    P("     threshold in per-dispatch work sits in (0.2539052, 0.2545562].")
    P("     ONE session; L2 co-variation binds at fixed B=3; nothing between")
    P("     grid points is interpolated (L5); NO causal mechanism is claimed")
    P("     or measured.")
elif CLASS["mid"] == "INTERMEDIATE/MIXED":
    w1 = "(b)"
    P("     VERDICT: branch (b) MID-INTERMEDIATE -- the B=3 class flip sits")
    P("     in (254,557, 255,208] n-units = (0.2545562, 0.2552072]")
    P("     work-units among measured grid points -- the bracket's UPPER")
    P("     half; the flip threshold in per-dispatch work sits in")
    P("     (0.2545562, 0.2552072]. ONE session; L2 binds; L5 no")
    P("     interpolation; NO causal mechanism is claimed or measured.")
elif CLASS["mid"] == "FLOOR":
    w1 = "(c)"
    P("     VERDICT: branch (c) MID-FLOOR NON-MONOTONE CONTRADICTION")
    P("     (named in advance, protocol section 5): mid FLOOR at n=254,557")
    P("     between the smaller n=253,906 point (lo) and the larger")
    P("     n=255,208 point (hi) -- the committed monotone B=3 picture is")
    P("     contradicted at this session; the contradiction stands as")
    P("     measured content and is NOT resolved here (L5). ONE session;")
    P("     NO causal mechanism is claimed or measured.")
else:
    w1 = "(d)"
    P("     VERDICT: branch (d) FLAGGED (no other letter applies).")
P(f"     b2m (B=2 control at the bisect n) class {CLASS['b2m']} (b2m "
  f"(sum,128,S=16)")
P(f"     pooled median {vb2m:.0f}): "
  + ("'B=2 never captures' extends to n=254,557 at total work 0.5091125 "
     f"(committed b2m-class want: {B2M_WANT})."
     if CLASS["b2m"] == "FLOOR" else
     "CONTRADICTION named in advance -- 'B=2 never captures' does NOT hold "
     "at n=254,557; not resolved here."))
P("")

# W2 the row (descriptive)
P("   W2 (pre-registered, descriptive) THE B=3 CLASS-VS-PER-DISPATCH-")
P("   WORK ROW: this cut's three B=3 points placed on the committed row as")
P("   grid points (the committed points QUOTE-ONLY, parsed from s27's")
P("   committed publication table; NO interpolation (L5); class")
P("   granularity only; * = the session-26 point carries its C3 (b)")
P("   caveat / was SETTLED OVER to INTERMEDIATE/MIXED by the bar):")
P("")
P("     n          work-unit     ticks  class                source")
for lbl, n, ticks, cls, src in B3ROW:
    mark = "*" if n == 253906 else ""
    P(f"     {n:<10} {lbl:<13} {ticks:>5}  {cls + mark:<20} {src} "
      f"(quote-only)")
P(f"     253906     0.2539052     {vlo:>5.0f}  {CLASS['lo']:<20} this "
  f"session (lo, == the bar-SETTLED (1024,4033) anchor)")
P(f"     254557     0.2545562     {vmid:>5.0f}  {CLASS['mid']:<20} THIS "
  f"SESSION (mid, the bisect point)")
P(f"     255208     0.2552072     {vhi:>5.0f}  {CLASS['hi']:<20} this "
  f"session (hi, == the committed (1213,4753) pair)")
P("")

# W3 paired equal-grid comparisons (descriptive)
P("   W3 (pre-registered, descriptive) THE PAIRED EQUAL-GRID COMPARISONS:")
P(f"     (i) mid vs eq3 (identical n=254,557 and B=3; differ only in the")
P(f"         (WORK_MUL,NDIV) representation (405,1591) vs (810,3182)): "
  f"{vmid:.0f} vs")
P(f"         {veq3:.0f} at (sum,128,16); classes {CLASS['mid']} vs "
  f"{CLASS['eq3']}")
P(f"     (ii) mid vs b2m (identical n=254,557 and pair (405,1591); differ "
  f"only")
P(f"         in B 3 vs 2): {vmid:.0f} vs {vb2m:.0f}; classes "
  f"{CLASS['mid']} vs {CLASS['b2m']}")
P(f"     (iii) lo vs mid vs hi (identical B=3; differ only in n/pair):"
  f" {vlo:.0f} / {vmid:.0f} / {vhi:.0f}; classes {CLASS['lo']} / "
  f"{CLASS['mid']} / {CLASS['hi']}")
P("")

# X1 host_ns (descriptive)
hn = {t: pooled_host(t, sum128) for t in TAGS}
P("   X1 (descriptive, host_ns at (sum,128,S=16)):")
P("     " + ", ".join(f"{t} {hn[t]:.0f}" for t in TAGS))
P(f"     same-knob comparisons (the parsed s26 census row and s27 "
  f"publication row, quote-only):")
P(f"     lo {hn['lo']:.0f} = {hn['lo'] / S26HN['mid']:.3f}x session-26's "
  f"same-knob mid ({S26HN['mid']:,}) = {hn['lo'] / S27HN['hi']:.3f}x "
  f"session 27's same-knob hi ({S27HN['hi']:,}) -- the (1024,4033) pair's "
  f"host_ns observations.")
P(f"     hi {hn['hi']:.0f} = {hn['hi'] / S26HN['hi']:.3f}x session-26's "
  f"same-knob hi ({S26HN['hi']:,}) -- the (1213,4753) pair's prior host_ns "
  f"observation (s27 did not run the pair).")
P(f"     c2 {hn['c2']:.0f} = {hn['c2'] / S26HN['c2']:.3f}x session 26's "
  f"({S26HN['c2']:,}) = {hn['c2'] / S27HN['c2']:.3f}x session 27's "
  f"({S27HN['c2']:,}); c8 {hn['c8']:.0f} = "
  f"{hn['c8'] / S26HN['c8']:.3f}x session 26's ({S26HN['c8']:,}) = "
  f"{hn['c8'] / S27HN['c8']:.3f}x session 27's ({S27HN['c8']:,}).")
P(f"     mid {hn['mid']:.0f}, eq3 {hn['eq3']:.0f}, b2m {hn['b2m']:.0f} "
  f"first measured here (their knob pairs are new). host_ns is the "
  f"HOST-side")
P("     proxy (L3), not a C criterion; any excursion is NAMED, NOT HIDDEN")
P("     and its cause is UNMEASURED.")
P("")

P("4. VERDICT SUMMARY: C1 (a)={0}; C2 (a)={1}; C3 (a)={2}; W1 {3}.".format(
    c1_ok, c2_ok, c3_ok, w1))
P("   The named-hypothesis discrimination of the row question is as W1")
P("   states; WHY is UNMEASURED and NO causal mechanism is claimed.")
P("   BAR NON-INTERFERENCE (frozen protocol section 6): these runs are")
P("   BISECT CONTENT and NOT bar readings -- NO settle-bar-ledger.txt")
P("   append, NO UTC-day slot consumption, NO movement of the bar's")
P("   SETTLED verdict, NO Rule 4 workgroup row or :measured? flag change.")

with open(os.path.join(HERE, "publication-s121.txt"), "w") as f:
    f.write("\n".join(out) + "\n")
