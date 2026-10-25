#!/usr/bin/env python3
# Ported after the C loader was removed (scripts/seed/RETIRED.md): --selfbuild-output is now the output
# directory of scripts/seed/selfhost-bootstrap.py; payloads run through its C-free aarch64 runner
# (R-aarch64.elf) and ON is its adopted fixed-point image (G3.bin). Run on arm64 Linux.
"""Source oracles, original fuel/traps and native nonzero dominance controls."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[2]
# Static single-feature audits (native-gate) compare against AUDITED, the adopted compiler at which they were established
# and last held; the same-algorithm m104 adoption replaced it. Every behavioural pair runs on the current adopted compiler (ON).
AUDITED=ROOT/'docs/evidence/same-algo-m104-20261015/previous-bootstrap.bin';AUDITED_SHA256='87efe842dc0389f0ba7d476fcf034f6820483632df61fad53b474a2297e3e345'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--selfbuild-output',type=Path,required=True);a=ap.parse_args();O=a.selfbuild_output.resolve();(O/'artifacts').mkdir(exist_ok=True);(O/'host').mkdir(exist_ok=True);D=O/'artifacts/nonzero-guard-charge-controls';D.mkdir(exist_ok=False);raw=D/'raw';raw.mkdir()
 E=ROOT/'docs/evidence/nonzero-guard-charge-20261014';F=ROOT/'seed/tests/nonzero-guard-charge';L=O/'R-aarch64.elf';S=D/'controls.kotoba';shutil.copy2(F/'controls.kotoba',S);P={'OFF':E/'previous-bootstrap.bin','ON':O/'G3.bin','AUDITED':AUDITED}
 assert sha(P['OFF'])=='611ac7a79532c345bc36c03280962d3b847e1ad622e3f39a0a2588ad794dd008'
 assert sha(P['AUDITED'])==AUDITED_SHA256
 assert sha(P['ON'])==json.loads((ROOT/'seed/adoption-20261022.json').read_text())['nativeImageSHA256']
 pins={p:sha(p)for p in [L,S,F/'cases.json',*P.values(),E/'native-gate.py',E/'source-pool.py',E/'trusted-loader-abi.c']};env={k:v for k,v in os.environ.items()if not k.startswith('KEXE_')};env.update(KEXE_COMMAND='1',KEXE_STACK_BYTES='8388608',KEXE_CAP_RESOURCES_35=str(D),KEXE_FUEL='off',KEXE_VECTORS='4194304',KEXE_VECTOR_ITEMS='134217728',KEXE_STRING_POOL='268435456',KEXE_PAIRS='16777216',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800',TMPDIR=str(D));calls=[]
 def run(tag,args,e):
  z=subprocess.run(list(map(str,args)),cwd=D,env=e,capture_output=True,timeout=1800);(raw/(tag+'.stdout')).write_bytes(z.stdout);(raw/(tag+'.stderr')).write_bytes(z.stderr);calls.append(dict(tag=tag,exit=z.returncode));(D/'calls.json').write_text(json.dumps(calls,indent=2)+'\n');assert all(sha(p)==h for p,h in pins.items());return z.returncode,z.stdout,z.stderr
 arms={}
 for tag,p in P.items():
  k=D/(tag+'.kseed');b=D/(tag+'.bin');base=[L,p,'0','0','aarch64','35,37,38,39','--']
  for name,args in [('compile',['compile',S,'--target','aarch64-macos','--output',k]),('extract',['extract-native',k,'--symbol','run','--output',b])]:
   code,_,err=run(tag+'-'+name,base+args,env);assert code==0 and not err
  h,payload=k.read_bytes().split(b'\n\n',1);assert payload==b.read_bytes();ex={n:[int(o),int(a)]for n,o,a in map(str.split,h.decode().splitlines()[1:])};assert ex['run'][1]==ex['char-at'][1]==2;arms[tag]=dict(native=pin(b),container=pin(k),source=pin(S),exports=ex)
 spec=importlib.util.spec_from_file_location('nonzero_physical',E/'native-gate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);audited=arms.pop('AUDITED');proof=m.audit(arms['OFF'],audited);assert proof['changed']and len(proof['sites'])==1;(D/'physical-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
 cases=json.loads((F/'cases.json').read_text())['cases'];assert len(cases)==614;guest={k:v for k,v in env.items()if not k.startswith('KEXE_')};guest.update(KEXE_ARENA_USE='1',KEXE_STRUCTURED_REPORT='1',KEXE_CPU_SECONDS='60',KEXE_WALL_SECONDS='60');actual=refusals=0
 for i,c in enumerate(cases):
  pair=[];guest['KEXE_FUEL']=str(c['fuel'])
  for tag,p in arms.items():
   off,arity=p['exports'][c['symbol']];code,o,e=run(f'{i}-{tag}',[L,p['native']['path'],off,arity,'aarch64','37',c['kind'],c['i']],guest)
   if c['fuel']>(1<<53)-1:
    assert code==2 and not o and e==b'kexe-loader: KEXE_FUEL exceeds the maximum budget 9007199254740991 (2^53-1)\n';refusals+=1
   else:
    actual+=1
    if b':status :ok'in o:
     v=re.search(rb':result (-?\d+)',o);assert code==0 and c['result'] is not None and v and int(v[1])==c['result']
    else:
     assert code==120 and b':status :trap :exit 120'in o
     if b':SIGTRAP'in e:assert c['fuel']<=128 and b'budget/fuel'in e and re.search(rb':remaining 0\}',o)
     else:assert b':SIGILL'in e and c['result'] is None
    f=re.search(rb':fuel \{:initial (\d+) :remaining (\d+)\}',o);assert f and int(f[1])==c['fuel'] and 0<=int(f[2])<=c['fuel'] and len(re.findall(rb':[a-z-]+ \d+',e))==17
   pair.append((code,o,e))
  assert pair[0]==pair[1],('EXACT_RAW_STRING_FUEL_TRAP_ARENA',c)
 assert actual==1192 and refusals==36
 report=dict(status='PASS_NONZERO_STRING614_ASCII_UNICODE_POOL_ENDPOINT_INVALID_HANDLE_INDEX_FUEL1_128_PUBLIC_MAX_EXACT_RAW_ALL17',pairs=614,actualGuestCalls=actual,configurationRefusals=refusals,compilerCalls=6,unreachableEdgeElisions=1,staticAuditCompiler=AUDITED_SHA256,performanceMeasured=False);(O/'host/nonzero-guard-charge-controls-report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])
if __name__=='__main__':main()
