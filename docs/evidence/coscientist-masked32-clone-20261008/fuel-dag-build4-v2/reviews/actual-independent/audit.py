"""Saved-file audit only. No driver import, subprocess, native or SSH invocation."""
from pathlib import Path
import json,hashlib,re,stat
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'vector-fuel-scalar-dag-compiler-build4-plan-v2-width';O=D/'run-outputs';A=Path(__file__).resolve().parent;G=W/'vector-fuel-scalar-dag-compiler-build4-go-v2-root/root-go.json'
def need(x,m):
 if not x:raise AssertionError(m)
def load(p):return json.loads(p.read_bytes())
def receipt(p):
 s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink(),'regular:'+str(p));b=p.read_bytes();need(s.st_size==len(b),'size');return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
pins={}
def bind(p,z=None):
 p=Path(p);v=receipt(p)
 if z is not None:need(v=={k:z[k]for k in ['bytes','sha256']},'pin:'+str(p))
 pins[str(p)]=v;return p
pr=load(bind(D/'preregistration.json'));g=load(bind(G));sp=load(bind(D/'source-pins.json'));ip=load(bind(D/'input-pins.json'))
for n,z in sp.items():bind(D/n,z)
need(len(ip)==1700 and sum(z['bytes']for z in ip.values())==362671770,'exact closure')
for p,z in ip.items():bind(p,z)
need(g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==4 and g['noRetry']is True and g['outerExecution']=='require_escalated','GO contract')
need(all(g[k]is False for k in ['generatedCompilerExecutionAuthorized','workloadGuestAuthorized','timingAuthorized']),'GO scope')
for k,p in [('driverSHA256',D/'run.py'),('driverSourcePinsSHA256',D/'source-pins.json'),('preregistrationSHA256',D/'preregistration.json'),('inputPinsSHA256',D/'input-pins.json')]:need(g[k]==receipt(p)['sha256'],'GO binding:'+k)
need(g['sourcePinsSHA256']==pr['sourcePinsSHA256']and g['outputRoot']==str(O),'emitter/output GO')
S=Path(pr['sourceDirectory']);need(receipt(bind(S/'source-pins.json'))['sha256']==pr['sourcePinsSHA256'],'emitter registry')
for n,z in load(S/'source-pins.json').items():bind(S/n,z)
for group,status in [('sourceReviews',pr['sourceReviewStatus']),('driverReviews',pr['driverReviewStatus'])]:
 need(len(g[group])==2 and len({q['path']for q in g[group]})==2,'two receipts')
 for q in g[group]:
  r=load(bind(q['path'],q));need(r['status']==status,'receipt status')
  if group=='sourceReviews':need(r['sourcePinsSHA256']==g['sourcePinsSHA256'],'review emitter')
  else:need(all(r[k]==g[k]for k in ['driverSourcePinsSHA256','driverSHA256','preregistrationSHA256']),'review driver')
t=load(bind(O/'terminal.json'));need(t['allChildrenClosed']is True,'root closure required')
rows=load(bind(O/'attempts.json'));report=load(bind(O/'report.json'));images=load(bind(O/'images.json'));gen=load(bind(O/'generated-pins.json'))
need(t==dict(loaderCalls=4,allChildrenClosed=True,failure=False),'terminal4 success');need(not(O/'failure.json').exists(),'no failure record')
need(len(rows)==4 and len(images)==2,'four/two')
for p,z in gen.items():bind(p,z)
fields=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes']
env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':str(O),'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_COMMAND':'1','KEXE_CAP_RESOURCES_35':str(O),'KEXE_STRING_POOL':'268435456','KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216','KEXE_VECTOR_ITEMS':'134217728','KEXE_CPU_SECONDS':'1800','KEXE_WALL_SECONDS':'1800','KEXE_FUEL':'off','KEXE_ARENA_USE':'1'}
counters=[]
for i,(r,label) in enumerate(zip(rows,['OFF-compile','OFF-extract','ON-compile','ON-extract'])):
 need(r['index']==i+1 and r['label']==label and r['state']=='terminal'and r['spawned']is True and r['reaped']is True and r['returncode']==0 and r['error']is None and r['terminationReason']is None and r['cleanupExceptions']==[],'terminal row')
 need(r['effectiveEnvironment']==env and r['timeoutSeconds']==1810,'literal env/wall')
 arm,mode=label.split('-');args=['compile',str(O/(arm+'.kotoba')),'--target','aarch64-macos','--output',str(O/(arm+'.kseed'))]if mode=='compile'else['extract-native',str(O/(arm+'.kseed')),'--symbol','main','--output',str(O/(arm+'.bin'))]
 need(r['argv']==[pr['loader'],pr['producer'],'0','0','aarch64','35,37,38,39','--',*args],'exact argv')
 raw={}
 for stream in ['stdout','stderr']:
  p=bind(O/(label+'.'+stream),r[stream]);need(p.stat().st_size<=1048576,'stream bound');raw[stream]=p.read_bytes()
 need(b':ok true'in raw['stdout']and b':ok false'not in raw['stdout'],'accepted')
 if mode=='extract':need(re.findall(rb':offset ([0-9]+)\b',raw['stdout'])==[b'0'],'main0 extract')
 pattern=('KEXE_ARENA_USE {'+' '.join(':'+f+' ([0-9]+)'for f in fields)+'}\n').encode();m=re.fullmatch(pattern,raw['stderr']);need(m is not None and all(len(x)<=20 for x in m.groups()),'entire raw17')
 u=dict(zip(fields,map(int,m.groups())));need(all(0<=x<2**64 for x in u.values()),'u64');need(u['heap-bytes']==16*u['pairs']+u['string-pool-bytes']+16*u['vectors']+8*u['vector-items'],'heap accounting')
 for f,cap in [('pairs',16777216),('string-pool-bytes',268435456),('vectors',4194304),('vector-items',134217728)]:need(u[f]<=cap,'arena bounds')
 need(r['counterObservation']==dict(status='valid',values=u,entireStderrIsCounterLine=True),'counter correspondence');counters.append(dict(label=label,values=u))
for im,arm,src in zip(images,['OFF','ON'],[pr['parentSource'],pr['ONSource']]):
 need(im['arm']==arm and im['offset']==im['arity']==0 and im['generatedCompilerExecuted']is False,'image metadata')
 for k in ['source','container','native']:bind(im[k]['path'],im[k])
 need(Path(im['source']['path']).read_bytes()==Path(src).read_bytes(),'whole copied source')
 b=Path(im['container']['path']).read_bytes();need(len(b)<=4194560,'container cap');m=re.match(rb'KSEED1 ([1-9][0-9]*) 1\nmain 0 0\n\n',b);need(m is not None,'sole export');payload=b[m.end():];need(0<len(payload)<=4194304 and len(payload)==int(m[1]),'whole payload');need(payload==Path(im['native']['path']).read_bytes(),'native whole payload')
 if arm=='OFF':need(b==Path(pr['OFFBaselineContainer']).read_bytes()and payload==Path(pr['OFFBaselineNative']).read_bytes(),'whole OFF baseline')
need(report['status']=='COMPLETE_FUEL_DAG_COMPILER_BUILD4_IDENTITY_ONLY'and report['loaderCalls']==4 and report['images']==images and report['OFFWholeBaselineContainerNativeEqual']is True,'runner report')
need(report['rootGOSHA256']==receipt(G)['sha256']and report['sourcePinsSHA256']==g['sourcePinsSHA256'],'runner bindings')
need(report['ONNativeBytes']==images[1]['native']['bytes']and report['ONMinusOFFNativeBytes']==images[1]['native']['bytes']-images[0]['native']['bytes'],'size arithmetic')
need(report['generatedCompilerExecuted']is False and report['fixedpointQualified']is False and report['performanceQualified']is False,'claims boundary')
result=dict(status='PASS_INDEPENDENT_SAVED_RAW_FUEL_DAG_BUILD4_IDENTITY_ONLY',sourcePinsSHA256=g['sourcePinsSHA256'],driverSourcePinsSHA256=g['driverSourcePinsSHA256'],driverSHA256=g['driverSHA256'],preregistrationSHA256=g['preregistrationSHA256'],rootGO=dict(path=str(G),**receipt(G)),inputClosure=dict(files=1700,logicalBytes=362671770),loaderCalls=4,allChildrenClosed=True,failure=False,OFFWholeBaselineContainerNativeEqual=True,images=images,raw17Counters=counters,reviewParticipation=dict(driverAuthor=False,priorDriverAndEmitterSourceReviewer=True),nativeCallsByReviewer=0,SSHCallsByReviewer=0,generatedCompilerExecuted=False,fixedpointQualified=False,performanceQualified=False,resourceContract='new ON prospective bounded reserve; actual build4 success only')
(A/'input-pins.json').write_text(json.dumps(pins,indent=2)+'\n');(A/'report.json').write_text(json.dumps(result,indent=2)+'\n')
(A/'source-pins.json').write_text(json.dumps({p.name:receipt(p)for p in sorted(A.iterdir())if p.is_file()and p.name!='source-pins.json'},indent=2)+'\n')
print(json.dumps({n:receipt(A/n)for n in ['report.json','source-pins.json']}))
