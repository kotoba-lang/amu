#!/usr/bin/env python3
# BOOTSTRAP-TOOL: pinned 19-arm preparation and optional quiet-asher paired timing.
import argparse,hashlib,json,pathlib,re,socket,statistics,subprocess,tarfile,time,math
from darwin_cpu_idle import snapshot as cpu_snapshot, interval as cpu_interval
p=argparse.ArgumentParser();p.add_argument('repo',type=pathlib.Path);p.add_argument('environment',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);p.add_argument('--measure',action='store_true');a=p.parse_args();repo=a.repo.resolve();env=a.environment.resolve();out=a.output.resolve()
def require(ok,detail):
 if not ok:raise AssertionError(detail)
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
spec=json.loads((repo/'bench/embench/paired-timing-spec.json').read_text());matrix=json.loads((repo/'bench/embench/comparison-matrix.json').read_text())
require(not out.exists(),'refusing to replace evidence')
# Refuse timing on other hosts before any build/execution or output creation.
if a.measure:require(socket.gethostname().split('.')[0]==spec['host'],'timing host must be asher')
require(sha(repo/'bench/embench/comparison-matrix.json')==spec['matrixSpecSha256'],'matrix spec changed')
compiler=env/'images/r6m';runner=env/'runner';up=env/'upstream';require(sha(compiler)==matrix['compilerSha256'],'selfhost compiler pin');require(sha(runner)==matrix['runnerSha256'],'runner pin')
require(subprocess.check_output(['git','-C',str(up),'rev-parse','HEAD'],text=True).strip()==matrix['upstreamCommit'],'upstream commit')
for f,h in matrix['upstreamSourceSha256'].items():require(sha(up/f)==h,('upstream pin',f))
require(len(spec['entries'])==19 and {e['workload'] for e in spec['entries']}=={e['workload'] for e in matrix['entries']},'19 unique paired workloads')
for e in spec['entries']:
 native=next(x for x in matrix['entries'] if x['workload']==e['workload']);require(native['qualification']=='matched-original-active-profile','unqualified native path');require(sha(repo/native['source'])==native['expectedSourceSha256'],'native source changed');require(sha(repo/e['archive'])==e['archiveSha256'],'C archive changed');require(e['cSymbol']==native['symbol'] and e['iterationsPerCall']==native['iterations'][-1],'arm alignment')
 with tarfile.open(repo/e['archive']) as t:
  for f in e['files']:require(hashlib.sha256(t.extractfile(f['member']).read()).hexdigest()==f['sha256'],'C adapter member changed');require(pathlib.PurePosixPath(f['output']).name==f['output'],'unsafe output filename')
out.mkdir(parents=True);(out/'upstream').symlink_to(up,target_is_directory=True)
report={'format':'amu.embench-paired-timing/v1','status':'running','host':socket.gethostname(),'specSha256':sha(repo/'bench/embench/paired-timing-spec.json'),'matrixSpecSha256':spec['matrixSpecSha256'],'compilerSha256':sha(compiler),'runnerSha256':sha(runner),'clang':subprocess.check_output(['clang','--version'],text=True),'performanceMeasured':False,'officialEmbenchScore':False,'formalPerfgateQualified':False,'ownSource100PercentSelfhostQualified':False,'entries':[],'rows':[]}
def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
def load():return float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1])
def sample(row,arm,calls,warm):
 d=out/row['workload'];kind='raw' if arm=='Kotoba' else 'dylib';binary=d/'native.bin' if arm=='Kotoba' else d/'c.dylib';entry=str(row['offset']) if arm=='Kotoba' else row['cSymbol'];cpu_before=cpu_snapshot() if a.measure else None;q=subprocess.run([str(runner),kind,str(binary),entry,'aarch64',str(row['iterationsPerCall']),str(calls),str(warm),str(matrix['maximumFuel'])],capture_output=True,text=True);require(q.returncode==0,(row['workload'],arm,q.returncode,q.stderr));s=json.loads(q.stdout);
 if a.measure:s['cpuActivityEnvelope']=cpu_interval(cpu_before,cpu_snapshot())
 require(s['result']==1 and s['calls']==calls and s['warmupCalls']==warm,('execution',row['workload'],arm,s));return s
save()
try:
 for e in spec['entries']:
  native=next(x for x in matrix['entries'] if x['workload']==e['workload']);d=out/e['workload'];d.mkdir()
  with tarfile.open(repo/e['archive']) as t:
   for f in e['files']:(d/f['output']).write_bytes(t.extractfile(f['member']).read())
  for label,cmd in [('check',[str(compiler),'check',str(repo/native['source'])]),('compile',[str(compiler),'compile',str(repo/native['source']),'--target','aarch64-macos','--output',str(d/'image.kexe')]),('extract',[str(compiler),'extract-native',str(d/'image.kexe'),'--symbol',native['symbol'],'--output',str(d/'native.bin')])]:
   with (d/(label+'.log')).open('w') as log:subprocess.run(cmd,stdout=log,check=True)
   if label=='check':require((d/'check.log').read_text().startswith('ok '),'native check refused')
  require(sha(d/'native.bin')==native['expectedNativeSha256'],'qualified native bytes changed')
  command=['clang','-O2','-std=gnu11','-dynamiclib','-I',str(up/'support'),str(d/'c-bridge.c'),*[str(up/f) for f in e['extraCFiles']],'-o',str(d/'c.dylib')]
  with (d/'c-build.log').open('w') as log:subprocess.run(command,stdout=log,stderr=log,check=True)
  row={**e,'offset':int(re.search(r':offset (\d+)',(d/'extract.log').read_text()).group(1)),'nativeSha256':sha(d/'native.bin'),'cDylibSha256':sha(d/'c.dylib'),'cBuildCommand':command,'checks':[]}
  for arm in ['Kotoba','C']:
   s=sample(row,arm,2,1);row['checks'].append({'arm':arm,'calls':2,'warmupCalls':1,'result':s['result']})
  report['entries'].append(row);save();print(e['workload'],'paired ABI repeat/warmup PASS',flush=True)
 report['status']='complete-paired-preparation';save()
 if a.measure:
  for row in report['entries']:
   counts={}
   for arm in ['Kotoba','C']:
    require(load()<=spec['maximumLoad'],'host too busy');s=sample(row,arm,3,spec['warmupCalls']);require(s['elapsedNanoseconds']>0,'invalid calibration');counts[arm]=max(1,round(spec['targetIntervalNs']/(s['elapsedNanoseconds']/3)))
   row['calibratedCalls']=counts
   for pair in range(spec['samplesPerArm']):
    for arm in (['Kotoba','C'] if pair%2==0 else ['C','Kotoba']):
     before=load();require(before<=spec['maximumLoad'],'host too busy');s=sample(row,arm,counts[arm],spec['warmupCalls']);after=load();require(after<=spec['maximumLoad'],'host too busy');require(s['elapsedNanoseconds']>=spec['minimumIntervalNs'],'interval too short');report['rows'].append({'workload':row['workload'],'arm':arm,'pair':pair,'calls':counts[arm],'iterationsPerCall':row['iterationsPerCall'],'warmupCalls':spec['warmupCalls'],'elapsedNanoseconds':s['elapsedNanoseconds'],'loadBefore':before,'loadAfter':after,'recordedEpoch':time.time(),'cpuActivityEnvelope':s['cpuActivityEnvelope']});save();require(s['cpuActivityEnvelope']['idlePercent']>=spec['minimumIdlePercent'],'CPU idle below threshold')
    save()
   summary={}
   for arm in ['Kotoba','C']:
    xs=[s['elapsedNanoseconds']/(s['calls']*s['iterationsPerCall']) for s in report['rows'] if s['workload']==row['workload'] and s['arm']==arm];mu=statistics.mean(xs);sd=statistics.stdev(xs);summary[arm]={'meanNsPerBody':mu,'sdNs':sd,'relativeSd':sd/mu,'samples':len(xs)}
   k=summary['Kotoba'];c=summary['C'];summary['KotobaTimeOverC']=k['meanNsPerBody']/c['meanNsPerBody'];summary['stable']=max(k['relativeSd'],c['relativeSd'])<=spec['maximumRelativeSd'];summary['separatedCOrBetter']=summary['stable'] and c['meanNsPerBody']-k['meanNsPerBody']>c['sdNs']+k['sdNs'] and c['meanNsPerBody']/k['meanNsPerBody']>=spec['minimumSpeedup'];row['timingSummary']=summary;save()
  report['performanceMeasured']=True;report['status']='complete-provisional-timing';report['geometricMeanKotobaTimeOverC']=math.exp(statistics.mean(math.log(e['timingSummary']['KotobaTimeOverC']) for e in report['entries']));report['allWorkloadsSeparatedCOrBetter']=all(e['timingSummary']['separatedCOrBetter'] for e in report['entries'])
  # CPU envelope includes warmup/setup, not exact timed boundaries; official scoring remains unqualified.
except (AssertionError,subprocess.CalledProcessError,RuntimeError,ValueError) as error:
 report['status']='failed';report['failure']={'type':type(error).__name__,'message':str(error)};raise
finally:save()
print('PASS',report['status'],len(report['entries']),flush=True)
