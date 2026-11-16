#!/usr/bin/env python3
"""verify-record-s231.py -- POST-HOC RECORD-VERIFY over the committed
captures (amu-gpu session 231, the s230 carry-forward's standing row).

THE QUESTION: does record.txt -- the s230 landing record -- hold over
the committed capture bytes?  Every number the record states is
re-derived from the committed captures by an INDEPENDENT code path
(explicit sort, middle-two even-N median -- never calling
statistics.median, never calling analysis-s229.py) and cross-checked
against the publication rows the record transcribes.

Reads ONLY committed bytes (fail-closed; every want source parsed from
committed bytes, never transcribed):
  - the 24 committed run logs of the s225 measurement window in this
    directory (run-rd<rd>-<arm>-r<NN>.txt.gz -- the committed gzip -n
    form, READ THROUGH GZIP) and their 24 committed 0-byte .stderr.txt
    siblings;
  - raw-digests-s225.txt (the s228 custody rows);
  - publication-s229.txt + publication-s229-run1.txt +
    publication-s229-run2.txt (the s229 analysis outputs);
  - record.txt (the s230 landing record);
  - ../anv-b3bisect7-20261027/derivation-census-s27.txt (the committed
    floor band and the c8 reference).

Writes NOTHING.  Prints the verification report to stdout, nothing to
stderr on success.  Exit 0 iff every check is ok (fail-closed: any
parse anomaly is an immediate abort, i.e. a failed run).

THREE-STATE: this script verifies DERIVED/transcribed rows against
MEASURED capture bytes; it measures nothing new on hardware and adds
no vendor optimization.  No workgroup default is touched.
"""

import gzip
import hashlib
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GPU = os.path.dirname(HERE)

PUB_SHA = "040ee2f60b601d9fb77d3ed044856d93549fa4bb0d10d12a8564ec6c9d3eb96d"
PUB_SIZE = 11026
R = 6400                       # frozen rounds (ROUNDS6400 variant)
N_POOL = 3 * R                 # 19,200 -- pooled N per reading per arm
H_CONST = 3.6420               # frozen CI constant (1.96 * 1.2533 * 1.4826)
CELL = ("sum", 128, "16")      # the reading cell (op, wg, forced)
ARMS = (("c2", 2), ("c8", 8))  # (tag, batch) -- the s217 frozen arms
RDS = (1, 2, 3, 4)

RESULTS = []                   # (ok_flag, description)


def check(desc, cond):
    RESULTS.append((bool(cond), desc))
    print(("ok   " if cond else "FAIL ") + desc)


def flat(s):
    return re.sub(r"\s+", " ", s)


def fmt_num(x):
    xf = float(x)
    return str(int(xf)) if xf.is_integer() else repr(xf)


def median_sorted(vals):
    """Sample median via explicit sort; even N = mean of the two middle
    values (the statistics.median convention -- the s229 cross-check)."""
    s = sorted(vals)
    n = len(s)
    assert n > 0
    if n % 2:
        return float(s[n // 2])
    return (s[n // 2 - 1] + s[n // 2]) / 2.0


def sha_stream(path, gunzip):
    h = hashlib.sha256()
    n = 0
    if gunzip:
        fh = gzip.open(path, "rb")
    else:
        fh = open(path, "rb")
    with fh:
        while True:
            chunk = fh.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
            n += len(chunk)
    return h.hexdigest(), n


CELL_RE = re.compile(
    r"^CELL idx=(\d+) spv=(\S+) op=(\S+) wg=(\d+) forced=(\S+) ")

print("== verify-record-s231.py -- POST-HOC RECORD-VERIFY over the ==")
print("== committed captures (amu-gpu session 231, s230 carry-     ==")
print("== forward's standing row).  Reads ONLY committed bytes;    ==")
print("== every record number re-derived from the captures by an   ==")
print("== independent code path (explicit sort, middle-two even-N  ==")
print("== median).  Nothing written; fail-closed.                  ==")
print()

# ---- check 1: capture census -------------------------------------
expected = []
for rd in RDS:
    for tag, _ in ARMS:
        for nn in (1, 2, 3):
            expected.append(f"run-rd{rd}-{tag}-r{nn:02d}.txt.gz")
expected = sorted(expected)
gz_present = sorted(f for f in os.listdir(HERE)
                    if f.startswith("run-") and f.endswith(".txt.gz"))
check("C1.1 gzip run-log census == the frozen 24-name grid",
      gz_present == expected)
err_present = sorted(f for f in os.listdir(HERE)
                     if f.startswith("run-") and f.endswith(".stderr.txt"))
check("C1.2 .stderr.txt sibling census == the frozen 24-name grid",
      err_present == sorted(n.replace(".txt.gz", ".stderr.txt")
                            for n in expected))
err_zero = all(os.path.getsize(os.path.join(HERE, f)) == 0
               for f in err_present)
check("C1.3 all 24 committed .stderr.txt siblings are 0 bytes", err_zero)

# ---- check 2: per-run sample census (parse the captures) ---------
SAMPLE = "SAMPLE round="
ticks = {}                     # (rd, tag) -> pooled int list
mismatch_total = 0             # summed over every committed VERIFY line
census_ok = True
knob_ok = True
verify_census_ok = True
for rd in RDS:
    for tag, batch in ARMS:
        pool = []
        for nn in (1, 2, 3):
            path = os.path.join(HERE, f"run-rd{rd}-{tag}-r{nn:02d}.txt.gz")
            total = 0
            nverify = 0
            run_pool = []
            reading_idx = None
            with gzip.open(path, "rt") as fh:
                for line in fh:
                    line = line.rstrip("\n")
                    if line.startswith("CELL "):
                        m = CELL_RE.match(line)
                        assert m, line
                        if (m.group(3), int(m.group(4)), m.group(5)) == CELL:
                            assert reading_idx is None, f"{path}: two reading cells"
                            reading_idx = int(m.group(1))
                        continue
                    if line.startswith("VERIFY "):
                        mv = re.match(r"^VERIFY idx=(\d+) checked=(\d+) "
                                      r"mismatch=(\d+) ok=(\d)", line)
                        assert mv, line
                        mismatch_total += int(mv.group(3))
                        nverify += 1
                        continue
                    if line.startswith(SAMPLE):
                        total += 1
                        f = line.split(" ")
                        assert len(f) == 10, line
                        if (f[3] != f"batch={batch}" or f[4] != "work_mul=1"
                                or f[5] != "ndiv=1"):
                            knob_ok = False
                        if int(f[2][4:]) == reading_idx:
                            run_pool.append(int(f[6][10:]))
                        continue
                    assert line.startswith("#"), line
            if total != 115200 or len(run_pool) != R or reading_idx is None:
                census_ok = False
            if nverify != 24:
                verify_census_ok = False
            pool.extend(run_pool)
        ticks[(rd, tag)] = pool
check("C2.1 every run: 115,200 SAMPLE lines, 6,400 at the reading cell",
      census_ok)
check("C2.2 every SAMPLE line: batch per arm, work_mul=1, ndiv=1", knob_ok)
check("C2.3 pooled N per reading per arm == 3R == 19,200",
      all(len(v) == N_POOL for v in ticks.values()))
check("C2.4 every run: 24 VERIFY lines", verify_census_ok)

# ---- check 3: raw-digest custody rows (s228) ---------------------
raw_rows = {}
with open(os.path.join(HERE, "raw-digests-s225.txt")) as fh:
    for line in fh:
        m = re.match(r"^([0-9a-f]{64})  (run-rd(\d)-(c[28])-r(\d\d)\.txt)  "
                     r"bytes=(\d+)$", line.rstrip("\n"))
        if m:
            raw_rows[(int(m.group(3)), m.group(4), int(m.group(5)))] = (
                m.group(1), int(m.group(6)))
check("C3.1 raw-digests-s225.txt rows == the frozen 24-run grid",
      sorted(raw_rows) == sorted((rd, t, n) for rd in RDS
                                 for t, _ in ARMS for n in (1, 2, 3)))
digest_ok = True
for rd in RDS:
    for tag, _ in ARMS:
        for nn in (1, 2, 3):
            want_sha, want_bytes = raw_rows[(rd, tag, nn)]
            got_sha, got_bytes = sha_stream(
                os.path.join(HERE, f"run-rd{rd}-{tag}-r{nn:02d}.txt.gz"),
                gunzip=True)
            if (got_sha, got_bytes) != (want_sha, want_bytes):
                digest_ok = False
check("C3.2 all 24 gz logs: decompressed raw sha256 + byte count == the "
      "committed custody rows", digest_ok)

# ---- check 4: publication pin -----------------------------------
pub = open(os.path.join(HERE, "publication-s229.txt"), "rb").read()
run1 = open(os.path.join(HERE, "publication-s229-run1.txt"), "rb").read()
run2 = open(os.path.join(HERE, "publication-s229-run2.txt"), "rb").read()
pub_sha = hashlib.sha256(pub).hexdigest()
check(f"C4.1 publication-s229.txt: {len(pub)} bytes sha256 {pub_sha}",
      len(pub) == PUB_SIZE and pub_sha == PUB_SHA)
check("C4.2 publication-s229-run1.txt == run2.txt == publication-s229.txt",
      run1 == run2 == pub)

# ---- check 5: independent re-derivation vs publication rows ------
pflat = flat(pub.decode())
pub_rows = re.findall(
    r"reading (\d) (c2|c8) N=([\d,]+) m=(\d+) mad=(\d+) h=([\d.]+)", pflat)
check("C5.0 publication section-2 row count == 8", len(pub_rows) == 8)
pub_by = {(int(r[0]), r[1]): r for r in pub_rows}
recomputed = {}                # (rd, tag) -> (m, mad, h_str, pct_str or None)
for rd in RDS:
    for tag, _ in ARMS:
        vals = ticks[(rd, tag)]
        m = median_sorted(vals)
        mad = median_sorted([abs(v - m) for v in vals])
        h = H_CONST * mad / math.sqrt(len(vals))
        recomputed[(rd, tag)] = (m, mad, f"{h:.4f}")
        row = pub_by.get((rd, tag))
        got = (f"m={fmt_num(m)}", f"mad={fmt_num(mad)}", f"h={f'{h:.4f}'}")
        want = (f"m={row[3]}", f"mad={row[4]}", f"h={row[5]}") if row else None
        check(f"C5.r{rd}.{tag} re-derived {got[0]} {got[1]} {got[2]} "
              f"N={len(vals)} == publication row", row is not None
              and got == want and row[2].replace(",", "") == str(len(vals)))

# ---- check 6: letter-domain + letter derivation recheck -----------
s27 = flat(open(os.path.join(GPU, "anv-b3bisect7-20261027",
                             "derivation-census-s27.txt")).read())
mband = re.search(r"floor band (\d+)\.\.(\d+)", s27)
mref = re.search(r"c8 ([\d,]+) \(session 4 pooled median\)", s27)
assert mband and mref
band = (int(mband.group(1)), int(mband.group(2)))
ref = int(mref.group(1).replace(",", ""))
check(f"C6.0 band/ref parsed from the committed s27 census: "
      f"floor band {band[0]}..{band[1]}, c8 ref {ref}",
      band == (31, 32) and ref == 32915)
mverify = re.search(
    r"VERIFY mismatch total over all runs: (\d+) \(per-arm: c2=(\d+), "
    r"c8=(\d+); per-reading (\d)/(\d)/(\d)/(\d)\)", pflat)
assert mverify
pub_verify_clean = all(int(g) == 0 for g in mverify.groups())
verify_clean = mismatch_total == 0 and pub_verify_clean
check(f"C6.1 VERIFY mismatches re-derived from the committed logs =="
      f" {mismatch_total} == publication rows (all 0, 24 runs)",
      verify_clean)
letters = []
for rd in RDS:
    m_c2 = recomputed[(rd, "c2")][0]
    m_c8 = recomputed[(rd, "c8")][0]
    pct = (m_c8 - ref) / ref * 100.0
    recomputed[(rd, "c8")] = recomputed[(rd, "c8")] + (f"{pct:.2f}",)
    domain = abs(m_c8 - ref) / ref <= 0.05 and verify_clean
    letter = "a" if band[0] <= m_c2 <= band[1] else "b"
    letters.append(letter if domain else None)
    pub_l = re.findall(r"L(\d) = \((\w)\) \(s218", pflat)
    want = dict((int(a), b) for a, b in pub_l).get(rd)
    check(f"C6.r{rd} domain(re-derived c8 pct {pct:.2f}%, verify-clean) "
          f"True; letter re-derived ({letter}) == publication L{rd}",
          domain and want == letter)
check("C6.2 the four re-derived letters give B_act (maximal "
      "constant-letter-run blocks) == 1", letters == ["b"] * 4)
bact_pub = re.search(r"B_act \(block count over L1\.\.L4[^:]*\): (\d+)", pflat)
check("C6.3 publication B_act == 1 == re-derived", bact_pub is not None
      and int(bact_pub.group(1)) == 1)
seq_pub = re.search(r"sequence identical to the record: (True|False)", pflat)
check("C6.4 publication 'sequence identical to the record: False' == "
      "re-derived (letters != record (b)/(a)/(a)/(b))",
      seq_pub is not None and seq_pub.group(1) == "False"
      and letters != ["b", "a", "a", "b"])
check("C6.5 publication act verdict literal set == {VALID}",
      set(re.findall(r"ACT VERDICT: (\w+)", pflat)) == {"VALID"})

# ---- check 7: record.txt transcription vs recomputed/publication --
rflat = flat(open(os.path.join(HERE, "record.txt")).read())


def rec_all(pattern):
    return re.findall(pattern, rflat)


c2recs = rec_all(r"c2 m (\d+) / (\d+) / (\d+) / (\d+) "
                 r"\(mad (\d+), h ([\d.]+) all four\)")
want_c2 = [tuple([fmt_num(recomputed[(rd, "c2")][0])] * 4
                 + [fmt_num(recomputed[(rd, "c2")][1]),
                    recomputed[(rd, "c2")][2]]) for rd in RDS]
check("C7.1 record c2 median/mad/h rows == re-derived (4 readings)",
      len(c2recs) >= 1 and all(tuple(r) == want_c2[0] for r in c2recs))
c8recs = rec_all(r"c8 m (\d+) / (\d+) / (\d+) / (\d+) "
                 r"\(mad (\d+)/(\d+)/(\d+)/(\d+); h descriptive ONLY\)")
want_c8 = tuple([fmt_num(recomputed[(rd, "c8")][0]) for rd in RDS]
                + [fmt_num(recomputed[(rd, "c8")][1]) for rd in RDS])
check("C7.2 record c8 median/mad rows == re-derived (4 readings)",
      len(c8recs) >= 1 and all(tuple(r) == want_c8 for r in c8recs))
pctrecs = rec_all(r"committed 32,915 \((-0\.\d\d)% / (-0\.\d\d)% / "
                  r"(-0\.\d\d)% / (-0\.\d\d)%\)")
want_pct = tuple(recomputed[(rd, "c8")][3] for rd in RDS)
check("C7.3 record c8 pct rows == re-derived (-0.13/-0.16/-0.36/-0.15)",
      len(pctrecs) >= 1 and all(tuple(r) == want_pct for r in pctrecs))
lrecs = rec_all(r"L1 = \((\w)\), L2 = \((\w)\), L3 = \((\w)\), "
                r"L4 = \((\w)\)")
check("C7.4 record L1..L4 == re-derived (b)/(b)/(b)/(b)",
      len(lrecs) >= 1 and all(list(r) == letters for r in lrecs))
srecs = rec_all(r"vs the committed record \((\w)\)/\((\w)\)/\((\w)\)/"
                r"\((\w)\) -- sequence identical: (True|False)")
check("C7.5 record sequence row (vs (b)/(a)/(a)/(b): False) == re-derived",
      len(srecs) >= 1 and all(list(r[:4]) == ["b", "a", "a", "b"]
                              and r[4] == "False" for r in srecs))
brecs = rec_all(r"B_act = (\d+) \(act block shape")
check("C7.6 record B_act == 1 == re-derived",
      len(brecs) >= 1 and all(r == "1" for r in brecs))
vrecs = rec_all(r"ACT VERDICT: (\w+)")
check("C7.7 record act verdict literal set == {VALID}",
      len(vrecs) >= 1 and set(vrecs) == {"VALID"})
pubrec = re.search(r"the committed record \(four-cut\): "
                   r"\((\w)\) / \((\w)\) / \((\w)\) / \((\w)\)", pflat)
check("C7.8 publication's committed-record letters (b)/(a)/(a)/(b) == "
      "the record's sequence row",
      pubrec is not None and srecs and list(pubrec.groups()) == list(srecs[0][:4]))

nok = sum(1 for ok, _ in RESULTS if ok)
nfail = len(RESULTS) - nok
print()
print(f"# record-verify s231 (verify-record-s231.py): {nok} ok / {nfail} failed")
sys.exit(0 if nfail == 0 else 1)
