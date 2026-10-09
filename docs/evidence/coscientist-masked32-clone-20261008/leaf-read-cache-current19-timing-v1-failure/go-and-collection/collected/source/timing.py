"""Prospective bounded SOURCE adapter. No launch without freeze/proofs/reviews/root GO."""
from ledger import *
from statistics_core import full_summary
from campaign_engine import run_finite_engine,quiet_admission
import external_cpu,host_identity,sys,re
from evidence_seal import Seal
D=Path(__file__).resolve().parent
HOST='zebulun@100.66.28.79'
ROOT=Path('/Users/zebulun/github/workspaces/codex/vector-leaf-straight-read-cache-current19-timing-v1-root')
FIELDS={'format','calls','warmupCalls','elapsedNanoseconds','result','maxRssBytes','fuelPerCall','contextFuelBefore','contextFuelAfter','contextFuelConsumed','nativeArtifactAbi','artifactKind','nativeArenaStatus','nativeArenas'}
VARIABLE_FIELDS={'calls','warmupCalls','elapsedNanoseconds','maxRssBytes'}
CAPS=dict(pairs=2097152,stringPoolBytes=65536,vectors=4096,vectorItems=65536)
def load(p):return json.loads(Path(p).read_bytes(),object_pairs_hook=unique)
def unique(ps):
 d={}
 for k,v in ps:need(k not in d,'duplicate JSON key');d[k]=v
 return d
def pin(r):
 p=Path(r['path']);s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size==r['bytes']<=448*1024**2,'exact regular input '+str(p));need(H(p.read_bytes())==r['sha256'],'input hash '+str(p));return p
def bounded_bank(bank,extra):
 refs=[dict(r,path=p)for p,r in bank.items()]+extra
 need(len(refs)<=8192 and sum(r['bytes']for r in refs)<=448*1024**2,'complete logical evidence budget8192/448MiB, no dropping')
 for r in refs:
  p=Path(r['path']);s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size==r['bytes'],'full closure stat before hash')
 for r in refs:pin(r)
 return dict(files=len(refs),bytes=sum(r['bytes']for r in refs))
def sample(out,err,calls,kind,expected):
 need(not err and out.endswith(b'\n')and out.count(b'\n')==1,'exact one telemetry line/empty stderr')
 q=json.loads(out,object_pairs_hook=unique);need(type(q)is dict and set(q)==FIELDS and q['format']=='kotoba.runtime-sample/v1','exact14 telemetry fields')
 for k in ['calls','warmupCalls','elapsedNanoseconds','result','maxRssBytes','fuelPerCall','contextFuelBefore','contextFuelAfter','contextFuelConsumed']:need(type(q[k])is int and 0<=q[k]<2**64,'strictuint64 '+k)
 need(q['calls']==calls and q['warmupCalls']==1 and q['artifactKind']==kind,'exact counter/kind')
 need(q['fuelPerCall']==q['contextFuelBefore']==16777216 and q['nativeArtifactAbi']=='kotoba.native-artifact-i64x8-to-i64-indirect/v1','fuel/ABI')
 if kind=='raw':
  need(0<q['contextFuelAfter']<=16777216 and q['contextFuelConsumed']==16777216-q['contextFuelAfter'] and q['nativeArenaStatus']=='available'and type(q['nativeArenas'])is dict and set(q['nativeArenas'])==set(CAPS),'native fuel/four arenas')
  for k,cap in CAPS.items():
   a=q['nativeArenas'][k];need(type(a)is dict and set(a)=={'capacity','used'} and type(a['capacity'])is int and type(a['used'])is int and a['capacity']==cap and 0<=a['used']<=cap,'strict arena '+k)
 else:need(q['contextFuelAfter']==16777216 and q['contextFuelConsumed']==0 and q['nativeArenaStatus']=='unavailable-C'and q['nativeArenas']is None,'exact C null/noarena nocharge')
 need(type(expected)is dict and set(expected)==FIELDS-VARIABLE_FIELDS,'exact accepted nmax semantic map')
 need({k:v for k,v in q.items()if k not in VARIABLE_FIELDS}==expected,'fresh285 lastcall result/fuel/fourarena exact')
 return q
def authorize(gp,remote=False):
 # Deliberately fails before any operational path until root supplies actual accepted
 # proof and author freezes exact semantic/input/source manifests in this directory.
 pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');g=load(pin(ref(gp)));contract=load(D/'go-schema.json')
 need(set(g)==set(contract['exactLocalFields'])|({'originalLocalGOSHA256'}if remote else set()),'exact root GO fields')
 for k,v in contract['fixedFields'].items():need(type(g[k])is type(v)and g[k]==v,'exact GO '+k)
 for n,key in contract['hashBindings'].items():need(g[key]==ref(D/n)['sha256'],'GO hash '+n)
 for n,r in sp.items():pin(dict(r,path=str(D/n)))
 need(g['sourcePinsSHA256']==ref(D/'source-pins.json')['sha256'],'SOURCE registry GO')
 rv=g['sourceReviews'];need(type(rv)is list and len(rv)==2 and len({r['path']for r in rv})==2 and len({r['sha256']for r in rv})==2,'two distinct SOURCE reviews')
 for r in rv:
  q=load(pin(r));need(q['status']==contract['sourceReviewStatus'],'exact review PASS status')
  for key in contract['hashBindings'].values():need(q[key]==g[key],'review exact SOURCE '+key)
 proof=load(D/'fresh285-binding.json');need(proof['calls']==285 and proof['comparisons']==95 and proof['workloads']==19 and proof['independentlyAccepted']is True,'actual independent fresh285 accepted')
 need(proof['acceptance']==pr['fresh285Acceptance'] and proof['independentReview']==pr['fresh285IndependentReview'],'exact proof contracts')
 pin(dict(proof['acceptance'],path=str(D/'fresh285-acceptance.json')));pin(dict(proof['independentReview'],path=str(D/'fresh285-independent-report.json')))
 need(pr['finalSourceFreeze']is True and pr['operationalAdapterPresent']is True,'final SOURCE freeze prerequisite')
 return g
class Adapter:
 def __init__(self,entries,semantics,led,guard,output,host):self.entries=entries;self.semantics=semantics;self.led=led;self.guard=guard;self.output=output;self.host=host
 def load_query(self,label):
  self.guard();o,e,r=self.led.call(label,['/usr/sbin/sysctl','-n','vm.loadavg'],5,'load');self.guard()
  need(not e and re.fullmatch(rb'\{ ([0-9]+\.[0-9]+) ([0-9]+\.[0-9]+) ([0-9]+\.[0-9]+) \}\n',o),'strict actual Darwin load3')
  return float(o.split()[1]),r
 def run(self,e,arm,count,label):
  self.guard();before,br=self.load_query(label+'-load-before');role={'baseline':'OFF','candidate':'LC','C':'C'}[arm];kind='dylib'if role=='C'else'raw';entry=e['CSymbol']if role=='C'else str(e[role]['offset'])
  argv=[e['runner']['path'],kind,e[role]['path'],entry,'aarch64',str(e['n']),str(count),'1','16777216']
  o,er,r=self.led.call(label,argv,30,'runner');self.guard();after,ar=self.load_query(label+'-load-after')
  # Persist enclosing CPU/load envelope before strict schema or semantic parsing.
  raw=Path(r['stdout']['path']).parent/'envelope.json';activity=external_cpu.background_activity(external_cpu.interval(r['CPUbefore'],r['CPUafter']),r['waitedCPU']['childCpuNs'],self.host['hw.logicalcpu'])
  envelope=dict(runner=r,loadBefore=before,loadAfter=after,beforeLoadReceipt=br,afterLoadReceipt=ar,activity=activity,scope='complete process including startup/warmup; not timed-loop CPU');need(len((json.dumps(envelope,indent=2)+'\n').encode())<=32768,'envelope32KiB');save(raw,envelope)
  q=sample(o,er,count,kind,self.semantics[e['workload']][arm]);quiet=quiet_admission(q,before,after,activity['estimatedBackgroundIdlePercent']);self.guard()
  return q,quiet,ref(raw)['sha256']
 def semantic_guard(self,e,arm,q):
  if arm=='native-pair':need({k:v for k,v in q['baseline'].items()if k not in VARIABLE_FIELDS}=={k:v for k,v in q['candidate'].items()if k not in VARIABLE_FIELDS},'native matched lastcall semantics')
def main():
 need(len(sys.argv)==2 and D==ROOT/'source' and Path.home()==Path('/Users/zebulun'),'selected host/fresh namespace')
 gp=Path(sys.argv[1]);g=authorize(gp,True);gh=ref(gp)['sha256'];pr=load(D/'preregistration.json');semantics=load(D/'expected-semantics.json');bank=load(D/'remote-input-pins.json');extras=[ref(gp)]+g['sourceReviews']+[dict(r,path=str(D/n))for n,r in load(D/'source-pins.json').items()]+[ref(D/'source-pins.json')]
 host=host_identity.current(pr['acceptedHostIdentity']);output=ROOT/'timing'
 seal=Seal([dict(r,path=p)for p,r in bank.items()]+extras);closure=seal.full()
 hostseal=Seal(host_identity.compiler_refs(pr['acceptedHostIdentity']),maximum_files=4,maximum_bytes=512*1024**2);hostclosure=hostseal.full()
 def guard():
  seal.check();hostseal.check();need(host_identity.current(pr['acceptedHostIdentity'])==host,'fresh same host identity stable')

 guard();entries=pr['entries'];need(len(entries)==19 and set(semantics)=={e['workload']for e in entries},'whole19 semantic closure')
 output=ROOT/'timing';need(not output.exists(),'fresh timing no retry');output.mkdir();(output/'tmp').mkdir();save(output/'host-before.json',host);save(output/'input-seal.json',closure);save(output/'compiler-sdk-seal.json',hostclosure)
 env=dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin',LANG='C',LC_ALL='C',TZ='UTC',HOME='/Users/zebulun',TMPDIR=str(output/'tmp'));save(output/'effective-environment.json',dict(environment=env,allInheritedVariablesRemoved=True));led=Ledger(output/'children',env,snapshot=external_cpu.snapshot);adapter=Adapter(entries,semantics,led,guard,output,host);ok=False
 def alarm(signum,frame):raise TimeoutError('absolute campaign172800 seconds')
 signal.signal(signal.SIGALRM,alarm);signal.alarm(172800)
 try:
  def persist(state):
   need(len((json.dumps(state,indent=2)+'\n').encode())<=1048576,'bounded workloadstate1MiB')
   if 'status'in state:
    seal.full();hostseal.full();guard();need(sum(p.stat().st_size for p in output.rglob('*')if p.is_file())<=805306368,'workload finite output768MiB')
   save(output/(state['workload']+'-state.json'),state)
  result=run_finite_engine(entries,adapter.run,adapter.semantic_guard,time.monotonic,persist)
  seal.full();hostseal.full();guard();need(sum(p.stat().st_size for p in output.rglob('*')if p.is_file())<=805306368,'exit output768MiB');need(led.terminal()['allClosed'],'complete process closure');stats=full_summary(result['complete'],[e['workload']for e in entries],g['sourcePinsSHA256'],{e['workload']for e in entries if e['codeChanged']});stats['status']='COMPLETE_ACTUAL_FIXED19'if len(result['complete'])==19 else'PARTIAL_ACTUAL_NO_SUBSET_GM';save(output/'statistics.json',stats);save(output/'host-after.json',host_identity.current(pr['acceptedHostIdentity']));seal.full();hostseal.full();guard();need(sum(p.stat().st_size for p in output.rglob('*')if p.is_file())<=805306368,'final output768MiB');ok=True
 except BaseException as ex:save(output/'failure.json',dict(exception=repr(ex),noRetry=True,firstFailureStop=True));raise
 finally:
  signal.alarm(0);save(output/'terminal.json',dict(**led.terminal(),failure=not ok,closure=closure,sourcePinsSHA256=g['sourcePinsSHA256'],remoteGOSHA256=gh,timingComplete=ok and len(result['complete'])==19 if ok else False,officialScore=False,CIDRuntimeEffect=False,productAdopted=False))
if __name__=='__main__':main()
