"""SOURCE and injected controls only; no actual FD/thread/process/native APIs."""
from pathlib import Path
import json,stat,hashlib,ast,sys,runpy,io,contextlib,types
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'current-runtime-process-ownership-race-source-v5-20261009-independent';B=W/'current-runtime-process-ownership-race-source-v3-20261009-crc';Q=Path(__file__).parent

def rec(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size<=33554432;x=p.read_bytes();z=p.lstat();assert(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns);return {'bytes':len(x),'sha256':hashlib.sha256(x).hexdigest()}
def check():
 sp=json.loads((D/'source-pins.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes());assert len(sp)==24 and len(ip)==38 and sum(v['bytes']for v in ip.values())==1513556
 for n,v in sp.items():assert rec(D/n)==v,n
 for p,v in ip.items():assert rec(p)==v,p
 return sp,ip
sp,ip=check();pr=json.loads((D/'preregistration.json').read_bytes());assert pr['exactInputFiles']==38 and pr['exactInputLogicalBytes']==1513556 and pr['inputPinsSHA256']==rec(D/'input-pins.json')['sha256']
assert rec(D/'source-pins.json')['sha256']=='252c116cc0ddf3c26b2d0ae7390ede785d169ea9a024f70d2c55be30ea05990c'
for n in ['kexe_loader_diagnostic.c','owner-hooks.c']:assert(D/n).read_bytes()==(B/n).read_bytes()
source=(D/'native-call.py').read_text();tree=ast.parse(source);f=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='call');predicate=next(n.test for n in ast.walk(f)if isinstance(n,ast.If)and 'ticketMayHaveBeenSent'in ast.unparse(n.test)and 'earlyLeaderSignalAuthority'in ast.unparse(n.test))
# Independently recompute actual predicate and extra boolean/ownership cases.
base=dict(proc=types.SimpleNamespace(pid=100),ctl=types.SimpleNamespace(active=False,waitEntered=False,waitUncertain=False),ticketMayHaveBeenSent=False,waitCalled=False,waitUncertain=False,earlyLeaderSignalAuthority=True,cleanupWatchdogStopAck=True)
code=compile(ast.fix_missing_locations(ast.Expression(predicate)),'source-v5-predicate','eval');assert eval(code,base)
for field in ['ticketMayHaveBeenSent','waitCalled','waitUncertain']:
 q=dict(base);q[field]=True;assert not eval(code,q)
for field in ['earlyLeaderSignalAuthority','cleanupWatchdogStopAck']:
 q=dict(base);q[field]=False;assert not eval(code,q)
for field in ['active','waitEntered','waitUncertain']:
 q=dict(base);q['ctl']=types.SimpleNamespace(active=False,waitEntered=False,waitUncertain=False);setattr(q['ctl'],field,True);assert not eval(code,q)
assert not eval(code,dict(base,proc=None))
assert source.index('ticketMayHaveBeenSent=True')<source.index('initial=protocol.handshake')and source.count('ticketMayHaveBeenSent=False')==1
assert 'earlyLeaderSignalAuthority=False;waitCalled=True'in source and 'os.kill(proc.pid,9)'in source and 'proc.kill()'not in source and '.poll('not in source
assert source.index("r['pid']=proc.pid;save(")<source.index('peer.close();peer=None')<source.index('ctl=Controller(')
# Existing author controls are all inert mocks, output writes intercepted.
sys.path.insert(0,str(D));old=Path.write_text;writes={}
def write(p,t,*a,**kw):
 assert p in [D/'pure-controls.json',D/'registration-controls.json']and t.encode()==p.read_bytes();writes[str(p)]=len(t);return len(t)
try:
 Path.write_text=write
 for n in ['pure-controls.py','registration-controls.py']:
  with contextlib.redirect_stdout(io.StringIO()):runpy.run_path(str(D/n),run_name='independent_v5_pure')
finally:Path.write_text=old
controls=json.loads((D/'pure-controls.json').read_bytes());assert len(controls['positive'])==11 and len(controls['negative'])==29 and len(controls['sourceBoundSetupCases'])==16
assert all(q['actualOperations']==0 and q['TICKETSent']is False and q['originalDeadlineUnchanged']is True for q in controls['sourceBoundSetupCases'])
# Explicitly do not certify timely OS cleanup: capture join can consume all
# remaining deadline BEFORE early leader signal, leaving cooperative wait .001.
assert source.index('cap.join_once(max(0,deadline-time.monotonic()))')<source.index('if proc is not None and not ticketMayHaveBeenSent')
assert 'proc.wait(timeout=max(.001,min(30,budget)))'in source
# Existing F1/F2 safety source gates retained; C build/actual closure still absent.
assert 'ownershipAck=protocol is None or protocol.writer_stop_acknowledged()'in source and 'hfile(oj,65536)if ownershipAck and ownershipFile.closed'in source
hooks=(D/'owner-hooks.c').read_text();assert 'oh_child_state=OH_WAIT_ENTERED'in hooks and 'supervised_pid=-1;alarm(0)'in hooks and 'OH_UNCERTAIN'in hooks and 'WEXITED|WNOWAIT'in hooks
schema=json.loads((D/'go-schema.json').read_bytes());assert len(schema['exactKeys'])==len(set(schema['exactKeys']));assert pr['maximumLoaderCalls']==2 and len(pr['environment'])==17 and pr['maximumParentFDs']==44 and pr['maximumAuxiliaryThreadsPerCall']==3 and pr['maximumOwnedGroupMembers']==2 and pr['originalOuterWallSeconds']==30 and pr['diagnosticLoaderChildFailureCleanupSeconds']==5
check()
r={'status':pr['sourceReviewStatus'],'subject':str(D),'reviewerRole':'Independent of LC-authored V4/V5 pre-TICKET repair and SOURCE harness. Reviewer authored unchanged V3 F1/F2 mechanism; this is disclosed and no self-independent actual C/FD/thread qualification is claimed.','sourcePinsSHA256':rec(D/'source-pins.json')['sha256'],'inputPinsSHA256':rec(D/'input-pins.json')['sha256'],'driverSHA256':rec(D/'run.py')['sha256'],'preregistrationSHA256':rec(D/'preregistration.json')['sha256'],'sourceFilesVerified':24,'inputFilesVerified':38,'inputLogicalBytes':1513556,'allPinsRereadAfterControls':True,'pureControls':{'authorSourceASTSetupCases':16,'authorNoSignalPredicates':8,'positive':11,'negative':29,'independentActualPredicateNegatives':9,'frozenOutputWritesIntercepted':2},'findings':[],'sourceConclusions':['Known V3/V4 peer/transfer pre-TICKET cleanup defects repaired: predicate independent of ctl presence, synchronized inactive/no-wait controller plus watchdog-stop ACK before exact local leader signal.','Popen PID/current invocation saved before endpoint cleanup; exact owned direct leader only, no group-membership inference or Popen.kill implicit poll.','Ticket boundary permanently conservative before handshake; wait entry or uncertain ownership never regains numeric signal authority.','F1 positive worker-finally event AND thread-death acknowledgment gates journal close/hash; retained unacknowledged journal/protocol remains unclosed/unhashed.','F2 unchanged C/hooks preserve anchored exact child state and alarm retirement before reaping waits; uncertain states forbid further signals.','Exact17 guest environment/typed argv2/fuel16777216/zeroCaps/counters and finite original30s protocol/resource budgets preserved; all historical HOLD/failure evidence remains immutable.'],'qualificationLimitations':['SOURCE safety/ordering PASS only; no native/build/GO or actual Popen/FD/thread/clock/WNOWAIT/zombie/cleanup trace.','Capture.join_once can consume remaining outer deadline before exact leader kill; direct wait may then receive .001s and fail uncertain. This PASS does not establish timely closure of all failure paths. Actual cooperative fsync/join/wait must be separately qualified; no blanket closure guarantee.','Ambiguous watchdog start/stop ACK failure deliberately refuses signaling and may leave explicit unclosed process ownership. No numeric authority is recovered after uncertainty.','Conservative ticketMayHaveBeenSent can be true even before successful IO; after handshake entry missing receipts remain refusal/unclosed uncertainty, never unknown PID success.','Immediate asynchronous Popen return/publication gaps, new C flag ABI/SDK/clock relation and real delayed journal writer cancellation remain actual proof gaps.','Sampled physicalFootprint policy is finite/soft, not hardpeak or atomic census; no functional/full19/performance/adoption qualification.'],'operations':{'native':0,'Clang':0,'Popen':0,'FD':0,'threadStarts':0,'kernel':0,'network':0,'frozenWrites':0},'audit':dict(path=str(Q/'audit.py'),**rec(Q/'audit.py'))}
(Q/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(dict(path=str(Q/'report.json'),**rec(Q/'report.json')))
