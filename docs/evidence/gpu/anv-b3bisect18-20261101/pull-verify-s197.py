#!/usr/bin/env python3
# amu-gpu s199 pull-verify (session 199): FAIL-CLOSED verification of
# the COMMITTED form of the s197 pull -- reads ONLY the committed
# bytes in docs/evidence/gpu/anv-b3bisect18-20261101/ (the 54
# run-<tag>-r<NN>.txt.gz + 54 plain 0-byte .stderr.txt + raw-
# digests-s197.txt). Checks: name set, gzip fidelity vs the raw-
# digest record (explicit counts), raw-digest structure, the
# canonical aggregate re-derived THROUGH the committed form ==
# 03511dbfa0f2a6a3f92caa1991493633e4fc2805778367fc5a59426d7adc3a53,
# and the per-arm RUN-HEADER census (the q3 header census:
# batch=3 work_mul=246 ndiv=965 n=254,923). Run TWICE byte-
# identical. Any mismatch raises.
import gzip, hashlib, math, os, re

EV = "/Users/junkawasaki/github/wt/amu-gpu/chain/docs/evidence/gpu/anv-b3bisect18-20261101"
WANT_AGG = "03511dbfa0f2a6a3f92caa1991493633e4fc2805778367fc5a59426d7adc3a53"
WANT_RAW_TOTAL = 771124077

def expected_names():
    ns = []
    for t, mx in (("c2", 3), ("c8", 3), ("q3", 48)):
        for i in range(1, mx + 1):
            n = "%02d" % i
            ns.append("run-%s-r%s.txt" % (t, n))
            ns.append("run-%s-r%s.stderr.txt" % (t, n))
    return sorted(ns)

names = expected_names()

# 1. committed name set == expected 108/108
present = sorted(os.listdir(EV))
have = set(n for n in present if re.fullmatch(r"run-(c2|c8|q3)-r\d\d\.(txt\.gz|stderr\.txt)", n))
want = set()
for n in names:
    want.add(n + ".gz" if n.endswith(".txt") and not n.endswith(".stderr.txt") else n)
assert have == want, "committed name set mismatch: extra=%s missing=%s" % (sorted(have - want), sorted(want - have))
print("committed name set == expected 108/108 (54 run-<tag>-r<NN>.txt.gz + 54 plain 0-byte .stderr.txt)")

# 2. raw-digest record structure (54 unique stdout rows)
rows = {}
with open(os.path.join(EV, "raw-digests-s197.txt")) as f:
    for line in f:
        m = re.fullmatch(r"([0-9a-f]{64})  (run-\S+\.txt)  bytes=(\d+)\n", line)
        if m:
            assert m.group(2) not in rows, "duplicate raw-digest row"
            rows[m.group(2)] = (m.group(1), int(m.group(3)))
assert len(rows) == 54, len(rows)
tot = sum(b for _, b in rows.values())
assert tot == WANT_RAW_TOTAL, tot
print("raw-digests-s197.txt: 54 unique rows; raw bytes total %d == the host wc -c census total" % tot)

# 3. gzip fidelity (explicit counts)
checked = 0
mismatch = 0
for n in sorted(rows):
    want_d, _ = rows[n]
    with gzip.open(os.path.join(EV, n + ".gz"), "rb") as f:
        d = hashlib.sha256(f.read()).hexdigest()
    checked += 1
    if d != want_d:
        mismatch += 1
        print("MISMATCH %s" % n)
assert checked == 54 and mismatch == 0
print("gzip fidelity: checked=%d mismatch=%d" % (checked, mismatch))

# 4. canonical aggregate THROUGH the committed form (sorted name order)
h = hashlib.sha256()
for n in names:
    if n.endswith(".stderr.txt"):
        p = os.path.join(EV, n)
        with open(p, "rb") as f:
            assert f.read() == b"", "stderr not empty: %s" % n
        continue
    with gzip.open(os.path.join(EV, n + ".gz"), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
agg = h.hexdigest()
assert agg == WANT_AGG, "committed-form aggregate != %s: %s" % (WANT_AGG, agg)
print("%s  -" % agg)
print("committed form -> raw aggregate preserved exactly")

# 5. per-arm RUN-HEADER census (parsed from committed bytes, never transcribed)
hdrs = {}
for n in names:
    if n.endswith(".stderr.txt"):
        continue
    with gzip.open(os.path.join(EV, n + ".gz"), "rt") as f:
        head = []
        for line in f:
            head.append(line)
            if len(head) >= 8:
                break
    hl = [l for l in head if l.startswith("# n=")]
    assert len(hl) == 1, n
    m = re.match(r"# n=(\d+) rounds=(\d+) warmup=(\d+) batch=(\d+) barrier_n=(\d+) work_mul=(\d+) ndiv=(\d+) ", hl[0])
    assert m, hl[0]
    key = tuple(int(g) for g in m.groups())
    hdrs.setdefault(key, []).append(n)

print("run-header census (fields n,rounds,warmup,batch,barrier_n,work_mul,ndiv; parsed from the 54 committed logs):")
q3 = None
for key in sorted(hdrs):
    tag = sorted(hdrs[key])[0].split("-")[1]
    print("  %s: n=%d rounds=%d warmup=%d batch=%d barrier_n=%d work_mul=%d ndiv=%d  logs=%d (%s..%s)"
          % (tag, key[0], key[1], key[2], key[3], key[4], key[5], key[6], len(hdrs[key]),
             sorted(hdrs[key])[0], sorted(hdrs[key])[-1]))
    if key[3] == 3:
        q3 = key
assert q3 is not None
assert q3 == (254923, 6400, 3, 3, 0, 246, 965), q3
assert (1000003 * 246) // 965 == 254923
assert math.gcd(246, 965) == 1
print("q3 header census: batch=3 work_mul=246 ndiv=965 n=254,923 rounds=6400 -- 48/48 logs uniform; == the frozen knob arithmetic ((1,000,003*246)//965 = 254,923, gcd 1) -- ok")
assert sorted(k for k in hdrs if k[3] == 2) == [(1000003, 6400, 3, 2, 0, 1, 1)]
assert sorted(k for k in hdrs if k[3] == 8) == [(1000003, 6400, 3, 8, 0, 1, 1)]
print("c2 header census: batch=2 work_mul=1 ndiv=1 n=1,000,003 rounds=6400 -- 3/3 uniform; c8 header census: batch=8 work_mul=1 ndiv=1 n=1,000,003 rounds=6400 -- 3/3 uniform -- ok")
print("PULL-VERIFY S197 SUMMARY: name set 108/108, raw rows 54/54, gzip fidelity 54/54, aggregate MATCH, headers 54/54")
print("PULL-VERIFY S197 COMPLETE (fail-closed: 0 failed)")
