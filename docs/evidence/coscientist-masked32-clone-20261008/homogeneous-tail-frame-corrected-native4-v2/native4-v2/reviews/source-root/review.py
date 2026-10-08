from pathlib import Path
import hashlib,json,runpy,sys,subprocess
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'tc-homogeneous-tail-frame-native4-source-v2-20261009';D=Path(__file__).resolve().parent;sys.path.insert(0,str(S));m=runpy.run_path(str(S/'run.py'));pr=m['load'](S/'preregistration.json');sp=m['load'](S/'source-pins.json');ip=m['load'](S/'input-pins.json')
for n,r in sp.items():m['pin'](S/n,r)
for p,r in ip.items():m['pin'](p,r)
assert len(sp)==21 and len(ip)==2885 and sum(r['bytes']for r in ip.values())==451777835
assembly=m['load'](S/'source-assembly.json');mods=assembly['modules'];assert len(mods)==16
for candidate,file in [(True,'candidate-current16.kotoba'),(False,'ordinary-current16.kotoba')]:
 parts=[Path(assembly['candidate41'if candidate else'ordinaryCandidate41']['path']if n=='seed/41-a64gen.kotoba'else r['path']).read_bytes()+b'\n'for n,r in zip(mods,assembly['modulePins'])];assert b''.join(parts)==(S/file).read_bytes()
assert pr['hostAuthorizedOuterEscalationRequired']and pr['loaderOwnedSandboxUnchanged']and not Path(pr['freshOutputRoot']).exists()
assert len(pr['cases'])==4 and len(pr['environment'])==17
for c in pr['cases']:assert c['nativeArgv'][2:7]==['0','0','aarch64','35,37,38,39','--']
old=W/'shared-frame-currenttyped-observer3-source-v1-20261009'
for n in ['capture.py','controller.py','integration.py','runtime.py','artifact_admission.py','typed-adapter.py']:assert (S/n).read_bytes()==(old/n).read_bytes()
r=subprocess.run(['/opt/homebrew/bin/python3.14',str(S/'source-controls.py')],cwd=S,capture_output=True,check=True);(D/'controls.stdout').write_bytes(r.stdout);(D/'controls.stderr').write_bytes(r.stderr)
for n,x in sp.items():m['pin'](S/n,x)
q=dict(status=pr['sourceReviewStatus'],sourcePinsSHA256=m['receipt'](S/'source-pins.json')['sha256'],driverSHA256=m['receipt'](S/'run.py')['sha256'],preregistrationSHA256=m['receipt'](S/'preregistration.json')['sha256'],exactSourceFiles=len(sp),exactInputFiles=len(ip),inputBytes=451777835,controls=31,qualifiedComponentsUnchanged=True,wholeExpectedFourWordCertificateRecomputed=True,sourceOnly=True,maximumLoaderCalls=4,nativeCalls=0,productChanges=0,C2=False,performanceQualified=False,notes=['Host outer escalation required; loader sandbox and resources unchanged.','Only immutable current16 module41 changed, primary compiler argv arity0.','Original NS source and implicit rem/sentinel267 closure pinned.','Exact expected whole native/container permits only four changed words.','Direct-child wait and finite sample policy; no hard-peak claim.','Native type/word binding, helper/private-stack ABI, fuel/trap/17arena and original19/C timing remain HOLD.'])
(D/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q,indent=2))
