#!/usr/bin/env python3
# BOOTSTRAP-TOOL: untimed QR codeword fragment; never a complete Embench score.
import argparse,ctypes,hashlib,json,pathlib,re,subprocess
p=argparse.ArgumentParser();p.add_argument('directory',type=pathlib.Path);args=p.parse_args();root=args.directory.resolve();compiler=root.parent/'images/r6m';runner=root.parent/'runner';up=root.parent/'upstream';out=root/'results.json'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
if out.exists():raise SystemExit('refusing to replace evidence')
profile=json.loads((root/'profile.json').read_text())
for f,d in profile['sourcePins'].items():
 if sha(up/'src/qrduino'/f)!=d:raise SystemExit('unreviewed QR profile: '+f)
with (root/'check.log').open('w') as log:subprocess.run([str(compiler),'check',str(root/'qr-codewords.kotoba')],stdout=log,check=True)
assert (root/'check.log').read_text().startswith('ok ')
with (root/'compile.log').open('w') as log:subprocess.run([str(compiler),'compile',str(root/'qr-codewords.kotoba'),'--target','aarch64-macos','--output',str(root/'codewords.kexe')],stdout=log,check=True)
for name in ('observe','table-cell','bounds-probe'):
 with (root/(name+'-extract.log')).open('w') as log:subprocess.run([str(compiler),'extract-native',str(root/'codewords.kexe'),'--symbol',name,'--output',str(root/(name+'.bin'))],stdout=log,check=True)
subprocess.run(['clang','-O2','-std=gnu11','-dynamiclib','-I',str(up/'support'),str(root/'c-bridge.c'),str(up/'src/qrduino/qrframe.c'),str(up/'support/beebsc.c'),'-o',str(root/'c.dylib')],check=True)
c=ctypes.CDLL(str(root/'c.dylib'))
for name in ('observe','table_cell','oracle_selfcheck'):
 f=getattr(c,name);f.restype=ctypes.c_int64;f.argtypes=[ctypes.c_int64]*8
def run(name,i,fuel=16777216):
 off=re.search(r':offset (\d+)',(root/(name+'-extract.log')).read_text()).group(1)
 return subprocess.run([str(runner),'raw',str(root/(name+'.bin')),off,'aarch64',str(i),'1','0',str(fuel)],capture_output=True,text=True)
def value(name,i):
 r=run(name,i);assert r.returncode==0,(name,i,r);return json.loads(r.stdout)['result']
report={'format':'amu.qr-codeword-fragment/v1','status':'running','completeWorkload':False,'officialEmbenchScore':False,'formalPerfgateQualified':False,'performanceMeasured':False,'compilerSha256':sha(compiler),'runnerSha256':sha(runner),'sha256':{f:sha(root/f) for f in ('qr-codewords.kotoba','observe.bin','c-bridge.c','c.dylib','profile.json')},'oracleSelfchecks':[],'tableCells':[],'cells':[],'guards':[],'rows':[]}
def save():out.write_text(json.dumps(report,indent=2)+'\n')
save()
try:
 for i in range(512):
  v=value('table-cell',i);w=c.table_cell(i,0,0,0,0,0,0,0);assert v==w,(i,v,w);report['tableCells'].append({'cell':i,'Kotoba':v,'C':w})
 for case in range(4):
  assert c.oracle_selfcheck(case,0,0,0,0,0,0,0)==1,case;report['oracleSelfchecks'].append({'case':case,'unchangedStringtoqrMatches':True})
  for stage in range(5):
   for cell in range(1024):
    encoded=case*8192+stage*1024+cell;v=value('observe',encoded);w=c.observe(encoded,0,0,0,0,0,0,0);assert v==w,(case,stage,cell,v,w)
    report['cells'].append({'case':case,'stage':stage,'cell':cell,'Kotoba':v,'C':w})
   save();print('case',case,'stage',stage,'all 1024 initialized cells match',flush=True)
 for name,i,fuel,code in [('bounds-probe',1023,16777216,0),('bounds-probe',1024,16777216,-4),('observe',0,1,-5)]:
  r=run(name,i,fuel);assert r.returncode==code,(name,i,r.returncode);report['guards'].append({'symbol':name,'input':i,'fuel':fuel,'returncode':r.returncode})
 report['status']='complete-fragment-correctness'
except (AssertionError,subprocess.CalledProcessError) as error:
 report['status']='failed';report['failure']={'type':type(error).__name__,'message':str(error)};raise
finally:save()
print('PASS',report['status'],len(report['cells']),len(report['tableCells']),flush=True)
