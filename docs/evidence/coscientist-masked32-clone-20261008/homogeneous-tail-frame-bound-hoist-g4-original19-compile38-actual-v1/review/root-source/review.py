from pathlib import Path
import json,hashlib,shutil,sys,runpy,contextlib,io
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-hft-compose511-bound-hoist-g4-original19-compile38-source-v1-20261009';O=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_bytes())
def rec(p):b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');pr=load(D/'preregistration.json')
assert len(sp)==22 and len(ip)==pr['exactInputFiles']==237 and sum(r['bytes']for r in ip.values())==pr['exactInputLogicalBytes']==20237066
for n,r in sp.items():assert rec(D/n)==r,n
for p,r in ip.items():assert rec(Path(p))=={k:r[k]for k in ['bytes','sha256']},p
C=O/'copied-source';C.mkdir(exist_ok=False)
for n in sp:shutil.copyfile(D/n,C/n)
sys.path.insert(0,str(C));import run
assert run.source_scope(pr,ip) and run.registry_scope(pr,ip) and run.existing_g4_guard(pr)
assert not Path(pr['freshOutputRoot']).exists();controls={}
for n in ['pure-controls.py','wrapper-controls.py']:
 s=io.StringIO()
 with contextlib.redirect_stdout(s):runpy.run_path(str(C/n),run_name='__main__')
 (O/(n+'.stdout')).write_text(s.getvalue());controls[n]=json.loads(s.getvalue())
for n,r in sp.items():assert rec(D/n)==r,n
for p,r in ip.items():assert rec(Path(p))=={k:r[k]for k in ['bytes','sha256']},p
q=dict(status=pr['sourceReviewStatus'],sourcePinsSHA256=rec(D/'source-pins.json')['sha256'],inputPinsSHA256=rec(D/'input-pins.json')['sha256'],driverSHA256=rec(D/'run.py')['sha256'],preregistrationSHA256=rec(D/'preregistration.json')['sha256'],sourceFiles=22,inputFiles=237,inputBytes=20237066,sharedRegistryGuardVerified=True,completeOriginal19MatrixAnd95Profiles=True,actualCurrentG4LineageVerified=True,current16AssemblyVerified=True,orderedGeneratedReceiptMapping=[2,3,4],controls=controls,nativeCalls=0,GO=False,performanceQualified=False,qualification='SOURCE only; no new38 artifacts or full19 guest execution')
(O/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(dict(status=q['status'],report=rec(O/'report.json'))))
