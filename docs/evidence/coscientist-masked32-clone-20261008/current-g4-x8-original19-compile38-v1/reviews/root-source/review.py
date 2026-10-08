from pathlib import Path
import json,runpy,sys,subprocess
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'published-mode2-x8-g4-original19-compile38-source-v1-20261009';D=Path(__file__).resolve().parent;sys.path.insert(0,str(S));m=runpy.run_path(str(S/'run.py'));p=m['load'](S/'preregistration.json');sp=m['load'](S/'source-pins.json');ip=m['load'](S/'input-pins.json')
for n,r in sp.items():m['pin'](S/n,r)
for f,r in ip.items():m['pin'](f,r)
assert len(sp)==22 and len(ip)==80 and sum(r['bytes']for r in ip.values())==10983592
assert m['source_scope'](p,ip)and m['existing_g4_guard'](p)
delta=m['load'](S/'delta.json');B=W/'published-mode2-x8-vector-statemate6-source-v2-20261009'
for n in ['artifact_admission.py','capture.py','compiler_output.py','controller.py','integration.py','runtime.py','typed-adapter.py']:assert (S/n).read_bytes()==(B/n).read_bytes()
r=delta['nativeCallerOrigin'];m['pin'](r['path'],r);assert (S/'native-call.py').read_bytes()==Path(r['path']).read_bytes();assert (S/'fixedpoint_lineage.py').read_bytes()==(W/'published-mode2-x8-g2-g3-g4-fixedpoint6-source-v1-20261009/run.py').read_bytes()
controls=[]
for n in ['pure-controls.py','wrapper-controls.py']:
 r=subprocess.run([p['interpreter']['path'],str(S/n)],cwd=S,capture_output=True,check=True);(D/(n+'.stdout')).write_bytes(r.stdout);(D/(n+'.stderr')).write_bytes(r.stderr);controls.append(dict(script=n,returncode=r.returncode))
for n,r in sp.items():m['pin'](S/n,r)
assert not Path(p['freshOutputRoot']).exists()
q=dict(status=p['sourceReviewStatus'],sourcePinsSHA256=m['receipt'](S/'source-pins.json')['sha256'],driverSHA256=m['receipt'](S/'run.py')['sha256'],preregistrationSHA256=m['receipt'](S/'preregistration.json')['sha256'],exactSourceFiles=len(sp),exactInputFiles=len(ip),inputBytes=10983592,scopePassed=True,controls=controls,sourceOnly=True,nativeCallsMade=0,maximumLoaderCalls=38,workloads=19,sourceBodyProfileABIUnchanged=True,wholeG4Main0AndRecursiveProducerChainChecked=True,perChildResourcesUnchanged=True,C2=False,performanceQualified=False,generalAdoptionQualified=False,fullMachineSemanticsQualified=False,notes=['All19 new artifacts must use current fixedpoint G4 main0, no previous workload output reuse.','Eight lifecycle components unchanged; inherited42 counter subordinated to exact38 case admission.','Explicit71000s campaign/2GiB retained-output reservation, not hardquota/peak guarantee.','Hostprofile preserves loader sandbox; compiler17env/caps/fuel unchanged.','Finite sampled or previously typed termination gap only; runtime/full19/performance await subsequent gates.'])
(D/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q,indent=2))
