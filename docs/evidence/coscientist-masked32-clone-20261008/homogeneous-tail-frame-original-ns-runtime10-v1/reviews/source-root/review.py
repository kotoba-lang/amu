from pathlib import Path
import json,runpy,sys,subprocess
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'tc-homogeneous-tail-frame-original-ns-runtime10-source-v1-20261009';D=Path(__file__).resolve().parent;sys.path.insert(0,str(S));m=runpy.run_path(str(S/'run.py'));pr=m['load'](S/'preregistration.json');sp=m['load'](S/'source-pins.json');ip=m['load'](S/'input-pins.json')
for n,r in sp.items():m['pin'](S/n,r)
for p,r in ip.items():m['pin'](p,r)
assert len(sp)==18 and len(ip)==55 and sum(r['bytes']for r in ip.values())==6696257 and m['source_scope'](pr)
old=W/'tc-original19-functional-remaining50-source-v1-20261009';components=['capture.py','controller.py','integration.py','runtime.py','typed-adapter.py','artifact_admission.py','callback_contract.py','loader_grammar.py']
for n in components:assert (S/n).read_bytes()==(old/n).read_bytes()
b=(old/'native-call.py').read_bytes();assert b.replace(b'len(rows)<190',b'len(rows)<10').replace(b'fixed ordered190 no retry',b'fixed ordered10 no retry')==(S/'native-call.py').read_bytes()
r=subprocess.run([pr['interpreter']['path'],str(S/'pure-controls.py')],cwd=S,capture_output=True,check=True);(D/'controls.stdout').write_bytes(r.stdout);(D/'controls.stderr').write_bytes(r.stderr)
for n,r in sp.items():m['pin'](S/n,r)
assert not Path(pr['freshOutputRoot']).exists()
q=dict(status=pr['sourceReviewStatus'],sourcePinsSHA256=m['receipt'](S/'source-pins.json')['sha256'],driverSHA256=m['receipt'](S/'run.py')['sha256'],preregistrationSHA256=m['receipt'](S/'preregistration.json')['sha256'],sourceFiles=18,inputFiles=55,inputBytes=6696257,sourceScopePassed=True,pureControlsPassed=True,qualifiedEightComponentsUnchanged=True,nativeCallOnlyGuardDelta=True,nativeCalls=0,maximumLoaderCalls=10,originalProfiles=[0,1,2,17,32],guestFuel=16777216,fullArena17PairParityRequired=True,C2=False,performanceQualified=False,notes=['Loader protocol/source-build-binary premises and exact currentOFF/newON four-word artifact binding checked.','Only finite original NS five pairs; same typed batch1 no-- argv and zero grants.','Saved C results only; no Cfuel/arena/timing.','Header docstring mentions prior x8 template; actual immutable case guards/GO/subjects are HFT NS only.','Host outer escalation required; existing loader sandbox and sampling policy unchanged.','Composition/generic ABI/full19/fixedpoint/performance/adoption remain HOLD.'])
(D/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q,indent=2))
