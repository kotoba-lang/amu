from pathlib import Path
import json,hashlib,sys,runpy
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'published-mode2-x8-vector-statemate6-source-v2-20261009';O=S/'run-outputs';D=Path(__file__).resolve().parent;sys.path.insert(0,str(S));m=runpy.run_path(str(S/'run.py'));pr=m['load'](S/'preregistration.json');sp=m['load'](S/'source-pins.json');ip=m['load'](S/'input-pins.json')
for n,r in sp.items():m['pin'](S/n,r)
for p,r in ip.items():m['pin'](p,r)
assert m['source_scope'](pr,ip)
a=m['load'](O/'attempts.json');t=m['load'](O/'terminal.json');q=m['load'](O/'report.json');art=m['load'](O/'artifacts.json');assert len(a)==6 and t=={'loaderCalls':6,'allChildrenClosed':True,'failure':False}
from artifact_admission import accept_artifact_observation
for i,r in enumerate(a):
 assert r['index']==i+1 and r['nativeArgv']==pr['cases'][i]['nativeArgv']and r['state']=='terminal'and r['returncode']==0 and r['failure']is None and not r['waitUncertain']and r['captureStopAcknowledged']
 assert accept_artifact_observation(r['controllerObservation'])
 label=r['label']
 for stream in ['stdout','stderr']:
  p=O/(label+'.'+stream);assert m['receipt'](p)==r[stream]
for x in art:
 n=m['pin'](x['native']['path'],x['native']).read_bytes();payload,exports=m['container'](m['pin'](x['container']['path'],x['container']).read_bytes());assert n==payload and tuple(x['selectedExport'])in exports
z=dict(status='PASS_ROOT_SAVED_X8_VECTOR_STATEMATE6_V2_ARTIFACTS_ONLY',sourcePinsSHA256=m['receipt'](S/'source-pins.json')['sha256'],closedCompilerCalls=6,strictMemorySamples=sum(r['memorySamples']for r in a),perCallSamples=[r['memorySamples']for r in a],artifacts=art,knownSizes={'vectorOFF':668,'vectorON':660,'statemateOFF':87716,'statemateON':86184},scope='Saved build artifacts only. Direct child waits; finite sampling, no hard peak. No native guests or performance.',stageClobberCertificateQualified=False,candidateAdoptionQualified=False,C2=False,performanceQualified=False)
(D/'report.json').write_text(json.dumps(z,indent=2)+'\n');print(json.dumps(z,indent=2))
p=W/'compute-address-continuation-20261008-root/checkpoint.json';c=json.loads(p.read_bytes());c['currentPublishedX8VectorStatemate6V2']=dict(source=str(S),state='CLOSED0_ONCE6_ACTUAL_REVIEW_PENDING',rootGO=str(W/'published-mode2-x8-vector-statemate6-go-v2-root-20261009/root-go.json'),actualRootReport=str(D/'report.json'),nativeCalls=6,vectorOFFBytes=668,vectorONBytes=660,statemateONBytes=86184,noLiveProcess=True,performanceQualified=False);p.write_text(json.dumps(c,indent=2)+'\n')
