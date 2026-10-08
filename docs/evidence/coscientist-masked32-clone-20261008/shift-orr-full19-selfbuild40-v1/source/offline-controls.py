"""Pure fake-process execution of source driver; no native/SSH/clang calls."""
from pathlib import Path
import importlib.util,json,hashlib,sys,types,struct
D=Path(__file__).resolve().parent;s=importlib.util.spec_from_file_location('driver40',D/'run.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);original_load=m.load;pr=original_load(D/'preregistration.json');counter=('KEXE_ARENA_USE {'+' '.join(':'+k+' 0'for k in m.FIELDS)+'}\n').encode();base={r['workload']:Path(r['container']['path']).read_bytes()for r in pr['cases']};base.update({k:Path(pr['compiler']['container']['path']).read_bytes()for k in ['G2','G3','G4']})
class Fake:
 pid=999999
 mutate=False
 def __init__(self,argv,**kwargs):self.argv=argv;self.returncode=None
 def communicate(self,timeout):
  a=self.argv;ix=a.index('--');cmd=a[ix+1];src=Path(a[ix+2]);out=Path(a[a.index('--output')+1]);label=out.stem
  if cmd=='compile':
   b=base[label]
   if self.mutate:b=b[:-1]+bytes([b[-1]^1])
   out.write_bytes(b);raw=b'{:ok true}\n'
  else:
   ex,payload=m.container(src.read_bytes());out.write_bytes(payload);sym=a[a.index('--symbol')+1];off=next(x['offset']for x in ex if x['name']==sym);raw=('{:ok true :offset '+str(off)+'}\n').encode()
  self.returncode=0;return raw,counter
 def wait(self,timeout):self.returncode=0;return 0
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':H(p)}
def run(label,mutate):
 t=D/label;t.mkdir();m.O=t/'results';m.subprocess=types.SimpleNamespace(Popen=Fake,PIPE=-1);Fake.mutate=mutate;m.load=lambda p:({**pr,'outputRoot':str(m.O)}if Path(p)==D/'preregistration.json'else original_load(p));sp=H(D/'source-pins.json');reviews=[]
 for i in range(2):
  p=t/('synthetic-review'+str(i)+'.json');p.write_text(json.dumps({'status':pr['sourceReviewStatus'],'sourcePinsSHA256':sp,'syntheticOnly':True}));reviews.append(pin(p))
 g={'status':pr['rootGOStatus'],'outputRoot':str(m.O),'sourcePinsSHA256':sp,'driverSHA256':H(D/'run.py'),'preregistrationSHA256':H(D/'preregistration.json'),'inputClosureSHA256':H(D/'input-closure.json'),'maximumChildCalls':40,'noRetry':True,'timingAuthorized':False,'workloadGuestSSHAuthorized':False,'sourceReviews':reviews,'syntheticOnly':True};p=t/'synthetic-go.json';p.write_text(json.dumps(g));sys.argv=['run.py',str(p)]
 try:m.main()
 except AssertionError:
  if not mutate:raise
 terminal=original_load(m.O/'terminal.json');need=1 if mutate else 40;assert terminal['childCalls']==need and terminal['allChildrenClosed']is True and terminal['failure']==mutate
 if mutate:assert terminal['extractCalls']==0 and not (m.O/'G2.kseed').exists()
 return terminal
positive=run('offline-positive',False);negative=run('offline-first-delta',True)
# Exact registered pattern proof and complement/tail rejects; no instruction execution.
old=struct.pack('<III',m.compare.__globals__['lsl'](9,19,24),m.compare.__globals__['lsr'](10,19,8),m.compare.__globals__['orr'](9,9,10))+b'\xa5'
new=struct.pack('<III',m.compare.__globals__['lsr'](10,19,8),m.compare.__globals__['orr'](9,10,19,24),0xd503201f)+b'\xa5';assert m.compare(old,new)['observedAlignedThreeWordPatterns']==1
for b in [new[:-1]+b'\xa4',new+b'\0',new[:8]+b'\0'*4+new[12:]]:
 try:m.compare(old,b);raise RuntimeError('accepted malformed delta')
 except AssertionError:pass
(D/'offline-controls.json').write_text(json.dumps({'status':'PASS_PURE_SOURCE_CONTROLS_NO_EXECUTION','fullFakeClosedCalls':40,'firstDeltaStopsBeforeExtractAtCall':1,'unknownDeltaMutantsRejected':3,'actualNativeSSHCompilerCalls':0,'sourceOutputRootSubstitution':'test-only owned namespace; source code unchanged'},indent=2)+'\n')
