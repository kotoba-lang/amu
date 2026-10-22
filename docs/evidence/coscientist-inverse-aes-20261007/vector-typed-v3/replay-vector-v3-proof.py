"""Stdlib-only DATA replay. Does not run compiler, guest, build, solver or network."""
from pathlib import Path,PurePosixPath
import json,hashlib,tarfile,tempfile,types,sys,re
D=Path(__file__).resolve().parent;sha=lambda b:hashlib.sha256(b).hexdigest()
mp=D/'vector-v3-proof.manifest.json'
assert sha(mp.read_bytes())=='c56364c30f4e34aa26311b6b9c1ca99ac1bd25cdb7ff73659f6ff1e20e09f622','manifest envelope hash'
m=json.loads(mp.read_text());a=D/m['archive'];assert a.stat().st_size==m['archiveBytes']<=5242880 and sha(a.read_bytes())==m['archiveSHA256'],'archive envelope hash'
assert len(m['paths'])<=2000 and m['uncompressedObjectBytes']<=67108864
with tempfile.TemporaryDirectory(prefix='vector-v3-data-replay-')as td:
 root=Path(td).resolve();objects={}
 with tarfile.open(a,'r:gz')as tf:
  for t in tf:
   assert t.isfile()and t.name.startswith('objects/')and len(t.name)==72 and t.size<=67108864
   b=tf.extractfile(t).read();h=t.name[8:];assert re.fullmatch('[0-9a-f]{64}',h)and sha(b)==h and h not in objects;objects[h]=b
 assert len(objects)==m['objects']and sum(map(len,objects.values()))==m['uncompressedObjectBytes']
 for name,v in m['paths'].items():
  rel=PurePosixPath(name);assert not rel.is_absolute()and'..'not in rel.parts
  b=objects[v['sha256']];assert len(b)==v['bytes'];p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 P=root/'workspace';T=root/'private';originalP='/Users/junkawasaki/github/workspaces/codex';originalT='/private/tmp/amu-aes-resident-fuel-20261007'
 def load(p):return json.loads(p.read_text())
 def orig(p):return str(p).replace(str(P),originalP).replace(str(T),originalT)
 def mapped(s):return Path(str(s).replace(originalP,str(P)).replace(originalT,str(T)))
 def module(p,name):
  s=p.read_text().replace(originalP,str(P)).replace(originalT,str(T));q=types.ModuleType(name);q.__file__=str(p);sys.modules[name]=q;exec(compile(s,str(p),'exec'),q.__dict__);return q
 def bind_selected(p,rec):
  assert sha(p.read_bytes())==rec['sha256']and len(p.read_bytes())==rec['bytes']
 # All current input manifests/review GO references rehashed when selected.
 for dirname in ['vector-typed-on-native-build-v3','vector-typed-observer-native-v3']:
  W=P/dirname
  for k,v in load(W/'input-pins.json').items():bind_selected(W/k,v)
 go=load(P/'vector-typed-on-native-build-v3/parent-build-go.json')
 for p,h in go['frozenReviews'].items():assert sha(mapped(p).read_bytes())==h
 # Actual four generations/exact previous producer argv and nativecontainer/header/offset.
 W=P/'vector-typed-on-native-build-v3';att=load(W/'attempts.json');assert len(att)==8;gens=[]
 assert load(W/'build-terminal.json')=={'allWritesComplete':True,'processes':8,'generations':4,'failure':False}
 for ix,r in enumerate(att):
  g=ix//2+1;stage=['compile','extract'][ix%2];off=(W/f'seed-{g-1}.offset').read_text().strip()
  prefix=[orig(W/'kexe-loader'),orig(W/f'seed-{g-1}.bin'),off,'0','aarch64','35,37,38,39','--']
  suffix=['compile',orig(W/'unity.kotoba'),'--target','aarch64-macos','--output',orig(W/f'seed-{g}.kseed')]if stage=='compile'else['extract-native',orig(W/f'seed-{g}.kseed'),'--symbol','main','--output',orig(W/f'seed-{g}.bin')]
  assert r['argv']==prefix+suffix and r['generation']==g and r['stage']==stage and r['state']=='terminal'and r['returncode']==0
  stdout=(W/f'seed-{g}-{stage}.stdout').read_bytes();assert stdout.startswith(b'{:ok true')and(W/f'seed-{g}-{stage}.stderr').read_bytes()==b''
  if stage=='extract':
   b=(W/f'seed-{g}.bin').read_bytes();kb=(W/f'seed-{g}.kseed').read_bytes();assert len(b)==919208 and kb==b'KSEED1 919208 1\nmain 0 0\n\n'+b and int((W/f'seed-{g}.offset').read_text())==0;gens.append(sha(b))
 assert len(set(gens))==1 and gens[0]=='c015d515027af98bbdb6ef9bf9d291046d388b55dc90309de253ae429d581683'
 # Exact source reverse V3 -> V2 + reconstruct four archived source variants' old hashes.
 A=P/'vector-typed-analysis-v3';B=P/'vector-typed-analysis-v2';new=(A/'analysis.kotoba').read_text();old=(B/'analysis.kotoba').read_text()
 def formspan(s,n):
  start=s.index('(defn- '+n+' ');level=0;quoted=comment=escape=False
  for i in range(start,len(s)):
   c=s[i]
   if comment:
    if c=='\n':comment=False
    continue
   if quoted:
    if escape:escape=False
    elif c=='\\':escape=True
    elif c=='"':quoted=False
    continue
   if c==';':comment=True
   elif c=='"':quoted=True
   elif c=='(':level+=1
   elif c==')':
    level-=1
    if not level:return start,i+1
  raise AssertionError(n)
 rev=new
 for n in ['vw-domain-all','vw-run']:
  st,en=formspan(rev,n);x,y=formspan(old,n);rev=rev[:st]+old[x:y]+rev[en:]
 st=rev.index(';; V3: complete module label-location');en=rev.index('(defn- vw-domain-all',st);x=old.index('(defn- vw-unique-label');y=old.index('(defn- vw-domain-all',x);rev=rev[:st]+old[x:y]+rev[en:];assert rev==old
 oldpins=load(B/'artifact-pins.json')
 for filename in ['41-vector-analysis-default.kotoba','41-vector-analysis-on.kotoba','unity-vector-analysis-default.kotoba','unity-vector-analysis-on.kotoba']:
  n=new if'default'in filename else new.replace('(def vw-feature 0)','(def vw-feature 1)');o=old if'default'in filename else old.replace('(def vw-feature 0)','(def vw-feature 1)');s=(A/filename).read_text();assert s.count(n)==1;r=s.replace(n,o).encode();rec=oldpins[originalP+'/vector-typed-analysis-v2/'+filename];assert sha(r)==rec['sha256']and len(r)==rec['bytes']
 # Actual original19 diagnostic compiler argv and complete raw records against independent snapshots.
 W=P/'vector-typed-observer-native-v3';assert load(W/'terminal.json')=={'allWritesComplete':True,'attempts':40,'images':19,'failure':False};attempts=load(W/'attempts.json');assert len(attempts)==40
 for ix,r in enumerate(attempts):
  group=ix//2;stage=['compile','extract'][ix%2];out=W/'observer'if group==0 else W/'ports'/load(W/'images.json')[group-1]['workload'];seed=W/'producer.bin'if group==0 else W/'observer/native.bin';src=W/'unity-observer.kotoba'if group==0 else W/'sources'/f'{out.name}.kotoba'
  suffix=['compile',orig(src),'--target','aarch64-macos','--output',orig(out/'image.kseed')]if stage=='compile'else['extract-native',orig(out/'image.kseed'),'--symbol','main'if group==0 else next(e['symbol']for e in load(W/'comparison-matrix.json')['entries']if e['workload']==out.name),'--output',orig(out/'native.bin')]
  assert r['argv']==[orig(W/'kexe-loader'),orig(seed),'0','0','aarch64','35,37,38,39','--',*suffix]and r['returncode']==0 and r['state']=='terminal'and r['index']==ix+1
  assert load(out/(stage+'.status.json'))==r and(out/(stage+'.stderr')).read_bytes()==b''
 filt=module(P/'vector-typed-observer-plan-v3/filter-records.py','filter')
 dom=module(P/'vector-reference-v6/domain.py','domain');an=module(P/'vector-reference-v6/analyze.py','analyze')
 rd={r['workload']:r for r in load(P/'vector-reference-v6/reference-results.json')};ind=load(P/'vector-typed-observer-independent-v3/report.json');ir={r['workload']:r for r in ind['rows']};joined=[];v6computed=[]
 for im in load(W/'images.json'):
  name=im['workload'];d=W/'ports'/name;baseline=T/'team-charged-compare-v1/original19-images/on'/name
  assert (d/'image.kseed').read_bytes()==(P/'vector-typed-default-original19/ports'/name/'image.kseed').read_bytes()
  b=(d/'native.bin').read_bytes();assert b==(baseline/'native.bin').read_bytes()and(d/'native.offset').read_bytes()==(baseline/'native.offset').read_bytes()and sha(b)==im['nativeSha256']and len(b)==im['bytes']
  assert sha((W/'sources'/f'{name}.kotoba').read_bytes())==im['sourceSha256']
  rows=load(d/'observer-records.json');assert rows==[{'tag':tag,'fields':v}for tag,v in filt.parse(d/'compile.stdout')];z=filt.audit(d/'compile.stdout');model=an.Module(rows)
  try:
   domain=dom.audit(rows)
   if domain['errors']:v={'status':'REFUSED whole-module indexed-domain','domain':domain,'reads':[],'summaries':{},'transferSteps':0}
   else:v=model.solve();v['status']='completed conservative reference';v['domain']=domain
  except(RuntimeError,KeyError,IndexError)as e:v={'status':'REFUSED setup/budget','error':repr(e),'reads':[],'summaries':{},'transferSteps':model.steps}
  v['workload']=name;v['admittedCount']=sum(x['admittedReference']for x in v['reads']);v=json.loads(json.dumps(v));assert v==rd[name],('V6 exact current records',name);v6computed.append(v)
  reads={x['sir']:x for x in v['reads']};emap={x['fields'][0]:x['fields']for x in rows if x['tag']=='EMIT'};cache={x['fields'][0]:x['fields']for x in rows if x['tag']=='CACHE'};sir={x['fields'][0]:x['fields']for x in rows if x['tag']=='SIR'}
  i=1;pos=1;visited=[]
  while i<=len(sir):
   _,skip,start,end=emap[i];assert start==pos and end>=start and skip>=0 and i in cache;visited.append(i);pos=end;i+=skip+1
  assert i==len(sir)+1 and set(visited)==set(emap)==set(cache)and(pos-1)*4<=len(b)
  for tag,fields in filt.parse(d/'compile.stdout'):
   if tag=='VWSITE':
    j,f,token,L,index,temp,ck,hk=fields;x=reads[j];assert x['admittedReference']and x['fn']==f and x['handleFact'][3]>=L and x['indexFact']==['s',index,index];kind,num=x['handleFact'][1];expected=num if kind=='param'else-num if kind=='allocation'else-65536-num;assert token==expected
  actual=ir[name]
  for a,k in [('entryStatus','entryStatus'),('kernelRefusal','refusal'),('phase','phase'),('workAccountingUnits','workUnits'),('semanticCount','semanticCount'),('generatorCompatibleCount','generatorCompatibleCount')]:assert z[a]==actual[k]
  z['workload']=name;joined.append(z)
 semantic=sum(z['semanticCount']for z in joined);compatible=sum(z['generatorCompatibleCount']for z in joined);priority={'edn','nettle-sha256','picojpeg','qrduino','xgboost'};pc=sum(z['generatorCompatibleCount']for z in joined if z['workload']in priority);pb=sum(z['generatorCompatibleCount']>0 for z in joined if z['workload']in priority);complete=sum(z['entryStatus']==z['kernelRefusal']==0 for z in joined);work=sum(z['entryStatus']==0 and z['kernelRefusal']!=0 for z in joined);fncap=sum(z['entryStatus']==4 for z in joined)
 assert(semantic,compatible,pc,pb,complete,work,fncap)==(22,18,3,1,8,9,2)
 second=load(P/'vector-typed-observer-resource-independent-v3/report.json');assert second['categories']=={'complete':complete,'workCapConsistentRefusal':work,'FNcap':fncap}and second['totalSemanticSites']==semantic
 for z in joined:
  rr=next(r for r in second['rows']if r['workload']==z['workload']);assert rr['entry']==z['entryStatus']and rr['semanticSites']==z['semanticCount']
  if rr['status']:assert rr['status'][:3]==[z['kernelRefusal'],z['phase'],z['workAccountingUnits']]
 owner=load(P/'vector-typed-observer-join-v3/report.json');assert owner['semanticCandidates']==semantic and owner['generatorCompatibleCandidates']==compatible and not owner['actual32EmittedSites3BodiesGate']
 print(json.dumps({'status':'PASS copied3file V3 DATA proof; FAIL32/3 eligibility','compilerBuildProcesses':8,'diagnosticCompilerProcesses':40,'original19ByteOffsetParity':True,'V6ExactRowsRecomputed':19,'semanticSites':semantic,'generatorCompatibleSites':compatible,'prioritySites':pc,'priorityWorkloads':pb,'completedModules':complete,'workCapRefusals':work,'FNcapRefusals':fncap,'native32Gate':False,'nativeGuestSolverNetworkTimingRuns':0,'NFWholeMWork128RuntimePerformanceAdoption':'HOLD','historicalUnselectedPins':'references only; V2comparison retained, no old raw reruns'}))
