from pathlib import Path
import subprocess,json,sys
W=Path(__file__).resolve().parent;R=Path('/Users/junkawasaki/github/wt/codex/seed-copy-chain48-20261014');O=W/'main-selfbuild-v1';raw=W/'standard-controls-raw';raw.mkdir(exist_ok=False);calls=[]
checks=['check-bounded-lookup.py','check-certified-scalar-calls.py','check-twoarg-comparisons.py','check-sequential-scan.py','check-positive-quotient.py','check-positive-quotient-proof.py','check-mask-direct-source.py','check-prepaid-fuel-reuse.py','check-nonzero-guard-charge.py','check-adjacent-fuel-reload.py']
jobs=[('native-selfbuild',['scripts/seed/build-adopted.py','--output',str(O),'--generations','2'])]+[(p,['scripts/seed/'+p,'--selfbuild-output',str(O)])for p in checks]
for name,args in jobs:
 with (raw/(name+'.stdout')).open('wb')as out,(raw/(name+'.stderr')).open('wb')as err:z=subprocess.run([sys.executable,*args],cwd=R,stdout=out,stderr=err,timeout=3600)
 calls.append(dict(name=name,exit=z.returncode));(W/'standard-controls-calls.json').write_text(json.dumps(calls,indent=2)+'\n');assert z.returncode==0,(name,z.returncode);print('PASS',name,flush=True)
(W/'standard-controls-receipt.json').write_text(json.dumps(dict(status='PASS_STANDARD_NATIVE_SELFBUILD_AND_ALL10_CONTROLS',selfbuildOutput=str(O),checks=checks,calls=calls,performanceMeasured=False),indent=2)+'\n')
