#!/usr/bin/env python3
# Bootstrap-only diagnostic tooling; product execution remains native selfhost.
import hashlib,json,os,pathlib,resource,socket,statistics,subprocess,sys
from darwin_cpu_idle import snapshot,interval,background_activity
root,runner,specpath,out=map(pathlib.Path,sys.argv[1:])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,msg):
 if not ok:raise AssertionError(msg)
manifest=json.loads((root/'manifest.json').read_text());spec=json.loads(specpath.read_text())
require(socket.gethostname().split('.')[0]==spec['host'],'wrong host')
require(sha(root/'native.bin')==manifest['nativeSha256'],'native pin')
require(sha(runner)==manifest['runnerSha256'],'runner pin')
require(not out.exists(),'preserve evidence')
out.mkdir();report={'format':'amu.native-cumulative-phase-timing/v1','status':'running','manifest':manifest,'spec':spec,'specSha256':sha(specpath),'host':socket.gethostname(),'rows':[],'calibrationRows':[],'officialEmbenchScore':False,'completeWorkloadBenchmark':False,'description':'Cumulative diagnostic phases; only bench executes canonical full workload. Differences are not exclusive component timings.'}
def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
def load():return float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1])
def sample(arm,calls,capture=False):
 if capture:usage=resource.getrusage(resource.RUSAGE_CHILDREN);before=snapshot()
 q=subprocess.run([str(runner),'raw',str(root/'native.bin'),str(manifest['offsets'][arm]),'aarch64','32',str(calls),str(spec['warmupCalls']),'16777216'],capture_output=True,text=True)
 require(q.returncode==0,(arm,q.returncode,q.stderr));s=json.loads(q.stdout)
 require(s['result']==1 and s['calls']==calls and s['warmupCalls']==spec['warmupCalls'],'incorrect result')
 expected=next(c['fuel'] for c in manifest['checks'] if c['symbol']==arm and c['n']==32)
 require(s['contextFuelConsumed']==expected,'diagnostic fuel changed')
 if capture:
  activity=interval(before,snapshot());after=resource.getrusage(resource.RUSAGE_CHILDREN)
  ns=round(((after.ru_utime+after.ru_stime)-(usage.ru_utime+usage.ru_stime))*1e9)
  s['cpuActivityEnvelope']=background_activity(activity,ns,os.cpu_count())
 return s
save()
try:
 arms=list(manifest['offsets']);counts={}
 for arm in arms:
  calls=3
  for attempt in range(5):
   s=sample(arm,calls);elapsed=s['elapsedNanoseconds'];require(elapsed>0,'invalid calibration')
   report['calibrationRows'].append({**s,'arm':arm,'attempt':attempt});save()
   if spec['targetIntervalNs']*.75<=elapsed<=spec['targetIntervalNs']*1.5:break
   calls=max(1,min(100000000,round(calls*spec['targetIntervalNs']/elapsed)))
  else:raise AssertionError('calibration failed: '+arm)
  counts[arm]=calls
 report['callsByArm']=counts;accepted=0
 for attempt in range(spec['maximumPairAttempts']):
  rows=[]
  for arm in arms[attempt%3:]+arms[:attempt%3]:
   before=load();s=sample(arm,counts[arm],True);after=load();reasons=[]
   if max(before,after)>spec['maximumLoad']:reasons.append('host-load')
   if s['elapsedNanoseconds']<spec['minimumIntervalNs']:reasons.append('short-interval')
   if s['cpuActivityEnvelope']['estimatedBackgroundIdlePercent']<spec['minimumBackgroundIdlePercent']:reasons.append('background-cpu')
   row={**s,'arm':arm,'attempt':attempt,'loadBefore':before,'loadAfter':after,'rejectionReasons':reasons,'accepted':False};rows.append(row);report['rows'].append(row);save()
  qualified=all(not row['rejectionReasons'] for row in rows)
  for row in rows:row['accepted']=qualified
  accepted+=int(qualified);report.update(acceptedTriples=accepted,attemptedTriples=attempt+1);save()
  if accepted==spec['samplesPerArm']:break
 require(accepted==spec['samplesPerArm'],'insufficient quiet triples')
 summary={}
 for arm in arms:
  xs=[r['elapsedNanoseconds']/(r['calls']*32) for r in report['rows'] if r['arm']==arm and r['accepted']];mu=statistics.mean(xs);sd=statistics.stdev(xs)
  summary[arm]={'meanNsPerBody':mu,'sdNs':sd,'relativeSd':sd/mu,'samples':len(xs)}
 require(max(s['relativeSd'] for s in summary.values())<=spec['maximumRelativeSd'],'unstable timing')
 report.update(status='complete-diagnostic-timing',summary=summary)
except Exception as e:
 report.update(status='failed',failure={'type':type(e).__name__,'message':str(e)});raise
finally:save()
print(json.dumps(report['summary'],indent=2),flush=True)
