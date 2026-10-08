import ast,copy,hashlib,json,stat,sys,tarfile
from pathlib import Path
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'vector-leaf-straight-read-cache-fresh-consumer-functional285-source-v1';R=Path(__file__).resolve().parent;S=W/'vector-leaf-straight-read-cache-current19-build52-source-v2-lc-remote';G=W/'vector-leaf-straight-read-cache-current19-build52-go-v2-root'
H=lambda b:hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
def check(p,r):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size==r['bytes'];assert H(p.read_bytes())==r['sha256']
pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');sf=load(D/'source-freeze.json');ip=load(D/'input-pins.json');rp=load(D/'remote-input-pins.json');contract=load(D/'evidence-role-contract.json');schema=load(D/'go-schema.json')
expected={'sourcePinsSHA256':'120c90f7823f649fae7f6998c5daa314396d0da97998db88ebf7676d04a191d8','driverSHA256':'a89466d76b960d670cca5241faeeecee1a915d7a18d2c9c338f0d3a39ec24277','launchSHA256':'2114afad5e75f95afacc04f3d8c2b1eda801ef4126d21731f294c1966cf7f646','preregistrationSHA256':'76e25fbc9a7a40e9cf1249802953e84a7fcbe0cbdfbe3d2c02dfa6ee564cf274','inputPinsSHA256':'d82623084eb80b0837434bad674f8ac2408bdd9c66e6c4a0f53f744d6f544780','remoteInputPinsSHA256':'2615f68b19162255553fd46cb95b2c21bff0f097fe9dcff55e86ab8f25f89f48'}
for k,v in expected.items():assert H((D/schema['sourceSHAFields'][k]).read_bytes())==v
for n,r in sf.items():check(D/n,r)
for n,r in sp.items():assert sf[n]==r
for n in ['functional285.py','launch.py','ledger.py']:ast.parse((D/n).read_bytes())
assert (len(ip),sum(r['bytes'] for r in ip.values()))==(3896,427710991)
assert (len(rp),sum(r['bytes'] for r in rp.values()))==(3786,427083757)
for bank in [ip,rp]:
 for p,r in bank.items():assert str(Path(p))==p and Path(p).is_absolute() and set(r)=={'bytes','sha256'} and type(r['bytes'])is int and r['bytes']>=0 and len(r['sha256'])==64
 assert len(bank)+19<=4096 and sum(r['bytes'] for r in bank.values())+5156215<=448*1024**2
old=load(S/'preregistration.json');origins=load(S/'input-origins.json');assert all(ip[k]==v for k,v in origins.items())
manifest=load(G/'collected/package/manifest.json');assert len(manifest['members'])==3592
for m in manifest['members']:assert rp[pr['buildRoot']+'/'+m['path']]=={k:m[k] for k in ['bytes','sha256']}
archive=Path(contract['historicalArchiveTransport']['path']);assert archive.is_file() and archive.stat().st_size==121263001;assert contract['historicalArchiveTransport']['sha256']==contract['archiveSHA256']=='3b099c22196af6ba53fae99c3696284e405714abacefef6015d39edcc210077a'
for r in contract['archiveProofs']:check(r['path'],r)
with tarfile.open(archive) as t:ob=t.extractfile('package/origin-map.json').read()
assert H(ob)==contract['originMapWholeFile']['sha256'] and len(ob)==contract['originMapWholeFile']['bytes'];omap=json.loads(ob)
assert rp[pr['buildRoot']+'/package/origin-map.json']=={k:contract['originMapWholeFile'][k] for k in ['bytes','sha256']}
review=load(D/'build52-independent-report.json');assert review['images']==[c['buildAnchors'] for c in pr['cases']]
critical=0
assert len(pr['cases'])==19 and sum(len(c['profiles']) for c in pr['cases'])==95
for c,o in zip(pr['cases'],old['entries']):
 for k,v in o.items():
  if k not in ['OFF','LC','OFFContainer','LCContainer']:assert c[k]==v
 assert c['profiles']==[0,1,2,17,c['n']];check(c['source']['path'],c['source']);critical+=1
 for role in ['OFF','LC','OFFContainer','LCContainer']:
  a=c[role];b=o[role];assert type(omap[b['path']])is str and a==dict(b,path=pr['buildRoot']+'/'+omap[b['path']]);assert ip[b['path']]=={k:b[k] for k in ['bytes','sha256']};assert rp[a['path']]=={k:a[k] for k in ['bytes','sha256']};check(b['path'],b);critical+=1
 for arm in ['OFF','LC']:
  raw=Path(o[arm]['path']).read_bytes();head,payload=Path(o[arm+'Container']['path']).read_bytes().split(b'\n\n',1);lines=head.decode('ascii').splitlines();assert lines[0]==f'KSEED1 {len(payload)} {len(lines)-1}' and payload==raw and f"{c['symbol']} {c[arm]['offset']} 1" in lines[1:]
 for role in ['C','runner','header']:
  a=c[role];assert a==c['buildAnchors'][role];assert rp[a['path']]=={k:a[k] for k in ['bytes','sha256']};p=G/'collected'/a['path'].removeprefix(pr['buildRoot']+'/');check(p,a);assert ip[str(p)]=={k:a[k] for k in ['bytes','sha256']};critical+=1
check(pr['consumerSource']['path'],pr['consumerSource']);critical+=1
sys.dont_write_bytecode=True;sys.path.insert(0,str(D));from functional285 import sample,CAPS,GO_FIELDS
assert set(schema['exactLocalFields'])==GO_FIELDS and set(schema['sourceReviews']['requiredBindings'])==set(expected)
fixtures=load(D/'parser-control-input-pins.json');accepted=rejected=0
for p,r in fixtures.items():
 check(p,r);b=Path(p).read_bytes();q=json.loads(b);n=int(Path(p).stem.rsplit('-n',1)[1]);kind=q['artifactKind'];sample(b,b'',n,kind);accepted+=1;variants=[]
 for k in ['calls','result','contextFuelConsumed']:
  bad=copy.deepcopy(q);bad[k]=True;variants.append(bad)
 if kind=='raw':
  for k in CAPS:
   bad=copy.deepcopy(q);bad['nativeArenas'][k]['capacity']=True;variants.append(bad)
  bad=copy.deepcopy(q);bad['nativeArenaStatus']='unavailable-C';variants.append(bad)
 else:
  bad=copy.deepcopy(q);bad['contextFuelConsumed']=1;variants.append(bad)
  bad=copy.deepcopy(q);bad['nativeArenas']={};variants.append(bad)
 for bad in variants:
  try:sample((json.dumps(bad)+'\n').encode(),b'',n,kind)
  except (AssertionError,TypeError,ValueError):rejected+=1
  else:raise AssertionError('invalid sample accepted')
assert accepted==171
report=dict(status=pr['sourceReviewStatus'],**expected,independent=True,priorAuthorship=False,scope='FINITE_SOURCE_ONLY_REVIEW_OF_FROZEN_BYTES',freeze='EXACT_SOURCE_FREEZE_RETAINED_NO_MODIFICATION',findings=[],sourceFreezeFilesVerified=len(sf),sourceRegistryFilesVerified=len(sp),criticalOriginalRuntimeFilesVerified=critical,originalWorkloads=19,unchangedProfiles=95,prospectiveFunctionalChildren=285,localRole=dict(files=3896,bytes=427710991),installedRole=dict(files=3786,bytes=427083757),retainedOriginalLocalOrigins=len(origins),retainedInstalledManifestMembers=3592,prospectiveExtraWorstBytes=5156215,roleCaps=dict(files=4096,bytes=448*1024**2),archivePhysicalBytes=121263001,archiveQualification='RETAINED_PHYSICAL_ARCHIVE_SIZE_AND_ACCEPTED_SHA_PROOFS; NO_ARCHIVE_REHASH',originMapWholeBytesVerified=True,pureParserControls=dict(savedHistoricalSamples=accepted,rejectedAdditionalMutants=rejected),reviewedGuards=['exact six hashes, all SOURCE registry hashes, exact root GO fields and two distinct review paths/hashes','same accepted full19 source/profile/native OFF/latest G3 LC/container/export/offset/C/header/runner anchors','native exact strict JSON uint64 and boolean rejection; available four terminal arenas/fuel parity before C; C boolean scalar/nocharge/unavailable null arenas','full local-origin and installed-member metadata closure retained within prospective4096/448MiB role caps before hash/spawn','one bounded ordinary SSH without fallback/SCP/retry;8MiB stdin;131072 command; source/control hashes before import','285 child ceiling,30-second call wall cap,9300 cohort alarm;16MiB RLIMIT_FSIZE; new process group SIGKILL and30+30 bounded reap; first failure/raw retained'],operationalDriverExecutions=0,SSH=0,compiler=0,native=0,guest=0,timing=0,functionalQualified=False,timingQualified=False,registerCanaryQualified=False,rootGOIssued=False,limitations=['Source review does not establish future285 success or actual remote closure; separate root GO and independent saved raw/argv/reap/closure acceptance required.','Full3896 origin byte verification is author evidence; independent byte checks covered SOURCE freeze, proof refs,171 parser fixtures and critical original19 runtime subset.','Retained whole manifest/chunk membership is metadata verified; whole archive duplicate transport bytes are referenced by accepted SHA/proofs and not copied or rehashed per child.'])
(R/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status=report['status'],report=str(R/'report.json'),sha256=H((R/'report.json').read_bytes()),critical=critical,accepted=accepted,rejected=rejected)))
