#!/usr/bin/env python3
"""JUN-31: the aiueos kernel object route through the C-free selfhost compiler.

Runs on Linux x86-64 (no C loader is built or run; Python orchestrates and
hashes only). Takes the loaderless selfhost build produced by
`selfhost-bootstrap.py` (arm64 Linux; Amu-produced root, no C compiler or
loader anywhere in the lineage) and compiles the aiueos kernel-object probe
fixtures with two C-free producers:

* the x86_64 static selfhost compiler `S-x86_64.elf` (built by the aarch64
  S1=S2=S3 fixed point), and
* the C-free KX64V1 runner `R-x86_64.elf` carrying the G1 payload (the same
  selfhost source compiled to `kx64-v1` by the static compiler).

Every object is validated against the fail-closed aiueos kernel object ABI
(x86_64-aiueos-kernel-v1), embedded here so this gate is self-contained after
`check-x86_64-aiueos-object.py` was retired with the C loader (RETIRED.md).
The fixtures and refusals are the same suite on both routes, so the static
image and C-free runner routes are directly comparable, and the harness
asserts the two routes emit byte-identical objects.

Boundary (do not round it up): the seed route emits the kernel OBJECT ABI
only. It is not the kernel IMAGE route, and no emitted object has run in a
kernel.
"""
import argparse
import hashlib
import json
import platform
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
TARGET = "x86_64-aiueos-kernel-v1"


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def extract_kx64(src, dst):
    """KX64V1 container -> bare payload (from the retired check-x86_64-selfhost.py)."""
    header, payload = Path(src).read_bytes().split(b"\n\n", 1)
    match = re.fullmatch(rb"KX64V1 x86_64-linux sysv-ctx-v11 ([0-9]+) 0", header)
    assert match and 0 < len(payload) == int(match[1]) < 4194304, "invalid x86 runtime container"
    assert payload[0] == 0xE9, "missing bounded entry trampoline"
    Path(dst).write_bytes(payload)


def verify_abi(blob, expected_symbol):
    """The aiueos x86_64-aiueos-kernel-v1 object ABI, fail-closed.

    Same conditions as aiueos's `os/aiueos/scripts/verify-kotoba-kernel-object.py`
    (carried over verbatim from the retired check-x86_64-aiueos-object.py).
    """
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


CASES = {
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

SHAPE_REFUSALS = {
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

FLAG_REFUSALS = [
    ("policy", ("--policy", "unknown")),
    ("source-path", ("--source-path", "unknown")),
    ("format-kx64", ("--format", "kx64-v1")),
    ("zero-fuel", ("--fuel", "0")),
    ("bad-fuel", ("--fuel", "12x")),
    ("overflow-fuel", ("--fuel", "99999999999999999")),
]


def command_env(scope):
    """The loader-suite command environment (retired check-x86_64-aiueos-object.py).

    Measured (2026-10-22, R1.elf + G1 payload): without KEXE_COMMAND the
    runner echoes the guest exit status as a trailing stdout line and exits 0,
    so refusal exits do not propagate; with KEXE_COMMAND=1 the guest exit
    status is the process exit status, matching the loader. The static image
    propagates either way.

    KEXE_SECCOMP=if-available is required on qemu-user hosts: the hardened
    runtime (seed/76-x86_64-static-rt.kotoba) fails closed at startup with
    `kexe-runtime: resource limit setup failed` when seccomp(2) returns ENOSYS
    and the invoker did not opt in. On a native kernel seccomp installs and
    enforces (measured on native aarch64 in selfhost-bootstrap.json
    hardening.sandboxProbe: SIGSYS/120); the receipt records per-run whether
    the sandbox was actually enforced.
    """
    env = {"PATH": "/usr/bin:/bin", "TMPDIR": str(scope)}
    env.update(KEXE_COMMAND="1", KEXE_SECCOMP="if-available",
               KEXE_CAP_RESOURCES_35=str(scope), KEXE_FUEL="off",
               KEXE_VECTORS="4194304", KEXE_VECTOR_ITEMS="134217728",
               KEXE_STRING_POOL="268435456", KEXE_PAIRS="16777216",
               KEXE_CPU_SECONDS="120", KEXE_WALL_SECONDS="120")
    return env


def compile_case(prefix, scope, name, source, extra, expect_ok, sentinel=None):
    src, obj = scope / (name + ".kotoba"), scope / (name + ".o")
    src.write_text(source)
    if sentinel is not None:
        obj.write_bytes(sentinel)
    args = [*prefix, "compile", src, "--target", TARGET, "--output", obj, *extra]
    result = subprocess.run(list(map(str, args)), cwd=scope, env=command_env(scope),
                            capture_output=True, timeout=600)
    if expect_ok:
        assert result.returncode == 0 and not result.stderr, (name, result.returncode, result.stderr)
    return obj, result


def run_route(label, prefix, scope, route_rows):
    scope.mkdir(parents=True, exist_ok=True)
    rows, refused = [], []
    for name, (source, symbol) in CASES.items():
        extra = ("--fuel", "3000000000") if name == "big-fuel" else ("--fuel", "1024")
        obj, result = compile_case(prefix, scope, name, source, extra, True)
        fields = {k.decode(): int(v) for k, v in re.findall(rb":([a-z-]+) (\d+)", result.stdout)}
        blob = obj.read_bytes()
        assert fields["bytes"] == len(blob), (name, fields, len(blob))
        verify_abi(blob, symbol)
        rows.append({"name": name, "symbol": symbol, "bytes": len(blob),
                     "textBytes": fields["text-bytes"], "objectPin": pin(obj)})
    for name, text in SHAPE_REFUSALS.items():
        obj, result = compile_case(prefix, scope, "refuse-" + name, text, ("--fuel", "1024"), False)
        assert result.returncode != 0 and not obj.exists(), (name, result.stdout, result.stderr)
        code = re.search(rb"E(\d{4})", result.stderr)
        assert code, (name, result.stderr)
        refused.append({"name": name, "code": "E" + code[1].decode()})
    for name, extra in FLAG_REFUSALS:
        obj, result = compile_case(prefix, scope, "refuse-" + name, CASES["probe"][0], extra, False)
        assert result.returncode == 2 and b"E7100" in result.stderr and not obj.exists(), (name, result.stderr)
        refused.append({"name": name, "code": "E7100"})
    obj, result = compile_case(prefix, scope, "existing-output", CASES["probe"][0], ("--fuel", "1024"), False,
                               sentinel=b"preserve original")
    assert result.returncode == 2 and obj.read_bytes() == b"preserve original"
    refused.append({"name": "existing-output", "code": "E7100"})
    route_rows.append({"route": label, "prefix": [str(p) for p in prefix], "cases": rows, "refusals": refused})


def main(build, output):
    assert platform.system() == "Linux" and platform.machine() in ("x86_64", "AMD64"), platform.platform()
    output.mkdir(parents=True, exist_ok=False)
    receipt = json.loads((build / "selfhost-bootstrap.json").read_text())
    assert receipt["status"] == "PASS_LOADERLESS_SELFHOST_BOOTSTRAP" and receipt["cCompilerOrLoader"] is False, \
        "the producer lineage must be the loaderless selfhost bootstrap"
    compiler = build / "S-x86_64.elf"
    runner = build / "R-x86_64.elf"
    assert pin(compiler) == receipt["built"]["x86_64Compiler"], "x86_64 compiler pin drift"
    assert pin(runner) == receipt["built"]["x86_64Runner"], "x86_64 runner pin drift"
    unity = build / "selfhost-unity.kotoba"
    # The unity source must be the exact concatenation of the manifest's
    # modules (the bootstrap's unity() contract), and the repo copies must not
    # have drifted from the receipt's pins.
    source_graph = receipt["sourceGraph"]
    for path, expected in source_graph.items():
        assert pin(ROOT / path) == expected, ("source pin drift", path)
    manifest_key = next(iter(source_graph))
    module_paths = [p for p in (ROOT / manifest_key).read_text().splitlines() if p and not p.startswith("#")]
    assert set([manifest_key, *module_paths]) == set(source_graph), "source graph shape drift"
    assert unity.read_bytes() == b"".join((ROOT / p).read_bytes() + b"\n" for p in module_paths), \
        "selfhost unity source drift"
    # Containment parity with the loader-run suite: producer and payload live
    # inside the declared capability root (KEXE_CAP_RESOURCES_35 = scope).
    static_scope = output / "static"
    static_scope.mkdir(parents=True, exist_ok=True)
    compiler_copy = static_scope / "S-x86_64.elf"
    shutil.copyfile(compiler, compiler_copy)
    compiler_copy.chmod(0o755)
    # The G1 payload: the selfhost source as a KX64V1 image, emitted C-free by
    # the static compiler itself and carried by the C-free runner.
    payload_scope = output / "payload"
    payload_scope.mkdir(parents=True, exist_ok=True)
    payload_producer = payload_scope / "S-x86_64.elf"
    shutil.copyfile(compiler, payload_producer)
    payload_producer.chmod(0o755)
    payload_src = payload_scope / "selfhost-unity.kotoba"
    shutil.copyfile(unity, payload_src)
    g1k = payload_scope / "G1.kx64"
    result = subprocess.run([str(payload_producer), "compile", str(payload_src), "--target", "x86_64-linux",
                             "--output", str(g1k), "--format", "kx64-v1"],
                            cwd=payload_scope, env=command_env(payload_scope), capture_output=True, timeout=600)
    assert result.returncode == 0 and not result.stderr, (result.returncode, result.stderr)
    runner_scope = output / "runner"
    runner_scope.mkdir(parents=True, exist_ok=True)
    runner_copy = runner_scope / "R-x86_64.elf"
    shutil.copyfile(runner, runner_copy)
    runner_copy.chmod(0o755)
    g1 = runner_scope / "G1.bin"
    extract_kx64(g1k, g1)
    # Was the guest sandbox actually enforced on this host? The runtime's own
    # diagnostic (KEXE_SANDBOX_PROBE: one syscall outside the filter) traps
    # SIGSYS/exit 120 when seccomp is installed and passes through when not
    # (qemu-user ENOSYS + KEXE_SECCOMP=if-available).
    probe = subprocess.run([str(payload_producer)], cwd=payload_scope,
                           env=dict(command_env(payload_scope), KEXE_SANDBOX_PROBE="1"),
                           capture_output=True, timeout=600)
    seccomp_enforced = probe.returncode == 120 and b"SIGSYS" in probe.stderr
    routes = []
    run_route("static-image-x86_64", [compiler_copy], static_scope, routes)
    run_route("kx64-runner-x86_64", [runner_copy, g1, 0, 0, "x86_64", "35,37,38,39", "--"], runner_scope, routes)
    # Route parity: the same source graph, two C-free producers, identical objects.
    by_route = {r["route"]: {c["name"]: c["objectPin"] for c in r["cases"]} for r in routes}
    assert by_route["static-image-x86_64"] == by_route["kx64-runner-x86_64"], "static and runner routes disagree"
    report = {
        "status": "PASS_LINUX_X86_CFREE_AIUEOS_KERNEL_OBJECT_ROUTE",
        "host": [platform.system(), platform.machine()],
        "linear": "JUN-31",
        "target": TARGET,
        "lineage": {"bootstrap": "selfhost-bootstrap.py (Amu-produced root, no C compiler or loader)",
                    "bootstrapReceipt": pin(build / "selfhost-bootstrap.json"),
                    "root": receipt["root"]["image"],
                    "aarch64FixedPoint": receipt["generations"]},
        "compiler": {"staticImage": pin(compiler), "producedBy": "S3.elf aarch64 selfhost fixed point"},
        "runner": {"R": pin(runner), "G1kx64": pin(g1k), "G1payload": pin(g1)},
        "sourcePins": receipt["sourceGraph"],
        "routes": routes,
        "seccomp": {"mode": "if-available", "sandboxProbeExit": probe.returncode, "enforced": seccomp_enforced},
        "executionHost": {"note": "x86_64 images run under qemu-user binfmt (podman --platform linux/amd64); "
                                  "seccomp(2) returns ENOSYS there and RLIMIT_AS/RLIMIT_STACK are not applied "
                                  "to the guest. The aarch64 bootstrap measured enforcement natively "
                                  "(selfhost-bootstrap.json hardening.sandboxProbe = SIGSYS/120); native x86_64 "
                                  "enforcement is unmeasured until a native x86_64 host runs this gate "
                                  "(JUN-34 OCI VM)."},
        "trustedCLoader": False,
        "JVMNodeOrGraalFallback": False,
        "kernelImage": False,
        "kernelExecution": False,
        "performanceMeasured": False,
        "boundary": "kernel OBJECT ABI only; not the kernel image route; no emitted object has run in a kernel",
    }
    (output / "cfree-kernel-object.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], sum(len(r["cases"]) for r in routes), "objects",
          sum(len(r["refusals"]) for r in routes), "refusals", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True, help="selfhost-bootstrap.py output directory")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.build.resolve(), args.output.resolve())
