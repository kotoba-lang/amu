#!/usr/bin/env python3
# amu-gpu s188 pull-verify (session 188): FAIL-CLOSED verification of
# the COMMITTED form of the s185 pull -- reads ONLY the committed
# bytes in docs/evidence/gpu/anv-b3bisect17-20261101/ (the 54
# run-<tag>-r<NN>.txt.gz + 54 plain 0-byte .stderr.txt + raw-
# digests-s185.txt). Checks: name set, gzip fidelity vs the raw-
# digest record (explicit counts), raw-digest structure, the
# canonical aggregate re-derived THROUGH the committed form ==
# acad342c459832f5584742f4b428ada002113adc359af214bcbdc6ec4ba3c513,
# and the per-arm RUN-HEADER census (the q1 header census:
# batch=3 work_mul=313 ndiv=1229 n=254,679). Run TWICE byte-
# identical. Any mismatch raises.
import gzip, hashlib, math, os, re

EV = "/Users/junkawasaki/github/wt/amu-gpu/chain/docs/evidence/gpu/anv-b3bisect17-20261101"
WANT_AGG = "acad342c459832f5584742f4b428ada002113adc359af214bcbdc6ec4ba3c513"

def expected_names():
    ns = []
    for t, mx in (("c2", 3), ("c8", 3), ("q1", 48)):
        for i in range(1, mx + 1):
            n = "%02d" % i
            ns.append("run-%s-r%s.txt" % (t, n))
            ns.append("run-%s-r%s.stderr.txt" % (t, n))
    return sorted(ns)

names = expected_names()

# 1. committed name set == expected 108/108
present = sorted(os.listdir(EV))
have = set(n for n in present if re.fullmatch(r"run-(c2|c8|q1)-r\d\d\.(txt\.gz|stderr\.txt)", n))
want = set()
for n in names:
    want.add(n + ".gz" if n.endswith(".txt") and not n.endswith(".stderr.txt") else n)
assert have == want, "committed name set mismatch: extra=%s missing=%s" % (sorted(have - want), sorted(want - have))
print("committed name set == expected 108/108 (54 run-<tag>-r<NN>.txt.gz + 54 plain 0-byte .stderr.txt)")

# 2. raw-digest record structure (54 unique stdout rows)
rows = {}
with open(os.path.join(EV, "raw-digests-s185.txt")) as f:
    for line in f:
        m = re.fullmatch(r"([0-9a-f]{64})  (run-\S+\.txt)  bytes=(\d+)\n", line)
        if m:
            assert m.group(2) not in rows, "duplicate raw-digest row"
            rows[m.group(2)] = (m.group(1), int(m.group(3)))
assert len(rows) == 54, len(rows)
tot = sum(b for _, b in rows.values())
assert tot == 776686013, tot
print("raw-digests-s185.txt: 54 unique rows; raw bytes total %d == the host wc -c census total" % tot)

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
q1 = None
for key in sorted(hdrs):
    tag = sorted(hdrs[key])[0].split("-")[1]
    print("  %s: n=%d rounds=%d warmup=%d batch=%d barrier_n=%d work_mul=%d ndiv=%d  logs=%d (%s..%s)"
          % (tag, key[0], key[1], key[2], key[3], key[4], key[5], key[6], len(hdrs[key]),
             sorted(hdrs[key])[0], sorted(hdrs[key])[-1]))
    if key[3] == 3:
        q1 = key
assert q1 is not None
assert q1 == (254679, 6400, 3, 3, 0, 313, 1229), q1
assert (1000003 * 313) // 1229 == 254679
assert math.gcd(313, 1229) == 1
print("q1 header census: batch=3 work_mul=313 ndiv=1229 n=254,679 rounds=6400 -- 48/48 logs uniform; == the frozen knob arithmetic ((1,000,003*313)//1,229 = 254,679, gcd 1) -- ok")
assert sorted(k for k in hdrs if k[3] == 2) == [(1000003, 6400, 3, 2, 0, 1, 1)]
assert sorted(k for k in hdrs if k[3] == 8) == [(1000003, 6400, 3, 8, 0, 1, 1)]
print("c2 header census: batch=2 work_mul=1 ndiv=1 n=1,000,003 rounds=6400 -- 3/3 uniform; c8 header census: batch=8 work_mul=1 ndiv=1 n=1,000,003 rounds=6400 -- 3/3 uniform -- ok")
print("PULL-VERIFY S185 SUMMARY: name set 108/108, raw rows 54/54, gzip fidelity 54/54, aggregate MATCH, headers 54/54")
print("PULL-VERIFY S185 COMPLETE (fail-closed: 0 failed)")
