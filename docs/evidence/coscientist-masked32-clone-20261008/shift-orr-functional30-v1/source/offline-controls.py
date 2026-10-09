"""Pure record/process controls; fake Popen only, never executes a guest."""
from pathlib import Path
import json,hashlib,importlib.util,sys,types,copy
D=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('functional30',D/'run.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def nraw(n):return ('{:status :ok :result '+str(0 if n==0 else 1)+' :fuel {:initial 16777216 :remaining 16777215} :heap {:capacity 2097152 :used 0} :string-pool {:capacity 65536 :used 0} :vectors {:capacity 4096 :used 0} :vector-items {:capacity 65536 :used 0}}\n').encode()
def craw(n):return (json.dumps({'format':'kotoba.runtime-sample/v1','calls':1,'warmupCalls':0,'elapsedNanoseconds':1,'result':0 if n==0 else 1,'maxRssBytes':1,'fuelPerCall':16777216,'contextFuelBefore':16777216,'contextFuelAfter':16777216,'contextFuelConsumed':0,'nativeArtifactAbi':'kotoba.native-artifact-i64x8-to-i64-indirect/v1','artifactKind':'dylib','nativeArenaStatus':'unavailable-C','nativeArenas':None})+'\n').encode()
for n in [0,1,2,17,32]:m.native(nraw(n),b'',n);m.csample(craw(n),b'',n)
bad=[nraw(1).replace(b'result 1',b'result 2'),nraw(1).replace(b'16777215',b'0'),nraw(1).replace(b'used 0',b'used 999999999'),nraw(1).replace(b'capacity 4096',b'capacity 4097'),nraw(1)+b'junk',nraw(1).replace(b':ok',b':trap')]
for b in bad:
 try:m.native(b,b'',1);raise RuntimeError('accepted mutant')
 except AssertionError:pass
for field,value in [('result',True),('nativeArenas',{}),('contextFuelConsumed',1),('calls',2),('nativeArenaStatus','available'),('extra',1)]:
 q=json.loads(craw(1));q[field]=value
 try:m.csample((json.dumps(q)+'\n').encode(),b'',1);raise RuntimeError('accepted C mutant')
 except AssertionError:pass
class Fake:
 pid=900001
 def __init__(self,argv,**kw):self.returncode=None;self.argv=argv
 def communicate(self,timeout):
  self.returncode=0;n=int(self.argv[5]if self.argv[1]=='dylib'else self.argv[-1]);return (craw(n)if self.argv[1]=='dylib'else nraw(n)),b''
 def wait(self,timeout):self.returncode=0;return 0
T=D/'offline-positive';T.mkdir();m.O=T/'results';m.subprocess=types.SimpleNamespace(Popen=Fake,PIPE=-1);m.platform=types.SimpleNamespace(machine=lambda:'arm64',system=lambda:'Darwin')
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':H(p)}
sp=H(D/'source-pins.json');reviews=[]
for i in range(2):
 p=T/('synthetic-review'+str(i)+'.json');p.write_text(json.dumps({'status':'PASS_SOURCE_ONLY_SR_AES_SHA_FUNCTIONAL30','sourcePinsSHA256':sp,'syntheticOnly':True}));reviews.append(pin(p))
g={'status':'ROOT_AUTHORIZED_SR_AES_SHA_FUNCTIONAL30_ONLY','outputRoot':str(m.O),'sourcePinsSHA256':sp,'driverSHA256':H(D/'run.py'),'preregistrationSHA256':H(D/'preregistration.json'),'inputClosureSHA256':H(D/'input-closure.json'),'maximumChildCalls':30,'noRetry':True,'timingAuthorized':False,'compilerSSHAuthorized':False,'sourceReviews':reviews,'syntheticOnly':True};p=T/'synthetic-go.json';p.write_text(json.dumps(g));sys.argv=['run.py',str(p)];m.main();assert len(json.loads((m.O/'attempts.json').read_text()))==30
E=D/'offline-interruption';E.mkdir();m.O=E
class Interrupted(Fake):
 def communicate(self,timeout):
  if not hasattr(self,'interrupted'):self.interrupted=True;raise KeyboardInterrupt('injected')
  self.returncode=-9;return b'partial',b'error'
m.subprocess=types.SimpleNamespace(Popen=Interrupted,PIPE=-1);m.os=types.SimpleNamespace(killpg=lambda pid,sig:None);l=m.Ledger()
try:l.call('interrupted',['fake'],{});raise RuntimeError('did not stop')
except AssertionError:pass
assert l.rows[0]['state']=='terminal'and (E/'interrupted.stdout').read_bytes()==b'partial'
(D/'offline-controls.json').write_text(json.dumps({'status':'PASS_PURE_SOURCE_CONTROLS_NO_NATIVE','positiveRecords':10,'rejectedMutants':12,'fakeFullDriverClosedCalls':30,'injectedInterruptionKilledDrainedClosed':True,'actualChildCalls':0},indent=2)+'\n')
