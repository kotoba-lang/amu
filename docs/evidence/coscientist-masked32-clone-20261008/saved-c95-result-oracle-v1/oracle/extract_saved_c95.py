from pathlib import Path
import json,hashlib,stat
W=Path('/Users/junkawasaki/github/workspaces/codex');R=Path(__file__).parent;C=W/'vector-leaf-straight-read-cache-fresh-consumer-functional285-go-v2-root/collected';B=W/'vector-leaf-straight-read-cache-current19-build52-go-v2-root/collected';A=W/'vector-leaf-straight-read-cache-fresh-consumer-functional285-actual-review-v2-independent/report.json';P=Path('/Users/junkawasaki/github/wt/amu-seed17/bench/embench/comparison-matrix.json');pins={};sha=lambda b:hashlib.sha256(b).hexdigest()
def read(p):
 assert stat.S_ISREG(p.lstat().st_mode) and not p.is_symlink();b=p.read_bytes();pins[str(p)]={'bytes':len(b),'sha256':sha(b)};return b
def load(p):return json.loads(read(p))
def verify(p,v):
 b=read(p);assert len(b)==v['bytes'] and sha(b)==v['sha256'];return b
def nodup(pairs):
 d={}
 for k,v in pairs:
  assert k not in d,'duplicate key';d[k]=v
 return d
FIELDS={'format','calls','warmupCalls','elapsedNanoseconds','result','maxRssBytes','fuelPerCall','contextFuelBefore','contextFuelAfter','contextFuelConsumed','nativeArtifactAbi','artifactKind','nativeArenaStatus','nativeArenas'}
def parse(b):
 assert len(b)<=4096
 x=json.loads(b,object_pairs_hook=nodup,parse_constant=lambda x:(_ for _ in ()).throw(AssertionError('nonfinite')));assert isinstance(x,dict) and set(x)==FIELDS
 for k in ['calls','warmupCalls','elapsedNanoseconds','result','maxRssBytes','fuelPerCall','contextFuelBefore','contextFuelAfter','contextFuelConsumed']:assert type(x[k]) is int and 0<=x[k]<2**64
 assert x['format']=='kotoba.runtime-sample/v1' and x['calls']==1 and x['warmupCalls']==0 and x['nativeArtifactAbi']=='kotoba.native-artifact-i64x8-to-i64-indirect/v1' and x['artifactKind']=='dylib' and x['nativeArenaStatus']=='unavailable-C' and x['nativeArenas'] is None
 assert x['fuelPerCall']==x['contextFuelBefore']==x['contextFuelAfter']==16777216 and x['contextFuelConsumed']==0 and x['result'] in [0,1]
 return x
review=load(A);assert review['status']=='PASS_ACTUAL_FRESH_CONSUMER_FUNCTIONAL285_V2_INDEPENDENT_SAVED_RAW_ONLY' and review['independent'] and review['functionalQualified'] and review['completedTriples']==95 and review['CNoFuelChargeAndUnavailableNullArenas']
oldpins=json.loads(verify(Path(review['inputPins']['path']),review['inputPins']));pr=load(C/'source/preregistration.json');assert sha(read(C/'source/preregistration.json'))==review['preregistrationSHA256'];assert sha(read(C/'source/source-pins.json'))==review['sourcePinsSHA256'];buildReview=load(C/'source/build52-independent-report.json');assert sha(read(C/'source/build52-independent-report.json'))==review['buildIndependentReportSHA256']
mat=load(P);assert len(pr['cases'])==len(mat['entries'])==19;ledger=load(C/'functional285/children/attempts.json');summary=load(C/'functional285/report.json');comparisons=load(C/'functional285/comparisons.json');collection=load(C/'collection-receipt.json');members={v['path']:v for v in collection['members']};assert len(ledger)==285 and len(summary['comparisons'])==95;assert load(C/'functional285/terminal.json')=={'children':285,'allClosed':True,'failure':False,'noRetry':True}
for p in [C/'source/preregistration.json',C/'source/source-pins.json',C/'functional285/report.json',C/'functional285/children/attempts.json',C/'functional285/comparisons.json',C/'functional285/terminal.json']:
 assert str(p) in oldpins;verify(p,oldpins[str(p)])
identityBefore=load(B/'build52/identity-before.json');identityAfter=load(B/'build52/identity-after.json');assert identityBefore==identityAfter==buildReview['identityBeforeAfter'];assert identityBefore['target']=='arm64-apple-darwin25.2.0' and identityBefore['OSBuild']=='25C56'
consumer=Path(pr['consumerSource']['path']);verify(consumer,pr['consumerSource']);assert b'result = fn(input, 0, 0, 0, 0, 0, 0, (int64_t)(uintptr_t)context);' in consumer.read_bytes()
packageManifest=load(B/'package/manifest.json');cInputs=[v for v in packageManifest['members'] if v['path'].startswith('package/c-inputs/')];resultRows=[];witness=[];builds=[]
for ci,(case,m) in enumerate(zip(pr['cases'],mat['entries'])):
 assert (case['workload'],case['symbol'],case['profiles'],case['source']['sha256'])==(m['workload'],m['symbol'],m['iterations'],m['expectedSourceSha256']);verify(Path(case['source']['path']),case['source']);assert len(case['profiles'])==5
 build={}
 for role,n in [('C','c.dylib'),('runner','runner'),('header','header.h')]:
  p=B/'build52'/case['workload']/n;verify(p,case[role]);build[role]={'localPath':str(p),**case[role]}
 assert buildReview['images'][ci]==case['buildAnchors'];builds.append({'workload':case['workload'],'symbol':case['symbol'],'CSymbol':case['CSymbol'],'build':build})
 for pi,n in enumerate(case['profiles']):
  index=(ci*5+pi)*3+3;row=ledger[index-1];assert row['index']==index and row['label']==case['workload']+'-C-n'+str(n) and row['state']=='terminal' and row['returncode']==0 and row['exception'] is None and row['cleanupException'] is None
  assert row['argv']==[case['runner']['path'],'dylib',case['C']['path'],case['CSymbol'],'aarch64',str(n),'1','0','16777216'];raw=C/'functional285/children'/(str(index)+'.stdout');err=C/'functional285/children'/(str(index)+'.stderr');out=verify(raw,row['stdout']);assert verify(err,row['stderr'])==b''
  for p in [raw,err]:verify(p,members[str(p.relative_to(C))]);assert str(p) in oldpins;verify(p,oldpins[str(p)])
  x=parse(out);saved=summary['comparisons'][ci*5+pi];assert saved['workload']==case['workload'] and saved['n']==n and saved['arms']['C']=={k:v for k,v in x.items() if k not in ['elapsedNanoseconds','maxRssBytes']};assert x['result']==(0 if n==0 else 1)
  resultRows.append({'workload':case['workload'],'sourceSHA256':case['source']['sha256'],'symbol':case['symbol'],'n':n,'result':x['result']});witness.append({'workload':case['workload'],'n':n,'CSymbol':case['CSymbol'],'source':case['source'],'historicalChildIndex':index,'argv':row['argv'],'stdout':{'localPath':str(raw),**row['stdout']},'stderr':{'localPath':str(err),**row['stderr']},'returncode':0,'abi':x['nativeArtifactAbi']})
assert len(resultRows)==len({(x['workload'],x['n']) for x in resultRows})==95
# Finite raw parser controls, no calls or native instructions.
x=parse(out);controls=[]
for name,b in [('boolinteger',out.replace(b'"result":1',b'"result":true').replace(b'"result": 1',b'"result": true')),('duplicate',out.replace(b'{',b'{"result":1,',1)),('extra',json.dumps(dict(x,extra=1)).encode()),('missing',json.dumps({k:v for k,v in x.items() if k!='result'}).encode()),('negative',json.dumps(dict(x,result=-1)).encode()),('overflow',json.dumps(dict(x,result=2**64)).encode()),('nonboolean',json.dumps(dict(x,result=2)).encode()),('Cfuel',json.dumps(dict(x,contextFuelConsumed=1)).encode()),('trailing',out+b'{}')]:
 try:parse(b)
 except (AssertionError,ValueError):controls.append({'mutation':name,'refused':True})
 else:raise AssertionError('mutation not rejected:'+name)
oracle={'status':'PASS_SAVED_C95_RESULT_ONLY_ORACLE_SOURCE_PROFILE_BOUND','schema':'tc.original19.saved-c95-result-oracle/v1','originalWorkloads':19,'profiles':95,'numericResultDomain':'integer Boolean 0 or 1 only','currentOFFNativeReused':False,'rows':resultRows,'timingQualified':False,'newHostQualified':False,'runtimeGuestExecutedByReviewer':False}
(R/'oracle.json').write_text(json.dumps(oracle,indent=2)+'\n');prov={'status':'PASS_SAVED_C95_PROVENANCE_ONLY','independentSaved285Review':{'path':str(A),**pins[str(A)]},'inputPinsFromIndependentReview':review['inputPins'],'hostHistorical':{'destination':pr['destination'],'arch':'arm64','OS':identityBefore['OS'],'OSBuild':identityBefore['OSBuild'],'compilerTarget':identityBefore['target'],'kernelVersionScope':'Darwin25.2.0 from captured compiler target; no standalone uname/kernel runtime witness asserted.','numericABI':'8 signed64 arguments -> signed64 result; profile n bounded and sent in x0, context x7 on aarch64; result serialized unsigned64 but admitted only0/1. C logical symbol comes from CSymbol while original native symbol is separately bound.'},'identityBeforeAfter':identityBefore,'CBuildAndRunnerReceipts':builds,'cInputSourceManifestReceipts':cInputs,'rawWitnesses95':witness,'parserControls':controls,'scope':'Reusable saved C Boolean answers for exact original19 source/profile/symbol inputs only. Fresh current OFF/TC190 must independently run and verify fuel/trap/arenas. No historical native comparison, timings, memory/quiet or current-host admission imported.','limitations':['C source tree witness is pinned manifest plus previously independently verified build52 provenance; only selected19 C dylib/runner/header bytes rehashed here.','HistoricalC no fuel consumption and arenas unavailable/null; C oracle cannot validate current native fuel/arena/trap equivalence.','No cache/reuse performance, hardware execution, new host or universal semantic proof.'],'operations':{'nativeCCompilerProcessThreadFDPipeNetworkCalls':0}}
(R/'provenance.json').write_text(json.dumps(prov,indent=2)+'\n');(R/'input-pins.json').write_text(json.dumps(pins,indent=2)+'\n');report={'status':'PASS_INDEPENDENT_SAVED_C95_RESULT_ONLY_ORACLE','independent':True,'workloads':19,'cases':95,'rawCStdoutVerified':95,'emptyCStderrVerified':95,'parserNegativeControls':9,'oracle':{'path':str(R/'oracle.json'),'bytes':(R/'oracle.json').stat().st_size,'sha256':sha((R/'oracle.json').read_bytes())},'provenance':{'path':str(R/'provenance.json'),'bytes':(R/'provenance.json').stat().st_size,'sha256':sha((R/'provenance.json').read_bytes())},'inputPins':{'path':str(R/'input-pins.json'),'bytes':(R/'input-pins.json').stat().st_size,'sha256':sha((R/'input-pins.json').read_bytes())},'scope':prov['scope'],'operations':prov['operations']};(R/'report.json').write_text(json.dumps(report,indent=2)+'\n');b=(R/'report.json').read_bytes();print(len(b),sha(b));print(report['oracle'])
