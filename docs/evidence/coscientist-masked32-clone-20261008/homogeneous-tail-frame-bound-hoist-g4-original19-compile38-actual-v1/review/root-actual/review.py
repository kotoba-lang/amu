from pathlib import Path
import json,sys,runpy,importlib.util
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'tc-hft-compose511-bound-hoist-g4-original19-compile38-source-v1-20261009';O=S/'run-outputs';D=Path(__file__).resolve().parent;sys.path.insert(0,str(S));m=runpy.run_path(str(S/'run.py'));pr=m['load'](S/'preregistration.json');ip=m['load'](S/'input-pins.json')
for n,r in m['load'](S/'source-pins.json').items():m['pin'](S/n,r)
for f,r in ip.items():m['pin'](f,r)
assert m['source_scope'](pr,ip) and m['existing_g4_guard'](pr)
c=m['load'](O/'report.json');go=c['rootGO'];g=m['load'](m['pin'](go['path'],go));assert m['go_header'](g,pr,O)
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:assert m['receipt'](S/n)['sha256']==g[k]
for rr in g['sourceReviews']:
 q=m['load'](m['pin'](rr['path'],rr));assert q['status']==pr['sourceReviewStatus']and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256'])
for n,r in c['evidence'].items():m['pin'](O/n,r)
a=m['load'](O/'attempts.json');rs=m['load'](O/'results.json');t=m['load'](O/'terminal.json');assert len(a)==len(rs)==38 and t==dict(loaderCalls=38,allChildrenClosed=True,failure=False)
from artifact_admission import accept_artifact_observation
from compiler_output import parse_output
from runtime import counters
s=importlib.util.spec_from_file_location('saved_native',S/'native-call.py');nc=importlib.util.module_from_spec(s);s.loader.exec_module(nc);tot=0
for i,r in enumerate(a):
 case=pr['cases'][i];assert r['index']==i+1 and r['label']==case['label'] and r['nativeArgv']==case['nativeArgv'] and r['environment']==pr['environment'] and r['state']=='terminal' and r['returncode']==0 and r['failure'] is None and not r['waitUncertain'] and r['captureStopAcknowledged'] and r['signalingAuthorityRetired'];assert accept_artifact_observation(r['controllerObservation'])
 for n in ['stdout','stderr']:assert m['receipt'](O/(r['label']+'.'+n))==r[n]
 for n,k in [('limit-journal','limitJournal'),('memory-journal','memoryJournal')]:assert m['receipt'](O/(r['label']+'.'+n+'.jsonl'))==r[k]
 assert nc.resource_journal(O/(r['label']+'.limit-journal.jsonl'),pr,case['nativeArgv'])
 out=parse_output((O/(r['label']+'.stdout')).read_bytes(),case);cnt=counters((O/(r['label']+'.stderr')).read_bytes());assert cnt['status']=='valid'and out==r['structuredReportObservation']==rs[i]['report']and cnt==r['counterObservation']
 seal=m['load'](O/(r['label']+'.admission.json'));assert seal['nativeArgv']==case['nativeArgv']and seal['rootGO']==go and seal['sourcePinsSHA256']==g['sourcePinsSHA256'];m['pin'](seal['input']['path'],seal['input']);m['pin'](seal['producer']['path'],seal['producer'])
 rows=[json.loads(l)for l in (O/(r['label']+'.memory-journal.jsonl')).read_bytes().splitlines()];assert len(rows)==r['memorySamples'];last=0;bindings={}
 for j,row in enumerate(rows,1):
  assert len(row)==4 and row[0]==j and row[1]>=last and row[2]==r['pid']and 1<=len(row[3])<=2;last=row[1];assert len({z[0]for z in row[3]})==len(row[3]);total=0
  for pid,birth,foot in row[3]:
   assert type(pid)is int and pid>0 and type(birth)is int and birth>0 and type(foot)is int and foot>=0
   if pid in bindings:assert bindings[pid]==birth
   bindings[pid]=birth;total+=foot
  assert total<=4294967296
 tot+=len(rows)
assert len(c['original19Images'])==19
for e,x in zip(pr['entries'],c['original19Images']):
 assert x['workload']==e['workload']and x['source']==e['source']and x['symbol']==e['symbol']and x['iterations']==e['iterations']
 payload,exports=m['container'](m['pin'](x['container']['path'],x['container']).read_bytes());assert payload==m['pin'](x['native']['path'],x['native']).read_bytes()and [list(z)for z in exports]==x['exports'];entry=next(z for z in exports if z[0]==e['symbol']);assert list(entry)==x['selectedExport']and entry[2]==1
ns=next(x for x in c['original19Images']if x['workload']=='nsichneu');assert ns['native']['sha256']=='f00efff199abd9795620e0a13be6695fb05de6d181fe080343b89ceae3703578'
q=dict(status='PASS_ROOT_SAVED_HFT_COMPOSE511_BOUND_HOIST_G4_ORIGINAL19_COMPILE38_ARTIFACTS_ONLY',completion=dict(path=str(O/'report.json'),**m['receipt'](O/'report.json')),closedCompilerCalls=38,sourcePinsSHA256=g['sourcePinsSHA256'],rootGO=go,currentG4Native=pr['currentCompiler'],fixedpointActualProof=pr['fixedpointActualProof'],original19Images=c['original19Images'],finiteSamples=tot,strictCalls=sum(r['controllerObservation']['strictOldMemoryPolicyPassed']for r in a),numericMemoryJournalAudit=True,guestRuntimeQualified=False,full19FunctionalQualified=False,performanceQualified=False,C2=False)
(D/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(dict(status=q['status'],finiteSamples=tot,strictCalls=q['strictCalls'],report=m['receipt'](D/'report.json'))))
