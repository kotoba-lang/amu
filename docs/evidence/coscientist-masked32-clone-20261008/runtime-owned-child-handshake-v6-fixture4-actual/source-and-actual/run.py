"""Fixed SOURCE fixture; operations only inside main after exact reviews and GO."""
from pathlib import Path
import json,hashlib,stat,ast,importlib.util,sys,os,time,types,threading,inspect
D=Path(__file__).resolve().parent

def need(q,m):
 if not q:raise AssertionError(m)
def load(p):return json.loads(Path(p).read_bytes())
def rec(p):
 p=Path(p);a=p.lstat();need(stat.S_ISREG(a.st_mode)and not p.is_symlink()and 0<=a.st_size<=33554432,'bounded regular input');b=p.read_bytes();z=p.lstat();need((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns),'immutable input');return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def pin(r):need(rec(r['path'])=={k:r[k]for k in ['bytes','sha256']},'exact receipt');return Path(r['path'])
def save(p,q):
 b=(json.dumps(q,indent=2)+'\n').encode();need(len(b)<=1048576,'finite fixture receipt');t=Path(str(p)+'.pending')
 with t.open('xb',buffering=0)as f:
  v=memoryview(b)
  while v:n=f.write(v);need(type(n)is int and 0<n<=len(v),'complete receipt');v=v[n:]
  os.fsync(f.fileno())
 os.replace(t,p);fd=os.open(str(Path(p).parent),os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
def closure(pr,sp,ip):
 need(type(pr['exactInputFiles'])is int and type(pr['exactInputLogicalBytes'])is int,'integer input counts')
 need(len(ip)==pr['exactInputFiles']<=256 and sum(r['bytes']for r in ip.values())==pr['exactInputLogicalBytes']<=33554432,'exact targeted closure')
 for n,r in sp.items():need(rec(D/n)==r,'source pin')
 for p,r in ip.items():need(rec(p)==r,'input pin')
 return True
GO_KEYS={'status','sourcePinsSHA256','inputPinsSHA256','driverSHA256','preregistrationSHA256','sourceReviews','maximumDirectStarts','outputRoot','noRetry','timingAuthorized','C2','outerHostLaunchRequiresEscalation','diagnosticLoaderBuildProof','diagnosticLoaderArtifact'}
def go_header(g,pr):
 need(set(g)==GO_KEYS and g['status']==pr['rootGOStatus']and g['maximumDirectStarts']==4 and g['outputRoot']==pr['freshOutputRoot']and g['noRetry']is True and g['timingAuthorized']is False and g['C2']is False and g['outerHostLaunchRequiresEscalation']is True,'exact fixture GO');return True

def source_scope(pr):
 S=Path(pr['targetMechanismWorkspace']);pin(pr['targetSourcePins']);pin(pr['targetPreregistration']);target=load(S/'preregistration.json');sp=load(S/'source-pins.json')
 need(target['sourceReviewStatus']=='PASS_SOURCE_ONLY_DIAGNOSTIC_HELD_OWNERSHIP_LOADER_PROTOCOL_PAIRED2_V6','specific V6 subject')
 need([(c['kind'],c['arm'])for c in pr['cases']]==[('normal','OFF'),('normal','ON'),('dup2','OFF'),('blocked','OFF')],'four fixed cases')
 for c in pr['cases']:
  C=Path(c['capsule']);cp=load(pin(c['sourcePins']));p=load(pin(c['preregistration']))
  for n,r in cp.items():need(rec(C/n)==r,'capsule pin')
  for n in cp:
   if n not in ['preregistration.json','run.py']:need(cp[n]==sp[n],'unchanged exact V6 source mechanism')
  need((C/'run.py').read_text()==(S/'run.py').read_text().replace("dict(path=str(D/'kexe_loader_diagnostic.c'),**receipt(D/'kexe_loader_diagnostic.c'))","pr['diagnosticCopiedCSource']"),'exact one loader owner guard adaptation')
  need(p['cases']==[c['case']]and c['case']in target['cases'],'one original fixed case')
  q=json.loads(json.dumps(target));q['cases']=[c['case']];q['freshOutputRoot']=c['outputRoot'];q['environment']['TMPDIR']=c['outputRoot'];q['rootGOStatus']='DELEGATED_ONE_USE_HELD_FIXTURE4_TICKET_V1';q['diagnosticCopiedCSource']=dict(path=str(S/'kexe_loader_diagnostic.c'),**rec(S/'kexe_loader_diagnostic.c'))
  need(p==q,'only capsule namespace/onecase/TMPDIR/ticket change')
  need(c['outputRoot']==str(Path(pr['freshOutputRoot'])/c['id'])and p['loader']==pr['loader'],'fresh exact capsule')
 need(pr['maximumDirectStarts']==4 and pr['maximumGuestForks']==3 and pr['maximumThreadStarts']==10 and pr['maximumAuxiliaryThreadsPerCall']==4 and pr['maximumParentFDs']==44 and pr['maximumOriginalOuterWallSeconds']==30,'fixed resource budget')
 need(pr['C2']is False and pr['runtimeFunctionalCredit']is False and pr['timingAuthorized']is False,'diagnostics only')
 return True

def journal_guard(module,ownershipFile,path):
 """Invoke exact actual native-call branch with a hash-forbidden callback."""
 tree=ast.parse(Path(module.__file__).read_bytes());assignment=next(n for n in ast.walk(tree)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Subscript)and isinstance(t.slice,ast.Constant)and t.slice.value=='ownershipJournal'for t in n.targets))
 need(isinstance(assignment.value,ast.IfExp),'actual journal guard shape')
 def forbidden(*a):raise AssertionError('active writer hash attempted')
 q=eval(compile(ast.fix_missing_locations(ast.Expression(assignment.value)),str(module.__file__),'eval'),{'hfile':forbidden,'oj':path,'ownershipAck':False,'ownershipFile':ownershipFile})
 need(q=={'path':str(path),'status':'UNHASHED_UNCLOSED_WRITER_OWNERSHIP_RETAINED','writerStopAcknowledged':False},'actual guard refuses hash');return q

class OSProxy:
 def __init__(self,original,kind,trace):self.original=original;self.kind=kind;self.trace=trace;self.dups=0;self.waitEntered=False
 def __getattr__(self,k):return getattr(self.original,k)
 def dup(self,fd):
  self.dups+=1
  if self.kind=='dup2'and self.dups==2:self.trace.append({'event':'injected-second-dup-failure'});raise OSError(24,'fixture injected second dup')
  return self.original.dup(fd)
 def kill(self,pid,sig):
  need(not self.waitEntered,'no numeric signal after wait');self.trace.append({'event':'exact-leader-signal','pid':pid,'signal':sig});return self.original.kill(pid,sig)
 def killpg(self,pid,sig):
  need(not self.waitEntered,'no group signal after wait');self.trace.append({'event':'group-signal','pid':pid,'signal':sig});return self.original.killpg(pid,sig)
class PopenProxy:
 def __init__(self,original,osproxy,trace):self.original=original;self.osproxy=osproxy;self.trace=trace;self.starts=0
 def __getattr__(self,k):return getattr(self.original,k)
 def Popen(self,*a,**kw):
  self.starts+=1;need(self.starts==1,'one case process start');p=self.original.Popen(*a,**kw);proxy=self.osproxy;trace=self.trace
  class Handle:
   pid=p.pid;stdout=p.stdout;stderr=p.stderr
   def wait(self,timeout):
    need(not proxy.waitEntered,'one exact leader wait');proxy.waitEntered=True;trace.append({'event':'leader-wait-enter','pid':p.pid})
    try:q=p.wait(timeout=timeout);trace.append({'event':'leader-wait-return','pid':p.pid,'returncode':q});return q
    except BaseException as ex:trace.append({'event':'leader-wait-uncertain','pid':p.pid,'error':repr(ex)});raise
  return Handle()

def load_capsule(C):
 # Sequential fixture; all imported module identities are isolated between cases.
 for n in ['ownership','capture','integration','controller','runtime','callback_contract','artifact_admission','loader_grammar','run']:sys.modules.pop(n,None)
 sys.path.insert(0,str(C));s=importlib.util.spec_from_file_location('fixed_native_fixture',C/'native-call.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);sys.path.pop(0);return m

def run_case(c,pr,g,gp,gr,O):
 C=Path(c['capsule']);P=load(c['preregistration']['path']);case=c['case'];out=Path(c['outputRoot']);need(not out.exists(),'fresh case namespace');out.mkdir();trace=[];rows=[];coord=None;coordinatorErrors=[];coordinatorReceipt={};release=threading.Event();entered=threading.Event();protocols=[]
 # Explicit delegated one-use admission receipt. Copied wrapper checks the
 # original max2 field; this parent fixture permits one invocation per capsule.
 ticket=dict(status=P['rootGOStatus'],maximumLoaderCalls=2,sourcePinsSHA256=c['sourcePins']['sha256'],preregistrationSHA256=c['preregistration']['sha256'],C2=False,runtimeGuestAuthorized=True,timingAuthorized=False,outerHostLaunchRequiresEscalation=True,diagnosticLoaderBuildProof=g['diagnosticLoaderBuildProof'],diagnosticLoaderArtifact=g['diagnosticLoaderArtifact'],delegation={'parentGO':dict(path=str(gp),**gr),'fixtureCase':c['id'],'allowedStarts':1,'originalPaired2Credit':False})
 ticketPath=out/'delegated-ticket.json';save(ticketPath,ticket);t=dict(path=str(ticketPath),**rec(ticketPath))
 seal={k:case[k]for k in ['label','nativeArgv','workload','arm','profile','symbol','offset','arity','native','container','source']};seal.update(format=P['invocationSealVersion'],index=1,rootGO=t,sourcePinsSHA256=c['sourcePins']['sha256'],preregistrationSHA256=c['preregistration']['sha256']);sealPath=out/(case['label']+'.admission.json');save(sealPath,seal);sealSHA=rec(sealPath)['sha256'];sealPath.chmod(0o444)
 m=load_capsule(C);osp=OSProxy(m.os,c['kind'],trace);m.os=osp;m.subprocess=PopenProxy(m.subprocess,osp,trace)
 originalProtocol=m.HeldProtocol
 if c['kind']=='blocked':
  class BarrierProtocol(originalProtocol):
   def __init__(self,*a):
    nonlocal coord
    args=list(a);persist=args[-1];file=inspect.getclosurevars(persist).nonlocals['ownershipFile']
    def wrapped(q):
     if q.get('stage')=='loader-child-exit-held':
      need(not entered.is_set(),'one injected EXIT_HELD stall');entered.set();need(release.wait(max(0,self.deadline-time.monotonic())),'original deadline injected callback release')
     return persist(q) # Real original fsync only after fixture release.
    args[-1]=wrapped;super().__init__(*args);protocols.append(self)
    def coordinator():
     try:
      need(entered.wait(5),'finite coordinator waits for EXIT_HELD');need(time.monotonic()+1<self.deadline,'original deadline still live')
      need(self.worker is not None and self.worker.is_alive()and not self.writer_stop_acknowledged()and not file.closed,'actual blocked live writer')
      retained=[q for q in m.UNACKNOWLEDGED_OWNERSHIP_JOURNALS if q[0]is file and q[1]is self];need(len(retained)==1,'actual strong journal retention')
      q=journal_guard(m,file,out/(case['label']+'.ownership-journal.jsonl'))
      coordinatorReceipt.update(status='ACTUAL_INJECTED_CALLBACK_STALL_GUARD_OBSERVED',workerAlive=True,writerStopAcknowledged=False,journalClosed=False,journalHashGuard=q,retainedJournal=True,kernelFsyncStall=False,originalDeadline=self.deadline,observedBeforeRelease=True)
      save(out/'blocked-guard.json',coordinatorReceipt)
     except BaseException as ex:coordinatorErrors.append(repr(ex))
     finally:release.set()
    coord=threading.Thread(target=coordinator,name='fixed-fixture-coordinator',daemon=False);coord.start()
  m.HeldProtocol=BarrierProtocol
 result=None;error=None
 try:result=m.call(C,out,P,case,rows,save,sealSHA)
 except BaseException as ex:error=repr(ex)
 finally:
  release.set()
  if coord is not None:coord.join(timeout=5)
 need(coord is None or not coord.is_alive(),'coordinator actual death acknowledgment');need(not coordinatorErrors,'coordinator refusal:'+repr(coordinatorErrors));need(len(rows)==1 and rows[0]['state']=='terminal'and rows[0]['waitEntered']is True and rows[0]['waitUncertain']is False,'one exact closed leader');r=rows[0]
 need(r['ownershipWriterStopAcknowledged']is True and not m.UNACKNOWLEDGED_OWNERSHIP_JOURNALS,'no unacknowledged writer on terminal qualification')
 need(trace[-1]['event']=='leader-wait-return'and sum(x['event']=='leader-wait-enter'for x in trace)==1,'onewait/no postsignal')
 if c['kind']=='dup2':
  need(error is not None and result is None and r['returncode']==-9 and r['childWaitReceipt']is None and r['ownershipBindings']=={}and r['memorySamples']==0,'exact pre-TICKET refusal/closed kill')
  need(osp.dups==2 and [x['event']for x in trace]==['injected-second-dup-failure','exact-leader-signal','leader-wait-enter','leader-wait-return'],'exact source pre-TICKET cleanup chronology')
  need(pin(dict(path=str(out/(case['label']+'.ownership-journal.jsonl')),**r['ownershipJournal'])).stat().st_size==0,'no ownership protocol bytes')
 else:
  need(error is None and result is not None and r['returncode']==0 and r['childWaitReceipt']['exit']==0,'normal exact child/leader wait0');need(result['report']['result']==1,'original actual result')
  need(len(r['ownershipBindings'])==2 and r['controllerObservation']['memoryAdmissionRecord']['groupOperationsAfterWait']==0,'exact held two births/no postwaitquery')
  if c['kind']=='blocked':need(coordinatorReceipt.get('observedBeforeRelease')is True and protocols[0].writer_stop_acknowledged(),'guard before release plus final worker death')
 saved=dict(id=c['id'],kind=c['kind'],result=result,error=error,trace=trace,attempt=dict(path=str(out/'attempts.json'),**rec(out/'attempts.json')),delegatedTicket=t,coordinator=coordinatorReceipt,preTicketGuestZeroIsConditionalSourceProtocol=(c['kind']=='dup2'),actualKernelForkCounterQualified=False)
 save(out/'fixture-case.json',saved);return saved

def main(goPath):
 pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');g=load(goPath);gp=Path(goPath);gr=rec(gp);go_header(g,pr)
 for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256')]:need(rec(D/n)['sha256']==g[k],'exact reviewed fixture source')
 need(len(g['sourceReviews'])==2 and len({r['path']for r in g['sourceReviews']})==2,'two independent SOURCE reviews')
 for r in g['sourceReviews']:
  q=load(pin(r));need(q['status']==pr['sourceReviewStatus']and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256']),'specific fixture SOURCE review')
 build=load(pin(g['diagnosticLoaderBuildProof']));pin(g['diagnosticLoaderArtifact']);target=load(pr['targetPreregistration']['path'])
 need(build['status']==pr['loaderBuildIdentityStatus']and build['artifact']==g['diagnosticLoaderArtifact']and build['artifact']['path']==pr['loader']and build['compileArgv']==target['prospectiveLoaderBuildArgv']and build['closedBuildCalls']==1 and build['noRetry']is True and build['copiedCSource']==dict(path=str(Path(pr['targetMechanismWorkspace'])/'kexe_loader_diagnostic.c'),**rec(Path(pr['targetMechanismWorkspace'])/'kexe_loader_diagnostic.c'))and build['originalCSource']==target['originalLoaderCSource']and build['compileFlag']=='KEXE_OWNERSHIP_DIAGNOSTIC_V3','exact fresh V6 build proof')
 O=Path(pr['freshOutputRoot']);need(not O.exists(),'fresh fixture output/no retry');closure(pr,sp,ip);source_scope(pr);O.mkdir();deadline=time.monotonic()+300;results=[];started=[];ok=False
 def guard():need(rec(gp)==gr,'immutable topGO');closure(pr,sp,ip);source_scope(pr);pin(g['diagnosticLoaderBuildProof']);pin(g['diagnosticLoaderArtifact'])
 try:
  for c in pr['cases']:
   guard();need(len(started)<4 and time.monotonic()+60<=deadline,'finite remaining campaign');started.append(c['id']);save(O/'started-cases.json',started);results.append(run_case(c,pr,g,gp,gr,O));save(O/'results.json',results)
  guard();need(len(results)==len(started)==4,'four closed finite cases');need(results[0]['result']['report']==results[1]['result']['report']and results[0]['result']['arena']==results[1]['result']['arena'],'normal original OFF/ON fullfuel17arena parity');ok=True
 except BaseException as ex:save(O/'failure.json',dict(error=repr(ex),completedCases=len(results),noRetry=True));raise
 finally:save(O/'terminal.json',dict(startedCases=started,completedCases=len(results),failure=not ok,noRetry=True,missingCaseClosureIsRefusal=True))
 save(O/'report.json',dict(status='COMPLETE_FIXED_HELD_LAUNCH_V6_DIAGNOSTIC_FIXTURE4_ONLY',sourcePinsSHA256=g['sourcePinsSHA256'],targetSourcePinsSHA256=pr['targetSourcePins']['sha256'],closedDirectStarts=4,maximumGuestForks=3,sourceDerivedGuestZeroNegative=True,actualForkCounterQualified=False,original95FunctionalCredit=False,performanceQualified=False,hardPeakQualified=False,actualKernelFsyncStall=False,results=results,rootGO=dict(path=str(gp),**gr)))
if __name__=='__main__':
 need(len(sys.argv)==2,'one fixed root GO');main(sys.argv[1])
