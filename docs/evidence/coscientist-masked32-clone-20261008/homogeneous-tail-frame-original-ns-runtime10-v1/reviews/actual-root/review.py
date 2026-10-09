from pathlib import Path
import json,sys,runpy
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'tc-homogeneous-tail-frame-original-ns-runtime10-source-v1-20261009';O=S/'run-outputs';D=Path(__file__).resolve().parent;sys.path.insert(0,str(S));m=runpy.run_path(str(S/'run.py'));pr=m['load'](S/'preregistration.json');sp=m['load'](S/'source-pins.json');ip=m['load'](S/'input-pins.json')
for n,r in sp.items():m['pin'](S/n,r)
for p,r in ip.items():m['pin'](p,r)
assert m['source_scope'](pr)
a=m['load'](O/'attempts.json');r=m['load'](O/'results.json');t=m['load'](O/'terminal.json');assert len(a)==len(r)==10 and t=={'loaderCalls':10,'allChildrenClosed':True,'failure':False}
from artifact_admission import accept_artifact_observation
from runtime import qualify
pairs=[]
for i,x in enumerate(a):
 c=pr['cases'][i];assert x['index']==i+1 and x['nativeArgv']==c['nativeArgv']and x['returncode']==0 and x['state']=='terminal'and x['failure']is None and not x['waitUncertain']and x['captureStopAcknowledged'];assert accept_artifact_observation(x['controllerObservation'])
 for n in ['stdout','stderr']:assert m['receipt'](O/(x['label']+'.'+n))==x[n]
 z=qualify((O/(x['label']+'.stdout')).read_bytes(),(O/(x['label']+'.stderr')).read_bytes(),c['expectedResult']);assert z==r[i]['report']
 if i%2:
  prev=r[i-1]['report'];assert all(prev[k]==z[k]for k in ['result','fuelInitial','fuelRemaining','fuelConsumed','arena17']);pairs.append(dict(workload=c['workload'],n=c['profile'],result=z['result'],fuelConsumed=z['fuelConsumed'],all17ArenasEqual=True))
q=dict(status='PASS_ROOT_SAVED_HFT_RUNTIME10_FINITE_FIVE_PAIR_PARITY_ONLY',sourcePinsSHA256=m['receipt'](S/'source-pins.json')['sha256'],runtimeCalls=10,pairs=pairs,finiteMemorySamples=sum(x['memorySamples']for x in a),strictSampledCalls=sum(x['controllerObservation']['strictOldMemoryPolicyPassed']for x in a),typedGapCalls=[x['label']for x in a if not x['controllerObservation']['strictOldMemoryPolicyPassed']],full19FunctionalQualified=False,generalMachineSemanticsQualified=False,performanceQualified=False,C2=False,notes=['All ten direct waits0 and existing admission accepted; no hardpeak.','C result-only nsichneu oracle checked, no Cfuel/arena/timing.','Only original five nsichneu profiles, one certified tail edge.','Compiler own fixedpoint, all19 artifacts/runtime and C speed still pending.'])
(D/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q,indent=2))
p=W/'compute-address-continuation-20261008-root/checkpoint.json';c=json.loads(p.read_bytes());c['currentHFTRuntime10']={'source':str(S),'rootGO':str(W/'tc-homogeneous-tail-frame-runtime10-go-root-20261009/root-go.json'),'state':'CLOSED0_ONCE10_ROOT_PAIR_PARITY_INDEPENDENT_PENDING','nativeCalls':10,'strictSampledCalls':q['strictSampledCalls'],'finiteSamples':q['finiteMemorySamples'],'rootActualProof':str(D/'report.json'),'pairs':pairs,'performanceQualified':False};c['noLiveProcess']=True;p.write_text(json.dumps(c,indent=2)+'\n')
