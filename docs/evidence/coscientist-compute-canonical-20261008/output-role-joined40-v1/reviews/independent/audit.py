from pathlib import Path
import json,hashlib,sys,re,stat
from collections import Counter
sys.dont_write_bytecode=True
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'vector-compute-result-output-role-continuation34-source-v1-census-review';P=W/'vector-compute-result-output-role-source-v1-census-review';O=Path(__file__).resolve().parent
sys.path.insert(0,str(S))
from decode import parse as crparse
from census import parse as cqparse
from artifact import container,counters
ip={}
def j(p):return json.loads(Path(p).read_text())
def pin(p,v=None):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size<=536870912
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 assert s==p.lstat();z={'bytes':s.st_size,'sha256':h.hexdigest()}
 if v is not None:assert z=={k:v[k]for k in ('bytes','sha256')},str(p)
 ip[str(p)]=z;return z
def save(n,v):(O/n).write_text(json.dumps(v,indent=2)+'\n')
assert len(sys.argv)==2 and sys.argv[1]=='SAVED_RAW_ONLY_ROOT_CONFIRMED_CLOSED'
orig=j(S/'origin-pins.json');assert len(orig)==828 and sum(v['bytes']for v in orig.values())==312917985
for p,v in orig.items():pin(p,v)
cohorts=[];comparisons=[];hit=Counter();changed=Counter();allnames=[];rawcalls=0
for D,prfile,gopath,total,build in [(P,'pilot-preregistration.json',W/'vector-compute-result-output-role-go-v1-root/root-go.json',6,2),(S,'preregistration.json',W/'vector-compute-result-output-role-continuation34-go-v1-root/root-go.json',34,0)]:
 R=D/'run-outputs';pr=j(D/prfile);pin(D/prfile);go=j(gopath);pin(gopath)
 assert pin(D/'source-pins.json')['sha256']==go['sourcePinsSHA256']
 for n,v in j(D/'source-pins.json').items():pin(D/n,v)
 for p,v in j(D/'input-pins.json').items():pin(p,v)
 assert go['compileAuthorized'] is True and go['guestAuthorized'] is False and go['timingAuthorized'] is False and go['maxCalls']==total
 if D==S:assert go['status']==pr['rootGOStatus']
 assert len(go['sourceReviews'])==2
 for z in go['sourceReviews']:
  pin(z['path'],z);rv=j(z['path']);assert rv['sourcePinsSHA256']==go['sourcePinsSHA256'] and rv['status']==pr['sourceReviewStatus']
 for z in pr['proofs']:pin(z['path'],z);assert j(z['path'])['status']==z['status']
 for p,v in j(R/'generated-pins.json').items():pin(p,v)
 rows=j(R/'attempts.json');pin(R/'attempts.json');term=j(R/'terminal.json');pin(R/'terminal.json');assert term=={'calls':total,'allCallsClosed':True,'images':len(pr['entries']),'failure':False}and len(rows)==total and not(R/'failure.json').exists()
 env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':str(R),'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_COMMAND':'1','KEXE_CAP_RESOURCES_35':str(R),'KEXE_CPU_SECONDS':'1800','KEXE_WALL_SECONDS':'1800','KEXE_STRING_POOL':'268435456','KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216','KEXE_VECTOR_ITEMS':'134217728','KEXE_ARENA_USE':'1','KEXE_FUEL':'off'}
 expected=[]
 if build:expected=[('observer-build',pr['producer']['path'],['compile',str(R/'sources/unity-result.kotoba'),'--target','aarch64-macos','--output',str(R/'observer.kseed')],None),('observer-extract',pr['producer']['path'],['extract-native',str(R/'observer.kseed'),'--symbol','main','--output',str(R/'observer.bin')],0)]
 for e in pr['entries']:
  n=e['workload'];p=R/'ports'/n;producer=str(R/'observer.bin')if build else pr['producer']['path']
  expected.extend([(n,producer,['compile',str(R/'sources'/(n+'.kotoba')),'--target','aarch64-macos','--output',str(p/'image.kseed')],None),(n,producer,['extract-native',str(p/'image.kseed'),'--symbol',e['symbol'],'--output',str(p/'native.bin')],e['offset'])])
 for idx,(r,ex)in enumerate(zip(rows,expected),1):
  label,producer,args,offset=ex;assert r['index']==idx and r['label']==label and r['argv']==[pr['loader']['path'],producer,'0','0','aarch64','35,37,38,39','--',*args]
  assert r['effectiveEnvironment']==env and r['kexeEnvironment']=={k:v for k,v in env.items()if k.startswith('KEXE_')}
  assert r['state']=='terminal' and r['processStarted'] is True and r['processReaped'] is True and type(r['pid'])is int and r['pid']>0 and r['returncode']==0 and not r['terminationReason'] and not r['cleanupErrors']
  op=Path(r['stdoutPath']);ep=Path(r['stderrPath']);pin(op,r['stdout']);pin(ep,r['stderr']);assert op.stat().st_size<=67108864 and ep.stat().st_size<=1048576
  c=counters(ep.read_bytes());assert c==r['arenaCounters']and c['status']=='valid'and c['entireStderrIsCounterLine'];rawcalls+=1
  offsets=[];ok=False
  with op.open('rb')as f:
   for line in iter(lambda:f.readline(65537),b''):
    assert len(line)<=65536 and b':ok false'not in line;ok|=b':ok true'in line;offsets+=re.findall(rb':offset (\d+)\b',line)
  assert ok
  if offset is not None:assert offsets==[str(offset).encode()]
 images=j(R/'images.json');pin(R/'images.json');assert len(images)==len(pr['entries'])
 for i,e in enumerate(pr['entries']):
  n=e['workload'];allnames.append(n);p=R/'ports'/n
  for file,k in [('image.kseed','oldContainer'),('native.bin','oldNative')]:pin(p/file,e[k]);assert(p/file).read_bytes()==Path(e[k]['path']).read_bytes()
  pin(R/'sources'/(n+'.kotoba'),e['source']);pin(p/'native.offset');assert(p/'native.offset').read_text()==str(e['offset'])+'\n'
  exports,body=container((p/'image.kseed').read_bytes());assert body==(p/'native.bin').read_bytes() and {'name':e['symbol'],'offset':e['offset'],'arity':1}in exports
  assert images[i]['exports']==exports and images[i]['native']==pin(p/'native.bin')and images[i]['container']==pin(p/'image.kseed')and images[i]['source']==pin(R/'sources'/(n+'.kotoba'))and images[i]['offset']==e['offset']
  raw=(p/(str(build+1+2*i)+'.stdout')).read_bytes();cq=cqparse(raw);cr=crparse(raw);saved=j(p/'frequency.json');pin(p/'frequency.json');assert saved['declaredOutput']==cr and all(saved[k]==cq[k]for k in cq)and images[i]['frequency']==saved and cq['queryCalls']==cr['calls']and cq['unsupported']==0
  assert [[int(v)for v in l.split()[1:]]for l in raw.decode().splitlines()if l.startswith('CR-RESULT ')]==[q['result']for q in cr['queries']]
  last={};previous=None;local=Counter()
  for qi,q in enumerate(cr['queries']):
   e0,x=q['entry'],q['exit'];sub=(q['activation'],e0[0]);isHit=e0[6]==1 and e0[7:11]==e0[11:15]and x[4]==1
   old={'statusSupportPoison':x[3:4]+x[5:7],'orderedEdges':[edge[:5]+edge[10:]for edge in q['edges']]};oldb=json.dumps(old,sort_keys=True,separators=(',',':')).encode()
   if isHit:
    hit['existingHitQueries']+=1
    if previous and q['result'][5:]==previous['result'][5:]:hit['summaryEqualsPreviousGlobalQuery']+=1
    if sub in last and q['result'][5:]!=last[sub][0]['result'][5:]:hit['summaryDiffersPriorSameSubject']+=1
   elif sub in last:
    assert e0[7:11]!=e0[11:15];prior,pb=last[sub];vw=[k for k in range(16)if q['wvf'][k]!=prior['wvf'][k]];fn=[k for k in range(16)if q['fnf'][k]!=prior['fnf'][k]];summary=[k+9 for k in range(6)if q['result'][5+k]!=prior['result'][5+k]]
    d={'workload':n,'queryOrdinal':qi,'activation':sub[0],'fn':sub[1],'oldProjectionEqual':oldb==pb,'expandedRawProjectionEqual':q['canonicalProjectionBytes']==prior['canonicalProjectionBytes'],'supportedSuccessfulPair':q['supportedSuccessful']and prior['supportedSuccessful'],'changedVWFieldIndices':vw,'changedFNFieldIndices':fn,'changedSummaryControlIndices':summary,'entryBoundFields6to9Changed':[k for k in vw if 6<=k<=9]};comparisons.append(d);local['changedBoundMiss']+=1
    for k in ('oldProjectionEqual','expandedRawProjectionEqual','supportedSuccessfulPair'):local[k]+=int(d[k])
    changed.update('VW'+str(k)for k in vw);changed.update('FN'+str(k)for k in fn);changed.update('control'+str(k)for k in summary)
   last[sub]=(q,oldb);previous=q
  cohorts.append({'workload':n,'queries':cr['calls'],'supportedSuccessful':cr['supportedSuccessful'],'orderedEdgeRecords':sum(len(q['edges'])for q in cr['queries']),'supportDrops':sum(q['result'][2]==0 for q in cr['queries']),'existingMemoHits':cq['existingMemoHits'],'sameTargetModeRepeats':cq['sameTargetModeRepeats'],'fourBoundProjectionRepeats':cq['fourBoundProjectionRepeats'],'comparisons':dict(local)})
 actual=j(R/'report.json');pin(R/'report.json');assert actual['calls']==total and actual['images']==len(pr['entries'])and actual['queryCalls']==sum(x['queries']for x in cohorts[-len(pr['entries']):])
# Canonical matrix and observer whole payload identity.
m=Path('/Users/junkawasaki/github/wt/amu-seed17/bench/embench/comparison-matrix.json');pin(m);matrix=j(m)['entries'];assert len(allnames)==19 and len(set(allnames))==19 and set(allnames)=={e['workload']for e in matrix}
for D,prfile in [(P,'pilot-preregistration.json'),(S,'preregistration.json')]:
 for e in j(D/prfile)['entries']:
  z=next(v for v in matrix if v['workload']==e['workload']);assert e['symbol']==z['symbol']and e['source']['sha256']==z['expectedSourceSha256']
ex,body=container((P/'run-outputs/observer.kseed').read_bytes());assert ex==[{'name':'main','offset':0,'arity':0}]and body==(P/'run-outputs/observer.bin').read_bytes()
assert rawcalls==40 and sum(x['queries']for x in cohorts)==4212
stats={k:sum(int(d[k])for d in comparisons)for k in ('oldProjectionEqual','expandedRawProjectionEqual','supportedSuccessfulPair')};stats['changedBoundMiss']=len(comparisons)
r={'status':'PASS_INDEPENDENT_ACTUAL_DECLARED_OUTPUT_ROLE_JOINED40_BYTE_IDENTITY_ONLY','sourcePinsSHA256':pin(S/'source-pins.json')['sha256'],'newClosedCalls':34,'retainedClosedCalls':6,'joinedClosedCalls':40,'originalWorkloads':19,'newImages':17,'raw17CounterReceipts':40,'queryCalls':4212,'cohorts':cohorts,'changedBoundComparisons':stats,'changedCapturedFields':dict(changed),'memoHitGlobalSummaryChecks':dict(hit),'wholeOriginalContainerNativeExportsExact':True,'orderedContributionPairingStrict':True,'interpretation':'Expanded raw projection includes VW input/aggregate fields6..9 and global scratch controls9..14. Equality/difference is captured-state diagnostic only. Existing hits replay ordered edge contributions without reset-flow/run-fn; global controls may retain preceding other-subject values. No unproven field exclusions, semantic ResultCID correspondence, or query-owned summary lifetime is approved.','participation':'Reviewer provided prior independent SOURCE review of continuation34 and authored earlier separate C1 diagnostics/optimizer work; current output-role observer/decoder/driver authored by another agent. This is a saved-raw audit, not independent OS execution tracing; root supplied terminal session closure.','fullComputeCIDQualified':False,'fullResultCIDQualified':False,'outputRoleClosed':False,'readClosureQualified':False,'semanticReapplicationQualified':False,'newQuerySkips':0,'C2':False,'performanceClaim':False,'officialScore':False,'nativeCallsByReviewer':0,'SSHCallsByReviewer':0}
save('comparisons.json',comparisons);save('report.json',r);save('input-pins.json',ip);save('source-pins.json',{p.name:pin(p)for p in sorted(O.iterdir())if p.is_file()and p.name!='source-pins.json'});print(json.dumps({'report':pin(O/'report.json'),'inputPins':pin(O/'input-pins.json'),'comparisons':stats,'hits':dict(hit)}))
