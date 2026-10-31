#!/usr/bin/env python3
"""The route B2 image (--format b2, ADR 0375, JUN-377; seed module 98 on x86_64-linux, seed/80 and
seed/77 on aarch64-linux, JUN-701).

--compiler is an Amu-produced compiler from the current sources (F or S of
selfhost-bootstrap.py, the complete x86_64 compiler, or a Mac arm64 compiler
built from FULL-MANIFEST); --target picks the images it writes (x86_64-linux
by default, or aarch64-linux). Python only orchestrates processes and parses
bytes.

Phase "build" (any Linux host the compiler runs on, or Mac arm64 with a Mac compiler):
* images: hello, mem (E2: 16- and 32-bit loads and stores) and abi (E1: SysV
  or AAPCS64 entry thunks and the export table), from tools/b2/tests/ (the
  target's image_arch_*.kotoba first; abi is image_abi_common.kotoba and the
  target's own test);
* structure, parsed from the bytes: a static ET_EXEC with exactly PT_LOAD RX,
  PT_LOAD RW and PT_GNU_STACK (no interpreter, no dynamic section), context
  word 408 = 5 and word 416 = the export table; the table (count, thunk, name
  and version per export, in definition order), each thunk's exact size and
  its bytes at both ends (push rbp; mov rbp,rsp ... leave; ret), the callee
  of its call, the fuel immediate, and the NUL-ended strings. A corrupted
  copy of the image must fail the same parse (the checker's negative control).
  On aarch64-linux the thunk is AArch64 words: sub sp / stp x29, x30 / add x29
  ... ldp x29, x30 / add sp / ret, the fuel word as movz/movk x16, the bl to the
  callee and two context loads (movz/movk x7);
* refusals: a runtime call outside the kxrt-b- API (E7101), the kxrt-b- API in
  --format static (E2101, an unknown name), an export with a :string parameter, an empty export
  name and an empty version (E7102), more than 16 parameters (E2178, the checker's limit); a cx-
  function in --format static is an ordinary function (no thunk, the same bytes as under another name);
* with --previous-compiler: the static, runner and launcher outputs of both
  Linux targets are the same bytes as the previous compiler's, and whether it
  refuses the format on --target.

Phase "run" (a Linux kernel of --target's architecture):
* hello: the output, the exit status 7 + argc;
* mem: the 16- and 32-bit stores touch exactly their bytes; loads zero-extend;
* abi, from Kotoba through kxrt-b-ccall: a thunk called with 14 words (six
  registers and eight stack words), 0 to 16 parameters, a :bool and a negative
  result, a missing version; then a hand-assembled C function (a machine-code
  page the test writes) that sets rbx, r12..r15, calls a thunk and stores the
  registers afterwards: unchanged. A control calls a function that clobbers rbx:
  the difference shows. Stack alignment: a machine-code probe does an aligned
  store (movaps) inside a call from C into Kotoba and back out; it passes, and a
  caller that misaligns the stack by 8 faults (SIGSEGV), so the probe can see it.
  On aarch64 the page is written, then made RX (the kernel synchronizes the
  instruction cache): the hand-assembled caller checks x19..x28 and sp, the
  control clobbers x19, and the misaligned caller faults with SIGBUS (SCTLR_EL1.SA0);
* fuel: a call from C runs on its own budget (a 3,000,000-iteration spin under
  KEXE_FUEL=1000000), and the caller's meter is restored on return (the caller
  then runs out: SIGILL on x86_64, SIGTRAP (brk) on aarch64).
The libvulkan image is never run here (GPU hosts only, check-b2-libvulkan.py).

  python3 check-b2-image.py all --compiler F.elf --output OUT      (x86_64 host)
  python3 check-b2-image.py build --compiler F.elf --output OUT    (arm64 host, for example)
  python3 check-b2-image.py run --output OUT                       (x86_64 host)
  python3 check-b2-image.py build --target aarch64-linux --compiler amu --output OUT   (Mac arm64)
  python3 check-b2-image.py run --output OUT                       (aarch64 host; the target is in OUT)
"""
import os
import argparse
import hashlib
import json
import platform
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "tools/b2/tests"
NS = "(ns g (:export [main]))\n"
CODE0 = 0x401000
CALL_FUEL = 0x7FFFFFFF
# the exports of image_abi_t.kotoba in definition order: (name, version, parameters)
EXPORTS = [("zero", "", 0), ("add5", "TESTV1", 5), ("six", "", 6), ("mix14", "GLIBC_2.2.5", 14), ("sixteen", "", 16),
           ("flag", "", 1), ("neg", "", 1), ("probe", "", 1), ("spin", "", 1), ("pair", "", 2)]
ABI_LINES = ["zero ok", "add5 ok", "six ok", "mix14 ok", "sixteen ok", "flag ok", "neg ok", "missing-version ok",
             "A returns ok", "rbx ok", "r12 ok", "r13 ok", "r14 ok", "r15 ok", "control returns ok", "control rbx ok",
             "aligned probe ok"]
ABI_LINES_A64 = (ABI_LINES[:9] + [f"x{r} ok" for r in range(19, 29)]
                 + ["sp ok", "control returns ok", "control x19 ok", "aligned probe ok"])
# per target: ELF machine, the abi test, the run host, the signals of the alignment control and of fuel exhaustion
TARGETS = {
    "x86_64-linux": dict(machine=62, abi="image_abi_t.kotoba", arch="image_arch_x86_64.kotoba", lines=ABI_LINES,
                         hosts=("x86_64", "AMD64"), align_signal=-11, fuel_signal=-4,
                         sources=("seed/98-x86_64-b2.kotoba", "seed/75-x86_64-static.kotoba",
                                  "seed/76-x86_64-static-rt.kotoba", "seed/70-x86_64-linux.kotoba")),
    "aarch64-linux": dict(machine=183, abi="image_abi_a64_t.kotoba", arch="image_arch_aarch64.kotoba", lines=ABI_LINES_A64,
                          hosts=("aarch64", "arm64"), align_signal=-7, fuel_signal=-5,
                          sources=("seed/98-x86_64-b2.kotoba", "seed/80-aarch64-linux.kotoba",
                                   "seed/77-aarch64-static-rt.kotoba", "seed/75-x86_64-static.kotoba")),
}


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def thunk_size(n):
    return 53 + (5 + 9 * (n - 6) if n > 5 else 0)


# aarch64 (seed/80 xa-b2-thunk): the frame, then 24 words plus the register and stack argument copies
def a64_frame(n):
    return 32 + ((15 + 8 * max(0, n - 5)) & -16)


def a64_thunk_size(n):
    regs = 0 if n <= 5 else min(3, n - 5)
    return 4 * (24 + regs + 2 * max(0, n - 8))


def a64_mov64(reg, v):
    return [0xD2800000 | ((v & 0xFFFF) << 5) | reg, 0xF2A00000 | (((v >> 16) & 0xFFFF) << 5) | reg,
            0xF2C00000 | (((v >> 32) & 0xFFFF) << 5) | reg, 0xF2E00000 | (((v >> 48) & 0xFFFF) << 5) | reg]


def elf(path):
    d = Path(path).read_bytes()
    assert d[:4] == b"\x7fELF" and d[4] == 2 and d[5] == 1, "ELF64 LE"
    e_type, e_machine, _, entry, phoff = struct.unpack_from("<HHIQQ", d, 16)
    phentsize, phnum = struct.unpack_from("<HH", d, 54)
    ph = [dict(zip(("type", "flags", "offset", "vaddr", "paddr", "filesz", "memsz", "align"),
                   struct.unpack_from("<IIQQQQQQ", d, phoff + i * phentsize))) for i in range(phnum)]
    return d, dict(type=e_type, machine=e_machine, entry=entry, phdrs=ph)


def export_table(path):
    """The export table of a --format b2 image, read from its bytes: (name, version, thunk address) in order."""
    d, e = elf(path)
    table, = struct.unpack_from("<Q", d, e["phdrs"][1]["offset"] + 416)
    if table == 0:
        return []
    t = table - 0x400000
    count, = struct.unpack_from("<Q", d, t)

    def text(addr):
        return d[addr - 0x400000:d.index(b"\0", addr - 0x400000)].decode()
    return [(text(n), text(v), th) for th, n, v in (struct.unpack_from("<QQQ", d, t + 8 + 24 * i) for i in range(count))]


def structure(path, exports, target="x86_64-linux"):
    """Every structural rule of the image and its export table; exports is the expected list."""
    d, e = elf(path)
    order = [p["type"] for p in e["phdrs"]]
    assert (e["type"], e["machine"], e["entry"]) == (2, TARGETS[target]["machine"], CODE0), e
    assert order == [1, 1, 0x6474E551], ("program headers: no interpreter, no dynamic section", order)
    rx, rw, stack = e["phdrs"]
    assert rx["flags"] == 5 and rx["offset"] == 0 and rw["flags"] == 6 and stack["flags"] == 6, e["phdrs"]
    assert rw["filesz"] == 512 and rw["memsz"] == 65536 and rw["offset"] % 4096 == 0, rw
    code_end = rx["filesz"]
    ctx = rw["offset"]
    mode, table = struct.unpack_from("<Q", d, ctx + 408)[0], struct.unpack_from("<Q", d, ctx + 416)[0]
    assert mode == 5, ("context word 408", mode)
    if not exports:
        assert table == 0, "no exports: no table"
        return dict(table=0, exports=[])
    assert table % 8 == 0 and CODE0 <= table < 0x400000 + code_end, hex(table)
    t = table - 0x400000
    count = struct.unpack_from("<Q", d, t)[0]
    assert count == len(exports), (count, len(exports))
    rows, thunk_at, strings = [], None, t + 8 + 24 * count
    for i, (name, version, n) in enumerate(exports):
        taddr, naddr, vaddr = struct.unpack_from("<QQQ", d, t + 8 + 24 * i)
        if thunk_at is None:
            thunk_at = taddr
        assert taddr == thunk_at, ("thunks are contiguous and in order", i, hex(taddr), hex(thunk_at))
        if target == "aarch64-linux":
            size, callee = a64_thunk(d, taddr, n, name, 0x400000 + ctx)
        else:
            size, callee = x86_thunk(d, taddr, n, name)
        thunk_at += size
        nm = d[naddr - 0x400000:d.index(b"\0", naddr - 0x400000)].decode()
        vr = d[vaddr - 0x400000:d.index(b"\0", vaddr - 0x400000)].decode()
        assert (nm, vr) == (name, version), ("name and version", i, nm, vr)
        assert vaddr == naddr + len(name) + 1 and naddr - 0x400000 >= strings, ("strings", name)
        rows.append(dict(name=name, version=version, parameters=n, thunk=hex(taddr), thunkBytes=size, callee=hex(callee)))
    assert thunk_at <= table < thunk_at + 8, "the table follows the thunks, 8-aligned"
    return dict(table=hex(table), exports=rows)


def x86_thunk(d, taddr, n, name):
        size = thunk_size(n)
        body = d[taddr - 0x400000:taddr - 0x400000 + size]
        frame = 16 if n <= 5 else (16 + 8 * (n - 5)) & -16
        assert body[:8] == b"\x55\x48\x89\xe5\x48\x83\xec" + bytes([frame]), ("prologue", name, body[:8].hex())
        assert body[-2:] == b"\xc9\xc3", ("leave; ret", name)
        # mov qword [r9+8], imm32 and the call, then the second context load
        fuel_at = body.index(b"\x49\xc7\x41\x08")
        assert struct.unpack_from("<I", body, fuel_at + 4)[0] == CALL_FUEL, ("fuel", name)
        assert body[fuel_at + 8] == 0xE8, ("call", name)
        rel = struct.unpack_from("<i", body, fuel_at + 9)[0]
        callee = taddr + fuel_at + 13 + rel
        assert CODE0 <= callee < taddr, ("the callee is guest code before the thunks", name, hex(callee))
        if n > 5:
            assert body[8:13] == b"\x4c\x89\x4c\x24\x00", ("mov [rsp], r9", name)
        assert body.count(b"\x4c\x8d\x0d") == 2, ("two context loads", name)
        return size, callee


def a64_thunk(d, taddr, n, name, ctx):
    """An AArch64 thunk (seed/80 xa-b2-thunk), word by word where the words are fixed."""
    size, frame = a64_thunk_size(n), a64_frame(n)
    w = list(struct.unpack_from(f"<{size // 4}I", d, taddr - 0x400000))
    fp = (frame - 16) // 8
    assert w[:3] == [0xD10003FF | (frame << 10), 0xA9007BFD | (fp << 15), 0x910003FD | ((frame - 16) << 10)], ("prologue", name)
    assert w[-3:] == [0xA9407BFD | (fp << 15), 0x910003FF | (frame << 10), 0xD65F03C0], ("epilogue: ldp, add sp, ret", name)
    if n > 5:
        assert w[3] == 0xF90003E5, ("str x5, [sp]", name)
    fuel = a64_mov64(16, CALL_FUEL) + [0xF90004F0]
    at = next((k for k in range(len(w)) if w[k:k + 5] == fuel), None)
    assert at is not None, ("fuel", name)
    bl = w[at + 5]
    assert bl >> 26 == 0x25, ("bl", name)
    rel = bl & 0x3FFFFFF
    rel = rel - (1 << 26) if rel & (1 << 25) else rel
    callee = taddr + 4 * (at + 5) + 4 * rel
    assert CODE0 <= callee < taddr, ("the callee is guest code before the thunks", name, hex(callee))
    load = a64_mov64(7, ctx)
    assert sum(1 for k in range(len(w)) if w[k:k + 4] == load) == 2, ("two context loads", name)
    return size, callee


def build(compiler, output, previous, target="x86_64-linux"):
    mac = platform.system() == "Darwin"
    assert platform.system() == "Linux" or (mac and platform.machine() == "arm64"), "run on Linux or Mac arm64"
    T = TARGETS[target]
    output.mkdir(parents=True, exist_ok=False)
    art = output / "artifacts"
    art.mkdir()
    producer = art / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)
    calls = []
    cenv = {"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art)}
    helpers = (TESTS / T["arch"]).read_text() + (TESTS / "image_helpers.kotoba").read_text()
    # a Mac compiler reads and writes through the file root on descriptor 3, with relative paths
    root = os.open(art, os.O_RDONLY | os.O_DIRECTORY) if mac else None
    if mac:
        os.dup2(root, 3)

    def compile_(prod, name, source, fmt="b2", tgt=target, success=True):
        src, out = art / (name + ".kotoba"), art / (name + ".elf")
        src.write_text(source)
        s_, o_ = (src.name, out.name) if mac else (str(src), str(out))
        argv = [str(prod), "compile", s_, "--target", tgt, "--output", o_] + (["--format", fmt] if fmt else [])
        z = subprocess.run(argv, cwd=art, env=cenv, capture_output=True, timeout=900, pass_fds=(3,) if mac else ())
        (art / (name + ".compile.stdout")).write_bytes(z.stdout)
        (art / (name + ".compile.stderr")).write_bytes(z.stderr)
        calls.append(dict(name=name, format=fmt, target=tgt, exit=z.returncode))
        if success:
            assert z.returncode == 0 and not z.stderr and b":ok true" in z.stdout, (name, z.returncode, z.stderr[-400:])
            out.chmod(0o755)
        return out, z

    def test_source(*names):
        return NS + helpers + "".join(l for name in names for l in (TESTS / name).read_text().splitlines(True)
                                      if not l.startswith("(ns "))

    rows = dict(structure={}, refusals={})
    images = {}
    for name, files, exports in (("hello", ["image_hello_t.kotoba"], []), ("mem", ["image_mem_t.kotoba"], []),
                                 ("abi", ["image_abi_common.kotoba", T["abi"]], EXPORTS)):
        img, z = compile_(producer, name, test_source(*files))
        assert b":format :b2" in z.stdout, z.stdout
        facts = structure(img, exports, target)
        images[name] = img
        rows["structure"][name] = dict(image=pin(img), exports=len(exports), table=facts["table"])
    rows["structure"]["abi"]["thunks"] = structure(images["abi"], EXPORTS, target)["exports"]
    # the checker's negative control: a damaged thunk, a wrong name and a wrong context word must each fail
    data = (art / "abi.elf").read_bytes()
    _, e = elf(images["abi"])
    t = struct.unpack_from("<Q", data, e["phdrs"][1]["offset"] + 416)[0] - 0x400000
    first = struct.unpack_from("<Q", data, t + 8)[0] - 0x400000
    controls = {}
    # x86_64: ret -> ret imm16, the fuel immediate; aarch64: the ret word's register field, the movz x16 of the fuel
    epilogue, fuel_byte = ((first + thunk_size(0) - 1, 0xC2), first + 27) if target == "x86_64-linux" else \
        ((first + a64_thunk_size(0) - 4, 0x00), first + 4 * 9 + 1)
    for tag, damage in (("thunk-epilogue", lambda b: b.__setitem__(epilogue[0], epilogue[1])),
                        ("thunk-fuel", lambda b: b.__setitem__(fuel_byte, b[fuel_byte] ^ 1)),
                        ("export-name", lambda b: b.__setitem__(struct.unpack_from("<Q", b, t + 16)[0] - 0x400000, 0x41)),
                        ("context-mode", lambda b: b.__setitem__(e["phdrs"][1]["offset"] + 408, 3))):
        bad = bytearray(data)
        damage(bad)
        (art / f"abi-damaged-{tag}.elf").write_bytes(bytes(bad))
        try:
            structure(art / f"abi-damaged-{tag}.elf", EXPORTS, target)
        except AssertionError:
            controls[tag] = "refused"
        else:
            raise AssertionError("the structure check accepted a damaged image: " + tag)
    rows["structure"]["negativeControls"] = controls
    # refusals
    f = "(ns g (:export [main]))\n"
    _, z = compile_(producer, "refuse-runtime", f + "(defn main [] :i64 (kxrt-exit 3))\n", success=False)
    assert z.returncode != 0 and b"E7101" in z.stderr and not (art / "refuse-runtime.elf").exists(), z.stderr[-300:]
    rows["refusals"]["runtime-call-outside-the-api"] = "E7101"
    _, z = compile_(producer, "refuse-b-api-static", f + "(defn main [] :i64 (kxrt-b-alloc 4096))\n", fmt="static", success=False)
    assert z.returncode != 0 and b"E2101" in z.stderr and not (art / "refuse-b-api-static.elf").exists(), z.stderr[-300:]
    rows["refusals"]["api-in-format-static"] = "E2101 (the name is not defined outside --format b2)"
    for tag, body in (("string-parameter", "(defn- cx-bad [s :string] :i64 0)"), ("empty-name", "(defn- cx- [a :i64] :i64 0)"),
                      ("empty-version", "(defn- cx-name- [a :i64] :i64 0)"),
                      ("seventeen-parameters", "(defn- cx-wide [" + " ".join(f"a{i} :i64" for i in range(17)) + "] :i64 0)")):
        _, z = compile_(producer, "refuse-export-" + tag, f + body + "\n(defn main [] :i64 0)\n", success=False)
        code = b"E2178" if tag == "seventeen-parameters" else b"E7102"
        assert z.returncode != 0 and code in z.stderr and not (art / ("refuse-export-" + tag + ".elf")).exists(), (tag, z.stderr[-300:])
        rows["refusals"]["export-" + tag] = code.decode()
    # a cx- function outside --format b2 is an ordinary function
    plain = f + "(defn- cx-thing-V [a :i64] :i64 (+ a 1))\n(defn main [] :i64 (cx-thing-V 6))\n"
    a, _ = compile_(producer, "cx-static", plain, fmt="static")
    b, _ = compile_(producer, "dx-static", plain.replace("cx-thing-V", "dx-thing-V"), fmt="static")
    assert a.read_bytes() == b.read_bytes(), "a cx- name changes nothing outside --format b2"
    rows["cxOutsideB2"] = pin(a)
    if previous:
        old = art / "previous-compiler.elf"
        old.write_bytes(previous.read_bytes())
        old.chmod(0o755)
        same = {}
        for tgt, fmt, src in (("x86_64-linux", "static", plain), ("x86_64-linux", "kx64-runner", (ROOT / "seed/x86_64-kx64-runner.kotoba").read_text()),
                              ("x86_64-linux", "launcher", (ROOT / "tools/static_launcher.kotoba").read_text()),
                              ("aarch64-linux", "static", plain), ("aarch64-linux", "launcher", (ROOT / "tools/static_launcher.kotoba").read_text())):
            tag = f"{tgt}-{fmt}"
            x, _ = compile_(producer, "same-new-" + tag, src, fmt=fmt, tgt=tgt)
            y, z = compile_(old, "same-old-" + tag, src, fmt=fmt, tgt=tgt, success=False)
            assert z.returncode == 0 and x.read_bytes() == y.read_bytes(), ("output changed", tag)
            same[tag] = pin(x)
        _, z = compile_(old, "previous-refuses", plain, tgt=target, success=False)
        rows["unchangedFormats"] = dict(previousCompiler=pin(previous), sameBytes=same,
                                        previousCompilerRefusesFormat=z.returncode != 0 and not (art / "previous-refuses.elf").exists())
        assert rows["unchangedFormats"]["previousCompilerRefusesFormat"], "the previous compiler must not have --format b2"
    if mac:
        os.close(root)
    report = dict(status="PASS_B2_IMAGE_BUILD", target=target, compiler=pin(compiler),
                  host=[platform.system(), platform.machine(), platform.release()],
                  sources={p: pin(ROOT / p) for p in T["sources"] + ("tools/b2/tests/" + T["abi"], "tools/b2/tests/" + T["arch"])},
                  images={k: str(v.relative_to(output)) for k, v in images.items()}, results=rows, calls=calls, cCompilerOrLoader=False)
    (output / "b2-image.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], len(rows["structure"]), "image structures", len(rows["refusals"]), "refusals", flush=True)


def run(output):
    report = json.loads((output / "b2-image.json").read_text())
    T = TARGETS[report.get("target", "x86_64-linux")]
    assert platform.system() == "Linux" and platform.machine() in T["hosts"], "run phase: a Linux kernel of the target's architecture"
    img = {k: output / v for k, v in report["images"].items()}
    raw = output / "run"
    raw.mkdir(exist_ok=False)
    env = {"PATH": "/usr/bin:/bin"}
    rows = {}

    def go(name, argv, extra=None, want=0):
        z = subprocess.run([str(a) for a in argv], env=dict(env, **(extra or {})), capture_output=True, timeout=300)
        (raw / (name + ".stdout")).write_bytes(z.stdout)
        (raw / (name + ".stderr")).write_bytes(z.stderr)
        assert z.returncode == want, (name, z.returncode, z.stdout[-300:], z.stderr[-300:])
        rows[name] = dict(exit=z.returncode, stdout=z.stdout.decode(errors="replace")[-400:])
        return z

    z = go("hello", [img["hello"]], want=7)
    assert z.stdout == b"hello b2\n" and not z.stderr, z.stdout
    z = go("hello-argc", [img["hello"], "x", "y"], want=9)
    z = go("mem", [img["mem"]], want=0)
    assert z.stdout == b"0\n", z.stdout
    z = go("abi", [img["abi"]])
    assert z.stdout.decode().splitlines() == T["lines"], z.stdout
    z = go("abi-alignment-control", [img["abi"], "align-control"], want=T["align_signal"])
    assert z.stdout == b"", "the misaligned call must fault before the probe reports"
    z = go("fuel-own-budget", [img["abi"], "fuel-ok"], {"KEXE_FUEL": "1000000"})
    assert z.stdout == b"3000000\n", z.stdout
    z = go("fuel-caller-meter-restored", [img["abi"], "fuel-trap"], {"KEXE_FUEL": "1000000"}, want=T["fuel_signal"])
    assert z.stdout == b"3000000\n", z.stdout
    z = go("fuel-unmetered", [img["abi"], "fuel-trap"], want=0)
    assert z.stdout == b"3000000\n", z.stdout
    report["run"] = dict(host=[platform.system(), platform.machine(), platform.release()], rows=rows,
                         notRun=["the libvulkan image: GPU hosts only (tools/b2/90-vk-probe.kotoba, check-b2-libvulkan.py)"])
    report["status"] = "PASS_B2_IMAGE_BUILD_AND_RUN"
    (output / "b2-image.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], len(rows), "runs", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("phase", nargs="?", choices=["build", "run", "all"], default="all")
    parser.add_argument("--compiler", type=Path, help="build: an Amu-produced compiler from these sources")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--previous-compiler", type=Path, help="build: a compiler from before this format (byte identity of the other formats)")
    parser.add_argument("--target", choices=sorted(TARGETS), default="x86_64-linux", help="build: the images' target")
    args = parser.parse_args()
    if args.phase in ("build", "all"):
        assert args.compiler, "--compiler is required to build"
        build(args.compiler.resolve(), args.output.resolve(), args.previous_compiler.resolve() if args.previous_compiler else None,
              args.target)
    if args.phase in ("run", "all"):
        run(args.output.resolve())
