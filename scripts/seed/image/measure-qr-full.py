#!/usr/bin/env python3
# BOOTSTRAP-TOOL: full active-profile selfhost QR differential and C timing.
import argparse,ctypes,hashlib,json,pathlib,re,statistics,subprocess,time
parser=argparse.ArgumentParser();parser.add_argument('directory',type=pathlib.Path);parser.add_argument('--correctness-only',action='store_true');args=parser.parse_args();p=args.directory.resolve();runner=p.parent/'runner';compiler=p.parent/'images/r6m';up=p.parent/'upstream';out=p/'results.json'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
if out.exists():raise SystemExit('refusing to replace evidence')
profile=json.loads((p/'profile.json').read_text())
for f,d in profile['sourcePins'].items():
 if sha(up/'src/qrduino'/f)!=d:raise SystemExit('unreviewed QR full profile: '+f)
def require(ok,detail):
 if not ok:raise AssertionError(detail)
report={'format':'amu.qr-full/v1','mode':'correctness-only' if args.correctness_only else 'correctness-and-timing','status':'running','completeActiveWorkload':False,'performanceMeasured':False,'officialEmbenchScore':False,'formalPerfgateQualified':False,'compilerSha256':sha(compiler),'runnerSha256':sha(runner),'sourcePins':profile['sourcePins'],'clang':subprocess.check_output(['clang','--version'],text=True),'host':subprocess.check_output(['uname','-a'],text=True),'oracleSelfchecks':[],'cells':[],'repeatCells':[],'batches':[],'guards':[],'rows':[]}
def save():out.write_text(json.dumps(report,indent=2)+'\n')
def offset(sym):return re.search(r':offset (\d+)',(p/(sym+'-extract.log')).read_text()).group(1)
def run(kind,sym,n,calls=1,warm=0,fuel=16777216):
 binary=p/(sym+'.bin') if kind=='raw' else p/'c.dylib';entry=offset(sym) if kind=='raw' else sym
 return subprocess.run([str(runner),kind,str(binary),entry,'aarch64',str(n),str(calls),str(warm),str(fuel)],capture_output=True,text=True)
def sample(kind,sym,n,calls=1,warm=0):
 r=run(kind,sym,n,calls,warm);require(r.returncode==0,(sym,n,r.returncode,r.stderr));return json.loads(r.stdout)
def load():return float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1])
save()
try:
 with (p/'check.log').open('w') as f:subprocess.run([str(compiler),'check',str(p/'qr-full.kotoba')],stdout=f,check=True)
 require((p/'check.log').read_text().startswith('ok '),'native check refused')
 with (p/'compile.log').open('w') as f:subprocess.run([str(compiler),'compile',str(p/'qr-full.kotoba'),'--target','aarch64-macos','--output',str(p/'qr.kexe')],stdout=f,check=True)
 for sym in ('batch','observe','repeat-observe','bounds-probe'):
  with (p/(sym+'-extract.log')).open('w') as f:subprocess.run([str(compiler),'extract-native',str(p/'qr.kexe'),'--symbol',sym,'--output',str(p/(sym+'.bin'))],stdout=f,check=True)
 subprocess.run(['clang','-O2','-std=gnu11','-dynamiclib','-I',str(up/'support'),str(p/'c-bridge.c'),str(up/'src/qrduino/qrframe.c'),str(up/'support/beebsc.c'),'-o',str(p/'c.dylib')],check=True)
 report['sha256']={f:sha(p/f) for f in ('qr-full.kotoba','batch.bin','observe.bin','repeat-observe.bin','bounds-probe.bin','c-bridge.c','c.dylib','profile.json')}
 c=ctypes.CDLL(str(p/'c.dylib'))
 for name in ('observe','repeat_observe','oracle_selfcheck','original_repeat_selfcheck'):
  f=getattr(c,name);f.restype=ctypes.c_int64;f.argtypes=[ctypes.c_int64]*8
 for case in range(4):
  require(c.oracle_selfcheck(case,0,0,0,0,0,0,0)==1,('unchanged qrencode',case));report['oracleSelfchecks'].append({'case':case,'unchangedQrencodeMatches':True})
 for n in (1,2,17,32):
  require(c.original_repeat_selfcheck(n,0,0,0,0,0,0,0)==1,('unchanged benchmark_body/verify',n));report['oracleSelfchecks'].append({'iterations':n,'unchangedBenchmarkBodyAndVerifyMatch':True})
 image=list(range(100))+list(range(768,868));final=profile['fields']+list(range(1780,1788))+[1790,1791,1792]
 for case in range(4):
  for stage in range(10):
   cells=final if stage==9 else image+([1780+stage-1] if stage else [])
   for cell in cells:
    encoded=case*1048576+stage*2048+cell;v=sample('raw','observe',encoded)['result'];w=c.observe(encoded,0,0,0,0,0,0,0);require(v==w,(case,stage,cell,v,w))
    report['cells'].append({'case':case,'stage':stage,'cell':cell,'Kotoba':v,'C':w})
   save();print('case',case,'stage',stage,len(cells),'cells match',flush=True)
 for n in (1,2,17,32):
  for cell in final:
   encoded=n*2048+cell;v=sample('raw','repeat-observe',encoded)['result'];w=c.repeat_observe(encoded,0,0,0,0,0,0,0);require(v==w,('repeat',n,cell,v,w));report['repeatCells'].append({'iterations':n,'cell':cell,'Kotoba':v,'C':w})
  save();print('repeat',n,len(final),'cells match',flush=True)
 for n in (0,1,2,17,32):
  a=sample('raw','batch',n);b=sample('dylib','batch',n);require(a['result']==b['result']==int(n>0),(n,a,b));report['batches'].append({'iterations':n,'Kotoba':a['result'],'C':b['result'],'fuelConsumed':a['contextFuelConsumed']})
 for sym,n,fuel,code in [('bounds-probe',2047,16777216,0),('bounds-probe',2048,16777216,-4),('batch',1,1,-5)]:
  r=run('raw',sym,n,fuel=fuel);require(r.returncode==code,(sym,n,r.returncode));report['guards'].append({'symbol':sym,'input':n,'fuel':fuel,'returncode':r.returncode})
 report['completeActiveWorkload']=True
 if args.correctness_only:report['status']='complete-correctness'
 else:
  iterations=32;arms=[('Kotoba','raw'),('C','dylib')];counts={}
  for name,kind in arms:
   require(load()<=4,'host too busy for timing');s=sample(kind,'batch',iterations,3,1);counts[name]=max(1,round(300000000/(s['elapsedNanoseconds']/3)))
  report.update(iterationsPerCall=iterations,warmupCalls=1,samplesPerArm=30,countByArm=counts)
  for i in range(30):
   for name,kind in arms[i%2:]+arms[:i%2]:
    before=load();require(before<=4,before);s=sample(kind,'batch',iterations,counts[name],1);after=load();require(after<=4,after)
    require(s['result']==1 and s['calls']==counts[name] and s['warmupCalls']==1 and s['elapsedNanoseconds']>=50000000,s)
    s.update(arm=name,pair=i,loadBefore=before,loadAfter=after,recordedAt=time.time());report['rows'].append(s)
   save()
  report['summary']={}
  for name,_ in arms:
   xs=[s['elapsedNanoseconds']/(s['calls']*iterations) for s in report['rows'] if s['arm']==name];mu=statistics.mean(xs);sd=statistics.stdev(xs);report['summary'][name]={'meanNsPerBody':mu,'sdNs':sd,'relativeSd':sd/mu}
  report['summary']['KotobaTimeOverC']=report['summary']['Kotoba']['meanNsPerBody']/report['summary']['C']['meanNsPerBody'];report.update(status='complete-timing',performanceMeasured=True)
except (AssertionError,subprocess.CalledProcessError) as error:
 report['status']='failed';report['failure']={'type':type(error).__name__,'message':str(error)};raise
finally:save()
print('PASS',report['status'],len(report['cells']),len(report['repeatCells']),flush=True)
