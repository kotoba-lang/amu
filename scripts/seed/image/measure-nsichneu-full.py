#!/usr/bin/env python3
# BOOTSTRAP-TOOL: full transition differential; optional matched C timing.
import argparse,ctypes,hashlib,json,pathlib,re,statistics,subprocess,time
parser=argparse.ArgumentParser();parser.add_argument('directory',type=pathlib.Path)
parser.add_argument('--correctness-only',action='store_true');args=parser.parse_args()
p=args.directory.resolve();runner=p.parent/'runner';up=p.parent/'upstream';output=p/'results.json'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(up/'src/nsichneu/libnsichneu.c')=='7d15a238b045f23d5206406fe0d5a15bd4050cf0ccd7e4c3dc49fb71429e2081'
if output.exists():raise SystemExit('refusing to replace evidence')
assert (p/'check.log').read_text().startswith('ok '),'native check did not accept source'
subprocess.run(['clang','-O2','-std=gnu11','-dynamiclib','-I',str(up/'support'),str(p/'c-bridge.c'),'-o',str(p/'c.dylib')],check=True)
c=ctypes.CDLL(str(p/'c.dylib'))
for name in ('stage_cell','oracle_selfcheck'):
 fn=getattr(c,name);fn.restype=ctypes.c_int64;fn.argtypes=[ctypes.c_int64]*8
def offset(symbol):return int(re.search(r':offset (\d+)',(p/(symbol+'-extract.log')).read_text()).group(1))
def run(kind,symbol,n,calls=1,warm=0,fuel=16777216):
 binary=p/(symbol+'.bin') if kind=='raw' else p/'c.dylib'
 entry=str(offset(symbol)) if kind=='raw' else symbol
 return subprocess.run([str(runner),kind,str(binary),entry,'aarch64',str(n),str(calls),str(warm),str(fuel)],capture_output=True,text=True)
def sample(kind,symbol,n,calls=1,warm=0):
 r=run(kind,symbol,n,calls,warm);assert r.returncode==0,(symbol,n,r.returncode,r.stderr);return json.loads(r.stdout)
def load():return float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1])
report={'format':'amu.nsichneu-full/v1','mode':'correctness-only' if args.correctness_only else 'correctness-and-timing','status':'running','officialEmbenchScore':False,'formalPerfgateQualified':False,'compilerSha256':sha(p.parent/'images/r6m'),'runnerSha256':sha(runner),'sourceSha256':sha(p/'nsichneu.kotoba'),'nativeSha256':sha(p/'batch.bin'),'upstreamSha256':sha(up/'src/nsichneu/libnsichneu.c'),'bridgeSha256':sha(p/'c-bridge.c'),'cSha256':sha(p/'c.dylib'),'clang':subprocess.check_output(['clang','--version'],text=True),'host':subprocess.check_output(['uname','-a'],text=True),'nativeCheck':(p/'check.log').read_text(),'oracleSelfchecks':[],'cells':[],'fullChainCells':[],'batches':[],'guards':[],'rows':[]}
def save():output.write_text(json.dumps(report,indent=2)+'\n')
save()
try:
 # A separate untimed export exercises the same production run-full function
 # on seeded inputs; stage-cell normally uses the stoppable diagnostic chain.
 source=(p/'nsichneu.kotoba').read_text();old='done (run-stages seeded stage)'
 assert source.count(old)==1
 (p/'full-audit.kotoba').write_text(source.replace(old,'done (run-full seeded)',1))
 compiler=p.parent/'images/r6m'
 with (p/'full-audit-check.log').open('w') as f:
  subprocess.run([str(compiler),'check',str(p/'full-audit.kotoba')],stdout=f,check=True)
 assert (p/'full-audit-check.log').read_text().startswith('ok ')
 with (p/'full-audit-compile.log').open('w') as f:
  subprocess.run([str(compiler),'compile',str(p/'full-audit.kotoba'),'--target','aarch64-macos','--output',str(p/'full-audit.kexe')],stdout=f,check=True)
 with (p/'full-audit-extract.log').open('w') as f:
  subprocess.run([str(compiler),'extract-native',str(p/'full-audit.kexe'),'--symbol','stage-cell','--output',str(p/'full-audit.bin')],stdout=f,check=True)
 report['fullAuditSourceSha256']=sha(p/'full-audit.kotoba');report['fullAuditNativeSha256']=sha(p/'full-audit.bin')
 for test in range(8):
  check=c.oracle_selfcheck(test,0,0,0,0,0,0,0);assert check==1,(test,check)
  report['oracleSelfchecks'].append({'case':test,'unchangedCFinalStateMatches':True})
  for stage in range(127):
   for cell in range(17):
    encoded=test*4096+stage*17+cell;expected=c.stage_cell(encoded,0,0,0,0,0,0,0)
    answer=sample('raw','stage-cell',encoded)['result'];assert answer==expected,(test,stage,cell,answer,expected)
    report['cells'].append({'case':test,'stage':stage,'cell':cell,'Kotoba':answer,'C':expected})
  for cell in range(17):
   expected=c.stage_cell(test*4096+126*17+cell,0,0,0,0,0,0,0)
   answer=sample('raw','full-audit',test*4096+cell)['result'];assert answer==expected,(test,cell,answer,expected)
   report['fullChainCells'].append({'case':test,'cell':cell,'Kotoba':answer,'C':expected})
  save();print('case',test,'all 127 stages / 2159 cells match',flush=True)
 for n in (0,1,2,17,32):
  a=sample('raw','batch',n);b=sample('dylib','batch',n);assert a['result']==b['result']==int(n>0),(n,a,b)
  report['batches'].append({'iterations':n,'Kotoba':a['result'],'C':b['result'],'fuelConsumed':a['contextFuelConsumed']})
 r=run('raw','batch',1,fuel=1);assert r.returncode==-5,r
 report['guards'].append({'symbol':'batch','input':1,'fuel':1,'returncode':r.returncode});save()
 if args.correctness_only:
  report['status']='complete-correctness';report['performanceMeasured']=False
 else:
  iterations=32;arms=[('Kotoba','raw'),('C','dylib')];counts={}
  for name,kind in arms:
   assert load()<=4,'host too busy for timing'
   s=sample(kind,'batch',iterations,3,1);counts[name]=max(1,round(300000000/(s['elapsedNanoseconds']/3)))
  report.update(iterationsPerCall=iterations,warmupCalls=1,samplesPerArm=30,countByArm=counts)
  for i in range(30):
   for name,kind in arms[i%2:]+arms[:i%2]:
    before=load();assert before<=4,before;s=sample(kind,'batch',iterations,counts[name],1);after=load();assert after<=4,after
    assert s['result']==1 and s['calls']==counts[name] and s['warmupCalls']==1 and s['elapsedNanoseconds']>=50000000,s
    s.update(arm=name,pair=i,loadBefore=before,loadAfter=after,recordedAt=time.time());report['rows'].append(s)
   save()
  report['summary']={}
  for name,_ in arms:
   xs=[s['elapsedNanoseconds']/(s['calls']*iterations) for s in report['rows'] if s['arm']==name];mu=statistics.mean(xs);sd=statistics.stdev(xs)
   report['summary'][name]={'meanNsPerBody':mu,'sdNs':sd,'relativeSd':sd/mu}
  report['summary']['KotobaTimeOverC']=report['summary']['Kotoba']['meanNsPerBody']/report['summary']['C']['meanNsPerBody']
  report['status']='complete-timing';report['performanceMeasured']=True
except (AssertionError,subprocess.CalledProcessError) as error:
 report['status']='failed';report['failure']={'type':type(error).__name__,'message':str(error)};raise
finally:save()
print('PASS',report['status'],len(report['cells']),'state cells',flush=True)
