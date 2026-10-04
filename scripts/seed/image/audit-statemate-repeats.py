#!/usr/bin/env python3
# BOOTSTRAP-TOOL: untimed repeated full-state and bounds differential.
import argparse,pathlib,subprocess,re,json,ctypes,hashlib
parser=argparse.ArgumentParser();parser.add_argument('directory',type=pathlib.Path);args=parser.parse_args()
p=args.directory.resolve();compiler=p.parent/'images/r6m';runner=p.parent/'runner'
if (p/'repeat-state-audit.json').exists():raise SystemExit('refusing to replace evidence')
if hashlib.sha256((p.parent/'upstream/src/statemate/libstatemate.c').read_bytes()).hexdigest()!='389c4bae5caba79a6f9139e02bf5e61c92921a756ec01200d2d2f16dc1c4ccf5':raise SystemExit('unreviewed Statemate profile')
s=(p/'statemate.kotoba').read_text().replace('(:export [batch stage-cell test-statemate])','(:export [batch stage-cell test-statemate repeat-cell bounds-probe])',1)
s+='\n(defn repeat-cell [encoded :i64] :i64 (let [n (quot encoded 169) cell (rem encoded 169) result (repeats (vector-alloc 169) n)] (vector-at result cell)))\n(defn bounds-probe [i :i64] :i64 (vector-at (vector-alloc 169) i))\n'
(p/'repeat-audit.kotoba').write_text(s)
for args,log in [(['check',str(p/'repeat-audit.kotoba')],'repeat-check.log'),(['compile',str(p/'repeat-audit.kotoba'),'--target','aarch64-macos','--output',str(p/'repeat-audit.kexe')],'repeat-compile.log')]:
 with (p/log).open('w') as f:subprocess.run([str(compiler)]+args,stdout=f,check=True)
 if args[0]=='check':assert (p/log).read_text().startswith('ok ')
for sym in ('repeat-cell','bounds-probe'):
 with (p/(sym+'-extract.log')).open('w') as f:subprocess.run([str(compiler),'extract-native',str(p/'repeat-audit.kexe'),'--symbol',sym,'--output',str(p/(sym+'.bin'))],stdout=f,check=True)
def run(sym,n):
 off=re.search(r':offset (\d+)',(p/(sym+'-extract.log')).read_text()).group(1)
 return subprocess.run([str(runner),'raw',str(p/(sym+'.bin')),off,'aarch64',str(n),'1','0','16777216'],capture_output=True,text=True)
c=ctypes.CDLL(str(p/'c.dylib'));c.repeat_cell.restype=ctypes.c_int64;c.repeat_cell.argtypes=[ctypes.c_int64]*8
report={'performanceMeasured':False,'cells':[],'guards':[]}
for n in (1,2,17,32):
 for i in range(169):
  r=run('repeat-cell',n*169+i);assert r.returncode==0,(n,i,r)
  v=json.loads(r.stdout)['result'];w=c.repeat_cell(n*169+i,0,0,0,0,0,0,0);assert v==w,(n,i,v,w)
  report['cells'].append({'iterations':n,'cell':i,'Kotoba':v,'C':w})
 print('repeat',n,'169 states match',flush=True)
for i,code in ((168,0),(169,-4)):
 r=run('bounds-probe',i);assert r.returncode==code,(i,r.returncode)
 report['guards'].append({'input':i,'returncode':r.returncode})
report['sha256']={f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in ('repeat-audit.kotoba','repeat-cell.bin','bounds-probe.bin','c.dylib')}
(p/'repeat-state-audit.json').write_text(json.dumps(report,indent=2)+'\n')
