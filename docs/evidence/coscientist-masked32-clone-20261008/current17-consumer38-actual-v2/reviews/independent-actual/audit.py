"""Saved-only consumer38 audit, independent of execution; driver authorship disclosed."""
from pathlib import Path,PurePosixPath
import json,hashlib,base64,shlex,re,posixpath,importlib.util
from macho import macho
W=Path('/Users/junkawasaki/github/workspaces/codex');A=Path(__file__).resolve().parent
K=W/'current17-consumer-build38-v2-collection2-root-20261009';D=K/'collected';O=D/'consumer-build-outputs';S=W/'current17-consumer-build38-source-v2-20261009-dense';C=W/'tc-hft-current17-timing-consumer-source-v2-20261009-crc';P=W/'current19-C-build38-v3-actual-review-independent-20261009';PC=W/'current19-C-build38-v3-collection-root-20261009/collected'
def h(b):return hashlib.sha256(b).hexdigest()
def unique(pairs):
 d={}
 for k,v in pairs:assert k not in d;d[k]=v
 return d
def load(p):return json.loads(Path(p).read_bytes(),object_pairs_hook=unique)
def rec(p):
 p=Path(p);a=p.lstat();assert p.is_file()and not p.is_symlink();b=p.read_bytes();z=p.lstat();assert(a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns);return dict(path=str(p),bytes=len(b),sha256=h(b))
def check(p,r):
 q=rec(p);assert(q['bytes'],q['sha256'])==(r['bytes'],r['sha256']),(str(p),'pin');return Path(p).read_bytes()
sp=load(S/'source-pins.json');ip=load(S/'input-pins.json');pr=load(S/'build-preregistration.json');rs=load(S/'recipes.json')['commands'];packet=load(S/'packet.json')['entries'];assert len(sp)==15 and len(ip)==108 and sum(v['bytes']for v in ip.values())==2931240
for n,r in sp.items():check(S/n,r)
for row in packet:
 w=row['workload'];pairs=[('sources/kotoba/'+w+'.kotoba',row['source'])]+[(f'inputs/{w}/{arm}.bin',row[arm]['native'])for arm in ['OFF','ON']]+[(f'inputs/{w}/{arm}.kseed',row[arm]['container'])for arm in ['OFF','ON']]
 for n,r in pairs:assert ip[n]=={k:r[k]for k in('bytes','sha256')};check(r['path'],r)
for n,r in load(C/'source-pins.json').items():assert ip['source/consumer/'+n]==r;check(C/n,r)
g=load(D/'root-current17-consumer-GO/root-go.json');R=g['taskRoot'];host=g['hostBinding'];q=load(O/'report.json')
def mapped(p):
 rel=PurePosixPath(p).relative_to(R);assert'..'not in rel.parts;return D/str(rel)
def remotecheck(r):return check(mapped(r['path']),r)
assert g['status']==pr['rootGOStatus']and g['maximumChildCalls']==38 and g['noRetry']is True and all(g[k]is False for k in ['guestAuthorized','consumerAuthorized','timingAuthorized','C2'])
for key,name in [('sourcePinsSHA256','source-pins.json'),('inputPinsSHA256','input-pins.json'),('preregistrationSHA256','build-preregistration.json'),('driverSHA256','build.py')]:assert g[key]==h((S/name).read_bytes())
assert q['status']==pr['completionStatus']and q['closedCompilerCalls']==38 and q['consumerBuildCalls']==19 and q['guestCalls']==0 and q['hostBinding']==host;assert all(q[k]==g[k]for k in ['sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256']);remotecheck(q['GO'])
assert len(g['sourceReviews'])==2 and len({x['sha256']for x in g['sourceReviews']})==2
for r in g['sourceReviews']:
 v=json.loads(remotecheck(r));assert v['status']==pr['sourceReviewStatus']and all(v[k]==g[k]for k in ['sourcePinsSHA256','preregistrationSHA256','driverSHA256'])
a=g['procLibraryAlias'];assert a['alias']==host['sdk']+'/usr/lib/libproc.tbd'and a['canonicalTargetPin']==dict(path=host['sdk']+'/usr/lib/libSystem.B.tbd',bytes=337542,sha256='607d9993892c95703a0909ff06f5843058ff1ec30b08337f42ab056d9bf325ea')and a['canonicalTargetPin']in host['libraryPins'];assert g['expectedDynamicLoadNames']==['/usr/lib/libSystem.B.dylib']
b=(K/'actual.stdout').read_bytes();summary=load(K/'collection-summary.json');assert h(b)==summary['payloadSHA256'];collection=json.loads(b);assert collection['status']==summary['status']and collection['root']==R
names=set();total=0
for f in collection['files']:
 n=PurePosixPath(f['path']);assert not n.is_absolute()and'..'not in n.parts and str(n)not in names;names.add(str(n));raw=base64.b64decode(f['base64'],validate=True);assert len(raw)==f['bytes']and h(raw)==f['sha256'];check(D/str(n),f);total+=len(raw)
assert len(names)==217 and total==13636749==summary['logicalBytes']and names=={str(p.relative_to(D))for p in D.rglob('*')if p.is_file()}
for k in ['attempts','terminal','dynamicPins','generatedPins']:remotecheck(q[k])
rows=load(O/'attempts.json');terminal=load(O/'terminal.json');dyn=load(O/'dynamic-pins.json');gen=load(O/'generated-pins.json');assert len(rows)==38 and len(gen)==38;assert terminal['directChildrenClosed']==38 and terminal['allDirectChildrenReaped']is True and terminal['failure']is False and terminal['noRetry']is True
cp={};cpdesc={};expectedgen={}
spec=importlib.util.spec_from_file_location('pure_header',S/'header.py');hm=importlib.util.module_from_spec(spec);spec.loader.exec_module(hm)
for d in g['C19Proofs']:
 raw=remotecheck(d);v=json.loads(raw);w=v['workload'];assert w not in cp and v==load(P/'per-work'/f'{w}.json');assert v['status']=='PASS_INDEPENDENT_FRESH_CURRENT19_C_BUILD_SOURCE_IDENTITY_ONLY'and v['bridgeABI']=='I64_8ARGS';cp[w]=v;cpdesc[w]=d
 row=next(r for r in packet if r['workload']==w);assert v['symbol']==row['symbol']and v['artifact']['path']==R+f'/C-build-outputs/{w}/c.dylib'
 c=check(PC/f'C-build-outputs/{w}/c.dylib',v['artifact']);off=check(row['OFF']['native']['path'],row['OFF']['native']);on=check(row['ON']['native']['path'],row['ON']['native']);header=hm.header(row,off,on,c,v);hp=R+f'/build/{w}/timing-packet-generated.h';assert check(mapped(hp),gen[hp])==header;expectedgen[hp]=dict(bytes=len(header),sha256=h(header));expectedgen[R+f'/inputs/{w}/C.dylib']=dict(bytes=len(c),sha256=h(c))
assert set(cp)=={r['workload']for r in packet}and gen==expectedgen
union=set();warnings=0;env=pr['environment']|{'TMPDIR':R+'/consumer-build-outputs/tmp','SDKROOT':host['sdk']}
for i,row in enumerate(rows,1):
 recipe=rs[(i-1)%19];assert load(O/f'{i:02d}.closure.json')==row;phase='dependencies'if i<=19 else'build';a=[t.replace('$RESOLVED_CLANG',host['compiler']['path']).replace('$TASK_ROOT',R).replace('$FRESH_BUILD',R+'/consumer-build-outputs')for t in recipe['argvTemplate']]
 if i<=19:a=a[:-3];a.insert(4,'-M')
 assert row['index']==i and row['phase']==phase and row['workload']==recipe['workload']and row['argv']==a and row['state']=='terminal'and row['returncode']==0 and row['directWaitCount']==1 and row['reaped']is True and type(row['pid'])is int and row['pid']>0
 raw=remotecheck(row['stdout']);err=remotecheck(row['stderr']);assert len(raw)<=1048576 and len(err)<=1048576 and b'\0'not in err and'error:'not in err.decode('utf8');warnings+=bool(err)
 res=json.loads(remotecheck(row['resources']));assert res['index']==i and res['phase']==phase and res['argv']==a and res['environment']==env and res['GO']==q['GO']and res['regularFileCapBytes']==16777216 and res['noLimitEnlargement']is True
 ew=res['environmentWitness'];assert ew['execEnvironmentExact']is True and ew['suppliedKeyNames']==sorted(env)and ew['runtimeExtraKeyNames']in [[],['__CF_USER_TEXT_ENCODING']]and ew['missingKeyNames']==ew['changedExpectedKeyNames']==[]
 for name,cap in {'RLIMIT_CPU':[180,181],'RLIMIT_FSIZE':[16777216,16777216],'RLIMIT_CORE':[0,0]}.items():
  z=res['limits'][name];old=z['inherited'];hard=cap[1]if old[1]==-1 else min(old[1],cap[1]);soft=min(cap[0]if old[0]==-1 else min(old[0],cap[0]),hard);assert z['actual']==[soft,hard]
 if i<=19:
  text=raw.decode('ascii').replace('\\\n',' ');lines=text.splitlines();assert 0<len(lines)<=3;deps=set()
  for line in lines:
   assert line.count(':')==1;target,body=line.split(':',1);assert target.endswith('.o')and'/'not in target
   for n in shlex.split(body):
    n=posixpath.normpath(n);assert PurePosixPath(n).is_absolute()and n in dyn
    if n.startswith(R+'/'):assert n[len(R)+1:]in ip or n in gen
    else:assert n.startswith(host['sdk']+'/')or n.startswith(host['resourceDirectory']+'/')
    deps.add(n)
  assert sorted(deps)==row['dependencies']and R+'/source/consumer/timing-loader.c'in deps and R+f'/build/{recipe["workload"]}/timing-packet-generated.h'in deps;union|=deps
 else:assert raw==b''
assert union==set(dyn)and len(dyn)<=4096 and sum(v['bytes']for v in dyn.values())<=67108864
for p,v in dyn.items():
 assert 0<v['bytes']<=8388608 and re.fullmatch('[0-9a-f]{64}',v['sha256'])
 if p.startswith(R+'/'):assert v==(ip.get(p[len(R)+1:])or gen[p])
proofs=[]
for j,recipe in enumerate(rs):
 a=q['artifacts'][j];w=recipe['workload'];assert a['workload']==w and a['symbol']==recipe['cSymbol']and a['consumerABI']=='ARM_n_calls_warmup_5ARGV_V1'and a['sourcePins']==ip and a['compileArgv']==rows[j+19]['argv']and a['dependencyCallIndex']==j+1 and a['buildCallIndex']==j+20
 assert a['artifact']['path']==R+f'/consumer-build-outputs/{w}/consumer';raw=remotecheck(a['artifact']);symbols=[macho(raw,'main')];assert b'static int timing_loader_main(int argc, char **argv)'in(C/'timing-loader.c').read_bytes();row=next(r for r in packet if r['workload']==w);assert all(Path(row[arm]['native']['path']).read_bytes()in raw for arm in ['OFF','ON']);assert (PC/f'C-build-outputs/{w}/c.dylib').read_bytes()in raw;assert a['dynamicDependencyPins']=={p:dyn[p]for p in rows[j]['dependencies']};hp=R+f'/build/{w}/timing-packet-generated.h'
 proofs.append(dict(status='PASS_INDEPENDENT_FRESH_CURRENT17_CONSUMER_BUILD_SOURCE_IDENTITY_ONLY',workload=w,symbol=a['symbol'],consumerABI=a['consumerABI'],artifact=a['artifact'],savedCopy=rec(mapped(a['artifact']['path'])),consumerSourcePinsSHA256='a0d2bed0535e7cf2e9fd6d277303ba99ff1664aff83466989a3c124626ff7699',consumerBuildSourcePinsSHA256=g['sourcePinsSHA256'],CProof=cpdesc[w],generatedHeader=dict(path=hp,**gen[hp]),compileArgv=a['compileArgv'],sourcePinsSHA256=g['sourcePinsSHA256'],inputPinsSHA256=g['inputPinsSHA256'],preregistrationSHA256=g['preregistrationSHA256'],GO=q['GO'],symbolDefinitions=symbols,dependencyCallIndex=j+1,buildCallIndex=j+20,guestExecutionQualified=False,resetQualified=False,bridgeExecutableQualified=False,performanceQualified=False))
assert not q['cleanBuildClaimed']and not q['performanceQualified']and not q['C2']and q['noRetry']is True
for n,r in sp.items():check(S/n,r)
(A/'verified-proofs.json').write_text(json.dumps(proofs,indent=2)+'\n');s=dict(verified=True,calls=38,artifacts=19,collectedFiles=len(names),collectedBytes=total,dynamicHeaders=len(dyn),diagnosticStreams=warnings,generatedHeadersReconstructed=19,CMaterializationsIndependentlyFetched=False,sourceDriverAuthorshipDisclosed=True)
(A/'verification-summary.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s))
