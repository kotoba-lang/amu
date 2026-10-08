"""Injected byte-store wrapper controls only; no operational APIs."""
from pathlib import Path
import json,hashlib,copy,importlib.util
D=Path(__file__).resolve().parent;s=importlib.util.spec_from_file_location('pure_wrapper',D/'launch-wrapper.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);pr=json.loads((D/'preregistration.json').read_bytes());files={str(D/'source-pins.json'):b'pure registry'};sourceSHA=hashlib.sha256(files[str(D/'source-pins.json')]).hexdigest();sp={'preregistration.json':{'sha256':'a'*64}}
for k in ['offCompiler','offCompilerContainer','candidateCompiler','candidateCompilerContainer','TCActualProof','candidateActualProof']:files[pr[k]['path']]=Path(pr[k]['path']).read_bytes()
files['/pure/go.json']=json.dumps(dict(status=pr['rootGOStatus'],maximumLoaderCalls=6,sourcePinsSHA256=sourceSHA,preregistrationSHA256='a'*64,C2=False,runtimeGuestAuthorized=False,timingAuthorized=False)).encode()
for c in pr['cases']:
 if c['kind']=='compile':files[c['nativeArgv'][8]]=Path(pr['statemateEntry']['source']['path']if c['label'].startswith('ON-statemate')else pr['fixtureSource']['path']).read_bytes()
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
 c=pr['cases'][i-1];on=i>=3;return dict(format=pr['invocationSealVersion'],index=i,label=c['label'],nativeArgv=c['nativeArgv'],producer=pr['candidateCompiler']if on else pr['offCompiler'],producerContainer=pr['candidateCompilerContainer']if on else pr['offCompilerContainer'],existingProducerProof=pr['candidateActualProof']if on else pr['TCActualProof'],input=rec(c['nativeArgv'][8]),outputPath=c['outputPath'],rootGO=rec('/pure/go.json'),sourcePinsSHA256=sourceSHA,preregistrationSHA256='a'*64)
positive=0
for i,c in enumerate(pr['cases'],1):
 if c['kind']=='extract':files[c['nativeArgv'][8]]=b'KSEED1 4 1\n'+c['symbol'].encode()+b' 0 1\n\n'+bytes.fromhex('c0035fd6')
 assert m.admit(c['nativeArgv'],pr,seal(i),sp,'b'*64);positive+=1
neg=[];base=seal(5)
for name,change in [('wrong-proof',lambda s,p:s['existingProducerProof'].update(sha256='0'*64)),('wrong-producer',lambda s,p:s['producer'].update(sha256='0'*64)),('wrong-container',lambda s,p:s['producerContainer'].update(sha256='0'*64)),('wrong-index',lambda s,p:s.update(index=1)),('wrong-input',lambda s,p:s['input'].update(sha256='0'*64)),('wrong-output',lambda s,p:s.update(outputPath='/pure/other')),('changed-compiler-fuel',lambda s,p:p['environment'].update(KEXE_FUEL='1')),('extra-key',lambda s,p:s.update(extra=True)),('missing-proof',lambda s,p:s.pop('existingProducerProof')),('wrong-source-binding',lambda s,p:s.update(sourcePinsSHA256='0'*64))]:
 q=copy.deepcopy(base);p=copy.deepcopy(pr);change(q,p)
 try:m.admit(pr['cases'][4]['nativeArgv'],p,q,sp,'b'*64)
 except (AssertionError,KeyError,TypeError):neg.append(name)
 else:raise AssertionError('negative admitted:'+name)
files[pr['cases'][4]['outputPath']]=b'exists'
try:m.admit(pr['cases'][4]['nativeArgv'],pr,base,sp,'b'*64)
except AssertionError:neg.append('existing-output-refused')
else:raise AssertionError('overwrite admitted')
print(json.dumps(dict(status='PASS_PURE_SIX_FIXED_AUDITED_COMPILER_WRAPPER_ONLY',positiveCompilerCases=positive,refusedMutants=neg,operationalCalls=0,syntheticContainerInputsAreControlModelsOnly=True),indent=2))
