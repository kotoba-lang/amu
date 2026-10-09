"""Pure injected byte store; no real file descriptors, process, exec or resource APIs."""
from pathlib import Path
import importlib.util,json,hashlib,copy
from integration import MEMORY_POLICY,classify_memory
D=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('pure_wrapper',D/'launch-wrapper.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
pr=json.loads((D/'preregistration.json').read_bytes());files={str(D/'source-pins.json'):b'pure registry'};sourceSHA=hashlib.sha256(files[str(D/'source-pins.json')]).hexdigest();sp={'preregistration.json':{'sha256':'a'*64}}
for p in [pr['producer'],pr['producerContainer'],pr['offCompiler']['path'],pr['offCompilerContainer']['path']]:files[p]=Path(p).read_bytes()
for c in pr['cases']:
 if c['kind']=='compile':files[c['nativeArgv'][8]]=Path(pr['sourceCandidate']['path']if c['label']=='candidate-compile'else pr['fixtureSource']['path']).read_bytes()
files['/pure/go.json']=json.dumps(dict(status=pr['rootGOStatus'],maximumLoaderCalls=6,sourcePinsSHA256=sourceSHA,preregistrationSHA256='a'*64,C2=False,runtimeGuestAuthorized=False,timingAuthorized=False)).encode()
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
 c=pr['cases'][i-1];pk=pr['producerContainer']if i<=2 else pr['offCompilerContainer']['path']if i<=4 else pr['candidateContainerPath'];return dict(format=pr['invocationSealVersion'],index=i,label=c['label'],nativeArgv=c['nativeArgv'],producer=rec(c['producer']),producerContainer=rec(pk),producerBuild=None,input=rec(c['nativeArgv'][8]),outputPath=c['outputPath'],rootGO=rec('/pure/go.json'),sourcePinsSHA256=sourceSHA,preregistrationSHA256='a'*64)
positive=0
for i in [1,3]:assert m.admit(pr['cases'][i-1]['nativeArgv'],pr,seal(i),sp,'b'*64);positive+=1
files[pr['candidateNativePath']]=files[pr['producer']];files[pr['candidateContainerPath']]=files[pr['producerContainer']]
# Synthetic generated producer is intentionally baseline bytes in injected store,
# not a claim that candidate has compiled or is clobber qualified.
nr=rec(pr['candidateNativePath']);kr=rec(pr['candidateContainerPath']);record=dict(policy=MEMORY_POLICY,failure=None,acceptedSamples=1,acceptedLeaderBirthBound=True,otherRefusals=[],completePipeEOF=True,stoppedClosedCapture=True,rawTruncated=False,captureErrors=[],exactDirectChildWait='closed0',waitUncertain=False,withinOriginalDeadline=True,groupAuthorityRetired=True,groupOperationsAfterUncertainty=0,groupOperationsAfterWait=0,loaderWaitProtocolPinned=True);obs=dict(semanticQualification=True,sampleReceiptPersistenceQualified=True,memoryAdmissionRecord=record,memoryObservation=classify_memory(record),status='COMPLETE_SEMANTIC_SAMPLED_MEMORY',strictOldMemoryPolicyPassed=True,capture={'firstFailure':None})
b=dict(format='published-mode2-x8-sealed-producer/v1',source=pr['sourceCandidate'],builder=rec(pr['producer']),native=nr,container=kr,rootGO=rec('/pure/go.json'),closedCompilerCalls=2,attempts=[],certificateQualified=False)
for i,c in enumerate(pr['cases'][:2]):b['attempts'].append(dict(index=i+1,label=c['label'],nativeArgv=c['nativeArgv'],state='terminal',returncode=0,failure=None,captureStopAcknowledged=True,waitUncertain=False,controllerObservation=copy.deepcopy(obs),structuredReportObservation={'kind':'compile','containerBytes':kr['bytes']}if i==0 else {'kind':'extract','offset':0,'nativeBytes':nr['bytes'],'arity':0}))
bp=str(Path(pr['freshOutputRoot'])/'candidate-build-receipt.json');files[bp]=json.dumps(b).encode();sg=seal(5);sg['producerBuild']=rec(bp);assert m.admit(pr['cases'][4]['nativeArgv'],pr,sg,sp,'b'*64);positive+=1
neg=[]
for name,change in [('missing-generated-build',lambda s,p:s.update(producerBuild=None)),('wrong-build-path',lambda s,p:s['producerBuild'].update(path='/pure/other')),('wrong-build-hash',lambda s,p:s['producerBuild'].update(sha256='0'*64)),('wrong-index',lambda s,p:s.update(index=6)),('wrong-source-hash',lambda s,p:s['input'].update(sha256='0'*64)),('wrong-producer-hash',lambda s,p:s['producer'].update(sha256='0'*64)),('wrong-container-hash',lambda s,p:s['producerContainer'].update(sha256='0'*64)),('wrong-output-path',lambda s,p:s.update(outputPath='/pure/other')),('wrong-fuel',lambda s,p:p['environment'].update(KEXE_FUEL='1')),('extra-seal-key',lambda s,p:s.update(extra=True)),('wrong-source-binding',lambda s,p:s.update(sourcePinsSHA256='0'*64))]:
 s=copy.deepcopy(sg);p=copy.deepcopy(pr);change(s,p)
 try:m.admit(pr['cases'][4]['nativeArgv'],p,s,sp,'b'*64)
 except (AssertionError,KeyError,TypeError):neg.append(name)
 else:raise AssertionError('negative admitted:'+name)
assert len({tuple(c['nativeArgv'])for c in pr['cases']})==6
print(json.dumps(dict(status='PASS_PURE_FIXED_AND_GENERATED_COMPILER_WRAPPER_ONLY',positiveByteStoreCases=positive,negatives=neg,operationalCalls=0),indent=2))
