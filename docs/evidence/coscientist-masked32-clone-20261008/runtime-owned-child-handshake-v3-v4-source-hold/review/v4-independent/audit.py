"""SOURCE/read-only and inert injected setup/cleanup AST only; no APIs."""
from pathlib import Path
import json,ast,hashlib,stat,runpy,sys,types,io,contextlib
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'current-runtime-process-ownership-race-source-v4-20261009-independent';B=W/'current-runtime-process-ownership-race-source-v3-20261009-crc';Q=Path(__file__).parent

def rec(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size<=33554432;b=p.read_bytes();z=p.lstat();assert(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns);return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def pins():
 sp=json.loads((D/'source-pins.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes());assert len(sp)==24 and len(ip)==34 and sum(v['bytes']for v in ip.values())==1504693
 for n,v in sp.items():assert rec(D/n)==v,n
 for p,v in ip.items():assert rec(p)==v,p
 return sp,ip
sp,ip=pins();pr=json.loads((D/'preregistration.json').read_bytes());assert rec(D/'source-pins.json')['sha256']=='ccda4f7a66edcf6c30b8da7c006bf7018ebb50219fed244fc48502f958e9e91e'
for n in ['kexe_loader_diagnostic.c','owner-hooks.c']:assert(D/n).read_bytes()==(B/n).read_bytes()
# Existing author controls: output writes intercepted and frozen JSON compared.
sys.path.insert(0,str(D));write=Path.write_text;outputs={}
def injectedWrite(p,t,*a,**kw):
 assert p in [D/'pure-controls.json',D/'registration-controls.json']and t.encode()==p.read_bytes();outputs[str(p)]=len(t);return len(t)
try:
 Path.write_text=injectedWrite
 for n in ['pure-controls.py','registration-controls.py']:
  with contextlib.redirect_stdout(io.StringIO()):runpy.run_path(str(D/n),run_name='independent_source_control')
finally:Path.write_text=write
# Exact V4 statements after returned Popen, through fallible transfer setup.
source=(D/'native-call.py').read_text();tree=ast.parse(source);f=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='call');tr=next(n for n in ast.walk(f)if isinstance(n,ast.Try)and any(isinstance(s,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='proc'for t in s.targets)for s in n.body));a=next(i for i,s in enumerate(tr.body)if isinstance(s,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='earlyLeaderSignalAuthority'for t in s.targets));b=next(i for i,s in enumerate(tr.body)if isinstance(s,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='cap'for t in s.targets));cleanup=next(n for n in ast.walk(f)if isinstance(n,ast.If)and 'earlyLeaderSignalAuthority'in ast.unparse(n.test)and 'ctl is None'in ast.unparse(n.test))
events=[]
class Peer:
 def close(self):events.append('peer-close-ok')
def transfer(*a):events.append('transfer-second-dup-refusal');raise RuntimeError('injected second dup failure')
def need(q,m):
 if not q:raise AssertionError(m)
ctx={'proc':types.SimpleNamespace(pid=100,stdout='stdout-owned',stderr='stderr-owned'),'r':{'invocation':'seal'},'admissionSHA256':'seal','O':Path('/injected-only-no-files'),'rows':[],'save':lambda*a:events.append('durable-PID'),'peer':Peer(),'ctl':None,'earlyLeaderSignalAuthority':False,'waitCalled':False,'failure':None,'Controller':lambda*a:types.SimpleNamespace(active=True),'time':types.SimpleNamespace(monotonic=lambda:0),'deadline':30,'transfer_popen_reads':transfer,'os':types.SimpleNamespace(dup=None,close=None,kill=lambda*a:events.append('kill-exact-leader')),'Capture':None,'need':need}
try:exec(compile(ast.fix_missing_locations(ast.Module(body=tr.body[a:b+1],type_ignores=[])),'exact-v4-setup','exec'),ctx)
except RuntimeError as e:ctx['failure']=repr(e)
else:raise AssertionError('injected setup did not fail')
assert ctx['ctl']is not None and ctx['r']['pid']==100 and ctx['earlyLeaderSignalAuthority']is True and ctx['waitCalled']is False
ctx['ctl'].active=False;events.append('retire-controller')
exec(compile(ast.fix_missing_locations(ast.Module(body=[cleanup],type_ignores=[])),'exact-v4-cleanup-condition','exec'),ctx)
assert 'kill-exact-leader'not in events
# No TICKET/watchdog exists yet. Primary oh_begin's clock is later than outer.
hooks=(D/'owner-hooks.c').read_text();assert 'oh_deadline=now+30000000000u'in hooks and source.index('if proc is not None and not waitCalled:')<source.index('if protocol is not None:protocol.close()')
outerDeadline=30;loaderDeadline=32;assert loaderDeadline>outerDeadline
r={'status':'HOLD_SOURCE_ONLY_HELD_LAUNCH_V4_PRE_TICKET_TRANSFER_CLEANUP_GAP','subject':str(D),'reviewerRole':'Independent of LC-authored V4 peer/controller-order change; reviewer authored earlier V3 implementation, disclosed. No self-independent qualification of unchanged V3 mechanics.','sourcePinsSHA256':rec(D/'source-pins.json')['sha256'],'inputPinsSHA256':rec(D/'input-pins.json')['sha256'],'driverSHA256':rec(D/'run.py')['sha256'],'preregistrationSHA256':rec(D/'preregistration.json')['sha256'],'sourceFilesVerified':24,'inputFilesVerified':34,'inputLogicalBytes':1504693,'pinsRereadAfterControls':True,'existingPureControlsByteCompared':len(outputs),'newExactASTFailureControl':{'events':events,'controllerCreatedBeforeTransfer':True,'currentPIDPublished':True,'noTicketOrWatchdogYet':True,'cleanupExactLeaderSignalSkipped':True,'modelOuterDeadline':outerDeadline,'modelLaterLoaderAdmissionDeadline':loaderDeadline,'actualProcessOrClockTrace':False},'finding':{'id':'F3-transfer-before-ticket','file':str(D/'native-call.py'),'trigger':'transfer_popen_reads fails after Controller assignment but before watchdog/protocol/TICKET (e.g. concrete previously fixture-supported second dup failure).','evidence':'Finally retires controller, but early exact-leader cleanup requires ctl is None and skips. Remaining outer deadline wait precedes host socket close. Pinned loader oh_begin starts a later30s deadline. The same prior peer-close cleanup gap remains for a different supported fallible setup step; eventual wait may be uncertain/unclosed.','requiredChange':'Preserve V4. Fresh version must cover every pre-TICKET setup failure with exact local unreaped direct-leader authority independent of controller presence after synchronized stop, or cancel owned channel before wait with correct worker/journal ownership. No post-wait numeric signaling, unknown-member forgiveness or extra guest deadline. Add source-bound transfer/start/sampler setup negatives before future actual qualification.','falseSuccessObserved':False},'positiveScope':['V4 fixes known peer.close ordering and retains exact current PID publication.','C/hooks byteexact V3 and F1 writer-stop acknowledgment journal gates unchanged.','Unknown birth/member/stage and all old failures remain refused; exact17 guest contracts and finite diagnostic resource declarations unchanged.'],'limitations':['SOURCE/injected AST only; no actual transfer/FD/Popen/child/timing trace.','No new C build/WNOWAIT/thread/FD qualification or GO; shared sampled memory remains soft.'],'operations':{'native':0,'Clang':0,'Popen':0,'FD':0,'threadStart':0,'kernel':0,'network':0,'frozenWrites':0},'audit':dict(path=str(Q/'audit.py'),**rec(Q/'audit.py'))}
pins();(Q/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(dict(path=str(Q/'report.json'),**rec(Q/'report.json')))
