#!/usr/bin/env python3
# freeze-verify-s215to220.py -- JUN-59 session 223: the open control
# question's RESOLUTION-ACT pre-registration FREEZE verification (the
# s222 carry-forward's protocol-freeze slice): fail-closed checks over
# the frozen protocol.txt (the s215-s220 decision span this protocol
# freezes -- named after the DECISION span, the design-verify-
# s215to220.py precedent).
#
# SCOPE (named, not hidden): (1) FILE PINS -- size + sha256 over every
# file protocol.txt quotes (the same pin values design-verify-
# s215to220.py verified at s222) + the six decision records + the
# ROUNDS6400 instrument source pin; (2) QUOTE BLOCKS -- every
# [[Q <path> L<a>-<b>]] block in protocol.txt re-extracted from the
# named source's committed bytes at the named lines and byte-compared
# (28 blocks); (3) GLOSS ADJACENCY -- every occurrence of the frozen
# name "three-state control record" in protocol.txt must carry the
# s220 2(e) gloss within the following 700 characters; (4)
# TERMINOLOGY -- outside quote blocks the bare word "state" is
# allowed only as state-BLOCK/state-IDENTITY, "underlying-state", a
# state-sNNN.txt filename, or inside a double-quoted term; every
# occurrence is listed with its disposition; (5) DERIVED
# re-derivations -- every labelled DERIVED quantity in the frozen
# protocol re-computed from scratch (4*(3+3), 3R, the CI constant,
# the tick-to-ns scale, the 16-sequence enumeration with block and
# identity counts, the B=3 set, I=2 iff B>=2, the 16+1 act outcome
# space) and its printed literal asserted present in protocol.txt.
#
# FAIL-CLOSED: ANY missing line, mismatched byte, missing gloss,
# unapproved "state" token, wrong arithmetic or missing literal is a
# hard failure (exit 1).
#
# QUOTE-ONLY / ARITHMETIC-ONLY: this script verifies the frozen
# protocol's quotations, gloss, terminology and arithmetic against
# committed bytes. It computes NO control-question quantity -- NO
# run, NO letter act, NO reading, NO verdict, NO claim. Every
# resolution-act quantity stays UNMEASURED. RULE 4 unchanged: NOTHING
# MOVES; the committed bracket stays EXACTLY (254,923, 255,045].
import hashlib
import itertools
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
GPU = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(GPU)))
PROTO = os.path.join(HERE, "protocol.txt")

FILES = {
    "pub169": os.path.join(GPU, "anv-b3bisect16-20261101", "publication-s169.txt"),
    "pub185": os.path.join(GPU, "anv-b3bisect17-20261101", "publication-s185.txt"),
    "pub197": os.path.join(GPU, "anv-b3bisect18-20261101", "publication-s197.txt"),
    "pub209": os.path.join(GPU, "anv-b3bisect19-20261102", "publication-s209.txt"),
    "pr19": os.path.join(GPU, "anv-b3bisect19prereg-20261102", "protocol.txt"),
    "a209id": os.path.join(GPU, "anv-b3bisect19-20261102", "analysis-s209-identity.txt"),
    "r6400": os.path.join(GPU, "anv-b3bisect17-20261101", "gpu-subgroup-reduce-anv-ndiv-rounds6400.c.txt"),
    "pub4": os.path.join(GPU, "anv-batchscale-20261027", "publication-s4.txt"),
    "s215": os.path.join(HERE, "state-s215.txt"),
    "s216": os.path.join(HERE, "refs-provenance-s216.txt"),
    "s218": os.path.join(HERE, "letters-s218.txt"),
    "s219": os.path.join(HERE, "invalidation-s219.txt"),
    "s220": os.path.join(HERE, "threestate-s220.txt"),
}

# (id, file key, expected size in bytes, expected sha256 hex) -- the
# s222 design-verify pin values, re-checked at this freeze.
FILE_PINS = [
    ("F-PUB169", "pub169", 56352,
     "c9aab750fd20120b3abe8db6e9cac554b6c8ea0fbb1b37d9169d1539e4ff7687"),
    ("F-PUB185", "pub185", 59777,
     "c62c01e17a045933782cc3fb8c67e452ae0f35a513ad1f396a9dea08834d6d34"),
    ("F-PUB197", "pub197", 62811,
     "f3d7465ad60a7de2be20d4edfcbb4743f73849d7b0a93e7ff6f2eccbd1ff5e53"),
    ("F-PUB209", "pub209", 66774,
     "d3a338f39a9cdb75938da3a412fee7ec299813d38bc46f1f7b9cb773bc2c2ebe"),
    ("F-PR19", "pr19", 26405,
     "9a6f7b75e932c51d8a45d5586bdfda15a73d350892153f31aec29c70b8ace6f6"),
    ("F-A209ID", "a209id", 2916,
     "80adc36467c8b06ac5643286590ace490ea533e73ef82ba74a490ecd2f24e5b6"),
    ("F-R6400", "r6400", 29535,
     "c2704aaad6bfeeae1f4f9cfa916d0160efb03926892237554c7dffc8386e84e0"),
    ("F-PUB4", "pub4", 16602,
     "435c45aa6f33e6ca6792bfabea5bf97c0fd50a1e095aefd155819005c29796de"),
    ("F-S215", "s215", 10214,
     "545b1ab8c7eafbdfc9e3db10fa43e4acc2fbe1d9bc0236d887f6b0474d42425f"),
    ("F-S216", "s216", 11969,
     "dec785c7cb47a6c0a7593d8bc30a36e36ec5e30a2e5c1943d14857d5f8a13a7a"),
    ("F-S218", "s218", 15736,
     "62d7b1f6012e95f11f26002ba8c7c143fbe9214507f255d1cbf07132009908da"),
    ("F-S219", "s219", 12509,
     "2958817b52968f6efdfc6ff4f308efc62621117dee47ce51f299f17a480c868e"),
    ("F-S220", "s220", 17492,
     "67de0879234e704ef3aad7c1b00690db2aa7f25ca2c7219b53a3e8f1c2c3d60b"),
]

# The expected quote-block count in protocol.txt (the template's
# [[Q ...]] marker count, expanded from committed bytes).
WANT_BLOCKS = 28

GLOSS = ("three state-BLOCKS ((b) | (a,a) | (b)) at letter "
         "granularity; identity count 2; underlying-state count "
         "UNMEASURED")

ok = 0
failed = 0

def want(name, cond, detail):
    global ok, failed
    if cond:
        ok += 1
        print("ok   %s %s" % (name, detail))
    else:
        failed += 1
        print("FAIL %s %s" % (name, detail))


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


print("=== FREEZE-VERIFY S215-TO-S220 (session 223, fail-closed) ===")
proto_bytes = open(PROTO, "rb").read()
proto = proto_bytes.decode("utf-8")
print("protocol.txt: %d bytes sha256 %s" % (len(proto_bytes), hashlib.sha256(proto_bytes).hexdigest()))

# --- (1) FILE PINS -------------------------------------------------
print("--- (1) FILE PINS (size + sha256 vs the s222 design-verify pins)")
for pid, key, size, digest in FILE_PINS:
    p = FILES[key]
    got_size = os.path.getsize(p)
    got = sha(p)
    want(pid, got_size == size and got == digest,
         "%s size %d sha256 %s" % (os.path.basename(p), got_size, got))

# --- (2) QUOTE BLOCKS ----------------------------------------------
print("--- (2) QUOTE BLOCKS (byte-exact re-extraction from committed bytes)")
blk_pat = re.compile(r"^\[\[Q (\S+) (L(\d+)(?:-(\d+))?)\]\]$", re.M)
lines = proto.split("\n")
blocks = 0
i = 0
while i < len(lines):
    m = blk_pat.match(lines[i])
    if m:
        blocks += 1
        path, a = m.group(1), int(m.group(3))
        b = int(m.group(4)) if m.group(4) else a
        j = i + 1
        body = []
        while j < len(lines) and lines[j] != "[[/Q]]":
            body.append(lines[j])
            j += 1
        want("Q-CLOSE-%d" % blocks, j < len(lines), "%s: [[/Q]] present" % m.group(2))
        src = open(os.path.join(ROOT, path), "r").read().split("\n")
        src_lines = src[a - 1:b]
        want("Q-%02d" % blocks,
             body == src_lines,
             "%s %s (%d lines) byte-exact vs committed bytes" % (path, m.group(2), len(body)))
        i = j + 1
    else:
        i += 1
want("Q-COUNT", blocks == WANT_BLOCKS, "%d quote blocks (want %d)" % (blocks, WANT_BLOCKS))

# --- (3) GLOSS ADJACENCY -------------------------------------------
print("--- (3) GLOSS ADJACENCY (the s220 2(e) fix)")
occ = [m.start() for m in re.finditer(re.escape("three-state control record"), proto)]
for k, pos in enumerate(occ):
    before = re.sub(r"\s+", " ", proto[max(0, pos - 700):pos])
    after = re.sub(r"\s+", " ", proto[pos:pos + 700])
    want("G-%d" % (k + 1), GLOSS in before or GLOSS in after,
         "name occurrence at char %d carries the gloss within 700 chars" % pos)
want("G-COUNT", len(occ) >= 2,
     "%d frozen-name occurrences (want >= 2: the two verbatim quotes)" % len(occ))

# --- (4) TERMINOLOGY (the s220 2(e) discipline) ---------------------
print("--- (4) TERMINOLOGY (bare 'state' only as state-BLOCK/state-IDENTITY/"
      "underlying-state/filename/quoted term; every occurrence listed)")
masked = blk_pat.sub(lambda m: "", proto)
mask_lines = []
skip = False
for ln in proto.split("\n"):
    if blk_pat.match(ln):
        skip = True
        mask_lines.append("")
        continue
    if skip and ln == "[[/Q]]":
        skip = False
        mask_lines.append("")
        continue
    mask_lines.append("" if skip else ln)
prose = "\n".join(mask_lines)
# quoted-term spans: walk the prose toggling at each double quote (the
# prose's double quotes are balanced -- asserted below).
in_quote = []
open_at = None
for idx, ch in enumerate(prose):
    if ch == '"':
        if open_at is None:
            open_at = idx
        else:
            in_quote.append((open_at, idx + 1))
            open_at = None
want("T-BALANCE", open_at is None, "prose double quotes balanced")
for m in re.finditer(r"(?i)\b[Ss]tate\b", prose):
    pos = m.start()
    after = prose[m.end():m.end() + 10]
    before = prose[max(0, pos - 12):pos]
    line = prose[:pos].count("\n") + 1
    if after.lower().startswith(("-block", "-identity")):
        want("T-ALLOW", True, "line %d: 'state' -> qualified term" % line)
    elif before.lower().endswith("underlying-"):
        want("T-ALLOW", True, "line %d: 'state' -> 'underlying-state' compound" % line)
    elif re.match(r"(?i)state-s\d+\.txt", prose[pos:]):
        want("T-ALLOW", True, "line %d: 'state' -> decision-record filename" % line)
    elif any(s <= pos < e for s, e in in_quote):
        want("T-ALLOW", True, "line %d: 'state' -> inside double-quoted term" % line)
    else:
        want("T-FLAG", False, "line %d: bare 'state' at char %d" % (line, pos))

# --- (5) DERIVED RE-DERIVATIONS ------------------------------------
print("--- (5) DERIVED re-derivations (computed from scratch; literal present)")
norm = re.sub(r"\s+", " ", proto)

def want_derived(name, computed, literal, note):
    want(name, literal in norm and computed,
         "%s -> %s (literal present, whitespace-normalized)" % (note, literal))

want_derived("D-PROC", 4 * (3 + 3) == 24, "4*(3+3) = 24", "act process count")
want_derived("D-N", 3 * 6400 == 19200, "3R = 19,200", "block-unit N")
c = round(1.96 * 1.2533 * 1.4826, 4)
want_derived("D-CI", c == 3.6420, "1.96 * 1.2533 * 1.4826 = 3.6420", "CI constant")
t = round(31 * 52.083, 3)
want_derived("D-NS", t == 1614.573, "31 * 52.083 = 1,614.573", "tick-to-ns floor scale")
want_derived("D-SEQ", 2 ** 4 == 16, "2^4 = 16", "letter sequence space")
want_derived("D-OUT", 16 + 1 == 17, "16 + 1 = 17", "act outcome space")

seqs = ["".join(p) for p in itertools.product("ab", repeat=4)]

def blocks_of(s):
    b, prev = 0, None
    for ch in s:
        if ch != prev:
            b += 1
            prev = ch
    return b

bcount = {}
icount = {}
for s in seqs:
    bcount[blocks_of(s)] = bcount.get(blocks_of(s), 0) + 1
    icount[len(set(s))] = icount.get(len(set(s)), 0) + 1
want_derived("D-BDIST", bcount == {1: 2, 2: 6, 3: 6, 4: 2},
             "B=1: 2, B=2: 6, B=3: 6, B=4: 2", "block-count distribution")
want_derived("D-IDIST", icount == {1: 2, 2: 14},
             "I=1: 2, I=2: 14", "identity distribution")
rec = "baab"
want_derived("D-REC", blocks_of(rec) == 3 and len(set(rec)) == 2,
             "b a a b -> B=3, I=2", "the record's own counts")
b3 = sorted(s for s in seqs if blocks_of(s) == 3)
want_derived("D-B3SET", b3 == ["aaba", "abaa", "abba", "baab", "babb", "bbab"],
             "{aaba, abaa, abba, baab, babb, bbab}", "the B=3 set")
want_derived("D-COINCIDE", all((len(set(s)) == 2) == (blocks_of(s) >= 2) for s in seqs),
             "I=2 iff B>=2", "prong-B coincidence")
want_derived("D-SPAN", max([30, 31, 31, 30]) - min([30, 31, 31, 30]) == 1,
             "1 tick", "record c2 median span")

print("FREEZE-VERIFY S215-TO-S220 SUMMARY: %d ok / %d failed" % (ok, failed))
if failed:
    print("INCOMPLETE (fail-closed: %d failed)" % failed)
    raise SystemExit(1)
print("COMPLETE (fail-closed: 0 failed)")
