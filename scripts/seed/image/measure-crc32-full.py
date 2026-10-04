#!/usr/bin/env python3
# BOOTSTRAP-TOOL: complete CRC differentials and optional quiet-asher paired timing.
import argparse,ctypes,hashlib,json,pathlib,re,statistics,subprocess,time,socket
parser=argparse.ArgumentParser();parser.add_argument('directory',type=pathlib.Path);parser.add_argument('--measure',action='store_true');args=parser.parse_args();p=args.directory.resolve();env=p.parent;compiler=env/'images/r6m';runner=env/'runner';up=env/'upstream';out=p/'results.json'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def require(ok,detail):
 if not ok:raise AssertionError(detail)
if out.exists():raise SystemExit('refusing to replace evidence')
profile=json.loads((p/'profile.json').read_text())
for f,s in profile['sourcePins'].items():require(sha(up/f)==s,('unreviewed CRC profile',f))
require(sha(compiler)=='abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e','selfhost compiler pin');require(sha(runner)=='a1b8778cf9af255f66bba3e3cad20e3baadd9653e18defe429bfa179840665ac','runner pin')
report={'format':'amu.crc32-full/v1','status':'running','completeActiveWorkload':False,'performanceMeasured':False,'officialEmbenchScore':False,'formalPerfgateQualified':False,'compilerSha256':sha(compiler),'runnerSha256':sha(runner),'sourcePins':profile['sourcePins'],'representation':profile['representation'],'host':socket.gethostname(),'oracleSelfchecks':[],'cells':[],'batches':[],'guards':[],'rows':[]}
def save():out.write_text(json.dumps(report,indent=2)+'\n')
def run(kind,symbol,n,calls=1,warm=0,fuel=16777216):
 binary=p/(symbol+'.bin') if kind=='raw' else p/'c.dylib';entry=re.search(r':offset (\d+)',(p/(symbol+'-extract.log')).read_text()).group(1) if kind=='raw' else symbol.replace('-','_')
 return subprocess.run([str(runner),kind,str(binary),entry,'aarch64',str(n),str(calls),str(warm),str(fuel)],capture_output=True,text=True)
def sample(kind,symbol,n,calls=1,warm=0):
 r=run(kind,symbol,n,calls,warm);require(r.returncode==0,(kind,symbol,n,r.returncode,r.stderr));return json.loads(r.stdout)
def load():return float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1])
save()
try:
 with (p/'check.log').open('w') as log:subprocess.run([str(compiler),'check',str(p/'crc32-full.kotoba')],stdout=log,check=True)
 require((p/'check.log').read_text().startswith('ok '),'native check refused')
 with (p/'compile.log').open('w') as log:subprocess.run([str(compiler),'compile',str(p/'crc32-full.kotoba'),'--target','aarch64-macos','--output',str(p/'crc.kexe')],stdout=log,check=True)
 for name in ('bench','prefix-crc','prefix-seed','table-entry'):
  with (p/(name+'-extract.log')).open('w') as log:subprocess.run([str(compiler),'extract-native',str(p/'crc.kexe'),'--symbol',name,'--output',str(p/(name+'.bin'))],stdout=log,check=True)
 subprocess.run(['clang','-O2','-std=gnu11','-dynamiclib','-I',str(up/'support'),str(p/'c-bridge.c'),'-o',str(p/'c.dylib')],check=True)
 report['sha256']={f:sha(p/f) for f in ('crc32-full.kotoba','bench.bin','c-bridge.c','profile.json','c.dylib')}
 c=ctypes.CDLL(str(p/'c.dylib'))
 for name in ('bench','prefix_crc','prefix_seed','table_entry','oracle_selfcheck'):
  f=getattr(c,name);f.restype=ctypes.c_int64;f.argtypes=[ctypes.c_int64]*8
 for n in (1,2,17,32):require(c.oracle_selfcheck(n,0,0,0,0,0,0,0)==1,('original body',n));report['oracleSelfchecks'].append({'iterations':n,'originalBodyVerifierAndRngMatch':True})
 for symbol,inputs in [('table-entry',range(256)),('prefix-crc',range(1025)),('prefix-seed',range(1025))]:
  for n in inputs:
   v=sample('raw',symbol,n)['result'];w=getattr(c,symbol.replace('-','_'))(n,0,0,0,0,0,0,0);require(v==w,(symbol,n,v,w));report['cells'].append({'symbol':symbol,'input':n,'Kotoba':v,'C':w})
  save();print(symbol,'all',len(inputs),'values match',flush=True)
 for n in profile['iterations']:
  a=sample('raw','bench',n);b=sample('dylib','bench',n);require(a['result']==b['result']==int(n>0),('batch',n,a,b));report['batches'].append({'iterations':n,'Kotoba':a['result'],'C':b['result'],'fuelConsumed':a['contextFuelConsumed']})
 r=run('raw','bench',32,fuel=1);require(r.returncode==-5,('fuel guard',r.returncode));report['guards'].append({'fuel':1,'returncode':r.returncode});report['completeActiveWorkload']=True;report['status']='complete-correctness'
 if args.measure:
  require(socket.gethostname().split('.')[0]=='asher','timing host must be asher');arms=[('Kotoba','raw'),('C','dylib')];counts={}
  for name,kind in arms:
   require(load()<=4,'host too busy');s=sample(kind,'bench',32,3,1);counts[name]=max(1,round(300000000/(s['elapsedNanoseconds']/3)))
  report.update(iterationsPerCall=32,samplesPerArm=30,warmupCalls=1,countByArm=counts)
  for i in range(30):
   for name,kind in arms[i%2:]+arms[:i%2]:
    before=load();require(before<=4,before);s=sample(kind,'bench',32,counts[name],1);after=load();require(after<=4,after);require(s['result']==1 and s['calls']==counts[name] and s['warmupCalls']==1 and s['elapsedNanoseconds']>=50000000,s);s.update(arm=name,pair=i,loadBefore=before,loadAfter=after,recordedAt=time.time());report['rows'].append(s)
   save()
  report['summary']={}
  for name,_ in arms:
   xs=[s['elapsedNanoseconds']/(32*s['calls']) for s in report['rows'] if s['arm']==name];mu=statistics.mean(xs);sd=statistics.stdev(xs);report['summary'][name]={'meanNsPerBody':mu,'sdNs':sd,'relativeSd':sd/mu}
  report['summary']['KotobaTimeOverC']=report['summary']['Kotoba']['meanNsPerBody']/report['summary']['C']['meanNsPerBody'];report['performanceMeasured']=True;report['status']='complete-timing'
except (AssertionError,subprocess.CalledProcessError) as error:
 report['status']='failed';report['failure']={'type':type(error).__name__,'message':str(error)};raise
finally:save()
print('PASS',report['status'],len(report['cells']),flush=True)
