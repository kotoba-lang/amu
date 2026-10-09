from pathlib import Path
import json,hashlib,shutil,sys,runpy,contextlib,io
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'held-launch-v6-ownership-fixture4-source-v1-20261009-crc';O=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_bytes())
def rec(p):b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');pr=load(D/'preregistration.json');assert len(sp)==64 and len(ip)==79 and sum(r['bytes']for r in ip.values())==2454696
for n,r in sp.items():assert rec(D/n)==r,n
for p,r in ip.items():assert rec(Path(p))=={k:r[k]for k in ['bytes','sha256']},p
C=O/'copied-source';C.mkdir(exist_ok=True)
for n in sp:
 q=C/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(D/n,q)
sys.path.insert(0,str(C));import run
assert run.closure(pr,sp,ip) and run.source_scope(pr);assert not Path(pr['freshOutputRoot']).exists()
s=io.StringIO()
old_exists=Path.exists
# Recreate only the declared pre-build SOURCE model; actual build proof remains separate.
Path.exists=lambda p:False if str(p)==pr['loader'] else old_exists(p)
try:
 with contextlib.redirect_stdout(s):runpy.run_path(str(C/'pure-controls.py'),run_name='__main__')
finally:Path.exists=old_exists
(O/'pure-controls.stdout').write_text(s.getvalue());ctrl=json.loads(s.getvalue());assert ctrl['actualOperations']==0 and ctrl['actualJournalASTGuardBranches']==4 and len(ctrl['refusedMutants'])==8
for n,r in sp.items():assert rec(D/n)==r,n
for p,r in ip.items():assert rec(Path(p))=={k:r[k]for k in ['bytes','sha256']},p
q=dict(status=pr['sourceReviewStatus'],sourcePinsSHA256=rec(D/'source-pins.json')['sha256'],inputPinsSHA256=rec(D/'input-pins.json')['sha256'],driverSHA256=rec(D/'run.py')['sha256'],preregistrationSHA256=rec(D/'preregistration.json')['sha256'],sourceFilesVerified=64,inputFilesVerified=79,inputLogicalBytes=2454696,controls=ctrl,purePrebuildExistenceModelInjected=True,actualLoaderNowExists=Path(pr['loader']).exists(),delegatedCapsulesExplicit=True,unchangedV6MechanismsVerified=True,original30SecondDeadline=True,budgets=dict(directStarts=4,maximumGuestForks=3,threads=10,FDs=44),scope='SOURCE-only new diagnostic capsules/injection/delegation, separate from original95/runtime/performance',limitations=['No actual process/FD/worker/channel/WNOWAIT qualification','Guest-zero negative source/protocol conditional, not kernel fork census','Blocked callback plus original fsync after release, not actual kernel fsync stall','Timed failure closure remains uncertain/refused; no postwait signaling','Future actual source-bound V6 C build proof required at GO'],operations=0,GO=False)
(O/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(dict(status=q['status'],report=rec(O/'report.json'))))
