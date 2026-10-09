from pathlib import Path
import json,sys,runpy,importlib.util,struct
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'tc-homogeneous-tail-frame-compose511-bound-hoist-native4-source-v1-20261009';O=S/'run-outputs';D=Path(__file__).resolve().parent;sys.path.insert(0,str(S));m=runpy.run_path(str(S/'run.py'));p=m['load'](S/'preregistration.json')
for n,r in m['load'](S/'source-pins.json').items():m['pin'](S/n,r)
for f,r in m['load'](S/'input-pins.json').items():m['pin'](f,r)
m['source_scope'](p);c=m['load'](O/'report.json');go=c['rootGO'];g=m['load'](m['pin'](go['path'],go));assert g['status']==p['rootGOStatus'] and g['maximumLoaderCalls']==4 and g['noRetry'] is True
for rr in g['sourceReviews']:
 q=m['load'](m['pin'](rr['path'],rr));assert q['status']==p['sourceReviewStatus'] and q['sourcePinsSHA256']==g['sourcePinsSHA256']
for n,r in c['evidence'].items():m['pin'](O/n,r)
a=m['load'](O/'attempts.json');rs=m['load'](O/'results.json');t=m['load'](O/'terminal.json');assert len(a)==len(rs)==4 and t['closed'] is True and t['failure'] is False
from artifact_admission import accept_artifact_observation
from compiler_output import parse_output
from runtime import counters
s=importlib.util.spec_from_file_location('saved_native',S/'native-call.py');nc=importlib.util.module_from_spec(s);s.loader.exec_module(nc)
for i,r in enumerate(a):
 case=p['cases'][i];assert r['index']==i+1 and r['label']==case['label'] and r['nativeArgv']==case['nativeArgv'] and r['environment']==p['environment'] and r['state']=='terminal' and r['returncode']==0 and r['failure'] is None and not r['waitUncertain'] and r['captureStopAcknowledged'] and r['signalingAuthorityRetired'];assert accept_artifact_observation(r['controllerObservation'])
 for n in ['stdout','stderr']:assert m['receipt'](O/(r['label']+'.'+n))==r[n]
 for n,k in [('limit-journal','limitJournal'),('memory-journal','memoryJournal')]:assert m['receipt'](O/(r['label']+'.'+n+'.jsonl'))==r[k]
 assert nc.resource_journal(O/(r['label']+'.limit-journal.jsonl'),p,case['nativeArgv'])
 out=parse_output((O/(r['label']+'.stdout')).read_bytes(),case);cnt=counters((O/(r['label']+'.stderr')).read_bytes());assert cnt['status']=='valid' and out==r['structuredReportObservation']==rs[i]['report'] and cnt==r['counterObservation']
 seal=m['load'](O/(r['label']+'.admission.json'));assert seal['nativeArgv']==case['nativeArgv'] and seal['rootGO']==go and seal['sourcePinsSHA256']==g['sourcePinsSHA256'];m['pin'](seal['input']['path'],seal['input']);m['pin'](seal['producer']['path'],seal['producer'])
 artifact=rs[i]['artifact'];b=m['pin'](artifact['path'],artifact).read_bytes()
 if case['kind']=='compile':
  payload,exports=m['container'](b);assert len(b)==out['containerBytes']
  if case['arity']==0:assert exports==[('main',0,0)]
 else:
  payload,exports=m['container'](Path(seal['input']['path']).read_bytes());assert b==payload;selected=next(e for e in exports if e[0]==case['symbol']);assert selected[2]==case['arity'] and out==dict(kind='extract',offset=selected[1],nativeBytes=len(payload),arity=selected[2])
native=rs[1]['artifact'];packed=rs[0]['artifact'];assert m['build_guard'](m['load'](O/'candidate-build-receipt.json'),p,native,packed,go)
ec=m['load'](S/'emission-certificate.json');old=m['pin'](ec['originalOffContainer']['path'],ec['originalOffContainer']).read_bytes();new=Path(rs[2]['artifact']['path']).read_bytes();cut=old.index(b'\n\n')+2;expected=bytearray(old)
assert len(ec['changes'])==492
for x in ec['changes']:
 pos=cut+x['physicalByteOffset'];assert struct.unpack_from('<I',old,pos)[0]==x['before'];struct.pack_into('<I',expected,pos,x['after'])
assert bytes(expected)==new and old[:cut]==new[:cut] and len(old)==len(new)
assert rs[2]['artifact']['sha256']==ec['expectedContainerSHA256'] and rs[3]['artifact']['sha256']==ec['expectedWholeNativeSHA256']
q=dict(status='PASS_ROOT_SAVED_HFT_COMPOSE511_BOUND_HOIST_NATIVE4_ARTIFACT_IDENTITY_ONLY',completion=dict(path=str(O/'report.json'),**m['receipt'](O/'report.json')),calls=4,sourcePinsSHA256=g['sourcePinsSHA256'],rootGO=go,candidateNative=native,candidateContainer=packed,originalNSNative=rs[3]['artifact'],originalNSContainer=rs[2]['artifact'],exactWordChanges=492,allOtherBytesUnchanged=True,finiteSamples=sum(r['memorySamples'] for r in a),strictCalls=sum(r['controllerObservation']['strictOldMemoryPolicyPassed'] for r in a),typedGapCalls=[r['label'] for r in a if not r['controllerObservation']['strictOldMemoryPolicyPassed']],guestRuntimeQualified=False,performanceQualified=False,C2=False)
tot=0
for attempt in a:
 rows=[json.loads(l) for l in (O/(attempt['label']+'.memory-journal.jsonl')).read_bytes().splitlines()]
 assert len(rows)==attempt['memorySamples'];last=0;bindings={}
 for i,row in enumerate(rows,1):
  assert len(row)==4 and row[0]==i and row[1]>=last and row[2]==attempt['pid'] and 1<=len(row[3])<=2;last=row[1]
  assert len({z[0] for z in row[3]})==len(row[3]);total=0
  for pid,birth,foot in row[3]:
   assert type(pid)is int and pid>0 and type(birth)is int and birth>0 and type(foot)is int and foot>=0
   if pid in bindings:assert bindings[pid]==birth
   bindings[pid]=birth;total+=foot
  assert total<=4294967296
 tot+=len(rows)
assert tot==q['finiteSamples']==69
q['numericMemoryJournalAudit']={'rows':tot,'monotonicSequencePIDBirthAndSumBound':True,'hardPeakQualified':False}
(D/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q))
