#!/usr/bin/env python3
"""Same-host native whole-core comparison; no qualification substitution.

The admitted public image builds both C0 variants. Original core18 and the
same lock are fed to each variant. Both cold compiler algorithms run; there
is no result cache. Python only stages Git bytes and observes processes.
"""
import argparse, hashlib, json, os, platform, resource, statistics, subprocess, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def pin(p):
 b=Path(p).read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main(output,revision):
 assert platform.system()=='Linux' and platform.machine()=='x86_64'
 output.mkdir(parents=True,exist_ok=False)
 # Use a single admitted CPU for both variants, with no parallel compilation.
 affinity=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,{affinity[0]})
 cpuinfo=Path('/proc/cpuinfo').read_text()
 metadata=dict(kernel=platform.release(),machine=platform.machine(),cpus=os.cpu_count(),allowedCPUs=affinity,selectedCPU=affinity[0],cpuModel=next(x for x in cpuinfo.splitlines() if x.startswith('model name')),cgroup={})
 for path in ('/sys/fs/cgroup/cpu.max','/sys/fs/cgroup/cpu.stat','/sys/fs/cgroup/memory.max'):
  p=Path(path)
  if p.exists(): metadata['cgroup'][path]=p.read_text()
 def old(path):
  return subprocess.run(['git','show',revision+':'+path],cwd=ROOT,check=True,capture_output=True).stdout
 paths=lambda manifest:[p for p in old(manifest).decode().splitlines() if p and not p.startswith('#')]
 corepaths=paths('seed/MANIFEST');staticpaths=paths('seed/CORE-STATIC-MANIFEST')
 assert len(corepaths)==len(staticpaths)==18
 source=output/'core.kotoba';source.write_bytes(b''.join(old(p)+b'\n' for p in corepaths))
 corepin=pin(source);policy=json.loads(old('seed/cdci/policy.json'));assert corepin['sha256']==policy['coreSourceSHA256']
 lock=output/'core.ksl';lock.write_text(f"KSL1\nentry {source}\nfile {corepin['sha256']} {source}\n")
 producer=ROOT/'bin/amu-linux-x86_64'
 report=dict(schema='amu.native-proof-scan-comparison.v1',qualificationReplacement=False,candidateAdopted=False,host=metadata,baselineRevision=revision,producer=pin(producer),input=corepin,lock=pin(lock),sourceBindings={},calls=[],targetSeconds=600,coldCompile=True)
 env=dict(PATH='/nonexistent',KEXE_STACK_BYTES='8388608',KEXE_CAP_RESOURCES_35=str(output))
 def run(name,argv,timeout=7200):
  started=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN);load=os.getloadavg()
  with (output/(name+'.stdout')).open('wb') as out,(output/(name+'.stderr')).open('wb') as err:
   r=subprocess.run(list(map(str,argv)),cwd=output,env=env,stdout=out,stderr=err,timeout=timeout)
  after=resource.getrusage(resource.RUSAGE_CHILDREN)
  row=dict(name=name,argv=list(map(str,argv)),exit=r.returncode,seconds=time.monotonic()-started,cpuSeconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,loadStart=load,loadEnd=os.getloadavg())
  report['calls'].append(row);(output/'observations.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(row),flush=True)
  assert r.returncode==0 and not (output/(name+'.stderr')).stat().st_size,(name,r.returncode,(output/(name+'.stderr')).read_bytes()[-1000:])
  return row
 images={}
 for variant in ('baseline','candidate'):
  data={p:old(p) if variant=='baseline' else (ROOT/p).read_bytes() for p in staticpaths}
  report['sourceBindings'][variant]={p:dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for p,b in data.items()}
  unit=output/(variant+'.kotoba');unit.write_bytes(b''.join(data[p]+b'\n' for p in staticpaths))
  image=output/(variant+'.elf');run('build-'+variant,[producer,'compile',unit,'--target','x86_64-linux','--output',image,'--format','static'],900);image.chmod(0o755);images[variant]=image;report[variant+'Compiler']=pin(image)
 assert [p for p in staticpaths if report['sourceBindings']['baseline'][p]!=report['sourceBindings']['candidate'][p]]==['seed/41-a64gen.kotoba']
 for index,variant in enumerate(('baseline','candidate','candidate','baseline')):
  artifact=output/(str(index)+'-'+variant+'.kseed')
  row=run(str(index)+'-'+variant,[images[variant],'compile',source,'--target','aarch64-macos','--output',artifact,'--source-lock',lock,'--source-lock-sha256',pin(lock)['sha256']])
  row['artifact']=pin(artifact);assert row['artifact']['sha256']==policy['coreContainerSHA256'],('semantic drift',variant,row['artifact'])
  report['wholeCoreArtifactByteIdentical']=True;(output/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
 samples={v:[r['seconds'] for r in report['calls'] if r['name'][0].isdigit() and r['name'].endswith(v)] for v in images}
 report.update(status='PASS_SAME_HOST_NATIVE_WHOLE_CORE_PARITY',samples=samples,candidateToBaselineRatio=statistics.median(samples['candidate'])/statistics.median(samples['baseline']),underTenMinutes=all(x<=600 for x in samples['candidate']))
 (output/'observations.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],report['candidateToBaselineRatio'],report['underTenMinutes'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--baseline-revision',required=True);a=p.parse_args();main(a.output.resolve(),a.baseline_revision)
