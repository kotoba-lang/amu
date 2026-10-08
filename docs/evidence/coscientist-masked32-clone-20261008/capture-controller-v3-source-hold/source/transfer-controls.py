"""Pure injected transfer/provenance controls; no actual FD/thread/process calls."""
from pathlib import Path
import json,copy,ast
from integration import *
D=Path(__file__).resolve().parent
class Stream:
 def __init__(self,fd):self.fd=fd;self.closed=False;self.closes=0
 def fileno(self):assert not self.closed;return self.fd
 def close(self):
  if not self.closed:self.closes+=1;self.closed=True
class Cap:
 def __init__(self,reads,grant_interrupt=False,stop=True):self.reads=reads;self.state='pending';self.grant_interrupt=grant_interrupt;self.stop=stop;self.joins=0
 def grant(self):
  self.state='granted'
  if self.grant_interrupt:raise KeyboardInterrupt('after-grant')
 def deny_pending(self):
  if self.state=='pending':self.state='denied'
  return self.state=='denied'
 def refuse(self,reason):self.refusal=reason
 def join_once(self,budget):self.joins+=1;return self.stop
def transfer_test(mode):
 streams={k:Stream(fd)for k,fd in [('stdout',1),('stderr',2)]};dups=[];closed=[];box=[]
 def duplicate(fd):
  if mode=='second-dup'and fd==2:raise OSError('injected duplicate failure')
  d=fd+10;dups.append(d);return d
 def construct(reads):
  if mode=='construct':raise ValueError('constructor')
  c=Cap(reads,grant_interrupt=mode.startswith('grant'),stop=mode!='grant-no-ack');box.append(c);return c
 def start(c):
  if mode=='ambiguous-start':raise KeyboardInterrupt('ambiguous')
 try:
  cap=transfer_popen_reads(streams,duplicate,closed.append,construct,start,1,lambda:0)
  assert mode=='normal'and cap.state=='granted'and not closed
 except TransferFailure as ex:
  assert mode!='normal'
  if mode.startswith('grant'):
   assert ex.readOwnership=='worker-granted'and closed==[]and ex.capture.joins==1
   assert ('worker-stop-ack-unavailable'in ex.cleanup)==(mode=='grant-no-ack')
  else:assert sorted(closed)==sorted(dups)and ex.readOwnership=='parent-denied'
 assert all(s.closed and s.closes==1 for s in streams.values())
 # Later Popen wrapper cleanup cannot close reused duplicate FD numbers.
 for s in streams.values():s.close()
 assert all(s.closes==1 for s in streams.values())
for mode in ['normal','second-dup','construct','ambiguous-start','grant-ack','grant-no-ack']:transfer_test(mode)
r={'policy':MEMORY_POLICY,'failure':{'typedOrigin':'fresh-owned-group-api-v1','errno':3,'stage':'leader-getpgid','contextVersion':'owned-group-sampling-failure-context-v1','failureClass':'kernel-oserror','queryOrdinal':2},'acceptedSamples':1,'acceptedLeaderBirthBound':True,'otherRefusals':[],'completePipeEOF':True,'stoppedClosedCapture':True,'rawTruncated':False,'captureErrors':[],'exactDirectChildWait':'closed0','waitUncertain':False,'withinOriginalDeadline':True,'groupAuthorityRetired':True,'groupOperationsAfterUncertainty':0,'groupOperationsAfterWait':0,'loaderWaitProtocolPinned':True}
assert classify_memory(r)['status']=='termination-gap-unavailable'
mutations={'acceptedSamples':0,'acceptedLeaderBirthBound':False,'otherRefusals':['threshold-exceeded'],'completePipeEOF':False,'stoppedClosedCapture':False,'rawTruncated':True,'captureErrors':['fsync'],'exactDirectChildWait':'closed1','waitUncertain':True,'withinOriginalDeadline':False,'groupAuthorityRetired':False,'groupOperationsAfterUncertainty':1,'groupOperationsAfterWait':1,'loaderWaitProtocolPinned':False}
for key,value in mutations.items():
 c=copy.deepcopy(r);c[key]=value;assert classify_memory(c)['status']=='refused'
for failure in [{'errno':1,'stage':'leader-getpgid'},{'errno':3,'stage':'unknown'},{'errno':3,'stage':'member-rusage','typedOrigin':'historical-untyped'}]:
 c=copy.deepcopy(r);c['failure']=failure;assert classify_memory(c)['status']=='refused'
for p in D.glob('*.py'):ast.parse(p.read_text())
q={'status':'PASS_PURE_SOURCE_INTEGRATION_CONTROLS_ONLY','transferCases':6,'memoryAdmissionNegativeControls':17,'actualFDCalls':0,'actualThreads':0,'nativeCalls':0,'runtimeIntegrationQualified':False}
(D/'transfer-controls.json').write_text(json.dumps(q,indent=2)+'\n')
