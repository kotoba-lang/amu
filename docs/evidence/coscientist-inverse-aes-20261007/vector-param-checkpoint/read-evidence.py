"""Bounded content check only: no extraction, native execution or retries."""
from pathlib import Path, PurePosixPath
import hashlib, json, tarfile
p = Path(__file__).resolve().parent
m = json.loads((p / 'manifest.json').read_text())
a = p / 'capture.tar.gz'
expected = '02b38c0a006ac1724a6e5d5403058ec8c83a9223b63e8931fa3275c303b25569'
assert hashlib.sha256(a.read_bytes()).hexdigest() == m['archiveSHA256'] == expected
assert len(m['members']) <= 900 and m['expandedBytes'] <= 96000000
seen, total = set(), 0
with tarfile.open(a, 'r:gz') as t:
    for member in t:
        name = member.name
        assert member.isfile() and name not in seen and name in m['members']
        assert not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts
        row = m['members'][name]
        total += member.size
        assert 0 <= member.size == row['bytes'] and total <= 96000000
        stream = t.extractfile(member)
        assert stream is not None
        payload = stream.read(member.size + 1)
        assert len(payload) == member.size and hashlib.sha256(payload).hexdigest() == row['sha256']
        seen.add(name)
assert seen == set(m['members']) and total == m['expandedBytes']
print(json.dumps({'status': 'PASS_CONTENT_INTEGRITY_ONLY', 'members': len(seen), 'bytes': total,
                  'extracted': False, 'nativeCalls': 0}))
