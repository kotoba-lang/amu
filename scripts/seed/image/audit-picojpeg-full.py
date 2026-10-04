#!/usr/bin/env python3
# BOOTSTRAP-TOOL: untimed original picojpeg transform differential.
import argparse,ctypes,hashlib,json,pathlib,re,subprocess
parser=argparse.ArgumentParser();parser.add_argument('directory',type=pathlib.Path);args=parser.parse_args();p=args.directory.resolve();compiler=p.parent/'images/r6m';runner=p.parent/'runner';up=p.parent/'upstream';out=p/'results.json'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
if out.exists():raise SystemExit('refusing to replace evidence')
profile=json.loads((p/'profile.json').read_text())
for f,d in profile['sourcePins'].items():
 if sha(up/'src/picojpeg'/f)!=d:raise SystemExit('unreviewed picojpeg transforms profile: '+f)
report={'format':'amu.picojpeg-full/v1','status':'running','completeWorkload':False,'performanceMeasured':False,'officialEmbenchScore':False,'formalPerfgateQualified':False,'compilerSha256':sha(compiler),'runnerSha256':sha(runner),'sourcePins':profile['sourcePins'],'oracleSelfchecks':[],'cells':[],'guards':[],'rows':[]}
def save():out.write_text(json.dumps(report,indent=2)+'\n')
def require(ok,info):
 if not ok:raise AssertionError(info)
def run(name,n,fuel=16777216):
 off=re.search(r':offset (\d+)',(p/(name+'-extract.log')).read_text()).group(1)
 return subprocess.run([str(runner),'raw',str(p/(name+'.bin')),off,'aarch64',str(n),'1','0',str(fuel)],capture_output=True,text=True)
save()
try:
 with (p/'check.log').open('w') as log:subprocess.run([str(compiler),'check',str(p/'picojpeg-full.kotoba')],stdout=log,check=True)
 require((p/'check.log').read_text().startswith('ok '),'native check refused')
 with (p/'compile.log').open('w') as log:subprocess.run([str(compiler),'compile',str(p/'picojpeg-full.kotoba'),'--target','aarch64-macos','--output',str(p/'full.kexe')],stdout=log,check=True)
 for name in ('bench','repeated-state','bounds-probe'):
  with (p/(name+'-extract.log')).open('w') as log:subprocess.run([str(compiler),'extract-native',str(p/'full.kexe'),'--symbol',name,'--output',str(p/(name+'.bin'))],stdout=log,check=True)
 subprocess.run(['clang','-O2','-std=gnu11','-dynamiclib','-I',str(up/'support'),str(p/'c-bridge.c'),'-o',str(p/'c.dylib')],check=True)
 report['sha256']={f:sha(p/f) for f in ('picojpeg-full.kotoba','bench.bin','repeated-state.bin','c-bridge.c','c.dylib','profile.json')}
 c=ctypes.CDLL(str(p/'c.dylib'))
 for name in ('bench','repeated_state','decoder_selfcheck'):
  f=getattr(c,name);f.restype=ctypes.c_int64;f.argtypes=[ctypes.c_int64]*8
 for n in (0,1,2,17,32):
  r=run('bench',n);require(r.returncode==0,('bench',n,r.returncode,r.stderr));v=json.loads(r.stdout)['result'];w=c.bench(n,0,0,0,0,0,0,0);require(v==w==(0 if n==0 else 1),('whole body',n,v,w));report['oracleSelfchecks'].append({'iterations':n,'completeOriginalInputVerifier':True,'result':v})
 for n in profile['iterations']:
  for cell in profile['repeatedFields']:
   encoded=n*4096+cell;r=run('repeated-state',encoded);require(r.returncode==0,(n,cell,r.returncode,r.stderr));v=json.loads(r.stdout)['result'];w=c.repeated_state(encoded,0,0,0,0,0,0,0);require(v==w,(n,cell,v,w));report['cells'].append({'iterations':n,'cell':cell,'Kotoba':v,'C':w})
  save();print('iterations',n,'all repeated decoder states and RGB buffers match',flush=True)
 for name,n,fuel,code in [('bounds-probe',4095,16777216,0),('bounds-probe',4096,16777216,-4),('bench',1,1,-5)]:
  r=run(name,n,fuel);require(r.returncode==code,(name,n,r.returncode));report['guards'].append({'symbol':name,'input':n,'fuel':fuel,'returncode':r.returncode})
 report['completeWorkload']=True
 report['nativeAllocsPerCall']=1
 report['workspaceCells']=4096
 report['status']='complete-original-profile-correctness'
except (AssertionError,subprocess.CalledProcessError) as error:
 report['status']='failed';report['failure']={'type':type(error).__name__,'message':str(error)};raise
finally:save()
print('PASS',report['status'],len(report['cells']),flush=True)
