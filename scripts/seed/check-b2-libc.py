#!/usr/bin/env python3
"""The libc subset of route B2's Kotoba loader (ADR 0375, JUN-377): tools/b2/00..70 and their tests.

--compiler is an Amu-produced compiler from the current sources that has --format b2 (seed module 84); it writes
x86_64 images. The tests call the exported libc functions from Kotoba directly (no C, no libvulkan), on an
x86_64 Linux kernel:
  string_t  memset memcpy memmove strlen strcmp strncmp strchr strrchr strstr strncpy strncat strcspn strtok_r,
            the fortified variants, the ctype table and strtol (unit 00 + 10);
  printf_t  snprintf, __snprintf_chk, __vsnprintf_chk (also from a hand-built va_list) and sscanf (unit 00 + 20);
  elf_t     the ELF loader on a shared object written by hand (scripts/seed/b2_fixture.py): segments and the zero tail of
            bss, RELATIVE, 64, GLOB_DAT and JUMP_SLOT relocations, versioned imports, a weak import, an import nothing
            implements, the GNU hash, DT_INIT and DT_INIT_ARRAY, dlopen, dlsym, RELRO; and ten variants it must refuse by name
            (unit 00..70);
  libc_t    malloc, calloc, realloc, free, stdio on files, the standard error stream, directories, access, readlink,
            getenv, qsort (a stable sort called with a machine-code comparator), mutexes, dlopen, dlsym, dlerror, the
            thread control block (fs:0, fs:0x10, the canary) and the refusing stub (unit 00..70).
Each runs once for its checks (every line ends in ok; the last exit status is 0) and once per refusal mode, where the
program must stop with exit status 127 and a `b2: refused:` line naming the reason, or (abort, stack smashing)
exit status 134.

  python3 check-b2-libc.py --compiler F.elf --output OUT      (x86_64 Linux host)
"""
import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import b2_fixture  # noqa: E402 (scripts/seed)

ROOT = Path(__file__).resolve().parents[2]
B2 = ROOT / "tools/b2"
NS = "(ns g (:export [main]))\n"
CHK = ["memcpy", "memset", "strncpy", "strcat", "strncat"]
# (name, test file, units, environment, [(argument, exit status, stderr contains)])
TESTS = [
    ("string", "string_t.kotoba", ["00-base", "10-string"], {},
     [(f"overflow-{n}", 127, f"b2: refused: buffer overflow detected: __{n}_chk") for n in CHK]
     + [("invalid-base", 127, "invalid base"), ("invalid-base-1", 127, "invalid base"),
        ("memcpy-huge", 127, "size exceeds the address space"), ("strtok-null", 127, "no string to continue from")]),
    ("printf", "printf_t.kotoba", ["00-base", "20-printf"], {},
     [("overflow-chk", 127, "b2: refused: buffer overflow detected: __snprintf_chk"), ("vchk", 127, "b2: refused: buffer overflow detected: __vsnprintf_chk"),
      ("float", 127, "b2: refused: printf: unsupported conversion"), ("pct-n", 127, "b2: refused: printf: unsupported conversion"),
      ("positional", 127, "b2: refused: printf: unsupported conversion"), ("wide-s", 127, "b2: refused: printf: unsupported conversion"),
      ("scan-float", 127, "b2: refused: sscanf: unsupported conversion"), ("scan-p", 127, "b2: refused: sscanf: unsupported conversion"),
      ("scan-wide", 127, "b2: refused: sscanf: unsupported conversion")]),
    ("elf", "elf_t.kotoba", ["00-base", "10-string", "20-printf", "30-malloc", "40-stdio", "50-elf", "60-fault", "70-init"], {}, []),
    ("libc", "libc_t.kotoba", ["00-base", "10-string", "20-printf", "30-malloc", "40-stdio", "50-elf", "60-fault", "70-init"],
     {"B2_TEST_VAR": "value=with=equals", "B2_TEST_VAR2x": "no", "B2_TEST_EMPTY": ""},
     [("mutex-twice", 127, "pthread_mutex_lock: the mutex is already held"), ("fopen-write", 127, "only read modes are supported"),
      ("abort", 134, "abort() called"), ("stack-chk", 134, "stack smashing detected"),
      ("free-wild", 127, "free: invalid pointer"), ("unresolved", 127, "unimplemented import no_such_import")]),
]


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def unit(units, test):
    text = NS
    for u in units:
        text += (B2 / (u + ".kotoba")).read_text() + "\n"
    return text + "".join(l for l in (B2 / "tests" / test).read_text().splitlines(True) if not l.startswith("(ns "))


def main(compiler, output):
    assert platform.system() == "Linux" and platform.machine() in ("x86_64", "AMD64"), "an x86_64 Linux kernel"
    output.mkdir(parents=True, exist_ok=False)
    art = output / "artifacts"
    art.mkdir()
    producer = art / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)
    cenv = {"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art)}
    rows = {}
    for name, test, units, extra, modes in TESTS:
        src, img = art / (name + ".kotoba"), art / (name + ".elf")
        src.write_text(unit(units, test))
        z = subprocess.run([str(producer), "compile", str(src), "--target", "x86_64-linux", "--output", str(img), "--format", "b2"],
                           cwd=art, env=cenv, capture_output=True, timeout=900)
        assert z.returncode == 0 and not z.stderr and b":format :b2" in z.stdout, (name, z.returncode, z.stderr[-400:])
        img.chmod(0o755)
        scratch = output / ("scratch-" + name)
        scratch.mkdir()
        env = dict({"PATH": "/usr/bin:/bin"}, **extra)
        fixtures = {}
        if name == "elf":
            for variant in b2_fixture.VARIANTS:
                fixtures[variant] = scratch / f"libfixture-{variant}.so.1"
                fixtures[variant].write_bytes(b2_fixture.build(variant))
            (scratch / "libfixture.so.1").write_bytes(b2_fixture.build("base"))
        # string_t and printf_t take only a mode argument, libc_t a scratch directory, elf_t the fixture
        dirarg = [str(scratch)] if name == "libc" else [str(scratch / "libfixture.so.1")] if name == "elf" else []
        z = subprocess.run([str(img), *dirarg], env=env, capture_output=True, timeout=600)
        (output / (name + ".stdout")).write_bytes(z.stdout)
        (output / (name + ".stderr")).write_bytes(z.stderr)
        lines = z.stdout.decode().splitlines()
        bad = [ln for ln in lines if "FAIL" in ln]
        assert z.returncode == 0 and not bad, (name, z.returncode, bad[:5], z.stderr[-300:])
        checks = sum(1 for ln in lines if ln.endswith(" ok"))
        assert checks > (15 if name == "elf" else 20), (name, checks)
        refusals = {}
        for arg, status, text in modes:
            z2 = subprocess.run([str(img), *dirarg, arg], env=env, capture_output=True, timeout=600)
            assert z2.returncode == status and text.encode() in z2.stderr, (name, arg, z2.returncode, z2.stderr[-300:])
            refusals[arg] = dict(exit=z2.returncode, stderr=z2.stderr.decode(errors="replace").strip().splitlines()[-1][:200])
        if name == "elf":
            maps = re.findall(r"^maps \S+ (\S+) ([0-9a-f]+) ", z.stdout.decode(), re.M)
            assert maps == [("r-xp", "00000000"), ("r--p", "00001000"), ("rw-p", "00002000")], maps
            for variant, why in b2_fixture.VARIANTS.items():
                if why:
                    z2 = subprocess.run([str(img), str(fixtures[variant]), variant], env=env, capture_output=True, timeout=600)
                    assert z2.returncode == 127 and why.encode() in z2.stderr and b"b2: refused:" in z2.stderr, (variant, z2.returncode, z2.stderr[-300:])
                    refusals["variant-" + variant] = dict(exit=127, stderr=z2.stderr.decode(errors="replace").strip().splitlines()[-1][:200])
            z2 = subprocess.run([str(img), str(scratch / "libfixture.so.1"), "call-missing"], env=env, capture_output=True, timeout=600)
            assert z2.returncode == 127 and b"b2: refused: unimplemented import no_such_import: called from " in z2.stderr, z2.stderr[-300:]
            refusals["call-missing"] = dict(exit=127, stderr=z2.stderr.decode(errors="replace").strip().splitlines()[-1][:200])
            z2 = subprocess.run([str(img), str(scratch / "libfixture.so.1"), "relro-write"], env=env, capture_output=True, timeout=600)
            assert z2.returncode == 139 and b"b2: fatal signal 11 at " in z2.stderr, (z2.returncode, z2.stderr[-300:])
            refusals["relro-write"] = dict(exit=139, stderr=z2.stderr.decode(errors="replace").strip().splitlines()[0][:200])
        rows[name] = dict(image=pin(img), source=pin(src), checks=checks, refusals=refusals)
    report = dict(status="PASS_B2_LIBC", compiler=pin(compiler), host=[platform.system(), platform.machine(), platform.release()],
                  units={p.name: pin(p) for p in sorted(B2.glob("*.kotoba"))}, results=rows, cCompilerOrLoader=False)
    (output / "b2-libc.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], {k: v["checks"] for k, v in rows.items()}, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve())
