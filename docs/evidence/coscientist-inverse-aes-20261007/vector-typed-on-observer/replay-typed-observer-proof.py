"""Stdlib three-file DATA-ONLY replay. Never runs compiler/guest/solver/build scripts."""
from pathlib import Path,PurePosixPath
import json,hashlib,tarfile,tempfile,types,sys,re,collections
D=Path(__file__).resolve().parent;sha=lambda b:hashlib.sha256(b).hexdigest()
mp=D/'typed-observer-proof.manifest.json'
assert sha(mp.read_bytes())=='2c7548d18e2b311d8f556cd05c64403321305c21a18e8535596f5af362618018','manifest envelope hash'
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
  b=objects[v['sha256']];assert len(b)==v['bytes'];p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 P=root/'workspace';T=root/'private'
 def load(p):return json.loads(p.read_text())
 def module(p,name):
  s=p.read_text().replace('/Users/junkawasaki/github/workspaces/codex',str(P)).replace('/private/tmp/amu-aes-resident-fuel-20261007',str(T))
  q=types.ModuleType(name);q.__file__=str(p);sys.modules[name]=q;exec(compile(s,str(p),'exec'),q.__dict__);return q
 # Run only the independent pure raw audit prefix; its later reporting writes omitted.
 p=P/'vector-typed-observer-resource-independent/audit.py';s=p.read_text().split('\nr={',1)[0]
 s=s.replace('/Users/junkawasaki/github/workspaces/codex',str(P)).replace('/private/tmp/amu-aes-resident-fuel-20261007',str(T))
 # GO contains original absolute paths: map those read-only references in Python Path construction.
 class MappedPath(type(Path())):
  def __new__(cls,*args):
   args=tuple(str(x).replace('/Users/junkawasaki/github/workspaces/codex',str(P)).replace('/private/tmp/amu-aes-resident-fuel-20261007',str(T))for x in args)
   return super().__new__(cls,*args)
 s=s.replace('from pathlib import Path','').replace("(W/'kexe-loader').stat().st_mode&0o111"," m['paths']['workspace/vector-typed-observer-native-v1/kexe-loader']['mode']&0o111")
 # Stored argv remain original strings; compare against original commandnames while opening mapped files.
 originalW='/Users/junkawasaki/github/workspaces/codex/vector-typed-observer-native-v1'
 def normalize_argv(x):return str(x).replace(str(P),'/Users/junkawasaki/github/workspaces/codex')
 # Adapt only path-text comparisons and origin hashing lookups, never predicates/oracles.
 s=s.replace("str(W/'kexe-loader')","normalize_argv(W/'kexe-loader')").replace('str(seed)','normalize_argv(seed)').replace('str(src)','normalize_argv(src)').replace("str(out/'image.kseed')","normalize_argv(out/'image.kseed')").replace("str(out/'native.bin')","normalize_argv(out/'native.bin')")
 q={'__file__':str(p),'Path':MappedPath,'normalize_argv':normalize_argv,'m':m};exec(compile(s,'raw40audit','exec'),q)
 assert len(q['attempts'])==40 and len(q['rows'])==19 and q['pc']==3
 # Eight compiler build processes, exact previous-generation/own temporary-header binding.
 W=P/'vector-typed-on-native-build-v1';att=load(W/'attempts.json');assert len(att)==8;gens=[]
 for i,r in enumerate(att):
  g=i//2+1;stage=['compile','extract'][i%2];prefix=[normalize_argv(W/'kexe-loader'),normalize_argv(W/f'seed-{g-1}.bin'),'0','0','aarch64','35,37,38,39','--']
  suffix=['compile',normalize_argv(W/'unity.kotoba'),'--target','aarch64-macos','--output',normalize_argv(W/f'seed-{g}.kseed')]if stage=='compile'else['extract-native',normalize_argv(W/f'seed-{g}.kseed'),'--symbol','main','--output',normalize_argv(W/f'seed-{g}.bin')]
  assert r['argv']==prefix+suffix and r['returncode']==0 and r['state']=='terminal'
  assert (W/f'seed-{g}-{stage}.stderr').read_bytes()==b''and b':ok true'in(W/f'seed-{g}-{stage}.stdout').read_bytes()
  if stage=='extract':
   kb=(W/f'seed-{g}.kseed').read_bytes();b=(W/f'seed-{g}.bin').read_bytes();assert kb==b'KSEED1 918384 1\nmain 0 0\n\n'+b and len(b)==918384 and int((W/f'seed-{g}.offset').read_text())==0;gens.append(sha(b))
 assert len(set(gens))==1 and gens[0]=='7dbc44c2301249fb91a9429f994d0f29190a9f2bdfa7f7336c34398552bc9eee'
 # Actual raw tuples/cache/span filters and complete raw V6 semantic reference, no native surrogate.
 filt=module(P/'vector-typed-observer-join-v1/filter-records.py','frozen_filter')
 dom=module(P/'vector-reference-v6/domain.py','domain');an=module(P/'vector-reference-v6/analyze.py','analyze')
 refs=load(P/'vector-reference-v6/reference-results.json');rd={x['workload']:x for x in refs};joined=[];v6computed=[]
 W=P/'vector-typed-observer-native-v1'
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
 assert (semantic,compatible,pc,pb)==(22,18,3,1)
 owner=load(P/'vector-typed-observer-join-v1/report.json');assert owner['semanticCandidates']==semantic and owner['generatorCompatibleCandidates']==compatible and not owner['actual32EmittedSites3BodiesGate']
 for z in joined:
  old=next(x for x in owner['rows']if x['workload']==z['workload'])
  for k in ['entryStatus','kernelRefusal','phase','workAccountingUnits','semanticCount','generatorCompatibleCount']:assert old[k]==z[k]
 print(json.dumps({'status':'PASS copied3file offline typed-on observer proof; applicability FAIL/HOLD','nativeCompilerBuildProcesses':8,'diagnosticCompilerProcesses':40,'originalModules':19,'KSEEDNativeBaselineParity':True,'V6RowsRecomputedExact':len(v6computed),'semanticSites':semantic,'generatorCompatibleSites':compatible,'prioritySites':pc,'priorityBodies':pb,'kernelComplete':7,'workCapConsistentRefusal':10,'FNcap':2,'actual32Site3BodyGate':False,'nativeGuestSolverNetworkTimingRuns':0,'NFWholeMWork128RuntimePerformanceAdoption':'HOLD'}))
