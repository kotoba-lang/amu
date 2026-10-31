#!/usr/bin/env python3
"""Token- and node-table headroom of the largest static builds (JUN-737).

The static profile's token table (MM-TOK-CAP) and read-node table (MM-NODE-CAP)
in seed/00-ns-static.kotoba, set by the seed/MEMORY-MAP static overrides, bound
every source the native compiler reads: FULL-MANIFEST plus a test harness
overflowed the token table in amu#1754 (E101 region 1). This gate measures,
with the native compiler itself, how many more tokens and read nodes each of
the largest static builds in CI can take, and fails when any is below the
floor, so a change sees the budget before it overflows.

Measurement: the build's exact source plus N stray tokens (or nodes) is
compiled with --format static. The lexer fills TOK and the reader NODE before
anything else runs, so the compile either refuses `E101 ... region 1` (TOK) /
`region 4` (NODE) or gets past reading and refuses the stray forms E2003.
Bisection finds the largest N that still fits: the headroom, exact to one
entry, observed on both sides of the boundary. NODE is read-time use only:
later phases (checker expansions) also take nodes, so treat it as an upper
bound.

Negative controls, one per table: the tightest build plus real code
(never-called module-local functions) that leaves exactly floor - 1 entries
must measure floor - 1 and be refused by the same verdict.

Python stages sources and observes processes; every lex and read is the native
compiler's. The checked builds are the kir-execution compiler
(check-checked-source-native.py / check-source-vectors-native.py), the whole
definition-graph producer (check-definition-graph-native.py) and the
FULL-MANIFEST unity.
"""
import argparse
import hashlib
import json
import platform
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FLOOR = 65536
FULL = b"E101 compiler table full: region "
ENTRY = "seed/78-full-entry.kotoba"
MAIN = b"(defn- seed-main [] :i64"


def pin(path):
    data = Path(path).read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def full_paths():
    return [p for p in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines() if p and not p.startswith("#")]


def renamed_entry(data, name):
    assert data.count(MAIN) == 1
    return data.replace(MAIN, b"(defn- " + name + b" [] :i64")


def builds():
    """The largest static sources CI compiles, composed as their gates compose them."""
    paths = full_paths()
    kir = [renamed_entry((ROOT / p).read_bytes(), b"dsx-original-main") if p == ENTRY else (ROOT / p).read_bytes()
           for p in paths]
    kernel = "seed/05-definition-graph.kotoba"
    graph = [renamed_entry((ROOT / p).read_bytes(), b"dgg-original-main") if p == ENTRY else (ROOT / p).read_bytes()
             for p in paths if p != kernel]
    whole_entry = b"\n(defn- seed-main [] :i64 (if (= (io-argc) 1) (dgsr-run (drv-read (io-arg 0))) 2))\n"
    return {
        "kir-execution-compiler": b"\n".join(kir) + b"\n" + (ROOT / "seed/tests/native-source-loop-execution.kotoba").read_bytes(),
        "definition-graph-whole-producer": b"\n".join(graph) + b"\n" + (ROOT / kernel).read_bytes() + b"\n"
        + (ROOT / "seed/tests/native-definition-graph-sir.kotoba").read_bytes() + whole_entry,
        "full-manifest-unity": b"".join((ROOT / p).read_bytes() + b"\n" for p in paths),
    }


# Region number of E101, the MM-*-CAP it fills, and the fixed tokens/nodes of one padding function.
TABLES = {"TOK": (1, "MM-TOK-CAP"), "NODE": (4, "MM-NODE-CAP")}


def capacity(name):
    caps = re.findall(r"\(def %s (\d+)\)" % name, (ROOT / "seed/00-ns-static.kotoba").read_text())
    assert len(caps) == 1
    return int(caps[0])


def padding(n, table):
    """Never-called module-local functions of exactly n tokens (TOK) or read nodes (NODE) in all, about 100 each.

    `(defn- zzN [] :i64 (do 1 .. 0))` with k ones is 11 + k tokens and 8 + k nodes (closing brackets are tokens only)."""
    fixed = 11 if table == "TOK" else 8
    assert n >= fixed
    sizes = [100] * (n // 100)
    if n % 100 >= fixed or not sizes:
        sizes.append(n % 100)
    else:
        sizes[-1] += n % 100
    return b"".join(b"\n(defn- zz-table-headroom-pad%d [] :i64 (do " % i + b"1 " * (k - fixed) + b"0))"
                    for i, k in enumerate(sizes)) + b"\n"


def filler(n, table):
    """Exactly n stray tokens (TOK) or read nodes (NODE), as lists of 100 tokens / 99 nodes: one top-level `0` each
    would be ~n top-level forms, and tens of thousands of top-level forms (or list children) crash the reader's
    recursion on its 8 MiB stack."""
    per = 98  # zeros per list: 100 tokens, 99 nodes
    unit = 100 if table == "TOK" else 99
    chunks, rest = [b"(" + b"0 " * per + b")"] * (n // unit), n % unit
    if rest == 1:
        chunks.append(b"0")
    elif rest:
        chunks.append(b"(" + b"0 " * (rest - (2 if table == "TOK" else 1)) + b")")
    return b"\n".join(chunks)


class Probe:
    def __init__(self, compiler, out, target):
        self.compiler, self.out, self.target, self.calls = compiler, out, target, []
        self.macho = compiler.read_bytes()[:4] == b"\xcf\xfa\xed\xfe"
        self.env = dict(PATH="/nonexistent", KEXE_ALLOW="35,37,38,39", KEXE_CAP_RESOURCES_35=str(out),
                        KEXE_STACK_BYTES="8388608", KEXE_FUEL="10000000000")

    def full(self, name, source, extra, table):
        """True when source + extra stray tokens/nodes fill the table (E101 of its region) while reading."""
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
        text = p.stdout + p.stderr
        filled = [r for r in (1, 4) if FULL + b"%d\n" % r in text + b"\n"]
        # The lexer fills TOK, the reader NODE, then the stray forms are refused E2003 (20-names). Any other outcome
        # (a crash, another table) is not a measurement. A NODE probe also stops when TOK fills first: its headroom
        # is then the room left before either read table is full (`limitedBy` says which).
        assert p.returncode == 1 and (filled or b"E2003" in text), (name, table, extra, p.returncode, text[-300:])
        hit = 1 in filled if table == "TOK" else bool(filled)
        self.calls.append(dict(build=name, table=table, extra=extra, exit=p.returncode, filledRegions=filled))
        if hit:
            self.last_region = filled[0]
        return hit

    def headroom(self, name, source, table, hi):
        """Largest n such that source + n stray tokens/nodes still fit; observed at n and n + 1."""
        lo = 1  # one stray token stops the compile right after reading instead of building an image
        assert not self.full(name, source, lo, table), (name, table, "already full")
        while not self.full(name, source, hi, table):
            lo, hi = hi, hi * 2
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.full(name, source, mid, table):
                hi = mid
            else:
                lo = mid
        return lo


def verdict(headroom, floor):
    return "PASS" if headroom >= floor else "BELOW_FLOOR"


def main(compiler, out, floor, mac_target=None):
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    data = compiler.read_bytes()
    if data[:4] == b"\x7fELF":
        target = {183: "aarch64-linux", 62: "x86_64-linux"}[int.from_bytes(data[18:20], "little")]
    else:
        assert data[:4] == b"\xcf\xfa\xed\xfe" and platform.system() == "Darwin", "an ELF or a local Mach-O compiler"
        target = mac_target or "aarch64-linux"
    probe = Probe(compiler, out, target)
    report = dict(schema="amu.native-table-headroom.v1", status="running", compiler=pin(compiler),
                  observer=pin(Path(__file__)), target=target, floor=floor,
                  capacities={t: capacity(c) for t, (_, c) in TABLES.items()}, builds={}, negativeControls={},
                  calls=probe.calls)
    save = lambda: (out / "token-headroom.json").write_text(json.dumps(report, indent=2) + "\n")
    sources = builds()
    for name, source in sources.items():
        row = report["builds"][name] = dict(source=dict(bytes=len(source), sha256=hashlib.sha256(source).hexdigest()))
        for table in TABLES:
            n = probe.headroom(name, source, table, 16384)
            row[table] = dict(headroom=n, limitedBy={1: "TOK", 4: "NODE"}[probe.last_region], verdict=verdict(n, floor))
            print(f"{name} {target}: {table} headroom {n} (full next: {row[table]['limitedBy']}; floor {floor})",
                  flush=True)
            save()
    # Negative controls: the tightest build grown by real code to one entry under the floor of each table.
    for table in TABLES:
        name = min(report["builds"], key=lambda b: report["builds"][b][table]["headroom"])
        measured = report["builds"][name][table]["headroom"]
        if measured < floor:
            report["negativeControls"][table] = dict(build=name, skipped="the build itself is below the floor")
            continue
        added = measured - floor + 1
        n = probe.headroom(name + "+pad", sources[name] + padding(added, table), table, 1024)
        # Padding adds both tokens and nodes; the count is exact for the table that bounds this measurement.
        if report["builds"][name][table]["limitedBy"] == table:
            assert n == floor - 1, ("padding control", table, n, "expected", floor - 1)
        assert verdict(n, floor) == "BELOW_FLOOR", ("padding control", table, n)
        assert verdict(n, floor) == "BELOW_FLOOR"
        report["negativeControls"][table] = dict(build=name, added=added, headroom=n, verdict="BELOW_FLOOR",
                                                 refused=True)
        save()
    low = {f"{b}/{t}": r[t]["headroom"] for b, r in report["builds"].items() for t in TABLES
           if r[t]["verdict"] != "PASS"}
    report["status"] = "PASS_NATIVE_TABLE_HEADROOM" if not low else "FAIL_TABLE_HEADROOM_BELOW_FLOOR"
    save()
    print(report["status"], json.dumps(low) if low else "")
    if low:
        raise SystemExit(f"table headroom below {floor}: {low}; raise the static MM-TOK-CAP / MM-NODE-CAP "
                         "(seed/MEMORY-MAP) or shrink the build")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--floor", type=int, default=FLOOR)
    p.add_argument("--mac-target", choices=["aarch64-linux", "x86_64-linux"],
                   help="local Mach-O compiler only: the static target to measure (an ELF compiler uses its own ISA)")
    a = p.parse_args()
    main(a.compiler.resolve(), a.output.resolve(), a.floor, a.mac_target)
