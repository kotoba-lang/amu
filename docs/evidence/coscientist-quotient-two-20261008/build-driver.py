"""Finite compiler build/fixed-point only. Never work on import."""
from pathlib import Path
import os,json,hashlib,re,subprocess,signal,sys
D=Path(__file__).resolve().parent
H=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(v,m):
 if not v:raise AssertionError(m)
def load(p):return json.loads(Path(p).read_text())
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def main():
 need(len(sys.argv)==2,'exact rootGO argument');gp=Path(sys.argv[1]);g=load(gp);gh=H(gp);pr=load(D/'preregistration.json')
 need(g['authorizeNativeBuild'] is True and type(g['maximumLoaderCalls']) is int and g['maximumLoaderCalls']==10 and g['noRetry'] is True and g['functionalGuestCalls']==0 and g['performanceTiming'] is False,'finite build-only rootGO')
 need(g['driverSHA256']==H(D/'run.py') and g['preregistrationSHA256']==H(D/'preregistration.json'),'frozen driver/prereg GO')
 need(type(g['sourceReviews']) is list and len(g['sourceReviews'])==2,'two exact independent source reviews')
 need(g['outerExecution']=='require_escalated' and g['newCODEContractAccepted'] is True,'explicit root execution/resource contract');need(type(g['approvedSourceReviewHashes']) is list and len(set(g['approvedSourceReviewHashes']))==2 and {v['sha256'] for v in g['sourceReviews']}==set(g['approvedSourceReviewHashes']) and '1c076d47f85b143ef5a5cc5dfc218ebdbbd732f3aa5c3bc8feb574e987aa9c5c' in g['approvedSourceReviewHashes'],'root-selected exact two current source reviews')
 need(g['sourcePinsSHA256']=='f57e7e70ed5b9a3223d3f7f8186a29d302889c1b3caea7d97a129664d3e1685a','exact frozen experimental source')
 S=Path('/Users/junkawasaki/github/workspaces/codex/vector-quotient-two-threeword-source-v1-width');B=Path('/Users/junkawasaki/github/workspaces/codex/vector-emitter-param-native-build-v1-root');out=D/'run-outputs';rows=[];artifacts={};success=False;sources={};compiled={}
 def guard():
  need(H(gp)==gh,'immutable GO')
  need(H(D/'run.py')==g['driverSHA256'] and H(D/'preregistration.json')==g['preregistrationSHA256'],'immutable driver/prereg')
  for p,v in pr['inputs'].items():need(H(p)==v['sha256'] and Path(p).stat().st_size==v['bytes'],'actual pinned input '+p)
  need(H(S/'source-pins.json')==g['sourcePinsSHA256'],'source pin manifest')
  for n,v in load(S/'source-pins.json').items():need(H(S/n)==v['sha256'] and (S/n).stat().st_size==v['bytes'],'all frozen source '+n)
  for v in g['sourceReviews']+[g['driverReview']]:need(H(v['path'])==v['sha256'] and Path(v['path']).stat().st_size==v['bytes'],'exact reviewed source/driver')
  for v in g['sourceReviews']:
   j=load(v['path']);need(j['status']==v['expectedStatus'] and j['status'].startswith('PASS') and j['sourcePinsSHA256']==g['sourcePinsSHA256'],'current parsed helper source qualification')
  j=load(g['driverReview']['path']);need(j['status']==g['driverReview']['expectedStatus'] and j['status'].startswith('PASS') and j['driverSHA256']==g['driverSHA256'] and j['preregistrationSHA256']==g['preregistrationSHA256'],'current parsed finite driver qualification')
  for arm,p in sources.items():need(H(p)==H(S/('unity-quot2-'+arm+'.kotoba')),'copied source unchanged before and after')
  for p,v in compiled.items():need(Path(p).stat().st_size==v['bytes'] and H(p)==v['sha256'],'compiled stage KSEED immutable before/after extract')
  for v in artifacts.values():
   for k in ['native','kseed']:need(H(v[k])==v[k+'SHA256'],'built artifact unchanged')
 guard();need(not out.exists(),'fresh outputs/no rerun');out.mkdir();sources={}
 for arm in ['off','on']:
  p=out/('unity-'+arm+'.kotoba');p.write_bytes((S/('unity-quot2-'+arm+'.kotoba')).read_bytes());p.chmod(0o444);sources[arm]=p
 loader=B/'kexe-loader';initial=Path(pr['initialProducer']);base={k:v for k,v in os.environ.items() if not k.startswith('KEXE_')};env={'KEXE_COMMAND':'1','KEXE_CAP_RESOURCES_35':str(out),'KEXE_STRING_POOL':'268435456','KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216','KEXE_VECTOR_ITEMS':'134217728','KEXE_CPU_SECONDS':'1800','KEXE_WALL_SECONDS':'1800'}
 def call(label,producer,args,arm):
  guard();need(H(sources[arm])==H(S/('unity-quot2-'+arm+'.kotoba')),'source copy exact');need(len(rows)<10,'10call hard cap');cmd=[str(loader),str(producer),'0','0','aarch64','35,37,38,39','--']+args
  r={'index':len(rows)+1,'label':label,'argv':cmd,'kexeEnvironment':env,'removedInheritedKexeKeys':sorted(k for k in os.environ if k.startswith('KEXE_')),'producerSHA256':H(producer),'sourceSHA256':H(sources[arm]),'timeoutSeconds':1810,'state':'started'};rows.append(r);save(out/'attempts.json',rows)
  p=subprocess.Popen(cmd,cwd=out,env=base|env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);timed=False
  try:o,e=p.communicate(timeout=1810)
  except subprocess.TimeoutExpired:timed=True;os.killpg(p.pid,signal.SIGKILL);o,e=p.communicate()
  (out/(label+'.stdout')).write_bytes(o);(out/(label+'.stderr')).write_bytes(e);r.update(state='terminal',returncode=p.returncode,timeout=timed,stdoutSHA256=hashlib.sha256(o).hexdigest(),stderrSHA256=hashlib.sha256(e).hexdigest());save(out/'attempts.json',rows);guard();need(not timed and p.returncode==0 and e==b'' and b':ok true' in o,'first failure '+label);return o
 try:
  for stage in pr['plannedStages']:
   arm='off' if stage.startswith('off') else 'on';producer=initial if stage in ['off-generation1','on-generation1'] else Path(artifacts['on-generation'+str(int(stage[-1])-1)]['native']);kseed=out/(stage+'.kseed');native=out/(stage+'.bin')
   call(stage+'-compile',producer,['compile',str(sources[arm]),'--target','aarch64-macos','--output',str(kseed)],arm)
   need(0<kseed.stat().st_size<=4194560,'bounded compiled container before extract');compiled[str(kseed)]={'bytes':kseed.stat().st_size,'sha256':H(kseed)};save(out/'compiled-containers.json',compiled);guard()
   o=call(stage+'-extract',producer,['extract-native',str(kseed),'--symbol','main','--output',str(native)],arm);xs=re.findall(rb':offset (\d+)\b',o);need(len(xs)==1 and int(xs[0])==0,'sole actual main offset0')
   b=native.read_bytes();need(0<len(b)<=4194304 ,'bounded native blob includingliteral tail');need(kseed.read_bytes()==f'KSEED1 {len(b)} 1\nmain 0 0\n\n'.encode()+b,'exact sole main0 whole payload')
   artifacts[stage]={'native':str(native),'kseed':str(kseed),'bytes':len(b),'nativeSHA256':H(native),'kseedSHA256':H(kseed),'producerSHA256':H(producer),'sourceSHA256':H(sources[arm])};save(out/'artifacts.json',artifacts)
   if stage.startswith('on') and stage not in ['on-generation1','on-generation2']:
    first=artifacts['on-generation2'];need(b==Path(first['native']).read_bytes() and kseed.read_bytes()==Path(first['kseed']).read_bytes(),'ON2 ON3 ON4 wholebytes must match; bootstrapON1 separate/no retry')
  guard();need(len(rows)==10,'exact 10compile/extract calls');save(out/'report.json',{'status':'PASS_FINITE_OFF1_ON_BOOTSTRAP1_AND_SETTLED_GENERATIONS2_3_4_FIXEDPOINT_ONLY','loaderCalls':10,'artifacts':artifacts,'functionalGuestCalls':0,'original19Validated':False,'deepStateValidated':False,'performanceQualified':False,'productAdopted':False});success=True
 except BaseException as e:save(out/'failure.json',{'exception':repr(e),'calls':len(rows),'stopFirstFailure':True,'noRetry':True});raise
 finally:save(out/'terminal.json',{'calls':len(rows),'allCallsClosed':all(r['state']=='terminal' for r in rows),'failure':not success,'noRetry':True,'functionalGuestCalls':0})
if __name__=='__main__':main()
