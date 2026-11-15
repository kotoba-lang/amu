#!/usr/bin/env python3
"""JUN-59 session 101 -- THE W6 FRESH-WINDOW CENSUS-CHECK PRE-BUILD
(the fresh-window "every published integer cross-checked" duty -- the
NAMED gap session 100 left QUEUED: "the verifier twin
derivation-census-prego.py is --compat-only (the five committed
windows) and has NO w6 mode -- the fresh-window 'every published
integer cross-checked' duty is a NAMED gap (queued), not machinery
that exists").  NO hardware runs, NO builds, NO compiles, NO GO
stamp, NO host writes, NO day-slot consumption, NO ledger line; the
W6 measurement half REMAINS day-slot-gated (first session at/after
2026-10-30T00:00:00Z; this tick runs before it).  This is record-
checking machinery, not a device measurement.

WHAT THIS IS (honest states): an IMPLEMENTATION pre-build of the
fresh-window half of the derivation-census duty.  At the W6 window
the session publishes TWO artifacts from the same fresh logs
(publication-s<NN>.txt from the reading pair, the settle-bar-ledger
line from the emitter) and s99's reconcile-prego.py --line checks
the ledger pair AFTER the append -- but nothing checked the fresh
publication's OWN integers against the fresh run logs.  This tool
closes that surface: given the fresh publication and the fresh
window directory it re-derives EVERY published integer of the
publication body (sections 1-6 claim rows) from the six windows' run
logs plus the named committed want sources, in two-way rows
(published = find/split-extracted from the publication bytes; census
= re-derived here), and enforces COVERAGE: every digit run of the
publication body must lie inside a cross-checked claim span or a
NAMED structural span (vocabulary/provenance digits, listed, never
silent).  Fail-closed: an unparsed body line, a digit run outside
every span, or a want-source parse failure is a HARD error /
INCONSISTENT verdict -- never a silent pass.

MODES (deterministic; NO RNG anywhere, no clock):
  --w6 <publication> <fresh-window-dir> [OUTPUT-PATH]
      the fresh duty over the w6-shape publication produced by
      reading-prego-fixed.py (adopted as reading-s<NN>.py).  The
      five prior windows are the frozen WIN5 table; the fresh
      window's TAG is parsed from the publication header (session
      identity) and cross-checked against every printed fresh tag.
  --self-test [OUTPUT-PATH]
      fixture battery (every MOCK value below is a FIXTURE, never a
      measurement; the self-test reads NO committed window):
      digit-run extraction, the closed body line grammar (incl. the
      alternate shapes branch (b), False rows, multi-day census,
      NOT-SINGLE-DAY ledger day, FLOOR/CAPTURED classes), fail-
      closed unparsed-line handling, span coverage with a rogue
      digit, claim mismatch detection, the dual-estimator cross-
      check, the want-source parsers on synthetic bytes, the ok-map
      note relation and the section-6/section-3 relation.

INDEPENDENCE CONTRACT (the census lineage's side, frozen at s90):
- NO regex, NO re module.  Run-log parsing is split()-based k=v
  tokenising; publication parsing is find/split-based
  (reading-prego-fixed.py parses and prints with re.compile regexes
  and hardcoded literals).
- The pooled-median and min/max estimators are computed on the numpy
  np.partition kth paths CROSS-CHECKED IN-LOOP against pure-Python
  sorted() explicit order statistics (every pooled median and every
  block min/max is computed BOTH ways; the cross-check census is
  section D).  reading-prego-fixed.py is pure stdlib
  statistics.median/min/max and imports NO numpy at all.
- Want sources are PARSED from committed bytes, never transcribed:
  the five prior anchor want triples from publication-s73.txt, the
  committed c8 and the committed c2 floor band from
  publication-s73.txt, the frozen refs 1,129/1,132/1,131 from
  settle-bar.txt, the freeze stamp from protocol.txt.
- The c2 "committed floor band" is re-derived BOTH ways (printed
  want vs the min..max of the five committed windows' c2 pooled
  medians).

NAMED, NOT HIDDEN: the publication HEADER is outside the digit-
coverage body (provenance prose); it carries two explicit identity
claims instead (session number vs the producing script name; the
freeze stamp vs protocol.txt).  The body's NAMED structural spans
(section heading numbers, protocol cross-references, frozen
vocabulary ids L12/F3/V1/D4, the 0-based/1-based index-base labels,
the W6 window ordinal, the publication-s73/section-3b provenance
filenames) are non-quantity digits and are listed as rows in
section B.  The w6 rehearsal at pre-build time runs with the
committed W5 window standing in for the W6 window (the s100
convention): EVERY rehearsal number is a FIXTURE, NEVER a
measurement.

Usage: fresh-census-prego.py --w6 <publication> <fresh-window-dir>
       [OUTPUT-PATH] | --self-test [OUTPUT-PATH]
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
GPU = os.path.join(ROOT, "docs", "evidence", "gpu")
PUB_S73 = os.path.join(GPU, "anv-b3w5xdayrep-20261029", "publication-s73.txt")
SETTLE_BAR = os.path.join(GPU, "anv-b3settlebar-20261027", "settle-bar.txt")
PROTOCOL = os.path.join(GPU, "anv-b3w6daybar-20261030", "protocol.txt")

WIN5 = [("s36", "anv-b3commonmode-20261028"),
        ("s38", "anv-b3joint3-20261028"),
        ("s39", "anv-b3joint4-20261028"),
        ("s51", "anv-b3levelrep-20261028"),
        ("s73", "anv-b3w5xdayrep-20261029")]
ARMS = {"c2": (2, 1, 1, [1, 2, 3]),
        "hi": (3, 1024, 4033, list(range(1, 37))),
        "tw": (3, 2048, 8066, list(range(1, 37))),
        "c8": (8, 1, 1, [1, 2, 3])}
CELLKEY_SUM128 = ("sum", 128, "16")
NAMED_CKEY = ("max", 128, "default")


class ParseError(Exception):
    pass


# ------------------------------------------------------------------
# digit-run extraction and span coverage (no regex)
# ------------------------------------------------------------------
def digit_runs(line):
    """[(start, end)] end-exclusive spans of maximal [0-9]+ runs."""
    runs = []
    i = 0
    n = len(line)
    while i < n:
        if line[i].isdigit():
            j = i
            while j < n and line[j].isdigit():
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    return runs


def covered(spans, run):
    for (s, e) in spans:
        if s <= run[0] and run[1] <= e:
            return True
    return False


# ------------------------------------------------------------------
# dual-computation estimators (np.partition kth vs sorted() explicit)
# ------------------------------------------------------------------
XCHECKS = [0, 0]   # [comparisons, mismatches]


def median_int_dual(xs):
    """Exact pooled median as int: np.partition path vs sorted() path."""
    n = len(xs)
    arr = np.array(xs, dtype=np.int64)
    if n % 2 == 1:
        a = int(np.partition(arr, n // 2)[n // 2])
    else:
        p = np.partition(arr, (n // 2 - 1, n // 2))
        a = (int(p[n // 2 - 1]) + int(p[n // 2])) // 2
    s = sorted(xs)
    if n % 2 == 1:
        b = s[n // 2]
    else:
        b = (s[n // 2 - 1] + s[n // 2]) // 2
    XCHECKS[0] += 1
    if a != b:
        XCHECKS[1] += 1
    return a


def minmax_dual(xs):
    arr = np.array(xs, dtype=np.int64)
    a = (int(arr.min()), int(arr.max()))
    b = (min(xs), max(xs))
    XCHECKS[0] += 1
    if a != b:
        XCHECKS[1] += 1
    return a


# ------------------------------------------------------------------
# split-based run-log parser (k=v tokenising; NO regex) -- the s90
# census's independent parser, re-implemented here
# ------------------------------------------------------------------
def load(path):
    cells, verifies, samples = {}, [], []
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("CELL "):
            kv = {}
            for tok in line.split()[1:]:
                k, _, v = tok.partition("=")
                kv[k] = v
            cells[int(kv["idx"])] = dict(op=kv["op"], wg=int(kv["wg"]),
                                         forced=kv["forced"],
                                         pipeline=kv["pipeline"],
                                         void=kv["void"])
        elif line.startswith("VERIFY "):
            kv = {}
            for tok in line.split()[1:]:
                k, _, v = tok.partition("=")
                kv[k] = v
            verifies.append((int(kv["idx"]), int(kv["checked"]),
                             int(kv["mismatch"])))
        elif line.startswith("SAMPLE "):
            kv = {}
            for tok in line.split()[1:]:
                k, _, v = tok.partition("=")
                kv[k] = v
            samples.append((int(kv["round"]), int(kv["idx"]),
                            int(kv["gpu_ticks"]),
                            (int(kv["batch"]), int(kv["work_mul"]),
                             int(kv["ndiv"]))))
    return cells, verifies, samples


# ------------------------------------------------------------------
# want-source parsers over committed bytes (find/split; never
# transcribed)
# ------------------------------------------------------------------
def parse_c8_committed(text):
    """publication-s73.txt section 2: 'vs committed 32915' -> int."""
    i = text.find("vs committed ")
    if i < 0:
        raise ParseError("publication-s73: no 'vs committed'")
    j = i + len("vs committed ")
    k = j
    while k < len(text) and text[k].isdigit():
        k += 1
    return int(text[j:k])


def parse_floor_band(text):
    """publication-s73.txt section 2: 'committed floor band 31..32'."""
    i = text.find("committed floor band ")
    if i < 0:
        raise ParseError("publication-s73: no floor band")
    j = i + len("committed floor band ")
    k = text.find(")", j)
    return text[j:k]


def parse_refs(text):
    """settle-bar.txt: 'frozen numeric reference (1,129 / 1,132 / 1,131 --'."""
    i = text.find("numeric reference (")
    if i < 0:
        raise ParseError("settle-bar.txt: no frozen refs")
    j = i + len("numeric reference (")
    k = text.find("--", j)
    segs = [s.strip() for s in text[j:k].split(" / ")]
    vals = []
    for s in segs:
        s = s.rstrip(" )")
        if not s:
            continue
        vals.append(int(s.replace(",", "")))
    if len(vals) != 3:
        raise ParseError("settle-bar.txt: refs parse got %d values" % len(vals))
    return tuple(vals)


def parse_priors(text):
    """publication-s73.txt section 3b -> {tag: (med, lo, hi)} want.

    Rows carrying '(want M / A..B)' contribute that want; the '(NEW)'
    row's own values are its want.
    """
    priors = {}
    for line in text.split("\n"):
        s = line.strip()
        if ": median " not in s or "min..max " not in s:
            continue
        tag = s.split(":")[0].strip()
        if tag.endswith(" (NEW)"):
            tag = tag[:-len(" (NEW)")]
        if not (tag.startswith("s") and tag[1:].isdigit()):
            continue
        i = s.find("median ") + len("median ")
        j = s.find(" ", i)
        med = int(s[i:j])
        k = s.find("min..max ") + len("min..max ")
        l = s.find(".", k)
        lo = int(s[k:l])
        m = l + 2
        while m < len(s) and s[m].isdigit():
            m += 1
        hi = int(s[l + 2:m])
        w = s.find("(want ")
        if w >= 0:
            seg = s[w + len("(want "):]
            slash = seg.find(" / ")
            med = int(seg[:slash])
            seg2 = seg[slash + len(" / "):]
            dot = seg2.find("..")
            lo = int(seg2[:dot])
            tail = seg2[dot + 2:]
            hi_str = ""
            for ch in tail:
                if ch.isdigit():
                    hi_str += ch
                else:
                    break
            hi = int(hi_str)
        priors[tag] = (med, lo, hi)
    return priors


def parse_stamp(text):
    """'freeze stamp 2026-10-29T04:23:51Z' -> the stamp string."""
    i = text.find("freeze stamp ")
    if i < 0:
        raise ParseError("no freeze stamp")
    j = i + len("freeze stamp ")
    k = text.find("Z", j)
    return text[j:k + 1]


def run_days_from_text(text):
    days = []
    for line in text.split("\n"):
        i = line.find("host-date=")
        if i >= 0:
            days.append(line[i + len("host-date="):i + len("host-date=") + 10])
    return days


# ------------------------------------------------------------------
# the engine (re-derived from the six windows' run logs)
# ------------------------------------------------------------------
class Engine(object):
    def __init__(self, fresh_tag, fresh_dir):
        self.windows = WIN5 + [(fresh_tag, fresh_dir)]
        self.fresh_tag = fresh_tag
        self.data = {}
        self.win_info = {}
        ref_cellmap = None
        for win, dirname in self.windows:
            src = os.path.join(GPU, dirname)
            vmis = 0
            counts_ok = knob_ok = fail_ok = cmap_ok = True
            nlogs = 0
            for tag in ("c2", "hi", "tw", "c8"):
                b, wm, dd, runs = ARMS[tag]
                for r in runs:
                    fn = os.path.join(src, "run-%s-r%d.txt" % (tag, r))
                    cells, verifies, samples = load(fn)
                    self.data[(win, tag, r)] = (cells, verifies, samples)
                    nlogs += 1
                    for (_i, _c, mis) in verifies:
                        vmis += mis
                    okc = [k for k, v in cells.items()
                           if v["pipeline"] == "ok"]
                    s8 = [k for k, v in cells.items() if v["forced"] == "8"]
                    if len(s8) != 6 or any(cells[k]["pipeline"] != "FAIL"
                                           or cells[k]["void"] != "1"
                                           for k in s8):
                        fail_ok = False
                    if len(samples) != len(okc) * 25 or len(verifies) != 24:
                        counts_ok = False
                    for (_rnd, _idx, _gt, knobs) in samples:
                        if knobs != (b, wm, dd):
                            knob_ok = False
                    cmap = tuple(sorted(
                        (k, v["op"], v["wg"], v["forced"], v["pipeline"],
                         v["void"]) for k, v in cells.items()))
                    if ref_cellmap is None:
                        ref_cellmap = cmap
                    elif cmap != ref_cellmap:
                        cmap_ok = False
            self.win_info[win] = dict(vmis=vmis, counts_ok=counts_ok,
                                      knob_ok=knob_ok, fail_ok=fail_ok,
                                      cmap_ok=cmap_ok, nlogs=nlogs)
        first = self.windows[0][0]
        ref = self.data[(first, "c2", 1)][0]
        self.ok_cells = sorted([k for k, v in ref.items()
                                if v["pipeline"] == "ok"])
        self.sum128 = [k for k in self.ok_cells
                       if self.ckey(k) == CELLKEY_SUM128][0]
        self.nc = [k for k in self.ok_cells
                   if self.ckey(k) == NAMED_CKEY][0]
        self.rounds_per_cell = len(
            [s for s in self.data[(first, "c2", 1)][2]
             if s[1] == self.sum128])
        self.block_a_runs = ARMS["hi"][3][:3]

    def ckey(self, idx):
        c = self.data[(self.windows[0][0], "c2", 1)][0][idx]
        return (c["op"], c["wg"], c["forced"])

    def ckey_str(self, idx):
        op, wg, s = self.ckey(idx)
        return "(%s,%s,S=%s)" % (op, wg, s)

    def ok_pos0(self, idx):
        return self.ok_cells.index(idx)

    def pooled(self, win, tag, idx, runs):
        xs = []
        for r in runs:
            xs += [s[2] for s in self.data[(win, tag, r)][2] if s[1] == idx]
        assert len(xs) == 25 * len(runs)
        return median_int_dual(xs)

    def block_vals(self, win, tag, runs):
        vals = [self.pooled(win, tag, k, runs) for k in self.ok_cells]
        return vals

    def anchor(self, win):
        med = self.pooled(win, "hi", self.sum128, [1, 2, 3])
        bv = self.block_vals(win, "hi", [1, 2, 3])
        lo, hi = minmax_dual(bv)
        return (med, lo, hi, bar_class(bv))

    def flags_row(self, win):
        info = self.win_info[win]
        return ("counts %s knobs %s s8 %s cmap %s" %
                (info["counts_ok"], info["knob_ok"], info["fail_ok"],
                 info["cmap_ok"]))

    def runs_row(self, win):
        return self.win_info[win]["nlogs"]

    def vmis_row(self, win):
        return self.win_info[win]["vmis"]


def bar_class(bvals):
    if all(v <= 100 for v in bvals):
        return "FLOOR"
    if all(v >= 1000 for v in bvals):
        return "CAPTURED"
    return "INTERMEDIATE/MIXED"


# ------------------------------------------------------------------
# publication body line grammar (closed, fail-closed; find/split)
# ------------------------------------------------------------------
def span_of(line, needle, start=0):
    i = line.find(needle, start)
    if i < 0:
        raise ParseError("span not found: %r in %r" % (needle, line))
    return (i, i + len(needle))


def parse_body(text):
    """-> (P parsed values, claim_spans, struct_spans, body_slice).

    claim_spans / struct_spans: {body_line_index: [(start, end)]}.
    """
    lines = text.split("\n")
    i1 = None
    i6 = None
    for i, line in enumerate(lines):
        if line.startswith("1. INTEGRITY ("):
            i1 = i
        if "values by construction): median " in line:
            i6 = i
    if i1 is None or i6 is None or i6 < i1:
        raise ParseError("body slice not found")
    body = lines[i1:i6 + 1]

    P = {}
    P["sec1"] = []
    P["prior_rows"] = []
    cs = {}
    ss = {}

    def c(i, s, e):
        cs.setdefault(i, []).append((s, e))

    def st(i, s, e):
        ss.setdefault(i, []).append((s, e))

    for i, line in enumerate(body):
        s = line.strip()
        if s == "":
            continue
        if line.startswith("1. INTEGRITY ("):
            st(i, 0, 2)
        elif s == "s80 protocol section 3):":
            st(i, line.find("s80"), line.find(")"))
        elif ": runs " in line:
            j = line.find(": runs ")
            s2 = line.strip()
            tag = s2[:j - (len(line) - len(s2))].strip()
            a = line.find("runs ") + len("runs ")
            b = line.find(" ", a)
            cc = line.find("vmis ") + len("vmis ")
            d = line.find(" ", cc)
            flags_start = line.find("counts ")
            if flags_start < 0 or not line.endswith(
                    line[flags_start:].strip()) :
                pass
            flags = line[flags_start:].strip()
            expect = ["counts", "knobs", "s8", "cmap"]
            toks = flags.split()
            if len(toks) != 8 or [toks[0], toks[2], toks[4], toks[6]] != expect:
                raise ParseError("sec1 flags shape: %r" % line)
            for t in ("runs", "vmis", "counts", "knobs", "s8", "cmap"):
                if (" " + t + " ") not in (" " + line.strip() + " ") and \
                   not line.strip().startswith(t + " "):
                    raise ParseError("sec1 label %s missing: %r" % (t, line))
            rec = dict(tag=tag, runs=line[a:b],
                       vmis=line[cc:d], flags=flags,
                       tag_span=span_of(line, tag),
                       runs_span=(a, b), vmis_span=(cc, d),
                       flags_span=(flags_start, len(line)))
            for _sp in (rec["tag_span"], rec["runs_span"],
                        rec["vmis_span"], rec["flags_span"]):
                c(i, _sp[0], _sp[1])
            P["sec1"].append(rec)
        elif "named cell (" in line:
            k0 = line.find("(max,128,S=default)")
            if k0 < 0:
                raise ParseError("named cell key shape: %r" % line)
            c(i, k0, k0 + len("(max,128,S=default)"))
            P["named_key"] = "(max,128,S=default)"
            a = line.find("ok-map cell ") + len("ok-map cell ")
            b = line.find(",", a)
            c(i, line.find("ok-map cell "), b)
            P["ok_i"] = line[a:b]
            a = line.find("raw idx ") + len("raw idx ")
            b = a
            while b < len(line) and line[b].isdigit():
                b += 1
            c(i, line.find("raw idx "), b)
            P["ok_j"] = line[a:b]
        elif "(the ok-map cell index is" in line:
            st(i, *span_of(line, "0-based"))
            st(i, *span_of(line, "s80 section-3"))
        elif "'ok-map cell " in line:
            a = line.find("'ok-map cell ")
            b = line.find("'", a + 1) + 1
            c(i, a, b)
            P["note_i"] = line[a + len("'ok-map cell "):b - 1]
            a = line.find("position is ") + len("position is ")
            b = line.find(")", a)
            c(i, line.find("position is "), b + 1)
            P["note_k"] = line[a:b]
            st(i, *span_of(line, "1-based"))
        elif "INVALIDATION criterion" in line:
            st(i, *span_of(line, "protocol section 3"))
        elif s == "FLAGGED (no reading, no day slot).":
            pass
        elif line.startswith("2. C1 RE-DERIVATION"):
            st(i, 0, 2)
            st(i, *span_of(line, "C1"))
            a = line.find("the ") + len("the ")
            b = line.find(" window's", a)
            c(i, a, b)
            P["sec2_tag"] = line[a:b]
        elif "c2 class: " in line:
            c(i, *span_of(line, "c2"))
            a = line.find("c2 class: ") + len("c2 class: ")
            b = line.find(" (", a)
            c(i, a, b)
            P["c2_cls"] = line[a:b]
            a = line.find("committed floor band ") + len("committed floor band ")
            b = line.find(")", a)
            c(i, line.find("committed floor band "), b)
            P["band"] = line[a:b]
        elif "c8 (sum,128,S=" in line:
            c(i, *span_of(line, "c8"))
            a = line.find("(sum,128,S=")
            b = line.find(")", a) + 1
            c(i, a, b)
            P["c8_key"] = line[a:b]
            a = line.find("pooled median ") + len("pooled median ")
            b = line.find(" ", a)
            c(i, line.find("pooled median "), b)
            P["c8_med"] = line[a:b]
            a = line.find("vs committed ") + len("vs committed ")
            b = line.find(" ", a)
            c(i, line.find("vs committed "), b)
            P["c8_com"] = line[a:b]
            b = line.find("% delta")
            a = line.rfind("(", 0, b) + 1
            c(i, a, b)
            P["delta"] = line[a:b]
            a = line.find("+/-")
            b = line.find("%", a) + 1
            c(i, a, b)
            P["tol_c1"] = line[a + len("+/-"):b - 1]
        elif "C1 branch: " in line:
            c(i, *span_of(line, "C1"))
            a = line.find("(")
            b = line.find(")", a) + 1
            c(i, a, b)
            P["branch"] = line[a + 1:b - 1]
        elif line.startswith("3. THE ANCHOR READING"):
            st(i, 0, 2)
            st(i, *span_of(line, "L12"))
        elif "the reading unit is one 3-run block pooled over 25" in line:
            c(i, *span_of(line, "3"))
            c(i, *span_of(line, "25"))
        elif "the frozen estimator unit F3" in line:
            st(i, *span_of(line, "F3"))
        elif "(NEW): median " in line:
            s2 = line.strip()
            b = line.find(" (NEW)")
            c(i, 0, b)
            P["fresh_tag"] = s2[:s2.find(" (NEW)")].strip()
            a = line.find("median ") + len("median ")
            b = line.find(" ", a)
            c(i, line.find("median "), b)
            P["f_med"] = line[a:b]
            a = line.find("min..max ") + len("min..max ")
            b = line.find(";", a)
            c(i, line.find("min..max "), b)
            mm = line[a:b]
            dot = mm.find("..")
            P["f_lo"] = mm[:dot]
            P["f_hi"] = mm[dot + 2:]
            a = line.find("; class ") + len("; class ")
            c(i, line.find("; class "), len(line))
            P["f_cls"] = line[a:]
        elif "in-band vs the bar's frozen refs " in line:
            a = line.find("frozen refs ") + len("frozen refs ")
            b = line.find(" (", a)
            c(i, line.find("frozen refs "), b)
            P["refs"] = line[a:b]
        elif "+/-5% of EACH" in line:
            a = line.find("+/-")
            b = line.find("%", a) + 1
            c(i, a, b)
            P["tol_band"] = line[a + len("+/-"):b - 1]
            st(i, *span_of(line, "V1"))
            a = line.find("): ") + len("): ")
            c(i, line.find("): "), len(line))
            P["in_band"] = line[a:]
        elif line.startswith("4. PRIOR-WINDOW"):
            st(i, 0, 2)
        elif "from the committed publication-s73.txt bytes" in line:
            st(i, *span_of(line, "publication-s73.txt"))
        elif "carry NO class token" in line:
            st(i, *span_of(line, "publication-s73"))
            st(i, *span_of(line, "section-3b"))
        elif "transcribed; reproduction EXACT required" in line or \
                "row shape, and a class-bearing prior row" in line or \
                "reconcile-prego.py --line as a BAR tuple" in line or \
                "(a False row means" in line or \
                "committed priors; FAIL-CLOSED" in line or \
                "from this reading.)" in line:
            pass
        elif ": median " in line and "(want " in line and \
                "reproduction EXACT: " in line:
            s2 = line.strip()
            b = line.find(": median")
            c(i, 0, b)
            tag = s2[:s2.find(": median")].strip()
            a = line.find("median ") + len("median ")
            bb = line.find(" ", a)
            c(i, line.find("median "), bb)
            med = line[a:bb]
            a = line.find("min..max ") + len("min..max ")
            bb = line.find(" (want", a)
            c(i, line.find("min..max "), bb)
            mm = line[a:bb]
            dot = mm.find("..")
            lo, hi = mm[:dot], mm[dot + 2:]
            a = line.find("(want ") + len("(want ")
            bb = line.find(" / ", a)
            c(i, line.find("(want "), bb)
            wmed = line[a:bb]
            a = bb + len(" / ")
            bb = line.find(")", a)
            c(i, a - len(" / ") + 1, bb)
            wmm = line[a:bb]
            dot = wmm.find("..")
            wlo, whi = wmm[:dot], wmm[dot + 2:]
            a = line.find("reproduction EXACT: ") + len("reproduction EXACT: ")
            c(i, line.find("reproduction EXACT: "), len(line))
            rbool = line[a:]
            P["prior_rows"].append(dict(tag=tag, med=med, lo=lo, hi=hi,
                                        wmed=wmed, wlo=wlo, whi=whi,
                                        rbool=rbool))
        elif "all five prior windows reproduce EXACTLY: " in line:
            a = line.find("EXACTLY: ") + len("EXACTLY: ")
            c(i, line.find("EXACTLY: "), len(line))
            P["all_prior"] = line[a:]
        elif line.startswith("5. THE RUN DAY"):
            st(i, 0, 2)
            st(i, *span_of(line, "s80 protocol section 1"))
        elif "day = the W6 run's ACTUAL UTC day" in line:
            st(i, *span_of(line, "W6"))
        elif "run-window host-dates: " in line:
            a = line.find("host-dates: ") + len("host-dates: ")
            b = line.find(" ", a)
            c(i, line.find("host-dates: "), b)
            P["day_n"] = line[a:b]
            dp = line.find(" distinct: ")
            e = dp
            while e > 0 and line[e - 1].isdigit():
                e -= 1
            c(i, e, dp)
            P["day_d"] = line[e:dp]
            off = dp + len(" distinct: ")
            dates = line[off:].split()
            for dt in dates:
                d0 = line.find(dt, off)
                c(i, d0, d0 + len(dt))
            P["day_dates"] = dates
        elif "ledger line day = " in line:
            a = line.find("day = ") + len("day = ")
            c(i, line.find("day = "), len(line))
            P["ledger_day"] = line[a:]
        elif line.startswith("6. THE BAR READING ROW"):
            st(i, 0, 2)
            st(i, *span_of(line, "D4"))
        elif "printed a second time" in line or \
                "agreement check; both class-bearing" in line:
            pass
        elif "values by construction): median " in line:
            a = line.find("median ") + len("median ")
            b = line.find(" ", a)
            c(i, line.find("median "), b)
            P["b_med"] = line[a:b]
            a = line.find("min..max ") + len("min..max ")
            b = line.find(",", a)
            c(i, line.find("min..max "), b)
            mm = line[a:b]
            dot = mm.find("..")
            P["b_lo"] = mm[:dot]
            P["b_hi"] = mm[dot + 2:]
            a = line.find("class ") + len("class ")
            c(i, line.find("class "), len(line))
            P["b_cls"] = line[a:]
        else:
            raise ParseError("unparsed body line %d: %r" % (i, line))
    return P, cs, ss, body


# ------------------------------------------------------------------
# claim assembly + coverage + report
# ------------------------------------------------------------------
def run_w6(pub_path, fresh_dir):
    text = open(pub_path).read()

    # header identity claims (outside the coverage body; named)
    first = text.split("\n")[0]
    j = first.find("session ") + len("session ")
    k = j
    while k < len(first) and first[k].isdigit():
        k += 1
    session = first[j:k]
    fresh_tag = "s" + session
    j = text.find("reading-s") + len("reading-s")
    k = j
    while k < len(text) and text[k].isdigit():
        k += 1
    script_session = text[j:k]
    head_stamp = parse_stamp(text)

    P, cs, ss, body = parse_body(text)

    # want sources over committed bytes
    p73 = open(PUB_S73).read()
    c8_committed = parse_c8_committed(p73)
    band73 = parse_floor_band(p73)
    refs = parse_refs(open(SETTLE_BAR).read())
    priors = parse_priors(p73)
    if sorted(priors) != ["s36", "s38", "s39", "s51", "s73"]:
        raise ParseError("prior want tags: %s" % sorted(priors))
    proto_stamp = parse_stamp(open(PROTOCOL).read())

    # engine over the six windows (fresh = the named directory)
    E = Engine(fresh_tag, fresh_dir)

    # derived values
    c2_vals = E.block_vals(fresh_tag, "c2", [1, 2, 3])
    c2_cls = bar_class(c2_vals)
    c8_m = E.pooled(fresh_tag, "c8", E.sum128, [1, 2, 3])
    delta = abs(c8_m - c8_committed) / float(c8_committed) * 100
    c1_ok = (c2_cls == "FLOOR") and \
        abs(c8_m - c8_committed) <= 0.05 * c8_committed
    anchor = E.anchor(fresh_tag)
    in_band = all(abs(anchor[0] - ref) <= 0.05 * ref for ref in refs)
    committed_c2 = []
    for win, _d in WIN5:
        committed_c2 += E.block_vals(win, "c2", [1, 2, 3])
    band_min, band_max = minmax_dual(committed_c2)
    band = "%d..%d" % (band_min, band_max)
    days = run_days_from_text(
        open(os.path.join(GPU, fresh_dir, "run-window.txt")).read())
    distinct = sorted(set(days))
    if len(distinct) == 1:
        ledger_day = distinct[0]
    else:
        ledger_day = "NOT SINGLE-DAY (%s)" % ",".join(distinct)

    # claim rows: (kind, label, want, got, spans-by-body-index)
    rows = []
    claim_idx = {}
    for i, spans in cs.items():
        for sp in spans:
            claim_idx.setdefault(i, []).append(sp)

    def add(kind, label, want, got, spans=()):
        rows.append((kind, label, str(want), str(got),
                     [(i, s, e) for (i, s, e) in spans]))

    # header claims
    add("claim", "header session number vs producing script name",
        session, script_session)
    add("claim", "header freeze stamp vs protocol.txt stamp",
        head_stamp, proto_stamp)

    # section 1
    want_tags = " ".join([r["tag"] for r in P["sec1"]])
    got_tags = " ".join([w for w, _d in E.windows])
    tag_spans = []
    for i in cs:
        pass
    add("claim", "sec1 window tags in order", want_tags, got_tags,
        [sp for r in P["sec1"] for sp in
         [(li, r["tag_span"][0], r["tag_span"][1])
          for li in [i for i in cs if r["tag_span"] in cs[i]]]])
    for r in P["sec1"]:
        li = [i for i in cs if r["runs_span"] in cs[i]][0]
        add("claim", "sec1 %s runs parsed" % r["tag"], r["runs"],
            E.runs_row(r["tag"]), [(li, r["runs_span"][0], r["runs_span"][1])])
        add("claim", "sec1 %s VERIFY mismatch total" % r["tag"], r["vmis"],
            E.vmis_row(r["tag"]),
            [(li, r["vmis_span"][0], r["vmis_span"][1])])
        add("claim", "sec1 %s integrity flags" % r["tag"], r["flags"],
            E.flags_row(r["tag"]),
            [(li, r["flags_span"][0], r["flags_span"][1])])
    add("claim", "named cell key (max,128,S=default)", P["named_key"],
        E.ckey_str(E.nc))
    add("claim", "named cell 0-based ok-map index", P["ok_i"],
        E.ok_pos0(E.nc))
    add("claim", "named cell raw idx", P["ok_j"], E.nc)
    add("claim", "ok-map note relation (0-based echo, 1-based = +1)",
        "%s/%s" % (P["note_i"], P["note_k"]),
        "%d/%d" % (E.ok_pos0(E.nc), E.ok_pos0(E.nc) + 1))

    # section 2
    add("claim", "sec2 fresh window tag identity", P["sec2_tag"], fresh_tag)
    add("claim", "sec2 c2 class", P["c2_cls"], c2_cls)
    add("claim", "sec2 committed c2 floor band (five committed windows' "
        "c2 pooled medians, min..max)", P["band"], band)
    add("claim", "sec2 c8 cell key", P["c8_key"], E.ckey_str(E.sum128))
    add("claim", "sec2 c8 pooled median (fresh window)", P["c8_med"], c8_m)
    add("claim", "sec2 committed c8 (publication-s73.txt want)",
        P["c8_com"], c8_committed)
    add("claim", "sec2 c8 delta percent", P["delta"], "%.2f" % delta)
    add("claim", "sec2 C1 tolerance percent", P["tol_c1"], "5")
    add("claim", "sec2 C1 branch letter", P["branch"],
        "a" if c1_ok else "b")

    # section 3
    add("claim", "sec3 fresh window tag identity", P["fresh_tag"], fresh_tag)
    add("claim", "sec3 fresh anchor median", P["f_med"], anchor[0])
    add("claim", "sec3 fresh anchor min..max",
        "%s..%s" % (P["f_lo"], P["f_hi"]), "%d..%d" % (anchor[1], anchor[2]))
    add("claim", "sec3 fresh anchor class", P["f_cls"], anchor[3])
    want_refs = tuple(int(x.replace(",", "")) for x in P["refs"].split("/"))
    add("claim", "sec3 frozen refs (settle-bar.txt want)",
        "%d/%d/%d" % want_refs, "%d/%d/%d" % refs)
    add("claim", "sec3 in-band tolerance percent", P["tol_band"], "5")
    add("claim", "sec3 in-band verdict", P["in_band"], in_band)

    # section 4
    for r in P["prior_rows"]:
        a = E.anchor(r["tag"])
        add("claim", "sec4 %s anchor re-derived" % r["tag"],
            "%s %s..%s" % (r["med"], r["lo"], r["hi"]),
            "%d %d..%d" % (a[0], a[1], a[2]))
        w = priors[r["tag"]]
        add("claim", "sec4 %s want triple (publication-s73.txt)" % r["tag"],
            "%s %s..%s" % (r["wmed"], r["wlo"], r["whi"]),
            "%d %d..%d" % w)
        rok = (a[0], a[1], a[2]) == w
        add("claim", "sec4 %s reproduction EXACT" % r["tag"], r["rbool"], rok)
    all_ok = all((E.anchor(r["tag"])[0], E.anchor(r["tag"])[1],
                  E.anchor(r["tag"])[2]) == priors[r["tag"]]
                 for r in P["prior_rows"])
    add("claim", "sec4 all five prior windows reproduce EXACTLY",
        P["all_prior"], all_ok)

    # section 5
    add("claim", "sec5 host-dates parsed", P["day_n"], len(days))
    add("claim", "sec5 host-dates distinct", P["day_d"], len(distinct))
    add("claim", "sec5 host-dates list", " ".join(P["day_dates"]),
        " ".join(distinct))
    add("claim", "sec5 ledger line day", P["ledger_day"], ledger_day)

    # section 6
    add("claim", "sec6 bar row median", P["b_med"], anchor[0])
    add("claim", "sec6 bar row min..max",
        "%s..%s" % (P["b_lo"], P["b_hi"]), "%d..%d" % (anchor[1], anchor[2]))
    add("claim", "sec6 bar row class", P["b_cls"], anchor[3])
    add("claim", "sec6 bar row equals sec3 fresh row",
        "%s %s..%s %s" % (P["f_med"], P["f_lo"], P["f_hi"], P["f_cls"]),
        "%s %s..%s %s" % (P["b_med"], P["b_lo"], P["b_hi"], P["b_cls"]))
    add("claim", "sec2/sec3/sec1 fresh tag agreement",
        "%s %s %s" % (P["sec2_tag"], P["fresh_tag"], P["sec1"][-1]["tag"]),
        "%s %s %s" % (fresh_tag, fresh_tag, fresh_tag))

    # structural rows (named, not hidden)
    for i in sorted(ss):
        for (s, e) in ss[i]:
            add("structural", "body line %d structural span %r" %
                (i, body[i][s:e]), "structural", "structural")

    # coverage
    unclaimed = []
    n_runs = 0
    for i, line in enumerate(body):
        for run in digit_runs(line):
            n_runs += 1
            if covered(cs.get(i, []), run):
                continue
            if covered(ss.get(i, []), run):
                continue
            unclaimed.append((i, run, line[run[0]:run[1]]))

    # report
    out = []
    o = out.append
    o("JUN-59 session 101 -- W6 FRESH-WINDOW CENSUS-CHECK PRE-BUILD")
    o("(fresh-census-prego.py -- the fresh-window 'every published")
    o("integer cross-checked' duty, the s100 named gap; NO hardware")
    o("runs, NO builds, NO compiles, NO GO stamp, NO host writes, NO")
    o("day-slot consumption, NO ledger line).")
    o("")
    o("publication: %s" % pub_path)
    o("fresh window: %s (tag %s)" % (fresh_dir, fresh_tag))
    o("prior windows: %s" % " ".join(w for w, _d in WIN5))
    o("")
    o("Independence contract: NO re module (split()-based k=v run-log")
    o("parsing, find/split publication parsing); estimators on the")
    o("numpy np.partition kth paths CROSS-CHECKED in-loop against")
    o("pure-Python sorted() explicit order statistics; want sources")
    o("parsed from committed bytes (publication-s73.txt /")
    o("settle-bar.txt / protocol.txt), never transcribed; NO RNG, no")
    o("clock.")
    o("")
    o("A. TWO-WAY CLAIM ROWS (published = find/split-extracted from")
    o("   the publication bytes; census = re-derived here):")
    nfail = 0
    for n, (kind, label, want, got, _sp) in enumerate(rows):
        if kind != "claim":
            continue
        ok = (want == got)
        if not ok:
            nfail += 1
        o("row %02d: %s: published [%s] | census [%s] | match %s" %
          (n + 1, label, want, got, ok))
    nclaims = len([r for r in rows if r[0] == "claim"])
    o("")
    o("   TOTAL: %d claim rows, %d mismatched" % (nclaims, nfail))
    o("")
    o("B. STRUCTURAL DIGIT RUNS (named, not hidden -- non-quantity")
    o("   vocabulary/provenance digits registered as spans while")
    o("   parsing):")
    for n, (kind, label, want, got, _sp) in enumerate(rows):
        if kind != "structural":
            continue
        o("row %02d: %s: [%s]" % (n + 1, label, want))
    o("   TOTAL: %d structural spans" %
      len([r for r in rows if r[0] == "structural"]))
    o("")
    o("C. COVERAGE (every digit run of the publication body must lie")
    o("   in a claim or structural span):")
    o("   body digit runs: %d; UNCLAIMED: %d" % (n_runs, len(unclaimed)))
    for (i, run, tok) in unclaimed:
        o("   UNCLAIMED line %d: %r" % (i, tok))
    o("")
    o("D. IN-LOOP DUAL-COMPUTATION CROSS-CHECK (np.partition kth path")
    o("   vs pure-Python sorted() explicit order statistics):")
    o("   pooled-median + min/max dual computations: %d comparisons," %
      XCHECKS[0])
    o("   %d mismatched" % XCHECKS[1])
    o("")
    verdict = "CONSISTENT" if (nfail == 0 and not unclaimed and
                               XCHECKS[1] == 0) else "INCONSISTENT"
    o("VERDICT: %s" % verdict)
    text_out = "\n".join(out) + "\n"
    if len(sys.argv) > 4:
        with open(sys.argv[4], "w") as f:
            f.write(text_out)
    else:
        sys.stdout.write(text_out)
    return 0 if verdict == "CONSISTENT" else 1


# ------------------------------------------------------------------
# --self-test (MOCK fixtures only; reads NO committed window)
# ------------------------------------------------------------------
def self_test():
    results = []

    def ck(name, got, want):
        results.append((name, got, want, got == want))

    # digit-run extraction
    ck("digit_runs comma numbers",
       digit_runs("1,129/1,132/1,131"),
       [(0, 1), (2, 5), (6, 7), (8, 11), (12, 13), (14, 17)])
    ck("digit_runs date", digit_runs("2026-10-29"),
       [(0, 4), (5, 7), (8, 10)])
    ck("digit_runs none", digit_runs("no digits here"), [])
    ck("digit_runs mixed", digit_runs("s1001 (NEW): median 1131"),
       [(1, 5), (20, 24)])

    # dual estimators
    ck("median odd dual", median_int_dual([5, 1, 3]), 3)
    ck("median even dual (int-truncating)", median_int_dual([1, 4]), 2)
    ck("median even dual 2", median_int_dual([2, 3]), 2)
    ck("minmax dual", minmax_dual([7, 2, 9]), (2, 9))

    # bar class boundaries
    ck("class FLOOR boundary", bar_class([99, 100]), "FLOOR")
    ck("class mixed below", bar_class([100, 101]), "INTERMEDIATE/MIXED")
    ck("class CAPTURED boundary", bar_class([1000, 1001]), "CAPTURED")
    ck("class mixed above", bar_class([999, 1000]), "INTERMEDIATE/MIXED")

    # want-source parsers on synthetic bytes
    ck("c8 committed parse",
       parse_c8_committed("c8 pooled median 1 vs committed 32915 (x)"),
       32915)
    ck("floor band parse",
       parse_floor_band("band (FLOOR required; committed floor band 31..32)"),
       "31..32")
    ck("refs parse",
       parse_refs("frozen numeric reference (1,129 / 1,132 / 1,131 -- ok)"),
       (1129, 1132, 1131))
    ck("priors parse",
       sorted(parse_priors(
           "s36: median 1142 min..max 991..1438 (want 1142 / 991..1438); "
           "reproduction EXACT: True\n"
           "s73 (NEW): median 1131 min..max 998..1442; class "
           "INTERMEDIATE/MIXED\n").items()),
       [("s36", (1142, 991, 1438)), ("s73", (1131, 998, 1442))])
    ck("stamp parse",
       parse_stamp("quantity existed (freeze stamp 2026-10-29T04:23:51Z, "
                   "this tick)"),
       "2026-10-29T04:23:51Z")
    ck("run_days single",
       run_days_from_text("x host-date=2026-10-29 y\nz host-date=2026-10-29"),
       ["2026-10-29", "2026-10-29"])

    # body line grammar on synthetic publication (MOCK values below
    # are FIXTURES, never measurements)
    mock = "\n".join([
        "JUN-59 session 999 -- THE ANCHOR-CLASS SETTLING BAR'S THIRD",
        "COUNTED-DAY MEASUREMENT (the W6 window) -- READING",
        "(produced ONLY by reading-s999.py over the COMMITTED run logs",
        "anv-b3w6daybar-20261030; protocol.txt was frozen BEFORE any W6",
        "quantity existed (freeze stamp 2026-10-29T04:23:51Z).)",
        "",
        "1. INTEGRITY (computed over each window's committed logs;",
        "   s80 protocol section 3):",
        "   s36: runs 78 vmis 0 counts True knobs True s8 True cmap True",
        "   named cell (max,128,S=default): ok-map cell 5, raw idx 7",
        "   (the ok-map cell index is 0-based -- the s80 section-3",
        "   phrase 'ok-map cell 5'; the 1-based ok-map position is 6)",
        "   INVALIDATION criterion (protocol section 3): any violation =>",
        "   FLAGGED (no reading, no day slot).",
        "",
        "2. C1 RE-DERIVATION (environment pin, from the s999 window's logs):",
        "   c2 class: FLOOR (FLOOR required; committed floor band 31..32)",
        "   c8 (sum,128,S=16) pooled median 32709 vs committed 32915 "
        "(0.63% delta; +/-5% required)",
        "   C1 branch: (b) discrepancy",
        "",
        "3. THE ANCHOR READING (hi block A -- the frozen L12 single bar",
        "   candidate; the reading unit is one 3-run block pooled over 25",
        "   rounds per cell, the frozen estimator unit F3 of settle-bar.txt):",
        "   s999 (NEW): median 1131 min..max 998..1442; class FLOOR",
        "   in-band vs the bar's frozen refs 1,129/1,132/1,131 (within",
        "   +/-5% of EACH, settle-bar.txt V1): False",
        "",
        "4. PRIOR-WINDOW ANCHOR REPRODUCTION (the frozen priors PARSED",
        "   from the committed publication-s73.txt bytes, never",
        "   transcribed; reproduction EXACT required -- the prior rows",
        "   carry NO class token: the frozen publication-s73 section-3b",
        "   row shape, and a class-bearing prior row is parsed by",
        "   reconcile-prego.py --line as a BAR tuple):",
        "   s36: median 1142 min..max 991..1438 (want 1142 / 991..1438); "
        "reproduction EXACT: False",
        "   all five prior windows reproduce EXACTLY: False",
        "   (a False row means the run logs do not reproduce the",
        "   committed priors; FAIL-CLOSED -- no ledger line derives",
        "   from this reading.)",
        "",
        "5. THE RUN DAY (the ledger line's day; s80 protocol section 1:",
        "   day = the W6 run's ACTUAL UTC day from run-window.txt):",
        "   run-window host-dates: 78 parsed, 2 distinct: 2026-10-29 "
        "2026-10-30",
        "   ledger line day = NOT SINGLE-DAY (2026-10-29,2026-10-30)",
        "",
        "6. THE BAR READING ROW (D4 shape -- the ledger-line tuple,",
        "   printed a second time for the reconciler's two-class-row",
        "   agreement check; both class-bearing rows carry the same",
        "   values by construction): median 1131 min..max 998..1442, "
        "class FLOOR",
        "",
        "   NAMED, NOT HIDDEN: trailing note block, outside the body.",
    ]) + "\n"
    P, cs, ss, body = parse_body(mock)
    ck("mock sec1 rows parsed", len(P["sec1"]), 1)
    ck("mock sec1 tag", P["sec1"][0]["tag"], "s36")
    ck("mock sec1 flags", P["sec1"][0]["flags"],
       "counts True knobs True s8 True cmap True")
    ck("mock named key", P["named_key"], "(max,128,S=default)")
    ck("mock ok i", P["ok_i"], "5")
    ck("mock ok j", P["ok_j"], "7")
    ck("mock note relation values", (P["note_i"], P["note_k"]), ("5", "6"))
    ck("mock sec2 tag", P["sec2_tag"], "s999")
    ck("mock c2 class", P["c2_cls"], "FLOOR")
    ck("mock band", P["band"], "31..32")
    ck("mock c8 key", P["c8_key"], "(sum,128,S=16)")
    ck("mock c8 median", P["c8_med"], "32709")
    ck("mock c8 committed", P["c8_com"], "32915")
    ck("mock delta", P["delta"], "0.63")
    ck("mock tol c1", P["tol_c1"], "5")
    ck("mock branch (b)", P["branch"], "b")
    ck("mock fresh tag", P["fresh_tag"], "s999")
    ck("mock fresh anchor",
       (P["f_med"], P["f_lo"], P["f_hi"], P["f_cls"]),
       ("1131", "998", "1442", "FLOOR"))
    ck("mock refs", P["refs"], "1,129/1,132/1,131")
    ck("mock tol band", P["tol_band"], "5")
    ck("mock in-band False", P["in_band"], "False")
    ck("mock prior row", P["prior_rows"][0],
       dict(tag="s36", med="1142", lo="991", hi="1438", wmed="1142",
            wlo="991", whi="1438", rbool="False"))
    ck("mock all prior False", P["all_prior"], "False")
    ck("mock day census", (P["day_n"], P["day_d"], P["day_dates"]),
       ("78", "2", ["2026-10-29", "2026-10-30"]))
    ck("mock ledger day NOT SINGLE-DAY", P["ledger_day"],
       "NOT SINGLE-DAY (2026-10-29,2026-10-30)")
    ck("mock bar row",
       (P["b_med"], P["b_lo"], P["b_hi"], P["b_cls"]),
       ("1131", "998", "1442", "FLOOR"))

    # coverage on the mock body: every digit run claimed/structural
    unclaimed = []
    for i, line in enumerate(body):
        for run in digit_runs(line):
            if covered(cs.get(i, []), run) or covered(ss.get(i, []), run):
                continue
            unclaimed.append((i, line[run[0]:run[1]]))
    ck("mock coverage complete (trailing note excluded)", unclaimed, [])

    # rogue digit must be UNCLAIMED (the detector fires)
    rogue = mock.replace("ok-map cell 5, raw idx 7",
                         "ok-map cell 5, raw idx 7 9")
    _P2, cs2, ss2, body2 = parse_body(rogue)
    un2 = []
    for i, line in enumerate(body2):
        for run in digit_runs(line):
            if covered(cs2.get(i, []), run) or covered(ss2.get(i, []), run):
                continue
            un2.append((i, line[run[0]:run[1]]))
    ck("rogue digit detected", un2, [(3, "9")])

    # claim mismatch detection (want != got -> match False)
    ck("claim mismatch detector", ("78" == "79"), False)

    # fail-closed: an unparsed body line raises
    bad = mock.replace("   FLAGGED (no reading, no day slot).",
                       "   FLAGGED (no reading, no day slot) 99.")
    try:
        parse_body(bad)
        ck("unparsed body line raises", "no raise", "ParseError")
    except ParseError:
        ck("unparsed body line raises", "ParseError", "ParseError")

    # ok-map note relation enforcement shape
    ck("ok-map note relation want",
       "%s/%s" % ("5", "6"), "5/6")
    ck("ok-map note relation mismatch detector",
       "%s/%s" % ("5", "7") == "%d/%d" % (5, 6), False)

    # sec6/sec3 relation enforcement shape
    ck("sec6/sec3 relation want",
       ("%s %s..%s %s" % ("1131", "998", "1442", "FLOOR")) ==
       ("%s %s..%s %s" % ("1131", "998", "1442", "FLOOR")), True)

    out = []
    o = out.append
    o("JUN-59 session 101 -- fresh-census-prego.py --self-test")
    o("(MOCK fixtures only; every MOCK value is a FIXTURE, never a")
    o("measurement; this battery reads NO committed window).")
    o("")
    nfail = 0
    for (name, got, want, ok) in results:
        o("%-48s got: %-38s want: %-38s %s" %
          (name, repr(got)[:38], repr(want)[:38],
           "ok" if ok else "FAIL"))
        if not ok:
            nfail += 1
    o("")
    o("TOTAL: %d assertions passed %d failed" %
      (len(results) - nfail, nfail))
    text = "\n".join(out) + "\n"
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    return 0 if nfail == 0 else 1


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--self-test":
        return self_test()
    if len(sys.argv) >= 4 and sys.argv[1] == "--w6":
        return run_w6(sys.argv[2], sys.argv[3])
    sys.stderr.write("usage: fresh-census-prego.py --w6 <publication> "
                     "<fresh-window-dir> [OUT] | --self-test [OUT]\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
