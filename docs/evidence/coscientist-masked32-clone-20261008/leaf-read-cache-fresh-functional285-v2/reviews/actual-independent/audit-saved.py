"""Independent saved-byte audit. No operative imports or execution."""
import hashlib,json,stat
from pathlib import Path
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'vector-leaf-straight-read-cache-fresh-consumer-functional285-source-v2-receipt-binding';G=W/'vector-leaf-straight-read-cache-fresh-consumer-functional285-go-v2-root';C=G/'collected';R=Path(__file__).resolve().parent;B=W/'vector-leaf-straight-read-cache-current19-build52-go-v2-root';V1=W/'vector-leaf-straight-read-cache-fresh-consumer-functional285-source-v1'
H=lambda b:hashlib.sha256(b).hexdigest();pins={}
def read(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();b=p.read_bytes();assert len(b)==s.st_size;pins[str(p)]={'bytes':len(b),'sha256':H(b)};return b
def load(p):return json.loads(read(p))
def check(p,r):b=read(p);assert len(b)==r['bytes'] and H(b)==r['sha256'];return b
def ref(p):read(p);return dict(path=str(p),**pins[str(p)])
pr=load(D/'preregistration.json');schema=load(D/'go-schema.json');root=pr['remoteRoot'];build=pr['buildRoot'];sp=load(D/'source-pins.json')
assert H(read(C/'source/source-pins.json'))==H(read(D/'source-pins.json'))=='15e8e6f7a1d9ca3338ee34a66bf4ca737ba36adcbac965eb2965e1ee54c3f86c'
for n,r in sp.items():assert check(C/'source'/n,r)==check(D/n,r)
receipt=load(C/'collection-receipt.json');assert len(receipt['members'])==600
for m in receipt['members']:check(C/m['path'],m)
assert {str(p.relative_to(C)) for p in C.rglob('*') if p.is_file()}=={m['path'] for m in receipt['members']}|{'collection-receipt.json'}
assert receipt['presentSubtrees']==['source','control','functional285'] and receipt['absentSubtrees']==[] and receipt['functionalTerminalPresent']is True
local=load(G/'root-go.json');remote=load(C/'control/root-go.json');localsha=H(read(G/'root-go.json'));remotesha=H(read(C/'control/root-go.json'))
assert localsha=='2c1bcd86f8ec93f923f2189f0698810304d2fd8aefdf656958d6a6ed168dca7e' and remote['originalLocalGOSHA256']==localsha
assert set(local)==set(schema['exactLocalFields']) and set(remote)==set(schema['exactLocalFields'])|{'originalLocalGOSHA256'}
for k,v in {**schema['fixedFields'],**schema['fixedAuthorization']}.items():assert type(local[k])is type(v) and type(remote[k])is type(v) and local[k]==remote[k]==v
for k,n in schema['sourceSHAFields'].items():assert local[k]==remote[k]==H(read(D/n))
assert len(local['sourceReviews'])==2 and len({r['path'] for r in local['sourceReviews']})==2 and len({r['sha256'] for r in local['sourceReviews']})==2
for i,r in enumerate(local['sourceReviews']):
 b=check(r['path'],r);q=remote['sourceReviews'][i];assert q['path']==root+f'/control/review{i}.json';assert check(C/f'control/review{i}.json',q)==b;review=json.loads(b);assert review['status']==schema['sourceReviews']['status']
 for k in schema['sourceReviews']['requiredBindings']:assert review[k]==local[k]
launch=D/'launch-outputs';attempts=load(launch/'children/attempts.json');assert len(attempts)==1;row=attempts[0]
assert row['state']=='terminal' and row['returncode']==0 and row['exception']is None and row['cleanupException']is None
assert check(row['stdout']['path'],row['stdout'])==b'LC_FRESH_CONSUMER_FUNCTIONAL285_REMOTE_TERMINAL\n' and check(row['stderr']['path'],row['stderr'])==b''
assert row['argv'][:8]==['/usr/bin/ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1',pr['destination']] and row['timeoutSeconds']==9420
assert load(launch/'terminal.json')==dict(children=1,allClosed=True,failure=False)
lr=load(launch/'report.json');assert lr['remoteGOSHA256']==remotesha and lr['originalLocalGOSHA256']==localsha and lr['launchChildren']==1 and lr['cumulativeLaunchChildren']==2 and lr['functionalAccepted']is False
assert read(launch/'derived-remote-go.json')==read(C/'control/root-go.json')
F=C/'functional285';report=load(F/'report.json');terminal=load(F/'terminal.json');assert terminal==dict(children=285,allClosed=True,failure=False,noRetry=True)
assert report['status']=='PASS_FRESH_CONSUMER_ORIGINAL19_FUNCTIONAL285_V2_ONLY' and report['calls']==285 and report['completedTriples']==95 and report['remoteGOSHA256']==remotesha and report['sourcePinsSHA256']==local['sourcePinsSHA256']
for k,v in dict(priorFailedLaunches=1,priorNativeChildren=0,cumulativeNativeChildren=285,maximumCumulativeNativeChildren=285,cumulativeLaunchChildren=2,compilerCalls=0,C2skip=False,timingQualified=False,quietQualified=False,registerCanaryQualified=False,SDKWholeTreeHashQualified=False,noRetry=True).items():assert type(report[k])is type(v) and report[k]==v
assert not (F/'failure.json').exists()
env=dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin',LANG='C',LC_ALL='C',TZ='UTC',HOME='/Users/zebulun',TMPDIR=root+'/functional285/tmp');assert load(F/'effective-environment.json')==dict(environment=env,allInheritedVariablesRemoved=True)
fields={'format','calls','warmupCalls','elapsedNanoseconds','result','maxRssBytes','fuelPerCall','contextFuelBefore','contextFuelAfter','contextFuelConsumed','nativeArtifactAbi','artifactKind','nativeArenaStatus','nativeArenas'};caps=dict(pairs=2097152,stringPoolBytes=65536,vectors=4096,vectorItems=65536)
def unique(pairs):
 d={}
 for k,v in pairs:assert k not in d;d[k]=v
 return d
def telemetry(b,n,arm):
 assert b.endswith(b'\n') and b.count(b'\n')==1;q=json.loads(b,object_pairs_hook=unique);assert type(q)is dict and set(q)==fields and q['format']=='kotoba.runtime-sample/v1'
 for k in ['calls','warmupCalls','elapsedNanoseconds','result','maxRssBytes','fuelPerCall','contextFuelBefore','contextFuelAfter','contextFuelConsumed']:assert type(q[k])is int and 0<=q[k]<2**64
 assert q['calls']==1 and q['warmupCalls']==0 and q['result']==(0 if n==0 else 1) and q['fuelPerCall']==q['contextFuelBefore']==16777216 and q['nativeArtifactAbi']=='kotoba.native-artifact-i64x8-to-i64-indirect/v1'
 if arm=='C':assert q['artifactKind']=='dylib' and q['contextFuelAfter']==16777216 and q['contextFuelConsumed']==0 and q['nativeArenaStatus']=='unavailable-C' and q['nativeArenas']is None
 else:
  assert q['artifactKind']=='raw' and 0<q['contextFuelAfter']<=16777216 and q['contextFuelConsumed']==16777216-q['contextFuelAfter'] and q['nativeArenaStatus']=='available' and type(q['nativeArenas'])is dict and set(q['nativeArenas'])==set(caps)
  for k,cap in caps.items():
   a=q['nativeArenas'][k];assert type(a)is dict and set(a)=={'capacity','used'} and type(a['capacity'])is int and type(a['used'])is int and a['capacity']==cap and 0<=a['used']<=cap
 return {k:v for k,v in q.items() if k not in ['elapsedNanoseconds','maxRssBytes']}
rows=load(F/'children/attempts.json');assert len(rows)==285;computed=[];baselines=[];index=0
for c in pr['cases']:
 assert c['profiles']==[0,1,2,17,c['n']]
 for n in c['profiles']:
  pair={};rawrefs={}
  for arm in ['OFF','LC','C']:
   r=rows[index];index+=1;kind='dylib' if arm=='C' else 'raw';entry=c['CSymbol'] if arm=='C' else str(c[arm]['offset']);artifact=c['C'] if arm=='C' else c[arm]
   assert r['index']==index and r['label']==c['workload']+'-'+arm+'-n'+str(n) and r['argv']==[c['runner']['path'],kind,artifact['path'],entry,'aarch64',str(n),'1','0','16777216']
   assert r['environment']==env and r['timeoutSeconds']==30 and r['state']=='terminal' and r['returncode']==0 and r['exception']is None and r['cleanupException']is None
   for stream in ['stdout','stderr']:
    name=f'functional285/children/{index}.{stream}';assert r[stream+'Path']==r[stream]['path']==root+'/'+name;data=check(C/name,r[stream]);assert len(data)<=16777216
    if stream=='stderr':assert data==b''
    else:stdout=data;rawrefs[arm]=ref(C/name)
   pair[arm]=telemetry(stdout,n,arm)
  assert pair['OFF']==pair['LC'];computed.append(dict(workload=c['workload'],n=n,arms=pair))
  if n==c['n']:baselines.append(dict(workload=c['workload'],n=n,semantics=pair,stdout=rawrefs,runner=c['runner'],C=c['C'],header=c['header'],OFF=c['OFF'],LC=c['LC']))
assert len(computed)==95 and computed==report['comparisons']==load(F/'comparisons.json')
old=load(V1/'preregistration.json');assert old['cases']==pr['cases']
accepted=load(D/'build52-independent-report.json');assert accepted['images']==[c['buildAnchors'] for c in pr['cases']]
orig=load(W/'vector-leaf-straight-read-cache-current19-build52-source-v2-lc-remote/preregistration.json');critical=0
for c,o in zip(pr['cases'],orig['entries']):
 assert c['source']==o['source'] and c['profiles']==o['profiles'] and c['symbol']==o['symbol'] and c['CSymbol']==o['CSymbol'];check(c['source']['path'],c['source']);critical+=1
 for arm in ['OFF','LC']:
  assert {k:v for k,v in c[arm].items() if k!='path'}=={k:v for k,v in o[arm].items() if k!='path'};raw=check(o[arm]['path'],o[arm]);container=check(o[arm+'Container']['path'],o[arm+'Container']);head,payload=container.split(b'\n\n',1);lines=head.decode('ascii').splitlines();assert payload==raw and lines[0]==f'KSEED1 {len(payload)} {len(lines)-1}' and f"{c['symbol']} {c[arm]['offset']} 1" in lines[1:];critical+=2
 for arm in ['C','runner','header']:
  assert c[arm]==c['buildAnchors'][arm];check(B/'collected'/c[arm]['path'].removeprefix(build+'/'),c[arm]);critical+=1
bank=load(D/'remote-input-pins.json');extra=[ref(C/'control/root-go.json')]+[ref(C/f'control/review{i}.json') for i in range(2)]+[dict(path=str(C/'source'/n),**r) for n,r in sp.items()]+[ref(C/'source/source-pins.json')]
assert report['closure']==dict(files=len(bank)+len(extra),bytes=sum(r['bytes'] for r in bank.values())+sum(r['bytes'] for r in extra))
assert report['closure']['files']<=4096 and report['closure']['bytes']<=448*1024**2
for p in ['collection-outputs/report.json','collection-outputs/attempt.json']:load(G/p)
prior=load(D/'prior-failure-independent-report.json');assert prior['nativeFunctionalChildren']==0 and prior['launchChildren']==1 and prior['functionalQualified']is False
(R/'timing-nmax-baselines.json').write_text(json.dumps(dict(status='FUNCTIONAL_ONLY_NMAX_RAW_SEMANTIC_BASELINES_FOR_TIMING_SOURCE',sourcePinsSHA256=local['sourcePinsSHA256'],cases=baselines,timingQualified=False),indent=2)+'\n')
(R/'input-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
verdict=dict(status='PASS_ACTUAL_FRESH_CONSUMER_FUNCTIONAL285_V2_INDEPENDENT_SAVED_RAW_ONLY',independent=True,priorOperationalAuthorship=False,priorParticipation=['V1 and V2 independent SOURCE review','Read-only collector source author; root executed collection','V1 independent saved failure audit'],sourcePinsSHA256=local['sourcePinsSHA256'],driverSHA256=local['driverSHA256'],launchSHA256=local['launchSHA256'],preregistrationSHA256=local['preregistrationSHA256'],inputPinsSHA256=local['inputPinsSHA256'],remoteInputPinsSHA256=local['remoteInputPinsSHA256'],localGOSHA256=localsha,remoteGOSHA256=remotesha,buildAcceptanceSHA256=local['buildAcceptanceSHA256'],buildIndependentReportSHA256=local['buildIndependentReportSHA256'],launchChildren=1,launchAllClosed=True,launchSSHReturncode=0,launchSealExact=True,nativeAndCChildren=285,allClosed=True,returncodeZero=285,exceptions=0,cleanupExceptions=0,rawPairsVerified=285,stdoutRawVerified=285,emptyStderrVerified=285,originalWorkloads=19,unchangedProfiles=95,completedTriples=95,nativeOFFLCPairs=95,nativeSemanticFuelFourTerminalArenaParityExact=True,semanticBooleanOracleExact=True,strict14FieldJSON=True,noJSONBooleanIntegers=True,noDuplicateJSONKeys=True,CNoFuelChargeAndUnavailableNullArenas=True,wholeAcceptedRuntimeCriticalFilesVerified=critical,priorFailedLaunches=1,priorNativeChildren=0,cumulativeNativeAndCChildren=285,cumulativeLaunchChildren=2,noRetry=True,compilerCalls=0,reviewerSSH=0,reviewerNative=0,reviewerDriverExecutions=0,functionalQualified=True,timingQualified=False,quietQualified=False,registerCanaryQualified=False,runtimeTrapBoundaryQualified=False,SDKWholeTreeHashQualified=False,closure=report['closure'],whole428MiBClosureRehashPerformed=False,inputPins=ref(R/'input-pins.json'),timingNmaxBaselines=ref(R/'timing-nmax-baselines.json'),rawEvidenceScope='Every saved stdout/stderr and complete ledger/environment/comparison/terminal, exact SOURCE/GO/review bindings and original19 runtime source/native/container/export/C/header/runner bytes independently verified.',limits=['Functional285 only; no timing, quiet, canary, trap boundary, SDK whole-tree or clone-theorem qualification.','Accepted52 proof and exact pinned runtime artifacts anchor remote installed closure; no repeated whole428MiB bank rehash by reviewer.'],freeze='ACTUAL_V2_SAVED_RAW285_ACCEPTED_WITH_V1_FAILED1_NATIVE0_PRESERVED')
(R/'report.json').write_text(json.dumps(verdict,indent=2)+'\n');print(json.dumps(ref(R/'report.json')));print(json.dumps(dict(nmax=str(R/'timing-nmax-baselines.json'),inputPins=str(R/'input-pins.json'),verifiedFiles=len(pins),criticalFiles=critical)))
