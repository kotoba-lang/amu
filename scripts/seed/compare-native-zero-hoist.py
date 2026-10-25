#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,subprocess,platform,time,resource,os,statistics,runpy,argparse,re
A=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description='Native reused-zero loop hoisting experiment, never product qualification');p.add_argument('--output',type=Path,required=True);args=p.parse_args();O=args.output.resolve();O.mkdir(parents=True,exist_ok=False)
assert platform.system()=='Linux' and platform.machine() in ('aarch64','x86_64')
arm=platform.machine()=='aarch64';target='aarch64-linux' if arm else 'x86_64-linux'
m=runpy.run_path(str(A/'scripts/seed/compare-native-zero-watermark.py'))
def pin(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
paths=[p for p in (A/'seed/FULL-MANIFEST').read_text().splitlines() if p and not p.startswith('#')]
original=b''.join((A/p).read_bytes()+b'\n' for p in paths).decode();assert original.count(m['MARK_OLD'])==original.count(m['ZERO_OLD'])==2
base=original.replace(m['MARK_OLD'],m['MARK_NEW']).replace(m['ZERO_OLD'],m['ZERO_NEW'])
old='z (loop [i 0] (if (= i count) 0 (let [w (kxrt-store64 (kxrt-item u i) 0)] (recur (inc i)))))'
new='base (kxrt-item u 0) byte-end (+ base (* 8 count))\n            z (loop [cursor base] (if (= cursor byte-end) 0 (let [w (kxrt-store64 cursor 0)] (recur (+ cursor 8)))))'
assert base.count(old)==2
texts={'baseline':base,'candidate':base.replace(old,new),'mutant-last-word':base.replace(old,new.replace('(* 8 count)','(* 8 (if (> count 0) (dec count) 0))'))}
root=A/('seed/bootstrap/aarch64-linux-static-root.elf' if arm else 'bin/amu');runner=O/'runner.kotoba';runner.write_bytes((A/'seed/x86_64-kx64-runner.kotoba').read_bytes())
fixture=O/'oracle.kotoba';fixture.write_bytes((A/'seed/tests/native-zero-watermark.kotoba').read_bytes())
work=O/'workload.kotoba';work.write_bytes((A/'seed/tests/native-zero-hoist-workload.kotoba').read_bytes())
cpus=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpus[0]})
env=dict(PATH='/nonexistent',KEXE_STACK_BYTES='8388608',KEXE_CAP_RESOURCES_35=str(O),KEXE_ALLOW='35,37,38,39',KEXE_FUEL='10000000000',KEXE_COMMAND='1')
d=dict(schema='amu.native-zero-hoist-experiment.v1',nativeVerdictAuthority=False,qualificationReplacement=False,candidateAdopted=False,fullQualification=False,host=[platform.system(),platform.machine(),platform.release()],producer=pin(root),workload=pin(work),fixture=pin(fixture),selectedCPU=cpus[0],calls=[])
def save():(O/'observations.json').write_text(json.dumps(d,indent=2)+'\n')
def run(name,args,expected=0,arena=False):
 t=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN);p=subprocess.run(list(map(str,args)),cwd=O,env=env|({'KEXE_ARENA_USE':'1'}if arena else{}),capture_output=True,timeout=900);after=resource.getrusage(resource.RUSAGE_CHILDREN)
 (O/(name+'.stdout')).write_bytes(p.stdout);(O/(name+'.stderr')).write_bytes(p.stderr);row=dict(name=name,exit=p.returncode,seconds=time.monotonic()-t,cpuSeconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,minorFaults=after.ru_minflt-before.ru_minflt,loadEnd=os.getloadavg());d['calls'].append(row);save();print(row,flush=True);assert p.returncode==expected,(name,p.returncode,p.stderr[-1000:])
 if arena:
  assert p.stderr.startswith(b'KEXE_ARENA_USE ') and not p.stdout
  for field in ['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','regions','string-regions']:assert re.search(b':'+field.encode()+rb' 0(?:[ }])',p.stderr)
 else:assert not p.stderr
 return row,p.stderr
d.update(runtimeChanged=True,compilerAlgorithmChanged=False,sourceWorkloadChanged=False,emulation=False,allowedCPUs=cpus,sourceBindings={p:pin(A/p)for p in paths})
d['cpuModel']=next((x for x in Path('/proc/cpuinfo').read_text().splitlines()if x.startswith('model name')),'unavailable')
images={}
for name,text in texts.items():
 src=O/(name+'-full.kotoba');src.write_text(text);d.setdefault('variants',{})[name]=pin(src);payload=O/(name+'.kseed');engine=O/(name+'-compiler.elf')
 if arm:
  run('container-'+name,[root,'compile',src,'--target','aarch64-macos','--output',payload]);run('pack-'+name,[root,'compile',runner,'--target',target,'--output',engine,'--format','packed','--payload',payload])
 else:run('compiler-'+name,[root,'compile',src,'--target',target,'--output',engine,'--format','static'])
 engine.chmod(0o755);d.setdefault('templates',{})[name]=dict(source=pin(src),image=pin(engine))
 for label,source in [('oracle',fixture),('workload',work)]:
  image=O/(name+'-'+label+'.elf');run('build-'+name+'-'+label,[engine,'compile',source,'--target',target,'--output',image,'--format','static']);image.chmod(0o755);images[(name,label)]=image;d.setdefault('images',{}).setdefault(name,{})[label]=pin(image)
 if name!='mutant-last-word':run('oracle-'+name,[images[(name,'oracle')]])
 else:run('detect-last-word',[images[(name,'workload')]],1)
for i,name in enumerate(['baseline','candidate','candidate','baseline']):
 row,raw=run('measure-'+str(i)+'-'+name,[images[(name,'workload')]],arena=True)
 if i==0:golden=raw
 else:assert raw==golden,'resource observation changed'
samples={v:[r['seconds']for r in d['calls']if r['name'].startswith('measure-')and r['name'].endswith('-'+v)]for v in ['baseline','candidate']}
d.update(status='PASS_NATIVE_ZERO_HOIST_EXPERIMENT',samples=samples,candidateToBaselineRatio=statistics.median(samples['candidate'])/statistics.median(samples['baseline']),resourceReportsByteIdentical=True,actualLastWordMutantDetected=True);save();print(d['status'],d['candidateToBaselineRatio'],flush=True)
