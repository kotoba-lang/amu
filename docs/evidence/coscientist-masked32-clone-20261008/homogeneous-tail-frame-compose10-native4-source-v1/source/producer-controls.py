"""Pure injected producer receipts/argv controls. No process, FD, thread or native API."""
from pathlib import Path
import sys,json,copy,hashlib,importlib.util
D=Path(__file__).resolve().parent;sys.path.insert(0,str(D))
import run
pr=run.load(D/'preregistration.json');run.source_scope(pr)
B=D.parent/'tc-homogeneous-tail-frame-native4-source-v2-20261009'
rows=copy.deepcopy(run.load(B/'run-outputs/attempts.json')[:2])
for i,r in enumerate(rows):r['nativeArgv']=pr['cases'][i]['nativeArgv'];r['label']=pr['cases'][i]['label']
raw=(B/'run-outputs/G1.kseed').read_bytes();payload,exports=run.container(raw);assert exports==[('main',0,0)]
native=dict(path=pr['candidateNativePath'],bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
packed=dict(path=pr['candidateContainerPath'],bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
go=dict(path=str(D.parent/'injected-only-no-file-go.json'),bytes=1,sha256='1'*64)
b={'format':pr['sealedProducerFormat'],'source':pr['sourceCandidate'],'builder':pr['builderLineage'],'native':native,'container':packed,'rootGO':go,'closedCompilerCalls':2,'attempts':rows,'certificateQualified':False}
assert run.build_guard(b,pr,native,packed,go)
passed=['owned-closed-build-positive','current-source-closure-positive']
mutants=[]
def mut(name,fn):
 q=copy.deepcopy(b);fn(q);mutants.append((name,q))
mut('missing-field',lambda q:q.pop('attempts'))
mut('wrong-format',lambda q:q.update(format='other'))
mut('wrong-source',lambda q:q['source'].update(sha256='0'*64))
mut('wrong-builder',lambda q:q['builder'].update(sha256='0'*64))
mut('wrong-native',lambda q:q['native'].update(sha256='0'*64))
mut('wrong-container',lambda q:q['container'].update(sha256='0'*64))
mut('wrong-GO',lambda q:q['rootGO'].update(sha256='0'*64))
mut('only-one-call',lambda q:q.update(attempts=q['attempts'][:1]))
mut('not-two-calls',lambda q:q.update(closedCompilerCalls=1))
mut('unclosed',lambda q:q['attempts'][1].update(state='live'))
mut('wait-failed',lambda q:q['attempts'][1].update(returncode=1))
mut('failure',lambda q:q['attempts'][1].update(failure='bad'))
mut('no-stopack',lambda q:q['attempts'][1].update(captureStopAcknowledged=False))
mut('uncertain-wait',lambda q:q['attempts'][1].update(waitUncertain=True))
mut('different-order',lambda q:q['attempts'][0].update(index=2))
mut('different-argv',lambda q:q['attempts'][0].update(nativeArgv=['other']))
mut('wrong-main-offset',lambda q:q['attempts'][1]['structuredReportObservation'].update(offset=4))
mut('partial-bytes',lambda q:q['attempts'][1]['structuredReportObservation'].update(nativeBytes=8))
mut('unqualified-observation',lambda q:q['attempts'][1]['controllerObservation'].update(semanticQualification=False))
mut('other-refusal',lambda q:q['attempts'][1]['controllerObservation']['memoryAdmissionRecord'].update(otherRefusals=['failure-pid-not-previously-bound']))
mut('invented-certification',lambda q:q.update(certificateQualified=True))
for name,q in mutants:
 try:run.build_guard(q,pr,native,packed,go)
 except (AssertionError,KeyError):passed.append(name)
 else:raise AssertionError('accepted '+name)
spec=importlib.util.spec_from_file_location('wrapper',D/'launch-wrapper.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
# Inert injected filesystem methods restrict the fixture to owned virtual paths.
realread=Path.read_bytes;realexists=Path.exists;realchecked=w.checked
virtual={};virtualGo={'status':pr['rootGOStatus'],'sourcePinsSHA256':hashlib.sha256(b'{}').hexdigest(),'preregistrationSHA256':'2'*64,'C2':False}
virtual[go['path']]=json.dumps(virtualGo).encode();virtual[str(D/'source-pins.json')]=b'{}'
def injectedRead(p):return virtual[str(p)]if str(p)in virtual else realread(p)
def injectedExists(p):return False if p.parent==Path(pr['freshOutputRoot'])else realexists(p)
def checked(p,r):
 q=virtual[str(p)];assert len(q)==r['bytes']and hashlib.sha256(q).hexdigest()==r['sha256'];return str(p)
go={'path':go['path'],'bytes':len(virtual[go['path']]),'sha256':hashlib.sha256(virtual[go['path']]).hexdigest()};b['rootGO']=go
sp={'preregistration.json':{'sha256':'2'*64}}
sealRefs=[]
try:
 Path.read_bytes=injectedRead;Path.exists=injectedExists;w.checked=checked
 virtual[str(Path(pr['freshOutputRoot'])/'candidate-build-receipt.json')]=json.dumps(b).encode()
 for c in pr['cases']:
  generated=c['producer']==pr['candidateNativePath'];nr=native if generated else pr['builderLineage'];pc=pr['candidateContainerPath']if generated else pr['candidateContainer'];kr=packed if generated else dict(path=pc,**run.receipt(pc))
  virtual[nr['path']]=payload if generated else realread(Path(nr['path']));virtual[pc]=raw if generated else realread(Path(pc))
  inp=c['nativeArgv'][8];virtual[inp]=(D/'candidate-current16.kotoba').read_bytes()if c['label']=='G1-compile'else raw if c['kind']=='extract'else(D/'nsichneu.kotoba').read_bytes()
  ir=dict(path=inp,bytes=len(virtual[inp]),sha256=hashlib.sha256(virtual[inp]).hexdigest())
  bp=Path(pr['freshOutputRoot'])/'candidate-build-receipt.json';br=dict(path=str(bp),bytes=len(virtual[str(bp)]),sha256=hashlib.sha256(virtual[str(bp)]).hexdigest())
  seal={'format':pr['invocationSealVersion'],'index':pr['cases'].index(c)+1,'label':c['label'],'nativeArgv':c['nativeArgv'],'producer':nr,'producerContainer':kr,'producerBuild':br if generated else None,'input':ir,'outputPath':c['outputPath'],'rootGO':go,'sourcePinsSHA256':virtualGo['sourcePinsSHA256'],'preregistrationSHA256':'2'*64}
  assert w.admit(c['nativeArgv'],pr,seal,sp,'3'*64);passed.append(c['label']+'-injected-wrapper-positive');sealRefs.append(copy.deepcopy(seal))
 last=sealRefs[-1]
 for name,fn in [('missing-receipt',lambda q:q.update(producerBuild=None)),('wrong-case',lambda q:q.update(index=1)),('wrong-input',lambda q:q['input'].update(sha256='0'*64)),('wrong-source-registry',lambda q:q.update(sourcePinsSHA256='0'*64)),('wrong-output',lambda q:q.update(outputPath='/wrong')),('unknown-field',lambda q:q.update(extra=1))]:
  q=copy.deepcopy(last);fn(q)
  try:w.admit(pr['cases'][-1]['nativeArgv'],pr,q,sp,'3'*64)
  except (AssertionError,KeyError,TypeError):passed.append(name)
  else:raise AssertionError('wrapper accepted '+name)
 for c in pr['cases']:
  q=copy.deepcopy(c);q['nativeArgv'][3]='1'
  try:run.compiler_case(q['nativeArgv'],pr,q)
  except AssertionError:passed.append(c['label']+'-misplaced-arity')
  else:raise AssertionError('bad argc accepted')
finally:Path.read_bytes=realread;Path.exists=realexists;w.checked=realchecked
out={'status':'PASS_PURE_COMPOSE10_NATIVE4_PRODUCER_AND_WRAPPER_CONTROLS_ONLY','controls':passed,'nativeCalls':0,'injectedFilesystemOnly':True,'noOperationalProof':True}
(D/'producer-controls-result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'controls':len(passed),'nativeCalls':0}))
