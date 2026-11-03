#!/usr/bin/env python3
"""The aiueos kernel object route hands out the address of a fixed-size .bss / .high_bss array (JUN-556 C, ADR 0385).

A private function bss-addr-<k>-<N> [] or highbss-addr-<k>-<N> [] (k a single digit 0..7, N a canonical decimal and a
multiple of 8 in 8..65536, body the placeholder 0) returns the address of zero-initialised LOCAL array k of N bytes:
`lea rax,[rip+disp32]` with an R_X86_64_PC32 relocation against the section's STT_SECTION symbol, addend offset - 4.
Arrays of one section lie in k order at 16-byte aligned offsets. The address is an ordinary value, not a rooted base: it
can only be handed to an extern. An object that names no such stub keeps its bytes (seven sections).

Compiles sources with a native Amu compiler and reads the objects back with an independent ELF parser. Positive: three
arrays (.bss 0 of 1280 and 1 of 24, .high_bss 0 of 1536) passed to a declared extern: two NOBITS sections of sizes 1312
and 1536, two LOCAL section symbols after the context, the globals shifted by two, and one PC32 per lea site with addends
-4, 1276 and -4. The one-export object of check-aiueos-object-exports.py is still byte-identical. Refused: malformed names,
a parameter, a non-zero body, two sizes for one array (E7102), the address as a window or record base (E7106), the image
route (E7102). In every refusal nothing is written.

The QEMU run of this object (addresses and memset contents) was done by hand for the ADR; the consumer's differential
check in the kotoba repository runs the linked kernel.
"""

import argparse
import importlib.util
import json
import struct
from pathlib import Path

HERE = Path(__file__).parent

POSITIVE = ("(ns arrays (:export [f g]))\n"
            "(defn- extern-memset [p :i64 v :i64 n :i64] :i64 0)\n"
            "(defn- bss-addr-0-1280 [] :i64 0)\n(defn- bss-addr-1-24 [] :i64 0)\n(defn- highbss-addr-0-1536 [] :i64 0)\n"
            "(defn f [x :i64] :i64 (+ (extern-memset (bss-addr-0-1280) x 1280) (extern-memset (bss-addr-1-24) 0 24)))\n"
            "(defn g [] :i64 (extern-memset (highbss-addr-0-1536) 0 1536))\n")
LEA = b"\x48\x8d\x05\x00\x00\x00\x00"


def refused_source(decl, call, params="x :i64"):
    return ("(ns r (:export [f]))\n(defn- extern-sink [a :i64] :i64 0)\n" + decl +
            f"\n(defn f [{params}] :i64 {call})\n")


def one_stub(name, body="0", params=""):
    return refused_source(f"(defn- {name} [{params}] :i64 {body})", f"(extern-sink ({name}{' x' if params else ''}))")


CASES_7102 = {
    "k-8": one_stub("bss-addr-8-16"),
    "n-not-multiple-of-8": one_stub("bss-addr-0-12"),
    "n-too-large": one_stub("bss-addr-0-65544"),
    "n-leading-zero": one_stub("bss-addr-0-016"),
    "n-missing": one_stub("bss-addr-0-"),
    "high-k-two-digits": one_stub("highbss-addr-10-16"),
    "with-param": one_stub("bss-addr-0-16", params="v :i64"),
    "body-not-zero": one_stub("bss-addr-0-16", body="7"),
    "two-sizes": refused_source("(defn- bss-addr-0-16 [] :i64 0)\n(defn- bss-addr-0-32 [] :i64 0)",
                                "(+ (extern-sink (bss-addr-0-16)) (extern-sink (bss-addr-0-32)))"),
}

CASES_7106 = {
    "address-as-window-base": refused_source(
        "(defn- bss-addr-0-64 [] :i64 0)", "(kernel-load-u32 (bss-addr-0-64) n 0)", "n :i64"),
    "address-as-record-base": refused_source(
        "(defn- bss-addr-0-64 [] :i64 0)\n(defn- record-load-u32-0-40 [b :i64] :i64 0)", "(record-load-u32-0-40 (bss-addr-0-64))"),
}


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_elf(path):
    blob = path.read_bytes()
    if blob[:16] != b"\x7fELF\x02\x01\x01\x00" + b"\0" * 8 or struct.unpack_from("<HH", blob, 16) != (1, 62):
        raise ValueError("not an ELF64 x86-64 ET_REL object")
    shoff, = struct.unpack_from("<Q", blob, 40)
    shnum, shstrndx = struct.unpack_from("<HH", blob, 60)
    secs = [struct.unpack_from("<IIQQQQIIQQ", blob, shoff + 64 * i) for i in range(shnum)]
    shstr = blob[secs[shstrndx][4]:secs[shstrndx][4] + secs[shstrndx][5]]

    def name_at(table, offset):
        return table[offset:table.index(b"\0", offset)].decode()

    names = [name_at(shstr, s[0]) for s in secs]
    body = lambda i: blob[secs[i][4]:secs[i][4] + secs[i][5]]
    strtab = body(names.index(".strtab"))
    symdata = body(names.index(".symtab"))
    symbols = [(name_at(strtab, n), info, shndx, value, size)
               for off in range(0, len(symdata), 24)
               for n, info, other, shndx, value, size in [struct.unpack_from("<IBBHQQ", symdata, off)]]
    reladata = body(names.index(".rela.text"))
    relas = [struct.unpack_from("<QQq", reladata, off) for off in range(0, len(reladata), 24)]
    return {"names": names, "secs": secs, "symbols": symbols, "relas": relas,
            "text": body(names.index(".text")), "sym_info": secs[names.index(".symtab")][7], "size": len(blob)}


def check(obj):
    if obj["names"] != ["", ".text", ".data", ".rela.text", ".symtab", ".strtab", ".shstrtab", ".bss", ".high_bss"]:
        raise ValueError(f"sections {obj['names']}")
    for i, size in ((7, 1312), (8, 1536)):
        _, typ, flags, addr, off, sz, link, info, align, entsize = obj["secs"][i]
        if (typ, flags, addr, sz, align, entsize) != (8, 3, 0, size, 16, 0):
            raise ValueError(f"{obj['names'][i]} header {obj['secs'][i]}, want NOBITS WA size {size} align 16")
        if off > obj["size"]:
            raise ValueError(f"{obj['names'][i]} offset {off} past the file")
    syms = obj["symbols"]
    if [(s[0], s[1], s[2], s[3]) for s in syms[2:4]] != [("", 0x03, 7, 0), ("", 0x03, 8, 0)]:
        raise ValueError(f"symbols 2 and 3 are {syms[2:4]}, want LOCAL SECTION symbols of .bss and .high_bss")
    if obj["sym_info"] != 4:
        raise ValueError(f"sh_info {obj['sym_info']}, want 4 (the first global after the section symbols)")
    if [s[0] for s in syms[4:]] != ["f", "g", "memset"]:
        raise ValueError(f"globals {[s[0] for s in syms[4:]]}")
    text = obj["text"]
    sites, at = [], 0
    while (at := text.find(LEA, at)) >= 0:
        sites.append(at + 3)
        at += len(LEA)
    found = [(info, a) for site in sites for off, info, a in obj["relas"] if off == site]
    want = [(2 << 32 | 2, -4), (2 << 32 | 2, 1280 - 4), (3 << 32 | 2, -4)]
    if found != want:
        raise ValueError(f"lea relocations {found}, want {want}")
    memset = [(off, a) for off, info, a in obj["relas"] if info == (6 << 32 | 4)]
    if len(memset) != 3 or any(a != -4 for _, a in memset):
        raise ValueError(f"memset relocations {memset}, want three PLT32 against symbol 6")


def refused(gate, exports, compiler, output, name, source, code):
    result, bad = exports.compile_object(gate, compiler, output, name, source, expected=1)
    if bad.exists() or code not in (result.stdout + result.stderr).decode(errors="replace"):
        raise ValueError(f"{name}: not refused with {code} and no output")
    return f"refused {code}"


def main(compiler, output):
    exports = load("check-aiueos-object-exports")
    gate = exports.gate_module()
    gate.verify_macho(compiler)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {}
    _, path = exports.compile_object(gate, compiler, output, "arrays", POSITIVE)
    check(read_elf(path))
    report["arrays"] = {"bytes": path.stat().st_size}
    import hashlib
    _, one = exports.compile_object(gate, compiler, output, "one", exports.ONE_SOURCE)
    if hashlib.sha256(one.read_bytes()).hexdigest() != exports.ONE_SHA256:
        raise ValueError("an object without arrays changed its bytes")
    report["withoutArrays"] = "byte-identical"
    for name, source in CASES_7102.items():
        report[name] = refused(gate, exports, compiler, output, name, source, "E7102")
    for name, source in CASES_7106.items():
        report[name] = refused(gate, exports, compiler, output, name, source, "E7106")
    (output / "image.kotoba").write_text("(ns i (:export [main]))\n(defn- bss-addr-0-16 [] :i64 0)\n(defn main [] :i64 (bss-addr-0-16))\n")
    result = gate.native_run(compiler, output, "compile", "image.kotoba", "--target", "x86_64-aiueos-kernel-v1",
                             "--artifact", "image", "--output", "image.elf", "--fuel", "1024", expected=1)
    if (output / "image.elf").exists() or "E7102" not in (result.stdout + result.stderr).decode(errors="replace"):
        raise ValueError("an array declaration on the image route was not refused with E7102")
    report["image"] = "refused E7102"
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_ARRAYS " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
