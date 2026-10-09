#!/usr/bin/env python3
# BOOTSTRAP-TOOL: untimed original picojpeg transform differential.
import argparse,ctypes,hashlib,json,pathlib,re,subprocess
parser=argparse.ArgumentParser();parser.add_argument('directory',type=pathlib.Path);args=parser.parse_args();p=args.directory.resolve();compiler=p.parent/'images/r6m';runner=p.parent/'runner';up=p.parent/'upstream';out=p/'results.json'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
if out.exists():raise SystemExit('refusing to replace evidence')
profile=json.loads((p/'profile.json').read_text())
for f,d in profile['sourcePins'].items():
 if sha(up/'src/picojpeg'/f)!=d:raise SystemExit('unreviewed picojpeg transforms profile: '+f)
report={'format':'amu.picojpeg-transform-fragment/v1','status':'running','completeWorkload':False,'performanceMeasured':False,'officialEmbenchScore':False,'formalPerfgateQualified':False,'compilerSha256':sha(compiler),'runnerSha256':sha(runner),'sourcePins':profile['sourcePins'],'oracleSelfchecks':[],'cells':[],'guards':[],'rows':[]}
def save():out.write_text(json.dumps(report,indent=2)+'\n')
def require(ok,info):
 if not ok:raise AssertionError(info)
def run(name,n,fuel=16777216):
 off=re.search(r':offset (\d+)',(p/(name+'-extract.log')).read_text()).group(1)
 return subprocess.run([str(runner),'raw',str(p/(name+'.bin')),off,'aarch64',str(n),'1','0',str(fuel)],capture_output=True,text=True)
save()
try:
 with (p/'check.log').open('w') as log:subprocess.run([str(compiler),'check',str(p/'picojpeg-transform.kotoba')],stdout=log,check=True)
 require((p/'check.log').read_text().startswith('ok '),'native check refused')
 with (p/'compile.log').open('w') as log:subprocess.run([str(compiler),'compile',str(p/'picojpeg-transform.kotoba'),'--target','aarch64-macos','--output',str(p/'transform.kexe')],stdout=log,check=True)
 for name in ('observe','bounds-probe'):
  with (p/(name+'-extract.log')).open('w') as log:subprocess.run([str(compiler),'extract-native',str(p/'transform.kexe'),'--symbol',name,'--output',str(p/(name+'.bin'))],stdout=log,check=True)
 subprocess.run(['clang','-O2','-std=gnu11','-dynamiclib','-I',str(up/'support'),str(p/'c-bridge.c'),'-o',str(p/'c.dylib')],check=True)
 report['sha256']={f:sha(p/f) for f in ('picojpeg-transform.kotoba','observe.bin','c-bridge.c','c.dylib','profile.json')}
 c=ctypes.CDLL(str(p/'c.dylib'))
 for name in ('observe','decoder_selfcheck','oracle_selfcheck','transform_selfcheck'):
  f=getattr(c,name);f.restype=ctypes.c_int64;f.argtypes=[ctypes.c_int64]*8
 for n in (1,2,17,32):
  require(c.decoder_selfcheck(n,0,0,0,0,0,0,0)==1,('original decoder',n));report['oracleSelfchecks'].append({'iterations':n,'unchangedCDecoderAndVerifier':True})
  require(c.oracle_selfcheck(n,0,0,0,0,0,0,0)==1,('original full init',n));report['oracleSelfchecks'].append({'iterations':n,'unchangedInitApiAndInfoState':True})
  require(c.transform_selfcheck(n,0,0,0,0,0,0,0)==1,('transform observation/original full decoder',n));report['oracleSelfchecks'].append({'iterations':n,'observedIdctRgbMatchOriginalFullDecoderAndVerifier':True})
 for phase in (1,2):
  for count in range(1,169):
   for cell in profile['coefficientFields']:
    encoded=phase*1048576+count*4096+cell;r=run('observe',encoded);require(r.returncode==0,(phase,count,cell,r.returncode,r.stderr));v=json.loads(r.stdout)['result'];w=c.observe(encoded,0,0,0,0,0,0,0);require(v==w,(phase,count,cell,v,w));report['cells'].append({'phase':phase,'blockCount':count,'cell':cell,'Kotoba':v,'C':w})
   if count%12==0:save();print('phase',phase,'blocks',count,'all IDCT coefficients match',flush=True)
 for mcu in range(1,57):
  for cell in profile['rgbFields']:
   encoded=3*1048576+mcu*3*4096+cell;r=run('observe',encoded);require(r.returncode==0,(mcu,cell,r.returncode));v=json.loads(r.stdout)['result'];w=c.observe(encoded,0,0,0,0,0,0,0);require(v==w,('RGB',mcu,cell,v,w));report['cells'].append({'phase':3,'mcuCount':mcu,'cell':cell,'Kotoba':v,'C':w})
  if mcu%7==0:save();print('MCUs',mcu,'all RGB pixels match',flush=True)
 for cell in profile['terminalFields']:
  encoded=3*1048576+169*4096+cell;r=run('observe',encoded);require(r.returncode==0,(cell,r.returncode));v=json.loads(r.stdout)['result'];w=c.observe(encoded,0,0,0,0,0,0,0);require(v==w,('terminal',cell,v,w));report['cells'].append({'group':'terminal','cell':cell,'Kotoba':v,'C':w})
 for name,n,fuel,code in [('bounds-probe',4095,16777216,0),('bounds-probe',4096,16777216,-4),('observe',3*1048576+169*4096,1,-5)]:
  r=run(name,n,fuel);require(r.returncode==code,(name,n,r.returncode));report['guards'].append({'symbol':name,'input':n,'fuel':fuel,'returncode':r.returncode})
 report['status']='complete-fragment-correctness'
except (AssertionError,subprocess.CalledProcessError) as error:
 report['status']='failed';report['failure']={'type':type(error).__name__,'message':str(error)};raise
finally:save()
print('PASS',report['status'],len(report['cells']),flush=True)
