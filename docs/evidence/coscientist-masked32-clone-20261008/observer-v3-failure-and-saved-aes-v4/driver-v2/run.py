"""SOURCE-only registered observer6 diagnostic. Import inert; root GO required."""
from pathlib import Path
import os,sys,json,hashlib,re,stat,subprocess,signal,time
D=Path(__file__).resolve().parent;O=D/'run-outputs'
H=lambda b:hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def need(c,s):
 if not c:raise AssertionError(s)
def regular(p,maxbytes=None):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode) and not p.is_symlink(),'regular file '+str(p));need(maxbytes is None or s.st_size<=maxbytes,'file cap '+str(p));return p

def pin(p,v):
 p=regular(p,v['bytes']);need(p.stat().st_size==v['bytes'],'pin size '+str(p));h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 need(h.hexdigest()==v['sha256'],'pin hash '+str(p));return p

def receipt(p):
 p=regular(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':H(p.read_bytes())}

def container(b):
 need(len(b)<=4194560 and b.count(b'\n\n')>=1,'bounded container');head,payload=b.split(b'\n\n',1);ls=head.decode('ascii').split('\n');m=re.fullmatch(r'KSEED1 ([0-9]+) ([0-9]+)',ls[0]);need(m is not None,'KSEED1 header');n,k=map(int,m.groups());need(0<n<=4194304 and len(payload)==n and len(ls)==k+1 and 1<=k<=128,'header lengths');exports=[]
 for line in ls[1:]:
  m=re.fullmatch(r'([A-Za-z0-9_-]+) ([0-9]+) ([0-9]+)',line);need(m is not None,'export syntax');s,off,a=m.groups();off=int(off);a=int(a);need(off%4==0 and off+4<=n and 0<=a<=32,'export range');exports.append({'name':s,'offset':off,'arity':a})
 need(len({r['name']for r in exports})==k,'unique exports');return exports,payload

FIELDS=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes']
PAT=re.compile(('KEXE_ARENA_USE {'+' '.join(':'+k+' ([0-9]+)'for k in FIELDS)+'}\n').encode())
def counters(err):
 matches=[PAT.fullmatch(line)for line in err.splitlines(keepends=True)];matches=[m for m in matches if m is not None]
 if len(matches)!=1:return {'status':'unavailable-or-not-exactly-one-counter-line','matchingLines':len(matches),'values':None,'entireStderrIsCounterLine':False}
 u=dict(zip(FIELDS,map(int,matches[0].groups())));valid=all(type(v)is int and 0<=v<2**64 for v in u.values()) and u['heap-bytes']==16*u['pairs']+u['string-pool-bytes']+16*u['vectors']+8*u['vector-items'] and u['pairs']<=16777216 and u['string-pool-bytes']<=268435456 and u['vectors']<=4194304 and u['vector-items']<=134217728
 return {'status':'valid'if valid else 'invalid','matchingLines':1,'values':u,'entireStderrIsCounterLine':PAT.fullmatch(err)is not None}

class Ledger:
 def __init__(self,env):self.env=env;self.rows=[]
 def call(self,label,argv):
  need(len(self.rows)<6,'six child cap');r={'index':len(self.rows)+1,'label':label,'argv':argv,'effectiveEnvironment':self.env,'timeoutSeconds':1810,'state':'started'};self.rows.append(r);save(O/'attempts.json',self.rows);p=None;failure=cleanup=None;out=O/(label+'.stdout');err=O/(label+'.stderr')
  with out.open('xb')as of,err.open('xb')as ef:
   try:
    p=subprocess.Popen(argv,cwd=O,env=self.env,stdout=of,stderr=ef,start_new_session=True);deadline=time.monotonic()+1810
    while p.poll()is None:
     need(time.monotonic()<deadline,'child timeout');need(out.stat().st_size<=67108864 and err.stat().st_size<=1048576,'raw file decode cap exceeded');time.sleep(.05)
    p.wait(timeout=30)
   except BaseException as ex:
    failure=repr(ex)
    if p is not None:
     try:
      try:os.killpg(p.pid,signal.SIGKILL)
      except ProcessLookupError:pass
      p.wait(timeout=30)
     except BaseException as ex2:cleanup=repr(ex2)
  closed=p is None or p.returncode is not None;oi=receipt_stream(out);ei=receipt_stream(err);eraw=err.read_bytes()if ei['bytes']<=1048576 else None;obs=counters(eraw)if eraw is not None else {'status':'stderr-over-decode-cap','values':None}
  r.update(state='terminal'if closed else 'unclosed',returncode=None if p is None else p.returncode,spawnSucceeded=p is not None,failure=failure,cleanupException=cleanup,stdout=oi,stderr=ei,counterObservation=obs);save(O/'attempts.json',self.rows)
  need(closed and failure is None and cleanup is None and p is not None and p.returncode==0,'child first failure '+label);need(oi['bytes']<=67108864 and ei['bytes']<=1048576,'raw cap after closure');raw=out.read_bytes();need(b':ok true'in raw and b':ok false'not in raw,'normal success '+label);need(obs['status']=='valid'and obs['entireStderrIsCounterLine'],'exact 17 normal counters '+label);return raw

def receipt_stream(p):
 p=regular(p);h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return {'path':str(p),'bytes':p.stat().st_size,'sha256':h.hexdigest()}

def main():
 need(len(sys.argv)==2,'root GO argument');gp=regular(sys.argv[1],1048576);gb=gp.read_bytes();g=json.loads(gb);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');cl=load(D/'input-closure.json');need(pr['secondObserverReviewBound']is True,'second observer SOURCE acceptance absent')
 need(type(g['driverCorrectionVersion'])is int and g['driverCorrectionVersion']==pr['driverCorrectionVersion']==2,'fresh V2 GO')
 need(g['status']==pr['rootGOStatus']and g['sourcePinsSHA256']==H((D/'source-pins.json').read_bytes())and type(g['maximumChildCalls'])is int and g['maximumChildCalls']==6 and g['noRetry']is True and g['workloadGuestAuthorized']is False and g['timingAuthorized']is False,'specific finite6 GO')
 allpins=dict(cl)
 def addref(e):
  v={k:e[k]for k in ['bytes','sha256']};need(e['path']not in allpins or allpins[e['path']]==v,'pin conflict');allpins[e['path']]=v;return e
 need(type(g['sourceReviews'])is list and len(g['sourceReviews'])==2 and len({e['path']for e in g['sourceReviews']})==2,'two driver reviews')
 for e in g['sourceReviews']:
  q=load(pin(e['path'],e));need(q['status']==pr['driverSourceReviewStatus']and q['sourcePinsSHA256']==g['sourcePinsSHA256'],'driver review current finite6');need(type(q['driverCorrectionVersion'])is int and q['driverCorrectionVersion']==2,'specific V2 driver review');addref(e)
 need(len(pr['observerSourceReviews'])==2 and len({e['path']for e in pr['observerSourceReviews']})==2,'two preregistered observer reviews')
 for e in pr['observerSourceReviews']:
  q=load(pin(e['path'],e));need(q['status']==pr['observerSourceReviewStatus']and q['sourcePinsSHA256']==pr['observerSourcePins']['sha256']and type(q[e['versionField']])is int and q[e['versionField']]==e['versionValue']==3,'exact observerV2 SOURCE acceptance');addref(e)
 for n,v in sp.items():addref({'path':str(D/n),**v})
 addref(receipt(gp));need(len(allpins)<=8192 and all(type(v['bytes'])is int and v['bytes']>=0 for v in allpins.values())and sum(v['bytes']for v in allpins.values())<=402653184,'complete <=384MiB source closure before spawn')
 need(H((D/'input-closure.json').read_bytes())==pr['sourceClosureSHA256']and len(cl)==pr['sourceClosureFiles']and sum(v['bytes']for v in cl.values())==pr['sourceClosureBytes'],'exact source closure')
 extra={}
 def guard():
  need(gp.read_bytes()==gb and H((D/'source-pins.json').read_bytes())==g['sourcePinsSHA256'],'immutable GO/source')
  for p,v in allpins.items():pin(p,v)
  for p,v in extra.items():pin(p,v)
 guard();pf=pr['priorFailure'];fq=load(pin(pf['report']['path'],pf['report']));fip=load(pin(pf['inputPins']['path'],pf['inputPins']));need(fq['status']==pf['status']and fq['counts']==pf['counts']and fq['sourcePinsSHA256']==pf['oldSourcePinsSHA256']and fq['inputPinsSHA256']==pf['inputPins']['sha256'],'prior one-call E2104 FAIL preserved exact receipt');need(all(p in cl and cl[p]==v for p,v in fip.items()),'full prior actualFAIL closure');q=load(pr['ordinaryONActualReview']['path']);ip=load(pr['ordinaryONActualInputPins']['path']);need(q['status']==pr['ordinaryONActualReviewStatus']and q['counts']==pr['ordinaryONActualCounts']and q['inputPinsSHA256']==pr['ordinaryONActualInputPins']['sha256']and q['compilerNativeSHA256']==pr['compiler']['native']['sha256']and q['diagnosticLoaderSHA256']==pr['loader']['sha256'],'accepted ordinaryON actual4 exact schema');need(all(p in cl and cl[p]==v for p,v in ip.items()),'whole ordinaryON audit input closure')
 ex,pay=container(Path(pr['compiler']['container']['path']).read_bytes());need(ex==[{'name':'main','offset':0,'arity':0}]and pay==Path(pr['compiler']['native']['path']).read_bytes(),'base producer whole main0');need(not O.exists(),'fresh output');O.mkdir();save(O/'source-admission.json',{'files':len(allpins),'logicalBytes':sum(v['bytes']for v in allpins.values()),'closureRehashed':True,'universalResourceAdmission':False})
 env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':str(Path.home()),'TMPDIR':str(O),'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_COMMAND':'1','KEXE_CAP_RESOURCES_35':str(O),'KEXE_STRING_POOL':'268435456','KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216','KEXE_VECTOR_ITEMS':'134217728','KEXE_CPU_SECONDS':'1800','KEXE_WALL_SECONDS':'1800','KEXE_ARENA_USE':'1','KEXE_FUEL':'off'};save(O/'effective-environment.json',env);led=Ledger(env);images=[];validation=[];ok=False;built=None
 def capture(p):
  r=receipt(p);extra[str(p)]={k:r[k]for k in ['bytes','sha256']};return r
 def prefix(image):return [pr['loader']['path'],str(image),'0','0','aarch64','35,37,38,39','--']
 try:
  guard();src=O/'observer.kotoba';src.write_bytes(Path(pr['observerSource']['path']).read_bytes());src.chmod(0o444);capture(src);k=O/'observer.kseed';b=O/'observer.bin'
  led.call('observer-compile',prefix(pr['compiler']['native']['path'])+['compile',str(src),'--target','aarch64-macos','--output',str(k)]);regular(k,4194560);kr=capture(k);ex,pay=container(k.read_bytes());need(ex==[{'name':'main','offset':0,'arity':0}],'observer compiler solemain0');guard()
  raw=led.call('observer-extract',prefix(pr['compiler']['native']['path'])+['extract-native',str(k),'--symbol','main','--output',str(b)]);regular(b,4194304);need(b.read_bytes()==pay and re.findall(rb':offset ([0-9]+)\b',raw)==[b'0'],'observer whole main0 extraction');br=capture(b);built={'source':receipt(src),'container':kr,'native':br,'offset':0,'arity':0};save(O/'observer-image.json',built);guard()
  ns={'__file__':pr['observerValidator']['path']};exec(compile(Path(pr['observerValidator']['path']).read_bytes(),pr['observerValidator']['path'],'exec'),ns)
  for c in pr['cases']:
   guard();s=O/(c['workload']+'.kotoba');s.write_bytes(Path(c['source']).read_bytes());s.chmod(0o444);sr=capture(s);k=O/(c['workload']+'.kseed');binary=O/(c['workload']+'.bin')
   raw=led.call(c['workload']+'-compile',prefix(b)+['compile',str(s),'--target','aarch64-macos','--output',str(k)]);regular(k,4194560);kr=capture(k);need(k.read_bytes()==Path(c['ordinaryONContainer']['path']).read_bytes(),'whole observed == ordinaryON before extract');ex,pay=container(k.read_bytes());need(ex==c['ordinaryONExports'],'whole ordinaryON export offsets not fixedprefix guess');guard()
   result=ns['validate'](raw,c['workload'],str(k),c['ordinaryONContainer']['path'],c['ordinaryONContainer']);need(result['status']=='PASS_FIXED_ON_CLONE_CAPTURE_WHOLE_NONINSTRUMENTED_IDENTITY_ONLY','actual clone trace validation');validation.append({'workload':c['workload'],**result});save(O/'validation.json',validation);guard()
   extracted=led.call(c['workload']+'-extract',prefix(b)+['extract-native',str(k),'--symbol',c['symbol'],'--output',str(binary)]);regular(binary,4194304);need(binary.read_bytes()==pay and binary.read_bytes()==Path(c['ordinaryONNative']['path']).read_bytes()and re.findall(rb':offset ([0-9]+)\b',extracted)==[str(c['ordinaryONOffset']).encode()],'whole ordinaryON native and actualoffset');nr=capture(binary);guard();images.append({'workload':c['workload'],'source':sr,'container':kr,'native':nr,'symbol':c['symbol'],'arity':c['arity'],'offset':c['ordinaryONOffset'],'ordinaryWholeIdentity':True});save(O/'images.json',images)
  need(len(led.rows)==6 and len(images)==2 and len(validation)==2,'six complete calls');ok=True
 except BaseException as ex:save(O/'failure.json',{'status':'FAIL_FIRST_FAILURE_NO_RETRY','exception':repr(ex),'childCalls':len(led.rows),'noRetry':True});raise
 finally:
  save(O/'report.json',{'status':'COMPLETE_READONLY_ON_CLONE_OBSERVER6_FIXED_TWO_CONTEXTS_ONLY'if ok else 'FAIL_READONLY_ON_CLONE_OBSERVER6','childCalls':len(led.rows),'priorFailedClosedCalls':1,'cumulativeChildCalls':1+len(led.rows),'priorFailureReclassified':False,'observerCompiler':built,'images':images,'validation':validation,'counterObservations':[{'label':r['label'],**r['counterObservation']}for r in led.rows if 'counterObservation'in r],'workloadGuestCalls':0,'newMaskValueLowering':False,'fuelRuntimeProved':False,'universalResourceAdmission':False,'performanceQualified':False,'officialScore':False})
  save(O/'terminal.json',{'childCalls':len(led.rows),'allChildrenClosed':all(r['state']=='terminal'for r in led.rows),'failure':not ok,'noRetry':True})
if __name__=='__main__':main()
