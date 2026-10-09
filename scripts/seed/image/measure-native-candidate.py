#!/usr/bin/env python3
# BOOTSTRAP-TOOL: prospective three-arm native-code hypothesis experiment.
import argparse,hashlib,json,math,os,pathlib,resource,socket,statistics,subprocess,time
from darwin_cpu_idle import snapshot,interval,background_activity
p=argparse.ArgumentParser();p.add_argument('baseline',type=pathlib.Path);p.add_argument('candidate',type=pathlib.Path);p.add_argument('runner',type=pathlib.Path);p.add_argument('spec',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);a=p.parse_args()
def require(ok,detail):
 if not ok:raise AssertionError(detail)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
spec=json.loads(a.spec.read_text());manifest=json.loads((a.candidate/'manifest.json').read_text());baseline=json.loads((a.baseline/'results.json').read_text())
require(socket.gethostname().split('.')[0]==spec['host'],'wrong timing host');require(not a.output.exists(),'refusing to replace evidence')
require(baseline['status']=='complete-provisional-timing','incomplete baseline');require(sha(a.runner)==baseline['runnerSha256'],'runner pin')
entry=next(e for e in baseline['entries'] if e['workload']==manifest['workload']);d=a.baseline/entry['workload']
require(sha(d/'native.bin')==entry['nativeSha256'],'baseline machine pin');require(sha(d/'c.dylib')==entry['cDylibSha256'],'C machine pin');require(sha(a.candidate/'native.bin')==manifest['nativeSha256'],'candidate machine pin')
require(manifest['sourceSha256']==manifest['baselineSourceSha256'],'source changed');require(len(set(manifest['compilerGenerationSha256'].values()))==1,'candidate compiler not a fixed point')
matrix_path=a.spec.parent/'comparison-matrix.json';require(sha(matrix_path)==baseline['matrixSpecSha256'],'baseline matrix pin')
matrix=json.loads(matrix_path.read_text());native=next(e for e in matrix['entries'] if e['workload']==manifest['workload'])
require(manifest['sourceSha256']==native['expectedSourceSha256'],'candidate source not canonical')
arms={'baseline':('raw',d/'native.bin',str(entry['offset'])),'candidate':('raw',a.candidate/'native.bin',str(manifest['offset'])),'C':('dylib',d/'c.dylib',entry['cSymbol'])}
report={'status':'running','format':'amu.native-candidate-timing/v1','host':socket.gethostname(),'specSha256':sha(a.spec),'manifest':manifest,'baselineResultsSha256':sha(a.baseline/'results.json'),'runnerSha256':sha(a.runner),'rows':[],'officialEmbenchScore':False,'formalPerfgateQualified':False,'performanceMeasured':False}
a.output.mkdir()
def save():(a.output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
def load():return float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1])
def sample(arm,calls,capture=False):
 kind,binary,symbol=arms[arm]
 if capture:usage=resource.getrusage(resource.RUSAGE_CHILDREN);before=snapshot()
 q=subprocess.run([str(a.runner),kind,str(binary),symbol,'aarch64',str(entry['iterationsPerCall']),str(calls),str(spec['warmupCalls']),'16777216'],capture_output=True,text=True)
 require(q.returncode==0,(arm,q.returncode,q.stderr));s=json.loads(q.stdout)
 require(s['result']==1 and s['calls']==calls and s['warmupCalls']==spec['warmupCalls'],'incorrect sample')
 if capture:
  activity=interval(before,snapshot());after=resource.getrusage(resource.RUSAGE_CHILDREN)
  ns=round(((after.ru_utime+after.ru_stime)-(usage.ru_utime+usage.ru_stime))*1e9)
  s['cpuActivityEnvelope']=background_activity(activity,ns,os.cpu_count())
 return s
save()
try:
 counts={};report['calibrationRows']=[]
 for arm in arms:
  calls=3
  for calibration_attempt in range(5):
   s=sample(arm,calls);elapsed=s['elapsedNanoseconds'];require(elapsed>0,'invalid calibration')
   report['calibrationRows'].append({**s,'arm':arm,'calibrationAttempt':calibration_attempt});save()
   if spec['targetIntervalNs']*.75<=elapsed<=spec['targetIntervalNs']*1.5:break
   calls=max(1,min(100000000,round(calls*spec['targetIntervalNs']/elapsed)))
  else:raise AssertionError('calibration failed within five attempts: '+arm)
  counts[arm]=calls
 report['callsByArm']=counts;accepted=0;order=list(arms)
 for attempt in range(spec['maximumPairAttempts']):
  rows=[]
  for arm in order[attempt%3:]+order[:attempt%3]:
   before=load();s=sample(arm,counts[arm],True);after=load();reasons=[]
   if max(before,after)>spec['maximumLoad']:reasons.append('host-load')
   if s['elapsedNanoseconds']<spec['minimumIntervalNs']:reasons.append('short-interval')
   if s['cpuActivityEnvelope']['estimatedBackgroundIdlePercent']<spec['minimumBackgroundIdlePercent']:reasons.append('background-cpu')
   row={**s,'arm':arm,'attempt':attempt,'accepted':False,'rejectionReasons':reasons,'loadBefore':before,'loadAfter':after};rows.append(row);report['rows'].append(row);save()
  qualified=all(not row['rejectionReasons'] for row in rows)
  for row in rows:row['accepted']=qualified
  accepted+=int(qualified);report.update(acceptedTriples=accepted,attemptedTriples=attempt+1);save()
  if accepted==spec['samplesPerArm']:break
 require(accepted==spec['samplesPerArm'],'not enough quiet triples within fixed attempt limit')
 summary={}
 for arm in arms:
  xs=[row['elapsedNanoseconds']/(row['calls']*entry['iterationsPerCall']) for row in report['rows'] if row['arm']==arm and row['accepted']];mu=statistics.mean(xs);sd=statistics.stdev(xs)
  summary[arm]={'meanNsPerBody':mu,'sdNs':sd,'relativeSd':sd/mu,'samples':len(xs)}
 b=summary['baseline'];c=summary['candidate'];ref=summary['C'];stable=max(s['relativeSd'] for s in summary.values())<=spec['maximumRelativeSd']
 report['summary']={**summary,'stable':stable,'baselineOverCandidate':b['meanNsPerBody']/c['meanNsPerBody'],'candidateOverC':c['meanNsPerBody']/ref['meanNsPerBody'],'candidateImprovesBaseline':stable and b['meanNsPerBody']/c['meanNsPerBody']>=spec['minimumSpeedup'] and b['meanNsPerBody']-c['meanNsPerBody']>b['sdNs']+c['sdNs']}
 report.update(status='complete-provisional-candidate-timing',performanceMeasured=True)
except (AssertionError,subprocess.CalledProcessError,ValueError,RuntimeError) as error:
 report.update(status='failed',failure={'type':type(error).__name__,'message':str(error)});raise
finally:save()
print(json.dumps(report['summary'],indent=2),flush=True)
