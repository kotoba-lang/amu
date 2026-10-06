from pathlib import Path
import hashlib,json,tarfile,tempfile,subprocess,sys
D=Path(__file__).resolve().parent;M=json.loads((D/'timing-entry-manifest.json').read_text());A=D/M['archive']
assert hashlib.sha256(A.read_bytes()).hexdigest()==M['sha256'] and A.stat().st_size==M['bytes']
with tempfile.TemporaryDirectory(prefix='shape-v4-timing-offline-') as fresh:
 with tarfile.open(A) as t:
  for m in t.getmembers():
   p=Path(m.name);assert not p.is_absolute() and '..' not in p.parts and (m.isfile() or m.isdir()) and not m.issym() and not m.islnk()
  t.extractall(fresh,filter='data')
 root=Path(fresh)/M['root'];subprocess.run([sys.executable,str(root/M['entry'])],check=True,cwd=root)
print('PASS fresh isolated timing replay; newMeasurements=0 native=0 solver=0')
