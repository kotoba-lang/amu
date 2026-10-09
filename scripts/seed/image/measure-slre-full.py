#!/usr/bin/env python3
# BOOTSTRAP-TOOL: full pinned regex differential and optional matched C timing.
import argparse,ctypes,hashlib,json,pathlib,re,statistics,subprocess,time
parser=argparse.ArgumentParser();parser.add_argument('directory',type=pathlib.Path);parser.add_argument('--correctness-only',action='store_true');args=parser.parse_args()
p=args.directory.resolve();runner=p.parent/'runner';compiler=p.parent/'images/r6m';up=p.parent/'upstream';output=p/'results.json'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
for name,digest in [('libslre.c','ff918566aa585c665433fecfa1c56ca0136f819df0a5654f2ae98cc696d96056'),('slre.h','87bdc34b18e269c46c13c3e221f2618fa2aac2b4299fe59561810522880e3264')]:
 if sha(up/'src/slre'/name)!=digest:raise SystemExit('unreviewed SLRE profile')
if output.exists():raise SystemExit('refusing to replace evidence')
assert (p/'check.log').read_text().startswith('ok '),'native check did not accept source'
assert (p/'fixture-audit.kotoba').read_text().startswith((p/'slre.kotoba').read_text().replace('(:export [batch test-slre observe bounds-probe])','(:export [batch test-slre observe bounds-probe observe-fixture])',1)), 'stale diagnostic source'
def build(source,stem,symbols):
 with (p/(stem+'-check.log')).open('w') as f:subprocess.run([str(compiler),'check',str(source)],stdout=f,check=True)
 assert (p/(stem+'-check.log')).read_text().startswith('ok ')
 with (p/(stem+'-compile.log')).open('w') as f:subprocess.run([str(compiler),'compile',str(source),'--target','aarch64-macos','--output',str(p/(stem+'.kexe'))],stdout=f,check=True)
 for sym in symbols:
  with (p/(sym+'-extract.log')).open('w') as f:subprocess.run([str(compiler),'extract-native',str(p/(stem+'.kexe')),'--symbol',sym,'--output',str(p/(sym+'.bin'))],stdout=f,check=True)
build(p/'slre.kotoba','slre',['batch','observe','bounds-probe','test-slre'])
build(p/'fixture-audit.kotoba','fixture-audit',['observe-fixture'])
subprocess.run(['clang','-O2','-std=gnu11','-dynamiclib','-I',str(up/'support'),str(p/'c-bridge.c'),'-o',str(p/'c.dylib')],check=True)
c=ctypes.CDLL(str(p/'c.dylib'))
for name in ('observe_fixture','fixture_selfcheck','observe','original_result'):
 fn=getattr(c,name);fn.restype=ctypes.c_int64;fn.argtypes=[ctypes.c_int64]*8
def offset(sym):return re.search(r':offset (\d+)',(p/(sym+'-extract.log')).read_text()).group(1)
def run(kind,sym,n,calls=1,warm=0,fuel=16777216):
 binary=p/(sym+'.bin') if kind=='raw' else p/'c.dylib';entry=offset(sym) if kind=='raw' else sym
 return subprocess.run([str(runner),kind,str(binary),entry,'aarch64',str(n),str(calls),str(warm),str(fuel)],capture_output=True,text=True)
def sample(kind,sym,n,calls=1,warm=0):
 r=run(kind,sym,n,calls,warm);assert r.returncode==0,(sym,n,r.returncode,r.stderr);return json.loads(r.stdout)
def load():return float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1])
report={'format':'amu.slre-full/v1','mode':'correctness-only' if args.correctness_only else 'correctness-and-timing','status':'running','officialEmbenchScore':False,'formalPerfgateQualified':False,'compilerSha256':sha(compiler),'runnerSha256':sha(runner),'sha256':{f:sha(p/f) for f in ('slre.kotoba','batch.bin','fixture-audit.kotoba','observe-fixture.bin','c-bridge.c','c.dylib','fixtures.json')},'upstreamSha256':sha(up/'src/slre/libslre.c'),'clang':subprocess.check_output(['clang','--version'],text=True),'host':subprocess.check_output(['uname','-a'],text=True),'nativeCheck':(p/'check.log').read_text(),'fixtures':[],'cells':[],'productionCells':[],'batches':[],'guards':[],'rows':[]}
def save():output.write_text(json.dumps(report,indent=2)+'\n')
save()
try:
 for i,case in enumerate(json.loads((p/'fixtures.json').read_text())):
  assert c.fixture_selfcheck(i,0,0,0,0,0,0,0)==1,(i,'oracle vs unchanged C')
  for cell in range(805):
   encoded=i*1024+cell;expected=c.observe_fixture(encoded,0,0,0,0,0,0,0)
   answer=sample('raw','observe-fixture',encoded)['result'];assert answer==expected,(i,cell,answer,expected,case)
   report['cells'].append({'case':i,'cell':cell,'Kotoba':answer,'C':expected})
  report['fixtures'].append({'case':i,'unchangedCMatches':True,'result':c.observe_fixture(i*1024+804,0,0,0,0,0,0,0)})
  save();print('case',i,'all 805 initialized state/result cells match',flush=True)
 # The four-match body reuses owned storage; compare only defined final active fields.
 for cell in list(range(12))+[604,605,804]:
  answer=sample('raw','observe',cell)['result'];expected=c.observe(cell,0,0,0,0,0,0,0);assert answer==expected,(cell,answer,expected)
  report['productionCells'].append({'cell':cell,'Kotoba':answer,'C':expected})
 for n in (0,1,2,17,32):
  a=sample('raw','batch',n);b=sample('dylib','batch',n);assert a['result']==b['result']==int(n>0),(n,a,b)
  if n>0:assert c.original_result(n,0,0,0,0,0,0,0)==102
  report['batches'].append({'iterations':n,'Kotoba':a['result'],'C':b['result'],'fuelConsumed':a['contextFuelConsumed']})
 for sym,n,fuel,code in [('bounds-probe',803,16777216,0),('bounds-probe',804,16777216,-4),('batch',1,1,-5)]:
  r=run('raw',sym,n,fuel=fuel);assert r.returncode==code,(sym,n,r.returncode)
  report['guards'].append({'symbol':sym,'input':n,'fuel':fuel,'returncode':r.returncode})
 if args.correctness_only:report.update(status='complete-correctness',performanceMeasured=False)
 else:
  iterations=32;arms=[('Kotoba','raw'),('C','dylib')];counts={}
  for name,kind in arms:
   assert load()<=4,'host too busy for timing';s=sample(kind,'batch',iterations,3,1)
   counts[name]=max(1,round(300000000/(s['elapsedNanoseconds']/3)))
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
  report.update(status='complete-timing',performanceMeasured=True)
except (AssertionError,subprocess.CalledProcessError) as error:
 report['status']='failed';report['failure']={'type':type(error).__name__,'message':str(error)};raise
finally:save()
print('PASS',report['status'],len(report['cells']),'state/result cells',flush=True)
