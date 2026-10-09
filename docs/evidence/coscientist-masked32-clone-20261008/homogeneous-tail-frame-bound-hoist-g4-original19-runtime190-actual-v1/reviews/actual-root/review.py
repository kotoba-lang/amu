from pathlib import Path
import hashlib,json,importlib.util,sys
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-hft-g4-held-v6-original19-runtime190-source-v1-20261009-dense';O=D/'run-outputs';A=Path(__file__).parent
load=lambda p:json.loads(p.read_bytes())
def rec(p):b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
seen=set()
def walk(x):
 if isinstance(x,dict):
  if all(k in x for k in ['path','bytes','sha256']):
   p=Path(x['path']);assert rec(p)=={k:x[k] for k in ['path','bytes','sha256']},p;seen.add(str(p))
  for v in x.values():walk(v)
 elif isinstance(x,list):
  for v in x:walk(v)
pr=load(D/'preregistration.json');report=load(O/'report.json');attempts=load(O/'attempts.json');results=load(O/'results.json');terminal=load(O/'terminal.json')
assert terminal==dict(loaderCalls=190,allChildrenClosed=True,failure=False)
assert report['runtimeCalls']==190 and report['pairedProfiles']==95 and report['originalWorkloads']==19 and report['results']==results
sys.path.insert(0,str(D));from runtime import qualify
for i,(case,a,r) in enumerate(zip(pr['cases'],attempts,results),1):
 assert a['index']==i and a['label']==r['label']==case['label'] and r['case']==case
 assert a['state']=='terminal' and a['returncode']==r['returncode']==0 and a['waitEntered'] and not a['waitUncertain'] and a['signalingAuthorityRetired'] and a['captureStopAcknowledged'] and a['ownershipWriterStopAcknowledged'] and not a['failure'] and not a['watchdogErrors']
 assert a['environment']==pr['environment'] and a['nativeArgv']==case['nativeArgv']
 out=(O/(case['label']+'.stdout')).read_bytes();err=(O/(case['label']+'.stderr')).read_bytes();parsed=qualify(out,err,case['expectedResult']);assert parsed==r['report']==a['structuredReportObservation']
 assert hashlib.sha256(out).hexdigest()==r['rawStdoutSHA256'] and hashlib.sha256(err).hexdigest()==r['rawStderrSHA256'] and r['strictHeldSamplingPolicyPassed']
 assert len(parsed['arena17'])==17 and parsed['fuelInitial']==16777216 and parsed['fuelConsumed']==parsed['fuelInitial']-parsed['fuelRemaining']
 if i%2==0:assert all(results[i-2]['report'][k]==parsed[k] for k in ['result','fuelInitial','fuelRemaining','fuelConsumed','arena17'])
 assert rec(O/(case['label']+'.admission.json'))['sha256']==a['invocation']
 for key,suffix in [('stdout','.stdout'),('stderr','.stderr'),('memoryJournal','.memory-journal.jsonl'),('ownershipJournal','.ownership-journal.jsonl'),('limitJournal','.limit-journal.jsonl')]:
  z=O/(case['label']+suffix);assert {k:rec(z)[k]for k in ['bytes','sha256']}==a[key];seen.add(str(z))
 walk(a);walk(r)
walk(report);walk(pr)
for n,r in load(D/'source-pins.json').items():assert {k:rec(D/n)[k] for k in ['bytes','sha256']}==r
for n,r in load(D/'input-pins.json').items():assert {k:rec(Path(n))[k] for k in ['bytes','sha256']}=={k:r[k] for k in ['bytes','sha256']}
q=dict(status='PASS_ROOT_SAVED_HFT_G4_HELD_V6_ORIGINAL19_RUNTIME190_DIAGNOSTIC_ONLY',completion=rec(O/'report.json'),closedRuntimeCalls=190,pairedProfiles=95,originalWorkloads=19,memorySamples=sum(a['memorySamples'] for a in attempts),all190StrictHeldSamplingPolicyPassed=True,resultFuelArena17Parity=True,CBooleanResultParity=True,verifiedDistinctReceiptPaths=len(seen),nativeOperations=0,performanceQualified=False,hardPeakQualified=False,generalABICertificateQualified=False,C2=False)
(A/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q))
