#!/usr/bin/env python3
"""SIGSTOP/SIGCONT across native clock_nanosleep; explicit native probe only."""
import argparse, json, os, signal, subprocess, time, hashlib, platform
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--probe',required=True,type=Path);p.add_argument('--control',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
assert platform.system()=='Linux'
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
a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
