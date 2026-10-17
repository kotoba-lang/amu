#!/usr/bin/env python3
"""Independent full64 source oracles and exact native raw fuel/arena pairs."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,shutil,subprocess,re
ROOT=Path(__file__).resolve().parents[2]
# Static single-feature audits (native-gate) compare against AUDITED, the adopted compiler at which they were established
# and last held; the same-algorithm m104 adoption replaced it. Every behavioural pair runs on the current adopted compiler (ON).
AUDITED=ROOT/'docs/evidence/same-algo-m104-20261015/previous-bootstrap.bin';AUDITED_SHA256='87efe842dc0389f0ba7d476fcf034f6820483632df61fad53b474a2297e3e345'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--selfbuild-output',type=Path,required=True);a=ap.parse_args();O=a.selfbuild_output.resolve();D=O/'artifacts/positive-quotient-controls';D.mkdir(exist_ok=False);raw=D/'raw';raw.mkdir()
 L=O/'host/kexe-loader';F=ROOT/'seed/tests/positive-power2-quotient';S=D/'controls.kotoba';shutil.copy2(F/'controls.kotoba',S)
 E=ROOT/'docs/evidence/positive-quotient-20261013';J=ROOT/'docs/evidence/oneword-jump-20261014';P={'OFF':E/'previous-bootstrap.bin','PRE':J/'previous-bootstrap.bin','ON':O/'artifacts/G2.bin','AUDITED':AUDITED}
 assert sha(P['OFF'])=='9ce5f89aec3c04a139e4bb713eb3613fd482ae70fd41d0271bc021b550a0668b'
 assert sha(P['PRE'])=='f49356b0e979293ee6f42b622089dc77e2dbb55d0a28b07d8a8f35125d8a6cdb'
 assert sha(P['AUDITED'])==AUDITED_SHA256
 assert sha(P['ON'])==json.loads((ROOT/'seed/adoption-20261017.json').read_text())['nativeImageSHA256']
 pins={p:sha(p)for p in[L,S,*P.values()]};env={k:v for k,v in os.environ.items()if not k.startswith('KEXE_')};env.update(KEXE_COMMAND='1',KEXE_CAP_RESOURCES_35=str(D),KEXE_FUEL='off',KEXE_VECTORS='4194304',KEXE_VECTOR_ITEMS='134217728',KEXE_STRING_POOL='268435456',KEXE_PAIRS='16777216',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800',TMPDIR=str(D));calls=[]
 def run(tag,args,e):
  z=subprocess.run(list(map(str,args)),cwd=D,env=e,capture_output=True,timeout=1800);(raw/(tag+'.stdout')).write_bytes(z.stdout);(raw/(tag+'.stderr')).write_bytes(z.stderr);calls.append(dict(tag=tag,exit=z.returncode));(D/'calls.json').write_text(json.dumps(calls,indent=2)+'\n');assert z.returncode==0 and all(sha(p)==h for p,h in pins.items()),tag;return z.stdout,z.stderr
 arms={}
 for tag,p in P.items():
  k=D/(tag+'.kseed');b=D/(tag+'.bin');base=[L,p,'0','0','aarch64','35,37,38,39','--']
  for name,args in [('compile',['compile',S,'--target','aarch64-macos','--output',k]),('extract',['extract-native',k,'--symbol','run','--output',b])]:_,err=run(tag+'-'+name,base+args,env);assert not err
  h,payload=k.read_bytes().split(b'\n\n',1);assert payload==b.read_bytes();ex={n:[int(o),int(a)]for n,o,a in map(str.split,h.decode().splitlines()[1:])};arms[tag]=dict(native=pin(b),container=pin(k),source=pin(S),exports=ex,offset=ex['run'][0],arity=ex['run'][1]);assert ex['run'][1]==2
 spec=importlib.util.spec_from_file_location('positive_physical',E/'native-gate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);proof=m.audit(arms['OFF'],arms['PRE']);assert proof['changed']and len(proof['sites'])==6;(D/'physical-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
 spec=importlib.util.spec_from_file_location('skip_physical',J/'native-gate.py');jump=importlib.util.module_from_spec(spec);spec.loader.exec_module(jump);skip=jump.audit(arms['PRE'],arms['AUDITED']);assert skip['changed']and len(skip['sites'])==6;(D/'skip-proof.json').write_text(json.dumps(skip,indent=2)+'\n')
 cases=json.loads((F/'cases.json').read_text())['cases'];assert len(cases)==152
 guest={k:v for k,v in env.items()if not k.startswith('KEXE_')};guest.update(KEXE_STRUCTURED_REPORT='1',KEXE_ARENA_USE='1',KEXE_FUEL='100000',KEXE_CPU_SECONDS='60',KEXE_WALL_SECONDS='60')
 for i,c in enumerate(cases):
  pairs=[]
  for tag,p in [(k,arms[k])for k in ['OFF','ON']]:
   o,e=run(f'{i}-{tag}',[L,p['native']['path'],p['offset'],'2','aarch64','37',c['mode'],c['x']],guest);v=re.search(rb':status :ok :result (-?\d+)',o);assert v and int(v[1])==c['result'];fuel=re.search(rb':fuel \{:initial (\d+) :remaining (\d+)\}',o);assert fuel and int(fuel[1])==100000;assert len(re.findall(rb':[a-z-]+ \d+',e))==17;pairs.append((o,e))
  assert pairs[0]==pairs[1],('EXACT_RAW_FUEL_ARENA_MISMATCH',i)
 report=dict(status='PASS_POSITIVE_QUOTIENT_GENERIC152_FULL64_EXACT_RAW_FUEL_ALL17',pairs=152,guestCalls=304,compilerCalls=8,actualB2Sites=6,actualTwoNOPSkipSites=6,historicalRangeAndScratchProofRetained=True,staticAuditCompiler=AUDITED_SHA256,performanceMeasured=False);(O/'host/positive-quotient-controls-report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])
if __name__=='__main__':main()
