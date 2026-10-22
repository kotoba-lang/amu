#!/usr/bin/env python3
# Ported after the C loader was removed (scripts/seed/RETIRED.md): --selfbuild-output is now the output
# directory of scripts/seed/selfhost-bootstrap.py; payloads run through its C-free aarch64 runner
# (R-aarch64.elf) and ON is its adopted fixed-point image (G3.bin). Run on arm64 Linux.
"""Independent native mask-writer result, trap, fuel and arena paired controls."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,shutil,subprocess,re
ROOT=Path(__file__).resolve().parents[2]
# Static single-feature audits (native-gate) compare against AUDITED, the adopted compiler at which they were established
# and last held; the same-algorithm m104 adoption replaced it. Every behavioural pair runs on the current adopted compiler (ON).
AUDITED=ROOT/'docs/evidence/same-algo-m104-20261015/previous-bootstrap.bin';AUDITED_SHA256='87efe842dc0389f0ba7d476fcf034f6820483632df61fad53b474a2297e3e345'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--selfbuild-output',type=Path,required=True);a=ap.parse_args();O=a.selfbuild_output.resolve();(O/'artifacts').mkdir(exist_ok=True);(O/'host').mkdir(exist_ok=True);D=O/'artifacts/prepaid-fuel-reuse-controls';D.mkdir(exist_ok=False);raw=D/'raw';raw.mkdir()
 E=ROOT/'docs/evidence/fuel-register-reuse-20261014';F=ROOT/'seed/tests/prepaid-fuel-reuse';L=O/'R-aarch64.elf';S=D/'controls.kotoba';shutil.copy2(F/'controls.kotoba',S);P={'OFF':E/'previous-bootstrap.bin','ON':O/'G3.bin','AUDITED':AUDITED}
 assert sha(P['OFF'])=='e918a3d56f79671494991a65ed4762336ef3704afad130b10d8fcee710d936ec'
 assert sha(P['AUDITED'])==AUDITED_SHA256
 assert sha(P['ON'])==json.loads((ROOT/'seed/adoption-20261017.json').read_text())['nativeImageSHA256']
 pins={p:sha(p)for p in[L,S,F/'cases.json',*P.values(),E/'native-gate.py',E/'source-pool.py',E/'index-proof-v3.py',E/'scratch-effects.py',E/'trusted-loader-abi.c']};env={k:v for k,v in os.environ.items()if not k.startswith('KEXE_')};env.update(KEXE_COMMAND='1',KEXE_STACK_BYTES='8388608',KEXE_CAP_RESOURCES_35=str(D),KEXE_FUEL='off',KEXE_VECTORS='4194304',KEXE_VECTOR_ITEMS='134217728',KEXE_STRING_POOL='268435456',KEXE_PAIRS='16777216',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800',TMPDIR=str(D));calls=[]
 def run(tag,args,e):
  z=subprocess.run(list(map(str,args)),cwd=D,env=e,capture_output=True,timeout=1800);(raw/(tag+'.stdout')).write_bytes(z.stdout);(raw/(tag+'.stderr')).write_bytes(z.stderr);calls.append(dict(tag=tag,exit=z.returncode));(D/'calls.json').write_text(json.dumps(calls,indent=2)+'\n');assert all(sha(p)==h for p,h in pins.items()),('INPUT_MUTATION',tag);return z.returncode,z.stdout,z.stderr
 arms={}
 for tag,p in P.items():
  k=D/(tag+'.kseed');b=D/(tag+'.bin');base=[L,p,'0','0','aarch64','35,37,38,39','--']
  for name,args in [('compile',['compile',S,'--target','aarch64-macos','--output',k]),('extract',['extract-native',k,'--symbol','run','--output',b])]:
   code,_,err=run(tag+'-'+name,base+args,env);assert code==0 and not err
  h,payload=k.read_bytes().split(b'\n\n',1);assert payload==b.read_bytes();ex={n:[int(o),int(a)]for n,o,a in map(str.split,h.decode().splitlines()[1:])};arms[tag]=dict(native=pin(b),container=pin(k),source=pin(S),exports=ex,offset=ex['run'][0],arity=ex['run'][1]);assert ex['run'][1]==2
 spec=importlib.util.spec_from_file_location('mask_physical',E/'native-gate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);audited=arms.pop('AUDITED');proof=m.audit(arms['OFF'],audited);assert proof['changed']and len(proof['sites'])==18;(D/'physical-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
 cases=json.loads((F/'cases.json').read_text())['cases'];assert len(cases)==596
 guest={k:v for k,v in env.items()if not k.startswith('KEXE_')};guest.update(KEXE_STRUCTURED_REPORT='1',KEXE_ARENA_USE='1',KEXE_CPU_SECONDS='60',KEXE_WALL_SECONDS='60');actual=refusals=0
 for i,c in enumerate(cases):
  pairs=[];guest['KEXE_FUEL']=str(c['fuel'])
  for tag,p in arms.items():
   code,o,e=run(f'{i}-{tag}',[L,p['native']['path'],p['offset'],'2','aarch64','37',c['mode'],c['x']],guest)
   if c['fuel']==0:
    assert code==2 and o==b''and e==b'kexe-loader: KEXE_FUEL must be a positive decimal integer, or off\n';refusals+=1
   else:
    actual+=1
    if b':status :ok' in o:
     assert code==0 and c['mode']!=3;v=re.search(rb':result (-?\d+)',o);assert v and int(v[1])==c['result']
    else:
     assert code==120 and b':status :trap :exit 120' in o
     if b'KEXE_TRAP {:kind :signal :signal :SIGILL}'in e:assert c['mode']==3
     else:
      assert 1<=c['fuel']<=128 and b'KEXE_TRAP {:kind :signal :signal :SIGTRAP}'in e and b'KEXE_TRAP {:kind :budget :reason :budget/fuel}'in e and re.search(rb':remaining 0\}',o)
    f=re.search(rb':fuel \{:initial (\d+) :remaining (\d+)\}',o);assert f and int(f[1])==c['fuel']and 0<=int(f[2])<=c['fuel'];assert len(re.findall(rb':[a-z-]+ \d+',e))==17
   pairs.append((code,o,e))
  assert pairs[0]==pairs[1],('EXACT_RAW_EXIT_FUEL_ARENA_MISMATCH',i)
 assert actual==1192 and refusals==0
 report=dict(status='PASS_PREPAID_FUEL_REUSE_GENERIC84_AND_FUEL512_FULL64_COLD_PAID_BOUNDARIES_ALL17',pairs=596,loaderInvocations=1192,actualGuestCalls=actual,configurationRefusals=refusals,compilerCalls=6,actualFuelAccessElisions=18,removedLoads=9,removedStores=9,staticAuditCompiler=AUDITED_SHA256,performanceMeasured=False);(O/'host/prepaid-fuel-reuse-controls-report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])
if __name__=='__main__':main()
