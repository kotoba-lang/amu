from pathlib import Path
import json,hashlib,ast
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'current-runtime-process-ownership-race-source-v4-20261009-independent';O=W/'current-runtime-process-ownership-race-source-v4-review-root-20261009';O.mkdir(exist_ok=False)
def rec(p):b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
load=lambda p:json.loads(p.read_bytes());sp=load(D/'source-pins.json');ip=load(D/'input-pins.json')
for n,r in sp.items():assert rec(D/n)==r,n
for p,r in ip.items():assert rec(Path(p))=={k:r[k]for k in ['bytes','sha256']},p
assert len(sp)==24 and len(ip)==34 and sum(r['bytes']for r in ip.values())==1504693
s=(D/'native-call.py').read_text();t=ast.parse(s)
assert s.index('peer.close();peer=None')<s.index("cap=transfer_popen_reads")
assert 'proc is not None and ctl is None and not waitCalled and earlyLeaderSignalAuthority' in s
assert s.index('ctl=Controller')<s.index('cap=transfer_popen_reads')
ind=W/'current-runtime-process-ownership-race-source-v4-review-independent-20261009-crc/report.json';q=load(ind);assert q['status']=='HOLD_SOURCE_ONLY_HELD_LAUNCH_V4_PRE_TICKET_TRANSFER_CLEANUP_GAP'
r=dict(status=q['status'],sourcePinsSHA256=rec(D/'source-pins.json')['sha256'],inputPinsSHA256=rec(D/'input-pins.json')['sha256'],driverSHA256=rec(D/'run.py')['sha256'],preregistrationSHA256=rec(D/'preregistration.json')['sha256'],sourceFilesVerified=24,inputFilesVerified=34,inputBytes=1504693,independentCounterexample=dict(path=str(ind),**rec(ind)),rootSourceCorroboration='Controller constructed before fallible read transfer, exact earlyleaderkill requires ctl is None; socket closure occurs after wait. Transfer failure can skip leader termination before its later held admission deadline.',scope='Source corroboration only; no replay of independent injected AST, no kernel or native proof.',nativeCalls=0,GO=False)
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(status=r['status'],report=rec(O/'report.json'))))
