"""Three-file portable DATA-ONLY full semantic replay. No subprocess/native/network."""
from pathlib import Path,PurePosixPath
import json,hashlib,tarfile,tempfile,types,sys,sysconfig,os
D=Path(__file__).resolve().parent;sha=lambda b:hashlib.sha256(b).hexdigest()
# Guard every file open: only the three supplied files, the materialized temp tree,
# and Python stdlib (excluding third-party site packages) are permitted.
stdlib=Path(sysconfig.get_path('stdlib')).resolve();temp_roots=[]
allowed={D/'typed-v8-proof.manifest.json',D/'typed-v8-proof.tgz',Path(__file__).resolve()}
def read_guard(event,args):
 if event!='open':return
 path=args[0]
 if isinstance(path,int):return  # Existing stdio descriptors; no arbitrary pathname.
 f=Path(os.fsdecode(path)).resolve()
 if f in allowed:return
 if any(f.is_relative_to(t)for t in temp_roots):return
 if f.is_relative_to(stdlib)and'site-packages'not in f.parts and'dist-packages'not in f.parts:return
 raise PermissionError('hermetic replay rejects file open: '+str(f))
sys.addaudithook(read_guard)
mp=D/'typed-v8-proof.manifest.json'
assert sha(mp.read_bytes())=='77763af9496c0652bb55eae37c5ce870e55f92981b99c830016a72e83ceb38e5','manifest envelope hash'
m=json.loads(mp.read_text());a=D/m['archive'];assert a.stat().st_size==m['archiveBytes']<=5242880 and sha(a.read_bytes())==m['archiveSHA256'],'archive envelope hash'
assert len(m['paths'])<=2000 and m['uncompressedObjectBytes']<=67108864
with tempfile.TemporaryDirectory(prefix='amu-v8-offline-',dir=D)as td:
 root=Path(td).resolve();temp_roots.append(root);objects={};cache={}
 with tarfile.open(a,'r:gz')as tar:
  for t in tar:
   assert t.isfile()and t.name.startswith('objects/')and len(t.name)==72 and t.size<=67108864
   b=tar.extractfile(t).read();h=t.name[8:];assert sha(b)==h and h not in objects;objects[h]=b
 assert len(objects)==m['objects']and sum(map(len,objects.values()))==m['uncompressedObjectBytes']
 def materialize(n):
  rel=PurePosixPath(n);assert not rel.is_absolute()and'..'not in rel.parts
  if n in cache:return cache[n]
  p=m['paths'][n]
  if 'recipe'in p:
   r=p['recipe'];assert r['kind']=='exact-single-kernel-replacement'
   b=materialize(r['basePath']);old=materialize(r['beforePath']);new=materialize(r['afterPath'])
   if r['feature']==1:old=old.replace(b'(def vw-feature 0)',b'(def vw-feature 1)',1);new=new.replace(b'(def vw-feature 0)',b'(def vw-feature 1)',1)
   assert b.count(old)==1;b=b.replace(old,new,1)
  else:b=objects[p['sha256']]
  assert len(b)==p['bytes']and sha(b)==p['sha256'];cache[n]=b;f=root/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b);return b
 for n in m['paths']:materialize(n)
 P=root/'workspace';T=root/'private';N=P/'vector-typed-observer-native-v8';B=P/'vector-typed-on-native-build-v8';J=P/'vector-typed-observer-join-v8-native-controls'
 load=lambda p:json.loads(p.read_text())
 def module(p,name):
  source=p.read_text()
  if name in {'domain','frozen_reference'}:
   old="P=Path('/private/tmp/amu-aes-resident-fuel-20261007')";new='P=Path('+repr(str(T))+')'
   assert source.count(old)==1,('exact P initializer',name)
   before,after=source.split(old);mapped=before+new+after
   assert mapped.split(new)==[before,after],('algorithm remainder unchanged',name)
   source=mapped
  q=types.ModuleType(name);q.__file__=str(p);sys.modules[name]=q;exec(compile(source,str(p),'exec'),q.__dict__);return q
 filt=module(J/'filter-records.py','frozen_filter');dom=module(P/'vector-reference-v6/domain.py','domain');an=module(P/'vector-reference-v6/analyze.py','frozen_reference')
 # Only pure owner audit definition prefix, guarded main reporting not executed.
 src=(J/'audit.py').read_text().split("if __name__=='__main__':",1)[0]
 src=src.replace("REFERENCE=Path('/Users/junkawasaki/github/workspaces/codex/vector-reference-v6/reference-results.json')",'REFERENCE=Path('+repr(str(P/'vector-reference-v6/reference-results.json'))+')')
 owner={'__file__':str(J/'audit.py')};exec(compile(src,'pure_raw_audit','exec'),owner)
 original='/Users/junkawasaki/github/workspaces/codex'
 norm=lambda p:str(p).replace(str(P),original)
 def process(r,prefix,suffix):assert r['state']=='terminal'and r['returncode']==0 and r['argv']==prefix+suffix
 att=load(B/'attempts.json');assert len(att)==8;gens=[]
 for i,r in enumerate(att):
  g=i//2+1;stage=['compile','extract'][i%2];pre=[norm(B/'kexe-loader'),norm(B/f'seed-{g-1}.bin'),'0','0','aarch64','35,37,38,39','--']
  suf=['compile',norm(B/'unity.kotoba'),'--target','aarch64-macos','--output',norm(B/f'seed-{g}.kseed')]if stage=='compile'else['extract-native',norm(B/f'seed-{g}.kseed'),'--symbol','main','--output',norm(B/f'seed-{g}.bin')]
  process(r,pre,suf);assert (B/f'seed-{g}-{stage}.stderr').read_bytes()==b''and b':ok true'in(B/f'seed-{g}-{stage}.stdout').read_bytes()
  if stage=='extract':
   b=(B/f'seed-{g}.bin').read_bytes();assert len(b)==929424 and int((B/f'seed-{g}.offset').read_text())==0;assert (B/f'seed-{g}.kseed').read_bytes()==b'KSEED1 929424 1\nmain 0 0\n\n'+b;gens.append(sha(b))
 assert len(set(gens))==1 and gens[0]=='2a0d9a3b47dab57ca8b52532e7ce5c9cff9b189de1e62af564b9436646dd239b'
 assert (N/'producer.bin').read_bytes()==(B/'seed-4.bin').read_bytes()
 attempts=load(N/'attempts.json');assert len(attempts)==40;refs={r['workload']:r for r in load(P/'vector-reference-v6/reference-results.json')};assert len(refs)==19
 # Exact canonical symbols from immutable matrix; observer main only.
 matrix_bytes=(N/'comparison-matrix.json').read_bytes();matrix_hash=sha(matrix_bytes)
 assert matrix_hash=='b3c4fcf09e51d9a42e7c8cdd9467dca401b8f99d9922b6b7fc086a3a0ba2721c'
 assert load(N/'input-pins.json')['comparison-matrix.json']=={'bytes':len(matrix_bytes),'sha256':matrix_hash}
 matrix=json.loads(matrix_bytes);assert matrix['format']=='amu.embench-comparison-matrix-spec/v1'
 entries=matrix['entries'];symbols={r['workload']:r['symbol']for r in entries};assert len(entries)==len(symbols)==19 and set(symbols)==set(refs) and set(symbols.values())<= {'bench','batch'}
 # Exact 2 observer then original19 ordered compile/extract commands.
 work=['observer']+['ports/'+n for n in sorted(refs)]
 for i,r in enumerate(attempts):
  label=work[i//2];out=N/label;stage=['compile','extract'][i%2];seed=N/'producer.bin'if label=='observer'else N/'observer/native.bin';source=N/'unity-observer.kotoba'if label=='observer'else N/'sources'/((out.name)+'.kotoba')
  pre=[norm(N/'kexe-loader'),norm(seed),'0','0','aarch64','35,37,38,39','--'];suf=['compile',norm(source),'--target','aarch64-macos','--output',norm(out/'image.kseed')]if stage=='compile'else['extract-native',norm(out/'image.kseed'),'--symbol',('main'if label=='observer'else symbols[out.name]),'--output',norm(out/'native.bin')]
  process(r,pre,suf);assert r['label']==label+'/'+stage;assert (out/(stage+'.stderr')).read_bytes()==b''and b':ok true'in(out/(stage+'.stdout')).read_bytes()
 baseline={x['workload']:x for x in load(N/'baseline19.json')};computed=[];joined=[];tuplecount=0
 for n in sorted(refs):
  d=N/'ports'/n;parsed=filt.parse(d/'compile.stdout');raw=[{'tag':t,'fields':v}for t,v in parsed];assert raw==load(d/'observer-records.json')
  mod=an.Module(raw)
  try:
   domain=dom.audit(raw)
   if domain['errors']:v={'status':'REFUSED whole-module indexed-domain','domain':domain,'reads':[],'summaries':{},'transferSteps':0}
   else:v=mod.solve();v['status']='completed conservative reference';v['domain']=domain
  except(RuntimeError,KeyError,IndexError)as e:v={'status':'REFUSED setup/budget','error':repr(e),'reads':[],'summaries':{},'transferSteps':mod.steps}
  v['workload']=n;v['admittedCount']=sum(x['admittedReference']for x in v['reads']);v=json.loads(json.dumps(v));assert v==refs[n],('reference',n);computed.append(v)
  z=owner['audit_raw'](d/'compile.stdout');assert not z['tupleDifferences']and not z['semanticSitesNotInV6'];z['workload']=n;joined.append(z)
  sir={x['fields'][0]:x['fields'][1:]for x in raw if x['tag']=='SIR'};sites=filt.indexed(parsed,'VWSITE');expect={x['sir']:x for x in v['reads']if x['admittedReference']};assert set(expect)==set(sites)
  for i,q in expect.items():
   h=q['handleFact'];kind,x=h[1];assert h[0]=='v'and h[2]=='entry'and h[4]is True
   token=x if kind=='param'else -x if kind=='allocation'else -65536-x if kind=='returned-allocation'else None;assert token is not None
   k=q['indexFact'];assert k[0]=='s'and k[1]==k[2];assert sites[i]==[i,q['fn'],token,h[3],k[1],sir[i][2],1,1];tuplecount+=1
  assert sha((N/'sources'/f'{n}.kotoba').read_bytes())==baseline[n]['sourceSha256']
  for base in [P/'vector-typed-default-original19/ports'/n,T/'team-charged-compare-v1/original19-images/on'/n]:
   for file in ['native.bin','image.kseed']:assert (d/file).read_bytes()==(base/file).read_bytes()
   assert int((d/'native.offset').read_text())==int((base/'native.offset').read_text())==baseline[n]['offset']
 priority={'edn','nettle-sha256','picojpeg','qrduino','xgboost'};semantic=sum(x['semanticCount']for x in joined);compatible=sum(x['generatorCompatibleCount']for x in joined);ps=sum(x['semanticCount']for x in joined if x['workload']in priority);pc=sum(x['generatorCompatibleCount']for x in joined if x['workload']in priority);pb=sum(x['generatorCompatibleCount']>0 for x in joined if x['workload']in priority)
 assert (semantic,compatible,ps,pc,pb,tuplecount)==(85,61,60,44,5,85)
 complete=sum(x['entryStatus']==0 and x['kernelRefusal']==0 for x in joined);refused=sum(x['entryStatus']==0 and x['kernelRefusal']==1 for x in joined);fncap=sum(x['entryStatus']==4 for x in joined);assert (complete,refused,fncap)==(17,0,2)
 print(json.dumps({'status':'PASS_PORTABLE_FULL_SEMANTIC_REPLAY','referenceRowsRecomputed':19,'identityTuples':tuplecount,'semantic':semantic,'compatible':compatible,'prioritySemantic':ps,'priorityCompatible':pc,'priorityBodies':pb,'fixedBuildCalls':8,'fixedObserverCalls':40,'whole19ContainerNativeOffsetBaselineExact':True,'kernelComplete':complete,'workCapRefusal':refused,'FNCapRefusal':fncap,'filtered60Gate':False,'compatible32Gate':True,'emittedSites':0,'nativeCalls':0,'new50689NativeSafety':'PENDING/HOLD','performance':'UNQUALIFIED'}))
