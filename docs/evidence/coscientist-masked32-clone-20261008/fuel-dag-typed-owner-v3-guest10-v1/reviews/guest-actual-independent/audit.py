"""Independent finite saved-raw audit only. Never imports or executes author validation/driver."""
from pathlib import Path
import hashlib,json,re,stat,datetime
W=Path('/Users/junkawasaki/github/workspaces/codex');D=Path(__file__).resolve().parent;S=W/'vector-fuel-scalar-dag-emitted18-source-v1-width';O=S/'guest-outputs';G=W/'vector-fuel-scalar-dag-emitted-guest10-go-v1-root/root-go.json'
cache={};hashes={};failures=[];checks={}
def read(p):
 p=str(p)
 if p not in cache:
  q=Path(p);a=q.lstat();assert stat.S_ISREG(a.st_mode) and not q.is_symlink();b=q.read_bytes();z=q.lstat();assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns)
  cache[p]=b;hashes[p]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
 return cache[p]
def load(p):return json.loads(read(p))
def ck(n,v):
 checks[n]=bool(v)
 if not v:failures.append(n)
def pin(p,z):read(p);return hashes[str(p)]=={k:z[k] for k in ['bytes','sha256']}
g=load(G);pr=load(S/'guest-preregistration.json');report=load(O/'report.json');term=load(O/'terminal.json');attempts=load(O/'attempts.json');comparisons=load(O/'comparisons.json');rip=load(g['runtimeInputPins']['path'])
ck('root-go-exact',hashes[str(G)]['sha256']=='f3c8996099ab1ac4cb177e819566e63eed995a19859d0fa3e77df610b13b851c' and g['status']=='ROOT_AUTHORIZED_FUEL_DAG_EMITTED_GUEST10_ONLY' and g['maximumLoaderCalls']==10 and g['noRetry'] is True and g['workloadGuestAuthorized'] is True and g['generatedCompilerExecutionAuthorized'] is False and g['timingAuthorized'] is False and g['outputRoot']==str(O))
ck('runtime-registry',pin(g['runtimeInputPins']['path'],g['runtimeInputPins']))
for p,z in rip.items():
 try:ck('pin:'+p,pin(p,z))
 except Exception as ex:failures.append('pin:'+p+':'+str(ex))
ck('exact-runtime-closure',len(rip)==1998 and sum(z['bytes'] for z in rip.values())==385691006)
base=load(S/'input-pins.json');ck('full-base-in-runtime',all(rip.get(p)==z for p,z in base.items()))
for n,k in [('guest10.py','guestDriverSHA256'),('source-pins.json','driverSourcePinsSHA256'),('guest-preregistration.json','guestPreregistrationSHA256'),('input-pins.json','inputPinsSHA256')]:read(S/n);ck('source:'+n,hashes[str(S/n)]['sha256']==g[k])
for n,z in load(S/'source-pins.json').items():ck('driver-pin:'+n,pin(S/n,z))
E=Path(pr['sourceDirectory']);read(E/'source-pins.json');ck('emitter-registry',hashes[str(E/'source-pins.json')]['sha256']==g['sourcePinsSHA256']==pr['sourcePinsSHA256'])
for n,z in load(E/'source-pins.json').items():ck('emitter-pin:'+n,pin(E/n,z))
for role,statuskey in [('sourceReviews','sourceReviewStatus'),('driverReviews','driverReviewStatus')]:
 ck('two-reviews:'+role,len(g[role])==2 and len({z['path'] for z in g[role]})==2)
 for z in g[role]:
  q=load(z['path']);ck('review:'+role+z['path'],pin(z['path'],z) and q['status']==pr[statuskey] and all(q[k]==g[k] for k in ['driverSourcePinsSHA256','guestDriverSHA256','guestPreregistrationSHA256']))
for role,key in [('componentAcceptance','componentAcceptanceStatus'),('machineAcceptance','machineAcceptanceStatus')]:
 z=g[role];q=load(z['path']);ck(role,pin(z['path'],z) and rip.get(z['path'])=={k:z[k] for k in ['bytes','sha256']} and q['status']==pr[key])
machine=load(g['machineAcceptance']['path']);images=load(S/'build-outputs/images.json')
ck('machine-prerequisite',machine['images']==images and machine['actualBuildCalls']==8 and machine['positiveQualifiedSiteCount']==1 and machine['negativeWholeIdentity'] is True and machine['fuelTransactionProof']==dict(benchEntryUnits=1,outerUnits=1,additionalDynamicCharges=0,privateContextX7Preserved=True,fuelInteriorIngress=False,directBenchABI=True))
ck('build8-closed',load(S/'build-outputs/terminal.json')==dict(loaderCalls=8,allChildrenClosed=True,failure=False))
component=load(g['componentAcceptance']['path']);ck('component18-prerequisite',component['actualLoaderCalls']==18 and component['savedCase0V3Accepted'] is True and component['remainingCases']==list(range(1,16)) and component['sourceBoundStateReceiptsAccepted'] is True)
ck('exact-qualified-loader',rip[pr['loader']]['sha256']=='e14c2919ac5afd0960d9e6a4ac30ed90da26047c99842ef4d66428322764a77f')
ck('terminal10',term==dict(loaderCalls=10,allChildrenClosed=True,failure=False) and len(attempts)==10)
ck('report-boundary',report['status']=='COMPLETE_FINITE_FUEL_DAG_EMITTED10_RESULT_FUEL_TRAP_ARENA_ONLY' and report['loaderCalls']==10 and report['priorBuildCalls']==8 and report['cumulativeLoaderCalls']==18 and report['rootGOSHA256']==hashes[str(G)]['sha256'] and report['sourcePinsSHA256']==g['sourcePinsSHA256'] and report['performanceQualified'] is False and report['full19Qualified'] is False)
fields=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes'];parsed=[];rawpins={}
cases=[(f,b,n,a) for f,bs,n in [('positive',[1,2,3],7),('negative',[2,3],-1)] for b in bs for a in ['OFF','ON']]
for i,(f,b,n,a) in enumerate(cases):
 try:
  t=attempts[i];label=f'{f}-{b}-{a}';image=next(z for z in images if z['fixture']==f and z['arm']==a);trap=f=='positive' and b==1;value=120 if trap else (16 if f=='positive' else 4294967289);remaining=0 if trap else b-2
  assert t['index']==i+1 and t['label']==label and t['argv']==[pr['loader'],image['native']['path'],str(image['offset']),'1','aarch64','-',str(n)]
  env=dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin',HOME='/Users/junkawasaki',TMPDIR=str(O),LANG='C',LC_ALL='C',TZ='UTC',KEXE_STRING_POOL='1048576',KEXE_VECTORS='65536',KEXE_PAIRS='4096',KEXE_VECTOR_ITEMS='65536',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800',KEXE_FUEL=str(b),KEXE_ARENA_USE='1',KEXE_STRUCTURED_REPORT='1')
  assert t['effectiveEnvironment']==env and t['timeoutSeconds']==1810 and t['state']=='terminal' and t['spawned'] is True and t['reaped'] is True and isinstance(t['pid'],int) and t['pid']>0 and t['returncode']==(120 if trap else 0) and t['error'] is None and t['terminationReason'] is None and t['cleanupExceptions']==[]
  assert image['native']['path'] in rip and pin(image['native']['path'],image['native']) and pin(image['container']['path'],image['container'])
  container=read(image['container']['path']);native=read(image['native']['path']);head,payload=container.split(b'\n\n',1);assert payload==native and head==f'KSEED1 {len(native)} 1\nbench {image["offset"]} 1'.encode()
  outp=O/(label+'.stdout');errp=O/(label+'.stderr');out=read(outp);err=read(errp);assert hashes[str(outp)]==t['stdout'] and hashes[str(errp)]==t['stderr'];rawpins[str(outp)]=hashes[str(outp)];rawpins[str(errp)]=hashes[str(errp)]
  # Exact independent grammar and complete line equality reject trailing/unparsed output.
  expected=(f'{{:status :{"trap" if trap else "ok"} :{"exit" if trap else "result"} {value} :fuel {{:initial {b} :remaining {remaining}}} :heap {{:capacity 4096 :used 0}} :string-pool {{:capacity 1048576 :used 0}} :vectors {{:capacity 65536 :used 0}} :vector-items {{:capacity 65536 :used 0}}}}\n').encode();assert out==expected
  signal=b'KEXE_TRAP {:kind :signal :signal :SIGTRAP}\nKEXE_TRAP {:kind :budget :reason :budget/fuel}\n';counter=('KEXE_ARENA_USE {'+' '.join(':'+x+' 0' for x in fields)+'}\n').encode();assert err==(signal if trap else b'')+counter
  parsed.append(dict(status='trap' if trap else 'ok',resultOrExit=value,initialFuel=b,remainingFuel=remaining,arenas=[4096,0,1048576,0,65536,0,65536,0],nonresumingFuelTrap=trap,arenaCounters=[0]*17));ck('actual-raw:'+label,True)
 except Exception as ex:ck('actual-raw:'+f'{f}-{b}-{a}',False);failures.append(repr(ex))
recomputed=[]
if len(parsed)==10:
 for j in range(5):
  f,b,n,_=cases[2*j];ck('parity:'+str(j),parsed[2*j]==parsed[2*j+1]);recomputed.append(dict(fixture=f,initialFuel=b,input=n,OFF=parsed[2*j],ON=parsed[2*j+1]))
ck('all-saved-comparisons',len(recomputed)==5 and recomputed==comparisons==report['comparisons'])
ck('guest-output-inventory',sorted(p.name for p in O.iterdir())==sorted(['attempts.json','comparisons.json','report.json','terminal.json']+[f'{f}-{b}-{a}.{ext}' for f,b,n,a in cases for ext in ['stdout','stderr']]))
receipt=dict(status='PASS' if not failures else 'HOLD',scope='Finite independent saved raw Guest10 result/fuel/nonresuming SIGTRAP/four arena parity audit only.',participation='Authored prior typed-owner receipt closeout; did not author or execute Guest10 source, driver, validator or native artifacts. Reviewed bytes independently without executing guest-check.py or guest10.py.',createdUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),executionBoundary='Parent root communicated CLOSED0 session24332; independent evidence is saved terminal and ten spawned/reaped attempt records, not an independent OS trace.',counts=dict(runtimeInputFiles=len(rip),runtimeInputLogicalBytes=sum(z['bytes'] for z in rip.values()),guestCalls=10,pairs=5,trapCalls=2,successfulCalls=8,priorBuildCalls=8,cumulativeBuildAndGuestCalls=18),checks={k:v for k,v in checks.items() if not k.startswith('pin:')},pinMismatches=[x for x in failures if x.startswith('pin:')],failures=failures,exactHashes={str(p):hashes[str(p)] for p in [G,Path(g['runtimeInputPins']['path']),S/'guest10.py',S/'guest-check.py',S/'guest-preregistration.json',S/'source-pins.json',O/'attempts.json',O/'comparisons.json',O/'report.json',O/'terminal.json']},observed=recomputed,performanceQualified=False,full19Qualified=False,reviewerNativeCompilerSSHDriverCalls=0,reviewerAuthorValidatorExecutions=0)
(D/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');(D/'input-pins.json').write_text(json.dumps(dict(sorted({**{p:hashes[p] for p in rip},**rawpins,**receipt['exactHashes']}.items())),indent=2)+'\n')
print(json.dumps(dict(status=receipt['status'],counts=receipt['counts'],failures=failures,exactHashes=receipt['exactHashes']),indent=2))
