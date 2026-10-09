"""Inert fresh-consumer SOURCE. Finite functional qualification needs exact root GO."""
from ledger import *
import sys,platform
D=Path(__file__).resolve().parent
HOST='zebulun@100.66.28.79'
ROOT=Path('/Users/zebulun/github/workspaces/codex/vector-leaf-straight-read-cache-fresh-consumer-functional285-v2-root')
BUILD=Path('/Users/zebulun/github/workspaces/codex/vector-leaf-straight-read-cache-current19-build52-v2-root')
CAPS=dict(pairs=2097152,stringPoolBytes=65536,vectors=4096,vectorItems=65536)
FIELDS={'format','calls','warmupCalls','elapsedNanoseconds','result','maxRssBytes','fuelPerCall','contextFuelBefore','contextFuelAfter','contextFuelConsumed','nativeArtifactAbi','artifactKind','nativeArenaStatus','nativeArenas'}
GO_FIELDS={'status','authorized','destination','buildRoot','remoteRoot','outputRoot','sourcePinsSHA256','driverSHA256','launchSHA256','preregistrationSHA256','inputPinsSHA256','remoteInputPinsSHA256','buildAcceptanceSHA256','buildIndependentReportSHA256','maximumChildren','maximumLaunchTransportChildren','functionalAuthorized','timingAuthorized','compilerAuthorized','noRetry','sourceReviews','priorFailedLaunches','priorNativeChildren','maximumCumulativeNativeChildren','maximumCumulativeLaunchChildren'}
def load(p):return json.loads(Path(p).read_bytes())
def sha(p):return H(Path(p).read_bytes())
def pin(r,cap=448*1024**2):
 p=Path(r['path']);s=p.lstat();need(stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size==r['bytes']<=cap,'regular exact bounded input '+str(p));need(sha(p)==r['sha256'],'input SHA '+str(p));return p

def sourceguard():
 for n,r in load(D/'source-pins.json').items():pin(dict(r,path=str(D/n)))
 return sha(D/'source-pins.json')
def unique(ps):
 d={}
 for k,v in ps:need(k not in d,'duplicate JSON key');d[k]=v
 return d
def sample(out,err,n,kind):
 need(not err and out.endswith(b'\n') and out.count(b'\n')==1,'one terminal JSON line and empty stderr')
 q=json.loads(out,object_pairs_hook=unique);need(type(q)is dict and set(q)==FIELDS and q['format']=='kotoba.runtime-sample/v1','exact telemetry schema')
 for k in ['calls','warmupCalls','elapsedNanoseconds','result','maxRssBytes','fuelPerCall','contextFuelBefore','contextFuelAfter','contextFuelConsumed']:need(type(q[k])is int and 0<=q[k]<2**64,'uint64 strict integer '+k)
 need(q['calls']==1 and q['warmupCalls']==0 and q['result']==(0 if n==0 else 1),'unchanged scalar source oracle')
 need(q['fuelPerCall']==q['contextFuelBefore']==16777216 and q['nativeArtifactAbi']=='kotoba.native-artifact-i64x8-to-i64-indirect/v1' and q['artifactKind']==kind,'fuel ABI and artifact kind')
 if kind=='raw':
  need(0<q['contextFuelAfter']<=16777216 and q['contextFuelConsumed']==16777216-q['contextFuelAfter'],'terminal native fuel')
  need(q['nativeArenaStatus']=='available' and type(q['nativeArenas'])is dict and set(q['nativeArenas'])==set(CAPS),'all four terminal arenas')
  for k,cap in CAPS.items():
   a=q['nativeArenas'][k];need(type(a)is dict and set(a)=={'capacity','used'} and type(a['capacity'])is int and type(a['used'])is int and a['capacity']==cap and 0<=a['used']<=cap,'strict terminal arena '+k)
 else:need(q['contextFuelAfter']==16777216 and q['contextFuelConsumed']==0 and q['nativeArenaStatus']=='unavailable-C' and q['nativeArenas']is None,'C no fuel charge and unavailable null arenas')
 return {k:v for k,v in q.items() if k not in ['elapsedNanoseconds','maxRssBytes']}

def authorize(gp,remote=False):
 gp=Path(gp);need(stat.S_ISREG(gp.lstat().st_mode) and gp.lstat().st_size<=1048576 and not gp.is_symlink(),'GO bounded regular');g=load(gp);pr=load(D/'preregistration.json')
 need(set(g)==GO_FIELDS|({'originalLocalGOSHA256'} if remote else set()),'exact GO field schema')
 expected=dict(status=pr['rootGOStatus'],authorized=True,destination=HOST,buildRoot=str(BUILD),remoteRoot=str(ROOT),outputRoot=str(ROOT/'functional285'),maximumChildren=285,maximumLaunchTransportChildren=1,functionalAuthorized=True,timingAuthorized=False,compilerAuthorized=False,noRetry=True,priorFailedLaunches=1,priorNativeChildren=0,maximumCumulativeNativeChildren=285,maximumCumulativeLaunchChildren=2)
 for k,v in expected.items():need(type(g[k])is type(v) and g[k]==v,'exact GO '+k)
 for n,k in [('source-pins.json','sourcePinsSHA256'),('functional285.py','driverSHA256'),('launch.py','launchSHA256'),('preregistration.json','preregistrationSHA256'),('input-pins.json','inputPinsSHA256'),('remote-input-pins.json','remoteInputPinsSHA256'),('build52-acceptance.json','buildAcceptanceSHA256'),('build52-independent-report.json','buildIndependentReportSHA256')]:need(g[k]==sha(D/n),'GO source SHA '+n)
 need(g['sourcePinsSHA256']==sourceguard(),'sourceguard');rv=g['sourceReviews'];need(type(rv)is list and len(rv)==2 and len({r['path'] for r in rv})==2 and len({r['sha256'] for r in rv})==2,'two distinct exact SOURCE reviews')
 for r in rv:
  q=load(pin(r,1048576));need(q['status']==pr['sourceReviewStatus'],'SOURCE PASS status')
  for k in ['sourcePinsSHA256','driverSHA256','launchSHA256','preregistrationSHA256','inputPinsSHA256','remoteInputPinsSHA256']:need(q[k]==g[k],'review exact binding '+k)
 a=load(D/'build52-acceptance.json');b=load(D/'build52-independent-report.json')
 need(g['buildAcceptanceSHA256']==pr['buildAcceptance']['sha256'] and g['buildIndependentReportSHA256']==pr['buildIndependentReview']['sha256'],'accepted proof SHA')
 need(a['status']=='ROOT_ACCEPTED_INDEPENDENT_LC_FRESH_C19_CONSUMER19_BUILD52_IDENTITY_ONLY' and a['independentActualReceipt']==pr['buildIndependentReview'] and [a[k] for k in ['closedChildren','CBuilds','consumerBuilds','identityQueries']]==[52,19,19,14],'root accepted exact52')
 need(b['status']=='PASS_ACTUAL_BUILD52_V2_INDEPENDENT_SAVED_RAW_IDENTITY_ONLY' and b['allClosed']is True and b['images']==[c['buildAnchors'] for c in pr['cases']],'independent whole image anchors')
 proof=load(pin(dict(path=str(D/'prior-launch-proof.json'),bytes=pr['priorLaunchProof']['bytes'],sha256=pr['priorLaunchProof']['sha256'])))
 need(proof['status']=='PRESERVED_V1_CLOSED_FAILED_LAUNCH1_PRE_NATIVE_MISSING_SYNTHETIC_RECEIPT' and proof['closedLaunchChildren']==1 and proof['remoteNativeChildrenStarted']==0 and proof['failureRemainsFailure']is True and proof['noRetryV1']is True and proof['remoteSealPresent']is False,'retained prior failed launch1/native0')
 binding=pr['syntheticReceiptBinding'];need(binding['remotePath']==str(ROOT/'source/collection-receipt.json') and binding['sourceFilename']=='collection-receipt.json','explicit synthetic receipt role')
 pin(dict(path=str(D/'collection-receipt.json'),**binding['receipt']))
 failureproof=load(pin(dict(path=str(D/'prior-failure-independent-report.json'),**pr['priorIndependentFailureReview']['receipt'])))
 need(failureproof['status']=='PASS_INDEPENDENT_SAVED_FAILURE_LC_FRESH_CONSUMER_FUNCTIONAL285_V1_PRE_NATIVE_ONLY' and failureproof['launchChildren']==1 and failureproof['launchAllClosed']is True and failureproof['nativeFunctionalChildren']==0 and failureproof['completedTriples']==0 and failureproof['functionalQualified']is False,'independent actual V1 failed pre-native only')
 return g

def bounded_bank(bank,extra):
 refs=[dict(r,path=p) for p,r in bank.items()]+extra
 need(len(refs)<=4096 and sum(r['bytes'] for r in refs)<=448*1024**2,'full finite evidence closure cap; no silent dropping or dedupe')
 total=0
 for r in refs:
  p=Path(r['path']);s=p.lstat();need(stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size==r['bytes'],'stat before aggregate hash');total+=s.st_size
 need(total<=448*1024**2,'aggregate stat before hash')
 for r in refs:pin(r)
 return dict(files=len(refs),bytes=total)

def main():
 need(len(sys.argv)==2 and D==ROOT/'source' and Path.home()==Path('/Users/zebulun') and platform.machine()=='arm64' and platform.system()=='Darwin','same accepted native arm64 host with fresh source namespace')
 gp=Path(sys.argv[1]);g=authorize(gp,True);gh=sha(gp);pr=load(D/'preregistration.json');bank=load(D/'remote-input-pins.json')
 extras=[ref(gp)]+g['sourceReviews']+[dict(r,path=str(D/n)) for n,r in load(D/'source-pins.json').items()]+[ref(D/'source-pins.json')]
 def guard():
  need(sha(gp)==gh,'GO unchanged');authorize(gp,True);return bounded_bank(bank,extras)
 closure=guard();need(len(pr['cases'])==19 and sum(len(c['profiles']) for c in pr['cases'])==95,'whole original19/95 profiles')
 for c in pr['cases']:
  for role in ['OFF','LC','OFFContainer','LCContainer','C','runner','header']:pin(c[role])
  for arm in ['OFF','LC']:
   raw=pin(c[arm]).read_bytes();head,payload=pin(c[arm+'Container']).read_bytes().split(b'\n\n',1);lines=head.decode('ascii').splitlines()
   need(lines[0]==f'KSEED1 {len(payload)} {len(lines)-1}' and payload==raw and f"{c['symbol']} {c[arm]['offset']} 1" in lines[1:],'full container/native/export unchanged')
 output=ROOT/'functional285';need(not output.exists(),'fresh output no retry');output.mkdir();(output/'tmp').mkdir()
 env=dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin',LANG='C',LC_ALL='C',TZ='UTC',HOME='/Users/zebulun',TMPDIR=str(output/'tmp'))
 save(output/'effective-environment.json',dict(environment=env,allInheritedVariablesRemoved=True));led=Ledger(output/'children',285,env);done=[];ok=False
 def alarm(signum,frame):raise TimeoutError('whole functional285 deadline')
 signal.signal(signal.SIGALRM,alarm);signal.alarm(9300)
 try:
  for c in pr['cases']:
   for n in c['profiles']:
    pair={}
    for arm in ['OFF','LC','C']:
     guard();kind='dylib' if arm=='C' else 'raw';entry=c['CSymbol'] if arm=='C' else str(c[arm]['offset']);artifact=c['C'] if arm=='C' else c[arm]
     argv=[c['runner']['path'],kind,artifact['path'],entry,'aarch64',str(n),'1','0','16777216']
     out,err,row=led.call(c['workload']+'-'+arm+'-n'+str(n),argv,30);guard();pair[arm]=sample(out,err,n,kind)
     if arm=='LC':need(pair['OFF']==pair['LC'],'exact semantic/fuel/four terminal arena parity before C')
    done.append(dict(workload=c['workload'],n=n,arms=pair));save(output/'comparisons.json',done)
  need(len(led.rows)==285 and len(done)==95 and led.terminal()['allClosed'],'all285 closed/95 triples without skip');ok=True
 except BaseException as ex:save(output/'failure.json',dict(exception=repr(ex),calls=len(led.rows),completedTriples=len(done),policy='STOP_FIRST_FAILURE_NO_RETRY'));raise
 finally:
  signal.alarm(0)
  save(output/'report.json',dict(status='PASS_FRESH_CONSUMER_ORIGINAL19_FUNCTIONAL285_V2_ONLY' if ok else 'FAIL_FRESH_CONSUMER_FUNCTIONAL285_V2_FIRST_FAILURE',calls=len(led.rows),completedTriples=len(done),nativeFuelAndFourTerminalArenaPairExact=ok,CNativeArenas='unavailable-C/null',timingQualified=False,quietQualified=False,registerCanaryQualified=False,SDKWholeTreeHashQualified=False,compilerCalls=0,C2skip=False,noRetry=True,priorFailedLaunches=1,priorNativeChildren=0,cumulativeNativeChildren=len(led.rows),maximumCumulativeNativeChildren=285,cumulativeLaunchChildren=2,sourcePinsSHA256=g['sourcePinsSHA256'],buildAcceptanceSHA256=g['buildAcceptanceSHA256'],remoteGOSHA256=gh,closure=closure,comparisons=done))
  save(output/'terminal.json',dict(**led.terminal(),failure=not ok,noRetry=True))
if __name__=='__main__':main()
