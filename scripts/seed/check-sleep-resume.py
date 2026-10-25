#!/usr/bin/env python3
"""SIGSTOP/SIGCONT across native clock_nanosleep; explicit native probe only."""
import argparse, json, os, signal, subprocess, time, hashlib, platform
from pathlib import Path
p=argparse.ArgumentParser()
producer=p.add_mutually_exclusive_group(required=True)
producer.add_argument('--probe',type=Path)
producer.add_argument('--compiler',type=Path,help='build both probes natively, including a no-restart_syscall control')
p.add_argument('--control',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
assert platform.system()=='Linux'
if a.compiler and a.control:
 p.error('--compiler builds its own control; --control is only for --probe')
def pin(path):
 data=path.read_bytes();return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
build=None
if a.compiler:
 root=Path(__file__).resolve().parents[2]
 target={'aarch64':'aarch64-linux','arm64':'aarch64-linux','x86_64':'x86_64-linux','AMD64':'x86_64-linux'}[platform.machine()]
 art=a.output.resolve().parent/'artifacts';art.mkdir(parents=True,exist_ok=False)
 manifest='seed/X86_64-LINUX-SELFHOST-MANIFEST'
 paths=[v for v in (root/manifest).read_text().splitlines() if v and not v.startswith('#')]
 text=''.join((root/v).read_text()+'\n' for v in paths)
 # Keep clock_nanosleep allowed; remove only restart_syscall in both runtimes.
 # The control must start sleeping before STOP/CONT exposes the missing rule.
 for clock,restart in [(115,128),(230,219)]:
  old=f'(kxrt-allow-nr p (kxrt-allow-nr p i7 {clock}) {restart})'
  assert text.count(old)==1,('restart control anchor',clock,restart,text.count(old))
  text=text.replace(old,f'(kxrt-allow-nr p i7 {clock})')
 control_source=art/'no-restart-compiler.kotoba';control_source.write_text(text)
 source=art/'probe.kotoba';source.write_bytes((root/'seed/tests/clock-sleep-resume/probe.kotoba').read_bytes())
 calls=[]
 def compile_(compiler,src,dst):
  result=subprocess.run([str(compiler.resolve()),'compile',str(src),'--target',target,'--output',str(dst),'--format','static'],
    env=dict(PATH='/nonexistent',KEXE_CAP_RESOURCES_35=str(art),KEXE_STACK_BYTES='8388608'),capture_output=True,timeout=1800)
  (art/(dst.name+'.stdout')).write_bytes(result.stdout);(art/(dst.name+'.stderr')).write_bytes(result.stderr)
  assert result.returncode==0 and not result.stderr,(dst,result.returncode,result.stderr[-600:])
  dst.chmod(0o755);calls.append(dict(source=pin(src),image=pin(dst),exit=0))
 control_compiler=art/'no-restart-compiler.elf'
 compile_(a.compiler,control_source,control_compiler)
 a.probe=art/'candidate.elf';a.control=art/'no-restart.elf'
 compile_(a.compiler,source,a.probe);compile_(control_compiler,source,a.control)
 build=dict(compiler=pin(a.compiler),target=target,sourceGraph={v:pin(root/v) for v in [manifest,*paths]},
   probeSource=pin(source),controlMutation='only restart_syscall removed; clock_nanosleep retained in both runtimes',calls=calls)
def run(path,expected):
 env=dict(os.environ,KEXE_ALLOW='7,37,39',KEXE_CAP_RESOURCES_35='')
 child=subprocess.Popen([str(path.resolve())],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 assert child.stderr.readline()=='ready\n'
 time.sleep(0.05);os.kill(child.pid,signal.SIGSTOP)
 _,st=os.waitpid(child.pid,os.WUNTRACED);assert os.WIFSTOPPED(st)
 time.sleep(0.15);os.kill(child.pid,signal.SIGCONT)
 out,err=child.communicate(timeout=8);assert child.returncode==expected,(out,err,child.returncode)
 if expected==0: assert out=='resumed\n' and not err,(out,err)
 else: assert 'SIGSYS' in err,(out,err)
 return {'artifactSha256':hashlib.sha256(path.read_bytes()).hexdigest(),'exit':child.returncode,'stdout':out,'stderr':err,'passed':True}
r={'schema':'amu.native.sleep-resume.gate.v1','host':platform.machine(),'candidate':run(a.probe,0)}
if a.control:r['oldRuntimeControl']=run(a.control,120)
if build:r['nativeBuild']=build
a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
