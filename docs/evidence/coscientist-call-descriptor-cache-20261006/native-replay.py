from pathlib import Path
import hashlib,json,tarfile,tempfile,subprocess,sys
D=Path(__file__).resolve().parent;m=json.loads((D/'native-manifest.json').read_text());f=D/m['archive'];assert hashlib.sha256(f.read_bytes()).hexdigest()==m['sha256'];assert f.stat().st_size==m['bytes'];root=Path(tempfile.mkdtemp(prefix='amu-descriptor-native-isolated-'))
with tarfile.open(f) as t:
 for v in t.getmembers():
  p=Path(v.name);assert not p.is_absolute() and '..' not in p.parts and (v.isfile() or v.isdir()) and not v.issym() and not v.islnk()
 t.extractall(root,filter='data')
subprocess.run([sys.executable,str(root/'amu-call-descriptor-cache-native-replay'/'replay.py')],check=True)
print('PASS independent extracted artifact replay; native executions=0, new measurements=0')
