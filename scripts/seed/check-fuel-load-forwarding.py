#!/usr/bin/env python3
"""Fuel-load forwarding controls: previous main (OFF) against the self-built compiler (ON).

The original 19 sources compile with both producers. Images, containers and exports must have
identical size and layout; every differing word must be an exact `ldr xD,[x7,#8]` in OFF that is
`mov xD,xS` or `nop` in ON. Every arity-0/1 export then runs on both images at many fuel levels
(early exhaustion included); exit status, stdout and stderr (result, remaining fuel, trap kind and
all 17 arena counters) must be byte-identical. Correctness only: no timing is taken."""
import argparse,hashlib,json,os,struct,subprocess,sys,tarfile
from pathlib import Path
assert not sys.flags.optimize
ROOT=Path(__file__).resolve().parents[2]
ORIGINAL19='workspace/held-compiler-cli30-bounded-balanced-byte-tree-token-capacity-picojpeg-g4-original19-compile38-source-v4-20261012-next/run-outputs/'
INPUTS=[0,1,2,3]
FUELS=list(range(0,13))+[25,100,1000,100000]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def words(b):return struct.unpack('<%dI'%(len(b)//4),b[:len(b)//4*4])
def forwarded(old,new):
 return (old&0xffffffe0)==0xf94004e0 and (new==0xd503201f or ((new&0xffe0ffe0)==0xaa0003e0 and (new&31)==(old&31)))
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--selfbuild-output',type=Path,required=True);a=ap.parse_args()
 out=a.selfbuild_output.resolve();W=out/'artifacts/fuel-load-forwarding';W.mkdir(exist_ok=False);raw=W/'raw';raw.mkdir()
 loader=out/'host/kexe-loader';receipt=json.loads((ROOT/'seed/adoption-20261012.json').read_text())
 off=receipt['fuelLoadForwardingQualification']['offBootstrap'];producers={'OFF':(ROOT/off['path']).resolve(),'ON':out/'artifacts/G2.bin'}
 assert producers['OFF'].is_relative_to(ROOT.resolve()) and sha(producers['OFF'])==off['sha256']==receipt['previousMainSnapshot']['nativeImageSHA256']
 assert sha(producers['ON'])==receipt['nativeImageSHA256']
 archive=ROOT/'docs/evidence/native-selfhost-paused-20261012/evidence.tgz'
 with tarfile.open(archive) as t:
  report=json.loads(t.extractfile(ORIGINAL19+'report.json').read())
  symbols={c['label'].removesuffix('-extract'):c['case']['symbol'] for c in report['calls'] if c['case']['kind']=='extract'}
  names=sorted(pathlib_stem for pathlib_stem in (Path(m.name).stem for m in t.getmembers() if m.name.startswith(ORIGINAL19) and m.name.endswith('.kotoba')) if pathlib_stem!='seed-unity')
  assert len(names)==19,len(names)
  for n in names:(W/(n+'.kotoba')).write_bytes(t.extractfile(ORIGINAL19+n+'.kotoba').read())
 pins={p:sha(p) for p in [loader,*producers.values()]}
 env={k:v for k,v in os.environ.items() if not k.startswith('KEXE_')}
 env.update(KEXE_COMMAND='1',KEXE_CAP_RESOURCES_35=str(W),KEXE_FUEL='off',KEXE_VECTORS='4194304',KEXE_VECTOR_ITEMS='134217728',KEXE_STRING_POOL='268435456',KEXE_PAIRS='16777216',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800',TMPDIR=str(W))
 calls=[]
 def run(argv,name,e,timeout=1800):
  z=subprocess.run(list(map(str,argv)),cwd=W,env=e,capture_output=True,timeout=timeout)
  calls.append(dict(name=name,exit=z.returncode,stdoutSHA256=hashlib.sha256(z.stdout).hexdigest(),stderrSHA256=hashlib.sha256(z.stderr).hexdigest()))
  assert all(sha(p)==h for p,h in pins.items()),'input mutation'
  return z.returncode,z.stdout,z.stderr
 images=[];rewrites={'mov':0,'nop':0};pairs=0
 guest={k:v for k,v in env.items() if not k.startswith('KEXE_')};guest.update(KEXE_ARENA_USE='1',KEXE_STRUCTURED_REPORT='1',KEXE_CPU_SECONDS='60',KEXE_WALL_SECONDS='60',KEXE_PAIRS='8388608')
 for n in names:
  arms={}
  for tag,p in producers.items():
   k=W/f'{n}-{tag}.kseed';b=W/f'{n}-{tag}.bin';prefix=[loader,p,'0','0','aarch64','35,37,38,39','--']
   for cmd,tail in [('compile',[W/(n+'.kotoba'),'--target','aarch64-macos','--output',k]),('extract-native',[k,'--symbol',symbols[n],'--output',b])]:
    rc,o,e=run(prefix+[cmd,*tail],f'{n}-{tag}-{cmd}',env);assert rc==0 and not e,(n,tag,cmd,rc,e[-400:])
   head,payload=k.read_bytes().split(b'\n\n',1);assert payload==b.read_bytes()
   arms[tag]=(b,head,payload)
  (ob,oh,op),(nb,nh,np)=arms['OFF'],arms['ON']
  assert oh==nh and len(op)==len(np) and op[len(op)//4*4:]==np[len(np)//4*4:],n+': layout changed'
  diff=[(x,y) for x,y in zip(words(op),words(np)) if x!=y]
  assert all(forwarded(x,y) for x,y in diff),n+': non-forwarding difference'
  mov=sum(1 for x,y in diff if y!=0xd503201f);rewrites['mov']+=mov;rewrites['nop']+=len(diff)-mov
  exports=[(s,int(o),int(r)) for s,o,r in map(str.split,oh.decode().splitlines()[1:])]
  for s,off,arity in exports:
   if arity>1:continue
   for x in (INPUTS if arity==1 else [None]):
    for fuel in FUELS:
     guest['KEXE_FUEL']=str(fuel);res=[]
     for tag,img in (('OFF',ob),('ON',nb)):
      argv=[loader,img,str(off),str(arity),'aarch64','37']+([str(x)] if arity==1 else [])
      res.append(run(argv,f'{n}-{s}-{x}-{fuel}-{tag}',guest,timeout=120))
     if res[0]!=res[1]:
      (raw/f'{n}-{s}-{x}-{fuel}.json').write_text(json.dumps([[r[0],r[1].decode(errors='replace'),r[2].decode(errors='replace')] for r in res],indent=1))
      raise SystemExit(f'EXACT_RAW_MISMATCH {n} {s} input={x} fuel={fuel}')
     pairs+=1
  images.append(dict(workload=n,bytes=len(np),offSHA256=sha(ob),onSHA256=sha(nb),forwardedLoads=len(diff)))
 (W/'calls.json').write_text(json.dumps(calls,indent=1)+'\n')
 assert rewrites['mov']+rewrites['nop']>0,'no load was forwarded'
 r=dict(status='PASS_FUEL_LOAD_FORWARDING_LAYOUT_AND_EXACT_RAW_PAIRS',images=images,rewrites=rewrites,pairs=pairs,guestCalls=2*pairs,compilerCalls=4*len(names),performanceMeasurement=False)
 (W/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='images'}))
if __name__=='__main__':main()
