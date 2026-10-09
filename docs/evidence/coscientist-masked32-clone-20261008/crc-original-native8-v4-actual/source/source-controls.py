"""Pure controller/provenance fixtures. No actual kernel/FD/thread/Popen calls."""
from pathlib import Path
import json,ast
from controller import Controller
D=Path(__file__).resolve().parent
ns={'__name__':'injected_typed_adapter'};exec(compile((D/'typed-adapter.py').read_bytes(),'typed-adapter.py','exec'),ns)
API=ns['DarwinOwnedGroupAPI'];Fault=ns['SamplingFault']
api=API.__new__(API);api.queryOrdinal=0;api.lastAttempt=None
def esrch(pid):raise ProcessLookupError(3,'injected')
try:api.attempt('leader-getpgid',11,esrch,11)
except Fault as ex:
 context=ex.context;assert context['errno']==3 and context['pid']==11 and context['queryOrdinal']==1 and context['contextVersion']==ns['CONTEXT_VERSION']
else:raise AssertionError('typed failure missing')
assert api.queryOrdinal==1 # No followup probe to classify the exception.
class Clock:
 def __init__(self):self.t=0
 def __call__(self):return self.t
 def pause(self,dt):self.t+=dt
class Flag:
 def __init__(self):self.value=False
 def is_set(self):return self.value
class Capture:
 def __init__(self,partial=False):self.stopped=Flag();self.partial=partial;self.firstFailure=None
 def refuse(self,r):
  if self.firstFailure is None:self.firstFailure=r
 def join_once(self,t):self.stopped.value=True;return True
 def snapshot(self):return {'stoppedWriter':self.stopped.value,'completeRaw':not self.partial,'errors':[],'EOF':{'stdout':not self.partial,'stderr':True},'dropped':{'stdout':0,'stderr':0},'firstFailure':self.firstFailure}
class Sampler:
 def __init__(self,context,policy=False):self.n=0;self.context=context;self.policy=policy
 def sample(self):
  self.n+=1
  if self.n==1:return {'ownedPGID':11,'members':[{'pid':11,'start':22}]}
  if self.policy:raise ns['Refusal']('threshold exceeded')
  raise Fault(self.context)
def test(kind):
 clock=Clock();ctl=Controller(clock,1);cap=Capture(partial=kind=='partial');ctx=dict(context)
 if kind=='wrong-errno':ctx['errno']=1
 if kind=='unknown-pid':ctx['pid']=77
 if kind=='unknown-stage':ctx['stage']='group-list'
 if kind=='missing-version':ctx['contextVersion']='old'
 def wait(t):
  if kind=='wait-uncertain':raise TimeoutError('injected')
  return 0
 q=ctl.observe(cap,Sampler(ctx,policy=kind=='threshold'),wait,lambda t:True,clock.pause,lambda r:True,lambda:kind!='bad-journal',{'pid':11,'birth':22},True)
 assert q['strictOldMemoryPolicyPassed']is False and q['nativeControllerWiringQualified']is False
 if kind=='gap':assert q['status']=='SEMANTIC_DIAGNOSTIC_TERMINATION_GAP'and q['memoryObservation']['missingFootprint']is None
 else:assert q['status']=='REFUSE'
 try:ctl.group(lambda:None)
 except AssertionError:pass
 else:raise AssertionError('retired authority restored')
 try:ctl.wait(wait)
 except AssertionError:pass
 else:raise AssertionError('second wait admitted')
for kind in ['gap','wrong-errno','unknown-pid','unknown-stage','missing-version','partial','threshold','wait-uncertain','bad-journal']:test(kind)
for mode in ['valid','missing-birth','wrong-birth','loader-false']:
 clock=Clock();ctl=Controller(clock,1);cap=Capture()
 class NormalSampler:
  def sample(self):
   cap.stopped.value=True
   return {'ownedPGID':11,'members':[{'pid':11,'start':22}]}
 binding=None if mode=='missing-birth'else{'pid':11,'birth':23 if mode=='wrong-birth'else 22}
 q=ctl.observe(cap,NormalSampler(),lambda t:0,lambda t:True,clock.pause,lambda r:True,lambda:True,binding,mode!='loader-false')
 if mode=='valid':assert q['strictOldMemoryPolicyPassed']is True and q['status']=='COMPLETE_SEMANTIC_SAMPLED_MEMORY'
 else:assert q['status']=='REFUSE'and q['strictOldMemoryPolicyPassed']is False and q['semanticQualification']is False
 assert q['nativeControllerWiringQualified']is False
for mode in ['watchdog-no-ack','capture-no-ack','transfer-first-failure']:
 clock=Clock();ctl=Controller(clock,1);cap=Capture();waits=[]
 class Normal:
  def sample(self):cap.stopped.value=True;return {'ownedPGID':11,'members':[{'pid':11,'start':22}]}
 if mode=='capture-no-ack':cap.join_once=lambda t:False
 if mode=='transfer-first-failure':cap.firstFailure='pipe-transfer-failure'
 result=ctl.observe(cap,Normal(),lambda t:waits.append(t)or 0,lambda t:mode!='watchdog-no-ack',clock.pause,lambda r:True,lambda:True,{'pid':11,'birth':22},True,lambda q:True)
 assert waits and len(waits)==1 and result['status']=='REFUSE'and not result['strictOldMemoryPolicyPassed']
ctl=Controller(lambda:0,1)
try:ctl.group(lambda:(_ for _ in ()).throw(ValueError('atomic callback failure')))
except ValueError:assert not ctl.active
else:raise AssertionError('callback failure absent')
from runtime import parse_report,counters
old=D.parent/'crc-table-decision-collapse-original-crc-guest8-source-v1-20261009-dense/run-outputs'
raw=(old/'prefix-crc-1-off.stdout').read_bytes();err=(old/'prefix-crc-1-off.stderr').read_bytes()
assert parse_report(raw)['result']==3523407757 and parse_report(raw)['remainingFuel']==999996
assert counters(err)['status']=='valid'and len(counters(err)['values'])==17
for bad in [err+b'EXTRA\n',b'EXTRA\n'+err]:assert counters(bad)['status']!='valid'
for bad in [raw+b'EXTRA\n',b'EXTRA\n'+raw]:
 try:parse_report(bad)
 except AssertionError:pass
 else:raise AssertionError('extra stdout admitted')
import importlib.util
spec=importlib.util.spec_from_file_location('inert_native_call',D/'native-call.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
import json
pr=json.loads((D/'preregistration.json').read_bytes())
assert module.resource_journal(old/'prefix-crc-1-off.limit-journal.jsonl',pr,pr['cases'][0]['nativeArgv'])is True
exec(compile((D/'transfer-controls.py').read_bytes(),'transfer-controls.py','exec'),{'__name__':'injected_transfer_controls','__file__':str(D/'transfer-controls.py')})
for p in D.glob('*.py'):ast.parse(p.read_text())
q={'status':'PASS_PURE_TYPED_CONTROLLER_SOURCE_ONLY','controllerCases':16,'atomicCallbackRetirementControls':1,'savedCompleteDecoderControls':2,'extraRawNegativeControls':4,'savedResourceJournalControl':1,'noFailureBindingNegativeControls':3,'typedProvenanceFaultCalls':1,'extraKernelQueries':0,'actualFDCalls':0,'actualThreads':0,'actualPopen':0,'nativeCalls':0,'sampleReceiptPersistenceQualified':False,'nativeControllerWiringQualified':False}
(D/'source-controls.json').write_text(json.dumps(q,indent=2)+'\n')
