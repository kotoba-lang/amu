"""Fixed C bootstrap invocation. Import inert; no guest invocation is allowed."""
from pathlib import Path
import json, os, sys, resource, hashlib
D = Path(__file__).resolve().parent

def main(label):
    pr = json.loads((D / 'preregistration.json').read_bytes())
    sp = json.loads((D / 'source-pins.json').read_bytes())
    for name in ['preregistration.json', 'limit-exec.py']:
        b = (D / name).read_bytes()
        assert len(b) == sp[name]['bytes'] and hashlib.sha256(b).hexdigest() == sp[name]['sha256']
    rows = [c for c in pr['cases'] if c['label'] == label]
    assert len(rows) == 1 and len(pr['cases']) == 5
    assert dict(os.environ) == pr['environment'] or (set(os.environ) == set(pr['environment']) | {'__CF_USER_TEXT_ENCODING'} and all(os.environ[k] == v for k, v in pr['environment'].items()))
    for kind, soft, hard in [(resource.RLIMIT_FSIZE, 8388608, 8388608), (resource.RLIMIT_CPU, 180, 181)]:
        a, b = resource.getrlimit(kind)
        assert a == resource.RLIM_INFINITY or a >= soft
        assert b == resource.RLIM_INFINITY or b >= hard
        resource.setrlimit(kind, (soft, hard))
        assert resource.getrlimit(kind) == (soft, hard)
    os.execve(rows[0]['argv'][0], rows[0]['argv'], pr['environment'])

if __name__ == '__main__':
    assert len(sys.argv) == 2
    main(sys.argv[1])
