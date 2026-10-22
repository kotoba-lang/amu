from pathlib import Path
import hashlib, json, sys, tarfile

p=Path(sys.argv[1]).resolve()
m=json.loads((p/'manifest.json').read_text())
a=p/'capture.tar.gz'
assert a.stat().st_size==m['archiveBytes'] and a.stat().st_size<=16*1024*1024
assert hashlib.sha256(a.read_bytes()).hexdigest()==m['archiveSHA256']
expected={r['path']:r for r in m['files']}
assert len(expected)==len(m['files'])<=600
seen=set();total=0
with tarfile.open(a,mode='r|gz') as t:
 for e in t:
  assert e.isfile() and e.name in expected and e.name not in seen
  assert not Path(e.name).is_absolute() and '..' not in Path(e.name).parts
  r=expected[e.name];assert e.size==r['bytes'] and 0<=e.size<=48*1024*1024
  total+=e.size;assert total<=48*1024*1024
  b=t.extractfile(e).read(e.size+1)
  assert len(b)==e.size and hashlib.sha256(b).hexdigest()==r['sha256']
  seen.add(e.name)
assert seen==set(expected)
print(json.dumps({'status':'PASS_CAPTURE_INTEGRITY_NO_NATIVE_REPLAY','files':len(seen),'expandedBytes':total,'nativeCalls':0}))
