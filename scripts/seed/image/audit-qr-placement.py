#!/usr/bin/env python3
# BOOTSTRAP-TOOL: untimed QR v2 codewords/frame/data-placement differential.
import argparse,ctypes,hashlib,json,pathlib,re,subprocess
parser=argparse.ArgumentParser();parser.add_argument('directory',type=pathlib.Path);args=parser.parse_args();p=args.directory.resolve();compiler=p.parent/'images/r6m';runner=p.parent/'runner';up=p.parent/'upstream';out=p/'results.json'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
if out.exists():raise SystemExit('refusing to replace evidence')
profile=json.loads((p/'profile.json').read_text())
for f,d in profile['sourcePins'].items():
 if sha(up/'src/qrduino'/f)!=d:raise SystemExit('unreviewed QR placement profile: '+f)
with (p/'check.log').open('w') as log:subprocess.run([str(compiler),'check',str(p/'qr-placement.kotoba')],stdout=log,check=True)
if not (p/'check.log').read_text().startswith('ok '):raise SystemExit('native check refused')
with (p/'compile.log').open('w') as log:subprocess.run([str(compiler),'compile',str(p/'qr-placement.kotoba'),'--target','aarch64-macos','--output',str(p/'placement.kexe')],stdout=log,check=True)
for name in ('observe','bounds-probe'):
 with (p/(name+'-extract.log')).open('w') as log:subprocess.run([str(compiler),'extract-native',str(p/'placement.kexe'),'--symbol',name,'--output',str(p/(name+'.bin'))],stdout=log,check=True)
subprocess.run(['clang','-O2','-std=gnu11','-dynamiclib','-I',str(up/'support'),str(p/'c-bridge.c'),str(up/'src/qrduino/qrframe.c'),str(up/'support/beebsc.c'),'-o',str(p/'c.dylib')],check=True)
c=ctypes.CDLL(str(p/'c.dylib'))
for name in ('observe','oracle_selfcheck'):
 f=getattr(c,name);f.restype=ctypes.c_int64;f.argtypes=[ctypes.c_int64]*8
def run(name,n,fuel=16777216):
 off=re.search(r':offset (\d+)',(p/(name+'-extract.log')).read_text()).group(1)
 return subprocess.run([str(runner),'raw',str(p/(name+'.bin')),off,'aarch64',str(n),'1','0',str(fuel)],capture_output=True,text=True)
report={'format':'amu.qr-placement-fragment/v1','status':'running','completeWorkload':False,'performanceMeasured':False,'officialEmbenchScore':False,'formalPerfgateQualified':False,'compilerSha256':sha(compiler),'runnerSha256':sha(runner),'sha256':{f:sha(p/f) for f in ('qr-placement.kotoba','observe.bin','c-bridge.c','c.dylib','profile.json')},'oracleSelfchecks':[],'cells':[],'guards':[],'rows':[]}
def save():out.write_text(json.dumps(report,indent=2)+'\n')
def compare(case,limit,cells,group):
 for cell in cells:
  encoded=case*1048576+limit*2048+cell;r=run('observe',encoded)
  if r.returncode!=0:raise AssertionError((case,limit,cell,r.returncode,r.stderr))
  v=json.loads(r.stdout)['result'];w=c.observe(encoded,0,0,0,0,0,0,0)
  if v!=w:raise AssertionError((case,limit,cell,v,w))
  report['cells'].append({'group':group,'case':case,'bits':limit,'cell':cell,'Kotoba':v,'C':w})
save()
try:
 for case in range(4):
  if c.oracle_selfcheck(case,0,0,0,0,0,0,0)!=1:raise AssertionError(('unchanged-fillframe',case))
  report['oracleSelfchecks'].append({'case':case,'unchangedFillframeMatches':True})
  for limit in (0,1,2,7,8,17,63,64,127,255,351,352):
   compare(case,limit,list(range(768,868))+list(range(1760,1764)),'image-and-path-prefix');save()
  compare(case,352,list(range(44))+list(range(1536,1636))+list(range(1664,1705)),'components');save()
  print('case',case,'12 image/path prefixes and final components match',flush=True)
 for limit in range(353):
  compare(0,limit,range(1760,1764),'every-path-prefix')
  if limit%32==0:save();print('path prefix',limit,'matches',flush=True)
 for name,n,fuel,code in [('bounds-probe',2047,16777216,0),('bounds-probe',2048,16777216,-4),('observe',352*2048,1,-5)]:
  r=run(name,n,fuel)
  if r.returncode!=code:raise AssertionError((name,n,r.returncode))
  report['guards'].append({'symbol':name,'input':n,'fuel':fuel,'returncode':r.returncode})
 report['status']='complete-fragment-correctness'
except (AssertionError,subprocess.CalledProcessError) as error:
 report['status']='failed';report['failure']={'type':type(error).__name__,'message':str(error)};raise
finally:save()
print('PASS',report['status'],len(report['cells']),flush=True)
