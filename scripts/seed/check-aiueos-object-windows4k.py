#!/usr/bin/env python3
"""The aiueos kernel object route's 4 KiB window tier (JUN-708, ADR 0401).

kernel-<load|store>-<u8|u16|u32|u64>-4k are ids 35..42 of seed/74-x86_64-aiueos-object.kotoba: kotoba-native machine-ir's
[:gmir/kernel-<op>-<w> 4096] memwidth windows, which kotoba-compiler/1 emitted into the AIUEOS crypto and rtl8125
objects. Compiles with a native Amu compiler and decodes every inlined window with a decoder written here (Python stages
and observes; it emits nothing):

  cmp rcx,4096; ja T; test rdx,rdx; jz T; cmp INDEX,rcx; jae T;
  [width > 1: mov rsi,rcx; sub rsi,INDEX; cmp rsi,WIDTH; jl T; test INDEX,WIDTH-1; ja T;]
  ACCESS; jmp +2; T: ud2

with every branch landing on that ud2 (the u32 forms are aligned, as the reference's are; only the 512-byte u32 pair is
exempt there).

* eight-4k: one object with the eight 4 KiB accesses, in order, each with bound 4096, and no 512-byte or 16 KiB window;
* mixed: a 512-byte, a 4 KiB and a 16 KiB u8 load in one object keep their own bounds (the ids stay positional);
* opt-in: objects that name no 4 KiB stub are byte-identical to main's root: the 512-byte width object (also with the
  new names in a comment only: the blocks are detected in call position), the 16 KiB width object and the out-port object
  of check-aiueos-object-outport.py (which carries every earlier block, ids 0..34);
* tier maximum: over the object's own .bss / .high_bss array, a literal length of exactly 4096 compiles; 8192 is refused
  (E7108 naming the intrinsic, the size and the maximum 4096; nothing written), loads and stores, u8 to u64;
* refused, nothing written: an unrooted base and a computed (or free literal) length (E7106); each form with one argument
  too few and one too many (E2103).

A length tied to a parameter keeps the run-time check (length > 4096 reaches ud2): not shown here, see
docs/evidence/windows4k-fence-20261031/, which runs the eight accesses under QEMU against the reference model.
"""

import argparse
import hashlib
import importlib.util
import json
import struct
from pathlib import Path

HERE = Path(__file__).parent
FORMS = [("load", 1, "u8"), ("store", 1, "u8"), ("load", 2, "u16"), ("store", 2, "u16"),
         ("load", 4, "u32"), ("store", 4, "u32"), ("load", 8, "u64"), ("store", 8, "u64")]
SOURCE = "(ns w4k (:export [ld8 st8 ld16 st16 ld32 st32 ld64 st64]))\n" + "".join(
    f"(defn {'ld' if kind == 'load' else 'st'}{name[1:]} [b :i64 n :i64 i :i64{' v :i64' if kind == 'store' else ''}] :i64 "
    f"(kernel-{kind}-{name}-4k b n i{' v' if kind == 'store' else ''}))\n" for kind, _, name in FORMS)
MIXED = """(ns mixed (:export [f g h]))
(defn f [b :i64 n :i64 i :i64] :i64 (kernel-load-u8 b n i))
(defn g [b :i64 n :i64 i :i64] :i64 (kernel-load-u8-4k b n i))
(defn h [b :i64 n :i64 i :i64] :i64 (kernel-load-u8-16k b n i))
"""
# a source that names the new forms only in prose (as kotoba's acpi-checksum-ok does) is not opted in
MENTION = ";; widths: `kernel-load-u8` (512), `kernel-load-u8-4k` (4096); a fence would be `kernel-fence-store`\n"
ACCESS = {("load", 1): "0fb60402", ("load", 2): "0fb70402", ("load", 4): "8b0402", ("load", 8): "488b0402",
          ("store", 1): "88043a", ("store", 2): "6689043a", ("store", 4): "89043a", ("store", 8): "4889043a"}
# SOURCE16 of check-aiueos-object-windows16.py compiled by main's root (amu 2d5ff706)
WIDTHS16_SHA256 = "63c0486c9378502b71c33ea108949743e9557d5d467509e3949b60e825dcce6c"
# SOURCE compiled by this change's root: the fence block (ids 43..45) must leave it as it is
W4K_SHA256 = "1813e4fe08f8a99a5f06dd91748da6a16e146c6739ffd4477f1a64d2a39aa36f"


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def one(form, params="b :i64 n :i64 i :i64 v :i64"):
    return f"(ns r (:export [f]))\n(defn f [{params}] :i64 {form})\n"


def refusals():
    cases = {
        "unrooted-base": (one("(kernel-load-u8-4k (+ b 1) n i)"), "E7106"),
        "computed-length": (one("(kernel-load-u32-4k b (+ n 4) i)"), "E7106"),
        "halved-length": (one("(kernel-store-u16-4k b (quot n 2) i v)"), "E7106"),
        "free-literal-length": (one("(kernel-store-u64-4k b 16 i v)"), "E7106"),
        "memory-base": (one("(kernel-load-u8-4k (kernel-load-u64-4k b n 0) n i)"), "E7106"),
    }
    for kind, _, name in FORMS:
        args = ["b", "n", "i"] + (["v"] if kind == "store" else [])
        cases[f"{kind}-{name}-few"] = (one(f"(kernel-{kind}-{name}-4k {' '.join(args[:-1])})"), "E2103")
        cases[f"{kind}-{name}-many"] = (one(f"(kernel-{kind}-{name}-4k {' '.join(args)} 0)"), "E2103")
    return cases


def head(bound):
    return bytes.fromhex("4881f9") + struct.pack("<I", bound)


def decode_window(text, at, bound):
    """Decode one window access starting at its `cmp rcx,BOUND`; return (kind, width)."""
    pos = at
    jumps = []

    def take(want):
        nonlocal pos
        want = bytes.fromhex(want)
        if text[pos:pos + len(want)] != want:
            raise ValueError(f"at {pos:#x}: want {want.hex()}, have {text[pos:pos + len(want)].hex()}")
        pos += len(want)

    def jcc(opcode):
        nonlocal pos
        take(opcode)
        rel, = struct.unpack_from("<i", text, pos)
        pos += 4
        jumps.append(pos + rel)

    take(head(bound).hex())
    jcc("0f87")
    take("4885d2")
    jcc("0f84")
    store = text[pos:pos + 3] == bytes.fromhex("4839cf")
    take("4839cf" if store else "4839c8")
    jcc("0f83")
    width = 1
    if text[pos:pos + 3] == bytes.fromhex("4889ce"):
        take("4889ce")
        take("4829fe" if store else "4829c6")
        take("4881fe")
        width, = struct.unpack_from("<i", text, pos)
        pos += 4
        jcc("0f8c")
        take("48f7c7" if store else "48f7c0")
        mask, = struct.unpack_from("<i", text, pos)
        pos += 4
        if mask != width - 1 or width not in (2, 4, 8):
            raise ValueError(f"width {width} mask {mask}")
        jcc("0f87")
    kind = "store" if store else "load"
    take(ACCESS[(kind, width)])
    take("eb02")
    trap = pos
    take("0f0b")
    if any(target != trap for target in jumps):
        raise ValueError(f"a branch misses the ud2 at {trap:#x}: {[hex(j) for j in jumps]}")
    return kind, width


def windows(text, bound):
    found, i = [], text.find(head(bound))
    while i >= 0:
        found.append((i, decode_window(text, i, bound)))
        i = text.find(head(bound), i + 1)
    return found


def main(compiler, output):
    windows16 = load("check-aiueos-object-windows16")
    outport = load("check-aiueos-object-outport")
    gate = windows16.gate_module()
    gate.verify_macho(compiler)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {}

    _, obj = windows16.compile_source(gate, compiler, output, "w4k", SOURCE)
    text = windows16.text_section(obj)
    found = [w for _, w in windows(text, 4096)]
    want = [(kind, width) for kind, width, _ in FORMS]
    if found != want or windows16.windows(text, 512) or windows16.windows(text, 16384):
        raise ValueError(f"4 KiB windows {found}; want {want} and no 512-byte or 16 KiB window")
    digest = hashlib.sha256(obj.read_bytes()).hexdigest()
    if digest != W4K_SHA256:
        raise ValueError(f"the 4 KiB width object is not the pinned one: {digest}")
    report["eight4k"] = {"windows": len(found), "sha256": digest}

    _, obj = windows16.compile_source(gate, compiler, output, "mixed", MIXED)
    text = windows16.text_section(obj)
    small, mid, large = windows16.windows(text, 512), windows(text, 4096), windows16.windows(text, 16384)
    if [w for _, w in small] != [("load", 1)] or [w for _, w in mid] != [("load", 1)] \
            or [w for _, w in large] != [("load", 1)] or not small[0][0] < mid[0][0] < large[0][0]:
        raise ValueError(f"mixed: 512-byte {small}, 4 KiB {mid}, 16 KiB {large}")
    report["mixed"] = "f keeps 512, g has 4096, h has 16384"

    for name, source, digest in (("widths", windows16.WIDTHS_SOURCE, windows16.WIDTHS_SHA256),
                                 ("mention", MENTION + windows16.WIDTHS_SOURCE, windows16.WIDTHS_SHA256),
                                 ("widths16", windows16.SOURCE16, WIDTHS16_SHA256),
                                 ("outport", outport.SOURCE, outport.SOURCE_SHA256)):
        _, obj = windows16.compile_source(gate, compiler, output, name, source)
        have = hashlib.sha256(obj.read_bytes()).hexdigest()
        if have != digest or windows(windows16.text_section(obj), 4096):
            raise ValueError(f"{name}: an object naming no 4 KiB stub changed ({have}) or carries a 4 KiB window")
        report[f"{name}Unchanged"] = have

    tiers = {}
    for kind, _, name in FORMS:
        intrinsic = f"kernel-{kind}-{name}-4k"
        for size, array in ((4096, "bss"), (8192, "highbss")):
            base = f"({array}-addr-0-{size})"
            call = f"({intrinsic} {base} {size} i v)" if kind == "store" else f"({intrinsic} {base} {size} i)"
            src = f"(ns t (:export [f]))\n(defn- {array}-addr-0-{size} [] :i64 0)\n(defn f [i :i64 v :i64] :i64 {call})\n"
            expected = 0 if size == 4096 else 1
            result, obj = windows16.compile_source(gate, compiler, output, f"{kind}-{name}-{size}", src, expected=expected)
            message = (result.stdout + result.stderr).decode(errors="replace")
            if size == 4096:
                if [w for _, w in windows(windows16.text_section(obj), 4096)] != [(kind, dict((n, w) for _, w, n in FORMS)[name])]:
                    raise ValueError(f"{intrinsic} at 4096: no single 4 KiB window")
            else:
                need = f"E7108 {intrinsic} size 8192 is above its tier maximum 4096"
                if obj.exists() or need not in message:
                    raise ValueError(f"{intrinsic} size 8192: want '{need}' and no output, got {message[-300:]!r}")
        tiers[intrinsic] = {"atMaximum": 4096, "refused": 8192}
    report["tierMaximum"] = tiers

    for name, (source, code) in refusals().items():
        result, obj = windows16.compile_source(gate, compiler, output, name, source, expected=1)
        message = (result.stdout + result.stderr).decode(errors="replace")
        if code not in message or obj.exists():
            raise ValueError(f"{name} was not refused with {code} and no output: {message}")
        report[name] = f"refused {code}"
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_WINDOWS4K " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
