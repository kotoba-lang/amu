from pathlib import Path
import hashlib,json,subprocess,sys,os
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'compute-result-native-edge-replay-source-v1-20261009-independent';O=Path(__file__).parent
load=lambda p:json.loads(p.read_bytes())
def rec(p):b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
sp=load(D/'source-pins.json');ip=load(D/'input-pins.json')
for n,r in sp.items():assert rec(D/n)=={k:r[k] for k in ['bytes','sha256']}
for n,r in ip.items():assert rec(Path(n))=={k:r[k] for k in ['bytes','sha256']}
c=O/'copied-controls';c.mkdir();(c/'differential_controls.py').write_bytes((D/'differential_controls.py').read_bytes());q=subprocess.run([sys.executable,str(c/'differential_controls.py')],capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=30);assert q.returncode==0,q.stderr;model=json.loads(q.stdout);assert model==load(D/'controls.json');(O/'control.stdout').write_bytes(q.stdout)
r=dict(status='PASS_ROOT_FINITE_NATIVE_FRAGMENT_MODELS_ONLY_INTEGRATION_HOLD',sourcePinsSHA256=rec(D/'source-pins.json')['sha256'],verifiedSourceFiles=len(sp),verifiedInputFiles=len(ip),verifiedInputBytes=sum(x['bytes'] for x in ip.values()),controls=model,nativeOperations=0,sharedCIDReuseQualified=False,currentNativeIntegrationQualified=False,performanceQualified=False,limitations=['Historical V7 is absent from current41','Current ctx memo fragment has no owned scratch location or native parser test','JSON/SHA model is not native IPLD encoding','Current G4 candidate lineage requires separate observer registration'])
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(status=r['status'],checks=model['arithmeticAndContributionChecks'],report=rec(O/'report.json'))))
