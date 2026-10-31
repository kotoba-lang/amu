#!/usr/bin/env python3
"""Token-table headroom of the largest static builds (JUN-737).

The static profile's token table (MM-TOK-CAP in seed/00-ns-static.kotoba, set
by the seed/MEMORY-MAP static overrides) bounds every source the native
compiler lexes: FULL-MANIFEST plus a test harness overflowed it in amu#1754
(E101 region 1). This gate measures, with the native compiler itself, how many
more tokens each of the largest static builds in CI can take, and fails when
any is below the floor, so a change sees the budget before it overflows.

Measurement: the build's exact source plus N stray `0`/list tokens is compiled with
--format static. The lexer fills the token table before anything else runs,
so the compile either refuses `E101 ... region 1` (the table is full) or gets
past the lexer (and refuses the stray `0` forms later, which is irrelevant).
Bisection finds the largest N that still lexes: the headroom, exact to one
token, observed on both sides of the boundary.

Negative control: the build plus (headroom - floor + 1) real tokens, module-local
functions that are never called, must measure exactly floor - 1
and be refused by the same verdict.

Python stages sources and observes processes; every lex is the native
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
OVERFLOW = b"E101 compiler table full: region 1"
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


def token_cap():
    caps = re.findall(r"\(def MM-TOK-CAP (\d+)\)", (ROOT / "seed/00-ns-static.kotoba").read_text())
    assert len(caps) == 1
    return int(caps[0])


def padding(n):
    """Never-called module-local functions of exactly n >= 11 tokens in all (each about 100 tokens, `(do 1 1 .. 0)`)."""
    assert n >= 11
    sizes = [100] * (n // 100)
    if n % 100 >= 11 or not sizes:
        sizes.append(n % 100)
    else:
        sizes[-1] += n % 100
    return b"".join(b"\n(defn- zz-token-headroom-pad%d [] :i64 (do " % i + b"1 " * (k - 11) + b"0))" for i, k in enumerate(sizes)) + b"\n"


def filler(n):
    """Exactly n stray tokens as lists of at most 100: one top-level `0` per token would be ~n top-level forms,
    and tens of thousands of top-level forms (or list children) crash the reader's recursion on its 8 MiB stack."""
    chunks, rest = [b"(" + b"0 " * 98 + b")"] * (n // 100), n % 100
    if rest == 1:
        chunks.append(b"0")
    elif rest:
        chunks.append(b"(" + b"0 " * (rest - 2) + b")")
    return b"\n".join(chunks)


class Lexer:
    def __init__(self, compiler, out, target):
        self.compiler, self.out, self.target, self.calls = compiler, out, target, []
        self.macho = compiler.read_bytes()[:4] == b"\xcf\xfa\xed\xfe"
        self.env = dict(PATH="/nonexistent", KEXE_ALLOW="35,37,38,39", KEXE_CAP_RESOURCES_35=str(out),
                        KEXE_STACK_BYTES="8388608", KEXE_FUEL="10000000000")

    def overflows(self, name, source, extra):
        """True when source + extra stray tokens fill the token table (E101 region 1)."""
        src, img = self.out / "probe.kotoba", self.out / "probe.elf"
        src.write_bytes(source + b"\n" + filler(extra))
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
        full = OVERFLOW in text
        # Past the lexer the stray tokens are refused E2003; anything else (a crash, another table) is not a measurement.
        assert p.returncode == 1 and (full or b"E2003" in text), (name, extra, p.returncode, text[-300:])
        self.calls.append(dict(build=name, extraTokens=extra, exit=p.returncode, tokenTableFull=full))
        return full

    def headroom(self, name, source, hi):
        """Largest n such that source + n tokens still lexes; observed at n and n + 1."""
        lo = 1  # one stray token stops the compile right after reading instead of building an image
        assert not self.overflows(name, source, lo), (name, "already overflows the token table")
        while not self.overflows(name, source, hi):
            lo, hi = hi, hi * 2
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.overflows(name, source, mid):
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
    lexer = Lexer(compiler, out, target)
    cap = token_cap()
    report = dict(schema="amu.native-token-headroom.v1", status="running", compiler=pin(compiler),
                  observer=pin(Path(__file__)), target=target, tokenCapacity=cap, floor=floor, builds={},
                  calls=lexer.calls)
    save = lambda: (out / "token-headroom.json").write_text(json.dumps(report, indent=2) + "\n")
    for name, source in builds().items():
        n = lexer.headroom(name, source, 16384)
        report["builds"][name] = dict(source=dict(bytes=len(source), sha256=hashlib.sha256(source).hexdigest()),
                                      headroomTokens=n, verdict=verdict(n, floor))
        print(f"{name} {target}: {n} tokens of headroom (floor {floor})", flush=True)
        save()
    # Negative control: the largest build grown by real code to one token under the floor.
    name = min(report["builds"], key=lambda b: report["builds"][b]["headroomTokens"])
    measured = report["builds"][name]["headroomTokens"]
    if measured >= floor:
        grown = builds()[name] + padding(measured - floor + 1)
        n = lexer.headroom(name + "+pad", grown, 1024)
        assert n == floor - 1, ("padding control measured", n, "expected", floor - 1)
        assert verdict(n, floor) == "BELOW_FLOOR"
        report["negativeControl"] = dict(build=name, addedTokens=measured - floor + 1, headroomTokens=n,
                                         verdict="BELOW_FLOOR", refused=True)
    else:
        report["negativeControl"] = dict(build=name, skipped="the build itself is below the floor")
    low = {b: r["headroomTokens"] for b, r in report["builds"].items() if r["verdict"] != "PASS"}
    report["status"] = "PASS_NATIVE_TOKEN_HEADROOM" if not low else "FAIL_TOKEN_HEADROOM_BELOW_FLOOR"
    save()
    print(report["status"], json.dumps(low) if low else "")
    if low:
        raise SystemExit(f"token headroom below {floor}: {low}; raise the static MM-TOK-CAP (seed/MEMORY-MAP) "
                         "or shrink the build")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--floor", type=int, default=FLOOR)
    p.add_argument("--mac-target", choices=["aarch64-linux", "x86_64-linux"],
                   help="local Mach-O compiler only: the static target to measure (an ELF compiler uses its own ISA)")
    a = p.parse_args()
    main(a.compiler.resolve(), a.output.resolve(), a.floor, a.mac_target)
