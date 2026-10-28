#!/usr/bin/env python3
"""Qualify the seed x86_64-aiueos-kernel-v1 kernel object route, loaderless.

Compiles probe fixtures with an Amu-produced static compiler (--compiler,
e.g. S3.elf from selfhost-bootstrap.py; no C loader) and validates each
object against the aiueos kernel object ABI -- the same fail-closed
conditions as aiueos's `os/aiueos/scripts/verify-kotoba-kernel-object.py`,
embedded here so this gate is self-contained. Also pins every refusal the
route must keep. Port of the script retired with the C loader
(scripts/seed/RETIRED.md); the probes, ABI checks and refusals are unchanged.
"""
import argparse
import hashlib
import json
import platform
import re
import struct
import subprocess
from pathlib import Path

TARGET = "x86_64-aiueos-kernel-v1"


def pin(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def verify_abi(blob, expected_symbol):
    """The aiueos x86_64-aiueos-kernel-v1 object ABI, fail-closed."""
    assert len(blob) >= 64 and blob[:16] == b"\x7fELF\x02\x01\x01\x00" + b"\0" * 8, "not canonical ELF64 LE SysV"
    header = struct.unpack_from("<HHIQQQIHHHHHH", blob, 16)
    etype, machine, version, entry, phoff, shoff, flags, ehsize, phentsize, phnum, shentsize, shnum, shstrndx = header
    assert (etype, machine, version, entry, phoff, phnum, flags, ehsize, shentsize) == (1, 62, 1, 0, 0, 0, 0, 64, 64), \
        "header is not ET_REL/EM_X86_64 without program headers"
    assert shnum and shnum <= 16 and shstrndx < shnum and shoff + shnum * 64 <= len(blob), "invalid section table bounds"
    sections = [struct.unpack_from("<IIQQQQIIQQ", blob, shoff + i * 64) for i in range(shnum)]

    def section_bytes(index):
        _, stype, _, _, offset, size, _, _, _, _ = sections[index]
        if stype == 8:
            return b""
        assert offset + size <= len(blob), "section exceeds file"
        return blob[offset:offset + size]

    strings = section_bytes(shstrndx)

    def string_at(table, offset):
        assert offset < len(table), "string offset exceeds table"
        end = table.find(b"\0", offset)
        assert end >= 0, "unterminated string"
        return table[offset:end].decode("ascii")

    names = [string_at(strings, section[0]) for section in sections]
    allowed = {"", ".text", ".data", ".rela.text", ".symtab", ".strtab", ".shstrtab"}
    assert set(names) == allowed and len(names) == len(allowed), f"section set {names!r}"
    by_name = {name: index for index, name in enumerate(names)}
    assert sections[by_name[".text"]][1] == 1 and sections[by_name[".text"]][2] & 0x4, ".text must be executable PROGBITS"
    assert sections[by_name[".data"]][1] == 1 and not sections[by_name[".data"]][2] & 0x4, ".data must be non-exec PROGBITS"
    sym_index = by_name[".symtab"]
    sym = sections[sym_index]
    assert sym[1] == 2 and sym[9] == 24 and sym[6] == by_name[".strtab"] and not sym[5] % 24, "invalid symbol table"
    symbol_strings = section_bytes(by_name[".strtab"])
    symbols = []
    for offset in range(0, len(section_bytes(sym_index)), 24):
        name, info, other, shndx, value, size = struct.unpack_from("<IBBHQQ", section_bytes(sym_index), offset)
        symbols.append((string_at(symbol_strings, name), info, other, shndx, value, size))
    # expected_symbol is one name, or several joined by commas (a multi-export
    # object, JUN-556); each must be exactly one GLOBAL FUNC in .text.
    expected_symbols = expected_symbol.split(",")
    assert 1 <= len(expected_symbols) <= 8 and len(set(expected_symbols)) == len(expected_symbols), "export list"
    for name in expected_symbols:
        probes = [item for item in symbols if item[0] == name]
        assert len(probes) == 1, f"requires exactly one {name} symbol"
        _, info, other, shndx, _, size = probes[0]
        assert info == 0x12 and other == 0 and shndx == by_name[".text"] and size != 0, \
            "export must be a default-visibility GLOBAL FUNC defined in .text"
    assert not any(item[3] == 0 and item[0] for item in symbols), "undefined/imported symbols are forbidden"
    rela = sections[by_name[".rela.text"]]
    count = len(expected_symbols)
    assert rela[1] == 4 and rela[9] == 24 and rela[6] == sym_index and rela[7] == by_name[".text"] and rela[5] == 24 * count, \
        "requires exactly one .rela.text entry per export"
    context_symbols = set()
    for entry in range(count):
        rel_offset, rel_info, addend = struct.unpack_from("<QQq", section_bytes(by_name[".rela.text"]), entry * 24)
        symbol_index, relocation_type = rel_info >> 32, rel_info & 0xFFFFFFFF
        assert symbol_index < len(symbols) and relocation_type == 2 and addend == -4, \
            "relocation must be R_X86_64_PC32 with addend -4"
        assert symbols[symbol_index][3] == by_name[".data"], "relocation target must be defined in .data"
        assert rel_offset + 4 <= len(section_bytes(by_name[".text"])), "relocation offset exceeds .text"
        context_symbols.add(symbol_index)
    assert len(context_symbols) == 1, "every relocation must name the same context symbol"


def main(compiler, output, seccomp_if_available=False):
    assert platform.system() == "Linux"
    output.mkdir(parents=True, exist_ok=False)
    artifacts = output / "artifacts"
    raw = output / "raw"
    artifacts.mkdir()
    raw.mkdir()
    env = {"PATH": "/nonexistent", "KEXE_CAP_RESOURCES_35": str(artifacts)}
    if seccomp_if_available:
        env["KEXE_SECCOMP"] = "if-available"
    compiler_pin = pin(compiler)

    def compile_case(name, source, expected_symbol, extra=("--fuel", "1024"), sentinel=None):
        src, obj = artifacts / (name + ".kotoba"), artifacts / (name + ".o")
        src.write_text(source)
        if sentinel is not None:
            obj.write_bytes(sentinel)
        source_before = pin(src)
        args = [compiler, "compile", src, "--target", TARGET, "--output", obj, *extra]
        result = subprocess.run(list(map(str, args)), cwd=artifacts, env=env, capture_output=True, timeout=180)
        (raw / (name + ".stdout")).write_bytes(result.stdout)
        (raw / (name + ".stderr")).write_bytes(result.stderr)
        assert pin(src) == source_before, "guest source changed during compilation"
        assert pin(compiler) == compiler_pin, "compiler mutation"
        return obj, result

    cases = {
        "probe": ("(ns kernel-probe (:export [kotoba_aiueos_probe]))\n(defn kotoba_aiueos_probe [] :i64 42)\n",
                  "kotoba_aiueos_probe"),
        "flat-args": ("(ns kernel-flat (:export [kotoba_aiueos_flat]))\n"
                      "(defn kotoba_aiueos_flat [a :i64 n :i64] :i64 (+ a n))\n", "kotoba_aiueos_flat"),
        "helper-loop": ("(ns kernel-loop (:export [kotoba_aiueos_loop]))\n"
                        "(defn- sum [n :i64 s :i64] :i64 (if (= n 0) s (sum (dec n) (+ s n))))\n"
                        "(defn kotoba_aiueos_loop [] :i64 (sum 10 0))\n", "kotoba_aiueos_loop"),
        "big-fuel": ("(ns kernel-big (:export [kotoba_aiueos_big]))\n(defn kotoba_aiueos_big [] :i64 7)\n",
                     "kotoba_aiueos_big"),
        "two-exports": ("(ns kernel-two (:export [kotoba_aiueos_a kotoba_aiueos_b]))\n"
                        "(defn kotoba_aiueos_a [] :i64 1)\n(defn kotoba_aiueos_b [x :i64] :i64 (+ x 2))\n",
                        "kotoba_aiueos_a,kotoba_aiueos_b"),
    }
    rows = []
    for name, (source, symbol) in cases.items():
        extra = ("--fuel", "3000000000") if name == "big-fuel" else ("--fuel", "1024")
        obj, result = compile_case(name, source, symbol, extra=extra)
        assert result.returncode == 0 and not result.stderr, (name, result.returncode, result.stderr)
        fields = {k.decode(): int(v) for k, v in re_findall(result.stdout)}
        blob = obj.read_bytes()
        assert fields["bytes"] == len(blob), (name, fields, len(blob))
        verify_abi(blob, symbol)
        rows.append({"name": name, "symbol": symbol, "bytes": len(blob),
                     "textBytes": fields["text-bytes"], "objectPin": pin(obj)})
    # A wrapper whose entry needs >2^31-1 fuel takes the imm64 replenish path;
    # both paths must stay ABI-identical.
    refusals = {
        "no-export": "(ns refused)\n(defn- helper [] :i64 1)\n",
        "nine-exports": "(ns refused (:export [" + " ".join(f"kotoba_aiueos_{i}" for i in range(9)) + "]))\n"
                       + "".join(f"(defn kotoba_aiueos_{i} [] :i64 {i})\n" for i in range(9)),
        "six-params": "(ns refused (:export [kotoba_aiueos_six]))\n"
                      "(defn kotoba_aiueos_six [a :i64 b :i64 c :i64 d :i64 e :i64 f :i64] :i64 (+ a b c d e f))\n",
        "float": "(ns refused (:export [kotoba_aiueos_f]))\n"
                 "(defn kotoba_aiueos_f [] :i64 (f64-to-i64-truncating (f64-add 1.0 2.0)))\n",
        "string": "(ns refused (:export [kotoba_aiueos_s]))\n"
                  "(defn kotoba_aiueos_s [] :i64 (string-length \"hello\"))\n",
        "vector": "(ns refused (:export [kotoba_aiueos_v]))\n"
                  "(defn kotoba_aiueos_v [] :i64 (vector-count [1 2]))\n",
        "capability": "(ns refused (:export [kotoba_aiueos_c]))\n"
                      "(defn kotoba_aiueos_c [p :string] :string (typed-cap-call :fs/app-data :string :string p))\n",
        "unused-bad-helper": "(ns refused (:export [kotoba_aiueos_u]))\n"
                             "(defn- unused [v :vector-i64] :i64 (vector-count v))\n"
                             "(defn kotoba_aiueos_u [] :i64 42)\n",
    }
    refused = []
    for name, source in refusals.items():
        obj, result = compile_case("refuse-" + name, source, "unused")
        assert result.returncode != 0 and not obj.exists(), (name, result.stdout, result.stderr)
        # Fail-closed at either stage is a refusal: the shared check stage
        # (E21xx) refuses some shapes before the route's own E71xx rules.
        code = re.search(rb"E(\d{4})", result.stderr)
        assert code, (name, result.stderr)
        refused.append({"name": name, "code": "E" + code[1].decode()})
    for name, extra in [("policy", ("--policy", "unknown")), ("source-path", ("--source-path", "unknown")),
                        ("format-kx64", ("--format", "kx64-v1")),
                        ("zero-fuel", ("--fuel", "0")), ("bad-fuel", ("--fuel", "12x")),
                        ("overflow-fuel", ("--fuel", "99999999999999999"))]:
        obj, result = compile_case("refuse-" + name, cases["probe"][0], "kotoba_aiueos_probe", extra=extra)
        assert result.returncode == 2 and b"E7100" in result.stderr and not obj.exists(), (name, result.stderr)
        refused.append({"name": name, "code": "E7100"})
    obj, result = compile_case("existing-output", cases["probe"][0], "kotoba_aiueos_probe", sentinel=b"preserve original")
    assert result.returncode == 2 and obj.read_bytes() == b"preserve original"
    refused.append({"name": "existing-output", "code": "E7100"})
    suite = {"status": "PASS_SEED_AIUEOS_KERNEL_OBJECT_ROUTE_LOADERLESS", "cases": rows, "refusals": refused,
             "compiler": compiler_pin, "host": [platform.system(), platform.machine(), platform.release()],
             "compilerSeccomp": "if-available" if seccomp_if_available else "required",
             "cCompilerOrLoader": False, "kernelExecution": False, "performanceMeasured": False}
    (output / "suite.json").write_text(json.dumps(suite, indent=2) + "\n")
    print(suite["status"], len(rows), "objects", len(refused), "refusals", flush=True)


def re_findall(stdout):
    import re
    return re.findall(rb":([a-z-]+) (\d+)", stdout)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True, help="an Amu-produced static compiler (e.g. S3.elf)")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seccomp-if-available", action="store_true",
                        help="run the compiler with KEXE_SECCOMP=if-available (kernels without seccomp); recorded")
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve(), args.seccomp_if_available)
