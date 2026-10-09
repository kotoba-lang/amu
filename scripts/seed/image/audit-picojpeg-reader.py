#!/usr/bin/env python3
# BOOTSTRAP-TOOL: untimed original picojpeg input/bit-reader differential.
import argparse,ctypes,hashlib,json,pathlib,re,subprocess
parser=argparse.ArgumentParser();parser.add_argument('directory',type=pathlib.Path);args=parser.parse_args();p=args.directory.resolve();compiler=p.parent/'images/r6m';runner=p.parent/'runner';up=p.parent/'upstream';out=p/'results.json'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
if out.exists():raise SystemExit('refusing to replace evidence')
profile=json.loads((p/'profile.json').read_text())
for f,d in profile['sourcePins'].items():
 if sha(up/'src/picojpeg'/f)!=d:raise SystemExit('unreviewed picojpeg reader profile: '+f)
report={'format':'amu.picojpeg-reader-fragment/v1','status':'running','completeWorkload':False,'performanceMeasured':False,'officialEmbenchScore':False,'formalPerfgateQualified':False,'compilerSha256':sha(compiler),'runnerSha256':sha(runner),'sourcePins':profile['sourcePins'],'oracleSelfchecks':[],'cells':[],'guards':[],'rows':[]}
def save():out.write_text(json.dumps(report,indent=2)+'\n')
def require(ok,info):
 if not ok:raise AssertionError(info)
def run(name,n,fuel=16777216):
 off=re.search(r':offset (\d+)',(p/(name+'-extract.log')).read_text()).group(1)
 return subprocess.run([str(runner),'raw',str(p/(name+'.bin')),off,'aarch64',str(n),'1','0',str(fuel)],capture_output=True,text=True)
save()
try:
 with (p/'check.log').open('w') as log:subprocess.run([str(compiler),'check',str(p/'picojpeg-reader.kotoba')],stdout=log,check=True)
 require((p/'check.log').read_text().startswith('ok '),'native check refused')
 with (p/'compile.log').open('w') as log:subprocess.run([str(compiler),'compile',str(p/'picojpeg-reader.kotoba'),'--target','aarch64-macos','--output',str(p/'reader.kexe')],stdout=log,check=True)
 for name in ('observe','bounds-probe'):
  with (p/(name+'-extract.log')).open('w') as log:subprocess.run([str(compiler),'extract-native',str(p/'reader.kexe'),'--symbol',name,'--output',str(p/(name+'.bin'))],stdout=log,check=True)
 subprocess.run(['clang','-O2','-std=gnu11','-dynamiclib','-I',str(up/'support'),str(p/'c-bridge.c'),'-o',str(p/'c.dylib')],check=True)
 report['sha256']={f:sha(p/f) for f in ('picojpeg-reader.kotoba','observe.bin','c-bridge.c','c.dylib','profile.json')}
 c=ctypes.CDLL(str(p/'c.dylib'))
 for name in ('observe','decoder_selfcheck'):
  f=getattr(c,name);f.restype=ctypes.c_int64;f.argtypes=[ctypes.c_int64]*8
 for n in (1,2,17,32):
  require(c.decoder_selfcheck(n,0,0,0,0,0,0,0)==1,('original decoder',n));report['oracleSelfchecks'].append({'iterations':n,'unchangedCDecoderAndVerifier':True})
 for mode in range(4):
  limits=profile['prefixes']+([profile['jpegLength']+d for d in (-1,0,1,4)] if mode==0 else [])
  for limit in limits:
   for cell in profile['fields']:
    encoded=mode*1048576+limit*512+cell;r=run('observe',encoded);require(r.returncode==0,(mode,limit,cell,r.returncode,r.stderr));v=json.loads(r.stdout)['result'];w=c.observe(encoded,0,0,0,0,0,0,0);require(v==w,(mode,limit,cell,v,w));report['cells'].append({'mode':mode,'operations':limit,'cell':cell,'Kotoba':v,'C':w})
   save();print('mode',mode,'prefix',limit,'all 264 buffer/state/return cells match',flush=True)
 for name,n,fuel,code in [('bounds-probe',511,16777216,0),('bounds-probe',512,16777216,-4),('observe',1024*512,1,-5)]:
  r=run(name,n,fuel);require(r.returncode==code,(name,n,r.returncode));report['guards'].append({'symbol':name,'input':n,'fuel':fuel,'returncode':r.returncode})
 report['status']='complete-fragment-correctness'
except (AssertionError,subprocess.CalledProcessError) as error:
 report['status']='failed';report['failure']={'type':type(error).__name__,'message':str(error)};raise
finally:save()
print('PASS',report['status'],len(report['cells']),flush=True)
