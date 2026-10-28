#!/usr/bin/env python3
"""The aiueos kernel object route emits one or several exports (JUN-556).

Compiles three sources with a native Amu compiler and reads the objects back
with an independent ELF parser (Python stages and observes; it emits nothing):

* one export: the object is byte-identical to the one the single-export route
  has always produced (its SHA-256 is pinned below), so nothing that links it
  changes;
* two exports: an ET_REL object with the seven expected sections, one local
  .data `context` symbol, two public GLOBAL FUNC symbols, and one R_X86_64_PC32
  addend -4 relocation per export at the context LEA of its shim (offset 3 into
  the shim), with the shims laid out back to back;
* nine exports: refused (E7102), nothing written.

The aiueos verifier (kotoba.aiueos verify-kotoba-kernel-object.py) takes the
export list; this gate does not depend on it.
"""

import argparse
import hashlib
import importlib.util
import json
import struct
from pathlib import Path

MAC_GATE = Path(__file__).with_name("check-aiueos-user-macos-native.py")

ONE_SHA256 = "4d68de1d09d2404b9df5bfabed223ae8b084962e26acee44f73a519e78122af7"
ONE_SOURCE = "(ns one (:export [f]))\n(defn f [x :i64] :i64 (+ x 1))\n"
TWO_SOURCE = ("(ns two (:export [f g]))\n(defn f [x :i64] :i64 (+ x 1))\n"
              "(defn g [x :i64 y :i64] :i64 (* x y))\n")
NINE_SOURCE = ("(ns nine (:export [" + " ".join(f"f{i}" for i in range(9)) + "]))\n"
               + "".join(f"(defn f{i} [x :i64] :i64 (+ x {i}))\n" for i in range(9)))
FUEL = "1024"
SHIM = 29      # the shim for a fuel that fits in 31 bits


def gate_module():
    spec = importlib.util.spec_from_file_location("mac_native_gate", MAC_GATE)
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    return gate


def compile_object(gate, compiler, directory, name, source, expected=0):
    """Compile with the compiler's file root on the output directory (fd 3)."""
    (directory / f"{name}.kotoba").write_text(source)
    out = directory / f"{name}.o"
    result = gate.native_run(compiler, directory, "compile", f"{name}.kotoba",
                             "--target", "x86_64-aiueos-kernel-v1", "--output", out.name,
                             "--fuel", FUEL, expected=expected)
    return result, out


def read_elf(path):
    blob = path.read_bytes()
    if blob[:16] != b"\x7fELF\x02\x01\x01\x00" + b"\0" * 8:
        raise ValueError("not ELF64 little-endian System V")
    etype, machine = struct.unpack_from("<HH", blob, 16)
    shoff, = struct.unpack_from("<Q", blob, 40)
    shnum, shstrndx = struct.unpack_from("<HH", blob, 60)
    if (etype, machine) != (1, 62):
        raise ValueError("not ET_REL / EM_X86_64")
    secs = [struct.unpack_from("<IIQQQQIIQQ", blob, shoff + 64 * i) for i in range(shnum)]
    shstr = blob[secs[shstrndx][4]:secs[shstrndx][4] + secs[shstrndx][5]]

    def name_at(table, offset):
        return table[offset:table.index(b"\0", offset)].decode()

    by_name = {name_at(shstr, s[0]): i for i, s in enumerate(secs)}
    if set(by_name) != {"", ".text", ".data", ".rela.text", ".symtab", ".strtab", ".shstrtab"}:
        raise ValueError(f"unexpected sections {sorted(by_name)}")

    def body(name):
        s = secs[by_name[name]]
        return blob[s[4]:s[4] + s[5]], s

    strtab, _ = body(".strtab")
    symdata, symsec = body(".symtab")
    symbols = []
    for off in range(0, len(symdata), 24):
        n, info, other, shndx, value, size = struct.unpack_from("<IBBHQQ", symdata, off)
        symbols.append((name_at(strtab, n), info, shndx, value, size))
    reladata, relasec = body(".rela.text")
    relas = [struct.unpack_from("<QQq", reladata, off) for off in range(0, len(reladata), 24)]
    text, _ = body(".text")
    return {"symbols": symbols, "relas": relas, "text": text, "sym_info": symsec[7],
            "data_index": by_name[".data"], "text_index": by_name[".text"]}


def check_two(obj):
    syms, relas = obj["symbols"], obj["relas"]
    expected = ["", "context", "f", "g"]
    if [s[0] for s in syms] != expected:
        raise ValueError(f"symbols {[s[0] for s in syms]}")
    null, context, f, g = syms
    if context[1:3] != (0x01, obj["data_index"]) or context[4] != 80:
        raise ValueError("context is not a local 80-byte .data object")
    if obj["sym_info"] != 2:
        raise ValueError("sh_info must name the first global (index 2)")
    for sym, start in ((f, 0), (g, SHIM)):
        if sym[1] != 0x12 or sym[2] != obj["text_index"] or sym[3] != start or sym[4] != SHIM:
            raise ValueError(f"export {sym[0]} is {sym[1:]}, want GLOBAL FUNC at {start} size {SHIM}")
    if len(relas) != 2:
        raise ValueError(f"{len(relas)} relocations, want 2")
    for (offset, info, addend), start in zip(relas, (0, SHIM)):
        if offset != start + 3 or info != (1 << 32 | 2) or addend != -4:
            raise ValueError(f"relocation {(offset, info, addend)} at shim {start}")
    # each shim: lea r9,[rip+context]; mov qword [r9+8], fuel; sub rsp,8; call; add rsp,8; ret
    for start in (0, SHIM):
        shim = obj["text"][start:start + SHIM]
        if shim[:3] != b"\x4c\x8d\x0d" or shim[7:11] != b"\x49\xc7\x41\x08" or shim[-1] != 0xC3 or shim[19] != 0xE8:
            raise ValueError(f"shim at {start} is not the expected sequence: {shim.hex()}")
        if struct.unpack_from("<i", shim, 11)[0] != int(FUEL):
            raise ValueError(f"shim at {start} does not replenish fuel {FUEL}")


def main(compiler, output):
    gate = gate_module()
    gate.verify_macho(compiler)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {}

    result, one = compile_object(gate, compiler, output, "one", ONE_SOURCE)
    digest = hashlib.sha256(one.read_bytes()).hexdigest()
    if digest != ONE_SHA256:
        raise ValueError(f"one-export object changed: {digest}")
    report["oneExport"] = {"sha256": digest, "bytes": one.stat().st_size}

    result, two = compile_object(gate, compiler, output, "two", TWO_SOURCE)
    check_two(read_elf(two))
    report["twoExports"] = {"sha256": hashlib.sha256(two.read_bytes()).hexdigest(), "bytes": two.stat().st_size}

    result, nine = compile_object(gate, compiler, output, "nine", NINE_SOURCE, expected=1)
    if "E7102" not in (result.stdout + result.stderr).decode(errors="replace") or nine.exists():
        raise ValueError("nine exports were not refused with E7102 and no output")
    report["nineExports"] = "refused E7102"

    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_EXPORTS " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True,
                        help="a signed Mac native Amu compiler image (the Mac gate's fixed-point F*-signed.macho)")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
