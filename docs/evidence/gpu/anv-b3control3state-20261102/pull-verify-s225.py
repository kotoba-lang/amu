#!/usr/bin/env python3
# amu-gpu s228 pull-verify (session 228): FAIL-CLOSED verification of
# the COMMITTED form of the s225 pull -- reads ONLY the committed
# bytes in docs/evidence/gpu/anv-b3control3state-20261102/ (the 24
# run-rd<rd>-<arm>-r<NN>.txt.gz + 24 plain 0-byte .stderr.txt +
# raw-digests-s225.txt). Checks: name set, names-order construction
# pin, gzip fidelity vs the raw-digest record (explicit counts),
# raw-digest structure, the canonical aggregate re-derived THROUGH
# the committed form == 31c0feaeef55a01a3e965fead1508babcf7e26a9aff95d369f189f9f7e2c49f0,
# and the per-arm RUN-HEADER census (c2 (B=2,WM=1,NDIV=1) n=1,000,003
# and c8 (B=8,WM=1,NDIV=1) n=1,000,003, the frozen control arms).
# Run TWICE byte-identical. Any mismatch raises.
import gzip, hashlib, os, re

EV = "/Users/junkawasaki/github/wt/amu-gpu/chain/docs/evidence/gpu/anv-b3control3state-20261102"
WANT_AGG = "31c0feaeef55a01a3e965fead1508babcf7e26a9aff95d369f189f9f7e2c49f0"
WANT_RAW_TOTAL = 333188873
WANT_NAMES_SHA = "ba5a06be81dcdacafae09c68e3a46659934260630cf0c19e4a7595671b69ee21"

def expected_names():
    ns = []
    for rd in "1234":
        for arm in ("c2", "c8"):
            for i in range(1, 4):
                n = "%02d" % i
                ns.append("run-rd%s-%s-r%s.txt" % (rd, arm, n))
                ns.append("run-rd%s-%s-r%s.stderr.txt" % (rd, arm, n))
    return sorted(ns)

names = expected_names()
assert len(names) == 48

# 0. names-order construction pin (the host /tmp/s228-names-pull.txt form)
nb = "".join(n + "\n" for n in names).encode()
assert hashlib.sha256(nb).hexdigest() == WANT_NAMES_SHA, "names construction digest mismatch"
print("names-order construction == the host names file (48 lines, sha256 %s)" % WANT_NAMES_SHA)

# 1. committed name set == expected 48/48
present = sorted(os.listdir(EV))
have = set(n for n in present if re.fullmatch(r"run-rd[1-4]-(c2|c8)-r\d\d\.(txt\.gz|stderr\.txt)", n))
want = set()
for n in names:
    want.add(n + ".gz" if n.endswith(".txt") and not n.endswith(".stderr.txt") else n)
assert have == want, "committed name set mismatch: extra=%s missing=%s" % (sorted(have - want), sorted(want - have))
print("committed name set == expected 48/48 (24 run-rd<rd>-<arm>-r<NN>.txt.gz + 24 plain 0-byte .stderr.txt)")

# 2. raw-digest record structure (24 unique stdout rows)
rows = {}
with open(os.path.join(EV, "raw-digests-s225.txt")) as f:
    for line in f:
        m = re.fullmatch(r"([0-9a-f]{64})  (run-\S+\.txt)  bytes=(\d+)\n", line)
        if m:
            assert m.group(2) not in rows, "duplicate raw-digest row"
            rows[m.group(2)] = (m.group(1), int(m.group(3)))
assert len(rows) == 24, len(rows)
tot = sum(b for _, b in rows.values())
assert tot == WANT_RAW_TOTAL, tot
print("raw-digests-s225.txt: 24 unique rows; raw bytes total %d == the host wc -c census total" % tot)

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
assert checked == 24 and mismatch == 0
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

print("run-header census (fields n,rounds,warmup,batch,barrier_n,work_mul,ndiv; parsed from the 24 committed logs):")
for key in sorted(hdrs):
    tag = "c2" if key[3] == 2 else ("c8" if key[3] == 8 else "?")
    print("  %s: n=%d rounds=%d warmup=%d batch=%d barrier_n=%d work_mul=%d ndiv=%d  logs=%d (%s..%s)"
          % (tag, key[0], key[1], key[2], key[3], key[4], key[5], key[6], len(hdrs[key]),
             sorted(hdrs[key])[0], sorted(hdrs[key])[-1]))
c2 = sorted(k for k in hdrs if k[3] == 2)
c8 = sorted(k for k in hdrs if k[3] == 8)
assert c2 == [(1000003, 6400, 3, 2, 0, 1, 1)], c2
assert c8 == [(1000003, 6400, 3, 8, 0, 1, 1)], c8
assert sum(len(hdrs[k]) for k in c2) == 12
assert sum(len(hdrs[k]) for k in c8) == 12
assert sorted(k for k in hdrs) == c2 + c8
print("c2 header census: batch=2 work_mul=1 ndiv=1 n=1,000,003 rounds=6400 -- 12/12 uniform; c8 header census: batch=8 work_mul=1 ndiv=1 n=1,000,003 rounds=6400 -- 12/12 uniform -- ok (the frozen control arms)")
print("PULL-VERIFY S225 SUMMARY: name set 48/48, raw rows 24/24, gzip fidelity 24/24, aggregate MATCH, headers 24/24")
print("PULL-VERIFY S225 COMPLETE (fail-closed: 0 failed)")
