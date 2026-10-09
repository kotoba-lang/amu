#!/usr/bin/env python3
# BOOTSTRAP-TOOL: untimed active QR v2 frame fragment differential.
import argparse,ctypes,hashlib,json,pathlib,re,subprocess
parser=argparse.ArgumentParser();parser.add_argument('directory',type=pathlib.Path);args=parser.parse_args();p=args.directory.resolve();compiler=p.parent/'images/r6m';runner=p.parent/'runner';up=p.parent/'upstream';out=p/'results.json'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
if out.exists():raise SystemExit('refusing to replace evidence')
profile=json.loads((p/'profile.json').read_text())
for f,d in profile['sourcePins'].items():
 if sha(up/'src/qrduino'/f)!=d:raise SystemExit('unreviewed QR frame profile: '+f)
with (p/'check.log').open('w') as log:subprocess.run([str(compiler),'check',str(p/'qr-frame.kotoba')],stdout=log,check=True)
assert (p/'check.log').read_text().startswith('ok ')
with (p/'compile.log').open('w') as log:subprocess.run([str(compiler),'compile',str(p/'qr-frame.kotoba'),'--target','aarch64-macos','--output',str(p/'frame.kexe')],stdout=log,check=True)
for name in ('observe','bounds-probe'):
 with (p/(name+'-extract.log')).open('w') as log:subprocess.run([str(compiler),'extract-native',str(p/'frame.kexe'),'--symbol',name,'--output',str(p/(name+'.bin'))],stdout=log,check=True)
subprocess.run(['clang','-O2','-std=gnu11','-dynamiclib','-I',str(up/'support'),str(p/'c-bridge.c'),str(up/'src/qrduino/qrencode.c'),str(up/'support/beebsc.c'),'-o',str(p/'c.dylib')],check=True)
c=ctypes.CDLL(str(p/'c.dylib'))
for name in ('observe','oracle_selfcheck'):
 f=getattr(c,name);f.restype=ctypes.c_int64;f.argtypes=[ctypes.c_int64]*8
def run(name,n,fuel=16777216):
 off=re.search(r':offset (\d+)',(p/(name+'-extract.log')).read_text()).group(1)
 return subprocess.run([str(runner),'raw',str(p/(name+'.bin')),off,'aarch64',str(n),'1','0',str(fuel)],capture_output=True,text=True)
report={'format':'amu.qr-frame-fragment/v1','status':'running','completeWorkload':False,'performanceMeasured':False,'officialEmbenchScore':False,'formalPerfgateQualified':False,'compilerSha256':sha(compiler),'runnerSha256':sha(runner),'sha256':{f:sha(p/f) for f in ('qr-frame.kotoba','observe.bin','c-bridge.c','c.dylib','profile.json')},'oracleSelfchecks':[],'cells':[],'guards':[],'rows':[]}
def save():out.write_text(json.dumps(report,indent=2)+'\n')
save()
try:
 for n in (1,2,17,32):
  assert c.oracle_selfcheck(n,0,0,0,0,0,0,0)==1,n;report['oracleSelfchecks'].append({'calls':n,'unchangedInitframeMatches':True})
 for stage in range(9):
  for cell in list(range(100))+list(range(128,169)):
   encoded=stage*256+cell;r=run('observe',encoded);assert r.returncode==0,(stage,cell,r)
   v=json.loads(r.stdout)['result'];w=c.observe(encoded,0,0,0,0,0,0,0);assert v==w,(stage,cell,v,w)
   report['cells'].append({'stage':stage,'cell':cell,'Kotoba':v,'C':w})
  save();print('stage',stage,'all 141 base/reserve bytes match',flush=True)
 for name,n,fuel,code in [('bounds-probe',255,16777216,0),('bounds-probe',256,16777216,-4),('observe',2048,1,-5)]:
  r=run(name,n,fuel);assert r.returncode==code,(name,n,r.returncode);report['guards'].append({'symbol':name,'input':n,'fuel':fuel,'returncode':r.returncode})
 report['status']='complete-fragment-correctness'
except (AssertionError,subprocess.CalledProcessError) as error:
 report['status']='failed';report['failure']={'type':type(error).__name__,'message':str(error)};raise
finally:save()
print('PASS',report['status'],len(report['cells']),flush=True)
