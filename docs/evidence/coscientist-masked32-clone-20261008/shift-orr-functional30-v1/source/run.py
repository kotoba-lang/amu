"""Finite SOURCE functional-only driver. Root GO and two specific reviews required."""
from pathlib import Path
import os,sys,json,re,hashlib,stat,subprocess,signal,platform
D=Path(__file__).resolve().parent;O=D/'run-outputs';H=lambda b:hashlib.sha256(b).hexdigest()
def need(c,m):
 if not c:raise AssertionError(m)
def load(p):return json.loads(Path(p).read_bytes())
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def regular(p,n):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size<=n,'regular bounded file '+str(p));return p
def pin(v):
 p=regular(v['path'],v['bytes']);need(p.stat().st_size==v['bytes'],'exact size');h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 need(h.hexdigest()==v['sha256'],'exact hash '+str(p));return p

def container(v):
 b=pin(v).read_bytes();head,payload=b.split(b'\n\n',1);ls=head.decode('ascii').splitlines();need(ls[0]==f'KSEED1 {len(payload)} {len(ls)-1}','full KSEED sizes');ex=[]
 for x in ls[1:]:
  m=re.fullmatch(r'([A-Za-z0-9_-]+) ([0-9]+) ([0-9]+)',x);need(m is not None,'export syntax');s,p,a=m.groups();p=int(p);a=int(a);need(p%4==0 and p+4<=len(payload),'export range');ex.append({'name':s,'offset':p,'arity':a})
 need(len({r['name']for r in ex})==len(ex),'unique exports');return ex,payload
NATIVE=re.compile(rb'\{:status :ok :result ([01]) :fuel \{:initial ([0-9]{1,20}) :remaining ([0-9]{1,20})\} :heap \{:capacity ([0-9]{1,20}) :used ([0-9]{1,20})\} :string-pool \{:capacity ([0-9]{1,20}) :used ([0-9]{1,20})\} :vectors \{:capacity ([0-9]{1,20}) :used ([0-9]{1,20})\} :vector-items \{:capacity ([0-9]{1,20}) :used ([0-9]{1,20})\}\}\n')
CAPS={'heap':2097152,'string-pool':65536,'vectors':4096,'vector-items':65536}
def native(out,err,n):
 need(not err,'native stderr empty, no peak diagnostics');m=NATIVE.fullmatch(out);need(m is not None,'exact terminal native report');v=list(map(int,m.groups()));need(all(x<2**64 for x in v),'uint64 fields');result,initial,remaining=v[:3];need(result==(0 if n==0 else 1)and initial==16777216 and 0<remaining<=initial,'native bool oracle/fuel');a={}
 for i,(k,cap)in enumerate(CAPS.items()):
  c,u=v[3+2*i:5+2*i];need(c==cap and 0<=u<=cap,'actual terminal arena');a[k]={'capacity':c,'used':u}
 return {'status':'ok','result':result,'fuel':{'initial':initial,'remaining':remaining},'terminalArenas':a}
CFIELDS={'format','calls','warmupCalls','elapsedNanoseconds','result','maxRssBytes','fuelPerCall','contextFuelBefore','contextFuelAfter','contextFuelConsumed','nativeArtifactAbi','artifactKind','nativeArenaStatus','nativeArenas'}
def unique(p):
 d={}
 for k,v in p:need(k not in d,'duplicate JSON key');d[k]=v
 return d
def csample(out,err,n):
 need(not err and out.endswith(b'\n')and out.count(b'\n')==1,'C single JSON empty stderr');q=json.loads(out,object_pairs_hook=unique);need(set(q)==CFIELDS and q['format']=='kotoba.runtime-sample/v1','C exact schema')
 for k in ['calls','warmupCalls','elapsedNanoseconds','result','maxRssBytes','fuelPerCall','contextFuelBefore','contextFuelAfter','contextFuelConsumed']:need(type(q[k])is int and 0<=q[k]<2**64,'C uint64 int')
 need(q['calls']==1 and q['warmupCalls']==0 and q['result']==(0 if n==0 else 1),'C bool source oracle');need(q['fuelPerCall']==q['contextFuelBefore']==q['contextFuelAfter']==16777216 and q['contextFuelConsumed']==0,'C no fuel charge');need(q['nativeArtifactAbi']=='kotoba.native-artifact-i64x8-to-i64-indirect/v1'and q['artifactKind']=='dylib'and q['nativeArenaStatus']=='unavailable-C'and q['nativeArenas']is None,'C arena unavailable/null');return {k:v for k,v in q.items()if k not in ['elapsedNanoseconds','maxRssBytes']}

class Ledger:
 def __init__(self):self.rows=[]
 def call(self,label,argv,env):
  need(len(self.rows)<30,'finite30');r={'index':len(self.rows)+1,'label':label,'argv':argv,'environment':env,'state':'started','timeoutSeconds':40};self.rows.append(r);save(O/'attempts.json',self.rows);p=None;out=err=b'';failure=cleanup=None
  try:
   p=subprocess.Popen(argv,cwd=O,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);out,err=p.communicate(timeout=40)
  except BaseException as e:
   failure=repr(e)
   if p is not None:
    try:
     try:os.killpg(p.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     out,err=p.communicate(timeout=30)
    except BaseException as e2:
     cleanup=repr(e2)
     try:p.wait(timeout=30)
     except BaseException as e3:cleanup+=';reap='+repr(e3)
  (O/(label+'.stdout')).write_bytes(out);(O/(label+'.stderr')).write_bytes(err);closed=p is None or p.returncode is not None;r.update(state='terminal'if closed else'unclosed',returncode=None if p is None else p.returncode,failure=failure,cleanupException=cleanup,stdoutSHA256=H(out),stderrSHA256=H(err));save(O/'attempts.json',self.rows)
  need(closed and p is not None and p.returncode==0 and failure is None and cleanup is None,'first child failure STOP');need(len(out)<=1048576 and len(err)<=1048576,'raw bounded validation');return out,err

def main():
 need(len(sys.argv)==2 and platform.machine()=='arm64'and platform.system()=='Darwin','root GO local Darwin arm64');gp=regular(sys.argv[1],1048576);gb=gp.read_bytes();g=json.loads(gb);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');cl=load(D/'input-closure.json')
 need(g['status']==pr['rootGOStatus']and g['outputRoot']==str(O)and g['sourcePinsSHA256']==H((D/'source-pins.json').read_bytes())and g['driverSHA256']==H((D/'run.py').read_bytes())and g['preregistrationSHA256']==H((D/'preregistration.json').read_bytes()),'exact source GO');need(g['maximumChildCalls']==30 and type(g['maximumChildCalls'])is int and g['noRetry']is True and g['timingAuthorized']is False and g['compilerSSHAuthorized']is False,'finite functional only');need(g['inputClosureSHA256']==H((D/'input-closure.json').read_bytes()),'closure GO');need(len(g['sourceReviews'])==2 and len({r['path']for r in g['sourceReviews']})==2,'two reviews')
 allpins={p:{'path':p,**v}for p,v in cl.items()}
 for n,v in sp.items():allpins[str(D/n)]={'path':str(D/n),**v}
 for v in g['sourceReviews']:
  q=load(pin(v));need(q['status']==pr['sourceReviewStatus']and q['sourcePinsSHA256']==g['sourcePinsSHA256'],'specific source receipt');allpins[v['path']]=v
 allpins[str(gp)]={'path':str(gp),'bytes':len(gb),'sha256':H(gb)}
 need(len(allpins)<=1536 and sum(v['bytes']for v in allpins.values())<=402653184,'full closure cap before hash/spawn')
 def guard():
  need(gp.read_bytes()==gb and H((D/'source-pins.json').read_bytes())==g['sourcePinsSHA256'],'immutable GO/SP')
  for v in allpins.values():regular(v['path'],v['bytes'])
  for v in allpins.values():pin(v)
 guard()
 for role,p in pr['proofs'].items():
  q=load(p['report']['path']);need(q['status']==p['status']and q['inputPinsSHA256']==p['inputPins']['sha256'],'parsed exact proof '+role)
  for path,v in load(p['inputPins']['path']).items():need(cl[path]==v,'entire proof closure '+role)
 sr=load(pr['proofs']['SR4']['report']['path']);old=load(pr['proofs']['ordinary4']['report']['path']);lr=load(pr['proofs']['loader16']['report']['path']);cr=load(pr['proofs']['C19']['report']['path']);rr=load(pr['proofs']['CConsumers19']['report']['path']);raw=load(pr['CConsumerRawReport']['path'])
 need(sr['counts']=={'closedChildCalls':4,'compileCalls':2,'extractCalls':2,'workloads':2,'observedAlignedThreeWordPatterns':13,'workloadGuestCalls':0,'auditorNativeCompilerSSHCalls':0},'SR4 exact counts');need(lr['loader']==pr['loader']and pr['loader']['sha256']=='e14c2919ac5afd0960d9e6a4ac30ed90da26047c99842ef4d66428322764a77f','source bound loader');need(cr['compilerBuilds']==19 and cr['identityQueries']==14 and rr['runnerBuilds']==19 and rr['all19ImmutableNativeAndCByteAnchorsPresent']is True,'historical C/consumer real acceptance');need(raw['sourceSHA256']==pr['CConsumerSource']['sha256']and raw['builds']==19,'consumer source identity')
 cp=pr['proofs']['component36'];cq=load(cp['report']['path']);need(cq['status']==pr['componentStatus']and {k:cq[k]for k in pr['componentFacts']}==pr['componentFacts']and cq['sourcePinsSHA256']==pr['componentSourcePinsSHA256'],'exact current component prerequisite')
 for c,x in zip(pr['cases'],sr['images']):
  need(c['workload']==x['workload']and c['SR']==x['native']and c['SRContainer']==x['container']and c['offset']==x['offset']and c['symbol']==x['symbol']and c['arity']==1,'SR4 image exact')
  y=next(r for r in old['images']if r['workload']==c['workload']);need(c['maskedON']==y['native']and c['maskedONContainer']==y['container']and c['source']['sha256']==y['source']['sha256'],'original maskedON same source')
  for arm in ['SR','maskedON']:
   ex,payload=container(c[arm+'Container']);need(ex==c['exports']and payload==pin(c[arm]).read_bytes()and {'name':c['symbol'],'offset':c['offset'],'arity':1}in ex,'whole header/payload/entry')
  z=next(r for r in cr['images']if r['workload']==c['workload']);need(z['sha256']==c['C']['sha256']and z['bytes']==c['C']['bytes']and z['cSymbolPlannedOnly']==c['CSymbol'],'exact C accepted bytes/export')
  z=next(r for r in rr['images']if r['workload']==c['workload']);need(z['runnerSHA256']==c['CRunner']['sha256']and z['runnerBytes']==c['CRunner']['bytes'],'exact C consumer actual')
  need(pin(c['CRunner']).read_bytes().count(pin(c['C']).read_bytes())==1,'immutable exact C embedded once')
 need(not O.exists(),'fresh output/noRetry');O.mkdir();(O/'tmp').mkdir();save(O/'source-admission.json',{'inputFiles':len(allpins),'logicalBytes':sum(v['bytes']for v in allpins.values()),'current33OrSDKQualification':False,'localHistoricalCConsumer':True});base={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':str(Path.home()),'TMPDIR':str(O/'tmp'),'LANG':'C','LC_ALL':'C','TZ':'UTC'};env={**base,'KEXE_ARG_TYPES':'i64','KEXE_RESULT_TYPE':'i64','KEXE_STRUCTURED_REPORT':'1','KEXE_FUEL':'16777216','KEXE_PAIRS':'2097152','KEXE_STRING_POOL':'65536','KEXE_VECTORS':'4096','KEXE_VECTOR_ITEMS':'65536','KEXE_CPU_SECONDS':'30','KEXE_WALL_SECONDS':'30'};need('KEXE_COMMAND'not in env,'ordinary return ABI');save(O/'effective-environment.json',{'native':env,'C':base,'allInheritedRemoved':True});led=Ledger();completed=[];ok=False
 try:
  for c in pr['cases']:
   for n in [0,1,2,17,32]:
    pair={}
    for arm in ['maskedON','SR','C']:
     guard();label=c['workload']+'-'+arm+'-n'+str(n)
     if arm=='C':argv=[c['CRunner']['path'],'dylib',c['C']['path'],c['CSymbol'],'aarch64',str(n),'1','0','16777216'];e=base
     else:argv=[pr['loader']['path'],c[arm]['path'],str(c['offset']),'1','aarch64','-',str(n)];e=env
     out,err=led.call(label,argv,e);guard();pair[arm]=csample(out,err,n)if arm=='C'else native(out,err,n)
     if arm=='SR':need(pair['maskedON']==pair['SR'],'native bool/status/fuel/four terminal arena exact')
    completed.append({'workload':c['workload'],'n':n,'arms':pair});save(O/'comparisons.json',completed)
  need(len(led.rows)==30 and len(completed)==10,'all30closed10triples');ok=True
 except BaseException as ex:save(O/'failure.json',{'exception':repr(ex),'calls':len(led.rows),'completedTriples':len(completed),'policy':'STOP_FIRST_FAILURE_NO_RETRY'});raise
 finally:
  save(O/'report.json',{'status':'PASS_FINITE_SR_AES_SHA30_FUNCTIONAL_ONLY'if ok else'FAIL_FINITE_SR_AES_SHA30_FIRST_FAILURE','calls':len(led.rows),'completedTriples':len(completed),'nativePairTerminalArenaFuelExact':ok,'CNativeArenas':'unavailable-C/null','current19Qualified':False,'timingQualified':False,'officialScore':False,'comparisons':completed});save(O/'terminal.json',{'calls':len(led.rows),'allCallsClosed':all(r['state']=='terminal'for r in led.rows),'failure':not ok,'noRetry':True})
if __name__=='__main__':main()
