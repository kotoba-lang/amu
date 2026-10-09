from pathlib import Path
import json,hashlib,shutil,sys,runpy,contextlib,io
W=Path('/Users/junkawasaki/github/workspaces/codex'); D=W/'tc-hft-compose511-bound-hoist-g2-g3-g4-fixedpoint6-source-v1-20261009'; O=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_bytes())
def rec(p):b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');pr=load(D/'preregistration.json')
assert rec(D/'source-pins.json')['sha256']=='178f3f0ade2baf75b83eb380e5d4a08e57fc2669ecfd69446c4b09c820d2a27c'
assert len(sp)==22 and len(ip)==pr['exactInputFiles']==141 and sum(r['bytes'] for r in ip.values())==pr['exactInputLogicalBytes']==13109277
for n,r in sp.items():assert rec(D/n)==r,n
for p,r in ip.items():assert rec(Path(p))=={k:r[k]for k in ['bytes','sha256']},p
C=O/'copied-source';C.mkdir(exist_ok=False)
for n in sp:shutil.copyfile(D/n,C/n)
sys.path.insert(0,str(C));import run
assert run.source_scope(pr,ip) and run.registry_scope(pr,ip)
assert not Path(pr['freshOutputRoot']).exists()
control={}
for n in ['pure-controls.py','wrapper-controls.py']:
 s=io.StringIO()
 with contextlib.redirect_stdout(s):runpy.run_path(str(C/n),run_name='__main__')
 (O/(n+'.stdout')).write_text(s.getvalue());control[n]=json.loads(s.getvalue())
for n,r in sp.items():assert rec(D/n)==r,n
for p,r in ip.items():assert rec(Path(p))=={k:r[k]for k in ['bytes','sha256']},p
r=dict(status=pr['sourceReviewStatus'],sourcePinsSHA256=rec(D/'source-pins.json')['sha256'],inputPinsSHA256=rec(D/'input-pins.json')['sha256'],driverSHA256=rec(D/'run.py')['sha256'],preregistrationSHA256=rec(D/'preregistration.json')['sha256'],sourceFiles=22,inputFiles=141,inputBytes=13109277,sharedRegistryGuardVerified=True,sourceScopeVerified=True,wholeCurrent16Verified=True,recursiveGeneratedProducerReviewed=True,G1EqualityRequired=False,G2G3G4WholeEqualityRequired=True,controls=control,nativeCalls=0,GO=False,qualification='SOURCE only; no new fixedpoint, guest runtime, full19, performance, shared cache or general ABI')
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(status=r['status'],report=rec(O/'report.json'))))
