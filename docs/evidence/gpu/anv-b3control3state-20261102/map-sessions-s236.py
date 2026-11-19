#!/usr/bin/env python3
"""map-sessions-s236.py -- THE RECORD SESSION-NUMBERED WINDOW -> COMMITTED
DIR MAPPING CHECK (amu-gpu session 236; the s235 carry-forward's named row
(ii) -- "whether every record session-numbered window maps onto a committed
dir enumerated here stays UNCHECKED from committed bytes (a publication-side
mapping row, not a raw-log row)") -- taken as this tick's ONE row.

THE ROW (quoted from the s235 commit's NOT DONE list, verbatim): "(ii)
whether every record session-numbered window maps onto a committed dir
enumerated here stays UNCHECKED from committed bytes (a publication-side
mapping row, not a raw-log row)".

THE QUESTION: does every session-numbered window the committed record chain
names map onto exactly one committed dir, and is that dir enumerated in the
s235 committed run-* census?  The s235 census enumerated (dir x arm) windows
from RAW run logs -- which carry NO session identity (their headers name the
instrument, knobs and device, never a session; the "JUN-59 session N run
window" lines live in separate host-side capture files, not in the run logs
themselves).  The session<->window identity lives ONLY on the publication
side: the placement of the committed publication-sN.txt files plus the
record chain's own map tables (the s233 SPEC, the s234 WINDOWS tuples, the
s235 REF_WINDOWS rows) and the record's own rows (the s215 four-cut table).
This slice derives the map from committed publication bytes and confronts
every committed map claim against it.

THE MAP (frozen before the numbers): session n maps onto dir D(n) iff D
carries the committed file publication-sN.txt (exact name form).  The map
must be SINGLE-VALUED (every n in exactly one dir) and at-most-one-per-dir
(every dir carries at most one publication-sN.txt).  Sessions 1..3 carry NO
publication-sN.txt names (s216 (c): the -sN naming starts at session 4);
their placement is REPORTED as the s216 session-ID READING and never
checked -- it is a reading, not a committed claim.

CITATION FORMS (frozen before the numbers; every session each names is a
record session-numbered window of this row's scope):
  V1 publication filename publication-sN.txt (the map itself)
  V2 header form 'C1 RE-DERIVATION (at sN' / '(environment pin, from the
     sN' (the s233 form)
  V3 preamble form 'session-N run logs' / 'measured in session N' (the s233
     form; preamble = the lines before the first '^1. ' section line, the
     s233 rule)
  V4 quote-row form 'sN: c2 class FLOOR (FLOOR required; committed floor
     band 31..32); c8 (sum,128,S=16) pooled median ...' (the s233
     RE_QUOTE_ROW session)
  V5 the s215 record rows 'Nth cut -- publication-sN.txt (dir/)' (the
     record's own ordinal -> session -> dir triples)
  V6 the committed map tables: the s234 WINDOWS tuples (label, session,
     kind, run dir, run pattern, publication), the s235 REF_WINDOWS rows
     (label, dir, arm, letter) and the s233 SPEC (session, dir, family)
  V7 'session N pooled median' (the c8 reference citation form, s216 1)
  any OTHER 'session[- ]N' form in the publication corpus is NAMED as
  unparsed-form (bucketed by normalized context line and counted, never
  silently skipped).  NAMED LIMITATION: bare 'sN' mentions outside V2/V4
  (e.g. "the s27 controls census") are NOT read as window citations here --
  the bare form does not distinguish analysis-session file citations from
  measurement-window citations; this scoping is named, not hidden.

THE CENSUS SIDE (the s235 enumeration rule, re-derived here from committed
bytes; the s235 script is NOT re-run): every run-* raw log under
docs/evidence/gpu (.stderr.txt siblings excluded); first-line families v2
instrument / v1 instrument / other; the c2-rung knob set n=1,000,003
batch=2 warmup=3 seed=20261027 with barrier_n 0-or-absent, work_mul
1-or-absent, ndiv 1-or-absent; census windows = (dir, arm family).

CHECKS (parse anomalies and committed-internal contradictions; fail the
run) vs REPORTS (mapping outcomes; never fail the run):
  C1 publication census: every exact-form publication-sN.txt parses n; n
     single-valued; at most one per dir; every publication reads as strict
     UTF-8.
  C2 the derived map == the s233 SPEC session->dir table (80 rows).
  C3 the s234 WINDOWS tuples (9 rows) and the s235 REF_WINDOWS rows (9):
     (session, dir) agree with the derived map; each tuple's named
     publication sits in its dir; each tuple's run-name-pattern files (3
     per window) exist; the s234 and s235 label->dir rows agree with each
     other.
  C4 V2/V3 provenance per publication: unambiguous under the s233 rule
     (a foreign signal set that is empty, or a singleton disjoint from n);
     every V2/V3-cited session maps.
  C5 V4/V7 citations: every cited session maps.
  C6 the s215 record rows: 4 (ordinal, session, dir) triples parse and
     agree with the map.
  C7 census reconciliation: v2 + v1 + other == every run-* file.
REPORTS: the full derived map, every publication's provenance class
(own / anchor at sM / no signal), the W set (every session named by
V1..V7), the unparsed-form census, the s216 session-1..3 readings, and for
every w in W its mapped dir with that dir's census rows -- the row's answer
(every record session-numbered window maps onto exactly one committed dir
enumerated in the s235 census, at run-* tree level and at c2-rung universe
level) with every non-mapping row named.

Reads ONLY committed bytes (fail-closed; any parse anomaly is an immediate
recorded failure).  Writes NOTHING to the evidence tree; prints the report
to stdout, nothing to stderr on success.  Exit 0 iff every check is ok.

THREE-STATE: this script RE-PARSES committed publication, record and script
bytes and committed raw run-log headers -- it measures NOTHING new on
hardware (no runs, no builds, NO GO stamp) and no value here is a
measurement of this tick; the session numbers, dirs and counts are READINGS
of committed bytes; every sample value whose window this map names remains
the named run's landed MEASURED QUANTITY on aiueos-6600hs (Intel BMG G31)
under the named instrument.  The accelerator-targets workgroup rows stay
exactly as ADR-0358 left them (:measured? false rows remain provisional --
NOT optimization evidence); NO vendor optimization exists for Intel (or for
any vendor) and none follows from this map.  RULE 4 unchanged: NOTHING
MOVES; the committed bracket stays EXACTLY (254,923, 255,045]; L9 binds at
n=254,984 (C2 (c), D3 (v)); the MID-ONLY NARROWING CLAIM stays SUSPENDED.
"""

import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

GPU = Path(__file__).resolve().parent.parent  # docs/evidence/gpu

# ----------------------------------------------------------------
# instrument contract (the s235 census rule, re-used verbatim)
# ----------------------------------------------------------------
V2_INSTR = ("# instrument=anv-subgroupsize-batch v2-batch64 "
            "(JUN-59 subgroup 16-vs-32 floor-lifting rerun, 2026-10-27)")
V1_INSTR_PREFIX = "# instrument=anv-subgroupsize v1"
HEADER_RE = re.compile(r"^# n=(\d+) rounds=(\d+) warmup=(\d+) batch=(\d+)(.*)$")

# ----------------------------------------------------------------
# citation forms (frozen above)
# ----------------------------------------------------------------
RE_PUB = re.compile(r"^publication-s(\d+)\.txt$")
RE_HDR_SRC = re.compile(
    r"C1 RE-DERIVATION (?:at s(\d+)|\(environment pin, from the s(\d+))")
RE_PRE_SRC = re.compile(r"session-(\d+) run logs|measured in session (\d+)")
RE_QUOTE_ROW = re.compile(
    r"^\s*s(\d+): c2 class FLOOR \(FLOOR required; committed floor band"
    r" 31\.\.32\); c8 \(sum,128,S=16\) pooled median \d+ vs committed"
    r" 32915", re.M)
RE_C8REF = re.compile(r"session (\d+) pooled median")
RE_GENERIC = re.compile(r"sessions?[- ](\d+(?:[/,-]\d+)*)")
RE_SECTION1 = re.compile(r"^\s*1\.\s")

RE_S215_ROW = re.compile(
    r"^(\d+)(?:st|nd|rd|th) cut -- publication-s(\d+)\.txt \(([^/]+)/\)",
    re.M)
RE_S234_TUPLE = re.compile(
    r'^\s*\("([a-z0-9-]+)",\s*(\d+),\s*"(cut|act)",\s*"([^"]+)",'
    r'\s*"([^"]+)",\s*"([^"]+)"\),', re.M)
RE_S235_REF = re.compile(
    r'^\s*\("([a-z0-9-]+)",\s*"([^"]+)",\s*"([^"]+)",\s*"([ab])"\),', re.M)
RE_S233_SPEC = re.compile(
    r'^\s*\((\d+), "([^"]+)", "(BRACKET|CLASSED|QUOTES|C1LINE|C1TWO)",'
    r' (?:None|"[^"]*"), (?:None|"[^"]*")\),', re.M)

S233_SCRIPT = GPU / "anv-b3control3state-20261102" / "enumerate-s233.py"
S234_SCRIPT = GPU / "anv-b3control3state-20261102" / "identity-shape-s234.py"
S235_SCRIPT = GPU / "anv-b3control3state-20261102" / "prepool-shape-s235.py"
S215_RECORD = (GPU / "anv-b3control3state-prereg-20261102" /
               "state-s215.txt")

problems = []
n_checks = [0]


def check(ok, label):
    n_checks[0] += 1
    if ok:
        print(f"  ok    {label}")
    else:
        print(f"  FAIL  {label}")
        problems.append(label)


def P(s=""):
    print(s)


def read_text(path):
    with open(path, "r", errors="strict") as fh:
        return fh.read()


def first_line(path):
    if path.name.endswith(".gz"):
        import gzip
        with gzip.open(path, "rt", errors="replace") as fh:
            return fh.readline().rstrip("\n")
    with open(path, "r", errors="replace") as fh:
        return fh.readline().rstrip("\n")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ================================================================
P("map-sessions-s236.py -- THE RECORD SESSION-NUMBERED WINDOW ->")
P("COMMITTED DIR MAPPING CHECK (amu-gpu s236; the s235 carry-forward's")
P("named row (ii) -- publication-side mapping row, not a raw-log row)")
P()
P("THE ROW (the s235 commit's NOT DONE (ii), quoted): 'whether every")
P("record session-numbered window maps onto a committed dir enumerated")
P("here stays UNCHECKED from committed bytes (a publication-side")
P("mapping row, not a raw-log row)' -- taken as this tick's ONE row.")
P("The map and the citation forms are frozen in this file's docstring")
P("BEFORE any number below is computed.")
P()

# ----------------------------------------------------------------
# 1. the publication-side map (V1)
# ----------------------------------------------------------------
P("1. PUBLICATION-SIDE MAP DERIVATION (V1: every committed file named")
P("   publication-sN.txt; the exact name form only -- the -run1/-run2/")
P("   -draft forms are NAMED in the census and excluded):")

all_pub_like = sorted(GPU.glob("*/publication*.txt"))
exact_rows = []      # (n, dir, path)
other_pub_names = []  # non-exact name forms (named, excluded)
for p in all_pub_like:
    m = RE_PUB.match(p.name)
    if m:
        try:
            text = read_text(p)
        except UnicodeDecodeError:
            check(False, f"publication reads strict UTF-8: "
                         f"{p.relative_to(GPU)}")
            text = ""
        exact_rows.append((int(m.group(1)), p.parent.name, p))
    else:
        other_pub_names.append(p)

P(f"   publication-like committed files found: {len(all_pub_like)}")
P(f"   exact publication-sN.txt rows (the map): {len(exact_rows)}")
P(f"   other name forms (NAMED, excluded from the map):"
  f" {len(other_pub_names)}")
for p in other_pub_names:
    P(f"     {p.relative_to(GPU)}")

map_n_dir = {}
dir_count = Counter()
for n, d, p in exact_rows:
    if n in map_n_dir:
        check(False, f"session {n} single-valued map (two dirs:"
                     f" {map_n_dir[n]} and {d})")
    map_n_dir[n] = d
    dir_count[d] += 1
check(len(map_n_dir) == len(exact_rows),
      "C1 every publication-sN.txt parses n and n is single-valued")
dup_dirs = sorted(d for d, c in dir_count.items() if c > 1)
check(not dup_dirs,
      "C1 at most one publication-sN.txt per dir")
P(f"   derived map rows (distinct sessions): {len(map_n_dir)}")
P(f"   map dirs (distinct): {len(dir_count)}")
P(f"   session range: {min(map_n_dir)}..{max(map_n_dir)}")

P()
P("   THE DERIVED MAP (session -> dir, from committed filename bytes):")
for n in sorted(map_n_dir):
    P(f"     s{n:<4d} -> {map_n_dir[n]}")

# ----------------------------------------------------------------
# 2. the record chain's own map claims (V6) confronted
# ----------------------------------------------------------------
P()
P("2. THE RECORD CHAIN'S OWN MAP CLAIMS CONFRONTED (V6: the committed")
P("   s233 SPEC table, the s234 WINDOWS tuples, the s235 REF_WINDOWS")
P("   rows -- every claim re-parsed from committed script bytes):")

spec_text = read_text(S233_SCRIPT)
spec_rows = [(int(m.group(1)), m.group(2))
             for m in RE_S233_SPEC.finditer(spec_text)]
check(len(spec_rows) == 80,
      f"C2 s233 SPEC parses exactly 80 (session, dir) rows"
      f" (got {len(spec_rows)})")
spec_mismatch = []
for n, d in spec_rows:
    if map_n_dir.get(n) != d:
        spec_mismatch.append((n, d, map_n_dir.get(n)))
check(not spec_mismatch,
      "C2 derived map == s233 SPEC session->dir (80 rows)")
for n, d, got in spec_mismatch:
    P(f"     MISMATCH s{n}: SPEC {d} vs derived {got}")
check(all(n in map_n_dir for n, _ in spec_rows),
      "C2 every SPEC session has a committed publication-sN.txt")
extra = sorted(set(map_n_dir) - {n for n, _ in spec_rows})
P(f"   map sessions outside the s233 SPEC (named; SPEC starts at s5):"
  f" {extra}")

s234_text = read_text(S234_SCRIPT)
s234_rows = [(m.group(1), int(m.group(2)), m.group(3), m.group(4),
              m.group(5), m.group(6))
             for m in RE_S234_TUPLE.finditer(s234_text)]
check(len(s234_rows) == 9,
      f"C3 s234 WINDOWS parses exactly 9 tuples (got {len(s234_rows)})")
for label, sess, kind, d, pat, pub in s234_rows:
    check(map_n_dir.get(sess) == d,
          f"C3 s234 tuple {label}: session {sess} -> {d} == derived map"
          f" ({map_n_dir.get(sess)})")
    check((GPU / d / pub).is_file(),
          f"C3 s234 tuple {label}: named publication {pub} sits in {d}")
    runs = [GPU / d / pat.format(i) for i in (1, 2, 3)]
    check(all(r.is_file() for r in runs),
          f"C3 s234 tuple {label}: run pattern {pat} present x3 in {d}")

s235_text = read_text(S235_SCRIPT)
s235_rows = [(m.group(1), m.group(2), m.group(3), m.group(4))
             for m in RE_S235_REF.finditer(s235_text)]
check(len(s235_rows) == 9,
      f"C3 s235 REF_WINDOWS parses exactly 9 rows (got {len(s235_rows)})")
s234_label_dir = {label: d for label, _, _, d, _, _ in s234_rows}
for label, d, arm, letter in s235_rows:
    check(s234_label_dir.get(label) == d,
          f"C3 s235 REF {label}: dir {d} == s234 WINDOWS dir"
          f" ({s234_label_dir.get(label)})")

# ----------------------------------------------------------------
# 3. citation forms V2/V3/V4/V7 over the publication corpus
# ----------------------------------------------------------------
P()
P("3. CITATION FORMS over the publication corpus (V2 header / V3")
P("   preamble / V4 quote row / V7 c8 reference; every cited session")
P("   is a record session-numbered window of this row's scope):")

cited = {}            # session -> Counter(form -> count)
prov_rows = []        # (n, dir, class, signals)
unparsed = Counter()  # normalized context line -> count
generic_sessions = Counter()  # sessions named only by generic forms

for n, d, p in sorted(exact_rows):
    text = read_text(p)
    lines = text.splitlines()
    # V2: first header-form hit
    hdr = None
    for ln in lines:
        m = RE_HDR_SRC.search(ln)
        if m:
            hdr = int(m.group(1) or m.group(2))
            break
    # V3: preamble = lines before the first '^1. ' section line (s233 rule)
    pre_end = len(lines)
    for i, ln in enumerate(lines):
        if RE_SECTION1.match(ln):
            pre_end = i
            break
    preamble = "\n".join(lines[:pre_end])
    pre_hits = list(RE_PRE_SRC.finditer(preamble))
    srcs = set()
    for m in pre_hits:
        srcs.add(int(m.group(1) or m.group(2)))
    signals = set(srcs)
    if hdr is not None:
        signals.add(hdr)
    ambiguous = bool(signals - {n}) and (n in signals
                                         or len(signals - {n}) > 1)
    check(not ambiguous,
          f"C4 s{n} provenance unambiguous (header"
          f" {'s%d' % hdr if hdr is not None else 'none'}, preamble"
          f" {sorted(srcs) or 'none'})")
    anchor = None
    if signals - {n}:
        anchor = sorted(signals - {n})[0]
    if anchor is None:
        cls = "own" if signals else "no-signal"
    else:
        cls = f"anchor@s{anchor}"
    prov_rows.append((n, d, cls, sorted(signals)))
    for s in signals:
        cited.setdefault(s, Counter())["V2/V3"] += 1
    # V4 quote rows
    for m in RE_QUOTE_ROW.finditer(text):
        cited.setdefault(int(m.group(1)), Counter())["V4"] += 1
    # V7 c8 reference citations
    v7_spans = [m.span() for m in RE_C8REF.finditer(text)]
    for m in RE_C8REF.finditer(text):
        cited.setdefault(int(m.group(1)), Counter())["V7"] += 1
    # generic 'session[- ]N' forms: named unparsed-form where not
    # covered by V3 preamble spans or V7 spans (frozen scoping)
    covered = [(m.start(), m.end()) for m in pre_hits]
    covered += v7_spans

    def covered_hit(pos):
        return any(a <= pos < b for a, b in covered)

    for ln in lines:
        for m in RE_GENERIC.finditer(ln):
            pos = text.find(ln) + m.start()
            if covered_hit(pos):
                continue
            sig = re.sub(r"\d+", "N", ln.strip())[:72]
            unparsed[sig] += 1
            for tok in re.split(r"[/,-]", m.group(1)):
                generic_sessions[int(tok)] += 1

P(f"   publications scanned: {len(exact_rows)}")
P(f"   provenance classes (V2/V3; the s233 ambiguity rule):")
prov_counts = Counter(cls.split("@")[0] for _, _, cls, _ in prov_rows)
for cls, cnt in sorted(prov_counts.items()):
    P(f"     {cls}: {cnt}")
P()
P("   per-publication provenance rows (own = window proper; anchor@sM =")
P("   re-derivation of session M's window, the s233 (iii) correction):")
for n, d, cls, sigs in prov_rows:
    P(f"     s{n:<4d} {d:<32s} {cls:<12s} signals={sigs}")

P()
P("   C4/C5 cited-session mapping (every cited session must map onto a")
P("   committed publication-side dir):")
unmapped_cited = []
for s in sorted(cited):
    forms = dict(cited[s])
    mapped = s in map_n_dir
    if not mapped:
        unmapped_cited.append(s)
    P(f"     s{s:<4d} map={'s%s->%s' % (s, map_n_dir[s]) if mapped else 'NONE'}"
      f" forms={forms}")
check(not unmapped_cited,
      "C5 every V2/V3/V4/V7-cited session maps onto a committed dir")
for s in unmapped_cited:
    P(f"     UNMAPPED CITED SESSION s{s} forms={dict(cited[s])}")

P()
P("   unparsed-form census (generic 'session[- ]N' mentions NOT covered")
P("   by V3/V7 -- NAMED, never silently skipped; bare 'sN' mentions are")
P("   outside this probe, a NAMED LIMITATION of the frozen forms):")
for sig, cnt in sorted(unparsed.items(), key=lambda kv: (-kv[1], kv[0])):
    P(f"     {cnt:4d}  {sig}")
P(f"   distinct unparsed forms: {len(unparsed)};"
  f" mentions: {sum(unparsed.values())}")
P("   sessions named ONLY by unparsed forms (REPORT rows; map status via")
P("   the derived map or the s216 readings where named):")
for s in sorted(set(generic_sessions) - set(map_n_dir)):
    P(f"     s{s}: mentions={generic_sessions[s]}"
      f" map={'s%s->%s' % (s, map_n_dir[s]) if s in map_n_dir else 'NONE'}")

# ----------------------------------------------------------------
# 4. the record's own rows (V5) and the s216 session-1..3 readings
# ----------------------------------------------------------------
P()
P("4. THE RECORD'S OWN ROWS (V5: the s215 four-cut table) and the s216")
P("   session-1..3 session-ID readings (REPORT only):")

s215_text = read_text(S215_RECORD)
s215_rows = [(int(m.group(1)), int(m.group(2)), m.group(3))
             for m in RE_S215_ROW.finditer(s215_text)]
check(len(s215_rows) == 4,
      f"C6 s215 record rows parse exactly 4 (ordinal, session, dir)"
      f" triples (got {len(s215_rows)})")
for ordinal, sess, d in s215_rows:
    check(map_n_dir.get(sess) == d,
          f"C6 s215 {ordinal}th cut: publication-s{sess}.txt in {d}"
          f" == derived map ({map_n_dir.get(sess)})")
    P(f"     {ordinal}th cut -> s{sess} -> {d}"
      f" (map: {map_n_dir.get(sess)})")

P()
P("   s216 (c) session-ID readings (READING, not a committed claim;")
P("   sessions 1..3 carry no publication-sN.txt names):")
for sess, d, note in (
        (1, "anv-subgroupsize-81632-20261027",
         "session 1's record (the floor-band primary origin)"),
        (2, "anv-subgroupsize-batch64-20261027",
         "floor-lifting rerun (batch64), s216 (c) reading"),
        (3, "anv-subgroupsize-batch64-rep-20261027",
         "floor-lifting rerun rep (batch64), s216 (c) reading")):
    exists = (GPU / d / "publication.txt").is_file()
    P(f"     s{sess}: {d}/publication.txt exists={exists} -- {note}")

# ----------------------------------------------------------------
# 5. the census side (the s235 rule re-derived) + the row's answer
# ----------------------------------------------------------------
P()
P("5. THE CENSUS SIDE (the s235 enumeration rule re-derived from")
P("   committed bytes; the s235 script NOT re-run): every run-* raw log")
P("   under docs/evidence/gpu, .stderr.txt siblings excluded; first-line")
P("   families; the c2-rung knob set; census windows = (dir, arm):")

all_run = sorted(p for p in GPU.rglob("run-*")
                 if p.is_file() and not p.name.endswith(".stderr.txt"))
v2_files, v1_files, other_files = [], [], []
for p in all_run:
    fl = first_line(p)
    if fl == V2_INSTR:
        v2_files.append(p)
    elif fl.startswith(V1_INSTR_PREFIX):
        v1_files.append(p)
    else:
        other_files.append(p)
check(len(v2_files) + len(v1_files) + len(other_files) == len(all_run),
      "C7 census reconciliation: v2 + v1 + other == every run-* file")
P(f"   run-* raw logs found: {len(all_run)}"
  f" (v2 {len(v2_files)}, v1 {len(v1_files)}, other {len(other_files)})")

c2_windows = {}   # (dir, arm) -> file count
run_dir_counts = Counter()
family_counts = Counter()
for p in v2_files:
    run_dir_counts[p.parent.name] += 1
    if p.name.endswith(".gz"):
        import gzip
        with gzip.open(p, "rt", errors="replace") as fh:
            head = [fh.readline().rstrip("\n") for _ in range(10)]
    else:
        with open(p, "r", errors="replace") as fh:
            head = [fh.readline().rstrip("\n") for _ in range(10)]
    hdr = next((l for l in head if l.startswith("# n=")), None)
    if hdr is None:
        check(False, f"v2 run without '# n=' header line:"
                     f" {p.relative_to(GPU)}")
        continue
    m = HEADER_RE.match(hdr)
    if not m:
        check(False, f"header line parse: {p.relative_to(GPU)}")
        continue
    n_, rounds, warmup, batch = (int(m.group(1)), int(m.group(2)),
                                 int(m.group(3)), int(m.group(4)))
    kv = dict(re.findall(r"(\w+)=(\S+)", m.group(5)))
    is_c2 = (n_ == 1000003 and batch == 2 and warmup == 3
             and kv.get("barrier_n") in (None, "0")
             and kv.get("work_mul") in (None, "1")
             and kv.get("ndiv") in (None, "1"))
    if is_c2:
        fam = re.sub(r"-r\d+\.txt(\.gz)?$", "", p.name[len("run-"):])
        c2_windows[(p.parent.name, fam)] = \
            c2_windows.get((p.parent.name, fam), 0) + 1
        family_counts[p.parent.name] += 1
for p in v1_files:
    run_dir_counts[p.parent.name] += 1
for p in other_files:
    run_dir_counts[p.parent.name] += 1

P(f"   c2-rung census windows (dir x arm): {len(c2_windows)}")
P(f"   c2-rung universe runs: {sum(c2_windows.values())}")
P(f"   dirs carrying run-* raw logs: {len(run_dir_counts)}")
P(f"   dirs carrying c2-rung universe runs: {len(family_counts)}")

# ----------------------------------------------------------------
# 6. THE ROW'S ANSWER
# ----------------------------------------------------------------
P()
P("6. THE ROW'S ANSWER (mapping outcomes, REPORT rows; every record")
P("   session-numbered window = every session named by V1..V7):")

W = sorted(set(map_n_dir) | set(cited))
P(f"   W (record session-numbered windows in scope): {len(W)}")
P(f"   {'sess':<6}{'mapped dir':<34}{'run-*':<7}{'c2 runs':<9}"
  f"{'census windows (dir x arm)':<44}{'E1':<7}E2")
e1_true = e2_true = 0
not_e1, not_e2 = [], []
for w in W:
    d = map_n_dir.get(w)
    if d is None:
        P(f"   s{w:<5d}{'NONE (unmapped)':<34}{'-':<7}{'-':<9}"
          f"{'-':<40}{'-':<4}{'-'}")
        not_e1.append(w)
        not_e2.append(w)
        continue
    rows = sorted((dd, arm, cnt) for (dd, arm), cnt in c2_windows.items()
                  if dd == d)
    rows_s = ", ".join(f"{arm}x{cnt}" for _, arm, cnt in rows) or "(none)"
    rc = run_dir_counts.get(d, 0)
    c2c = sum(cnt for _, _, cnt in rows)
    e1 = rc > 0
    e2 = c2c > 0
    e1_true += e1
    e2_true += e2
    if not e1:
        not_e1.append(w)
    if not e2:
        not_e2.append(w)
    P(f"   s{w:<5d}{d:<34}{rc:<7}{c2c:<9}{rows_s:<44}"
      f"{str(e1):<7}{e2}")

P()
P(f"   ANSWER (scoped to the frozen forms V1..V7): every record")
P(f"   session-numbered window maps onto exactly one committed dir")
P(f"   (single-valued, publication-side):"
  f" {sum(1 for w in W if w in map_n_dir)}/{len(W)}; of those,")
P("   enumerated in the s235 run-* census at run-* tree level (E1,")
P(f"   the dir carries committed run-* raw logs): {e1_true}/{len(W)};")
P("   at c2-rung universe level (E2, the dir carries committed c2-rung")
P(f"   runs of the s235 knob set): {e2_true}/{len(W)}.")
if not_e1:
    P(f"   NOT E1 (named): {['s%d' % w for w in not_e1]}")
if not_e2:
    P(f"   NOT E2 (named): {['s%d' % w for w in not_e2]}")
anchor_targets = sorted({int(cls.split("@s")[1]) for _, _, cls, _ in prov_rows
                         if cls.startswith("anchor@")})
anchor_pubs = sorted(n for n, _, cls, _ in prov_rows
                     if cls.startswith("anchor@"))
e1_false_nonanchor = sorted(w for w in not_e1 if w not in anchor_pubs)
P()
P("   COMPOSITION (named): of the mapped sessions, the anchor")
P(f"   re-derivation publications are exactly {len(anchor_pubs)} rows"
  f" (the s233 (iii) correction's shape; their dirs carry NO committed")
P(f"   run-* raw logs and their windows are their anchor targets')")
P(f"   windows): {['s%d' % n for n in anchor_pubs]}")
P(f"   the NOT-E1 rows outside the anchor set ({len(e1_false_nonanchor)}"
  f" -- their dirs likewise carry NO committed run-* raw logs;")
P(f"   publication-side sessions whose pubs quote or re-derive other")
P(f"   sessions' rows): {['s%d' % w for w in e1_false_nonanchor]}")
P(f"   every anchor-target window's census status (E1 dir run-*,")
P(f"   E2 c2-rung runs):")
for t in anchor_targets:
    d = map_n_dir.get(t)
    e1 = d is not None and run_dir_counts.get(d, 0) > 0
    e2 = d is not None and family_counts.get(d, 0) > 0
    P(f"     s{t} -> {d}: E1={e1} E2={e2}")
e2_only = sorted(set(not_e2) - set(not_e1))
P(f"   the E2-False rows among the E1-True sessions:"
  f" {['s%d' % w for w in e2_only]} (each sits OUTSIDE the s235 c2-rung")
P("   knob set by the s235 rule -- barrier_n=2 for s6, the")
P("   (BATCH,BARRIER_N) pair design, s232's named row -- NOT mapping")
P("   failures, knob-set boundaries named by the census rule itself)")
P("   The session<->dir identity is a PUBLICATION-SIDE reading of")
P("   committed bytes (the raw run logs carry NO session identity; this")
P("   is why the row is a publication-side mapping row, not a raw-log")
P("   row).  This map check establishes IDENTITY BINDING only: it")
P("   measures NOTHING and it moves NO row of any prior finding.")

# ----------------------------------------------------------------
# 7. three-state / scope / carry-forward
# ----------------------------------------------------------------
P()
P("7. THREE-STATE / SCOPE / RULE 4 / BAR: this tick re-parses")
P("   committed publication, record, script and raw run-log header")
P("   bytes -- it measures NOTHING new on hardware (NO runs, NO builds,")
P("   NO GO stamp); every sample value whose window this map names")
P("   remains the named run's landed MEASURED QUANTITY on aiueos-6600hs")
P("   (Intel BMG G31) under the named instrument; the mapping/count")
P("   rows are READINGS of committed bytes, not measurements; the")
P("   accelerator-targets workgroup rows stay exactly as ADR-0358 left")
P("   them (:measured? false rows remain provisional -- NOT optimization")
P("   evidence); NO vendor optimization exists for Intel (or for any")
P("   vendor) and none follows from this map.  RULE 4 unchanged:")
P("   NOTHING MOVES; the committed bracket stays EXACTLY (254,923,")
P("   255,045]; L9 binds at n=254,984 (C2 (c), D3 (v)); the MID-ONLY")
P("   NARROWING CLAIM stays SUSPENDED.  BAR NON-INTERFERENCE: NO")
P("   settle-bar-ledger line, NO day-slot consumption; the bar's")
P("   SETTLED INTERMEDIATE/MIXED verdict unmoved.")
P()
P("   NAMED, NOT HIDDEN: (a) sessions 1..3 carry no publication-sN.txt")
P("   names -- their placement is the s216 (c) session-ID READING")
P("   (reported above, never checked); (b) bare 'sN' mentions outside")
P("   V2/V4 are NOT read as window citations (the bare form does not")
P("   distinguish analysis-session file citations from window")
P("   citations) -- the unparsed-form census names every generic")
P("   'session[- ]N' mention so nothing is silently dropped; (c) the")
P("   W set is the frozen-forms scope -- a session-numbered window the")
P("   record names ONLY through a form outside V1..V7 would sit in the")
P("   unparsed-form census, not in W.")
P()
P("   NOT DONE (s237 carries exactly this list): the s216 identity")
P("   hazard's remaining residuals (standing, not queued): the CAUSE of")
P("   the sample-shape difference (execution-time state vs")
P("   instrument/timestamp-quantization state) stays UNMEASURED; the")
P("   underlying-instrument-state COUNT stays outside (s220 1(b)); (i)")
P("   at N=75 the classification carries NO noise model and 30/46")
P("   windows are NEAR-NEITHER -- a higher-N pre-deep-pooling shape")
P("   reading needs new hardware runs (each needs its own freeze;")
P("   standing, not queued); (iii) the excluded kernel-variant arms'")
P("   (sum,128,16) shapes (iter1/iter3/iter8 spvs) stay UNCHECKED (out")
P("   of scope by the s235 bytes-forced correction) -- QUEUED for s237;")
P("   standing, not queued: any further counted-day slot (each needs")
P("   its own freeze) and the cross-day tail-movement row.")
P()
P(f"checks: {n_checks[0]} run; failures: {len(problems)}")
P(f"# map-sessions s236 (map-sessions-s236.py):"
  f" {n_checks[0] - len(problems)} ok / {len(problems)} failed")
sys.exit(1 if problems else 0)
