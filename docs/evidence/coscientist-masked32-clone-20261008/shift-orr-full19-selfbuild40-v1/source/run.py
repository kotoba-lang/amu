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
  need(len(self.rows)<40,'child cap');r={'index':len(self.rows)+1,'label':label,'argv':argv,'effectiveEnvironment':self.env,'timeoutSeconds':1810,'state':'started'};self.rows.append(r);save(O/'attempts.json',self.rows);p=None;raw=err=b'';failure=cleanup=None
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
 need(len(sys.argv)==2,'root GO argument');gp=regular(sys.argv[1],1048576);gb=gp.read_bytes();g=json.loads(gb);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');cl=load(D/'input-closure.json')
 need(g['status']==pr['rootGOStatus']and g['outputRoot']==pr['outputRoot']==str(O)and g['sourcePinsSHA256']==H((D/'source-pins.json').read_bytes())and g['driverSHA256']==H((D/'run.py').read_bytes())and g['preregistrationSHA256']==H((D/'preregistration.json').read_bytes())and g['inputClosureSHA256']==H((D/'input-closure.json').read_bytes()),'exact root GO/source')
 need(type(g['maximumChildCalls'])is int and g['maximumChildCalls']==40 and g['noRetry']is True and g['timingAuthorized']is False and g['workloadGuestSSHAuthorized']is False,'bounded40 no guests/timing');need(len(g['sourceReviews'])==2 and len({r['path']for r in g['sourceReviews']})==2,'two specific reviews')
 allpins=dict(cl)
 for n,v in sp.items():allpins[str(D/n)]=v
 for e in g['sourceReviews']:
  q=load(pin(e['path'],e));need(q['status']==pr['sourceReviewStatus']and q['sourcePinsSHA256']==g['sourcePinsSHA256'],'specific source receipt');allpins[e['path']]={k:e[k]for k in ['bytes','sha256']}
 allpins[str(gp)]={'bytes':len(gb),'sha256':H(gb)};need(len(allpins)<=2048 and sum(v['bytes']for v in allpins.values())<=402653184,'full closure cap before hash/spawn')
 def guard():
  need(gp.read_bytes()==gb and H((D/'source-pins.json').read_bytes())==g['sourcePinsSHA256'],'immutable root GO/SP')
  for p,v in allpins.items():need(regular(p,v['bytes']).stat().st_size==v['bytes'],'all bounded stat beforehash')
  for p,v in allpins.items():pin(p,v)
 guard()
 for role,f in pr['proofs'].items():
  q=load(f['report']['path']);ip=load(f['inputPins']['path']);need(q['status']==f['status']and q['inputPinsSHA256']==f['inputPins']['sha256'],'exact parsed current proof '+role)
  if 'counts'in f:need(q['counts']==f['counts'],'exact proof counts '+role)
  need(all(cl[p]==v for p,v in ip.items()),'complete proof input closure '+role)
 f=load(pr['proofs']['functional30']['report']['path']);need(f['counts']=={'closedChildCalls':30,'nativeCalls':20,'CCalls':10,'triples':10,'workloads':2,'profilesPerWorkload':5,'auditorNativeCompilerSSHCalls':0}and f['nativePairResultFuelFourTerminalArenasExact']is True,'actual functional30 accepted scope')
 c=load(pr['proofs']['component36']['report']['path']);need(c['correctionVersion']==3 and c['closedChildCalls']==36 and c['componentProbeCalls']==34 and c['cumulativeClosedCalls']==42 and c['sourcePinsSHA256']=='4d7342773b19048dab93637759aef3813e873f619214bf6b484f06b946898d1f','actual current scalar component36')
 s=load(pr['proofs']['SR4']['report']['path']);need(s['counts']['closedChildCalls']==4 and s['counts']['observedAlignedThreeWordPatterns']==13 and [r['workload']for r in s['images']]==['nettle-aes','nettle-sha256'],'retained actual4 without rerun')
 a=load(pr['proofs']['SRCompilerBuild4']['report']['path']);need([r for r in a['images']if r['arm']=='ON']==[pr['compiler']],'qualified SR5404 G1 image');l=load(pr['proofs']['loaderBuild16']['report']['path']);need(l['loader']==pr['loader'],'qualified e14 loader')
 co=load(pr['proofs']['maskedON19']['report']['path']);need(co['counts']=={'closedNewChildCalls':34,'newCompileCalls':17,'newExtractCalls':17,'retainedFirstONCalls':4,'joinedOriginal19CompileExtractCalls':38,'joinedOriginal19Images':19,'rerunRetainedWorkloads':0,'workloadGuestCalls':0,'auditorNativeCompilerSSHCalls':0}and co['joinedOriginal19Images']==pr['original19'],'entire actual original19 baseline')
 original=pr['original19'];need(len(original)==len(pr['profiles'])==19 and len({r['workload']for r in original})==19,'19 unique original profiles');need(pr['cases']==[r for r in original if r['workload']not in ['nettle-aes','nettle-sha256']]and len(pr['cases'])==17,'exact complement17 in original order')
 matrix=load(pr['matrix']['path']);need(matrix['format']=='amu.embench-comparison-matrix-spec/v1'and matrix['upstreamCommit']=='09c2ed8c3b7008c95d08b038de4a3f6dc103ed70','unchanged canonical upstream cohort');need(len(matrix['entries'])==19 and [r['workload']for r in matrix['entries']]==[r['workload']for r in original],'canonical whole19 order');need(all(m['symbol']==r['symbol']and m['expectedSourceSha256']==r['source']['sha256']and m['iterations']==p['iterations']for m,r,p in zip(matrix['entries'],original,pr['profiles'])),'canonical19 sourcehash/symbol/profile joins')
 for p,r in zip(pr['profiles'],original):
  need(p['workload']==r['workload']and p['symbol']==r['symbol']and p['arity']==r['arity']==1 and p['sourceSHA256']==r['source']['sha256']and p['iterations']==[0,1,2,17,2000 if r['workload']=='depthconv'else 32],'exact source/export/profiles')
  ex,payload=container(pin(r['container']['path'],r['container']).read_bytes());need(ex==r['exports']and payload==pin(r['native']['path'],r['native']).read_bytes()and {'name':r['symbol'],'offset':r['offset'],'arity':1}in ex,'every old full header/native/entry')
 ex,payload=container(pin(pr['compiler']['container']['path'],pr['compiler']['container']).read_bytes());need(ex==[{'name':'main','offset':0,'arity':0}]and payload==pin(pr['compiler']['native']['path'],pr['compiler']['native']).read_bytes(),'G1 full main0 container');need(pin(pr['unitySource']['path'],pr['unitySource']).read_bytes()==pin(pr['compiler']['source']['path'],pr['compiler']['source']).read_bytes()and pr['unitySource']['sha256']=='2b00f83cf91e4215882530893281a22d9eb23168e97aff59221867937fe7a207','exact frozen unity-sr-on source')
 need(not O.exists(),'fresh output no retry');O.mkdir();env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':str(Path.home()),'TMPDIR':str(O),'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_COMMAND':'1','KEXE_CAP_RESOURCES_35':str(O),'KEXE_STRING_POOL':'268435456','KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216','KEXE_VECTOR_ITEMS':'134217728','KEXE_CPU_SECONDS':'1800','KEXE_WALL_SECONDS':'1800','KEXE_ARENA_USE':'1','KEXE_FUEL':'off'};save(O/'effective-environment.json',env);save(O/'source-admission.json',{'inputFiles':len(allpins),'logicalBytes':sum(v['bytes']for v in allpins.values()),'fixedCapBytes':402653184,'noUniversalAllocationAdmission':True});led=Ledger(env);extra={};images=[];gens=[];ok=False;phase='remaining17'
 def outputguard():
  guard()
  for p,v in extra.items():pin(p,v)
 def remember(p):
  r=receipt(p);extra[str(p)]={k:r[k]for k in ['bytes','sha256']};return r
 def compile_extract(label,source,compiler,symbol,prevalidate):
  outputguard();src=O/(label+'.kotoba');src.write_bytes(pin(source['path'],source).read_bytes());src.chmod(0o444);sr=remember(src);k=O/(label+'.kseed');b=O/(label+'.bin');prefix=[pr['loader']['path'],compiler['path'],'0','0','aarch64','35,37,38,39','--'];led.call(label+'-compile',prefix+['compile',str(src),'--target','aarch64-macos','--output',str(k)]);regular(k,4194560);kr=remember(k);ex,payload=container(k.read_bytes());chosen=[r for r in ex if r['name']==symbol];need(len(chosen)==1,'unique selectedexport before extract');prevalidate(k.read_bytes(),ex,payload);outputguard();raw=led.call(label+'-extract',prefix+['extract-native',str(k),'--symbol',symbol,'--output',str(b)]);regular(b,4194304);br=remember(b);need(b.read_bytes()==payload and re.findall(rb':offset ([0-9]+)\b',raw)==[str(chosen[0]['offset']).encode()],'whole native extraction exactoffset');outputguard();return {'label':label,'source':sr,'container':kr,'native':br,'exports':ex,'symbol':symbol,'offset':chosen[0]['offset'],'arity':chosen[0]['arity']}
 try:
  for r in pr['cases']:
   im=compile_extract(r['workload'],r['source'],pr['compiler']['native'],r['symbol'],lambda kb,ex,payload,r=r:need(kb==Path(r['container']['path']).read_bytes(),'unexpected remaining17 compiled container STOP before extract'));need(im['arity']==r['arity']and im['offset']==r['offset']and Path(im['container']['path']).read_bytes()==Path(r['container']['path']).read_bytes()and Path(im['native']['path']).read_bytes()==Path(r['native']['path']).read_bytes(),'remaining17 entire oldON bytes no unexpected delta');images.append(im);save(O/'remaining17-images.json',images)
  need(len(led.rows)==34 and len(images)==17,'phase boundary34 complete');phase='selfbuild';save(O/'phase-boundary.json',{'closedCalls':34,'remaining17Complete':True,'retainedAES_SHACompileCalls':4,'joinedOriginal19CompileExtractCalls':38,'newSelfbuildCalls':0});current=pr['compiler']['native'];g2=None
  for generation in [2,3,4]:
   def pre_generation(kb,ex,payload):
    need(ex==[{'name':'main','offset':0,'arity':0}],'generation main0 beforeextract')
    if generation==2:
     oldk=Path(pr['compiler']['container']['path']).read_bytes();old=Path(pr['compiler']['native']['path']).read_bytes();need(kb.split(b'\n\n',1)[0]==oldk.split(b'\n\n',1)[0],'G2 header beforeextract')
     if payload!=old:compare(old,payload)
    else:need(kb==Path(g2['container']['path']).read_bytes(),'fixedpoint failure STOP beforeextract')
   im=compile_extract('G'+str(generation),pr['unitySource'],current,'main',pre_generation);need(im['exports']==[{'name':'main','offset':0,'arity':0}],'generation solemain0arity0');new=Path(im['native']['path']).read_bytes();k=Path(im['container']['path']).read_bytes()
   if generation==2:
    old=Path(pr['compiler']['native']['path']).read_bytes();oldk=Path(pr['compiler']['container']['path']).read_bytes();need(k.split(b'\n\n',1)[0]==oldk.split(b'\n\n',1)[0],'G1-G2 fullheader unchanged');im['G1toG2Observation']={'wholeEqual':True,'observedAlignedThreeWordPatterns':0}if new==old else compare(old,new);g2=im
   else:need(new==Path(g2['native']['path']).read_bytes()and k==Path(g2['container']['path']).read_bytes(),'G2/G3/G4 whole container AND native bytefixedpoint')
   gens.append(im);save(O/'generations.json',gens);current=im['native']
  need(len(led.rows)==40,'closed40 complete');ok=True
 except BaseException as ex:save(O/'failure.json',{'status':'FAIL_FIRST_FAILURE_NO_RETRY','phase':phase,'exception':repr(ex),'childCalls':len(led.rows),'completedRemaining17':len(images),'completedSelfbuildGenerations':len(gens)});raise
 finally:
  save(O/'report.json',{'status':'COMPLETE_SR_REMAINING17_SELFBUILD40_IDENTITY_ONLY'if ok else'FAIL_SR_REMAINING17_SELFBUILD40','phase':phase,'childCalls':len(led.rows),'remaining17':images,'generations':gens,'retainedAES_SHACompileCalls':4,'retainedFunctionalCalls':30,'joinedOriginal19CompileExtractCalls':38 if len(images)==17 else None,'G2G3G4ByteFixedpoint':ok,'counterObservations':[{'label':r['label'],**r['counterObservation']}for r in led.rows if 'counterObservation'in r],'productAdopted':False,'universalCorrectnessQualified':False,'full19FunctionalQualified':False,'timingQualified':False,'officialScore':False});save(O/'terminal.json',{'childCalls':len(led.rows),'compileCalls':sum(r['label'].endswith('-compile')for r in led.rows),'extractCalls':sum(r['label'].endswith('-extract')for r in led.rows),'allChildrenClosed':all(r['state']=='terminal'for r in led.rows),'failure':not ok,'noRetry':True})
if __name__=='__main__':main()
