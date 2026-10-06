"""Replay pinned diagnostic evidence without native executions or timing."""
from pathlib import Path
import hashlib, json, subprocess, sys, tarfile, tempfile

D = Path(__file__).resolve().parent
info = json.loads((D / 'archive-manifest.json').read_text())
archive = D / info['artifact']
assert hashlib.sha256(archive.read_bytes()).hexdigest() == info['sha256']

def clean(text):
    return '\n'.join(l for l in text.splitlines() if not l.startswith(('ENTRY_TRACE ', 'ENTRY_COUNT '))).strip()

def same(a, b):
    assert a['exit'] == b['exit'] and a['stdout'].strip() == b['stdout'].strip()
    assert clean(a['stderr']) == clean(b['stderr'])

with tempfile.TemporaryDirectory(prefix='amu-hotpath-replay-') as tmp:
    dest = Path(tmp)
    with tarfile.open(archive) as t:
        for member in t.getmembers():
            p = Path(member.name)
            assert not p.is_absolute() and '..' not in p.parts
            assert member.isfile() or member.isdir()
        t.extractall(dest)
    W = dest / 'native-hotpath-proof'
    manifest = json.loads((W / 'manifest.json').read_text())['files']
    assert len(manifest) == info['pinnedFiles']
    for name, pin in manifest.items():
        p = W / name
        assert p.stat().st_size == pin['bytes']
        assert hashlib.sha256(p.read_bytes()).hexdigest() == pin['sha256'], name
    build = json.loads((W / 'implementation/build-proof.json').read_text())['entries']
    fixed = [b for b in build if b['arm'] == 'diagnostic' and b['generation'] >= 2]
    assert len(fixed) == 3 and len({(b['bytes'], b['sha256']) for b in fixed}) == 1
    for b in fixed:
        p = W / ('implementation/diagnostic-seed-' + str(b['generation']) + '.bin')
        assert hashlib.sha256(p.read_bytes()).hexdigest() == b['sha256']
    source = (W / 'implementation/machine-audit.py').read_text()
    needle = "B=Path('/private/tmp/amu-static-vector-chain-20261006/observer/meta-ports')"
    assert source.count(needle) == 1
    source = source.replace(needle, "B=W.parent/'baseline-inputs/meta-ports'")
    derived = W / 'implementation/replay-machine-audit.py'
    derived.write_text(source)
    subprocess.run([sys.executable, str(derived)], check=True, capture_output=True, text=True)
    subprocess.run([sys.executable, str(W / 'root-proof/cross-profile.py')], check=True,
                   capture_output=True, text=True)
    trace = json.loads((W / 'team-constructor/trace.json').read_text())
    assert len(trace['rows']) == 216
    for row in trace['rows']:
        same(row, row['diagnostic'])
    public = json.loads((W / 'team-constructor/public-entry.json').read_text())
    assert len(public['rows']) == 4
    for row in public['rows']:
        same(row['baseline'], row['trace'])
    resources = json.loads((W / 'team-resource/resource-states.json').read_text())
    assert len(resources['rows']) == 161
    for row in resources['rows']:
        assert row['product'] == row['diagnostic']
    assert sum(r['product']['exit'] != 0 for r in resources['rows']) == 46
    report = {
        'status': 'PASS-pinned-extracted-independent-replay', 'pinnedFiles': len(manifest),
        'nativeFixedPointGenerations': 3, 'machineAuditRecomputed': True,
        'original19TraceMappingsRecomputed': 95, 'constructorStatePairsRechecked': 220,
        'resourceStatePairsRechecked': 161, 'resourceTraps': 46,
        'freshNativeExecutions': 0, 'freshTimings': 0,
        'limits': 'Retained actual native evidence; modulo entry counts, not cost shares or universal proof.'
    }
    (D / 'replay.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
