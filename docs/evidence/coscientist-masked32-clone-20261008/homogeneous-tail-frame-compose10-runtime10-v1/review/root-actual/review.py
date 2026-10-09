from pathlib import Path
import json,sys,runpy,importlib.util
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'tc-hft-compose10-original-ns-runtime10-source-v1-20261009';O=S/'run-outputs';D=Path(__file__).resolve().parent;sys.path.insert(0,str(S));m=runpy.run_path(str(S/'run.py'));p=m['load'](S/'preregistration.json')
for n,r in m['load'](S/'source-pins.json').items():m['pin'](S/n,r)
for n,r in m['load'](S/'input-pins.json').items():m['pin'](n,r)
assert m['source_scope'](p);c=m['load'](O/'report.json');go=c['rootGO'];g=m['load'](m['pin'](go['path'],go));m['go_header'](g,p,O)
schema=m['load'](S/'go-schema.json');assert len(schema['exactKeys'])==len(set(schema['exactKeys']))==19 and set(schema['exactKeys'])==set(g)
for rr in g['sourceReviews']:
 q=m['load'](m['pin'](rr['path'],rr));assert q['status']==p['sourceReviewStatus'] and q['sourcePinsSHA256']==g['sourcePinsSHA256']
for n,r in c['evidence'].items():m['pin'](O/n,r)
a=m['load'](O/'attempts.json');rs=m['load'](O/'results.json');assert len(a)==len(rs)==10 and m['load'](O/'terminal.json')==dict(loaderCalls=10,allChildrenClosed=True,failure=False)
from artifact_admission import accept_artifact_observation
from runtime import qualify
s=importlib.util.spec_from_file_location('saved_native',S/'native-call.py');nc=importlib.util.module_from_spec(s);s.loader.exec_module(nc)
for i,r in enumerate(a):
 case=p['cases'][i];assert r['index']==i+1 and r['label']==case['label'] and r['nativeArgv']==case['nativeArgv'] and r['environment']==p['environment'] and r['state']=='terminal' and r['returncode']==0 and r['failure'] is None and not r['waitUncertain'] and r['captureStopAcknowledged'] and r['signalingAuthorityRetired'];assert accept_artifact_observation(r['controllerObservation'])
 for n in ['stdout','stderr']:assert m['receipt'](O/(r['label']+'.'+n))==r[n]
 for n,k in [('limit-journal','limitJournal'),('memory-journal','memoryJournal')]:assert m['receipt'](O/(r['label']+'.'+n+'.jsonl'))==r[k]
 assert nc.resource_journal(O/(r['label']+'.limit-journal.jsonl'),p,case['nativeArgv'])
 decoded=qualify((O/(r['label']+'.stdout')).read_bytes(),(O/(r['label']+'.stderr')).read_bytes(),case['expectedResult']);assert decoded==r['structuredReportObservation']==rs[i]['report']
 seal=m['load'](O/(r['label']+'.admission.json'));assert seal['nativeArgv']==case['nativeArgv'] and seal['rootGO']==go and seal['native']==case['native'] and seal['container']==case['container'] and seal['source']==case['source'];payload,exports=m['container'](m['pin'](seal['container']['path'],seal['container']).read_bytes());assert payload==m['pin'](seal['native']['path'],seal['native']).read_bytes() and ('batch',36440,1) in exports
 samples=[json.loads(x)for x in (O/(r['label']+'.memory-journal.jsonl')).read_text().splitlines()];assert len(samples)==r['memorySamples']
 births={};previousTime=-1
 for ordinal,sample in enumerate(samples,1):
  assert type(sample) is list and len(sample)==4 and sample[0]==ordinal and type(sample[1]) is int and previousTime<sample[1]<2**64 and sample[2]==r['pid']
  members=sample[3];assert type(members) is list and 1<=len(members)<=2 and len({v[0] for v in members})==len(members) and r['pid'] in [v[0] for v in members]
  for pid,birth,foot in members:
   assert all(type(v) is int for v in [pid,birth,foot]) and 0<pid<2**31 and 0<birth<2**64 and 0<=foot<2**64 and (pid not in births or births[pid]==birth);births[pid]=birth
  assert len(births)<=2 and sum(v[2] for v in members)<=4294967296;previousTime=sample[1]
for i in range(0,10,2):assert rs[i]['report']==rs[i+1]['report']
q=dict(status='PASS_ROOT_SAVED_HFT_COMPOSE10_RUNTIME10_ORIGINAL_FIVE_PAIRS_ONLY',completion=dict(path=str(O/'report.json'),**m['receipt'](O/'report.json')),runtimeCalls=10,profiles=[0,1,2,17,32],results=[rs[i]['report'] for i in range(0,10,2)],fuel=[rs[i]['report']['fuelConsumed']for i in range(0,10,2)],finiteSamples=sum(r['memorySamples']for r in a),strictCalls=sum(r['controllerObservation']['strictOldMemoryPolicyPassed']for r in a),sourcePinsSHA256=g['sourcePinsSHA256'],rootGO=go,all19Qualified=False,generalPrivateABIQualified=False,performanceQualified=False,hardPeakQualified=False,C2=False)
(D/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k!='results'}))
