#!/usr/bin/env python3
"""Regenerate the policy-native golden for the adopted compiler (the #1313 convention: each adoption pins the 19 images
its compiler produces for the archived original19 sources).

  python3 docs/evidence/same-algo-m104-20261015/native19-golden.py --output <new-dir> [--write]

Compiles the 19 archived sources of docs/evidence/native-selfhost-paused-20261012/evidence.tgz with the adopted image
seed/bootstrap/adopted-20261012.bin exactly as scripts/seed/verify-preserved-integration.py --main does (same archive
members, extract symbols, loader build and environment). With --write it writes seed/main-same-algo-m104-native19.json
and docs/evidence/same-algo-m104-20261015/main-same-algo-m104-native19.tgz (deterministic tar/gzip)."""
import argparse, gzip, hashlib, io, json, os, pathlib, platform, subprocess, tarfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
FROZEN19 = 'workspace/held-compiler-cli30-bounded-balanced-byte-tree-token-capacity-picojpeg-g4-original19-compile38-source-v4-20261012-next/run-outputs/'


def sha(b): return hashlib.sha256(b).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--output', required=True, type=pathlib.Path); ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    if (platform.system(), platform.machine()) != ('Darwin', 'arm64'): raise SystemExit('requires macOS arm64')
    out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False); art = out / 'artifacts'; art.mkdir()
    receipt = json.loads((ROOT / 'seed/adoption-20261012.json').read_text())
    producer = ROOT / 'seed/bootstrap/adopted-20261012.bin'; assert sha(producer.read_bytes()) == receipt['nativeImageSHA256']
    paths = [p for p in (ROOT / 'seed/MANIFEST').read_text().splitlines() if p and not p.startswith('#')]
    unity = b''.join((ROOT / p).read_bytes() + b'\n' for p in paths); assert sha(unity) == receipt['sourceUnitySHA256']
    loader = out / 'loader'
    subprocess.run(['clang', '-std=c11', '-O2', str(ROOT / 'seed/bootstrap/adopted-loader-20261012.c'), '-o', str(loader)], check=True)
    archive = ROOT / 'docs/evidence/native-selfhost-paused-20261012/evidence.tgz'
    env = dict(os.environ); env.update(KEXE_COMMAND='1', KEXE_CAP_RESOURCES_35=str(art), KEXE_FUEL='off', KEXE_VECTORS='4194304', KEXE_VECTOR_ITEMS='134217728',
                                      KEXE_STRING_POOL='268435456', KEXE_PAIRS='16777216', KEXE_CPU_SECONDS='1800', KEXE_WALL_SECONDS='1800', TMPDIR=str(art))
    images = {}; rows = []
    with tarfile.open(archive) as t:
        report = json.loads(t.extractfile(FROZEN19 + 'report.json').read())
        symbols = {c['label'].removesuffix('-extract'): c['case']['symbol'] for c in report['calls'] if c['case']['kind'] == 'extract'}
        members = {pathlib.PurePosixPath(m.name).stem: m for m in t.getmembers() if m.name.startswith(FROZEN19) and m.name.endswith('.kotoba')}
        members.pop('seed-unity', None); assert len(members) == 19
        for name in sorted(members):
            src = art / (name + '.kotoba'); src.write_bytes(t.extractfile(members[name]).read())
            kseed = art / (name + '-new.kseed'); image = art / (name + '-new.bin'); prefix = [loader, producer, '0', '0', 'aarch64', '35,37,38,39', '--']
            subprocess.run(list(map(str, prefix + ['compile', src, '--target', 'aarch64-macos', '--output', kseed])), cwd=art, env=env, check=True, capture_output=True)
            subprocess.run(list(map(str, prefix + ['extract-native', kseed, '--symbol', symbols[name], '--output', image])), cwd=art, env=env, check=True, capture_output=True)
            images[name] = image.read_bytes()
            rows.append(dict(workload=name, sourceSHA256=sha(src.read_bytes()), nativeSHA256=sha(images[name])))
            print('%-15s %s' % (name, rows[-1]['nativeSHA256'][:16]), flush=True)
    golden = dict(schema='amu.seed.main-native19.v1', producerCommit=receipt['sourceCommit'], producerNativeSHA256=receipt['nativeImageSHA256'],
                  sourceUnitySHA256=receipt['sourceUnitySHA256'],
                  source='Archived original19 sources compiled by the adopted same-algorithm compiler (m104 plus the SIR capacity raise; fixed point) with the verify-preserved-integration --main path; regenerated per the #1313 adoption convention',
                  images=rows)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w', format=tarfile.USTAR_FORMAT) as t:
        for name in sorted(images):
            info = tarfile.TarInfo(name + '.bin'); info.size = len(images[name]); info.mtime = 0; info.mode = 0o644; info.uid = info.gid = 0; info.uname = info.gname = ''
            t.addfile(info, io.BytesIO(images[name]))
    tgz = gzip.compress(buf.getvalue(), mtime=0)
    (out / 'golden.json').write_text(json.dumps(golden, indent=2) + '\n'); (out / 'golden.tgz').write_bytes(tgz)
    if a.write:
        (ROOT / 'seed/main-same-algo-m104-native19.json').write_text(json.dumps(golden, indent=2) + '\n')
        (HERE / 'main-same-algo-m104-native19.tgz').write_bytes(tgz)
    print('GOLDEN', sha((out / 'golden.json').read_bytes()), 'ARCHIVE', sha(tgz), 'written' if a.write else '(dry run)')


if __name__ == '__main__':
    main()
