#!/usr/bin/env python3
"""Rebuild and observe the actual public native Mac CLI and its aliases.

Python stages/hashes bytes and observes processes. Amu performs checking,
compilation, ABI checking, emission, packaging, host operations and execution.
"""
import argparse
import hashlib
import importlib.util
import json
import platform
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/seed' / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main(out):
    assert (platform.system(), platform.machine()) == ('Darwin', 'arm64')
    mac = module('mac_native', 'check-aiueos-user-macos-native.py')
    builder = module('mac_cli_build', 'build-macos-cli.py')
    product = module('mac_cli_product', 'check-macos-cli-product.py')
    d = json.loads((ROOT / 'seed/bootstrap/aarch64-macos/cli.json').read_text())
    root = json.loads((ROOT / 'seed/bootstrap/aarch64-macos/root.json').read_text())
    assert d['schema'] == 'amu.macos-native-cli.v1'
    assert d['image']['sha256'] in (ROOT / 'examples/foundation-starter/MACOS-ARM64.md').read_text(), 'first-run guide has a stale CLI digest'
    assert d['compiler'] == root['compiler'] and d['packager'] == root['packager']
    for role in ('compiler', 'packager', 'image'):
        assert mac.verify_macho(ROOT / d[role]['path']) == {k: d[role][k] for k in ('bytes','sha256')}
    aliases = [ROOT / name for name in (d['entry'], *d['aliases'])]
    image = ROOT / d['image']['path']
    for alias in aliases:
        assert alias.is_symlink() and alias.resolve(strict=True) == image.resolve(strict=True)
    for name, identity in d['sources'].items():
        assert mac.pin(ROOT / name) == identity
    names = [x for x in (ROOT / 'seed/FULL-MANIFEST').read_text().splitlines() if x and not x.startswith('#')]
    unity = b''.join((ROOT / name).read_bytes() + b'\n' for name in names)
    assert dict(bytes=len(unity), sha256=hashlib.sha256(unity).hexdigest()) == root['fullSource']
    out.mkdir(parents=True, mode=0o700, exist_ok=False)
    # The complete fresh native derivation must reproduce the source-bound
    # unsigned image. Ad-hoc signature encodings may differ between OS hosts.
    builder.build(out / 'rebuild')
    rebuilt = json.loads((out / 'rebuild/cli-build.json').read_text())
    assert rebuilt['unity'] == d['unity'] and rebuilt['sources'] == d['sources']
    unsigned = out / 'rebuild/amu-cli-unsigned.macho'
    assert mac.pin(unsigned) == d['unsigned']
    stripped = out / 'stripped.macho'
    shutil.copy2(image, stripped)
    subprocess.run(['/usr/bin/codesign', '--remove-signature', str(stripped)], check=True, capture_output=True)
    observed = bytearray(stripped.read_bytes())
    expected = unsigned.read_bytes()
    # codesign leaves the rounded __LINKEDIT virtual size after removal.
    # Compare every executable/data/header byte other than that metadata word.
    assert len(observed) == len(expected)
    observed[280:288] = expected[280:288]
    assert observed == expected, 'public image does not contain the rebuilt native payload'
    product.check(aliases[0], out / 'commands')
    for i, alias in enumerate(aliases[1:]):
        p = subprocess.run([str(alias), 'check', str(out / 'commands/hello.kotoba')],
                           cwd=out, env={'PATH':'/nonexistent'}, capture_output=True, timeout=150)
        assert p.returncode == 0 and p.stdout == b'ok\n' and not p.stderr
    assert mac.pin(image) == {k: d['image'][k] for k in ('bytes','sha256')}
    result = dict(schema='amu.public-macos-product.v2', status='PASS_PUBLIC_MACOS_PRODUCT',
                  descriptor=mac.pin(ROOT / 'seed/bootstrap/aarch64-macos/cli.json'), image=mac.pin(image),
                  unsigned=mac.pin(unsigned), aliases=[str(p.relative_to(ROOT)) for p in aliases],
                  normalCommands=json.loads((out / 'commands/cli-product.json').read_text()),
                  nativeRebuildMatchesPublicPayload=True, manualFD3=False, hostedFallback=False,
                  fullRuntimeQualified=False, independentUserQualified=False)
    (out / 'public-macos-product.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'], 'native rebuild, three public aliases, ordinary check/compile/run')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    main(p.parse_args().output.resolve())
