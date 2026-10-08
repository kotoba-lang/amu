"""Pure injected wrapper admission controls. No actual exec/resource/FD/thread/process APIs."""
from pathlib import Path
import importlib.util,json,hashlib,copy
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('wrapper_source',D/'launch-wrapper.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
pr=json.loads((D/'preregistration.json').read_bytes());case=pr['cases'][0];sp={'preregistration.json':{'sha256':'a'*64}};registry=b'pure source registry';sourceSHA=hashlib.sha256(registry).hexdigest()
files={str(D/'source-pins.json'):registry,pr['producer']:Path(pr['producer']).read_bytes(),pr['candidateContainer']:Path(pr['candidateContainer']).read_bytes(),case['nativeArgv'][8]:Path(pr['entries'][17]['source']['path']).read_bytes()}
files['/pure/go.json']=json.dumps({'status':pr['rootGOStatus'],'sourcePinsSHA256':sourceSHA,'preregistrationSHA256':'a'*64,'C2':False}).encode()
class P:
 def __init__(self,p):self.p=str(p)
 def __str__(self):return self.p
 def __eq__(self,o):return self.p==str(o)
 def __truediv__(self,o):return P(str(Path(self.p)/str(o)))
 def read_bytes(self):return files[self.p]
 def with_suffix(self,s):return P(Path(self.p).with_suffix(s))
 @property
 def parent(self):return P(Path(self.p).parent)
 def exists(self):return self.p in files
 def is_symlink(self):return False
m.Path=P;m.D=P(D)
def checked(p,r):
 b=files[str(p)];assert len(b)==r['bytes']and hashlib.sha256(b).hexdigest()==r['sha256'];return str(p)
m.checked=checked
def rec(p):b=files[p];return {'path':p,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
seal={'format':pr['invocationSealVersion'],'index':1,'label':case['label'],'nativeArgv':case['nativeArgv'],'producer':rec(pr['producer']),'producerContainer':rec(pr['candidateContainer']),'input':rec(case['nativeArgv'][8]),'outputPath':case['outputPath'],'rootGO':rec('/pure/go.json'),'sourcePinsSHA256':sourceSHA,'preregistrationSHA256':'a'*64}
assert m.admit(case['nativeArgv'],pr,seal,sp,'b'*64) is True
neg=[]
for name,change in [('wrong-index',lambda s,p:s.update(index=2)),('wrong-source-hash',lambda s,p:s['input'].update(sha256='0'*64)),('wrong-producer-hash',lambda s,p:s['producer'].update(sha256='0'*64)),('wrong-container-hash',lambda s,p:s['producerContainer'].update(sha256='0'*64)),('wrong-output-path',lambda s,p:s.update(outputPath='/pure/other')),('wrong-fuel',lambda s,p:p['environment'].update(KEXE_FUEL='1000000')),('extra-seal-key',lambda s,p:s.update(extra=True)),('wrong-source-binding',lambda s,p:s.update(sourcePinsSHA256='0'*64))]:
 s=copy.deepcopy(seal);p=copy.deepcopy(pr);change(s,p)
 try:m.admit(case['nativeArgv'],p,s,sp,'b'*64)
 except AssertionError:neg.append(name)
 else:raise AssertionError('negative admitted:'+name)
assert len(pr['cases'])==10 and len({tuple(c['nativeArgv'])for c in pr['cases']})==10
assert all(c['nativeArgv'][2:7]==['0','0','aarch64','35,37,38,39','--']for c in pr['cases'])
dynamic=0
files[str(D/'run-outputs/unity-tc.kotoba')]=(D/'unity-tc.kotoba').read_bytes()
for index in [6,8]:
 row=pr['cases'][index];prod=row['nativeArgv'][1];con=str(Path(prod).with_suffix('.kseed'));files[prod]=files[pr['producer']];files[con]=files[pr['candidateContainer']]
 ds=copy.deepcopy(seal);ds.update(index=index+1,label=row['label'],nativeArgv=row['nativeArgv'],outputPath=row['outputPath'],producer=rec(prod),producerContainer=rec(con),input=rec(row['nativeArgv'][8]))
 assert m.admit(row['nativeArgv'],pr,ds,sp,'b'*64);dynamic+=1
print(json.dumps({'dynamicSealedG1G2BindingPositiveControls':dynamic,'status':'PASS_PURE_COMPILER_WRAPPER_ADMISSION_ONLY','positiveFixedG0WholePayload':1,'negatives':neg,'fixedUniqueCases':10,'operationalCalls':0},indent=2))
