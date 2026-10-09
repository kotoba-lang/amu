"""Injected dictionaries only. No actual threads, capture, child, pipe or API calls."""
from pathlib import Path
import ast,sys,copy,json,importlib.util
A=Path(__file__).resolve().parent;S=Path('/Users/junkawasaki/github/workspaces/codex/current17-consumer-qualify342-source-v2-20261009-dense');sys.dont_write_bytecode=True;sys.path.insert(0,str(S))
spec=importlib.util.spec_from_file_location('offline342',A/'audit_saved.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from integration import classify_memory,MEMORY_POLICY
ast.parse((A/'audit_saved.py').read_text(),feature_version=(3,9))
record=dict(policy=MEMORY_POLICY,failure=None,acceptedSamples=2,acceptedLeaderBirthBound=True,otherRefusals=[],completePipeEOF=True,stoppedClosedCapture=True,rawTruncated=False,captureErrors=[],exactDirectChildWait='closed0',waitUncertain=False,withinOriginalDeadline=True,groupAuthorityRetired=True,groupOperationsAfterUncertainty=0,groupOperationsAfterWait=0,loaderWaitProtocolPinned=True,heldOwnershipQualified=True,exactHeldChildWait0=True,initialHeldSamples=2,freshKnownFailureVerified=False)
out=b'x';err=b'y';a=dict(pid=10,stdout=dict(bytes=1,sha256=m.digest(out)),stderr=dict(bytes=1,sha256=m.digest(err)),memorySamples=2)
cap=dict(EOF={'stdout':True,'stderr':True},completeRaw=True,stoppedWriter=True,semanticDecodeAuthorized=True,ownershipDecision='worker-granted',errors=[],dropped={'stdout':0,'stderr':0},hashes={'stdout':a['stdout'],'stderr':a['stderr']},retained={'stdout':1,'stderr':1},observedBytes=2,firstFailure=None)
ev=['group-operation','group-operation','retire:owned-child-exit-before-reap-ACK','retire:before-watchdog-stop-and-wait','wait-enter'];o=dict(semanticQualification=True,sampleReceiptPersistenceQualified=True,memoryAdmissionRecord=record,capture=cap,sampleCount=2,directChildWait='closed0',waitUncertain=False,controllerEvents=ev,status='COMPLETE_HELD_LAUNCH_SEMANTIC_SAMPLED_MEMORY',strictHeldSamplingPolicyPassed=True,memoryObservation=classify_memory(record));rows=[[1,1000,10,[[10,100,64]]],[2,2000,10,[[10,100,64],[20,200,32]]]];bindings={10:100,20:200};assert m.memory(o,a,rows,out,err,bindings,'i')==(96,True)
n=0
def refuses(f):
 global n
 try:f()
 except(AssertionError,KeyError,ValueError,TypeError):n+=1;return
 raise AssertionError('mutant admitted')
for k,v in [('exactHeldChildWait0',False),('groupOperationsAfterWait',1),('withinOriginalDeadline',False),('otherRefusals',['unknown'])]:
 q=copy.deepcopy(o);q['memoryAdmissionRecord'][k]=v;refuses(lambda:m.memory(q,a,rows,out,err,bindings,'i'))
q=copy.deepcopy(o);q['capture']['stoppedWriter']=False;refuses(lambda:m.memory(q,a,rows,out,err,bindings,'i'))
q=copy.deepcopy(o);q['controllerEvents'].append('group-operation');refuses(lambda:m.memory(q,a,rows,out,err,bindings,'i'))
r=copy.deepcopy(rows);r[1][3][1][1]+=1;refuses(lambda:m.memory(o,a,r,out,err,bindings,'i'))
gap=copy.deepcopy(o);f=dict(typedOrigin='fresh-owned-group-api-v1',contextVersion='owned-group-sampling-failure-context-v1',invocation='i',queryOrdinal=21,pid=20,stage='member-getpgid',errno=3,failureClass='kernel-oserror');gap['memoryAdmissionRecord'].update(failure=f,freshKnownFailureVerified=True);gap.update(status='HELD_LAUNCH_SEMANTIC_TERMINATION_GAP',strictHeldSamplingPolicyPassed=False,memoryObservation=classify_memory(gap['memoryAdmissionRecord']));gap['capture']['firstFailure']='sampling-uncertainty';gap['controllerEvents'].insert(2,'group-operation');gap['controllerEvents'].insert(3,'retire:group-exception-atomic');assert m.memory(gap,a,rows,out,err,bindings,'i')==(96,False)
for k,v in [('pid',99),('errno',1),('invocation','foreign'),('stage','unknown')]:
 q=copy.deepcopy(gap);q['memoryAdmissionRecord']['failure'][k]=v;refuses(lambda:m.memory(q,a,rows,out,err,bindings,'i'))
print(json.dumps(dict(strictModelPositive=1,typedGapModelPositive=1,refusals=n,Python39AST=1,actualEvidenceAudited=False,actualCalls=0),sort_keys=True))
