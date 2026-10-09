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
  need(len(self.rows)<255,'finite255');r={'index':len(self.rows)+1,'label':label,'argv':argv,'environment':env,'state':'started','timeoutSeconds':40};self.rows.append(r);save(O/'attempts.json',self.rows);p=None;out=err=b'';failure=cleanup=None
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
 need(g['status']==pr['rootGOStatus']and g['outputRoot']==str(O)and g['maximumChildCalls']==255 and g['functionalAuthorized']is True and g['timingAuthorized']is False and g['compilerSSHAuthorized']is False and g['noRetry']is True,'specific finite255 root GO')
 for n,k in [('source-pins.json','sourcePinsSHA256'),('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256'),('input-closure.json','inputClosureSHA256')]:need(H((D/n).read_bytes())==g[k],'exact SOURCE registry '+n)
 need(len(g['sourceReviews'])==2 and len({v['path']for v in g['sourceReviews']})==2,'two SOURCE receipts')
 allpins={p:{'path':p,**v}for p,v in cl.items()}
 for n,v in sp.items():allpins[str(D/n)]={'path':str(D/n),**v}
 for v in g['sourceReviews']+[g['LC40RootAcceptance']]:allpins[v['path']]=v
 allpins[str(gp)]={'path':str(gp),'bytes':len(gb),'sha256':H(gb)}
 need(len(allpins)<=pr['maximumInputFiles']and sum(v['bytes']for v in allpins.values())<=pr['maximumInputLogicalBytes'],'bounded full evidence closure BEFORE hash or spawn')
 def guard():
  need(gp.read_bytes()==gb,'immutable GO')
  for n,k in [('source-pins.json','sourcePinsSHA256'),('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256'),('input-closure.json','inputClosureSHA256')]:need(H((D/n).read_bytes())==g[k],'immutable registry')
  actualTotal=0
  for v in allpins.values():
   p=regular(v['path'],v['bytes']);size=p.stat().st_size;need(size==v['bytes'],'exact stat before hash');actualTotal+=size;need(actualTotal<=pr['maximumInputLogicalBytes'],'actual aggregate BEFORE hash')
  for v in allpins.values():pin(v)
 guard()
 for v in g['sourceReviews']:
  q=load(v['path']);need(q['status']==pr['sourceReviewStatus']and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256']),'specific SOURCE review')
 for role,p in pr['proofs'].items():
  q=load(p['report']['path']);need(q['status']==p['status']and q['inputPinsSHA256']==p['inputPins']['sha256'],'specific actual proof '+role)
  for path,v in load(p['inputPins']['path']).items():need(cl[path]==v,'full inherited dependency closure')
 a40=load(g['LC40RootAcceptance']['path']);need(a40['status']==pr['root40AcceptanceRequired']and a40['independentReport']==pr['proofs']['LC40']['report']and a40['originalWorkloads']==19 and a40['closedLoaderCalls']==40,'actual40 ROOT accepted exact independent report')
 a30=load(pr['LC30Acceptance']['path']);need(a30['status']=='ROOT_ACCEPTED_FINITE_LC_MD5_SHA30_FUNCTIONAL_ONLY'and a30['actualCalls']==30 and a30['independentReport']==pr['proofs']['LC30']['report']and a30['OFFONFuelAndFourTerminalArenasParity']is True,'retained actual30 ROOT accepted')
 lc40=load(pr['proofs']['LC40']['report']['path']);need(lc40['counts']['closedLoaderCalls']==40 and lc40['counts']['originalWorkloads']==19 and lc40['G1G2G3WholeContainerAndNativeByteFixedpoint']is True,'LC40 actual schema')
 old285=load(pr['proofs']['resourceProfiles']['report']['path']);need(old285['closedFunctionalCalls']==285 and old285['workloads']==19 and old285['comparisons']==95 and old285['nativeFuelAndFourTerminalArenaPairExact']is True,'actual matched original19 resource precedent')
 matrix=load(pr['canonicalMatrix']['path']);need(len(matrix['entries'])==19,'original19 matrix');expected=[e for e in matrix['entries']if e['workload']not in ['md5sum','nettle-sha256']];need(len(expected)==len(pr['cases'])==17,'exact17 complement')
 profiles=load(pr['resourceProfiles']['path']);rr=load(pr['proofs']['CConsumer19']['report']['path']);cr=load(pr['proofs']['C19']['report']['path'])
 for c,e in zip(pr['cases'],expected):
  need(c['workload']==e['workload']and c['symbol']==e['symbol']and c['iterations']==e['iterations']and c['source']['sha256']==e['expectedSourceSha256'],'unchanged original source/symbol/profiles')
  p=[v for v in profiles if v['workload']==c['workload']];need(p==c['resourceReferenceProfiles']and [v['n']for v in p]==e['iterations'],'perworkload actual resource references')
  for v in p:need(0<v['nativeFuelConsumed']<pr['nativeFuel']and all(x['used']<=x['capacity']for x in v['nativeArenas'].values()),'finite previous resource margin; never peak')
  sr=load(pr['proofs']['SR4'if c['workload']=='nettle-aes'else'SR40']['report']['path']);off=next(v for v in(sr['images']if c['workload']=='nettle-aes'else sr['remaining17'])if v.get('workload',v.get('label'))==c['workload']);need(c['OFF']==off['native']and c['OFFContainer']==off['container']and c['OFFOffset']==off['offset'],'actual SR OFF correspondence')
  z=next(v for v in lc40['images']if v['workload']==c['workload']);need(c['ON']==z['native']and c['ONContainer']==z['container']and c['ONOffset']==z['offset'],'G0 LC actual full artifact identity')
  for arm in ['OFF','ON']:
   exports,payload=container(c[arm+'Container']);need(payload==pin(c[arm]).read_bytes()and dict(name=c['symbol'],offset=c[arm+'Offset'],arity=1)in exports,'full native/container/export binding')
  z=next(v for v in cr['images']if v['workload']==c['workload']);need(c['C']['sha256']==z['sha256']and c['C']['bytes']==z['bytes']and c['CSymbol']==z['cSymbolPlannedOnly'],'actual C dylib symbol identity')
  z=next(v for v in rr['images']if v['workload']==c['workload']);need(c['CRunner']['sha256']==z['runnerSHA256']and c['CRunner']['bytes']==z['runnerBytes'],'historical C consumer exact');cb=pin(c['C']).read_bytes();rb=pin(c['CRunner']).read_bytes();need(rb.count(cb)==1 and rb.find(cb)==z['immutableImageByteAnchors']['C'],'whole current C embedded byte position')
 need(not O.exists(),'fresh output/no retry');O.mkdir();(O/'tmp').mkdir();base={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':str(O/'tmp'),'LANG':'C','LC_ALL':'C','TZ':'UTC'};env={**base,'KEXE_ARG_TYPES':'i64','KEXE_RESULT_TYPE':'i64','KEXE_STRUCTURED_REPORT':'1','KEXE_FUEL':'16777216','KEXE_PAIRS':'2097152','KEXE_STRING_POOL':'65536','KEXE_VECTORS':'4096','KEXE_VECTOR_ITEMS':'65536','KEXE_CPU_SECONDS':'30','KEXE_WALL_SECONDS':'30'};need('KEXE_COMMAND'not in env,'ordinary return ABI');save(O/'effective-environment.json',{'native':env,'C':base,'allInheritedRemoved':True});led=Ledger();completed=[];ok=False
 try:
  for c in pr['cases']:
   for n in c['iterations']:
    pair={}
    for arm in ['OFF','ON','C']:
     guard();label=c['workload']+'-'+arm+'-n'+str(n)
     if arm=='C':argv=[c['CRunner']['path'],'dylib',c['C']['path'],c['CSymbol'],'aarch64',str(n),'1','0','16777216'];e=base
     else:argv=[pr['loader']['path'],c[arm]['path'],str(c[arm+'Offset']),'1','aarch64','-',str(n)];e=env
     out,err=led.call(label,argv,e);guard();pair[arm]=csample(out,err,n)if arm=='C'else native(out,err,n)
     if arm=='ON':need(pair['OFF']==pair['ON'],'native status/result/fuel/four terminal arenas exact before C')
    completed.append({'workload':c['workload'],'n':n,'arms':pair});save(O/'comparisons.json',completed)
  need(len(led.rows)==255 and len(completed)==85,'255 calls85triples');ok=True
 except BaseException as ex:save(O/'failure.json',{'exception':repr(ex),'calls':len(led.rows),'completedTriples':len(completed),'policy':'STOP_FIRST_FAILURE_NO_RETRY'});raise
 finally:
  save(O/'report.json',{'status':'PASS_FINITE_LC_REMAINING17_FUNCTIONAL255_ONLY'if ok else'FAIL_FINITE_LC_REMAINING17_FUNCTIONAL255_FIRST_FAILURE','calls':len(led.rows),'completedTriples':len(completed),'joinedOriginal19Calls':285 if ok else None,'retainedAcceptedCalls':30,'nativePairTerminalArenaFuelExact':ok,'CNativeArenas':'unavailable-C/null','producerScope':pr['parentProducerScope'],'timingQualified':False,'officialScore':False,'registerCanaryQualified':False,'comparisons':completed});save(O/'terminal.json',{'calls':len(led.rows),'allCallsClosed':all(r['state']=='terminal'for r in led.rows),'failure':not ok,'noRetry':True})
if __name__=='__main__':main()
