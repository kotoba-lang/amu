from pathlib import Path
import json,sys,importlib.util
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'published-mode2-x8-build-fixture6-source-v1-20261009';O=S/'run-outputs';D=Path(__file__).resolve().parent
sys.path.insert(0,str(S));import run
from compiler_output import parse_output
from runtime import counters
from artifact_admission import accept_artifact_observation
pr=run.load(S/'preregistration.json');sp=run.load(S/'source-pins.json');ip=run.load(S/'input-pins.json');q=run.load(O/'report.json');a=run.load(O/'attempts.json')
for n,r in sp.items():run.pin(S/n,r)
for p,r in ip.items():run.pin(p,r)
for p,r in run.load(O/'generated-pins.json').items():run.pin(p,r)
for r in q['evidence'].values():run.pin(r['path'],r)
assert run.load(O/'terminal.json')=={'loaderCalls':6,'allChildrenClosed':True,'failure':False}
assert len(a)==6 and sum(x['memorySamples']for x in a)==73
spec=importlib.util.spec_from_file_location('callmodule',S/'native-call.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
for c,r in zip(pr['cases'],a):
 assert c['label']==r['label']and c['nativeArgv']==r['nativeArgv']and r['environment']==pr['environment']and r['state']=='terminal'and r['returncode']==0 and r['failure']is None
 assert r['waitEntered']and not r['waitUncertain']and r['captureStopAcknowledged']and r['signalingAuthorityRetired']
 assert accept_artifact_observation(r['controllerObservation'])and r['controllerObservation']['strictOldMemoryPolicyPassed']
 for n in ['stdout','stderr']:run.pin(O/(c['label']+'.'+n),r['controllerObservation']['capture']['hashes'][n])
 raw=(O/(c['label']+'.stdout')).read_bytes();err=(O/(c['label']+'.stderr')).read_bytes();assert parse_output(raw,c)==r['structuredReportObservation']and counters(err)['status']=='valid'
 assert m.resource_journal(O/(c['label']+'.limit-journal.jsonl'),pr,c['nativeArgv'])
 seal=run.load(O/(c['label']+'.admission.json'));assert seal['nativeArgv']==c['nativeArgv']and seal['input']['path']==c['nativeArgv'][8]
 for k in ['producer','producerContainer','input','rootGO']:run.pin(seal[k]['path'],seal[k])
for art in q['artifacts']:
 payload,exports=run.container(run.pin(art['container']['path'],art['container']).read_bytes());assert payload==run.pin(art['native']['path'],art['native']).read_bytes()and [tuple(x)for x in art['exports']]==exports and tuple(art['selectedExport'])in exports
b=run.load(O/'candidate-build-receipt.json');assert run.build_guard(b,pr,q['artifacts'][0]['native'],q['artifacts'][0]['container'],q['rootGO'])
off=(O/'off-fixture.bin').read_bytes();on=(O/'on-fixture.bin').read_bytes();assert len(off)==len(on)==236;diff=[i for i in range(0,len(off),4)if off[i:i+4]!=on[i:i+4]];assert diff==[208,212,224]
r={'status':'PASS_ROOT_SAVED_PUBLISHED_MODE2_X8_BUILD_FIXTURE6_ARTIFACTS_ONLY','sourcePinsSHA256':run.receipt(S/'source-pins.json')['sha256'],'fullSourceAndInputPinsRehashed':True,'closedCalls':6,'strictSampled':6,'sampleCount':73,'wholeArtifacts':q['artifacts'],'changedFixtureWordOffsets':diff,'noMultiDebitOrPrivateChainCoverage':True,'stageClobberCertificateQualified':False,'nativeOperations':0,'performanceQualified':False,'C2':False}
(D/'report.json').write_text(json.dumps(r,indent=2)+'\n');print({'status':r['status'],'report':run.receipt(D/'report.json')})
