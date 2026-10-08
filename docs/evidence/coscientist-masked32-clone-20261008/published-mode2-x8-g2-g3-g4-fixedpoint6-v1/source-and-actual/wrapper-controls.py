"""Injected complete byte store; wrapper six cases, no process/FD APIs."""
from pathlib import Path
import json,copy,hashlib,importlib.util,contextlib,io
import run
from integration import MEMORY_POLICY,classify_memory
D=Path(__file__).resolve().parent;pr=json.loads((D/'preregistration.json').read_bytes());O=Path(pr['freshOutputRoot']);files={};realPath=run.Path;realPin=run.pin
class P:
 def __init__(self,p):self.p=str(p)
 def __str__(self):return self.p
 def __truediv__(self,p):return P(realPath(self.p)/str(p))
 def read_bytes(self):return files[self.p]
 def exists(self):return self.p in files
 def is_symlink(self):return False
 def __fspath__(self):return self.p
def rec(p):b=files[str(p)];return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def pinned(p,r):assert rec(p)==dict(path=str(p),bytes=r['bytes'],sha256=r['sha256']);return P(p)
files[str(D/'source-pins.json')]=b'pure registry';sourceSHA=hashlib.sha256(files[str(D/'source-pins.json')]).hexdigest();sp={'preregistration.json':{'sha256':'a'*64}};root='/pure/go.json'
files[root]=json.dumps(dict(status=pr['rootGOStatus'],maximumLoaderCalls=6,sourcePinsSHA256=sourceSHA,preregistrationSHA256='a'*64,C2=False,runtimeGuestAuthorized=False,timingAuthorized=False,outerHostLaunchRequiresEscalation=True)).encode();gr=rec(root)
for k in ['G1Native','G1Container']:files[pr[k]['path']]=Path(pr[k]['path']).read_bytes()
files[str(O/'candidate-source.kotoba')]=Path(pr['sourceCandidate']['path']).read_bytes()
r=dict(policy=MEMORY_POLICY,failure=None,acceptedSamples=1,acceptedLeaderBirthBound=True,otherRefusals=[],completePipeEOF=True,stoppedClosedCapture=True,rawTruncated=False,captureErrors=[],exactDirectChildWait='closed0',waitUncertain=False,withinOriginalDeadline=True,groupAuthorityRetired=True,groupOperationsAfterUncertainty=0,groupOperationsAfterWait=0,loaderWaitProtocolPinned=True)
obs=dict(semanticQualification=True,sampleReceiptPersistenceQualified=True,memoryAdmissionRecord=r,memoryObservation=classify_memory(r),status='COMPLETE_SEMANTIC_SAMPLED_MEMORY',strictOldMemoryPolicyPassed=True,capture={'firstFailure':None})
builds={}
for gen in [2,3,4]:
 n=str(O/('G'+str(gen)+'.bin'));k=str(O/('G'+str(gen)+'.kseed'));files[n]=bytes.fromhex('c0035fd6');files[k]=b'KSEED1 4 1\nmain 0 0\n\n'+files[n]
 b=dict(format='published-mode2-x8-generation-producer/v1',generation=gen,source=copy.deepcopy(pr['sourceCandidate']),builder=copy.deepcopy(pr['G1Native'])if gen==2 else rec(O/('G'+str(gen-1)+'.bin')),builderBuild=None if gen==2 else rec(O/('G'+str(gen-1)+'-build-receipt.json')),native=rec(n),container=rec(k),rootGO=gr,closedCompilerCalls=2,certificateQualified=False,attempts=[])
 for j in [0,1]:
  i=(gen-2)*2+j;c=pr['cases'][i];b['attempts'].append(dict(index=i+1,label=c['label'],nativeArgv=c['nativeArgv'],state='terminal',returncode=0,failure=None,captureStopAcknowledged=True,waitUncertain=False,controllerObservation=copy.deepcopy(obs),structuredReportObservation=dict(kind='compile',containerBytes=b['container']['bytes'])if j==0 else dict(kind='extract',offset=0,nativeBytes=4,arity=0)))
 files[str(O/('G'+str(gen)+'-build-receipt.json'))]=json.dumps(b).encode();builds[gen]=b
s=importlib.util.spec_from_file_location('pure_wrapper',D/'launch-wrapper.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.Path=P;m.D=P(D);m.checked=lambda p,r:str(pinned(p,r));run.Path=P;run.pin=pinned
neg=[];positive=0
def seal(i):
 c=pr['cases'][i-1];gen=c['generation'];previous=gen-1;return dict(format=pr['invocationSealVersion'],index=i,label=c['label'],nativeArgv=c['nativeArgv'],producer=copy.deepcopy(pr['G1Native'])if gen==2 else rec(O/('G'+str(previous)+'.bin')),producerContainer=copy.deepcopy(pr['G1Container'])if gen==2 else rec(O/('G'+str(previous)+'.kseed')),producerBuild=None if gen==2 else rec(O/('G'+str(previous)+'-build-receipt.json')),input=rec(c['nativeArgv'][8]),outputPath=c['outputPath'],rootGO=gr,sourcePinsSHA256=sourceSHA,preregistrationSHA256='a'*64)
# Output files removed only in the injected store during each prospective invocation.
for i,c in enumerate(pr['cases'],1):
 saved=files.pop(c['outputPath']);assert m.admit(c['nativeArgv'],pr,seal(i),sp,'b'*64);files[c['outputPath']]=saved;positive+=1
c=pr['cases'][4];base=seal(5);saved=files.pop(c['outputPath'])
for name,change in [('wrong-index',lambda s,p:s.update(index=1)),('wrong-builder',lambda s,p:s['producer'].update(sha256='0'*64)),('wrong-container',lambda s,p:s['producerContainer'].update(sha256='0'*64)),('missing-prev-build',lambda s,p:s.update(producerBuild=None)),('wrong-prev-receipt',lambda s,p:s['producerBuild'].update(sha256='0'*64)),('wrong-source',lambda s,p:s['input'].update(sha256='0'*64)),('wrong-output',lambda s,p:s.update(outputPath='/pure/other')),('extra-seal',lambda s,p:s.update(extra=True)),('missing-seal-key',lambda s,p:s.pop('producerBuild')),('wrong-source-binding',lambda s,p:s.update(sourcePinsSHA256='0'*64)),('changed-fuel',lambda s,p:p['environment'].update(KEXE_FUEL='1'))]:
 q=copy.deepcopy(base);p=copy.deepcopy(pr);change(q,p)
 try:m.admit(c['nativeArgv'],p,q,sp,'b'*64)
 except (AssertionError,KeyError,IndexError,TypeError):neg.append(name)
 else:raise AssertionError('mutant admitted:'+name)
files[c['outputPath']]=saved
try:m.admit(c['nativeArgv'],pr,base,sp,'b'*64)
except AssertionError:neg.append('existing-output')
else:raise AssertionError('overwrite admitted')
run.Path=realPath;run.pin=realPin
print(json.dumps(dict(status='PASS_PURE_SIX_GENERATION_COMPILER_WRAPPER_CASES_ONLY',positiveCases=positive,refusedMutants=neg,generatedContainersAreModelInputsOnly=True,operationalCalls=0),indent=2))
