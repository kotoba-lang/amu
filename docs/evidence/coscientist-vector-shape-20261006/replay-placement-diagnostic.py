#!/usr/bin/env python3
"""Offline raw placement schedule, bounds, result/fuel and criterion replay."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile

D = Path(__file__).resolve().parent
manifest = json.loads((D / 'placement-diagnostic.manifest.json').read_text())
archive = D / manifest['archive']
assert hashlib.sha256(archive.read_bytes()).hexdigest() == manifest['archiveSha256']
root = Path(tempfile.mkdtemp(prefix='amu-placement-offline-'))
with tarfile.open(archive, 'r:gz') as handle:
    members = handle.getmembers()
    assert len(members) == len(manifest['files'])
    assert len({m.name for m in members}) == len(members)
    for member in members:
        name = PurePosixPath(member.name)
        assert member.isfile() and not name.is_absolute() and '..' not in name.parts
        record = manifest['files'][member.name]
        raw = handle.extractfile(member).read()
        assert len(raw) == record['bytes']
        assert hashlib.sha256(raw).hexdigest() == record['sha256']
        path = root / member.name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
expected = json.loads((root / 'diagnostic-analysis.json').read_text())
result = subprocess.run([sys.executable, str(root / 'analyze.py')],
                        capture_output=True, text=True, cwd=root)
assert result.returncode == 0, result.stderr
assert json.loads((root / 'diagnostic-analysis.json').read_text()) == expected
assert expected['rows'] == 28 and expected['supportedSensitivity'] == []
assert len(expected['lowIdleFlagRows']) == 10
print(json.dumps({'status': 'PASS offline raw placement diagnostic',
                  'selectedFiles': len(manifest['files']), 'rawJobs': 28,
                  'lowIdleFlagsRetained': 10, 'supportedSensitivity': [],
                  'nativeExecutions': 0, 'solverRuns': 0, 'newMeasurements': 0,
                  'CPUEnvelopes': 'stored records; not new host observations',
                  'performanceQualified': False, 'causalProof': False}))
