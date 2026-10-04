#!/usr/bin/env python3
# BOOTSTRAP-TOOL: revalidate canonical native artifacts; never infer suite timing.
import argparse,hashlib,json,pathlib,re,subprocess,time
p=argparse.ArgumentParser();p.add_argument('repo',type=pathlib.Path);p.add_argument('environment',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);a=p.parse_args();repo=a.repo.resolve();env=a.environment.resolve();out=a.output.resolve()
if out.exists():raise SystemExit('refusing to replace matrix evidence')
spec=json.loads((repo/'bench/embench/comparison-matrix.json').read_text());compiler=env/'images/r6m';runner=env/'runner';up=env/'upstream'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def require(ok,detail):
 if not ok:raise AssertionError(detail)
require(sha(compiler)==spec['compilerSha256'],'compiler pin');require(sha(runner)==spec['runnerSha256'],'runner pin')
require(subprocess.check_output(['git','-C',str(up),'rev-parse','HEAD'],text=True).strip()==spec['upstreamCommit'],'upstream commit')
for f,s in spec['upstreamSourceSha256'].items():require(sha(up/f)==s,('upstream source changed',f))
require(len(spec['entries'])==19 and len({e['workload'] for e in spec['entries']})==19,'exactly 19 workloads')
for e in spec['entries']:require(sha(repo/e['source'])==e['expectedSourceSha256'],('canonical source changed',e['workload']));require((repo/e['evidence']).exists(),('missing prior evidence',e['workload']))
out.mkdir(parents=True)
report={'format':'amu.embench-comparison-matrix-audit/v1','status':'running','createdEpoch':time.time(),'specSha256':sha(repo/'bench/embench/comparison-matrix.json'),'compilerSha256':sha(compiler),'runnerSha256':sha(runner),'upstreamCommit':spec['upstreamCommit'],'entries':[],'wholeSuiteTimingAligned':False,'performanceMeasured':False,'officialEmbenchScore':False,'formalPerfgateQualified':False,'ownSource100PercentSelfhostQualified':False,'rows':[]}
def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
save()
try:
 for e in spec['entries']:
  d=out/e['workload'];d.mkdir();source=repo/e['source'];symbol=e['symbol']
  with (d/'check.log').open('w') as log:subprocess.run([str(compiler),'check',str(source)],stdout=log,check=True)
  require((d/'check.log').read_text().startswith('ok '),('native check refused',e['workload']))
  with (d/'compile.log').open('w') as log:subprocess.run([str(compiler),'compile',str(source),'--target','aarch64-macos','--output',str(d/'image.kexe')],stdout=log,check=True)
  with (d/'extract.log').open('w') as log:subprocess.run([str(compiler),'extract-native',str(d/'image.kexe'),'--symbol',symbol,'--output',str(d/'native.bin')],stdout=log,check=True)
  require(sha(d/'native.bin')==e['expectedNativeSha256'],('canonical native bytes differ from qualified artifact',e['workload'],sha(d/'native.bin'),e['expectedNativeSha256']))
  offset=re.search(r':offset (\d+)',(d/'extract.log').read_text()).group(1);row={**e,'nativeSha256':sha(d/'native.bin'),'nativeBytes':(d/'native.bin').stat().st_size,'offset':int(offset),'runs':[],'guards':[]}
  for n in e['iterations']:
   r=subprocess.run([str(runner),'raw',str(d/'native.bin'),offset,'aarch64',str(n),'1','0',str(spec['maximumFuel'])],capture_output=True,text=True)
   require(r.returncode==0,('execution failure',e['workload'],n,r.returncode,r.stderr));sample=json.loads(r.stdout);want=1 if e['qualification']=='single-body-correctness-only' else int(n>0);require(sample['result']==want,('incorrect result',e['workload'],n,sample['result']));row['runs'].append({'input':n,'result':sample['result'],'fuelConsumed':sample.get('contextFuelConsumed'),'fuelPerCall':spec['maximumFuel']})
  r=subprocess.run([str(runner),'raw',str(d/'native.bin'),offset,'aarch64',str(e['iterations'][-1]),'1','0','1'],capture_output=True,text=True);require(r.returncode==-5,('fuel guard failure',e['workload'],r.returncode));row['guards'].append({'fuel':1,'returncode':r.returncode})
  report['entries'].append(row);save();print(e['workload'],'PASS',e['qualification'],flush=True)
 report['status']='complete-canonical-native-audit';report['nativeCanonicalPaths']=len(report['entries']);report['matchedActiveProfiles']=sum(e['qualification']=='matched-original-active-profile' for e in report['entries']);report['singleBodyPathsNeedingAlignment']=[e['workload'] for e in report['entries'] if e['timingAlignmentPending']]
except (AssertionError,subprocess.CalledProcessError) as error:
 report['status']='failed';report['failure']={'type':type(error).__name__,'message':str(error)};raise
finally:save()
print('PASS',report['nativeCanonicalPaths'],'native paths;',report['matchedActiveProfiles'],'matched profiles; full-suite timing remains unqualified',flush=True)
