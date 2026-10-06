#!/usr/bin/env python3
"""Offline selected-pin and exact interrupted-PC mapping replay; no guest/timing."""
from pathlib import Path, PurePosixPath
import collections
import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile

D = Path(__file__).resolve().parent
manifest = json.loads((D / 'pc-diagnostic.manifest.json').read_text())
archive = D / manifest['archive']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == manifest['archiveSha256']
root = Path(tempfile.mkdtemp(prefix='amu-pc-offline-'))
with tarfile.open(archive, 'r:gz') as handle:
    members = handle.getmembers()
    assert len(members) == len(manifest['files'])
    assert len({m.name for m in members}) == len(members)
    for member in members:
        name = PurePosixPath(member.name)
        assert member.isfile() and not name.is_absolute() and '..' not in name.parts
        record = manifest['files'][member.name]
        assert member.size == record['bytes']
        raw = handle.extractfile(member).read()
        assert hashlib.sha256(raw).hexdigest() == record['sha256']
        path = root / member.name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

profile = root / 'profile'
expected = json.loads((profile / 'profile-analysis.json').read_text())
maps = {p.name: json.loads(p.read_text()) for p in profile.glob('profile-*.mapped.json')}
# The frozen analyzer is stdlib only. Adapt its sole absolute input directory
# to this isolated payload; opcode, PC, FN, SIR and statistic logic is unchanged.
original = (profile / 'analyze.py').read_text()
needle = "B=Path('/private/tmp/amu-scalar-dag-inline-20261006/implementation')"
assert original.count(needle) == 1
adapted = original.replace(needle, "B=W/'baseline'", 1)
(profile / 'offline-analyze.py').write_text(adapted)
result = subprocess.run([sys.executable, str(profile / 'offline-analyze.py')],
                        capture_output=True, text=True, cwd=root)
assert result.returncode == 0, result.stderr
assert json.loads((profile / 'profile-analysis.json').read_text()) == expected
for name, rows in maps.items():
    assert json.loads((profile / name).read_text()) == rows, name
report = json.loads((profile / 'report.json').read_text())
for arm, field in [('baseline', 'baselineCaptured'), ('candidate', 'candidateCaptured')]:
    assert expected['aggregate'][arm]['captured'] == report[field]
    assert expected['aggregate'][arm]['proportions'] == report['proportions'][arm]
assert sum(a['regions'].get('outsideGuest', 0) for a in expected['aggregate'].values()) == 3
assert sum(a['regions'].get('unmappedGuest', 0) for a in expected['aggregate'].values()) == 0
print(json.dumps({'status': 'PASS exact offline PC mapping and selected pins',
                  'selectedFiles': len(manifest['files']), 'profiles': len(maps),
                  'baselineCaptured': report['baselineCaptured'],
                  'candidateCaptured': report['candidateCaptured'],
                  'nativeExecutions': 0, 'solverRuns': 0, 'newMeasurements': 0,
                  'causalRegressionProof': False, 'officialScore': False}))
