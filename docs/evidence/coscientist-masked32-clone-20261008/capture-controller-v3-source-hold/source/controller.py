"""Injectable SOURCE controller. No Popen/group/native invocation at import."""
import threading
from integration import classify_memory,MEMORY_POLICY
class Controller:
 def __init__(self,clock,deadline,maximumEvents=4096):
  self.clock=clock;self.deadline=deadline;self.lock=threading.Lock();self.active=True;self.waitEntered=False;self.waitUncertain=False;self.events=[];self.maxEvents=maximumEvents
 def record(self,event):
  assert len(self.events)<self.maxEvents,'finite controller event budget'
  self.events.append(event)
 def group(self,fn):
  with self.lock:
   assert self.active and not self.waitEntered and not self.waitUncertain,'retired group authority'
   assert len(self.events)<self.maxEvents-8,'controller query budget; retirement reserve'
   self.record('group-operation');return fn()
 def retire(self,reason):
  with self.lock:self.active=False;self.record('retire:'+reason)
 def wait(self,fn):
  with self.lock:
   assert not self.waitEntered and not self.waitUncertain
   self.active=False;self.waitEntered=True;self.record('wait-enter')
  try:return fn(max(0,self.deadline-self.clock()))
  except BaseException:
   self.waitUncertain=True;self.record('wait-uncertain');raise
 def observe(self,capture,sampler,waitDirect,stopWatchdog,pause,validateCompleteRaw,validateResourceJournal,leaderBirthBound,loaderProtocolPinned):
  """Capture must already own dup reads; caller launch/transfer remains separate."""
  samples=[];failure=None;other=[];waitStatus='unavailable';watchdogStopped=False
  try:
   while not capture.stopped.is_set() and self.clock()<self.deadline:
    try:
     q=self.group(sampler.sample);assert len(samples)<90502,'memory receipt budget';samples.append(q)
    except BaseException as ex:
     context=getattr(ex,'context',None)
     failure=context if isinstance(context,dict)else{'typedOrigin':'untyped-or-policy-refusal','errno':None,'stage':'unavailable'}
     if context is None:other.append(type(ex).__name__)
     self.retire('sampling-uncertainty');capture.refuse('sampling-uncertainty');break
    pause(min(.02,max(0,self.deadline-self.clock())))
   if self.clock()>=self.deadline:other.append('outer-deadline');capture.refuse('outer-deadline')
  finally:
   self.retire('before-watchdog-stop-and-wait')
   try:watchdogStopped=stopWatchdog(max(0,self.deadline-self.clock()))is True
   except BaseException as ex:other.append('watchdog-stop:'+type(ex).__name__)
  if not watchdogStopped:return {'status':'REFUSE_WATCHDOG_STOP_ACK','strictOldMemoryPolicyPassed':False,'capture':capture.snapshot(),'otherRefusals':other}
  if not capture.join_once(max(0,self.deadline-self.clock())):
   return {'status':'REFUSE_CAPTURE_STOP_ACK','strictOldMemoryPolicyPassed':False,'capture':capture.snapshot(),'otherRefusals':other}
  raw=capture.snapshot()
  try:
   rc=self.wait(waitDirect);waitStatus='closed0'if rc==0 else'closed-other'
  except BaseException as ex:other.append('direct-wait:'+type(ex).__name__)
  completeExpected=False;resources=False
  if raw['stoppedWriter']and raw['completeRaw']and not raw['errors']:
   try:completeExpected=validateCompleteRaw(raw)is True;resources=validateResourceJournal()is True
   except BaseException as ex:other.append('validation:'+type(ex).__name__)
  if not resources:other.append('resource-journal-unqualified')
  bound=False
  if isinstance(leaderBirthBound,dict)and set(leaderBirthBound)=={'pid','birth'}and samples:
   pid,birth=leaderBirthBound['pid'],leaderBirthBound['birth']
   bound=type(pid)is int and pid>0 and type(birth)is int and birth>0 and all(q.get('ownedPGID')==pid and [(m.get('pid'),m.get('start'))for m in q.get('members',[])if m.get('pid')==pid]==[(pid,birth)]for q in samples)
  if failure is not None and samples:
   acceptedPIDs={m['pid']for q in samples for m in q.get('members',[])}
   if failure.get('pid')not in acceptedPIDs:other.append('failure-pid-not-previously-bound')
  record={'policy':MEMORY_POLICY,'failure':failure,'acceptedSamples':len(samples),'acceptedLeaderBirthBound':bound,'otherRefusals':other,'completePipeEOF':all(raw['EOF'].values()),'stoppedClosedCapture':raw['stoppedWriter'],'rawTruncated':any(raw['dropped'].values()),'captureErrors':raw['errors'],'exactDirectChildWait':waitStatus,'waitUncertain':self.waitUncertain,'withinOriginalDeadline':self.clock()<self.deadline,'groupAuthorityRetired':not self.active,'groupOperationsAfterUncertainty':0,'groupOperationsAfterWait':0,'loaderWaitProtocolPinned':loaderProtocolPinned is True}
  memory=classify_memory(record)
  semantic=completeExpected and resources and bound and loaderProtocolPinned is True and waitStatus=='closed0'and not self.waitUncertain and not other and self.clock()<self.deadline
  # No samples cannot be admitted by absence of a typed failure.
  strict=semantic and failure is None and len(samples)>0
  diagnostic=semantic and memory['status']=='termination-gap-unavailable'
  return {'status':'SEMANTIC_DIAGNOSTIC_TERMINATION_GAP'if diagnostic else'COMPLETE_SEMANTIC_SAMPLED_MEMORY'if strict else'REFUSE','semanticQualification':semantic,'strictOldMemoryPolicyPassed':strict,'memoryObservation':memory,'capture':raw,'sampleCount':len(samples),'sampleReceiptPersistenceQualified':False,'controllerEvents':self.events,'nativeControllerWiringQualified':False}
