from pathlib import Path,PurePosixPath
import json,hashlib,base64,struct,shlex,re,posixpath
W=Path('/Users/junkawasaki/github/workspaces/codex')
A=W/'current19-C-build38-v3-actual-review-independent-20261009'
K=W/'current19-C-build38-v3-collection-root-20261009'
D=K/'collected'; O=D/'C-build-outputs'; S=W/'current19-zebulun-C-build38-source-v3-20261009-dense'; P=W/'tc-hft-current19-packet-install-source-v3-20261009-crc'
def h(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
def rec(p):
 assert p.is_file() and not p.is_symlink();b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=h(b))
def check(p,r):
 q=rec(p); assert (q['bytes'],q['sha256'])==(r['bytes'],r['sha256']),(str(p),'hash');return p.read_bytes()
sp=load(S/'source-pins.json');ip=load(S/'input-pins.json');pr=load(S/'preregistration.json');rs=load(S/'recipes.json')['commands']
for name,v in {**sp,**ip}.items():check(S/name,v)
assert len(sp)==10 and len(ip)==53 and sum(x['bytes'] for x in ip.values())==844196
q=load(O/'report.json');g=load(D/'root-C-build-GO/root-go.json'); R=g['taskRoot']; host=g['hostBinding']
def mapped(p):
 p=PurePosixPath(p); rel=p.relative_to(R);assert '..' not in rel.parts;return D/str(rel)
def remotecheck(r):return check(mapped(r['path']),r)
assert g['status']==pr['rootGOStatus'] and g['maximumChildCalls']==38 and g['noRetry'] and not any(g[x] for x in ('guestAuthorized','consumerAuthorized','timingAuthorized','C2'))
for field,name in [('sourcePinsSHA256','source-pins.json'),('inputPinsSHA256','input-pins.json'),('preregistrationSHA256','preregistration.json'),('driverSHA256','run.py')]:assert g[field]==h((S/name).read_bytes())
assert q['status']==pr['completionStatus'] and q['closedCompilerCalls']==38 and q['CBuildCalls']==19 and q['guestCalls']==0
assert q['hostBinding']==host and all(q[x]==g[x] for x in ('sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256'))
remotecheck(q['GO']);assert len(g['sourceReviews'])==2 and len({v['sha256'] for v in g['sourceReviews']})==2
for r in g['sourceReviews']:
 v=json.loads(remotecheck(r));assert v['status']==pr['sourceReviewStatus'] and all(v[k]==g[k] for k in ('sourcePinsSHA256','driverSHA256','preregistrationSHA256'))
# Collector framing and every actual copied byte, without invoking the collector.
b=(K/'actual.stdout').read_bytes();summary=load(K/'collection-summary.json');assert len(b)==summary['rawBytes'] and h(b)==summary['rawSHA256'];c=json.loads(b)
assert c['status']=='READ_ONLY_CURRENT19_C_BUILD38_CLOSED_OUTPUT_COLLECTION' and c['root']==R
names=set(); total=0
for v in c['files']:
 p=PurePosixPath(v['path']); assert not p.is_absolute() and '..' not in p.parts and str(p) not in names;names.add(str(p));raw=base64.b64decode(v['base64'],validate=True);assert len(raw)==v['bytes'] and h(raw)==v['sha256'];check(D/str(p),v);total+=len(raw)
assert len(names)==178 and total==2125939==c['logicalBytes']==summary['logicalBytes'];assert names=={str(p.relative_to(D)) for p in D.rglob('*') if p.is_file()}
# Frozen packet declares exact source and owned C inputs installed remotely.
manifest=load(P/'manifest.json'); members=manifest['files'] if 'files' in manifest else manifest['members']; members={v['relativePath']:v for v in members}
for n,v in ip.items():assert (members[n]['bytes'],members[n]['sha256'])==(v['bytes'],v['sha256'])
for n,v in sp.items():assert (members['source/C-build/'+n]['bytes'],members['source/C-build/'+n]['sha256'])==(v['bytes'],v['sha256'])
assert load(P/'preregistration.json')['remoteRoot']==R
attempts=load(O/'attempts.json');assert len(attempts)==38; dyn=load(O/'dynamic-pins.json');assert len(dyn)==177
remotecheck(q['attempts']);remotecheck(q['terminal']);remotecheck(q['dynamicPins']);term=load(O/'terminal.json');assert term['directChildrenClosed']==38 and term['allDirectChildrenReaped'] and not term['failure'] and term['noRetry']
env={**pr['environment'],'TMPDIR':R+'/C-build-outputs/tmp','SDKROOT':host['sdk']}; union=set(); warnings=0
artifacts=q['artifacts']; assert len(artifacts)==19 and len({v['workload'] for v in artifacts})==19
for i in range(1,39):
 r=rs[(i-1)%19];row=load(O/f'{i:02}.closure.json');assert row==attempts[i-1];phase='dependencies' if i<=19 else 'build'
 a=[x.replace('$RESOLVED_CLANG',host['compiler']['path']).replace('$TASK_ROOT',R).replace('$FRESH_BUILD',R+'/C-build-outputs') for x in r['argvTemplate']]
 if i<=19:a=a[:-2];a.insert(4,'-M')
 assert row['index']==i and row['workload']==r['workload'] and row['phase']==phase and row['argv']==a
 assert row['state']=='terminal' and row['returncode']==0 and row['directWaitCount']==1 and row['reaped'] and row['pid']>0
 raw=remotecheck(row['stdout']);err=remotecheck(row['stderr']);assert len(raw)<=1048576 and len(err)<=1048576 and b'\0' not in err and 'error:' not in err.decode();warnings+=bool(err)
 v=json.loads(remotecheck(row['resources']));assert v['index']==i and v['phase']==phase and v['argv']==a and v['environment']==env and v['GO']==q['GO'] and v['noLimitEnlargement'] and v['regularFileCapBytes']==16777216
 ew=v['environmentWitness'];assert ew['suppliedKeyNames']==sorted(env) and ew['runtimeExtraKeyNames'] in ([],['__CF_USER_TEXT_ENCODING']) and ew['missingKeyNames']==[] and ew['changedExpectedKeyNames']==[] and ew['execEnvironmentExact']
 for k,lim in {'RLIMIT_CPU':[180,181],'RLIMIT_FSIZE':[16777216]*2,'RLIMIT_CORE':[0,0]}.items():
  d=v['limits'][k];assert d['actual']==[min(d['inherited'][j],lim[j]) for j in range(2)]
 if i<=19:
  text=raw.decode('ascii');assert '\0' not in text; lines=text.replace('\\\n',' ').splitlines();assert 1<=len(lines)<=3;deps=set()
  for line in lines:
   assert line.count(':')==1;target,body=line.split(':');assert target.strip().endswith('.o') and '/' not in target
   for name in shlex.split(body):
    name=posixpath.normpath(name);pp=PurePosixPath(name);assert pp.is_absolute() and '..' not in pp.parts
    if name.startswith(R+'/'):assert name[len(R)+1:] in ip
    else:assert name.startswith(host['sdk']+'/') or name.startswith(host['resourceDirectory']+'/');assert name in dyn;union.add(name)
    deps.add(name);union.add(name)
  assert sorted(deps)==row['dependencies'];assert R+f"/inputs/{r['workload']}/c-bridge.c" in deps
 else: assert raw==b''
assert all(dyn[R+'/'+n]==v for n,v in ip.items());assert union==set(dyn) and sum(v['bytes'] for v in dyn.values())<=67108864
for n,v in dyn.items():assert 0<v['bytes']<=8388608 and re.fullmatch('[0-9a-f]{64}',v['sha256'])
# Independent Mach-O load-command and symbol-definition decoder; no dylib loading.
def macho(b,symbol):
 assert len(b)<=16777216 and b[:4]==bytes.fromhex('cffaedfe');_,cpu,sub,typ,ncmd,cmdbytes,flags,res=struct.unpack_from('<8I',b);assert cpu==0x100000c and typ==6 and 1<=ncmd<=128 and cmdbytes<=65536
 pos=32; syms=None; sections=[]; libs=[]
 for _ in range(ncmd):
  cmd,size=struct.unpack_from('<II',b,pos);assert size>=8 and size%8==0 and pos+size<=32+cmdbytes
  assert cmd not in {0x18,0x80000018,0x1f,0x8000001f,0x20,0x23,0x80000023,0x8000001c,0x27,0x2d}
  if cmd==12:
   off=struct.unpack_from('<I',b,pos+8)[0];assert 24<=off<size;libs.append(b[pos+off:pos+size].split(b'\0')[0].decode())
  if cmd==2:assert syms is None;syms=struct.unpack_from('<4I',b,pos+8)
  if cmd==0x19:
   nsec=struct.unpack_from('<I',b,pos+64)[0];assert 72+80*nsec==size
   for j in range(nsec):
    off=pos+72+80*j;sect,seg,addr,sz,foff,al,roff,nrel,fl,r1,r2,r3=struct.unpack_from('<16s16sQQ8I',b,off);sections.append((sect.rstrip(b'\0').decode(),seg.rstrip(b'\0').decode(),addr,sz,foff,fl))
  pos+=size
 assert pos==32+cmdbytes and libs==['/usr/lib/libSystem.B.dylib'] and syms is not None
 so,ns,st,ss=syms;assert so+ns*16<=len(b) and st+ss<=len(b);found=[]
 for j in range(ns):
  ix,t,sect,desc,value=struct.unpack_from('<IBBHQ',b,so+j*16);assert ix<ss;name=b[st+ix:st+ss].split(b'\0')[0].decode()
  if name=='_'+symbol:
   assert t&0xe0==0 and t&0x0e==0x0e and t&1 and 1<=sect<=len(sections)
   sec=sections[sect-1];assert sec[1]=='__TEXT' and sec[0]=='__text' and sec[2]<=value<sec[2]+sec[3];found.append(dict(name=name,n_type=t,n_sect=sect,value=value,section=sec[0],segment=sec[1]))
 assert len(found)==1;return found[0]
proofs=[]
for j,r in enumerate(rs):
 a=artifacts[j];w=r['workload'];assert a['workload']==w and a['symbol']==r['cSymbol'] and a['bridgeABI']=='I64_8ARGS' and a['sourcePins']==ip and a['dependencyCallIndex']==j+1 and a['buildCallIndex']==j+20
 assert a['compileArgv']==attempts[j+19]['argv'] and a['artifact']['path']==R+f'/C-build-outputs/{w}/c.dylib'
 deps=attempts[j]['dependencies'];assert a['dynamicDependencyPins']=={n:dyn[n] for n in deps if n in dyn}
 raw=remotecheck(a['artifact']);sym=macho(raw,a['symbol']);bridge=(S/f'inputs/{w}/c-bridge.c').read_text()
 source=bridge
 if w=='picojpeg':source+=(S/'inputs/picojpeg/headers-bridge.c').read_text()
 sig=re.findall(r'int64_t\s+'+re.escape(a['symbol'])+r'\s*\(([^)]*)\)',bridge);assert len(sig)==1
 args=sig[0].replace('EXTRA','int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx')
 assert len(args.split(','))==8 and all(re.fullmatch(r'\s*int64_t\s+[a-zA-Z_][a-zA-Z_0-9]*\s*',x) for x in args.split(','))
 if 'EXTRA' in sig[0]:assert '#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx' in source
 proofs.append(dict(status=pr['expectedIndependentPerWorkloadStatus'],workload=w,symbol=a['symbol'],bridgeABI='I64_8ARGS',artifact=a['artifact'],savedCopy=rec(mapped(a['artifact']['path'])),symbolDefinition=sym,sourcePinsSHA256=g['sourcePinsSHA256'],inputPinsSHA256=g['inputPinsSHA256'],preregistrationSHA256=g['preregistrationSHA256'],GO=q['GO'],dependencyCallIndex=j+1,buildCallIndex=j+20,guestExecutionQualified=False,performanceQualified=False,CfuelArenaQualified=False))
assert not q['cleanBuildClaimed'] and not q['performanceQualified'] and not q['C2'] and q['noRetry']
print(json.dumps(dict(verified=True,calls=38,artifacts=19,collectedFiles=len(names),collectedBytes=total,dynamicHeaders=len(dyn),diagnosticStreams=warnings,symbols=[v['symbolDefinition'] for v in proofs]),indent=2))
(A/'verified-proofs.json').write_text(json.dumps(proofs,indent=2)+'\n')
