from pathlib import Path
import json,sys,runpy,importlib.util
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'published-mode2-x8-g4-original19-compile38-source-v1-20261009';O=S/'run-outputs';D=Path(__file__).resolve().parent;sys.path.insert(0,str(S));m=runpy.run_path(str(S/'run.py'));p=m['load'](S/'preregistration.json');sp=m['load'](S/'source-pins.json');ip=m['load'](S/'input-pins.json')
for n,r in sp.items():m['pin'](S/n,r)
for f,r in ip.items():m['pin'](f,r)
assert m['source_scope'](p,ip)
c=m['load'](O/'report.json');go=c['rootGO'];g=m['load'](m['pin'](go['path'],go));assert m['go_header'](g,p,O)
for rr in g['sourceReviews']:qq=m['load'](m['pin'](rr['path'],rr));assert qq['status']==p['sourceReviewStatus']
for n,rr in c['evidence'].items():m['pin'](O/n,rr)
a=m['load'](O/'attempts.json');rs=m['load'](O/'results.json');assert len(a)==len(rs)==38;assert m['load'](O/'terminal.json')==dict(loaderCalls=38,allChildrenClosed=True,failure=False)
from artifact_admission import accept_artifact_observation
from compiler_output import parse_output
from runtime import counters
spec=importlib.util.spec_from_file_location('saved_native',S/'native-call.py');nc=importlib.util.module_from_spec(spec);spec.loader.exec_module(nc)
for i,r in enumerate(a):
 case=p['cases'][i];assert r['index']==i+1 and r['label']==case['label']and r['nativeArgv']==case['nativeArgv']and r['environment']==p['environment']and r['state']=='terminal'and r['returncode']==0 and r['failure']is None and not r['waitUncertain']and r['captureStopAcknowledged']and r['signalingAuthorityRetired'];assert accept_artifact_observation(r['controllerObservation'])
 for n in ['stdout','stderr']:assert m['receipt'](O/(r['label']+'.'+n))==r[n]
 assert m['receipt'](O/(r['label']+'.limit-journal.jsonl'))==r['limitJournal'];assert m['receipt'](O/(r['label']+'.memory-journal.jsonl'))==r['memoryJournal'];assert nc.resource_journal(O/(r['label']+'.limit-journal.jsonl'),p,case['nativeArgv'])
 out=parse_output((O/(r['label']+'.stdout')).read_bytes(),case);cnt=counters((O/(r['label']+'.stderr')).read_bytes());assert cnt['status']=='valid'and out==r['structuredReportObservation']==rs[i]['report']and cnt==r['counterObservation']and cnt['values']==rs[i]['arena']
 seal=m['load'](O/(r['label']+'.admission.json'));assert seal['nativeArgv']==case['nativeArgv']and seal['rootGO']==go and seal['producer']==p['currentCompiler']and seal['producerContainer']==p['currentCompilerContainer']and seal['existingProducerProof']==p['fixedpointActualProof'];m['pin'](seal['input']['path'],seal['input'])
arts=m['load'](O/'artifacts.json');assert len(arts)==19 and arts==c['original19Images']
old=m['load'](W/'tc-current7618-off18-compile36-actual-review-independent-20261009/report.json');comparisons=[]
for i,ar in enumerate(arts):
 entry=p['entries'][i];assert ar['workload']==entry['workload']and ar['source']==entry['source']and ar['iterations']==entry['iterations']and ar['symbol']==entry['symbol'];payload,exports=m['container'](m['pin'](ar['container']['path'],ar['container']).read_bytes());assert payload==m['pin'](ar['native']['path'],ar['native']).read_bytes()and tuple(ar['selectedExport'])in exports and ar['selectedExport'][0]==entry['symbol']and ar['selectedExport'][2]==1 and [list(x)for x in exports]==ar['exports']
 off=next(x for x in old['joinedOriginal19Images']if x['workload']==ar['workload']);ob=m['pin'](off['native']['path'],off['native']).read_bytes();comparisons.append(dict(workload=ar['workload'],OFFBytes=len(ob),G4Bytes=len(payload),deltaBytes=len(payload)-len(ob),wholeNativeEqual=ob==payload))
q=dict(status='PASS_ROOT_SAVED_CURRENT_G4_X8_ORIGINAL19_COMPILE38_ARTIFACT_IDENTITY_ONLY',sourcePinsSHA256=m['receipt'](S/'source-pins.json')['sha256'],closedCompilerCalls=38,completion=dict(path=str(O/'report.json'),**m['receipt'](O/'report.json')),original19Images=arts,currentG4Native=p['currentCompiler'],currentG4Container=p['currentCompilerContainer'],finiteSamples=sum(r['memorySamples']for r in a),strictSampledCalls=sum(r['controllerObservation']['strictOldMemoryPolicyPassed']for r in a),typedGapCalls=[r['label']for r in a if not r['controllerObservation']['strictOldMemoryPolicyPassed']],comparisons= comparisons,full19FunctionalQualified=False,performanceQualified=False,candidateAdoptionQualified=False,generalMachineSemanticsQualified=False,C2=False)
(D/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k!='original19Images'},indent=2))
