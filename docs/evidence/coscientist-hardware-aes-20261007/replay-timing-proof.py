from pathlib import Path
import hashlib,json,tarfile,subprocess,sys
D=Path(__file__).resolve().parent;M=json.loads((D/'timing-replay.manifest.json').read_text());A=D/M['archive'];assert A.stat().st_size==M['archiveBytes'] and hashlib.sha256(A.read_bytes()).hexdigest()==M['archiveSha256']
O=Path(sys.argv[1]) if len(sys.argv)>1 else D/'offline-timing-replay';assert not O.exists(),'use a fresh destination; never overwrite retained replay';O.mkdir(parents=True)
with tarfile.open(A,'r:gz') as t:
 actual={}
 for m in t.getmembers():
  p=Path(m.name);assert not p.is_absolute() and '..' not in p.parts and (m.isfile() or m.isdir()) and not m.issym() and not m.islnk()
  if m.isfile():
   assert m.name not in actual;data=t.extractfile(m).read();actual[m.name]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
 assert actual==M['regularMembers'];t.extractall(O,filter='data')
R=O/'amu-hardware-aes-v2-full19-timing-replay';subprocess.run([sys.executable,str(R/'replay.py')],check=True)
print('PASS selected AES timing proof: hashes+raw recompute+11 modified-packet controls; nativeExecutions=0 solverRuns=0 newMeasurements=0')
