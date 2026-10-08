from pathlib import Path
import json,hashlib,runpy,sys,subprocess
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'published-mode2-x8-vector-statemate6-source-v1-20261009';D=Path(__file__).resolve().parent
sys.path.insert(0,str(S));m=runpy.run_path(str(S/'run.py'));pr=m['load'](S/'preregistration.json');sp=m['load'](S/'source-pins.json');ip=m['load'](S/'input-pins.json')
for n,r in sp.items():m['pin'](S/n,r)
for p,r in ip.items():m['pin'](p,r)
assert len(sp)==21 and len(ip)==64 and sum(r['bytes']for r in ip.values())==10965742
assert m['source_scope'](pr,ip)
old=W/'published-mode2-x8-build-fixture6-source-v1-20261009'
components=['capture.py','controller.py','integration.py','native-call.py','typed-adapter.py','runtime.py','artifact_admission.py','compiler_output.py']
for n in components:assert (S/n).read_bytes()==(old/n).read_bytes(),n
controls=[]
for n in ['pure-controls.py','wrapper-controls.py']:
 r=subprocess.run([pr['interpreter']['path'],str(S/n)],cwd=S,capture_output=True,check=True)
 (D/(n+'.stdout')).write_bytes(r.stdout);(D/(n+'.stderr')).write_bytes(r.stderr);controls.append({'source':n,'returncode':r.returncode,'stdoutSHA256':hashlib.sha256(r.stdout).hexdigest()})
assert not Path(pr['freshOutputRoot']).exists()
report=dict(status=pr['sourceReviewStatus'],sourcePinsSHA256=m['receipt'](S/'source-pins.json')['sha256'],driverSHA256=m['receipt'](S/'run.py')['sha256'],preregistrationSHA256=m['receipt'](S/'preregistration.json')['sha256'],exactSourceFiles=len(sp),exactInputFiles=len(ip),inputLogicalBytes=10965742,scopePassed=True,unchangedQualifiedComponents=components,controls=controls,maximumLoaderCalls=6,nativeCallsMade=0,C2=False,runtimeGuestAuthorized=False,timingAuthorized=False,stageClobberCertificateQualified=False,candidateAdoptionQualified=False,oldProducerProofAndOldGORechecked=True,notes=['All six calls arity0 compiler CLI; extracted own exports arity1.','Fresh six only; no original statemate invocation or timing.','All dependency pins and old sealed producer proof rechecked.','Terminal durable before COMPLETE; guard before each call.'])
(D/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
