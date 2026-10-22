"""Stdlib three-file DATA-ONLY replay. Never runs compiler/guest/solver/build scripts."""
from pathlib import Path,PurePosixPath
import json,hashlib,tarfile,tempfile,types,sys,re,collections
D=Path(__file__).resolve().parent;sha=lambda b:hashlib.sha256(b).hexdigest()
mp=D/'typed-v7-proof.manifest.json'
assert sha(mp.read_bytes())=='e0a767bc88068a149179d59d26b71988bba9ae364fb4e4ae412a8eafcc7fbc6f','manifest envelope hash'
m=json.loads(mp.read_text());a=D/m['archive'];assert a.stat().st_size==m['archiveBytes']<=5242880 and sha(a.read_bytes())==m['archiveSHA256'],'archive envelope hash'
assert len(m['paths'])<=2000 and m['uncompressedObjectBytes']<=67108864
with tempfile.TemporaryDirectory(prefix='amu-typed-observer-offline-')as td:
 root=Path(td).resolve();objects={}
 with tarfile.open(a,'r:gz')as tf:
  for t in tf:
   assert t.isfile()and t.name.startswith('objects/')and len(t.name)==72 and t.size<=67108864
   b=tf.extractfile(t).read();h=t.name[8:];assert sha(b)==h and h not in objects;objects[h]=b
 assert len(objects)==m['objects']and sum(map(len,objects.values()))==m['uncompressedObjectBytes']
 for name,v in m['paths'].items():
  rel=PurePosixPath(name);assert not rel.is_absolute()and'..'not in rel.parts
  if 'recipe'in v:continue
  b=objects[v['sha256']];assert len(b)==v['bytes'];p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 for name,v in m['paths'].items():
  if 'recipe'not in v:continue
  rec=v['recipe'];base=(root/rec['basePath']).read_bytes();before=(root/rec['beforePath']).read_bytes();after=(root/rec['afterPath']).read_bytes()
  if rec['feature']==1:before=before.replace(b'(def vw-feature 0)',b'(def vw-feature 1)',1);after=after.replace(b'(def vw-feature 0)',b'(def vw-feature 1)',1)
  assert base.count(before)==1
  b=base.replace(before,after,1);assert sha(b)==v['sha256']and len(b)==v['bytes'];p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 P=root/'workspace';T=root/'private'
 def load(p):return json.loads(p.read_text())
 def module(p,name):
  s=p.read_text().replace('/Users/junkawasaki/github/workspaces/codex',str(P)).replace('/private/tmp/amu-aes-resident-fuel-20261007',str(T))
  q=types.ModuleType(name);q.__file__=str(p);sys.modules[name]=q;exec(compile(s,str(p),'exec'),q.__dict__);return q
 # Run only the independent pure raw audit prefix; its later reporting writes omitted.
 p=P/'vector-typed-observer-resource-independent-v7/audit.py';s=p.read_text().split('\nr={',1)[0]
 s=s.replace('/Users/junkawasaki/github/workspaces/codex',str(P)).replace('/private/tmp/amu-aes-resident-fuel-20261007',str(T))
 # GO contains original absolute paths: map those read-only references in Python Path construction.
 class MappedPath(type(Path())):
  def __new__(cls,*args):
   args=tuple(str(x).replace('/Users/junkawasaki/github/workspaces/codex',str(P)).replace('/private/tmp/amu-aes-resident-fuel-20261007',str(T))for x in args)
   return super().__new__(cls,*args)
 s=s.replace('from pathlib import Path','').replace("(W/'kexe-loader').stat().st_mode&0o111"," m['paths']['workspace/vector-typed-observer-native-v7/kexe-loader']['mode']&0o111")
 # Stored argv remain original strings; compare against original commandnames while opening mapped files.
 originalW='/Users/junkawasaki/github/workspaces/codex/vector-typed-observer-native-v7'
 def normalize_argv(x):return str(x).replace(str(P),'/Users/junkawasaki/github/workspaces/codex')
 # Adapt only path-text comparisons and origin hashing lookups, never predicates/oracles.
 s=s.replace("str(W/'kexe-loader')","normalize_argv(W/'kexe-loader')").replace('str(seed)','normalize_argv(seed)').replace('str(src)','normalize_argv(src)').replace("str(out/'image.kseed')","normalize_argv(out/'image.kseed')").replace("str(out/'native.bin')","normalize_argv(out/'native.bin')")
 q={'__file__':str(p),'Path':MappedPath,'normalize_argv':normalize_argv,'m':m};exec(compile(s,'raw40audit','exec'),q)
 assert len(q['attempts'])==40 and len(q['rows'])==19 and q['pc']==18
 assert collections.Counter(x['category']for x in q['rows'])=={'complete':15,'workCapConsistentRefusal':2,'FNcap':2}
 # Source-only six-form reversal, not nativeM cleanup proof.
 def forms(s):
  out={}
  for v in re.finditer(r'^\(def(?:n-?)?\s+([^\s\[]+)',s,re.M):
   depth=0;comment=False
   for end in range(v.start(),len(s)):
    c=s[end]
    if c=='\n':comment=False
    if comment:continue
    if c==';':comment=True;continue
    if c=='(':depth+=1
    if c==')':
     depth-=1
     if depth==0:out[v[1]]=s[v.start():end+1];break
   else:raise AssertionError(('unbalancedform',v[1]))
  return out
 A=P/'vector-typed-analysis-v6';B=P/'vector-typed-analysis-v7';old=forms((A/'analysis.kotoba').read_text());new=forms((B/'analysis.kotoba').read_text());changed=[n for n in new if old.get(n)!=new[n]]
 assert set(changed)=={'vw-mutual-links','vw-out-build','vw-out-checked','vw-out-head','vw-path-links','vw-mutual','vw-path-edges','vw-run'}
 delta=load(B/'source-deltas.json');assert len(delta['replacements'])==3
 for name in ['41-vector-analysis-on.kotoba','41-vector-analysis-default.kotoba','unity-vector-analysis-on.kotoba','unity-vector-analysis-default.kotoba']:
  body=(B/name).read_text();assert body.count(delta['helperInsertion'])==1;body=body.replace(delta['helperInsertion'],'',1)
  for x in reversed(delta['replacements']):assert body.count(x['new'])==1;body=body.replace(x['new'],x['old'],1)
  assert body==(A/name).read_text()
 assert load(B/'layout.json')['ownedWords']==50177 and load(B/'layout.json')['extraAllocation']==0
 # Current producer inputs and GO reviews are independently hashbound, no historical statistics.
 BW=P/'vector-typed-on-native-build-v7'
 for n,v in load(BW/'input-pins.json').items():assert sha((BW/n).read_bytes())==v['sha256']and(BW/n).stat().st_size==v['bytes']
 bg=load(BW/'parent-build-go.json');assert bg['nativeCompilerOnly']and not bg['benchmarkTiming']and bg['unitySHA256']==sha((BW/'unity.kotoba').read_bytes())
 for path,h in bg['frozenReviews'].items():assert sha(MappedPath(path).read_bytes())==h
 assert (BW/'unity.kotoba').read_bytes()==(B/'unity-vector-analysis-on.kotoba').read_bytes()
 # Preserved lexical source failure and pure ordered graph model2, no native controls.
 failure=load(B/'initial-source-check-failure.json');assert failure['nativeActions']==0 and 'missing closing parentheses'in failure['failure']
 p=P/'vector-outgoing-edge-index-design-v1/model-v2.py';s=p.read_text().split("(D/'report-v2.json').write_text",1)[0]
 ns={'__file__':str(p)};exec(compile(s,str(p),'exec'),ns)
 assert ns['r']==load(P/'vector-outgoing-edge-index-design-v1/report-v2.json')and ns['cases']==1669 and all(ns['mutants'].values())
 # Eight compiler build processes, exact previous-generation/own temporary-header binding.
 W=P/'vector-typed-on-native-build-v7';att=load(W/'attempts.json');assert len(att)==8;gens=[]
 for i,r in enumerate(att):
  g=i//2+1;stage=['compile','extract'][i%2];prefix=[normalize_argv(W/'kexe-loader'),normalize_argv(W/f'seed-{g-1}.bin'),'0','0','aarch64','35,37,38,39','--']
  suffix=['compile',normalize_argv(W/'unity.kotoba'),'--target','aarch64-macos','--output',normalize_argv(W/f'seed-{g}.kseed')]if stage=='compile'else['extract-native',normalize_argv(W/f'seed-{g}.kseed'),'--symbol','main','--output',normalize_argv(W/f'seed-{g}.bin')]
  assert r['argv']==prefix+suffix and r['returncode']==0 and r['state']=='terminal'
  assert (W/f'seed-{g}-{stage}.stderr').read_bytes()==b''and b':ok true'in(W/f'seed-{g}-{stage}.stdout').read_bytes()
  if stage=='extract':
   kb=(W/f'seed-{g}.kseed').read_bytes();b=(W/f'seed-{g}.bin').read_bytes();assert kb==b'KSEED1 924032 1\nmain 0 0\n\n'+b and len(b)==924032 and int((W/f'seed-{g}.offset').read_text())==0;gens.append(sha(b))
 assert len(set(gens))==1 and gens[0]=='3942ae3b5b7fd7edae054b1867ae08b7a048a1601bef3dc6787951d5776c802e'
 # Actual raw tuples/cache/span filters and complete raw V6 semantic reference, no native surrogate.
 filt=module(P/'vector-typed-observer-join-v7/filter-records.py','frozen_filter')
 dom=module(P/'vector-reference-v6/domain.py','domain');an=module(P/'vector-reference-v6/analyze.py','analyze')
 refs=load(P/'vector-reference-v6/reference-results.json');rd={x['workload']:x for x in refs};joined=[];v6computed=[]
 W=P/'vector-typed-observer-native-v7'
 for d in sorted((W/'ports').iterdir()):
  z=filt.audit(d/'compile.stdout');r=load(d/'observer-records.json');model=an.Module(r)
  try:
   domain=dom.audit(r)
   if domain['errors']:v={'status':'REFUSED whole-module indexed-domain','domain':domain,'reads':[],'summaries':{},'transferSteps':0}
   else:v=model.solve();v['status']='completed conservative reference';v['domain']=domain
  except(RuntimeError,KeyError,IndexError)as e:v={'status':'REFUSED setup/budget','error':repr(e),'reads':[],'summaries':{},'transferSteps':model.steps}
  v['workload']=d.name;v['admittedCount']=sum(x['admittedReference']for x in v['reads']);v=json.loads(json.dumps(v))
  assert v==rd[d.name],('V6 recompute exact current data',d.name);v6computed.append(v)
  reads={x['sir']:x for x in v['reads']if x['admittedReference']}
  for tag,fields in filt.parse(d/'compile.stdout'):
   if tag=='VWSITE':
    i,f,token,L,index,temp,ck,hk=fields;x=reads[i];assert x['fn']==f and x['handleFact'][3]==L and x['indexFact'][1]==index
  z['workload']=d.name;joined.append(z)
 semantic=sum(z['semanticCount']for z in joined);compatible=sum(z['generatorCompatibleCount']for z in joined);priority={'edn','nettle-sha256','picojpeg','qrduino','xgboost'}
 pc=sum(z['generatorCompatibleCount']for z in joined if z['workload']in priority);pb=sum(z['generatorCompatibleCount']>0 for z in joined if z['workload']in priority)
 assert (semantic,compatible,pc,pb)==(43,33,16,3)
 ps=sum(z['semanticCount']for z in joined if z['workload']in priority);assert ps==18
 missing=sum(v['admittedCount']for v in v6computed)-semantic;assert missing==42
 owner=load(P/'vector-typed-observer-join-v7/report.json');assert owner['semanticCandidates']==semantic and owner['generatorCompatibleCandidates']==compatible and not owner['actual32EmittedSites3BodiesGate']
 for z in joined:
  old=next(x for x in owner['rows']if x['workload']==z['workload'])
  for k in ['entryStatus','kernelRefusal','phase','workAccountingUnits','semanticCount','generatorCompatibleCount']:assert old[k]==z[k]
 print(json.dumps({'status':'PASS copied3file offline typed-on observer proof; applicability FAIL/HOLD','nativeCompilerBuildProcesses':8,'totalLoaderBuildCalls':8,'initialLexicalSourceFailureRetained':True,'orderedGraphModelV2Cases':1669,'diagnosticCompilerProcesses':40,'originalModules':19,'KSEEDNativeBaselineParity':True,'V6RowsRecomputedExact':len(v6computed),'semanticSites':semantic,'generatorCompatibleSites':compatible,'prioritySemanticSites':ps,'prioritySites':pc,'priorityBodies':pb,'publishedTuplesMatched':43,'referenceCandidatesMissing':missing,'kernelComplete':15,'workCapConsistentRefusal':2,'FNcap':2,'actual32Site3BodyGate':False,'nativeGuestSolverNetworkTimingRuns':0,'new50177BankCleanupDirtyReuse':'PENDING','NFWholeMWork128RuntimePerformanceAdoption':'HOLD'}))
