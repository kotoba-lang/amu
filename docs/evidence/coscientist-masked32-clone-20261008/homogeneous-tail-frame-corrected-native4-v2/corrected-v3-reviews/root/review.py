from pathlib import Path
import json,hashlib,subprocess
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'tc-homogeneous-tail-frame-candidate-source-v3-20261009';D=Path(__file__).resolve().parent;old=W/'tc-homogeneous-tail-frame-candidate-source-v2-20261009'
def r(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
sp=json.loads((S/'source-pins.json').read_bytes());ip=json.loads((S/'input-pins.json').read_bytes())
for n,x in sp.items():assert {k:r(S/n)[k]for k in ['bytes','sha256']}==x
for p,x in ip.items():assert {k:r(p)[k]for k in ['bytes','sha256']}=={k:x[k]for k in ['bytes','sha256']}
for n in ['rule.kotoba','41-a64gen-candidate.kotoba']:
 b=(old/n).read_bytes();assert b.count(b'(enc-mov ')==2 and b.replace(b'(enc-mov ',b'(enc-mov-r ')==(S/n).read_bytes()
controls=[]
for n in ['helper-heads.py','model.py','saved-controls.py']:
 z=subprocess.run(['/opt/homebrew/bin/python3.14',str(S/n)],cwd=S,capture_output=True,check=True);(D/(n+'.stdout')).write_bytes(z.stdout);(D/(n+'.stderr')).write_bytes(z.stderr);controls.append(dict(script=n,returncode=z.returncode))
for n,x in sp.items():assert {k:r(S/n)[k]for k in ['bytes','sha256']}==x
q=dict(status='PASS_SOURCE_ONLY_HFT_V3_ENCODER_HEAD_REPAIR_WITH_NATIVE_ABI_HOLD',sourcePins=r(S/'source-pins.json'),candidate=r(S/'41-a64gen-candidate.kotoba'),exactTwoCallHeadDelta=True,controls=controls,oldUnknownEncoderFailurePreserved=True,nativeCalls=0,productChanges=0,C2=False,performanceQualified=False,HOLD=['Native syntax/type/linearity and full emitted binding.','Helper/private-stack ABI and actual fuel/trap/17arena.','Full19/fixedpoint and freshquiet C timing.'])
(D/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(r(D/'report.json'))
