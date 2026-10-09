from pathlib import Path
import json,hashlib,shlex
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'held-launch-v5-loader-build5-source-v2-20261009-independent';O=W/'current-runtime-process-ownership-race-source-v5-20261009-independent/loader-build-outputs';D=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_bytes())
def rec(p):b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
for n,r in load(S/'source-pins.json').items():assert {k:rec(S/n)[k]for k in ['bytes','sha256']}==r
for p,r in load(S/'input-pins.json').items():assert {k:rec(Path(p))[k]for k in ['bytes','sha256']}=={k:r[k]for k in ['bytes','sha256']}
p=load(S/'preregistration.json');a=load(O/'attempts.json');assert len(a)==3 and load(O/'terminal.json')==dict(childCalls=3,allDirectChildrenClosed=True,failure=True,descendantClosureUniversal=False)
for c,r in zip(p['cases'],a):
 assert c['label']==r['label']and c['argv']==r['argv']and r['state']=='terminal'and r['returncode']==0
 for n in ['stdout','stderr']:assert {k:rec(O/(r['label']+'.'+n))[k]for k in ['bytes','sha256']}==r[n]
raw=(O/'link-preview.stderr').read_text();cmds=[shlex.split(l)for l in raw.splitlines()if l.lstrip().startswith('"/')];assert len(cmds)==2
cc=cmds[0];j=cc.index('-dumpdir');prefix=str(O/'kexe-loader-');assert cc[j+1]==prefix
f=load(O/'failure.json');assert f['noRetry']and f['childCalls']==3 and f['error']==repr(AssertionError('unregistered absolute link/compiler input: '+prefix));assert not(O/'kexe-loader').exists()and not(O/'report.json').exists()
q=dict(status='PASS_ROOT_SAVED_HELD_LAUNCH_V5_BUILD5_V2_QUERY3_FAILURE_ONLY',sourcePinsSHA256=rec(S/'source-pins.json')['sha256'],preregistrationSHA256=rec(S/'preregistration.json')['sha256'],calls=3,closed0=3,buildCalls=0,guestCalls=0,firstFailure='option role -dumpdir output prefix rejected as unregistered input',failure=f,rawPreview=rec(O/'link-preview.stderr'),diagnosis='Other default absolute include search operands need option-specific registration; prefixed -I/-L need explicit search closure before future build. Frozen V2 and output namespace retained.',noRetry=True,loaderQualified=False,performanceQualified=False,operations=0)
(D/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(dict(status=q['status'],report=rec(D/'report.json'))))
