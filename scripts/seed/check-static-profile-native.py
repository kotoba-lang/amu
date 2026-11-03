#!/usr/bin/env python3
"""Observe the native static-capacity generator and bounded refusal cases."""
import argparse,hashlib,json,platform,shutil,subprocess
from pathlib import Path
from aiueos_native_proof import load_native_producers
ROOT=Path(__file__).resolve().parents[2]
def pin(p):
 b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main(build,complete,out):
 graph,producers,_=load_native_producers(build,complete);out.mkdir(parents=True,exist_ok=False);routes=[]
 parts=[ROOT/'seed/00-ns-static.kotoba',ROOT/'seed/01-mem.kotoba',ROOT/'seed/02-io.kotoba',ROOT/'seed/gen-static-ns.kotoba']
 target='x86_64-linux' if platform.machine()=='x86_64' else 'aarch64-linux'
 for compiler in producers:
  work=out/compiler.stem;work.mkdir();source=work/'generator.kotoba';source.write_bytes(b''.join(p.read_bytes()+b'\n' for p in parts))
  normal=work/'normal.kotoba';shutil.copy2(ROOT/'seed/00-ns.kotoba',normal);policy=work/'MEMORY-MAP';shutil.copy2(ROOT/'seed/MEMORY-MAP',policy)
  env=dict(PATH='/nonexistent',KEXE_ALLOW='35,37,38,39',KEXE_CAP_RESOURCES_35=str(work),KEXE_STACK_BYTES='8388608');calls=[]
  def run(name,args,expected=0,custom=None):
   r=subprocess.run(list(map(str,args)),env=custom or env,capture_output=True,timeout=300)
   (work/(name+'.stdout')).write_bytes(r.stdout);(work/(name+'.stderr')).write_bytes(r.stderr);calls.append(dict(name=name,exit=r.returncode));(work/'calls.json').write_text(json.dumps(calls,indent=2)+'\n')
   assert r.returncode==expected,(name,r.returncode,r.stderr[-1000:])
   if expected==0:assert not r.stderr
   return r
  tool=work/'generator.elf';run('compile',[compiler,'compile',source,'--target',target,'--output',tool,'--format','static']);tool.chmod(0o755)
  good=work/'static.kotoba';run('generate',[tool,normal,policy,good]);assert good.read_bytes()==(ROOT/'seed/00-ns-static.kotoba').read_bytes()
  run('existing-output',[tool,normal,policy,good],1);assert good.read_bytes()==(ROOT/'seed/00-ns-static.kotoba').read_bytes()
  text=policy.read_text();cases={'zero-node':text.replace(';; [:s MM-NODE-CAP 786432]',';; [:s MM-NODE-CAP 0]'),
    'zero-sir':text.replace(';; [:s MM-SIR-CAP 589824]',';; [:s MM-SIR-CAP 0]'),
    'missing-sir':text.replace(';; [:s MM-SIR-CAP 589824]\n',''),
    'vector-budget':text.replace(';; [:s MM-NODE-CAP 786432]',';; [:s MM-NODE-CAP 33554432]'),
    'duplicate-override':text+'\n;; [:s MM-NODE-CAP 786432]\n',
    'missing-override':text.replace(';; [:s MM-OUT-CAP 12582912]\n','')}
  for name,bad in cases.items():
   assert bad!=text;p=work/(name+'.policy');p.write_text(bad);destination=work/(name+'.kotoba');run(name,[tool,normal,p,destination],1);assert not destination.exists()
  denied=work/'denied.kotoba';r=run('no-fs-grant',[tool,normal,policy,denied],120,{**env,'KEXE_ALLOW':'37,38,39'});assert b':wire 35 :refused :not-granted' in r.stderr and not denied.exists()
  routes.append(dict(compiler=pin(compiler),generator=pin(tool),output=pin(good),refusals=8))
 assert routes[0]['output']==routes[1]['output']
 report=dict(status='PASS_NATIVE_STATIC_PROFILE_GENERATOR',source=graph,inputs={p:pin(ROOT/p) for p in ['seed/MEMORY-MAP','seed/00-ns.kotoba','seed/gen-static-ns.kotoba']},routes=routes,nativeGeneration=True,PythonGeneration=False)
 (out/'native-static-profile.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])
if __name__=='__main__':
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--build',type=Path);g.add_argument('--complete',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.build.resolve() if a.build else None,a.complete.resolve() if a.complete else None,a.output.resolve())
