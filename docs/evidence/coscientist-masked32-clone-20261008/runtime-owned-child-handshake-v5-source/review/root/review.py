from pathlib import Path
import json,hashlib,shutil,sys,runpy,contextlib,io,ast
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'current-runtime-process-ownership-race-source-v5-20261009-independent';O=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_bytes())
def rec(p):b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');pr=load(D/'preregistration.json')
assert len(sp)==24 and len(ip)==38 and sum(r['bytes']for r in ip.values())==1513556
for n,r in sp.items():assert rec(D/n)==r,n
for p,r in ip.items():assert rec(Path(p))=={k:r[k]for k in ['bytes','sha256']},p
C=O/'copied-source';C.mkdir(exist_ok=True)
for n in sp:shutil.copyfile(D/n,C/n)
sys.path.insert(0,str(C));controls={}
for n in ['pure-controls.py','registration-controls.py']:
 s=io.StringIO()
 with contextlib.redirect_stdout(s):runpy.run_path(str(C/n),run_name='__main__')
 (O/(n+'.stdout')).write_text(s.getvalue());controls[n]=load(C/n.replace('.py','.json'));assert (C/n.replace('.py','.json')).read_bytes()==(D/n.replace('.py','.json')).read_bytes()
s=(D/'native-call.py').read_text();ast.parse(s)
assert s.index('ticketMayHaveBeenSent=True')<s.index('initial=protocol.handshake')
assert 'not ticketMayHaveBeenSent and not waitCalled and not waitUncertain' in s and 'cleanupWatchdogStopAck' in s
assert 'not ctl.active and not ctl.waitEntered and not ctl.waitUncertain' in s
assert (D/'kexe_loader_diagnostic.c').read_bytes()==(W/'current-runtime-process-ownership-race-source-v4-20261009-independent/kexe_loader_diagnostic.c').read_bytes()
for n,r in sp.items():assert rec(D/n)==r,n
for p,r in ip.items():assert rec(Path(p))=={k:r[k]for k in ['bytes','sha256']},p
q=dict(status='PASS_SOURCE_ONLY_DIAGNOSTIC_HELD_OWNERSHIP_LOADER_PROTOCOL_PAIRED2_V5',sourcePinsSHA256=rec(D/'source-pins.json')['sha256'],inputPinsSHA256=rec(D/'input-pins.json')['sha256'],driverSHA256=rec(D/'run.py')['sha256'],preregistrationSHA256=rec(D/'preregistration.json')['sha256'],sourceFilesVerified=24,inputFilesVerified=38,inputBytes=1513556,controls=controls,allPreticketSetupFailurePredicateVerified=True,conservativeHandshakeBoundary=True,controllerRetirementAndWatchdogStopAcknowledgmentRequired=True,signalAfterWaitOrUncertaintyForbidden=True,CAndHooksUnchanged=True,limitations=['SOURCE predicates and injected controls only; no actual FD/thread/process fixture','Cooperative stop acknowledgment and bounded actual wait remain runtime obligations','No actual C build/WNOWAIT/zombie-birth qualification; no GO or paired execution','No native cache, full19 or performance qualification'],nativeCalls=0,ClangCalls=0,GO=False)
(O/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(dict(status=q['status'],report=rec(O/'report.json'))))
