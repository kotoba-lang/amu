from pathlib import Path
import hashlib,json,tarfile,tempfile,runpy
D=Path(__file__).parent
m=json.loads((D/'gate-proof.manifest.json').read_text());a=D/'gate-proof.tgz'
assert hashlib.sha256(a.read_bytes()).hexdigest()==m['archiveSha256']
o=Path(tempfile.mkdtemp(prefix='amu-hostgate-replay-'))
with tarfile.open(a) as t:
 assert set(t.getnames())==set(m['files'])
 for v in t.getmembers():
  p=Path(v.name);assert v.isfile() and not p.is_absolute() and '..' not in p.parts
 t.extractall(o,filter='data')
for n,v in m['files'].items():
 p=o/n;assert p.stat().st_size==v['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==v['sha256'],n
expected=hashlib.sha256((o/'team-independent-review/report.json').read_bytes()).hexdigest()
runpy.run_path(str(o/'team-independent-review/verify.py'),run_name='__main__')
assert hashlib.sha256((o/'team-independent-review/report.json').read_bytes()).hexdigest()==expected
print('PASS source delta/early gate/control raw replay; no native/build/timing execution')
