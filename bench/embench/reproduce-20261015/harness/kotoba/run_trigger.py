"""Official Embench target API for translated native ports; retain all attempts."""
import argparse,json,os,re,resource,statistics,subprocess,time
from pathlib import Path
from darwin_cpu_idle import snapshot,interval,background_activity
def get_target_args(remnant):
 p=argparse.ArgumentParser();p.add_argument('--samples',type=int,default=1);return p.parse_args(remnant)
_quiet_wait_remaining=120.0

def wait_for_quiet(bench,out,attempt,deadline_seconds=60):
 global _quiet_wait_remaining
 deadline_seconds=min(deadline_seconds,_quiet_wait_remaining)
 if deadline_seconds<=0:
  (out/(bench+'-quiet-'+str(attempt)+'.json')).write_text(json.dumps(dict(workload=bench,attempt=attempt,ready=False,probes=[],reason='campaign-quiet-wait-budget-exhausted'))+'\n')
  return False
 # Outside the timed child invocation. No elapsed measurement is inspected.
 probes=[];consecutive=0;started=time.monotonic()
 while time.monotonic()-started<deadline_seconds:
  load_before=os.getloadavg()[0];before=snapshot();time.sleep(1);after=snapshot()
  activity=interval(before,after);load_after=os.getloadavg()[0]
  quiet=activity['idlePercent']>=70
  consecutive=consecutive+1 if quiet else 0
  probes.append(dict(loadBefore=load_before,loadAfter=load_after,cpuActivity=activity,quiet=quiet,consecutive=consecutive))
  record=dict(workload=bench,attempt=attempt,requiredConsecutive=1,probeSeconds=1,rawIdleMinimumPercent=70,loadInformationalOnly=True,deadlineSeconds=deadline_seconds,elapsedSeconds=time.monotonic()-started,ready=consecutive>=1,probes=probes)
  (out/(bench+'-quiet-'+str(attempt)+'.json')).write_text(json.dumps(record,indent=2)+'\n')
  (out/'progress.json').write_text(json.dumps(dict(workload=bench,phase='quiet-admission',attempt=attempt,consecutive=consecutive,ready=record['ready']))+'\n')
  if record['ready']:
   _quiet_wait_remaining=max(0,_quiet_wait_remaining-(time.monotonic()-started));return True
  time.sleep(min(10,max(0,deadline_seconds-(time.monotonic()-started))))
 _quiet_wait_remaining=max(0,_quiet_wait_remaining-(time.monotonic()-started))
 return False

ARM='official'
CPU_ONLY_REASONS={'quiet-admission-timeout','raw-post-cpu','background-cpu'}
MAX_ATTEMPTS=3

def run_benchmark(bench,path,args):
 assert args.samples==1, 'one first-qualified sample only'
 rows=[];accepted=[];out=Path(path).parents[2]/'raw';out.mkdir(exist_ok=True)
 expected=None
 if ARM=='official':
  ledger=json.loads((Path(__file__).parent/'expected-original-accounting.json').read_text())
  expected=next(e for e in ledger if e['workload']==bench)
 def save():
  selected=next((r['attempt']for r in rows if r['accepted']),None)
  (out/(bench+'.json')).write_text(json.dumps(dict(workload=bench,samples=rows,complete=selected is not None,maxAttempts=3,selectionPolicy='FIRST_CPU_QUALIFIED_NOT_FASTEST',selectedAttempt=selected,cpuOnlyRetries=True,noPilot=True,noOldElapsedReuse=True),indent=2)+'\n')
 for attempt in range(MAX_ATTEMPTS):
  if not wait_for_quiet(bench,out,attempt):
   rows.append(dict(attempt=attempt,accepted=False,reasons=['quiet-admission-timeout'],executed=False,retryEligible=True));save();continue
  load=os.getloadavg()[0];u=resource.getrusage(resource.RUSAGE_CHILDREN);before=snapshot();timeout=None
  try:p=subprocess.run([path],capture_output=True,text=True,timeout=1805 if ARM=='official' else 120)
  except subprocess.TimeoutExpired as ex:
   timeout=ex;p=None
  after=snapshot();v=resource.getrusage(resource.RUSAGE_CHILDREN);cpu=round((v.ru_utime+v.ru_stime-u.ru_utime-u.ru_stime)*1e9);activity=background_activity(interval(before,after),cpu,os.cpu_count());load2=os.getloadavg()[0]
  def text(x):return x.decode()if isinstance(x,bytes)else(x or '')
  stdout=p.stdout if p else text(timeout.stdout);stderr=p.stderr if p else text(timeout.stderr)
  row=dict(attempt=attempt,executed=True,returncode=p.returncode if p else None,stdout=stdout,stderr=stderr,elapsedNs=None,loadBefore=load,loadAfter=load2,cpuActivity=activity,accepted=False,reasons=['pending-parser'],sample=None if ARM=='official'else None)
  rows.append(row);save() # Persist raw/exit/full CPU receipt before parsing or assertions.
  if timeout:
   row.update(reasons=['wall-timeout'],retryEligible=False);save();raise RuntimeError(('NON_CPU_FAILURE_DO_NOT_RETRY',bench,attempt,'wall-timeout'))
  sample=None;elapsed=None;reasons=[]
  if ARM=='official':
   try:sample=json.loads(stdout.splitlines()[-1])
   except (ValueError,IndexError):pass
   row['sample']=sample
   valid=p.returncode==0 and sample and {k:v for k,v in sample.items()if k!='elapsedNs'}==expected['expectedSample'] and stderr==expected['expectedStderr']
   f=re.search(r':status :ok :result 1 .*:fuel \{:initial (\d+) :remaining (\d+)\}',stdout)
   valid=valid and f and int(f[1])==34359738368 and int(f[1])-int(f[2])==sample['benchmarkFuel']+sample['verifyFuel']
   if not valid:reasons.append('execution-or-verification')
   elapsed=sample.get('elapsedNs')if sample else None
  else:
   m=re.fullmatch(r'EMBENCH_NS=(\d+)\n',stdout)
   if p.returncode or stderr or m is None:reasons.append('execution-or-verification')
   elapsed=int(m[1])if m else None
  if not isinstance(elapsed,int)or elapsed<500000000:reasons.append('short-interval')
  if activity['idlePercent']<70:reasons.append('raw-post-cpu')
  if activity['estimatedBackgroundIdlePercent']<70:reasons.append('background-cpu')
  row.update(elapsedNs=elapsed,accepted=not reasons,reasons=reasons,retryEligible=bool(reasons)and set(reasons)<=CPU_ONLY_REASONS);save()
  (out/'progress.json').write_text(json.dumps(dict(workload=bench,attempt=attempt+1,maxAttempts=3,accepted=int(not reasons),selectionPolicy='FIRST_CPU_QUALIFIED_NOT_FASTEST',reasons=reasons))+'\n')
  print('ATTEMPT',bench,attempt+1,'accepted',int(not reasons),'reasons',','.join(reasons),flush=True)
  if not reasons:accepted.append(elapsed);break
  if not row['retryEligible']:raise RuntimeError(('NON_CPU_FAILURE_DO_NOT_RETRY',bench,attempt,reasons))
 save()
 return accepted[0]/1e6 if len(accepted)==1 else None
