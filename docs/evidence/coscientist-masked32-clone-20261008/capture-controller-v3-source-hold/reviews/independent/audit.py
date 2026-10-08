"""Independent finite SOURCE audit. No subject writes or operational APIs.

Controller imports are removed by AST; its lock is a sequential injected stub.
No threading/Popen/ctypes/kernel/FD callback is invoked. Source pin reads only.
"""
import ast,hashlib,json,pathlib,types
D=pathlib.Path(__file__).resolve().parent
S=D.parent/'crc-original-guest-capture-controller-source-v3-20261009-dense'
def pin(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
sp=pin(S/'source-pins.json')
assert sp['sha256']=='aae532180677dd72dca4ec7fe3f9f64350aa64879defe79e1be7a8e756ec731b'
sources=json.loads((S/'source-pins.json').read_text())
for name,want in sources.items():
 p=pin(S/name);assert p['bytes']==want['bytes'] and p['sha256']==want['sha256'],name
inputs=json.loads((S/'input-pins.json').read_text())
def entries(x):
 if isinstance(x,dict):
  if {'path','bytes','sha256'}<=set(x):yield x
  else:
   for v in x.values():yield from entries(v)
 elif isinstance(x,list):
  for v in x:yield from entries(v)
checked=0
for path,value in inputs.items():
 e=dict(value,path=path)
 p=pin(pathlib.Path(e['path']));assert p['bytes']==e['bytes']and p['sha256']==e['sha256'],e['path'];checked+=1
assert checked==2101
V2=D.parent/'crc-original-guest-capture-controller-source-v2-20261009-dense'
assert pin(V2/'source-pins.json')['sha256']=='26f17f2ce1fdc1309fcfe8323ee08806f83c665ad53270b07c9852348030c674'
v2sources=json.loads((V2/'source-pins.json').read_text())
for name,want in v2sources.items():
 p=pin(V2/name);assert p['bytes']==want['bytes']and p['sha256']==want['sha256']
for p in S.glob('*.py'):ast.parse(p.read_text())
ns={'__name__':'injected_integration'}
exec(compile((S/'integration.py').read_bytes(),str(S/'integration.py'),'exec'),ns)
class Lock:
 def __enter__(self):return self
 def __exit__(self,*args):return False
cn={'__name__':'injected_controller','threading':types.SimpleNamespace(Lock=Lock),
 'classify_memory':ns['classify_memory'],'MEMORY_POLICY':ns['MEMORY_POLICY']}
t=ast.parse((S/'controller.py').read_text());t.body=[x for x in t.body if not isinstance(x,(ast.Import,ast.ImportFrom))]
exec(compile(t,str(S/'controller.py'),'exec'),cn)
Controller=cn['Controller']
class Flag:
 def __init__(self):self.value=False
 def is_set(self):return self.value
class Capture:
 def __init__(self,partial=False):self.stopped=Flag();self.refusals=[];self.partial=partial
 def refuse(self,r):self.refusals.append(r)
 def join_once(self,t):self.stopped.value=True;return True
 def snapshot(self):return {'stoppedWriter':True,'completeRaw':not self.partial,'errors':[],
  'EOF':{'stdout':not self.partial,'stderr':True},'dropped':{'stdout':0,'stderr':0}}
class Clock:
 def __init__(self):self.t=0
 def __call__(self):return self.t
 def pause(self,dt):self.t+=dt
class Fault(Exception):
 def __init__(self,c):self.context=c
failure={'typedOrigin':'fresh-owned-group-api-v1','contextVersion':'owned-group-sampling-failure-context-v1',
 'stage':'leader-getpgid','pid':11,'queryOrdinal':2,'errno':3,'failureClass':'kernel-oserror'}
def exercise(mode,bound={'pid':11,'birth':22},loader=True):
 clock=Clock();cap=Capture(partial=mode=='partial');ctl=Controller(clock,1);n=0
 def sample():
  nonlocal n
  n+=1
  if n==1:
   if mode=='normal':cap.stopped.value=True
   return {'ownedPGID':11,'members':[{'pid':11,'start':22}]}
  f=dict(failure)
  if mode=='wrong-errno':f['errno']=1
  if mode=='wrong-stage':f['stage']='group-list'
  if mode=='unknown-pid':f['pid']=77
  if mode=='missing-version':f['contextVersion']='old'
  if mode=='threshold':raise ValueError('injected threshold refusal')
  raise Fault(f)
 sampler=types.SimpleNamespace(sample=sample)
 def wait(t):
  assert not ctl.active and ctl.waitEntered
  if mode=='wait-gap':raise KeyboardInterrupt('injected waitpid released, returncode not published')
  return 0
 q=ctl.observe(cap,sampler,wait,lambda t:True,clock.pause,lambda r:True,lambda:mode!='bad-journal',bound,loader)
 for call in [lambda:ctl.group(lambda:None),lambda:ctl.wait(wait)]:
  try:call()
  except AssertionError:pass
  else:raise AssertionError('retired authority restored')
 return q
controls=[]
for mode in ['gap','wrong-errno','unknown-pid','wrong-stage','missing-version','partial','threshold','wait-gap','bad-journal']:
 q=exercise(mode)
 expected='SEMANTIC_DIAGNOSTIC_TERMINATION_GAP'if mode=='gap'else'REFUSE'
 assert q['status']==expected and q['strictOldMemoryPolicyPassed']is False
 controls.append({'mode':mode,'observed':q['status'],'authorityCannotResume':True})
# Meaningful no-failure controls recompute the frozen V2 bug cases against V3.
bugs=[]
for label,bound,loader in [('missing-leader-birth',None,True),('wrong-leader-birth',{'pid':11,'birth':23},True),('missing-loader-proof',{'pid':11,'birth':22},False)]:
 q=exercise('normal',bound,loader)
 assert q['status']=='REFUSE' and q['strictOldMemoryPolicyPassed']is False and q['semanticQualification']is False
 bugs.append({'negative':label,'observed':q['status'],'strictOldMemoryPolicyPassed':False,'semanticQualification':False})
normal=exercise('normal')
assert normal['status']=='COMPLETE_SEMANTIC_SAMPLED_MEMORY' and normal['strictOldMemoryPolicyPassed']is True
assert normal['sampleReceiptPersistenceQualified']is False and normal['nativeControllerWiringQualified']is False
pr=json.loads((S/'preregistration.json').read_text())
assert len(pr['cases'])==8 and [c['argument']for c in pr['cases']]==[1,1,2,2,1024,1024,1,1]
assert [c['arm']for c in pr['cases']]==['OFF','ON']*4
assert [c['offset']for c in pr['cases']]==[1352,1392]*3+[1224,1264]
assert len(pr['exactEnvironment'])==17 and pr['maximumGuestFuelPerCall']==1000000
assert pr['maximumGateGuestFuel']==8000000 and pr['maximumDistinctProcessStartsProposed']==16
assert pr['strictOldGateRemains']=='FAIL_FIRST_FAILURE_NO_RETRY' and pr['nativeLaunchEntryAvailable']is False
for key in ['nativeControllerWiringQualified','sampleReceiptPersistenceQualified','totalRuntimeFDBoundQualified','deterministicIntegrationFixtureQualified','typedESRCHProvenanceQualified']:
 assert pr[key]is False
design=(S/'DESIGN.md').read_text()
assert 'operational HOLD' in design and 'no launch' in design.lower()
report={'status':'PASS_INDEPENDENT_V3_SOURCE_GUARD_REPAIR_ONLY_RUNTIME_HOLD_NO_GO',
 'subject':str(S),'sourcePins':sp,'sourceFilesVerified':len(sources),'inputFilesVerified':checked,
 'sourcePythonASTsParsed':len(list(S.glob('*.py'))),'nativeProcessThreadFDKernelNetworkCalls':0,
 'injectedSequentialControls':controls,'noFailureNegativeControls':bugs,
 'positiveNoFailureStatus':normal['status'],'frozenV2SourceFilesUnchanged':len(v2sources),
 'authorityFinding':'group operations serialize under one lock; active=false/waitEntered=true precedes wait; uncertainty permanently retires; tested sequentially, not a lock race proof',
 'typedProvenanceFinding':'exact copied API sites preserve stages/errno/query ordinal, with no extra query; controller accepts context shape from callback and native adapter wiring remains unqualified',
 'policyFinding':'new diagnosticv2 explicitly separate; saved old two-call failure remains failed and six calls absent; unavailable footprint is never zero',
 'original8ContractPreserved':True,
 'remainingHolds':['complete native callback wiring and direct-child-to-birth binding','valid-last durable bounded sample journal','full original resource-journal validator','total runtime FD ledger','actual bounded Popen duplicate/grant/interrupt fixture','serialized actual watchdog-stop/retire/wait fixture'],
 'subjectEdited':False,'actualFixtureOrNativeQualified':False}
(D/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'report':pin(D/'report.json'),'inputs':checked,'nineControls':len(controls),'birthLoaderNegativesRejected':len(bugs),'normalPositive':True},indent=2))
