from pathlib import Path
import json,hashlib,sys,re
from collections import Counter
sys.dont_write_bytecode=True
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'vector-compute-result-output-role-source-v1-census-review';R=D/'run-outputs';O=Path(__file__).resolve().parent;sys.path.insert(0,str(D))
from decode import parse
from census import parse as parse_cq
from artifact import container,counters
def load(p):return json.loads(p.read_text())
inputs={}
def pin(p):
 assert p.is_file()and not p.is_symlink()
 h=hashlib.sha256();n=0
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):n+=len(b);h.update(b)
 return {'bytes':n,'sha256':h.hexdigest()}
def verify(p,v=None):
 z=pin(p)
 if v is not None:assert z==v,str(p)
 inputs[str(p)]=z;return z
def save(p,j):p.write_text(json.dumps(j,indent=2)+'\n')
assert len(sys.argv)==2 and sys.argv[1]=='ROOT_CONFIRMED_TERMINAL_CLOSURE'
gp=W/'vector-compute-result-output-role-go-v1-root/root-go.json';assert verify(gp)['sha256']=='e14ea619290bb3d9191755a2fc0326feed134b177985a653a244a4db2b6bd6ee';go=load(gp)
assert verify(D/'source-pins.json')['sha256']==go['sourcePinsSHA256']=='8bc8142815f26f6de16b0a72ced00984a0a201a4bfabc31ac88efcb6a92cd072'
for n,v in load(D/'source-pins.json').items():verify(D/n,v)
for p,v in load(D/'origin-pins.json').items():verify(Path(p),v)
assert len(load(D/'origin-pins.json'))==763
for p,v in load(D/'input-pins.json').items():verify(Path(p),v)
assert len(go['sourceReviews'])==2 and len({z['path']for z in go['sourceReviews']})==2
for z in go['sourceReviews']:
 p=Path(z['path']);verify(p,{k:z[k]for k in ('bytes','sha256')});j=load(p);assert j['sourcePinsSHA256']==go['sourcePinsSHA256']and j['status']=='PASS_SOURCE_ONLY_DECLARED_OUTPUT_ROLE_PILOT6'
pr=load(D/'pilot-preregistration.json')
for z in pr['proofs']:
 p=Path(z['path']);verify(p,{k:z[k]for k in ('bytes','sha256')});assert load(p)['status']==z['status']
K=W/'vector-compute-current19-query-census-source-v1-controls';new=(D/'helpers.kotoba').read_text();old=(K/'helpers.kotoba').read_text()
for name in ('41','unity'):
 assert (D/(name+'-result.kotoba')).read_text().replace(new,old).encode()==(K/(name+'-census.kotoba')).read_bytes()
for p,v in load(R/'generated-pins.json').items():verify(Path(p),v)
term=load(R/'terminal.json');verify(R/'terminal.json');rows=load(R/'attempts.json');verify(R/'attempts.json');assert term=={'calls':6,'allCallsClosed':True,'images':2,'failure':False}and not(R/'failure.json').exists()and len(rows)==6
assert go['maxCalls']==6 and go['compileAuthorized']and not go['guestAuthorized']and not go['timingAuthorized']
env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':str(R),'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_COMMAND':'1','KEXE_CAP_RESOURCES_35':str(R),'KEXE_CPU_SECONDS':'1800','KEXE_WALL_SECONDS':'1800','KEXE_STRING_POOL':'268435456','KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216','KEXE_VECTOR_ITEMS':'134217728','KEXE_ARENA_USE':'1','KEXE_FUEL':'off'}
expected=[('observer-build',pr['producer']['path'],['compile',str(R/'sources/unity-result.kotoba'),'--target','aarch64-macos','--output',str(R/'observer.kseed')]),('observer-extract',pr['producer']['path'],['extract-native',str(R/'observer.kseed'),'--symbol','main','--output',str(R/'observer.bin')])]
for e in pr['entries']:
 p=R/'ports'/e['workload'];expected.extend([(e['workload'],str(R/'observer.bin'),['compile',str(R/'sources'/(e['workload']+'.kotoba')),'--target','aarch64-macos','--output',str(p/'image.kseed')]),(e['workload'],str(R/'observer.bin'),['extract-native',str(p/'image.kseed'),'--symbol',e['symbol'],'--output',str(p/'native.bin')])])
for i,r in enumerate(rows):
 label,producer,args=expected[i];assert r['index']==i+1 and r['label']==label and r['argv']==[pr['loader']['path'],producer,'0','0','aarch64','35,37,38,39','--',*args]
 assert r['effectiveEnvironment']==env and r['kexeEnvironment']=={k:v for k,v in env.items()if k.startswith('KEXE_')}
 assert r['state']=='terminal'and r['processStarted']and r['processReaped']and r['returncode']==0 and not r['terminationReason']and not r['cleanupErrors']
 op=Path(r['stdoutPath']);ep=Path(r['stderrPath']);verify(op,r['stdout']);verify(ep,r['stderr']);assert op.stat().st_size<=67108864 and ep.stat().st_size<=1048576
 c=counters(ep.read_bytes());assert c==r['arenaCounters']and c['status']=='valid'and c['entireStderrIsCounterLine']
 ok=False;offsets=[]
 with op.open('rb')as f:
  for line in iter(lambda:f.readline(65537),b''):
   assert len(line)<=65536 and b':ok false'not in line;ok|=b':ok true'in line;offsets+=re.findall(rb':offset (\d+)\b',line)
 assert ok
 if args[0]=='extract-native':assert offsets==[str(0 if i==1 else pr['entries'][(i-2)//2]['offset']).encode()]
ex,body=container((R/'observer.kseed').read_bytes());assert ex==[{'name':'main','offset':0,'arity':0}]and body==(R/'observer.bin').read_bytes()
images=load(R/'images.json');verify(R/'images.json');assert len(images)==2;cohorts=[];compares=[];hitContexts=Counter();changes=Counter()
for i,e in enumerate(pr['entries']):
 n=e['workload'];p=R/'ports'/n
 for file,k in [('image.kseed','oldContainer'),('native.bin','oldNative')]:verify(p/file,{x:e[k][x]for x in ('bytes','sha256')})
 verify(R/'sources'/(n+'.kotoba'),{k:e['source'][k]for k in ('bytes','sha256')});assert (p/'native.offset').read_text()==str(e['offset'])+'\n'
 ex,body=container((p/'image.kseed').read_bytes());assert body==(p/'native.bin').read_bytes()and {'name':e['symbol'],'offset':e['offset'],'arity':1}in ex
 raw=(p/(str(3+2*i)+'.stdout')).read_bytes();cr=parse(raw);cq=parse_cq(raw);saved=load(p/'frequency.json');verify(p/'frequency.json');assert saved['declaredOutput']==cr and all(cq[k]==saved[k]for k in cq)and images[i]['frequency']==saved
 assert cr['calls']==cq['queryCalls']and cq['unsupported']==0
 # A separately decoded raw CR record vector checks decoder's field mapping.
 resultLines=[[int(x)for x in line.split()[1:]]for line in raw.decode().splitlines()if line.startswith('CR-RESULT ')]
 assert resultLines==[q['result']for q in cr['queries']]
 last={};previous=None;local=Counter()
 for index,q in enumerate(cr['queries']):
  e0,x=q['entry'],q['exit'];sub=(q['activation'],e0[0]);hit=e0[6]==1 and e0[7:11]==e0[11:15]and x[4]==1
  oldproj={'statusSupportPoison':x[3:4]+x[5:7],'orderedEdges':[edge[:5]+edge[10:]for edge in q['edges']]}
  exact=json.dumps(oldproj,sort_keys=True,separators=(',',':')).encode()
  if hit:
   hitContexts['existingHitQueries']+=1
   if previous and q['result'][5:]==previous['result'][5:]:hitContexts['summaryEqualsPreviousGlobalQuery']+=1
   if sub in last and q['result'][5:]!=last[sub][0]['result'][5:]:hitContexts['summaryDiffersPriorSameSubject']+=1
  elif sub in last:
   assert e0[7:11]!=e0[11:15];prior,priorOld=last[sub]
   changedVW=[k for k in range(16)if q['wvf'][k]!=prior['wvf'][k]];changedFN=[k for k in range(16)if q['fnf'][k]!=prior['fnf'][k]];changedSummary=[k+9 for k in range(6)if q['result'][5+k]!=prior['result'][5+k]]
   d={'workload':n,'activation':sub[0],'fn':sub[1],'oldProjectionEqual':exact==priorOld,'expandedRawProjectionEqual':q['canonicalProjectionBytes']==prior['canonicalProjectionBytes'],'supportedSuccessfulPair':q['supportedSuccessful']and prior['supportedSuccessful'],'changedVWFieldIndices':changedVW,'changedFNFieldIndices':changedFN,'changedSummaryControlIndices':changedSummary,'entryBoundFields6to9Changed':[k for k in changedVW if k in range(6,10)]}
   compares.append(d);local['changedBoundMiss']+=1;local['oldProjectionEqual']+=int(d['oldProjectionEqual']);local['expandedRawProjectionEqual']+=int(d['expandedRawProjectionEqual']);changes.update('VW'+str(k)for k in changedVW);changes.update('FN'+str(k)for k in changedFN);changes.update('control'+str(k)for k in changedSummary)
  last[sub]=(q,exact);previous=q
 cohorts.append({'workload':n,'queries':cr['calls'],'supportedSuccessful':cr['supportedSuccessful'],'existingMemoHits':cq['existingMemoHits'],'comparisons':dict(local)})
actual=load(R/'report.json');verify(R/'report.json');assert actual['status']=='PASS_ACTUAL_DECLARED_OUTPUT_ROLE_CRC32_SLRE_PILOT6_BYTE_IDENTITY_ONLY'and actual['queryCalls']==sum(x['queries']for x in cohorts)==161
r={'status':'PASS_SAVED_RAW_AUTHOR_RECHECK_DECLARED_OUTPUT_ROLE_PILOT6_BYTE_IDENTITY_ONLY','sourcePinsSHA256':go['sourcePinsSHA256'],'GO_SHA256':inputs[str(gp)]['sha256'],'calls':6,'images':2,'raw17Counters':6,'allCallsClosed':True,'wholeOriginalKSEEDNativeExportIdentity':True,'originalAnalyzerSourceExactReversal':True,'cohorts':cohorts,'changedMissComparisons':compares,'changedCapturedFields':dict(changes),'memoHitGlobalSummaryChecks':dict(hitContexts),'interpretation':'Expanded payload is a raw captured state projection. Subject VW fields6..9 include input/aggregate bounds. Original memo hit performs replay without run-fn/reset-flow, so global controls9..14 can remain from the preceding different subject. Captured differences are not automatically semantic result changes; no unproved exclusions are approved.','futureOutputRoleNeed':'Own each query summary/certificate result by source-defined lifetime and saved-result provenance, and separately represent ordered contributions and current-target aggregate merges before claiming semanticResult/reapplication.','authorParticipation':'Reviewer authored this observer, source preparation, decoder and pilot driver; this is a disclosed saved-raw author recheck, not an independent author-free audit. Root and width reviewers supply independent evidence.','fullResultCIDQualified':False,'fullComputeCIDQualified':False,'outputRoleClosed':False,'readClosureQualified':False,'semanticReapplicationQualified':False,'original19Qualified':False,'downstreamSkips':0,'newQuerySkips':0,'C2':False,'performanceClaim':False,'nativeCallsByReviewer':0,'SSHCallsByReviewer':0}
save(O/'comparisons.json',compares);save(O/'report.json',r);save(O/'input-pins.json',inputs);save(O/'source-pins.json',{p.name:pin(p)for p in sorted(O.iterdir())if p.is_file()and p.name!='source-pins.json'});print(json.dumps({'report':pin(O/'report.json'),'cohorts':cohorts,'hitContext':dict(hitContexts)}))
