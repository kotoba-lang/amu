#!/usr/bin/env python3
"""Compiler table headroom of the largest static builds (JUN-737).

The static profile's tables (seed/00-ns-static.kotoba, set by the
seed/MEMORY-MAP static overrides) bound every source the native compiler
reads: FULL-MANIFEST plus a test harness overflowed the token table in
amu#1754 (E101 region 1). This gate measures, with the native compiler itself,
how many more entries the largest static builds in CI can take in the three
tables that fill while a source is read and its names registered, and fails
when any is below its floor, so a change sees the budget before it overflows:

  TOK  (MM-TOK-CAP, E101 region 1)  tokens, filled by the lexer;
  NODE (MM-NODE-CAP, region 4)      read nodes, filled by the reader;
  FN   (MM-FN-CAP, region 6)        functions, registered by 20-names.

Measurement: the build's exact source plus N stray entries (tokens or nodes as
lists of `0`, or trivial `defn-`s followed by a stray `0`) is compiled with
--format static. The compile either refuses E101 for the table, or gets past
it and refuses the stray `0` E2003 (20-names). Bisection finds the largest N
that still fits: the headroom, exact to one entry, observed on both sides of
the boundary. NODE and FN count read/registration use only; later phases
(checker expansions) take more, so treat them as upper bounds. A NODE probe
also stops when TOK fills first (`limitedBy`).

Negative controls, one per table: the tightest build plus real code
(never-called module-local functions) that leaves exactly floor - 1 entries:
floor - 1 more must still fit, floor more must fill the table, and the verdict
refuses floor - 1.

Python stages sources and observes processes; every lex, read and name pass is
the native compiler's. The checked builds are the kir-execution compiler
(check-checked-source-native.py / check-source-vectors-native.py) and the whole
definition-graph producer (check-definition-graph-native.py); the FULL-MANIFEST
unity is a strict subset of both. The first build is searched from scratch;
the second in a window centred by an estimated size difference, since every
probe lexes and reads ~4 MB (seconds on a CI runner).
"""
import argparse
import hashlib
import json
import platform
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FULL = b"E101 compiler table full: region "
ENTRY = "seed/78-full-entry.kotoba"
MAIN = b"(defn- seed-main [] :i64"
# table -> (E101 region, capacity constant, default floor)
TABLES = {"TOK": (1, "MM-TOK-CAP", 65536), "NODE": (4, "MM-NODE-CAP", 65536), "FN": (6, "MM-FN-CAP", 256)}
REGIONS = {1: "TOK", 4: "NODE", 6: "FN"}
LEX = re.compile(rb';[^\n]*|"(?:\\.|[^"\\])*"|#\{|[()\[\]{}]|[^\s()\[\]{}",;]+')


def pin(path):
    data = Path(path).read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def renamed_entry(data, name):
    assert data.count(MAIN) == 1
    return data.replace(MAIN, b"(defn- " + name + b" [] :i64")


def builds():
    """The largest static sources CI compiles, composed as their gates compose them."""
    paths = [p for p in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines() if p and not p.startswith("#")]
    kir = [renamed_entry((ROOT / p).read_bytes(), b"dsx-original-main") if p == ENTRY else (ROOT / p).read_bytes()
           for p in paths]
    kernel = "seed/05-definition-graph.kotoba"
    graph = [renamed_entry((ROOT / p).read_bytes(), b"dgg-original-main") if p == ENTRY else (ROOT / p).read_bytes()
             for p in paths if p != kernel]
    whole_entry = b"\n(defn- seed-main [] :i64 (if (= (io-argc) 1) (dgsr-run (drv-read (io-arg 0))) 2))\n"
    return {
        "kir-execution-compiler": b"\n".join(kir) + b"\n"
        + (ROOT / "seed/tests/native-source-loop-execution.kotoba").read_bytes(),
        "definition-graph-whole-producer": b"\n".join(graph) + b"\n" + (ROOT / kernel).read_bytes() + b"\n"
        + (ROOT / "seed/tests/native-definition-graph-sir.kotoba").read_bytes() + whole_entry,
    }


def capacity(name):
    caps = re.findall(r"\(def %s (\d+)\)" % name, (ROOT / "seed/00-ns-static.kotoba").read_text())
    assert len(caps) == 1
    return int(caps[0])


def estimate(source, table):
    """Approximate count, only to centre a search window (the native compiler decides)."""
    items = [m for m in LEX.findall(source) if not m.startswith(b";")]
    if table == "TOK":
        return len(items)
    if table == "NODE":
        return sum(1 for m in items if m not in (b")", b"]", b"}"))
    return sum(1 for a, b in zip(items, items[1:]) if a == b"(" and b in (b"defn", b"defn-"))


def filler(n, table):
    """Exactly n stray tokens / read nodes as lists of 100 tokens (99 nodes), or n trivial functions and a stray `0`.

    One top-level `0` per entry would be ~n top-level forms, and tens of thousands of top-level forms (or list
    children) crash the reader's recursion on its 8 MiB stack."""
    if table == "FN":
        return b"".join(b"(defn- zz-fn-headroom%d [] :i64 0)\n" % i for i in range(n)) + b"0\n"
    unit = 100 if table == "TOK" else 99
    chunks, rest = [b"(" + b"0 " * 98 + b")"] * (n // unit), n % unit
    if rest == 1:
        chunks.append(b"0")
    elif rest:
        chunks.append(b"(" + b"0 " * (rest - (2 if table == "TOK" else 1)) + b")")
    return b"\n".join(chunks)


def padding(n, table):
    """Never-called module-local functions adding exactly n tokens / read nodes / functions.

    `(defn- zzN [] :i64 (do 1 .. 0))` with k ones is 11 + k tokens and 8 + k nodes; TOK/NODE padding uses about
    1000 per function so that it does not exhaust the much smaller FN table first."""
    if table == "FN":
        return b"".join(b"\n(defn- zz-table-headroom-fn%d [] :i64 0)" % i for i in range(n)) + b"\n"
    fixed = 11 if table == "TOK" else 8
    assert n >= fixed
    sizes = [1000] * (n // 1000)
    if n % 1000 >= fixed or not sizes:
        sizes.append(n % 1000)
    else:
        sizes[-1] += n % 1000
    return b"".join(b"\n(defn- zz-table-headroom-pad%d [] :i64 (do " % i + b"1 " * (k - fixed) + b"0))"
                    for i, k in enumerate(sizes)) + b"\n"


class Probe:
    def __init__(self, compiler, out, target):
        self.compiler, self.out, self.target, self.calls, self.last = compiler, out, target, [], None
        self.macho = compiler.read_bytes()[:4] == b"\xcf\xfa\xed\xfe"
        self.env = dict(PATH="/nonexistent", KEXE_ALLOW="35,37,38,39", KEXE_CAP_RESOURCES_35=str(out),
                        KEXE_STACK_BYTES="8388608", KEXE_FUEL="10000000000")

    def full(self, name, source, extra, table):
        """True when source + extra stray entries fill the table (E101 of its region; NODE: also TOK first)."""
        src, img = self.out / "probe.kotoba", self.out / "probe.elf"
        src.write_bytes(source + b"\n" + filler(extra, table))
        if self.macho:  # local Apple Silicon run: the Mach-O compiler reads through FD3
            argv = ["/bin/sh", "-c", '"$0" compile probe.kotoba --target "$1" --output probe.elf --format static 3<.',
                    str(self.compiler), self.target]
            p = subprocess.run(argv, cwd=self.out, capture_output=True, timeout=600)
        else:
            argv = [str(self.compiler), "compile", str(src), "--target", self.target, "--output", str(img),
                    "--format", "static"]
            p = subprocess.run(argv, cwd=self.out, env=self.env, capture_output=True, timeout=600)
        img.unlink(missing_ok=True)
        text = p.stdout + p.stderr + b"\n"
        filled = [r for r in range(1, 10) if FULL + b"%d\n" % r in text]
        region = TABLES[table][0]
        hit = region in filled or (table == "NODE" and 1 in filled)
        # Anything else (a crash, an unrelated table, no stray-form refusal) is not a measurement of this table.
        valid = hit or (not filled and b"E2003" in text) or (table == "TOK" and filled == [4])
        assert p.returncode == 1 and valid, (name, table, extra, p.returncode, text[-300:])
        self.calls.append(dict(build=name, table=table, extra=extra, exit=p.returncode, filledRegions=filled))
        if hit:
            self.last = filled[0]
        return hit

    def headroom(self, name, source, table, guess=None):
        """Largest n such that source + n stray entries still fit; observed at n and n + 1."""
        step = 256 if table != "FN" else 16
        # The least probe still needs a stray form, so the compile stops after reading instead of building an image:
        # FN filler always ends in a stray `0`; TOK/NODE need one stray entry.
        least = 0 if table == "FN" else 1
        if guess is None:
            lo, hi = least, 64 * step
            assert not self.full(name, source, lo, table), (name, table, "already full")
            while not self.full(name, source, hi, table):
                lo, hi = hi, hi * 2
        else:
            lo, hi, width = max(least, guess - step), None, step
            while lo > least and self.full(name, source, lo, table):
                hi, lo, width = lo, max(least, lo - width), width * 2
            assert lo > least or not self.full(name, source, lo, table), (name, table, "already full")
            if hi is None:
                hi, width = guess + step, step
                while not self.full(name, source, hi, table):
                    lo, hi, width = hi, hi + width, width * 2
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.full(name, source, mid, table):
                hi = mid
            else:
                lo = mid
        return lo


def verdict(headroom, floor):
    return "PASS" if headroom >= floor else "BELOW_FLOOR"


def main(compiler, out, floors, mac_target=None):
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    data = compiler.read_bytes()
    if data[:4] == b"\x7fELF":
        target = {183: "aarch64-linux", 62: "x86_64-linux"}[int.from_bytes(data[18:20], "little")]
    else:
        assert data[:4] == b"\xcf\xfa\xed\xfe" and platform.system() == "Darwin", "an ELF or a local Mach-O compiler"
        target = mac_target or "aarch64-linux"
    probe = Probe(compiler, out, target)
    report = dict(schema="amu.native-table-headroom.v1", status="running", compiler=pin(compiler),
                  observer=pin(Path(__file__)), target=target, floors=floors,
                  capacities={t: capacity(c) for t, (_, c, _) in TABLES.items()}, builds={}, negativeControls={},
                  calls=probe.calls)
    save = lambda: (out / "token-headroom.json").write_text(json.dumps(report, indent=2) + "\n")
    sources = builds()
    first = {}
    for name, source in sources.items():
        row = report["builds"][name] = dict(source=dict(bytes=len(source), sha256=hashlib.sha256(source).hexdigest()))
        for table in TABLES:
            guess = None
            if table in first:  # centre the window by the estimated size difference to the measured build
                base, measured = first[table]
                guess = max(0, measured + estimate(sources[base], table) - estimate(source, table))
            n = probe.headroom(name, source, table, guess)
            first.setdefault(table, (name, n))
            limited = REGIONS[probe.last]
            row[table] = dict(headroom=n, limitedBy=limited, verdict=verdict(n, floors[table]))
            print(f"{name} {target}: {table} headroom {n} (full next: {limited}; floor {floors[table]})", flush=True)
            save()
    for table in TABLES:
        floor = floors[table]
        name = min(report["builds"], key=lambda b: report["builds"][b][table]["headroom"])
        measured = report["builds"][name][table]["headroom"]
        if measured < floor or report["builds"][name][table]["limitedBy"] != table:
            report["negativeControls"][table] = dict(build=name, skipped="below the floor, or bounded by another table")
            continue
        added = measured - floor + 1
        grown = sources[name] + padding(added, table)
        # Exactly floor - 1 left: floor - 1 more still fits, floor more fills the table.
        fits = not probe.full(name + "+pad", grown, floor - 1, table)
        fills = probe.full(name + "+pad", grown, floor, table)
        assert fits and fills, ("padding control", table, fits, fills)
        assert verdict(floor - 1, floor) == "BELOW_FLOOR"
        report["negativeControls"][table] = dict(build=name, added=added, headroom=floor - 1, verdict="BELOW_FLOOR",
                                                 refused=True)
        print(f"negative control {table}: {name} + {added} -> {floor - 1} left, refused", flush=True)
        save()
    low = {f"{b}/{t}": r[t]["headroom"] for b, r in report["builds"].items() for t in TABLES
           if r[t]["verdict"] != "PASS"}
    report["status"] = "PASS_NATIVE_TABLE_HEADROOM" if not low else "FAIL_TABLE_HEADROOM_BELOW_FLOOR"
    save()
    print(report["status"], json.dumps(low) if low else "")
    if low:
        raise SystemExit(f"compiler table headroom below its floor: {low}; raise the static capacity "
                         "(seed/MEMORY-MAP overrides) or shrink the build")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--floor", action="append", default=[], metavar="TABLE=N",
                   help="override a floor (defaults: " + ", ".join(f"{t}={f}" for t, (_, _, f) in TABLES.items()) + ")")
    p.add_argument("--mac-target", choices=["aarch64-linux", "x86_64-linux"],
                   help="local Mach-O compiler only: the static target to measure (an ELF compiler uses its own ISA)")
    a = p.parse_args()
    floors = {t: f for t, (_, _, f) in TABLES.items()}
    for item in a.floor:
        table, value = item.split("=")
        assert table in floors
        floors[table] = int(value)
    main(a.compiler.resolve(), a.output.resolve(), floors, a.mac_target)
