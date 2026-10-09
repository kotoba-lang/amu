from pathlib import Path
import json,hashlib,subprocess
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'tc-homogeneous-tail-frame-candidate-source-v2-20261009';D=Path(__file__).resolve().parent
def r(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
sp=json.loads((S/'source-pins.json').read_bytes());ip=json.loads((S/'input-pins.json').read_bytes())
for n,x in sp.items():assert {k:r(S/n)[k]for k in ['bytes','sha256']}==x
for p,x in ip.items():assert {k:r(p)[k]for k in ['bytes','sha256']}=={k:x[k]for k in ['bytes','sha256']}
controls=[]
for n in ['model.py','saved-controls.py']:
 z=subprocess.run(['/opt/homebrew/bin/python3.14',str(S/n)],cwd=S,capture_output=True,check=True);(D/(n+'.stdout')).write_bytes(z.stdout);(D/(n+'.stderr')).write_bytes(z.stderr);controls.append(dict(script=n,returncode=z.returncode,stdoutSHA256=hashlib.sha256(z.stdout).hexdigest()))
rule=(S/'rule.kotoba').read_text();assert rule.index('(sf-old-fix M 1)')<rule.index('(loop [f 1]');assert '(> t 0) (< t ln)'in rule and '(> target 0) (< target cn)'in rule
v1=W/'tc-homogeneous-tail-frame-candidate-source-v1-20261009'
for n in ['model.py','model-result.json']:assert (S/n).read_bytes()==(v1/n).read_bytes()
q=dict(status='PASS_SOURCE_ONLY_HFT_V2_WITH_ABI_AND_NATIVE_HOLD',sourcePins=r(S/'source-pins.json'),candidate=r(S/'41-a64gen-candidate.kotoba'),preregistration=r(S/'preregistration.json'),controls=controls,oldFIXClosurePrecedesMutation=True,LRReloadRetained=True,firstCertifiedPairOnly=True,nativeCalls=0,productChanges=0,performanceQualified=False,adoptionQualified=False,HOLD=['Native Kotoba type/word binding.','Full current helper ABI x7/callee-save/private-stack ownership.','Actual current fuel/trap/17-arena comparison and selfhost fixedpoint.','Quiet-host fresh C timing.'])
(D/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(r(D/'report.json'))
