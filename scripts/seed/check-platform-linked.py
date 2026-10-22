#!/usr/bin/env python3
"""The platform-linked image (--format platform-linked, ADR 0371 step 5).

--compiler is an Amu-produced static compiler from the current sources
(S3.elf of selfhost-bootstrap.py, X2 on x86_64, or the re-pinned root); it
runs on this host and writes x86_64 images.

Phase "build" (any Linux):
* images: hello, arguments, the platform API (alloc, load, store, ccall), a
  GOT write (the RELRO control), and a program that calls kxrt-p-vkgipa;
* structure, parsed from the bytes: the 7 program headers in order, the
  interpreter, W^X, the dynamic section's exact tag set (no PLT, TEXTREL,
  DEBUG, RPATH, INIT or FINI), DF_BIND_NOW and DF_1_NOW, NEEDED and the
  imported symbols against the allowlist (libc.so.6 __libc_start_main;
  libvulkan.so.1 vkGetInstanceProcAddr only for kxrt-p-vkgipa), and GLOB_DAT
  relocations inside the RELRO page;
* the ABI image: a test-only compiler (in memory, never written to seed/)
  whose import 1 is libc's snprintf; the allowlist check must refuse that
  image (the checker's negative control);
* refusals: a program calling a runtime function outside the kxrt-p- block
  (E7101), the platform API in --format static (unresolved), and the format
  on aarch64-linux (E7100);
* with --previous-root: the static, runner and launcher outputs are the same
  bytes as the previous root's.

Phase "run" (x86_64 Linux with glibc's /lib64/ld-linux-x86-64.so.2; native,
or emulated by qemu-user): hello (exit 7, and the structured line), the
arguments, snprintf through kxrt-p-ccall with 14 arguments (6 registers and
8 stack words, varargs), and the RELRO control (SIGSEGV). On a native kernel
also a provider skeleton: a platform-linked Kotoba program that answers INFO
on fds 0/1 and reports on fd 4, started by the static launcher with a guest
that calls wire 42. (Through binfmt_misc the launcher cannot start an image:
execveat of a close-on-exec memfd, ENOENT.)

The libvulkan image is never executed here: the owner decided (2026-10-22)
that the libvulkan probe runs on GPU hosts only. libc-only images may run in
the native x86_64 CI job. Python only orchestrates processes and parses bytes.
  podman run --platform linux/arm64 ... python3 check-platform-linked.py build --compiler S3.elf --output OUT
  podman run --platform linux/amd64 (glibc image) ... python3 check-platform-linked.py run --output OUT
  python3 check-platform-linked.py all --compiler X2.elf --output OUT   (x86_64 host)
"""
import argparse
import hashlib
import json
import platform
import shutil
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELFHOST = "seed/X86_64-LINUX-SELFHOST-MANIFEST"
INTERP = "/lib64/ld-linux-x86-64.so.2"
ALLOWED = {"__libc_start_main": "libc.so.6", "vkGetInstanceProcAddr": "libvulkan.so.1"}
PT = {1: "LOAD", 2: "DYNAMIC", 3: "INTERP", 6: "PHDR", 0x6474E551: "GNU_STACK", 0x6474E552: "GNU_RELRO"}
DT = {0: "NULL", 1: "NEEDED", 4: "HASH", 5: "STRTAB", 6: "SYMTAB", 7: "RELA", 8: "RELASZ", 9: "RELAENT",
      10: "STRSZ", 11: "SYMENT", 30: "FLAGS", 0x6FFFFFFB: "FLAGS_1"}
TEST_ONLY = [
    ('(defn- xp-import-name [k :i64] :string (case k 0 "__libc_start_main" 1 "vkGetInstanceProcAddr" ""))',
     '(defn- xp-import-name [k :i64] :string (case k 0 "__libc_start_main" 1 "snprintf" ""))'),
    ("(defn- xp-import-lib [k :i64] :i64 (case k 0 0 1 1 -1))", "(defn- xp-import-lib [k :i64] :i64 (case k 0 0 1 0 -1))"),
]
API = ('(defn- put-str [a :i64 s :string] :i64\n'
       '  (let [n (string-length s)\n'
       '        z (loop [i 0] (if (= i n) 0 (let [w (kxrt-p-store8 (+ a i) (string-code-point-at s i))] (recur (inc i)))))]\n'
       '    (kxrt-p-store8 (+ a n) 0)))\n'
       '(defn- cstr [a :i64] :string\n'
       '  (string-from-utf8 (bytes-from-vector-i64\n'
       '    (loop [i 0 v []] (let [c (kxrt-p-load8 (+ a i))] (if (= c 0) v (recur (inc i) (conj v c))))))))\n'
       '(defn- say [s :string] :i64 (let [w (typed-cap-call :io/write :string :string (string-concat s "\\n"))] 0))\n')
GUESTS = {
    "hello": '(ns g (:export [main]))\n(defn main [] :i64 (let [w (typed-cap-call :io/write :string :string "hello\\n")] 7))\n',
    "args": ('(ns g (:export [main]))\n(defn- arg [i :string] :string (typed-cap-call :cli/args :string :string i))\n'
             '(defn main [] :i64 (let [w (typed-cap-call :io/write :string :string (string-concat (arg "")'
             ' (string-concat "|" (string-concat (arg "0") (string-concat "|" (string-concat (arg "1") "\\n"))))))] 0))\n'),
    # snprintf(buf, 256, fmt, 1 .. 11): 14 arguments through kxrt-p-ccall; import 1 is
    # snprintf only in the test-only compiler
    "abi": ('(ns g (:export [main]))\n' + API +
            '(defn main [] :i64\n'
            '  (let [m (kxrt-p-alloc 4096) buf m fmt (+ m 1024) argv (+ m 2048)\n'
            '        f (put-str fmt "%ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld")\n'
            '        a (kxrt-p-store64 argv buf) b (kxrt-p-store64 (+ argv 8) 256) c (kxrt-p-store64 (+ argv 16) fmt)\n'
            '        v (loop [k 0] (if (= k 11) 0 (let [w (kxrt-p-store64 (+ argv (* 8 (+ 3 k))) (+ k 1))] (recur (inc k)))))\n'
            '        n (bit-and (kxrt-p-ccall (kxrt-p-vkgipa) argv) 4294967295)\n'
            '        s (say (cstr buf))]\n'
            '    n))\n'),
    "relro": '(ns g (:export [main]))\n(defn main [] :i64 (kxrt-p-store64 (kxrt-p-got-slot 0) 0))\n',
    "vk": '(ns g (:export [main]))\n(defn main [] :i64 (if (= (kxrt-p-vkgipa) 0) 1 0))\n',
    "refuse-runtime": '(ns g (:export [main]))\n(defn main [] :i64 (kxrt-exit 3))\n',
    # a provider skeleton: frames on fds 0 (requests) and 1 (answers), the report on fd 4
    "provider": ('(ns p (:export [main]))\n' + API +
                 '(defn- read-full [fd :i64 a :i64 n :i64] :i64\n'
                 '  (loop [k 0] (if (>= k n) k (let [r (kxrt-p-read fd (+ a k) (- n k))] (if (<= r 0) k (recur (+ k r)))))))\n'
                 '(defn- u32-at [a :i64] :i64\n'
                 '  (bit-or (kxrt-p-load8 a) (bit-or (i64-shift-left (kxrt-p-load8 (+ a 1)) 8)\n'
                 '    (bit-or (i64-shift-left (kxrt-p-load8 (+ a 2)) 16) (i64-shift-left (kxrt-p-load8 (+ a 3)) 24)))))\n'
                 '(defn- frame [m :i64 s :string] :i64\n'
                 '  (let [n (string-length s) a (kxrt-p-store8 m n) b (kxrt-p-store8 (+ m 1) 0) c (kxrt-p-store8 (+ m 2) 0)\n'
                 '        d (kxrt-p-store8 (+ m 3) 0) e (put-str (+ m 4) s)]\n'
                 '    (kxrt-p-write 1 m (+ n 4))))\n'
                 '(defn main [] :i64\n'
                 '  (let [m (kxrt-p-alloc 65536) out (+ m 32768)\n'
                 '        served (loop [k 0]\n'
                 '                 (if (< (read-full 0 m 4) 4) k\n'
                 '                   (let [n (u32-at m) b (read-full 0 (+ m 8) n) z (kxrt-p-store8 (+ m 8 n) 0)\n'
                 '                         w (frame out (if (string=? (cstr (+ m 8)) "INFO") "Kotoba platform-linked provider|none|0|0" "!gpu/unknown-verb unknown :gpu/compute request"))]\n'
                 '                     (recur (inc k)))))\n'
                 '        r (put-str out (string-concat "served " (string-from-i64 served)))]\n'
                 '    (bit-and (kxrt-p-write 4 out (+ 7 (string-length (string-from-i64 served)))) 0)))\n'),
    "gpu-guest": '(ns g (:export [main]))\n(defn main [] :i64 (string-length (typed-cap-call 42 :string :string "INFO")))\n',
}
PROVIDER_ANSWER = b"Kotoba platform-linked provider|none|0|0"


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def elf(path):
    """Parse what the checks need from a platform-linked image."""
    d = Path(path).read_bytes()
    assert d[:4] == b"\x7fELF" and d[4] == 2 and d[5] == 1, "ELF64 LE"
    e_type, e_machine, _, entry, phoff = struct.unpack_from("<HHIQQ", d, 16)
    phentsize, phnum = struct.unpack_from("<HH", d, 54)
    ph = [dict(zip(("type", "flags", "offset", "vaddr", "paddr", "filesz", "memsz", "align"),
                   struct.unpack_from("<IIQQQQQQ", d, phoff + i * phentsize))) for i in range(phnum)]
    interp = next(p for p in ph if p["type"] == 3)
    dyn_ph = next(p for p in ph if p["type"] == 2)
    dyn = [struct.unpack_from("<qQ", d, dyn_ph["offset"] + 16 * i) for i in range(dyn_ph["filesz"] // 16)]
    tags = [t for t, _ in dyn]
    val = {t: v for t, v in dyn if t != 1}

    def off(vaddr):
        return vaddr - 0x400000

    strtab = d[off(val[5]):off(val[5]) + val[10]]

    def cstr(o):
        return strtab[o:strtab.index(b"\0", o)].decode()

    nchain = struct.unpack_from("<II", d, off(val[4]))
    syms = [struct.unpack_from("<IBBHQQ", d, off(val[6]) + 24 * i) for i in range(nchain[1])]
    relas = [struct.unpack_from("<QQq", d, off(val[7]) + 24 * i) for i in range(val[8] // 24)]
    return dict(type=e_type, machine=e_machine, entry=entry, phdrs=ph,
                interp=d[interp["offset"]:interp["offset"] + interp["filesz"]].rstrip(b"\0").decode(),
                tags=tags, flags=val.get(30), flags1=val.get(0x6FFFFFFB), hash=nchain,
                needed=[cstr(v) for t, v in dyn if t == 1],
                symbols=[(cstr(s[0]), s[1], s[3]) for s in syms[1:]],
                relas=[(r[0], r[1] & 0xFFFFFFFF, r[1] >> 32, r[2]) for r in relas])


def structure(path, imports):
    """Every structural rule; imports is the expected import list. Returns the parsed facts."""
    e = elf(path)
    order = [PT.get(p["type"]) for p in e["phdrs"]]
    assert (e["type"], e["machine"], e["entry"]) == (2, 62, 0x401000), e
    assert order == ["PHDR", "INTERP", "LOAD", "LOAD", "DYNAMIC", "GNU_RELRO", "GNU_STACK"], order
    assert e["interp"] == INTERP, e["interp"]
    assert all(not (p["flags"] & 2 and p["flags"] & 1) for p in e["phdrs"]), "W^X"
    rx, rw, dyn, relro, stack = e["phdrs"][2], e["phdrs"][3], e["phdrs"][4], e["phdrs"][5], e["phdrs"][6]
    assert rx["flags"] == 5 and rx["offset"] == 0 and rw["flags"] == 6 and stack["flags"] == 6, e["phdrs"]
    assert dyn["offset"] == rw["offset"] == relro["offset"] and relro["filesz"] == 4096 and rw["offset"] % 4096 == 0
    assert sorted(set(e["tags"])) == sorted(DT) and e["tags"][-1] == 0 and e["tags"].count(0) == 1, \
        ("dynamic tags", [DT.get(t, hex(t)) for t in e["tags"]])
    assert e["flags"] == 8 and e["flags1"] == 1, "DF_BIND_NOW, DF_1_NOW"
    names = [s[0] for s in e["symbols"]]
    assert names == imports and all(s[1] == 0x12 and s[2] == 0 for s in e["symbols"]), e["symbols"]
    assert e["needed"] == sorted({ALLOWED.get(n, "libc.so.6") for n in imports}, key=["libc.so.6", "libvulkan.so.1"].index), e["needed"]
    assert e["hash"] == (1, len(imports) + 1), e["hash"]
    lo, hi = relro["vaddr"], relro["vaddr"] + relro["memsz"]
    assert len(e["relas"]) == len(imports) and all(t == 6 and a == 0 and lo + 2048 <= o < hi for o, t, s, a in e["relas"]), e["relas"]
    assert sorted(s for _, _, s, _ in e["relas"]) == list(range(1, len(imports) + 1))
    return e


def allowlisted(e):
    return all(n in ALLOWED and ALLOWED[n] in e["needed"] for n, _, _ in e["symbols"]) and \
        set(e["needed"]) <= set(ALLOWED.values())


def build(compiler, output, previous_root):
    assert platform.system() == "Linux", "run on Linux"
    host = {"aarch64": "aarch64-linux", "arm64": "aarch64-linux", "x86_64": "x86_64-linux", "AMD64": "x86_64-linux"}[platform.machine()]
    output.mkdir(parents=True, exist_ok=False)
    art = output / "artifacts"
    art.mkdir()
    producer = art / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)
    calls = []
    cenv = {"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art)}

    def compile_(prod, name, source, fmt="platform-linked", tgt="x86_64-linux", success=True):
        src, out = art / (name + ".kotoba"), art / (name + ".elf")
        src.write_text(source)
        z = subprocess.run([str(prod), "compile", str(src), "--target", tgt, "--output", str(out), "--format", fmt],
                           cwd=art, env=cenv, capture_output=True, timeout=900)
        (art / (name + ".compile.stdout")).write_bytes(z.stdout)
        (art / (name + ".compile.stderr")).write_bytes(z.stderr)
        calls.append(dict(name=name, format=fmt, target=tgt, exit=z.returncode))
        if success:
            assert z.returncode == 0 and not z.stderr and b":ok true" in z.stdout, (name, z.returncode, z.stderr[-400:])
            out.chmod(0o755)
        return out, z

    rows = dict(structure={}, refusals={})
    images = {}
    for name, imports in (("hello", ["__libc_start_main"]), ("args", ["__libc_start_main"]), ("relro", ["__libc_start_main"]),
                          ("provider", ["__libc_start_main"]), ("vk", ["__libc_start_main", "vkGetInstanceProcAddr"])):
        img, z = compile_(producer, name, GUESTS[name])
        e = structure(img, imports)
        assert allowlisted(e) and (b":libvulkan true" in z.stdout) == ("vkGetInstanceProcAddr" in imports), (name, z.stdout)
        images[name] = img
        rows["structure"][name] = dict(image=pin(img), needed=e["needed"], imports=imports)
    # the ABI image: a test-only compiler whose import 1 is libc's snprintf
    paths = [p for p in (ROOT / SELFHOST).read_text().splitlines() if p and not p.startswith("#")]
    unity = "".join((ROOT / p).read_text() + "\n" for p in paths)
    for old, new in TEST_ONLY:
        assert unity.count(old) == 1, old
        unity = unity.replace(old, new)
    test_compiler, _ = compile_(producer, "test-compiler-snprintf", unity, fmt="static", tgt=host)
    images["abi"], _ = compile_(test_compiler, "abi", GUESTS["abi"])
    e = structure(images["abi"], ["__libc_start_main", "snprintf"])
    assert not allowlisted(e), "the allowlist check must refuse an image importing snprintf"
    rows["structure"]["abi"] = dict(image=pin(images["abi"]), needed=e["needed"], imports=["__libc_start_main", "snprintf"],
                                    testOnlyCompiler="import 1 replaced by libc snprintf in memory; never written to seed/",
                                    allowlistRefuses=True)
    # refusals
    _, z = compile_(producer, "refuse-runtime", GUESTS["refuse-runtime"], success=False)
    assert z.returncode != 0 and b"E7101" in z.stderr and not (art / "refuse-runtime.elf").exists(), z.stderr[-300:]
    rows["refusals"]["runtime-call-outside-the-api"] = "E7101"
    _, z = compile_(producer, "refuse-static-api", GUESTS["relro"], fmt="static", success=False)
    assert z.returncode != 0 and not (art / "refuse-static-api.elf").exists(), z.stderr[-300:]
    rows["refusals"]["api-in-format-static"] = z.stderr.decode(errors="replace").replace(str(art) + "/", "").strip()[-160:]
    _, z = compile_(producer, "refuse-aarch64", GUESTS["hello"], tgt="aarch64-linux", success=False)
    assert z.returncode == 2 and b"E7100" in z.stderr, z.stderr[-300:]
    rows["refusals"]["format-on-aarch64-linux"] = "E7100"
    # the launcher and the guest for the provider skeleton
    images["launcher"], _ = compile_(producer, "launcher", (ROOT / "tools/static_launcher.kotoba").read_text(), fmt="launcher")
    images["gpu-guest"], _ = compile_(producer, "gpu-guest", GUESTS["gpu-guest"], fmt="static")
    if previous_root:
        old = art / "previous-root.elf"
        old.write_bytes(previous_root.read_bytes())
        old.chmod(0o755)
        same = {}
        for tgt, fmt, src in (("x86_64-linux", "static", GUESTS["hello"]), ("x86_64-linux", "kx64-runner", (ROOT / "seed/x86_64-kx64-runner.kotoba").read_text()),
                              ("x86_64-linux", "launcher", (ROOT / "tools/static_launcher.kotoba").read_text()),
                              ("aarch64-linux", "static", GUESTS["hello"]), ("aarch64-linux", "launcher", (ROOT / "tools/static_launcher.kotoba").read_text())):
            tag = f"{tgt}-{fmt}"
            a, _ = compile_(producer, "same-new-" + tag, src, fmt=fmt, tgt=tgt)
            b, _ = compile_(old, "same-old-" + tag, src, fmt=fmt, tgt=tgt)
            assert a.read_bytes() == b.read_bytes(), ("output changed", tag)
            same[tag] = pin(a)
        _, z = compile_(old, "previous-refuses", GUESTS["hello"], success=False)
        assert z.returncode != 0 and not (art / "previous-refuses.elf").exists(), z.stderr[-200:]
        rows["unchangedFormats"] = dict(previousRoot=pin(previous_root), sameBytes=same, previousRootRefusesFormat=True)
    report = dict(status="PASS_PLATFORM_LINKED_BUILD", compiler=pin(compiler), host=[platform.system(), platform.machine(), platform.release()],
                  sources={p: pin(ROOT / p) for p in ("seed/78-x86_64-platform.kotoba", "seed/75-x86_64-static.kotoba", "seed/76-x86_64-static-rt.kotoba")},
                  images={k: str(v.relative_to(output)) for k, v in images.items()}, results=rows, calls=calls, cCompilerOrLoader=False)
    (output / "platform-linked.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], len(rows["structure"]), "images", len(rows["refusals"]), "refusals", flush=True)


def native_kernel():
    """True on an x86_64 kernel. Under qemu-user /proc/cpuinfo is the host's (no x86 vendor)."""
    try:
        info = Path("/proc/cpuinfo").read_text()
    except OSError:
        return False
    return "GenuineIntel" in info or "AuthenticAMD" in info


def run(output):
    assert platform.system() == "Linux" and platform.machine() in ("x86_64", "AMD64"), "run phase: x86_64 Linux (native or qemu-user)"
    assert Path(INTERP).exists(), "glibc's dynamic linker is needed: " + INTERP
    report = json.loads((output / "platform-linked.json").read_text())
    img = {k: output / v for k, v in report["images"].items()}
    raw = output / "run"
    raw.mkdir(exist_ok=False)
    env = {"PATH": "/usr/bin:/bin"}
    rows = {}

    def go(name, argv, extra=None, want=0):
        z = subprocess.run([str(a) for a in argv], env=dict(env, **(extra or {})), capture_output=True, timeout=120)
        (raw / (name + ".stdout")).write_bytes(z.stdout)
        (raw / (name + ".stderr")).write_bytes(z.stderr)
        assert z.returncode == want, (name, z.returncode, z.stdout[-300:], z.stderr[-300:])
        rows[name] = dict(exit=z.returncode, stdout=z.stdout.decode(errors="replace")[-300:])
        return z

    z = go("hello", [img["hello"]], want=7)
    assert z.stdout == b"hello\n" and not z.stderr, z.stdout
    z = go("hello-structured", [img["hello"]], {"KEXE_STRUCTURED_REPORT": "1"})
    assert z.stdout.startswith(b"hello\n{:status :ok :result 7 "), z.stdout
    z = go("args", [img["args"], "first", "second"])
    assert z.stdout == b"2|first|second\n", z.stdout
    z = go("abi-snprintf-14-arguments", [img["abi"]], want=23)
    assert z.stdout == b"1 2 3 4 5 6 7 8 9 10 11\n", z.stdout
    z = go("relro-control", [img["relro"]], want=-11)
    native = native_kernel()
    gl = shutil.which("ldd")
    if gl:
        z = subprocess.run([gl, str(img["hello"])], capture_output=True, text=True)
        rows["ldd-hello"] = z.stdout.strip()
    if native:
        grant = raw / "grant.edn"
        grant.write_bytes(b"{:wires #{42} :artifacts [] :device-bytes 0}\n")
        z = go("provider-skeleton-under-the-launcher",
               [img["launcher"], "10", "37,38,39,42", grant, img["provider"], "--", img["gpu-guest"]])
        line = z.stdout[z.stdout.rindex(b"{:receipt "):].decode()
        assert ":verdict :ok" in line and f":result {len(PROVIDER_ANSWER)} " in line and ':report "served 1"' in line, line
        rows["provider-skeleton-under-the-launcher"]["receipt"] = line.strip()
    report["run"] = dict(host=[platform.system(), platform.machine(), platform.release()], nativeKernel=native,
                         glibc=subprocess.run(["ldd", "--version"], capture_output=True, text=True).stdout.splitlines()[0] if gl else None,
                         rows=rows, notRun=([] if native else ["provider skeleton under the launcher: binfmt_misc cannot start a close-on-exec memfd image (native kernels only)"])
                         + ["the libvulkan image: GPU hosts only (owner decision 2026-10-22)"])
    report["status"] = "PASS_PLATFORM_LINKED_BUILD_AND_RUN"
    (output / "platform-linked.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], "native" if native else "emulated", len(rows), "runs", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("phase", nargs="?", choices=["build", "run", "all"], default="all")
    parser.add_argument("--compiler", type=Path, help="build: an Amu-produced static compiler from these sources")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--previous-root", type=Path, help="build: the root from before this format (byte identity of the others)")
    args = parser.parse_args()
    if args.phase in ("build", "all"):
        assert args.compiler, "--compiler is required to build"
        build(args.compiler.resolve(), args.output.resolve(), args.previous_root.resolve() if args.previous_root else None)
    if args.phase in ("run", "all"):
        run(args.output.resolve())
