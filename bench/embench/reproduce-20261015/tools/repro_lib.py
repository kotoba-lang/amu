"""Shared helpers for the 2026-10-15 Embench reproduction package (kotoba-lang/amu).

Everything is located relative to this file; no absolute host paths. The repository root is three levels up
(bench/embench/reproduce-20261015/tools -> repository root)."""
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]          # bench/embench/reproduce-20261015
REPO = PKG.parents[2]                               # repository root
FUEL = 34359738368                                  # 2^35, the official fuel budget
COMPILE_ENV = dict(KEXE_COMMAND='1', KEXE_FUEL='off', KEXE_VECTORS='4194304', KEXE_VECTOR_ITEMS='134217728',
                   KEXE_STRING_POOL='268435456', KEXE_PAIRS='16777216', KEXE_CPU_SECONDS='1800', KEXE_WALL_SECONDS='1800')
LOADER_PREFIX = ['0', '0', 'aarch64', '35,37,38,39', '--']


def sha(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    return sha(Path(p).read_bytes())


def pin(p):
    b = Path(p).read_bytes()
    return dict(bytes=len(b), sha256=sha(b))


def load(rel):
    return json.loads((PKG / rel).read_text())


def require_macos_arm64():
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise SystemExit('this step runs native aarch64 Mach-O code: it needs macOS on Apple silicon (arm64)')


def fresh_dir(p):
    p = Path(p).resolve()
    if p.exists():
        raise SystemExit('output directory exists; use a new one: ' + str(p))
    p.mkdir(parents=True)
    return p


def git_show(commit, path, repo=REPO):
    q = subprocess.run(['git', '-C', str(repo), 'show', commit + ':' + path], capture_output=True)
    if q.returncode != 0:
        raise SystemExit('git show %s:%s failed (is the full history present? use a normal clone, not --depth 1): %s'
                         % (commit, path, q.stderr.decode(errors='replace')[-300:]))
    return q.stdout


def unity(commit, overrides=None, repo=REPO):
    """Unity source = the seed/MANIFEST files of `commit`, each followed by one newline (scripts/seed/build-adopted.py).
    `overrides` maps a manifest path to (commit, path) taken from another public commit."""
    paths = [l.strip() for l in git_show(commit, 'seed/MANIFEST', repo).decode().splitlines() if l.strip() and not l.startswith('#')]
    parts = []
    for p in paths:
        src = (overrides or {}).get(p)
        parts.append((git_show(src[0], src[1], repo) if src else git_show(commit, p, repo)) + b'\n')
    return b''.join(parts), paths


def build_loader(c_source, out_binary):
    q = subprocess.run(['clang', '-std=c11', '-O2', str(c_source), '-o', str(out_binary)], capture_output=True, text=True)
    if q.returncode != 0:
        raise SystemExit('loader build failed: ' + q.stderr[-2000:])
    return out_binary


def kexe(loader, compiler, args, workdir, log_prefix):
    """Run one compiler command under the trusted C loader exactly as scripts/seed/build-adopted.py does."""
    env = {k: v for k, v in os.environ.items() if not k.startswith('KEXE_')}
    env.update(COMPILE_ENV, KEXE_CAP_RESOURCES_35=str(workdir), TMPDIR=str(workdir))
    argv = [str(loader), str(compiler)] + LOADER_PREFIX + [str(a) for a in args]
    q = subprocess.run(argv, cwd=workdir, env=env, capture_output=True, timeout=3600)
    Path(str(log_prefix) + '.stdout').write_bytes(q.stdout)
    Path(str(log_prefix) + '.stderr').write_bytes(q.stderr)
    return q.returncode, q.stdout, q.stderr


def build_compiler(loader, producer, unity_bytes, workdir, name):
    """producer compiles the unity source; the native `main` is extracted (one generation of build-adopted.py)."""
    d = Path(workdir); d.mkdir(parents=True, exist_ok=True)
    src = d / (name + '-seed-unity.kotoba'); src.write_bytes(unity_bytes)
    kseed = d / (name + '.kseed'); native = d / (name + '.bin')
    rc, out, err = kexe(loader, producer, ['compile', src, '--target', 'aarch64-macos', '--output', kseed], d, d / (name + '-compile'))
    if rc != 0:
        return dict(name=name, ok=False, stage='compile', exit=rc, stderr=err.decode(errors='replace')[-1500:], stdout=out.decode(errors='replace')[-1500:])
    rc, out, err = kexe(loader, producer, ['extract-native', kseed, '--symbol', 'main', '--output', native], d, d / (name + '-extract'))
    if rc != 0:
        return dict(name=name, ok=False, stage='extract', exit=rc, stderr=err.decode(errors='replace')[-1500:])
    return dict(name=name, ok=True, producerSHA256=sha_file(producer), unitySHA256=sha(unity_bytes), unityBytes=len(unity_bytes),
                kseed=pin(kseed), native=dict(pin(native), path=str(native)))


def compile_port(loader, compiler, source_bytes, workdir, tag):
    """Compile one official port exactly as the measurement did; returns kseed/native pins and the export table."""
    d = Path(workdir); src = d / (tag + '.kotoba'); src.write_bytes(source_bytes)
    kseed = d / (tag + '.kseed')
    rc, out, err = kexe(loader, compiler, ['compile', src, '--target', 'aarch64-macos', '--output', kseed], d, d / (tag + '.compile'))
    if rc != 0:
        raise SystemExit('compile failed for %s: %s' % (tag, err.decode(errors='replace')[-800:]))
    head, native = kseed.read_bytes().split(b'\n\n', 1)
    (d / (tag + '.bin')).write_bytes(native)
    exports = {l.split()[0]: [int(l.split()[1]), int(l.split()[2])] for l in head.decode().splitlines()[1:]}
    return dict(kseed=pin(kseed), native=pin(d / (tag + '.bin')), exports=exports)


def kseed_parts(kseed_bytes):
    head, native = kseed_bytes.split(b'\n\n', 1)
    exports = {l.split()[0]: [int(l.split()[1]), int(l.split()[2])] for l in head.decode().splitlines()[1:]}
    return exports, native


# ---------------------------------------------------------------------------------------------- timers
def caps_for(workload, extra=None):
    """Official per-run KEXE caps (the campaign's base caps, the three round114 per-workload overrides, then extraCaps)."""
    caps = dict(KEXE_FUEL=str(FUEL), KEXE_STRUCTURED_REPORT='1', KEXE_ARENA_USE='1', KEXE_CPU_SECONDS='1800', KEXE_WALL_SECONDS='1800')
    if workload == 'aha-mont64': caps.update(KEXE_VECTORS='67108864', KEXE_VECTOR_ITEMS='134217728')
    if workload == 'qrduino': caps.update(KEXE_PAIRS='65536')
    if workload == 'slre': caps.update(KEXE_PAIRS='8388608')
    caps.update(extra or {})
    return caps


def timer_header(native_path, image, exports, w):
    """timing-packet-generated.h: the same defines and embedded image the official packet used (only the path differs)."""
    sym = w['measuredSymbol']
    lines = ['#include <stdint.h>', '#include <stddef.h>', '#define TIMING_PACKET_ISA "aarch64"',
             '#define TIMING_NATIVE_PATH ' + json.dumps(str(native_path)),
             '#define TIMING_BENCH_OFFSET %d' % exports[sym][0], '#define TIMING_VERIFY_OFFSET %d' % exports['verify-state'][0],
             '#define TIMING_BENCH_ARITY %d' % exports[sym][1],
             '#define TIMING_WARM_SEED_OFFSET %d' % (exports[w['seedSymbol']][0] if w.get('seedSymbol') else -1)]
    assert exports[sym][1] == w['measuredArity']
    return '\n'.join(lines) + '\nstatic const unsigned char timing_native[]={' + ','.join(map(str, image)) + '};\n'


def build_timer(dst, harness, image, exports, w, extension_patches=None):
    """Timer = the timing loader (harness/separated-loader.c) + timing headers + a generated packet header."""
    dst = Path(dst); dst.mkdir(parents=True)
    for f in ['separated-loader.c', 'timing-frontend.h']:
        shutil.copyfile(Path(harness) / f, dst / f)
    te = (Path(harness) / 'timing-extension.h').read_text()
    for a, b in (extension_patches or []):
        assert te.count(a) == 1, a
        te = te.replace(a, b)
    (dst / 'timing-extension.h').write_text(te)
    (dst / 'image.bin').write_bytes(image)
    (dst / 'timing-packet-generated.h').write_text(timer_header(dst / 'image.bin', image, exports, w))
    q = subprocess.run(['clang', '-std=c11', '-O2', str(dst / 'separated-loader.c'), '-o', str(dst / 'timer')], capture_output=True, text=True)
    if q.returncode != 0 or q.stderr:
        raise SystemExit('timer build failed: ' + q.stderr[-1500:])
    return dst / 'timer'


def run_timer(timer, n, caps, timeout=1805):
    env = dict({k: v for k, v in os.environ.items() if not k.startswith('KEXE_')}, **caps)
    p = subprocess.run([str(timer), str(n)], env=env, capture_output=True, text=True, timeout=timeout)
    try:
        sample = json.loads(p.stdout.splitlines()[-1])
    except (ValueError, IndexError):
        sample = None
    f = re.search(r':status :ok :result 1 .*:fuel \{:initial (\d+) :remaining (\d+)\}', p.stdout)
    fuel_ok = bool(sample and f and int(f[1]) == FUEL and int(f[1]) - int(f[2]) == sample['benchmarkFuel'] + sample['verifyFuel'])
    return dict(n=n, returncode=p.returncode, stdout=p.stdout, stderr=p.stderr, sample=sample, fuelConsistent=fuel_ok,
                elapsedNs=sample.get('elapsedNs') if sample else None)


def exact(run, expected):
    """The official run_trigger.py validity rule (sample without elapsedNs, exact stderr arena line, fuel)."""
    s = run['sample']
    return bool(run['returncode'] == 0 and s and {k: v for k, v in s.items() if k != 'elapsedNs'} == expected['expectedSample']
                and run['stderr'] == expected['expectedStderr'] and run['fuelConsistent'])
