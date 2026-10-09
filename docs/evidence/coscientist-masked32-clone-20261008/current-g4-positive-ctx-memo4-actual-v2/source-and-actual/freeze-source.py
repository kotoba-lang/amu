"""One-shot SOURCE registry freeze; file hashing only, no operational calls."""
from pathlib import Path
import json,hashlib,stat
D=Path(__file__).parent;W=D.parent;P=W/'native-ctx-positive-memo-source-v1-20261009-independent';T=W/'tc-homogeneous-tail-frame-native4-source-v2-20261009'
def load(p):return json.loads(Path(p).read_bytes())
def rec(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink();b=p.read_bytes();t=p.lstat();assert (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns);return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(n,q):(D/n).write_text(json.dumps(q,indent=2)+'\n')
pr=load(D/'preregistration.json');ip={}
def add(p):
 p=Path(p);assert p.is_absolute();r=rec(p);ip[str(p)]=r
# Exact declared source/evidence closure, not blind recursive archive expansion.
for p in P.iterdir():
 if p.is_file():add(p)
for r in load(D/'source-assembly.json')['modulePins']:
 if Path(r['path']).parent!=D:add(r['path'])
for q in ['baseCandidate','baseUnity','currentProducerProof','currentG4BuildReceipt','loaderArtifact','interpreter','qualifiedIntegrationFixtureProof']:
 r=pr[q];assert rec(r['path'])=={k:r[k]for k in ['bytes','sha256']};add(r['path'])
add(pr['producer']);add(pr['candidateContainer'])
for e in pr['entries']:
 for k in ['source','container','native']:
  assert rec(e[k]['path'])=={z:e[k][z]for z in ['bytes','sha256']};add(e[k]['path'])
C=W/'tc-hft-compose511-bound-hoist-g4-original19-compile38-source-v1-20261009'
for n in ['preregistration.json','source-pins.json','input-pins.json','freeze.json','run-outputs/report.json','run-outputs/terminal.json']:add(C/n)
# Provenance records governing the saved current G4 generated producer.
F=Path(pr['currentG4BuildReceipt']['path']).parent.parent
for n in ['preregistration.json','source-pins.json','input-pins.json','freeze.json','run-outputs/report.json','run-outputs/terminal.json']:add(F/n)
for n in ['capture.py','integration.py','controller.py','typed-adapter.py','runtime.py','artifact_admission.py','native-call.py']:
 assert rec(D/n)==rec(T/n);add(T/n)
for n in ['preregistration.json','source-pins.json','input-pins.json','freeze.json']:add(T/n)
# Loader grammar/protocol, source-bound compiler interpreter provenance.
add('/Users/junkawasaki/github/wt/amu-seed17/tools/kexe_loader.c')
for r in [W/'crc-loader-supervisor-protocol-view-root-20261009/report.json']:
 add(r)
 # Exact descriptor references in the saved protocol report, without executing it.
 def refs(q):
  if isinstance(q,dict):
   if all(k in q for k in ['path','bytes','sha256']) and isinstance(q['path'],str) and Path(q['path']).is_file():
    assert rec(q['path'])=={k:q[k]for k in ['bytes','sha256']};add(q['path'])
   for v in q.values():refs(v)
  elif isinstance(q,list):
   for v in q:refs(v)
 refs(load(r))

for n in ['source-pins.json','input-pins.json','preregistration.json','freeze.json','report.json']:
 add(W/'native-ctx-positive-memo4-source-v1-20261009-independent'/n)
save('input-pins.json',ip);pr.update(inputPinsSHA256=rec(D/'input-pins.json')['sha256'],exactInputFiles=len(ip),exactInputLogicalBytes=sum(r['bytes']for r in ip.values()),operationalHOLD=['two exact source reviews and root GO absent','actual memo compilation/capacity/whole outputs pending','no cache or performance qualification'])
assert pr['exactInputFiles']<=3072 and pr['exactInputLogicalBytes']<=469762048
save('preregistration.json',pr)
sp={p.name:rec(p)for p in sorted(D.iterdir())if p.is_file()and p.name not in ['source-pins.json','input-pins.json','freeze.json','report.json']}
save('source-pins.json',sp)
report={'status':'FROZEN_EXECUTABLE_SOURCE_CURRENT_G4_POSITIVE_CTX_MEMO4_V2_PENDING_TWO_REVIEWS','sourcePinsSHA256':rec(D/'source-pins.json')['sha256'],'inputPinsSHA256':rec(D/'input-pins.json')['sha256'],'driverSHA256':rec(D/'run.py')['sha256'],'preregistrationSHA256':rec(D/'preregistration.json')['sha256'],'sourceFiles':len(sp),'inputFiles':len(ip),'inputLogicalBytes':pr['exactInputLogicalBytes'],'callsRegistered':4,'actualOperations':0,'nativeQualified':False,'cacheImplementedInCopiedSource':True,'performanceQualified':False,'conditionalMemoSourcePreserved':True,'explicitHeapAndFueloffScope':True,'internalGeneratedReceiptIsIndependentActorAudit':False,'pureControls':load(D/'source-controls.json')}
save('report.json',report);save('freeze.json',{'status':'FROZEN_SOURCE_ONLY','files':{n:rec(D/n)for n in ['source-pins.json','input-pins.json','preregistration.json','run.py','report.json']},'actualOperations':0});print(json.dumps(report))
