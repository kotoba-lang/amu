from pathlib import Path
import json
D=Path(__file__).resolve().parent;B=D.parent/'published-mode2-x8-g4-original19-runtime190-source-v1-20261009-root'
for n in ['capture.py','callback_contract.py','loader_grammar.py','runtime.py']:(D/n).write_bytes((B/n).read_bytes())
s=(B/'typed-adapter.py').read_text().replace('def __init__(self):','def __init__(self,invocation):',1).replace('self.queryOrdinal=0;self.lastAttempt=None;self.getpgid=os.getpgid','self.invocation=invocation;self.queryOrdinal=0;self.lastAttempt=None;self.getpgid=os.getpgid').replace("'typedOrigin':'fresh-owned-group-api-v1','stage':stage","'typedOrigin':'fresh-owned-group-api-v1','invocation':self.invocation,'stage':stage")
(D/'typed-adapter.py').write_text(s)
s=(B/'integration.py').read_text();s=s[:s.index("MEMORY_POLICY=")]+'''from ownership import POLICY
MEMORY_POLICY=POLICY
ALLOWED_ESRCH_STAGES={'leader-getpgid','member-getpgid','member-rusage'}
def classify_memory(record):
 assert record['policy']==MEMORY_POLICY
 owned=(record['heldOwnershipQualified']is True and record['exactHeldChildWait0']is True and record['initialHeldSamples']==2 and record['acceptedLeaderBirthBound']is True and record['acceptedSamples']>=2 and record['otherRefusals']==[] and record['completePipeEOF']is True and record['stoppedClosedCapture']is True and record['rawTruncated']is False and record['captureErrors']==[] and record['exactDirectChildWait']=='closed0'and record['waitUncertain']is False and record['withinOriginalDeadline']is True and record['groupAuthorityRetired']is True and record['groupOperationsAfterWait']==record['groupOperationsAfterUncertainty']==0 and record['loaderWaitProtocolPinned']is True)
 if not owned:return {'status':'refused','hardPeakQualified':False}
 if record['failure']is None:return {'status':'held-launch-sampled-observations-only','hardPeakQualified':False,'sampleCompleteness':'finite-samples-only'}
 if record['freshKnownFailureVerified']is True:return {'status':'held-launch-owned-termination-gap','missingFootprint':None,'zeroSynthesized':False,'hardPeakQualified':False,'sampleCompleteness':'gap-unavailable'}
 return {'status':'refused','hardPeakQualified':False}
''';(D/'integration.py').write_text(s)
s=(B/'controller.py').read_text().replace('persistSample=None):','persistSample=None,initialSamples=None,ownershipState=None,validateFailureContext=None):').replace('samples=[];failure=None;other=[];',"samples=list(initialSamples or []);assert len(samples)==2;failure=None;other=[];freshFault=False;")
s=s.replace("if context is None:other.append(type(ex).__name__)","if context is None:other.append(type(ex).__name__)\n     else:\n      try:freshFault=validateFailureContext(context)is True\n      except BaseException:other.append('current-owned-fault-unqualified')")
s=s.replace("memory=classify_memory(record)","record.update(heldOwnershipQualified=ownershipState.get('qualified')is True,exactHeldChildWait0=ownershipState.get('childWait0')is True,initialHeldSamples=len(initialSamples or []),freshKnownFailureVerified=freshFault)\n  memory=classify_memory(record)")
s=s.replace("strict=semantic and failure is None and len(samples)>0","semantic=semantic and ownershipState.get('qualified')is True and ownershipState.get('childWait0')is True\n  strict=semantic and failure is None and len(samples)>=2")
s=s.replace("memory['status']=='termination-gap-unavailable'","memory['status']=='held-launch-owned-termination-gap'").replace("'SEMANTIC_DIAGNOSTIC_TERMINATION_GAP'","'HELD_LAUNCH_SEMANTIC_TERMINATION_GAP'").replace("'COMPLETE_SEMANTIC_SAMPLED_MEMORY'","'COMPLETE_HELD_LAUNCH_SEMANTIC_SAMPLED_MEMORY'")
(D/'controller.py').write_text(s)
(D/'artifact_admission.py').write_text('''"""New diagnostic ownership policy only; no old policy success alias."""
from integration import classify_memory,MEMORY_POLICY
def accept_artifact_observation(o):
 assert o['semanticQualification']is True and o['sampleReceiptPersistenceQualified']is True
 r=o['memoryAdmissionRecord'];assert r['policy']==MEMORY_POLICY and r['heldOwnershipQualified']is True and r['exactHeldChildWait0']is True and r['initialHeldSamples']==2 and r['otherRefusals']==[]
 assert o['memoryObservation']==classify_memory(r)
 if o['status']=='COMPLETE_HELD_LAUNCH_SEMANTIC_SAMPLED_MEMORY':
  assert r['failure']is None and o['strictOldMemoryPolicyPassed']is True and o['memoryObservation']['status']=='held-launch-sampled-observations-only';return True
 assert o['status']=='HELD_LAUNCH_SEMANTIC_TERMINATION_GAP'and o['strictOldMemoryPolicyPassed']is False and r['freshKnownFailureVerified']is True and o['memoryObservation']['status']=='held-launch-owned-termination-gap';return True
''')
s=(B/'native-call.py').read_text().replace('import os,json,time,threading,subprocess,hashlib,importlib.util','import os,json,time,threading,subprocess,hashlib,importlib.util,socket\nfrom ownership import HeldProtocol,validate_failure')
s=s.replace("len(rows)<190","len(rows)<2").replace("api=mod.DarwinOwnedGroupAPI()","invocation=admissionSHA256;api=mod.DarwinOwnedGroupAPI(invocation)")
s=s.replace('proc=None;cap=None;ctl=None;', 'peer=None;host=None;protocol=None;ownershipState={};proc=None;cap=None;ctl=None;')
s=s.replace("with lj.open('xb',buffering=0)as limitFile,mj.open('xb',buffering=0)as memoryFile:","oj=base.with_suffix('.ownership-journal.jsonl');ownershipBytes=0\n with lj.open('xb',buffering=0)as limitFile,mj.open('xb',buffering=0)as memoryFile,oj.open('xb',buffering=0)as ownershipFile:")
s=s.replace('  def validateRaw(raw):',"  def persistOwnership(q):\n   nonlocal ownershipBytes\n   ownershipBytes=persist_jsonline(ownershipFile,q,ownershipBytes,65536);return True\n  def qualifiedResources():\n   need(protocol is not None and protocol.finish()is True,'exact childwait0');ownershipState.update(qualified=True,childWait0=True)\n   return resource_journal(lj,pr,case['nativeArgv'])\n  def validateRaw(raw):")
s=s.replace("need(len(os.listdir('/dev/fd'))<=32","need(len(os.listdir('/dev/fd'))<=32")
s=s.replace("   argv=[pr['interpreter']['path']", "   host,peer=socket.socketpair();host.setblocking(False);peer.setblocking(False)\n   argv=[pr['interpreter']['path']")
s=s.replace("'--admission-sha',admissionSHA256,'--'","'--admission-sha',admissionSHA256,'--ownership-fd',str(peer.fileno()),'--'")
s=s.replace('pass_fds=(limitFile.fileno(),)', 'pass_fds=(limitFile.fileno(),peer.fileno())')
s=s.replace("r['pid']=proc.pid;ctl=Controller", "peer.close();peer=None;r['pid']=proc.pid;ctl=Controller")
s=s.replace("   observed=ctl.observe", "   seal=json.loads((O/(case['label']+'.admission.json')).read_bytes());nonce=hashlib.sha256((admissionSHA256+seal['rootGO']['sha256']).encode()).hexdigest()\n   protocol=HeldProtocol(host,proc.pid,deadline,seal['rootGO']['sha256'],nonce,persistOwnership)\n   initial=protocol.handshake(ctl,sampler,persistSample);protocol.start_wait()\n   fault=lambda context:validate_failure(context,api,protocol.bindings,proc.pid,invocation)\n   observed=ctl.observe")
s=s.replace("lambda:resource_journal(lj,pr,case['nativeArgv']),birthBinding,True,persistSample)","qualifiedResources,birthBinding,True,persistSample,initial,ownershipState,fault)")
s=s.replace('   for file in [limitFile,memoryFile]:',"   try:\n    if protocol is not None:protocol.close()\n    elif host is not None:host.close()\n    if peer is not None:peer.close()\n   except BaseException as ex:failure=failure or'ownership-cleanup:'+repr(ex)\n   for file in [limitFile,memoryFile,ownershipFile]:")
s=s.replace(" r['limitJournal']=hfile(lj,65536)"," r['ownershipJournal']=hfile(oj,65536);r['ownershipBindings']=protocol.bindings if protocol else{};r['childWaitReceipt']=protocol.waitReceipt if protocol else None\n r['limitJournal']=hfile(lj,65536)")
(D/'native-call.py').write_text(s)
