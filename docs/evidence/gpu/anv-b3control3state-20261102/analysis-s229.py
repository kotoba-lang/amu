#!/usr/bin/env python3
"""analysis-s229.py -- THE OPEN CONTROL QUESTION'S RESOLUTION ACT:
THE ANALYSIS HALF (session 229).

Reads ONLY (fail-closed; every want source parsed from committed
bytes, never transcribed):
  - the 24 committed run logs of the s225 measurement window in this
    directory (run-rd<rd>-<arm>-r<NN>.txt.gz -- the committed gzip -n
    form, READ THROUGH GZIP, the s157 capture-form deviation; custody
    of these bytes is the s228 pull: pull-verify-s225.py run twice
    byte-identical over the committed tree) and their 24 committed
    0-byte .stderr.txt siblings;
  - the s27 controls census (anv-b3bisect7-20261027/
    derivation-census-s27.txt: the committed floor band and the c8
    reference);
  - the four committed control-record publications' C1 blocks
    (publication-s169.txt / -s185.txt / -s197.txt / -s209.txt);
  - the frozen protocol's record-shape line and threshold literals
    (anv-b3control3state-prereg-20261102/protocol.txt, freeze stamp
    2026-11-02T10:48:32Z -- written once BEFORE any run of the act
    existed).

Writes ONLY publication-s229.txt (this directory).  Prints nothing to
stdout/stderr on success.

FROZEN DERIVATION (protocol.txt, ADOPTED UNCHANGED -- computed, never
re-derived): per reading per arm, m = pooled sample median gpu_ticks
over k=3 runs x R rounds at cell (sum, W=128, S=16), N = 3R =
19,200; MAD = sample median |x - m|; h = 3.6420 * MAD / sqrt(N)
(1.96 * 1.2533 * 1.4826 = 3.6420, frozen formula; h is descriptive,
NEVER a letter input).  The letters (s218, frozen): alphabet EXACTLY
{a,b}; the letter is a function of the pooled median m against the
committed floor band 31..32 at B=2 ONLY; the letter domain is c8
within +/-5% of the committed 32,915 (session 4 pooled median) plus
the control arms VERIFY-mismatch-free.  Reading-level FAIL-CLOSED,
all-or-nothing (s219, frozen): a non-evaluable reading gives the act
NO letters at all and the verdict literal "ACT VERDICT: INVALID"; NO
selective re-run.  Every resolution-act quantity below is COMPUTED
FRESH from the committed bytes at each run of this script.
"""

import gzip
import hashlib
import math
import os
import re
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
GPU = os.path.dirname(HERE)

R = 6400                       # frozen rounds (the ROUNDS6400 variant)
WARMUP = 3
N_BASE = 1000003
H_CONST = 3.6420               # frozen CI constant (1.96 * 1.2533 * 1.4826)
TICK_NS = 52.083               # timestampPeriod (asserted against the logs)
CAP_MIN = 1000                 # frozen unit-class threshold (ticks)
FLOOR_MAX = 100                # frozen unit-class threshold (ticks)
CELL = ("sum", 128, "16")      # the reading cell (sum, W=128, S=16)
ARMS = (("c2", 2), ("c8", 8))  # (tag, batch) -- the s217 frozen arms
READINGS = (1, 2, 3, 4)        # the s217 frozen four readings
K = 3                          # runs per arm per reading


def fmt(v):
    if isinstance(v, str):
        return v
    if float(v).is_integer():
        return str(int(v))
    return f"{v:.1f}"


def f4(v):
    return f"{v:.4f}"


def flat(text):
    return re.sub(r"\s+", " ", text)


def parse1(text, pattern, what):
    m = re.search(pattern, flat(text))
    assert m is not None, f"WANT SOURCE NOT PARSED: {what}"
    return m.group(1).strip()


def dp_class(cell_stats):
    """THE DEEP-POOLING CI CLASS STATISTIC (protocol section 6 quote;
    the frozen 1,000-tick threshold).  cell_stats: iterable of
    (m_c, h_c) over the 18 pipeline-ok cells.  Class descriptor only
    at this act (s218 4(d)) -- not a letter input."""
    if all(m - h >= CAP_MIN for m, h in cell_stats):
        return "CAPTURED"
    if all(m + h <= FLOOR_MAX for m, h in cell_stats):
        return "FLOOR"
    if (any(m + h < CAP_MIN for m, h in cell_stats)
            and any(m - h > FLOOR_MAX for m, h in cell_stats)):
        return "INTERMEDIATE/MIXED"
    return "IN-BAND-UNDECIDED"


# ---- NAMED COMMITTED WANT SOURCES (parsed from committed bytes,
# ---- never transcribed; fail-closed) ----
s27c = open(os.path.join(GPU, "anv-b3bisect7-20261027",
                         "derivation-census-s27.txt")).read()
pub169 = open(os.path.join(GPU, "anv-b3bisect16-20261101",
                           "publication-s169.txt")).read()
pub185 = open(os.path.join(GPU, "anv-b3bisect17-20261101",
                           "publication-s185.txt")).read()
pub197 = open(os.path.join(GPU, "anv-b3bisect18-20261101",
                           "publication-s197.txt")).read()
pub209 = open(os.path.join(GPU, "anv-b3bisect19-20261102",
                           "publication-s209.txt")).read()
proto = open(os.path.join(GPU, "anv-b3control3state-prereg-20261102",
                          "protocol.txt")).read()

# committed controls (s27 census): "committed controls: c2 31 (floor
# band 31..32); c8 32,915 (session 4 pooled median)"
ctl = parse1(s27c, r"(committed controls: c2 \d+ \(floor band [\d.]+\.[\d.]+\); "
                   r"c8 [\d,]+ \(session 4 pooled median\))", "committed controls")
m = re.search(r"c2 (\d+) \(floor band (\d+)\.\.(\d+)\); c8 ([\d,]+)", ctl)
assert m, "committed controls shape"
C2_COMMITTED = int(m.group(1))
C2_BAND = (int(m.group(2)), int(m.group(3)))
C8_COMMITTED = int(m.group(4).replace(",", ""))
C8_TOL = 0.05
assert C2_BAND == (31, 32), C2_BAND
assert C8_COMMITTED == 32915, C8_COMMITTED

# the frozen protocol's threshold literals (cross-check the census)
assert "committed floor band 31..32 at B=2" in flat(proto), "protocol band literal"
assert "32,915" in proto, "protocol c8 literal"
assert "3.6420" in proto, "protocol h-constant literal"
assert "freeze stamp\n2026-11-02T10:48:32Z" in proto or \
    "2026-11-02T10:48:32Z" in proto, "protocol freeze stamp"

# the four committed control-record C1 blocks (one per publication;
# fail-closed: exactly one block match per publication)
C1_RE = re.compile(
    r"^     c2 \(sum,128,S=16\) pooled median m ([\d.]+), deep-pooling\n"
    r"     class FLOOR \(committed floor band (\d+)\.\.(\d+) at B=2\): (True|False)\n"
    r"     c8 \(sum,128,S=16\) pooled median m ([\d.]+) within \+/-5% of committed ([\d,]+) "
    r"\(session 4 pooled median\): (True|False) \(([-+\d.]+)%\)\n"
    r"     control arms free of VERIFY mismatches \(frozen INVALIDATION criterion\): (True|False)\n"
    r"     VERDICT: branch \((\w)\)", re.M)


def c1_block(pub, tag):
    ms = C1_RE.findall(pub)
    assert len(ms) == 1, f"record C1 block count {len(ms)} in {tag}"
    (m_c2, blo, bhi, c2bool, m_c8, ref, c8bool, pct, armbool,
     branch) = ms[0]
    assert (int(blo), int(bhi)) == C2_BAND, f"{tag} band"
    assert int(ref.replace(",", "")) == C8_COMMITTED, f"{tag} c8 ref"
    return dict(m_c2=float(m_c2), c2bool=(c2bool == "True"),
                m_c8=float(m_c8), c8bool=(c8bool == "True"),
                pct=float(pct), armbool=(armbool == "True"),
                letter="(" + branch + ")")


RECORD = [c1_block(pub169, "s169"), c1_block(pub185, "s185"),
          c1_block(pub197, "s197"), c1_block(pub209, "s209")]
RECORD_LETTERS = [r["letter"] for r in RECORD]
RECORD_MEDIANS = [r["m_c2"] for r in RECORD]
# the frozen protocol's own record-shape line (second construction)
m = re.search(r"the C1 letter sequence is \((\w)\) / \((\w)\) / \((\w)\) / \((\w)\)",
              flat(proto))
assert m, "protocol record letter sequence"
assert list(m.groups()) == [l[1] for l in RECORD_LETTERS], "record letters 2-way"
m = re.search(r"c2 pooled medians (\d+) / (\d+) / (\d+) / (\d+)", flat(proto))
assert m, "protocol record medians"
assert [float(x) for x in m.groups()] == RECORD_MEDIANS, "record medians 2-way"
assert RECORD_LETTERS == ["(b)", "(a)", "(a)", "(b)"], RECORD_LETTERS
assert RECORD_MEDIANS == [30.0, 31.0, 31.0, 30.0], RECORD_MEDIANS

# ---- run-log parsing (the record's own check shape: the s169
# ---- load/load_run machinery; cell/verify counts, tail, header knob
# ---- fields, SAMPLE lines per run) ----
cell_re = re.compile(
    r"^CELL idx=(\d+) spv=(\S+) op=(\S+) wg=(\d+) forced=(\S+) probe_size=(-?\d+) "
    r"probe_nsub=(-?\d+) probe_wg=(-?\d+) pipeline=(\S+) void=(\d)")
verify_re = re.compile(r"^VERIFY idx=(\d+) checked=(\d+) mismatch=(\d+) ok=(\d)")
SAMPLE_FIELDS = ("round=", "idx=", "batch=", "work_mul=", "ndiv=",
                 "gpu_ticks=", "gpu_ns=", "per_dispatch_ns=", "host_ns=")


def load(path, b):
    """One committed run log, READ THROUGH GZIP.  Returns
    (cells, verifies, header, ticks, counts) with ticks as int lists."""
    cells, verifies, header = {}, [], []
    ticks, counts = {}, {}
    with gzip.open(path, "rt") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("#"):
                header.append(line)
                continue
            if line.startswith("CELL "):
                mm = cell_re.match(line)
                assert mm, line
                cells[int(mm.group(1))] = dict(
                    spv=mm.group(2), op=mm.group(3), wg=int(mm.group(4)),
                    forced=mm.group(5), pipeline=mm.group(9),
                    void=int(mm.group(10)))
                continue
            if line.startswith("VERIFY "):
                mm = verify_re.match(line)
                assert mm, line
                verifies.append((int(mm.group(1)), int(mm.group(2)),
                                 int(mm.group(3)), int(mm.group(4))))
                continue
            assert line.startswith("SAMPLE "), line
            f = line.split(" ")
            assert len(f) == 10, line
            assert f[0] == "SAMPLE", line
            for i in range(1, 10):
                assert f[i].startswith(SAMPLE_FIELDS[i - 1]), line
            idx = int(f[2][4:])
            gt = int(f[6][10:])
            float(f[7][7:])
            float(f[8][16:])
            int(f[9][8:])
            assert (int(f[3][6:]) == b and int(f[4][9:]) == 1
                    and int(f[5][5:]) == 1), line
            ticks.setdefault(idx, []).append(gt)
            counts[idx] = counts.get(idx, 0) + 1
    return cells, verifies, header, ticks, counts


def load_run(path, b):
    cells, verifies, header, ticks, counts = load(path, b)
    s128 = [k for k, v in cells.items()
            if (v["op"], v["wg"], v["forced"]) == CELL]
    assert len(s128) == 1, f"reading-cell count {s128}"
    integrity = []
    ok = True
    if len(cells) != 24:
        ok = False
        integrity.append(f"CELL COUNT {len(cells)} != 24")
    if len(verifies) != 24:
        ok = False
        integrity.append(f"VERIFY COUNT {len(verifies)} != 24")
    if "# done cells=24" not in header:
        ok = False
        integrity.append("TAIL MISSING")
    for l in header:
        if l.startswith("# n="):
            mb = re.search(r"batch=(\d+)", l)
            mbar = re.search(r"barrier_n=(\d+)", l)
            mmu = re.search(r"work_mul=(\d+)", l)
            mdi = re.search(r"ndiv=(\d+)", l)
            mn = re.search(r"n=(\d+)", l)
            mro = re.search(r"rounds=(\d+)", l)
            mwa = re.search(r"warmup=(\d+)", l)
            if (not mb or int(mb.group(1)) != b
                    or not mbar or int(mbar.group(1)) != 0
                    or not mmu or int(mmu.group(1)) != 1
                    or not mdi or int(mdi.group(1)) != 1
                    or not mro or int(mro.group(1)) != R
                    or not mwa or int(mwa.group(1)) != WARMUP
                    or not mn or int(mn.group(1)) != N_BASE):
                ok = False
                integrity.append(f"HEADER knob FIELD MISMATCH: {l}")
    if not any("timestampPeriod=52.083" in l for l in header):
        ok = False
        integrity.append("timestampPeriod PIN MISMATCH")
    for kk, v in cells.items():
        if not (v["spv"].endswith(".emitted.spv") and ".iter" not in v["spv"]):
            ok = False
            integrity.append(f"CELL spv SET MISMATCH idx={kk}: {v['spv']}")
    ok_cells = sorted(k for k, v in cells.items() if v["pipeline"] == "ok")
    if len(ok_cells) != 18:
        ok = False
        integrity.append(f"OK CELL COUNT {len(ok_cells)} != 18")
    exp = len(ok_cells) * R
    if sum(counts.values()) != exp:
        ok = False
        integrity.append(f"SAMPLE COUNT {sum(counts.values())} != {exp}")
    for kk in ok_cells:
        if counts.get(kk, 0) != R:
            ok = False
            integrity.append(f"SAMPLE COUNT idx={kk} {counts.get(kk, 0)} != {R}")
    fail_cells = sorted(k for k, v in cells.items() if v["pipeline"] == "FAIL")
    for kk in fail_cells:
        if kk in ticks:
            ok = False
            integrity.append(f"FAIL CELL HAS SAMPLES idx={kk}")
    mismatches = sum(t[2] for t in verifies)
    cell_map = tuple(sorted((kk, v["spv"], v["op"], v["wg"], v["forced"],
                             v["pipeline"], v["void"])
                            for kk, v in cells.items()))
    return dict(cells=cells, verifies=verifies, header=header, ticks=ticks,
                counts=counts, s128=s128[0], ok_cells=ok_cells,
                fail_cells=fail_cells, ok=ok, integrity=integrity,
                mismatches=mismatches, cell_map=cell_map)


# ---- the 24 committed run logs (the frozen run names; the frozen
# ---- protocol fixes the run ORDER, the s225 names are the committed
# ---- capture names) ----
runs = {}
for rd in READINGS:
    for tag, b in ARMS:
        for nn in range(1, K + 1):
            name = f"run-rd{rd}-{tag}-r{nn:02d}.txt.gz"
            path = os.path.join(HERE, name)
            assert os.path.exists(path), f"RUN LOG MISSING: {name}"
            runs[(rd, tag, nn)] = load_run(path, b)

# run-count self-check (the s219 1(b) act check shape)
assert len(runs) == 24, len(runs)
gz_present = sorted(f for f in os.listdir(HERE)
                    if f.startswith("run-") and f.endswith(".txt.gz"))
assert len(gz_present) == 24, f"gzip run-log census {len(gz_present)}"
err_present = sorted(f for f in os.listdir(HERE)
                     if f.startswith("run-") and f.endswith(".stderr.txt"))
assert len(err_present) == 24, f"stderr census {len(err_present)}"
err_nonzero = [f for f in err_present
               if os.path.getsize(os.path.join(HERE, f)) != 0]

# cell map identical across runs (the act check shape)
maps = set(r["cell_map"] for r in runs.values())
assert len(maps) == 1, f"cell map differs across runs ({len(maps)} maps)"
map_pin = hashlib.sha256(repr(sorted(maps.pop())).encode()).hexdigest()
s128_idx = set(r["s128"] for r in runs.values())
assert len(s128_idx) == 1, s128_idx
S128 = s128_idx.pop()
assert runs[(1, "c2", 1)]["cells"][S128]["pipeline"] == "ok"

# ---- the per-reading pooled statistic (the frozen formula) ----
def pooled_stats(runs3, idx):
    xs = []
    for r in runs3:
        xs.extend(r["ticks"][idx])
    N = len(xs)
    assert N == K * R, N
    m_ = statistics.median(xs)
    mad = statistics.median([abs(x - m_) for x in xs])
    h_ = H_CONST * mad / math.sqrt(N)
    return N, m_, mad, h_


reading = {}
for rd in READINGS:
    ent = {}
    for tag, b in ARMS:
        r3 = [runs[(rd, tag, nn)] for nn in range(1, K + 1)]
        ent[tag] = dict(zip(("N", "m", "mad", "h"), pooled_stats(r3, S128)))
        ent[tag]["runs"] = r3
        ent[tag]["mismatch"] = sum(r["mismatches"] for r in r3)
        ent[tag]["integrity_ok"] = all(r["ok"] for r in r3)
        # class descriptor over the 18 pipeline-ok cells (k=3 unit)
        cell_stats = []
        for kk in r3[0]["ok_cells"]:
            _, m_c, _, h_c = pooled_stats(r3, kk)
            cell_stats.append((m_c, h_c))
        ent[tag]["cls"] = dp_class(cell_stats)
    reading[rd] = ent

# ---- letters (the s218 frozen derivation) ----
letters = {}
letter_rows = {}
for rd in READINGS:
    ent = reading[rd]
    v_c2, v_c8 = ent["c2"]["m"], ent["c8"]["m"]
    band_ok = C2_BAND[0] <= v_c2 <= C2_BAND[1]
    c8_ok = abs(v_c8 - C8_COMMITTED) <= C8_TOL * C8_COMMITTED
    arm_ok = (ent["c2"]["mismatch"] == 0 and ent["c8"]["mismatch"] == 0
              and ent["c2"]["integrity_ok"] and ent["c8"]["integrity_ok"])
    # the record's own C1 c2 boolean derivation (analysis-s209.py
    # L1228: deep-pooling class FLOOR AND m in band) -- reported for
    # one-for-one confrontation; the FROZEN act letter derivation is
    # m against the band ONLY (s218 1(c)) and governs the letter.
    record_derivation_ok = ent["c2"]["cls"] == "FLOOR" and band_ok
    in_domain = c8_ok and arm_ok
    letter_rows[rd] = dict(v_c2=v_c2, v_c8=v_c8, band_ok=band_ok,
                           c8_ok=c8_ok, arm_ok=arm_ok,
                           record_derivation_ok=record_derivation_ok,
                           in_domain=in_domain)
    if not in_domain:
        letters[rd] = None
    else:
        letters[rd] = "(a)" if band_ok else "(b)"

evaluable = all(letters[rd] is not None for rd in READINGS)
act_invalid = not evaluable

# ---- B_act / block shape (the s220 2(a) block rule) ----
def block_reading(seq):
    blocks = []
    for l in seq:
        if blocks and blocks[-1][-1] == l:
            blocks[-1].append(l)
        else:
            blocks.append([l])
    return blocks


if not act_invalid:
    SEQ = [letters[rd] for rd in READINGS]
    BLOCKS = block_reading(SEQ)
    B_act = len(BLOCKS)
    I_act = len(set(SEQ))
    shape = " | ".join("(" + ",".join(l[1] for l in blk) + ")"
                       for blk in BLOCKS)
else:
    SEQ, BLOCKS, B_act, I_act, shape = None, None, None, None, None

RECORD_SHAPE = "(b) | (a,a) | (b)"
B_record = 3

out = []
P = out.append
P("JUN-59 -- THE OPEN CONTROL QUESTION'S RESOLUTION ACT: THE")
P("ANALYSIS HALF (session 229) -- the four per-reading c2/c8 pooled")
P("medians under the frozen deep-pooling CI class statistic")
P("(R = 6,400), the letters L1..L4 under the frozen alphabet {a,b},")
P("B_act, and the act verdict under the frozen invalidation")
P("criteria, computed ONLY from the 24 committed run logs of the")
P("s225 measurement window (this directory -- the committed gzip -n")
P("form run-rd<rd>-<arm>-r<NN>.txt.gz, READ THROUGH GZIP, the s157")
P("capture-form deviation; custody of these bytes is the s228 pull:")
P("pull-verify-s225.py run twice byte-identical over the committed")
P("tree) under the frozen anv-b3control3state-prereg-20261102/")
P("protocol.txt (freeze stamp 2026-11-02T10:48:32Z, written ONCE")
P("BEFORE any run of the act existed).")
P("Produced ONLY by analysis-s229.py over those 24 committed run")
P("logs and the NAMED COMMITTED WANT SOURCES parsed fail-closed")
P("below (the s27 controls census; the four committed control-record")
P("publications' C1 blocks; the frozen protocol's record-shape line")
P("and threshold literals). No resolution-act quantity is")
P("transcribed -- every median, letter, count and verdict below is")
P("computed fresh from the committed bytes at each run of this")
P("script.")
P("")
P("1. INTEGRITY (the s219 1(b) act check shape, ADOPTED from the")
P("   record: run-count self-check; per-log integrity cell/verify")
P("   counts, tail, header knob fields, SAMPLE lines per run; cell")
P("   map identical across runs):")
integ_all = all(r["ok"] for r in runs.values())
tail_all = sum(1 for r in runs.values()
               if "# done cells=24" in r["header"])
samples_all = sum(1 for r in runs.values()
                  if sum(r["counts"].values()) == 18 * R
                  and all(r["counts"].get(kk, 0) == R for kk in r["ok_cells"]))
fail_cell_runs = sum(len(r["fail_cells"]) for r in runs.values())
P(f"   runs parsed: 24 (c2 x12, c8 x12 -- four readings x (c2 k=3 +")
P(f"   c8 k=3); run-count self-check 4*(3+3) = 24 -> True)")
P(f"   cell map identical across runs: True (map pin sha256 {map_pin})")
P(f"   all per-log integrity checks pass: {integ_all}")
P(f"   tail '# done cells=24' in {tail_all}/24 runs: {tail_all == 24}")
P(f"   SAMPLE lines: 115,200 per run (18 ok cells x 6,400 rounds) in")
P(f"   {samples_all}/24 runs: {samples_all == 24}")
P(f"   forced=8 cells fail-closed (pipeline=FAIL): {fail_cell_runs}")
P(f"   cell-runs (6 per run x 24 runs = 144 expected -- fail-closed,")
P(f"   never read as data)")
P(f"   committed .stderr.txt siblings: {len(err_present)}/24 present,")
P(f"   0 bytes {24 - len(err_nonzero)}/24")
tot_mis = sum(r["mismatches"] for r in runs.values())
per_arm_mis = {t: sum(r["mismatches"] for (rd, tg, nn), r in runs.items()
                      if tg == t) for t, _ in ARMS}
per_rd_mis = [sum(r["mismatches"] for (rd, tg, nn), r in runs.items()
                  if rd == q) for q in READINGS]
P(f"   VERIFY mismatch total over all runs: {tot_mis} (per-arm:")
P(f"   c2={per_arm_mis['c2']}, c8={per_arm_mis['c8']}; per-reading")
P(f"   {'/'.join(str(x) for x in per_rd_mis)}) -- the frozen")
P(f"   INVALIDATION criterion (s219 2(a)): > 0 in any run makes that")
P(f"   run DEFECTIVE and the arm INVALID.")
P("")
P("2. THE PER-READING POOLED STATISTIC (the frozen formula, ADOPTED")
P("   UNCHANGED: each arm's quantity per reading is the pooled sample")
P("   median m over k=3 runs x R rounds at cell (sum, W=128, S=16),")
P(f"   N = 3R = {3 * R:,}; MAD = sample median |x - m|; h = 3.6420 *")
P("   MAD / sqrt(N); h is descriptive ONLY, never a letter input):")
for rd in READINGS:
    ent = reading[rd]
    for tag, _ in ARMS:
        e = ent[tag]
        P(f"   reading {rd} {tag} N={e['N']:,} m={fmt(e['m'])} "
          f"mad={fmt(e['mad'])} h={f4(e['h'])}")
P("")
P("3. THE LETTERS L1..L4 (the s218 frozen derivation; the letter is")
P("   a function of the pooled median m against the committed floor")
P("   band 31..32 at B=2 ONLY (s218 1(c)); the c2 line's boolean is")
P("   the band check on m; the deep-pooling class is the line's")
P("   CLASS DESCRIPTOR only (s218 4(d))):")
for i, rd in enumerate(READINGS):
    row = letter_rows[rd]
    ent = reading[rd]
    P(f"   reading {rd} (the L{rd} slot beside the record's "
      f"{('16th', '17th', '18th', '19th')[i]} cut's {RECORD_LETTERS[i]}):")
    P(f"     c2 (sum,128,S=16) pooled median m {fmt(row['v_c2'])}, "
      f"deep-pooling")
    P(f"     class FLOOR (committed floor band {C2_BAND[0]}..{C2_BAND[1]} "
      f"at B=2): {row['band_ok']}")
    pct = (row['v_c8'] - C8_COMMITTED) / C8_COMMITTED * 100
    P(f"     c8 (sum,128,S=16) pooled median m {fmt(row['v_c8'])} "
      f"within +/-5% of committed {C8_COMMITTED} (session 4 pooled "
      f"median): {row['c8_ok']} ({pct:+.2f}%)")
    P(f"     control arms free of VERIFY mismatches (frozen "
      f"INVALIDATION criterion): {row['arm_ok']}")
    P(f"     reading evaluable (both arms valid under (a) + in the s218")
    P(f"     letter domain): {row['in_domain']}")
    P(f"     deep-pooling class descriptor (c2 unit, 18 cells, k=3 x R):"
      f" {ent['c2']['cls']}; the record's own C1 derivation (class")
    P(f"     FLOOR AND m in band, analysis-s209.py L1228) gives"
      f" {row['record_derivation_ok']}; agreement with the frozen")
    P(f"     band-only boolean:"
      f" {row['record_derivation_ok'] == row['band_ok']}")
    if row['in_domain']:
        P(f"     L{rd} = {letters[rd]} (s218 1(c): letter = f(m against")
        P(f"     the band) only -> m {fmt(row['v_c2'])} "
          f"{'in' if row['band_ok'] else 'OUT of'} committed floor band"
          f" {C2_BAND[0]}..{C2_BAND[1]} at B=2)")
    else:
        P(f"     L{rd} = NO LETTER (out of the s218 letter domain or")
        P(f"     VERIFY-invalid/integrity-failed arm; s219 2(b): the")
        P(f"     whole ACT is FAIL-CLOSED INVALID -- NO partial sequence)")
P("")
P("4. THE SEQUENCE, B_act, AND THE FROZEN NAME'S CONFRONTATION (the")
P("   s220 2(d) rows; PATTERN-LEVEL at four readings (s218 2(e)):")
if act_invalid:
    P("   NO SEQUENCE: the act is FAIL-CLOSED at the reading level")
    P("   (s219 2(b), NAMED, NOT HIDDEN): NO partial sequence -- an act")
    P("   with one non-evaluable reading has NO letters at all (it is")
    P("   NOT a three-letter act, NOT a three-reading act).")
    P("   B_act: UNDEFINED (INVALID acts carry NO block count -- the")
    P("   threestate-s220 2(d) rule: B is undefined on an INVALID act).")
else:
    P(f"   L1..L4 = {' / '.join(SEQ)}")
    P(f"   the committed record (four-cut): {' / '.join(RECORD_LETTERS)}")
    P(f"   sequence identical to the record: {SEQ == RECORD_LETTERS}")
    P(f"   B_act (block count over L1..L4, the s220 2(a) maximal")
    P(f"   constant-letter-run rule): {B_act}")
    P(f"   act block shape: {shape}")
    P(f"   the record's block reading: {RECORD_SHAPE} (B_record = "
      f"{B_record})")
    P(f"   B_act count-level agreement with the record (B_act == "
      f"{B_record}): {B_act == B_record}")
    P(f"   shape identical to the record's {RECORD_SHAPE}: "
      f"{shape == RECORD_SHAPE}")
    P(f"   I_act (letter IDENTITIES over L1..L4): {I_act} (the s220 2(b)")
    P(f"   occurrence/identity separation: B is an occurrence count, I")
    P(f"   an identity count; the underlying-state count stays")
    P(f"   UNMEASURED and is never read off the name)")
    if B_act == B_record and shape == RECORD_SHAPE:
        P(f"   s220 2(d) row: B_act = 3 WITH the same block shape")
        P(f"   {RECORD_SHAPE} -- the frozen name's structure reproduces")
        P(f"   at act scale (count and shape both reported, neither")
        P(f"   conflated).")
    elif B_act == B_record:
        P(f"   s220 2(d) row: B_act = 3 of another shape -- count-level")
        P(f"   agreement only (count and shape both reported, neither")
        P(f"   conflated).")
    else:
        P(f"   s220 2(d) row: B_act = {B_act} in {{1, 2, 4}} -- differs")
        P(f"   from the record at count level.")
    if SEQ == ["(a)"] * 4:
        P("   s218 2(b) shape row (ALL FOUR (a)): the committed")
        P("   \"current control state\" (a quoted committed term -- the")
        P("   17th cut's C1 (a), replicated by the 18th) REPRODUCES at")
        P("   four consecutive readings; the row question's prong A")
        P("   confronts POSITIVELY for the PRESENT instrument. NAMED:")
        P("   the historical (b) readings are NOT retro-resolved; their")
        P("   cause stays UNMEASURED (L2 binds).")
    elif SEQ == ["(b)"] * 4:
        P("   s218 2(b) shape row (ALL FOUR (b)): a constant sequence of")
        P("   the (b) letter -- one present state-BLOCK of the (b)")
        P("   state-IDENTITY. NAMED, NOT HIDDEN: this does NOT confirm")
        P("   the committed \"current control state\"; constancy and")
        P("   identity are separate (the s218 separation): prong A")
        P("   requires BOTH constancy AND identity (a); an all-(b) act")
        P("   ALONE shows one present state and does not by itself")
        P("   establish two states (prong B confronts only ACROSS the")
        P("   full record).")
    else:
        P("   s218 2(b) shape row (ANY (b) among (a)s / non-constant):")
        P("   the instrument does NOT hold the (a) state-IDENTITY across")
        P("   the act's readings; prong B confronts (at least two")
        P("   readings disagree in letter within the present act); a")
        P("   mixed act replicates the record's alternation shape at act")
        P("   scale.")
P("   PATTERN-LEVEL ONLY (s218 2(e)): NO p-value, NO test statistic,")
P("   NO probability claim on any letter or sequence.")
P("   RETRO-RESOLUTION BOUNDARY (the D2 shape, s218 2(f)): the letters")
P("   read the PRESENT instrument only; no letter retro-resolves the")
P("   historical discrepancy cause (UNMEASURED, L2 binds) under every")
P("   letter sequence.")
P("   THE IDENTITY HAZARD (s216, carried): no act sequence establishes")
P("   an underlying-state count; whether m 30 is a NEW control state")
P("   or a tolerance/defect reading stays UNDECIDED (the letters")
P("   cannot close the hazard).")
P("")
P("5. ACT VERDICT (the s219 frozen invalidation criteria):")
n_eval = sum(1 for rd in READINGS if letters[rd] is not None)
P(f"   evaluable readings: {n_eval} of 4 (the s219 reading-level")
P(f"   criteria: both arms valid under (a) AND in the s218 letter")
P(f"   domain, all-or-nothing)")
if act_invalid:
    bad = [rd for rd in READINGS if letters[rd] is None]
    P(f"   non-evaluable readings: {', '.join('reading ' + str(rd) for rd in bad)}")
    P("   ACT VERDICT: INVALID (the frozen literal form, s219 2(c) --")
    P("   the W1 (d) analogue at act scale). INVALID is NOT a letter")
    P("   and NOT a state-BLOCK or state-IDENTITY reading: it confronts")
    P("   NEITHER prong of the row question; NOTHING MOVES -- the")
    P("   control question stays EXACTLY as open as before the act (the")
    P("   invalid act's content is committed as record; cause")
    P("   UNMEASURED, L2 binds). NO selective re-run (s219 2(d)): a")
    P("   replacement, if any, is a NEW named act (act 2) under the")
    P("   SAME frozen protocol with nothing re-decided after the runs")
    P("   are read.")
else:
    P("   ACT VERDICT: VALID -- every reading evaluable, the four")
    P("   letters computed under the frozen derivation. NAMED: the")
    P("   frozen protocol fixes the INVALID verdict literal only")
    P("   (s219 2(c)); \"VALID\" is this analysis's report label for an")
    P("   act with 4/4 evaluable readings, not a frozen literal; the")
    P("   confrontation content is section 4's rows (the frozen s218")
    P("   shapes and the frozen s220 2(d) rows).")
P("")
P("6. STATE / LIMITATIONS / BAR NON-INTERFERENCE:")
P("   STATE (three-state discipline): the four per-reading pooled")
P("   medians above are MEASURED quantities -- computed from the s225")
P("   hardware runs on aiueos-6600hs (Intel BMG G31) under the frozen")
P("   protocol; the letters, sequence, B_act and verdict are DERIVED")
P("   confrontations of those measured quantities under the frozen")
P("   derivation. NOT workgroup defaults: the accelerator-targets")
P("   workgroup rows stay exactly as ADR-0358 left them (:measured?")
P("   true scoped to each row's one named measured device for")
P("   :nvidia/:apple/:intel/:amd; :arm and :unknown remain provisional;")
P("   :measured? false rows remain provisional design assumptions --")
P("   NOT optimization evidence). NO vendor optimization exists for")
P("   Intel (or for any vendor); this is control-question")
P("   measurement-machinery content on ONE host's instrument question.")
P("   LIMITATIONS (the frozen protocol's): single host")
P("   (aiueos-6600hs), single instrument channel; no causal mechanism")
P("   claimed -- WHY any reading takes its letter is UNMEASURED (L2")
P("   binds) and the historical discrepancy cause stays UNMEASURED")
P("   under every outcome; the s217 named hazards carried: (a) the c2")
P("   letter boundary sits at the 1-tick median level (31 * 52.083 =")
P("   1,614.573 ns, DERIVED scale), (b) the c8 +/-5% band is loose")
P("   relative to the reference's own within-session cross-S spread")
P("   (-2.09% / -2.18%); the reading-level invalidation criteria are")
P("   untested against the record (s219 2(f) -- DESIGN, not")
P("   experience).")
P("   BAR NON-INTERFERENCE (frozen protocol section 10): NO hardware,")
P("   NO builds, NO GO stamp this tick; NO settle-bar-ledger line, NO")
P("   day-slot consumption; the bar's SETTLED INTERMEDIATE/MIXED")
P("   verdict unmoved (the s117 committed landing).")
P("   RULE 4: NOTHING MOVES -- the committed bracket stays EXACTLY")
P("   (254,923, 255,045]; L9 binds at n=254,984 (C2 (c), D3 (v)); the")
P("   MID-ONLY NARROWING CLAIM stays SUSPENDED.")
P("")

with open(os.path.join(HERE, "publication-s229.txt"), "w") as f:
    f.write("\n".join(out) + "\n")
