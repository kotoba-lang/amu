#!/usr/bin/env python3
"""Route B2, slice 1 (ADR 0375, JUN-377): the system libvulkan.so.1 through the Kotoba loader. GPU hosts only.

The unit tools/b2 (the Kotoba loader and the libc subset) is compiled with --compiler (--format b2) and the image
is run on this host. It maps /usr/lib/.../libvulkan.so.1 itself (no ld.so, no glibc is loaded into the image),
binds the library's imports to the libc subset, runs its initializers, and calls vkEnumerateInstanceVersion and
vkEnumerateInstanceExtensionProperties. No ICD is loaded: the loader refuses each ICD's dlopen by name.

Checked, with the receipt written to --output/b2-libvulkan.json:
* the library's import table, parsed from its section headers (dynsym, versym, verneed): every undefined symbol
  is either exported by the image at the version the library requires, the data object stderr, a weak
  reference (bound to 0), or one of the declared stubs (pow: a refusal by name that is not reached);
* the image's own export table is read from its bytes, not from the source;
* the run: exit 0, the program's lines, `stubs for unresolved imports` equal to the declared stubs, the five
  /proc/self/maps lines of the library (paths and offsets from the file, permissions from its program headers,
  RELRO read-only), the instance version equal to the file's version, results 0;
* an independent oracle, only to compare results (not part of the product route): the same two calls made through
  the system's own ld.so and glibc (Python ctypes) with the drivers hidden (VK_DRIVER_FILES names a file that
  does not exist), which must give the same version, count and extension names and spec versions as the
  image under the same environment, and as the image under the default environment (where each ICD's dlopen is
  refused: the log shows every manifest found and every refusal);
* the negative control: the same image with VK_LOADER_DEBUG=error,driver shows the loader reading each manifest through the
  libc subset (opendir, fopen, fread, sscanf) and the refusal of each library.

  python3 check-b2-libvulkan.py --compiler F.elf --output OUT [--libvulkan PATH]      (gad or the B70)
"""
import argparse
import hashlib
import importlib.util
import json
import platform
import re
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
B2 = ROOT / "tools/b2"
NS = "(ns g (:export [main]))\n"
PATHS = ["/usr/lib/x86_64-linux-gnu/libvulkan.so.1", "/lib/x86_64-linux-gnu/libvulkan.so.1", "/usr/lib64/libvulkan.so.1"]
DECLARED_STUBS = {"pow"}
DATA_SYMBOLS = {"stderr"}
ORACLE = r'''
import ctypes
lib = ctypes.CDLL("libvulkan.so.1")
v = ctypes.c_uint32(0)
r = lib.vkEnumerateInstanceVersion(ctypes.byref(v))
print("version", ctypes.c_int32(r).value, (v.value >> 22) & 127, (v.value >> 12) & 1023, v.value & 4095)
cnt = ctypes.c_uint32(0)
r1 = lib.vkEnumerateInstanceExtensionProperties(None, ctypes.byref(cnt), None)
print("count", ctypes.c_int32(r1).value, cnt.value)
buf = ctypes.create_string_buffer(260 * max(cnt.value, 1))
r2 = lib.vkEnumerateInstanceExtensionProperties(None, ctypes.byref(cnt), buf)
print("list", ctypes.c_int32(r2).value, cnt.value)
for i in range(cnt.value):
    print("ext", buf.raw[260 * i:260 * i + 256].split(b"\0")[0].decode(), int.from_bytes(buf.raw[260 * i + 256:260 * i + 260], "little"))
'''


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, path
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sections(d):
    shoff, = struct.unpack_from("<Q", d, 40)
    shentsize, shnum = struct.unpack_from("<HH", d, 58)
    rows = [struct.unpack_from("<IIQQQQIIQQ", d, shoff + i * shentsize) for i in range(shnum)]
    return [dict(name=r[0], type=r[1], addr=r[3], offset=r[4], size=r[5], link=r[6], info=r[7], entsize=r[9]) for r in rows]


def cstr(d, o):
    return d[o:d.index(b"\0", o)].decode()


def imports(path):
    """The undefined dynamic symbols of an ELF: name, type, bind, required version (from versym and verneed)."""
    d = Path(path).read_bytes()
    sec = sections(d)
    dynsym = next(s for s in sec if s["type"] == 11)
    strtab = sec[dynsym["link"]]
    versym = next((s for s in sec if s["type"] == 0x6FFFFFFF), None)
    verneed = next((s for s in sec if s["type"] == 0x6FFFFFFE), None)
    names = {}
    if verneed:
        o = verneed["offset"]
        for _ in range(verneed["info"]):
            vn_cnt, = struct.unpack_from("<H", d, o + 2)
            vn_aux, vn_next = struct.unpack_from("<II", d, o + 8)[0], struct.unpack_from("<I", d, o + 12)[0]
            a = o + vn_aux
            for _ in range(vn_cnt):
                other, = struct.unpack_from("<H", d, a + 6)
                name, nxt = struct.unpack_from("<I", d, a + 8)[0], struct.unpack_from("<I", d, a + 12)[0]
                names[other] = cstr(d, strtab["offset"] + name)
                a += nxt
            o += vn_next
    out = []
    for i in range(1, dynsym["size"] // 24):
        st_name, st_info, _other, st_shndx = struct.unpack_from("<IBBH", d, dynsym["offset"] + 24 * i)
        if st_shndx != 0:
            continue
        idx = struct.unpack_from("<H", d, versym["offset"] + 2 * i)[0] & 0x7FFF if versym else 0
        out.append(dict(name=cstr(d, strtab["offset"] + st_name), type={0: "NOTYPE", 1: "OBJECT", 2: "FUNC"}.get(st_info & 15, str(st_info & 15)),
                        bind={1: "GLOBAL", 2: "WEAK"}.get(st_info >> 4, str(st_info >> 4)), version=names.get(idx, "")))
    return out


def load_segments(path):
    d = Path(path).read_bytes()
    phoff, = struct.unpack_from("<Q", d, 32)
    phentsize, phnum = struct.unpack_from("<HH", d, 54)
    ph = [dict(zip(("type", "flags", "offset", "vaddr", "paddr", "filesz", "memsz", "align"), struct.unpack_from("<IIQQQQQQ", d, phoff + i * phentsize)))
          for i in range(phnum)]
    return [p for p in ph if p["type"] == 1], next((p for p in ph if p["type"] == 0x6474E552), None)


def expected_maps(path):
    """(offset, permissions) of each mapping the loader makes: PT_LOAD pages, the RW segment split at RELRO."""
    loads, relro = load_segments(path)
    down = lambda n: n & -4096
    rows = []
    for p in loads:
        perm = ("r" if p["flags"] & 4 else "-") + ("w" if p["flags"] & 2 else "-") + ("x" if p["flags"] & 1 else "-") + "p"
        off = down(p["offset"])
        if p["flags"] & 2 and relro and down(relro["vaddr"]) == down(p["vaddr"]):
            end = (relro["vaddr"] + relro["memsz"] + 4095) & -4096
            rows.append((off, "r--p"))
            if end < ((p["vaddr"] + p["memsz"] + 4095) & -4096):
                rows.append((off + end - down(p["vaddr"]), perm))
        else:
            rows.append((off, perm))
    return rows


def unit_source():
    text = NS
    for line in (B2 / "MANIFEST").read_text().splitlines():
        if line and not line.startswith("#"):
            text += (ROOT / line).read_text() + "\n"
    return text


def run_image(img, env, args=()):
    z = subprocess.run([str(img), *args], env=env, capture_output=True, timeout=300)
    return z.returncode, z.stdout.decode(errors="replace"), z.stderr.decode(errors="replace")


def parse_run(stdout):
    ver = re.search(r"^vkEnumerateInstanceVersion result=(-?\d+) version=(\d+)\.(\d+)\.(\d+)$", stdout, re.M)
    count = re.search(r"^vkEnumerateInstanceExtensionProperties\(count\) result=(-?\d+) count=(\d+)$", stdout, re.M)
    lst = re.search(r"^vkEnumerateInstanceExtensionProperties\(list\) result=(-?\d+) count=(\d+)$", stdout, re.M)
    exts = re.findall(r"^extension (\S+) (\d+)$", stdout, re.M)
    assert ver and count and lst, stdout
    return dict(version=[int(ver[1]), int(ver[2]), int(ver[3]), int(ver[4])], count=[int(count[1]), int(count[2])],
                list=[int(lst[1]), int(lst[2])], extensions=[[n, int(s)] for n, s in exts])


def parse_oracle(stdout):
    lines = stdout.splitlines()
    v = lines[0].split()
    return dict(version=[int(v[1]), int(v[2]), int(v[3]), int(v[4])], count=[int(lines[1].split()[1]), int(lines[1].split()[2])],
                list=[int(lines[2].split()[1]), int(lines[2].split()[2])],
                extensions=[[ln.split()[1], int(ln.split()[2])] for ln in lines[3:] if ln.startswith("ext ")])


def main(compiler, output, libvulkan):
    assert platform.system() == "Linux" and platform.machine() in ("x86_64", "AMD64"), "an x86_64 Linux GPU host"
    lib = Path(libvulkan or next((p for p in PATHS if Path(p).exists()), "")).resolve()
    assert lib.exists(), "libvulkan.so.1 not found; pass --libvulkan"
    image_check = load_module("check_b2_image", ROOT / "scripts/seed/check-b2-image.py")
    output.mkdir(parents=True, exist_ok=False)
    art = output / "artifacts"
    art.mkdir()
    producer = art / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)
    src, img = art / "b2-vk-probe.kotoba", art / "b2-vk-probe.elf"
    src.write_text(unit_source())
    z = subprocess.run([str(producer), "compile", str(src), "--target", "x86_64-linux", "--output", str(img), "--format", "b2"],
                       cwd=art, env={"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art)}, capture_output=True, timeout=900)
    assert z.returncode == 0 and not z.stderr and b":format :b2" in z.stdout, (z.returncode, z.stderr[-400:])
    img.chmod(0o755)
    # the library's imports against the image's export table
    table = image_check.export_table(img)
    have = {(n, v) for n, v, _ in table}
    names_have = {n for n, _, _ in table}
    imps = imports(lib)
    coverage = []
    for i in imps:
        n, v = i["name"], i["version"]
        if n in DATA_SYMBOLS and i["type"] == "OBJECT":
            how = "data object of the libc subset"
        elif i["bind"] == "WEAK" and n not in names_have:
            how = "weak reference, bound to 0"
        elif (n, v) in have or (n in names_have and v == ""):
            how = "exported by the image"
        elif n in DECLARED_STUBS:
            how = "declared stub: refuses by name when called"
        else:
            raise AssertionError(("an import nothing implements", i))
        coverage.append(dict(i, bound=how))
    stubs = [c["name"] for c in coverage if c["bound"].startswith("declared stub")]
    assert set(stubs) == DECLARED_STUBS, stubs
    base_env = {"PATH": "/usr/bin:/bin"}
    none_dir = output / "no-icd"
    none_dir.mkdir()
    none_env = dict(base_env, VK_DRIVER_FILES=str(none_dir / "does-not-exist.json"))
    runs = {}
    # the image: explicit path, default search, drivers hidden, and the debug log
    rc, out, err = run_image(img, base_env, [str(lib)])
    (output / "run-default.stdout").write_text(out)
    (output / "run-default.stderr").write_text(err)
    assert rc == 0, (rc, out[-500:], err[-500:])
    default = parse_run(out)
    rc2, out2, err2 = run_image(img, none_env)
    (output / "run-no-icd.stdout").write_text(out2)
    (output / "run-no-icd.stderr").write_text(err2)
    assert rc2 == 0, (rc2, out2[-500:], err2[-500:])
    no_icd = parse_run(out2)
    rc3, out3, err3 = run_image(img, dict(base_env, VK_LOADER_DEBUG="error,driver"))
    (output / "run-driver-log.stdout").write_text(out3)
    (output / "run-driver-log.stderr").write_text(err3)
    assert rc3 == 0, (rc3, err3[-500:])
    # the oracle: the same calls through the system's own loader, drivers hidden
    zo = subprocess.run(["python3", "-I", "-c", ORACLE], env=none_env, capture_output=True, timeout=300)
    assert zo.returncode == 0, zo.stderr[-400:]
    (output / "oracle.stdout").write_bytes(zo.stdout)
    oracle = parse_oracle(zo.stdout.decode())
    assert oracle["version"][0] == 0 and oracle["count"][0] == 0 and oracle["list"][0] == 0, oracle
    assert default == no_icd == oracle, ("the image and the system loader differ", default, no_icd, oracle)
    # the version equals the file's name (libvulkan.so.1.3.275)
    m = re.search(r"libvulkan\.so\.(\d+)\.(\d+)\.(\d+)$", lib.name)
    if m:
        assert default["version"][1:] == [int(m[1]), int(m[2]), int(m[3])], (default["version"], lib.name)
    # the program's own facts and the maps lines
    stubs_line = re.search(r"^stubs for unresolved imports: (\d+)$", out, re.M)
    assert stubs_line and int(stubs_line[1]) == len(stubs) and "initializers done" in out
    maps = re.findall(r"^maps ([0-9a-f]+)-([0-9a-f]+) (\S+) ([0-9a-f]+) \S+ \d+\s+(.*)$", out, re.M)
    want = expected_maps(lib)
    assert [(int(o, 16), p) for _, _, p, o, _ in maps] == want, (maps, want)
    assert all(Path(p).resolve() == lib for *_, p in maps), maps
    starts = [int(a, 16) for a, *_ in maps]
    assert starts == sorted(starts) and all(int(b, 16) == int(a2, 16) for (a1, b, *_), (a2, *_) in zip(maps, maps[1:])), "contiguous"
    # the driver log: every manifest found is read and every library refused by name; none is loaded
    log = err3 + out3
    manifests = list(dict.fromkeys(re.findall(r"Found ICD manifest file (\S+),", log)))
    refused = list(dict.fromkeys(re.findall(r"Failed loading library associated with ICD JSON (\S+)\. Ignoring this JSON", log)))
    assert len(manifests) == len(refused) >= 1 and "not loaded by this loader" in log, (manifests, refused)
    runs = dict(default=dict(exit=rc, parsed=default), noIcd=dict(exit=rc2, parsed=no_icd), oracleNoIcd=oracle,
                driverLog=dict(manifestsFound=manifests, librariesRefused=refused))
    report = dict(status="PASS_B2_LIBVULKAN", compiler=pin(compiler), image=pin(img), unit={p: pin(ROOT / p) for p in
                  [l for l in (B2 / "MANIFEST").read_text().splitlines() if l and not l.startswith("#")]},
                  host=[platform.system(), platform.machine(), platform.release()],
                  library=dict(path=str(lib), **pin(lib), imports=len(coverage)),
                  imports=coverage, exportsOfImage=len(table), runs=runs, maps=[list(m) for m in maps], expectedMaps=[list(w) for w in want],
                  stubs=stubs, oracle="the same two calls through the system ld.so and glibc (Python ctypes), drivers hidden; compared, not used by the product route",
                  noICDLoaded=True, cCompilerOrLoader=False)
    (output / "b2-libvulkan.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], "version", ".".join(map(str, default["version"][1:])), "extensions", default["count"][1],
          "imports", len(coverage), "stubs", stubs, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--libvulkan", type=Path)
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve(), args.libvulkan)
