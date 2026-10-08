from pathlib import Path
import json,sys,runpy,importlib.util
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'published-mode2-x8-g2-g3-g4-fixedpoint6-source-v1-20261009';O=S/'run-outputs';D=Path(__file__).resolve().parent;sys.path.insert(0,str(S));m=runpy.run_path(str(S/'run.py'));p=m['load'](S/'preregistration.json');sp=m['load'](S/'source-pins.json');ip=m['load'](S/'input-pins.json')
for n,r in sp.items():m['pin'](S/n,r)
for f,r in ip.items():m['pin'](f,r)
assert m['source_scope'](p,ip)
c=m['load'](O/'report.json');go=c['rootGO'];g=m['load'](m['pin'](go['path'],go));assert m['go_header'](g,p,O)
for r in g['sourceReviews']:q=m['load'](m['pin'](r['path'],r));assert q['status']==p['sourceReviewStatus']
for n,r in c['evidence'].items():m['pin'](O/n,r)
a=m['load'](O/'attempts.json');rs=m['load'](O/'results.json');assert len(a)==len(rs)==6;assert m['load'](O/'terminal.json')==dict(loaderCalls=6,allChildrenClosed=True,failure=False)
from artifact_admission import accept_artifact_observation
from compiler_output import parse_output
from runtime import counters
spec=importlib.util.spec_from_file_location('saved_native',S/'native-call.py');nc=importlib.util.module_from_spec(spec);spec.loader.exec_module(nc)
for i,r in enumerate(a):
 case=p['cases'][i];assert r['index']==i+1 and r['label']==case['label']and r['nativeArgv']==case['nativeArgv']and r['environment']==p['environment']and r['state']=='terminal'and r['returncode']==0 and r['failure']is None and not r['waitUncertain']and r['captureStopAcknowledged']and r['signalingAuthorityRetired'];assert accept_artifact_observation(r['controllerObservation'])
 for n in ['stdout','stderr']:assert m['receipt'](O/(r['label']+'.'+n))==r[n]
 assert m['receipt'](O/(r['label']+'.limit-journal.jsonl'))==r['limitJournal'];assert m['receipt'](O/(r['label']+'.memory-journal.jsonl'))==r['memoryJournal'];assert nc.resource_journal(O/(r['label']+'.limit-journal.jsonl'),p,case['nativeArgv'])
 out=parse_output((O/(r['label']+'.stdout')).read_bytes(),case);cnt=counters((O/(r['label']+'.stderr')).read_bytes());assert cnt['status']=='valid'and out==r['structuredReportObservation']==rs[i]['report']and cnt==r['counterObservation']and cnt['values']==rs[i]['arena']
 seal=m['load'](O/(r['label']+'.admission.json'));assert seal['nativeArgv']==case['nativeArgv']and seal['rootGO']==go;assert m['whole_compiler'](seal['producer'],seal['producerContainer'])
 if seal['producerBuild']is not None:br=seal['producerBuild'];m['build_guard'](m['load'](m['pin'](br['path'],br)),p,seal['producer'],seal['producerContainer'],go,case['generation']-1)
arts=m['load'](O/'artifacts.json')
for ar in arts:
 ar['exports']=[tuple(x)for x in ar['exports']];m['build_guard'](m['load'](O/('G'+str(ar['generation'])+'-build-receipt.json')),p,ar['native'],ar['container'],go,ar['generation'])
assert m['fixedpoint'](arts)
q=dict(status='PASS_ROOT_SAVED_X8_G2_G3_G4_FIXEDPOINT6_WHOLE_COMPILER_ONLY',sourcePinsSHA256=m['receipt'](S/'source-pins.json')['sha256'],closedCompilerCalls=6,artifacts=arts,finiteSamples=sum(r['memorySamples']for r in a),strictSampledCalls=sum(r['controllerObservation']['strictOldMemoryPolicyPassed']for r in a),typedGapCalls=[r['label']for r in a if not r['controllerObservation']['strictOldMemoryPolicyPassed']],G2G3G4WholeNativeEqual=True,G2G3G4WholeContainerEqual=True,G1EqualityRequired=False,full19FunctionalQualified=False,performanceQualified=False,candidateAdoptionQualified=False,generalMachineSemanticsQualified=False,C2=False)
(D/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q,indent=2))
