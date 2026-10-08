"""Pure injected runtime wrapper byte/seal admission; no operational APIs."""
from pathlib import Path
import json,hashlib,copy,importlib.util
D=Path(__file__).resolve().parent;s=importlib.util.spec_from_file_location('pure_wrapper',D/'launch-wrapper.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);pr=json.loads((D/'preregistration.json').read_bytes());files={str(D/'source-pins.json'):b'pure registry'};sourceSHA=hashlib.sha256(files[str(D/'source-pins.json')]).hexdigest();sp={'preregistration.json':{'sha256':'a'*64}}
for c in pr['cases']:
 for k in ['native','container','source']:files[c[k]['path']]=Path(c[k]['path']).read_bytes()
files['/pure/go.json']=json.dumps(dict(status=pr['rootGOStatus'],maximumLoaderCalls=12,sourcePinsSHA256=sourceSHA,preregistrationSHA256='a'*64,C2=False,runtimeGuestAuthorized=True,timingAuthorized=False,outerHostLaunchRequiresEscalation=True)).encode()
class P:
 def __init__(self,p):self.p=str(p)
 def __str__(self):return self.p
 def __truediv__(self,o):return P(Path(self.p)/str(o))
 def read_bytes(self):return files[self.p]
 def exists(self):return self.p in files
 def is_symlink(self):return False
m.Path=P;m.D=P(D)
def checked(p,r):
 b=files[str(p)];assert len(b)==r['bytes']and hashlib.sha256(b).hexdigest()==r['sha256'];return str(p)
m.checked=checked
def rec(p):b=files[p];return dict(path=p,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def seal(i):
 c=pr['cases'][i-1];x={k:c[k]for k in ['label','nativeArgv','workload','arm','profile','symbol','offset','arity','native','container','source']};x.update(format=pr['invocationSealVersion'],index=i,rootGO=rec('/pure/go.json'),sourcePinsSHA256=sourceSHA,preregistrationSHA256='a'*64);return x
for i,c in enumerate(pr['cases'],1):assert m.admit(c['nativeArgv'],pr,seal(i),sp,'b'*64)
neg=[]
for name,change in [('wrong-index',lambda s,p:s.update(index=2)),('wrong-image',lambda s,p:s['native'].update(sha256='0'*64)),('wrong-container',lambda s,p:s['container'].update(sha256='0'*64)),('wrong-source',lambda s,p:s['source'].update(sha256='0'*64)),('wrong-offset',lambda s,p:s.update(offset=0)),('wrong-profile',lambda s,p:s.update(profile=64)),('changed-fuel',lambda s,p:p['environment'].update(KEXE_FUEL='off')),('changed-arena',lambda s,p:p['environment'].update(KEXE_VECTORS='1')),('extra-seal',lambda s,p:s.update(extra=True)),('missing-source',lambda s,p:s.pop('source')),('wrong-sourcebinding',lambda s,p:s.update(sourcePinsSHA256='0'*64))]:
 s=copy.deepcopy(seal(1));p=copy.deepcopy(pr);change(s,p)
 try:m.admit(pr['cases'][0]['nativeArgv'],p,s,sp,'b'*64)
 except (AssertionError,KeyError,TypeError):neg.append(name)
 else:raise AssertionError('mutant admitted:'+name)
for i,c in enumerate(pr['cases']):
 q=c['nativeArgv'][:6]+['--']+c['nativeArgv'][6:]
 try:m.runtime_case(q,pr,c)
 except AssertionError:neg.append('typed-separator-'+str(i))
 else:raise AssertionError('separator admitted')
print(json.dumps(dict(status='PASS_PURE_TWELVE_RUNTIME_WRAPPER_CASES_ONLY',positiveWholeImagesAndExportCases=12,refusedMutants=neg,operationalCalls=0),indent=2))
