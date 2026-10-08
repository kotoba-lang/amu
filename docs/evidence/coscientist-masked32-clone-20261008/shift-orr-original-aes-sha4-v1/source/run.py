"""SOURCE-only registered first ON4 diagnostic. Import inert; root GO required."""
from pathlib import Path
from compare import compare
import os,sys,json,hashlib,re,stat,subprocess,signal
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
 if any(len(x)>20 for x in matches[0].groups()):return {'status':'invalid','matchingLines':1,'values':None,'entireStderrIsCounterLine':PAT.fullmatch(err)is not None}
 u=dict(zip(FIELDS,map(int,matches[0].groups())));valid=all(type(v)is int and 0<=v<2**64 for v in u.values()) and u['heap-bytes']==16*u['pairs']+u['string-pool-bytes']+16*u['vectors']+8*u['vector-items'] and u['pairs']<=16777216 and u['string-pool-bytes']<=268435456 and u['vectors']<=4194304 and u['vector-items']<=134217728
 return {'status':'valid'if valid else 'invalid','matchingLines':1,'values':u,'entireStderrIsCounterLine':PAT.fullmatch(err)is not None}

class Ledger:
 def __init__(self,env):self.env=env;self.rows=[]
 def call(self,label,argv):
  need(len(self.rows)<4,'child cap');r={'index':len(self.rows)+1,'label':label,'argv':argv,'effectiveEnvironment':self.env,'timeoutSeconds':1810,'state':'started'};self.rows.append(r);save(O/'attempts.json',self.rows);p=None;raw=err=b'';failure=cleanup=None
  try:
   p=subprocess.Popen(argv,cwd=O,env=self.env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);raw,err=p.communicate(timeout=1810)
  except BaseException as ex:
   failure=repr(ex)
   if p is not None:
    try:
     try:os.killpg(p.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     raw,err=p.communicate(timeout=30)
    except BaseException as ex2:
     cleanup=repr(ex2)
     try:p.wait(timeout=30)
     except BaseException as ex3:cleanup+=';reap='+repr(ex3)
  (O/(label+'.stdout')).write_bytes(raw);(O/(label+'.stderr')).write_bytes(err);closed=p is None or p.returncode is not None
  r.update(state='terminal'if closed else 'unclosed',returncode=None if p is None else p.returncode,failure=failure,cleanupException=cleanup,stdoutSHA256=H(raw),stderrSHA256=H(err),counterObservation=counters(err));save(O/'attempts.json',self.rows)
  need(closed and failure is None and cleanup is None and p is not None and p.returncode==0,'child failure '+label)
  need(b':ok true'in raw and b':ok false'not in raw,'normal compiler success '+label);need(r['counterObservation']['status']=='valid'and r['counterObservation']['entireStderrIsCounterLine'],'normal exact 17 counters '+label);return raw

def main():
 need(len(sys.argv)==2,'root GO argument');gp=regular(sys.argv[1],1048576);gb=gp.read_bytes();g=json.loads(gb);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');closure=load(D/'input-closure.json')
 need(g['outputRoot']==pr['outputRoot']==str(O)and g['driverSHA256']==H((D/'run.py').read_bytes())and g['preregistrationSHA256']==H((D/'preregistration.json').read_bytes())and g['inputClosureSHA256']==pr['inputClosureSHA256'],'exact GO driver/namespace/closure');need(g['status']==pr['rootGOStatus']and g['sourcePinsSHA256']==H((D/'source-pins.json').read_bytes())and type(g['maximumChildCalls'])is int and g['maximumChildCalls']==4 and g['noRetry']is True and g['workloadGuestAuthorized']is False and g['timingAuthorized']is False,'exact bounded GO')
 need(type(g['sourceReviews'])is list and len(g['sourceReviews'])==2 and len({e['path']for e in g['sourceReviews']})==2,'two specific reviews')
 need(H((D/'input-closure.json').read_bytes())==pr['inputClosureSHA256']and len(closure)==pr['inputClosureFiles'],'closure identity')
 allpins=dict(closure)
 for e in g['sourceReviews']:
  q=load(pin(e['path'],e));need(q['status']==pr['sourceReviewStatus']and q['sourcePinsSHA256']==g['sourcePinsSHA256'],'specific current source review');v={'bytes':e['bytes'],'sha256':e['sha256']};need(e['path']not in allpins or allpins[e['path']]==v,'review conflict');allpins[e['path']]=v
 for n,v in sp.items():allpins[str(D/n)]=v
 allpins[str(gp)]=receipt(gp);allpins[str(gp)].pop('path')
 need(len(allpins)<=1024 and all(type(v['bytes'])is int and v['bytes']>=0 for v in allpins.values())and sum(v['bytes']for v in allpins.values())<=402653184,'full physical source closure cap before any spawn')
 def guard():
  need(gp.read_bytes()==gb and H((D/'source-pins.json').read_bytes())==g['sourcePinsSHA256'],'immutable GO/source pins')
  total=0
  for p,v in allpins.items():
   q=regular(p,v['bytes']);need(q.stat().st_size==v['bytes'],'pin stat beforehash');total+=q.stat().st_size;need(total<=402653184,'readcap beforehash')
  for p,v in allpins.items():pin(p,v)
 guard()
 for role,proof in pr['proofs'].items():
  q=load(proof['report']['path']);ip=load(proof['inputPins']['path']);need(q['status']==proof['status']and q['counts']==proof['counts']and q['inputPinsSHA256']==proof['inputPins']['sha256'],'parsed current actual proof '+role)
  need(all(p in closure and closure[p]==v for p,v in ip.items()),'entire actual input closure '+role)
 a=load(pr['proofs']['SRCompilerBuild4']['report']['path']);l=load(pr['proofs']['loaderBuild16']['report']['path']);f=load(pr['proofs']['ordinaryBaseline4']['report']['path'])
 need(a['emitterSourcePinsSHA256']=='32f76a039b4df424a7cc20c3d2f5c56d94e25ef349d10921ffd64a59d129e434'and a['counts']['closedChildCalls']==4 and a['counts']['generatedCompilerExecutions']==0,'exact SR source/build')
 need(len(a['images'])==2 and {r['arm']for r in a['images']}=={'OFF','ON'}and [r for r in a['images']if r['arm']=='ON']==[pr['compiler']],'actual SR ON image')
 need(l['loader']==pr['loader']and f['diagnosticLoaderSHA256']==pr['loader']['sha256']and len(f['images'])==2 and {r['workload']for r in f['images']}=={'nettle-aes','nettle-sha256'},'loader/ordinary priorbaseline')
 for c in pr['cases']:
  matches=[r for r in f['images']if r['workload']==c['workload']];need(len(matches)==1,'baselinecaseunique');r=matches[0]
  need(r['container']['path']==c['baselineWholeContainer']and r['symbol']==c['symbol']and r['arity']==c['arity']and closure[c['source']]=={k:r['source'][k]for k in ['bytes','sha256']},'complete original source/baseline bindings')
 ex,payload=container(Path(pr['compiler']['container']['path']).read_bytes());need(ex==[{'name':'main','offset':0,'arity':0}]and payload==Path(pr['compiler']['native']['path']).read_bytes(),'compiler whole main0 payload')
 need(not O.exists(),'fresh output namespace');O.mkdir();save(O/'source-admission.json',{'inputFiles':len(allpins),'logicalBytes':sum(v['bytes']for v in allpins.values()),'capBytes':402653184,'sourceClosureRehashed':True,'universalONResourceAdmission':False})
 env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':str(Path.home()),'TMPDIR':str(O),'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_COMMAND':'1','KEXE_CAP_RESOURCES_35':str(O),'KEXE_STRING_POOL':'268435456','KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216','KEXE_VECTOR_ITEMS':'134217728','KEXE_CPU_SECONDS':'1800','KEXE_WALL_SECONDS':'1800','KEXE_ARENA_USE':'1','KEXE_FUEL':'off'}
 led=Ledger(env);images=[];ok=False;extra={};save(O/'effective-environment.json',env)
 def outputguard():
  guard()
  for p,v in extra.items():pin(p,v)
 try:
  for c in pr['cases']:
   outputguard();src=O/(c['workload']+'.kotoba');src.write_bytes(Path(c['source']).read_bytes());src.chmod(0o444);sr=receipt(src);extra[str(src)]={k:sr[k]for k in ['bytes','sha256']};k=O/(c['workload']+'.kseed');b=O/(c['workload']+'.bin');prefix=[pr['loader']['path'],pr['compiler']['native']['path'],'0','0','aarch64','35,37,38,39','--']
   led.call(c['workload']+'-compile',prefix+['compile',str(src),'--target','aarch64-macos','--output',str(k)])
   regular(k,4194560);kr=receipt(k);newex,payload=container(k.read_bytes());oldex,oldpayload=container(Path(c['baselineWholeContainer']).read_bytes());need(newex==oldex,'unchanged complete exports/offsets/arities');chosen=[r for r in newex if r['name']==c['symbol']and r['arity']==c['arity']];need(len(chosen)==1,'selected workload export');extra[str(k)]={x:kr[x]for x in ['bytes','sha256']};outputguard()
   raw=led.call(c['workload']+'-extract',prefix+['extract-native',str(k),'--symbol',c['symbol'],'--output',str(b)]);regular(b,4194304);need(b.read_bytes()==payload and re.findall(rb':offset ([0-9]+)\b',raw)==[str(chosen[0]['offset']).encode()],'whole current extraction and exact offset');br=receipt(b);extra[str(b)]={x:br[x]for x in ['bytes','sha256']};outputguard()
   delta=compare(oldpayload,payload);need(k.read_bytes().split(b'\n\n',1)[0]==Path(c['baselineWholeContainer']).read_bytes().split(b'\n\n',1)[0],'entire container header exact')
   images.append({'wordPatternObservation':delta,'workload':c['workload'],'source':sr,'container':kr,'native':br,'exports':newex,'symbol':c['symbol'],'arity':c['arity'],'offset':chosen[0]['offset'],'baselineContainer':receipt(c['baselineWholeContainer']),'wholeContainerEqualsBaseline':k.read_bytes()==Path(c['baselineWholeContainer']).read_bytes(),'nativePayloadEqualsBaseline':payload==oldpayload,'nativeLengthDelta':len(payload)-len(oldpayload),'transformationQualified':False,'workloadExecuted':False});save(O/'images.json',images)
  ok=True
 except BaseException as ex:
  save(O/'failure.json',{'status':'FAIL_FIRST_FAILURE_NO_RETRY','exception':repr(ex),'childCalls':len(led.rows),'noRetry':True});raise
 finally:
  save(O/'report.json',{'status':'COMPLETE_SR_ORIGINAL_AES_SHA_COMPILE_EXTRACT4_PATTERN_OBSERVATION_ONLY'if ok else 'FAIL_SR_ORIGINAL_AES_SHA_COMPILE_EXTRACT4','childCalls':len(led.rows),'images':images,'counterObservations':[{'label':r['label'],**r['counterObservation']}for r in led.rows if 'counterObservation'in r],'transformOwnerOpcodeQualified':False,'universalONResourceAdmission':False,'workloadFunctionalQualified':False,'selfhostQualified':False,'full19Qualified':False,'timingQualified':False,'officialScore':False})
  save(O/'terminal.json',{'childCalls':len(led.rows),'compileCalls':sum(r['label'].endswith('-compile')for r in led.rows),'extractCalls':sum(r['label'].endswith('-extract')for r in led.rows),'allChildrenClosed':all(r['state']=='terminal'for r in led.rows),'failure':not ok,'noRetry':True})
if __name__=='__main__':main()
