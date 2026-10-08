from pathlib import Path
import json,runpy,sys,subprocess
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'published-mode2-x8-g2-g3-g4-fixedpoint6-source-v1-20261009';D=Path(__file__).resolve().parent;sys.path.insert(0,str(S));m=runpy.run_path(str(S/'run.py'));pr=m['load'](S/'preregistration.json');sp=m['load'](S/'source-pins.json');ip=m['load'](S/'input-pins.json')
for n,r in sp.items():m['pin'](S/n,r)
for p,r in ip.items():m['pin'](p,r)
assert len(sp)==21 and len(ip)==50 and sum(r['bytes']for r in ip.values())==5292422
assert m['source_scope'](pr,ip)
delta=m['load'](S/'delta.json');old=Path(delta['baseWorkspace'])
for n in delta['unchangedComponents']:assert (S/n).read_bytes()==(old/n).read_bytes()
controls=[]
for n in ['pure-controls.py','wrapper-controls.py']:
 r=subprocess.run([pr['interpreter']['path'],str(S/n)],cwd=S,capture_output=True,check=True);(D/(n+'.stdout')).write_bytes(r.stdout);(D/(n+'.stderr')).write_bytes(r.stderr);controls.append(dict(script=n,returncode=r.returncode))
for n,r in sp.items():m['pin'](S/n,r)
assert not Path(pr['freshOutputRoot']).exists()
q=dict(status=pr['sourceReviewStatus'],sourcePinsSHA256=m['receipt'](S/'source-pins.json')['sha256'],driverSHA256=m['receipt'](S/'run.py')['sha256'],preregistrationSHA256=m['receipt'](S/'preregistration.json')['sha256'],exactSourceFiles=len(sp),exactInputFiles=len(ip),inputBytes=5292422,scopePassed=True,controls=controls,qualifiedEightComponentsUnchanged=True,sourceOnly=True,nativeCallsMade=0,maximumLoaderCalls=6,fixedpointGenerations=[2,3,4],G1EqualityRequired=False,C2=False,performanceQualified=False,generalAdoptionQualified=False,fullMachineSemanticsQualified=False,notes=['Exact current unity and full G1 saved source/artifact correspondence.','Generated producer recursively binds previous two closed admitted calls, current GO and whole container/native.','Full G2/G3/G4 bytes and sole main0 exports required, no G1 equality requirement.','Compiler argv typed0 separator/caps and 17 resource environment remain fixed.','Finite physical samples or unchanged typed termination gap only; no hardpeak or descendant trace.','Diagnostic candidate only; no runtime19 or C speed qualification.'])
(D/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q,indent=2))
