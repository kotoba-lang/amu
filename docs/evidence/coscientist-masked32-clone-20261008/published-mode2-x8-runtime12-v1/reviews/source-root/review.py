from pathlib import Path
import json,runpy,sys,subprocess
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'published-mode2-x8-statemate-vector-runtime12-source-v1-20261009';D=Path(__file__).resolve().parent;sys.path.insert(0,str(S));m=runpy.run_path(str(S/'run.py'));pr=m['load'](S/'preregistration.json');sp=m['load'](S/'source-pins.json');ip=m['load'](S/'input-pins.json')
for n,r in sp.items():m['pin'](S/n,r)
for p,r in ip.items():m['pin'](p,r)
assert len(sp)==22 and len(ip)==45 and sum(r['bytes']for r in ip.values())==3073284
assert m['source_scope'](pr)
delta=m['load'](S/'delta.json');old=Path(delta['baseWorkspace'])
for n in delta['copiedComponents']:assert (S/n).read_bytes()==(old/n).read_bytes()
controls=[]
for n in ['pure-controls.py','wrapper-controls.py']:
 r=subprocess.run([pr['interpreter']['path'],str(S/n)],cwd=S,capture_output=True,check=True);(D/(n+'.stdout')).write_bytes(r.stdout);(D/(n+'.stderr')).write_bytes(r.stderr);controls.append(dict(script=n,returncode=r.returncode))
for n,r in sp.items():m['pin'](S/n,r)
assert not Path(pr['freshOutputRoot']).exists()
q=dict(status=pr['sourceReviewStatus'],sourcePinsSHA256=m['receipt'](S/'source-pins.json')['sha256'],driverSHA256=m['receipt'](S/'run.py')['sha256'],preregistrationSHA256=m['receipt'](S/'preregistration.json')['sha256'],exactSourceFiles=len(sp),exactInputFiles=len(ip),inputBytes=3073284,scopePassed=True,controls=controls,qualifiedNineComponentsUnchanged=True,sourceOnly=True,nativeCallsMade=0,maximumLoaderCalls=12,originalStatemateProfiles=[0,1,2,17,32],guestFuelPerCall=16777216,fullArena17PairParityRequired=True,loaderProtocolPremisesRechecked=True,C2=False,performanceQualified=False,generalAdoptionQualified=False,fullMachineSemanticsQualified=False,notes=['Original statemate ten calls plus vector fixture pair; twelve own-export arity1 typed argv without --.','Vector expected result3 follows frozen synthetic source; no guessed fuel golden.','Six proof receipts; saved C result-only rows no Cfuel/arena/timing import.','Host outer escalation required with unchanged loader-owned sandbox/resources.','Direct child wait and finite samples; typed termination-gap refusal rules unchanged.'])
(D/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q,indent=2))
